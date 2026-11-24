import pytest

from weedit_native.catalog_guard import catalog_locked, usage_lock_threshold
from weedit_native.models import RenderAST, RenderShot
from weedit_native.optimizer import optimize_render
from weedit_native.passes import run_pass_pipeline
from weedit_native.replay import ReplayLedger, sha256_object
from weedit_native.styles import install_style


def test_ten_pass_pipeline_is_contiguous_and_deterministic():
    ast = RenderAST("song.mp3", (
        RenderShot("a.mp4", 0, 0.5, 0, camera="push", color="warm", score=0.8),
        RenderShot("b.mp4", 0, 0.5, 0.5, camera="steady", color="natural", score=0.6),
    ), 1)
    result, evidence = run_pass_pipeline(ast)
    assert evidence["pass_count"] == 10
    assert result.shots[0].timeline_start == 0
    assert result.shots[1].timeline_start == 0.5


def test_optimizer_rejects_sub_minimum_after_passes():
    ast = RenderAST("song.mp3", (RenderShot("a.mp4", 0, 0.05, 0),), 1)
    with pytest.raises(ValueError):
        optimize_render(ast)


def test_catalog_lock_uses_percentile_threshold():
    threshold = usage_lock_threshold([0, 1, 2, 100])
    assert catalog_locked(101, threshold)


def test_style_install_and_replay(tmp_path):
    style = install_style(tmp_path, "cinematic")
    assert (style / "package.json").exists()
    ledger = ReplayLedger(tmp_path / "replay.db")
    shot = RenderShot("a.mp4", 0, 1, 0, score=0.7)
    ledger.record("r1", "s1", shot, ["a", "b"], {"passes": []}, sha256_object({"song": "a"}))
    assert ledger.replay("s1")["clip_path"] == "a.mp4"
    ledger.close()
