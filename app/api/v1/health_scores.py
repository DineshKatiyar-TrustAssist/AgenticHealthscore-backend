from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db
from app.services.health_score_service import HealthScoreService
from app.agents.orchestrator import CustomerHealthOrchestrator
from app.schemas.health_score import (
    HealthScoreResponse,
    HealthScoreListResponse,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.get("", response_model=HealthScoreListResponse)
async def list_health_scores(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    customer_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all health scores with pagination. Shows only latest score per customer."""
    from app.services.customer_service import CustomerService

    service = HealthScoreService(db)
    customer_service = CustomerService(db)

    if customer_id:
        scores = await service.get_history(customer_id, limit=limit)
        # Apply skip manually for customer-specific query
        scores = scores[skip:skip + limit]
        total = len(scores)
    else:
        # Get only the latest health score per customer
        from app.models.health_score import HealthScore
        subquery = (
            select(
                HealthScore.customer_id,
                func.max(HealthScore.created_at).label('max_created_at')
            )
            .group_by(HealthScore.customer_id)
            .subquery()
        )
        
        query = (
            select(HealthScore)
            .join(
                subquery,
                (HealthScore.customer_id == subquery.c.customer_id) &
                (HealthScore.created_at == subquery.c.max_created_at)
            )
            .order_by(HealthScore.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        scores = list(result.scalars().all())
        
        # Get total count of unique customers with health scores
        count_query = select(func.count(func.distinct(HealthScore.customer_id)))
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

    # Get customer names for all scores
    customer_ids = {s.customer_id for s in scores}
    customers = {}
    for cid in customer_ids:
        customer = await customer_service.get_by_id(cid)
        if customer:
            customers[cid] = customer.name

    return HealthScoreListResponse(
        health_scores=[
            HealthScoreResponse(
                id=s.id,
                customer_id=s.customer_id,
                customer_name=customers.get(s.customer_id),
                score=s.score,
                churn_probability=s.churn_probability,
                score_components=s.score_components,
                calculation_period_start=s.calculation_period_start,
                calculation_period_end=s.calculation_period_end,
                messages_analyzed=s.messages_analyzed,
                reasoning=s.reasoning,
                created_at=s.created_at,
            )
            for s in scores
        ],
        total=total,
    )


@router.get("/{health_score_id}", response_model=HealthScoreResponse)
async def get_health_score(
    health_score_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a health score by ID."""
    from app.services.customer_service import CustomerService

    service = HealthScoreService(db)
    customer_service = CustomerService(db)
    score = await service.get_by_id(health_score_id)

    if not score:
        raise HTTPException(status_code=404, detail="Health score not found")

    customer = await customer_service.get_by_id(score.customer_id)
    customer_name = customer.name if customer else None

    return HealthScoreResponse(
        id=score.id,
        customer_id=score.customer_id,
        customer_name=customer_name,
        score=score.score,
        churn_probability=score.churn_probability,
        score_components=score.score_components,
        calculation_period_start=score.calculation_period_start,
        calculation_period_end=score.calculation_period_end,
        messages_analyzed=score.messages_analyzed,
        reasoning=score.reasoning,
        created_at=score.created_at,
    )


@router.post("/calculate-all")
async def calculate_all_health_scores(
    background_tasks: BackgroundTasks,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Trigger health score calculation for all active customers. Fetches messages from all channels first."""
    from app.services.customer_service import CustomerService
    from app.services.channel_service import ChannelService
    from app.slack.api_client import SlackAPIClient
    from app.services.message_service import MessageService
    from datetime import datetime, timedelta, timezone

    customer_service = CustomerService(db)
    channel_service = ChannelService(db)
    message_service = MessageService(db)
    
    # Get API keys from database
    from app.utils.api_keys import get_slack_api_token, get_google_api_key
    slack_token = await get_slack_api_token(db)
    google_api_key = await get_google_api_key(db)
    
    if not slack_token:
        raise HTTPException(
            status_code=400,
            detail="SLACK_API_TOKEN is not configured. Please set it in the Settings page."
        )
    if not google_api_key:
        raise HTTPException(
            status_code=400,
            detail="GOOGLE_API_KEY is not configured. Please set it in the Settings page."
        )
    
    slack_client = SlackAPIClient(token=slack_token)

    try:
        # Step 1: Fetch messages from all channels linked to customers
        logger.info("Fetching messages from all customer channels")
        customers = await customer_service.get_active_customers()
        total_messages_fetched = 0

        for customer in customers:
            # Get all channels linked to this customer
            channels = await channel_service.get_by_customer_id(customer.id)
            for channel in channels:
                if channel.is_monitored:
                    try:
                        oldest = datetime.now(timezone.utc) - timedelta(days=days)
                        messages = await slack_client.fetch_channel_history(
                            channel_id=channel.slack_channel_id,
                            oldest=oldest,
                        )

                        # Store messages
                        messages_data = [
                            {
                                "channel_id": channel.id,
                                "ts": msg["ts"],
                                "text": msg.get("text", ""),
                                "user": msg.get("user"),
                                "user_type": "customer",
                            }
                            for msg in messages
                            if msg.get("text")
                        ]

                        created = await message_service.bulk_create(messages_data)
                        total_messages_fetched += len(messages)
                        logger.info(f"Fetched {len(messages)} messages from channel {channel.name} for customer {customer.name}")
                    except Exception as e:
                        logger.warning(f"Failed to fetch messages from channel {channel.name}: {e}")
                        continue

        await db.commit()
        logger.info(f"Total messages fetched: {total_messages_fetched}")

        # Step 2: Calculate health scores for all customers
        orchestrator = CustomerHealthOrchestrator(db, google_api_key=google_api_key)
        results = await orchestrator.analyze_all_customers()

        success_count = sum(1 for r in results if r.get("status") == "success")
        error_count = sum(1 for r in results if r.get("status") == "error")
        skipped_count = sum(1 for r in results if r.get("status") == "insufficient_data")

        return {
            "total_customers": len(results),
            "success": success_count,
            "errors": error_count,
            "skipped": skipped_count,
            "messages_fetched": total_messages_fetched,
            "details": results,
        }

    except Exception as e:
        logger.error(f"Error calculating all health scores: {e}")
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")
