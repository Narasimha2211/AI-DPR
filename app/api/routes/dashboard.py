# ============================================
# Dashboard API Routes – PostgreSQL backed
# Analytics & Statistics
# ============================================

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from config.settings import settings
from app.models.database import get_db
from app.services import db_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get overall dashboard statistics from PostgreSQL."""
    live_stats = await db_service.get_dashboard_stats(db)

    all_states = await db_service.get_all_states(db)
    mdoner = await db_service.get_mdoner_states(db)
    sections = await db_service.get_all_sections(db)
    weights = await db_service.get_scoring_weights(db)

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
async def get_state_info(state: str, db: AsyncSession = Depends(get_db)):
    """Get information about a specific state from PostgreSQL."""
    db_state = await db_service.get_state_by_name(db, state)
    if not db_state:
        all_states = await db_service.get_all_states(db)
        return {
            "error": f"State '{state}' not found",
            "supported": [s.name for s in all_states],
        }

    sections = await db_service.get_all_sections(db)

    state_info = {
        "state": db_state.name,
        "code": db_state.code,
        "is_mdoner_state": db_state.is_mdoner,
        "region": db_state.region,
        "terrain": db_state.terrain,
        "risk_factor": db_state.risk_factor,
        "dpr_requirements": [s.name for s in sections],
    }

    if bool(db_state.is_mdoner):
        state_info["mdoner_special_provisions"] = db_state.special_provisions or [
            "90:10 Central-State funding pattern",
            "Special Category State provisions",
            "Border Area Development Programme eligibility",
            "Flood/Landslide vulnerability assessment",
            "Tribal community impact assessment",
        ]
        state_info["priority_sectors"] = db_state.priority_sectors or []
        state_info["additional_requirements"] = db_state.additional_requirements or []

    return state_info


@router.get("/grading-system")
async def get_grading_system(db: AsyncSession = Depends(get_db)):
    """Get the DPR quality grading system from PostgreSQL."""
    grades = await db_service.get_grade_definitions(db)
    weights = await db_service.get_scoring_weights(db)

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
    db: AsyncSession = Depends(get_db),
):
    """
    Submit user feedback on analysis results.
    Used for future quality improvement & ML retraining.
    """
    doc = await db_service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    fb = await db_service.create_feedback(
        db,
        document_id=document_id,
        feedback_type=feedback_type,
        rating=rating,
        is_accurate=is_accurate,
        user_comment=user_comment,
        corrected_score=corrected_score,
        corrected_risk_level=corrected_risk_level,
    )

    await db_service.log_action(
        db, action="feedback", document_id=document_id,
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
    db: AsyncSession = Depends(get_db),
):
    """List feedback records for quality improvement."""
    if document_id:
        rows = await db_service.get_feedback_for_document(db, document_id)
    else:
        rows = await db_service.get_all_feedback(db, feedback_type=feedback_type, limit=limit)

    return {
        "feedback": [
            {
                "id": f.id,
                "document_id": f.document_id,
                "type": f.feedback_type,
                "rating": f.rating,
                "is_accurate": f.is_accurate,
                "comment": f.user_comment,
                "created_at": f.created_at.isoformat() if f.created_at is not None else None,
            }
            for f in rows
        ],
        "count": len(rows),
    }
