from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "revenue_recovery",
    broker=settings.redis_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=False,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)
