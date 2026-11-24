"""Song source compiler. Librosa is optional; tests can inject beat data."""
from __future__ import annotations

from pathlib import Path

from .models import Section, SongAST


def compile_song(path: str | Path, *, bpm: float | None = None,
                 beat_times: list[float] | None = None,
                 duration: float | None = None) -> SongAST:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    warnings: list[str] = []
    energy_curve: list[tuple[float, float]] = []
    if beat_times is None or duration is None or bpm is None:
        try:
            import librosa
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("Audio analysis requires `pip install -e '.[audio]'` or explicit bpm, beat_times, duration") from exc
        signal, sr = librosa.load(str(source), sr=22050, mono=True)
        duration = float(librosa.get_duration(y=signal, sr=sr))
        tempo, frames = librosa.beat.beat_track(y=signal, sr=sr, units="frames")
        if bpm is None:
            bpm = float(np.asarray(tempo).reshape(-1)[0])
        if beat_times is None:
            beat_times = [float(t) for t in librosa.frames_to_time(frames, sr=sr)]
        rms = librosa.feature.rms(y=signal)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
        scale = float(np.max(rms)) or 1.0
        energy_curve = [(float(t), float(v / scale)) for t, v in zip(times, rms)]
    assert duration is not None
    if duration <= 0:
        raise ValueError("duration must be positive")
    beats = sorted(set(float(t) for t in (beat_times or []) if 0 <= float(t) < duration))
    if not beats:
        warnings.append("No beat positions supplied or detected; using regular tempo grid when available.")
        if bpm and bpm > 0:
            step = 60.0 / bpm
            beats = [i * step for i in range(int(duration / step))]
        else:
            beats = [0.0]
    if not energy_curve:
        # Deterministic neutral fallback: downstream modules can still compile
        # a timeline without pretending that energy was measured.
        energy_curve = [(0.0, 0.5), (float(duration), 0.5)]
        warnings.append("Energy curve unavailable; neutral energy is used.")
    sections = _sections(beats, energy_curve, float(duration))
    return SongAST(str(source), float(duration), float(bpm) if bpm else None,
                   tuple(beats), tuple(sections), tuple(energy_curve), tuple(warnings))


def _sections(beats: list[float], curve: list[tuple[float, float]], duration: float) -> list[Section]:
    """Produce transparent 8-beat phrases and simple relative-energy labels."""
    boundaries = [0.0]
    boundaries.extend(beats[i] for i in range(8, len(beats), 8) if beats[i] > boundaries[-1])
    boundaries.append(duration)
    raw = []
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
        values = [value for time, value in curve if start <= time < end]
        energy = sum(values) / len(values) if values else 0.5
        raw.append((start, end, energy, index))
    midpoint = sorted(item[2] for item in raw)[len(raw) // 2] if raw else 0.5
    return [Section("high_energy" if energy >= midpoint else "low_energy", start, end, energy)
            for start, end, energy, _ in raw if end > start]
