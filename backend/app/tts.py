import base64
from .config import TTS_VOICE
from .viseme import build_timeline

async def synthesize(text: str) -> dict:
    """TTS đóng gói sau một giao diện riêng để thay được edge-tts khi cần."""
    import edge_tts
    comm = edge_tts.Communicate(text, TTS_VOICE, boundary="WordBoundary")
    audio, bounds = bytearray(), []
    async for ev in comm.stream():
        if ev["type"] == "audio":
            audio.extend(ev["data"])
        elif ev["type"] == "WordBoundary":
            bounds.append({"text": ev["text"], "start": ev["offset"] / 1e7, "dur": ev["duration"] / 1e7})
    return {"audio_b64": base64.b64encode(bytes(audio)).decode(), "mime": "audio/mpeg",
            "visemes": build_timeline(text, bounds or None)}
