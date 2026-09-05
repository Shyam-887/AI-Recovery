class RecommendationAgent:
    def recommend(self, reason: str, attempt_number: int) -> dict:
        reason = reason.lower()

        if reason in {"temporary_decline", "network_error"} and attempt_number < 3:
            return {"action": "retry_payment", "message": "Retry payment after a controlled delay."}

        if reason == "expired_card":
            return {"action": "send_payment_update_link", "message": "Send a secure payment-method update link."}

        if reason == "insufficient_funds" and attempt_number < 3:
            return {"action": "schedule_retry", "message": "Schedule one controlled retry after 24 hours."}

        return {"action": "send_payment_link", "message": "Send a secure payment link and monitor the case."}
