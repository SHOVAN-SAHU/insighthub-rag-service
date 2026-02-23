from app.core.celery_app import celery_app
from app.services.ingestion_service import ingest_document


@celery_app.task(bind=True, max_retries=3, default_retry_delay=15)
def ingest_document_task(self, document_id: str, metadata: dict):
    try:
        chunks = ingest_document(document_id, metadata)

        # Next step:
        # embeddings = embed_chunks(chunks)
        # store_vectors(document_id, embeddings)
    except Exception as exc:
        raise self.retry(exc=exc)