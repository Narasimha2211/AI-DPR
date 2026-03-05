# 🇮🇳 AI DPR Analysis System

> **AI-powered Detailed Project Report (DPR) analyzer for MDoNER states of India — SIH 2026**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Overview

The **AI DPR Analysis System** is an end-to-end intelligent platform that automates the evaluation of government Detailed Project Reports (DPRs), with a focus on **MDoNER (Ministry of Development of North Eastern Region)** states. Built for **Smart India Hackathon (SIH) 2026**, it combines:

- 🧠 **NLP Document Intelligence** — Section identification, entity extraction, financial figure parsing
- ⭐ **Quality & Compliance Scoring** — 14-section completeness check + Central/State/MDoNER rule validation
- 🎯 **ML Risk Prediction** — XGBoost/LightGBM models for cost overrun, delay, and risk classification
- 🔍 **Explainable AI** — SHAP/LIME-inspired narrative explanations + Monte Carlo simulations
- 🌐 **Interactive Dashboard** — Real-time visualization with Chart.js

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│                  Frontend Dashboard                     │
│         (HTML/CSS/JS + Chart.js)                       │
├────────────────────────────────────────────────────────┤
│                   FastAPI Backend                       │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │  Upload   │  │ Analysis │  │ Dashboard │           │
│   │  Routes   │  │  Routes  │  │  Routes   │           │
│   └──────────┘  └──────────┘  └──────────┘           │
├────────────────────────────────────────────────────────┤
│              Core Analysis Modules                      │
│   ┌──────────────┐ ┌─────────────┐ ┌──────────────┐  │
│   │  Document     │ │  Quality    │ │    Risk      │  │
│   │  Parser       │ │  Scorer     │ │  Predictor   │  │
│   │  ─ PDF/DOCX   │ │  ─ Sections │ │  ─ Features  │  │
│   │  ─ OCR        │ │  ─ Comply   │ │  ─ ML Models │  │
│   │  ─ NLP        │ │  ─ Report   │ │  ─ Explain   │  │
│   │  ─ Tables     │ │             │ │  ─ Monte C.  │  │
│   └──────────────┘ └─────────────┘ └──────────────┘  │
├────────────────────────────────────────────────────────┤
│              SQLite + SQLAlchemy (Async)                │
└────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features

### 📄 Document Intelligence
- **PDF & DOCX parsing** with pdfplumber + PyPDF2 fallback
- **Multilingual OCR** (EasyOCR) — supports Hindi, Bengali, Assamese, Manipuri, and 7+ Indian languages
- **NLP-powered section identification** — detects all 14 standard DPR sections
- **Named Entity Recognition** — organizations, locations, monetary values, dates
- **Indian currency parsing** — ₹, Rs, Crores, Lakhs
- **Table extraction & classification** — budget tables, BOQ, timelines

### ⭐ Quality Scoring
- **14-section completeness check** with depth and sub-element analysis
- **5-dimensional scoring**: Completeness (25%) + Technical (20%) + Financial (20%) + Compliance (20%) + Risk (15%)
- **A+ to F grading** system
- **Government compliance validation**: Central rules, State-specific rules, MDoNER special provisions
- **Funding ratio verification** (90:10 for NE states)

### 🎯 Risk Prediction
- **Cost Overrun Prediction** — XGBoost regression
- **Delay Prediction** — LightGBM regression
- **Risk Classification** — LOW / MEDIUM / HIGH / CRITICAL
- **29-feature engineering** from NLP analysis → ML-ready vectors
- **Monte Carlo Simulation** — 1000 iterations for probabilistic cost/delay estimates
- **Heuristic fallback** when trained models aren't available

### 🔍 Explainable AI
- **Narrative explanations** in plain English
- **Top risk drivers** with severity scoring
- **Protective factors** identification
- **Confidence analysis** with uncertainty communication
- **Actionable mitigation strategies**

---

## 🗂️ Project Structure

