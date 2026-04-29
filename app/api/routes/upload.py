# ============================================
# Upload API Routes – PostgreSQL backed
# ============================================

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Depends, BackgroundTasks
from loguru import logger
from sqlalchemy.orm import Session

from config.settings import settings
from config.postgres_config import get_db
from app.services import postgres_db_service as db_service
from app.api.dependencies import get_current_analyst_user, get_current_user
from app.api.security import sanitize_filename
from app.services.pipeline_service import run_full_pipeline

router = APIRouter(prefix="/api/upload", tags=["Upload"])


@router.post("/dpr")
async def upload_dpr(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    state: str = Form(None),
    project_type: str = Form(None),
    project_cost_crores: float = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload a DPR document for analysis."""
    
    # Validate file format
    file_ext = Path(file.filename or "unknown").suffix.lower()
    if file_ext not in settings.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_ext}. "
                   f"Supported: {', '.join(settings.SUPPORTED_FORMATS)}"
        )

    # Read and validate file size
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size_mb:.1f}MB. Max: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Save file to disk with sanitized filename
    unique_id = str(uuid.uuid4())[:8]
    safe_filename = f"{unique_id}_{sanitize_filename(file.filename or 'unknown')}"
    file_path = settings.UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Save to PostgreSQL
    doc = db_service.create_document(
        db=db,
        filename=file.filename or "unknown",
        file_path=str(file_path),
        state_name=state,
        project_type=project_type,
        project_cost_crores=project_cost_crores or 0,
        file_size_mb=round(file_size_mb, 2),
    )

    doc_id = doc.id
    logger.info(f"DPR uploaded: {file.filename} ({file_size_mb:.1f}MB) → doc.id={doc_id}")

    # Trigger background pipeline
    background_tasks.add_task(
        run_full_pipeline,
        document_id=str(doc_id),
        file_path=str(file_path),
        state=state,
        project_type=project_type,
        project_cost_crores=project_cost_crores or 0
    )

    return {
        "status": "success",
        "document_id": doc_id,
        "file_name": file.filename,
        "message": "Upload complete. Analysis pipeline started.",
        "websocket_url": f"/api/ws/progress/{doc_id}"
    }


@router.get("/documents")
async def list_documents_route(
    state: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List uploaded documents with optional state filter."""
    docs = db_service.list_documents(db=db, state_name=state, limit=limit, offset=offset)
    return {
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "state": d.state_name,
                "status": d.processing_status,
                "upload_date": d.upload_date,
            }
            for d in docs
        ],
        "count": len(docs),
    }


@router.get("/documents/{document_id}")
async def get_document_detail(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Get full document record with all related analysis results."""
    doc = db_service.get_document(db=db, document_id=document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    result: dict = {
        "id": doc.id,
        "file_name": doc.filename,
        "state": doc.state_name,
        "project_name": getattr(doc, 'project_name', None),
        "project_type": getattr(doc, 'project_type', None),
        "project_cost_crores": getattr(doc, 'project_cost_crores', None),
        "status": doc.processing_status,
        "upload_date": getattr(doc, 'upload_date', None),
    }
    
    # Get related data
    analysis = db_service.get_analysis(db=db, document_id=document_id)
    if analysis:
        result["analysis_summary"] = {
            "sections_found": analysis.sections_found,
            "sections_total": analysis.sections_total,
            "organizations": analysis.organizations_count,
            "locations": analysis.locations_count,
        }
    
    quality = db_service.get_quality_score(db=db, document_id=document_id)
    if quality:
        result["quality_summary"] = {
            "score": quality.composite_score,
            "grade": quality.grade,
        }
    
    risk = db_service.get_risk_assessment(db=db, document_id=document_id)
    if risk:
        result["risk_summary"] = {
            "level": risk.overall_risk_level,
            "cost_overrun_probability": risk.cost_overrun_probability,
        }
    
    return result


@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats."""
    return {
        "formats": settings.SUPPORTED_FORMATS,
        "max_size_mb": settings.MAX_UPLOAD_SIZE_MB
    }


@router.get("/supported-states")
async def get_supported_states(db: Session = Depends(get_db)):
    """Get list of supported Indian states from PostgreSQL."""
    all_states = db_service.get_all_states(db=db)
    mdoner = db_service.get_mdoner_states(db=db)
    return {
        "all_states": [s.name for s in all_states],
        "mdoner_states": [s.name for s in mdoner],
        "total_states": len(all_states),
        "mdoner_count": len(mdoner),
    }
