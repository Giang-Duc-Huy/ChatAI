from __future__ import annotations

from app.services.retriever import RetrievedChunk, _distance_to_score


def test_distance_to_score():
    assert _distance_to_score(0.0) == 1.0
    assert abs(_distance_to_score(0.25) - 0.75) < 1e-6
    assert _distance_to_score(2.0) == 0.0


def test_retrieved_chunk_fields():
    c = RetrievedChunk(
        chunk_id="doc_01__0001",
        text="học phí",
        score=0.9,
        doc_id="doc_01",
        title="Đề án",
        year=2025,
        version="2025.1",
        status="active",
        page=1,
        section="Học phí",
        source_url="x.txt",
    )
    assert c.status == "active"
    assert c.year == 2025
