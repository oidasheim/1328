"""Constraint-aware deterministic candidate ranking and simple UCB learning."""
from __future__ import annotations

import math
from .models import ClipDNA, Intent, RenderShot, ShotNeed


def resolve(need: ShotNeed, clips: list[ClipDNA], top_k: int = 25,
            used_paths: set[str] | None = None) -> list[tuple[ClipDNA, float]]:
    used_paths = used_paths or set()
    ranked = []
    for clip in clips:
        if clip.duration <= 0:
            continue
        tag_set = set(clip.tags)
        required = set(need.required_tags)
        tag_score = len(required & tag_set) / max(1, len(required))
        motion_score = 1.0 - min(1.0, abs(clip.motion - need.preferred_motion))
        novelty = 0.0 if clip.path in used_paths else 0.12
        score = 0.48 * tag_score + 0.4 * motion_score + novelty
        ranked.append((clip, score))
    return sorted(ranked, key=lambda item: (-item[1], item[0].path))[:max(0, top_k)]


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


def resolve_intents(intents: list[Intent], clips: list[ClipDNA], *, seed: int = 0) -> list[RenderShot]:
    selector = UCBSelector()
    used: set[str] = set()
    result = []
    index = 0
    for intent in intents:
        beat_boundaries = [intent.start]
        # Shot length is capped by the next beat or a 4-second visual ceiling.
        while beat_boundaries[-1] < intent.end - 1e-6:
            next_beat = min((t for t in _beat_candidates if t > beat_boundaries[-1] + 1e-6), default=intent.end)
            beat_boundaries.append(min(intent.end, next_beat, beat_boundaries[-1] + 4.0))
        for start, end in zip(beat_boundaries, beat_boundaries[1:]):
            duration = end - start
            if duration <= 0: continue
            need = ShotNeed(f"shot-{index:05d}", start, end, intent.energy, intent.tags,
                            min(1.0, intent.energy), intent.camera, intent.color)
            candidates = resolve(need, clips, used_paths=used)
            if not candidates:
                raise RuntimeError("No usable clips; run `weed scan` and check clip files")
            selected = selector.select(candidates, total_pulls=index + 1)
            score = next(score for clip, score in candidates if clip.path == selected.path)
            result.append(RenderShot(selected.path, 0.0, min(duration, selected.duration), start,
                                     intent.camera, intent.color, score))
            used.add(selected.path)
            selector.update(selected.path, score)
            index += 1
    return result


# Resolver receives an explicit beat grid through this narrow adapter to keep
# intent generation separate from music analysis.
_beat_candidates: tuple[float, ...] = ()

def set_beat_grid(beats: tuple[float, ...]) -> None:
    global _beat_candidates
    _beat_candidates = beats
