from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from app.services.websocket_manager import manager

router = APIRouter(prefix="/api/ws", tags=["WebSockets"])

@router.websocket("/progress/{document_id}")
async def websocket_progress_endpoint(websocket: WebSocket, document_id: str):
    await manager.connect(websocket, document_id)
    try:
        while True:
            # We don't expect the client to send messages here, just keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, document_id)
        logger.info(f"WebSocket disconnected for document {document_id}")
