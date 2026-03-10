fastapi_app: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 --log-level info
celery_worker: celery -A app.core.celery_app worker --loglevel=info --concurrency=2