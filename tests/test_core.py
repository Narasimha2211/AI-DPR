"""
AI DPR - Test Suite
Tests for NLP processing, quality scoring, and risk prediction.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ============================================================
# NLP Processor Tests
# ============================================================
class TestNLPProcessor:
    """Tests for NLP document analysis."""

    def test_section_identification(self):
        """Test that section patterns correctly identify DPR sections."""
        from app.modules.document_parser.nlp_processor import NLPProcessor

        processor = NLPProcessor()
        sample_text = """
        1. Executive Summary
        This project aims to build a road connecting remote villages.

        2. Project Background
        The state of Manipur has long needed improved connectivity.

        3. Objectives
        - Improve road connectivity
        - Reduce travel time

        4. Cost Estimates
        Total project cost: Rs 150 Crores
        """

        sections = processor.identify_sections(sample_text)
        assert "executive_summary" in sections
        assert "project_background" in sections
        assert "objectives" in sections
        assert "cost_estimates" in sections
        assert sections["executive_summary"]["found"] is True

    def test_financial_extraction(self):
        """Test currency value extraction from text."""
        from app.modules.document_parser.nlp_processor import NLPProcessor

        processor = NLPProcessor()
        text = """
        The total project cost is ₹ 250 Crores.
        Phase 1 costs Rs 50 Lakhs.
        The contingency budget is INR 10,00,000.
        """

        figures = processor.extract_financial_figures(text)
        assert len(figures) > 0
        assert any(f["original"] for f in figures)

    def test_empty_text_handling(self):
        """Test NLP processor handles empty text gracefully."""
        from app.modules.document_parser.nlp_processor import NLPProcessor

        processor = NLPProcessor()
        result = processor.analyze_document("")
        assert result is not None
        assert "sections" in result
        assert "entities" in result

    def test_text_statistics(self):
        """Test text statistics computation."""
        from app.modules.document_parser.nlp_processor import NLPProcessor

        processor = NLPProcessor()
        text = "This is a test document. It has multiple sentences. The project cost is significant."
        stats = processor.compute_text_statistics(text)
        assert stats["total_words"] > 0
        assert stats["total_sentences"] > 0
        assert "avg_word_length" in stats


# ============================================================
# Section Checker Tests
# ============================================================
class TestSectionChecker:
    """Tests for section completeness checking."""

    def test_full_completeness(self):
        """Test scoring with all sections present."""
        from app.modules.quality_scorer.section_checker import SectionChecker

        checker = SectionChecker()
        sections = {}
        section_names = [
            "executive_summary", "project_background", "objectives",
            "scope_of_work", "technical_feasibility", "financial_analysis",
            "cost_estimates", "implementation_schedule", "institutional_framework",
            "environmental_impact", "risk_assessment", "monitoring_evaluation",
            "sustainability", "annexures"
        ]
        for s in section_names:
            sections[s] = {"found": True, "word_count": 500, "content": "Detailed content " * 50}

        result = checker.check_completeness(sections)
        assert result["overall_score"] > 50
        assert result["sections_found"] == 14

    def test_missing_sections(self):
        """Test scoring with missing sections."""
        from app.modules.quality_scorer.section_checker import SectionChecker

        checker = SectionChecker()
        sections = {
            "executive_summary": {"found": True, "word_count": 100, "content": "Brief summary"},
            "objectives": {"found": True, "word_count": 50, "content": "Some objectives"}
        }

        result = checker.check_completeness(sections)
        assert result["overall_score"] < 50
        assert result["sections_found"] == 2
        assert len(result["missing_sections"]) > 0

    def test_empty_sections(self):
        """Test handling of empty sections dict."""
        from app.modules.quality_scorer.section_checker import SectionChecker

        checker = SectionChecker()
        result = checker.check_completeness({})
        assert result["overall_score"] == 0
        assert result["sections_found"] == 0


# ============================================================
# Compliance Engine Tests
# ============================================================
class TestComplianceEngine:
    """Tests for government compliance validation."""

    def test_mdoner_state_compliance(self):
        """Test compliance check for MDoNER state."""
        from app.modules.quality_scorer.compliance_engine import ComplianceEngine

        engine = ComplianceEngine()
        nlp_analysis = {
            "sections": {
                "executive_summary": {"found": True, "word_count": 200},
                "financial_analysis": {"found": True, "word_count": 300},
                "cost_estimates": {"found": True, "word_count": 200},
                "environmental_impact": {"found": True, "word_count": 150},
                "risk_assessment": {"found": True, "word_count": 100}
            },
            "financial_figures": [{"value_inr": 150_00_00_000}],
            "entities": {},
            "text_statistics": {"total_words": 5000}
        }

        result = engine.validate_compliance(nlp_analysis, state="Manipur")
        assert "overall_score" in result or "overall_compliance_score" in result
        assert "compliance_level" in result
        assert result["compliance_level"] in ["HIGH", "MEDIUM", "LOW", "CRITICAL"]

    def test_non_mdoner_state(self):
        """Test compliance for non-MDoNER state."""
        from app.modules.quality_scorer.compliance_engine import ComplianceEngine

        engine = ComplianceEngine()
        nlp_analysis = {
            "sections": {"executive_summary": {"found": True, "word_count": 200}},
            "financial_figures": [],
            "entities": {},
            "text_statistics": {"total_words": 1000}
        }

        result = engine.validate_compliance(nlp_analysis, state="Maharashtra")
        assert "overall_score" in result or "overall_compliance_score" in result


# ============================================================
# Feature Engineer Tests
# ============================================================
class TestFeatureEngineer:
    """Tests for ML feature extraction."""

    def test_feature_extraction(self):
        """Test that feature extraction produces correct shape."""
        from app.modules.risk_predictor.feature_engineer import FeatureEngineer

        fe = FeatureEngineer()
        nlp_analysis = {
            "sections": {
                "executive_summary": {"found": True, "word_count": 200},
                "financial_analysis": {"found": True, "word_count": 300}
            },
            "financial_figures": [{"value_inr": 100_00_00_000}],
            "entities": {"organizations": [{"text": "MDoNER"}], "locations": []},
            "tables": [],
            "text_statistics": {"total_words": 3000, "avg_word_length": 5.2},
            "dates_timelines": [],
            "key_phrases": []
        }

        compliance = {"overall_compliance_score": 65, "violations": [], "warnings": []}

        features = fe.extract_features(
            nlp_analysis,
            quality_score=None,
            compliance_report=compliance,
            state="Meghalaya",
            project_cost=100
        )
        assert features.shape[1] == len(FeatureEngineer.FEATURE_COLUMNS)
        assert features.shape[0] == 1

    def test_feature_defaults(self):
        """Test feature extraction with minimal input."""
        from app.modules.risk_predictor.feature_engineer import FeatureEngineer

        fe = FeatureEngineer()
        features = fe.extract_features({})
        assert features is not None
        assert features.shape[0] == 1


# ============================================================
# Risk ML Models Tests
# ============================================================
class TestRiskMLModels:
    """Tests for risk prediction pipeline."""

    def test_heuristic_risk_prediction(self):
        """Test risk analysis with heuristic fallback (no trained models)."""
        from app.modules.risk_predictor.ml_models import RiskMLModels
        from app.modules.risk_predictor.feature_engineer import FeatureEngineer
        import pandas as pd
        import numpy as np

        models = RiskMLModels()
        feature_cols = FeatureEngineer.FEATURE_COLUMNS

        features = pd.DataFrame(
            [np.zeros(len(feature_cols))],
            columns=feature_cols
        )
        features["completeness_ratio"] = 0.7
        features["terrain_difficulty"] = 5
        features["compliance_score"] = 60
        features["has_budget_table"] = 1
        features["is_mdoner_state"] = 1

        cost_result = models.predict_cost_overrun(features)
        assert "probability" in cost_result
        assert 0 <= cost_result["probability"] <= 100

        delay_result = models.predict_delay(features)
        assert "probability" in delay_result
        assert 0 <= delay_result["probability"] <= 100

        risk_result = models.classify_risk(features)
        assert "risk_level" in risk_result
        assert risk_result["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


# ============================================================
# Quality Report Tests
# ============================================================
class TestQualityReport:
    """Tests for master quality scoring."""

    def test_grade_assignment(self):
        """Test that grade assignment works correctly."""
        from app.modules.quality_scorer.quality_report import QualityScorer

        scorer = QualityScorer()
        grade_a_plus = scorer._get_grade(95)
        grade_a = scorer._get_grade(85)
        grade_b_plus = scorer._get_grade(75)
        grade_b = scorer._get_grade(65)
        grade_c = scorer._get_grade(55)
        grade_d = scorer._get_grade(45)
        grade_f = scorer._get_grade(30)

        # Check that higher scores get better grades
        assert grade_a_plus[0] == "A+"
        assert grade_a[0] == "A"
        assert grade_b_plus[0] == "B+"
        assert grade_b[0] == "B"
        assert grade_c[0] == "C"
        assert grade_d[0] == "D"
        assert grade_f[0] == "F"


# ============================================================
# Table Extractor Tests
# ============================================================
class TestTableExtractor:
    """Tests for table classification."""

    def test_budget_table_classification(self):
        """Test budget table detection."""
        from app.modules.document_parser.table_extractor import TableExtractor

        extractor = TableExtractor()
        table = [
            ["Item", "Amount (Rs)", "Budget Head"],
            ["Construction", "50,00,000", "Capital"],
            ["Equipment", "20,00,000", "Capital"]
        ]
        result = extractor._classify_table(table)
        assert result in ["budget", "other", "unknown"]

    def test_empty_table(self):
        """Test handling of empty table."""
        from app.modules.document_parser.table_extractor import TableExtractor

        extractor = TableExtractor()
        result = extractor.extract_tables_from_text([])
        assert result["total_tables"] == 0


# ============================================================
# Configuration Tests
# ============================================================
class TestConfig:
    """Tests for project configuration."""

    def test_settings_load(self):
        """Test that settings load correctly."""
        from config.settings import Settings

        settings = Settings()
        assert len(settings.MDONER_STATES) == 8
        assert "Manipur" in settings.MDONER_STATES
        assert len(settings.REQUIRED_DPR_SECTIONS) == 14
        assert settings.MAX_FILE_SIZE_MB > 0

    def test_mdoner_states_complete(self):
        """Test all 8 NE states are listed."""
        from config.settings import Settings

        settings = Settings()
        expected = {"Arunachal Pradesh", "Assam", "Manipur", "Meghalaya",
                    "Mizoram", "Nagaland", "Sikkim", "Tripura"}
        assert set(settings.MDONER_STATES) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
