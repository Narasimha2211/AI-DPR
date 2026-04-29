# ============================================
# Scoring Service - Quality Scoring
# Wrapper for quality scoring
# ============================================

from typing import Optional
from loguru import logger
from app.modules.quality_scorer.quality_report import QualityScorer


async def generate_quality_report(
    analysis_result: dict,
    state: Optional[str] = None,
    project_type: Optional[str] = None
) -> dict:
    """
    Generate quality report from analysis results.
    
    Args:
        analysis_result: Output from analyze_document
        state: Indian state name
        project_type: Type of project
    
    Returns:
        dict containing quality report
    """
    try:
        logger.info("Starting quality assessment")
        
        scorer = QualityScorer()
        
        # Ensure sections is a dict (not a list)
        sections = analysis_result.get("sections", {})
        if isinstance(sections, list):
            sections = {}
        
        # Pass empty dict for table_analysis (tables is a list, not a dict)
        quality_report = scorer.score_dpr(
            nlp_analysis=analysis_result,
            table_analysis={},  # tables are extracted separately, pass empty dict
            state=state,
            project_type=project_type
        )
        
        logger.info(f"Quality assessment complete. Grade: {quality_report.get('grade', 'N/A')}")
        return quality_report
        
    except Exception as e:
        logger.error(f"Quality assessment failed: {e}")
        raise
