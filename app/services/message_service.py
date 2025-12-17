from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.channel import Channel
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class MessageService:
    """Service for managing message operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        channel_id: str,
        slack_message_ts: str,
        content: str,
        message_timestamp: datetime,
        slack_user_id: Optional[str] = None,
        user_type: str = "customer",
    ) -> Optional[Message]:
        """Create a new message. Returns existing message if duplicate."""
        # Check if message already exists (SQLite-compatible upsert)
        result = await self.db.execute(
            select(Message).where(
                and_(
                    Message.channel_id == channel_id,
                    Message.slack_message_ts == slack_message_ts,
                )
            )
        )
        existing_message = result.scalar_one_or_none()
        
        if existing_message:
            logger.debug(f"Message already exists: {existing_message.id}")
            return existing_message
        
        # Create new message
        message = Message(
            channel_id=channel_id,
            slack_message_ts=slack_message_ts,
            slack_user_id=slack_user_id,
            user_type=user_type,
            content=content,
            message_timestamp=message_timestamp,
        )
        
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        
        logger.debug(f"Created new message: {message.id}")
        return message

    async def get_by_id(self, message_id: str) -> Optional[Message]:
        """Get message by ID."""
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_channel_messages(
        self,
        channel_id: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Message]:
        """Get messages for a channel."""
        query = select(Message).where(Message.channel_id == channel_id)

        if since:
            query = query.where(Message.message_timestamp >= since)
        if until:
            query = query.where(Message.message_timestamp <= until)

        query = query.order_by(Message.message_timestamp.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_customer_messages(
        self,
        customer_id: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Message]:
        """Get all messages for a customer across all their channels."""
        query = (
            select(Message)
            .join(Channel, Message.channel_id == Channel.id)
            .where(Channel.customer_id == customer_id)
        )

        if since:
            query = query.where(Message.message_timestamp >= since)
        if until:
            query = query.where(Message.message_timestamp <= until)

        query = query.order_by(Message.message_timestamp.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_unanalyzed_messages(
        self,
        limit: int = 100,
    ) -> List[Message]:
        """Get messages that haven't been analyzed for sentiment."""
        result = await self.db.execute(
            select(Message)
            .where(Message.is_analyzed == False)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_sentiment(
        self,
        message_id: str,
        sentiment_score: float,
        sentiment_label: str,
        sentiment_magnitude: float,
    ) -> Optional[Message]:
        """Update sentiment analysis results for a message."""
        message = await self.get_by_id(message_id)
        if not message:
            return None

        message.sentiment_score = Decimal(str(sentiment_score))
        message.sentiment_label = sentiment_label
        message.sentiment_magnitude = Decimal(str(sentiment_magnitude))
        message.is_analyzed = True

        await self.db.flush()
        return message

    async def update_sentiments(
        self,
        messages: List[Message],
        sentiment_results: List[dict],
    ) -> int:
        """Batch update sentiment results for messages."""
        updated = 0

        for result in sentiment_results:
            idx = result.get("index", 0)
            if idx < len(messages):
                message = messages[idx]
                message.sentiment_score = Decimal(str(result.get("sentiment_score", 0)))
                message.sentiment_label = result.get("sentiment_label", "neutral")
                message.sentiment_magnitude = Decimal(str(result.get("sentiment_magnitude", 0)))
                message.is_analyzed = True
                updated += 1

        await self.db.flush()
        logger.info(f"Updated sentiment for {updated} messages")
        return updated

    async def add_reaction_signal(
        self,
        channel_slack_id: str,
        message_ts: str,
        signal: str,
    ) -> bool:
        """Add a reaction signal to message metadata."""
        # Find the channel first
        channel_result = await self.db.execute(
            select(Channel).where(Channel.slack_channel_id == channel_slack_id)
        )
        channel = channel_result.scalar_one_or_none()
        if not channel:
            return False

        # Find the message
        result = await self.db.execute(
            select(Message).where(
                and_(
                    Message.channel_id == channel.id,
                    Message.slack_message_ts == message_ts,
                )
            )
        )
        message = result.scalar_one_or_none()
        if not message:
            return False

        # Update metadata with reaction signal
        metadata = message.metadata_ or {}
        reactions = metadata.get("reaction_signals", [])
        reactions.append({
            "signal": signal,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        metadata["reaction_signals"] = reactions
        message.metadata_ = metadata

        await self.db.flush()
        return True

    async def bulk_create(
        self,
        messages_data: List[dict],
    ) -> int:
        """Bulk create messages from Slack history."""
        created = 0

        for data in messages_data:
            try:
                message = await self.create(
                    channel_id=data["channel_id"],
                    slack_message_ts=data["ts"],
                    content=data.get("text", ""),
                    message_timestamp=datetime.fromtimestamp(float(data["ts"])),
                    slack_user_id=data.get("user"),
                    user_type=data.get("user_type", "customer"),
                )
                if message:
                    created += 1
            except Exception as e:
                logger.error(f"Error creating message: {e}")

        await self.db.flush()
        logger.info(f"Bulk created {created} messages")
        return created

    async def get_message_count_by_channel(self, channel_id: str) -> int:
        """Get message count for a channel."""
        result = await self.db.execute(
            select(func.count(Message.id)).where(Message.channel_id == channel_id)
        )
        return result.scalar() or 0
