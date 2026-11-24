"""WE.ED.IT OIDA music-video compiler command line."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

from .genome import GenomeDB, scan_directory
from .models import RenderAST
from .pipeline import compile_project, write_ast
from .renderer import FFmpegBackend
from .report import write_report
from .styles import BUILTIN_STYLES, install_style
from .passes import run_pass_pipeline


def _doctor(deep: bool = False) -> dict[str, object]:
    checks: dict[str, object] = {"python": sys.version.split()[0],
                                 "executable": sys.executable,
                                 "ffmpeg": shutil.which("ffmpeg") or "missing",
                                 "ffprobe": shutil.which("ffprobe") or "missing"}
    for package in ("numpy", "librosa", "cv2", "torch", "duckdb", "pytest"):
        try:
            module = __import__(package)
            checks[package] = getattr(module, "__version__", "available")
        except ImportError:
            checks[package] = "optional / not installed"
    if deep and checks["ffmpeg"] != "missing":
        probe = subprocess.run([str(checks["ffmpeg"]), "-hide_banner", "-encoders"],
                               capture_output=True, text=True, check=False)
        checks["nvenc"] = "h264_nvenc" in (probe.stdout + probe.stderr)
        checks["libx264"] = "libx264" in (probe.stdout + probe.stderr)
    return checks


def _verify(db_path: Path) -> dict[str, object]:
    checks: dict[str, object] = {"status": "pass", "checks": {}}
    modules = ("weedit_native.models", "weedit_native.genome", "weedit_native.pipeline",
               "weedit_native.renderer", "weedit_native.passes", "weedit_native.replay")
    checks["checks"]["modules"] = {name: __import__(name) is not None for name in modules}
    checks["checks"]["styles"] = sorted(BUILTIN_STYLES)
    if db_path.exists():
        con = sqlite3.connect(db_path)
        try:
            integrity = con.execute("PRAGMA quick_check").fetchone()[0]
            checks["checks"]["database_integrity"] = integrity
            checks["checks"]["clip_count"] = con.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
            if integrity != "ok":
                checks["status"] = "fail"
        finally:
            con.close()
    else:
        checks["checks"]["database_integrity"] = "not initialized"
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(prog="weed", description="WE.ED.IT OIDA music-video compiler")
    subs = parser.add_subparsers(dest="command", required=True)
    scan = subs.add_parser("scan", help="Index clip metadata into the genome database")
    scan.add_argument("clips", type=Path)
    scan.add_argument("--db", type=Path, default=Path("database/genome.sqlite3"))

    compile_cmd = subs.add_parser("compile", help="Compile audio and clip genome to RenderAST JSON")
    compile_cmd.add_argument("song", type=Path); compile_cmd.add_argument("clips", type=Path)
    compile_cmd.add_argument("--db", type=Path, default=Path("database/genome.sqlite3"))
    compile_cmd.add_argument("--out", type=Path, default=Path("reports/render_ast.json"))
    compile_cmd.add_argument("--width", type=int, default=1920); compile_cmd.add_argument("--height", type=int, default=1080); compile_cmd.add_argument("--fps", type=int, default=30)

    render = subs.add_parser("render", help="Render a previously compiled RenderAST")
    render.add_argument("ast", type=Path); render.add_argument("--out", type=Path, required=True); render.add_argument("--cpu", action="store_true")
    make = subs.add_parser("make", help="Scan (if needed), compile and optionally render")
    make.add_argument("song", type=Path); make.add_argument("clips", type=Path)
    make.add_argument("--db", type=Path, default=Path("database/genome.sqlite3"))
    make.add_argument("--ast", type=Path, default=Path("reports/render_ast.json")); make.add_argument("--out", type=Path)
    make.add_argument("--width", type=int, default=1920); make.add_argument("--height", type=int, default=1080); make.add_argument("--fps", type=int, default=30)

    doctor = subs.add_parser("doctor", help="Check Python, FFmpeg and optional dependencies")
    doctor.add_argument("--deep", action="store_true")
    verify = subs.add_parser("verify", help="Verify imports, style packages and local DB integrity")
    verify.add_argument("--db", type=Path, default=Path("database/genome.sqlite3"))
    toolchain = subs.add_parser("toolchain", help="Show available local media encoders")
    toolchain.add_argument("--json", action="store_true")
    benchmark = subs.add_parser("benchmark", help="Measure local SQLite read latency (not a hardware claim)")
    benchmark.add_argument("--db", type=Path, default=Path("database/genome.sqlite3")); benchmark.add_argument("--iterations", type=int, default=1000)
    styles = subs.add_parser("style", help="List or install built-in deterministic style packages")
    styles.add_argument("action", choices=("list", "install")); styles.add_argument("name", nargs="?"); styles.add_argument("--root", type=Path, default=Path("."))
    report = subs.add_parser("report", help="Write HTML and JSON report from a RenderAST")
    report.add_argument("ast", type=Path); report.add_argument("--out", type=Path, default=Path("reports/render_report.html"))
    replay = subs.add_parser("replay", help="Inspect a persisted shot decision")
    replay.add_argument("shot_id"); replay.add_argument("--db", type=Path, default=Path("database/replay.sqlite3"))
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
            print(f"Scan: {scan_directory(args.clips, args.db)}")
        ast = compile_project(args.song, args.clips, args.db, width=args.width, height=args.height, fps=args.fps)
        write_ast(ast, args.ast)
        print(f"Compiled {len(ast.shots)} shots → {args.ast}")
        if args.out:
            print(f"Rendered {FFmpegBackend().render(ast, args.out)}")
        return 0
    if args.command == "doctor":
        checks = _doctor(args.deep)
        print(json.dumps(checks, indent=2))
        return 0 if checks["ffmpeg"] != "missing" else 1
    if args.command == "verify":
        result = _verify(args.db)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1
    if args.command == "toolchain":
        checks = _doctor(True)
        print(json.dumps(checks, indent=2))
        return 0 if checks["ffmpeg"] != "missing" else 1
    if args.command == "benchmark":
        if args.iterations < 1:
            parser.error("--iterations must be positive")
        args.db.parent.mkdir(parents=True, exist_ok=True)
        genome = GenomeDB(args.db)
        try:
            started = time.perf_counter()
            for _ in range(args.iterations):
                genome.db.execute("SELECT COUNT(*) FROM clips").fetchone()
            elapsed = time.perf_counter() - started
        finally:
            genome.close()
        print(json.dumps({"benchmark": "sqlite_count_roundtrip", "iterations": args.iterations,
                          "elapsed_seconds": elapsed, "microseconds_per_query": elapsed * 1e6 / args.iterations,
                          "claim": "local measurement; not a vector-scoring benchmark"}, indent=2))
        return 0
    if args.command == "style":
        if args.action == "list":
            print(json.dumps(sorted(BUILTIN_STYLES), indent=2)); return 0
        if not args.name:
            parser.error("style install requires a name")
        print(install_style(args.root, args.name)); return 0
    if args.command == "report":
        ast = RenderAST.from_dict(json.loads(args.ast.read_text(encoding="utf-8")))
        print(write_report(ast, args.out)); return 0
    if args.command == "replay":
        from .replay import ReplayLedger
        ledger = ReplayLedger(args.db)
        try:
            result = ledger.replay(args.shot_id)
        finally:
            ledger.close()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result is not None else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
