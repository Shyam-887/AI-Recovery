from typing import Any

class RazorpayPaymentAdapter:
    def __init__(self, key_id: str = "", key_secret: str = ""):
        self.key_id = key_id
        self.key_secret = key_secret

    async def create_payment_link(self, amount: float, currency: str, customer_id: str) -> dict[str, Any]:
        if not self.key_id or not self.key_secret:
            return {
                "provider": "razorpay",
                "status": "simulation",
                "message": "Razorpay credentials are not configured",
            }
        return {
            "provider": "razorpay",
            "status": "ready",
            "message": "Connect Razorpay SDK/API call here.",
            "customer_id": customer_id,
            "amount": amount,
            "currency": currency,
        }

    async def retry_payment(self, provider_payment_id: str) -> dict[str, Any]:
        if not self.key_id or not self.key_secret:
            return {"provider": "razorpay", "status": "simulation", "message": "Retry simulated"}
        return {
            "provider": "razorpay",
            "status": "ready",
            "message": "Connect Razorpay payment retry flow here.",
            "provider_payment_id": provider_payment_id,
        }
