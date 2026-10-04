from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.rag import rag_service


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def load_questions(path: Path) -> list[str]:
    qs = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                qs.append(json.loads(line)["question"])
    return qs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--testset", default=str(BACKEND_ROOT / "eval" / "testset.jsonl"))
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--out", default=str(BACKEND_ROOT / "eval" / "latency_report.csv"))
    args = parser.parse_args()

    questions = load_questions(Path(args.testset))
    if not questions:
        raise SystemExit("Empty testset")

    retrievals, llms, totals = [], [], []
    detail_rows = []

    for i in range(args.runs):
        q = questions[i % len(questions)]
        t0 = time.perf_counter()
        resp = rag_service.answer(q)
        wall = (time.perf_counter() - t0) * 1000
        retrievals.append(resp.timings_ms.retrieval)
        llms.append(resp.timings_ms.llm)
        totals.append(resp.timings_ms.total or wall)
        detail_rows.append(
            {
                "run": i + 1,
                "question": q[:80],
                "retrieval_ms": resp.timings_ms.retrieval,
                "llm_ms": resp.timings_ms.llm,
                "total_ms": resp.timings_ms.total,
            }
        )
        print(f"run {i+1}/{args.runs}: total={resp.timings_ms.total:.1f}ms")

    summary = []
    for name, vals in (("retrieval", retrievals), ("llm", llms), ("total", totals)):
        summary.append(
            {
                "stage": name,
                "mean_ms": round(statistics.mean(vals), 2),
                "median_ms": round(statistics.median(vals), 2),
                "p95_ms": round(percentile(vals, 95), 2),
                "n": len(vals),
            }
        )

    out = Path(args.out)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["stage", "mean_ms", "median_ms", "p95_ms", "n"])
        w.writeheader()
        w.writerows(summary)
    detail = out.with_name("latency_detail.csv")
    with detail.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(detail_rows[0].keys()))
        w.writeheader()
        w.writerows(detail_rows)

    print("=== Latency summary ===")
    for row in summary:
        print(row)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
