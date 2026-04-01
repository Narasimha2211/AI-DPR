# AI DPR Analysis System

> **AI-powered Detailed Project Report (DPR) analyzer for Indian government projects with incremental learning**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://www.postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

The **AI DPR Analysis System** is an end-to-end intelligent platform that automates the evaluation of government Detailed Project Reports (DPRs), with special focus on **MDoNER (Ministry of Development of North Eastern Region)** states. It combines:

- **NLP Document Intelligence** - Section identification, entity extraction, financial figure parsing
- **Quality & Compliance Scoring** - 14-section completeness check + Central/State/MDoNER rule validation
- **ML Risk Prediction** - XGBoost/LightGBM models for cost overrun, delay, and risk classification
- **Explainable AI** - SHAP/LIME-inspired narrative explanations + Monte Carlo simulations
- **Incremental Learning** - AI improves with every DPR uploaded, retrains on real data with user feedback
- **Interactive Dashboard** - Real-time visualization with Chart.js
- **PostgreSQL Backend** - Production-ready async database with full persistence

---

## Architecture

```
+-------------------------------------------------------------+
|                    Frontend Dashboard                        |
|           (HTML/CSS/JS + Chart.js 4.4)                      |
|   +----------+ +----------+ +----------+ +--------------+   |
|   |  Upload   | | Analysis | |Dashboard | |Model Learning|   |
|   |   Tab     | |   Tab    | |   Tab    | |     Tab      |   |
|   +----------+ +----------+ +----------+ +--------------+   |
+-------------------------------------------------------------+
|                    FastAPI Backend                           |
|   +----------+ +----------+ +----------+ +--------------+   |
|   |  Upload   | | Analysis | |  Risk    | |  Learning    |   |
|   |  Routes   | | Scoring  | |  Routes  | |  Routes      |   |
|   +----------+ +----------+ +----------+ +--------------+   |
+-------------------------------------------------------------+
|                 Core Analysis Modules                        |
|   +----------------+ +--------------+ +-----------------+   |
|   |  Document       | |  Quality     | |    Risk         |   |
|   |  Parser         | |  Scorer      | |  Predictor      |   |
|   |  - PDF/DOCX     | |  - Sections  | |  - 30 Features  |   |
|   |  - OCR          | |  - Comply    | |  - ML Models    |   |
|   |  - NLP          | |  - Report    | |  - Explain      |   |
|   |  - Tables       | |              | |  - Monte Carlo  |   |
|   +----------------+ +--------------+ +-----------------+   |
+-------------------------------------------------------------+
|              Incremental Learning Engine                     |
|   +------------------------------------------------------+  |
|   |  Auto-capture -> Synthetic augment -> Retrain models |  |
|   |  User feedback -> Ground truth -> Improve accuracy   |  |
|   +------------------------------------------------------+  |
+-------------------------------------------------------------+
|         PostgreSQL 15 + SQLAlchemy 2.0 (Async)              |
|   13 tables: documents, analyses, scores, risks,            |
|              training_data, model_versions, ...              |
+-------------------------------------------------------------+
```

---

## Key Features

### Document Intelligence
- **PDF & DOCX parsing** with pdfplumber + PyPDF2 fallback
- **Multilingual OCR** (EasyOCR) - supports Hindi, Bengali, Assamese, Manipuri, and 7+ Indian languages
- **NLP-powered section identification** - detects all 14 standard DPR sections
- **Named Entity Recognition** - organizations, locations, monetary values, dates
- **Indian currency parsing** - Rs, Crores, Lakhs
- **Table extraction & classification** - budget tables, BOQ, timelines

### Quality Scoring
- **14-section completeness check** with depth and sub-element analysis
- **5-dimensional scoring**: Completeness (25%) + Technical (20%) + Financial (20%) + Compliance (20%) + Risk (15%)
- **A+ to F grading** system
- **Government compliance validation**: Central rules, State-specific rules, MDoNER special provisions
- **Funding ratio verification** (90:10 for NE states)

