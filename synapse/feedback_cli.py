"""CLI for import and local descriptive release reports."""
from __future__ import annotations

import argparse
import json

from .feedback import FeedbackStore


def main() -> int:
    parser = argparse.ArgumentParser(prog="synapse-feedback")
    sub = parser.add_subparsers(dest="command", required=True)

    import_cmd = sub.add_parser("import", help="Import a CSV of authorized observed metrics")
    import_cmd.add_argument("csv")
    import_cmd.add_argument("--db", default="database/viral_feedback.db")

    report_cmd = sub.add_parser("report", help="Write descriptive platform aggregates")
    report_cmd.add_argument("--db", default="database/viral_feedback.db")
    report_cmd.add_argument("--out", default="reports/deep-insights.json")

    args = parser.parse_args()
    store = FeedbackStore(args.db)
    try:
        if args.command == "import":
            print(json.dumps({"imported": store.import_csv(args.csv)}, indent=2))
        else:
            report = store.deep_insights()
            from pathlib import Path
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(report, indent=2, ensure_ascii=False))
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
