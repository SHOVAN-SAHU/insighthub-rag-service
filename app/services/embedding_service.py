import requests
from app.core.config import settings

HF_MODEL = settings.hf_embed_model
HF_TOKEN = settings.hf_api_token

# HF_API_URL = (
#     f"https://router.huggingface.co/"
#     f"hf-inference/models/{settings.hf_embed_model}"
# )

HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
print(f"Requesting URL: {HF_API_URL}")
print(f"Requesting Token: {HF_TOKEN}")

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

def _batch(iterable: list[str], size: int = 16):
    """Split list into smaller batches."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple text chunks.
    Returns list of embedding vectors.
    """

    all_embeddings = []

    for batch in _batch(texts, size=16):
        response = requests.post(
            HF_API_URL,
            headers=HEADERS,
            json={"inputs": batch},
            timeout=60,
        )

        if response.status_code != 200:
            raise Exception(f"HF API Error: {response.text}")

        embeddings = response.json()

        # Handle nested format if returned
        if isinstance(embeddings[0], list) and isinstance(embeddings[0][0], list):
            embeddings = [e[0] for e in embeddings]

        all_embeddings.extend(embeddings)

    return all_embeddings
