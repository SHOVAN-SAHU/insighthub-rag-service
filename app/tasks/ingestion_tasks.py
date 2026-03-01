from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.ingestion_service import ingest_document
from app.services.embedding_service import generate_embeddings
from app.core.mongo_sync import get_database
from app.core.vector_db import create_collection, upsert_chunks

COLLECTION_NAME = settings.collection_name


@celery_app.task(bind=True, max_retries=3, default_retry_delay=15)
def ingest_document_task(self, document_id: str, metadata: dict):
    try:
        db = get_database()

        # Mark as processing
        db.documents.update_one(
            {"document_id": document_id},
            {"$set": {"status": "processing"}},
            upsert=True
        )

        # 1️⃣ Extract + Chunk
        chunks = ingest_document(document_id, metadata)

        if not chunks:
            db.documents.update_one(
                {"document_id": document_id},
                {"$set": {"status": "failed", "error": "No text extracted"}}
            )
            return

        # 2️⃣ Generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = generate_embeddings(texts)

        if len(embeddings) != len(chunks):
            raise Exception("Embedding count mismatch")
        
        print(f"embedding length: {len(embeddings)}")
        print(f"embedding chunks: {len(chunks)}")

        # 3️⃣ Attach embeddings + ownership metadata
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
            chunk["user_id"] = metadata["user_id"]
            chunk["space_type"] = metadata["space_type"]
            chunk["space_id"] = metadata.get("space_id")

        # 4️⃣ Ensure collection exists (better to run once at startup)
        create_collection(COLLECTION_NAME)

        # 5️⃣ Store in Qdrant FIRST (vector source of truth)
        upsert_chunks(COLLECTION_NAME, chunks)

        # 6️⃣ Store chunks in Mongo AFTER successful vector insert
        chunk_docs = []
        for chunk in chunks:
            chunk_docs.append({
                "chunk_id": chunk["chunk_id"],
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
            })

        db.chunks.insert_many(chunk_docs)

        # 7️⃣ Mark completed
        db.documents.update_one(
            {"document_id": document_id},
            {"$set": {"status": "completed"}}
        )

    except Exception as exc:
        db = get_database()
        db.documents.update_one(
            {"document_id": document_id},
            {"$set": {"status": "failed", "error": str(exc)}}
        )
        raise self.retry(exc=exc)
