ALLOWED_ACTIONS = {
    "retry_payment",
    "schedule_retry",
    "send_payment_update_link",
    "send_payment_link",
    "notify_customer",
}

def authorize(action: str, amount: float) -> dict:
    if action not in ALLOWED_ACTIONS:
        return {"allowed": False, "reason": "Action is outside recovery policy."}

    if amount >= 100000 and action == "retry_payment":
        return {"allowed": False, "reason": "High-value retry requires human approval."}

    return {"allowed": True, "reason": "Action is within policy."}
