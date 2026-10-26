# Trợ lý ảo 3D tư vấn tuyển sinh UIT

## Cài đặt (Python 3.11)
```bash
cd backend && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env     # điền ANTHROPIC_API_KEY
```
## Nạp dữ liệu
1. Chép 2 PDF + 1 HTML vào `data/raw/`.
2. `python -m ingest.build_index` (lần đầu tạo `data/catalog.csv`; mở file này điền `issuer, date, version, effective_date`, rồi chạy lại. Các tài liệu cùng cột `group` sẽ giữ bản `effective_date` mới nhất, bản cũ bị `superseded`).
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
## Đánh giá
`eval/test_set.jsonl` có một số ca khói để kiểm tra nhanh, không thay thế bộ đánh giá đầy đủ. Bổ sung câu hỏi, đáp án tham chiếu và tài liệu/mục nguồn đã kiểm chứng trước khi dùng kết quả để điều chỉnh `MIN_SCORE`. Chạy từ thư mục gốc: `python -m eval.run_eval`.
## Ghi chú
- Log độ trễ + chi phí, không ghi nội dung câu hỏi: `logs/latency.jsonl`. Các file log cũ có thể vẫn chứa câu hỏi và cần được quản lý/xóa theo chính sách lưu trữ của bạn.
- Đặt model VRM vào `frontend/public/models/avatar.vrm` (chưa được dùng: hiện nhân vật dựng bằng hình khối).
- Giao diện dùng nhận dạng và tổng hợp giọng nói của trình duyệt; các endpoint `/api/stt`, `/api/tts` hiện chưa được giao diện gọi. Tải tài liệu trong giao diện chỉ tạo chỉ mục cục bộ trong phiên; để cập nhật dữ liệu dùng chung trên máy chủ, hãy đưa tệp vào `data/raw/` và chạy lại pipeline nạp dữ liệu.
- Trạng thái Git hiện tại có thể phản ánh việc chuyển dự án từ `Pro/` lên thư mục gốc. Kiểm tra `git status` và xác nhận việc di chuyển trước khi stage hoặc commit; không khôi phục/xóa các đường dẫn này nếu chưa xác nhận.
