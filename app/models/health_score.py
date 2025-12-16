import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Numeric, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class HealthScore(Base):
    """Health score model representing a calculated customer health score."""

    __tablename__ = "health_scores"
    __table_args__ = (
        CheckConstraint("score >= 1 AND score <= 10", name="check_score_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-10
    churn_probability: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )  # 0.0000 to 1.0000

    # Score breakdown
    score_components: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Components: sentiment_score, engagement_score, issue_resolution_score,
    #             tone_consistency_score, response_pattern_score

    # Analysis period
    calculation_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    calculation_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    messages_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )

    # Relationships
    customer = relationship("Customer", back_populates="health_scores")
    action_items = relationship("ActionItem", back_populates="health_score")

    def __repr__(self) -> str:
        return f"<HealthScore(id={self.id}, customer_id={self.customer_id}, score={self.score})>"
