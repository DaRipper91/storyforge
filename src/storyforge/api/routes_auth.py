"""
Google OAuth2 Authentication.

Uses Google Identity Services (GIS) ID Tokens.
Backend verifies the token, creates a local session, and sets an HttpOnly cookie.
"""
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from google.oauth2 import id_token
from google.auth.transport import requests
from jose import jwt, JWTError
from pydantic import BaseModel
import time

from storyforge.config import settings
from storyforge.api.deps import get_state_manager
from storyforge.core.state_manager import StateManager

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthToken(BaseModel):
    token: str


class UserSession(BaseModel):
    email: str
    name: str
    picture: str | None = None
    exp: int


def create_session_token(id_info: dict) -> str:
    """Create a local JWT from Google's verified info."""
    payload = {
        "sub": id_info["sub"],  # Unique Google ID
        "email": id_info.get("email"),
        "name": id_info.get("name"),
        "picture": id_info.get("picture"),
        "exp": int(time.time()) + (24 * 3600)  # 24 hour session
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/google")
async def google_auth(body: AuthToken, response: Response):
    """Verify Google ID token and set session cookie."""
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google Auth not configured on server")

    try:
        # Verify the ID token from Google
        id_info = id_token.verify_oauth2_token(
            body.token, requests.Request(), settings.google_client_id
        )

        # Create our own session JWT
        token = create_session_token(id_info)

        # Set HttpOnly Cookie
        response.set_cookie(
            key="storyforge_session",
            value=token,
            httponly=True,
            secure=False,  # Set to True if using HTTPS
            samesite="lax",
            max_age=24 * 3600
        )
        
        return {
            "status": "ok",
            "user": {
                "name": id_info.get("name"),
                "email": id_info.get("email"),
                "picture": id_info.get("picture")
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")


@router.get("/me")
async def get_me(request: Request):
    """Return current user session info from cookie."""
    token = request.cookies.get("storyforge_session")
    if not token:
        return {"authenticated": False}
    
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return {"authenticated": True, "user": payload}
    except JWTError:
        return {"authenticated": False}


@router.post("/logout")
async def logout(response: Response):
    """Clear the session cookie."""
    response.delete_cookie("storyforge_session")
    return {"status": "ok"}
