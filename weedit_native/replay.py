"""Replay ledger for reproducible WE.ED.IT decisions."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    shot_id TEXT PRIMARY KEY,
    render_id TEXT NOT NULL,
    timeline_start REAL NOT NULL,
    timeline_end REAL NOT NULL,
    clip_path TEXT,
    source_in REAL,
    source_out REAL,
    camera TEXT,
    color TEXT,
    candidate_ids TEXT NOT NULL,
    selected_score REAL,
    reward REAL,
    pass_evidence TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_decisions_render ON decisions(render_id);
"""


class ReplayLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        self.db.commit()

    def record(self, render_id: str, shot_id: str, shot: Any, candidates: list[str],
               pass_evidence: dict[str, object], input_hash: str,
               reward: float | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        source_out = float(shot.source_in) + float(shot.duration)
        self.db.execute("""INSERT OR REPLACE INTO decisions
            (shot_id,render_id,timeline_start,timeline_end,clip_path,source_in,source_out,
             camera,color,candidate_ids,selected_score,reward,pass_evidence,input_hash,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            shot_id, render_id, shot.timeline_start, shot.timeline_start + shot.duration,
            shot.clip_path, shot.source_in, source_out, shot.camera, shot.color,
            json.dumps(candidates), float(shot.score), reward,
            json.dumps(pass_evidence, sort_keys=True), input_hash, now,
        ))
        self.db.commit()

    def replay(self, shot_id: str) -> dict[str, object] | None:
        row = self.db.execute("SELECT * FROM decisions WHERE shot_id=?", (shot_id,)).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["candidate_ids"] = json.loads(data["candidate_ids"])
        data["pass_evidence"] = json.loads(data["pass_evidence"])
        return data

    def close(self) -> None:
        self.db.close()


def sha256_object(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
