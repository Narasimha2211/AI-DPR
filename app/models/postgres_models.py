# ============================================
# PostgreSQL Models - SQLAlchemy ORM
# ============================================

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()


class DPRDocument(Base):
    __tablename__ = "dpr_documents"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    state_name = Column(String(100))
    project_type = Column(String(100))
    project_cost_crores = Column(Float, default=0)
    file_path = Column(String(500))
    processing_status = Column(String(50), default="uploaded")
    processed = Column(Boolean, default=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_size_mb = Column(Float)
    
    # Relationships
    analysis = relationship("DPRAnalysis", uselist=False, backref="document")
    quality_score = relationship("QualityScore", uselist=False, backref="document")
    risk_assessment = relationship("RiskAssessment", uselist=False, backref="document")


class DPRAnalysis(Base):
    __tablename__ = "dpr_analyses"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("dpr_documents.id"), unique=True)
    sections_found = Column(Integer, default=0)
    sections_total = Column(Integer, default=14)
    organizations_count = Column(Integer, default=0)
    locations_count = Column(Integer, default=0)
    dates_count = Column(Integer, default=0)
    total_cost_extracted = Column(Float, default=0)
    word_count = Column(Integer, default=0)
    char_count = Column(Integer, default=0)
    analysis_date = Column(DateTime, default=datetime.utcnow)


class QualityScore(Base):
    __tablename__ = "quality_scores"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("dpr_documents.id"), unique=True)
    composite_score = Column(Float, default=0)
    grade = Column(String(10), default="F")
    grade_description = Column(Text)
    section_completeness_score = Column(Float, default=0)
    technical_depth_score = Column(Float, default=0)
    financial_accuracy_score = Column(Float, default=0)
    compliance_score = Column(Float, default=0)
    risk_assessment_quality_score = Column(Float, default=0)
    compliance_level = Column(String(50))
    compliance_status = Column(String(50))
    violations = Column(JSON, default=[])
    warnings = Column(JSON, default=[])
    recommendations = Column(JSON, default=[])
    scored_date = Column(DateTime, default=datetime.utcnow)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("dpr_documents.id"), unique=True)
    overall_risk_level = Column(String(50), default="Unknown")
    cost_overrun_probability = Column(Float, default=0)
    delay_probability = Column(Float, default=0)
    model_confidence = Column(Float, default=0)
    top_risk_drivers = Column(JSON, default=[])
    mitigation_strategies = Column(JSON, default=[])
    assessed_date = Column(DateTime, default=datetime.utcnow)


class TrainingData(Base):
    __tablename__ = "training_data"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("dpr_documents.id"))
    feature_vector = Column(JSON)
    features = Column(JSON)
    labels = Column(JSON)
    metadata_info = Column(JSON, default=None)
    actual_cost_overrun = Column(Float)
    actual_delay = Column(Float)
    risk_label = Column(String(50))
    is_user_corrected = Column(Boolean, default=False, index=True)
    source = Column(String(30), default="auto")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class State(Base):
    __tablename__ = "states"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    code = Column(String(10))
    is_mdoner = Column(Boolean, default=False)
    region = Column(String(50))


class ModelVersion(Base):
    __tablename__ = "model_versions"
    
    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False, index=True)
    real_samples_used = Column(Integer, default=0)
    synthetic_samples_used = Column(Integer, default=0)
    total_samples_used = Column(Integer, default=0)
    cost_model_metrics = Column(JSON, default={})
    delay_model_metrics = Column(JSON, default={})
    risk_model_metrics = Column(JSON, default={})
    feature_importance = Column(JSON, default={})
    training_report = Column(JSON, default={})
    trained_at = Column(DateTime, default=datetime.utcnow, index=True)


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("dpr_documents.id"))
    feedback_type = Column(String(50), nullable=False)
    rating = Column(Integer)
    is_accurate = Column(Boolean)
    user_comment = Column(Text)
    corrected_score = Column(Float)
    corrected_risk_level = Column(String(20))
    corrected_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AnalyticsLog(Base):
    __tablename__ = "analytics_logs"
    
    id = Column(Integer, primary_key=True)
    action = Column(String(100), index=True)
    document_id = Column(Integer, ForeignKey("dpr_documents.id"))
    state = Column(String(100))
    details = Column(JSON, default={})
    duration_ms = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default="Viewer")  # Admin, Analyst, Viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DPRSection(Base):
    __tablename__ = "dpr_sections"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text)


class ScoringWeight(Base):
    __tablename__ = "scoring_weights"
    
    id = Column(Integer, primary_key=True)
    criterion = Column(String(100), unique=True, nullable=False)
    weight = Column(Float, default=0)
    description = Column(Text)


class GradeDefinition(Base):
    __tablename__ = "grade_definitions"
    
    id = Column(Integer, primary_key=True)
    grade = Column(String(10), unique=True, nullable=False)
    min_score = Column(Float, default=0)
    max_score = Column(Float, default=100)
    description = Column(Text)

