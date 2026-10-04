from __future__ import annotations

import logging
from typing import List

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self._model = None
        self.model_name = get_settings().EMBEDDING_MODEL

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", self.model_name)
        self._model = SentenceTransformer(self.model_name)
        logger.info("Embedding model loaded")

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        self.load()
        assert self._model is not None
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.embed([text])[0]


embedding_service = EmbeddingService()
