"""Exact rational utilities for polyrhythm, polymeter, and meter timelines.

Times are expressed against quarter-note BPM. A denominator of 8 means that
one notated beat is an eighth note (half a quarter-note); it is not called an
irrational meter. Fractions are retained until presentation to avoid drift.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import gcd, lcm


@dataclass(frozen=True)
class PolyrhythmGrid:
    ratio_a: int
    ratio_b: int
    subdivisions: int
    attacks_a: tuple[Fraction, ...]
    attacks_b: tuple[Fraction, ...]
    coincidences: tuple[Fraction, ...]


def lcm_polyrhythm_grid(ratio_a: int, ratio_b: int) -> PolyrhythmGrid:
    """Return normalized attack positions and the exact shared-cycle grid.

    For 3:2, each voice has three and two evenly spaced attacks over one
    common cycle. The normalized cycle uses lcm(3, 2) grid subdivisions.
    """
    if ratio_a <= 0 or ratio_b <= 0:
        raise ValueError("Polyrhythm ratios must be positive integers")
    attacks_a = tuple(Fraction(i, ratio_a) for i in range(ratio_a))
    attacks_b = tuple(Fraction(i, ratio_b) for i in range(ratio_b))
    coincidences = tuple(sorted(set(attacks_a).intersection(attacks_b)))
    return PolyrhythmGrid(
        ratio_a, ratio_b, lcm(ratio_a, ratio_b),
        attacks_a, attacks_b, coincidences,
    )


@dataclass(frozen=True)
class MeterSpec:
    numerator: int
    denominator: int
    bpm: float
    fps: float
    quarter_notes_per_bar: Fraction
    seconds_per_bar: float
    frames_per_bar: Fraction
    bar_is_exact_integer_frames: bool


def resolve_meter(numerator: int, denominator: int, bpm: float, fps: float) -> MeterSpec:
    """Resolve bar duration and frame alignment for a time signature.

    BPM is quarter-notes per minute. For compound meters such as 6/8, callers
    may supply a dotted-quarter BPM convention explicitly by converting it to
    quarter-note BPM first.
    """
    if numerator <= 0 or denominator <= 0:
        raise ValueError("Meter numerator and denominator must be positive")
    if bpm <= 0 or fps <= 0:
        raise ValueError("BPM and FPS must be positive")
    quarter_notes = Fraction(numerator * 4, denominator)
    frames = quarter_notes * Fraction(str(fps)) * Fraction(60, 1) / Fraction(str(bpm))
    seconds = float(quarter_notes) * 60.0 / float(bpm)
    return MeterSpec(
        numerator=numerator,
        denominator=denominator,
        bpm=float(bpm),
        fps=float(fps),
        quarter_notes_per_bar=quarter_notes,
        seconds_per_bar=seconds,
        frames_per_bar=frames,
        bar_is_exact_integer_frames=frames.denominator == 1,
    )


@dataclass(frozen=True)
class PolymeterCycle:
    meter_a: tuple[int, int]
    meter_b: tuple[int, int]
    cycle_quarter_notes: Fraction
    bars_a: Fraction
    bars_b: Fraction
    re_align_seconds: float
    re_align_frames: Fraction


def _quarter_notes_per_bar(meter: tuple[int, int]) -> Fraction:
    numerator, denominator = meter
    if numerator <= 0 or denominator <= 0:
        raise ValueError("Meter values must be positive")
    return Fraction(numerator * 4, denominator)


def _rational_lcm(a: Fraction, b: Fraction) -> Fraction:
    """Least positive rational multiple shared by a and b."""
    numerator_lcm = lcm(a.numerator, b.numerator)
    denominator_gcd = gcd(a.denominator, b.denominator)
    return Fraction(numerator_lcm, denominator_gcd)


def compute_polymeter_cycle(
    meter_a: tuple[int, int], meter_b: tuple[int, int], bpm: float, fps: float
) -> PolymeterCycle:
    """Compute the exact downbeat re-alignment cycle of two bar lengths."""
    if bpm <= 0 or fps <= 0:
        raise ValueError("BPM and FPS must be positive")
    length_a = _quarter_notes_per_bar(meter_a)
    length_b = _quarter_notes_per_bar(meter_b)
    cycle = _rational_lcm(length_a, length_b)
    frames = cycle * Fraction(str(fps)) * Fraction(60, 1) / Fraction(str(bpm))
    return PolymeterCycle(
        meter_a=meter_a,
        meter_b=meter_b,
        cycle_quarter_notes=cycle,
        bars_a=cycle / length_a,
        bars_b=cycle / length_b,
        re_align_seconds=float(cycle) * 60.0 / float(bpm),
        re_align_frames=frames,
    )


def generate_meter_timeline(
    numerator: int = 4,
    denominator: int = 4,
    bpm: float = 144.0,
    fps: float = 30.0,
    bars: int = 16,
) -> list[dict[str, int | float | bool]]:
    """Generate every notated beat in a bar-by-bar timeline.

    Frames are reported as the nearest frame index; `exact_frame` indicates
    whether the musical event lands exactly on a video frame boundary.
    """
    if bars <= 0:
        raise ValueError("bars must be positive")
    spec = resolve_meter(numerator, denominator, bpm, fps)
    beat_seconds = 60.0 / bpm * 4.0 / denominator
    beat_frames = Fraction(60, 1) * Fraction(str(fps)) * Fraction(4, denominator) / Fraction(str(bpm))
    events: list[dict[str, int | float | bool]] = []
    for bar in range(bars):
        for beat_index in range(numerator):
            exact_time = bar * spec.seconds_per_bar + beat_index * beat_seconds
            exact_frame = bar * spec.frames_per_bar + beat_index * beat_frames
            events.append({
                "bar": bar + 1,
                "count": beat_index + 1,
                "time_seconds": exact_time,
                "frame": round(float(exact_frame)),
                "exact_frame": exact_frame.denominator == 1,
                "bar_downbeat": beat_index == 0,
            })
    return events
