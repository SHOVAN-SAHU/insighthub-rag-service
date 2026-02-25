from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = "RAG Service"
    environment: str = "development"

    hf_api_token: str = Field(..., env="HF_API_TOKEN")
    hf_embed_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2",
        env="HF_EMBED_MODEL"
    )

    celery_broker_url: str = Field(..., env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., env="CELERY_RESULT_BACKEND")

    model_config = {
        "env_file": ".env"
    }

settings = Settings()
