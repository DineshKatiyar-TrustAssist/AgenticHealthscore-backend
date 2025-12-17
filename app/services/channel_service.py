from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.message import Message
from app.schemas.channel import ChannelCreate, ChannelUpdate
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChannelService:
    """Service for managing channel operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        slack_channel_id: str,
        name: str,
        customer_id: Optional[str] = None,
        channel_type: str = "customer_support",
    ) -> Channel:
        """Create a new channel."""
        channel = Channel(
            slack_channel_id=slack_channel_id,
            name=name,
            customer_id=customer_id,
            channel_type=channel_type,
        )
        self.db.add(channel)
        await self.db.flush()
        await self.db.refresh(channel)
        logger.info(f"Created channel: {channel.id} ({name})")
        return channel

    async def get_by_id(self, channel_id: str) -> Optional[Channel]:
        """Get channel by ID."""
        result = await self.db.execute(
            select(Channel).where(Channel.id == channel_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slack_id(self, slack_channel_id: str) -> Optional[Channel]:
        """Get channel by Slack channel ID."""
        result = await self.db.execute(
            select(Channel).where(Channel.slack_channel_id == slack_channel_id)
        )
        return result.scalar_one_or_none()

    async def get_by_customer_id(self, customer_id: str) -> List[Channel]:
        """Get all channels linked to a customer."""
        result = await self.db.execute(
            select(Channel).where(Channel.customer_id == customer_id)
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        monitored_only: bool = False,
    ) -> tuple[List[Channel], int]:
        """Get all channels with pagination."""
        query = select(Channel)

        if monitored_only:
            query = query.where(Channel.is_monitored == True)

        # Get total count
        count_query = select(func.count(Channel.id))
        if monitored_only:
            count_query = count_query.where(Channel.is_monitored == True)
        total = (await self.db.execute(count_query)).scalar()

        # Get channels
        query = query.offset(skip).limit(limit).order_by(Channel.created_at.desc())
        result = await self.db.execute(query)
        channels = result.scalars().all()

        return list(channels), total

    async def get_by_customer(self, customer_id: str) -> List[Channel]:
        """Get all channels for a customer."""
        result = await self.db.execute(
            select(Channel).where(Channel.customer_id == customer_id)
        )
        return list(result.scalars().all())

    async def update(self, channel_id: str, data: ChannelUpdate) -> Optional[Channel]:
        """Update a channel."""
        channel = await self.get_by_id(channel_id)
        if not channel:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(channel, field, value)

        channel.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(channel)
        logger.info(f"Updated channel: {channel_id}")
        return channel

    async def link_customer(self, channel_id: str, customer_id: str) -> Optional[Channel]:
        """Link a channel to a customer."""
        channel = await self.get_by_id(channel_id)
        if not channel:
            return None

        channel.customer_id = customer_id
        channel.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(channel)
        logger.info(f"Linked channel {channel_id} to customer {customer_id}")
        return channel

    async def unlink_customer(self, channel_id: str) -> Optional[Channel]:
        """Unlink a channel from its customer."""
        channel = await self.get_by_id(channel_id)
        if not channel:
            return None

        channel.customer_id = None
        channel.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(channel)
        logger.info(f"Unlinked channel {channel_id} from customer")
        return channel

    async def set_monitoring(self, channel_id: str, is_monitored: bool) -> Optional[Channel]:
        """Enable or disable monitoring for a channel."""
        channel = await self.get_by_id(channel_id)
        if not channel:
            return None

        channel.is_monitored = is_monitored
        channel.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(channel)
        logger.info(f"Set channel {channel_id} monitoring to {is_monitored}")
        return channel

    async def get_with_message_count(self, channel_id: str) -> Optional[dict]:
        """Get channel with message count."""
        channel = await self.get_by_id(channel_id)
        if not channel:
            return None

        count_result = await self.db.execute(
            select(func.count(Message.id)).where(Message.channel_id == channel_id)
        )
        message_count = count_result.scalar()

        return {
            "channel": channel,
            "message_count": message_count,
        }

    async def delete(self, channel_id: str) -> bool:
        """Delete a channel."""
        channel = await self.get_by_id(channel_id)
        if not channel:
            return False

        await self.db.delete(channel)
        await self.db.flush()
        logger.info(f"Deleted channel: {channel_id}")
        return True
