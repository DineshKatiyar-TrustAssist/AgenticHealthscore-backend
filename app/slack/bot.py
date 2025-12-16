import asyncio
from typing import Optional
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Initialize Slack Bolt app lazily
slack_app: Optional[AsyncApp] = None

# Global handler reference
socket_handler: Optional[AsyncSocketModeHandler] = None


def get_slack_app() -> Optional[AsyncApp]:
    """
    Get or initialize the Slack app.
    
    Note: Bot functionality is disabled for batch-on-demand mode.
    This requires SLACK_SIGNING_SECRET which is not used in API-only mode.
    """
    global slack_app

    if slack_app is not None:
        return slack_app

    # Bot mode disabled - requires SLACK_SIGNING_SECRET which is not available in API-only mode
    # Using SLACK_API_TOKEN for batch-on-demand processing instead
    if not settings.SLACK_API_TOKEN:
        logger.warning("Slack API token not configured. Slack app not initialized.")
        return None
    
    # Note: SLACK_SIGNING_SECRET is required for Bolt app but not available in API-only mode
    # This will prevent bot initialization, which is intended for batch-on-demand deployment
    logger.info("Slack bot mode disabled - using batch-on-demand API processing")
    return None

    # Original bot initialization code (disabled):
    # if not settings.SLACK_BOT_TOKEN or not settings.SLACK_SIGNING_SECRET:
    #     logger.warning("Slack tokens not configured. Slack app not initialized.")
    #     return None
    #
    # slack_app = AsyncApp(
    #     token=settings.SLACK_BOT_TOKEN,
    #     signing_secret=settings.SLACK_SIGNING_SECRET,
    # )
    #
    # # Register event handlers
    # _register_handlers(slack_app)
    #
    # return slack_app


def _register_handlers(app: AsyncApp):
    """Register all Slack event handlers."""

    @app.event("message")
    async def handle_message(event: dict, say, client):
        """Handle incoming messages from Slack channels."""
        from app.slack.event_handlers import process_message_event
        await process_message_event(event, client)

    @app.event("member_joined_channel")
    async def handle_member_joined(event: dict, client):
        """Handle when bot is added to a channel."""
        from app.slack.event_handlers import process_channel_join
        await process_channel_join(event, client)

    @app.event("reaction_added")
    async def handle_reaction(event: dict, client):
        """Track reactions for sentiment signals."""
        from app.slack.event_handlers import process_reaction
        await process_reaction(event, client)

    @app.command("/healthscore")
    async def handle_healthscore_command(ack, respond, command):
        """Slash command to calculate health score for a channel."""
        await ack()

        channel_id = command.get("channel_id")
        user_id = command.get("user_id")

        await respond(
            f"Calculating health score for this channel... Please wait.",
            response_type="ephemeral",
        )

        try:
            from app.services.health_score_service import HealthScoreService
            from app.database import async_session_maker

            async with async_session_maker() as session:
                service = HealthScoreService(session)
                result = await service.calculate_for_channel(channel_id)

                if result:
                    await respond(
                        f"*Health Score Analysis Complete*\n\n"
                        f"Score: *{result['score']}/10*\n"
                        f"Churn Risk: *{result['churn_probability']:.1%}*\n"
                        f"Messages Analyzed: {result['messages_analyzed']}\n\n"
                        f"_{result.get('reasoning', 'No additional details')}_",
                        response_type="in_channel",
                    )
                else:
                    await respond(
                        "Could not calculate health score. Make sure this channel is linked to a customer.",
                        response_type="ephemeral",
                    )
        except Exception as e:
            logger.error(f"Error in healthscore command: {e}")
            await respond(
                f"Error calculating health score: {str(e)}",
                response_type="ephemeral",
            )


async def start_slack_bot():
    """
    Start the Slack bot using Socket Mode.
    
    Note: Bot functionality is disabled for batch-on-demand mode.
    This function will not start the bot as SLACK_APP_TOKEN is not available.
    """
    global socket_handler

    # Bot mode disabled - SLACK_APP_TOKEN not available in API-only mode
    logger.info("Slack bot startup disabled - using batch-on-demand API processing")
    return

    # Original bot startup code (disabled):
    # if not settings.SLACK_BOT_TOKEN or not settings.SLACK_APP_TOKEN:
    #     logger.warning("Slack tokens not configured. Slack bot will not start.")
    #     return
    #
    # app = get_slack_app()
    # if not app:
    #     return
    #
    # try:
    #     socket_handler = AsyncSocketModeHandler(app, settings.SLACK_APP_TOKEN)
    #     logger.info("Starting Slack bot with Socket Mode...")
    #     await socket_handler.start_async()
    # except Exception as e:
    #     logger.error(f"Failed to start Slack bot: {e}")
    #     raise


async def stop_slack_bot():
    """Stop the Slack bot gracefully."""
    global socket_handler

    if socket_handler:
        await socket_handler.close_async()
        logger.info("Slack bot stopped")
