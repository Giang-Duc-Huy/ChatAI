from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    section: str
    page: int | None
    index: int


_HEADING_RE = re.compile(r"^(#{1,3}\s+|[IVX]+\.|(\d+\.)+\s*|[A-ZĐÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÊỀẾỂỄỆÔỒỐỔỖỘƠỜỚỞỠỢƯỪỨỬỮỰ][^\n]{0,80}:?\s*)$")


def _approx_tokens(text: str) -> int:
    # Rough VI/EN estimate: ~1 token ≈ 4 chars
    return max(1, len(text) // 4)


def chunk_pages(
    pages: list[dict],
    chunk_size_tokens: int = 650,
    overlap_tokens: int = 100,
) -> list[Chunk]:
    # Prefer cutting on headings / blank lines
    blocks: list[tuple[str, int | None, str]] = []
    current_section = "general"
    for page in pages:
        page_no = page.get("page")
        text = page.get("text") or ""
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if not para:
                continue
            first_line = para.splitlines()[0].strip()
            if len(first_line) < 80 and (
                first_line.isupper()
                or first_line.startswith("#")
                or re.match(r"^(\d+\.|[IVX]+\.)\s+", first_line)
            ):
                current_section = first_line.lstrip("#").strip()[:120]
            blocks.append((para, page_no, current_section))

    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_tokens = 0
    buf_page: int | None = None
    buf_section = "general"
    overlap_chars = overlap_tokens * 4
    target_chars = chunk_size_tokens * 4

    def flush() -> None:
        nonlocal buf, buf_tokens, buf_page, buf_section
        if not buf:
            return
        text = "\n\n".join(buf).strip()
        if text:
            chunks.append(
                Chunk(text=text, section=buf_section, page=buf_page, index=len(chunks))
            )
        # Keep overlap tail
        if overlap_chars > 0 and text:
            tail = text[-overlap_chars:]
            buf = [tail]
            buf_tokens = _approx_tokens(tail)
        else:
            buf = []
            buf_tokens = 0

    for para, page_no, section in blocks:
        para_tokens = _approx_tokens(para)
        if not buf:
            buf_page = page_no
            buf_section = section
        if buf_tokens + para_tokens > chunk_size_tokens and buf:
            flush()
            buf_page = page_no
            buf_section = section
        buf.append(para)
        buf_tokens += para_tokens
        # Hard split very long paragraph
        while buf_tokens > chunk_size_tokens * 1.5 and buf:
            joined = "\n\n".join(buf)
            cut = joined[:target_chars]
            # try cut at sentence
            m = re.search(r"[\.\!\?]\s+", cut[::-1])
            if m:
                cut_at = len(cut) - m.start()
                cut = joined[:cut_at]
            chunks.append(
                Chunk(text=cut.strip(), section=buf_section, page=buf_page, index=len(chunks))
            )
            remainder = joined[len(cut) :].strip()
            if overlap_chars and cut:
                remainder = (cut[-overlap_chars:] + " " + remainder).strip()
            buf = [remainder] if remainder else []
            buf_tokens = _approx_tokens(remainder) if remainder else 0

    flush()
    return chunks
