from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List

from app.api.deps import get_db
from app.services.health_score_service import HealthScoreService
from app.services.customer_service import CustomerService
from app.schemas.customer import CustomerResponse

router = APIRouter()


class DashboardSummary(BaseModel):
    """Dashboard summary statistics."""
    average_health_score: float
    at_risk_count: int
    pending_actions_count: int
    channels_monitored: int
    score_trend: str


class AtRiskCustomer(BaseModel):
    """At-risk customer details."""
    id: str
    name: str
    company_name: Optional[str]
    health_score: int
    churn_probability: float


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard summary statistics."""
    service = HealthScoreService(db)
    summary = await service.get_dashboard_summary()

    return DashboardSummary(
        average_health_score=summary["average_health_score"],
        at_risk_count=summary["at_risk_count"],
        pending_actions_count=summary["pending_actions_count"],
        channels_monitored=summary["channels_monitored"],
        score_trend=summary["score_trend"],
    )


@router.get("/at-risk", response_model=List[AtRiskCustomer])
async def get_at_risk_customers(
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """Get customers with churn probability above threshold."""
    service = CustomerService(db)
    at_risk = await service.get_at_risk_customers(churn_threshold=threshold)

    return [
        AtRiskCustomer(
            id=str(item["customer"].id),
            name=item["customer"].name,
            company_name=item["customer"].company_name,
            health_score=item["health_score"],
            churn_probability=item["churn_probability"],
        )
        for item in at_risk
    ]


@router.get("/trends")
async def get_trends(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Get health score trends over time."""
    # Simplified trend data - in production would aggregate from health_scores table
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select, func
    from app.models.health_score import HealthScore

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # Get daily average scores
    result = await db.execute(
        select(
            func.date(HealthScore.created_at).label("date"),
            func.avg(HealthScore.score).label("avg_score"),
            func.count(HealthScore.id).label("count"),
        )
        .where(HealthScore.created_at >= start_date)
        .group_by(func.date(HealthScore.created_at))
        .order_by(func.date(HealthScore.created_at))
    )

    rows = result.all()

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days,
        },
        "data": [
            {
                "date": row.date.isoformat() if row.date else None,
                "average_score": round(float(row.avg_score), 2) if row.avg_score else 0,
                "count": row.count,
            }
            for row in rows
        ],
    }
