from datetime import datetime
from typing import List, Dict, Optional
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SlackAPIClient:
    """Client for fetching historical Slack data via API."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize Slack API client.
        
        Args:
            token: Slack API token. If not provided, will raise ValueError.
        """
        if not token:
            raise ValueError("SLACK_API_TOKEN is not configured. Please set it in the Settings page.")
        self.client = AsyncWebClient(token=token)

    async def fetch_channel_history(
        self,
        channel_id: str,
        oldest: Optional[datetime] = None,
        latest: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict]:
        """
        Fetch message history from a Slack channel.

        Args:
            channel_id: Slack channel ID
            oldest: Start datetime for messages
            latest: End datetime for messages
            limit: Maximum messages to fetch

        Returns:
            List of message dictionaries
        """
        messages = []
        cursor = None

        # Convert datetimes to Unix timestamps
        oldest_ts = str(oldest.timestamp()) if oldest else None
        latest_ts = str(latest.timestamp()) if latest else None

        try:
            while len(messages) < limit:
                response = await self.client.conversations_history(
                    channel=channel_id,
                    oldest=oldest_ts,
                    latest=latest_ts,
                    limit=min(200, limit - len(messages)),
                    cursor=cursor,
                )

                messages.extend(response.get("messages", []))

                # Check for pagination
                if response.get("has_more") and response.get("response_metadata"):
                    cursor = response["response_metadata"].get("next_cursor")
                else:
                    break

            logger.info(f"Fetched {len(messages)} messages from channel {channel_id}")
            return messages

        except SlackApiError as e:
            logger.error(f"Error fetching channel history: {e}")
            raise

    async def fetch_channel_info(self, channel_id: str) -> Dict:
        """Get information about a Slack channel."""
        try:
            response = await self.client.conversations_info(channel=channel_id)
            return response.get("channel", {})
        except SlackApiError as e:
            logger.error(f"Error fetching channel info: {e}")
            raise

    async def fetch_user_info(self, user_id: str) -> Dict:
        """Get information about a Slack user."""
        try:
            response = await self.client.users_info(user=user_id)
            return response.get("user", {})
        except SlackApiError as e:
            logger.error(f"Error fetching user info: {e}")
            raise

    async def list_channels(
        self,
        types: str = "public_channel,private_channel",
        exclude_archived: bool = True,
    ) -> List[Dict]:
        """List all channels the bot has access to."""
        channels = []
        cursor = None

        try:
            while True:
                response = await self.client.conversations_list(
                    types=types,
                    exclude_archived=exclude_archived,
                    cursor=cursor,
                    limit=200,
                )

                channels.extend(response.get("channels", []))

                if response.get("response_metadata"):
                    cursor = response["response_metadata"].get("next_cursor")
                    if not cursor:
                        break
                else:
                    break

            return channels

        except SlackApiError as e:
            logger.error(f"Error listing channels: {e}")
            raise

    async def fetch_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
    ) -> List[Dict]:
        """Fetch all replies in a thread."""
        try:
            response = await self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
            )
            return response.get("messages", [])
        except SlackApiError as e:
            logger.error(f"Error fetching thread replies: {e}")
            raise

    async def get_bot_user_id(self) -> str:
        """Get the bot's user ID."""
        try:
            response = await self.client.auth_test()
            return response.get("user_id", "")
        except SlackApiError as e:
            logger.error(f"Error getting bot user ID: {e}")
            raise
