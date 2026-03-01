from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings

client = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key
)

VECTOR_SIZE = 384  # sentence-transformers/all-MiniLM-L6-v2


def create_collection(collection_name: str):
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )


def upsert_chunks(collection_name: str, chunks: list):
    points = []

    for chunk in chunks:
        points.append(
            PointStruct(
                id=chunk["chunk_id"],  # use real chunk_id
                vector=chunk["embedding"],
                payload={
                  "document_id": chunk["document_id"],
                  "chunk_index": chunk["chunk_index"],
                  "user_id": chunk["user_id"],
                  "space_type": chunk["space_type"],
                  "space_id": chunk.get("space_id"),
              }
            )
        )

    if points:
        client.upsert(
            collection_name=collection_name,
            points=points
        )


def get_vector_client():
    return client