import logging
from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.retrieval_service import (
    retrieve_context,
    CollectionNotFoundException,
    VectorSearchException,
)
from app.services.llm_service import generate_answer_async
from app.core.config import settings
from app.schemas.document import ProcessDocumentRequest, DeleteDocumentRequest, SpaceType
from app.schemas.question import AskQuestionRequest
from app.core.mongo_async import get_database
from app.services.document_service import process_document_service, delete_document_service
from app.services.node_api import update_document_status

logger = logging.getLogger(__name__)

router = APIRouter()
api_key_header = APIKeyHeader(name="X-API-KEY")


@router.post("/process")
async def process_document(
    payload: ProcessDocumentRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    x_api_key: str = Security(api_key_header),
):
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Unauthorized"}
        )

    if payload.space_type == SpaceType.team and not payload.space_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "space_id is required for team space"}
        )

    metadata = {
        "file_url": payload.file_url,
        "user_id": payload.user_id,
        "space_type": payload.space_type.value,
        "space_id": payload.space_id
    }

    try:
        await process_document_service(db, payload.document_id, metadata)

        # Notify Node.js API service if document processing succeeded
        try:
            await update_document_status(payload.document_id, "ready")
        except Exception as notify_err:
            logger.error(f"Failed to update document status to ready: {notify_err}")

        return {"message": "Processing completed"}

    except Exception as e:
        logger.error(f"Error processing document {payload.document_id}: {e}")
        # Notify Node.js API service of failure
        try:
            await update_document_status(
                payload.document_id,
                "failed",
                str(e)
            )
        except Exception as notify_err:
            logger.error(f"Failed to update document status to failed: {notify_err}")

        raise HTTPException(
            status_code=500,
            detail={"error": "processing_failed", "message": f"Processing failed: {str(e)}"}
        )


@router.post("/ask")
async def ask_question(
    payload: AskQuestionRequest,
    x_api_key: str = Security(api_key_header)
):
    # 🔐 API Key Check
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Unauthorized"}
        )

    question = payload.question.strip() if payload.question else ""

    if not question:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "Question cannot be empty"}
        )

    if len(question) > 2000:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "Question too long"}
        )

    if payload.space_type == SpaceType.team and not payload.space_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "space_id is required for team space"}
        )

    # Retrieve context (async)
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
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "bad_request",
                "message": str(e),
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving context for question: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"An unexpected error occurred during retrieval: {str(e)}",
            }
        )

    # Handle no context found
    if not context:
        return {
            "question": question,
            "answer": "No relevant information found in your documents.",
            "context_used": False,
        }

    # Generate answer
    try:
        answer = await generate_answer_async(
            question=question,
            context=context,
        )
    except RuntimeError as e:
        logger.error(f"LLM runtime error: {e}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "llm_error",
                "message": str(e),
            }
        )
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"An unexpected error occurred during answer generation: {str(e)}",
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
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Unauthorized"}
        )

    if not document_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "document_id is required"}
        )

    try:
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
    except Exception as e:
        logger.error(f"Database error fetching status for {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "database_error", "message": f"Failed to retrieve document status: {str(e)}"}
        )

    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Document not found"}
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
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Unauthorized"}
        )

    if not document_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "Document id is required"}
        )
    if not payload.user_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "Uploader id is required"}
        )
    if not payload.space_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "Space id is required"}
        )
    if not payload.space_type or not payload.space_type.value:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "Space type is required"}
        )

    query = {
        "document_id": str(document_id),
        "user_id": str(payload.user_id),
        "space_id": str(payload.space_id),
        "space_type": payload.space_type.value,
        "status": {"$nin": ["deleting", "deleted"]}
    }

    try:
        result = await db.documents.update_one(
            query,
            {"$set": {"status": "deleting"}}
        )
    except Exception as e:
        logger.error(f"Database error marking document {document_id} as deleting: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "database_error", "message": f"Failed to mark document as deleting: {str(e)}"}
        )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Document not found or already deleting"}
        )

    try:
        await delete_document_service(db, document_id)
    except Exception as e:
        logger.error(f"Error during document deletion for {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "deletion_failed", "message": f"Failed to delete document: {str(e)}"}
        )

    return {"message": "Document deleted successfully"}