### Risk Prediction
- **Cost Overrun Prediction** - XGBoost regression (R2 ~ 0.50)
- **Delay Prediction** - LightGBM regression (R2 ~ 0.34)
- **Risk Classification** - Low / Medium / High / Critical (89% accuracy)
- **30-feature engineering** from NLP analysis to ML-ready vectors
- **Monte Carlo Simulation** - 1000 iterations for probabilistic cost/delay estimates
- **Heuristic fallback** when trained models aren't available

### Incremental Learning
- **Auto-capture**: Every DPR analyzed generates a training sample automatically
- **Synthetic augmentation**: 3000 synthetic samples aligned to real feature columns
- **Smart weighting**: Real data weighted 5x over synthetic for faster learning
- **User feedback**: Submit actual outcomes (cost overrun %, delays, risk level) as ground truth
- **Model versioning**: Full history of model versions with accuracy metrics
- **One-click retrain**: Retrain all 3 models from the dashboard
- **Progressive improvement**: Models get smarter with each uploaded DPR

### Explainable AI
- **Narrative explanations** in plain English
- **Top risk drivers** with severity scoring
- **Protective factors** identification
- **Confidence analysis** with uncertainty communication
- **Actionable mitigation strategies**

---

## Project Structure

```
AI DPR/
|-- app/
|   |-- main.py                          # FastAPI application entry
|   |-- api/routes/
|   |   |-- upload.py                    # File upload endpoints
|   |   |-- analysis.py                  # NLP analysis endpoints
|   |   |-- scoring.py                   # Quality scoring endpoints
|   |   |-- risk.py                      # Risk prediction endpoints
|   |   |-- dashboard.py                 # Dashboard stats endpoints
|   |   +-- learning.py                  # Incremental learning endpoints
|   |-- models/
|   |   |-- database.py                  # Async SQLAlchemy + PostgreSQL
|   |   |-- db_models.py                 # 13 ORM models (mapped_column)
|   |   +-- schemas.py                   # Pydantic schemas
|   |-- services/
|   |   |-- db_service.py                # CRUD operations (upsert pattern)
|   |   |-- learning_service.py          # Incremental ML learning engine
|   |   +-- seed.py                      # Database seeding (states, rules)
|   +-- modules/
|       |-- document_parser/
|       |   |-- pdf_extractor.py         # PDF/DOCX extraction
|       |   |-- ocr_engine.py            # Multilingual OCR
|       |   |-- nlp_processor.py         # Core NLP analysis
|       |   +-- table_extractor.py       # Table classification
|       |-- quality_scorer/
|       |   |-- section_checker.py       # Section completeness
|       |   |-- compliance_engine.py     # Government compliance
|       |   +-- quality_report.py        # Master quality scoring
|       +-- risk_predictor/
|           |-- feature_engineer.py      # NLP -> 30 ML features
|           |-- ml_models.py             # XGBoost/LightGBM/sklearn models
|           |-- risk_analyzer.py         # Risk orchestrator
|           +-- explainability.py        # Explainable AI engine
|-- config/
|   +-- settings.py                      # Central configuration
|-- data/
|   |-- indian_states.json               # State metadata (36 states/UTs)
|   |-- dpr_templates/standard_template.json
|   +-- compliance_rules/mdoner_rules.json
|-- frontend/
|   |-- index.html                       # Dashboard UI (5 tabs)
|   |-- css/styles.css                   # Styling + animations
|   +-- js/app.js                        # Frontend logic (~750 lines)
|-- ml/
|   |-- train_models.py                  # Initial training pipeline
|   |-- models/                          # Trained .pkl models (auto-generated)
|   +-- reports/                         # Training reports (JSON)
|-- tests/
|   |-- test_core.py                     # Unit tests
|   +-- test_api.py                      # API integration tests
|-- uploads/                             # Uploaded DPR files
|-- requirements.txt
|-- Dockerfile
|-- docker-compose.yml
|-- .gitignore
|-- pytest.ini
+-- README.md
```

