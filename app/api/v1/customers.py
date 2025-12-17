from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.logger import setup_logger

from app.api.deps import get_db

logger = setup_logger(__name__)
from app.services.customer_service import CustomerService
from app.services.health_score_service import HealthScoreService
from app.agents.orchestrator import CustomerHealthOrchestrator
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
)
from app.schemas.health_score import (
    HealthScoreResponse,
    HealthScoreListResponse,
    HealthScoreCalculateRequest,
    HealthScoreCalculateResponse,
)

router = APIRouter()


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List all customers with pagination."""
    service = CustomerService(db)
    customers, total = await service.get_all(
        skip=skip, limit=limit, include_inactive=include_inactive
    )

    # Add latest health scores
    response_customers = []
    for customer in customers:
        data = await service.get_with_latest_score(customer.id)
        response_customers.append(
            CustomerResponse(
                id=customer.id,
                name=customer.name,
                company_name=customer.company_name,
                email=customer.email,
                slack_user_id=customer.slack_user_id,
                created_at=customer.created_at,
                updated_at=customer.updated_at,
                is_active=customer.is_active,
                latest_health_score=data.get("latest_score"),
                churn_probability=data.get("churn_probability"),
            )
        )

    return CustomerListResponse(customers=response_customers, total=total)


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new customer."""
    service = CustomerService(db)
    customer = await service.create(data)
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        company_name=customer.company_name,
        email=customer.email,
        slack_user_id=customer.slack_user_id,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        is_active=customer.is_active,
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a customer by ID."""
    service = CustomerService(db)
    data = await service.get_with_latest_score(customer_id)

    if not data:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer = data["customer"]
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        company_name=customer.company_name,
        email=customer.email,
        slack_user_id=customer.slack_user_id,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        is_active=customer.is_active,
        latest_health_score=data.get("latest_score"),
        churn_probability=data.get("churn_probability"),
    )


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a customer."""
    service = CustomerService(db)
    customer = await service.update(customer_id, data)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        company_name=customer.company_name,
        email=customer.email,
        slack_user_id=customer.slack_user_id,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        is_active=customer.is_active,
    )


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a customer (soft delete)."""
    service = CustomerService(db)
    success = await service.delete(customer_id)

    if not success:
        raise HTTPException(status_code=404, detail="Customer not found")


@router.get("/{customer_id}/health-scores", response_model=HealthScoreListResponse)
async def get_customer_health_scores(
    customer_id: str,
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get health score history for a customer."""
    customer_service = CustomerService(db)
    customer = await customer_service.get_by_id(customer_id)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    health_service = HealthScoreService(db)
    scores = await health_service.get_history(customer_id, limit=limit)

    return HealthScoreListResponse(
        health_scores=[
            HealthScoreResponse(
                id=s.id,
                customer_id=s.customer_id,
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
        total=len(scores),
    )


@router.get("/{customer_id}/health-score/latest", response_model=HealthScoreResponse)
async def get_customer_latest_health_score(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the latest health score for a customer."""
    health_service = HealthScoreService(db)
    score = await health_service.get_latest(customer_id)

    if not score:
        raise HTTPException(status_code=404, detail="No health score found")

    return HealthScoreResponse(
        id=score.id,
        customer_id=score.customer_id,
        score=score.score,
        churn_probability=score.churn_probability,
        score_components=score.score_components,
        calculation_period_start=score.calculation_period_start,
        calculation_period_end=score.calculation_period_end,
        messages_analyzed=score.messages_analyzed,
        reasoning=score.reasoning,
        created_at=score.created_at,
    )


@router.post("/{customer_id}/health-score/calculate", response_model=HealthScoreCalculateResponse)
async def calculate_customer_health_score(
    customer_id: str,
    request: HealthScoreCalculateRequest = HealthScoreCalculateRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Trigger health score calculation for a customer. Fetches recent messages first."""
    from app.services.channel_service import ChannelService
    from app.services.message_service import MessageService
    from app.slack.api_client import SlackAPIClient
    from app.utils.api_keys import get_slack_api_token, get_google_api_key
    from datetime import datetime, timedelta, timezone

    customer_service = CustomerService(db)
    customer = await customer_service.get_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    slack_token = await get_slack_api_token(db)
    google_api_key = await get_google_api_key(db)
    if not slack_token or not google_api_key:
        raise HTTPException(status_code=400, detail="API keys not configured")

    # Fetch messages from Slack
    channel_service = ChannelService(db)
    message_service = MessageService(db)
    slack_client = SlackAPIClient(token=slack_token)
    channels = await channel_service.get_by_customer_id(customer_id)
    total_messages_fetched = 0
    oldest = datetime.now(timezone.utc) - timedelta(days=request.analysis_period_days)
    
    for channel in channels:
        if channel.is_monitored:
            try:
                messages = await slack_client.fetch_channel_history(channel_id=channel.slack_channel_id, oldest=oldest)
                messages_data = [
                    {"channel_id": channel.id, "ts": msg["ts"], "text": msg.get("text", ""), "user": msg.get("user"), "user_type": "customer"}
                    for msg in messages if msg.get("text")
                ]
                total_messages_fetched += await message_service.bulk_create(messages_data)
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to fetch messages from channel {channel.id}: {e}")
    
    # Calculate health score
    try:
        orchestrator = CustomerHealthOrchestrator(db, google_api_key=google_api_key)
        result = await orchestrator.analyze_customer(customer_id=customer_id, analysis_period_days=request.analysis_period_days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating health score: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate health score")

    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message", "Analysis failed"))

    return HealthScoreCalculateResponse(
        status="success",
        customer_id=customer_id,
        health_score=HealthScoreResponse(
            id="00000000-0000-0000-0000-000000000000",
            customer_id=customer_id,
            score=result["health_score"]["score"],
            churn_probability=result["churn_prediction"]["churn_probability"],
            score_components=result["health_score"]["components"],
            messages_analyzed=result["messages_analyzed"],
            reasoning=result["health_score"]["reasoning"],
            created_at=result["analysis_period"]["end"],
        ),
        churn_prediction=result["churn_prediction"],
        action_items_generated=len(result["action_items"]),
        messages_analyzed=result["messages_analyzed"],
        messages_fetched=total_messages_fetched,
    )
