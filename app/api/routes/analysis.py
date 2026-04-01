# ============================================
# Analysis API Routes – PostgreSQL backed
# NLP Processing & Document Analysis
# ============================================

import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from config.settings import settings
from app.models.database import get_db
from app.services import db_service
from app.modules.document_parser.pdf_extractor import PDFExtractor
from app.modules.document_parser.nlp_processor import NLPProcessor
from app.modules.document_parser.table_extractor import TableExtractor
from app.modules.document_parser.ocr_engine import OCREngine

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

# Initialize modules
pdf_extractor = PDFExtractor()
nlp_processor = NLPProcessor()
table_extractor = TableExtractor()
ocr_engine = OCREngine()


@router.post("/analyze")
async def analyze_dpr(
    file_path: str,
    document_id: int = Query(None, description="Document ID from upload"),
    state: Optional[str] = Query(None, description="Indian state name"),
    include_ocr: bool = Query(False, description="Enable OCR for scanned documents"),
    db: AsyncSession = Depends(get_db),
):
    """
    Run comprehensive NLP analysis on an uploaded DPR.
    Results are persisted in PostgreSQL.
    """
    # Normalise optional params (frontend may send empty strings)
    state = state.strip() if state else None

    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    t0 = time.time()

    try:
        # Step 1: Extract text
        logger.info(f"Starting analysis of {file_path_obj.name}")

        if file_path_obj.suffix.lower() == ".pdf":
            extraction = pdf_extractor.extract_text(file_path)
        elif file_path_obj.suffix.lower() in [".docx", ".doc"]:
            extraction = pdf_extractor.extract_from_docx(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported format for analysis")

        full_text = extraction.get("full_text", "")

        # OCR fallback if needed
        if (extraction.get("needs_ocr", False) or include_ocr) and file_path_obj.suffix.lower() == ".pdf":
            logger.info("Running OCR on scanned document...")
            ocr_result = ocr_engine.extract_text_from_pdf_images(
                file_path, state=state
            )
            if ocr_result.get("full_text"):
                full_text = ocr_result["full_text"]
                extraction["ocr_applied"] = True

        if not full_text or len(full_text.strip()) < 50:
            raise HTTPException(
                status_code=422,
                detail="Could not extract meaningful text from the document"
            )

        # Step 2: NLP Analysis
        nlp_analysis = nlp_processor.analyze_document(full_text)

        # Step 3: Table Analysis
        tables = extraction.get("tables", [])
        table_analysis = table_extractor.extract_tables_from_text(tables) if tables else {}

        # Step 4: Persist to PostgreSQL
        if document_id:
            doc = await db_service.get_document(db, document_id)
            if doc:
                await db_service.save_analysis(
                    db, document_id,
                    nlp_result=nlp_analysis,
                    table_analysis=table_analysis,
                    extraction_meta={
                        "total_pages": extraction.get("total_pages", 0),
                        "method": extraction.get("extraction_method", "unknown"),
                    },
                )

        duration_ms = (time.time() - t0) * 1000
        await db_service.log_action(
            db, action="analyze", document_id=document_id, state=state,
            details={"file": file_path_obj.name}, duration_ms=duration_ms,
        )

        # Combine results
        result = {
            "document_id": document_id,
            "file_name": extraction.get("file_name"),
            "total_pages": extraction.get("total_pages", 0),
            "extraction_method": extraction.get("extraction_method", "unknown"),
            "ocr_applied": extraction.get("ocr_applied", False),
            "nlp_analysis": nlp_analysis,
            "table_analysis": table_analysis,
            "metadata": extraction.get("metadata", {}),
            "persisted": document_id is not None,
        }

        logger.info(f"Analysis complete: {nlp_analysis['summary']}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/extract-text")
async def extract_text_only(file_path: str):
    """Extract raw text from a document."""
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if file_path_obj.suffix.lower() == ".pdf":
        result = pdf_extractor.extract_text(file_path)
    elif file_path_obj.suffix.lower() in [".docx", ".doc"]:
        result = pdf_extractor.extract_from_docx(file_path)
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

    return {
        "file_name": result.get("file_name"),
        "total_pages": result.get("total_pages", 0),
        "total_words": len(result.get("full_text", "").split()),
        "text_preview": result.get("full_text", "")[:2000],
        "needs_ocr": result.get("needs_ocr", False)
    }


@router.post("/identify-sections")
async def identify_sections(file_path: str):
    """Identify DPR sections in a document."""
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise HTTPException(status_code=404, detail="File not found")

    extraction = pdf_extractor.extract_text(file_path)
    sections = nlp_processor.identify_sections(extraction.get("full_text", ""))

    found = {k: v for k, v in sections.items() if v["found"]}
    missing = {k: v for k, v in sections.items() if not v["found"]}

    return {
        "found_sections": {k: {"header": v["header"], "word_count": v["word_count"]} for k, v in found.items()},
        "missing_sections": list(missing.keys()),
        "found_count": len(found),
        "missing_count": len(missing),
        "completeness": round(len(found) / max(len(sections), 1) * 100, 2)
    }


@router.post("/extract-financial")
async def extract_financial_data(file_path: str):
    """Extract financial figures from a DPR."""
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise HTTPException(status_code=404, detail="File not found")

    extraction = pdf_extractor.extract_text(file_path)
    figures = nlp_processor.extract_financial_figures(extraction.get("full_text", ""))

    total_crores = sum(f.get("value_in_crores", 0) for f in figures)

    return {
        "financial_figures": figures,
        "total_figures_found": len(figures),
        "total_value_crores": round(total_crores, 4)
    }
