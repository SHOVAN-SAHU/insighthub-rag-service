from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, PayloadSchemaType, Filter, FieldCondition, MatchValue
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings

VECTOR_SIZE = 384  # sentence-transformers/all-MiniLM-L6-v2

# ── Lazy singleton client ────────────────────────────────────────────────────
# QdrantClient does not open a socket until the first request, so this is safe
# at import time even if Qdrant is temporarily unreachable.

_client: QdrantClient | None = None


def get_vector_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
    return _client


# ── Collection ───────────────────────────────────────────────────────────────

def create_collection(collection_name: str) -> None:
    """
    Creates the Qdrant collection + payload indexes if they don't exist.
    Safe to call multiple times — exits early if collection already exists.
    Intended to be called ONCE at Celery worker startup via the ready signal,
    not on every task.
    """
    client = get_vector_client()

    if client.collection_exists(collection_name):
        print(f"Collection '{collection_name}' already exists, skipping creation.")
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )

    # Payload indexes for fast filtered search
    for field in ["user_id", "space_type", "space_id", "document_id"]:
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD,
        )

    collection_info = client.get_collection(collection_name)
    payload_indexes = collection_info.payload_schema

    print(f"Collection '{collection_name}' created.")
    print("Payload indexes:")
    if payload_indexes:
        for field_name in payload_indexes:
            print(f"  - {field_name}")
    else:
        print("  (none)")


# ── Upsert ───────────────────────────────────────────────────────────────────

def upsert_chunks(collection_name: str, chunks: list) -> None:
    if not chunks:
        print("upsert_chunks: no chunks provided, skipping.")
        return

    client = get_vector_client()

    if not client.collection_exists(collection_name):
        create_collection(collection_name)
    
    points = []

    for chunk in chunks:
        # Only store space_id if it has a real value —
        # storing None can cause filter mismatches on team vs personal spaces.
        payload = {
            "document_id": chunk["document_id"],
            "chunk_index": chunk["chunk_index"],
            "user_id": chunk["user_id"],
            "space_type": chunk["space_type"],
        }
        if chunk.get("space_id"):
            payload["space_id"] = chunk["space_id"]

        points.append(
            PointStruct(
                id=chunk["chunk_id"],
                vector=chunk["embedding"],
                payload=payload,
            )
        )

    try:
        client.upsert(
            collection_name=collection_name,
            points=points,
        )
        print(f"upsert_chunks: upserted {len(points)} points into '{collection_name}'.")

    except UnexpectedResponse as e:
        raise RuntimeError(
            f"Failed to upsert into '{collection_name}': "
            f"Qdrant {e.status_code} — {e.content}"
        ) from e

    except Exception as e:
        raise RuntimeError(
            f"Unexpected error during upsert into '{collection_name}': {str(e)}"
        ) from e

# ── Delete ───────────────────────────────────────────────────────────────────

def delete_document_vectors(collection_name: str, document_id: str):

    client = get_vector_client()
    client.delete(
        collection_name=collection_name,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id)
                )
            ]
        )
    )
