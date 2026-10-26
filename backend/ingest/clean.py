import re, unicodedata
from collections import Counter

def clean_pages(pages):
    """Bỏ dòng lặp ở > 50% trang (header/footer), NFC, gộp khoảng trắng."""
    if len(pages) > 2:
        cnt = Counter(l.strip() for p in pages for l in set(p.splitlines()) if l.strip())
        pages = ["\n".join(l for l in p.splitlines() if cnt[l.strip()] <= len(pages) / 2) for p in pages]
    return clean("\n".join(pages))

def clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()
