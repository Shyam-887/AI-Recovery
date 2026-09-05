import hashlib
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.webhook_event import WebhookEvent

async def already_processed(
    db: AsyncSession,
    provider: str,
    provider_event_id: str,
    payload: dict,
) -> bool:
    if provider_event_id:
        result = await db.execute(
            select(WebhookEvent).where(
                WebhookEvent.provider == provider,
                WebhookEvent.provider_event_id == provider_event_id,
            )
        )
        if result.scalar_one_or_none():
            return True

    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()

    result = await db.execute(
        select(WebhookEvent).where(
            WebhookEvent.provider == provider,
            WebhookEvent.payload_hash == fingerprint,
        )
    )
    return result.scalar_one_or_none() is not None
