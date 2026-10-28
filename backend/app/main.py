import time, collections, unicodedata, logging
from threading import Thread
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import config, latency
from .latency import Timer

logger = logging.getLogger(__name__)
app = FastAPI(
    title="Trợ lý ảo 3D tuyển sinh",
    description=(
        "API tư vấn tuyển sinh sử dụng RAG. Chỉ mục ChromaDB dùng collection "
        "`tuyensinh`, mỗi vector gắn với nội dung một đoạn và metadata tài liệu "
        "như `doc_title`, `version`, `effective_date`, `section`, `page` và "
        "`superseded`."
    ),
    openapi_tags=[
        {
            "name": "Hệ thống",
            "description": "Các API kiểm tra trạng thái dịch vụ.",
        },
        {
            "name": "Hỏi đáp",
            "description": "API hỏi đáp tuyển sinh dựa trên tài liệu đã lập chỉ mục.",
        },
        {
            "name": "Giọng nói",
            "description": "Các API chuyển giọng nói thành văn bản và tổng hợp giọng nói.",
        },
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
_hits = collections.defaultdict(collections.deque)

def _warm_retriever():
    try:
        from .rag.retriever import warm
        warm()
    except Exception:
        logger.exception("Không thể khởi tạo trước mô hình truy xuất RAG.")

@app.on_event("startup")
def warm_rag_in_background():
    Thread(target=_warm_retriever, name="rag-warmup", daemon=True).start()

def rate_limit(request: Request):
    ip, now = request.client.host, time.time()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= config.RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Bạn hỏi hơi nhanh, vui lòng thử lại sau ít phút.")
    q.append(now)

class ChatIn(BaseModel):
    query: str = Field(
        description="Câu hỏi cần tra cứu trong tài liệu tuyển sinh.",
        examples=["Điều kiện xét tuyển năm 2026 là gì?"],
    )
    year: int | None = Field(
        default=None,
        description="Lọc tài liệu theo năm phiên bản; bỏ trống để tìm trên mọi năm.",
        examples=[2026],
    )
    top_k: int = Field(default=config.TOP_K, ge=1, le=10)
    min_score: float = Field(default=config.MIN_SCORE, ge=0, le=1)

class SourceOut(BaseModel):
    doc_title: str = Field(description="Tên tài liệu nguồn.")
    section: str = Field(description="Mục hoặc phần chứa nội dung được trích dẫn.")
    date: str = Field(description="Ngày hiệu lực hoặc ngày tài liệu.")
    url: str = Field(description="URL tài liệu chính thức, nếu có.")
    score: float = Field(description="Điểm tương đồng của nguồn truy xuất.")

class ChatOut(BaseModel):
    answer: str = Field(description="Câu trả lời được tạo từ các đoạn tài liệu truy xuất.")
    sources: list[SourceOut] = Field(description="Metadata các nguồn hỗ trợ câu trả lời.")
    retrieved_chunks: list[dict] = Field(description="Các đoạn văn bản truy xuất từ ChromaDB.")
    latency: dict[str, float] = Field(description="Thời gian xử lý theo từng giai đoạn, mili giây.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "answer": "Điều kiện xét tuyển được nêu trong thông tin tuyển sinh năm 2026.",
                "sources": [
                    {
                        "doc_title": "Thông tin tuyển sinh UIT 2026",
                        "section": "Đối tượng và điều kiện tuyển sinh",
                        "date": "2026-01-01",
                        "url": "https://tuyensinh.uit.edu.vn/",
                        "score": 0.82,
                    }
                ],
                "retrieved_chunks": [
                    {
                        "doc_title": "Thông tin tuyển sinh UIT 2026",
                        "version": "2026",
                        "section": "Đối tượng và điều kiện tuyển sinh",
                        "text": "...",
                        "score": 0.82,
                    }
                ],
                "latency": {"retrieval": 120.0, "llm": 800.0, "total": 920.0},
            }
        }
    }

class TtsIn(BaseModel):
    text: str

@app.get(
    "/api/health",
    tags=["Hệ thống"],
    summary="Kiểm tra trạng thái API",
)
def health():
    return {"status": "ok", "llm": config.LLM_MODEL, "api_key_set": bool(config.GOOGLE_API_KEY),
            "index_exists": config.INDEX_DIR.exists()}

@app.post(
    "/api/chat",
    response_model=ChatOut,
    status_code=200,
    tags=["Hỏi đáp"],
    summary="Hỏi đáp RAG về tuyển sinh",
    description=(
        "Truy xuất các đoạn phù hợp trong collection ChromaDB `tuyensinh`, sau đó "
        "tạo câu trả lời và trả về metadata nguồn. Có thể đặt `year` để chỉ tìm "
        "trong phiên bản tài liệu tương ứng."
    ),
    response_description="Câu trả lời, metadata nguồn, các đoạn truy xuất và độ trễ.",
)
def chat(body: ChatIn, request: Request):
    rate_limit(request)
    question = unicodedata.normalize("NFC", body.query).strip()
    if not question or len(question) > 1000:
        raise HTTPException(400, "Câu hỏi trống hoặc quá dài.")
    from .rag.retriever import retrieve
    from .rag.generator import generate
    t = Timer()
    try:
        with t.stage("retrieval"):
            chunks, ok = retrieve(
                question,
                k=body.top_k,
                min_score=body.min_score,
                year=body.year,
            )
        with t.stage("llm"):
            answer, cost = generate(question, chunks, ok)
    except Exception as e:
        if getattr(e, "code", None) in {429, 500, 502, 503, 504}:
            raise HTTPException(
                503,
                "Dịch vụ AI đang quá tải hoặc tạm thời không khả dụng. "
                "Bạn vui lòng thử gửi lại sau ít phút.",
            ) from e
        raise HTTPException(502, f"Lỗi xử lý: {e}")
    lat = t.total()
    sources = [{"doc_title": c["doc_title"], "section": c["section"], "date": c["effective_date"] or c["date"],
                "url": c.get("official_url", ""),
                "score": c["score"]} for c in chunks] if ok else []
    latency.log({"latency_ms": lat, "cost": cost, "sufficient": ok})
    return {"answer": answer, "sources": sources, "retrieved_chunks": chunks, "latency": lat}

@app.post(
    "/api/stt",
    tags=["Giọng nói"],
    summary="Chuyển giọng nói thành văn bản",
)
async def stt(request: Request, file: UploadFile = File(...)):
    rate_limit(request)
    from .stt import transcribe
    t = Timer()
    with t.stage("stt"):
        text = transcribe(await file.read())
    latency.log({"stage": "stt", "latency_ms": t.total()})
    if not text:
        raise HTTPException(422, "Không nghe rõ, bạn thử lại hoặc nhập văn bản.")
    return {"text": text}

@app.post(
    "/api/tts",
    tags=["Giọng nói"],
    summary="Tạo giọng nói từ văn bản",
)
async def tts(body: TtsIn, request: Request):
    rate_limit(request)
    from .tts import synthesize
    t = Timer()
    with t.stage("tts"):
        res = await synthesize(body.text[:1500])
    latency.log({"stage": "tts", "latency_ms": t.total()})
    return res

if config.FRONTEND.joinpath("index.html").exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND, html=True), name="web")
