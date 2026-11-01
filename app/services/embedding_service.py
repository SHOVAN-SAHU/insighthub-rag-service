from typing import List
from fastembed import TextEmbedding
from app.core.config import settings

_model: TextEmbedding | None = None


def get_embedding_model() -> TextEmbedding:
    """
    Lazy initialization of FastEmbed model singleton.
    Runs locally on ONNX runtime (CPU) for free without external API costs or limits.
    Produces 384-dimensional embeddings using sentence-transformers/all-MiniLM-L6-v2.
    """
    global _model
    if _model is None:
        model_name = settings.embed_model or "sentence-transformers/all-MiniLM-L6-v2"
        _model = TextEmbedding(model_name=model_name)
    return _model


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple text chunks using local FastEmbed.
    Returns list of 384-dimensional embedding vectors.
    """
    if not texts:
        return []

    try:
        model = get_embedding_model()
        # FastEmbed handles batching internally and yields numpy arrays
        embeddings = list(model.embed(texts, batch_size=32))
        return [e.tolist() for e in embeddings]
    except Exception as e:
        raise RuntimeError(f"Embedding generation error: {str(e)}") from e
