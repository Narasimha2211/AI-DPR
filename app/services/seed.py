# ============================================
# Seed Reference Data into PostgreSQL
# ============================================

from loguru import logger


async def seed_reference_data():
    """Seed initial reference data if collections are empty."""
    await _seed_states()
    await _seed_sections()
    await _seed_scoring_weights()
    await _seed_grade_definitions()
    await _seed_compliance_rules()
    await _seed_admin_user()
    logger.info("✅ PostgreSQL reference data verified / seeded")


async def _seed_states():
    if _has_docs(col):
        return
    logger.info("Seeding states…")
    states = [
        {"name": "Andhra Pradesh", "code": "AP", "is_mdoner": False, "region": "South", "terrain": "mixed", "risk_factor": 4.0},
        {"name": "Arunachal Pradesh", "code": "AR", "is_mdoner": True, "region": "North East", "terrain": "mountainous", "risk_factor": 8.0,
         "special_provisions": {"funding_pattern": "90:10", "tribal_provisions": True},
         "priority_sectors": ["connectivity", "education", "health"]},
        {"name": "Assam", "code": "AS", "is_mdoner": True, "region": "North East", "terrain": "flood-plain", "risk_factor": 7.0,
         "special_provisions": {"funding_pattern": "90:10", "flood_risk": True},
         "priority_sectors": ["flood_management", "connectivity", "industry"]},
        {"name": "Bihar", "code": "BR", "is_mdoner": False, "region": "East", "terrain": "plain", "risk_factor": 5.0},
        {"name": "Chhattisgarh", "code": "CG", "is_mdoner": False, "region": "Central", "terrain": "mixed", "risk_factor": 5.0},
        {"name": "Goa", "code": "GA", "is_mdoner": False, "region": "West", "terrain": "plain", "risk_factor": 2.0},
        {"name": "Gujarat", "code": "GJ", "is_mdoner": False, "region": "West", "terrain": "mixed", "risk_factor": 3.0},
        {"name": "Haryana", "code": "HR", "is_mdoner": False, "region": "North", "terrain": "plain", "risk_factor": 3.0},
        {"name": "Himachal Pradesh", "code": "HP", "is_mdoner": False, "region": "North", "terrain": "hilly", "risk_factor": 6.0},
        {"name": "Jharkhand", "code": "JH", "is_mdoner": False, "region": "East", "terrain": "plateau", "risk_factor": 5.0},
        {"name": "Karnataka", "code": "KA", "is_mdoner": False, "region": "South", "terrain": "mixed", "risk_factor": 3.0},
        {"name": "Kerala", "code": "KL", "is_mdoner": False, "region": "South", "terrain": "mixed", "risk_factor": 4.0},
        {"name": "Madhya Pradesh", "code": "MP", "is_mdoner": False, "region": "Central", "terrain": "mixed", "risk_factor": 5.0},
        {"name": "Maharashtra", "code": "MH", "is_mdoner": False, "region": "West", "terrain": "mixed", "risk_factor": 3.0},
        {"name": "Manipur", "code": "MN", "is_mdoner": True, "region": "North East", "terrain": "hilly", "risk_factor": 7.5,
         "special_provisions": {"funding_pattern": "90:10", "ethnic_harmony": True},
         "priority_sectors": ["connectivity", "sports", "handicrafts"]},
        {"name": "Meghalaya", "code": "ML", "is_mdoner": True, "region": "North East", "terrain": "hilly", "risk_factor": 7.0,
         "special_provisions": {"funding_pattern": "90:10", "sixth_schedule": True},
         "priority_sectors": ["tourism", "mining", "agriculture"]},
        {"name": "Mizoram", "code": "MZ", "is_mdoner": True, "region": "North East", "terrain": "mountainous", "risk_factor": 7.5,
         "special_provisions": {"funding_pattern": "90:10"},
         "priority_sectors": ["bamboo", "connectivity", "tourism"]},
        {"name": "Nagaland", "code": "NL", "is_mdoner": True, "region": "North East", "terrain": "mountainous", "risk_factor": 8.0,
         "special_provisions": {"funding_pattern": "90:10", "tribal_council": True},
         "priority_sectors": ["connectivity", "tourism", "horticulture"]},
        {"name": "Odisha", "code": "OD", "is_mdoner": False, "region": "East", "terrain": "mixed", "risk_factor": 5.0},
        {"name": "Punjab", "code": "PB", "is_mdoner": False, "region": "North", "terrain": "plain", "risk_factor": 3.0},
        {"name": "Rajasthan", "code": "RJ", "is_mdoner": False, "region": "West", "terrain": "plain", "risk_factor": 4.0},
        {"name": "Sikkim", "code": "SK", "is_mdoner": True, "region": "North East", "terrain": "mountainous", "risk_factor": 7.0,
         "special_provisions": {"funding_pattern": "90:10", "ecological_sensitivity": True},
         "priority_sectors": ["tourism", "organic_farming", "hydropower"]},
        {"name": "Tamil Nadu", "code": "TN", "is_mdoner": False, "region": "South", "terrain": "mixed", "risk_factor": 3.0},
        {"name": "Telangana", "code": "TG", "is_mdoner": False, "region": "South", "terrain": "plateau", "risk_factor": 3.0},
        {"name": "Tripura", "code": "TR", "is_mdoner": True, "region": "North East", "terrain": "hilly", "risk_factor": 6.5,
         "special_provisions": {"funding_pattern": "90:10", "border_area": True},
         "priority_sectors": ["rubber", "connectivity", "IT"]},
        {"name": "Uttar Pradesh", "code": "UP", "is_mdoner": False, "region": "North", "terrain": "plain", "risk_factor": 5.0},
        {"name": "Uttarakhand", "code": "UK", "is_mdoner": False, "region": "North", "terrain": "mountainous", "risk_factor": 6.0},
        {"name": "West Bengal", "code": "WB", "is_mdoner": False, "region": "East", "terrain": "mixed", "risk_factor": 4.0},
    ]
    batch = db.batch()
    for s in states:
        batch.set(col.document(s["name"]), s)
    batch.commit()


