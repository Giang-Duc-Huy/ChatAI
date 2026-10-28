# Trợ lý ảo 3D tư vấn tuyển sinh UIT

## Cài đặt (Python 3.11)
```bash
cd backend && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env     # Windows PowerShell: Copy-Item ..\.env.example ..\.env
```
Điền `GOOGLE_API_KEY` bằng khóa Google AI Studio. Backend cũng đọc tương thích `GEMINI_API_KEY` và `ANTHROPIC_API_KEY` nếu file `.env` hiện tại vẫn dùng tên cũ. Model mặc định là `gemini-2.5-flash`; có thể đổi qua `LLM_MODEL`. Để ghi ước tính chi phí, đặt `GEMINI_PRICE_IN_PER_M` và `GEMINI_PRICE_OUT_PER_M` theo model/tier đang dùng; nếu không, báo cáo chỉ ghi token usage và để trống chi phí.
## Nạp dữ liệu
1. Chép các PDF/HTML vào `data/raw/`. Corpus hiện có PDF tuyển sinh UIT 2025/2026, hướng dẫn lệ phí 2023 và thông báo ngưỡng đầu vào UIT 2026.
2. `python -m ingest.build_index` (lần đầu tạo `data/catalog.csv`; điền các metadata còn thiếu rồi chạy lại. Tài liệu cùng cột `group` giữ bản có `effective_date` mới nhất; bản cũ bị `superseded`). Catalog bảo toàn các cột bổ sung như `official_url`, `source_verification` và `rights_status`.
## Frontend (React + Vite + TypeScript)
```bash
cd frontend && npm install
npm run dev          # http://localhost:5173 (proxy /api -> :8000)
npm run build        # ra frontend/dist để backend phục vụ
```
## Chạy
```bash
cd backend && uvicorn app.main:app --port 8000
```
Mở http://localhost:5173 (dev) hoặc http://localhost:8000 sau `npm run build`. Kiểm tra: http://localhost:8000/api/health
## Kiểm thử API RAG và cấu trúc ChromaDB
Mở http://localhost:8000/docs để dùng Swagger UI. `POST /api/chat` nhận JSON có `query` (bắt buộc), `year` (năm phiên bản tài liệu, tùy chọn), `top_k` và `min_score`. Để chỉ tìm tài liệu phiên bản 2026:
```json
{
  "query": "Điều kiện xét tuyển năm 2026 là gì?",
  "year": 2026
}
```
Phản hồi thành công `200 OK` có `answer`, `sources` (mỗi nguồn gồm `doc_title`, `section`, `date`, `url`, `score`), `retrieved_chunks` và `latency`. `year` lọc metadata `version` trong collection `tuyensinh`; không truyền `year` để tìm trên tất cả tài liệu hiện hành.

