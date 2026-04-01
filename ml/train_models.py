"""
AI DPR - ML Model Training Script
Generates synthetic DPR data and trains XGBoost/LightGBM models for:
  1. Cost overrun prediction (regression)
  2. Delay prediction (regression)
  3. Risk classification (classification)
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, classification_report, f1_score
)
from sklearn.preprocessing import LabelEncoder

try:
    import xgboost as xgb
except ImportError:
    xgb = None

try:
    import lightgbm as lgb
except ImportError:
    lgb = None


# ---- Paths ----
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "ml" / "trained_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = BASE_DIR / "ml" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ---- Feature columns matching feature_engineer.py ----
FEATURE_COLUMNS = [
    "sections_found", "sections_missing", "completeness_ratio",
    "total_word_count", "avg_section_words", "has_executive_summary",
    "has_financial_analysis", "has_cost_estimates", "has_risk_assessment",
    "has_implementation_schedule", "has_environmental_impact",
    "financial_figures_count", "has_budget_table", "has_boq_table",
    "total_entities", "org_entities", "location_entities",
    "technical_depth_score", "readability_score",
    "timeline_months", "has_milestones",
    "state_risk_factor", "terrain_difficulty",
    "is_mdoner_state", "compliance_score",
    "project_cost_crores", "cost_per_word",
    "has_monitoring_evaluation", "has_sustainability"
]


# =============================================================
# Synthetic Data Generation
# =============================================================
def generate_synthetic_data(n_samples: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Generate realistic synthetic DPR feature data with labels."""
    np.random.seed(seed)

    data = {}

    # Section features
    data["sections_found"] = np.random.randint(4, 15, n_samples)
    data["sections_missing"] = 14 - data["sections_found"]
    data["completeness_ratio"] = data["sections_found"] / 14.0

    # Text features
    data["total_word_count"] = np.random.lognormal(9, 0.8, n_samples).astype(int)
    data["total_word_count"] = np.clip(data["total_word_count"], 500, 100000)
    data["avg_section_words"] = data["total_word_count"] / np.maximum(data["sections_found"], 1)

    # Boolean section flags
    for col in ["has_executive_summary", "has_financial_analysis", "has_cost_estimates",
                "has_risk_assessment", "has_implementation_schedule",
                "has_environmental_impact", "has_monitoring_evaluation", "has_sustainability"]:
        data[col] = np.random.binomial(1, 0.6 + 0.03 * data["sections_found"], n_samples)

    # Financial
    data["financial_figures_count"] = np.random.poisson(8, n_samples)
    data["has_budget_table"] = np.random.binomial(1, 0.5, n_samples)
    data["has_boq_table"] = np.random.binomial(1, 0.35, n_samples)

    # Entity features
    data["total_entities"] = np.random.poisson(30, n_samples)
    data["org_entities"] = np.random.poisson(8, n_samples)
    data["location_entities"] = np.random.poisson(5, n_samples)

    # Quality features
    data["technical_depth_score"] = np.clip(np.random.normal(55, 20, n_samples), 0, 100)
    data["readability_score"] = np.clip(np.random.normal(60, 15, n_samples), 0, 100)

    # Timeline
    data["timeline_months"] = np.random.choice([0, 6, 12, 18, 24, 36, 48, 60], n_samples,
                                               p=[0.15, 0.05, 0.15, 0.15, 0.2, 0.15, 0.1, 0.05])
    data["has_milestones"] = np.random.binomial(1, 0.45, n_samples)

    # State & terrain
    data["state_risk_factor"] = np.random.choice([0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9], n_samples)
    data["terrain_difficulty"] = np.random.choice([0.3, 0.5, 0.7, 0.9], n_samples,
                                                   p=[0.3, 0.3, 0.25, 0.15])
    data["is_mdoner_state"] = np.random.binomial(1, 0.35, n_samples)

    # Compliance
    data["compliance_score"] = np.clip(np.random.normal(60, 25, n_samples), 0, 100)

    # Cost
    data["project_cost_crores"] = np.random.lognormal(3, 1.5, n_samples)
    data["project_cost_crores"] = np.clip(data["project_cost_crores"], 0.5, 5000)
    data["cost_per_word"] = data["project_cost_crores"] * 1e7 / np.maximum(data["total_word_count"], 1)

    df = pd.DataFrame(data)

    # ---- Generate target labels ----

    # Cost overrun %  (0 - 100)
    cost_base = (
        30
        - 0.2 * df["completeness_ratio"] * 100
        - 0.15 * df["technical_depth_score"]
        + 0.25 * df["state_risk_factor"] * 100
        + 0.20 * df["terrain_difficulty"] * 100
        - 0.10 * df["compliance_score"]
        + 0.10 * df["is_mdoner_state"] * 20
        - 0.05 * df["has_budget_table"] * 20
        + np.random.normal(0, 8, n_samples)
    )
    df["cost_overrun_pct"] = np.clip(cost_base, 0, 100)

    # Delay months (0 - 36)
    delay_base = (
        12
        - 0.08 * df["completeness_ratio"] * 100
        - 0.05 * df["has_implementation_schedule"] * 15
        + 0.10 * df["terrain_difficulty"] * 20
        + 0.08 * df["state_risk_factor"] * 15
        - 0.04 * df["has_milestones"] * 10
        + np.random.normal(0, 3, n_samples)
    )
    df["delay_months"] = np.clip(delay_base, 0, 36)

    # Risk class: LOW / MEDIUM / HIGH / CRITICAL
    risk_score = (
        df["cost_overrun_pct"] * 0.4
        + (df["delay_months"] / 36 * 100) * 0.3
        + (1 - df["compliance_score"] / 100) * 100 * 0.3
    )
    conditions = [risk_score < 25, risk_score < 50, risk_score < 75]
    choices = [0, 1, 2]
    df["risk_class"] = np.select(conditions, choices, default=3)
    # 0=LOW, 1=MEDIUM, 2=HIGH, 3=CRITICAL

    return df


