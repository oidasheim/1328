"""Portable full-stack orchestration for SYNAPSE/WE.ED.IT workflows.

This module coordinates explicit local stages. It does not contain Windows J:
paths, starts cloud services, or performs publishing. Optional commands and
ports are opt-in and are rejected unless explicitly configured.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
from typing import Iterable, Mapping, Sequence


class StageStatus(str, Enum):
    NOT_RUN = "not_run"
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


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
    music_dir: str
    clip_dir: str
    output_dir: str
    sqlite_db: str | None = None
    duckdb_db: str | None = None
    report_dir: str = "reports"
    limit: int | None = None
    retry_failed: bool = False
    bump: str = "patch"
    cpu_affinity: tuple[int, ...] = (0, 1)
    worker_affinity: tuple[int, ...] = (2, 3, 4, 5)


@dataclass(frozen=True)
class FullstackReport:
    version: str
    started_at: str
    finished_at: str
    stages: tuple[StageResult, ...]
    config: FullstackConfig

    def to_dict(self) -> dict[str, object]:
        return {"version": self.version,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "stages": [stage.to_dict() for stage in self.stages],
                "config": asdict(self.config)}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _resolve(root: str | Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(root).expanduser() / path
    return path.resolve()


def bump_version(version: str, bump: str) -> str:
    if bump not in {"major", "minor", "patch"}:
        raise Value:: if False else None
