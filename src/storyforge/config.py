"""Environment + path resolution. No secrets in code."""
import sys
from pathlib import Path
import secrets
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Pinned AI Model Versions
STORYFORGE_PRIMARY_MODEL = "gemini-3.5-flash"
STORYFORGE_PRO_MODEL = "gemini-3.1-pro-preview"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="STORYFORGE_",
        extra="ignore",
    )
    
    gemini_api_key: str = Field(..., description="Google AI Studio API key")
    
    # Auth
    google_client_id: str = ""
    google_client_secret: str = ""
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"

    # CORS — space-separated list of allowed origins.
    # Add your ngrok URL here each session, e.g.:
    #   STORYFORGE_ALLOWED_ORIGINS=http://localhost:8765 https://abc123.ngrok-free.app
    allowed_origins: str = "http://localhost:8765 http://127.0.0.1:8765"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split() if o.strip()]
    
    campaign_id: str = "family_campaign_01"
    
    @property
    def campaign_path(self) -> Path:
        # Save campaigns in the current working directory to avoid losing them
        # when running from a temporary PyInstaller directory
        base_dir = Path.cwd() / "data" / "campaigns"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / self.campaign_id
    
    @property
    def prompts_path(self) -> Path:
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS) / "storyforge" / "ai" / "prompts"
        return PROJECT_ROOT / "src" / "storyforge" / "ai" / "prompts"


settings = Settings()