ChromaDB lưu một vector embedding cho mỗi đoạn văn bản. ID đoạn có dạng `<tên-file>::<số-đoạn>`; metadata gồm `doc_title`, `source`, `official_url`, `version`, `date`, `effective_date`, `section`, `page` và `superseded`. Truy xuất mặc định loại tài liệu cũ bằng `superseded = 0`.
Trợ lý chỉ trả lời trong phạm vi thông tin tuyển sinh có trong tài liệu; nếu chỉ nhập một chủ đề chưa rõ ý, trợ lý sẽ hỏi lại khía cạnh cần tra cứu thay vì đưa lời chào chung chung.
## Đánh giá
`eval/test_set.jsonl` có 54 ca kiểm thử với trang nguồn: 50 câu trong phạm vi, 2 câu ngoài phạm vi và 2 câu chưa có dữ liệu. Chạy retrieval không cần API key bằng `python -m eval.run_eval --retrieval-only`; kết quả được lưu riêng ở `eval/results/retrieval_report.md` và `retrieval_report.csv`, không ghi đè kết quả generation. Một so sánh reranking trực tiếp trên 54 ca cho profile BM25 60% + dense similarity 40% với các từ hỏi tuyển sinh chung được bỏ khỏi BM25 đạt page-level Recall@1/3/5 là 26.0% / 86.0% / 98.0% và MRR 0.534. Bản hiện tại còn lọc/rerank theo cụm ý định (ví dụ “chỉ tiêu”, “học phí”) và tên ngành khi có đủ căn cứ; phép so sánh trên chưa tính thay đổi này. Các report đã lưu vẫn là kết quả profile cũ và cần chạy lại để cập nhật. Chế độ đầy đủ `python -m eval.run_eval --llm-request-interval 13.2` gọi Gemini API, có thể tiêu thụ quota/credit và lưu checkpoint từng ca. Checkpoint generation hiện là kết quả cũ trên bộ 50 câu: 14 câu dùng reranker BM25 50% / dense 50% và 1 câu dùng profile hiện tại; không gộp chúng để kết luận chất lượng cấu hình hiện tại. Để đánh giá lại bộ 54 câu, chạy lượt mới **không** có `--resume`. Nếu lượt mới chạm quota sau khi đã lưu ít nhất một ca, tiếp tục checkpoint của chính lượt đó bằng `python -m eval.run_eval --resume --llm-request-interval 13.2`; không resume checkpoint cũ khác profile. Kết quả cũ được sao lưu tự động trước khi bắt đầu lượt mới. Câu trả lời, dẫn nguồn và hallucination vẫn cần chấm thủ công. STT/TTS chưa nằm trong bộ đánh giá RAG.
- `eval/user_survey_template.csv` là mẫu trống; cần thu thập 15–30 phản hồi thật, không điền phản hồi giả.
- `eval/speech_test_template.csv` là mẫu ghi phép thử STT/TTS bằng audio thật có sự đồng ý. Chỉ dùng mã mẫu ẩn danh; không commit audio hoặc dữ liệu định danh. WER trong mẫu là WER theo token cách nhau bằng dấu cách, vì vậy không đồng nhất hoàn toàn với WER có tách từ tiếng Việt.
- Trong khảo sát, dùng thang 1–5 (1 = rất không đồng ý/kém, 5 = rất đồng ý/tốt); mã người trả lời chỉ là mã ẩn danh. Trong `eval/results/report.csv`, có thể chấm thủ công các cột `manual_content_correct`, `manual_citation_correct`, `manual_complete`, `manual_hallucination` bằng `yes`/`no`. Cột `automatic_key_facts_match` chỉ kiểm tra số/mã khớp chính xác với đáp án tham chiếu; đây là heuristic, không thay thế đánh giá ngữ nghĩa.
- `data/catalog.csv` ghi metadata, vị trí bản lưu, URL chính thức và tình trạng xác minh. Đã xác minh URL tải PDF tuyển sinh 2025 và tải thêm thông báo ngưỡng đầu vào 2026 từ trang UIT chính thức. URL tải trực tiếp của PDF tuyển sinh 2026 và điều khoản tái sử dụng của tài liệu vẫn chưa được xác minh.
## Ghi chú
- Log độ trễ + chi phí, không ghi nội dung câu hỏi: `logs/latency.jsonl`. Các file log cũ có thể vẫn chứa câu hỏi và cần được quản lý/xóa theo chính sách lưu trữ của bạn.
- TTS câu trả lời dùng endpoint `/api/tts` (Edge TTS, có cache trong bộ nhớ) và đồng bộ khẩu hình từ mốc từ; nếu endpoint lỗi, giao diện dự phòng sang Web Speech API. STT vẫn dùng Web Speech API của trình duyệt; endpoint `/api/stt` là tùy chọn và chưa được giao diện gọi. Đề cương chốt Google Cloud TTS, hiện chưa được tích hợp.
- Nhân vật VRM được tải từ `frontend/Model.vrm`, đồng bộ viseme qua các expression `aa`, `ee`, `ih`, `oh`, `ou`; nếu tải lỗi thì giao diện báo trạng thái và dùng nhân vật Three.js dự phòng. Model ghi tác giả `superlit` và yêu cầu ghi công theo metadata VRM.
- Tải tài liệu trong giao diện chỉ tạo chỉ mục cục bộ trong phiên; để cập nhật dữ liệu dùng chung trên máy chủ, hãy đưa tệp vào `data/raw/` và chạy lại pipeline nạp dữ liệu. Pipeline chia đoạn theo tokenizer BAAI/bge-m3, mục tiêu 700 token và overlap 100 token.
- Trạng thái Git hiện tại có thể phản ánh việc chuyển dự án từ `Pro/` lên thư mục gốc. Kiểm tra `git status` và xác nhận việc di chuyển trước khi stage hoặc commit; không khôi phục/xóa các đường dẫn này nếu chưa xác nhận.