async def _seed_sections():
    col = db.collection("dpr_section_defs")
    if _has_docs(col):
        return
    logger.info("Seeding DPR section definitions…")
    sections = [
        {"key": "executive_summary", "name": "Executive Summary", "min_word_count": 200, "weight": 1.0, "is_mandatory": True, "order_index": 1},
        {"key": "project_background", "name": "Project Background & Justification", "min_word_count": 300, "weight": 1.0, "is_mandatory": True, "order_index": 2},
        {"key": "objectives", "name": "Project Objectives", "min_word_count": 150, "weight": 0.8, "is_mandatory": True, "order_index": 3},
        {"key": "scope_of_work", "name": "Scope of Work", "min_word_count": 300, "weight": 1.0, "is_mandatory": True, "order_index": 4},
        {"key": "technical_feasibility", "name": "Technical Feasibility", "min_word_count": 500, "weight": 1.2, "is_mandatory": True, "order_index": 5},
        {"key": "financial_analysis", "name": "Financial Analysis", "min_word_count": 400, "weight": 1.2, "is_mandatory": True, "order_index": 6},
        {"key": "cost_estimates", "name": "Cost Estimates", "min_word_count": 300, "weight": 1.2, "is_mandatory": True, "order_index": 7},
        {"key": "implementation_schedule", "name": "Implementation Schedule", "min_word_count": 200, "weight": 1.0, "is_mandatory": True, "order_index": 8},
        {"key": "institutional_framework", "name": "Institutional Framework", "min_word_count": 200, "weight": 0.8, "is_mandatory": True, "order_index": 9},
        {"key": "environmental_impact", "name": "Environmental & Social Impact Assessment", "min_word_count": 300, "weight": 1.0, "is_mandatory": True, "order_index": 10},
        {"key": "risk_assessment", "name": "Risk Assessment & Mitigation", "min_word_count": 250, "weight": 1.0, "is_mandatory": True, "order_index": 11},
        {"key": "monitoring_evaluation", "name": "Monitoring & Evaluation Framework", "min_word_count": 200, "weight": 0.8, "is_mandatory": True, "order_index": 12},
        {"key": "sustainability", "name": "Sustainability Plan", "min_word_count": 200, "weight": 0.8, "is_mandatory": True, "order_index": 13},
        {"key": "annexures", "name": "Annexures & Supporting Documents", "min_word_count": 100, "weight": 0.5, "is_mandatory": False, "order_index": 14},
    ]
    batch = db.batch()
    for s in sections:
        batch.set(col.document(s["key"]), s)
    batch.commit()


