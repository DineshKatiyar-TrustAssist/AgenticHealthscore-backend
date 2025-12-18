from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Customer Health Score API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    # SECRET_KEY: Optional - not currently used, but available for future use (sessions, JWT, etc.)
    SECRET_KEY: str = "change-me-in-production"

    # Database
    # SQLite database connection string
    # For local development: sqlite+aiosqlite:///./healthscore.db
    # For Cloud Run with Cloud Storage volume: sqlite+aiosqlite:///mnt/data/healthscore.db
    # (GCS bucket is mounted at /mnt/data via Cloud Run volume mount)
    DATABASE_URL: str = "sqlite+aiosqlite:///./healthscore.db"

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

    # Authentication Configuration
    VERIFICATION_TOKEN_EXPIRY_HOURS: int = 1
    JWT_SECRET_KEY: str = "change-me-in-production-jwt"  # Should use SECRET_KEY or separate
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    ADMIN_NOTIFICATION_EMAIL: str = "dinesh.katiyar@trustassist.ai"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"  # Backend URL for OAuth callbacks

    # SMTP Configuration (for email verification)
    # Priority: Environment Variables > Database
    SMTP_HOST: str | None = None
    SMTP_PORT: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_USE_TLS: str = "true"  # "true" for STARTTLS (port 587), "false" for SSL (port 465)

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
