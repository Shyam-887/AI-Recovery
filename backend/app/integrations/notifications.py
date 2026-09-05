from typing import Protocol

class NotificationProvider(Protocol):
    async def send(self, to: str, subject: str, body: str) -> dict: ...

class ConsoleNotificationProvider:
    async def send(self, to: str, subject: str, body: str) -> dict:
        print(f"[notification] to={to} subject={subject} body={body}")
        return {"provider": "console", "status": "sent"}
