import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track TEXT NOT NULL,
    node TEXT NOT NULL,
    event TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_events_track ON events(track);
"""


class EventLedger:
    def __init__(self, path: str | Path = "database/synapse_events.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def record(self, track: str, node: str, event: str, payload: dict[str, Any] | None = None) -> None:
        self.connection.execute(
            "INSERT INTO events(track,node,event,payload) VALUES(?,?,?,?)",
            (track, node, event, json.dumps(payload or {}, sort_keys=True)),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
