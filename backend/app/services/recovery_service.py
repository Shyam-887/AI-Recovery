from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.payment import Payment
from app.models.recovery import RecoveryCase
from app.models.audit import AuditLog
from app.schemas.events import PaymentCreateRequest
from app.workers.recovery_tasks import process_recovery_case

class RecoveryService:
    async def record_payment(
        self,
        db: AsyncSession,
        organization_id: UUID,
        payload: PaymentCreateRequest,
    ):
        customer = None
        if payload.customer_email:
            customer = await db.scalar(
                select(Customer).where(
                    Customer.organization_id == organization_id,
                    Customer.email == payload.customer_email,
                )
            )
        if not customer:
            customer = Customer(
                organization_id=organization_id,
                name=payload.customer_name,
                email=payload.customer_email,
            )
            db.add(customer)
            await db.flush()

        payment = Payment(
            organization_id=organization_id,
            customer_id=customer.id,
            amount=payload.amount,
            currency=payload.currency.upper(),
            status=payload.status.lower(),
            payment_method=payload.payment_method,
            provider=payload.provider,
            provider_payment_id=payload.payment_number or f"manual-{uuid4().hex[:12]}",
        )
        db.add(payment)
        case = None
        if payment.status in {"failed", "declined"}:
            case = RecoveryCase(
                organization_id=organization_id,
                customer_id=customer.id,
                payment_id=payment.id,
                amount=payload.amount,
                currency=payload.currency.upper(),
                reason="manual_payment_failed",
                risk_score=0,
                action="pending_ai_decision",
                status="queued",
            )
            db.add(case)
            await db.flush()
        await db.commit()
        if case:
            process_recovery_case.delay(str(case.id))
        return {
            "payment_id": str(payment.id),
            "transaction_id": payment.provider_payment_id,
            "status": payment.status,
            "case_id": str(case.id) if case else None,
        }

    async def create_case(self, db: AsyncSession, event):
        customer = await db.get(Customer, event.customer_id)
        if not customer:
            customer = Customer(
                id=event.customer_id,
                organization_id=event.organization_id,
                name=event.customer_name,
            )
            db.add(customer)

        payment = Payment(
            organization_id=event.organization_id,
            customer_id=event.customer_id,
            amount=event.amount,
            currency=event.currency,
            status="failed",
            failure_reason=event.reason,
            attempt_number=event.attempt_number,
            payment_method=event.payment_method,
            provider=event.provider,
            provider_payment_id=event.provider_payment_id,
        )
        db.add(payment)
        await db.flush()

        case = RecoveryCase(
            organization_id=event.organization_id,
            customer_id=event.customer_id,
            payment_id=payment.id,
            amount=event.amount,
            currency=event.currency,
            reason=event.reason,
            risk_score=0,
            action="pending_ai_decision",
            status="queued",
        )
        db.add(case)
        await db.flush()

        db.add(AuditLog(
            organization_id=event.organization_id,
            case_id=case.id,
            event_type="payment_failed",
            actor="webhook",
            details=f"amount={event.amount};reason={event.reason}",
        ))

        await db.commit()

        # Queue only after the DB transaction has committed.
        process_recovery_case.delay(str(case.id))

        return {
            "case_id": str(case.id),
            "payment_id": str(payment.id),
            "status": "queued",
        }

    async def list_payments(self, db: AsyncSession, organization_id: UUID):
        stmt = (
            select(Payment, Customer)
            .join(Customer, Customer.id == Payment.customer_id)
            .where(Payment.organization_id == organization_id)
            .order_by(Payment.created_at.desc())
        )
        result = await db.execute(stmt)
        rows = []
        for payment, customer in result.all():
            rows.append({
                "id": str(payment.id),
                "transaction_id": payment.provider_payment_id or str(payment.id),
                "customer": customer.name,
                "customer_id": str(payment.customer_id),
                "amount": float(payment.amount),
                "currency": payment.currency,
                "status": payment.status,
                "failure_reason": payment.failure_reason,
                "attempt_number": payment.attempt_number,
                "payment_method": payment.payment_method,
                "provider": payment.provider,
                "receipt_filename": payment.receipt_filename,
                "created_at": payment.created_at.isoformat() if payment.created_at else None,
            })
        return rows

    async def list_cases(self, db: AsyncSession, organization_id: UUID | None = None):
        stmt = (
            select(RecoveryCase)
            .options(selectinload(RecoveryCase.customer))
            .options(selectinload(RecoveryCase.payment))
            .order_by(RecoveryCase.created_at.desc())
        )
        if organization_id:
            stmt = stmt.where(RecoveryCase.organization_id == organization_id)

        result = await db.execute(stmt)
        return [
            {
                "case_id": str(c.id),
                "customer_id": str(c.customer_id),
                "customer_name": c.customer.name if c.customer else None,
                "amount": float(c.amount),
                "currency": c.currency,
                "payment_method": c.payment.payment_method if c.payment else None,
                "provider": c.payment.provider if c.payment else None,
                "transaction_id": c.payment.provider_payment_id if c.payment else None,
                "payment_status": c.payment.status if c.payment else None,
                "reason": c.reason,
                "risk_score": c.risk_score,
                "recovery_probability": float(c.recovery_probability) if c.recovery_probability is not None else None,
                "root_cause": c.root_cause,
                "confidence": float(c.confidence) if c.confidence is not None else None,
                "action": c.action,
                "action_message": c.action_message,
                "status": c.status,
                "recovered": c.recovered,
                "human_approval_required": c.human_approval_required,
            }
            for c in result.scalars().all()
        ]
