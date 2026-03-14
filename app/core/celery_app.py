# from .config import settings
# from celery import Celery
# from celery.signals import worker_process_init, worker_shutdown

# from app.core.mongo_sync import connect_to_mongo, close_mongo_connection


# celery_app = Celery(
#     "rag_service",
#     broker=settings.celery_broker_url,
#     backend=settings.celery_result_backend,
#     include=[
#         "app.tasks.ingestion_tasks",
#         "app.tasks.document_tasks",
#     ],
# )

# celery_app.conf.task_routes = {
#     "app.tasks.ingestion_tasks.ingest_document_task": {"queue": "celery"},
#     "app.tasks.document_tasks.delete_document_task": {"queue": "celery"},
# }

# celery_app.conf.update(
#     task_acks_late=True,
#     task_reject_on_worker_lost=True,
#     task_time_limit=300,
#     worker_prefetch_multiplier=1,
#     task_serializer="json",
#     result_serializer="json",
#     accept_content=["json"],
# )


# # 🔥 Connect Mongo when worker process starts
# @worker_process_init.connect
# def init_worker(**kwargs):
#     connect_to_mongo()
#     print("MongoDB connected (Celery worker)")


# # 🔥 Close Mongo when worker shuts down
# @worker_shutdown.connect
# def shutdown_worker(**kwargs):
#     close_mongo_connection()
#     print("MongoDB disconnected (Celery worker)")