# =============================================================
# Model Training
# =============================================================
def train_cost_model(df: pd.DataFrame) -> dict:
    """Train cost overrun regression model."""
    X = df[FEATURE_COLUMNS]
    y = df["cost_overrun_pct"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results = {}

    if xgb is not None:
        model = xgb.XGBRegressor(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            objective="reg:squarederror", random_state=42
        )
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

        preds = np.asarray(model.predict(X_test))
        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)

        path = MODEL_DIR / "cost_overrun_model.joblib"
        joblib.dump(model, path)

        results["xgb_cost"] = {"mae": mae, "rmse": rmse, "r2": r2, "path": str(path)}
        print(f"  ✅ Cost Model — MAE: {mae:.2f}%, RMSE: {rmse:.2f}%, R²: {r2:.3f}")
    else:
        print("  ⚠️ XGBoost not installed — skipping cost model")

    return results


def train_delay_model(df: pd.DataFrame) -> dict:
    """Train delay prediction regression model."""
    X = df[FEATURE_COLUMNS]
    y = df["delay_months"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results = {}

    if lgb is not None:
        model = lgb.LGBMRegressor(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            objective="regression", random_state=42, verbose=-1
        )
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)])

        preds = np.asarray(model.predict(X_test))
        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)

        path = MODEL_DIR / "delay_model.joblib"
        joblib.dump(model, path)

        results["lgb_delay"] = {"mae": mae, "rmse": rmse, "r2": r2, "path": str(path)}
        print(f"  ✅ Delay Model — MAE: {mae:.2f} mo, RMSE: {rmse:.2f} mo, R²: {r2:.3f}")
    elif xgb is not None:
        model = xgb.XGBRegressor(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            objective="reg:squarederror", random_state=42
        )
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

        preds = np.asarray(model.predict(X_test))
        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)

        path = MODEL_DIR / "delay_model.joblib"
        joblib.dump(model, path)

        results["xgb_delay"] = {"mae": mae, "rmse": rmse, "r2": r2, "path": str(path)}
        print(f"  ✅ Delay Model (XGB fallback) — MAE: {mae:.2f} mo, RMSE: {rmse:.2f} mo, R²: {r2:.3f}")
    else:
        print("  ⚠️ Neither LightGBM nor XGBoost installed — skipping delay model")

    return results


