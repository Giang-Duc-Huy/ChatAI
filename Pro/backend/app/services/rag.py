from __future__ import annotations

import logging
import re

from app.config import get_settings
from app.schemas import ChatResponse, SourceItem, TimingsMs
from app.services.llm import REFUSAL_NO_CONTEXT, llm_service
from app.services.retriever import retriever_service
from app.utils.timing import StageTimer

logger = logging.getLogger(__name__)


def _redact_pii(text: str) -> str:
    text = re.sub(r"\b\d{9,12}\b", "[ID]", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.\w+", "[EMAIL]", text)
    text = re.sub(r"(0|\+84)\d{8,10}", "[PHONE]", text)
    return text


class RAGService:
    def answer(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatResponse:
        settings = get_settings()
        timer = StageTimer()
        timer.start("total")

        history = history or []
        # Keep last N turns
        max_msgs = settings.MAX_HISTORY_TURNS * 2
        history = history[-max_msgs:]

        q = question.strip()
        if len(q) > settings.MAX_QUESTION_CHARS:
            q = q[: settings.MAX_QUESTION_CHARS]

        logger.info("chat question_len=%s redacted=%s", len(q), _redact_pii(q)[:120])

        with timer.measure("rewrite"):
            rewritten = llm_service.rewrite_question(q, history)

        with timer.measure("retrieval"):
            chunks = retriever_service.retrieve(rewritten)

        if not chunks:
            timer.stop("total")
            timings = TimingsMs(
                retrieval=timer.stages.get("retrieval", 0.0),
                llm=0.0,
                total=timer.stages.get("total", 0.0),
            )
            timer.log("rag_refusal")
            return ChatResponse(
                answer=REFUSAL_NO_CONTEXT,
                sources=[],
                answerable=False,
                timings_ms=timings,
            )

        with timer.measure("llm"):
            answer, _usage = llm_service.generate(rewritten, chunks)

        timer.stop("total")
        sources = [
            SourceItem(
                doc_id=c.doc_id,
                title=c.title,
                year=c.year,
                page=c.page,
                snippet=(c.text[:240] + ("…" if len(c.text) > 240 else "")),
                score=c.score,
            )
            for c in chunks
        ]
        timings = TimingsMs(
            retrieval=timer.stages.get("retrieval", 0.0),
            llm=timer.stages.get("llm", 0.0),
            total=timer.stages.get("total", 0.0),
        )
        timer.log("rag_ok")
        return ChatResponse(answer=answer, sources=sources, answerable=True, timings_ms=timings)


rag_service = RAGService()
