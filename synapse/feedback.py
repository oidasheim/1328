"""Local release feedback store for observed, source-labelled outcomes.

No platform scraping or posting is performed here. Import only official API
exports or manually recorded metrics obtained lawfully. The module treats
completion, shares, saves and reach as observations, never as proof of viral
cause or audience control.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
import sqlite3
from typing import Iterable, Sequence


SCHEMA = """
CREATE TABLE IF NOT EXISTS render_queue (
    clip_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    rendered_at TEXT,
    published_at TEXT,
    source_render TEXT,
    predicted_probability REAL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS viral_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clip_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL,
    views REAL,
    likes REAL,
    comments REAL,
    shares REAL,
    saves REAL,
    completion_rate REAL,
    watch_time REAL,
    followers_delta REAL,
    raw_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(clip_id, platform, observed_at, source),
    FOREIGN KEY(clip_id) REFERENCES render_queue(clip_id)
);
CREATE INDEX IF NOT EXISTS idx_feedback_clip ON viral_feedback(clip_id);
CREATE INDEX IF NOT EXISTS idx_feedback_platform ON viral_feedback(platform);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _nonnegative(name: str, value: float | int | None) -> float | None:
    if value is None:
        return None
    result = float(value)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


@dataclass(frozen=True)
class QueueItem:
    clip_id: str
    platform: str
    rendered_at: str | None = None
    published_at: str | None = None
    source_render: str | None = None
    predicted_probability: float | None = None
    metadata: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if not self.clip_id.strip():
            raise ValueError("clip_id cannot be empty")
        if not self.platform.strip():
            raise ValueError("platform cannot be empty")
        if self.predicted_probability is not None:
            p = float(self.predicted_probability)
            if not 0 <= p <= 1:
                raise ValueError("predicted_probability must be between 0 and 1")


@dataclass(frozen=True)
class Feedback:
    clip_id: str
    platform: str
    observed_at: str
    source: str
    views: float | None = None
    likes: float | None = None
    comments: float | None = None
    shares: float | None = None
    saves: float | None = None
    completion_rate: float | None = None
    watch_time: float | None = None
    followers_delta: float | None = None
    raw: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if not self.clip_id.strip() or not self.platform.strip() or not self.source.strip():
            raise ValueError("clip_id, platform and source are required")
        for name in ("views", "likes", "comments", "shares", "saves", "watch_time"):
            _nonnegative(name, getattr(self, name))
        if self.completion_rate is not None and not 0 <= float(self.completion_rate) <= 1:
            raise ValueError("completion_rate must be between 0 and 1")


class FeedbackStore:
    def __init__(self, path: str | Path = "database/viral_feedback.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def enqueue(self, item: QueueItem) -> None:
        self.connection.execute("""
            INSERT OR REPLACE INTO render_queue
            (clip_id,platform,rendered_at,published_at,source_render,predicted_probability,metadata_json)
            VALUES(?,?,?,?,?,?,?)
        """, (item.clip_id, item.platform, item.rendered_at, item.published_at,
              item.source_render, item.predicted_probability,
              json.dumps(item.metadata or {}, sort_keys=True)))
        self.connection.commit()

    def record(self, item: Feedback) -> None:
        if not self.connection.execute("SELECT 1 FROM render_queue WHERE clip_id=?", (item.clip_id,)).fetchone():
            raise KeyError(f"Unknown clip_id; enqueue it first: {item.clip_id}")
        values = (item.clip_id, item.platform, item.observed_at, item.source,
                  item.views, item.likes, item.comments, item.shares, item.saves,
                  item.completion_rate, item.watch_time, item.followers_delta,
                  json.dumps(item.raw or {}, sort_keys=True))
        self.connection.execute("""
            INSERT OR REPLACE INTO viral_feedback
            (clip_id,platform,observed_at,source,views,likes,comments,shares,saves,
             completion_rate,watch_time,followers_delta,raw_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, values)
        self.connection.commit()

    def import_csv(self, path: str | Path) -> int:
        count = 0
        with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            required = {"clip_id", "platform", "observed_at", "source"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise ValueError("CSV requires clip_id, platform, observed_at, source")
            for row in reader:
                def number(name: str) -> float | None:
                    value = (row.get(name) or "").strip()
                    return float(value) if value else None
                self.record(Feedback(
                    clip_id=row["clip_id"].strip(), platform=row["platform"].strip(),
                    observed_at=row["observed_at"].strip(), source=row["source"].strip(),
                    views=number("views"), likes=number("likes"), comments=number("comments"),
                    shares=number("shares"), saves=number("saves"),
                    completion_rate=number("completion_rate"), watch_time=number("watch_time"),
                    followers_delta=number("followers_delta"), raw={k: v for k, v in row.items() if k not in {
                        "clip_id", "platform", "observed_at", "source", "views", "likes", "comments",
                        "shares", "saves", "completion_rate", "watch_time", "followers_delta"
                    }},
                ))
                count += 1
        return count

    def summaries(self) -> list[dict[str, object]]:
        rows = self.connection.execute("""
            SELECT platform, COUNT(*) AS observations,
                   COUNT(DISTINCT clip_id) AS clips,
                   AVG(completion_rate) AS mean_completion,
                   AVG(CASE WHEN views > 0 THEN 1.0*shares/views END) AS share_rate,
                   AVG(CASE WHEN views > 0 THEN 1.0*saves/views END) AS save_rate,
                   AVG(followers_delta) AS mean_follower_delta
            FROM viral_feedback
            WHERE completion_rate IS NOT NULL OR views IS NOT NULL
            GROUP BY platform
            ORDER BY platform
        """).fetchall()
        return [dict(row) for row in rows]

    def deep_insights(self) -> dict[str, object]:
        """Descriptive report only: it asserts no causality or guaranteed success."""
        summaries = self.summaries()
        return {
            "generated_at": utc_now(),
            "sample_scope": "Observed exports/imported metrics only",
            "platforms": summaries,
            "warnings": [
                "Small and self-selected samples are not representative.",
                "Causal attribution is not established by this aggregate report.",
                "Do not infer audience psychology or manipulate users from these metrics.",
                "Completion and retention metrics require a consistent source definition.",
            ],
        }

    def close(self) -> None:
        self.connection.close()
