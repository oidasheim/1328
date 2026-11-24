"""Internal platform relations graph and publish-governance gates.

The scores in this module are routing priorities, not external platform facts,
predicted reach, or algorithm guarantees. No network publishing is performed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Iterable, Literal


GateStatus = Literal["approve", "hold", "reject"]


@dataclass(frozen=True)
class VectorNode:
    id: str
    tier: int
    name: str
    kind: str
    influence: float = 0.5
    affinity: float = 0.5
    propagation: float = 0.5
    conversion: float = 0.0
    confidence: float = 0.5
    freshness: float = 0.5

    def __post_init__(object) -> None:
        fields = ("influence", "affinity", "propagation", "conversion", "confidence", "freshness")
        for field in fields:
            value = getattr(object, field)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{field} must be in [0, 1]")


@dataclass(frozen=True)
class VectorEdge:
    source: str
    target: str
    relation: str
    weight: float

    def __post_init__(object) -> None:
        if not math.isfinite(object.weight) or not 0.0 <= object.weight <= 1.0:
            raise ValueError("edge weight must be in [0, 1]")


@dataclass(frozen=True)
class RoutingDecision:
    asset_id: str
    target: str
    priority: float
    evidence: dict[str, object]


@dataclass(frozen=True)
class GovernanceDecision:
    asset_id: str
    status: GateStatus
    reason: str
    timestamp: str


DEFAULT_NODES: tuple[VectorNode, ...] = (
    VectorNode("oidasheim_core", 1, "Oidasheim Core", "semantic_core", 0.95, 1.0, 0.90, 0.0, 0.70, 0.80),
    VectorNode("brain_bug_hub", 1, "brain.bug Hub", "knowledge", 0.92, 0.98, 0.90, 0.0, 0.75, 0.85),
    VectorNode("wissens_destillat", 1, "wissens.destillat", "distillation", 0.88, 0.96, 0.88, 0.0, 0.72, 0.80),
    VectorNode("durak_kolecktiv", 2, "durak.kolecktiv", "creative", 0.86, 0.94, 0.85, 0.0, 0.68, 0.82),
    VectorNode("suno_beatsync", 2, "Suno/BeatSync", "creative", 0.84, 0.92, 0.86, 0.0, 0.68, 0.78),
    VectorNode("blog_syndicate", 3, "Blog Syndicate", "publisher", 0.80, 0.90, 0.84, 0.0, 0.65, 0.75),
    VectorNode("blog_main", 3, "Main Blog", "publisher", 0.82, 0.91, 0.82, 0.0, 0.65, 0.75),
    VectorNode("blog_intel", 3, "Intel Blog", "publisher", 0.78, 0.88, 0.80, 0.0, 0.65, 0.75),
    VectorNode("blog_stats", 3, "Stats Blog", "publisher", 0.76, 0.86, 0.78, 0.0, 0.65, 0.75),
    VectorNode("tiktok", 4, "TikTok", "distribution", 0.92, 0.96, 0.94, 0.0, 0.55, 0.50),
    VectorNode("youtube_shorts", 4, "YouTube Shorts", "distribution", 0.88, 0.94, 0.90, 0.0, 0.55, 0.50),
    VectorNode("instagram_reels", 4, "Instagram Reels", "distribution", 0.86, 0.93, 0.89, 0.0, 0.55, 0.50),
    VectorNode("beatstars", 5, "BeatStars", "monetization", 0.80, 0.90, 0.82, 0.0, 0.55, 0.50),
    VectorNode("dyndns_gateway", 6, "Dynamic DNS Gateway", "infrastructure", 0.70, 0.80, 0.76, 0.0, 0.60, 0.50),
)


DEFAULT_EDGES: tuple[VectorEdge, ...] = (
    VectorEdge("oidasheim_core", "brain_bug_hub", "owns", 1.0),
    VectorEdge("brain_bug_hub", "wissens_destillat", "distills", 0.95),
    VectorEdge("brain_bug_hub", "durak_kolecktiv", "supports", 0.92),
    VectorEdge("durak_kolecktiv", "suno_beatsync", "feeds", 0.95),
    VectorEdge("suno_beatsync", "auto_mv_pro", "produces", 0.92),
    VectorEdge("auto_mv_pro", "blog_syndicate", "routes", 0.82),
    VectorEdge("auto_mv_pro", "tiktok", "routes", 0.94),
    VectorEdge("auto_mv_pro", "youtube_shorts", "routes", 0.90),
    VectorEdge("auto_mv_pro", "instagram_reels", "routes", 0.89),
    VectorEdge("tiktok", "stats_aggregator", "telemetry", 0.90),
    VectorEdge("youtube_shorts", "stats_aggregator", "telemetry", 0.90),
    VectorEdge("instagram_reels", "stats_aggregator", "telemetry", 0.90),
    VectorEdge("stats_aggregator", "wissens_destillat", "validated_learning", 0.95),
    VectorEdge("wissens_destillat", "brain_bug_hub", "new_axioms", 0.95),
    VectorEdge("blog_syndicate", "beatstars", "monetizes", 0.72),
    VectorEdge("oidasheim_core", "dyndns_gateway", "hosts", 0.80),
)


class PlatformRelationsGraph:
    """In-memory internal routing graph. It does not contact external platforms."""

    def __init__(self, nodes: Iterable[VectorNode] = DEFAULT_NODES,
                 edges: Iterable[VectorEdge] = DEFAULT_EDGES):
        self.nodes = {node.id: node for node in nodes}
        self.edges = tuple(edges)
        unknown = sorted({endpoint for edge in self.edges
                          for endpoint in (edge.source, edge.target)
                          if endpoint not in self.nodes and endpoint not in {
                              "auto_mv_pro", "stats_aggregator", "publisher_gate",
                              "creative_genome_os"}})
        if unknown:
            raise ValueError(f"edges reference unknown graph nodes: {unknown}")

    def route_priority(self, target: str, asset_affinity: float = 0.5,
                       telemetry_freshness: float = 0.5) -> float:
        node = self.nodes[target]
        if not 0.0 <= asset_affinity <= 1.0:
            raise ValueError("asset_affinity must be in [0, 1]")
        if not 0.0 <= telemetry_freshness <= 1.0:
            raise ValueError("telemetry_freshness must be in [0, 1]")
        weighted = (0.30 * node.influence + 0.25 * node.affinity +
                    0.20 * node.propagation + 0.15 * asset_affinity +
                    0.10 * min(node.freshness, telemetry_freshness))
        return round(max(0.0, min(1.0, weighted)), 6)

    def recommend(self, asset_id: str, targets: Iterable[str],
                  asset_affinity: float = 0.5,
                  telemetry_freshness: float = 0.5,
                  limit: int = 10) -> list[RoutingDecision]:
        if not targets:
            return []
        if limit < 1:
            raise ValueError("limit must be positive")
        decisions = []
        for target in targets:
            if target not in self.nodes:
                raise ValueError(f"unknown routing target: {target}")
            priority = self.route_priority(target, asset_affinity, telemetry_freshness)
            node = self.nodes[target]
            decisions.append(RoutingDecision(asset_id, target, priority,
                                             {"epistemic_status": "INTERNAL_MODEL",
                                              "confidence": node.confidence,
                                              "freshness": min(node.freshness, telemetry_freshness),
                                              "external_algorithm_claim": False}))
        return sorted(decisions, key=lambda item: (-item.priority, item.target))[:limit]

    def apply_publisher_gate(self, asset_id: str, approved_content: bool,
                             human_confirmation: bool = False,
                             content_rights_verified: bool = False,
                             qc_passed: bool = False,
                             gate_status: GateStatus = "hold") -> GovernanceDecision:
        if gate_status not in {"approve", "hold", "reject"}:
            raise ValueError("invalid governance status")
        if gate_status == "reject":
            status, reason = "reject", "explicit rejection"
        elif not approved_content:
            status, reason = "hold", "content is not approved"
        elif not human_confirmation:
            status, reason = "hold", "human confirmation is missing"
        elif not content_rights_verified:
            status, reason = "hold", "content rights are not verified"
        elif not qc_passed:
            status, reason = "hold", "QC gate has not passed"
        else:
            status, reason = "approve", "all hard governance gates passed"
        return GovernanceDecision(asset_id, status, reason,
                                  datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, object]:
        return {"epistemic_status": "INTERNAL_MODEL",
                "constraints": {"external_algorithm_claims": False,
                                "guaranteed_reach_claims": False,
                                "oracle_decision_authority": False,
                                "autonomous_publish": False,
                                "autonomous_budget_change": False},
                "nodes": [asdict(node) for node in self.nodes.values()],
                "edges": [asdict(edge) for edge in self.edges],
                "feedback_loop": ["published_asset_events", "stats_aggregator",
                                  "validated_telemetry", "wissens_destillat",
                                  "distilled_rule", "brain_bug_hub"]}


def write_graph(destination: str | Path, graph: PlatformRelationsGraph | None = None) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    graph = graph or PlatformRelationsGraph()
    target.write_text(json.dumps(graph.to_dict(), indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return target
