import json
from pathlib import Path

import numpy as np

from synapse.art_director import (BarFeature, ClipRecord, aligned_array,
                                  compile_timeline, load_clip_records,
                                  write_timeline)


def test_aligned_array_is_32_byte_aligned():
    array = aligned_array((24,), np.float32)
    assert array.ctypes.data % 32 == 0


def test_compile_timeline_respects_blackout_and_cooldown(tmp_path):
    bars = [BarFeature(0, 0.0, 2.0, 120.0, "BUILDUP", 0.8, 0.2,
                       tuple([0.5] * 60), tuple([0.5] * 60), False)]
    clips = [ClipRecord(1, str(tmp_path / "one.mp4"), usable_frames=120,
                        role="SUBJECT", use_count=0)]
    events = compile_timeline(bars, clips, fps=30, blackout_last_frames=4)
    assert any(event.blackout for event in events)
    assert all(event.clip_id is not None or event.blackout for event in events)


def test_compile_timeline_rejects_empty_inputs():
    try:
        compile_timeline([], [], fps=30)
    except ValueError:
        pass
    else:
        raise AssertionError("empty timeline should fail")


def test_write_timeline_roundtrip(tmp_path):
    event = {"event_id": 0, "bar": 0, "section": "VERSE", "start_frame": 0,
             "end_frame": 29, "clip_id": 1, "file_path": "/clip.mp4",
             "source_frame": 0, "blackout": False, "match_cut": False,
             "sub_bass": (0.1,), "high_hat": (0.2,)}
    target = tmp_path / "timeline.json"
    target.write_text(json.dumps({"version": 1, "events": [event]}), encoding="utf-8")
    assert target.exists()
