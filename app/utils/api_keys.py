"""Utility functions for getting API keys from database."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.app_config_service import AppConfigService


async def get_slack_api_token(db: AsyncSession) -> Optional[str]:
    """Get Slack API token from database."""
    config_service = AppConfigService(db)
    return await config_service.get("SLACK_API_TOKEN")


async def get_google_api_key(db: AsyncSession) -> Optional[str]:
    """Get Google API key from database."""
    config_service = AppConfigService(db)
    return await config_service.get("GOOGLE_API_KEY")

