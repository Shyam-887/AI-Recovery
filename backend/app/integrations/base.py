from typing import Protocol

class PaymentGateway(Protocol):
    def verify_webhook(self, payload: bytes, signature: str) -> bool: ...
