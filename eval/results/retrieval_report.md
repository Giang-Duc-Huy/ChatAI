# Báo cáo đánh giá (54 câu)
- Retrieval profile: `hybrid_bm25_60_dense_40`.
- Recall@1 / Recall@3 / Recall@5: 24.0% / 72.0% / 94.0%
- MRR: 0.494
- Tỷ lệ từ chối, chi phí và chất lượng câu trả lời: chưa đo (không gọi LLM).
- Số lượt đo retrieval: 54 (cần tối thiểu 30 lượt để báo cáo theo đề cương).
- retrieval (ms), mean / median / P95: 117.2 / 112.3 / 142.6
- total (ms), mean / median / P95: 117.2 / 112.3 / 142.6
- Chế độ retrieval-only: không gọi LLM; chưa có số đo generation, STT hoặc TTS.
- Retrieval được khởi động trước khi đo để không tính thời gian nạp model vào từng câu.