def train_risk_classifier(df: pd.DataFrame) -> dict:
    """Train risk classification model."""
    X = df[FEATURE_COLUMNS]
    y = df["risk_class"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results = {}

    if xgb is not None:
        model = xgb.XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            objective="multi:softprob", num_class=4,
            random_state=42, eval_metric="mlogloss"
        )
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

        preds = np.asarray(model.predict(X_test))
        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds, average="weighted")
        labels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        report = classification_report(y_test, preds, target_names=labels, output_dict=True)

        path = MODEL_DIR / "risk_classifier.joblib"
        joblib.dump(model, path)

        results["xgb_risk"] = {"accuracy": acc, "f1_weighted": f1, "report": report, "path": str(path)}
        print(f"  ✅ Risk Classifier — Acc: {acc:.3f}, F1: {f1:.3f}")
    else:
        print("  ⚠️ XGBoost not installed — skipping risk classifier")

    return results


# =============================================================
# Feature Importance
# =============================================================
def extract_feature_importance(model_path: str, model_type: str) -> dict:
    """Extract and rank feature importances."""
    model = joblib.load(model_path)
    importances = model.feature_importances_
    importance_dict = dict(zip(FEATURE_COLUMNS, importances.tolist()))
    sorted_imp = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
    return {
        "model": model_type,
        "top_features": [{"feature": f, "importance": round(v, 4)} for f, v in sorted_imp[:10]],
        "all_features": {f: round(v, 4) for f, v in sorted_imp}
    }


# =============================================================
# Main
# =============================================================
def main():
    print("=" * 60)
    print("  AI DPR — ML Model Training Pipeline")
    print("=" * 60)
    print(f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 Models will be saved to: {MODEL_DIR}\n")

    # Generate data
    print("📊 Generating synthetic DPR data (5000 samples)...")
    df = generate_synthetic_data(5000)
    print(f"   Shape: {df.shape}")
    print(f"   Features: {len(FEATURE_COLUMNS)}")
    print(f"   Targets: cost_overrun_pct, delay_months, risk_class\n")

    all_results = {}

    # Train models
    print("🔧 Training Cost Overrun Model (XGBoost)...")
    all_results.update(train_cost_model(df))

    print("\n🔧 Training Delay Prediction Model (LightGBM)...")
    all_results.update(train_delay_model(df))

    print("\n🔧 Training Risk Classifier (XGBoost)...")
    all_results.update(train_risk_classifier(df))

    # Feature importance
    print("\n📈 Extracting Feature Importances...")
    importances = {}
    for key, res in all_results.items():
        if "path" in res:
            imp = extract_feature_importance(res["path"], key)
            importances[key] = imp
            print(f"  {key} top-3: {', '.join(f['feature'] for f in imp['top_features'][:3])}")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "n_samples": 5000,
        "features": FEATURE_COLUMNS,
        "model_results": {k: {kk: vv for kk, vv in v.items() if kk != "report"} for k, v in all_results.items()},
        "feature_importances": importances
    }

    report_path = REPORT_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n📝 Training report saved: {report_path}")
    print(f"\n{'=' * 60}")
    print("  ✅ Training complete!")
    print(f"{'=' * 60}")

    # Save synthetic data for reference
    data_path = REPORT_DIR / "synthetic_data_sample.csv"
    df.head(100).to_csv(data_path, index=False)
    print(f"📂 Sample data saved: {data_path}")


if __name__ == "__main__":
    main()
