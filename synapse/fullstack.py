"""Portable, local-first orchestration for SYNAPSE workflows."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Callable


class StageStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_RUN = "not_run"


@dataclass(frozen=True)
class StageResult:
    stage: str
    status: StageStatus
    message: str
    details: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {"stage": self.stage, "status": self.status.value,
                "message": self.message, "details": self.details or {}}


@dataclass(frozen=True)
class FullstackConfig:
    root: str
    music_dir: str = "music"
    clip_dir: str = "clips"
    output_dir: str = "output"
    report_dir: str = "reports"
    sqlite_db: str | None = None
    duckdb_db: str | None = None
    limit: int | None = None
    retry_failed: bool = False
    bump: str = "patch"
    cpu_affinity: tuple[int, ...] = (0, 1)
    worker_affinity: tuple[int, ...] = (2, 3, 4, 5)

    def paths(self) -> dict[str, Path]:
        root = Path(self.root).expanduser().resolve()
        values = {"root": root, "music": self.music_dir, "clips": self.clip_dir,
                  "output": self.output_dir, "reports": self.report_dir}
        resolved = {name: (value if isinstance(value, Path) else (root / value).resolve())
                    for name, value in values.items()}
        if self.sqlite_db:
            resolved["sqlite_db"] = (root / self.sqlite_db).resolve()
        if self.duckdb_db:
            resolved["duckdb_db"] = (root / self.duckdb_db).resolve()
        return resolved


@dataclass(frozen=True)
class FullstackReport:
    version: str
    started_at: str
    finished_at: str
    stages: tuple[StageResult, ...]
    config: FullstackConfig

    def to_dict(self) -> dict[str, object]:
        return {"version": self.version, "started_at": self.started_at,
                "finished_at": self.finished_at,
                "stages": [stage.to_dict() for stage in self.stages],
                "config": asdict(self.config)}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def bump_version(version: str, bump: str) -> str:
    if bump not in {"major", "minor", "patch"}:
        raise ValueError("bump must be major, minor, or patch")
    parts = version.lstrip("v").split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("version must have MAJOR.MINOR.PATCH form")
    numbers = [int(part) for part in parts]
    index = {"major": 0, "minor": 1, "patch": 2}[bump]
    numbers[index] += 1
    for position in range(index + 1, 3):
        numbers[position] = 0
    return ".".join(map(str, numbers))


def read_version(path: str | Path) -> str:
    target = Path(path)
    if not target.exists():
        return "0.0.0"
    data = json.loads(target.read_text(encoding="utf-8"))
    version = data.get("version", "0.0.0")
    if not isinstance(version, str):
        raise ValueError("version ledger contains a non-string version")
    return version


def write_version(path: str | Path, version: str, bump: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"version": version, "bump": bump,
                                  "updated_at": utc_now()}, indent=2) + "\n", encoding="utf-8")


def _stage(name: str, action: Callable[[], tuple[str, dict[str, object]]]) -> StageResult:
    try:
        message, details = action()
        return StageResult(name, StageStatus.PASS, message, details)
    except (OSError, ValueError, RuntimeError) as exc:
        return StageResult(name, StageStatus.FAIL, str(exc))


def preflight(config: FullstackConfig) -> StageResult:
    def action() -> tuple[str, dict[str, object]]:
        paths = config.paths()
        paths["output"].mkdir(parents=True, exist_ok=True)
        paths["reports"].mkdir(parents=True, exist_ok=True)
        missing = [name for name in ("music", "clips") if not paths[name].is_dir()]
        details = {"python": sys.version.split()[0], "ffmpeg": shutil.which("ffmpeg") or "missing",
                   "paths": {key: str(value) for key, value in paths.items()},
                   "cpu_affinity": list(config.cpu_affinity), "worker_affinity": list(config.worker_affinity)}
        if missing:
            raise RuntimeError(f"missing input directories: {', '.join(missing)}")
        return "local paths and optional tools checked", details
    return _stage("preflight", action)


def evaluate_inputs(config: FullstackConfig) -> StageResult:
    def action() -> tuple[str, dict[str, object]]:
        paths = config.paths()
        audio = sorted(p for p in paths["music"].rglob("*") if p.suffix.lower() in {".wav", ".mp3", ".flac", ".m4a"})
        clips = sorted(p for p in paths["clips"].rglob("*") if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"})
        if config.limit is not None:
            if config.limit < 1:
                raise ValueError("limit must be positive")
            audio, clips = audio[:config.limit], clips[:config.limit]
        if not audio:
            raise RuntimeError("no audio inputs found")
        if not clips:
            raise RuntimeError("no video clips found")
        return f"found {len(audio)} audio file(s) and {len(clips)} clip(s)", {"audio": len(audio), "clips": len(clips)}
    return _stage("input-evaluation", action)


def run(config: FullstackConfig, *, execute_render: bool = False) -> FullstackReport:
    started = utc_now()
    stages = [preflight(config), evaluate_inputs(config)]
    paths = config.paths()
    if all(stage.status != StageStatus.FAIL for stage in stages):
        if config.duckdb_db:
            stages.append(StageResult("database-sync", StageStatus.WARN,
                                      "DuckDB path recorded; schema-specific sync is opt-in",
                                      {"database": str(paths["duckdb_db"])}))
        else:
            stages.append(StageResult("database-sync", StageStatus.WARN, "no DuckDB database configured"))
        stages.append(StageResult("render", StageStatus.WARN if not execute_render else StageStatus.NOT_RUN,
                                  "render adapter not invoked by orchestration baseline"))
    else:
        stages.extend([StageResult("database-sync", StageStatus.NOT_RUN, "blocked by failed preflight"),
                       StageResult("render", StageStatus.NOT_RUN, "blocked by failed preflight")])
    old = read_version(paths["reports"] / "workflow_version.json")
    version = bump_version(old, config.bump)
    write_version(paths["reports"] / "workflow_version.json", version, config.bump)
    report = FullstackReport(version, started, utc_now(), tuple(stages), config)
    report_path = paths["reports"] / "fullstack-latest.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(prog="synapse-fullstack")
    parser.add_argument("--root", default=".")
    parser.add_argument("--music", default="music")
    parser.add_argument("--clips", default="clips")
    parser.add_argument("--output", default="output")
    parser.add_argument("--reports", default="reports")
    parser.add_argument("--duckdb")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--bump", choices=("major", "minor", "patch"), default="patch")
    parser.add_argument("--render", action="store_true", help="reserved; rendering remains explicit")
    args = parser.parse_args()
    config = FullstackConfig(args.root, args.music, args.clips, args.output, args.reports,
                             duckdb_db=args.duckdb, limit=args.limit, bump=args.bump)
    report = run(config, execute_render=args.render)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 1 if any(stage.status == StageStatus.FAIL for stage in report.stages) else 0


if __name__ == "__main__":
    raise SystemExit(main())
