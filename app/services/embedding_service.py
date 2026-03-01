from typing import List
from huggingface_hub import InferenceClient
from app.core.config import settings


HF_MODEL = settings.hf_embed_model
HF_TOKEN = settings.hf_api_token

client = InferenceClient(
    model=HF_MODEL,
    token=HF_TOKEN,
)

def _batch(iterable: List[str], size: int = 16):
    """Split list into smaller batches."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple text chunks.
    Returns list of embedding vectors.
    """

    all_embeddings = []

    for batch in _batch(texts, size=16):
        try:
            embeddings = client.feature_extraction(batch)
        except Exception as e:
            raise Exception(f"HF API Error: {str(e)}")

        # Normalize nested format (HF sometimes returns [[[]]])
        if isinstance(embeddings[0], list) and isinstance(embeddings[0][0], list):
            embeddings = [e[0] for e in embeddings]

        all_embeddings.extend(embeddings)

    return all_embeddings
