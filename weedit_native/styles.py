"""Deterministic style packages with validation."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class StylePackage:
    name: str
    constraints: dict[str, object]
    camera: dict[str, object]
    grading: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "constraints": self.constraints,
                "camera": self.camera, "grading": self.grading}


BUILTIN_STYLES: dict[str, StylePackage] = {
    name: StylePackage(name,
                       {"min_shot_seconds": 0.15, "catalog_lock_ratio": 0.667},
                       {"movement": "auto", "persist_across_phrase": True},
                       {"grading": "neutral", "preserve_source": True})
    for name in ("drill", "trap", "cinematic", "horror", "anime", "musicvideo", "lofi")
}


def install_style(root: str | Path, name: str) -> Path:
    if name not in BUILTIN_STYLES:
        raise KeyError(f"Unknown style: {name}")
    target = Path(root).expanduser().resolve() / "styles" / name
    target.mkdir(parents=True, exist_ok=True)
    package = BUILTIN_STYLES[name]
    for filename, data in (("constraints.json", package.constraints),
                           ("camera.json", package.camera), ("grading.json", package.grading)):
        (target / filename).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (target / "package.json").write_text(json.dumps(package.to_dict(), indent=2) + "\n", encoding="utf-8")
    return target
