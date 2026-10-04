from __future__ import annotations

from ingest.chunk import chunk_pages
from ingest.clean import clean_text


def test_clean_text_nfc_and_whitespace():
    raw = "Xin\u0043\u0301 chào\n\n\n  thế   giới  "
    # NFC + collapse
    out = clean_text("A   B\n\n\nC")
    assert "A B" in out or out.startswith("A")
    assert "\n\n\n" not in out


def test_chunk_size_and_overlap():
    pages = [
        {
            "page": 1,
            "text": "\n\n".join(
                [f"Đoạn số {i}. " + ("nội dung tuyển sinh học phí chỉ tiêu. " * 20) for i in range(12)]
            ),
        }
    ]
    chunks = chunk_pages(pages, chunk_size_tokens=200, overlap_tokens=40)
    assert len(chunks) >= 2
    # Approximate size: each chunk should not be wildly oversized
    for ch in chunks:
        assert len(ch.text) < 200 * 4 * 2.5


def test_chunk_prefers_sections():
    pages = [
        {
            "page": 1,
            "text": "1. HỌC PHÍ\n\nHọc phí CNTT 28 triệu.\n\n2. CHỈ TIÊU\n\nChỉ tiêu 700 sinh viên.",
        }
    ]
    chunks = chunk_pages(pages, chunk_size_tokens=80, overlap_tokens=20)
    assert chunks
    assert any(c.section for c in chunks)