---

## Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 15+
- pip

### 1. Clone & Setup

```bash
git clone https://github.com/Narasimha2211/AI-DPR.git
cd AI-DPR

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### 2. Set Up PostgreSQL

```bash
# Create database
createdb ai_dpr

# Or via psql
psql -c "CREATE DATABASE ai_dpr;"
```

Update your database connection in `config/settings.py`:

```python
DATABASE_URL = "postgresql+asyncpg://your_user:your_password@localhost:5432/ai_dpr"
```

Tables are created automatically on first server start.

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Open Dashboard

Navigate to **http://localhost:8000** in your browser.

### 5. Upload & Analyze

1. Upload a DPR (PDF/DOCX) via the **Upload** tab
2. View NLP analysis, quality scores, and risk predictions
3. Check the **Model Learning** tab to see AI progress
4. Click **Retrain Models** after uploading a few DPRs
5. Submit feedback with actual outcomes to improve accuracy

---

## Docker Deployment

```bash
# Build & run (includes PostgreSQL)
docker compose up --build

# Or using Docker directly
docker build -t ai-dpr .
docker run -p 8000:8000 ai-dpr
```

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload/dpr` | Upload a DPR file (PDF/DOCX) |
| `GET`  | `/api/upload/supported-formats` | List supported file formats |
| `GET`  | `/api/upload/supported-states` | List all supported Indian states |
| `POST` | `/api/analysis/analyze` | Run full NLP analysis |
| `POST` | `/api/analysis/extract-text` | Extract raw text |
| `POST` | `/api/analysis/identify-sections` | Identify DPR sections |
| `POST` | `/api/analysis/extract-financial` | Extract financial figures |
| `POST` | `/api/scoring/quality-score` | Calculate quality score & grade |
| `POST` | `/api/scoring/compliance-check` | Run compliance validation |
| `POST` | `/api/risk/predict` | Predict risks (cost/delay/class) |
| `POST` | `/api/risk/full-analysis` | End-to-end analysis pipeline |
| `GET`  | `/api/dashboard/stats` | Get dashboard statistics |
| `GET`  | `/api/dashboard/grading-system` | Get grading system details |
| `GET`  | `/health` | Health check |

### Learning Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/learning/status` | Training data count, model version, retrain recommendation |
| `POST` | `/api/learning/retrain` | Retrain all ML models from accumulated data |
| `POST` | `/api/learning/feedback` | Submit actual outcomes as ground truth |
| `GET`  | `/api/learning/history` | Model version history with accuracy metrics |

### Learning Flow

