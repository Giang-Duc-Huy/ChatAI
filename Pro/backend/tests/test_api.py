from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ChatResponse, SourceItem, TimingsMs
from app.services.llm import REFUSAL_NO_CONTEXT


client = TestClient(app)


def test_health_ok():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert "status" in body
    assert "chunk_count" in body


def test_chat_question_too_long():
    long_q = "a" * 600
    res = client.post("/api/chat", json={"question": long_q, "session_id": "t"})
    assert res.status_code == 400


def test_chat_empty_question():
    res = client.post("/api/chat", json={"question": "   ", "session_id": "t"})
    assert res.status_code == 400


@patch("app.routers.chat.rag_service")
def test_chat_schema_ok(mock_rag):
    mock_rag.answer.return_value = ChatResponse(
        answer="Học phí CNTT là 28 triệu/năm theo thông báo 2025.",
        sources=[
            SourceItem(doc_id="doc_02", title="Học phí", year=2025, page=1, snippet="...", score=0.8)
        ],
        answerable=True,
        timings_ms=TimingsMs(retrieval=10, llm=20, total=30),
    )
    res = client.post(
        "/api/chat",
        json={"question": "Học phí CNTT?", "session_id": "t", "history": []},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["answerable"] is True
    assert "timings_ms" in body
    assert body["sources"][0]["doc_id"] == "doc_02"


@patch("app.services.rag.retriever_service")
@patch("app.services.rag.llm_service")
def test_no_context_skips_llm(mock_llm, mock_retriever):
    from app.services.rag import rag_service

    mock_retriever.retrieve.return_value = []
    mock_llm.rewrite_question.side_effect = lambda q, h: q
    resp = rag_service.answer("Điểm chuẩn 2025?")
    assert resp.answerable is False
    assert resp.answer == REFUSAL_NO_CONTEXT
    mock_llm.generate.assert_not_called()


@patch("app.routers.tts.tts_service")
def test_tts_error_returns_clear_status(mock_tts):
    mock_tts.synthesize_base64.side_effect = RuntimeError("TTS chưa cấu hình")
    res = client.post("/api/tts", json={"text": "Xin chào"})
    assert res.status_code == 503
