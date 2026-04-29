# ============================================
# Database Service - PostgreSQL
# ============================================

from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.postgres_models import (
    DPRDocument, DPRAnalysis, QualityScore, RiskAssessment, 
    TrainingData, State, ModelVersion, UserFeedback, AnalyticsLog
)


# ─── Document CRUD ───

def get_document(db: Session, document_id: int):
    doc = db.query(DPRDocument).filter(DPRDocument.id == document_id).first()
    return doc


def create_document(
    db: Session,
    filename: str,
    file_path: str,
    state_name: Optional[str] = None,
    project_type: Optional[str] = None,
    project_cost_crores: float = 0,
    file_size_mb: float = 0,
):
    doc = DPRDocument(
        filename=filename,
        file_path=file_path,
        state_name=state_name,
        project_type=project_type,
        project_cost_crores=project_cost_crores,
        file_size_mb=file_size_mb,
        processing_status="uploaded",
        processed=False,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def update_document_status(db: Session, document_id: int, status: str):
    doc = get_document(db, document_id)
    if doc:
        doc.processing_status = status  # type: ignore
        doc.processed = status == "completed"  # type: ignore
        db.commit()
        db.refresh(doc)
    return doc


def list_documents(db: Session, state_name: Optional[str] = None, limit: int = 50, offset: int = 0):
    query = db.query(DPRDocument).order_by(DPRDocument.upload_date.desc())
    if state_name:
        query = query.filter(DPRDocument.state_name == state_name)
    return query.limit(limit).offset(offset).all()


# ─── Analysis CRUD ───

def save_analysis(
    db: Session,
    document_id: int,
    nlp_result: dict,
    table_analysis: Optional[dict] = None,
    extraction_meta: Optional[dict] = None,
):
    """Save analysis to PostgreSQL with only primitive types."""
    
    if not isinstance(nlp_result, dict):
        nlp_result = {}
    
    # Extract sections data - the structure is {section_name: {found, word_count, ...}, ...}
    sections = nlp_result.get("sections", {})
    sections_found = 0
    sections_total = 14  # Standard DPR sections
    if isinstance(sections, dict):
        sections_total = len(sections)
        sections_found = sum(1 for s in sections.values() if isinstance(s, dict) and s.get("found", False))
    
    entities = nlp_result.get("entities", {})
    organizations_count = 0
    locations_count = 0
    dates_count = 0
    if isinstance(entities, dict):
        orgs = entities.get("organizations", [])
        organizations_count = len(orgs) if isinstance(orgs, list) else 0
        locs = entities.get("locations", [])
        locations_count = len(locs) if isinstance(locs, list) else 0
        dates = entities.get("dates", [])
        dates_count = len(dates) if isinstance(dates, list) else 0
    
    financial_figures = nlp_result.get("financial_figures", [])
    total_cost_extracted = 0
    if isinstance(financial_figures, list):
        for f in financial_figures:
            if isinstance(f, dict):
                val = f.get("value_in_crores", 0)
                if isinstance(val, (int, float)):
                    total_cost_extracted += val
    
    text_stats = nlp_result.get("text_statistics", {})
    word_count = 0
    char_count = 0
    if isinstance(text_stats, dict):
        wc = text_stats.get("word_count", 0)
        word_count = wc if isinstance(wc, (int, float)) else 0
        cc = text_stats.get("char_count", 0)
        char_count = cc if isinstance(cc, (int, float)) else 0
    
    # Create or update analysis
    analysis = db.query(DPRAnalysis).filter(DPRAnalysis.document_id == document_id).first()
    if not analysis:
        analysis = DPRAnalysis(document_id=document_id)
    
    analysis.sections_found = int(sections_found)  # type: ignore
    analysis.sections_total = int(sections_total)  # type: ignore
    analysis.organizations_count = int(organizations_count)  # type: ignore
    analysis.locations_count = int(locations_count)  # type: ignore
    analysis.dates_count = int(dates_count)  # type: ignore
    analysis.total_cost_extracted = float(total_cost_extracted)  # type: ignore
    analysis.word_count = int(word_count)  # type: ignore
    analysis.char_count = int(char_count)  # type: ignore
    
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    update_document_status(db, document_id, "analyzed")
    return analysis


# ─── Quality Score CRUD ───

def save_quality_score(db: Session, document_id: int, report: dict):
    """Save quality score to PostgreSQL with only primitive types."""
    
    if not isinstance(report, dict):
        report = {}
    
    individual_scores = report.get("individual_scores", {})
    if not isinstance(individual_scores, dict):
        individual_scores = {}
    
    composite_score = report.get("composite_score", 0)
    composite_score = composite_score if isinstance(composite_score, (int, float)) else 0
    
    grade = report.get("grade", "F")
    grade = str(grade) if grade else "F"
    
    grade_description = report.get("grade_description", "")
    grade_description = str(grade_description) if grade_description else ""
    
    section_completeness_score = individual_scores.get("section_completeness", 0)
    section_completeness_score = section_completeness_score if isinstance(section_completeness_score, (int, float)) else 0
    
    technical_depth_score = individual_scores.get("technical_depth", 0)
    technical_depth_score = technical_depth_score if isinstance(technical_depth_score, (int, float)) else 0
    
    financial_accuracy_score = individual_scores.get("financial_accuracy", 0)
    financial_accuracy_score = financial_accuracy_score if isinstance(financial_accuracy_score, (int, float)) else 0
    
    compliance_score = individual_scores.get("compliance", 0)
    compliance_score = compliance_score if isinstance(compliance_score, (int, float)) else 0
    
    risk_assessment_quality_score = individual_scores.get("risk_assessment", 0)
    risk_assessment_quality_score = risk_assessment_quality_score if isinstance(risk_assessment_quality_score, (int, float)) else 0
    
    compliance_level = report.get("compliance_level", "")
    compliance_level = str(compliance_level) if compliance_level else ""
    
    compliance_status = report.get("compliance_status", "")
    compliance_status = str(compliance_status) if compliance_status else ""
    
    violations = report.get("violations", [])
    violations = [str(v) for v in violations] if isinstance(violations, list) else []
    
    warnings = report.get("warnings", [])
    warnings = [str(w) for w in warnings] if isinstance(warnings, list) else []
    
    recommendations = report.get("recommendations", [])
    recommendations = [str(r) for r in recommendations] if isinstance(recommendations, list) else []
    
    # Create or update score
    score = db.query(QualityScore).filter(QualityScore.document_id == document_id).first()
    if not score:
        score = QualityScore(document_id=document_id)
    
    score.composite_score = float(composite_score)  # type: ignore
    score.grade = grade  # type: ignore
    score.grade_description = grade_description  # type: ignore
    score.section_completeness_score = float(section_completeness_score)  # type: ignore
    score.technical_depth_score = float(technical_depth_score)  # type: ignore
    score.financial_accuracy_score = float(financial_accuracy_score)  # type: ignore
    score.compliance_score = float(compliance_score)  # type: ignore
    score.risk_assessment_quality_score = float(risk_assessment_quality_score)  # type: ignore
    score.compliance_level = compliance_level  # type: ignore
    score.compliance_status = compliance_status  # type: ignore
    score.violations = violations  # type: ignore
    score.warnings = warnings  # type: ignore
    score.recommendations = recommendations  # type: ignore
    
    db.add(score)
    db.commit()
    db.refresh(score)
    
    update_document_status(db, document_id, "scored")
    return score


# ─── Risk Assessment CRUD ───

def save_risk_assessment(
    db: Session,
    document_id: int,
    risk_report: dict,
    verdict: Optional[dict] = None,
):
    """Save risk assessment to PostgreSQL with only primitive types."""
    
    if not isinstance(risk_report, dict):
        risk_report = {}
    
    risk_summary = risk_report.get("risk_summary", {})
    if not isinstance(risk_summary, dict):
        risk_summary = {}
    
    overall_risk_level = risk_summary.get("overall_risk_level", "Unknown")
    overall_risk_level = str(overall_risk_level) if overall_risk_level else "Unknown"
    
    cost_overrun_probability = risk_summary.get("cost_overrun_probability", 0)
    cost_overrun_probability = cost_overrun_probability if isinstance(cost_overrun_probability, (int, float)) else 0
    
    delay_probability = risk_summary.get("delay_probability", 0)
    delay_probability = delay_probability if isinstance(delay_probability, (int, float)) else 0
    
    model_confidence = risk_summary.get("model_confidence", 0)
    model_confidence = model_confidence if isinstance(model_confidence, (int, float)) else 0
    
    top_risk_drivers = risk_summary.get("top_risk_drivers", [])
    top_risk_drivers = [str(d) for d in top_risk_drivers] if isinstance(top_risk_drivers, list) else []
    
    mitigation_strategies = risk_report.get("mitigation_strategies", [])
    mitigation_strategies = [str(m) for m in mitigation_strategies] if isinstance(mitigation_strategies, list) else []
    
    # Create or update assessment
    assessment = db.query(RiskAssessment).filter(RiskAssessment.document_id == document_id).first()
    if not assessment:
        assessment = RiskAssessment(document_id=document_id)
    
    assessment.overall_risk_level = overall_risk_level  # type: ignore
    assessment.cost_overrun_probability = float(cost_overrun_probability)  # type: ignore
    assessment.delay_probability = float(delay_probability)  # type: ignore
    assessment.model_confidence = float(model_confidence)  # type: ignore
    assessment.top_risk_drivers = top_risk_drivers  # type: ignore
    assessment.mitigation_strategies = mitigation_strategies  # type: ignore
    
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    
    update_document_status(db, document_id, "completed")
    return assessment


# ─── Training Data CRUD ───

def save_training_data(
    db: Session,
    document_id: int,
    features: dict,
    labels: dict,
    metadata_info: Optional[dict] = None,
    is_user_corrected: bool = False,
):
    """Save training data (features + labels) extracted from a DPR analysis.
    This is used by the incremental learning system to retrain ML models."""
    
    # Ensure features and labels are dicts
    if not isinstance(features, dict):
        features = {}
    if not isinstance(labels, dict):
        labels = {}
    if not isinstance(metadata_info, dict):
        metadata_info = {}
    
    # Check if training data already exists for this document
    training = db.query(TrainingData).filter(TrainingData.document_id == document_id).first()
    
    if not training:
        # Create new training data record
        training = TrainingData(
            document_id=document_id,
            features=features,  # type: ignore
            labels=labels,  # type: ignore
            metadata_info=metadata_info,  # type: ignore
            is_user_corrected=is_user_corrected,  # type: ignore
            source="auto",
        )
    else:
        # Update existing training data
        training.features = features  # type: ignore
        training.labels = labels  # type: ignore
        training.metadata_info = metadata_info  # type: ignore
        training.updated_at = datetime.utcnow()  # type: ignore
    
    db.add(training)
    db.commit()
    db.refresh(training)
    
    return training


# ─── State Reference Data ───

def get_all_states(db: Session):
    return db.query(State).order_by(State.name).all()


def get_mdoner_states(db: Session):
    return db.query(State).filter(State.is_mdoner == True).all()


# ─── Explainability Helper Functions ───

def get_risk_assessment(db: Session, document_id: int):
    """Fetch risk assessment for a document."""
    assessment = db.query(RiskAssessment).filter(RiskAssessment.document_id == document_id).first()
    return assessment


def get_training_data(db: Session, document_id: int):
    """Fetch training data (feature vector) for a document."""
    training = db.query(TrainingData).filter(TrainingData.document_id == document_id).first()
    return training


def get_quality_score(db: Session, document_id: int):
    """Fetch quality score for a document."""
    quality = db.query(QualityScore).filter(QualityScore.document_id == document_id).first()
    return quality


def get_analysis(db: Session, document_id: int):
    """Fetch analysis for a document."""
    analysis = db.query(DPRAnalysis).filter(DPRAnalysis.document_id == document_id).first()
    return analysis


# ─── Learning & Model Management Functions ───

def get_training_data_count(db: Session) -> dict:
    """Get training data statistics."""
    total = db.query(TrainingData).count()
    user_corrected = db.query(TrainingData).filter(TrainingData.is_user_corrected == True).count()
    
    return {
        "total": total,
        "user_corrected": user_corrected,
        "auto_generated": total - user_corrected,
    }


def get_all_training_data(db: Session):
    """Get all training data records."""
    return db.query(TrainingData).all()


def get_model_versions(db: Session, limit: int = 10):
    """Get model versions ordered by version descending."""
    return db.query(ModelVersion).order_by(ModelVersion.version.desc()).limit(limit).all()


def get_latest_model_version(db: Session):
    """Get the latest model version."""
    return db.query(ModelVersion).order_by(ModelVersion.version.desc()).first()


def save_model_version(db: Session, report: dict):
    """Save a new model version."""
    # Get next version number
    latest = get_latest_model_version(db)
    next_version = (latest.version + 1) if latest else 1
    
    mv = ModelVersion(
        version=next_version,
        real_samples_used=report.get("real_samples", 0),
        synthetic_samples_used=report.get("synthetic_samples", 0),
        total_samples_used=report.get("total_samples", 0),
        cost_model_metrics=report.get("cost_metrics", {}),
        delay_model_metrics=report.get("delay_metrics", {}),
        risk_model_metrics=report.get("risk_metrics", {}),
        feature_importance=report.get("feature_importance", {}),
        training_report=report,
    )
    db.add(mv)
    db.commit()
    db.refresh(mv)
    return mv


def update_training_labels(db: Session, document_id: int, corrected_labels: dict):
    """Update training data labels for a document (user feedback)."""
    training = db.query(TrainingData).filter(TrainingData.document_id == document_id).first()
    if training:
        training.labels = corrected_labels  # type: ignore
        training.is_user_corrected = True  # type: ignore
        training.updated_at = datetime.utcnow()  # type: ignore
        db.commit()
        db.refresh(training)
    return training


def create_feedback(db: Session, document_id: int, feedback_type: str, **kwargs):
    """Create user feedback record."""
    feedback = UserFeedback(
        document_id=document_id,
        feedback_type=feedback_type,
        rating=kwargs.get("rating"),
        is_accurate=kwargs.get("is_accurate"),
        user_comment=kwargs.get("user_comment"),
        corrected_score=kwargs.get("corrected_score"),
        corrected_risk_level=kwargs.get("corrected_risk_level"),
        corrected_data=kwargs.get("corrected_data"),
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def log_action(db: Session, action: str, document_id: Optional[int] = None, state: Optional[str] = None, details: Optional[dict] = None, duration_ms: Optional[float] = None):
    """Log an action in analytics log."""
    log_entry = AnalyticsLog(
        action=action,
        document_id=document_id,
        state=state,
        details=details or {},
        duration_ms=duration_ms,
    )
    db.add(log_entry)
    db.commit()
    return log_entry


# ─── Dashboard \u0026 Reference Data ───

def get_dashboard_stats(db: Session) -> dict:
    """Get dashboard statistics."""
    total_docs = db.query(DPRDocument).count()
    completed = db.query(DPRDocument).filter(DPRDocument.processing_status == "completed").count()
    
    from sqlalchemy import func
    avg_score = db.query(func.avg(QualityScore.composite_score)).scalar() or 0
    
    return {
        "total_documents": total_docs,
        "completed_analyses": completed,
        "average_quality_score": round(float(avg_score), 1),
    }


def get_all_sections(db: Session):
    """Get all DPR sections from reference table."""
    from app.models.postgres_models import DPRSection
    sections = db.query(DPRSection).all()
    if not sections:
        # Return default sections if table is empty
        from config.settings import settings
        class SectionProxy:
            def __init__(self, name):
                self.name = name
        return [SectionProxy(s) for s in settings.REQUIRED_DPR_SECTIONS]
    return sections


def get_scoring_weights(db: Session):
    """Get scoring weights from reference table."""
    from app.models.postgres_models import ScoringWeight
    weights = db.query(ScoringWeight).all()
    if not weights:
        # Return default weights if table is empty
        from config.settings import settings
        class WeightProxy:
            def __init__(self, criterion, weight, description=""):
                self.criterion = criterion
                self.weight = weight
                self.description = description
        return [
            WeightProxy("Section Completeness", settings.SECTION_COMPLETENESS_WEIGHT),
            WeightProxy("Technical Depth", settings.TECHNICAL_DEPTH_WEIGHT),
            WeightProxy("Financial Accuracy", settings.FINANCIAL_ACCURACY_WEIGHT),
            WeightProxy("Compliance", settings.COMPLIANCE_WEIGHT),
            WeightProxy("Risk Assessment", settings.RISK_ASSESSMENT_WEIGHT),
        ]
    return weights


def get_grade_definitions(db: Session):
    """Get grade definitions from reference table."""
    from app.models.postgres_models import GradeDefinition
    grades = db.query(GradeDefinition).order_by(GradeDefinition.min_score.desc()).all()
    if not grades:
        # Return default grade definitions
        class GradeProxy:
            def __init__(self, grade, min_score, max_score, description):
                self.grade = grade
                self.min_score = min_score
                self.max_score = max_score
                self.description = description
        return [
            GradeProxy("A+", 90, 100, "Excellent"),
            GradeProxy("A", 80, 89, "Very Good"),
            GradeProxy("B+", 70, 79, "Good"),
            GradeProxy("B", 60, 69, "Satisfactory"),
            GradeProxy("C", 50, 59, "Below Average"),
            GradeProxy("D", 40, 49, "Poor"),
            GradeProxy("F", 0, 39, "Fail"),
        ]
    return grades


def get_state_by_name(db: Session, name: str):
    """Get a state by its name."""
    return db.query(State).filter(State.name == name).first()


def get_feedback_for_document(db: Session, document_id: int):
    """Get feedback records for a specific document."""
    return db.query(UserFeedback).filter(UserFeedback.document_id == document_id).all()


def get_all_feedback(db: Session, feedback_type: Optional[str] = None, limit: int = 50):
    """Get all feedback records, optionally filtered by type."""
    query = db.query(UserFeedback).order_by(UserFeedback.created_at.desc())
    if feedback_type:
        query = query.filter(UserFeedback.feedback_type == feedback_type)
    return query.limit(limit).all()

