from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "RAG Service"
    environment: str = "development"

settings = Settings()
