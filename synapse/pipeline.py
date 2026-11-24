from dataclasses import dataclass
from typing import Protocol

from .ledger import EventLedger
from .models import ReleaseManifest, Track


class Node(Protocol):
    name: str

    def run(self, manifest: ReleaseManifest) -> None: ...


@dataclass
class Kairo:
    name: str = "KAIRO"

    def run(self, manifest: ReleaseManifest) -> None:
        manifest.add_stage("audio_analysis", deliverables=["beat_grid", "energy_curve", "stems"])


@dataclass
class Vega:
    name: str = "VEGA"

    def run(self, manifest: ReleaseManifest) -> None:
        manifest.add_stage("mastering_qc", targets={"lufs": -14, "true_peak_db": -0.5})
        manifest.approvals_required.append("audio_qc")


@dataclass
class Jinx:
    name: str = "JINX"

    def run(self, manifest: ReleaseManifest) -> None:
        manifest.add_stage("visuals", formats=["16:9", "9:16", "1:1"], anti_repeat=True)
        manifest.approvals_required.append("content_review")


@dataclass
class Orion:
    name: str = "ORION"

    def run(self, manifest: ReleaseManifest) -> None:
        manifest.add_stage("distribution_plan", channels=["DSP", "sync", "direct_to_fan"])
        manifest.approvals_required.append("distribution_review")


@dataclass
class Atlas:
    name: str = "ATLAS"

    def run(self, manifest: ReleaseManifest) -> None:
        manifest.add_stage("finance_report", budget_status="approval_required")
        manifest.approvals_required.extend(["ad_budget", "royalty_settlement"])


class SynapsePipeline:
    def __init__(self, ledger: EventLedger | None = None, nodes: list[Node] | None = None) -> None:
        self.ledger = ledger or EventLedger()
        self.nodes = nodes or [Kairo(), Vega(), Jinx(), Orion(), Atlas()]

    def plan(self, track: Track) -> ReleaseManifest:
        manifest = ReleaseManifest(track=track)
        for node in self.nodes:
            node.run(manifest)
            self.ledger.record(str(track.path), node.name, "stage_complete", {"stages": manifest.stages})
        manifest.status = "awaiting_approval"
        self.ledger.record(str(track.path), "SYNAPSE", "plan_complete", manifest.to_dict())
        return manifest
