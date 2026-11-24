"""CLI to export or inspect the creative-evidence profile."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .viral_evidence import evidence_manifest, write_evidence


def main() -> int:
    parser = argparse.ArgumentParser(prog="synapse-evidence")
    parser.add_argument("--out", type=Path, help="optional JSON export path")
    args = parser.parse_args()
    if args.out:
        print(write_evidence(args.out))
    else:
        print(json.dumps(evidence_manifest(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
