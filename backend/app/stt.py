import os, tempfile
from .config import WHISPER_MODEL

_model = None

def transcribe(data: bytes, suffix=".webm") -> str:
    """STT cục bộ bằng faster-whisper. Âm thanh chỉ ghi file tạm và xoá ngay."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(WHISPER_MODEL, compute_type="int8")
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        segs, _ = _model.transcribe(path, language="vi", vad_filter=True)
        return " ".join(s.text.strip() for s in segs).strip()
    finally:
        os.remove(path)
