from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Customer Health Score API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/healthscore"

    # Google Gemini
    # Note: GOOGLE_API_KEY is now stored in the database (app_config table)
    # Set it via the Settings page in the UI
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"

    # Slack
    # Note: SLACK_API_TOKEN is now stored in the database (app_config table)
    # Set it via the Settings page in the UI

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Analysis Configuration
    ANALYSIS_PERIOD_DAYS: int = 30
    MESSAGE_BATCH_SIZE: int = 50
    HEALTH_SCORE_CALCULATION_HOUR: int = 2  # 2 AM daily

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow extra env vars like NEXT_PUBLIC_API_URL

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name == "CORS_ORIGINS":
                return json.loads(raw_val)
            return raw_val


settings = Settings()
