import hmac
import hashlib

class StripeAdapter:
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        if not self.webhook_secret or not signature:
            return False
        # Stripe-style timestamped signature: t=...,v1=...
        parts = dict(item.split("=", 1) for item in signature.split(",") if "=" in item)
        timestamp = parts.get("t")
        expected = parts.get("v1")
        if not timestamp or not expected:
            return False
        signed = f"{timestamp}.".encode() + payload
        digest = hmac.new(
            self.webhook_secret.encode(),
            signed,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(digest, expected)
