# ============================================
# DPR Compliance Engine
# Validates against Indian Government Standards
# ============================================

import json
from pathlib import Path
from typing import Optional

from loguru import logger

from config.settings import settings


class ComplianceEngine:
    """
    Validates DPR compliance against:
    1. Central Government DPR Guidelines
    2. State-specific requirements (MDoNER states)
    3. Ministry-specific standards
    4. Financial prudence norms
    5. Environmental clearance requirements
    """

    # Government compliance rules
    CENTRAL_RULES = {
        "minimum_sections": 10,
        "must_have_sections": [
            "executive_summary", "project_background", "objectives",
            "technical_feasibility", "financial_analysis", "cost_estimates",
            "implementation_schedule", "risk_assessment"
        ],
        "financial_rules": {
            "contingency_max_percent": 10,
            "escalation_max_percent": 7,
            "admin_overhead_max_percent": 5,
            "cost_per_beneficiary_threshold": True
        },
        "timeline_rules": {
            "max_project_duration_years": 5,
            "must_have_milestones": True,
            "quarterly_reporting": True
        }
    }

    # MDoNER (Ministry of Development of North Eastern Region) specific rules
    MDONER_RULES = {
        "additional_sections": [
            "terrain_accessibility",
            "tribal_community_impact",
            "northeast_specific_challenges",
            "connectivity_infrastructure"
        ],
        "special_provisions": [
            "90:10 funding pattern",
            "special category state provisions",
            "border area development",
            "flood/landslide vulnerability"
        ],
        "priority_sectors": [
            "connectivity", "tourism", "power", "horticulture",
            "education", "health", "water resources", "skill development"
        ]
    }

    # State-specific compliance additions
    STATE_RULES = {
        "Arunachal Pradesh": {
            "special_focus": ["border area", "tribal welfare", "hydropower"],
            "terrain": "hilly",
            "additional_checks": ["forest clearance", "tribal consent"]
        },
        "Assam": {
            "special_focus": ["flood management", "tea industry", "oil & gas"],
            "terrain": "flood-plain",
            "additional_checks": ["flood risk assessment", "wetland impact"]
        },
        "Manipur": {
            "special_focus": ["border trade", "handloom", "sports infrastructure"],
            "terrain": "hilly",
            "additional_checks": ["ethnic harmony impact"]
        },
        "Meghalaya": {
            "special_focus": ["mining", "tourism", "agriculture"],
            "terrain": "plateau",
            "additional_checks": ["sixth schedule compliance"]
        },
        "Mizoram": {
            "special_focus": ["bamboo industry", "border trade"],
            "terrain": "hilly",
            "additional_checks": ["young mizo association consultation"]
        },
        "Nagaland": {
            "special_focus": ["tribal economy", "tourism"],
            "terrain": "hilly",
            "additional_checks": ["tribal council approval"]
        },
        "Sikkim": {
            "special_focus": ["organic farming", "tourism", "hydropower"],
            "terrain": "mountainous",
            "additional_checks": ["ecological sensitivity"]
        },
        "Tripura": {
            "special_focus": ["rubber plantation", "border trade"],
            "terrain": "mixed",
            "additional_checks": ["border area clearance"]
        }
    }

    def __init__(self):
        self.rules_path = settings.DATA_DIR / "compliance_rules"
        logger.info("ComplianceEngine initialized")

    def validate_compliance(
        self,
        nlp_analysis: dict,
        state: Optional[str] = None,
        project_type: Optional[str] = None
    ) -> dict:
        """
        Comprehensive compliance validation.

        Args:
            nlp_analysis: Output from NLPProcessor.analyze_document()
            state: Indian state name
            project_type: Type of project (road, bridge, building, etc.)

        Returns:
            Compliance report with scores and violations
        """
        report = {
            "state": state or "General",
            "project_type": project_type or "Unknown",
            "overall_compliance_score": 0,
            "central_compliance": {},
            "state_compliance": {},
            "financial_compliance": {},
            "environmental_compliance": {},
            "violations": [],
            "warnings": [],
            "recommendations": [],
            "is_mdoner_state": state in settings.MDONER_STATES if state else False
        }

        # 1. Central Government Compliance
        report["central_compliance"] = self._check_central_compliance(nlp_analysis)

        # 2. State-specific Compliance
        if state:
            report["state_compliance"] = self._check_state_compliance(nlp_analysis, state)

        # 3. Financial Compliance
        report["financial_compliance"] = self._check_financial_compliance(nlp_analysis)

        # 4. Environmental Compliance
        report["environmental_compliance"] = self._check_environmental_compliance(nlp_analysis)

        # Calculate overall score
        scores = [
            report["central_compliance"].get("score", 0) * 0.35,
            report["state_compliance"].get("score", 50) * 0.20,
            report["financial_compliance"].get("score", 0) * 0.25,
            report["environmental_compliance"].get("score", 0) * 0.20,
        ]
        report["overall_compliance_score"] = round(sum(scores), 2)

        # Aggregate violations and recommendations
        for comp_type in ["central_compliance", "state_compliance",
                         "financial_compliance", "environmental_compliance"]:
            comp = report.get(comp_type, {})
            report["violations"].extend(comp.get("violations", []))
            report["warnings"].extend(comp.get("warnings", []))
            report["recommendations"].extend(comp.get("recommendations", []))

        # Compliance level
        score = report["overall_compliance_score"]
        if score >= 80:
            report["compliance_level"] = "HIGH"
            report["compliance_status"] = "✅ Compliant"
        elif score >= 60:
            report["compliance_level"] = "MEDIUM"
            report["compliance_status"] = "⚠️ Partially Compliant - Improvements Needed"
        elif score >= 40:
            report["compliance_level"] = "LOW"
            report["compliance_status"] = "🔶 Non-Compliant - Major Revisions Required"
        else:
            report["compliance_level"] = "CRITICAL"
            report["compliance_status"] = "❌ Critically Non-Compliant - Reject/Rework"

        logger.info(
            f"Compliance check complete: {report['compliance_level']} "
            f"({report['overall_compliance_score']}%)"
        )

        return report

    def _check_central_compliance(self, analysis: dict) -> dict:
        """Check against central government DPR rules."""
        result = {
            "score": 0,
            "checks": [],
            "violations": [],
            "warnings": [],
            "recommendations": []
        }

        sections = analysis.get("sections", {})

        # Check mandatory sections
        must_have = self.CENTRAL_RULES["must_have_sections"]
        found_mandatory = 0
        for section in must_have:
            if sections.get(section, {}).get("found", False):
                found_mandatory += 1
                result["checks"].append({
                    "rule": f"Section '{section}' present",
                    "status": "PASS",
                    "severity": "high"
                })
            else:
                result["violations"].append(
                    f"Missing mandatory section: {section.replace('_', ' ').title()}"
                )
                result["checks"].append({
                    "rule": f"Section '{section}' present",
                    "status": "FAIL",
                    "severity": "high"
                })

        # Check minimum section count
        total_found = sum(1 for s in sections.values() if s.get("found", False))
        min_required = self.CENTRAL_RULES["minimum_sections"]

        if total_found >= min_required:
            result["checks"].append({
                "rule": f"Minimum {min_required} sections",
                "status": "PASS",
                "severity": "high"
            })
        else:
            result["violations"].append(
                f"Only {total_found} sections found, minimum {min_required} required"
            )

        # Check text statistics
        stats = analysis.get("text_statistics", {})
        if stats.get("total_words", 0) < 2000:
            result["warnings"].append(
                "DPR appears too brief. Government DPRs typically have 5000+ words."
            )

        # Calculate score
        mandatory_score = (found_mandatory / len(must_have)) * 60
        section_score = min((total_found / min_required) * 40, 40)
        result["score"] = round(mandatory_score + section_score, 2)

        return result

    def _check_state_compliance(self, analysis: dict, state: str) -> dict:
        """Check state-specific compliance rules."""
        result = {
            "score": 50,  # Default for states without specific rules
            "state": state,
            "is_mdoner": state in settings.MDONER_STATES,
            "checks": [],
            "violations": [],
            "warnings": [],
            "recommendations": []
        }

        text = ""
        for section_data in analysis.get("sections", {}).values():
            text += " " + section_data.get("text", "")
        text_lower = text.lower()

        # MDoNER specific checks
        if result["is_mdoner"]:
            mdoner_score = 0
            for provision in self.MDONER_RULES["special_provisions"]:
                if provision.lower() in text_lower:
                    mdoner_score += 10
                    result["checks"].append({
                        "rule": f"MDoNER provision: {provision}",
                        "status": "PASS"
                    })
                else:
                    result["warnings"].append(
                        f"MDoNER special provision not addressed: {provision}"
                    )

            # Check priority sector alignment
            sector_matches = 0
            for sector in self.MDONER_RULES["priority_sectors"]:
                if sector in text_lower:
                    sector_matches += 1

            if sector_matches > 0:
                result["checks"].append({
                    "rule": "Aligns with MDoNER priority sectors",
                    "status": "PASS"
                })
                mdoner_score += 20

            result["score"] = min(50 + mdoner_score, 100)

        # State-specific checks
        state_rules = self.STATE_RULES.get(state, {})
        if state_rules:
            for check in state_rules.get("additional_checks", []):
                if check.lower() in text_lower:
                    result["checks"].append({
                        "rule": f"State requirement: {check}",
                        "status": "PASS"
                    })
                    result["score"] = min(result["score"] + 10, 100)
                else:
                    result["recommendations"].append(
                        f"Consider addressing: {check} (required for {state})"
                    )

        return result

    def _check_financial_compliance(self, analysis: dict) -> dict:
        """Check financial compliance of the DPR."""
        result = {
            "score": 0,
            "checks": [],
            "violations": [],
            "warnings": [],
            "recommendations": []
        }

        financial_figures = analysis.get("financial_figures", [])
        sections = analysis.get("sections", {})

        # Check if financial section exists
        fin_section = sections.get("financial_analysis", {})
        cost_section = sections.get("cost_estimates", {})

        score = 0

        if fin_section.get("found", False):
            score += 25
            result["checks"].append({
                "rule": "Financial Analysis section present",
                "status": "PASS"
            })
        else:
            result["violations"].append("Missing Financial Analysis section")

        if cost_section.get("found", False):
            score += 25
            result["checks"].append({
                "rule": "Cost Estimates section present",
                "status": "PASS"
            })
        else:
            result["violations"].append("Missing Cost Estimates section")

        # Check if financial figures are present
        if financial_figures:
            score += 20
            result["checks"].append({
                "rule": f"Financial figures found ({len(financial_figures)} values)",
                "status": "PASS"
            })

            # Check for contingency mention
            full_text = " ".join(
                s.get("text", "") for s in sections.values()
            ).lower()

            if "contingency" in full_text:
                score += 15
                result["checks"].append({
                    "rule": "Contingency provisions mentioned",
                    "status": "PASS"
                })
            else:
                result["warnings"].append("No contingency provisions found in the DPR")

            if "escalation" in full_text:
                score += 15
                result["checks"].append({
                    "rule": "Cost escalation addressed",
                    "status": "PASS"
                })
            else:
                result["recommendations"].append(
                    "Include cost escalation provisions in financial analysis"
                )
        else:
            result["violations"].append("No financial figures found in the DPR")

        result["score"] = min(score, 100)
        return result

    def _check_environmental_compliance(self, analysis: dict) -> dict:
        """Check environmental and social compliance."""
        result = {
            "score": 0,
            "checks": [],
            "violations": [],
            "warnings": [],
            "recommendations": []
        }

        sections = analysis.get("sections", {})
        env_section = sections.get("environmental_impact", {})

        score = 0

        if env_section.get("found", False):
            score += 40
            result["checks"].append({
                "rule": "Environmental Impact section present",
                "status": "PASS"
            })

            text_lower = env_section.get("text", "").lower()

            # Check for EIA components
            eia_keywords = [
                "environmental clearance", "eia", "pollution",
                "waste management", "green", "sustainable",
                "carbon", "emission", "ecology"
            ]
            found_keywords = sum(1 for kw in eia_keywords if kw in text_lower)

            keyword_score = min((found_keywords / len(eia_keywords)) * 30, 30)
            score += keyword_score

            # Social impact checks
            social_keywords = [
                "displacement", "rehabilitation", "livelihood",
                "community", "stakeholder", "consultation",
                "social impact", "gender"
            ]
            social_found = sum(1 for kw in social_keywords if kw in text_lower)
            social_score = min((social_found / len(social_keywords)) * 30, 30)
            score += social_score

            if social_found == 0:
                result["warnings"].append("No social impact assessment found")
        else:
            result["violations"].append("Missing Environmental & Social Impact Assessment")
            result["recommendations"].append(
                "Add Environmental & Social Impact Assessment section — "
                "required for government project approvals"
            )

        result["score"] = min(round(score), 100)
        return result
