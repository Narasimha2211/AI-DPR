# ============================================
# ML Models for DPR Risk Prediction
# Cost Overrun & Delay Prediction
# ============================================

import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import joblib
from loguru import logger

from config.settings import settings


class RiskMLModels:
    """
    Machine Learning models for project risk prediction:

    1. Cost Overrun Predictor - Predicts probability of cost exceeding estimates
    2. Delay Predictor - Predicts probability of project delay
    3. Overall Risk Classifier - Classifies project risk level (Low/Medium/High/Critical)

    Models: XGBoost (primary), LightGBM (secondary), RandomForest (baseline)
    """

    def __init__(self):
        self.cost_model = None
        self.delay_model = None
        self.risk_classifier = None
        self.models_dir = settings.MODELS_DIR
        logger.info("RiskMLModels initialized")

    def load_models(self) -> bool:
        """Load pre-trained models from disk."""
        try:
            cost_path = self.models_dir / "cost_overrun_model.pkl"
            delay_path = self.models_dir / "delay_model.pkl"
            risk_path = self.models_dir / "risk_classifier.pkl"

            if cost_path.exists():
                self.cost_model = joblib.load(str(cost_path))
                logger.info("Cost overrun model loaded")

            if delay_path.exists():
                self.delay_model = joblib.load(str(delay_path))
                logger.info("Delay prediction model loaded")

            if risk_path.exists():
                self.risk_classifier = joblib.load(str(risk_path))
                logger.info("Risk classifier loaded")

            return True
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            return False

    def predict_cost_overrun(self, features: pd.DataFrame) -> dict:
        """
        Predict probability of cost overrun.

        Returns:
            dict with probability, risk level, and contributing factors
        """
        if self.cost_model is not None:
            try:
                prob = self.cost_model.predict_proba(features)[0]
                predicted_class = self.cost_model.predict(features)[0]

                return {
                    "probability": round(float(prob[1]) * 100, 2),
                    "prediction": "Cost Overrun Likely" if predicted_class == 1 else "Within Budget",
                    "confidence": round(float(max(prob)) * 100, 2),
                    "model_used": "trained_model"
                }
            except Exception as e:
                logger.warning(f"Model prediction failed, using heuristic: {e}")

        # Heuristic-based prediction when model is not available
        return self._heuristic_cost_prediction(features)

    def predict_delay(self, features: pd.DataFrame) -> dict:
        """
        Predict probability of project delay.
        """
        if self.delay_model is not None:
            try:
                prob = self.delay_model.predict_proba(features)[0]
                predicted_class = self.delay_model.predict(features)[0]

                return {
                    "probability": round(float(prob[1]) * 100, 2),
                    "prediction": "Delay Likely" if predicted_class == 1 else "On Schedule",
                    "confidence": round(float(max(prob)) * 100, 2),
                    "model_used": "trained_model"
                }
            except Exception as e:
                logger.warning(f"Delay model failed, using heuristic: {e}")

        return self._heuristic_delay_prediction(features)

    def classify_risk(self, features: pd.DataFrame) -> dict:
        """
        Classify overall project risk level.
        """
        if self.risk_classifier is not None:
            try:
                prediction = self.risk_classifier.predict(features)[0]
                prob = self.risk_classifier.predict_proba(features)[0]
                risk_levels = ["Low", "Medium", "High", "Critical"]
                probabilities = {
                    level: round(float(p) * 100, 2)
                    for level, p in zip(risk_levels, prob)
                }

                return {
                    "risk_level": risk_levels[prediction],
                    "probabilities": probabilities,
                    "confidence": round(float(max(prob)) * 100, 2),
                    "model_used": "trained_model"
                }
            except Exception as e:
                logger.warning(f"Risk classifier failed, using heuristic: {e}")

        return self._heuristic_risk_classification(features)

    def _heuristic_cost_prediction(self, features: pd.DataFrame) -> dict:
        """
        Rule-based cost overrun prediction when ML model unavailable.
        Based on research from Indian government project data.
        """
        row = features.iloc[0]
        risk_score = 0

        # Section completeness effect
        if row.get("sections_found_ratio", 0) < 0.6:
            risk_score += 20
        elif row.get("sections_found_ratio", 0) < 0.8:
            risk_score += 10

        # Financial analysis quality
        if not row.get("has_financial_analysis", 0):
            risk_score += 15
        if not row.get("has_cost_estimates", 0):
            risk_score += 15
        if not row.get("has_contingency", 0):
            risk_score += 10
        if not row.get("has_cost_escalation", 0):
            risk_score += 10

        # Project size risk (larger = more risk)
        cost = row.get("total_project_cost_crores", 0)
        if cost > 500:
            risk_score += 15
        elif cost > 100:
            risk_score += 10
        elif cost > 50:
            risk_score += 5

        # State/terrain risk
        if row.get("is_mdoner_state", 0):
            risk_score += 10
        terrain = row.get("terrain_difficulty", 3)
        if terrain >= 6:
            risk_score += 10
        elif terrain >= 4:
            risk_score += 5

        # Compliance issues
        if row.get("violations_count", 0) > 3:
            risk_score += 10

        probability = min(risk_score, 95)

        return {
            "probability": probability,
            "prediction": "Cost Overrun Likely" if probability > 50 else "Within Budget",
            "confidence": 65,  # Lower confidence for heuristic
            "model_used": "heuristic_rules",
            "risk_factors": self._get_cost_risk_factors(row)
        }

    def _heuristic_delay_prediction(self, features: pd.DataFrame) -> dict:
        """Rule-based delay prediction."""
        row = features.iloc[0]
        risk_score = 0

        # Schedule-related
        if not row.get("has_implementation_schedule", 0):
            risk_score += 20
        if not row.get("has_milestones", 0):
            risk_score += 10
        if row.get("dates_found", 0) < 3:
            risk_score += 10

        # DPR quality
        if row.get("sections_found_ratio", 0) < 0.7:
            risk_score += 15
        if row.get("total_word_count", 0) < 3000:
            risk_score += 10

        # Regional/terrain
        if row.get("is_mdoner_state", 0):
            risk_score += 15  # NE states have higher delay risk
        terrain = row.get("terrain_difficulty", 3)
        if terrain >= 6:
            risk_score += 15

        # Risk assessment quality
        if not row.get("has_risk_assessment", 0):
            risk_score += 10

        probability = min(risk_score, 95)

        return {
            "probability": probability,
            "prediction": "Delay Likely" if probability > 50 else "On Schedule",
            "confidence": 65,
            "model_used": "heuristic_rules",
            "risk_factors": self._get_delay_risk_factors(row)
        }

    def _heuristic_risk_classification(self, features: pd.DataFrame) -> dict:
        """Rule-based overall risk classification."""
        cost_pred = self._heuristic_cost_prediction(features)
        delay_pred = self._heuristic_delay_prediction(features)

        avg_risk = (cost_pred["probability"] + delay_pred["probability"]) / 2

        if avg_risk >= 70:
            level = "Critical"
        elif avg_risk >= 50:
            level = "High"
        elif avg_risk >= 30:
            level = "Medium"
        else:
            level = "Low"

        return {
            "risk_level": level,
            "probabilities": {
                "Low": max(0, 100 - avg_risk * 1.5),
                "Medium": 30 if 30 <= avg_risk < 50 else 15,
                "High": 30 if 50 <= avg_risk < 70 else 15,
                "Critical": avg_risk if avg_risk >= 70 else 10
            },
            "confidence": 65,
            "model_used": "heuristic_rules"
        }

    def _get_cost_risk_factors(self, row) -> list:
        """Identify key cost overrun risk factors."""
        factors = []
        if not row.get("has_contingency", 0):
            factors.append({"factor": "No contingency provisions", "impact": "High"})
        if not row.get("has_cost_escalation", 0):
            factors.append({"factor": "No cost escalation clause", "impact": "High"})
        if not row.get("has_financial_analysis", 0):
            factors.append({"factor": "Missing financial analysis", "impact": "Critical"})
        if row.get("terrain_difficulty", 0) >= 6:
            factors.append({"factor": "Difficult terrain increases costs", "impact": "Medium"})
        if row.get("total_project_cost_crores", 0) > 100:
            factors.append({"factor": "Large project scale", "impact": "Medium"})
        if row.get("is_mdoner_state", 0):
            factors.append({"factor": "NE region logistics challenges", "impact": "Medium"})
        return factors

    def _get_delay_risk_factors(self, row) -> list:
        """Identify key delay risk factors."""
        factors = []
        if not row.get("has_implementation_schedule", 0):
            factors.append({"factor": "No implementation schedule", "impact": "Critical"})
        if not row.get("has_milestones", 0):
            factors.append({"factor": "No milestones defined", "impact": "High"})
        if not row.get("has_risk_assessment", 0):
            factors.append({"factor": "No risk assessment", "impact": "High"})
        if row.get("terrain_difficulty", 0) >= 6:
            factors.append({"factor": "Hilly/mountainous terrain", "impact": "High"})
        if row.get("is_mdoner_state", 0):
            factors.append({"factor": "NE region monsoon/access issues", "impact": "High"})
        if row.get("sections_found_ratio", 0) < 0.7:
            factors.append({"factor": "Incomplete DPR increases uncertainty", "impact": "Medium"})
        return factors

    def save_models(self, cost_model=None, delay_model=None, risk_classifier=None):
        """Save trained models to disk."""
        self.models_dir.mkdir(parents=True, exist_ok=True)

        if cost_model:
            joblib.dump(cost_model, str(self.models_dir / "cost_overrun_model.pkl"))
            logger.info("Cost overrun model saved")

        if delay_model:
            joblib.dump(delay_model, str(self.models_dir / "delay_model.pkl"))
            logger.info("Delay model saved")

        if risk_classifier:
            joblib.dump(risk_classifier, str(self.models_dir / "risk_classifier.pkl"))
            logger.info("Risk classifier saved")
