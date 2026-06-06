## 2024-06-06 - Missing Authentication on Websocket Endpoints
**Vulnerability:** The `/ws/session/{room_id}` websocket endpoint accepted connections without verifying the session token, exposing internal event bus data to unauthenticated clients.
**Learning:** In FastAPI, global dependencies (like `get_current_user` on HTTP routes) do not automatically apply to websocket connections unless explicitly injected or checked during the connection lifecycle.
**Prevention:** Always extract and manually verify authentication tokens (e.g. from cookies via `websocket.cookies.get`) in the `websocket` endpoint function before calling `await websocket.accept()`. If unauthorized, use `await websocket.close(code=1008)` to cleanly reject the connection.
