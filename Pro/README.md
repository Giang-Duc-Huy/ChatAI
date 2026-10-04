# Trợ lý tư vấn tuyển sinh MVP (RAG + giọng nói + nhân vật 3D)

Hệ thống hỏi–đáp tuyển sinh **một trường**, lõi là RAG văn bản; STT/TTS và avatar VRM bật/tắt độc lập.

## Yêu cầu máy

- Python 3.11+
- Node.js 18+
- (Tuỳ chọn) Tài khoản Anthropic Claude API
- (Tuỳ chọn) Google Cloud TTS service account JSON
- (Tuỳ chọn) File `frontend/public/models/avatar.vrm`

## Cài đặt backend

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # hoặc cp .env.example .env
```

Sửa `backend/.env`: điền `ANTHROPIC_API_KEY`. Nếu dùng TTS, đặt `GOOGLE_APPLICATION_CREDENTIALS` trỏ tới file JSON.

### Index tài liệu mẫu

```bash
cd backend
python -m ingest.build_index --rebuild
```

Lần đầu sẽ tải model embedding `BAAI/bge-m3` (hơi nặng).

Cập nhật một tài liệu:

```bash
python -m ingest.build_index --update doc_02
```

### Chạy API

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: http://127.0.0.1:8000/api/health  
- Docs: http://127.0.0.1:8000/docs  

## Cài đặt frontend

```bash
cd frontend
npm install
npm run dev
```

Mở http://localhost:5173 (Vite proxy `/api` → `:8000`).

Đặt model VRM vào `frontend/public/models/avatar.vrm`. Nếu thiếu file, avatar hiện hình cầu fallback; tắt công tắc **Nhân vật 3D** nếu máy yếu.

## Feature flags

Trong `.env` / Settings UI:

| Flag | Ý nghĩa |
|---|---|
| `ENABLE_TTS` / công tắc “Đọc câu trả lời” | TTS |
| `ENABLE_VOICE` | Cho phép lớp giọng nói phía server config |
| `ENABLE_3D` / công tắc “Nhân vật 3D” | Avatar |
| `ENABLE_QUERY_REWRITE` | Viết lại câu hỏi phụ thuộc ngữ cảnh |

Nếu TTS lỗi, UI vẫn chat văn bản bình thường.

## API chính

### `POST /api/chat`

```json
{
  "question": "Học phí ngành CNTT?",
  "session_id": "uuid",
  "history": [{"role": "user", "content": "..."}]
}
```

### `POST /api/tts`

```json
{ "text": "Câu trả lời..." }
```

Trả base64 MP3 + `timings_ms` (hoặc `?format=audio` để nhận `audio/mpeg`).

### `GET /api/health`

Trạng thái Chroma, số chunk, LLM/TTS đã cấu hình chưa.

## Đánh giá

```bash
cd backend
python eval/eval_retrieval.py
python eval/eval_generation.py --limit 10
python eval/eval_latency.py --runs 30
```

Bộ câu hỏi: `eval/testset.jsonl` (50 câu). Phiếu khảo sát: `docs/user_survey.md`.

## Kiểm thử

```bash
cd backend
pytest -q
```

## Cấu trúc

Xem đặc tả dự án — thư mục `backend/app`, `ingest`, `eval`, `frontend/src` đã khớp bố cục yêu cầu.

## Giới hạn hệ thống

- Chỉ miền tuyển sinh (ngành, phương thức, học phí, chỉ tiêu) của dữ liệu đã index.
- Không thay thế tư vấn chính thức; số liệu phụ thuộc tài liệu trong `data/raw`.
- Web Speech API phụ thuộc trình duyệt (Chrome/Edge tốt nhất), xử lý giọng nói phía Google/trình duyệt — hệ thống không lưu audio.
- Lip-sync MVP dùng biên độ phổ, không phải mô hình chuyên dụng.
- Chi phí: log token LLM và số ký tự TTS trên backend để ước tính vận hành.

## Ước tính chi phí (tham khảo)

| Hạng mục | Ghi chú |
|---|---|
| Claude API | Theo token input/output mỗi `/api/chat` (xem log) |
| Embedding | Chạy local — không phí API |
| Google TTS | Theo ký tự; có cache hash trên đĩa `data/tts_cache` |
| Chroma / máy chủ | Chi phí máy host |

## Dữ liệu mẫu

`data/sources.csv` + `data/raw/*.txt` mô phỏng **Đại học ABC 2025** (demo). Thay bằng đề án thật của trường khi triển khai.
