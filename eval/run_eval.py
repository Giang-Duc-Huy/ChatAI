"""Chạy: python -m eval.run_eval (từ thư mục gốc project, sau khi chạy ingest)."""
import sys, json, csv, math, statistics, time, argparse
import re
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.rag.retriever import RETRIEVAL_PROFILE, retrieve
from app.rag.generator import generate
from google.genai.errors import ClientError

def percentile(values, p):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p * len(ordered)) - 1)]

def latency_summary(values):
    return {"mean": statistics.mean(values), "median": statistics.median(values),
            "p95": percentile(values, 0.95)}

def key_fact_match(answer, reference):
    pattern = r"(?<![\w.])\d+(?:[.,]\d+)?[A-Za-z]{0,3}(?!\w)"
    expected = re.findall(pattern, reference)
    if not expected:
        return ""
    actual = {value.casefold() for value in re.findall(pattern, answer)}
    return all(value.casefold() in actual for value in expected)

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Đánh giá retrieval và sinh câu trả lời RAG.")
    parser.add_argument("--retrieval-only", action="store_true",
                        help="Chỉ đo retrieval, không gọi LLM/API.")
    parser.add_argument("--latency-repeats", type=int, default=1,
                        help="Số lượt retrieval trên mỗi câu để đo độ trễ (mặc định 1).")
    parser.add_argument("--llm-request-interval", type=float, default=0,
                        help="Khoảng cách tối thiểu giữa các request LLM, tính bằng giây.")
    parser.add_argument("--resume", action="store_true",
                        help="Tiếp tục các ca chưa có câu trả lời trong report.csv.")
    args = parser.parse_args()
    if args.latency_repeats < 1:
        raise ValueError("--latency-repeats phải >= 1.")
    if args.llm_request_interval < 0:
        raise ValueError("--llm-request-interval phải >= 0.")
    if args.retrieval_only and args.resume:
        raise ValueError("--resume chỉ dùng cho đánh giá có gọi LLM.")

    test_path = Path(__file__).parent / "test_set.jsonl"
    rows = [json.loads(l) for l in test_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        raise ValueError(f"Không có ca đánh giá nào trong {test_path}.")
    for row in rows:
        if not row.get("id") or not row.get("question") or not row.get("reference_answer"):
            raise ValueError(f"Ca đánh giá thiếu id, question hoặc reference_answer: {row}")
        if row.get("type") not in ("ngoai_pham_vi", "khong_co_du_lieu") and not row.get("source_doc"):
            raise ValueError(f"Ca trong phạm vi phải khai báo source_doc: {row['id']}")

    res, ranks, n_in = [], [], 0
    out = Path(__file__).parent / "results"
    out.mkdir(exist_ok=True)
    report_csv = out / ("retrieval_report.csv" if args.retrieval_only else "report.csv")
    report_md = out / ("retrieval_report.md" if args.retrieval_only else "report.md")
    completed = {}
    if report_csv.exists() and not args.retrieval_only:
        with report_csv.open(encoding="utf-8-sig", newline="") as f:
            previous_rows = list(csv.DictReader(f))
        previous_answers = [item for item in previous_rows if item.get("answer")]
        if args.resume:
            stale = [
                item for item in previous_answers
                if item.get("retrieval_profile") != RETRIEVAL_PROFILE
            ]
            if stale:
                raise ValueError(
                    "Checkpoint dùng retrieval profile khác hoặc chưa được gắn profile. "
                    "Chạy lại không có --resume; checkpoint cũ sẽ được lưu riêng."
                )
            for item in previous_answers:
                if item.get("answer"):
                    for key in ("retrieved_ok", "refused", "expected_refusal", "correct_refusal"):
                        if item.get(key) != "":
                            item[key] = item[key] in ("True", "true", "1")
                    item.setdefault("input_tokens", "")
                    item.setdefault("output_tokens", "")
                    item.setdefault("manual_content_correct", "")
                    item.setdefault("manual_citation_correct", "")
                    item.setdefault("manual_complete", "")
                    item.setdefault("manual_hallucination", "")
                    item["automatic_key_facts_match"] = key_fact_match(
                        item.get("answer", ""), item.get("reference", "")
                    )
                    completed[item["id"]] = item
        elif previous_answers:
            backup = out / f"report_previous_retrieval_{time.strftime('%Y%m%d_%H%M%S')}.csv"
            shutil.copy2(report_csv, backup)
    retrieve(rows[0]["question"], k=5)
    latency = {"retrieval": [], "llm": [], "total": []}
    last_llm_call = None
    api_error = None
    for r in rows:
        if r["id"] in completed:
            item = completed[r["id"]]
            res.append(item)
            if r.get("type") not in ("ngoai_pham_vi", "khong_co_du_lieu"):
                n_in += 1
                ranks.append(int(item["retrieval_rank"]) if item["retrieval_rank"] else None)
            latency["retrieval"].append(float(item["retrieval_ms"]))
            latency["llm"].append(float(item["llm_ms"]))
            latency["total"].append(float(item["total_ms"]))
            continue
        retrieval_started = time.perf_counter()
        chunks, ok = retrieve(r["question"], k=5)
        retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
        if args.retrieval_only:
            ans, cost, llm_ms = "", {"usd": 0.0}, 0.0
        else:
            if ok and last_llm_call is not None and args.llm_request_interval:
                delay = args.llm_request_interval - (time.perf_counter() - last_llm_call)
                if delay > 0:
                    time.sleep(delay)
            llm_started = time.perf_counter()
            try:
                ans, cost = generate(r["question"], chunks, ok)
            except ClientError as exc:
                if exc.code != 429:
                    raise
                api_error = (
                    "Gemini free-tier quota (HTTP 429); retry after the quota resets."
                )
                print(f"Gemini quota limit reached; saved completed cases to {report_csv}.")
                break
            llm_ms = (time.perf_counter() - llm_started) * 1000
            if ok:
                last_llm_call = time.perf_counter()
        total_ms = retrieval_ms + llm_ms
        oos = r.get("type") == "ngoai_pham_vi"
        expected_refusal = r.get("type") in ("ngoai_pham_vi", "khong_co_du_lieu")
        answerable = not expected_refusal
        matching = [
            c for c in chunks
            if r.get("source_doc") and r["source_doc"] in c["doc_title"]
            and (not r.get("source_page") or c.get("page") == r["source_page"])
            and (not r.get("source_section") or r["source_section"] in c["section"])
        ]
        rank = next((i + 1 for i, c in enumerate(chunks)
                     if r.get("source_doc") and r["source_doc"] in c["doc_title"]
                     and (not r.get("source_page") or c.get("page") == r["source_page"])
                     and (not r.get("source_section") or r["source_section"] in c["section"])), None)
        if answerable:
            n_in += 1
            ranks.append(rank)
        latency["retrieval"].append(retrieval_ms)
        latency["llm"].append(llm_ms)
        latency["total"].append(total_ms)
        refused = "" if args.retrieval_only else not ok
        res.append({"id": r["id"], "type": r.get("type"), "retrieved_ok": answerable and bool(matching),
                    "retrieved_sections": " | ".join(dict.fromkeys(c["section"] for c in matching)),
                    "retrieval_rank": rank or "",
                    "refused": refused,
                    "expected_refusal": expected_refusal,
                    "correct_refusal": "" if args.retrieval_only else refused == expected_refusal,
                    "retrieval_ms": round(retrieval_ms, 1), "llm_ms": round(llm_ms, 1),
                    "total_ms": round(total_ms, 1),
                    "answer": ans, "reference": r["reference_answer"],
                    "input_tokens": cost.get("in", 0), "output_tokens": cost.get("out", 0),
                    "retrieval_profile": RETRIEVAL_PROFILE,
                    "usd": "" if args.retrieval_only else cost["usd"],
                    "manual_content_correct": "", "manual_citation_correct": "",
                    "manual_complete": "", "manual_hallucination": "",
                    "automatic_key_facts_match": (
                        "" if args.retrieval_only else key_fact_match(
                            ans, r["reference_answer"]
                        )
                    )})
        with report_csv.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, list(res[0])); w.writeheader(); w.writerows(res)
    if args.retrieval_only and args.latency_repeats > 1:
        for _ in range(args.latency_repeats - 1):
            for row in rows:
                started = time.perf_counter()
                retrieve(row["question"], k=5)
                elapsed = (time.perf_counter() - started) * 1000
                latency["retrieval"].append(elapsed)
                latency["total"].append(elapsed)

    refusal_rows = [x for x in res if x["expected_refusal"]]
    expected_refusal_count = sum(
        row.get("type") in ("ngoai_pham_vi", "khong_co_du_lieu") for row in rows
    )
    recalls = {
        k: sum(rank is not None and rank <= k for rank in ranks) / max(1, n_in)
        for k in (1, 3, 5)
    }
    mrr = sum(1 / rank for rank in ranks if rank is not None) / max(1, n_in)
    stages = ("retrieval", "total") if args.retrieval_only else ("retrieval", "llm", "total")
    latency_report = {
        name: latency_summary(latency[name]) if latency[name] else None
        for name in stages
    }
    md = [f"# Báo cáo đánh giá ({len(rows)} câu)",
          f"- Retrieval profile: `{RETRIEVAL_PROFILE}`.",
          f"- Recall@1 / Recall@3 / Recall@5: {recalls[1]:.1%} / {recalls[3]:.1%} / {recalls[5]:.1%}",
          f"- MRR: {mrr:.3f}"]
    if args.retrieval_only:
        md.append("- Tỷ lệ từ chối, chi phí và chất lượng câu trả lời: chưa đo (không gọi LLM).")
    else:
        known_costs = [float(x["usd"]) for x in res if x.get("usd") not in ("", None)]
        token_rows = [x for x in res if x.get("input_tokens") not in ("", None)
                      and x.get("output_tokens") not in ("", None)]
        key_fact_rows = [x for x in res if x.get("automatic_key_facts_match") not in ("", None)]
        md.extend([
          f"- Ca đã hoàn thành: {len(res)}/{len(rows)}; "
          f"ca cần từ chối đã xử lý: {len(refusal_rows)}/{expected_refusal_count}; "
          f"đúng trong số đã xử lý: "
          f"{sum(x['correct_refusal'] for x in refusal_rows)}/{len(refusal_rows)}",
          f"- Token ghi nhận ở {len(token_rows)}/{len(res)} ca: "
          f"input {sum(int(x['input_tokens']) for x in token_rows):,}, "
          f"output {sum(int(x['output_tokens']) for x in token_rows):,}.",
          (f"- Khớp chính xác các số/mã trong đáp án tham chiếu (heuristic, không thay thế chấm ngữ nghĩa): "
           f"{sum(x['automatic_key_facts_match'] is True or x['automatic_key_facts_match'] == 'True' for x in key_fact_rows)}"
           f"/{len(key_fact_rows)} ca có số/mã.")
          if key_fact_rows else "- Chưa có ca đủ số liệu để kiểm tra khớp số/mã tự động.",
          (f"- Chi phí TB/lượt (ước tính): ${statistics.mean(known_costs):.5f}"
           if known_costs else "- Chi phí chưa ước tính (chưa cấu hình đơn giá Gemini).")])
    md.extend([
          f"- Số lượt đo retrieval: {len(latency['retrieval'])} "
          f"(cần tối thiểu 30 lượt để báo cáo theo đề cương)."])
    for stage, stats in latency_report.items():
        if stats is not None:
            md.append(f"- {stage} (ms), mean / median / P95: "
                      f"{stats['mean']:.1f} / {stats['median']:.1f} / {stats['p95']:.1f}")
        else:
            md.append(f"- {stage}: chưa có lượt đo.")
    if args.retrieval_only:
        md.append("- Chế độ retrieval-only: không gọi LLM; chưa có số đo generation, STT hoặc TTS.")
    else:
        md.append("- Độ đúng nội dung, dẫn nguồn và hallucination cần được chấm thủ công; "
                  "STT/TTS không được gọi trong bộ đánh giá RAG này.")
    md.append("- Retrieval được khởi động trước khi đo để không tính thời gian nạp model vào từng câu.")
    if api_error:
        md.append(f"- Đánh giá LLM chưa hoàn tất do giới hạn quota Gemini: {api_error}")
    report_md.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))

if __name__ == "__main__":
    main()
