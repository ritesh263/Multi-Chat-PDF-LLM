import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise AI Research Assistant"
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = "enterprise_rag"
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_signing_key_change_in_production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    UPLOAD_DIR: str = "uploaded_documents"
    FAISS_INDEX_DIR: str = "faiss_indices"

    class Config:
        env_file = ".env"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.FAISS_INDEX_DIR, exist_ok=True)