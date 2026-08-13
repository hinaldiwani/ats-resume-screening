"""
app/core/config.py

Centralized application configuration.
Loads values from environment variables / .env file via pydantic-settings.

No business logic lives here — only settings declarations and a cached
accessor (`get_settings`) so the rest of the app never reads os.environ directly.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- App ----
    APP_NAME: str = "ATS Resume Screening System"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # ---- Security / JWT ----
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- Database ----
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DATABASE_URL: str

    # ---- Redis / Celery ----
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # ---- File storage ----
    UPLOAD_DIR: str = "static/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_RESUME_EXTENSIONS: str = ".pdf,.docx"

    # ---- Hugging Face / AI models ----
    HF_HOME: str = "./.hf_cache"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    NER_MODEL_NAME: str = "dslim/bert-base-NER"

    # ---- Logging ----
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FILE: str = "app.log"

    # ---- CORS ----
    CORS_ORIGINS: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def allowed_resume_extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.ALLOWED_RESUME_EXTENSIONS.split(",")]

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance so the .env file is parsed only once
    per process. Import this everywhere instead of instantiating Settings()
    directly:

        from app.core.config import get_settings
        settings = get_settings()
    """
    return Settings()
