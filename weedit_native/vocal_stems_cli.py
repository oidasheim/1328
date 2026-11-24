"""CLI to create/reuse local vocal stem artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .vocal_stems import separate_vocal_stem


def main() -> int:
    parser = argparse.ArgumentParser(prog="weedit-separate-vocals")
    parser.add_argument("audio", type=Path)
    parser.add_argument("--cache", type=Path, default=Path("cache/stems"))
    parser.add_argument("--method", choices=("auto", "roformer", "demucs", "fallback"), default="auto")
    parser.add_argument("--allow-model-download", action="store_true",
                        help="explicitly allow installed model separators to load/download weights")
    args = parser.parse_args()
    try:
        result = separate_vocal_stem(args.audio, args.cache, method=args.method,
                                     allow_model_download=args.allow_model_download)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"stem separation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
