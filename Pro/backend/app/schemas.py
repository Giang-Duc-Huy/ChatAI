from typing import Literal

from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str = "default"
    history: list[HistoryMessage] = Field(default_factory=list)


class SourceItem(BaseModel):
    doc_id: str
    title: str
    year: int | None = None
    page: int | None = None
    snippet: str = ""
    score: float = 0.0


class TimingsMs(BaseModel):
    retrieval: float = 0.0
    llm: float = 0.0
    tts: float = 0.0
    total: float = 0.0


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem] = Field(default_factory=list)
    answerable: bool = True
    timings_ms: TimingsMs = Field(default_factory=TimingsMs)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)


class TTSResponse(BaseModel):
    audio_content: str  # base64 audio/mpeg
    timings_ms: TimingsMs = Field(default_factory=TimingsMs)
    cached: bool = False


class HealthResponse(BaseModel):
    status: str = "ok"
    vector_db_ready: bool = False
    chunk_count: int = 0
    embedding_loaded: bool = False
    embedding_model: str = ""
    llm_configured: bool = False
    tts_configured: bool = False
    features: dict[str, bool] = Field(default_factory=dict)
