from fractions import Fraction

import pytest

from synapse.rhythm import (
    compute_polymeter_cycle,
    generate_meter_timeline,
    lcm_polyrhythm_grid,
    resolve_meter,
)


def test_3_against_2_shared_cycle():
    grid = lcm_polyrhythm_grid(3, 2)
    assert grid.subdivisions == 6
    assert grid.coincidences == (Fraction(0, 1),)
    assert grid.attacks_a == (Fraction(0), Fraction(1, 3), Fraction(2, 3))


def test_meter_duration_and_frame_alignment():
    meter = resolve_meter(7, 8, bpm=144, fps=30)
    assert meter.quarter_notes_per_bar == Fraction(7, 2)
    assert meter.seconds_per_bar == pytest.approx(1.4583333333)
    assert meter.frames_per_bar == Fraction(175, 4)
    assert not meter.bar_is_exact_integer_frames


def test_polymeter_4_4_against_3_4():
    cycle = compute_polymeter_cycle((4, 4), (3, 4), bpm=120, fps=30)
    assert cycle.cycle_quarter_notes == 12
    assert cycle.bars_a == 3
    assert cycle.bars_b == 4
    assert cycle.re_align_seconds == pytest.approx(6.0)


def test_16_bar_timeline_count_and_downbeats():
    timeline = generate_meter_timeline(7, 8, bpm=144, fps=30, bars=16)
    assert len(timeline) == 16 * 7
    assert [row["bar"] for row in timeline if row["bar_downbeat"]] == list(range(1, 17))
    assert timeline[0]["time_seconds"] == 0


@pytest.mark.parametrize("meter", [(6, 8), (7, 8), (7, 12), (16, 12), (24, 16)])
def test_unusual_denominator_meters_are_supported(meter):
    result = resolve_meter(*meter, bpm=144, fps=30)
    assert result.seconds_per_bar > 0
    assert result.frames_per_bar > 0
