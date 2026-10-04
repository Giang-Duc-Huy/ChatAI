from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import get_settings
from app.services.embedding import embedding_service
from app.services.vectorstore import vector_store_service

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float
    doc_id: str
    title: str
    year: int | None
    version: str
    status: str
    page: int | None
    section: str
    source_url: str


def _distance_to_score(distance: float) -> float:
    # Cosine distance in Chroma ≈ 1 - cosine_similarity for normalized vectors
    return max(0.0, 1.0 - float(distance))


class RetrieverService:
    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        settings = get_settings()
        k = top_k or settings.TOP_K
        if vector_store_service.count() == 0:
            return []

        embedding = embedding_service.embed_query(query)
        # Prefer active documents; if filter fails (empty), fall back without filter
        raw = None
        try:
            raw = vector_store_service.query(
                query_embedding=embedding,
                n_results=max(k * 3, k),
                where={"status": "active"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Filtered query failed, retrying without filter: %s", exc)
            raw = vector_store_service.query(query_embedding=embedding, n_results=max(k * 3, k))

        ids = (raw.get("ids") or [[]])[0]
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for i, chunk_id in enumerate(ids):
            meta = metas[i] or {}
            score = _distance_to_score(dists[i]) if i < len(dists) else 0.0
            if score < settings.MIN_SCORE:
                continue
            status = str(meta.get("status") or "active")
            if status != "active":
                continue
            year_raw = meta.get("year")
            page_raw = meta.get("page")
            try:
                year = int(year_raw) if year_raw not in (None, "") else None
            except (TypeError, ValueError):
                year = None
            try:
                page = int(page_raw) if page_raw not in (None, "") else None
            except (TypeError, ValueError):
                page = None
            chunks.append(
                RetrievedChunk(
                    chunk_id=str(chunk_id),
                    text=docs[i] or "",
                    score=round(score, 4),
                    doc_id=str(meta.get("doc_id") or ""),
                    title=str(meta.get("title") or ""),
                    year=year,
                    version=str(meta.get("version") or ""),
                    status=status,
                    page=page,
                    section=str(meta.get("section") or ""),
                    source_url=str(meta.get("source_url") or ""),
                )
            )

        # Prefer newer year when scores are close
        chunks.sort(key=lambda c: (c.score, c.year or 0), reverse=True)
        return chunks[:k]


retriever_service = RetrieverService()
