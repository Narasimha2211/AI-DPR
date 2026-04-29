import asyncio
from loguru import logger
from sqlalchemy.orm import Session
from app.services.websocket_manager import manager
from app.services import postgres_db_service as db_service
from app.services.analysis_service import analyze_document
from app.services.scoring_service import generate_quality_report
from app.services.risk_service import assess_risk
from app.services.learning_service import extract_training_sample
from config.postgres_config import SessionLocal


def _transform_analysis_for_frontend(analysis_result: dict) -> dict:
    """Transform analysis result to frontend format with nlp_analysis wrapper and summary."""
    sections = analysis_result.get("sections", {})
    entities = analysis_result.get("entities", {})
    text_stats = analysis_result.get("text_statistics", {})
    financial_figures = analysis_result.get("financial_figures", [])
    
    # Count sections found
    sections_found = sum(1 for s in sections.values() if isinstance(s, dict) and s.get("found", False)) if isinstance(sections, dict) else 0
    sections_total = len(sections) if isinstance(sections, dict) else 14
    
    # Count entities
    organizations = entities.get("organizations", []) if isinstance(entities, dict) else []
    locations = entities.get("locations", []) if isinstance(entities, dict) else []
    dates = entities.get("dates", []) if isinstance(entities, dict) else []
    
    # Count financial figures
    total_financial = len(financial_figures) if isinstance(financial_figures, list) else 0
    
    # Create frontend format with summary
    return {
        "nlp_analysis": {
            "summary": {
                "sections_found": sections_found,
                "sections_total": sections_total,
                "total_financial_figures": total_financial,
                "organizations_count": len(organizations),
                "locations_count": len(locations),
                "dates_count": len(dates),
            },
            "sections": sections,
            "entities": {
                "organizations": organizations,
                "locations": locations,
                "dates": dates,
            },
            "text_statistics": text_stats,
            "financial_figures": financial_figures,
        },
        "total_pages": analysis_result.get("raw_text_length", 0) // 3000 + 1,  # Rough estimate
    }


def _wrap_quality_report(quality_report: dict) -> dict:
    """Wrap quality report in the format the frontend expects."""
    return {
        "quality_report": quality_report,
        # Flatten individual scores for easier access
        "scores": quality_report.get("individual_scores", {}),
        "grade": quality_report.get("grade", "-"),
        "composite_score": quality_report.get("composite_score", 0),
    }


def _wrap_risk_report(risk_report: dict) -> dict:
    """Wrap risk report in the format the frontend expects."""
    return {
        "risk_report": risk_report,
        # Ensure risk_summary is present
        "risk_summary": risk_report.get("risk_summary", {}),
    }


async def run_full_pipeline(document_id: str, file_path: str, state: str, project_type: str, project_cost_crores: float):
    db: Session = SessionLocal()
    doc_id = int(document_id)
    
    # Step 1: Upload step completed
    await manager.broadcast_progress(document_id, {"step": "uploaded", "progress": 20, "message": "📤 Upload complete. Initializing analysis..."})
    await asyncio.sleep(1)

    try:
        # Step 2: NLP Analysis
        await manager.broadcast_progress(document_id, {"step": "analysis", "progress": 40, "message": "🧠 Running Deep NLP Analysis..."})
        analysis_result = await analyze_document(file_path, state)
        
        # Save the analysis to PostgreSQL
        db_service.save_analysis(db, doc_id, analysis_result)
        
        # Step 3: Quality Scoring
        await manager.broadcast_progress(document_id, {"step": "scoring", "progress": 65, "message": "⭐ Calculating Quality Grade..."})
        quality_report = await generate_quality_report(analysis_result, state, project_type)
        db_service.save_quality_score(db, doc_id, quality_report)
        
        # Step 4: Risk Prediction
        await manager.broadcast_progress(document_id, {"step": "risk", "progress": 85, "message": "🎯 Predicting Risk Factors..."})
        risk_report = await assess_risk(analysis_result, quality_report, state, project_type, project_cost_crores)
        db_service.save_risk_assessment(db, doc_id, risk_report)
        
        # Step 5: Extract & Save Training Data (for AI Learning)
        # This creates a training sample from the analysis for incremental learning
        training_sample = extract_training_sample(
            nlp_analysis=analysis_result,
            quality_report=quality_report,
            risk_report=risk_report,
            state=state,
            project_type=project_type,
            project_cost=project_cost_crores,
        )
        db_service.save_training_data(
            db=db,
            document_id=doc_id,
            features=training_sample.get("features", {}),
            labels=training_sample.get("labels", {}),
            metadata_info=training_sample.get("metadata", {}),
        )
        logger.info(f"✅ Training data saved for document {doc_id}")
        
        # Step 6: Finalizing - Transform data for frontend
        analysis_for_frontend = _transform_analysis_for_frontend(analysis_result)
        quality_for_frontend = _wrap_quality_report(quality_report)
        risk_for_frontend = _wrap_risk_report(risk_report)
        
        await manager.broadcast_progress(document_id, {"step": "done", "progress": 100, "message": "✅ Analysis Completed Successfully", "data": {
            "analysis": analysis_for_frontend,
            "quality": quality_for_frontend,
            "risk": risk_for_frontend
        }})
        
    except Exception as e:
        logger.error(f"Pipeline failed for doc {document_id}: {e}")
        await manager.broadcast_progress(document_id, {"step": "error", "progress": 100, "message": f"❌ Pipeline Failed: {str(e)}"})
    
    finally:
        db.close()
