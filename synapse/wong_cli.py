"""Evaluate forecast CSV records with proper scoring and calibration summaries.

Expected CSV columns: probability,outcome,agent,source. Outcome is 0 or 1.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from .wong import brier_score, calibration_bins


def evaluate_csv(path: Path, bins: int = 10) -> dict:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("CSV contains no forecast rows")
    probabilities = [float(row["probability"]) for row in rows]
    outcomes = [int(row["outcome"]) for row in rows]
    result = {
        "count": len(rows),
        "brier_score": brier_score(probabilities, outcomes),
        "reliability_curve": calibration_bins(probabilities, outcomes, bins),
        "leaderboards": {},
        "warning": "Small samples and selective labels can make rankings unstable.",
    }
    for column in ("agent", "source"):
        groups = defaultdict(list)
        for row in rows:
            if row.get(column):
                groups[row[column]].append(row)
        result["leaderboards"][column] = [
            {"name": name,
             "count": len(group),
             "brier_score": brier_score([float(r["probability"]) for r in group],
                                         [int(r["outcome"]) for r in group])}
            for name, group in sorted(groups.items())
        ]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--bins", type=int, default=10)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = evaluate_csv(args.csv, args.bins)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
