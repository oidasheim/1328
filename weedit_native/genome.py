"""One-time-per-file clip feature extraction with a persistent SQLite cache."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3

from .models import ClipDNA

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


class GenomeDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS clips(
            clip_id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, duration REAL NOT NULL,
            motion REAL NOT NULL, brightness REAL NOT NULL, saturation REAL NOT NULL,
            tags_json TEXT NOT NULL, file_size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        self.db.commit()

    def get(self, path: Path) -> ClipDNA | None:
        stat = path.stat()
        row = self.db.execute("SELECT clip_id,path,duration,motion,brightness,saturation,tags_json,file_size,mtime_ns FROM clips WHERE path=?", (str(path.resolve()),)).fetchone()
        if not row or row[7] != stat.st_size or row[8] != stat.st_mtime_ns:
            return None
        return ClipDNA(row[0], row[1], row[2], row[3], row[4], row[5], tuple(json.loads(row[6])), file_size=row[7], mtime_ns=row[8])

    def put(self, clip: ClipDNA) -> None:
        self.db.execute("INSERT OR REPLACE INTO clips(clip_id,path,duration,motion,brightness,saturation,tags_json,file_size,mtime_ns,updated_at) VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                        (clip.clip_id, clip.path, clip.duration, clip.motion, clip.brightness, clip.saturation, json.dumps(clip.tags), clip.file_size, clip.mtime_ns))
        self.db.commit()

    def all(self) -> list[ClipDNA]:
        rows = self.db.execute("SELECT clip_id,path,duration,motion,brightness,saturation,tags_json,file_size,mtime_ns FROM clips ORDER BY path").fetchall()
        return [ClipDNA(r[0], r[1], r[2], r[3], r[4], r[5], tuple(json.loads(r[6])), file_size=r[7], mtime_ns=r[8]) for r in rows]

    def close(self) -> None:
        self.db.close()


def scan_clip(path: str | Path) -> ClipDNA:
    path = Path(path).resolve()
    stat = path.stat()
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Clip scanning requires `pip install -e '.[vision]'`") from exc
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot decode video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = float(frame_count / fps) if fps > 0 else 0.0
    frame_count_i = int(frame_count)
    samples = []
    for position in (0.15, 0.5, 0.85):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(max(0, frame_count_i - 1) * position))
        ok, frame = cap.read()
        if ok:
            samples.append(cv2.resize(frame, (160, 90)))
    cap.release()
    if duration <= 0 or not samples:
        raise ValueError(f"No decodable frames/duration: {path}")
    gray = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) for frame in samples]
    motion = float(np.mean([np.mean(cv2.absdiff(a, b)) / 255.0 for a, b in zip(gray, gray[1:])])) if len(gray) > 1 else 0.0
    hsv = cv2.cvtColor(samples[len(samples) // 2], cv2.COLOR_BGR2HSV)
    brightness = float(np.mean(hsv[:, :, 2]) / 255.0)
    saturation = float(np.mean(hsv[:, :, 1]) / 255.0)
    tags = []
    if brightness < 0.3: tags.append("lowlight")
    if brightness > 0.72: tags.append("bright")
    if saturation > 0.55: tags.append("saturated")
    if motion > 0.18: tags.append("fast")
    digest = hashlib.sha256(f"{path}:{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()[:16]
    return ClipDNA(digest, str(path), duration, motion, brightness, saturation, tuple(tags), file_size=stat.st_size, mtime_ns=stat.st_mtime_ns)


def scan_directory(directory: str | Path, database: str | Path) -> dict[str, int]:
    root = Path(directory).resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    genome = GenomeDB(database)
    counts = {"indexed": 0, "cached": 0, "skipped": 0}
    try:
        for path in sorted(p for p in root.rglob("*") if p.suffix.lower() in VIDEO_EXTENSIONS):
            try:
                existing = genome.get(path)
                if existing:
                    counts["cached"] += 1
                    continue
                genome.put(scan_clip(path))
                counts["indexed"] += 1
            except (OSError, ValueError, RuntimeError) as exc:
                print(f"Skip {path}: {exc}")
                counts["skipped"] += 1
    finally:
        genome.close()
    return counts
