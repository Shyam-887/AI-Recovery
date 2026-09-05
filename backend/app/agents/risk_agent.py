class RiskAgent:
    def score(self, amount: float, reason: str, attempt_number: int) -> int:
        score = 50

        if amount >= 100000:
            score += 30
        elif amount >= 50000:
            score += 20
        elif amount >= 5000:
            score += 10

        score += {
            "insufficient_funds": 15,
            "temporary_decline": 12,
            "network_error": 8,
            "expired_card": 10,
        }.get(reason.lower(), 5)

        score += max(0, 10 - (attempt_number - 1) * 5)
        return min(score, 99)
