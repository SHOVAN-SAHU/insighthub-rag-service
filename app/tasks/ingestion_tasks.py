from app.core.celery_app import celery_app
from app.services.ingestion_service import ingest_document


@celery_app.task(bind=True, max_retries=3, default_retry_delay=15)
def ingest_document_task(self, document_id: str, metadata: dict):
    try:
        ingest_document(document_id, metadata)
    except Exception as exc:
        raise self.retry(exc=exc)