```
Upload DPR -> Analyze -> Training sample auto-saved
                              |
              Accumulate samples (3+ recommended)
                              |
              POST /api/learning/retrain
                              |
         XGBoost/LightGBM models trained (v1, v2, ...)
                              |
              Future predictions use trained models
                              |
         POST /api/learning/feedback (optional)
              -> Submit real outcomes -> Improve accuracy
```

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test class
pytest tests/test_core.py::TestNLPProcessor -v
```

---

## MDoNER States Supported

| State | Key Challenges | Priority Sectors |
|-------|---------------|-----------------|
| Arunachal Pradesh | Extreme terrain, border area | Connectivity, hydropower |
| Assam | Flood-prone, ethnic diversity | Flood management, industry |
| Manipur | Insurgency, remote terrain | Road connectivity, healthcare |
| Meghalaya | Heavy rainfall, mining | Tourism, sustainable mining |
| Mizoram | Hilly terrain, remoteness | Agriculture, bamboo industry |
| Nagaland | Tribal areas, limited infra | Education, horticulture |
| Sikkim | Seismic zone, glacial terrain | Tourism, organic farming |
| Tripura | Border area, limited industry | IT, rubber plantation |

---

## Scoring System

### Quality Grades

| Grade | Score Range | Description |
|-------|------------|-------------|
| A+ | 90-100 | Excellent - Ready for submission |
| A  | 80-89  | Very Good - Minor improvements needed |
| B+ | 70-79  | Good - Some improvements recommended |
| B  | 60-69  | Satisfactory - Several improvements needed |
| C  | 50-59  | Below Average - Significant improvements needed |
| D  | 40-49  | Poor - Major revision required |
| F  | 0-39   | Fail - Complete revision required |

### Compliance Levels
- **HIGH** (75-100): Meets most government requirements
- **MEDIUM** (50-74): Partial compliance, improvements needed
- **LOW** (25-49): Significant compliance gaps
- **CRITICAL** (0-24): Fails basic requirements

---

## ML Model Performance

After training with real DPR data:

| Model | Algorithm | Metric | Value |
|-------|-----------|--------|-------|
| Cost Overrun | XGBoost | MAE | ~5% |
| Cost Overrun | XGBoost | R2 | ~0.50 |
| Delay | LightGBM | MAE | ~5% |
| Delay | LightGBM | R2 | ~0.34 |
| Risk Classifier | XGBoost | Accuracy | ~89% |
| Risk Classifier | XGBoost | F1 (weighted) | ~0.89 |

> Models improve as more DPRs are analyzed. The system falls back to heuristic rules when no trained models are available.

### 30 Engineered Features

The system extracts 30 features from each DPR:

- **Section features** (8): sections_found_ratio, has_executive_summary, has_technical_feasibility, has_financial_analysis, has_cost_estimates, has_risk_assessment, has_environmental_impact, has_implementation_schedule
- **Text features** (6): total_word_count, avg_section_words, min_section_words, max_section_words, vocabulary_richness, avg_sentence_length
- **Financial features** (5): total_project_cost_crores, financial_figures_count, has_contingency, has_cost_escalation, cost_per_word_ratio
- **Technical features** (2): technical_keywords_count, quantitative_data_points
- **Timeline features** (3): dates_found, has_milestones, project_duration_mentioned
- **Regional features** (3): is_mdoner_state, state_encoded, terrain_difficulty
- **Compliance features** (3): compliance_score, violations_count, warnings_count

---

## Configuration

Key settings in `config/settings.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `MAX_FILE_SIZE_MB` | 50 | Maximum upload file size |
| `SUPPORTED_FORMATS` | PDF, DOCX | Accepted document formats |
| `OCR_LANGUAGES` | 10 languages | Indian language OCR support |
| `SCORING_WEIGHTS` | 5 dimensions | Quality score weights |
| `ML_DIR` | `ml/` | ML models and reports directory |
| `MODELS_DIR` | `ml/models/` | Trained model .pkl files |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.9, uvicorn |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 (async) + asyncpg |
| NLP | spaCy, langdetect |
| OCR | EasyOCR (multilingual) |
| PDF | pdfplumber, PyPDF2 |
| ML | XGBoost, LightGBM, scikit-learn |
| XAI | SHAP, LIME |
| Frontend | Vanilla JS + Chart.js 4.4 |
| Logging | Loguru |
| Deploy | Docker, Docker Compose |

---

## Database Schema

13 PostgreSQL tables:

| Table | Purpose |
|-------|---------|
| `documents` | Uploaded DPR metadata |
| `document_analyses` | NLP analysis results |
| `quality_scores` | Quality scoring reports |
| `risk_assessments` | Risk prediction results |
| `compliance_reports` | Compliance validation |
| `indian_states` | 36 states/UTs with metadata |
| `project_types` | Project type definitions |
| `compliance_rules` | Government compliance rules |
| `activity_logs` | System activity tracking |
| `upload_sessions` | File upload sessions |
| `scoring_history` | Historical score tracking |
| `training_data` | ML training samples (auto-captured) |
| `model_versions` | ML model version history |

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Author

**Narasimha Reddy Kasarla** - [GitHub](https://github.com/Narasimha2211)
