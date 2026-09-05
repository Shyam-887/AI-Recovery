import hashlib
import json
from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.database import get_db
from app.core.config import settings
from app.integrations.stripe_adapter import StripeAdapter
from app.integrations.razorpay_adapter import RazorpayAdapter
from app.models.webhook_event import WebhookEvent
from app.schemas.events import PaymentFailedEvent
from app.services.recovery_service import RecoveryService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
service = RecoveryService()

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    adapter = StripeAdapter(settings.stripe_webhook_secret)
    if not adapter.verify_webhook(payload, stripe_signature or ""):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    data = json.loads(payload)
    event_id = data.get("id")
    event_type = data.get("type", "unknown")

    if event_type != "payment_intent.payment_failed":
        return {"status": "ignored", "event_type": event_type}

    obj = data.get("data", {}).get("object", {})
    metadata = obj.get("metadata", {})
    try:
        event = PaymentFailedEvent(
            organization_id=metadata["organization_id"],
            customer_id=metadata["customer_id"],
            customer_name=metadata.get("customer_name", "Unknown"),
            amount=float(obj.get("amount", 0)) / 100,
            currency=(obj.get("currency") or "INR").upper(),
            reason=obj.get("last_payment_error", {}).get("code", "payment_failed"),
            attempt_number=int(metadata.get("attempt_number", 1)),
            payment_method=_stripe_method(obj),
            provider="stripe",
            provider_payment_id=obj.get("id"),
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid Stripe event: {exc}")

    payload_hash = hashlib.sha256(payload).hexdigest()
    duplicate = await _is_duplicate(db, "stripe", event_id, payload_hash)
    if duplicate:
        return {"status": "duplicate", "event_id": event_id}

    db.add(WebhookEvent(
        provider="stripe",
        provider_event_id=event_id,
        event_type=event_type,
        payload_hash=payload_hash,
        status="received",
    ))
    await db.commit()

    return await service.create_case(db, event)

@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    adapter = RazorpayAdapter(settings.razorpay_webhook_secret)
    if not adapter.verify_webhook(payload, x_razorpay_signature or ""):
        raise HTTPException(status_code=400, detail="Invalid Razorpay signature")

    data = json.loads(payload)
    event_type = data.get("event", "unknown")
    event_id = data.get("payload", {}).get("payment", {}).get("entity", {}).get("id")

    if event_type not in {"payment.failed", "payment.authorized"}:
        return {"status": "ignored", "event_type": event_type}

    entity = data.get("payload", {}).get("payment", {}).get("entity", {})
    notes = entity.get("notes", {})
    if event_type == "payment.authorized":
        return {"status": "ignored", "event_type": event_type}

    try:
        event = PaymentFailedEvent(
            organization_id=notes["organization_id"],
            customer_id=notes["customer_id"],
            customer_name=notes.get("customer_name", "Unknown"),
            amount=float(entity.get("amount", 0)) / 100,
            currency=entity.get("currency", "INR"),
            reason=entity.get("error_code") or "payment_failed",
            attempt_number=int(notes.get("attempt_number", 1)),
            payment_method=_razorpay_method(entity),
            provider="razorpay",
            provider_payment_id=entity.get("id"),
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid Razorpay event: {exc}")

    payload_hash = hashlib.sha256(payload).hexdigest()
    duplicate = await _is_duplicate(db, "razorpay", event_id, payload_hash)
    if duplicate:
        return {"status": "duplicate", "event_id": event_id}

    db.add(WebhookEvent(
        provider="razorpay",
        provider_event_id=event_id,
        event_type=event_type,
        payload_hash=payload_hash,
        status="received",
    ))
    await db.commit()

    return await service.create_case(db, event)

async def _is_duplicate(db, provider, event_id, payload_hash):
    from sqlalchemy import select
    if event_id:
        result = await db.execute(
            select(WebhookEvent).where(
                WebhookEvent.provider == provider,
                WebhookEvent.provider_event_id == event_id,
            )
        )
        if result.scalar_one_or_none():
            return True

    result = await db.execute(
        select(WebhookEvent).where(
            WebhookEvent.provider == provider,
            WebhookEvent.payload_hash == payload_hash,
        )
    )
    return result.scalar_one_or_none() is not None


def _stripe_method(obj):
    details = obj.get("payment_method_types") or []
    method = details[0] if details else "card"
    card = (obj.get("last_payment_error") or {}).get("payment_method", {})
    card_details = card.get("card", {}) if isinstance(card, dict) else {}
    last4 = card_details.get("last4")
    return f"{method} •••• {last4}" if last4 else method

def _razorpay_method(entity):
    method = entity.get("method") or "card"
    card = entity.get("card") or {}
    last4 = card.get("last4")
    return f"{method} •••• {last4}" if last4 else method
