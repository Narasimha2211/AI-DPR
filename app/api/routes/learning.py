# ============================================
# Learning API Routes – Incremental ML Training
# The system learns from every DPR uploaded
# ============================================

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.database import get_db
from app.services import db_service
from app.services.learning_service import (
    retrain_models,
    get_model_files_info,
)

router = APIRouter(prefix="/api/learning", tags=["Model Learning"])


@router.get("/status")
async def get_learning_status(db: AsyncSession = Depends(get_db)):
    """
    Get the current model learning status:
    - How many DPRs the model has learned from
    - Model version history with accuracy metrics
    - Whether retraining is recommended
    """
    # Training data stats
    td_counts = await db_service.get_training_data_count(db)

    # Model versions
    versions = await db_service.get_model_versions(db, limit=10)
    version_history = []
    for v in versions:
        version_history.append({
            "version": v.version,
            "real_samples": v.real_samples_used,
            "synthetic_samples": v.synthetic_samples_used,
            "total_samples": v.total_samples_used,
            "cost_metrics": v.cost_model_metrics,
            "delay_metrics": v.delay_model_metrics,
            "risk_metrics": v.risk_model_metrics,
            "trained_at": v.trained_at.isoformat() if v.trained_at else None,
        })

    # Latest model info
    latest = await db_service.get_latest_model_version(db)
    model_files = get_model_files_info()

    # Check if retraining is recommended
    last_trained_samples = latest.real_samples_used if latest else 0
    new_samples_since = td_counts["total"] - last_trained_samples
    retrain_recommended = new_samples_since >= 3  # Retrain after 3 new DPRs

    return {
        "training_data": td_counts,
        "current_model_version": latest.version if latest else 0,
        "model_files": model_files["models"],
        "version_history": version_history,
        "new_samples_since_last_train": new_samples_since,
        "retrain_recommended": retrain_recommended,
        "retrain_threshold": 3,
        "learning_summary": _build_learning_summary(td_counts, latest, new_samples_since),
    }


