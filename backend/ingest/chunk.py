import re

SPLIT = re.compile(r"\n(?=\s*(?:Điều|ĐIỀU|Mục|MỤC|Chương|CHƯƠNG)\s+\d+)")
HEAD = re.compile(r"^\s*((?:Điều|ĐIỀU|Mục|MỤC|Chương|CHƯƠNG)\s+\d+[^\n]{0,80})")
PAGE = re.compile(r"^\[\[PAGE:(\d+)\]\]\s*")

def chunk(text, tokenizer, size=700, overlap=100):
    out = []
    for raw_page in re.split(r"(?=\[\[PAGE:\d+\]\])", text):
        page_match = PAGE.match(raw_page.strip())
        page = int(page_match.group(1)) if page_match else 0
        if page_match:
            raw_page = raw_page.strip()[page_match.end():]
        for part in SPLIT.split(raw_page):
            m = HEAD.match(part)
            section = m.group(1).strip() if m else "Nội dung chung"
            p = re.sub(r"\s+", " ", part).strip()
            if len(p) < 20:
                continue
            tokens = tokenizer.encode(p, add_special_tokens=False)
            step = size - overlap
            for i in range(0, len(tokens), step):
                piece = tokenizer.decode(tokens[i:i + size], skip_special_tokens=True).strip()
                if len(piece) >= 20:
                    out.append((section, piece, page))
                if i + size >= len(tokens):
                    break
    return out
