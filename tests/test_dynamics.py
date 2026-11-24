import pytest

from synapse.dynamics import DynamicsConfig, validate_affinity
from synapse.fullstack import FullstackConfig, StageStatus, bump_version, run


def test_dynamics_args_and_affinity():
    config = DynamicsConfig()
    assert "h264_nvenc" in config.ffmpeg_video_args()
    assert config.ffmpeg_audio_args()[-1] == "48000"
    assert validate_affinity([0, 1, 1], cpu_count=4) == (0, 1)
    with pytest.raises(ValueError):
        validate_affinity([4], cpu_count=4)


def test_bump_version():
    assert bump_version("1.2.3", "minor") == "1.3.0"
    with pytest.raises(ValueError):
        bump_version("1.2", "patch")


def test_fullstack_dry_run_writes_report(tmp_path):
    (tmp_path / "music").mkdir()
    (tmp_path / "clips").mkdir()
    (tmp_path / "music" / "song.mp3").touch()
    (tmp_path / "clips" / "clip.mp4").touch()
    report = run(FullstackConfig(str(tmp_path)), execute_render=False)
    assert report.version == "0.0.1"
    assert all(stage.status != StageStatus.FAIL for stage in report.stages[:2])
    assert (tmp_path / "reports" / "fullstack-latest.json").exists()
