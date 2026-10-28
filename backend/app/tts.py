import base64
from collections import OrderedDict
from .config import TTS_VOICE
from .viseme import build_timeline

_CACHE_LIMIT = 64
_cache = OrderedDict()

async def synthesize(text: str) -> dict:
    """TTS đóng gói sau một giao diện riêng để thay được edge-tts khi cần."""
    key = (TTS_VOICE, text)
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]

    import edge_tts
    comm = edge_tts.Communicate(text, TTS_VOICE, boundary="WordBoundary")
    audio, bounds = bytearray(), []
    async for ev in comm.stream():
        if ev["type"] == "audio":
            audio.extend(ev["data"])
        elif ev["type"] == "WordBoundary":
            bounds.append({"text": ev["text"], "start": ev["offset"] / 1e7, "dur": ev["duration"] / 1e7})
    result = {"audio_b64": base64.b64encode(bytes(audio)).decode(), "mime": "audio/mpeg",
              "visemes": build_timeline(text, bounds or None)}
    _cache[key] = result
    _cache.move_to_end(key)
    if len(_cache) > _CACHE_LIMIT:
        _cache.popitem(last=False)
    return result
