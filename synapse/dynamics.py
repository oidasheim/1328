"""Configuration and validation primitives for SYNAPSE Audio Dynamics."""
from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
from typing import Iterable


@dataclass(frozen=True)
class DynamicsConfig:
    target_fps: int = 60
    width: int = 1920
    height: int = 1080
    audio_sample_rate: int = 48_000
    nvenc_encoder: str = "h264_nvenc"
    video_preset: str = "p4"
    video_cq: int = 19
    catalog_lock_percentile: float = 66.7
    loudness_i: float = -14.0
    true_peak: float = -1.0
    audio_bitrate: str = "320k"

    def __post_init__(self) -> None:
        if self.target_fps <= 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("video dimensions and FPS must be positive")
        if self.audio_sample_rate <= 0 or self.video_cq < 0:
            raise ValueError("audio sample rate and CQ must be positive")
        if not 0 < self.catalog_lock_percentile <= 100:
            raise ValueError("catalog lock percentile must be in (0, 100]")

    def ffmpeg_video_args(self, *, cpu_only: bool = False) -> list[str]:
        if cpu_only:
            return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22"]
        return ["-c:v", self.nvenc_encoder, "-preset", self.video_preset,
                "-rc", "vbr", "-cq", str(self.video_cq)]

    def ffmpeg_audio_args(self) -> list[str]:
        return ["-af", f"loudnorm=I={self.loudness_i}:TP={self.true_peak}:LRA=11",
                "-c:a", "aac", "-b:a", self.audio_bitrate, "-ar", str(self.audio_sample_rate)]


def available_tools() -> dict[str, str | bool]:
    return {"ffmpeg": shutil.which("ffmpeg") or False,
            "python": os.sys.executable,
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "")}


def validate_affinity(cores: Iterable[int], cpu_count: int | None = None) -> tuple[int, ...]:
    count = cpu_count if cpu_count is not None else (os.cpu_count() or 1)
    result = tuple(dict.fromkeys(int(core) for core in cores))
    if any(core < 0 or core >= count for core in result):
        raise ValueError(f"affinity cores must be in range 0..{count - 1}")
    return result
