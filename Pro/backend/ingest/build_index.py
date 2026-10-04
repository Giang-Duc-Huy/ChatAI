from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

# Allow running as `python -m ingest.build_index` from backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.services.embedding import embedding_service
from app.services.vectorstore import vector_store_service
from ingest.chunk import chunk_pages
from ingest.clean import clean_text
from ingest.load_docs import load_document

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest")


def read_sources(csv_path: Path) -> list[dict]:
    with csv_path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def resolve_path(raw_dir: Path, url_or_path: str) -> Path | None:
    p = Path(url_or_path)
    if p.is_file():
        return p
    candidate = raw_dir / url_or_path
    if candidate.is_file():
        return candidate
    # basename only
    candidate = raw_dir / Path(url_or_path).name
    if candidate.is_file():
        return candidate
    return None


def index_doc(row: dict, raw_dir: Path, settings) -> int:
    doc_id = row["doc_id"].strip()
    path = resolve_path(raw_dir, row["url_or_path"].strip())
    if path is None:
        logger.warning("Skip %s: file not found (%s)", doc_id, row["url_or_path"])
        return 0

    pages = load_document(path)
    for p in pages:
        p["text"] = clean_text(p["text"])

    chunks = chunk_pages(
        pages,
        chunk_size_tokens=settings.CHUNK_SIZE_TOKENS,
        overlap_tokens=settings.CHUNK_OVERLAP_TOKENS,
    )
    if not chunks:
        logger.warning("No chunks for %s", doc_id)
        return 0

    ids, docs, metas = [], [], []
    year = int(row["year"]) if row.get("year") else None
    for ch in chunks:
        chunk_id = f"{doc_id}__{ch.index:04d}"
        ids.append(chunk_id)
        docs.append(ch.text)
        metas.append(
            {
                "doc_id": doc_id,
                "title": row.get("title") or path.stem,
                "year": year if year is not None else "",
                "version": row.get("version") or "",
                "status": row.get("status") or "active",
                "page": ch.page if ch.page is not None else "",
                "section": ch.section,
                "chunk_id": chunk_id,
                "source_url": row.get("url_or_path") or "",
            }
        )

    # Idempotent: upsert by chunk_id
    vector_store_service.delete_by_doc_id(doc_id)
    # embed in batches
    batch = 16
    for i in range(0, len(ids), batch):
        sl = slice(i, i + batch)
        embeddings = embedding_service.embed(docs[sl])
        vector_store_service.upsert(
            ids=ids[sl],
            documents=docs[sl],
            metadatas=metas[sl],
            embeddings=embeddings,
        )
    logger.info("Indexed %s → %s chunks (status=%s)", doc_id, len(ids), row.get("status"))
    return len(ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build / update admissions Chroma index")
    parser.add_argument("--rebuild", action="store_true", help="Xóa collection và index lại toàn bộ")
    parser.add_argument("--update", type=str, default=None, help="Chỉ cập nhật một doc_id")
    args = parser.parse_args()

    settings = get_settings()
    sources_path = Path(settings.SOURCES_CSV)
    raw_dir = Path(settings.RAW_DOCS_DIR)
    if not sources_path.exists():
        raise SystemExit(f"Missing sources.csv at {sources_path}")

    rows = read_sources(sources_path)
    if args.rebuild:
        logger.info("Rebuilding collection from scratch")
        vector_store_service.delete_all()

    if args.update:
        rows = [r for r in rows if r["doc_id"] == args.update]
        if not rows:
            raise SystemExit(f"doc_id not found: {args.update}")

    total = 0
    for row in rows:
        if (row.get("status") or "").strip() == "superseded" and not args.rebuild:
            # Still index superseded so metadata exists, but retriever filters them out
            pass
        total += index_doc(row, raw_dir, settings)

    logger.info("Done. Total chunks written this run: %s. Collection count=%s", total, vector_store_service.count())


if __name__ == "__main__":
    main()
