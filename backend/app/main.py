import time, collections, unicodedata
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import config, latency
from .latency import Timer

app = FastAPI(title="Trợ lý ảo 3D tuyển sinh")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
_hits = collections.defaultdict(collections.deque)

def rate_limit(request: Request):
    ip, now = request.client.host, time.time()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= config.RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Bạn hỏi hơi nhanh, vui lòng thử lại sau ít phút.")
    q.append(now)

class ChatIn(BaseModel):
    question: str
    top_k: int = Field(default=config.TOP_K, ge=1, le=10)
    min_score: float = Field(default=config.MIN_SCORE, ge=0, le=1)

class TtsIn(BaseModel):
    text: str

@app.get("/api/health")
def health():
    return {"status": "ok", "llm": config.LLM_MODEL, "api_key_set": bool(config.ANTHROPIC_API_KEY),
            "index_exists": config.INDEX_DIR.exists()}

@app.post("/api/chat")
def chat(body: ChatIn, request: Request):
    rate_limit(request)
    question = unicodedata.normalize("NFC", body.question).strip()
    if not question or len(question) > 1000:
        raise HTTPException(400, "Câu hỏi trống hoặc quá dài.")
    from .rag.retriever import retrieve
    from .rag.generator import generate
    t = Timer()
    try:
        with t.stage("retrieval"):
            chunks, ok = retrieve(question, k=body.top_k, min_score=body.min_score)
        with t.stage("llm"):
            answer, cost = generate(question, chunks, ok)
    except Exception as e:
        raise HTTPException(502, f"Lỗi xử lý: {e}")
    lat = t.total()
    sources = [{"doc_title": c["doc_title"], "section": c["section"], "date": c["effective_date"] or c["date"],
                "score": c["score"]} for c in chunks] if ok else []
    latency.log({"latency_ms": lat, "cost": cost, "sufficient": ok})
    return {"answer": answer, "sources": sources, "retrieved_chunks": chunks, "latency": lat}

@app.post("/api/stt")
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

@app.post("/api/tts")
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
