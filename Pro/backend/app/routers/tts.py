from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response

from app.config import get_settings
from app.schemas import TimingsMs, TTSRequest, TTSResponse
from app.services.tts_service import tts_service
from app.utils.rate_limit import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)
router = APIRouter()

_limiter: SlidingWindowRateLimiter | None = None


def _get_limiter() -> SlidingWindowRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = SlidingWindowRateLimiter(get_settings().RATE_LIMIT_PER_MINUTE)
    return _limiter


@router.post("/tts")
async def tts(req: TTSRequest, request: Request, format: str = "json"):
    settings = get_settings()
    if not settings.ENABLE_TTS:
        raise HTTPException(status_code=503, detail="TTS đang tắt.")

    client_ip = request.client.host if request.client else "unknown"
    if not _get_limiter().allow(f"tts:{client_ip}"):
        raise HTTPException(status_code=429, detail="Quá nhiều yêu cầu TTS.")

    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text TTS trống.")
    if len(text) > settings.TTS_MAX_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Text TTS tối đa {settings.TTS_MAX_CHARS} ký tự.",
        )

    try:
        if format == "audio":
            audio, timings, _cached = tts_service.synthesize(text)
            return Response(
                content=audio,
                media_type="audio/mpeg",
                headers={"X-Timings-Ms": str(timings.get("total", 0))},
            )
        b64, timings, cached = tts_service.synthesize_base64(text)
        return TTSResponse(
            audio_content=b64,
            timings_ms=TimingsMs(tts=timings.get("tts", 0.0), total=timings.get("total", 0.0)),
            cached=cached,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.warning("TTS unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("TTS error")
        raise HTTPException(
            status_code=502,
            detail="Lỗi TTS. Frontend nên rơi về chế độ chỉ văn bản.",
        ) from exc
