from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.channel_service import ChannelService
from app.services.message_service import MessageService
from app.services.customer_service import CustomerService
from app.slack.api_client import SlackAPIClient
from app.schemas.channel import (
    ChannelCreate,
    ChannelUpdate,
    ChannelResponse,
    ChannelListResponse,
    ChannelLinkCustomer,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.get("", response_model=ChannelListResponse)
async def list_channels(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    monitored_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List all channels with pagination."""
    service = ChannelService(db)
    channels, total = await service.get_all(
        skip=skip, limit=limit, monitored_only=monitored_only
    )

    response_channels = []
    for channel in channels:
        data = await service.get_with_message_count(channel.id)
        customer_name = None
        if channel.customer_id:
            customer_service = CustomerService(db)
            customer = await customer_service.get_by_id(channel.customer_id)
            if customer:
                customer_name = customer.name

        response_channels.append(
            ChannelResponse(
                id=channel.id,
                slack_channel_id=channel.slack_channel_id,
                name=channel.name,
                customer_id=channel.customer_id,
                customer_name=customer_name,
                channel_type=channel.channel_type,
                is_monitored=channel.is_monitored,
                created_at=channel.created_at,
                updated_at=channel.updated_at,
                message_count=data.get("message_count", 0) if data else 0,
            )
        )

    return ChannelListResponse(channels=response_channels, total=total)


@router.post("/sync")
async def sync_channels(
    db: AsyncSession = Depends(get_db),
):
    """Sync channels from Slack."""
    try:
        from app.utils.api_keys import get_slack_api_token
        slack_token = await get_slack_api_token(db)
        if not slack_token:
            raise HTTPException(
                status_code=400,
                detail="SLACK_API_TOKEN is not configured. Please set it in the Settings page."
            )
        slack_client = SlackAPIClient(token=slack_token)
        slack_channels = await slack_client.list_channels()

        service = ChannelService(db)
        synced = 0

        for ch in slack_channels:
            existing = await service.get_by_slack_id(ch["id"])
            if not existing:
                await service.create(
                    slack_channel_id=ch["id"],
                    name=ch.get("name", ch["id"]),
                )
                synced += 1

        await db.commit()
        return {"synced": synced, "total_slack_channels": len(slack_channels)}

    except Exception as e:
        logger.error(f"Error syncing channels: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync channels: {str(e)}")


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a channel by ID."""
    service = ChannelService(db)
    data = await service.get_with_message_count(channel_id)

    if not data:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel = data["channel"]
    customer_name = None
    if channel.customer_id:
        customer_service = CustomerService(db)
        customer = await customer_service.get_by_id(channel.customer_id)
        if customer:
            customer_name = customer.name

    return ChannelResponse(
        id=channel.id,
        slack_channel_id=channel.slack_channel_id,
        name=channel.name,
        customer_id=channel.customer_id,
        customer_name=customer_name,
        channel_type=channel.channel_type,
        is_monitored=channel.is_monitored,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
        message_count=data.get("message_count", 0),
    )


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: str,
    data: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a channel."""
    service = ChannelService(db)
    channel = await service.update(channel_id, data)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    return ChannelResponse(
        id=channel.id,
        slack_channel_id=channel.slack_channel_id,
        name=channel.name,
        customer_id=channel.customer_id,
        channel_type=channel.channel_type,
        is_monitored=channel.is_monitored,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.put("/{channel_id}/customer", response_model=ChannelResponse)
async def link_channel_to_customer(
    channel_id: str,
    data: ChannelLinkCustomer,
    db: AsyncSession = Depends(get_db),
):
    """Link a channel to a customer."""
    # Verify customer exists
    customer_service = CustomerService(db)
    customer = await customer_service.get_by_id(data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    service = ChannelService(db)
    channel = await service.link_customer(channel_id, data.customer_id)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    return ChannelResponse(
        id=channel.id,
        slack_channel_id=channel.slack_channel_id,
        name=channel.name,
        customer_id=channel.customer_id,
        customer_name=customer.name,
        channel_type=channel.channel_type,
        is_monitored=channel.is_monitored,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.delete("/{channel_id}/customer", response_model=ChannelResponse)
async def unlink_channel_from_customer(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Unlink a channel from its customer."""
    service = ChannelService(db)
    channel = await service.unlink_customer(channel_id)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    return ChannelResponse(
        id=channel.id,
        slack_channel_id=channel.slack_channel_id,
        name=channel.name,
        customer_id=channel.customer_id,
        channel_type=channel.channel_type,
        is_monitored=channel.is_monitored,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.post("/{channel_id}/fetch-history")
async def fetch_channel_history(
    channel_id: str,
    days: int = Query(30, ge=1, le=365),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """Fetch historical messages from a Slack channel."""
    service = ChannelService(db)
    channel = await service.get_by_id(channel_id)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    try:
        from datetime import datetime, timedelta, timezone
        from slack_sdk.errors import SlackApiError
        from app.utils.api_keys import get_slack_api_token

        slack_token = await get_slack_api_token(db)
        if not slack_token:
            raise HTTPException(
                status_code=400,
                detail="SLACK_API_TOKEN is not configured. Please set it in the Settings page."
            )
        slack_client = SlackAPIClient(token=slack_token)
        oldest = datetime.now(timezone.utc) - timedelta(days=days)

        messages = await slack_client.fetch_channel_history(
            channel_id=channel.slack_channel_id,
            oldest=oldest,
        )

        # Store messages
        message_service = MessageService(db)
        messages_data = [
            {
                "channel_id": channel.id,
                "ts": msg["ts"],
                "text": msg.get("text", ""),
                "user": msg.get("user"),
                "user_type": "customer",  # Default, could be enhanced
            }
            for msg in messages
            if msg.get("text")  # Skip empty messages
        ]

        created = await message_service.bulk_create(messages_data)
        await db.commit()

        return {
            "channel_id": str(channel_id),
            "messages_fetched": len(messages),
            "messages_stored": created,
        }

    except SlackApiError as e:
        error_data = e.response
        if error_data and error_data.get("error") == "not_in_channel":
            error_message = (
                f"Cannot fetch history: The bot is not a member of channel #{channel.name}. "
                f"Please add the bot to the channel in Slack first."
            )
            logger.error(f"Error fetching channel history: {error_message}")
            raise HTTPException(status_code=403, detail=error_message)
        else:
            logger.error(f"Error fetching channel history: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching channel history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


@router.put("/{channel_id}/monitoring")
async def set_channel_monitoring(
    channel_id: str,
    is_monitored: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable monitoring for a channel."""
    service = ChannelService(db)
    channel = await service.set_monitoring(channel_id, is_monitored)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    return {"channel_id": str(channel_id), "is_monitored": channel.is_monitored}
