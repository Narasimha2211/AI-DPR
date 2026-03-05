# ============================================
# Quality Scoring API Routes – PostgreSQL backed
# ============================================

import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.database import get_db
from app.services import db_service
from app.modules.document_parser.pdf_extractor import PDFExtractor
from app.modules.document_parser.nlp_processor import NLPProcessor
from app.modules.document_parser.table_extractor import TableExtractor
from app.modules.quality_scorer.quality_report import QualityScorer

router = APIRouter(prefix="/api/scoring", tags=["Quality Scoring"])

pdf_extractor = PDFExtractor()
nlp_processor = NLPProcessor()
table_extractor = TableExtractor()
quality_scorer = QualityScorer()


@router.post("/quality-score")
async def get_quality_score(
    file_path: str,
    document_id: int = Query(None, description="Document ID from upload"),
    state: Optional[str] = Query(None, description="Indian state name"),
    project_type: Optional[str] = Query(None, description="Project type"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate comprehensive quality score for a DPR.
    Results are persisted in PostgreSQL.
    """
    # Normalise optional params (frontend may send empty strings)
    state = state.strip() if state else None
    project_type = project_type.strip() if project_type else None

    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise HTTPException(status_code=404, detail="File not found")

    t0 = time.time()

    try:
        # Extract text
        if file_path_obj.suffix.lower() == ".pdf":
            extraction = pdf_extractor.extract_text(file_path)
        elif file_path_obj.suffix.lower() in [".docx", ".doc"]:
            extraction = pdf_extractor.extract_from_docx(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

        # NLP Analysis
        nlp_analysis = nlp_processor.analyze_document(extraction.get("full_text", ""))

        # Table Analysis
        tables = extraction.get("tables", [])
        table_analysis = table_extractor.extract_tables_from_text(tables) if tables else None

        # Quality Scoring
        score_report = quality_scorer.score_dpr(
            nlp_analysis=nlp_analysis,
            table_analysis=table_analysis,
            state=state,
            project_type=project_type
        )

        # Persist to PostgreSQL
        if document_id:
            doc = await db_service.get_document(db, document_id)
            if doc:
                await db_service.save_quality_score(db, document_id, score_report)

        duration_ms = (time.time() - t0) * 1000
        await db_service.log_action(
            db, action="quality_score", document_id=document_id, state=state,
            details={"score": score_report.get("composite_score")},
            duration_ms=duration_ms,
        )

        return {
            "document_id": document_id,
            "file_name": extraction.get("file_name"),
            "quality_report": score_report,
            "persisted": document_id is not None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quality scoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compliance-check")
async def check_compliance(
    file_path: str,
    state: str = Query(None),
    project_type: str = Query(None),
):
    """Run compliance validation against government standards."""
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        extraction = pdf_extractor.extract_text(file_path)
        nlp_analysis = nlp_processor.analyze_document(extraction.get("full_text", ""))

        compliance_report = quality_scorer.compliance_engine.validate_compliance(
            nlp_analysis, state=state, project_type=project_type
        )

        return {
            "file_name": extraction.get("file_name"),
            "compliance_report": compliance_report
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compliance check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
