from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.rag import rag_service


def load_testset(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chạy generation và xuất CSV để chấm thủ công (+ cột gợi ý)"
    )
    parser.add_argument("--testset", default=str(BACKEND_ROOT / "eval" / "testset.jsonl"))
    parser.add_argument("--out", default=str(BACKEND_ROOT / "eval" / "generation_report.csv"))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    data = load_testset(Path(args.testset))
    if args.limit:
        data = data[: args.limit]

    rows = []
    for item in data:
        resp = rag_service.answer(item["question"])
        expected_refuse = not item.get("answerable", True)
        auto_refuse_ok = ""
        if expected_refuse:
            auto_refuse_ok = "yes" if not resp.answerable else "no"

        rows.append(
            {
                "id": item["id"],
                "category": item.get("category", ""),
                "question": item["question"],
                "gold_answer": item.get("gold_answer", ""),
                "model_answer": resp.answer,
                "answerable_pred": resp.answerable,
                "answerable_gold": item.get("answerable", True),
                "sources": "|".join(s.doc_id for s in resp.sources),
                "gold_doc_ids": "|".join(item.get("gold_doc_ids") or []),
                # Manual scoring columns (1/0)
                "score_dung_noi_dung": "",
                "score_co_can_cu": "",
                "score_du_thong_tin": "",
                "score_khong_bia": "",
                "score_tu_choi_dung": auto_refuse_ok,
                "retrieval_ms": resp.timings_ms.retrieval,
                "llm_ms": resp.timings_ms.llm,
                "total_ms": resp.timings_ms.total,
            }
        )
        print(f"[{item['id']}] answerable={resp.answerable} total_ms={resp.timings_ms.total}")

    out = Path(args.out)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out} — điền các cột score_* bằng chấm thủ công.")


if __name__ == "__main__":
    main()
