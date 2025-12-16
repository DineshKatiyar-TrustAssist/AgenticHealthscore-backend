import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Date, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class ActionItem(Base):
    """Action item model representing a suggested action to improve health score."""

    __tablename__ = "action_items"
    __table_args__ = (
        CheckConstraint("impact_score >= 1 AND impact_score <= 10", name="check_impact_range"),
        CheckConstraint("effort_score >= 1 AND effort_score <= 10", name="check_effort_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    health_score_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("health_scores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20), default="medium", index=True
    )  # critical, high, medium, low
    category: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # engagement, support, relationship, technical, billing
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, in_progress, completed, dismissed

    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    impact_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-10
    effort_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-10

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    customer = relationship("Customer", back_populates="action_items")
    health_score = relationship("HealthScore", back_populates="action_items")

    def __repr__(self) -> str:
        return f"<ActionItem(id={self.id}, title={self.title}, priority={self.priority})>"
