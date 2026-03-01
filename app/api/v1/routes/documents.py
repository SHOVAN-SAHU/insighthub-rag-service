from fastapi import APIRouter, Header, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from app.tasks.ingestion_tasks import ingest_document_task
from app.core.config import settings

router = APIRouter()

api_key_header = APIKeyHeader(name="X-API-KEY")

class ProcessDocumentRequest(BaseModel):
    document_id: str
    file_url: str
    user_id: str
    space_type: str  # "personal" or "team"
    space_id: str | None = None # team_id if space_type == "team"

@router.post("/process")
async def process_document(
    payload: ProcessDocumentRequest,
    x_api_key: str = Security(api_key_header)
):

    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    ingest_document_task.delay(
        payload.document_id,
        {
            "file_url": payload.file_url,
            "user_id": payload.user_id,
            "space_type": payload.space_type,
            "space_id": payload.space_id
        }
    )

    return {"message": "Processing started"}
