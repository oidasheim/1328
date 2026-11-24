"""Evidence-backed creative planning notes for short-form video.

This module records planning hypotheses and source provenance. It deliberately
has no virality score and does not claim that engagement guarantees reach.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
from typing import Iterable


@dataclass(frozen=True)
class EvidenceSource:
    id: str
    title: str
    year: int
    type: str
    url: str
    findings: tuple[str, ...]
    limitations: tuple[str, ...] = ()


SOURCES: tuple[EvidenceSource, ...] = (
    EvidenceSource(
        "joyce-wirtz-2025",
        "Emotion In Motion: How Sentiment Shapes TikTok Post Performance and Engagement",
        2025,
        "Stanford thesis/repository",
        "https://purl.stanford.edu/yj849ry4057",
        ("High-arousal emotional sentiment is associated with engagement.",
         "Emotional intensity can differ from emotional valence."),
        ("Association is not causation; platform and network effects remain unresolved.",),
    ),
    EvidenceSource(
        "mishra-2025",
        "The Science of the First Three Seconds: An Empirical Analysis of Emotional Tone, Rhetorical Style, and Category Norms in Viral TikTok Hooks",
        2025,
        "OSF preprint",
        "https://doi.org/10.31235/osf.io/rj2mz",
        ("First-seconds language and rhetorical devices vary in association with engagement.",
         "Category norms and social context matter."),
        ("Preprint evidence; no universal hook rule; engagement is not guaranteed reach.",),
    ),
    EvidenceSource(
        "chi-tiktok-2024",
        "Analyzing User Engagement with TikTok's Short Format Video Recommendations using Data Donations",
        2024,
        "CHI/arXiv empirical paper",
        "https://arxiv.org/abs/2301.04945",
        ("User attention and viewing behavior can be measured at short-format scale.",),
        ("Observed attention is contextual and not proof of causal virality.",),
    ),
    EvidenceSource(
        "tiktok-feed-2025",
        "How TikTok recommends content in the For You Feed",
        2025,
        "Official platform guidance",
        "https://newsroom.tiktok.com/en-us/how-tiktok-recommends-videos-for-you",
        ("Watch/rewatch behavior and interactions are among recommendation signals.",
         "Viewer and platform context are also considered."),
        ("Official guidance does not guarantee outcomes or expose a complete ranking formula.",),
    ),
    EvidenceSource(
        "youtube-discovery",
        "How videos are discovered and recommended",
        2026,
        "Official platform guidance",
        "https://support.google.com/youtube/answer/9314410",
        ("Viewer satisfaction and watch behavior inform discovery and can be measured in analytics.",),
        ("Metrics vary by content format and do not guarantee distribution.",),
    ),
    EvidenceSource(
        "instagram-reels",
        "Instagram Reels analytics and ranking guidance",
        2026,
        "Official platform guidance",
        "https://help.instagram.com/1533933820244654",
        ("Watch time, average view duration and interactions are observable Reel measures.",),
        ("Official documentation does not establish a single virality threshold.",),
    ),
)


@dataclass(frozen=True)
class CreativeHypothesis:
    id: str
    name: str
    planning_note: str
    evidence_ids: tuple[str, ...]
    prohibited_claim: str


HYPOTHESES: tuple[CreativeHypothesis, ...] = (
    CreativeHypothesis("clear-hook", "Clear opening hook", "Open with an understandable visual/audio hook and remove avoidable delay.", ("mishra-2025", "tiktok-feed-2025"), "No claim that a particular opening guarantees reach."),
    CreativeHypothesis("retention-review", "Retention-oriented editing", "Use reviewable pacing, loops and payoff, then measure completion and rewatch instead of optimizing an assumed formula.", ("chi-tiktok-2024", "tiktok-feed-2025", "youtube-discovery"), "No claim that watch time alone causes virality."),
    CreativeHypothesis("emotional-clarity", "Emotionally legible scene", "Choose one clear emotion or practical value proposition and avoid confusing or manipulative escalation.", ("joyce-wirtz-2025", "mishra-2025"), "No claim that high-arousal content is universally better or should exploit fear/anger."),
    CreativeHypothesis("utility-identification", "Utility or identification", "Include practical value or recognizable local context only when relevant to the audience and rights permit.", ("joyce-wirtz-2025",), "No claim that utility or local identity guarantees sharing."),
    CreativeHypothesis("responsible-cta", "Measured call to engagement", "Use a contextual CTA for feedback or sharing; do not fabricate urgency or artificially engage viewers.", ("tiktok-feed-2025", "instagram-reels",), "No claim that CTA volume guarantees likes, shares or discovery."),
)


def evidence_manifest() -> dict[str, object]:
    return {"status": "reference_notes_not_predictions",
            "sources": [asdict(source) for source in SOURCES],
            "hypotheses": [asdict(hypothesis) for hypothesis in HYPOTHESISS]}


def write_evidence(destination: str | Path) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence_manifest(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
