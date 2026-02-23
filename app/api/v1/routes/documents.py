from fastapi import APIRouter, Form, HTTPException
from app.tasks.ingestion_tasks import ingest_document_task

router = APIRouter()

@router.post("/process")
async def process_document(
    document_id: str = Form(...),
    file_url: str = Form(...),
    scope_type: str = Form(...),
    owner_id: str = Form(...),
    team_id: str | None = Form(None),
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

    ingest_document_task.delay(
        document_id,
        {
            "file_url": file_url,
            "scope_type": scope_type,
            "owner_id": owner_id,
            "team_id": team_id,
        }
    )

    return {"message": "Processing started"}
