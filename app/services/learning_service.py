# ============================================
# Incremental Learning Service
# Learns from each uploaded DPR to improve
# accuracy over time
# ============================================

import datetime
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

import numpy as np
import pandas as pd
import joblib
from loguru import logger

from config.settings import settings
from app.modules.risk_predictor.feature_engineer import FeatureEngineer

# ── Feature columns must match FeatureEngineer.FEATURE_COLUMNS ──
FEATURE_COLUMNS = FeatureEngineer.FEATURE_COLUMNS

MODELS_DIR = settings.MODELS_DIR
MODELS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = settings.ML_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# 1.  Extract a training sample from analysis
# ─────────────────────────────────────────────

def extract_training_sample(
    nlp_analysis: dict,
    quality_report: Optional[dict] = None,
    risk_report: Optional[dict] = None,
    compliance_report: Optional[dict] = None,
    state: Optional[str] = None,
    project_type: Optional[str] = None,
    project_cost: Optional[float] = None,
) -> dict:
    """
    Convert a DPR analysis into a training sample (features + labels).
    Called after every DPR analysis to accumulate training data.
    """
    fe = FeatureEngineer()
    features_df = fe.extract_features(
        nlp_analysis=nlp_analysis,
        quality_score=quality_report,
        compliance_report=compliance_report,
        state=state,
        project_cost=project_cost,
    )
    feature_dict = features_df.iloc[0].to_dict()

    # ── Labels derived from heuristic/model predictions ──
    labels = {}
    if risk_report:
        summary = risk_report.get("risk_summary", {})
        labels["cost_overrun_probability"] = summary.get("cost_overrun_probability", 50)
        labels["delay_probability"] = summary.get("delay_probability", 50)
        risk_level = summary.get("overall_risk_level", "Medium")
        risk_map = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
        labels["risk_class"] = risk_map.get(risk_level, 1)
    else:
        labels["cost_overrun_probability"] = 50
        labels["delay_probability"] = 50
        labels["risk_class"] = 1

    if quality_report:
        labels["quality_score"] = quality_report.get("composite_score", 0)

    return {
        "features": feature_dict,
        "labels": labels,
        "metadata": {
            "state": state,
            "project_type": project_type,
            "project_cost": project_cost,
        },
    }


# ─────────────────────────────────────────────
# 2.  Generate synthetic data (aligned to real
#     feature columns)
# ─────────────────────────────────────────────

