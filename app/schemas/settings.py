from pydantic import BaseModel
from typing import Optional


class SettingsResponse(BaseModel):
    """Application settings response."""
    
    slack_api_token_configured: bool
    google_api_key_configured: bool
    gemini_model: str
    analysis_period_days: int
    message_batch_size: int
    health_score_calculation_hour: int


class SettingsUpdateRequest(BaseModel):
    """Request to update API keys."""
    
    slack_api_token: Optional[str] = None
    google_api_key: Optional[str] = None

