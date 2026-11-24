"""Portable end-to-end music-video build using the repository's existing pipeline.

This is deliberately a CPU/Python control plane. CUDA pointer interop and native
AVX2 bindings are not enabled unless their ABI and kernels are actually present.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any

from .genome import scan_directory
from .models import RenderAST
from .passes import run_pass_pipeline
from .pipeline import compile_project, write_ast
from .renderer import FFmpegBackend
from .report import write_report
from .replay import ReplayLedger, sha256_object


@dataclass(frozen=True)
class BuildConfig:
    song: Path
    clips: Path
    database: Path = Path("database/genome.sqlite3")
    output: Path = Path("output")
    reports: Path = Path("reports")
    width: int = 1080
    height: int = 1920
    fps: int = 30
    render: bool = False
    cpu_only: bool = False
    prefer_nvenc: bool = True

    def validate(self) -> None:
        if self.width <= 0 or self.height <= 0 or self.width % 2 or self.height % 2:
            raise ValueError("width and height must be positive even integers")
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        if self.render and self.output.exists() and self.output.is_dir():
            raise ValueError("output must be a file path when rendering")


@dataclass
class BuildStage:
    name: str
    status: str
    elapsed_seconds: float
    details: dict[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _file_fingerprint(path: Path) -> dict[str, Any]:
    info = path.stat()
    return {"path": str(path.resolve()), "size_bytes": info.st_size,
            "mtime_ns": info.st_mtime_ns}


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _stage(stages: list[BuildStage], name: str, started: float, **details: Any) -> None:
    stages.append(BuildStage(name, "pass", round(time.perf_counter() - started, 4), details))


def run_build(config: BuildConfig) -> dict[str, Any]:
    config.validate()
    song = config.song.expanduser().resolve()
    clips = config.clips.expanduser().resolve()
    database = config.database.expanduser().resolve()
    output = config.output.expanduser().resolve()
    reports = config.reports.expanduser().resolve()
    if not song.is_file():
        raise FileNotFoundError(f"audio source not found: {song}")
    if not clips.is_dir():
        raise FileNotFoundError(f"clip directory not found: {clips}")

    stages: list[BuildStage] = []
    started_at = _now()
    begin = time.perf_counter()
    scan = scan_directory(clips, database)
    _stage(stages, "genome-scan", begin, **scan, database=str(database))

    begin = time.perf_counter()
    ast = compile_project(song, clips, database, width=config.width,
                          height=config.height, fps=config.fps)
    ast, pass_evidence = run_pass_pipeline(ast)
    _stage(stages, "compile-and-optimize", begin,
           shot_count=len(ast.shots), duration=ast.duration,
           pass_count=pass_evidence["pass_count"])

    render_id = sha256_object({"song": _file_fingerprint(song),
                               "config": {"width": config.width, "height": config.height, "fps": config.fps},
                               "ast": ast.to_dict()})[:24]
    ast.metadata.update({"render_id": render_id, "pass_evidence": pass_evidence,
                         "pipeline": "weedit_native.art_director", "started_at": started_at})
    ast_path = reports / f"{song.stem}-{render_id}.ast.json"
    report_path = reports / f"{song.stem}-{render_id}.html"
    manifest_path = reports / f"{song.stem}-{render_id}.manifest.json"

    begin = time.perf_counter()
    write_ast(ast, ast_path)
    write_report(ast, report_path)
    ledger_path = database.parent / "replay.sqlite3"
    ledger = ReplayLedger(ledger_path)
    try:
        input_hash = sha256_object({"song": _file_fingerprint(song), "ast": ast.to_dict()})
        for index, shot in enumerate(ast.shots):
            ledger.record(render_id, f"{render_id}:shot-{index:05d}", shot, [],
                          pass_evidence, input_hash)
    finally:
        ledger.close()
    _stage(stages, "reports-and-replay-ledger", begin, ast=str(ast_path),
           html=str(report_path), ledger=str(ledger_path))

    rendered_path: str | None = None
    if config.render:
        begin = time.perf_counter()
        renderer = FFmpegBackend(prefer_nvenc=config.prefer_nvenc and not config.cpu_only)
        rendered_path = str(renderer.render(ast, output))
        _stage(stages, "render", begin, output=rendered_path,
               requested_encoder="cpu" if config.cpu_only else ("nvenc-preferred" if config.prefer_nvenc else "cpu"))
    else:
        stages.append(BuildStage("render", "not-requested", 0.0,
                                 {"message": "pass --render to invoke FFmpeg"}))

    manifest = {
        "schema_version": 1,
        "render_id": render_id,
        "started_at": started_at,
        "finished_at": _now(),
        "inputs": {"song": _file_fingerprint(song), "clip_root": str(clips)},
        "config": {"width": config.width, "height": config.height, "fps": config.fps,
                   "render_requested": config.render, "cpu_only": config.cpu_only,
                   "nvenc_preferred": config.prefer_nvenc},
        "artifacts": {"ast": str(ast_path), "html_report": str(report_path),
                      "render": rendered_path, "replay_ledger": str(ledger_path)},
        "stages": [asdict(stage) for stage in stages],
        "limitations": ["No CUDA zero-copy bridge or custom AVX2 extension was invoked.",
                         "No platform posting, ad spend, or reward learning is performed."],
    }
    _write_json_atomic(manifest_path, manifest)
    manifest["artifacts"]["manifest"] = str(manifest_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(prog="synapse-art-director",
                                     description="Compile, validate, report, and optionally render a local video project")
    parser.add_argument("song", type=Path)
    parser.add_argument("clips", type=Path)
    parser.add_argument("--db", type=Path, default=Path("database/genome.sqlite3"))
    parser.add_argument("--output", type=Path, default=Path("output/final.mp4"))
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--render", action="store_true", help="invoke FFmpeg; off by default")
    parser.add_argument("--cpu", action="store_true", help="disable NVENC preference")
    args = parser.parse_args()
    config = BuildConfig(args.song, args.clips, args.db, args.output, args.reports,
                         args.width, args.height, args.fps, args.render, args.cpu, not args.cpu)
    try:
        print(json.dumps(run_build(config), indent=2, ensure_ascii=False))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
