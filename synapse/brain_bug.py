"""Brain.bug include registry and validated learning stubs.

This module indexes local files and manifest metadata only. It does not execute
unknown local scripts, contact external services, or convert forecasts into
facts or signing decisions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class KnowledgeInclude:
    id: str
    kind: str
    description: str
    source_path: str
    epistemic_status: str = "INTERNAL_MODEL"


@dataclass(frozen=True)
class TelemetryEvent:
    asset_id: str
    published_at: str
    platform: str
    metrics: dict[str, float]
    source: str


DEFAULT_INCLUDES: tuple[KnowledgeInclude, ...] = (
    KnowledgeInclude("wissens_destillat", "knowledge_distillation",
                     "Validated rules, forensic recovery and causal audio-DNA notes",
                     "distilled_knowledge.json"),
    KnowledgeInclude("durak_kolecktiv", "creative_collective",
                     "Polyrhythmic 140-168 BPM creative corpus metadata",
                     "corpus/durak"),
    KnowledgeInclude("platform_relations_vector", "platform_relation_graph",
                     "Internal routing priorities and governance-linked distribution graph",
                     "reports/platform_vector.json"),
)


class BrainBugRegistry:
    def __init__(self, root: str | Path, includes: Iterable[KnowledgeInclude] = DEFAULT_INCLUDES):
        self.root = Path(root).expanduser().resolve()
        self.includes = tuple(includes)

    def manifest(self) -> dict[str, object]:
        items = []
        for include in self.includes:
            source = (self.root / include.source_path) if not Path(include.source_path).is_absolute() else Path(include.source_path)
            items.append({**asdict(include), "exists": source.exists(), "resolved_path": str(source)})
        return {"root": str(self.root), "status": "manifest-only", "includes": items}

    def validate_telemetry(self, event: TelemetryEvent) -> dict[str, object]:
        finite = all(isinstance(value, (int, float)) and not isinstance(value, bool)
                     and 0.0 <= float(value) <= 1_000_000_000 for value in event.metrics.values())
        if not event.asset_id or not event.platform or not event.published_at:
            raise ValueError("telemetry requires asset_id, platform and published_at")
        if not finite:
            raise ValueError("telemetry metrics must be finite non-negative numbers")
        return {"validated": True, "asset_id": event.asset_id, "platform": event.platform,
                "published_at": event.published_at, "metrics": event.metrics,
                "source": event.source, "epistemic_status": "GROUND_TRUTH_CANDIDATE"}


def write_registry(destination: str | Path, root: str | Path) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    registry = BrainBugRegistry(root)
    target.write_text(json.dumps(registry.manifest(), indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return target
