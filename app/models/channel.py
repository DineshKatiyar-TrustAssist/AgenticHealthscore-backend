import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utcnow():
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Channel(Base):
    """Channel model representing a Slack channel being monitored."""

    __tablename__ = "channels"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    slack_channel_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    channel_type: Mapped[str] = mapped_column(
        String(50), default="customer_support"
    )  # customer_support, shared, dedicated
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), default=utcnow, onupdate=utcnow
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    # Relationships
    customer = relationship("Customer", back_populates="channels")
    messages = relationship("Message", back_populates="channel", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, name={self.name}, slack_id={self.slack_channel_id})>"