def generate_aligned_synthetic_data(n_samples: int = 3000, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic data with the same columns as FeatureEngineer.
    Used to augment real data when we have few real samples.
    """
    rng = np.random.default_rng(seed)
    data: Dict[str, Any] = {}

    # Section features
    sections_found = rng.integers(3, 15, n_samples)
    data["sections_found_ratio"] = sections_found / 14.0
    data["total_word_count"] = np.clip(rng.lognormal(9, 0.8, n_samples).astype(int), 500, 100_000)
    data["avg_section_words"] = data["total_word_count"] / np.maximum(sections_found, 1)
    data["min_section_words"] = np.clip(rng.integers(0, 200, n_samples), 0, data["avg_section_words"].astype(int))
    data["max_section_words"] = data["avg_section_words"] * rng.uniform(1.5, 4.0, n_samples)

    for col in [
        "has_executive_summary", "has_technical_feasibility", "has_financial_analysis",
        "has_cost_estimates", "has_risk_assessment", "has_environmental_impact",
        "has_implementation_schedule",
    ]:
        data[col] = rng.binomial(1, 0.5 + 0.03 * sections_found, n_samples)

    # Financial
    data["total_project_cost_crores"] = np.clip(rng.lognormal(3, 1.5, n_samples), 0.5, 5000)
    data["financial_figures_count"] = rng.poisson(8, n_samples)
    data["has_contingency"] = rng.binomial(1, 0.4, n_samples)
    data["has_cost_escalation"] = rng.binomial(1, 0.35, n_samples)
    data["cost_per_word_ratio"] = data["total_project_cost_crores"] / np.maximum(data["total_word_count"], 1)

    # Technical
    data["vocabulary_richness"] = np.clip(rng.normal(0.28, 0.08, n_samples), 0.05, 0.8)
    data["avg_sentence_length"] = np.clip(rng.normal(18, 6, n_samples), 4, 60)
    data["technical_keywords_count"] = rng.integers(0, 14, n_samples)
    data["quantitative_data_points"] = rng.poisson(12, n_samples)

    # Timeline
    data["dates_found"] = rng.poisson(5, n_samples)
    data["has_milestones"] = rng.binomial(1, 0.45, n_samples)
    data["project_duration_mentioned"] = rng.binomial(1, 0.5, n_samples)

    # State/Regional
    data["is_mdoner_state"] = rng.binomial(1, 0.3, n_samples)
    data["state_encoded"] = rng.integers(1, 9, n_samples)
    data["terrain_difficulty"] = rng.choice([1, 2, 3, 4, 6, 8], n_samples, p=[0.2, 0.2, 0.15, 0.15, 0.2, 0.1])

    # Compliance
    data["compliance_score"] = np.clip(rng.normal(55, 22, n_samples), 0, 100)
    data["violations_count"] = rng.poisson(2, n_samples)
    data["warnings_count"] = rng.poisson(3, n_samples)

    df = pd.DataFrame(data)

    # ── Target labels ──
    # Cost overrun probability (0-100)
    cost_base = (
        30
        - 0.20 * df["sections_found_ratio"] * 100
        - 0.10 * df["has_financial_analysis"] * 15
        - 0.10 * df["has_contingency"] * 15
        + 0.20 * df["terrain_difficulty"] * 5
        + 0.15 * df["is_mdoner_state"] * 20
        - 0.08 * df["compliance_score"]
        + rng.normal(0, 6, n_samples)
    )
    df["cost_overrun_probability"] = np.clip(cost_base, 0, 100)

    # Delay probability (0-100)
    delay_base = (
        35
        - 0.15 * df["sections_found_ratio"] * 100
        - 0.10 * df["has_implementation_schedule"] * 20
        - 0.08 * df["has_milestones"] * 15
        + 0.15 * df["terrain_difficulty"] * 5
        + 0.10 * df["is_mdoner_state"] * 20
        - 0.05 * df["compliance_score"]
        + rng.normal(0, 6, n_samples)
    )
    df["delay_probability"] = np.clip(delay_base, 0, 100)

    # Risk class: 0=Low, 1=Medium, 2=High, 3=Critical
    risk_score = df["cost_overrun_probability"] * 0.4 + df["delay_probability"] * 0.3 + (100 - df["compliance_score"]) * 0.3
    conditions = [risk_score < 25, risk_score < 50, risk_score < 75]
    df["risk_class"] = np.select(conditions, [0, 1, 2], default=3)

    return df


# ─────────────────────────────────────────────
# 3.  Train / Retrain models from real + synthetic
# ─────────────────────────────────────────────

def retrain_models(
    training_rows: List[dict],
    synthetic_count: int = 3000,
) -> dict:
    """
    Retrain all three ML models using accumulated real DPR data
    plus synthetic augmentation.

    training_rows: list of dicts, each with 'features' and 'labels'.
    Returns: metrics and model version info.
    """
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (
        mean_absolute_error, mean_squared_error, r2_score,
        accuracy_score, f1_score,
    )

    # ── Build real data DataFrame ──
    real_records = []
    for row in training_rows:
        features = row.get("features", {})
        labels = row.get("labels", {})
        record = {**features}
        record["cost_overrun_probability"] = labels.get("cost_overrun_probability", 50)
        record["delay_probability"] = labels.get("delay_probability", 50)
        record["risk_class"] = labels.get("risk_class", 1)
        record["is_real"] = True
        real_records.append(record)

    real_df = pd.DataFrame(real_records) if real_records else pd.DataFrame()

    # ── Generate synthetic data ──
    # Reduce synthetic data as real data grows
    adjusted_synthetic = max(500, synthetic_count - len(real_records) * 10)
    synth_df = generate_aligned_synthetic_data(n_samples=adjusted_synthetic)
    synth_df["is_real"] = False

    # ── Combine with higher weight for real data ──
    if not real_df.empty:
        # Repeat real data to give it 5x weight
        real_weight = min(5, max(2, 100 // max(len(real_df), 1)))
        weighted_real = pd.concat([real_df] * real_weight, ignore_index=True)
        combined = pd.concat([weighted_real, synth_df], ignore_index=True)
        logger.info(
            f"Training data: {len(real_df)} real (×{real_weight} weight) + "
            f"{len(synth_df)} synthetic = {len(combined)} total"
        )
    else:
        combined = synth_df
        logger.info(f"Training with {len(synth_df)} synthetic samples (no real data yet)")

    # Ensure all feature columns present
    for col in FEATURE_COLUMNS:
        if col not in combined.columns:
            combined[col] = 0

    X = combined[FEATURE_COLUMNS].fillna(0)
    y_cost = combined["cost_overrun_probability"].fillna(50)
    y_delay = combined["delay_probability"].fillna(50)
    y_risk = combined["risk_class"].fillna(1).astype(int)

    results: Dict[str, Any] = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "real_samples": len(real_df),
        "synthetic_samples": len(synth_df),
        "total_training_samples": len(combined),
        "models": {},
    }

    # ── Try XGBoost, fall back to sklearn ──
    try:
        import xgboost as xgb
        # Verify XGBoost can actually create a model (catches libomp issues)
        xgb.XGBRegressor(n_estimators=1)
        has_xgb = True
    except Exception:
        has_xgb = False
        logger.info("XGBoost unavailable, falling back to sklearn")

    try:
        import lightgbm as lgb
        lgb.LGBMRegressor(n_estimators=1)
        has_lgb = True
    except Exception:
        has_lgb = False
        logger.info("LightGBM unavailable, falling back to sklearn")

    from sklearn.ensemble import (
        GradientBoostingRegressor, GradientBoostingClassifier,
        RandomForestRegressor, RandomForestClassifier,
    )

    # ──── Cost Overrun Model ────
    X_train, X_test, y_train, y_test = train_test_split(X, y_cost, test_size=0.2, random_state=42)

    if has_xgb:
        cost_model = xgb.XGBRegressor(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, random_state=42,
        )
        model_name = "XGBoost"
    else:
        cost_model = GradientBoostingRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.05, random_state=42,
        )
        model_name = "GradientBoosting"

    cost_model.fit(X_train, y_train)
    preds = np.asarray(cost_model.predict(X_test))
    cost_metrics = {
        "model": model_name,
        "mae": round(float(mean_absolute_error(y_test, preds)), 2),
        "rmse": round(float(np.sqrt(mean_squared_error(y_test, preds))), 2),
        "r2": round(float(r2_score(y_test, preds)), 4),
    }
    cost_path = MODELS_DIR / "cost_overrun_model.pkl"
    joblib.dump(cost_model, str(cost_path))
    results["models"]["cost_overrun"] = cost_metrics
    logger.info(f"✅ Cost model trained: MAE={cost_metrics['mae']}%, R²={cost_metrics['r2']}")

    # ──── Delay Model ────
    X_train, X_test, y_train, y_test = train_test_split(X, y_delay, test_size=0.2, random_state=42)

    if has_lgb:
        delay_model = lgb.LGBMRegressor(
            n_estimators=300, max_depth=6, learning_rate=0.05, random_state=42, verbose=-1,
        )
        model_name = "LightGBM"
    elif has_xgb:
        delay_model = xgb.XGBRegressor(
            n_estimators=300, max_depth=6, learning_rate=0.05, random_state=42,
        )
        model_name = "XGBoost"
    else:
        delay_model = GradientBoostingRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.05, random_state=42,
        )
        model_name = "GradientBoosting"

    delay_model.fit(X_train, y_train)
    preds = np.asarray(delay_model.predict(X_test))
    delay_metrics = {
        "model": model_name,
        "mae": round(float(mean_absolute_error(y_test, preds)), 2),
        "rmse": round(float(np.sqrt(mean_squared_error(y_test, preds))), 2),
        "r2": round(float(r2_score(y_test, preds)), 4),
    }
    delay_path = MODELS_DIR / "delay_model.pkl"
    joblib.dump(delay_model, str(delay_path))
    results["models"]["delay"] = delay_metrics
    logger.info(f"✅ Delay model trained: MAE={delay_metrics['mae']}%, R²={delay_metrics['r2']}")

    # ──── Risk Classifier ────
    X_train, X_test, y_train, y_test = train_test_split(X, y_risk, test_size=0.2, random_state=42)

    if has_xgb:
        risk_clf = xgb.XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            num_class=4, random_state=42, eval_metric="mlogloss",
        )
        model_name = "XGBoost"
    else:
        risk_clf = GradientBoostingClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.05, random_state=42,
        )
        model_name = "GradientBoosting"

    risk_clf.fit(X_train, y_train)
    preds = np.asarray(risk_clf.predict(X_test))
    risk_metrics = {
        "model": model_name,
        "accuracy": round(float(accuracy_score(y_test, preds)), 4),
        "f1_weighted": round(float(f1_score(y_test, preds, average="weighted")), 4),
    }
    risk_path = MODELS_DIR / "risk_classifier.pkl"
    joblib.dump(risk_clf, str(risk_path))
    results["models"]["risk_classifier"] = risk_metrics
    logger.info(f"✅ Risk classifier trained: Acc={risk_metrics['accuracy']}, F1={risk_metrics['f1_weighted']}")

    # ── Feature importance ──
    importance_dict = {}
    for model, name in [(cost_model, "cost"), (delay_model, "delay"), (risk_clf, "risk")]:
        try:
            imps = model.feature_importances_
            ranked = sorted(zip(FEATURE_COLUMNS, imps.tolist()), key=lambda x: x[1], reverse=True)
            importance_dict[name] = [{"feature": f, "importance": round(v, 4)} for f, v in ranked[:10]]
        except Exception:
            pass

    results["feature_importance"] = importance_dict

    # ── Save training report ──
    report_path = REPORTS_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"📝 Training report saved: {report_path}")
    return results


# ─────────────────────────────────────────────
# 4.  Get learning statistics
# ─────────────────────────────────────────────

def get_model_files_info() -> dict:
    """Check which trained model files exist and their metadata."""
    models = {}
    for name, fname in [
        ("cost_overrun", "cost_overrun_model.pkl"),
        ("delay", "delay_model.pkl"),
        ("risk_classifier", "risk_classifier.pkl"),
    ]:
        path = MODELS_DIR / fname
        if path.exists():
            stat = path.stat()
            models[name] = {
                "exists": True,
                "path": str(path),
                "size_kb": round(stat.st_size / 1024, 1),
                "last_modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        else:
            models[name] = {"exists": False}

    # Load training report if exists
    report_path = REPORTS_DIR / "training_report.json"
    training_report = None
    if report_path.exists():
        with open(report_path) as f:
            training_report = json.load(f)

    return {
        "models": models,
        "training_report": training_report,
        "models_dir": str(MODELS_DIR),
    }
