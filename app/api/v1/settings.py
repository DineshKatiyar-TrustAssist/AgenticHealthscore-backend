from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.config import settings
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest
from app.services.app_config_service import AppConfigService

router = APIRouter()


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """
    Get current application settings.
    API keys are stored in the database and can be updated via the UI.
    """
    config_service = AppConfigService(db)
    
    slack_token = await config_service.get("SLACK_API_TOKEN")
    google_key = await config_service.get("GOOGLE_API_KEY")
    
    return SettingsResponse(
        slack_api_token_configured=bool(slack_token),
        google_api_key_configured=bool(google_key),
        gemini_model=settings.GEMINI_MODEL,
        analysis_period_days=settings.ANALYSIS_PERIOD_DAYS,
        message_batch_size=settings.MESSAGE_BATCH_SIZE,
        health_score_calculation_hour=settings.HEALTH_SCORE_CALCULATION_HOUR,
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(
    request: SettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update API keys.
    Only provided keys will be updated.
    """
    config_service = AppConfigService(db)
    
    try:
        if request.slack_api_token is not None:
            if request.slack_api_token.strip():
                await config_service.set("SLACK_API_TOKEN", request.slack_api_token.strip())
            else:
                await config_service.delete("SLACK_API_TOKEN")
        
        if request.google_api_key is not None:
            if request.google_api_key.strip():
                await config_service.set("GOOGLE_API_KEY", request.google_api_key.strip())
            else:
                await config_service.delete("GOOGLE_API_KEY")
        
        # Return updated settings
        slack_token = await config_service.get("SLACK_API_TOKEN")
        google_key = await config_service.get("GOOGLE_API_KEY")
        
        return SettingsResponse(
            slack_api_token_configured=bool(slack_token),
            google_api_key_configured=bool(google_key),
            gemini_model=settings.GEMINI_MODEL,
            analysis_period_days=settings.ANALYSIS_PERIOD_DAYS,
            message_batch_size=settings.MESSAGE_BATCH_SIZE,
            health_score_calculation_hour=settings.HEALTH_SCORE_CALCULATION_HOUR,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

