import os
import json
from typing import Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Default scopes required for identifying the user
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

def authenticate_google_user(
    client_secret_path: str = 'client_secret.json', 
    token_path: str = 'token.json',
    scopes: Optional[list[str]] = None
) -> Dict[Any, Any]:
    """
    Authenticates the user using Google OAuth2.
    
    1. Checks for an existing token.json in the root directory.
    2. If valid, loads credentials. If expired but refreshable, refreshes them.
    3. If no valid token exists, initiates InstalledAppFlow with a local server (port=0).
    4. Saves resulting credentials to token.json.
    5. Returns the user's email and profile data.
    """
    auth_scopes = scopes or DEFAULT_SCOPES
    creds = None
    
    # Check if we have a saved token
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
            if not os.path.exists(client_secret_path):
                raise FileNotFoundError(
                    f"Client secret file not found at {client_secret_path}."
                )
                
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_path, auth_scopes)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        return user_info
    except Exception as e:
        raise RuntimeError(f"Failed to fetch user info from Google API: {e}")
