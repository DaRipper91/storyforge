from fastapi import Request, HTTPException
from jose import jwt, JWTError
from storyforge.config import settings
from storyforge.core.state_manager import StateManager


def get_state_manager(request: Request) -> StateManager:
    return request.app.state.state_manager


def get_current_user(request: Request) -> dict:
    """Dependency to get authenticated user from HttpOnly cookie."""
    token = request.cookies.get("storyforge_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session")
