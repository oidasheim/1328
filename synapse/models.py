from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Track:
    path: Path
    artist: str = "Unknown Artist"
    title: str = "Untitled"
    genre: str = ""
    bpm: float | None = None
    duration: float | None = None


@dataclass
class ReleaseManifest:
    track: Track
    stages: list[str] = field(default_factory=list)
    assets: dict[str, Any] = field(default_factory=dict)
    approvals_required: list[str] = field(default_factory=list)
    status: str = "planned"

    def add_stage(self, name: str, **data: Any) -> None:
        self.stages.append(name)
        if data:
            self.assets[name] = data

    def to_dict(self) -> dict[str, Any]:
        return {
            "track": {
                "path": str(self.track.path),
                "artist": self.track.artist,
                "title": self.track.title,
                "genre": self.track.genre,
                "bpm": self.track.bpm,
                "duration": self.track.duration,
            },
            "stages": self.stages,
            "assets": self.assets,
            "approvals_required": self.approvals_required,
            "status": self.status,
        }
