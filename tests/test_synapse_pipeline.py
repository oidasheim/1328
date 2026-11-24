import json

from synapse.models import Track
from synapse.pipeline import SynapsePipeline


def test_pipeline_creates_approval_gates(tmp_path):
    ledger = tmp_path / "events.db"
    pipeline = SynapsePipeline()
    manifest = pipeline.plan(Track(tmp_path / "song.mp3", title="Test Song"))
    assert manifest.status == "awaiting_approval"
    assert "audio_qc" in manifest.approvals_required
    assert "ad_budget" in manifest.approvals_required
    assert "visuals" in manifest.stages


def test_manifest_is_serializable(tmp_path):
    manifest = SynapsePipeline().plan(Track(tmp_path / "song.mp3"))
    json.dumps(manifest.to_dict())
