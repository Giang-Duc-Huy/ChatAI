from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data"


class Settings(BaseSettings):
    # LLM
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_API_KEY: str = ""
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024
    LLM_TIMEOUT_SEC: float = 60.0
    LLM_MAX_RETRIES: int = 2
    ENABLE_QUERY_REWRITE: bool = True

    # Embedding / vector
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    CHROMA_PATH: str = str(DATA_DIR / "chroma")
    CHROMA_COLLECTION: str = "admissions"
    TOP_K: int = 5
    MIN_SCORE: float = 0.35

    # Chunking
    CHUNK_SIZE_TOKENS: int = 650
    CHUNK_OVERLAP_TOKENS: int = 100

    # Chat limits
    MAX_QUESTION_CHARS: int = 500
    MAX_HISTORY_TURNS: int = 6
    RATE_LIMIT_PER_MINUTE: int = 30

    # TTS
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    GOOGLE_TTS_API_KEY: str = ""
    TTS_VOICE_NAME: str = "vi-VN-Neural2-A"
    TTS_LANGUAGE_CODE: str = "vi-VN"
    TTS_MAX_CHARS: int = 800
    TTS_CACHE_DIR: str = str(DATA_DIR / "tts_cache")
    ENABLE_TTS: bool = True

    # Feature flags
    ENABLE_VOICE: bool = True
    ENABLE_3D: bool = True

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Paths
    SOURCES_CSV: str = str(DATA_DIR / "sources.csv")
    RAW_DOCS_DIR: str = str(DATA_DIR / "raw")

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
