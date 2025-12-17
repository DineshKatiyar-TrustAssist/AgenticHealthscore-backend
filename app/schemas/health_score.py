from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal


class ScoreComponents(BaseModel):
    """Schema for health score components breakdown."""
    sentiment_score: int = Field(..., ge=1, le=10)
    engagement_score: int = Field(..., ge=1, le=10)
    issue_resolution_score: int = Field(..., ge=1, le=10)
    tone_consistency_score: int = Field(..., ge=1, le=10)
    response_pattern_score: int = Field(..., ge=1, le=10)


class HealthScoreResponse(BaseModel):
    """Schema for health score response."""
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    score: int = Field(..., ge=1, le=10)
    churn_probability: Optional[Decimal] = None
    score_components: ScoreComponents
    calculation_period_start: Optional[datetime] = None
    calculation_period_end: Optional[datetime] = None
    messages_analyzed: int
    reasoning: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class HealthScoreListResponse(BaseModel):
    """Schema for list of health scores response."""
    health_scores: list[HealthScoreResponse]
    total: int


class HealthScoreCalculateRequest(BaseModel):
    """Schema for triggering health score calculation."""
    analysis_period_days: int = Field(default=30, ge=1, le=365)


class HealthScoreCalculateResponse(BaseModel):
    """Schema for health score calculation response."""
    status: str
    customer_id: str
    health_score: Optional[HealthScoreResponse] = None
    churn_prediction: Optional[dict] = None
    action_items_generated: int = 0
    messages_analyzed: int = 0
    messages_fetched: int = 0
    error: Optional[str] = None


class ChurnPrediction(BaseModel):
    """Schema for churn prediction result."""
    churn_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: str  # low, medium, high, critical
    contributing_factors: list[str] = []
    protective_factors: list[str] = []
    predicted_timeframe: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
