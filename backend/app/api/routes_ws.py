"""WebSocket 实时推送。"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..ws.manager import manager

router = APIRouter()

@router.websocket("/realtime")
async def ws_realtime(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
