import json

from synapse.viral_evidence import HYPOTHESES, SOURCES, evidence_manifest, write_evidence


def test_evidence_manifest_has_sources_and_no_prediction_claim():
    manifest = evidence_manifest()
    assert len(SOURCES) >= 5
    assert len(HYPOTHESES) >= 5
    assert manifest["status"] == "reference_notes_not_predictions"


def test_write_evidence_exports_complete_source_records(tmp_path):
    target = write_evidence(tmp_path / "viral_evidence.json")
    data = json.loads(target.read_text())
    assert data["sources"]
    assert all(source["url"] for source in data["sources"])
