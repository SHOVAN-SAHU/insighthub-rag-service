from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from app.services.retrieval_service import (
    retrieve_context,
    CollectionNotFoundException,
    VectorSearchException,
)
from app.services.llm_service import generate_answer_async
from app.core.config import settings

from app.schemas.document import ProcessDocumentRequest, DeleteDocumentRequest
from app.schemas.question import AskQuestionRequest
from app.core.mongo_async import get_database
from app.services.document_service import process_document_service, delete_document_service
from motor.motor_asyncio import AsyncIOMotorDatabase

# Imported background workers
# from app.tasks.ingestion_tasks import ingest_document_task
# from app.tasks.document_tasks import delete_document_task

router = APIRouter()
api_key_header = APIKeyHeader(name="X-API-KEY")


@router.post("/process")
async def process_document(
    payload: ProcessDocumentRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    x_api_key: str = Security(api_key_header),
):

    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    metadata = {
        "file_url": payload.file_url,
        "user_id": payload.user_id,
        "space_type": payload.space_type.value,
        "space_id": payload.space_id
    }

    await process_document_service(db, payload.document_id, metadata)

    return {"message": "Processing completed"}


@router.post("/ask")
async def ask_question(
    payload: AskQuestionRequest,
    x_api_key: str = Security(api_key_header)
):
    # 🔐 API Key Check
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    question = payload.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    if len(question) > 2000:
        raise HTTPException(400, "Question too long")
    
    if payload.space_type.value == "team" and not payload.space_id:
        raise HTTPException(
            status_code=400,
            detail="space_id is required for team space"
        )

    # 1️⃣ Retrieve context (async)
    try:
        context = await retrieve_context(
            question=question,
            user_id=payload.user_id,
            space_type=payload.space_type.value,
            space_id=payload.space_id,
        )

    except CollectionNotFoundException as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "collection_not_found",
                "message": str(e),
            }
        )

    except VectorSearchException as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "vector_search_failed",
                "message": str(e),
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"An unexpected error occurred: {str(e)}",
            }
        )

    # Handle no context found
    if not context:
        return {
            "question": question,
            "answer": "No relevant information found in your documents.",
            "context_used": False,
        }

    # 2️⃣ Generate answer
    try:
        answer = await generate_answer_async(
            question=question,
            context=context,
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "llm_error",
                "message": str(e),
            }
        )

    return {
        "question": question,
        "answer": answer,
        "context_used": True,
    }


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    x_api_key: str = Security(api_key_header),
):

    # API key check
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    document = await db.documents.find_one(
        {"document_id": document_id},
        {
            "_id": 0, 
            "document_id": 1,
            "created_at": 1,
            "status": 1,
            "updated_at": 1,
            "chunk_count": 1
        }
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return document


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    payload: DeleteDocumentRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    x_api_key: str = Security(api_key_header),
):

    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    query = {
        "document_id": document_id,
        "user_id": payload.user_id,
        "space_type": payload.space_type.value,
        "status": {"$nin": ["deleting", "deleted"]}
    }

    if payload.space_id is not None:
        query["space_id"] = payload.space_id
    else:
        query["space_id"] = None

    result = await db.documents.update_one(
        query,
        {"$set": {"status": "deleting"}}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Document not found or already deleting"
        )

    await delete_document_service(db, document_id)

    return {"message": "Document deleted successfully"}


# API's with background workers

# @router.post("/process")
# async def process_document(
#     payload: ProcessDocumentRequest,
#     x_api_key: str = Security(api_key_header)
# ):

#     if x_api_key != settings.api_key:
#         raise HTTPException(status_code=401, detail="Unauthorized")

#     ingest_document_task.delay(
#         payload.document_id,
#         {
#             "file_url": payload.file_url,
#             "user_id": payload.user_id,
#             "space_type": payload.space_type.value,
#             "space_id": payload.space_id
#         }
#     )

#     return {"message": "Processing started"}


# @router.delete("/{document_id}")
# async def delete_document(
#     document_id: str,
#     payload: DeleteDocumentRequest,
#     db: AsyncIOMotorDatabase = Depends(get_database),
#     x_api_key: str = Security(api_key_header),
# ):

#     if x_api_key != settings.api_key:
#         raise HTTPException(status_code=401, detail="Unauthorized")

#     query = {
#         "document_id": document_id,
#         "user_id": payload.user_id,
#         "space_type": payload.space_type.value,
#         "status": {"$nin": ["deleting", "deleted"]}
#     }

#     if payload.space_id is not None:
#         query["space_id"] = payload.space_id
#     else:
#         query["space_id"] = None

#     result = await db.documents.update_one(
#         query,
#         {"$set": {"status": "deleting"}}
#     )

#     if result.modified_count == 0:
#         raise HTTPException(
#             status_code=404,
#             detail="Document not found or already deleting"
#         )

#     task = delete_document_task.delay(document_id)

#     return {
#         "message": "Document deletion started",
#         "task_id": task.id
#     }
