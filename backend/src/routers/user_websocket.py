"""WebSocket endpoints for user chat widget (separate from pharmacist dashboard)"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

from routers.pharmacist_dashboard import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["User WebSocket"])


@router.websocket("/chat/{consultation_id}")
async def user_chat_websocket(
    websocket: WebSocket,
    consultation_id: str,
):
    """
    WebSocket connection for user chat widget.
    Subscribes to real-time updates for a specific consultation.

    Endpoint: /api/ws/chat/{consultation_id}
    Used by: ChatContext.jsx (frontend user widget)
    """
    await ws_manager.connect_user(websocket, consultation_id)
    logger.info(
        f"User WebSocket connected for consultation {consultation_id}. Total: {len(ws_manager.active_connections)}"
    )
    try:
        while True:
            data = await websocket.receive_text()
            # Ping/pong keepalive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect_user(websocket, consultation_id)
        logger.info(
            f"User WebSocket disconnected for {consultation_id}. Total: {len(ws_manager.active_connections)}"
        )
    except Exception as e:
        ws_manager.disconnect_user(websocket, consultation_id)
        logger.error(f"User WebSocket error for {consultation_id}: {e}")
