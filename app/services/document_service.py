from datetime import datetime, timezone
from app.services.ingestion_service import ingest_document
from app.services.embedding_service import generate_embeddings
from app.core.vector_db import upsert_chunks, delete_document_vectors
from app.core.config import settings

COLLECTION_NAME = settings.collection_name


async def process_document_service(db, document_id: str, metadata: dict):

    try:

        await db.documents.update_one(
            {"document_id": document_id},
            {
                "$set": {
                    "status": "processing",
                    "user_id": metadata["user_id"],
                    "space_type": metadata["space_type"],
                    "space_id": metadata.get("space_id"),
                    "updated_at": datetime.now(timezone.utc)
                },
                "$setOnInsert": {
                    "created_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )

        chunks = ingest_document(document_id, metadata)

        if not chunks:
            raise Exception("No chunks extracted")

        texts = [chunk["text"] for chunk in chunks]
        embeddings = generate_embeddings(texts)

        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
            chunk["user_id"] = metadata["user_id"]
            chunk["space_type"] = metadata["space_type"]
            chunk["space_id"] = metadata.get("space_id")

        upsert_chunks(COLLECTION_NAME, chunks)

        chunk_docs = [
            {
                "chunk_id": c["chunk_id"],
                "document_id": document_id,
                "chunk_index": c["chunk_index"],
                "text": c["text"],
                "user_id": metadata["user_id"],
                "space_type": metadata["space_type"],
                "space_id": metadata.get("space_id")
            }
            for c in chunks
        ]

        await db.chunks.insert_many(chunk_docs)

        await db.documents.update_one(
            {"document_id": document_id},
            {
                "$set": {
                    "status": "completed",
                    "chunk_count": len(chunks),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

    except Exception as e:

        await db.documents.update_one(
            {"document_id": document_id},
            {
                "$set": {
                    "status": "process_failed",
                    "error": str(e),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        raise


async def delete_document_service(db, document_id: str):

    try:

        doc = await db.documents.find_one({"document_id": document_id})

        if not doc:
            return

        delete_document_vectors(COLLECTION_NAME, document_id)

        await db.chunks.delete_many({"document_id": document_id})

        await db.documents.update_one(
            {"document_id": document_id},
            {"$set": {"status": "deleted"}}
        )

    except Exception as e:
        print(f"Deletion failed for {document_id}: {e}")
        await db.documents.update_one(
                  {"document_id": document_id},
                  {"$set": 
                      {"status": 
                          "delete_failed", 
                          "error": str(e),
                          "updated_at": datetime.now(timezone.utc)
                      }
                  }
              )
        raise
