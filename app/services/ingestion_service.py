from typing import List, Dict
import re

from app.services.document_ingestion import extract_text
from app.services.chunking import chunk_text
from app.services.download_service import download_from_r2, cleanup_temp_file

def ingest_document(document_id: str, context: dict) -> List[Dict]:
    """
    Stateless ingestion:
    - download file
    - extract text
    - normalize
    - chunk
    - attach document_id
    - return enriched chunks
    """

    file_url = context["file_url"]

    temp_path = download_from_r2(file_url)

    try:
        extracted_text = extract_text(temp_path)

        if not extracted_text.strip():
            return []

        normalized = normalize_text(extracted_text)

        raw_chunks = chunk_text(normalized, chunk_size=200, overlap=50)

        # Attach document_id
        enriched_chunks = []

        for chunk in raw_chunks:
            enriched_chunks.append({
                "chunk_id": chunk["chunk_id"],
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
            })

        return enriched_chunks

    finally:
        cleanup_temp_file(temp_path)


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()
