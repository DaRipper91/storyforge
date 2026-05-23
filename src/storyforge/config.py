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
