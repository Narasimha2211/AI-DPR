# ============================================
# Dashboard API Routes – PostgreSQL backed
# Analytics & Statistics
# ============================================

from fastapi import APIRouter, Query, HTTPException, Depends
from loguru import logger
from sqlalchemy.orm import Session

from config.settings import settings
from config.postgres_config import get_db
from app.services import postgres_db_service as db_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get overall dashboard statistics."""
    live_stats = db_service.get_dashboard_stats(db)

    all_states = db_service.get_all_states(db)
    mdoner = db_service.get_mdoner_states(db)
    sections = db_service.get_all_sections(db)
    weights = db_service.get_scoring_weights(db)

    return {
        "system_info": {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "supported_states": len(all_states),
            "mdoner_states": len(mdoner),
            "required_dpr_sections": len(sections),
        },
        "live_stats": live_stats,
        "supported_states": [s.name for s in all_states],
        "mdoner_states": [s.name for s in mdoner],
        "dpr_sections": [s.name for s in sections],
        "scoring_weights": {w.criterion: w.weight for w in weights},
    }


@router.get("/states/{state}")
async def get_state_info(state: str, db: Session = Depends(get_db)):
    """Get information about a specific state."""
    db_state = db_service.get_state_by_name(db, state)
    if not db_state:
        all_states = db_service.get_all_states(db)
        return {
            "error": f"State '{state}' not found",
            "supported": [s.name for s in all_states],
        }

    sections = db_service.get_all_sections(db)

    state_info = {
        "state": db_state.name,
        "code": getattr(db_state, 'code', None),
        "is_mdoner_state": db_state.is_mdoner,
        "region": getattr(db_state, 'region', None),
        "terrain": getattr(db_state, 'terrain', None),
        "risk_factor": getattr(db_state, 'risk_factor', None),
        "dpr_requirements": [s.name for s in sections],
    }

    if bool(db_state.is_mdoner):
        state_info["mdoner_special_provisions"] = getattr(db_state, 'special_provisions', None) or [
            "90:10 Central-State funding pattern",
            "Special Category State provisions",
            "Border Area Development Programme eligibility",
            "Flood/Landslide vulnerability assessment",
            "Tribal community impact assessment",
        ]
        state_info["priority_sectors"] = getattr(db_state, 'priority_sectors', None) or []
        state_info["additional_requirements"] = getattr(db_state, 'additional_requirements', None) or []

    return state_info


@router.get("/grading-system")
async def get_grading_system(db: Session = Depends(get_db)):
    """Get the DPR quality grading system."""
    grades = db_service.get_grade_definitions(db)
    weights = db_service.get_scoring_weights(db)

    return {
        "grades": {
            str(g.grade): {
                "range": f"{int(g.min_score or 0)}-{int(g.max_score or 0)}",
                "description": g.description,
            }
            for g in grades
        },
        "scoring_criteria": {
            f"{w.criterion} ({int((w.weight or 0) * 100)}%)": w.description
            for w in weights
        },
    }


# ─── Feedback endpoints ───

@router.post("/feedback")
async def submit_feedback(
    document_id: int,
    feedback_type: str,
    rating: int = Query(None, ge=1, le=5),
    is_accurate: bool = Query(None),
    user_comment: str = Query(None),
    corrected_score: float = Query(None),
    corrected_risk_level: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Submit user feedback on analysis results.
    Used for future quality improvement & ML retraining.
    """
    doc = db_service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    fb = db_service.create_feedback(
        db,
        document_id=document_id,
        feedback_type=feedback_type,
        rating=rating,
        is_accurate=is_accurate,
        user_comment=user_comment,
        corrected_score=corrected_score,
        corrected_risk_level=corrected_risk_level,
    )

    db_service.log_action(
        db,
        action="feedback", document_id=document_id,
        details={"type": feedback_type, "rating": rating},
    )

    return {
        "feedback_id": fb.id,
        "document_id": document_id,
        "message": "Feedback recorded. Thank you for helping improve the system!",
    }


@router.get("/feedback")
async def list_feedback(
    document_id: int = Query(None),
    feedback_type: str = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List feedback records for quality improvement."""
    if document_id:
        rows = db_service.get_feedback_for_document(db, document_id)
    else:
        rows = db_service.get_all_feedback(db, feedback_type=feedback_type, limit=limit)

    return {
        "feedback": [
            {
                "id": f.id,
                "document_id": f.document_id,
                "type": f.feedback_type,
                "rating": getattr(f, 'rating', None),
                "is_accurate": getattr(f, 'is_accurate', None),
                "comment": getattr(f, 'user_comment', None),
                "created_at": getattr(f, 'created_at', None),
            }
            for f in rows
        ],
        "count": len(rows),
    }
