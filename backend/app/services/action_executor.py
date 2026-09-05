from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recovery import RecoveryAction, RecoveryCase
from app.models.audit import AuditLog
from app.models.customer import Customer
from app.integrations.notifications import ConsoleNotificationProvider
from app.integrations.stripe_payments import StripePaymentAdapter
from app.integrations.razorpay_payments import RazorpayPaymentAdapter

class ActionExecutor:
    async def execute(self, db: AsyncSession, case: RecoveryCase, action: RecoveryAction):
        customer = await db.get(Customer, case.customer_id)

        if case.action in {"send_payment_link", "send_payment_update_link"}:
            provider = ConsoleNotificationProvider()
            result = await provider.send(
                customer.email if customer and customer.email else "customer@example.com",
                "Payment recovery",
                f"Your payment of {case.currency} {case.amount} needs attention.",
            )
        elif case.action == "retry_payment":
            result = {"status": "queued_for_provider_retry"}
        elif case.action == "schedule_retry":
            result = {"status": "scheduled", "delay_hours": 24}
        else:
            result = {"status": "not_executable"}

        action.provider_response = str(result)
        action.status = "completed" if result.get("status") in {
            "sent", "scheduled", "queued_for_provider_retry"
        } else "failed"
        action.completed_at = datetime.now(timezone.utc)

        case.status = "action_executed" if action.status == "completed" else "action_failed"
        case.executed_at = datetime.now(timezone.utc)

        db.add(AuditLog(
            organization_id=case.organization_id,
            case_id=case.id,
            event_type="recovery_action_executed",
            actor="action-executor",
            details=str(result),
        ))
