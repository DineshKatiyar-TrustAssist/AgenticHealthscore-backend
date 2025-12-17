from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_score import HealthScore
from app.models.action_item import ActionItem
from app.models.channel import Channel
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class HealthScoreService:
    """Service for managing health score operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        customer_id: str,
        score: int,
        churn_probability: float,
        score_components: dict,
        messages_analyzed: int,
        reasoning: str,
        period_start: datetime,
        period_end: datetime,
    ) -> HealthScore:
        """Create a new health score record."""
        health_score = HealthScore(
            customer_id=customer_id,
            score=score,
            churn_probability=Decimal(str(churn_probability)),
            score_components=score_components,
            messages_analyzed=messages_analyzed,
            reasoning=reasoning,
            calculation_period_start=period_start,
            calculation_period_end=period_end,
        )
        self.db.add(health_score)
        await self.db.flush()
        await self.db.refresh(health_score)
        logger.info(f"Created health score: {health_score.id} for customer {customer_id}")
        return health_score

    async def get_by_id(self, health_score_id: str) -> Optional[HealthScore]:
        """Get health score by ID."""
        result = await self.db.execute(
            select(HealthScore).where(HealthScore.id == health_score_id)
        )
        return result.scalar_one_or_none()

    async def get_latest(self, customer_id: str) -> Optional[HealthScore]:
        """Get the latest health score for a customer."""
        result = await self.db.execute(
            select(HealthScore)
            .where(HealthScore.customer_id == customer_id)
            .order_by(HealthScore.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(
        self,
        customer_id: str,
        limit: int = 30,
    ) -> List[HealthScore]:
        """Get health score history for a customer."""
        result = await self.db.execute(
            select(HealthScore)
            .where(HealthScore.customer_id == customer_id)
            .order_by(HealthScore.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[HealthScore], int]:
        """Get all health scores with pagination."""
        # Get total count
        count_result = await self.db.execute(select(func.count(HealthScore.id)))
        total = count_result.scalar()

        # Get health scores
        result = await self.db.execute(
            select(HealthScore)
            .offset(skip)
            .limit(limit)
            .order_by(HealthScore.created_at.desc())
        )
        scores = result.scalars().all()

        return list(scores), total

    async def calculate_for_channel(self, slack_channel_id: str) -> Optional[dict]:
        """Calculate health score for a channel (called from Slack command)."""
        from app.agents.orchestrator import CustomerHealthOrchestrator

        # Find the channel and its customer
        result = await self.db.execute(
            select(Channel).where(Channel.slack_channel_id == slack_channel_id)
        )
        channel = result.scalar_one_or_none()

        if not channel or not channel.customer_id:
            return None

        # Run the orchestrator
        orchestrator = CustomerHealthOrchestrator(self.db)
        analysis_result = await orchestrator.analyze_customer(channel.customer_id)

        if analysis_result.get("status") == "success":
            return {
                "score": analysis_result["health_score"]["score"],
                "churn_probability": analysis_result["churn_prediction"]["churn_probability"],
                "messages_analyzed": analysis_result["messages_analyzed"],
                "reasoning": analysis_result["health_score"]["reasoning"],
            }

        return None

    async def create_action_item(
        self,
        customer_id: str,
        health_score_id: str,
        title: str,
        description: str = "",
        priority: str = "medium",
        category: str = "engagement",
        impact_score: int = 5,
        effort_score: int = 5,
        **kwargs,
    ) -> ActionItem:
        """Create an action item linked to a health score."""
        action_item = ActionItem(
            customer_id=customer_id,
            health_score_id=health_score_id,
            title=title,
            description=description,
            priority=priority,
            category=category,
            impact_score=impact_score,
            effort_score=effort_score,
        )
        self.db.add(action_item)
        await self.db.flush()
        await self.db.refresh(action_item)
        logger.info(f"Created action item: {action_item.id}")
        return action_item

    async def get_action_items(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[ActionItem], int]:
        """Get action items with optional filters."""
        query = select(ActionItem)
        count_query = select(func.count(ActionItem.id))

        if customer_id:
            query = query.where(ActionItem.customer_id == customer_id)
            count_query = count_query.where(ActionItem.customer_id == customer_id)
        if status:
            query = query.where(ActionItem.status == status)
            count_query = count_query.where(ActionItem.status == status)
        if priority:
            query = query.where(ActionItem.priority == priority)
            count_query = count_query.where(ActionItem.priority == priority)

        # Get total count
        total = (await self.db.execute(count_query)).scalar()

        # Get action items
        query = query.offset(skip).limit(limit).order_by(
            ActionItem.priority.desc(),
            ActionItem.created_at.desc(),
        )
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update_action_item_status(
        self,
        action_item_id: str,
        status: str,
    ) -> Optional[ActionItem]:
        """Update action item status."""
        result = await self.db.execute(
            select(ActionItem).where(ActionItem.id == action_item_id)
        )
        item = result.scalar_one_or_none()

        if not item:
            return None

        item.status = status
        item.updated_at = datetime.now(timezone.utc)

        if status == "completed":
            item.completed_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(item)
        logger.info(f"Updated action item {action_item_id} status to {status}")
        return item

    async def get_dashboard_summary(self) -> dict:
        """Get summary statistics for the dashboard."""
        from app.models.customer import Customer

        # Average health score (from latest scores per customer)
        latest_scores_subq = (
            select(
                HealthScore.customer_id,
                func.max(HealthScore.created_at).label("latest_date")
            )
            .group_by(HealthScore.customer_id)
            .subquery()
        )

        avg_score_result = await self.db.execute(
            select(func.avg(HealthScore.score))
            .join(
                latest_scores_subq,
                (HealthScore.customer_id == latest_scores_subq.c.customer_id) &
                (HealthScore.created_at == latest_scores_subq.c.latest_date)
            )
        )
        avg_score = avg_score_result.scalar() or 0

        # At-risk customers (churn > 0.5)
        at_risk_result = await self.db.execute(
            select(func.count(HealthScore.id.distinct()))
            .join(
                latest_scores_subq,
                (HealthScore.customer_id == latest_scores_subq.c.customer_id) &
                (HealthScore.created_at == latest_scores_subq.c.latest_date)
            )
            .where(HealthScore.churn_probability >= 0.5)
        )
        at_risk_count = at_risk_result.scalar() or 0

        # Pending actions
        pending_result = await self.db.execute(
            select(func.count(ActionItem.id)).where(ActionItem.status == "pending")
        )
        pending_actions = pending_result.scalar() or 0

        # Channels monitored
        channels_result = await self.db.execute(
            select(func.count(Channel.id)).where(Channel.is_monitored == True)
        )
        channels_monitored = channels_result.scalar() or 0

        # Score trend (compare this week vs last week)
        # Simplified: just return "stable" for now
        score_trend = "stable"

        return {
            "average_health_score": round(float(avg_score), 1),
            "at_risk_count": at_risk_count,
            "pending_actions_count": pending_actions,
            "channels_monitored": channels_monitored,
            "score_trend": score_trend,
        }
