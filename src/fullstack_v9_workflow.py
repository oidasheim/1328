"""Deterministic, local-only Fullstack v9 stage orchestrator.

This implementation does not execute publishing, cloud synchronization, ad
spending, or external commands by default. External stages are represented as
reviewable step definitions and only local dry-run/evaluation is enabled.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Callable, Iterable


STAGE_ORDER = ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8")
PROFILES: dict[str, tuple[str, ...]] = {
    "full": ("S0", "S1", "S3", "S4", "S5", "S6", "S7"),
    "dual": ("S0", "S1", "S4", "S5", "S7"),
    "fast": ("S0", "S1", "S5", "S7"),
    "noparm": ("S0", "S1", "S2", "S4", "S5", "S7"),
    "distill": ("S0", "S1", "S3", "S4"),
    "sync": ("S0", "S6", "S7", "S8"),
}


@dataclass(frozen=True)
class Stage:
    id: str
    name: str
    enabled_by_default: bool
    external_action: bool


STAGES: dict[str, Stage] = {
    "S0": Stage("S0", "resolve and verify paths", True, False),
    "S1": Stage("S1", "build audio and beat report", True, False),
    "S2": Stage("S2", "scan a provided input directory", True, False),
    "S3": Stage("S3", "distill local knowledge metadata", True, False),
    "S4": Stage("S4", "prepare clip candidates", True, False),
    "S5": Stage("S5", "render a local low-risk preview", True, False),
    "S6": Stage("S6", "create a review-only audit report", True, False),
    "S7": Stage("S7", "write JSON run ledger", True, False),
    "S8": Stage("S8", "explicit external sync placeholder", False, True),
}


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    started_at: str
    profile: str
    dry_run: bool
    stages: tuple[str, ...]
    status: str
    findings: tuple[str, ...]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resolve_path(value: str | None, environment_keys: Iterable[str],
                 fallbacks: Iterable[Path]) -> Path | None:
    """Resolve an explicit path or one of several environment fallbacks."""
    candidates: list[Path] = []
    if value:
        candidates.append(Path(value).expanduser())
    for key in environment_keys:
        env = os.environ.get(key)
        if env:
            candidates.append(Path(env).expanduser())
    candidates.extend(fallbacks)
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists():
            return resolved
    return None


def stage_resolution(root: Path, profile: str, *, song: str | None = None,
                     clips: str | None = None, output: str | None = None,
                     dry_run: bool = True) -> dict[str, object]:
    if profile not selected_profile(profiles=PROFILES):
        raise ValueError(f"unknown profile: {profile}")
    music = resolve_path(song, ("OIDA_MUSIC_DIR", "MUSIC_DIR"),
                         (root / "music", root / "audio", Path.cwd()))
    clip_root = resolve_path(clips, ("OIDA_CLIPS_DIR", "CLIPS_DIR"),
                            (root / "clips", root / "assets", root))
    output_root = resolve_path(output, ("OIDA_OUTPUT_DIR", "OUTPUT_DIR"),
                               (root / "output",))
    if output_root is None:
        output_root = root / "output"
    stages = PROFILES[profile]
    external = [stage_id for stage_id in stages if STAGES[stage_id].external_action]
    if external and not dry_run:
        raise RuntimeError("External stages require a separately reviewed adapter; current workflow refuses execution")
    return {"root": str(root.resolve()), "music": str(music) if music else None,
            "clips": str(clip_root) if clip_root else None,
            "output": str(output_root), "profile": profile,
            "stages": list(stages), "dry_run": dry_run,
            "external_stages": external}


def selected_profile(profiles: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    # Small helper enables validation without mutating the profile registry.
    return tuple(profiles)


def audit_repository(root: Path) -> dict[str, object]:
    """Inventory BAT files and report obvious static path/drift risks."""
    bat_files = sorted(p for p in root.rglob("*.bat") if p.is_file())
    findings: list[str] = []
    patterns = (
        (re.compile(r"(?i)E:\\[\\^]+"), "legacy E:\\ hard-coded path"),
        (re.compile(r"\\\\"), "possible double-backslash path"),
        (re.compile(r"(?i)(posteverywhere|send_to_creators|api\.creator-network)"),
         "potential external publishing/distribution call"),
    )
    for bat in bat_files:
        try:
            text = bat.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern, description in patterns:
            if pattern.search(text):
                findings.append(f"{bat.relative_to(root).as_posix()}: {description}")
    findings = sorted(set(findings))
    return {"bat_count": len(bat_files), "bat_files": [p.relative_to(root).as_posix() for p in bat_files],
            "findings": findings, "status": "review_required" if findings else "pass"}


def run_fullstack(profile: str = "full", *, root: Path | None = None,
                  song: str | None = None, clips: str | None = None,
                  output: str | None = None, dry_run: bool = True,
                  ledger: str | None = None) -> dict[str, object]:
    root = (root or Path(__file__).resolve().parents[1]).resolve()
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    resolution = stage_resolution(root, profile, song=song, clips=clips,
                                  output=output, dry_run=dry_run)
    audit = audit_repository(root)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    record = RunRecord(run_id, utc_now(), profile, dry_run,
                       tuple(resolution["stages"]),
                       "pass-dry-run" if dry_run else "review-only",
                       tuple(audit["findings"]))
    report = {"schema_version": 1, "epistemic_status": "LOCAL_RUN_AUDIT",
              "resolution": resolution, "audit": audit,
              "run": asdict(record),
              "constraints": {"external_publish": False,
                               "cloud_sync": False,
                               "ad_spend": False,
                               "external_stages_require_review": True}}
    target = Path(ledger).expanduser().resolve() if ledger else root / "reports" / "fullstack_v9_workflow_report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(prog="synapse-fullstack-v9")
    parser.add_argument("--profile", choices=tuple(PROFILES), default="full")
    parser.add_argument("--song", type=Path)
    parser.add_argument("--clips", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--eval", action="store_true", help="run repository BAT/JSON audit only")
    args = parser.parse_args()
    root = args.root or Path(__file__).resolve().parents[1]
    try:
        if args.eval:
            audit = audit_repository(root.resolve())
            print(json.dumps(audit, indent=2, ensure_ascii=False))
            return 0
        report = run_fullstack(args.profile, root=root, song=str(args.song) if args.song else None,
                               clips=str(args.clips) if args.clips else None,
                               output=str(args.output) if args.output else None,
                               dry_run=args.dry_run, ledger=str(args.ledger) if args.ledger else None)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"fullstack v9 failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