async def _seed_scoring_weights():
    col = db.collection("scoring_weights")
    if _has_docs(col):
        return
    logger.info("Seeding scoring weights…")
    weights = [
        {"criterion": "section_completeness", "weight": 0.25, "description": "Presence and depth of required DPR sections", "is_active": True},
        {"criterion": "technical_depth", "weight": 0.20, "description": "Technical detail and quantitative data quality", "is_active": True},
        {"criterion": "financial_accuracy", "weight": 0.20, "description": "Financial analysis completeness and accuracy", "is_active": True},
        {"criterion": "compliance", "weight": 0.20, "description": "Government guideline compliance", "is_active": True},
        {"criterion": "risk_assessment", "weight": 0.15, "description": "Risk identification and mitigation quality", "is_active": True},
    ]
    batch = db.batch()
    for w in weights:
        batch.set(col.document(w["criterion"]), w)
    batch.commit()


async def _seed_grade_definitions():
    col = db.collection("grade_definitions")
    if _has_docs(col):
        return
    logger.info("Seeding grade definitions…")
    grades = [
        {"grade": "A+", "min_score": 90, "max_score": 100, "description": "Excellent — Ready for approval", "is_active": True},
        {"grade": "A", "min_score": 80, "max_score": 89, "description": "Very Good — Minor improvements recommended", "is_active": True},
        {"grade": "B+", "min_score": 70, "max_score": 79, "description": "Good — Some improvements needed", "is_active": True},
        {"grade": "B", "min_score": 60, "max_score": 69, "description": "Satisfactory — Multiple improvements needed", "is_active": True},
        {"grade": "C", "min_score": 50, "max_score": 59, "description": "Below Average — Significant revision required", "is_active": True},
        {"grade": "D", "min_score": 40, "max_score": 49, "description": "Poor — Major revision required", "is_active": True},
        {"grade": "F", "min_score": 0, "max_score": 39, "description": "Fail — Complete rework needed", "is_active": True},
    ]
    batch = db.batch()
    for g in grades:
        batch.set(col.document(g["grade"]), g)
    batch.commit()


async def _seed_compliance_rules():
    col = db.collection("compliance_rules")
    if _has_docs(col):
        return
    logger.info("Seeding compliance rules…")
    rules = [
        {"rule_code": "GOV-001", "category": "central", "title": "Executive Summary Required", "severity": "critical", "applies_to": "all", "is_active": True},
        {"rule_code": "GOV-002", "category": "central", "title": "Financial Analysis Required", "severity": "critical", "applies_to": "all", "is_active": True},
        {"rule_code": "GOV-003", "category": "central", "title": "Cost Estimates Required", "severity": "critical", "applies_to": "all", "is_active": True},
        {"rule_code": "GOV-004", "category": "central", "title": "Implementation Schedule Required", "severity": "warning", "applies_to": "all", "is_active": True},
        {"rule_code": "GOV-005", "category": "central", "title": "Environmental Impact Required", "severity": "warning", "applies_to": "all", "is_active": True},
        {"rule_code": "NER-001", "category": "ner", "title": "90:10 Funding Pattern Declaration", "severity": "critical", "applies_to": "mdoner", "is_active": True},
        {"rule_code": "NER-002", "category": "ner", "title": "Tribal Impact Assessment", "severity": "critical", "applies_to": "mdoner", "is_active": True},
        {"rule_code": "NER-003", "category": "ner", "title": "State-specific Provisions", "severity": "warning", "applies_to": "mdoner", "is_active": True},
    ]
    batch = db.batch()
    for r in rules:
        batch.set(col.document(r["rule_code"]), r)
    batch.commit()


def _has_docs(col_ref) -> bool:
    """Check if collection already has documents (idempotent seeding)."""
    return len(list(col_ref.limit(1).stream())) > 0

async def _seed_admin_user():
    col = db.collection("users")
    if _has_docs(col):
        return
    logger.info("Seeding initial admin user…")
    from app.services import auth_service
    from config.settings import settings
    try:
        await auth_service.create_user(
            email="admin@aidpr.gov.in",
            password=settings.ADMIN_PASSWORD,
            name="System Administrator",
            role="Admin"
        )
    except ValueError:
        pass  # User already exists
