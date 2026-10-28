# Báo cáo đánh giá

## Retrieval-only (bộ hiện tại: 54 câu)

- Retrieval profile: `hybrid_bm25_60_dense_40`.
- Recall@1 / Recall@3 / Recall@5: 24.0% / 72.0% / 94.0%; MRR: 0.494.
- Latency retrieval-only mean / median / P95: 117.2 / 112.3 / 142.6 ms (latest run).
- Có 47/50 câu trong phạm vi tìm thấy trang nguồn trong top 5; cả 4 câu hỏi mới về ngưỡng đầu vào UIT 2026 đều có nguồn trong top 5.
- Chi tiết kết quả: [retrieval_report.md](./retrieval_report.md). Chế độ này không gọi LLM nên không đo chất lượng câu trả lời, tỷ lệ từ chối, chi phí, STT hoặc TTS.

## Gemini generation (checkpoint cũ, chưa đủ đánh giá)

- Checkpoint hiện lưu 15 câu có câu trả lời trong bộ 50 câu trước khi mở rộng: 14 câu dùng profile cũ `hybrid_bm25_50_dense_50`, 1 câu dùng profile hiện tại `hybrid_bm25_60_dense_40`. Đây là các profile khác nhau và bộ câu hỏi cũ không đại diện cho toàn bộ 54 câu hiện tại.
- Heuristic so khớp số/mã khớp 8/14 câu ở profile cũ và 0/1 ở profile hiện tại. Đây không phải chấm điểm ngữ nghĩa, độ đầy đủ, dẫn nguồn hoặc hallucination.
- Chưa có ca từ chối nào được xử lý trong 15 câu hoàn tất (0/4 ca cần từ chối); chưa thể báo cáo tỷ lệ từ chối đúng.
- Token usage chỉ có cho 1/15 câu: input 2,019, output 23. Token usage của 14 câu còn lại và chi phí chưa biết.
- Độ trễ trong checkpoint generation pha trộn 2 profile, có cold-start ngoại lệ và không dùng làm kết quả retrieval chính. STT/TTS chưa được đo.
- Lần chạy trước bị giới hạn quota Gemini free-tier; thông báo khi đó đề nghị đợi khoảng 45 phút, nhưng quota hiện tại cần kiểm tra lại.
- Để đánh giá bộ 54 câu với cấu hình hiện tại, bắt đầu lượt generation mới **không** có `--resume`. Nếu lượt mới đã ghi checkpoint rồi chạm quota, tiếp tục chính lượt đó bằng `python -m eval.run_eval --resume --llm-request-interval 13.2`. Không resume checkpoint cũ vì khác profile và khác bộ câu hỏi.
- Chưa có người đánh giá chấm chất lượng nội dung, citation và hallucination. Không suy diễn kết quả người dùng hoặc tạo dữ liệu đánh giá giả.
