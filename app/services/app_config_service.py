from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.app_config import AppConfig


class AppConfigService:
    """Service for managing application configuration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, key: str) -> Optional[str]:
        """Get a configuration value by key."""
        result = await self.db.execute(
            select(AppConfig).where(AppConfig.key == key)
        )
        config = result.scalar_one_or_none()
        return config.value if config else None

    async def set(self, key: str, value: str) -> AppConfig:
        """Set a configuration value. Creates if not exists, updates if exists."""
        result = await self.db.execute(
            select(AppConfig).where(AppConfig.key == key)
        )
        config = result.scalar_one_or_none()

        if config:
            config.value = value
        else:
            config = AppConfig(key=key, value=value)
            self.db.add(config)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete(self, key: str) -> bool:
        """Delete a configuration value."""
        result = await self.db.execute(
            select(AppConfig).where(AppConfig.key == key)
        )
        config = result.scalar_one_or_none()

        if config:
            await self.db.delete(config)
            await self.db.commit()
            return True
        return False

    async def get_all(self) -> dict[str, str]:
        """Get all configuration values as a dictionary."""
        result = await self.db.execute(select(AppConfig))
        configs = result.scalars().all()
        return {config.key: config.value for config in configs}

