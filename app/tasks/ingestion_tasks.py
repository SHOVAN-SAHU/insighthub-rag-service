from app.core.celery_app import celery_app
from app.services.ingestion_service import ingest_document
from app.services.embedding_service import generate_embeddings


@celery_app.task(bind=True, max_retries=3, default_retry_delay=15)
def ingest_document_task(self, document_id: str, metadata: dict):
    try:
        chunks = ingest_document(document_id, metadata)
        print(f"chunks from line 10: {chunks}")

        # Extract raw text for model input
        texts = [chunk["text"] for chunk in chunks]

        embeddings = generate_embeddings(texts)
        print(f"embeddings from like 16: {embeddings}")

        # Attach embedding back to each chunk
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        # Next step: store in vector DB
        # store_vectors(document_id, chunks)
    except Exception as exc:
        raise self.retry(exc=exc)
