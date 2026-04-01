# ============================================
# DPR Quality Scoring Engine
# Comprehensive scoring with weighted criteria
# ============================================

from typing import Optional

from loguru import logger

from config.settings import settings
from app.modules.quality_scorer.section_checker import SectionChecker
from app.modules.quality_scorer.compliance_engine import ComplianceEngine


class QualityScorer:
    """
    Master quality scoring engine that combines:
    1. Section completeness score
    2. Technical depth score
    3. Financial accuracy score
    4. Compliance score
    5. Risk assessment quality score

    Produces a composite DPR Quality Score (0-100)
    with detailed breakdown and recommendations.
    """

    # Quality grade thresholds
    GRADES = {
        "A+": (90, 100, "Excellent - Ready for approval"),
        "A":  (80, 89, "Very Good - Minor improvements recommended"),
        "B+": (70, 79, "Good - Some improvements needed"),
        "B":  (60, 69, "Satisfactory - Multiple improvements needed"),
        "C":  (50, 59, "Below Average - Significant revision required"),
        "D":  (40, 49, "Poor - Major revision required"),
        "F":  (0, 39, "Fail - Complete rework needed"),
    }

    def __init__(self):
        self.section_checker = SectionChecker()
        self.compliance_engine = ComplianceEngine()
        logger.info("QualityScorer initialized")

    def score_dpr(
        self,
        nlp_analysis: dict,
        table_analysis: Optional[dict] = None,
        state: Optional[str] = None,
        project_type: Optional[str] = None
    ) -> dict:
        """
        Generate comprehensive quality score for a DPR.

        Args:
            nlp_analysis: Output from NLPProcessor.analyze_document()
            table_analysis: Output from TableExtractor
            state: Indian state name
            project_type: Type of project

        Returns:
            Comprehensive quality report with scores
        """
        logger.info(f"Scoring DPR for state: {state}, type: {project_type}")

        # 1. Section Completeness Score (25%)
        section_report = self.section_checker.check_completeness(
            nlp_analysis.get("sections", {})
        )

        # 2. Technical Depth Score (20%)
        technical_score = self._evaluate_technical_depth(nlp_analysis)

        # 3. Financial Accuracy Score (20%)
        financial_score = self._evaluate_financial_quality(nlp_analysis, table_analysis)

        # 4. Compliance Score (20%)
        compliance_report = self.compliance_engine.validate_compliance(
            nlp_analysis, state=state, project_type=project_type
        )

        # 5. Risk Assessment Quality Score (15%)
        risk_quality_score = self._evaluate_risk_quality(nlp_analysis)

        # Compute weighted composite score
        composite_score = (
            section_report["overall_completeness"] * settings.SECTION_COMPLETENESS_WEIGHT +
            technical_score["score"] * settings.TECHNICAL_DEPTH_WEIGHT +
            financial_score["score"] * settings.FINANCIAL_ACCURACY_WEIGHT +
            compliance_report["overall_compliance_score"] * settings.COMPLIANCE_WEIGHT +
            risk_quality_score["score"] * settings.RISK_ASSESSMENT_WEIGHT
        )
        composite_score = round(min(composite_score, 100), 2)

        # Determine grade
        grade, grade_description = self._get_grade(composite_score)

        # Build final report
        report = {
            "composite_score": composite_score,
            "grade": grade,
            "grade_description": grade_description,
            "state": state,
            "project_type": project_type,

            # Individual scores
            "scores": {
                "section_completeness": {
                    "score": section_report["overall_completeness"],
                    "weight": settings.SECTION_COMPLETENESS_WEIGHT,
                    "weighted_score": round(
                        section_report["overall_completeness"] * settings.SECTION_COMPLETENESS_WEIGHT, 2
                    ),
                    "details": section_report
                },
                "technical_depth": {
                    "score": technical_score["score"],
                    "weight": settings.TECHNICAL_DEPTH_WEIGHT,
                    "weighted_score": round(
                        technical_score["score"] * settings.TECHNICAL_DEPTH_WEIGHT, 2
                    ),
                    "details": technical_score
                },
                "financial_accuracy": {
                    "score": financial_score["score"],
                    "weight": settings.FINANCIAL_ACCURACY_WEIGHT,
                    "weighted_score": round(
                        financial_score["score"] * settings.FINANCIAL_ACCURACY_WEIGHT, 2
                    ),
                    "details": financial_score
                },
                "compliance": {
                    "score": compliance_report["overall_compliance_score"],
                    "weight": settings.COMPLIANCE_WEIGHT,
                    "weighted_score": round(
                        compliance_report["overall_compliance_score"] * settings.COMPLIANCE_WEIGHT, 2
                    ),
                    "details": compliance_report
                },
                "risk_assessment_quality": {
                    "score": risk_quality_score["score"],
                    "weight": settings.RISK_ASSESSMENT_WEIGHT,
                    "weighted_score": round(
                        risk_quality_score["score"] * settings.RISK_ASSESSMENT_WEIGHT, 2
                    ),
                    "details": risk_quality_score
                }
            },

            # Aggregated recommendations
            "recommendations": self._aggregate_recommendations(
                section_report, technical_score, financial_score,
                compliance_report, risk_quality_score
            ),

            # Summary statistics
            "summary": {
                "total_sections_found": sum(
                    1 for s in nlp_analysis.get("sections", {}).values() if s.get("found")
                ),
                "total_sections_required": len(nlp_analysis.get("sections", {})),
                "total_words": nlp_analysis.get("text_statistics", {}).get("total_words", 0),
                "total_financial_figures": len(nlp_analysis.get("financial_figures", [])),
                "compliance_status": compliance_report.get("compliance_status", "Unknown"),
                "is_mdoner_state": state in settings.MDONER_STATES if state else False
            }
        }

        logger.info(f"DPR Quality Score: {composite_score} ({grade}) - {grade_description}")
        return report

    def _evaluate_technical_depth(self, analysis: dict) -> dict:
        """Evaluate technical quality of the DPR."""
        score = 0
        checks = []

        sections = analysis.get("sections", {})
        stats = analysis.get("text_statistics", {})

        # Check technical feasibility section depth
        tech_section = sections.get("technical_feasibility", {})
        if tech_section.get("found"):
            word_count = tech_section.get("word_count", 0)
            if word_count >= 500:
                score += 30
                checks.append("✅ Technical feasibility section is detailed")
            elif word_count >= 200:
                score += 15
                checks.append("⚠️ Technical feasibility section needs more detail")
            else:
                checks.append("❌ Technical feasibility section is too brief")

        # Check for technical terminology
        technical_keywords = [
            "specification", "standard", "design", "capacity", "load",
            "stress", "foundation", "structural", "methodology",
            "technology", "equipment", "material", "quality control"
        ]
        full_text = " ".join(s.get("text", "") for s in sections.values()).lower()
        tech_keyword_count = sum(1 for kw in technical_keywords if kw in full_text)
        keyword_score = min((tech_keyword_count / len(technical_keywords)) * 30, 30)
        score += keyword_score

        # Check for quantitative data
        entities = analysis.get("entities", {})
        quantities = len(entities.get("quantities", []))
        if quantities >= 10:
            score += 20
            checks.append("✅ Good amount of quantitative data")
        elif quantities >= 5:
            score += 10
            checks.append("⚠️ More quantitative data recommended")
        else:
            checks.append("❌ Insufficient quantitative data")

        # Vocabulary richness
        vocab_richness = stats.get("vocabulary_richness", 0)
        if vocab_richness > 0.3:
            score += 20
            checks.append("✅ Good vocabulary diversity")
        elif vocab_richness > 0.2:
            score += 10
        else:
            checks.append("⚠️ Low vocabulary diversity - may indicate repetitive content")

        return {
            "score": min(round(score), 100),
            "checks": checks,
            "technical_keywords_found": tech_keyword_count,
            "quantitative_data_points": quantities
        }

    def _evaluate_financial_quality(self, analysis: dict, table_analysis: Optional[dict] = None) -> dict:
        """Evaluate financial quality of the DPR."""
        score = 0
        checks = []

        financial_figures = analysis.get("financial_figures", [])
        sections = analysis.get("sections", {})

        # Check financial figures presence
        if len(financial_figures) >= 5:
            score += 25
            checks.append(f"✅ {len(financial_figures)} financial figures found")
        elif len(financial_figures) > 0:
            score += 10
            checks.append(f"⚠️ Only {len(financial_figures)} financial figures found")
        else:
            checks.append("❌ No financial figures found")

        # Check financial section
        fin_section = sections.get("financial_analysis", {})
        cost_section = sections.get("cost_estimates", {})

        if fin_section.get("found"):
            score += 20
        if cost_section.get("found"):
            score += 20

        # Check for budget tables
        if table_analysis:
            budget_tables = table_analysis.get("budget_tables", [])
            if budget_tables:
                score += 20
                checks.append(f"✅ {len(budget_tables)} budget tables found")
            else:
                checks.append("⚠️ No budget tables detected")

            # Check for BOQ
            boq_tables = table_analysis.get("boq_tables", [])
            if boq_tables:
                score += 15
                checks.append("✅ Bill of Quantities found")
        else:
            score += 15  # Partial credit when table analysis not available

        return {
            "score": min(round(score), 100),
            "checks": checks,
            "financial_figures_count": len(financial_figures),
            "total_project_cost": sum(
                f.get("value_in_crores", 0) for f in financial_figures
            )
        }

    def _evaluate_risk_quality(self, analysis: dict) -> dict:
        """Evaluate the quality of risk assessment in the DPR."""
        score = 0
        checks = []

        sections = analysis.get("sections", {})
        risk_section = sections.get("risk_assessment", {})

        if risk_section.get("found"):
            score += 30
            checks.append("✅ Risk Assessment section present")

            text_lower = risk_section.get("text", "").lower()

            risk_elements = {
                "risk identification": ["risk", "threat", "vulnerability"],
                "probability assessment": ["probability", "likelihood", "chance"],
                "impact assessment": ["impact", "consequence", "severity"],
                "mitigation measures": ["mitigation", "response", "strategy", "action"],
                "contingency planning": ["contingency", "backup", "alternative"],
                "risk monitoring": ["monitor", "review", "track"]
            }

            for element_name, keywords in risk_elements.items():
                if any(kw in text_lower for kw in keywords):
                    score += 10
                    checks.append(f"✅ {element_name} addressed")
                else:
                    checks.append(f"⚠️ {element_name} not clearly addressed")
        else:
            checks.append("❌ Risk Assessment section missing")

        return {
            "score": min(round(score), 100),
            "checks": checks
        }

    def _get_grade(self, score: float) -> tuple:
        """Determine quality grade from score."""
        for grade, (min_score, max_score, description) in self.GRADES.items():
            if min_score <= score <= max_score:
                return grade, description
        return "F", "Ungraded"

    def _aggregate_recommendations(self, *reports) -> list:
        """Aggregate and prioritize recommendations from all reports."""
        all_recommendations = []

        for report in reports:
            if isinstance(report, dict):
                recs = report.get("recommendations", [])
                if isinstance(recs, list):
                    all_recommendations.extend(recs)

        # Deduplicate while preserving order
        seen = set()
        unique_recs = []
        for rec in all_recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recs.append(rec)

        # Prioritize (critical first)
        critical = [r for r in unique_recs if "❌" in r or "CRITICAL" in r.upper() or "MISSING" in r.upper()]
        warnings = [r for r in unique_recs if "⚠️" in r or "WARNING" in r.upper()]
        suggestions = [r for r in unique_recs if r not in critical and r not in warnings]

        return critical + warnings + suggestions
