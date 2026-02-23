from typing import List, Dict
import uuid

def chunk_text(
    text: str,
    chunk_size: int = 200,  # words per chunk
    overlap: int = 50       # words overlap
) -> List[Dict]:
    """
    Splits text into chunks with overlap.
    Returns a list of dicts:
    [{"chunk_id": str, "chunk_index": int, "text": str}]
    """
    words = text.split()
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text_str = " ".join(chunk_words)

        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "chunk_index": chunk_index,
            "text": chunk_text_str
        })

        chunk_index += 1
        start += chunk_size - overlap  # advance start with overlap

    return chunks
