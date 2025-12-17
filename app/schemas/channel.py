from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ChannelBase(BaseModel):
    """Base schema for channel data."""
    slack_channel_id: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    channel_type: str = Field(default="customer_support", max_length=50)
    is_monitored: bool = True


class ChannelCreate(ChannelBase):
    """Schema for creating a new channel."""
    customer_id: Optional[str] = None


class ChannelUpdate(BaseModel):
    """Schema for updating a channel."""
    name: Optional[str] = Field(None, max_length=255)
    customer_id: Optional[str] = None
    channel_type: Optional[str] = Field(None, max_length=50)
    is_monitored: Optional[bool] = None


class ChannelResponse(ChannelBase):
    """Schema for channel response."""
    id: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None

    class Config:
        from_attributes = True


class ChannelListResponse(BaseModel):
    """Schema for list of channels response."""
    channels: list[ChannelResponse]
    total: int


class ChannelLinkCustomer(BaseModel):
    """Schema for linking a channel to a customer."""
    customer_id: str
