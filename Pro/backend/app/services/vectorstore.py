from __future__ import annotations

import logging
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.services.embedding import embedding_service

logger = logging.getLogger(__name__)


class VectorStoreService:
    def __init__(self) -> None:
        self._client: chromadb.PersistentClient | None = None
        self._collection = None

    def _ensure(self) -> None:
        if self._collection is not None:
            return
        settings = get_settings()
        logger.info("Opening Chroma at %s collection=%s", settings.CHROMA_PATH, settings.CHROMA_COLLECTION)
        self._client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def collection(self):
        self._ensure()
        return self._collection

    def count(self) -> int:
        try:
            self._ensure()
            return int(self._collection.count())  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Chroma count failed: %s", exc)
            return 0

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        self._ensure()
        if embeddings is None:
            embeddings = embedding_service.embed(documents)
        # Chroma metadata values must be scalars
        clean_meta = []
        for m in metadatas:
            clean_meta.append({k: ("" if v is None else v) for k, v in m.items()})
        self._collection.upsert(  # type: ignore[union-attr]
            ids=ids,
            documents=documents,
            metadatas=clean_meta,
            embeddings=embeddings,
        )

    def delete_by_doc_id(self, doc_id: str) -> None:
        self._ensure()
        self._collection.delete(where={"doc_id": doc_id})  # type: ignore[union-attr]

    def delete_all(self) -> None:
        settings = get_settings()
        self._ensure()
        assert self._client is not None
        try:
            self._client.delete_collection(settings.CHROMA_COLLECTION)
        except Exception:  # noqa: BLE001
            pass
        self._collection = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ensure()
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        return self._collection.query(**kwargs)  # type: ignore[union-attr]


vector_store_service = VectorStoreService()
