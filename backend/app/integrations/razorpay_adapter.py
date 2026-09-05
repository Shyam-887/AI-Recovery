import hmac
import hashlib

class RazorpayAdapter:
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        if not self.webhook_secret or not signature:
            return False
        digest = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(digest, signature)
