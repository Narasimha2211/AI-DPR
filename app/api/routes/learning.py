# ============================================
# Learning API Routes – Incremental ML Training
# The system learns from every DPR uploaded
# ============================================

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Header, Depends
from loguru import logger
from sqlalchemy.orm import Session

from config.settings import settings as app_settings
from config.postgres_config import get_db
from app.api.dependencies import get_current_admin_user

from app.services import postgres_db_service as db_service
from app.services.learning_service import (
    retrain_models,
    get_model_files_info,
)

router = APIRouter(prefix="/api/learning", tags=["Model Learning"])


@router.get("/status")
async def get_learning_status(db: Session = Depends(get_db)):
    """
    Get the current model learning status:
    - How many DPRs the model has learned from
    - Model version history with accuracy metrics
    - Whether retraining is recommended
    """
    # Training data stats
    td_counts = db_service.get_training_data_count(db)

    # Model versions
    versions = db_service.get_model_versions(db, limit=10)
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
            "trained_at": v.trained_at.isoformat() if hasattr(v.trained_at, 'isoformat') else str(v.trained_at) if v.trained_at else None,
        })

    # Latest model info
    latest = db_service.get_latest_model_version(db)
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
async def trigger_retrain(db: Session = Depends(get_db), current_user: dict = Depends(get_current_admin_user)):
    """
    Trigger model retraining using all accumulated training data.
    Combines real DPR data (weighted higher) with synthetic augmentation.
    The more DPRs you upload, the smarter the model gets.
    """
    # Get all training data
    all_td = db_service.get_all_training_data(db)

    training_rows = []
    for td in all_td:
        training_rows.append({
            "features": td.features or {},
            "labels": td.labels or {},
            "is_user_corrected": td.is_user_corrected if hasattr(td, 'is_user_corrected') else False,
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
    mv = db_service.save_model_version(db, report)

    # Reload models in the risk analyzer
    try:
        from app.api.routes.risk import risk_analyzer
        risk_analyzer.ml_models.load_models()
        logger.info("✅ Models reloaded into risk analyzer")
    except Exception as e:
        logger.warning(f"Model reload warning: {e}")

    db_service.log_action(
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
    db: Session = Depends(get_db),
):
    """
    Submit feedback on model predictions for a DPR.
    This creates ground-truth labels that improve future predictions.
    The more feedback you provide, the better the model gets.
    """
    doc = db_service.get_document(db, document_id)
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
    updated = db_service.update_training_labels(db, document_id, corrected_labels)

    # Also save as user feedback
    db_service.create_feedback(
        db,
        document_id=document_id,
        feedback_type="prediction_correction",
        is_accurate=is_accurate,
        user_comment=comment,
        corrected_risk_level=actual_risk_level,
        corrected_score=actual_quality_score,
        corrected_data=corrected_labels,
    )

    db_service.log_action(
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
    db: Session = Depends(get_db),
):
    """Get the full model training history showing improvement over time."""
    versions = db_service.get_model_versions(db, limit=limit)

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


@router.post("/backfill-training-data")
async def backfill_training_data(
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin_user),
):
    """
    Backfill training data for existing documents that were analyzed 
    before the save_training_data() function was added.
    """
    from app.services.learning_service import extract_training_sample
    from sqlalchemy import text
    
    try:
        # Query for document IDs with analysis but no training data
        query = text("""
            SELECT d.id FROM dpr_documents d
            JOIN dpr_analyses a ON d.id = a.document_id
            WHERE d.id NOT IN (SELECT COALESCE(document_id, 0) FROM training_data)
            GROUP BY d.id
        """)
        result = db.execute(query)
        doc_ids = [row[0] for row in result]
        
        backfilled_count = 0
        errors = []
        
        for doc_id in doc_ids:
            try:
                # Query analysis data with all columns available
                analysis_query = text("""
                    SELECT * FROM dpr_analyses WHERE document_id = :doc_id
                """)
                analysis_row_dict = db.execute(analysis_query, {"doc_id": doc_id}).mappings().first()
                
                if not analysis_row_dict:
                    continue
                
                # Query quality score
                quality_query = text("""
                    SELECT composite_score, grade, compliance_level FROM quality_scores 
                    WHERE document_id = :doc_id
                """)
                quality_row = db.execute(quality_query, {"doc_id": doc_id}).first()
                
                # Query risk assessment
                risk_query = text("""
                    SELECT overall_risk_level, cost_overrun_probability, delay_probability
                    FROM risk_assessments WHERE document_id = :doc_id
                """)
                risk_row = db.execute(risk_query, {"doc_id": doc_id}).first()
                
                # Build quality and risk dicts from query results
                quality_dict = None
                if quality_row:
                    quality_dict = {
                        "composite_score": quality_row[0] or 0,
                        "grade": quality_row[1] or 'F',
                        "compliance_level": quality_row[2] or 'LOW'
                    }
                
                risk_dict = None
                if risk_row:
                    risk_dict = {
                        "risk_summary": {
                            "overall_risk_level": risk_row[0] or 'Medium',
                            "cost_overrun_probability": risk_row[1] or 50,
                            "delay_probability": risk_row[2] or 50
                        }
                    }
                
                # analysis_row_dict already contains full_nlp_result - use it as is
                nlp_analysis = analysis_row_dict.get('full_nlp_result') or {}
                
                # Extract training sample using dict parameters
                training_sample = extract_training_sample(
                    nlp_analysis=nlp_analysis,
                    quality_report=quality_dict,
                    risk_report=risk_dict
                )
                
                if training_sample:
                    # Save to training data
                    db_service.save_training_data(
                        db=db,
                        document_id=doc_id,
                        features=training_sample.get("features", {}),
                        labels=training_sample.get("labels", {}),
                        metadata_info={"source": "backfill_migration"},
                        is_user_corrected=False
                    )
                    backfilled_count += 1
                    logger.info(f"✅ Backfilled training data for document {doc_id}")
                        
            except Exception as e:
                error_msg = f"Failed to backfill document {doc_id}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            "success": True,
            "backfilled_count": backfilled_count,
            "total_docs_processed": len(doc_ids),
            "errors": errors if errors else None,
            "message": f"✅ Successfully backfilled training data for {backfilled_count} document(s)"
        }
        
    except Exception as e:
        logger.error(f"Backfill failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Backfill operation failed: {str(e)}"
        )


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
