# ============================================
# Pydantic Schemas for API Request/Response
# ============================================

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ---- Upload Schemas ----
class DPRUploadRequest(BaseModel):
    state: Optional[str] = Field(None, description="Indian state name")
    project_type: Optional[str] = Field(None, description="Type of project")
    project_name: Optional[str] = Field(None, description="Name of the project")
    project_cost_crores: Optional[float] = Field(None, description="Estimated project cost in crores")


class DPRUploadResponse(BaseModel):
    document_id: int
    file_name: str
    state: Optional[str]
    message: str
    status: str


# ---- Analysis Schemas ----
class AnalysisRequest(BaseModel):
    document_id: int
    include_ocr: bool = False
    state: Optional[str] = None


class SectionAnalysis(BaseModel):
    section_name: str
    found: bool
    word_count: int
    header: str


class NLPAnalysisResponse(BaseModel):
    document_id: int
    sections_found: int
    sections_total: int
    sections_completeness: float
    entities_count: int
    financial_figures_count: int
    dates_count: int
    text_statistics: dict
    sections: dict
    key_phrases: list


# ---- Quality Score Schemas ----
class QualityScoreRequest(BaseModel):
    document_id: int
    state: Optional[str] = None
    project_type: Optional[str] = None


class ScoreBreakdown(BaseModel):
    score: float
    weight: float
    weighted_score: float


class QualityScoreResponse(BaseModel):
    document_id: int
    composite_score: float
    grade: str
    grade_description: str
    scores: dict
    recommendations: list
    summary: dict


# ---- Risk Prediction Schemas ----
class RiskPredictionRequest(BaseModel):
    document_id: int
    state: Optional[str] = None
    project_type: Optional[str] = None
    project_cost_crores: Optional[float] = None


class RiskPredictionResponse(BaseModel):
    document_id: int
    risk_summary: dict
    cost_overrun_analysis: dict
    delay_analysis: dict
    risk_classification: dict
    monte_carlo_simulation: dict
    mitigation_strategies: list


# ---- Dashboard Schemas ----
class DashboardStats(BaseModel):
    total_documents: int
    avg_quality_score: float
    avg_risk_level: str
    documents_by_state: dict
    recent_analyses: list
    risk_distribution: dict


class StateAnalytics(BaseModel):
    state: str
    total_projects: int
    avg_quality_score: float
    avg_cost_overrun_risk: float
    avg_delay_risk: float
    common_issues: list


# ---- Common Schemas ----
class HealthCheck(BaseModel):
    status: str
    version: str
    timestamp: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int
