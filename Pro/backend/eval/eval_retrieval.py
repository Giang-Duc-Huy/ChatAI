from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.retriever import retriever_service


def load_testset(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def mrr_at(ranked_doc_ids: list[str], gold: list[str]) -> float:
    gold_set = set(gold)
    for i, d in enumerate(ranked_doc_ids, start=1):
        if d in gold_set:
            return 1.0 / i
    return 0.0


def recall_at(ranked_doc_ids: list[str], gold: list[str], k: int) -> float:
    if not gold:
        return 1.0 if not ranked_doc_ids else 1.0
    hit = len(set(ranked_doc_ids[:k]) & set(gold))
    return hit / len(set(gold))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--testset", default=str(BACKEND_ROOT / "eval" / "testset.jsonl"))
    parser.add_argument("--out", default=str(BACKEND_ROOT / "eval" / "retrieval_report.csv"))
    args = parser.parse_args()

    data = load_testset(Path(args.testset))
    rows_out = []
    metrics = defaultdict(lambda: {"n": 0, "r1": 0.0, "r3": 0.0, "r5": 0.0, "mrr": 0.0})

    for item in data:
        if not item.get("answerable", True):
            # Skip unanswerable for retrieval gold when no docs; still record empty retrieval
            gold = item.get("gold_doc_ids") or []
        else:
            gold = item.get("gold_doc_ids") or []

        chunks = retriever_service.retrieve(item["question"], top_k=5)
        ranked = []
        for c in chunks:
            if c.doc_id not in ranked:
                ranked.append(c.doc_id)

        r1, r3, r5 = recall_at(ranked, gold, 1), recall_at(ranked, gold, 3), recall_at(ranked, gold, 5)
        mrr = mrr_at(ranked, gold)
        cat = item.get("category") or "all"
        for key in (cat, "all"):
            m = metrics[key]
            m["n"] += 1
            m["r1"] += r1
            m["r3"] += r3
            m["r5"] += r5
            m["mrr"] += mrr

        rows_out.append(
            {
                "id": item["id"],
                "category": cat,
                "recall@1": round(r1, 3),
                "recall@3": round(r3, 3),
                "recall@5": round(r5, 3),
                "mrr": round(mrr, 3),
                "retrieved": "|".join(ranked),
            }
        )

    out = Path(args.out)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()) if rows_out else ["id"])
        w.writeheader()
        w.writerows(rows_out)

    print("=== Retrieval summary ===")
    for cat, m in sorted(metrics.items()):
        n = max(m["n"], 1)
        print(
            f"{cat}: n={m['n']} Recall@1={m['r1']/n:.3f} "
            f"Recall@3={m['r3']/n:.3f} Recall@5={m['r5']/n:.3f} MRR={m['mrr']/n:.3f}"
        )
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