@router.post("/retrain")
async def trigger_retrain(db: AsyncSession = Depends(get_db)):
    """
    Trigger model retraining using all accumulated training data.
    Combines real DPR data (weighted higher) with synthetic augmentation.
    The more DPRs you upload, the smarter the model gets.
    """
    # Get all training data
    all_td = await db_service.get_all_training_data(db)

    training_rows = []
    for td in all_td:
        training_rows.append({
            "features": td.features or {},
            "labels": td.labels or {},
            "is_user_corrected": td.is_user_corrected,
        })

    logger.info(f"🧠 Retraining with {len(training_rows)} real samples...")

    try:
        # Run training (CPU-intensive, run in thread pool)
        report = await asyncio.to_thread(retrain_models, training_rows)
    except Exception as e:
        logger.error(f"Retraining failed: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

    # Save model version to DB
    report["real_samples"] = len(training_rows)
    mv = await db_service.save_model_version(db, report)

    # Reload models in the risk analyzer
    try:
        from app.api.routes.risk import risk_analyzer
        risk_analyzer.ml_models.load_models()
        logger.info("✅ Models reloaded into risk analyzer")
    except Exception as e:
        logger.warning(f"Model reload warning: {e}")

    await db_service.log_action(
        db,
        action="model_retrain",
        details={
            "version": mv.version,
            "real_samples": len(training_rows),
            "models": report.get("models", {}),
        },
    )

    return {
        "success": True,
        "model_version": mv.version,
        "real_samples_used": len(training_rows),
        "training_report": report,
        "message": f"Models retrained successfully (v{mv.version}) with {len(training_rows)} real DPR samples!",
    }


@router.post("/feedback")
async def submit_feedback(
    document_id: int,
    actual_cost_overrun: Optional[float] = Query(None, description="Actual cost overrun % (0-100)"),
    actual_delay_months: Optional[float] = Query(None, description="Actual delay in months"),
    actual_risk_level: Optional[str] = Query(None, description="Actual risk: Low/Medium/High/Critical"),
    actual_quality_score: Optional[float] = Query(None, description="Corrected quality score (0-100)"),
    is_accurate: Optional[bool] = Query(None, description="Was the prediction accurate?"),
    comment: Optional[str] = Query(None, description="Optional comment"),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit feedback on model predictions for a DPR.
    This creates ground-truth labels that improve future predictions.
    The more feedback you provide, the better the model gets.
    """
    doc = await db_service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Build corrected labels
    corrected_labels = {}
    if actual_cost_overrun is not None:
        corrected_labels["cost_overrun_probability"] = actual_cost_overrun
    if actual_delay_months is not None:
        # Convert delay months to probability-like score (0-100)
        delay_prob = min(100, actual_delay_months / 36 * 100)
        corrected_labels["delay_probability"] = delay_prob
    if actual_risk_level:
        risk_map = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
        if actual_risk_level in risk_map:
            corrected_labels["risk_class"] = risk_map[actual_risk_level]
    if actual_quality_score is not None:
        corrected_labels["quality_score"] = actual_quality_score

    # Update training data labels
    updated = await db_service.update_training_labels(db, document_id, corrected_labels)

    # Also save as user feedback
    await db_service.create_feedback(
        db,
        document_id=document_id,
        feedback_type="prediction_correction",
        is_accurate=is_accurate,
        user_comment=comment,
        corrected_risk_level=actual_risk_level,
        corrected_score=actual_quality_score,
        corrected_data=corrected_labels,
    )

    await db_service.log_action(
        db,
        action="learning_feedback",
        document_id=document_id,
        details={"corrected_labels": corrected_labels, "is_accurate": is_accurate},
    )

    return {
        "success": True,
        "document_id": document_id,
        "labels_updated": bool(updated),
        "corrected_fields": list(corrected_labels.keys()),
        "message": "Thank you! Your feedback will improve future predictions.",
    }


@router.get("/history")
async def get_training_history(
    limit: int = Query(20, description="Number of versions to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get the full model training history showing improvement over time."""
    versions = await db_service.get_model_versions(db, limit=limit)

    history = []
    for v in versions:
        entry = {
            "version": v.version,
            "trained_at": v.trained_at.isoformat() if v.trained_at else None,
            "real_samples": v.real_samples_used,
            "total_samples": v.total_samples_used,
        }
        # Extract key accuracy metrics
        if v.cost_model_metrics:
            entry["cost_r2"] = v.cost_model_metrics.get("r2", 0)
            entry["cost_mae"] = v.cost_model_metrics.get("mae", 0)
        if v.delay_model_metrics:
            entry["delay_r2"] = v.delay_model_metrics.get("r2", 0)
            entry["delay_mae"] = v.delay_model_metrics.get("mae", 0)
        if v.risk_model_metrics:
            entry["risk_accuracy"] = v.risk_model_metrics.get("accuracy", 0)
            entry["risk_f1"] = v.risk_model_metrics.get("f1_weighted", 0)
        history.append(entry)

    return {"history": history, "total_versions": len(history)}


def _build_learning_summary(td_counts: dict, latest_version, new_samples: int) -> str:
    """Build a human-readable learning summary."""
    total = td_counts["total"]
    corrected = td_counts["user_corrected"]

    if total == 0:
        return (
            "🆕 No DPRs analyzed yet. Upload your first DPR to start teaching the AI! "
            "The model currently uses heuristic rules and will switch to ML predictions "
            "once trained."
        )

    version_str = f"v{latest_version.version}" if latest_version else "v0 (untrained)"
    parts = [f"📊 The AI has learned from {total} DPR(s)."]

    if corrected:
        parts.append(f"✅ {corrected} have user-verified labels (ground truth).")

    if latest_version:
        metrics = latest_version.cost_model_metrics or {}
        r2 = metrics.get("r2", 0)
        parts.append(f"🎯 Current model ({version_str}) — Cost prediction R²: {r2:.3f}")
    else:
        parts.append("⚠️ Models not yet trained. Click 'Retrain' to build your first ML model!")

    if new_samples >= 3:
        parts.append(f"🔄 {new_samples} new samples available — retraining recommended!")

    return " ".join(parts)
