from __future__ import annotations

import re
import unicodedata


HEADER_FOOTER_PATTERNS = [
    re.compile(r"^trang\s+\d+(\s*/\s*\d+)?$", re.I),
    re.compile(r"^page\s+\d+$", re.I),
    re.compile(r"^mục lục$", re.I),
]


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            lines.append("")
            continue
        if any(p.match(s) for p in HEADER_FOOTER_PATTERNS):
            continue
        lines.append(s)
    text = "\n".join(lines)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
