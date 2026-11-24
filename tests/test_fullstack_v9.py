from src.fullstack_v9_workflow import (PROFILES, audit_repository, resolve_path,
                                       run_fullstack, stage_resolution)


def test_profile_stage_lists_are_resolved():
    assert "S5" in PROFILES["full"]
    assert "S8" not in PROFILES["full"]
    assert "S8" in PROFILES["sync"]


def test_dry_run_run_writes_ledger(tmp_path):
    ledger = tmp_path / "report.json"
    report = run_fullstack("full", root=tmp_path, ledger=str(ledger), dry_run=True)
    assert ledger.exists()
    assert report["run"]["status"] == "pass-dry-run"
    assert report["constraints"]["external_publish"] is False
    assert report["constraints"]["render_execution"] is False


def test_audit_finds_hardcoded_paths_and_publish_call(tmp_path):
    bat = tmp_path / "legacy.bat"
    bat.write_text("set ROOT=E:\\Music\nposteverywhere --publish\n", encoding="utf-8")
    audit = audit_repository(tmp_path)
    assert audit["bat_count"] == 1
    assert len(audit["findings"]) == 2


def test_sync_profile_is_blocked_outside_dry_run(tmp_path):
    try:
        run_fullstack("sync", root=tmp_path, ledger=str(tmp_path / "report.json"), dry_run=False)
    except RuntimeError:
        pass
    else:
        raise AssertionError("external stage must be blocked")


def test_invalid_profile_is_rejected(tmp_path):
    try:
        stage_resolution(tmp_path, "unknown")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid profile must be rejected")
