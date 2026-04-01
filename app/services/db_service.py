# ============================================
# Database CRUD Service Layer
# All persistent operations go through here
# ============================================

import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import (
    State, DPRSectionDef, ComplianceRule, ScoringWeight, GradeDefinition,
    DPRDocument, DPRAnalysis, QualityScore, RiskAssessment,
    UserFeedback, AnalyticsLog, TrainingData, ModelVersion,
)


# ─── Reference / Config Queries ───

async def get_all_states(db: AsyncSession) -> List[State]:
    result = await db.execute(select(State).order_by(State.name))
    return list(result.scalars().all())


async def get_mdoner_states(db: AsyncSession) -> List[State]:
    result = await db.execute(
        select(State).where(State.is_mdoner == True).order_by(State.name)
    )
    return list(result.scalars().all())


async def get_state_by_name(db: AsyncSession, name: str) -> Optional[State]:
    result = await db.execute(select(State).where(State.name == name))
    return result.scalar_one_or_none()


async def get_all_sections(db: AsyncSession) -> List[DPRSectionDef]:
    result = await db.execute(
        select(DPRSectionDef).order_by(DPRSectionDef.order_index)
    )
    return list(result.scalars().all())


async def get_scoring_weights(db: AsyncSession) -> List[ScoringWeight]:
    result = await db.execute(
        select(ScoringWeight).where(ScoringWeight.is_active == True)
    )
    return list(result.scalars().all())


async def get_grade_definitions(db: AsyncSession) -> List[GradeDefinition]:
    result = await db.execute(
        select(GradeDefinition).where(GradeDefinition.is_active == True)
        .order_by(desc(GradeDefinition.min_score))
    )
    return list(result.scalars().all())


async def get_compliance_rules(
    db: AsyncSession, category: Optional[str] = None
) -> List[ComplianceRule]:
    q = select(ComplianceRule).where(ComplianceRule.is_active == True)
    if category:
        q = q.where(ComplianceRule.category == category)
    result = await db.execute(q)
    return list(result.scalars().all())


# ─── Document CRUD ───

async def create_document(
    db: AsyncSession,
    *,
    file_name: str,
    file_path: str,
    file_size_kb: float,
    file_format: str,
    state_name: Optional[str] = None,
    project_type: Optional[str] = None,
    project_name: Optional[str] = None,
    project_cost_crores: Optional[float] = None,
    total_pages: Optional[int] = None,
    total_words: Optional[int] = None,
) -> DPRDocument:
    state_id = None
    if state_name:
        state = await get_state_by_name(db, state_name)
        if state:
            state_id = state.id

    doc = DPRDocument(
        file_name=file_name,
        file_path=file_path,
        file_size_kb=file_size_kb,
        file_format=file_format,
        state_id=state_id,
        state_name=state_name,
        project_type=project_type,
        project_name=project_name,
        project_cost_crores=project_cost_crores,
        total_pages=total_pages,
        total_words=total_words,
        processing_status="uploaded",
    )
    db.add(doc)
    await db.flush()
    return doc


async def get_document(db: AsyncSession, document_id: int) -> Optional[DPRDocument]:
    result = await db.execute(
        select(DPRDocument).where(DPRDocument.id == document_id)
    )
    return result.scalar_one_or_none()


async def get_document_with_relations(db: AsyncSession, document_id: int) -> Optional[DPRDocument]:
    result = await db.execute(
        select(DPRDocument)
        .where(DPRDocument.id == document_id)
        .options(
            selectinload(DPRDocument.analysis),
            selectinload(DPRDocument.quality_score),
            selectinload(DPRDocument.risk_assessment),
        )
    )
    return result.scalar_one_or_none()


async def update_document_status(
    db: AsyncSession, document_id: int, status: str
):
    await db.execute(
        update(DPRDocument)
        .where(DPRDocument.id == document_id)
        .values(processing_status=status, processed=(status == "completed"))
    )
    await db.flush()


