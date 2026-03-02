from fastapi import APIRouter, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from app.tasks.ingestion_tasks import ingest_document_task
from app.services.retrieval_service import retrieve_context
from app.services.llm_service import generate_answer_async
from app.core.config import settings

from app.schemas.document import ProcessDocumentRequest
from app.schemas.question import AskQuestionRequest

router = APIRouter()

api_key_header = APIKeyHeader(name="X-API-KEY")


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
            "space_type": payload.space_type.value,
            "space_id": payload.space_id
        }
    )

    return {"message": "Processing started"}


@router.post("/ask")
async def ask_question(
    payload: AskQuestionRequest,
    x_api_key: str = Security(api_key_header)
):
    # 🔐 API Key Check
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    print("Before retrieve_context")

    # 1️⃣ Retrieve context (async)
    context = await retrieve_context(
        question=payload.question,
        user_id=payload.user_id,
        space_type=payload.space_type.value,
        space_id=payload.space_id,
    )

    # Optional: handle no context found
    if not context:
        return {
            "question": payload.question,
            "answer": "No relevant information found in your documents.",
            "context_used": False
        }
    
    print("Before generate_answer_async")

    # 2️⃣ Generate answer
    answer = await generate_answer_async(
        question=payload.question,
        context=context,
    )

    return {
        "question": payload.question,
        "answer": answer,
        "context_used": True
    }
