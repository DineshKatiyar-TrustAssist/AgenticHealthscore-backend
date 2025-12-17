from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal


class MessageBase(BaseModel):
    """Base schema for message data."""
    slack_message_ts: str = Field(..., max_length=50)
    slack_user_id: Optional[str] = Field(None, max_length=50)
    user_type: str = Field(default="customer", max_length=20)
    content: str


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    channel_id: str
    message_timestamp: datetime


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: str
    channel_id: str
    sentiment_score: Optional[Decimal] = None
    sentiment_label: Optional[str] = None
    sentiment_magnitude: Optional[Decimal] = None
    is_analyzed: bool
    message_timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Schema for list of messages response."""
    messages: list[MessageResponse]
    total: int


class SentimentResult(BaseModel):
    """Schema for sentiment analysis result."""
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    sentiment_label: str
    sentiment_magnitude: float = Field(..., ge=0.0, le=1.0)
    key_phrases: list[str] = []
