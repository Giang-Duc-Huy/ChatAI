import csv, re
from pathlib import Path
from bs4 import BeautifulSoup
from app.config import DATA_RAW, CATALOG

FIELDS = ["file", "doc_title", "issuer", "date", "version", "effective_date", "group", "source"]

def read_file(p: Path) -> str:
    ext = p.suffix.lower()
    if ext == ".pdf":
        import fitz
        with fitz.open(p) as d:
            return "\n".join(page.get_text() for page in d)
    if ext in (".html", ".htm"):
        soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        for t in soup(["script", "style", "nav", "header", "footer"]):
            t.decompose()
        return soup.get_text("\n")
    if ext == ".docx":
        import docx
        return "\n".join(x.text for x in docx.Document(p).paragraphs)
    return ""

def load_catalog():
    """Tạo catalog.csv nếu chưa có (điền tay các cột còn trống: issuer, date, effective_date, version...)."""
    rows = {}
    if CATALOG.exists():
        with open(CATALOG, encoding="utf-8-sig") as f:
            rows = {r["file"]: r for r in csv.DictReader(f)}
    for p in sorted(DATA_RAW.iterdir()):
        if p.suffix.lower() in (".pdf", ".html", ".htm", ".docx") and p.name not in rows:
            rows[p.name] = {"file": p.name, "doc_title": p.stem, "issuer": "", "date": "", "version": "1",
                            "effective_date": "", "group": re.sub(r"[\d_\-\s]+$", "", p.stem), "source": str(p)}
    with open(CATALOG, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows.values())
    return list(rows.values())
