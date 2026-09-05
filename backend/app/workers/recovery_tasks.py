import asyncio
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.recovery import RecoveryCase, RecoveryAction
from app.models.audit import AuditLog
from app.agents.risk_agent import RiskAgent
from app.agents.diagnosis_agent import DiagnosisAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.policy import authorize
from app.services.action_executor import ActionExecutor

@celery_app.task(
    bind=True,
    name="recovery.process_case",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def process_recovery_case(self, case_id: str):
    return asyncio.run(_process(case_id))

async def _process(case_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RecoveryCase).where(RecoveryCase.id == case_id)
        )
        case = result.scalar_one_or_none()
        if not case:
            return {"status": "not_found", "case_id": case_id}

        risk = RiskAgent().score(float(case.amount), case.reason, 1)
        diagnosis = DiagnosisAgent().diagnose(case.reason)
        recommendation = RecommendationAgent().recommend(case.reason, 1)
        policy = authorize(recommendation["action"], float(case.amount))

        case.risk_score = risk
        case.root_cause = diagnosis["root_cause"]
        case.confidence = diagnosis["confidence"]
        case.action = recommendation["action"]
        case.action_message = recommendation["message"]
        case.human_approval_required = not policy["allowed"]

        if not policy["allowed"]:
            case.status = "approval_required"
            db.add(AuditLog(
                organization_id=case.organization_id,
                case_id=case.id,
                event_type="human_approval_required",
                actor="policy-engine",
                details=policy["reason"],
            ))
            await db.commit()
            return {"case_id": case_id, "status": case.status}

        action = RecoveryAction(
            case_id=case.id,
            action_type=case.action,
            channel="payment" if "payment" in case.action or "retry" in case.action else "whatsapp",
            status="pending",
        )
        db.add(action)
        await db.flush()

        await ActionExecutor().execute(db, case, action)
        await db.commit()

        return {
            "case_id": case_id,
            "status": case.status,
            "risk_score": risk,
            "action": case.action,
        }
