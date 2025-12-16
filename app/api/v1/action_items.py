from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.health_score_service import HealthScoreService
from app.services.customer_service import CustomerService
from app.schemas.action_item import (
    ActionItemResponse,
    ActionItemListResponse,
    ActionItemUpdate,
    ActionItemStatusUpdate,
)

router = APIRouter()


@router.get("", response_model=ActionItemListResponse)
async def list_action_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    customer_id: Optional[UUID] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all action items with optional filters."""
    service = HealthScoreService(db)
    items, total = await service.get_action_items(
        customer_id=customer_id,
        status=status,
        priority=priority,
        skip=skip,
        limit=limit,
    )

    # Get customer names for each item
    customer_service = CustomerService(db)
    response_items = []

    for item in items:
        customer_name = None
        customer = await customer_service.get_by_id(item.customer_id)
        if customer:
            customer_name = customer.name

        response_items.append(
            ActionItemResponse(
                id=item.id,
                customer_id=item.customer_id,
                health_score_id=item.health_score_id,
                title=item.title,
                description=item.description,
                priority=item.priority,
                category=item.category,
                status=item.status,
                due_date=item.due_date,
                assigned_to=item.assigned_to,
                impact_score=item.impact_score,
                effort_score=item.effort_score,
                created_at=item.created_at,
                updated_at=item.updated_at,
                completed_at=item.completed_at,
                customer_name=customer_name,
            )
        )

    return ActionItemListResponse(action_items=response_items, total=total)


@router.get("/{action_item_id}", response_model=ActionItemResponse)
async def get_action_item(
    action_item_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get an action item by ID."""
    service = HealthScoreService(db)
    items, _ = await service.get_action_items(skip=0, limit=1000)

    item = next((i for i in items if i.id == action_item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    customer_name = None
    customer_service = CustomerService(db)
    customer = await customer_service.get_by_id(item.customer_id)
    if customer:
        customer_name = customer.name

    return ActionItemResponse(
        id=item.id,
        customer_id=item.customer_id,
        health_score_id=item.health_score_id,
        title=item.title,
        description=item.description,
        priority=item.priority,
        category=item.category,
        status=item.status,
        due_date=item.due_date,
        assigned_to=item.assigned_to,
        impact_score=item.impact_score,
        effort_score=item.effort_score,
        created_at=item.created_at,
        updated_at=item.updated_at,
        completed_at=item.completed_at,
        customer_name=customer_name,
    )


@router.patch("/{action_item_id}/status", response_model=ActionItemResponse)
async def update_action_item_status(
    action_item_id: UUID,
    data: ActionItemStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an action item's status."""
    service = HealthScoreService(db)
    item = await service.update_action_item_status(action_item_id, data.status)

    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    customer_name = None
    customer_service = CustomerService(db)
    customer = await customer_service.get_by_id(item.customer_id)
    if customer:
        customer_name = customer.name

    return ActionItemResponse(
        id=item.id,
        customer_id=item.customer_id,
        health_score_id=item.health_score_id,
        title=item.title,
        description=item.description,
        priority=item.priority,
        category=item.category,
        status=item.status,
        due_date=item.due_date,
        assigned_to=item.assigned_to,
        impact_score=item.impact_score,
        effort_score=item.effort_score,
        created_at=item.created_at,
        updated_at=item.updated_at,
        completed_at=item.completed_at,
        customer_name=customer_name,
    )
