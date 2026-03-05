# ============================================
# Seed Reference Data into PostgreSQL
# Runs on first startup – idempotent
# ============================================

from sqlalchemy import select
from loguru import logger

from app.models.database import async_session
from app.models.db_models import (
    State, DPRSectionDef, ComplianceRule,
    ScoringWeight, GradeDefinition,
)

# ─── Indian States ───
_STATES = [
    # (name, code, is_mdoner, region, terrain, risk_factor)
    ("Andhra Pradesh",      "AP",  False, "South",     "Coastal/Plains", 4.5),
    ("Arunachal Pradesh",   "AR",  True,  "Northeast", "Mountainous",    7.5),
    ("Assam",               "AS",  True,  "Northeast", "Plains/Hills",   6.5),
    ("Bihar",               "BR",  False, "East",      "Plains",         6.0),
    ("Chhattisgarh",        "CG",  False, "Central",   "Forested",       5.5),
    ("Goa",                 "GA",  False, "West",      "Coastal",        3.5),
    ("Gujarat",             "GJ",  False, "West",      "Coastal/Arid",   4.5),
    ("Haryana",             "HR",  False, "North",     "Plains",         4.0),
    ("Himachal Pradesh",    "HP",  False, "North",     "Mountainous",    6.0),
    ("Jharkhand",           "JH",  False, "East",      "Forested/Hills", 6.0),
    ("Karnataka",           "KA",  False, "South",     "Deccan Plateau", 4.0),
    ("Kerala",              "KL",  False, "South",     "Coastal/Hills",  4.5),
    ("Madhya Pradesh",      "MP",  False, "Central",   "Plateau",        5.0),
    ("Maharashtra",         "MH",  False, "West",      "Mixed",          4.5),
    ("Manipur",             "MN",  True,  "Northeast", "Hills",          7.0),
    ("Meghalaya",           "ML",  True,  "Northeast", "Hills/Plateau",  7.0),
    ("Mizoram",             "MZ",  True,  "Northeast", "Mountainous",    7.5),
    ("Nagaland",            "NL",  True,  "Northeast", "Mountainous",    7.5),
    ("Odisha",              "OD",  False, "East",      "Coastal/Plains", 5.5),
    ("Punjab",              "PB",  False, "North",     "Plains",         4.0),
    ("Rajasthan",           "RJ",  False, "West",      "Arid/Desert",    5.5),
    ("Sikkim",              "SK",  True,  "Northeast", "Mountainous",    7.0),
    ("Tamil Nadu",          "TN",  False, "South",     "Coastal/Plains", 4.5),
    ("Telangana",           "TS",  False, "South",     "Deccan Plateau", 4.0),
    ("Tripura",             "TR",  True,  "Northeast", "Hills/Plains",   6.5),
    ("Uttar Pradesh",       "UP",  False, "North",     "Plains",         5.0),
    ("Uttarakhand",         "UK",  False, "North",     "Mountainous",    6.0),
    ("West Bengal",         "WB",  False, "East",      "Plains/Coastal", 5.0),
]

_MDONER_PROVISIONS = [
    "90:10 Central-State funding pattern",
    "Special Category State provisions",
    "Border Area Development Programme eligibility",
    "Flood/Landslide vulnerability assessment",
    "Tribal community impact assessment",
]
_MDONER_SECTORS = [
    "Connectivity", "Tourism", "Power & Energy",
    "Horticulture", "Education", "Health",
    "Water Resources", "Skill Development",
]
_MDONER_EXTRA = [
    "Terrain & accessibility assessment",
    "Tribal/community consultation documentation",
    "Northeast-specific challenge mitigation plan",
    "Connectivity infrastructure baseline",
]

# ─── DPR Sections ───
_SECTIONS = [
    ("Executive Summary",                            "executive_summary",          100, 1.0,  True, 1),
    ("Project Background & Justification",           "project_background",         200, 1.0,  True, 2),
    ("Project Objectives",                           "project_objectives",         100, 1.0,  True, 3),
    ("Scope of Work",                                "scope_of_work",              150, 1.0,  True, 4),
    ("Technical Feasibility",                        "technical_feasibility",      200, 1.2,  True, 5),
    ("Financial Analysis",                           "financial_analysis",         200, 1.2,  True, 6),
    ("Cost Estimates",                               "cost_estimates",             150, 1.2,  True, 7),
    ("Implementation Schedule",                      "implementation_schedule",    100, 1.0,  True, 8),
    ("Institutional Framework",                      "institutional_framework",    100, 0.8,  True, 9),
    ("Environmental & Social Impact Assessment",     "esia",                       200, 1.0,  True, 10),
    ("Risk Assessment & Mitigation",                 "risk_assessment",            150, 1.0,  True, 11),
    ("Monitoring & Evaluation Framework",            "monitoring_evaluation",      100, 0.8,  True, 12),
    ("Sustainability Plan",                          "sustainability_plan",        100, 0.8,  True, 13),
    ("Annexures & Supporting Documents",             "annexures",                   50, 0.5, False, 14),
]

