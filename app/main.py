from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.v1.router import api_router
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Slack bot task reference (disabled for batch-on-demand mode)
# slack_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # global slack_task

    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Slack bot disabled - using batch-on-demand API processing instead
    # Real-time bot functionality (Socket Mode) requires SLACK_APP_TOKEN and SLACK_SIGNING_SECRET
    # For initial deployment, we use only SLACK_API_TOKEN for on-demand message fetching
    # if settings.SLACK_BOT_TOKEN and settings.SLACK_APP_TOKEN:
    #     from app.slack.bot import start_slack_bot
    #
    #     slack_task = asyncio.create_task(start_slack_bot())
    #     logger.info("Slack bot task created")
    # else:
    #     logger.warning("Slack tokens not configured - bot will not start")

    # Start scheduler
    from app.scheduler.jobs import start_scheduler
    start_scheduler()
    logger.info("Scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Stop Slack bot (disabled)
    # if slack_task:
    #     from app.slack.bot import stop_slack_bot
    #
    #     await stop_slack_bot()
    #     slack_task.cancel()
    #     try:
    #         await slack_task
    #     except asyncio.CancelledError:
    #         pass
    #     logger.info("Slack bot stopped")

    # Stop scheduler
    from app.scheduler.jobs import stop_scheduler
    stop_scheduler()
    logger.info("Scheduler stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Agentic AI-powered customer health scoring system that analyzes Slack conversations to predict churn and suggest actions.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
    }
