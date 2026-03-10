from app.core.celery_app import celery_app
from app.core.mongo_sync import get_database
from app.core.vector_db import delete_document_vectors
from app.core.config import settings

COLLECTION_NAME = settings.collection_name


@celery_app.task(bind=True, max_retries=3, default_retry_delay=15)
def delete_document_task(self, document_id: str):

    db = None

    try:
        db = get_database()
        doc = db.documents.find_one({"document_id": document_id})

        if not doc or doc.get("status") == "deleted":
            return

        # 1️⃣ Delete vectors from Qdrant
        delete_document_vectors(COLLECTION_NAME, document_id)

        # 2️⃣ Delete chunks from Mongo
        db.chunks.delete_many({"document_id": document_id})

        # 3️⃣ Mark document deleted
        db.documents.update_one(
            {"document_id": document_id},
            {"$set": {"status": "deleted"}}
        )

        print(f"Document '{document_id}' deleted successfully.")

    except Exception as exc:

        if db is not None:
            db.documents.update_one(
                {"document_id": document_id},
                {"$set": {"status": "delete_failed", "error": str(exc)}}
            )

        raise self.retry(exc=exc)