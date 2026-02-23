from pathlib import Path
from typing import List, Dict
import re

from app.schemas.common import Scope
from app.core.paths import resolve_scope_path
from app.services.document_ingestion import extract_text
from app.services.chunking import chunk_text


def ingest_document(document_id: str, metadata: dict) -> None:
    """
    Pure ingestion logic.
    No in-memory repo.
    No API logic.
    """

    scope = Scope(
        scope_type=metadata["scope_type"],
        owner_id=metadata["owner_id"],
        team_id=metadata.get("team_id"),
    )

    base_path = resolve_scope_path(scope)

    raw_path = base_path / "raw" / metadata["raw_filename"]

    extracted_text = extract_text(raw_path)

    extracted_dir = base_path / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    extracted_path = extracted_dir / f"{document_id}.txt"
    extracted_path.write_text(extracted_text, encoding="utf-8")

    chunks = process_document(extracted_path)

    # Later: push to vector DB
    # Later: persist chunk metadata

    return chunks

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

def load_extracted_text(extracted_path: Path) -> str:
    """
    Load extracted text from a file.
    """
    if not extracted_path.exists():
        raise FileNotFoundError(f"Extracted file not found: {extracted_path}")

    return extracted_path.read_text(encoding="utf-8", errors="ignore")

def process_document(extracted_path: Path, chunk_size: int = 200, overlap: int = 50) -> List[Dict]:
    """
    Load extracted text, normalize it, split into chunks.
    Returns a list of chunks with metadata:
    [
        {
            "chunk_id": str,
            "chunk_index": int,
            "text": str
        }
    ]
    """
    # 1️⃣ Load text
    text = load_extracted_text(extracted_path)

    if not text.strip():
        # No text to process
        return []

    # 2️⃣ Normalize
    text = normalize_text(text)

    # 3️⃣ Chunk
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    return chunks