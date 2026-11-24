"""Evidence-backed creative planning notes for short-form video.

This module records source provenance and hypotheses. It deliberately has no
virality score and does not claim that engagement guarantees reach.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


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
    EvidenceSource("joyce-wirtz-2025", "Emotion In Motion: How Sentiment Shapes TikTok Post Performance and Engagement", 2025,
                   "Stanford thesis/repository", "https://purl.stanford.edu/yj849ry4057",
                   ("High-arousal emotional sentiment is associated with engagement.",
                    "Emotional intensity can differ from emotional valence."),
                   ("Association is not causation; platform and network effects remain unresolved.",)),
    EvidenceSource("mishra-2025", "The Science of the First Three Seconds: An Empirical Analysis of Emotional Tone, Rhetorical Style, and Category Norms in Viral TikTok Hooks", 2025,
                   "OSF preprint", "https://doi.org/10.31235/osf.io/rj2mz",
                   ("First-seconds language and rhetorical devices vary in association with engagement.",
                    "Category norms and social context matter."),
                   ("Preprint; no universal hook rule; engagement is not guaranteed reach.",)),
    EvidenceSource("chi-tiktok-2024", "Analyzing User Engagement with TikTok's Short Format Video Recommendations using Data Donations", 2024,
                   "CHI/arXiv empirical paper", "https://arxiv.org/abs/2301.04945",
                   ("User attention and viewing behavior can be measured at short-format scale.",),
                   ("Observed attention is contextual and not proof of causal virality.",)),
    EvidenceSource("tiktok-feed-2025", "How TikTok recommends content in the For You Feed", 2025,
                   "Official platform guidance", "https://newsroom.tiktok.com/en-us/how-tiktok-recommends-videos-for-you",
                   ("Watch/rewatch behavior and interactions are among recommendation signals.",
                    "Viewer and platform context are also considered."),
                   ("Does not guarantee outcomes or disclose the complete ranking formula.",)),
    EvidenceSource("youtube-discovery", "YouTube Analytics: audience retention and watch-time metrics", 2026,
                   "Official platform guidance", "https://support.google.com/youtube/answer/9314410",
                   ("Viewer satisfaction and watch behavior can be measured in analytics.",),
                   ("Metrics vary by format and do not guarantee distribution.",)),
    EvidenceSource("instagram-reels", "Instagram Reels analytics help", 2026,
                   "Official platform guidance", "https://help.instagram.com/1533933820244654",
                   ("Watch time, average view duration and interactions are observable measures.",),
                   ("No single virality threshold is established.",)),
)


@dataclass(frozen=True)
class CreativeHypothesis:
    id: str
    name: str
    planning_note: str
    evidence_ids: tuple[str, ...]
    prohibited_claim: str


HYPOTHESES: tuple[CreativeHypothesis, ...] = (
    CreativeHypothesis("clear-hook", "Clear opening hook", "Open with an understandable visual/audio hook and remove avoidable delay.",
                       ("mishra-2025", "tiktok-feed-2025"), "A particular opening guarantees reach."),
    CreativeHypothesis("retention-review", "Retention-oriented editing", "Use reviewable pacing and payoff, then measure completion and rewatch.",
                       ("chi-tiktok-2024", "tiktok-feed-2025", "youtube-discovery"), "Watch time alone causes virality."),
    CreativeHypothesis("emotional-clarity", "Emotionally legible scene", "Choose a clear emotion or practical value; avoid manipulative escalation.",
                       ("joyce-wirtz-2025", "mishra-2025"), "High-arousal content is universally better."),
    CreativeHypothesis("utility-identification", "Utility or identification", "Use practical value or relevant local context when appropriate and rights permit.",
                       ("joyce-wirtz-2025",), "Utility or local identity guarantees sharing."),
    CreativeHypothesis("responsible-cta", "Measured call to engagement", "Use contextual feedback invitations; do not fabricate urgency or engagement.",
                       ("tiktok-feed-2025", "instagram-reels"), "A CTA guarantees likes, shares or discovery."),
)


def evidence_manifest() -> dict[str, object]:
    return {"status": "reference_notes_not_predictions",
            "sources": [asdict(source) for source in SOURCES],
            "hypotheses": [asdict(hypothesis) for hypothesis in HYPOTHESES]}


def write_evidence(destination: str | Path) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence_manifest(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
