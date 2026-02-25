from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.tasks.ingestion_tasks import ingest_document_task
from typing import Literal, Optional

router = APIRouter()

class ProcessDocumentRequest(BaseModel):
    document_id: str
    file_url: str
    scope_type: Literal["personal", "team"]
    owner_id: str
    team_id: Optional[str] = None


@router.post("/process")
async def process_document(payload: ProcessDocumentRequest):

    # ---- invariant checks (NOT auth) ----
    if payload.scope_type == "personal" and payload.team_id is not None:
        raise HTTPException(
            status_code=400,
            detail="team_id not allowed for personal scope"
        )

    if payload.scope_type == "team" and payload.team_id is None:
        raise HTTPException(
            status_code=400,
            detail="team_id is required for team scope"
        )

    ingest_document_task.delay(
        payload.document_id,
        payload.model_dump()
    )

    return {"message": "Processing started"}