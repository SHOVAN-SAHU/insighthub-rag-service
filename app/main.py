from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.v1.router import api_router
from app.core.mongo_async import connect_to_mongo, close_mongo_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    print("MongoDB connected")

    yield

    # Shutdown
    await close_mongo_connection()
    print("MongoDB disconnected")


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Service",
        version="0.1.0",
        lifespan=lifespan
    )

    @app.get("/")
    def home():
        return {"message": "Hello World"}

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
