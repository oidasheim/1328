from weedit_native.models import ClipDNA, Intent, ShotNeed
from weedit_native.pool import PoolPlan, allocate_song_pools
from weedit_native.resolver import build_shot_needs, resolve


def _clip(name, motion=.5, brightness=.5):
    return ClipDNA(name, f"/{name}.mp4", 5, motion=motion, brightness=brightness, tags=(name,))


def test_global_pool_reserves_specialist_clips_and_is_order_independent():
    clips = [_clip("shared"), _clip("song-a-best", .9), _clip("song-b-best", .1)]
    needs_a = [ShotNeed("a", 0, 1, .9, ("song-a-best",), .9)]
    needs_b = [ShotNeed("b", 0, 1, .1, ("song-b-best",), .1)]
    first = allocate_song_pools({"/music/a.mp3": needs_a, "/music/b.mp3": needs_b}, clips, pool_size=1)
    second = allocate_song_pools({"/music/b.mp3": needs_b, "/music/a.mp3": needs_a}, list(reversed(clips)), pool_size=1)
    assert first == second
    by_song = {PathLike(item.song): item.clip_paths for item in first.songs}
    assert by_song["a.mp3"] == ("/song-a-best.mp4",)
    assert by_song["b.mp3"] == ("/song-b-best.mp4",)


def PathLike(path):
    return path.rsplit("/", 1)[-1]


def test_pool_capacity_shortfall_is_explicit_and_plan_roundtrips():
    plan = allocate_song_pools({"/a.mp3": [], "/b.mp3": []}, [_clip("only")], pool_size=1)
    assert any("smaller" in warning for warning in plan.warnings)
    assert sum(len(song.clip_paths) for song in plan.songs) == 2
    restored = PoolPlan.from_dict(plan.to_dict())
    assert restored == plan
    assert sum(len(song.shared_fallbacks) for song in restored.songs) == 1


def test_color_filter_rejects_extreme_brightness_but_keeps_usable_variation():
    need = ShotNeed("s", 0, 1, .5)
    clips = [_clip("black", brightness=0.0), _clip("white", brightness=1.0),
             _clip("normal", brightness=.12), _clip("warm", brightness=.75)]
    assert [clip.clip_id for clip, _ in resolve(need, clips)] == ["warm", "normal"]


def test_build_shot_needs_progresses_on_sparse_beats_and_closes_tail():
    intents = [Intent("verse", 0, 5.2, .5)]
    needs = build_shot_needs(intents, (0, 1, 2), fps=30)
    assert needs[0].start == 0
    assert abs(needs[-1].end - 5.2) < 1e-8
    assert all(abs(left.end - right.start) < 1e-8 for left, right in zip(needs, needs[1:]))
