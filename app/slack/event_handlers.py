from datetime import datetime
from typing import Dict
from slack_sdk.web.async_client import AsyncWebClient

from app.utils.logger import setup_logger
from app.database import async_session_maker
from app.services.message_service import MessageService
from app.services.channel_service import ChannelService

logger = setup_logger(__name__)


async def process_message_event(event: dict, client: AsyncWebClient):
    """
    Process incoming message events from Slack.

    Stores the message in the database for later analysis.
    """
    # Skip bot messages and message changes
    if event.get("subtype") in ["bot_message", "message_changed", "message_deleted"]:
        return

    channel_id = event.get("channel")
    message_ts = event.get("ts")
    user_id = event.get("user")
    text = event.get("text", "")

    # Skip empty messages
    if not text.strip():
        return

    try:
        async with async_session_maker() as session:
            channel_service = ChannelService(session)
            message_service = MessageService(session)

            # Get or create channel
            channel = await channel_service.get_by_slack_id(channel_id)
            if not channel:
                # Fetch channel info from Slack
                try:
                    channel_info = await client.conversations_info(channel=channel_id)
                    channel_name = channel_info["channel"].get("name", channel_id)
                except Exception:
                    channel_name = channel_id

                channel = await channel_service.create(
                    slack_channel_id=channel_id,
                    name=channel_name,
                )

            # Check if channel is monitored
            if not channel.is_monitored:
                return

            # Determine user type
            user_type = "customer"  # Default
            try:
                # Get bot user ID to identify internal messages
                from app.slack.api_client import SlackAPIClient
                slack_client = SlackAPIClient()
                bot_user_id = await slack_client.get_bot_user_id()

                if user_id == bot_user_id:
                    user_type = "bot"
                else:
                    # Could add logic here to identify internal team members
                    # For now, assume non-bot users are customers
                    user_type = "customer"
            except Exception:
                pass

            # Store message
            message_timestamp = datetime.fromtimestamp(float(message_ts))
            await message_service.create(
                channel_id=channel.id,
                slack_message_ts=message_ts,
                slack_user_id=user_id,
                user_type=user_type,
                content=text,
                message_timestamp=message_timestamp,
            )

            logger.debug(f"Stored message from channel {channel_id}")

    except Exception as e:
        logger.error(f"Error processing message event: {e}")


async def process_channel_join(event: dict, client: AsyncWebClient):
    """
    Process channel join events when bot is added to a channel.

    Creates or updates the channel in the database.
    """
    channel_id = event.get("channel")

    try:
        async with async_session_maker() as session:
            channel_service = ChannelService(session)

            # Check if channel already exists
            existing = await channel_service.get_by_slack_id(channel_id)
            if existing:
                logger.info(f"Bot rejoined existing channel: {channel_id}")
                return

            # Fetch channel info from Slack
            channel_info = await client.conversations_info(channel=channel_id)
            channel_data = channel_info.get("channel", {})

            # Create channel record
            await channel_service.create(
                slack_channel_id=channel_id,
                name=channel_data.get("name", channel_id),
                channel_type="customer_support",
            )

            logger.info(f"Bot joined new channel: {channel_data.get('name', channel_id)}")

    except Exception as e:
        logger.error(f"Error processing channel join event: {e}")


async def process_reaction(event: dict, client: AsyncWebClient):
    """
    Process reaction events for additional sentiment signals.

    Positive reactions (thumbsup, heart, etc.) and negative reactions
    can be used as additional sentiment indicators.
    """
    reaction = event.get("reaction", "")
    item = event.get("item", {})

    # Map common reactions to sentiment signals
    positive_reactions = {"thumbsup", "+1", "heart", "star", "tada", "clap", "smile"}
    negative_reactions = {"thumbsdown", "-1", "angry", "disappointed", "cry"}

    if reaction in positive_reactions:
        sentiment_signal = "positive"
    elif reaction in negative_reactions:
        sentiment_signal = "negative"
    else:
        return  # Ignore neutral reactions

    channel_id = item.get("channel")
    message_ts = item.get("ts")

    try:
        async with async_session_maker() as session:
            message_service = MessageService(session)

            # Update message metadata with reaction signal
            await message_service.add_reaction_signal(
                channel_slack_id=channel_id,
                message_ts=message_ts,
                signal=sentiment_signal,
            )

            logger.debug(f"Recorded {sentiment_signal} reaction on message {message_ts}")

    except Exception as e:
        logger.error(f"Error processing reaction event: {e}")
