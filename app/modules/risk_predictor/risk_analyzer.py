# ============================================
# Risk Analysis Orchestrator
# Combines ML predictions with DPR analysis
# ============================================

from typing import Optional

import pandas as pd
from loguru import logger

from config.settings import settings
from app.modules.risk_predictor.feature_engineer import FeatureEngineer
from app.modules.risk_predictor.ml_models import RiskMLModels


class RiskAnalyzer:
    """
    Master risk analysis engine that:
    1. Engineers features from DPR analysis
    2. Runs ML predictions
    3. Provides explainable AI insights
    4. Generates risk mitigation recommendations
    """

    # Risk mitigation strategy database
    MITIGATION_STRATEGIES = {
        "no_contingency": {
            "risk": "No contingency budget",
            "recommendation": "Include 5-10% contingency provision as per government norms",
            "impact": "Reduces cost overrun risk by 20-30%"
        },
        "no_escalation": {
            "risk": "No cost escalation clause",
            "recommendation": "Add 5-7% annual cost escalation factor for multi-year projects",
            "impact": "Protects against inflation-driven cost increases"
        },
        "missing_risk_assessment": {
            "risk": "No formal risk assessment",
            "recommendation": "Add comprehensive risk register with probability-impact matrix",
            "impact": "Reduces overall project failure probability by 25%"
        },
        "no_schedule": {
            "risk": "Missing implementation schedule",
            "recommendation": "Create detailed Gantt chart with milestones and critical path",
            "impact": "Reduces delay probability by 30-40%"
        },
        "terrain_risk": {
            "risk": "Difficult terrain/geography",
            "recommendation": "Include geological survey and terrain-specific engineering solutions",
            "impact": "Mitigates terrain-related cost and delay risks"
        },
        "ne_region": {
            "risk": "North Eastern region challenges",
            "recommendation": "Account for monsoon seasons, limited road access, and material logistics",
            "impact": "Addresses region-specific supply chain and weather risks"
        },
        "low_dpr_quality": {
            "risk": "Incomplete or low-quality DPR",
            "recommendation": "Address all missing sections and add detailed technical specifications",
            "impact": "Comprehensive DPR reduces project risk by 35-45%"
        },
        "environmental_gaps": {
            "risk": "Incomplete environmental assessment",
            "recommendation": "Conduct full EIA and obtain necessary environmental clearances",
            "impact": "Prevents regulatory delays and project stoppages"
        }
    }

    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.ml_models = RiskMLModels()

        # Try to load pre-trained models
        self.ml_models.load_models()

        logger.info("RiskAnalyzer initialized")

    def analyze_risk(
        self,
        nlp_analysis: dict,
        quality_score: Optional[dict] = None,
        compliance_report: Optional[dict] = None,
        state: Optional[str] = None,
        project_type: Optional[str] = None,
        project_cost: Optional[float] = None
    ) -> dict:
        """
        Comprehensive risk analysis for a DPR.

        Returns:
            Complete risk assessment with predictions, explanations,
            and mitigation recommendations
        """
        logger.info(f"Starting risk analysis for {state} ({project_type})")

        # Step 1: Engineer features
        features = self.feature_engineer.extract_features(
            nlp_analysis=nlp_analysis,
            quality_score=quality_score,
            compliance_report=compliance_report,
            state=state,
            project_cost=project_cost
        )

        # Step 2: Run predictions
        cost_prediction = self.ml_models.predict_cost_overrun(features)
        delay_prediction = self.ml_models.predict_delay(features)
        risk_classification = self.ml_models.classify_risk(features)

        # Step 3: No longer generating explainability explanations
        explanation = {}

        # Step 4: Generate mitigation strategies
        mitigation = self._generate_mitigation_strategies(
            features, cost_prediction, delay_prediction, state
        )

        # Step 5: Monte Carlo simulation for cost/delay ranges
        monte_carlo = self._run_monte_carlo(
            base_cost=project_cost or features.iloc[0].get("total_project_cost_crores", 0),
            cost_overrun_prob=cost_prediction["probability"] / 100,
            delay_prob=delay_prediction["probability"] / 100,
            state=state
        )

        # Build comprehensive risk report
        report = {
            "risk_summary": {
                "overall_risk_level": risk_classification["risk_level"],
                "cost_overrun_probability": cost_prediction["probability"],
                "delay_probability": delay_prediction["probability"],
                "model_confidence": round(
                    (cost_prediction["confidence"] + delay_prediction["confidence"]) / 2, 2
                )
            },

            "cost_overrun_analysis": cost_prediction,
            "delay_analysis": delay_prediction,
            "risk_classification": risk_classification,

            "monte_carlo_simulation": monte_carlo,
            "mitigation_strategies": mitigation,

            "feature_summary": {
                "sections_found_ratio": float(features.iloc[0]["sections_found_ratio"]),
                "total_word_count": int(features.iloc[0]["total_word_count"]),
                "is_mdoner_state": bool(features.iloc[0]["is_mdoner_state"]),
                "terrain_difficulty": int(features.iloc[0]["terrain_difficulty"]),
                "compliance_score": float(features.iloc[0]["compliance_score"])
            }
        }

        logger.info(
            f"Risk analysis complete: {risk_classification['risk_level']} risk | "
            f"Cost overrun: {cost_prediction['probability']}% | "
            f"Delay: {delay_prediction['probability']}%"
        )

        return report

    def _generate_mitigation_strategies(
        self, features: pd.DataFrame, cost_pred: dict, delay_pred: dict, state: Optional[str] = None
    ) -> list:
        """Generate specific mitigation strategies based on identified risks."""
        strategies = []
        row = features.iloc[0]

        # Check each risk factor
        if not row.get("has_contingency", 0):
            strategies.append(self.MITIGATION_STRATEGIES["no_contingency"])

        if not row.get("has_cost_escalation", 0):
            strategies.append(self.MITIGATION_STRATEGIES["no_escalation"])

        if not row.get("has_risk_assessment", 0):
            strategies.append(self.MITIGATION_STRATEGIES["missing_risk_assessment"])

        if not row.get("has_implementation_schedule", 0):
            strategies.append(self.MITIGATION_STRATEGIES["no_schedule"])

        if row.get("terrain_difficulty", 0) >= 6:
            strategies.append(self.MITIGATION_STRATEGIES["terrain_risk"])

        if row.get("is_mdoner_state", 0):
            strategies.append(self.MITIGATION_STRATEGIES["ne_region"])

        if row.get("sections_found_ratio", 0) < 0.7:
            strategies.append(self.MITIGATION_STRATEGIES["low_dpr_quality"])

        if not row.get("has_environmental_impact", 0):
            strategies.append(self.MITIGATION_STRATEGIES["environmental_gaps"])

        # Prioritize by impact
        priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        strategies.sort(
            key=lambda x: priority_order.get(
                x.get("impact", "").split()[0] if x.get("impact") else "Low", 3
            )
        )

        return strategies

    def _run_monte_carlo(
        self,
        base_cost: float,
        cost_overrun_prob: float,
        delay_prob: float,
        state: Optional[str] = None,
        n_simulations: int = 1000
    ) -> dict:
        """
        Simple Monte Carlo simulation for cost and delay estimation.
        """
        import numpy as np

        if base_cost <= 0:
            return {
                "simulated": False,
                "reason": "No base cost available for simulation"
            }

        # Cost simulation parameters
        cost_mean_overrun = 0.15 + (cost_overrun_prob * 0.3)  # 15% base + risk-adjusted
        cost_std = 0.10 + (cost_overrun_prob * 0.15)

        # Simulate costs
        cost_multipliers = np.random.normal(1 + cost_mean_overrun, cost_std, n_simulations)
        cost_multipliers = np.clip(cost_multipliers, 0.8, 2.5)  # Realistic bounds
        simulated_costs = base_cost * cost_multipliers

        # Delay simulation (in months)
        base_delay_months = 0
        delay_mean = 6 + (delay_prob * 18)  # 6 to 24 months
        delay_std = 4 + (delay_prob * 8)

        if state and state in settings.MDONER_STATES:
            delay_mean += 3  # NE region additional delay
            delay_std += 2

        simulated_delays = np.random.normal(delay_mean, delay_std, n_simulations)
        simulated_delays = np.clip(simulated_delays, 0, 48)

        return {
            "simulated": True,
            "n_simulations": n_simulations,
            "cost_simulation": {
                "base_cost_crores": round(base_cost, 2),
                "p10_cost": round(float(np.percentile(simulated_costs, 10)), 2),
                "p50_cost": round(float(np.percentile(simulated_costs, 50)), 2),
                "p75_cost": round(float(np.percentile(simulated_costs, 75)), 2),
                "p90_cost": round(float(np.percentile(simulated_costs, 90)), 2),
                "mean_cost": round(float(np.mean(simulated_costs)), 2),
                "max_cost": round(float(np.max(simulated_costs)), 2),
                "prob_within_budget": round(
                    float(np.mean(simulated_costs <= base_cost * 1.10)) * 100, 2
                ),
                "expected_overrun_percent": round(
                    float((np.mean(simulated_costs) - base_cost) / base_cost * 100), 2
                )
            },
            "delay_simulation": {
                "p10_delay_months": round(float(np.percentile(simulated_delays, 10)), 1),
                "p50_delay_months": round(float(np.percentile(simulated_delays, 50)), 1),
                "p75_delay_months": round(float(np.percentile(simulated_delays, 75)), 1),
                "p90_delay_months": round(float(np.percentile(simulated_delays, 90)), 1),
                "mean_delay_months": round(float(np.mean(simulated_delays)), 1),
                "prob_on_schedule": round(
                    float(np.mean(simulated_delays <= 3)) * 100, 2
                )
            }
        }
