from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.ingestion_service import ingest_document
from app.services.embedding_service import generate_embeddings
from app.core.mongo_sync import get_database
from app.core.vector_db import upsert_chunks

COLLECTION_NAME = settings.collection_name


# ── Celery worker startup signal ─────────────────────────────────────────────
# Create the Qdrant collection ONCE when the worker process starts,
# not on every task invocation. This avoids a redundant API call per task.

from celery.signals import worker_ready
from app.core.vector_db import create_collection

@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    print(f"[worker_ready] Ensuring Qdrant collection '{COLLECTION_NAME}' exists...")
    try:
        create_collection(COLLECTION_NAME)
    except Exception as e:
        # Log but don't crash the worker — tasks will fail with clear errors
        # if the collection truly doesn't exist when needed.
        print(f"[worker_ready] WARNING: Could not create collection: {e}")


# ── Task ─────────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=15)
def ingest_document_task(self, document_id: str, metadata: dict):
    db = None

    try:
        db = get_database()

        # Mark as processing
        db.documents.update_one(
            {"document_id": document_id},
            {"$set": {"status": "processing"}},
            upsert=True,
        )

        # 1️⃣ Extract + Chunk
        chunks = ingest_document(document_id, metadata)

        if not chunks:
            db.documents.update_one(
                {"document_id": document_id},
                {"$set": {"status": "failed", "error": "No text extracted"}},
            )
            return

        # 2️⃣ Generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = generate_embeddings(texts)

        if len(embeddings) != len(chunks):
            raise ValueError(
                f"Embedding count mismatch: got {len(embeddings)} embeddings "
                f"for {len(chunks)} chunks."
            )

        print(f"Embeddings generated: {len(embeddings)} for {len(chunks)} chunks.")

        # 3️⃣ Attach embeddings + ownership metadata to each chunk
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
            chunk["user_id"] = metadata["user_id"]
            chunk["space_type"] = metadata["space_type"]
            chunk["space_id"] = metadata.get("space_id")  # may be None for personal

        # 4️⃣ Store in Qdrant FIRST (vector source of truth)
        upsert_chunks(COLLECTION_NAME, chunks)

        # 5️⃣ Store chunk text in Mongo AFTER successful vector insert
        chunk_docs = [
            {
                "chunk_id": chunk["chunk_id"],
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
            }
            for chunk in chunks
        ]
        db.chunks.insert_many(chunk_docs)

        # 6️⃣ Mark completed
        db.documents.update_one(
            {"document_id": document_id},
            {"$set": {"status": "completed"}},
        )

        print(f"Document '{document_id}' ingested successfully.")

    except Exception as exc:
        # Always attempt to mark as failed in Mongo, but guard against
        # the case where db itself failed to initialise.
        if db is not None:
            try:
                db.documents.update_one(
                    {"document_id": document_id},
                    {"$set": {"status": "failed", "error": str(exc)}},
                )
            except Exception as mongo_exc:
                print(f"[ingest_document_task] Failed to update error status in Mongo: {mongo_exc}")

        raise self.retry(exc=exc)