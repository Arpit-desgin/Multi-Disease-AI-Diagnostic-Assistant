from functools import lru_cache
from typing import List, Optional
import json
import logging

from pydantic_settings import BaseSettings
from pydantic import field_validator

logger = logging.getLogger("app.config")


class Settings(BaseSettings):
    # Core
    DATABASE_URL: str = "sqlite+aiosqlite:///./medintel.db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # External services (optional)
    GEMINI_API_KEY: Optional[str] = None
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # ML model paths
    LUNG_MODEL_PATH: str = "app/ml_models/lung_cancer_model.h5"
    SKIN_MODEL_PATH: str = "app/ml_models/skin_disease_model.h5"
    DR_MODEL_PATH: str = "app/ml_models/diabetic_retinopathy_model.h5"

    # CORS - should include localhost:8080 for the React frontend
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8080"]

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

