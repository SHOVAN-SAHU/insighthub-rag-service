from typing import List, Dict, Tuple
from fastapi.concurrency import run_in_threadpool
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings
from app.core.mongo_async import get_database
from app.services.embedding_service import generate_embeddings
from app.core.vector_db import get_vector_client

qdrant_client = get_vector_client()

MODEL_CONTEXT_LIMIT = 8192
ANSWER_BUFFER = 1200
SYSTEM_AND_QUESTION_BUFFER = 1000
MAX_CONTEXT_TOKENS = MODEL_CONTEXT_LIMIT - ANSWER_BUFFER - SYSTEM_AND_QUESTION_BUFFER

SIMILARITY_THRESHOLD = 0.35
RETRIEVAL_LIMIT = 20


def estimate_tokens(text: str) -> int:
    return len(text) // 4


async def generate_query_embedding(question: str) -> List[float]:
    return await run_in_threadpool(
        lambda: generate_embeddings([question])[0]
    )


async def search_similar_chunks(
    query_embedding: List[float],
    user_id: str,
    space_type: str,
    space_id: str | None,
) -> List:
    filter_payload = {
        "must": [
            {"key": "user_id", "match": {"value": user_id}},
            {"key": "space_type", "match": {"value": space_type}},
        ]
    }
    
    if space_type == "team":
        if not space_id:
            raise ValueError("space_id required for team space")

        filter_payload["must"].append(
            {"key": "space_id", "match": {"value": space_id}}
        )

    print(f"Before search for the points, filter payload: {filter_payload}")

    try:
        result = await run_in_threadpool(
            lambda: qdrant_client.query_points(
                collection_name=settings.collection_name,
                query=query_embedding,
                limit=RETRIEVAL_LIMIT,
                query_filter=filter_payload,
            )
        )
        return result.points

    except UnexpectedResponse as e:
        if e.status_code == 404:
            raise CollectionNotFoundException(
                f"Vector collection '{settings.collection_name}' does not exist. "
                "Please upload documents before querying."
            )
        raise VectorSearchException(f"Qdrant error ({e.status_code}): {e.content}") from e

    except Exception as e:
        raise VectorSearchException(f"Unexpected error during vector search: {str(e)}") from e


async def fetch_chunks_batch(
    keys: List[Tuple[str, int]],
    user_id: str,
    space_type: str,
    space_id: str | None,
) -> Dict[Tuple[str, int], str]:

    if not keys:
        return {}

    db = get_database()
    chunks_collection = db["chunks"]

    query = {
        "user_id": user_id,
        "space_type": space_type,
        "$or": [
            {"document_id": doc_id, "chunk_index": chunk_idx}
            for doc_id, chunk_idx in keys
        ]
    }

    if space_type == "team":
        query["space_id"] = space_id
    else:
        query["space_id"] = None

    print(f"Chunk fetching query: {query}")

    cursor = chunks_collection.find(query)

    chunk_map = {}
    async for doc in cursor:
        key = (doc["document_id"], doc["chunk_index"])
        chunk_map[key] = doc.get("text", "")

    return chunk_map


async def build_context_from_results(
    results: List,
    user_id: str,
    space_type: str,
    space_id: str | None,
) -> str:
    filtered = [
        r for r in results if r.score >= SIMILARITY_THRESHOLD
    ]

    if not filtered:
        return ""

    keys = [
        (r.payload["document_id"], r.payload["chunk_index"])
        for r in filtered
    ]

    print(f"before fetch chunks: {keys}")

    chunk_map = await fetch_chunks_batch(
        keys,
        user_id=user_id,
        space_type=space_type,
        space_id=space_id,
    )

    selected_chunks = []
    current_tokens = 0

    for r in filtered:
        doc_id = r.payload["document_id"]
        chunk_idx = r.payload["chunk_index"]
        score = r.score

        text = chunk_map.get((doc_id, chunk_idx))
        if not text:
            continue

        chunk_tokens = estimate_tokens(text)

        if current_tokens + chunk_tokens > MAX_CONTEXT_TOKENS:
            break

        structured_chunk = (
            f"[Document: {doc_id} | Chunk: {chunk_idx} | Score: {round(score, 3)}]\n"
            f"{text}\n"
        )

        selected_chunks.append(structured_chunk)
        current_tokens += chunk_tokens

    return "\n".join(selected_chunks)


async def retrieve_context(
    question: str,
    user_id: str,
    space_type: str,
    space_id: str | None = None,
) -> str:

    query_embedding = await generate_query_embedding(question)

    print(f"Question in embedding length: {len(query_embedding)}")

    results = await search_similar_chunks(
        query_embedding=query_embedding,
        user_id=user_id,
        space_type=space_type,
        space_id=space_id,
    )

    print(f"Before build_context_from_results, points found: {len(results)}")
    for r in results:
        print(f"Score: {r.score}, chunk: {r.payload}")

    return await build_context_from_results(
        results,
        user_id=user_id,
        space_type=space_type,
        space_id=space_id,
    )


# ── Custom exceptions ────────────────────────────────────────────────────────

class CollectionNotFoundException(Exception):
    """Raised when the Qdrant collection does not exist."""
    pass


class VectorSearchException(Exception):
    """Raised on any other Qdrant / vector search failure."""
    pass
