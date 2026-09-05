from pydantic import BaseModel, Field
from uuid import UUID

class PaymentFailedEvent(BaseModel):
    organization_id: UUID
    customer_id: UUID
    customer_name: str
    amount: float = Field(gt=0)
    currency: str = "INR"
    reason: str
    attempt_number: int = Field(default=1, ge=1)
    payment_method: str = "card"
    provider: str | None = None
    provider_payment_id: str | None = None

class PaymentCreateRequest(BaseModel):
    customer_name: str = Field(min_length=1, max_length=160)
    customer_email: str | None = None
    amount: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    status: str = Field(default="success", min_length=2, max_length=40)
    payment_method: str = Field(default="card", min_length=2, max_length=80)
    provider: str | None = None
    payment_number: str | None = None

class NormalizedWebhookEvent(BaseModel):
    provider: str
    provider_event_id: str | None = None
    event_type: str
    payment: PaymentFailedEvent
