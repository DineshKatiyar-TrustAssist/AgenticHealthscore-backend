from fastapi import APIRouter

from app.api.v1 import customers, channels, health_scores, action_items, dashboard, settings, auth

api_router = APIRouter()

api_router.include_router(
    customers.router,
    prefix="/customers",
    tags=["Customers"],
)

api_router.include_router(
    channels.router,
    prefix="/channels",
    tags=["Channels"],
)

api_router.include_router(
    health_scores.router,
    prefix="/health-scores",
    tags=["Health Scores"],
)

api_router.include_router(
    action_items.router,
    prefix="/action-items",
    tags=["Action Items"],
)

api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
)

api_router.include_router(
    settings.router,
    prefix="/settings",
    tags=["Settings"],
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)
