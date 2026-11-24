"""Explainable AI director heuristics for semantic music-video shot planning.

OpenCLIP retrieval supplies image/text similarity. This module adds transparent,
configurable BPM pacing, lyric-keyword context, and diversity-aware sampling. It
is a creative aid, not a platform-performance or virality predictor.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import random
import re
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class DirectorProfile:
    name: str = "cinematic"
    bpm_pacing: tuple[tuple[float, float, float, float], ...] = (
        (80.0, 99.999, 2.2, 3.8),
        (100.0, 109.999, 1.4, 2.4),
        (140.0, 149.999, 0.65, 1.25),
    )
    default_beats_per_shot: float = 2.0
    max_recent_reuse: int = 3
    usage_penalty: float = 0.025
    recent_penalty: float = 0.12
    temperature: float = 0.08
    theme_boost: float = 0.08
    theme_lexicon: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("urban", ("beton", "kiez", "street", "hood", "u-bahn", "urban")),
        ("cyber", ("roboter", "cyber", "digital", "terminal", "neon", "glitch")),
        ("bass_drop", ("bass", "808", "drop", "wumms", "subbass")),
        ("atmospheric", ("schatten", "nacht", "regen", "allein", "dark", "soft")),
        ("bavarian", ("oida", "oidasheim", "minga", "089", "bayern", "bavarian")),
    )
    visual_cues: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("urban", ("urban street, concrete, night city, documentary movement",)),
        ("cyber", ("cyber neon, technology, digital glitch, night scene",)),
        ("bass_drop", ("high-energy action, rhythmic movement, dramatic impact",)),
        ("atmospheric", ("dark cinematic atmosphere, rain, shadows, restrained movement",)),
        ("bavarian", ("Bavarian urban culture, Munich street atmosphere, authentic local setting",)),
    )


def infer_themes(text: str, profile: DirectorProfile | None = None) -> tuple[str, ...]:
    profile = profile or DirectorProfile()
    tokens = set(re.findall(r"[\wäöüß]+", text.casefold()))
    found = []
    for theme, keywords in profile.theme_lexicon:
        if tokens.intersection(word.casefold() for word in keywords):
            found.append(theme)
    return tuple(found)


def pacing_window(bpm: float, profile: DirectorProfile | None = None) -> tuple[float, float]:
    """Return editorial shot-duration range in seconds for an estimated BPM."""
    profile = profile or DirectorProfile()
    if not math.isfinite(bpm) or bpm <= 0:
        raise ValueError("bpm must be positive and finite")
    for low, high, min_seconds, max_seconds in profile.bpm_pacing:
        if low <= bpm <= high:
            return min_seconds, max_seconds
    beat_seconds = 60.0 / bpm
    return max(0.5, beat_seconds), max(beat_seconds, beat_seconds * profile.default_beats_per_shot)


def compose_visual_prompt(energy: float, lyric_context: str, bpm: float,
                          profile: DirectorProfile | None = None) -> tuple[str, tuple[str, ...]]:
    profile = profile or DirectorProfile()
    if not math.isfinite(energy) or not 0.0 <= energy <= 1.0:
        raise ValueError("energy must be in [0, 1]")
    themes = infer_themes(lyric_context, profile)
    base = ("cinematic high-energy music video, vivid color, dynamic movement, dramatic lighting"
            if energy >= 0.5 else
            "cinematic restrained music video, atmospheric shadows, slow movement, soft contrast")
    cues = [cue for theme, values in profile.visual_cues if theme in themes for cue in values]
    pace = "rapid rhythmic cuts" if pacing_window(bpm, profile)[1] <= 1.5 else "measured cinematic pacing"
    context = " ".join(lyric_context.split())[:180]
    pieces = [base, pace, *cues]
    if context:
        pieces.append(f"visual context inspired by lyric: {context}")
    return ", ".join(pieces), themes


def select_diverse(matches: Sequence[object], usage: Mapping[str, int], recent_paths: Iterable[str],
                   rng: random.Random, profile: DirectorProfile | None = None):
    """Seeded softmax sampling over semantic matches with repetition penalties."""
    profile = profile or DirectorProfile()
    if not matches:
        raise ValueError("matches must not be empty")
    recent = set(recent_paths)
    candidates = [m for m in matches if str(m.path) not in recent]
    if not candidates:
        candidates = list(matches)
    scored = []
    for match in candidates:
        path = str(match.path)
        prior_uses = max(0, int(usage.get(path, 0)))
        score = float(match.score) - profile.usage_penalty * math.log1p(prior_uses)
        if path in recent:
            score -= profile.recent_penalty
        scored.append((match, score))
    best = max(score for _, score in scored)
    weights = [math.exp(max(-60.0, (score - best) / profile.temperature)) for _, score in scored]
    return rng.choices([match for match, _ in scored], weights=weights, k=1)[0]


def confidence_margin(matches: Sequence[object]) -> float:
    """Return top-two cosine-score margin; descriptive, not calibrated confidence."""
    scores = sorted((float(item.score) for item in matches), reverse=True)
    return max(0.0, scores[0] - scores[1]) if len(scores) >= 2 else (1.0 if scores else 0.0)
