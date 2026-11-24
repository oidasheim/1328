"""Master-art-director utilities for reviewable, local timeline compilation.

The module deliberately provides no hard-coded external paths or automatic
publishing behavior. Native acceleration and CUDA are optional and unavailable
when their ABI or schema cannot be verified.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import shutil
import subprocess
from typing import Any, Iterable, Sequence

import numpy as np


@dataclass(frozen=True)
class BarFeature:
    bar: int
    start: float
    end: float
    local_bpm: float
    section: str
    tension: float
    delta_energy: float
    sub_bass: tuple[float, ...]
    high_hat: tuple[float, ...]
    vocal_active: bool


@dataclass(frozen=True)
class CutEvent:
    event_id: int
    bar: int
    section: str
    start_frame: int
    end_frame: int
    clip_id: int | None
    file_path: str | None
    source_frame: int = 0
    blackout: bool = False
    match_cut: bool = False
    sub_bass: tuple[float, ...] = ()
    high_hat: tuple[float, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalized(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return np.array([], dtype=np.float32)
    finite = np.asarray(values, dtype=np.float64)
    finite = np.nan_to_num(finite, nan=0.0, posinf=0.0, neginf=0.0)
    ceiling = float(np.percentile(finite, 98))
    if ceiling <= 0:
        return np.zeros_like(finite, dtype=np.float32)
    return np.clip(finite / ceiling, 0.0, 1.0).astype(np.float32)


def analyze_audio_features(song: str | Path, fps: int = 30,
                           ) -> tuple[float, list[BarFeature], np.ndarray]:
    """Analyze audio into bars using optional librosa.

    Returns (global BPM, bars, mono waveform). Supplying no optional packages
    raises an actionable error rather than silently inventing musical features.
    """
    if fps <= 0:
        raise ValueError("fps must be positive")
    path = Path(song).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError("Install audio extras: pip install -e '.[audio]'") from exc

    signal, sr = librosa.load(str(path), sr=48000, mono=True)
    if len(signal) == 0:
        raise ValueError("Audio file contains no samples")

    harmonic, percussion = librosa.effects.hpss(signal)
    tempo, beat_frames = librosa.beat.beat_track(y=percussion, sr=sr, units="frames")
    bpm = float(np.asarray(tempo).reshape(-1)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    stft = np.abs(librosa.stft(signal, n_fft=2048, hop_length=512))
    frequencies = librosa.fft_frequencies(sr=sr, n_fft=2048)
    sub_mask = (frequencies >= 20) & (frequencies <= 90)
    high_mask = (frequencies >= 6000) & (frequencies <= 12000)

    sub_env = _normalized(np.mean(stft[sub_mask, :], axis=0))
    high_env = _normalized(np.mean(stft[high_mask, :], axis=0))
    flux = _normalized(librosa.onset.onset_strength(y=percussion, sr=sr, hop_length=512))
    harmonic_rms = _normalized(librosa.feature.rms(y=harmonic, hop_length=512)[0])
    env_times = librosa.frames_to_time(np.arange(len(sub_env)), sr=sr, hop_length=512)

    if len(beat_times) < 8:
        duration = len(signal) / sr
        bars_count = max(1, int(round(duration / (240.0 / bpm))))
        beat_times = np.arange(bars_count * 4) * (240.0 / bpm) / 4

    bars_count = max(0, len(beat_times) // 4)
    bars: list[BarFeature] = []
    previous_energy = 0.0

    for bar_index in range(bars_count):
        start = float(beat_times[bar_index * 4])
        end_index = min((bar_index + 1) * 4, len(beat_times) - 1)
        end = float(beat_times[end_index])
        if end <= start:
            end = start + 240.0 / bpm

        mask = (env_times >= start) & (env_times < end)
        if not np.any(mask):
            continue
        sub = float(np.mean(sub_env[mask]))
        high = float(np.mean(high_env[mask]))
        onset = float(np.mean(flux[mask]))
        vocal = float(np.mean(harmonic_rms[mask]))
        energy = 0.45 * sub + 0.30 * onset + 0.25 * high
        delta = energy - previous_energy
        previous_energy = energy
        tension = float(np.clip(0.30 * sub + 0.25 * high + 0.25 * onset + 0.20 * max(0.0, delta * 2), 0, 1))

        progress = bar_index / max(1, bars_count)
        if progress < 0.08 or (tension < 0.25 and bar_index < 8):
            section = "INTRO"
        elif progress > 0.92:
            section = "OUTRO"
        elif delta > 0.18 and tension > 0.50:
            section = "BUILDUP"
        elif delta < -0.22:
            section = "BREAKDOWN"
        elif tension >= 0.68:
            section = "DROP"
        else:
            section = "VERSE"

        frames = max(1, int(round((end - start) * fps)))
        times = np.linspace(start, end, frames, endpoint=False)
        sub_frame = np.interp(times, env_times, sub_env).astype(np.float32)
        high_frame = np.interp(times, env_times, high_env).astype(np.float32)
        bars.append(BarFeature(bar_index, start, end, 240.0 / (end - start),
                               section, tension, delta,
                               tuple(sub_frame), tuple(high_frame), vocal > 0.28))

    return bpm, bars, signal


@dataclass(frozen=True)
class ClipRecord:
    clip_id: int
    file_path: str
    scene_group_id: int = 0
    usable_frames: int = 0
    last_used_bar: int = -999
    shot_scale: float = 1.0
    mean_luma: float = 0.5
    dominant_hue: float = 180.0
    motion_x: float = 0.0
    motion_y: float = 0.0
    lip_motion: float = 0.0
    role: str = "SUBJECT"
    use_count: int = 0


def load_clip_records(database: str | Path) -> list[ClipRecord]:
    """Read a DuckDB clip_master_index table without implicit hard-coded paths."""
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("Install DuckDB: pip install '.[semantic]' or duckdb") from exc
    path = Path(database).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    con = duckdb.connect(str(path), read_only=True)
    try:
        required = """
            SELECT clip_id, file_path, scene_group_id, usable_frames,
                   last_used_bar, shot_scale, mean_luma, dominant_hue,
                   motion_vec_x, motion_vec_y, lip_motion_score,
                   semantic_role, use_count
            FROM clip_master_index
            WHERE usable_frames >= 12
            ORDER BY clip_id
        """
        rows = con.execute(required).fetchall()
    finally:
        con.close()

    records = []
    for row in rows:
        records.append(ClipRecord(
            int(row[0]), str(row[1]), int(row[2]), int(row[3]), int(row[4]),
            float(row[5]), float(row[6]), float(row[7]), float(row[8]), float(row[9]),
            float(row[10]), str(row[11]), int(row[12]),
        ))
    return records


def aligned_array(shape: Sequence[int], dtype: type, alignment: int = 32) -> np.ndarray:
    nbytes = math.prod(shape) * np.dtype(dtype).itemsize
    storage = np.empty(nbytes + alignment, dtype=np.uint8)
    offset = (-storage.ctypes.data) % alignment
    return storage[offset:offset + nbytes].view(dtype).reshape(shape)


def compile_timeline(bars: Iterable[BarFeature], clips: Sequence[ClipRecord],
                    fps: int = 30, cooldown_bars: int = 16,
                    blackout_last_frames: int = 4) -> list[CutEvent]:
    """Compile a Python reference timeline; no hardware acceleration is assumed."""
    if fps <= 0 or cooldown_bars < 1 or blackout_last_frames < 0:
        raise ValueError("fps/cooldown/blackout values are invalid")
    bars = list(bars)
    if not bars:
        raise ValueError("No bars supplied")
    if not clips:
        raise ValueError("No clips supplied")

    events: list[CutEvent] = []
    use_count_limit = max(1, int(np.percentile([clip.use_count for clip in clips], 66.7)))
    used_scene_groups: list[int] = []
    event_id = 0

    for bar in bars:
        if bar.section == "BUILDUP": subdivisions = (4.0,)
        elif bar.section == "DROP": subdivisions = (1.5, 1.5, 1.0) if bar.tension < 0.85 else (1.0, .5, .5, 1.0, .5, .5)
        elif bar.section in ("INTRO", "BREAKDOWN", "OUTRO"): subdivisions = (4.0,)
        else: subdivisions = (2.0, 2.0)

        beat_cursor = 0.0
        for sub in subdivisions:
            start_time = bar.start + (beat_cursor / 4.0) * (bar.end - bar.start)
            end_time = bar.start + ((beat_cursor + sub) / 4.0) * (bar.end - bar.start)
            start = max(0, int(round(start_time * fps)))
            end = max(start, int(round(end_time * fps)) - 1)

            candidate_segments: list[tuple[int, int, bool]]
            if bar.section == "BUILDUP" and sub == subdivisions[-1] and end - start + 1 > blackout_last_frames:
                main_end = end - blackout_last_frames
                candidate_segments = [(start, main_end, False), (main_end + 1, end, True)]
            else:
                candidate_segments = [(start, end, False)]

            for segment_start, segment_end, blackout in candidate_segments:
                length = segment_end - segment_start + 1
                sub = bar.sub_bass[segment_start - int(round(bar.start * fps)):segment_start - int(round(bar.start * fps)) + length]
                high = bar.high_hat[segment_start - int(round(bar.start * fps)):segment_start - int(round(bar.start * fps)) + length]
                sub = sub if len(sub) == length else sub + (0.0,) * (length - len(sub))
                high = high if len(high) == length else high + (0.0,) * (length - len(high))

                if blackout:
                    events.append(CutEvent(event_id, bar.bar, bar.section, segment_start,
                                           segment_end, None, None, 0, True, False, sub[:length], high[:length]))
                    event_counter = event_id + 1
                    event_id = event_counter
                    continue

                eligible = []
                for clip in clips:
                    scene_recent = clip.scene_group_id in used_scene_groups[-32:] and clip.scene_group_id != 0
                    cooldown = clip.use_count > use_count_limit
                    cool = bar.bar - clip.last_used_bar >= cooldown_bars
                    if scene_recent or cooldown or not cool:
                        continue
                    if clip.usable_frames < length:
                        continue
                    tag_match = clip.role in ("ACTION" if bar.section == "DROP" else "SUBJECT")
                    luma_tension = 1.0 - abs(clip.mean_luma - bar.tension)
                    score = (0.55 if tag_match else 0.25) + 0.45 * max(0.0, luma_tension)
                    eligible.append((score, clip))
                if not eligible:
                    eligible = [(0.0, clip) for clip in clips if clip.usable_frames >= length]
                if not eligible:
                    raise RuntimeError("No clip is usable for the required segment length")

                _, clip = sorted(eligible, key=lambda pair: (-pair[0], pair[1].clip_id))[0]
                used_scene_groups.append(clip.scene_group_id)
                events.append(CutEvent(event_id, bar.bar, bar.section, segment_start,
                                       segment_end, clip.clip_id, clip.file_path,
                                       clip.last_used_bar + 1 if clip.last_used_bar >= 0 else 0,
                                       False, False, sub[:length], high[:length]))
                event_id += 1
            beat_cursor += sub
    return events


def write_timeline(events: Sequence[CutEvent], output: str | Path) -> Path:
    target = Path(output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "events": [event.to_dict() for event in events]}
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def render_timeline(events: Sequence[CutEvent], audio: str | Path, output: str | Path,
                    fps: int = 30, width: int = 1920, height: int = 1080,
                    cpu_only: bool = False) -> Path:
    """Render with FFmpeg. This baseline never enables strobe effects or CUDA."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required on PATH")
    source_audio = Path(audio).expanduser().resolve()
    if not source_audio.is_file():
        raise FileNotFoundError(source_audio)
    target = Path(output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite: {target}")

    temp_dir = target.parent / f".{target.stem}_art_director"
    temp_dir.mkdir(parents=True, exist_ok=True)
    clips = list(dict.fromkeys(str(Path(e.file_path).resolve()) for e in events if e.file_path))
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source_audio)]
    for clip in clips:
        command.extend(["-i", clip])

    filters: list[str] = []
    labels: list[str] = []
    for index, event in enumerate(events):
        label = f"v{index}"
        duration = max(1.0 / fps, (event.end_frame - event.start_frame + 1) / fps)
        if event.blackout:
            filters.append(f"color=c=black:s={width}x{height}:r={fps}:d={duration:.6f},format=yuv420p[{label}]")
        else:
            source = clips.index(str(Path(event.file_path).resolve())) + 1
            filters.append(
                f"[{source}:v]trim=start={event.source_frame / fps:.6f}:duration={duration:.6f},"
                f"setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},fps={fps},format=yuv420p[{label}]"
            )
        labels.append(f"[{label}]")
    filters.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[outv]")

    encoder = "libx264"
    if not cpu_only:
        encoder_probe = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True,
                                       text=True, check=False).stdout
        if "h264_nvenc" in encoder_probe:
            encoder = "h264_nvenc"
    command.extend(["-filter_complex", ";".join(filters), "-map", "[outv]", "-map", "0:a:0?",
                    "-map_metadata", "-1", "-map_chapters", "-1", "-sn", "-dn",
                    "-c:v", encoder])
    command += ["-preset", "p4", "-cq", "19"] if encoder == "h264_nvenc" else ["-preset", "medium", "-crf", "20"]
    command += ["-af", "loudnorm=I=-14.0:TP=-1.0:LRA=11",
                "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", str(target)]
    subprocess.run(command, check=True)
    return target
