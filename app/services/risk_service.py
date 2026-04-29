# ============================================
# Risk Service - Risk Prediction
# Wrapper for risk analysis
# ============================================

from typing import Optional
from loguru import logger
from app.modules.risk_predictor.risk_analyzer import RiskAnalyzer


async def assess_risk(
    analysis_result: dict,
    quality_report: dict,
    state: Optional[str] = None,
    project_type: Optional[str] = None,
    project_cost_crores: Optional[float] = None
) -> dict:
    """
    Assess risk factors for the project.
    
    Args:
        analysis_result: Output from analyze_document
        quality_report: Output from generate_quality_report
        state: Indian state name
        project_type: Type of project
        project_cost_crores: Project cost in crores
    
    Returns:
        dict containing risk assessment
    """
    try:
        logger.info("Starting risk assessment")
        
        analyzer = RiskAnalyzer()
        
        # Assess risk
        risk_report = analyzer.analyze_risk(
            nlp_analysis=analysis_result,
            quality_score=quality_report,
            state=state,
            project_type=project_type,
            project_cost=project_cost_crores or 0
        )
        
        logger.info(f"Risk assessment complete. Overall Risk: {risk_report.get('overall_risk_level', 'N/A')}")
        return risk_report
        
    except Exception as e:
        logger.error(f"Risk assessment failed: {e}")
        raise
