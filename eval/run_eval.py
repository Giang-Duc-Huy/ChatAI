"""Chạy: python -m eval.run_eval  (từ thư mục gốc project, sau khi chạy ingest)
test_set.jsonl: {id, question, reference_answer, source_doc, source_section, type}"""
import sys, json, csv, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.rag.retriever import retrieve
from app.rag.generator import generate

def main():
    test_path = Path(__file__).parent / "test_set.jsonl"
    rows = [json.loads(l) for l in test_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        raise ValueError(f"Không có ca đánh giá nào trong {test_path}.")
    for row in rows:
        if not row.get("id") or not row.get("question") or not row.get("reference_answer"):
            raise ValueError(f"Ca đánh giá thiếu id, question hoặc reference_answer: {row}")
        if row.get("type") != "ngoai_pham_vi" and not row.get("source_doc"):
            raise ValueError(f"Ca trong phạm vi phải khai báo source_doc: {row['id']}")

    res, hit, n_in = [], 0, 0
    for r in rows:
        chunks, ok = retrieve(r["question"])
        ans, cost = generate(r["question"], chunks, ok)
        oos = r.get("type") == "ngoai_pham_vi"
        matching = [
            c for c in chunks
            if r["source_doc"] in c["doc_title"]
            and (not r.get("source_section") or r["source_section"] in c["section"])
        ]
        found = (not oos) and bool(matching)
        hit += found; n_in += (not oos)
        res.append({"id": r["id"], "type": r.get("type"), "retrieved_ok": found,
                    "retrieved_sections": " | ".join(dict.fromkeys(c["section"] for c in matching)),
                    "refused": not ok,
                    "answer": ans, "reference": r["reference_answer"], "usd": cost["usd"]})
    out = Path(__file__).parent / "results"; out.mkdir(exist_ok=True)
    with open(out / "report.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, list(res[0])); w.writeheader(); w.writerows(res)
    oos_rows = [x for x in res if x["type"] == "ngoai_pham_vi"]
    md = [f"# Báo cáo đánh giá ({len(rows)} câu)",
          f"- Recall@k: {hit / max(1, n_in):.1%}",
          f"- Từ chối đúng câu ngoài phạm vi: {sum(x['refused'] for x in oos_rows)}/{len(oos_rows)}",
          f"- Chi phí TB/lượt: ${statistics.mean(x['usd'] for x in res):.5f}",
          "- Độ đúng nội dung / dẫn nguồn / hallucination: chấm bằng LLM + kiểm tay ~20% (xem report.csv)"]
    (out / "report.md").write_text("\n".join(md), encoding="utf-8"); print("\n".join(md))

if __name__ == "__main__":
    main()
