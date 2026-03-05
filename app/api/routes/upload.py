# ============================================
# Upload API Routes – PostgreSQL backed
# ============================================

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from config.settings import settings
from app.models.database import get_db
from app.services import db_service

router = APIRouter(prefix="/api/upload", tags=["Upload"])


@router.post("/dpr")
async def upload_dpr(
    file: UploadFile = File(...),
    state: str = Form(None),
    project_type: str = Form(None),
    project_name: str = Form(None),
    project_cost_crores: float = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a DPR document for analysis.

    Supports: PDF, DOCX, DOC, TXT, PNG, JPG
    Max size: 50MB
    The uploaded document is persisted in PostgreSQL.
    """
    # Validate file format
    file_ext = Path(file.filename or "unknown").suffix.lower()
    if file_ext not in settings.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_ext}. "
                   f"Supported: {', '.join(settings.SUPPORTED_FORMATS)}"
        )

    # Validate file size
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size_mb:.1f}MB. Max: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Validate state against DB
    if state:
        db_state = await db_service.get_state_by_name(db, state)
        if not db_state:
            all_states = await db_service.get_all_states(db)
            names = [str(s.name) for s in all_states]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state: {state}. Supported: {', '.join(names)}"
            )

    # Save file to disk
    unique_id = str(uuid.uuid4())[:8]
    safe_filename = f"{unique_id}_{file.filename}"
    file_path = settings.UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Persist to PostgreSQL
    doc = await db_service.create_document(
        db,
        file_name=file.filename or "unknown",
        file_path=str(file_path),
        file_size_kb=round(len(content) / 1024, 2),
        file_format=file_ext,
        state_name=state,
        project_type=project_type,
        project_name=project_name,
        project_cost_crores=project_cost_crores,
    )

    doc_id = int(doc.id)
    await db_service.log_action(
        db, action="upload", document_id=doc_id, state=state,
        details={"file_name": file.filename, "size_mb": round(file_size_mb, 2)},
    )

    logger.info(f"DPR uploaded: {file.filename} ({file_size_mb:.1f}MB) → doc.id={doc_id}")

    return {
        "document_id": doc_id,
        "file_name": file.filename,
        "file_path": str(file_path),
        "file_size_mb": round(file_size_mb, 2),
        "state": state,
        "project_type": project_type,
        "project_name": project_name,
        "project_cost_crores": project_cost_crores,
        "status": "uploaded",
        "message": f"DPR '{file.filename}' uploaded successfully. Ready for analysis."
    }


@router.get("/documents")
async def list_documents(
    state: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List uploaded documents with optional state filter."""
    docs = await db_service.list_documents(db, state_name=state, limit=limit, offset=offset)
    return {
        "documents": [
            {
                "id": d.id,
                "file_name": d.file_name,
                "state": d.state_name,
                "project_name": d.project_name,
                "status": d.processing_status,
                "upload_date": d.upload_date.isoformat() if d.upload_date is not None else None,
            }
            for d in docs
        ],
        "count": len(docs),
    }


@router.get("/documents/{document_id}")
async def get_document(document_id: int, db: AsyncSession = Depends(get_db)):
    """Get full document record with all related analysis results."""
    doc = await db_service.get_document_with_relations(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    result: dict = {
        "id": doc.id,
        "file_name": doc.file_name,
        "file_path": doc.file_path,
        "state": doc.state_name,
        "project_name": doc.project_name,
        "project_type": doc.project_type,
        "project_cost_crores": doc.project_cost_crores,
        "status": doc.processing_status,
        "upload_date": doc.upload_date.isoformat() if doc.upload_date is not None else None,
    }
    if doc.analysis:
        result["analysis_summary"] = {
            "sections_found": doc.analysis.sections_found,
            "sections_total": doc.analysis.sections_total,
            "organizations": doc.analysis.organizations_count,
            "locations": doc.analysis.locations_count,
        }
    if doc.quality_score:
        result["quality_summary"] = {
            "score": doc.quality_score.composite_score,
            "grade": doc.quality_score.grade,
        }
    if doc.risk_assessment:
        result["risk_summary"] = {
            "level": doc.risk_assessment.overall_risk_level,
            "cost_overrun_probability": doc.risk_assessment.cost_overrun_probability,
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
async def get_supported_states(db: AsyncSession = Depends(get_db)):
    """Get list of supported Indian states from DB."""
    all_states = await db_service.get_all_states(db)
    mdoner = await db_service.get_mdoner_states(db)
    return {
        "all_states": [s.name for s in all_states],
        "mdoner_states": [s.name for s in mdoner],
        "total_states": len(all_states),
        "mdoner_count": len(mdoner),
    }
