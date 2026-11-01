import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from app.api.v1.router import api_router
from app.core.mongo_async import connect_to_mongo, close_mongo_connection

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    print("MongoDB connected")

    yield

    await close_mongo_connection()
    print("MongoDB disconnected")


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Service",
        version="0.1.0",
        lifespan=lifespan
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "http_error", "message": str(exc.detail)}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        messages = [
            f"{'.'.join(str(loc) for loc in err.get('loc', []))}: {err.get('msg', '')}"
            for err in errors
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "; ".join(messages) if messages else "Invalid request data",
                "details": errors
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error processing request {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": f"An unexpected internal server error occurred: {str(exc)}"
            }
        )

    @app.api_route("/health", methods=["GET", "HEAD"])
    async def health_check():
        return {"status": "ok"}

    @app.api_route("/", methods=["GET", "HEAD"])
    async def home():
        return {"status": "ok", "service": "rag-service"}

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()