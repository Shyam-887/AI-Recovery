from pathlib import Path
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.payment import Payment
from app.schemas.events import PaymentCreateRequest, PaymentFailedEvent
from app.services.recovery_service import RecoveryService

router = APIRouter()
service = RecoveryService()
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "payment-receipts"
ALLOWED_RECEIPT_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
MAX_RECEIPT_SIZE = 10 * 1024 * 1024

@router.post("/events/payment-failed")
async def payment_failed(
    event: PaymentFailedEvent,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("admin", "manager", "agent")),
):
    # Prevent cross-tenant event injection.
    if str(event.organization_id) != user["organization_id"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Organization mismatch")
    return await service.create_case(db, event)

@router.get("/payments")
async def payments(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = UUID(user["organization_id"])
    return await service.list_payments(db, tenant_id)


@router.post("/payments")
async def create_payment(
    payload: PaymentCreateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("admin", "manager", "agent")),
):
    return await service.record_payment(db, UUID(user["organization_id"]), payload)


@router.delete("/payments/{payment_id}")
async def clear_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("admin", "manager", "agent")),
):
    payment = await db.scalar(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.organization_id == UUID(user["organization_id"]),
        )
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    await db.delete(payment)
    await db.commit()
    return {"payment_id": str(payment_id), "status": "cleared"}


@router.post("/payments/{payment_id}/receipt")
async def upload_payment_receipt(
    payment_id: UUID,
    receipt: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("admin", "manager", "agent")),
):
    tenant_id = UUID(user["organization_id"])
    payment = await db.scalar(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.organization_id == tenant_id,
        )
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if receipt.content_type not in ALLOWED_RECEIPT_TYPES:
        raise HTTPException(status_code=415, detail="Only PDF, JPG, PNG, or WEBP files are allowed")

    contents = await receipt.read(MAX_RECEIPT_SIZE + 1)
    if len(contents) > MAX_RECEIPT_SIZE:
        raise HTTPException(status_code=413, detail="Receipt must be 10 MB or smaller")

    suffix = Path(receipt.filename or "receipt").suffix.lower()
    if suffix not in {".pdf", ".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=415, detail="Unsupported receipt file extension")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{payment_id}-{uuid4().hex}{suffix}"
    stored_path = UPLOAD_DIR / stored_name
    stored_path.write_bytes(contents)
    payment.receipt_filename = receipt.filename or stored_name
    payment.receipt_path = str(stored_path)
    await db.commit()
    return {
        "payment_id": str(payment.id),
        "receipt_filename": payment.receipt_filename,
    }

@router.get("/recovery/cases")
async def cases(
    organization_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = UUID(user["organization_id"])
    requested = organization_id or tenant_id
    if requested != tenant_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Organization mismatch")
    return await service.list_cases(db, tenant_id)