async def list_documents(
    db: AsyncSession,
    *,
    state_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[DPRDocument]:
    q = select(DPRDocument).order_by(desc(DPRDocument.upload_date))
    if state_name:
        q = q.where(DPRDocument.state_name == state_name)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


# ─── Analysis CRUD ───

async def save_analysis(
    db: AsyncSession,
    document_id: int,
    nlp_result: dict,
    table_analysis: Optional[dict] = None,
    extraction_meta: Optional[dict] = None,
) -> DPRAnalysis:
    summary = nlp_result.get("summary", {})
    entities = nlp_result.get("entities", {})
    fields = dict(
        sections_found=summary.get("sections_found", 0),
        sections_total=summary.get("sections_total", 14),
        sections_data=nlp_result.get("sections", {}),
        entities_data=entities,
        organizations_count=len(entities.get("organizations", [])),
        locations_count=len(entities.get("locations", [])),
        dates_count=len(entities.get("dates", [])),
        financial_figures=nlp_result.get("financial_figures", []),
        total_cost_extracted=sum(
            f.get("value_in_crores", 0)
            for f in nlp_result.get("financial_figures", [])
        ),
        text_statistics=nlp_result.get("text_statistics", {}),
        key_phrases=nlp_result.get("key_phrases", []),
        table_analysis=table_analysis,
        full_nlp_result=nlp_result,
        analysis_date=datetime.datetime.utcnow(),
    )
    # Upsert: update existing record or create new one
    result = await db.execute(
        select(DPRAnalysis).where(DPRAnalysis.document_id == document_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis:
        for k, v in fields.items():
            setattr(analysis, k, v)
    else:
        analysis = DPRAnalysis(document_id=document_id, **fields)
        db.add(analysis)
    await db.flush()
    await update_document_status(db, document_id, "analyzed")
    return analysis


# ─── Quality Score CRUD ───

async def save_quality_score(
    db: AsyncSession,
    document_id: int,
    report: dict,
) -> QualityScore:
    fields = dict(
        composite_score=report.get("composite_score", 0),
        grade=report.get("grade", "F"),
        grade_description=report.get("grade_description", ""),
        section_completeness_score=report.get("individual_scores", {}).get("section_completeness", 0),
        technical_depth_score=report.get("individual_scores", {}).get("technical_depth", 0),
        financial_accuracy_score=report.get("individual_scores", {}).get("financial_accuracy", 0),
        compliance_score=report.get("individual_scores", {}).get("compliance", 0),
        risk_assessment_quality_score=report.get("individual_scores", {}).get("risk_assessment", 0),
        compliance_level=report.get("compliance_level", ""),
        compliance_status=report.get("compliance_status", ""),
        violations=report.get("violations", []),
        warnings=report.get("warnings", []),
        recommendations=report.get("recommendations", []),
        full_report=report,
        scored_date=datetime.datetime.utcnow(),
    )
    # Upsert: update existing record or create new one
    result = await db.execute(
        select(QualityScore).where(QualityScore.document_id == document_id)
    )
    qs = result.scalar_one_or_none()
    if qs:
        for k, v in fields.items():
            setattr(qs, k, v)
    else:
        qs = QualityScore(document_id=document_id, **fields)
        db.add(qs)
    await db.flush()
    await update_document_status(db, document_id, "scored")
    return qs


# ─── Risk Assessment CRUD ───

async def save_risk_assessment(
    db: AsyncSession,
    document_id: int,
    risk_report: dict,
    verdict: Optional[dict] = None,
) -> RiskAssessment:
    risk_summary = risk_report.get("risk_summary", {})
    fields = dict(
        overall_risk_level=risk_summary.get("overall_risk_level", "Unknown"),
        cost_overrun_probability=risk_summary.get("cost_overrun_probability", 0),
        delay_probability=risk_summary.get("delay_probability", 0),
        model_confidence=risk_summary.get("model_confidence", 0),
        cost_prediction=risk_report.get("cost_prediction", {}),
        delay_prediction=risk_report.get("delay_prediction", {}),
        risk_classification=risk_report.get("risk_classification", {}),
        monte_carlo_results=risk_report.get("monte_carlo_simulation", {}),
        explanation=risk_report.get("explainability", {}),
        top_risk_drivers=risk_report.get("risk_summary", {}).get("top_risk_drivers", []),
        mitigation_strategies=risk_report.get("mitigation_strategies", []),
        verdict=verdict,
        full_report=risk_report,
        assessed_date=datetime.datetime.utcnow(),
    )
    # Upsert: update existing record or create new one
    result = await db.execute(
        select(RiskAssessment).where(RiskAssessment.document_id == document_id)
    )
    ra = result.scalar_one_or_none()
    if ra:
        for k, v in fields.items():
            setattr(ra, k, v)
    else:
        ra = RiskAssessment(document_id=document_id, **fields)
        db.add(ra)
    await db.flush()
    await update_document_status(db, document_id, "completed")
    return ra


# ─── User Feedback CRUD ───

async def create_feedback(
    db: AsyncSession,
    *,
    document_id: int,
    feedback_type: str,
    rating: Optional[int] = None,
    is_accurate: Optional[bool] = None,
    user_comment: Optional[str] = None,
    corrected_score: Optional[float] = None,
    corrected_risk_level: Optional[str] = None,
    corrected_data: Optional[dict] = None,
) -> UserFeedback:
    fb = UserFeedback(
        document_id=document_id,
        feedback_type=feedback_type,
        rating=rating,
        is_accurate=is_accurate,
        user_comment=user_comment,
        corrected_score=corrected_score,
        corrected_risk_level=corrected_risk_level,
        corrected_data=corrected_data,
    )
    db.add(fb)
    await db.flush()
    return fb


async def get_feedback_for_document(
    db: AsyncSession, document_id: int
) -> List[UserFeedback]:
    result = await db.execute(
        select(UserFeedback)
        .where(UserFeedback.document_id == document_id)
        .order_by(desc(UserFeedback.created_at))
    )
    return list(result.scalars().all())


async def get_all_feedback(
    db: AsyncSession, feedback_type: Optional[str] = None, limit: int = 100
) -> List[UserFeedback]:
    q = select(UserFeedback).order_by(desc(UserFeedback.created_at)).limit(limit)
    if feedback_type:
        q = q.where(UserFeedback.feedback_type == feedback_type)
    result = await db.execute(q)
    return list(result.scalars().all())


# ─── Analytics Log ───

async def log_action(
    db: AsyncSession,
    action: str,
    document_id: Optional[int] = None,
    state: Optional[str] = None,
    details: Optional[dict] = None,
    duration_ms: Optional[float] = None,
):
    entry = AnalyticsLog(
        action=action,
        document_id=document_id,
        state=state,
        details=details,
        duration_ms=duration_ms,
    )
    db.add(entry)
    await db.flush()


# ─── Dashboard Aggregations ───

async def get_dashboard_stats(db: AsyncSession) -> dict:
    """Aggregate statistics for the dashboard."""
    total_docs = (await db.execute(select(func.count(DPRDocument.id)))).scalar() or 0
    analyzed_docs = (await db.execute(
        select(func.count(DPRDocument.id)).where(DPRDocument.processed == True)
    )).scalar() or 0
    avg_quality = (await db.execute(
        select(func.avg(QualityScore.composite_score))
    )).scalar()

    # Risk distribution
    risk_rows = (await db.execute(
        select(
            RiskAssessment.overall_risk_level,
            func.count(RiskAssessment.id)
        ).group_by(RiskAssessment.overall_risk_level)
    )).all()
    risk_distribution = {row[0]: row[1] for row in risk_rows}

    # Grade distribution
    grade_rows = (await db.execute(
        select(QualityScore.grade, func.count(QualityScore.id))
        .group_by(QualityScore.grade)
    )).all()
    grade_distribution = {row[0]: row[1] for row in grade_rows}

    # Top states by document count
    state_rows = (await db.execute(
        select(DPRDocument.state_name, func.count(DPRDocument.id))
        .where(DPRDocument.state_name.isnot(None))
        .group_by(DPRDocument.state_name)
        .order_by(desc(func.count(DPRDocument.id)))
        .limit(10)
    )).all()
    top_states = {row[0]: row[1] for row in state_rows}

    # Recent documents
    recent_result = await db.execute(
        select(DPRDocument)
        .order_by(desc(DPRDocument.upload_date))
        .limit(10)
    )
    recent_docs = recent_result.scalars().all()

    # Feedback count
    feedback_count = (await db.execute(
        select(func.count(UserFeedback.id))
    )).scalar() or 0

    return {
        "total_documents": total_docs,
        "analyzed_documents": analyzed_docs,
        "pending_documents": total_docs - analyzed_docs,
        "average_quality_score": round(avg_quality, 2) if avg_quality else 0,
        "risk_distribution": risk_distribution,
        "grade_distribution": grade_distribution,
        "top_states": top_states,
        "feedback_count": feedback_count,
        "recent_documents": [
            {
                "id": d.id,
                "file_name": d.file_name,
                "state": d.state_name,
                "status": d.processing_status,
                "upload_date": d.upload_date.isoformat() if d.upload_date is not None else None,
            }
            for d in recent_docs
        ],
    }


# ─── Training Data CRUD (Incremental Learning) ───

async def save_training_sample(
    db: AsyncSession,
    document_id: int,
    features: dict,
    labels: dict,
    metadata_info: Optional[dict] = None,
    source: str = "auto",
) -> TrainingData:
    """Save or update a training sample for a DPR."""
    result = await db.execute(
        select(TrainingData).where(TrainingData.document_id == document_id)
    )
    td = result.scalar_one_or_none()
    if td:
        td.features = features
        td.labels = labels
        td.metadata_info = metadata_info
        td.source = source
        td.updated_at = datetime.datetime.utcnow()
    else:
        td = TrainingData(
            document_id=document_id,
            features=features,
            labels=labels,
            metadata_info=metadata_info,
            source=source,
        )
        db.add(td)
    await db.flush()
    return td


async def update_training_labels(
    db: AsyncSession,
    document_id: int,
    corrected_labels: dict,
) -> Optional[TrainingData]:
    """Update labels with user-corrected values (ground truth)."""
    result = await db.execute(
        select(TrainingData).where(TrainingData.document_id == document_id)
    )
    td = result.scalar_one_or_none()
    if td:
        existing = td.labels or {}
        existing.update(corrected_labels)
        td.labels = existing
        td.is_user_corrected = True
        td.updated_at = datetime.datetime.utcnow()
        await db.flush()
    return td


async def get_all_training_data(
    db: AsyncSession, corrected_only: bool = False
) -> List[TrainingData]:
    """Retrieve all training samples."""
    q = select(TrainingData).order_by(TrainingData.created_at)
    if corrected_only:
        q = q.where(TrainingData.is_user_corrected == True)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_training_data_count(db: AsyncSession) -> dict:
    """Get count of training samples."""
    total = (await db.execute(select(func.count(TrainingData.id)))).scalar() or 0
    corrected = (await db.execute(
        select(func.count(TrainingData.id)).where(TrainingData.is_user_corrected == True)
    )).scalar() or 0
    return {"total": total, "user_corrected": corrected, "auto_labeled": total - corrected}


# ─── Model Version CRUD ───

async def save_model_version(
    db: AsyncSession,
    training_report: dict,
) -> ModelVersion:
    """Record a new model version after training."""
    # Get next version number
    latest = (await db.execute(
        select(func.max(ModelVersion.version))
    )).scalar() or 0
    new_version = latest + 1

    mv = ModelVersion(
        version=new_version,
        real_samples_used=training_report.get("real_samples", 0),
        synthetic_samples_used=training_report.get("synthetic_samples", 0),
        total_samples_used=training_report.get("total_training_samples", 0),
        cost_model_metrics=training_report.get("models", {}).get("cost_overrun"),
        delay_model_metrics=training_report.get("models", {}).get("delay"),
        risk_model_metrics=training_report.get("models", {}).get("risk_classifier"),
        feature_importance=training_report.get("feature_importance"),
        training_report=training_report,
    )
    db.add(mv)
    await db.flush()
    return mv


async def get_model_versions(
    db: AsyncSession, limit: int = 20
) -> List[ModelVersion]:
    """Get model version history (newest first)."""
    result = await db.execute(
        select(ModelVersion)
        .order_by(desc(ModelVersion.version))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_latest_model_version(
    db: AsyncSession,
) -> Optional[ModelVersion]:
    """Get the latest model version."""
    result = await db.execute(
        select(ModelVersion).order_by(desc(ModelVersion.version)).limit(1)
    )
    return result.scalar_one_or_none()
