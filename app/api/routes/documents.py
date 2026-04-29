# ============================================
# Documents API Routes – Document Management & History
# ============================================

from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException, Path as FastAPIPath
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services import postgres_db_service as db_service
from app.api.dependencies import get_current_user
from config.postgres_config import get_db

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.get("/list")
async def list_documents_endpoint(
    state: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch a list of all documents with their risk and quality summary.
    Allows filtering by state.
    """
    try:
        # Fetch docs from db service
        docs = db_service.list_documents(
            db=db, state_name=state, limit=limit, offset=offset
        )
        # Format the response
        result = []
        for d in docs:
            result.append({
                "id": d.id,
                "file_name": getattr(d, 'file_name', 'Unknown'),
                "state_name": getattr(d, 'state_name', 'Unknown'),
                "project_type": getattr(d, 'project_type', 'Unknown'),
                "upload_date": getattr(d, 'upload_date', None),
                "processing_status": getattr(d, 'processing_status', 'Unknown'),
                "grade": getattr(d.quality_score, 'grade', '-') if hasattr(d, 'quality_score') and d.quality_score else '-',
                "risk_level": getattr(d.risk_assessment, 'overall_risk_level', '-') if hasattr(d, 'risk_assessment') and d.risk_assessment else '-'
            })
        return {"documents": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/{document_id}/pdf")
async def export_document_pdf(
    document_id: int = FastAPIPath(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a formatted PDF report for a given document.
    """
    from app.services.pdf_generator import generate_dpr_pdf
    
    try:
        pdf_bytes = generate_dpr_pdf(document_id)
        
        # We need a fallback file name
        doc = db_service.get_document(db=db, document_id=document_id)
        file_name = getattr(doc, 'file_name', f"dpr_report_{document_id}").replace('.pdf', '')
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="AI_Evaluation_{file_name}.pdf"'}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
