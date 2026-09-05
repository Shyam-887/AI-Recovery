from typing import Any

class StripePaymentAdapter:
    """Payment execution boundary.

    Real Stripe SDK calls should be enabled only after STRIPE_SECRET_KEY is configured.
    Keeping this behind an adapter prevents provider logic from leaking into the worker.
    """

    def __init__(self, secret_key: str = ""):
        self.secret_key = secret_key

    async def create_payment_link(self, amount: float, currency: str, customer_id: str) -> dict[str, Any]:
        if not self.secret_key:
            return {
                "provider": "stripe",
                "status": "simulation",
                "message": "STRIPE_SECRET_KEY is not configured",
            }
        return {
            "provider": "stripe",
            "status": "ready",
            "message": "Connect the Stripe SDK/API call here.",
            "customer_id": customer_id,
            "amount": amount,
            "currency": currency,
        }

    async def retry_payment(self, provider_payment_id: str) -> dict[str, Any]:
        if not self.secret_key:
            return {"provider": "stripe", "status": "simulation", "message": "Retry simulated"}
        return {
            "provider": "stripe",
            "status": "ready",
            "message": "Connect payment-method confirmation/retry flow here.",
            "provider_payment_id": provider_payment_id,
        }
