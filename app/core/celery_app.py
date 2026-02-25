from .config import settings
from celery import Celery

celery_app = Celery(
    "rag_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.ingestion_tasks"],
)

celery_app.conf.task_routes = {
    "app.tasks.ingestion_tasks.ingest_document_task": {"queue": "celery"},
}

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)