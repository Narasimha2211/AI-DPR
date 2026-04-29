# ============================================
# Analysis Detail API – Get document analysis results
# ============================================

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from loguru import logger

from config.postgres_config import get_db
from app.services import postgres_db_service as db_service
from app.api.dependencies import get_current_user
from app.models.postgres_models import DPRDocument, DPRAnalysis, QualityScore, RiskAssessment

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.get("/detail/{document_id}")
async def get_analysis_detail(
    document_id: int = Path(..., description="Document ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed analysis results for a document from PostgreSQL."""
    try:
        # Get document
        doc = db.query(DPRDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        
        # Get analysis results
        analysis = db.query(DPRAnalysis).filter_by(document_id=document_id).first()
        quality = db.query(QualityScore).filter_by(document_id=document_id).first()
        risk = db.query(RiskAssessment).filter_by(document_id=document_id).first()
        
        return {
            "document": {
                "id": doc.id,
                "filename": doc.filename,
                "state": doc.state_name,
                "project_type": doc.project_type,
                "status": doc.processing_status,
                "upload_date": str(doc.upload_date) if doc.upload_date is not None else None,
            },
            "analysis": {
                "sections_found": analysis.sections_found if analysis else 0,
                "sections_total": analysis.sections_total if analysis else 14,
                "word_count": analysis.word_count if analysis else 0,
                "char_count": analysis.char_count if analysis else 0,
                "organizations_count": analysis.organizations_count if analysis else 0,
                "locations_count": analysis.locations_count if analysis else 0,
                "dates_count": analysis.dates_count if analysis else 0,
                "total_cost_extracted": analysis.total_cost_extracted if analysis else 0,
            } if analysis else {},
            "quality": {
                "grade": quality.grade if quality else "-",
                "composite_score": quality.composite_score if quality else 0,
                "compliance_level": quality.compliance_level if quality else "",
            } if quality else {},
            "risk": {
                "overall_risk_level": risk.overall_risk_level if risk else "Unknown",
                "cost_overrun_probability": risk.cost_overrun_probability if risk else 0,
                "delay_probability": risk.delay_probability if risk else 0,
            } if risk else {},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis for doc {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