```
AI DPR/
├── app/
│   ├── main.py                          # FastAPI application entry
│   ├── api/routes/
│   │   ├── upload.py                    # File upload endpoints
│   │   ├── analysis.py                  # NLP analysis endpoints
│   │   ├── scoring.py                   # Quality scoring endpoints
│   │   ├── risk.py                      # Risk prediction endpoints
│   │   └── dashboard.py                 # Dashboard stats endpoints
│   ├── models/
│   │   ├── database.py                  # Async SQLAlchemy setup
│   │   ├── db_models.py                 # ORM models
│   │   └── schemas.py                   # Pydantic schemas
│   └── modules/
│       ├── document_parser/
│       │   ├── pdf_extractor.py         # PDF/DOCX extraction
│       │   ├── ocr_engine.py            # Multilingual OCR
│       │   ├── nlp_processor.py         # Core NLP analysis
│       │   └── table_extractor.py       # Table classification
│       ├── quality_scorer/
│       │   ├── section_checker.py       # Section completeness
│       │   ├── compliance_engine.py     # Government compliance
│       │   └── quality_report.py        # Master quality scoring
│       └── risk_predictor/
│           ├── feature_engineer.py      # NLP → ML features
│           ├── ml_models.py             # XGBoost/LightGBM models
│           ├── risk_analyzer.py         # Risk orchestrator
│           └── explainability.py        # Explainable AI engine
├── config/
│   └── settings.py                      # Central configuration
├── data/
│   ├── indian_states.json               # State metadata
│   ├── dpr_templates/standard_template.json
│   └── compliance_rules/mdoner_rules.json
├── frontend/
│   ├── index.html                       # Dashboard UI
│   ├── css/styles.css                   # Styling
│   └── js/app.js                        # Frontend logic
├── ml/
│   ├── train_models.py                  # Training pipeline
│   ├── trained_models/                  # Saved .joblib models
│   └── reports/                         # Training reports
├── tests/
│   ├── test_core.py                     # Unit tests
│   └── test_api.py                      # API integration tests
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── pytest.ini
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- pip

### 1. Clone & Setup

```bash
cd "AI DPR"

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Copy env config
cp .env.example .env
```

### 2. Train ML Models (Optional)

```bash
python ml/train_models.py
```

This generates synthetic data and trains XGBoost/LightGBM models. The system works without trained models using built-in heuristic fallbacks.

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Open Dashboard

Navigate to **http://localhost:8000** in your browser.

---

## 🐳 Docker Deployment

```bash
# Build & run
docker compose up --build

# Or using Docker directly
docker build -t ai-dpr .
docker run -p 8000:8000 ai-dpr
```

---

## 📡 API Reference

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

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test class
pytest tests/test_core.py::TestNLPProcessor -v
```

---

## 🏔️ MDoNER States Supported

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

## 📊 Scoring System

### Quality Grades

| Grade | Score Range | Description |
|-------|------------|-------------|
| A+ | 90-100 | 🟢 Excellent — Ready for submission |
| A  | 80-89  | 🟢 Very Good — Minor improvements needed |
| B+ | 70-79  | 🔵 Good — Some improvements recommended |
| B  | 60-69  | 🔵 Satisfactory — Several improvements needed |
| C  | 50-59  | 🟡 Below Average — Significant improvements needed |
| D  | 40-49  | 🟠 Poor — Major revision required |
| F  | 0-39   | 🔴 Fail — Complete revision required |

### Compliance Levels
- **HIGH** (75-100): Meets most government requirements
- **MEDIUM** (50-74): Partial compliance, improvements needed
- **LOW** (25-49): Significant compliance gaps
- **CRITICAL** (0-24): Fails basic requirements

---

## 🔧 Configuration

Key settings in `config/settings.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_FILE_SIZE_MB` | 50 | Maximum upload file size |
| `SUPPORTED_FORMATS` | PDF, DOCX | Accepted document formats |
| `OCR_LANGUAGES` | 10 languages | Indian language OCR support |
| `SCORING_WEIGHTS` | 5 dimensions | Quality score weights |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11 |
| NLP | spaCy, langdetect |
| OCR | EasyOCR (multilingual) |
| PDF | pdfplumber, PyPDF2 |
| ML | XGBoost, LightGBM, scikit-learn |
| XAI | SHAP, LIME |
| Database | SQLAlchemy (async) + SQLite |
| Frontend | Vanilla JS + Chart.js |
| Deploy | Docker, Docker Compose |

---

## 📝 License


---

