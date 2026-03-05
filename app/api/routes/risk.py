# ============================================
# Risk Prediction API Routes – PostgreSQL backed
# ============================================

import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.database import get_db
from app.services import db_service
from app.modules.document_parser.pdf_extractor import PDFExtractor
from app.modules.document_parser.nlp_processor import NLPProcessor
from app.modules.document_parser.table_extractor import TableExtractor
from app.modules.quality_scorer.quality_report import QualityScorer
from typing import Optional
from app.modules.risk_predictor.risk_analyzer import RiskAnalyzer

router = APIRouter(prefix="/api/risk", tags=["Risk Prediction"])

pdf_extractor = PDFExtractor()
nlp_processor = NLPProcessor()
table_extractor = TableExtractor()
quality_scorer = QualityScorer()
risk_analyzer = RiskAnalyzer()


@router.post("/predict")
async def predict_risk(
    file_path: str,
    document_id: int = Query(None, description="Document ID from upload"),
    state: Optional[str] = Query(None, description="Indian state name"),
    project_type: Optional[str] = Query(None, description="Project type"),
    project_cost_crores: Optional[str] = Query(None, description="Estimated cost in crores"),
    db: AsyncSession = Depends(get_db),
):
    """
    Predict project risks from DPR analysis.
    Results are persisted in PostgreSQL.
    """
    # Normalise optional params (frontend may send empty strings)
    state = state.strip() if state else None
    project_type = project_type.strip() if project_type else None
    cost_value: Optional[float] = None
    if project_cost_crores and project_cost_crores.strip():
        try:
            cost_value = float(project_cost_crores)
        except ValueError:
            cost_value = None

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

        # Quality Score (for features)
        quality_report = quality_scorer.score_dpr(
            nlp_analysis=nlp_analysis,
            table_analysis=table_analysis,
            state=state,
            project_type=project_type
        )

        # Compliance Report (for features)
        compliance_report = quality_scorer.compliance_engine.validate_compliance(
            nlp_analysis, state=state, project_type=project_type
        )

        # Risk Analysis
        risk_report = risk_analyzer.analyze_risk(
            nlp_analysis=nlp_analysis,
            quality_score=quality_report,
            compliance_report=compliance_report,
            state=state,
            project_type=project_type,
            project_cost=cost_value
        )

        # Persist to PostgreSQL
        if document_id:
            doc = await db_service.get_document(db, document_id)
            if doc:
                await db_service.save_risk_assessment(db, document_id, risk_report)

        duration_ms = (time.time() - t0) * 1000
        await db_service.log_action(
            db, action="risk_predict", document_id=document_id, state=state,
            details={"risk_level": risk_report.get("risk_summary", {}).get("overall_risk_level")},
            duration_ms=duration_ms,
        )

        return {
            "document_id": document_id,
            "file_name": extraction.get("file_name"),
            "risk_report": risk_report,
            "persisted": document_id is not None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/full-analysis")
async def full_dpr_analysis(
    file_path: str,
    document_id: int = Query(None, description="Document ID from upload"),
    state: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    project_cost_crores: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Run complete end-to-end DPR analysis.
    All phases are persisted in PostgreSQL.
    """
    # Normalise optional params
    state = state.strip() if state else None
    project_type = project_type.strip() if project_type else None
    cost_value: Optional[float] = None
    if project_cost_crores and project_cost_crores.strip():
        try:
            cost_value = float(project_cost_crores)
        except ValueError:
            cost_value = None

    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise HTTPException(status_code=404, detail="File not found")

    t0 = time.time()

    try:
        # Phase 1: Document Intelligence
        logger.info("Phase 1: Document extraction...")
        if file_path_obj.suffix.lower() == ".pdf":
            extraction = pdf_extractor.extract_text(file_path)
        elif file_path_obj.suffix.lower() in [".docx", ".doc"]:
            extraction = pdf_extractor.extract_from_docx(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

        full_text = extraction.get("full_text", "")
        if not full_text or len(full_text.strip()) < 50:
            raise HTTPException(status_code=422, detail="Insufficient text content")

        # Phase 1b: NLP Analysis
        logger.info("Phase 1b: NLP analysis...")
        nlp_analysis = nlp_processor.analyze_document(full_text)

        # Phase 1c: Table Analysis
        tables = extraction.get("tables", [])
        table_analysis = table_extractor.extract_tables_from_text(tables) if tables else {}

        # Phase 2: Quality Scoring
        logger.info("Phase 2: Quality scoring...")
        quality_report = quality_scorer.score_dpr(
            nlp_analysis=nlp_analysis,
            table_analysis=table_analysis,
            state=state,
            project_type=project_type
        )

        # Phase 3: Compliance Check
        logger.info("Phase 3: Compliance validation...")
        compliance_report = quality_scorer.compliance_engine.validate_compliance(
            nlp_analysis, state=state, project_type=project_type
        )

        # Phase 4: Risk Prediction
        logger.info("Phase 4: Risk prediction...")
        risk_report = risk_analyzer.analyze_risk(
            nlp_analysis=nlp_analysis,
            quality_score=quality_report,
            compliance_report=compliance_report,
            state=state,
            project_type=project_type,
            project_cost=cost_value
        )

        verdict = _generate_verdict(quality_report, compliance_report, risk_report)

        # ── Persist everything to PostgreSQL ──
        if document_id:
            doc = await db_service.get_document(db, document_id)
            if doc:
                await db_service.save_analysis(
                    db, document_id,
                    nlp_result=nlp_analysis,
                    table_analysis=table_analysis,
                )
                await db_service.save_quality_score(db, document_id, quality_report)
                await db_service.save_risk_assessment(
                    db, document_id, risk_report, verdict=verdict,
                )

        # Check MDoNER status from DB
        is_mdoner = False
        if state:
            db_state = await db_service.get_state_by_name(db, state)
            if db_state:
                is_mdoner = db_state.is_mdoner

        duration_ms = (time.time() - t0) * 1000
        await db_service.log_action(
            db, action="full_analysis", document_id=document_id, state=state,
            details={"verdict": verdict.get("verdict")}, duration_ms=duration_ms,
        )

        comprehensive_report = {
            "document_id": document_id,
            "document_info": {
                "file_name": extraction.get("file_name"),
                "total_pages": extraction.get("total_pages", 0),
                "total_words": nlp_analysis.get("text_statistics", {}).get("total_words", 0),
                "state": state,
                "project_type": project_type,
                "project_cost_crores": cost_value,
                "is_mdoner_state": is_mdoner,
            },
            "nlp_analysis_summary": nlp_analysis.get("summary", {}),
            "table_analysis_summary": table_analysis.get("summary", {}) if isinstance(table_analysis, dict) else {},
            "quality_report": quality_report,
            "compliance_report": compliance_report,
            "risk_report": risk_report,
            "overall_verdict": verdict,
            "persisted": document_id is not None,
        }

        logger.info("Full analysis complete!")
        return comprehensive_report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _generate_verdict(quality_report: dict, compliance_report: dict, risk_report: dict) -> dict:
    """Generate overall DPR verdict."""
    quality_score = quality_report.get("composite_score", 0)
    compliance_score = compliance_report.get("overall_compliance_score", 0)
    risk_level = risk_report.get("risk_summary", {}).get("overall_risk_level", "Unknown")
    cost_risk = risk_report.get("risk_summary", {}).get("cost_overrun_probability", 0)

    if quality_score >= 75 and compliance_score >= 70 and risk_level in ["Low", "Medium"]:
        verdict = "RECOMMENDED FOR APPROVAL"
        verdict_icon = "✅"
        action = "DPR meets quality and compliance standards with acceptable risk levels."
    elif quality_score >= 60 and compliance_score >= 50:
        verdict = "CONDITIONAL APPROVAL - IMPROVEMENTS NEEDED"
        verdict_icon = "⚠️"
        action = "DPR needs improvements before final approval. Address highlighted recommendations."
    elif quality_score >= 40:
        verdict = "MAJOR REVISION REQUIRED"
        verdict_icon = "🔶"
        action = "DPR has significant gaps. Return for major revision with specific feedback."
    else:
        verdict = "NOT RECOMMENDED - REWORK NEEDED"
        verdict_icon = "❌"
        action = "DPR fails to meet minimum standards. Complete rework recommended."

    return {
        "verdict": verdict,
        "verdict_icon": verdict_icon,
        "action": action,
        "quality_score": quality_score,
        "compliance_score": compliance_score,
        "risk_level": risk_level,
        "cost_overrun_risk": cost_risk
    }

