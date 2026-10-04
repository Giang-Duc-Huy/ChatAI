from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.schemas import ChatRequest, ChatResponse
from app.services.rag import rag_service
from app.utils.rate_limit import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)
router = APIRouter()

_limiter: SlidingWindowRateLimiter | None = None


def _get_limiter() -> SlidingWindowRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = SlidingWindowRateLimiter(get_settings().RATE_LIMIT_PER_MINUTE)
    return _limiter


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{req.session_id}"
    if not _get_limiter().allow(key):
        raise HTTPException(status_code=429, detail="Quá nhiều yêu cầu, vui lòng thử lại sau.")

    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")
    if len(question) > settings.MAX_QUESTION_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Câu hỏi tối đa {settings.MAX_QUESTION_CHARS} ký tự.",
        )

    history = [{"role": m.role, "content": m.content} for m in req.history]

    try:
        return rag_service.answer(question=question, history=history)
    except RuntimeError as exc:
        logger.exception("RAG runtime error")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("RAG unexpected error")
        raise HTTPException(
            status_code=502,
            detail="Dịch vụ trả lời tạm thời lỗi. Bạn có thể thử lại hoặc dùng chế độ chỉ văn bản.",
        ) from exc
