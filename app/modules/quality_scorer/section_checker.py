# ============================================
# DPR Section Completeness Checker
# Validates presence & quality of required sections
# ============================================

from typing import Optional

from loguru import logger

from config.settings import settings


class SectionChecker:
    """
    Checks DPR section completeness against Indian government standards.

    Evaluation criteria:
    1. Section presence (is it there?)
    2. Section depth (is it detailed enough?)
    3. Required sub-elements within sections
    4. Cross-references between sections
    """

    # Minimum word count expectations per section
    SECTION_MIN_WORDS = {
        "executive_summary": 200,
        "project_background": 300,
        "objectives": 100,
        "scope_of_work": 250,
        "technical_feasibility": 500,
        "financial_analysis": 400,
        "cost_estimates": 200,
        "implementation_schedule": 200,
        "institutional_framework": 200,
        "environmental_impact": 300,
        "risk_assessment": 250,
        "monitoring_evaluation": 200,
        "sustainability": 200,
        "annexures": 50
    }

    # Required sub-elements per section
    SECTION_SUBELEMENTS = {
        "executive_summary": [
            "project name", "location", "cost", "duration", "objective", "benefit"
        ],
        "project_background": [
            "need", "existing", "gap", "population", "demand"
        ],
        "objectives": [
            "primary", "specific", "measurable", "target"
        ],
        "scope_of_work": [
            "component", "deliverable", "activity", "output"
        ],
        "technical_feasibility": [
            "design", "technology", "standard", "specification", "capacity"
        ],
        "financial_analysis": [
            "cost", "benefit", "return", "viability", "funding"
        ],
        "cost_estimates": [
            "total", "component", "contingency", "escalation", "breakup"
        ],
        "implementation_schedule": [
            "phase", "milestone", "timeline", "month", "year", "duration"
        ],
        "institutional_framework": [
            "agency", "department", "role", "responsibility", "coordination"
        ],
        "environmental_impact": [
            "impact", "mitigation", "clearance", "assessment", "social"
        ],
        "risk_assessment": [
            "risk", "probability", "impact", "mitigation", "contingency"
        ],
        "monitoring_evaluation": [
            "indicator", "monitoring", "evaluation", "reporting", "framework"
        ],
        "sustainability": [
            "operation", "maintenance", "revenue", "sustainability", "long-term"
        ]
    }

    def __init__(self):
        logger.info("SectionChecker initialized")

    def check_completeness(self, sections: dict) -> dict:
        """
        Comprehensive section completeness check.

        Args:
            sections: Output from NLPProcessor.identify_sections()

        Returns:
            Detailed completeness report
        """
        report = {
            "section_scores": {},
            "overall_completeness": 0,
            "missing_sections": [],
            "weak_sections": [],
            "strong_sections": [],
            "recommendations": []
        }

        total_score = 0
        section_count = 0

        for section_name, min_words in self.SECTION_MIN_WORDS.items():
            section_data = sections.get(section_name, {})
            score_info = self._evaluate_section(
                section_name, section_data, min_words
            )
            report["section_scores"][section_name] = score_info
            total_score += score_info["score"]
            section_count += 1

            if not section_data.get("found", False):
                report["missing_sections"].append(section_name)
                report["recommendations"].append(
                    f"❌ MISSING: Add '{self._format_section_name(section_name)}' section to the DPR"
                )
            elif score_info["score"] < 40:
                report["weak_sections"].append(section_name)
                report["recommendations"].extend(score_info["suggestions"])
            elif score_info["score"] >= 70:
                report["strong_sections"].append(section_name)

        report["overall_completeness"] = round(total_score / max(section_count, 1), 2)

        # Add overall recommendations
        if len(report["missing_sections"]) > 3:
            report["recommendations"].insert(
                0, "⚠️ CRITICAL: Multiple core DPR sections are missing. The document may not be a proper DPR."
            )

        logger.info(
            f"Completeness check: {report['overall_completeness']}% | "
            f"Missing: {len(report['missing_sections'])} | "
            f"Weak: {len(report['weak_sections'])}"
        )

        return report

    def _evaluate_section(self, section_name: str, section_data: dict, min_words: int) -> dict:
        """Evaluate a single section."""
        result = {
            "section_name": section_name,
            "display_name": self._format_section_name(section_name),
            "found": section_data.get("found", False),
            "word_count": section_data.get("word_count", 0),
            "min_expected_words": min_words,
            "score": 0,
            "sub_scores": {},
            "suggestions": []
        }

        if not result["found"]:
            result["score"] = 0
            return result

        # 1. Presence Score (30%)
        presence_score = 30

        # 2. Depth Score - word count relative to minimum (40%)
        word_ratio = min(section_data.get("word_count", 0) / max(min_words, 1), 2.0)
        depth_score = min(word_ratio * 20, 40)

        if word_ratio < 0.5:
            result["suggestions"].append(
                f"⚠️ '{self._format_section_name(section_name)}' is too brief "
                f"({section_data.get('word_count', 0)} words, minimum {min_words} expected)"
            )

        # 3. Sub-element Score (30%)
        subelement_score = self._check_subelements(
            section_name, section_data.get("text", "")
        )

        result["sub_scores"] = {
            "presence": presence_score,
            "depth": round(depth_score, 2),
            "sub_elements": round(subelement_score, 2)
        }

        result["score"] = round(presence_score + depth_score + subelement_score, 2)

        # Add sub-element suggestions
        missing_elements = self._get_missing_subelements(
            section_name, section_data.get("text", "")
        )
        if missing_elements:
            result["suggestions"].append(
                f"📝 '{self._format_section_name(section_name)}' may be missing: "
                f"{', '.join(missing_elements)}"
            )

        return result

    def _check_subelements(self, section_name: str, text: str) -> float:
        """Check what percentage of required sub-elements are present."""
        elements = self.SECTION_SUBELEMENTS.get(section_name, [])
        if not elements:
            return 30  # Full score if no sub-elements defined

        text_lower = text.lower()
        found = sum(1 for elem in elements if elem in text_lower)
        return (found / len(elements)) * 30

    def _get_missing_subelements(self, section_name: str, text: str) -> list:
        """Get list of missing sub-elements."""
        elements = self.SECTION_SUBELEMENTS.get(section_name, [])
        text_lower = text.lower()
        return [elem for elem in elements if elem not in text_lower]

    def _format_section_name(self, name: str) -> str:
        """Convert section_name to display format."""
        return name.replace("_", " ").title()

    def get_section_summary(self, sections: dict) -> dict:
        """Quick summary of section status."""
        found = [name for name, data in sections.items() if data.get("found")]
        missing = [name for name, data in sections.items() if not data.get("found")]

        return {
            "found_sections": [self._format_section_name(s) for s in found],
            "missing_sections": [self._format_section_name(s) for s in missing],
            "found_count": len(found),
            "missing_count": len(missing),
            "total_count": len(sections),
            "completeness_percentage": round(len(found) / max(len(sections), 1) * 100, 2)
        }
