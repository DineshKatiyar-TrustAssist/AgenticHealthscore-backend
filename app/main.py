from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import init_db
from app.api.v1.router import api_router
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests."""
    async def dispatch(self, request: Request, call_next):
        import sys
        # Force flush to ensure logs appear immediately
        print(f"REQUEST: {request.method} {request.url.path}", flush=True, file=sys.stdout)
        logger.info(f"Incoming request: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
        try:
            response = await call_next(request)
            logger.info(f"Response status: {response.status_code} for {request.method} {request.url.path}")
            print(f"RESPONSE: {response.status_code} for {request.method} {request.url.path}", flush=True, file=sys.stdout)
            return response
        except Exception as e:
            logger.error(f"Error processing request {request.method} {request.url.path}: {str(e)}", exc_info=True)
            print(f"ERROR: {request.method} {request.url.path}: {str(e)}", flush=True, file=sys.stdout)
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    try:
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
        
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Start scheduler
        from app.scheduler.jobs import start_scheduler
        start_scheduler()
        logger.info("Scheduler started")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise

    yield

    # Shutdown
    try:
        logger.info("Shutting down...")
        from app.scheduler.jobs import stop_scheduler
        stop_scheduler()
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Agentic AI-powered customer health scoring system that analyzes Slack conversations to predict churn and suggest actions.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Request logging middleware (add before CORS)
app.add_middleware(LoggingMiddleware)

# CORS middleware
# Ensure CORS_ORIGINS is a list
cors_origins = settings.CORS_ORIGINS
if isinstance(cors_origins, str):
    cors_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
elif not isinstance(cors_origins, list):
    cors_origins = list(cors_origins) if cors_origins else ["http://localhost:3000"]

logger.info(f"CORS allowed origins: {cors_origins}")
logger.info(f"CORS origins type: {type(cors_origins)}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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


@app.post("/api/v1/test-logging")
async def test_logging():
    """Test endpoint to verify logging is working."""
    logger.info("TEST: Logging test endpoint called")
    logger.warning("TEST: This is a warning log")
    logger.error("TEST: This is an error log (test only)")
    return {"message": "Logging test successful", "check_logs": True}


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle OPTIONS requests for CORS preflight."""
    return {"status": "ok"}
