import re, unicodedata

MAP = {"a": "aa", "ă": "aa", "â": "aa", "e": "ee", "ê": "ee", "i": "ih", "y": "ih",
       "o": "oh", "ô": "oh", "ơ": "oh", "u": "ou", "ư": "ou"}
_TONES = dict.fromkeys(map(ord, "\u0300\u0301\u0303\u0309\u0323"))

def syllable(word):
    w = unicodedata.normalize("NFD", word).translate(_TONES)
    w = unicodedata.normalize("NFC", w).lower()
    w = re.sub(r"[^a-zăâêôơưđ]", "", w)
    if not w:
        return None
    lip = bool(re.match(r"[bmp]", w))
    s = re.sub(r"^qu", "q", w)
    s = re.sub(r"^gi(?=[aăâeêoôơuưy])", "g", s)
    vs = [c for c in s if c in MAP]
    if not vs:
        return {"v": None, "lip": lip}
    main = next((c for c in vs if c in "aăâơôoeê"), vs[0])
    return {"v": MAP[main], "lip": lip}

def build_timeline(text, boundaries=None, duration=None):
    """Trả về [{t0,t1,viseme,lip}] (giây). Dùng mốc từ do TTS trả về nếu có,
    nếu không thì chia đều theo tổng thời lượng."""
    words = [(m.start(), m.group()) for m in re.finditer(r"\S+", text)]
    if boundaries:
        tl = []
        for b in boundaries:
            sy = syllable(b["text"]) or {"v": None, "lip": False}
            tl.append({"t0": b["start"], "t1": b["start"] + b["dur"], "viseme": sy["v"], "lip": sy["lip"]})
        return tl
    duration = duration or 0.24 * len(words)
    step = duration / max(1, len(words))
    out = []
    for i, (_, w) in enumerate(words):
        sy = syllable(w) or {"v": None, "lip": False}
        out.append({"t0": i * step, "t1": (i + 1) * step, "viseme": sy["v"], "lip": sy["lip"]})
    return out
