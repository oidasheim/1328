"""Local phoneme-to-MAR utilities and bounded lip-motion matching.

This module does not identify people or infer identity. It operates only on
caller-supplied phoneme alignments and numeric mouth-aperture (MAR) curves.
WhisperX integration is intentionally an adapter boundary: model loading and
transcription are heavyweight and should be performed explicitly by the caller.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping, Sequence

import numpy as np


PHONEME_TO_MAR: dict[str, float] = {
    "B": 0.02, "P": 0.02, "M": 0.03, "SIL": 0.04, "SP": 0.04,
    "AA": 0.68, "AE": 0.62, "AH": 0.58, "AW": 0.65, "AY": 0.60, "A": 0.65,
    "OW": 0.34, "UW": 0.25, "UH": 0.30, "W": 0.22, "O": 0.35, "U": 0.26,
    "F": 0.14, "V": 0.15, "S": 0.18, "Z": 0.19, "SH": 0.22, "ZH": 0.22,
    "IY": 0.32, "IH": 0.36, "E": 0.42, "I": 0.34, "T": 0.24, "D": 0.26,
    "N": 0.25, "L": 0.30, "TH": 0.28, "DH": 0.28, "K": 0.35, "G": 0.36,
    "NG": 0.28, "R": 0.32, "HH": 0.40, "CH": 0.25, "JH": 0.26,
}
PLOSIVES = {"B", "P", "M"}


@dataclass(frozen=True)
class LipSyncMatch:
    score: float
    speed_warp: float
    source_offset: int
    distance: float
    evaluated_offsets: int


def _curve(values: Sequence[float] | np.ndarray, name: str) -> np.ndarray:
    result = np.asarray(values, dtype=np.float32)
    if result.ndim != 1:
        raise ValueError(f"{name} must be a one-dimensional curve")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return np.clip(result, 0.0, 1.0)


def phonemes_to_mar(alignments: Iterable[Mapping[str, object]], duration: float,
                    fps: int = 60, *, plosive_lead_frames: float = 1.5,
                    smoothing: bool = True) -> np.ndarray:
    """Convert aligned phoneme intervals into a frame-sampled MAR target.

    Each record must have ``start``, ``end`` and ``phoneme`` keys. The lead is
    applied to interval onset only for bilabial closures; timing is clamped to
    the song bounds. Unknown phonemes use a neutral, mildly open target.
    """
    if not math.isfinite(duration) or duration <= 0 or fps <= 0:
        raise ValueError("duration and fps must be positive and finite")
    if not math.isfinite(plosive_lead_frames) or plosive_lead_frames < 0:
        raise ValueError("plosive_lead_frames must be non-negative and finite")
    count = int(math.ceil(duration * fps)) + 1
    target = np.full(count, 0.04, dtype=np.float32)
    for item in alignments:
        try:
            start = float(item["start"])
            end = float(item["end"])
            token = str(item["phoneme"]).strip().upper()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("alignment entries require numeric start/end and phoneme") from exc
        if not math.isfinite(start) or not math.isfinite(end) or end < start:
            raise ValueError("phoneme intervals must have finite start <= end")
        if not token:
            continue
        start -= plosive_lead_frames / fps if token in PLOSIVES else 0.0
        start = max(0.0, start)
        end = min(duration, max(end, start + 1.0 / fps))
        first = min(count - 1, max(0, int(round(start * fps))))
        last = min(count - 1, max(first, int(round(end * fps))))
        target[first:last + 1] = np.maximum(
            target[first:last + 1], PHONEME_TO_MAR.get(token, 0.32)
        )
    if smoothing and count >= 3:
        # A normalized three-tap filter preserves bounded values and reduces
        # abrupt frame edges without shifting the alignment by a frame.
        padded = np.pad(target, (1, 1), mode="edge")
        target = 0.25 * padded[:-2] + 0.50 * padded[1:-1] + 0.25 * padded[2:]
    return np.asarray(np.clip(target, 0.0, 1.0), dtype=np.float32)


def formant_energy_mar(audio_path: str, duration: float, fps: int = 60,
                       *, sample_rate: int = 48_000) -> np.ndarray:
    """Build a non-phonetic mouth-motion proxy from 300–3400 Hz energy.

    This is only an energy proxy, not phoneme recognition or a claim of accurate
    lip synchronization. Requires the optional ``audio`` extra (librosa).
    """
    if duration <= 0 or fps <= 0 or sample_rate <= 0:
        raise ValueError("duration, fps and sample_rate must be positive")
    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError("Install audio support with: pip install -e '.[audio]'") from exc
    signal, sr = librosa.load(audio_path, sr=sample_rate, mono=True, duration=duration)
    count = int(math.ceil(duration * fps)) + 1
    if signal.size == 0:
        return np.full(count, 0.04, dtype=np.float32)
    harmonic, _ = librosa.effects.hpss(signal)
    spectrum = np.abs(librosa.stft(harmonic, n_fft=2048, hop_length=512))
    frequencies = librosa.fft_frequencies(sr=sr, n_fft=2048)
    mask = (frequencies >= 300) & (frequencies <= 3400)
    energy = np.mean(spectrum[mask], axis=0) if np.any(mask) else np.zeros(spectrum.shape[1])
    ceiling = float(np.percentile(energy, 97)) if energy.size else 0.0
    normalized = np.clip(energy / max(ceiling, 1e-8), 0.0, 1.0)
    times = librosa.frames_to_time(np.arange(len(normalized)), sr=sr, hop_length=512)
    target_times = np.arange(count, dtype=np.float64) / fps
    mar = 0.04 + 0.60 * np.interp(target_times, times, normalized,
                                  left=float(normalized[0]), right=float(normalized[-1]))
    return np.asarray(np.clip(mar, 0.04, 0.64), dtype=np.float32)


def _banded_dtw_distance(target: np.ndarray, source: np.ndarray, radius: int) -> float:
    """Normalized 1-D DTW distance, using O(radius) memory."""
    n = len(target)
    inf = float("inf")
    previous = np.full(n + 1, inf, dtype=np.float64)
    previous[0] = 0.0
    for i in range(1, n + 1):
        current = np.full(n + 1, inf, dtype=np.float64)
        lo, hi = max(1, i - radius), min(n, i + radius)
        for j in range(lo, hi + 1):
            cost = abs(float(target[i - 1]) - float(source[j - 1]))
            current[j] = cost + min(previous[j], current[j - 1], previous[j - 1])
        previous = current
    return float(previous[n] / max(1, n))


def dtw_lipsync_match(clip_mar: Sequence[float] | np.ndarray,
                      target_mar: Sequence[float] | np.ndarray, *,
                      warp_candidates: Sequence[float] = (0.94, 0.97, 1.0, 1.03, 1.06),
                      max_offsets: int = 24, radius: int = 2) -> LipSyncMatch:
    """Search bounded source offsets and speed factors for a MAR curve match.

    ``speed_warp`` is source frames consumed per output frame. Values above 1
    speed up source playback; below 1 slow it down. Coarse speed candidates and
    a bounded offset grid keep runtime finite. The score is a normalized
    descriptive similarity, not a probability or model confidence.
    """
    source = _curve(clip_mar, "clip_mar")
    target = _curve(target_mar, "target_mar")
    if max_offsets < 1 or radius < 0:
        raise ValueError("max_offsets must be positive and radius non-negative")
    candidates = tuple(float(value) for value in warp_candidates)
    if not candidates or any(not math.isfinite(v) or not 0.94 <= v <= 1.06 for v in candidates):
        raise ValueError("warp candidates must lie in the supported [0.94, 1.06] range")
    if len(target) < 3 or len(source) < len(target):
        return LipSyncMatch(0.0, 1.0, 0, 1.0, 0)

    best = LipSyncMatch(0.0, 1.0, 0, 1.0, 0)
    evaluated = 0
    for alpha in candidates:
        needed = max(3, int(round((len(target) - 1) * alpha)) + 1)
        if needed > len(source):
            continue
        max_start = len(source) - needed
        starts = np.unique(np.linspace(0, max_start, min(max_offsets, max_start + 1), dtype=np.int64))
        for start in starts:
            window = source[int(start):int(start) + needed]
            source_positions = np.linspace(0.0, float(needed - 1), len(target))
            resampled = np.interp(source_positions, np.arange(needed), window)
            distance = _banded_dtw_distance(target, resampled, radius)
            score = float(np.clip(1.0 - distance, 0.0, 1.0))
            evaluated += 1
            if (score > best.score or
                    (score == best.score and (abs(alpha - 1.0), int(start)) <
                     (abs(best.speed_warp - 1.0), best.source_offset))):
                best = LipSyncMatch(score, alpha, int(start), distance, evaluated)
    return LipSyncMatch(best.score, best.speed_warp, best.source_offset,
                        best.distance, evaluated)
