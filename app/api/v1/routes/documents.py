from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.common import Scope
from app.schemas.document import DocumentMeta
from app.core.paths import resolve_scope_path
from app.services.ingestion_service import ingest_document
from app.storage import documents_repo

router = APIRouter()

@router.post("/upload")
async def upload_document(
    scope_type: str = Form(...),
    owner_id: str = Form(...),
    team_id: str | None = Form(None),
    file: UploadFile = File(...)
):
    # ---- invariant checks (NOT auth) ----
    if scope_type not in ("personal", "team"):
        raise HTTPException(status_code=400, detail="Invalid scope_type")

    if scope_type == "personal" and team_id is not None:
        raise HTTPException(
            status_code=400,
            detail="team_id not allowed for personal scope"
        )

    if scope_type == "team" and team_id is None:
        raise HTTPException(
            status_code=400,
            detail="team_id is required for team scope"
        )
    
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".txt", ".pdf", ".csv", ".docx", ".json"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}"
        )

    scope = Scope(
        scope_type=scope_type,
        owner_id=owner_id,
        team_id=team_id
    )

    base_path = resolve_scope_path(scope)
    raw_path = base_path / "raw"
    raw_path.mkdir(parents=True, exist_ok=True)

    document_id = str(uuid4())

    # ---- filename safety ----
    safe_filename = Path(file.filename).name[:255]
    file_path = raw_path / f"{document_id}_{safe_filename}"
    print("Saving file to:", file_path.resolve())

    # ---- stream file to disk ----
    size_bytes = 0
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            size_bytes += len(chunk)
            f.write(chunk)

    print("File saved, size:", size_bytes)

    metadata = DocumentMeta(
        document_id=document_id,
        filename=safe_filename,
        raw_filename=f"{document_id}_{safe_filename}",
        content_type=file.content_type,
        size_bytes=size_bytes,
        uploaded_at=datetime.now(timezone.utc),
        scope_type=scope.scope_type,
        owner_id=scope.owner_id,
        team_id=scope.team_id,
    )
    documents_repo.add(document_id, metadata.model_dump())
    print(f"documents_repo: {documents_repo}")

    ingest_document(document_id)

    return {
        "message": "Document stored",
        "metadata": metadata.model_dump()
    }
