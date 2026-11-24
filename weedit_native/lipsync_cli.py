"""Small CLI for validating phoneme alignment JSON and matching MAR curves."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

from .lipsync import dtw_lipsync_match, formant_energy_mar, phonemes_to_mar


def main() -> int:
    parser = argparse.ArgumentParser(prog="weedit-lipsync")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_cmd = sub.add_parser("compile", help="Convert supplied aligned phoneme JSON to MAR curve")
    compile_cmd.add_argument("alignments", type=Path, help="JSON array of {start,end,phoneme} records")
    compile_cmd.add_argument("--duration", type=float, required=True)
    compile_cmd.add_argument("--fps", type=int, default=60)
    compile_cmd.add_argument("--out", type=Path, required=True)
    fallback = sub.add_parser("fallback", help="Make an audio formant-energy MAR proxy")
    fallback.add_argument("audio", type=Path); fallback.add_argument("--duration", type=float, required=True)
    fallback.add_argument("--fps", type=int, default=60); fallback.add_argument("--out", type=Path, required=True)
    match = sub.add_parser("match", help="Bounded DTW match of two .npy MAR curves")
    match.add_argument("clip_curve", type=Path); match.add_argument("target_curve", type=Path)
    match.add_argument("--max-offsets", type=int, default=24); match.add_argument("--radius", type=int, default=2)
    args = parser.parse_args()
    try:
        if args.command == "compile":
            alignments = json.loads(args.alignments.read_text(encoding="utf-8"))
            curve = phonemes_to_mar(alignments, args.duration, args.fps)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            np.save(args.out, curve)
            print(json.dumps({"frames": len(curve), "fps": args.fps, "output": str(args.out)}))
        elif args.command == "fallback":
            curve = formant_energy_mar(str(args.audio), args.duration, args.fps)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            np.save(args.out, curve)
            print(json.dumps({"frames": len(curve), "fps": args.fps, "method": "formant-energy-proxy", "output": str(args.out)}))
        else:
            result = dtw_lipsync_match(np.load(args.clip_curve), np.load(args.target_curve),
                                       max_offsets=args.max_offsets, radius=args.radius)
            print(json.dumps(result.__dict__, indent=2))
            return 0 if result.evaluated_offsets else 1
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"lipsync failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
