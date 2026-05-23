import os
import stat
from pathlib import Path
from typing import Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Store OAuth token in the user's home data dir, not the project root.
_TOKEN_DIR = Path.home() / ".local" / "share" / "storyforge"
DEFAULT_TOKEN_PATH = str(_TOKEN_DIR / "token.json")

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

def authenticate_google_user(
    token_path: str = DEFAULT_TOKEN_PATH,
    scopes: Optional[list[str]] = None
) -> Dict[Any, Any]:
    """
    Authenticates via Google OAuth2 using credentials from environment variables.

    1. Checks for an existing token.json; refreshes if expired.
    2. If no valid token, runs InstalledAppFlow using client_id/secret from env.
    3. Saves credentials to token.json and returns user profile.
    """
    from storyforge.config import settings  # late import to avoid circular deps

    auth_scopes = scopes or DEFAULT_SCOPES
    creds = None

    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, auth_scopes)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds or not creds.valid:
            if not settings.google_client_id or not settings.google_client_secret:
                raise RuntimeError(
                    "STORYFORGE_GOOGLE_CLIENT_ID and STORYFORGE_GOOGLE_CLIENT_SECRET "
                    "must be set in .env to use desktop OAuth login."
                )

            client_config = {
                "installed": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, auth_scopes)
            creds = flow.run_local_server(port=0)

        token_file = Path(token_path)
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json())
        token_file.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600 — owner only

    try:
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        return user_info
    except Exception as e:
        raise RuntimeError(f"Failed to fetch user info from Google API: {e}")
