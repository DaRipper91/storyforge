"""Environment + path resolution. No secrets in code."""
import sys
import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_base_path():
    """Returns the base path for static assets (frontend, prompts, seeds)."""
    if getattr(sys, 'frozen', False):
        # We are running in a PyInstaller bundle
        return Path(sys._MEIPASS)
    else:
        # We are running in a normal Python environment
        return Path(__file__).resolve().parents[2]

def get_user_data_path():
    """Returns a writable path for user data (campaigns)."""
    if getattr(sys, 'frozen', False):
        # On Windows, use APPDATA, on others use home directory
        if os.name == 'nt':
            base = Path(os.environ.get('APPDATA', '~')).expanduser()
        else:
            base = Path('~/.local/share').expanduser()
        return base / "StoryForge"
    else:
        return get_base_path() / "data"


BASE_PATH = get_base_path()
USER_DATA_PATH = get_user_data_path()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="STORYFORGE_",
        extra="ignore",
    )
    
    gemini_api_key: str = Field(..., description="Google AI Studio API key")
    gemini_model: str = "gemini-2.0-flash-exp"
    
    campaign_id: str = "family_campaign_01"
    
    @property
    def campaign_path(self) -> Path:
        return USER_DATA_PATH / "campaigns" / self.campaign_id
    
    @property
    def prompts_path(self) -> Path:
        return BASE_PATH / "src" / "storyforge" / "ai" / "prompts"
    
    @property
    def seeds_path(self) -> Path:
        return BASE_PATH / "data" / "seeds"
    
    @property
    def frontend_path(self) -> Path:
        return BASE_PATH / "frontend"


settings = Settings()
