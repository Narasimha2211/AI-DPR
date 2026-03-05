# ============================================
# Feature Engineering for Risk Prediction
# Converts DPR analysis into ML-ready features
# ============================================

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from config.settings import settings


class FeatureEngineer:
    """
    Transforms NLP analysis output into numerical features
    for machine learning risk prediction models.

    Feature categories:
    1. Section completeness features
    2. Financial features
    3. Technical quality features
    4. Timeline features
    5. State/regional features
    6. Compliance features
    """

    # Feature column order (must match training data)
    FEATURE_COLUMNS = [
        # Section features
        "sections_found_ratio",
        "total_word_count",
        "avg_section_words",
        "min_section_words",
        "max_section_words",
        "has_executive_summary",
        "has_technical_feasibility",
        "has_financial_analysis",
        "has_cost_estimates",
        "has_risk_assessment",
        "has_environmental_impact",
        "has_implementation_schedule",

        # Financial features
        "total_project_cost_crores",
        "financial_figures_count",
        "has_contingency",
        "has_cost_escalation",
        "cost_per_word_ratio",

        # Technical features
        "vocabulary_richness",
        "avg_sentence_length",
        "technical_keywords_count",
        "quantitative_data_points",

        # Timeline features
        "dates_found",
        "has_milestones",
        "project_duration_mentioned",

        # State/Regional features
        "is_mdoner_state",
        "state_encoded",
        "terrain_difficulty",

        # Compliance features
        "compliance_score",
        "violations_count",
        "warnings_count"
    ]

    # State encoding (ordinal based on historical project risk)
    STATE_ENCODING = {
        "Arunachal Pradesh": 8, "Assam": 6, "Manipur": 7,
        "Meghalaya": 7, "Mizoram": 7, "Nagaland": 8,
        "Sikkim": 6, "Tripura": 5,
        "Andhra Pradesh": 3, "Bihar": 5, "Chhattisgarh": 4,
        "Goa": 2, "Gujarat": 2, "Haryana": 3,
        "Himachal Pradesh": 5, "Jharkhand": 5, "Karnataka": 2,
        "Kerala": 2, "Madhya Pradesh": 4, "Maharashtra": 3,
        "Odisha": 5, "Punjab": 3, "Rajasthan": 4,
        "Tamil Nadu": 2, "Telangana": 3, "Uttar Pradesh": 4,
        "Uttarakhand": 5, "West Bengal": 4
    }

    TERRAIN_DIFFICULTY = {
        "plain": 1, "mixed": 2, "flood-plain": 3,
        "plateau": 4, "hilly": 6, "mountainous": 8
    }

    def __init__(self):
        logger.info("FeatureEngineer initialized")

    def extract_features(
        self,
        nlp_analysis: dict,
        quality_score: Optional[dict] = None,
        compliance_report: Optional[dict] = None,
        state: Optional[str] = None,
        project_cost: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Extract all features from analysis outputs.

        Returns:
            DataFrame with one row of features
        """
        features = {}

        # --- Section Features ---
        sections = nlp_analysis.get("sections", {})
        section_word_counts = [
            s.get("word_count", 0) for s in sections.values() if s.get("found")
        ]
        total_sections = len(sections)
        found_sections = sum(1 for s in sections.values() if s.get("found"))

        features["sections_found_ratio"] = found_sections / max(total_sections, 1)
        features["total_word_count"] = nlp_analysis.get("text_statistics", {}).get("total_words", 0)
        features["avg_section_words"] = np.mean(section_word_counts) if section_word_counts else 0
        features["min_section_words"] = min(section_word_counts) if section_word_counts else 0
        features["max_section_words"] = max(section_word_counts) if section_word_counts else 0

        # Binary section presence features
        features["has_executive_summary"] = int(sections.get("executive_summary", {}).get("found", False))
        features["has_technical_feasibility"] = int(sections.get("technical_feasibility", {}).get("found", False))
        features["has_financial_analysis"] = int(sections.get("financial_analysis", {}).get("found", False))
        features["has_cost_estimates"] = int(sections.get("cost_estimates", {}).get("found", False))
        features["has_risk_assessment"] = int(sections.get("risk_assessment", {}).get("found", False))
        features["has_environmental_impact"] = int(sections.get("environmental_impact", {}).get("found", False))
        features["has_implementation_schedule"] = int(sections.get("implementation_schedule", {}).get("found", False))

        # --- Financial Features ---
        financial_figures = nlp_analysis.get("financial_figures", [])
        total_cost = project_cost or sum(f.get("value_in_crores", 0) for f in financial_figures)

        features["total_project_cost_crores"] = total_cost
        features["financial_figures_count"] = len(financial_figures)

        full_text = " ".join(s.get("text", "") for s in sections.values()).lower()
        features["has_contingency"] = int("contingency" in full_text)
        features["has_cost_escalation"] = int("escalation" in full_text)
        features["cost_per_word_ratio"] = (
            total_cost / max(features["total_word_count"], 1)
        )

        # --- Technical Features ---
        stats = nlp_analysis.get("text_statistics", {})
        features["vocabulary_richness"] = stats.get("vocabulary_richness", 0)
        features["avg_sentence_length"] = stats.get("avg_words_per_sentence", 0)

        technical_keywords = [
            "specification", "standard", "design", "capacity", "load",
            "stress", "foundation", "structural", "methodology",
            "technology", "equipment", "material", "quality control"
        ]
        features["technical_keywords_count"] = sum(1 for kw in technical_keywords if kw in full_text)
        features["quantitative_data_points"] = len(
            nlp_analysis.get("entities", {}).get("quantities", [])
        )

        # --- Timeline Features ---
        dates = nlp_analysis.get("dates_timelines", [])
        features["dates_found"] = len(dates)
        features["has_milestones"] = int("milestone" in full_text)
        features["project_duration_mentioned"] = int(
            any(d.get("type") == "duration" for d in dates)
        )

        # --- State/Regional Features ---
        features["is_mdoner_state"] = int(state in settings.MDONER_STATES) if state else 0
        features["state_encoded"] = self.STATE_ENCODING.get(state or "", 5)

        # Terrain difficulty
        terrain = self._get_state_terrain(state or "")
        features["terrain_difficulty"] = self.TERRAIN_DIFFICULTY.get(terrain, 3)

        # --- Compliance Features ---
        if compliance_report:
            features["compliance_score"] = compliance_report.get("overall_compliance_score", 50)
            features["violations_count"] = len(compliance_report.get("violations", []))
            features["warnings_count"] = len(compliance_report.get("warnings", []))
        else:
            features["compliance_score"] = 50
            features["violations_count"] = 0
            features["warnings_count"] = 0

        # Create DataFrame
        df = pd.DataFrame([features])

        # Ensure column order matches training
        for col in self.FEATURE_COLUMNS:
            if col not in df.columns:
                df[col] = 0

        df = df.reindex(columns=self.FEATURE_COLUMNS, fill_value=0)

        logger.info(f"Extracted {len(self.FEATURE_COLUMNS)} features")
        return df

    def _get_state_terrain(self, state: str) -> str:
        """Get terrain type for a state."""
        terrain_map = {
            "Arunachal Pradesh": "mountainous",
            "Assam": "flood-plain",
            "Manipur": "hilly",
            "Meghalaya": "plateau",
            "Mizoram": "hilly",
            "Nagaland": "hilly",
            "Sikkim": "mountainous",
            "Tripura": "mixed",
            "Himachal Pradesh": "mountainous",
            "Uttarakhand": "mountainous",
            "Jharkhand": "plateau",
            "Chhattisgarh": "mixed",
            "Odisha": "mixed",
            "Rajasthan": "plain",
            "Gujarat": "plain",
            "Punjab": "plain",
            "Haryana": "plain",
            "Bihar": "flood-plain",
            "West Bengal": "flood-plain",
        }
        return terrain_map.get(state, "mixed")

    def get_feature_importance_names(self) -> list:
        """Return feature names for model interpretability."""
        return self.FEATURE_COLUMNS.copy()
