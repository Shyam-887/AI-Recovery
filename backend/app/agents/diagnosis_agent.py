class DiagnosisAgent:
    def diagnose(self, reason: str) -> dict:
        mapping = {
            "insufficient_funds": "Customer balance may be insufficient.",
            "temporary_decline": "Issuer declined the payment temporarily.",
            "network_error": "Payment infrastructure/network interruption.",
            "expired_card": "Payment method has expired.",
        }
        known = reason.lower() in mapping
        return {
            "root_cause": mapping.get(reason.lower(), "Unknown payment failure."),
            "confidence": 0.90 if known else 0.55,
        }
