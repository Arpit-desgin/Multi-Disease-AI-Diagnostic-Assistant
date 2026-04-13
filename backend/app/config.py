from functools import lru_cache
from typing import List, Optional
import json
import logging

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("app.config")


class Settings(BaseSettings):
    # Core
    DATABASE_URL: str = "sqlite+aiosqlite:///./medintel.db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # External services (optional)
    LLM_PROVIDER: str = "local"
    OLLAMA_MODEL: str = "mistral"
    FAISS_INDEX_PATH: str = "app/rag/faiss_index"
    TOP_K: int = 4
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    REDIS_URL: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # ML model paths are resolved via pathlib in ml_service.py
    # (app/ml_models/{diabetic_retinopathy,lung,skin}/)
    # No path config needed here.

    # CORS - should include localhost:8080 for the React frontend
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8080"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse ALLOWED_ORIGINS from JSON string or keep as list"""
        logger.info(f"[CONFIG] Parsing ALLOWED_ORIGINS: {v} (type: {type(v).__name__})")
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                logger.info(f"[CONFIG] Successfully parsed ALLOWED_ORIGINS from JSON: {parsed}")
                return parsed
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"[CONFIG] Failed to parse ALLOWED_ORIGINS as JSON: {e}, using default")
                return ["http://localhost:8080"]
        logger.info(f"[CONFIG] Using ALLOWED_ORIGINS as-is: {v}")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

