from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas import HealthResponse
from app.services.embedding import embedding_service
from app.services.llm import llm_service
from app.services.tts_service import tts_service
from app.services.vectorstore import vector_store_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    chunk_count = vector_store_service.count()
    return HealthResponse(
        status="ok" if chunk_count > 0 else "degraded",
        vector_db_ready=chunk_count > 0,
        chunk_count=chunk_count,
        embedding_loaded=embedding_service.loaded,
        embedding_model=settings.EMBEDDING_MODEL,
        llm_configured=llm_service.configured,
        tts_configured=tts_service.configured,
        features={
            "voice": settings.ENABLE_VOICE,
            "tts": settings.ENABLE_TTS,
            "avatar_3d": settings.ENABLE_3D,
            "query_rewrite": settings.ENABLE_QUERY_REWRITE,
        },
    )
