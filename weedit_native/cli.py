"""`weed` command-line entry point."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from .compiler import compile_song
from .genome import scan_directory
from .models import RenderAST
from .pipeline import compile_project, write_ast
from .renderer import FFmpegBackend


def main() -> int:
    parser = argparse.ArgumentParser(prog="weed", description="WE.ED.IT OIDA music-video compiler")
    subs = parser.add_subparsers(dest="command", required=True)
    scan = subs.add_parser("scan", help="Index clip metadata into the genome database")
    scan.add_argument("clips", type=Path); scan.add_argument("--db", type=Path, default=Path("cache/genome.sqlite3"))
    compile_cmd = subs.add_parser("compile", help="Compile audio and clip genome to RenderAST JSON")
    compile_cmd.add_argument("song", type=Path); compile_cmd.add_argument("clips", type=Path)
    compile_cmd.add_argument("--db", type=Path, default=Path("cache/genome.sqlite3")); compile_cmd.add_argument("--out", type=Path, default=Path("reports/render_ast.json"))
    compile_cmd.add_argument("--width", type=int, default=1920); compile_cmd.add_argument("--height", type=int, default=1080); compile_cmd.add_argument("--fps", type=int, default=30)
    render = subs.add_parser("render", help="Render a previously compiled RenderAST")
    render.add_argument("ast", type=Path); render.add_argument("--out", type=Path, required=True); render.add_argument("--cpu", action="store_true")
    make = subs.add_parser("make", help="Scan (if needed), compile and optionally render")
    make.add_argument("song", type=Path); make.add_argument("clips", type=Path); make.add_argument("--db", type=Path, default=Path("cache/genome.sqlite3"))
    make.add_argument("--ast", type=Path, default=Path("reports/render_ast.json")); make.add_argument("--out", type=Path, default=None)
    make.add_argument("--width", type=int, default=1920); make.add_argument("--height", type=int, default=1080); make.add_argument("--fps", type=int, default=30)
    doctor = subs.add_parser("doctor", help="Check required and optional tools")
    doctor.add_argument("--deep", action="store_true")
    args = parser.parse_args()

    if args.command == "scan":
        print(json.dumps(scan_directory(args.clips, args.db), indent=2)); return 0
    if args.command == "compile":
        ast = compile_project(args.song, args.clips, args.db, width=args.width, height=args.height, fps=args.fps)
        print(f"Wrote {write_ast(ast, args.out)} ({len(ast.shots)} shots)"); return 0
    if args.command == "render":
        ast = RenderAST.from_dict(json.loads(args.ast.read_text(encoding="utf-8")))
        print(f"Rendered {FFmpegBackend(prefer_nvenc=not args.cpu).render(ast, args.out)}"); return 0
    if args.command == "make":
        if not args.db.exists():
            result = scan_directory(args.clips, args.db)
            print(f"Scan: {result}")
        ast = compile_project(args.song, args.clips, args.db, width=args.width, height=args.height, fps=args.fps)
        write_ast(ast, args.ast)
        print(f"Compiled {len(ast.shots)} shots → {args.ast}")
        if args.out:
            print(f"Rendered {FFmpegBackend().render(ast, args.out)}")
        return 0
    if args.command == "doctor":
        checks = {"python": sys.version.split()[0], "ffmpeg": shutil.which("ffmpeg") or "missing"}
        for package in ("librosa", "cv2", "numpy", "torch", "duckdb"):
            try:
                module = __import__(package)
                checks[package] = getattr(module, "__version__", "available")
            except ImportError:
                checks[package] = "optional / not installed"
        print(json.dumps(checks, indent=2)); return 0 if checks["ffmpeg"] != "missing" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
