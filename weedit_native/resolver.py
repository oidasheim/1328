"""Constraint-aware deterministic candidate ranking and clip reservation helpers."""
from __future__ import annotations

import math
from .models import ClipDNA, Intent, RenderShot, ShotNeed


def resolve(need: ShotNeed, clips: list[ClipDNA], top_k: int = 25,
            used_paths: set[str] | None = None, *,
            brightness_range: tuple[float, float] = (0.03, 0.99)) -> list[tuple[ClipDNA, float]]:
    """Rank usable clips and filter only invalid or extreme-brightness samples."""
    if top_k < 0:
        raise ValueError("top_k must be non-negative")
    low, high = brightness_range
    if not (math.isfinite(low) and math.isfinite(high) and 0 <= low < high <= 1):
        raise ValueError("brightness_range must be finite bounds in [0, 1]")
    used_paths = used_paths or set()
    required = set(need.required_tags)
    ranked = []
    for clip in clips:
        if (not math.isfinite(clip.duration) or clip.duration <= 0 or not clip.path
                or not math.isfinite(clip.motion) or not 0 <= clip.motion <= 1
                or not math.isfinite(clip.brightness) or not low <= clip.brightness <= high
                or not math.isfinite(clip.saturation) or not 0 <= clip.saturation <= 1):
            continue
        tag_score = len(required & set(clip.tags)) / max(1, len(required))
        motion_score = 1.0 - min(1.0, abs(clip.motion - need.preferred_motion))
        target_brightness = 0.62 if need.color == "warm" else 0.5
        color_score = 1.0 - min(1.0, abs(clip.brightness - target_brightness))
        novelty = 0.0 if clip.path in used_paths else 0.12
        score = 0.44 * tag_score + 0.36 * motion_score + 0.08 * color_score + novelty
        ranked.append((clip, score))
    return sorted(ranked, key=lambda item: (-item[1], item[0].path))[:top_k]


def build_shot_needs(intents: list[Intent], beat_grid: tuple[float, ...], *,
                     fps: int = 30, max_shot_seconds: float = 4.0) -> list[ShotNeed]:
    """Expand intents to a contiguous shot plan, including sparse-beat tails."""
    if fps <= 0 or not math.isfinite(max_shot_seconds) or max_shot_seconds <= 0:
        raise ValueError("fps and max_shot_seconds must be positive")
    beats = tuple(sorted(set(float(t) for t in beat_grid if math.isfinite(float(t)))))
    result = []
    frame = 1.0 / fps
    index = 0
    cursor = 0.0
    for intent in intents:
        if not (math.isfinite(intent.start) and math.isfinite(intent.end) and intent.end > intent.start):
            continue
        start = max(cursor, intent.start)
        while start < intent.end - frame * 0.25:
            next_beat = next((t for t in beats if t > start + 1e-6), intent.end)
            end = min(intent.end, next_beat, start + max_shot_seconds)
            end = min(intent.end, max(end, start + frame))
            result.append(ShotNeed(f"shot-{index:05d}", start, end, intent.energy,
                                   intent.tags, min(1.0, max(0.0, intent.energy)),
                                   intent.camera, intent.color))
            index += 1
            cursor = start = end
    return result


class UCBSelector:
    """Small contextual-free UCB1 selector; rewards must be explicitly supplied."""
    def __init__(self):
        self.counts: dict[str, int] = {}
        self.values: dict[str, float] = {}

    def select(self, candidates: list[tuple[ClipDNA, float]], total_pulls: int = 1) -> ClipDNA:
        if not candidates:
            raise ValueError("No clip candidates")
        def upper(item):
            clip, prior = item
            count = self.counts.get(clip.path, 0)
            if count == 0:
                return (float("inf"), prior)
            mean = self.values[clip.path]
            return (mean + math.sqrt(2.0 * math.log(max(1, total_pulls)) / count), prior)
        return max(candidates, key=lambda item: (upper(item), item[0].path))[0]

    def update(self, path: str, reward: float) -> None:
        if not math.isfinite(reward):
            raise ValueError("reward must be finite")
        count = self.counts.get(path, 0) + 1
        old = self.values.get(path, 0.0)
        self.values[path] = old + (reward - old) / count
        self.counts[path] = count


def resolve_intents(intents: list[Intent], clips: list[ClipDNA], *, seed: int = 0,
                    beat_grid: tuple[float, ...] | None = None, fps: int = 30) -> list[RenderShot]:
    selector = UCBSelector()
    used: set[str] = set()
    result = []
    needs = build_shot_needs(intents, _beat_candidates if beat_grid is None else beat_grid, fps=fps)
    for index, need in enumerate(needs):
        candidates = resolve(need, clips, used_paths=used)
        if not candidates:
            raise RuntimeError("No usable clips after quality/color filtering; inspect indexed clip brightness metadata")
        selected = selector.select(candidates, total_pulls=index + 1)
        score = next(value for clip, value in candidates if clip.path == selected.path)
        # The renderer pads short sources with their final decoded frame. Keeping
        # timeline duration equal to the full need prevents silent coverage gaps.
        shot_duration = need.end - need.start
        result.append(RenderShot(selected.path, 0.0, shot_duration, need.start,
                                 need.camera, need.color, score))
        used.add(selected.path)
        selector.update(selected.path, score)
    return result


_beat_candidates: tuple[float, ...] = ()

def set_beat_grid(beats: tuple[float, ...]) -> None:
    global _beat_candidates
    _beat_candidates = tuple(beats)
