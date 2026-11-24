import json
from pathlib import Path

import pytest

from synapse.brain_bug import BrainBugRegistry, TelemetryEvent
from synapse.platform_relations import (PlatformRelationsGraph,
                                        write_graph)


def test_platform_recommendations_are_internal_and_sorted():
    graph = PlatformRelationsGraph()
    decisions = graph.recommend("asset-1", ["tiktok", "beatstars"], 0.8, 0.7)
    assert decisions
    assert decisions == sorted(decisions, key=lambda item: (-item.priority, item.target))
    assert all(item.evidence["epistemic_status"] == "INTERNAL_MODEL" for item in decisions)
    assert all(item.evidence["external_algorithm_claim"] is False for item in decisions)


def test_publisher_gate_requires_all_hard_conditions():
    graph = PlatformRelationsGraph()
    held = graph.apply_publisher_gate("asset-1", True, False, True, True)
    assert held.status == "hold"
    approved = graph.apply_publisher_gate("asset-1", True, True, True, True)
    assert approved.status == "approve"
    rejected = graph.apply_publisher_gate("asset-1", True, True, True, True, "reject")
    assert rejected.status == "reject"


def test_manifest_and_telemetry_validation(tmp_path):
    registry = BrainBugRegistry(tmp_path)
    manifest = registry.manifest()
    assert "wissens_destillat" in json.dumps(manifest)
    event = TelemetryEvent("asset-1", "2026-11-24T12:00:00Z", "tiktok",
                           {"views": 100, "completion": 0.4}, "local_fixture")
    validated = registry.validate_telemetry(event)
    assert validated["epistemic_status"] == "GROUND_TRUTH_CANDIDATE"


def test_graph_export(tmp_path):
    target = write_graph(tmp_path / "platform.json")
    data = json.loads(target.read_text())
    assert data["epistemic_status"] == "INTERNAL_MODEL"
    assert data["constraints"]["autonomous_publish"] is False
