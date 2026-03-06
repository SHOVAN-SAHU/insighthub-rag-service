from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = "RAG Service"
    environment: str = "development"
    api_key: str = Field(..., env="API_KEY")
    collection_name: str = "insighthub_chunks"

    hf_api_token: str = Field(..., env="HF_API_TOKEN")
    hf_embed_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2",
        env="HF_EMBED_MODEL"
    )

    celery_broker_url: str = Field(..., env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., env="CELERY_RESULT_BACKEND")

    mongo_uri: str
    mongo_db_name: str = "rag_service_db"

    qdrant_url: str = Field(..., env="QDRANT_URL")
    qdrant_api_key: str = Field(..., env="QDRANT_API_KEY")

    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    groq_model: str = Field("llama-3.1-8b-instant", env="GROQ_MODEL")

    model_config = {
        "env_file": ".env"
    }

settings = Settings()
