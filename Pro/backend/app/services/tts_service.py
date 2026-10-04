from __future__ import annotations

import base64
import hashlib
import logging
import re
from pathlib import Path

from app.config import get_settings
from app.utils.timing import StageTimer

logger = logging.getLogger(__name__)


def clean_tts_text(text: str) -> str:
    text = re.sub(r"[#*_`>~\[\]\(\)]+", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class TTSService:
    def __init__(self) -> None:
        self._client = None

    @property
    def configured(self) -> bool:
        settings = get_settings()
        return bool(settings.GOOGLE_APPLICATION_CREDENTIALS or settings.GOOGLE_TTS_API_KEY)

    def _cache_path(self, text: str) -> Path:
        settings = get_settings()
        cache_dir = Path(settings.TTS_CACHE_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(f"{settings.TTS_VOICE_NAME}:{text}".encode("utf-8")).hexdigest()
        return cache_dir / f"{digest}.mp3"

    def _get_client(self):
        if self._client is not None:
            return self._client
        settings = get_settings()
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            from google.cloud import texttospeech

            self._client = texttospeech.TextToSpeechClient()
            return self._client
        # API key via REST fallback is not implemented for service-account SDK;
        # require GOOGLE_APPLICATION_CREDENTIALS for production TTS.
        raise RuntimeError(
            "TTS cần GOOGLE_APPLICATION_CREDENTIALS trỏ tới file service account JSON"
        )

    def synthesize(self, text: str) -> tuple[bytes, dict, bool]:
        settings = get_settings()
        if not settings.ENABLE_TTS:
            raise RuntimeError("TTS đang tắt (ENABLE_TTS=false)")

        cleaned = clean_tts_text(text)
        if not cleaned:
            raise ValueError("Text TTS rỗng sau khi làm sạch")
        if len(cleaned) > settings.TTS_MAX_CHARS:
            cleaned = cleaned[: settings.TTS_MAX_CHARS]

        timer = StageTimer()
        timer.start("total")
        cache_file = self._cache_path(cleaned)
        if cache_file.exists():
            audio = cache_file.read_bytes()
            timer.stop("total")
            logger.info("TTS cache hit chars=%s bytes=%s", len(cleaned), len(audio))
            return audio, {"tts": timer.stages.get("total", 0.0), "total": timer.stages.get("total", 0.0)}, True

        from google.cloud import texttospeech

        with timer.measure("tts"):
            client = self._get_client()
            synthesis_input = texttospeech.SynthesisInput(text=cleaned)
            voice = texttospeech.VoiceSelectionParams(
                language_code=settings.TTS_LANGUAGE_CODE,
                name=settings.TTS_VOICE_NAME,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
            audio = response.audio_content

        cache_file.write_bytes(audio)
        timer.stop("total")
        logger.info(
            "TTS synthesized chars=%s bytes=%s voice=%s",
            len(cleaned),
            len(audio),
            settings.TTS_VOICE_NAME,
        )
        return (
            audio,
            {"tts": timer.stages.get("tts", 0.0), "total": timer.stages.get("total", 0.0)},
            False,
        )

    def synthesize_base64(self, text: str) -> tuple[str, dict, bool]:
        audio, timings, cached = self.synthesize(text)
        return base64.b64encode(audio).decode("ascii"), timings, cached


tts_service = TTSService()
