from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Literal


PriorityLevel = Literal["critical", "high", "medium", "low"]
StatusLevel = Literal["pending", "in_progress", "completed", "dismissed"]
CategoryType = Literal["engagement", "support", "relationship", "technical", "billing"]


class ActionItemBase(BaseModel):
    """Base schema for action item data."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: PriorityLevel = "medium"
    category: Optional[CategoryType] = None


class ActionItemCreate(ActionItemBase):
    """Schema for creating a new action item."""
    customer_id: str
    health_score_id: Optional[str] = None
    due_date: Optional[date] = None
    assigned_to: Optional[str] = Field(None, max_length=255)
    impact_score: Optional[int] = Field(None, ge=1, le=10)
    effort_score: Optional[int] = Field(None, ge=1, le=10)


class ActionItemUpdate(BaseModel):
    """Schema for updating an action item."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[PriorityLevel] = None
    category: Optional[CategoryType] = None
    status: Optional[StatusLevel] = None
    due_date: Optional[date] = None
    assigned_to: Optional[str] = Field(None, max_length=255)


class ActionItemStatusUpdate(BaseModel):
    """Schema for updating action item status."""
    status: StatusLevel


class ActionItemResponse(ActionItemBase):
    """Schema for action item response."""
    id: str
    customer_id: str
    health_score_id: Optional[str] = None
    status: StatusLevel
    due_date: Optional[date] = None
    assigned_to: Optional[str] = None
    impact_score: Optional[int] = None
    effort_score: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    customer_name: Optional[str] = None

    class Config:
        from_attributes = True


class ActionItemListResponse(BaseModel):
    """Schema for list of action items response."""
    action_items: list[ActionItemResponse]
    total: int
