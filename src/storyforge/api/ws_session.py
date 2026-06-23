from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import jwt
from jwt import PyJWTError

from storyforge.config import settings
from storyforge.events.bus import event_bus

router = APIRouter()
_connections: set[WebSocket] = set()


@router.websocket("/ws/session/{room_id}")
async def session_ws(websocket: WebSocket, room_id: str):
    token = websocket.cookies.get("storyforge_session")
    if not token:
        await websocket.close(code=1008, reason="Not authenticated")
        return

    try:
        jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except PyJWTError:
        await websocket.close(code=1008, reason="Invalid session")
        return

    await websocket.accept()
    _connections.add(websocket)
    
    # Subscribe to internal event bus
    queue = event_bus.subscribe()
    try:
        while True:
            # We don't use room_id for filtering in MVP,
            # but it's there for future multi-room support.
            diff = await queue.get()
            await websocket.send_json(diff)
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(websocket)
        event_bus.unsubscribe(queue)
