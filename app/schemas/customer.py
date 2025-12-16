from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class CustomerBase(BaseModel):
    """Base schema for customer data."""
    name: str = Field(..., min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    slack_user_id: Optional[str] = Field(None, max_length=50)


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer."""
    pass


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    slack_user_id: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    """Schema for customer response."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool
    latest_health_score: Optional[int] = None
    churn_probability: Optional[float] = None

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    """Schema for list of customers response."""
    customers: list[CustomerResponse]
    total: int
