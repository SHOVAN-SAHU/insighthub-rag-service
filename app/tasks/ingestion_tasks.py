# from app.core.celery_app import celery_app
# from app.core.config import settings
# from app.services.ingestion_service import ingest_document
# from app.services.embedding_service import generate_embeddings
# from app.core.mongo_sync import get_database
# from app.core.vector_db import upsert_chunks
# from datetime import datetime, timezone

# import time

# COLLECTION_NAME = settings.collection_name


# # ── Celery worker startup signal ─────────────────────────────────────────────
# # Create the Qdrant collection ONCE when the worker process starts,
# # not on every task invocation. This avoids a redundant API call per task.

# from celery.signals import worker_ready
# from app.core.vector_db import create_collection

# @worker_ready.connect
# def on_worker_ready(sender, **kwargs):
#     print(f"[worker_ready] Ensuring Qdrant collection '{COLLECTION_NAME}' exists...")
#     try:
#         create_collection(COLLECTION_NAME)
#     except Exception as e:
#         # Log but don't crash the worker — tasks will fail with clear errors
#         # if the collection truly doesn't exist when needed.
#         print(f"[worker_ready] WARNING: Could not create collection: {e}")


# # ── Task ─────────────────────────────────────────────────────────────────────

# @celery_app.task(bind=True, max_retries=3, default_retry_delay=15)
# def ingest_document_task(self, document_id: str, metadata: dict):
#     start_time = time.time()
#     db = None

#     try:
#         db = get_database()
#         t0 = time.time()

#         # Mark as processing
#         db.documents.update_one(
#             {"document_id": document_id},
#             {
#                 "$set": {
#                     "status": "processing",
#                     "user_id": metadata["user_id"],
#                     "space_type": metadata["space_type"],
#                     "space_id": metadata.get("space_id"),
#                     "updated_at": datetime.now(timezone.utc)
#                 },
#                 "$setOnInsert": {
#                     "created_at": datetime.now(timezone.utc)
#                 }
#             },
#             upsert=True,
#         )

#         print(f"[TIMING] Mongo status update: {time.time() - t0:.2f}s")

#         # 1️⃣ Extract + Chunk
#         t1 = time.time()
#         chunks = ingest_document(document_id, metadata)

#         print(f"[TIMING] Extraction + Chunking: {time.time() - t1:.2f}s")
#         print(f"[INFO] Chunks created: {len(chunks)}")

#         if not chunks:
#             db.documents.update_one(
#                 {"document_id": document_id},
#                 {"$set": {"status": "failed", "error": "No text extracted"}},
#             )
#             return

#         # 2️⃣ Generate embeddings
#         t2 = time.time()
#         texts = [chunk["text"] for chunk in chunks]
#         embeddings = generate_embeddings(texts)

#         print(f"[TIMING] Embedding generation: {time.time() - t2:.2f}s")

#         if len(embeddings) != len(chunks):
#             raise ValueError(
#                 f"Embedding count mismatch: got {len(embeddings)} embeddings "
#                 f"for {len(chunks)} chunks."
#             )

#         print(f"Embeddings generated: {len(embeddings)} for {len(chunks)} chunks.")

#         # 3️⃣ Attach embeddings + ownership metadata to each chunk
#         t3 = time.time()
#         for chunk, embedding in zip(chunks, embeddings):
#             chunk["embedding"] = embedding
#             chunk["user_id"] = metadata["user_id"]
#             chunk["space_type"] = metadata["space_type"]
#             chunk["space_id"] = metadata.get("space_id")  # may be None for personal

#         print(f"[TIMING] Metadata attach: {time.time() - t3:.2f}s")

#         # 4️⃣ Store in Qdrant FIRST (vector source of truth)
#         t4 = time.time()
#         upsert_chunks(COLLECTION_NAME, chunks)

#         print(f"[TIMING] Qdrant insert: {time.time() - t4:.2f}s")

#         # 5️⃣ Store chunk text in Mongo AFTER successful vector insert
#         t5 = time.time()
#         chunk_docs = [
#             {
#                 "chunk_id": chunk["chunk_id"],
#                 "document_id": document_id,
#                 "chunk_index": chunk["chunk_index"],
#                 "text": chunk["text"],
#                 "user_id": metadata["user_id"],
#                 "space_type": metadata["space_type"],
#                 "space_id": metadata.get("space_id"),
#             }
#             for chunk in chunks
#         ]
#         db.chunks.insert_many(chunk_docs)

#         print(f"[TIMING] Mongo chunk insert: {time.time() - t5:.2f}s")

#         # 6️⃣ Mark completed
#         t6 = time.time()
#         chunk_count = len(chunks)
#         db.documents.update_one(
#             {"document_id": document_id},
#             {
#                 "$set": {
#                     "status": "completed",
#                     "chunk_count": chunk_count,
#                     "updated_at": datetime.now(timezone.utc)
#                 }
#             },
#         )

#         print(f"[TIMING] Final status update: {time.time() - t6:.2f}s")

#         print(f"[TOTAL INGESTION TIME]: {time.time() - start_time:.2f}s")

#         print(f"Document '{document_id}' ingested successfully.")

#     except Exception as exc:
#         # Always attempt to mark as failed in Mongo, but guard against
#         # the case where db itself failed to initialise.
#         if db is not None:
#             try:
#                 db.documents.update_one(
#                     {"document_id": document_id},
#                     {  
#                         "$set": {
#                             "status": "failed", 
#                             "error": str(exc),
#                             "updated_at": datetime.now(timezone.utc)
#                         }
#                     },
#                 )
#             except Exception as mongo_exc:
#                 print(f"[ingest_document_task] Failed to update error status in Mongo: {mongo_exc}")

#         raise self.retry(exc=exc)