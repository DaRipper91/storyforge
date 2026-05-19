"""Environment + path resolution. No secrets in code."""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="STORYFORGE_",
        extra="ignore",
    )
    
    gemini_api_key: str = Field(..., description="Google AI Studio API key")
    gemini_model: str = "gemini-3.5-flash"
    
    campaign_id: str = "family_campaign_01"
    
    @property
    def campaign_path(self) -> Path:
        return PROJECT_ROOT / "data" / "campaigns" / self.campaign_id
    
    @property
    def prompts_path(self) -> Path:
        return PROJECT_ROOT / "src" / "storyforge" / "ai" / "prompts"


settings = Settings()