# ─── Scoring Weights ───
_WEIGHTS = [
    ("Section Completeness", 0.25, "Presence and depth of all required DPR sections"),
    ("Technical Depth",      0.20, "Quality of technical analysis, specifications, and data"),
    ("Financial Accuracy",   0.20, "Completeness of cost estimates, budget tables, and financial analysis"),
    ("Compliance",           0.20, "Adherence to central and state government DPR guidelines"),
    ("Risk Assessment",      0.15, "Quality of risk identification, analysis, and mitigation planning"),
]

# ─── Grades ───
_GRADES = [
    ("A+", 90, 100, "Excellent – Ready for approval"),
    ("A",  80,  89, "Very Good – Minor improvements recommended"),
    ("B+", 70,  79, "Good – Some improvements needed"),
    ("B",  60,  69, "Satisfactory – Multiple improvements needed"),
    ("C",  50,  59, "Below Average – Significant revision required"),
    ("D",  40,  49, "Poor – Major revision required"),
    ("F",   0,  39, "Fail – Complete rework needed"),
]

# ─── Compliance Rules ───
_RULES = [
    ("GOV-001", "documentation", "Mandatory Sections Present",
     "All mandatory DPR sections must be included", "error", "all"),
    ("GOV-002", "financial", "Cost Estimate Completeness",
     "Detailed cost breakdowns required for projects above 10 crores", "error", "all"),
    ("GOV-003", "environmental", "EIA Clearance Reference",
     "Environmental Impact Assessment reference must be present", "warning", "all"),
    ("GOV-004", "risk", "Risk Mitigation Plan",
     "At least 3 risk mitigation strategies must be documented", "warning", "all"),
    ("GOV-005", "schedule", "Implementation Timeline",
     "Project milestones and Gantt chart or equivalent required", "warning", "all"),
    ("NER-001", "mdoner", "Tribal Impact Assessment",
     "Tribal community impact analysis required for NE states", "error", "mdoner"),
    ("NER-002", "mdoner", "Terrain Assessment",
     "Detailed terrain and accessibility study required", "warning", "mdoner"),
    ("NER-003", "mdoner", "Funding Pattern",
     "90:10 central-state funding pattern documentation", "error", "mdoner"),
]


async def seed_reference_data():
    """Populate reference tables if they are empty. Idempotent."""
    async with async_session() as session:
        async with session.begin():
            # ── States ──
            existing = (await session.execute(select(State.id).limit(1))).first()
            if not existing:
                for name, code, mdoner, region, terrain, rf in _STATES:
                    extras = {}
                    if mdoner:
                        extras = {
                            "special_provisions": _MDONER_PROVISIONS,
                            "priority_sectors": _MDONER_SECTORS,
                            "additional_requirements": _MDONER_EXTRA,
                        }
                    session.add(State(
                        name=name, code=code, is_mdoner=mdoner,
                        region=region, terrain=terrain, risk_factor=rf,
                        **extras,
                    ))
                logger.info(f"  Seeded {len(_STATES)} states")

            # ── DPR Sections ──
            existing = (await session.execute(select(DPRSectionDef.id).limit(1))).first()
            if not existing:
                for name, key, min_wc, weight, mandatory, idx in _SECTIONS:
                    session.add(DPRSectionDef(
                        name=name, key=key, min_word_count=min_wc,
                        weight=weight, is_mandatory=mandatory, order_index=idx,
                    ))
                logger.info(f"  Seeded {len(_SECTIONS)} DPR sections")

            # ── Scoring Weights ──
            existing = (await session.execute(select(ScoringWeight.id).limit(1))).first()
            if not existing:
                for criterion, weight, desc in _WEIGHTS:
                    session.add(ScoringWeight(
                        criterion=criterion, weight=weight, description=desc,
                    ))
                logger.info(f"  Seeded {len(_WEIGHTS)} scoring weights")

            # ── Grades ──
            existing = (await session.execute(select(GradeDefinition.id).limit(1))).first()
            if not existing:
                for grade, lo, hi, desc in _GRADES:
                    session.add(GradeDefinition(
                        grade=grade, min_score=lo, max_score=hi, description=desc,
                    ))
                logger.info(f"  Seeded {len(_GRADES)} grade definitions")

            # ── Compliance Rules ──
            existing = (await session.execute(select(ComplianceRule.id).limit(1))).first()
            if not existing:
                for code, cat, title, desc, sev, applies in _RULES:
                    session.add(ComplianceRule(
                        rule_code=code, category=cat, title=title,
                        description=desc, severity=sev, applies_to=applies,
                    ))
                logger.info(f"  Seeded {len(_RULES)} compliance rules")
