from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_roles
from app.models.recovery import RecoveryCase
from app.models.payment import Payment
from app.workers.recovery_tasks import process_recovery_case

router = APIRouter(prefix="/recovery", tags=["recovery-actions"])

@router.post("/cases/{case_id}/execute")
async def execute_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("admin", "manager")),
):
    case = await db.scalar(select(RecoveryCase).where(RecoveryCase.id == case_id))
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    if str(case.organization_id) != user["organization_id"]:
        raise HTTPException(status_code=403, detail="Organization mismatch")

    if case.human_approval_required is False and case.status not in {
        "approval_required", "action_ready"
    }:
        raise HTTPException(status_code=409, detail=f"Case cannot be executed from status {case.status}")

    case.human_approval_required = False
    case.status = "queued"
    await db.commit()

    task = process_recovery_case.delay(str(case.id))
    return {"status": "queued", "task_id": task.id, "case_id": str(case.id)}


@router.post("/cases/{case_id}/mark-recovered")
async def mark_recovered(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("admin", "manager", "agent")),
):
    case = await db.scalar(select(RecoveryCase).where(RecoveryCase.id == case_id))
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    if str(case.organization_id) != user["organization_id"]:
        raise HTTPException(status_code=403, detail="Organization mismatch")

    case.recovered = True
    case.status = "recovered"
    if case.payment_id:
        payment = await db.scalar(select(Payment).where(Payment.id == case.payment_id))
        if payment:
            payment.status = "recovered"
    await db.commit()
    return {"case_id": str(case.id), "status": case.status, "recovered": True}
