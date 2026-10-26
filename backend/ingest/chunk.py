import re

SPLIT = re.compile(r"\n(?=\s*(?:Điều|ĐIỀU|Mục|MỤC|Chương|CHƯƠNG)\s+\d+)")
HEAD = re.compile(r"^\s*((?:Điều|ĐIỀU|Mục|MỤC|Chương|CHƯƠNG)\s+\d+[^\n]{0,80})")

def chunk(text, size=1000, overlap=150):
    out = []
    for part in SPLIT.split(text):
        m = HEAD.match(part)
        section = m.group(1).strip() if m else "Nội dung chung"
        p = re.sub(r"\s+", " ", part).strip()
        if len(p) < 20:
            continue
        step = size - overlap
        for i in range(0, len(p), step):
            out.append((section, p[i:i + size]))
            if i + size >= len(p):
                break
    return out
