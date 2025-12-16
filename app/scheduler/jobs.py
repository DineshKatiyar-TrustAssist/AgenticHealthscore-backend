import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import async_session_maker
from app.agents.orchestrator import CustomerHealthOrchestrator
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def calculate_all_health_scores():
    """
    Scheduled job to calculate health scores for all customers.

    Runs daily at the configured hour.
    """
    logger.info("Starting scheduled health score calculation for all customers...")

    async with async_session_maker() as session:
        orchestrator = CustomerHealthOrchestrator(session)

        try:
            results = await orchestrator.analyze_all_customers()

            success_count = sum(1 for r in results if r.get("status") == "success")
            error_count = sum(1 for r in results if r.get("status") == "error")
            skipped_count = sum(1 for r in results if r.get("status") == "insufficient_data")

            logger.info(
                f"Scheduled health score calculation complete. "
                f"Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}"
            )

            await session.commit()

        except Exception as e:
            logger.error(f"Error in scheduled health score calculation: {e}")
            await session.rollback()


def start_scheduler():
    """Start the background scheduler."""
    if scheduler.running:
        logger.warning("Scheduler is already running")
        return

    # Add daily health score calculation job
    scheduler.add_job(
        calculate_all_health_scores,
        trigger=CronTrigger(hour=settings.HEALTH_SCORE_CALCULATION_HOUR),
        id="daily_health_score_calculation",
        name="Daily Health Score Calculation",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started. Daily health score calculation scheduled at {settings.HEALTH_SCORE_CALCULATION_HOUR}:00"
    )


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_scheduler_status() -> dict:
    """Get current scheduler status and job information."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })

    return {
        "running": scheduler.running,
        "jobs": jobs,
    }
