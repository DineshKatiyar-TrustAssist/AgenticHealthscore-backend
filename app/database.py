from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pathlib import Path
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Create async SQLite engine
try:
    db_url = settings.DATABASE_URL
    
    # Validate that we're using SQLite (this application only supports SQLite)
    if not db_url.startswith("sqlite"):
        raise ValueError(
            f"Invalid DATABASE_URL: '{db_url}'. This application only supports SQLite. "
            f"Please use a SQLite connection string like 'sqlite+aiosqlite:///./healthscore.db'"
        )
    
    # Extract path from connection string
    # Format: sqlite+aiosqlite:///path/to/db.db
    db_path = db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    
    # Create directory if it doesn't exist (for persistent storage paths)
    if db_path != ":memory:":
        db_dir = Path(db_path).parent
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
    
    # SQLite connection arguments
    connect_args = {"check_same_thread": False}
    
    engine = create_async_engine(
        db_url,
        echo=settings.DEBUG,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
    logger.info(f"SQLite database engine created: {db_path}")
        
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    raise

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    try:
        logger.info("Initializing database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        logger.error(f"Check DATABASE_URL configuration")
        raise
