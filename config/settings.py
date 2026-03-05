# ============================================
# AI DPR Configuration
# ============================================
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ML_DIR = BASE_DIR / "ml"
UPLOAD_DIR = BASE_DIR / "uploads"
MODELS_DIR = ML_DIR / "models"

# Create directories if they don't exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)


class Settings:
    """Application configuration settings."""

    # Directories (accessible via settings instance)
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    ML_DIR: Path = ML_DIR
    UPLOAD_DIR: Path = UPLOAD_DIR
    MODELS_DIR: Path = MODELS_DIR

    # App
    APP_NAME: str = "AI DPR Analysis System"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-Powered Detailed Project Report Analysis for Indian Government Projects"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database – PostgreSQL via asyncpg
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://narasimhareddykasarla@localhost:5432/ai_dpr"
    )
    DATABASE_ECHO: bool = False

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "ai-dpr-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # File handling
    MAX_FILE_SIZE_MB: int = 50

    # NLP
    SPACY_MODEL: str = "en_core_web_sm"
    MAX_UPLOAD_SIZE_MB: int = 50
    SUPPORTED_FORMATS: list = [".pdf", ".docx", ".doc", ".txt", ".png", ".jpg", ".jpeg"]

    # OCR
    TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "/usr/bin/tesseract")
    OCR_LANGUAGES: list = ["eng", "hin", "tel", "tam", "kan", "mal", "ben", "guj", "mar", "ori"]

    # ML Models
    RISK_MODEL_PATH: str = str(MODELS_DIR / "risk_predictor.pkl")
    QUALITY_MODEL_PATH: str = str(MODELS_DIR / "quality_classifier.pkl")

    # Indian States Configuration
    SUPPORTED_STATES: list = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
        "Chhattisgarh", "Goa", "Gujarat", "Haryana",
        "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
        "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
        "Mizoram", "Nagaland", "Odisha", "Punjab",
        "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
        "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
    ]

    # MDoNER - Ministry of Development of North Eastern Region States
    MDONER_STATES: list = [
        "Arunachal Pradesh", "Assam", "Manipur", "Meghalaya",
        "Mizoram", "Nagaland", "Sikkim", "Tripura"
    ]

    # DPR Sections required by Indian Government Standards
    REQUIRED_DPR_SECTIONS: list = [
        "Executive Summary",
        "Project Background & Justification",
        "Project Objectives",
        "Scope of Work",
        "Technical Feasibility",
        "Financial Analysis",
        "Cost Estimates",
        "Implementation Schedule",
        "Institutional Framework",
        "Environmental & Social Impact Assessment",
        "Risk Assessment & Mitigation",
        "Monitoring & Evaluation Framework",
        "Sustainability Plan",
        "Annexures & Supporting Documents"
    ]

    # Scoring Weights
    SECTION_COMPLETENESS_WEIGHT: float = 0.25
    TECHNICAL_DEPTH_WEIGHT: float = 0.20
    FINANCIAL_ACCURACY_WEIGHT: float = 0.20
    COMPLIANCE_WEIGHT: float = 0.20
    RISK_ASSESSMENT_WEIGHT: float = 0.15


settings = Settings()
