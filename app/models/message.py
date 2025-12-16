import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Message(Base):
    """Message model representing a Slack message from a channel."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("channel_id", "slack_message_ts", name="uq_channel_message"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slack_message_ts: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    slack_user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_type: Mapped[str] = mapped_column(
        String(20), default="customer"
    )  # customer, internal, bot
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Sentiment fields
    sentiment_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )  # -1.00 to 1.00
    sentiment_label: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # positive, negative, neutral
    sentiment_magnitude: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    is_analyzed: Mapped[bool] = mapped_column(Boolean, default=False)

    message_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    channel = relationship("Channel", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, channel_id={self.channel_id}, ts={self.slack_message_ts})>"
