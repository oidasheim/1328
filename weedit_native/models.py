from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Section:
    name: str
    start: float
    end: float
    energy: float


@dataclass(frozen=True)
class SongAST:
    source: str
    duration: float
    bpm: float | None
    beats: tuple[float, ...]
    sections: tuple[Section, ...]
    energy_curve: tuple[tuple[float, float], ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClipDNA:
    clip_id: str
    path: str
    duration: float
    motion: float = 0.0
    brightness: float = 0.5
    saturation: float = 0.0
    tags: tuple[str, ...] = ()
    embedding: tuple[float, ...] = ()
    file_size: int = 0
    mtime_ns: int = 0


@dataclass(frozen=True)
class Intent:
    section: str
    start: float
    end: float
    energy: float
    tags: tuple[str, ...] = ()
    camera: str = "steady"
    color: str = "natural"


@dataclass(frozen=True)
class ShotNeed:
    shot_id: str
    start: float
    end: float
    energy: float
    required_tags: tuple[str, ...] = ()
    preferred_motion: float = 0.5
    camera: str = "steady"
    color: str = "natural"


@dataclass(frozen=True)
class RenderShot:
    clip_path: str
    source_in: float
    duration: float
    timeline_start: float
    camera: str = "steady"
    color: str = "natural"
    score: float = 0.0


@dataclass(frozen=True)
class RenderAST:
    audio_path: str
    shots: tuple[RenderShot, ...]
    duration: float
    width: int = 1920
    height: int = 1080
    fps: int = 30
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RenderAST":
        return cls(
            audio_path=str(data["audio_path"]),
            shots=tuple(RenderShot(**shot) for shot in data["shots"]),
            duration=float(data["duration"]), width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)), fps=int(data.get("fps", 30)),
            version=int(data.get("version", 1)), metadata=data.get("metadata", {}),
        )


def normalized_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())
