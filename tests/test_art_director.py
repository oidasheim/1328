import json

from weedit_native.art_director import BuildConfig, run_build
from weedit_native.models import RenderAST, RenderShot


def test_build_pipeline_emits_reports_and_ledger_without_render(tmp_path, monkeypatch):
    song = tmp_path / "song.wav"
    song.write_bytes(b"not decoded by mocked compiler")
    clips = tmp_path / "clips"
    clips.mkdir()
    video = clips / "clip.mp4"
    video.write_bytes(b"placeholder")
    db = tmp_path / "database" / "genome.sqlite3"

    monkeypatch.setattr("weedit_native.art_director.scan_directory", lambda *_: {"indexed": 1, "cached": 0, "skipped": 0})
    def fake_compile(*args, **kwargs):
        return RenderAST(str(song), (RenderShot(str(video), 0, 1, 0),), 1,
                         width=1080, height=1920, fps=30)
    monkeypatch.setattr("weedit_native.art_director.compile_project", fake_compile)

    report = run_build(BuildConfig(song, clips, db, tmp_path / "out.mp4", tmp_path / "reports"))
    assert report["render_id"]
    assert report["stages"][-1]["status"] == "not-requested"
    assert (tmp_path / "reports" / f"song-{report['render_id']}.ast.json").exists()
    assert (tmp_path / "reports" / f"song-{report['render_id']}.html").exists()
    manifest = json.loads((tmp_path / "reports" / f"song-{report['render_id']}.manifest.json").read_text())
    assert manifest["limitations"]


def test_build_config_rejects_odd_dimensions(tmp_path):
    config = BuildConfig(tmp_path / "a", tmp_path / "b", width=101, height=200)
    try:
        config.validate()
    except ValueError as exc:
        assert "even" in str(exc)
    else:
        raise AssertionError("odd dimensions should be rejected")
