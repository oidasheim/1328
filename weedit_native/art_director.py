"""Portable Art Director with optional isolated-vocal analysis."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
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
from .vocal_stems import separate_vocal_stem


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
    analyze_vocals: bool = False
    stem_method: str = "auto"
    allow_model_download: bool = False

    def validate(self) -> None:
        if self.width <= 0 or self.height <= 0 or self.width % 2 or self.height % 2:
            raise ValueError("width and height must be positive even integers")
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        if self.stem_method not in {"auto", "roformer", "demucs", "fallback"}:
            raise ValueError("invalid stem method")
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
    return {"path": str(path.resolve()), "size_bytes": info.st_size, "mtime_ns": info.st_mtime_ns}


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _stage(stages: list[BuildStage], name: str, started: float, **details: Any) -> None:
    stages.append(BuildStage(name, "pass", round(time.perf_counter() - started, 4), details))


def run_build(config: BuildConfig) -> dict[str, Any]:
    config.validate()
    song, clips = config.song.expanduser().resolve(), config.clips.expanduser().resolve()
    database, output, reports = (config.database.expanduser().resolve(),
                                 config.output.expanduser().resolve(),
                                 config.reports.expanduser().resolve())
    if not song.is_file():
        raise FileNotFoundError(f"audio source not found: {song}")
    if not clips.is_dir():
        raise FileNotFoundError(f"clip directory not found: {clips}")

    stages: list[BuildStage] = []
    started_at = _now()
    begin = time.perf_counter()
    scan = scan_directory(clips, database)
    _stage(stages, "genome-scan", begin, **scan, database=str(database))

    vocal_artifacts: dict[str, Any] | None = None
    if config.analyze_vocals:
        begin = time.perf_counter()
        stem_cache = output.parent / "_tmp_synapse_chunks" / "stems"
        stems = separate_vocal_stem(song, stem_cache, method=config.stem_method,
                                    allow_model_download=config.allow_model_download)
        vocal_artifacts = stems.to_dict()
        vocal_artifacts["cache_dir"] = str(stem_cache)
        try:
            from .lipsync import formant_energy_mar
            import numpy as np
            vocal_path = Path(stems.vocals)
            import librosa
            vocal_duration = float(librosa.get_duration(path=str(vocal_path)))
            mar = formant_energy_mar(str(vocal_path), vocal_duration, config.fps)
            mar_path = reports / f"{song.stem}-{stems.source_sha256[:12]}-vocal-mar.npy"
            mar_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(mar_path, mar)
            vocal_artifacts.update({"mar_proxy": str(mar_path), "mar_frames": int(len(mar)),
                                    "mar_fps": config.fps,
                                    "mar_kind": "formant-energy proxy, not phoneme alignment"})
        except (ImportError, RuntimeError) as exc:
            vocal_artifacts["mar_warning"] = str(exc)
        _stage(stages, "vocal-separation-and-analysis", begin, **vocal_artifacts)

    begin = time.perf_counter()
    ast = compile_project(song, clips, database, width=config.width, height=config.height, fps=config.fps)
    ast, pass_evidence = run_pass_pipeline(ast)
    _stage(stages, "compile-and-optimize", begin, shot_count=len(ast.shots),
           duration=ast.duration, pass_count=pass_evidence["pass_count"])

    render_id = sha256_object({"song": _file_fingerprint(song),
                               "config": {"width": config.width, "height": config.height, "fps": config.fps},
                               "ast": ast.to_dict()})[:24]
    ast.metadata.update({"render_id": render_id, "pass_evidence": pass_evidence,
                         "pipeline": "weedit_native.art_director", "started_at": started_at,
                         "vocal_analysis": vocal_artifacts})
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
            ledger.record(render_id, f"{render_id}:shot-{index:05d}", shot, [], pass_evidence, input_hash)
    finally:
        ledger.close()
    _stage(stages, "reports-and-replay-ledger", begin, ast=str(ast_path), html=str(report_path), ledger=str(ledger_path))

    rendered_path: str | None = None
    if config.render:
        begin = time.perf_counter()
        rendered_path = str(FFmpegBackend(prefer_nvenc=config.prefer_nvenc and not config.cpu_only).render(ast, output))
        _stage(stages, "render", begin, output=rendered_path,
               requested_encoder="cpu" if config.cpu_only else ("nvenc-preferred" if config.prefer_nvenc else "cpu"))
    else:
        stages.append(BuildStage("render", "not-requested", 0.0, {"message": "pass --render to invoke FFmpeg"}))

    manifest = {"schema_version": 1, "render_id": render_id, "started_at": started_at,
                "finished_at": _now(), "inputs": {"song": _file_fingerprint(song), "clip_root": str(clips)},
                "config": {"width": config.width, "height": config.height, "fps": config.fps,
                           "render_requested": config.render, "analyze_vocals": config.analyze_vocals,
                           "stem_method": config.stem_method,
                           "allow_model_download": config.allow_model_download},
                "vocal_analysis": vocal_artifacts,
                "artifacts": {"ast": str(ast_path), "html_report": str(report_path),
                              "render": rendered_path, "replay_ledger": str(ledger_path)},
                "stages": [asdict(stage) for stage in stages],
                "limitations": ["No CUDA zero-copy bridge or custom AVX2 extension was invoked.",
                                "Vocal proxy fallback is approximate, not guaranteed source separation.",
                                "WhisperX transcription/forced alignment is not run by this pipeline.",
                                "No platform posting, ad spend, or reward learning is performed."]}
    _write_json_atomic(manifest_path, manifest)
    manifest["artifacts"]["manifest"] = str(manifest_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(prog="synapse-art-director",
                                     description="Compile, validate, report, and optionally render a local video project")
    parser.add_argument("song", type=Path); parser.add_argument("clips", type=Path)
    parser.add_argument("--db", type=Path, default=Path("database/genome.sqlite3"))
    parser.add_argument("--output", type=Path, default=Path("output/final.mp4"))
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("--width", type=int, default=1080); parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--render", action="store_true"); parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--analyze-vocals", action="store_true", help="separate/cache vocals and create a formant-energy proxy")
    parser.add_argument("--stem-method", choices=("auto", "roformer", "demucs", "fallback"), default="auto")
    parser.add_argument("--allow-model-download", action="store_true",
                        help="allow external separator packages to load/download model weights")
    args = parser.parse_args()
    config = BuildConfig(args.song, args.clips, args.db, args.output, args.reports,
                         args.width, args.height, args.fps, args.render, args.cpu, not args.cpu,
                         args.analyze_vocals, args.stem_method, args.allow_model_download)
    try:
        print(json.dumps(run_build(config), indent=2, ensure_ascii=False))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
