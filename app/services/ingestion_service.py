from typing import List, Dict
import re

from app.services.document_ingestion import extract_text
from app.services.chunking import chunk_text
from app.storage.object_storage import download_from_r2, cleanup_temp_file

def ingest_document(document_id: str, context: dict) -> List[Dict]:
    """
    Stateless ingestion:
    - download file from object storage
    - extract text
    - normalize
    - chunk
    - return chunks
    """

    file_url = context["file_url"]

    temp_path = download_from_r2(file_url)

    try:
        # 1️⃣ Extract text directly from temp file
        extracted_text = extract_text(temp_path)

        if not extracted_text.strip():
            return []

        # 2️⃣ Normalize
        normalized = normalize_text(extracted_text)

        # 3️⃣ Chunk
        chunks = chunk_text(normalized, chunk_size=200, overlap=50)

        return chunks

    finally:
        cleanup_temp_file(temp_path)

def normalize_text(text: str) -> str:
    """
    Normalize text before chunking:
    - collapse multiple spaces
    - strip leading/trailing whitespace
    - replace newlines with spaces where appropriate
    """
    text = re.sub(r"\s+", " ", text)  # collapse all whitespace to single space
    text = text.strip()
    return text
