# ============================================
# PostgreSQL Database Models (SQLAlchemy 2.0)
# Full persistent storage for AI DPR system
# ============================================

import datetime
from typing import Optional, List, Any

from sqlalchemy import String, Float, Text, Integer, Boolean, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


# ─── Reference / Config Tables (DB-driven, not hardcoded) ───

class State(Base):
    """Indian states – loaded from DB, not hardcoded."""
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(10), unique=True, default=None)
    is_mdoner: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    region: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    terrain: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    risk_factor: Mapped[float] = mapped_column(Float, default=5.0)
    special_provisions: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    priority_sectors: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    additional_requirements: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(default=datetime.datetime.utcnow)

    documents: Mapped[List["DPRDocument"]] = relationship(back_populates="state_ref")


class DPRSectionDef(Base):
    """Required DPR sections – stored in DB for easy updates."""
    __tablename__ = "dpr_section_defs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    min_word_count: Mapped[int] = mapped_column(Integer, default=100)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    sub_elements: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(default=datetime.datetime.utcnow)


class ComplianceRule(Base):
    """Government compliance rules – editable via DB."""
    __tablename__ = "compliance_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    applies_to: Mapped[str] = mapped_column(String(50), default="all")
    state_code: Mapped[Optional[str]] = mapped_column(String(10), default=None)
    threshold_value: Mapped[Optional[float]] = mapped_column(Float, default=None)
    threshold_unit: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(default=datetime.datetime.utcnow)


class ScoringWeight(Base):
    """Quality scoring weights – adjustable via DB."""
    __tablename__ = "scoring_weights"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    criterion: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(300), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )


class GradeDefinition(Base):
    """Grading definitions – stored in DB."""
    __tablename__ = "grade_definitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    grade: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)
    min_score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(300), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ─── Core Data Tables ───

class DPRDocument(Base):
    """Stores uploaded DPR documents and their metadata."""
    __tablename__ = "dpr_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_kb: Mapped[Optional[float]] = mapped_column(Float, default=None)
    file_format: Mapped[Optional[str]] = mapped_column(String(10), default=None)
    state_id: Mapped[Optional[int]] = mapped_column(ForeignKey("states.id"), default=None, index=True)
    state_name: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    project_type: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    project_name: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    project_cost_crores: Mapped[Optional[float]] = mapped_column(Float, default=None)
    total_pages: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    total_words: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    upload_date: Mapped[Optional[datetime.datetime]] = mapped_column(default=datetime.datetime.utcnow, index=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="uploaded")

    state_ref: Mapped[Optional["State"]] = relationship(back_populates="documents")
    analysis: Mapped[Optional["DPRAnalysis"]] = relationship(
        back_populates="document", uselist=False, cascade="all, delete-orphan"
    )
    quality_score: Mapped[Optional["QualityScore"]] = relationship(
        back_populates="document", uselist=False, cascade="all, delete-orphan"
    )
    risk_assessment: Mapped[Optional["RiskAssessment"]] = relationship(
        back_populates="document", uselist=False, cascade="all, delete-orphan"
    )
    feedback: Mapped[List["UserFeedback"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_documents_state_date", "state_name", "upload_date"),
    )


class DPRAnalysis(Base):
    """Stores NLP analysis results for a DPR."""
    __tablename__ = "dpr_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("dpr_documents.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    sections_found: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    sections_total: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    sections_data: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    entities_data: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    organizations_count: Mapped[int] = mapped_column(Integer, default=0)
    locations_count: Mapped[int] = mapped_column(Integer, default=0)
    dates_count: Mapped[int] = mapped_column(Integer, default=0)
    financial_figures: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    total_cost_extracted: Mapped[Optional[float]] = mapped_column(Float, default=None)
    text_statistics: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    key_phrases: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    table_analysis: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    full_nlp_result: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    analysis_date: Mapped[Optional[datetime.datetime]] = mapped_column(default=datetime.datetime.utcnow)

    document: Mapped["DPRDocument"] = relationship(back_populates="analysis")


class QualityScore(Base):
    """Stores quality scoring results."""
    __tablename__ = "quality_scores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("dpr_documents.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    composite_score: Mapped[Optional[float]] = mapped_column(Float, default=None, index=True)
    grade: Mapped[Optional[str]] = mapped_column(String(5), default=None)
    grade_description: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    section_completeness_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    technical_depth_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    financial_accuracy_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    compliance_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    risk_assessment_quality_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    compliance_level: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    compliance_status: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    violations: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    warnings: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    recommendations: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    full_report: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    scored_date: Mapped[Optional[datetime.datetime]] = mapped_column(default=datetime.datetime.utcnow)

    document: Mapped["DPRDocument"] = relationship(back_populates="quality_score")


class RiskAssessment(Base):
    """Stores risk prediction results."""
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("dpr_documents.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    overall_risk_level: Mapped[Optional[str]] = mapped_column(String(20), default=None, index=True)
    cost_overrun_probability: Mapped[Optional[float]] = mapped_column(Float, default=None)
    delay_probability: Mapped[Optional[float]] = mapped_column(Float, default=None)
    model_confidence: Mapped[Optional[float]] = mapped_column(Float, default=None)
    cost_prediction: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    delay_prediction: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    risk_classification: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    monte_carlo_results: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    explanation: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    top_risk_drivers: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    mitigation_strategies: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    verdict: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    full_report: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    assessed_date: Mapped[Optional[datetime.datetime]] = mapped_column(default=datetime.datetime.utcnow)

    document: Mapped["DPRDocument"] = relationship(back_populates="risk_assessment")


class UserFeedback(Base):
    """User feedback on results – used for future quality & ML retraining."""
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("dpr_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    is_accurate: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    user_comment: Mapped[Optional[str]] = mapped_column(Text, default=None)
    corrected_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    corrected_risk_level: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    corrected_data: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(default=datetime.datetime.utcnow)

    document: Mapped["DPRDocument"] = relationship(back_populates="feedback")

    __table_args__ = (
        Index("ix_feedback_type_date", "feedback_type", "created_at"),
    )


class AnalyticsLog(Base):
    """Tracks system usage and analytics."""
    __tablename__ = "analytics_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action: Mapped[Optional[str]] = mapped_column(String(100), default=None, index=True)
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dpr_documents.id", ondelete="SET NULL"), default=None
    )
    state: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    details: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, default=None)
    timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(default=datetime.datetime.utcnow, index=True)
