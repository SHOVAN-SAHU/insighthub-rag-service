from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, PayloadSchemaType
from app.core.config import settings

print("QDRANT URL RAW:", repr(settings.qdrant_url))
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

        # Below code in here is new.
        # Create indexes
        indexed_fields = ["user_id", "space_type"]

        for field in indexed_fields:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=PayloadSchemaType.KEYWORD,
            )

        # ---- Fetch collection info ----
        collection_info = client.get_collection(collection_name)

        # Extract indexed fields
        payload_indexes = collection_info.payload_schema

        print(f"Collection '{collection_name}' created.")
        print("Payload indexes:")

        if payload_indexes:
            for field_name in payload_indexes:
                print(f" - {field_name}")
        else:
            print("No payload indexes found.")


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