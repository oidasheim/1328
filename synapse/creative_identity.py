"""Governed creative-system identity and transparent virtual-artist planning.

This module is local planning only. It never scrapes social platforms, generates
voice likenesses, posts content, messages users, or spends money.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class SystemIdentity:
    version: str
    values: tuple[str, ...]
    capabilities: tuple[str, ...]
    policies: tuple[str, ...]
    provenance: tuple[str, ...] = ()
    known_failures: tuple[str, ...] = ()
    current_world_model: str = "local creative-production system; external facts require evidence"


@dataclass(frozen=True)
class IdentityRevision:
    revision_id: str
    parent_version: str
    next_version: str
    experience_refs: tuple[str, ...]
    reflection: str
    changes: tuple[str, ...]
    reviewed_by: str | None = None
    approved: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> None:
        if not self.parent_version or not self.next_version or self.parent_version == self.next_version:
            raise ValueError("revision requires distinct parent and next versions")
        if not self.experience_refs or not self.reflection.strip() or not self.changes:
            raise ValueError("revision requires experience references, reflection, and changes")
        if self.approved and not (self.reviewed_by and self.reviewed_by.strip()):
            raise ValueError("approved revision must identify its human reviewer")


@dataclass(frozen=True)
class VirtualArtistProfile:
    artist_id: str
    display_name: str
    fictional: bool = True
    ai_disclosure: bool = True
    voice_source: str = "original_synthetic_voice"
    voice_rights_verified: bool = False
    human_review_required: bool = True
    personal_data_collection: bool = False


@dataclass(frozen=True)
class CampaignPlan:
    campaign_id: str
    artist_id: str
    platforms: tuple[str, ...]
    assets: tuple[str, ...]
    posts_per_week: int = 2
    data_basis: str = "first_party_aggregated_opt_in"
    human_approval_required: bool = True
    external_publish_enabled: bool = False
    budget_spend_enabled: bool = False
    tactics: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanReview:
    status: str
    reasons: tuple[str, ...]
    publish_enabled: bool = False
    budget_spend_enabled: bool = False


PROHIBITED_TACTICS = frozenset({
    "fake_trend", "covert_sentiment_scraping", "fake_beef",
    "impersonation", "algorithm_backdoor", "spam_or_mass_posting",
    "unlicensed_voice_clone", "emotional_exploitation",
})


def review_campaign(profile: VirtualArtistProfile, plan: CampaignPlan) -> PlanReview:
    """Return a conservative local review; never execute the proposed campaign."""
    reasons: list[str] = []
    if plan.artist_id != profile.artist_id:
        reasons.append("campaign artist_id does not match the profile")
    if not profile.fictional or not profile.ai_disclosure:
        reasons.append("virtual artist must be fictional and clearly disclosed as AI")
    if profile.voice_source != "original_synthetic_voice" and not profile.voice_rights_verified:
        reasons.append("voice likeness lacks verified authorization")
    if profile.personal_data_collection:
        reasons.append("personal-data collection is disabled by policy")
    if not profile.human_review_required or not plan.human_approval_required:
        reasons.append("human review and approval are mandatory")
    if plan.external_publish_enabled:
        reasons.append("external publishing is not implemented or enabled")
    if plan.budget_spend_enabled:
        reasons.append("autonomous budget spending is not implemented or enabled")
    if not 0 <= plan.posts_per_week <= 7:
        reasons.append("posts_per_week must be between 0 and 7")
    if plan.data_basis != "first_party_aggregated_opt_in":
        reasons.append("only first-party, aggregated, opt-in analytics may inform planning")
    prohibited = sorted(set(plan.tactics) & PROHIBITED_TACTICS)
    if prohibited:
        reasons.append("prohibited tactics: " + ", ".join(prohibited))
    if not plan.platforms or not plan.assets:
        reasons.append("plan must identify intended platforms and reviewed assets")
    return PlanReview("hold" if reasons else "review_ready", tuple(reasons))


def default_identity() -> SystemIdentity:
    return SystemIdentity(
        version="1.0.0",
        values=("creative integrity", "transparency", "consent", "human accountability"),
        capabilities=("local creative planning", "provenance tracking", "reviewable workflow"),
        policies=("No autonomous publishing", "No autonomous budget changes",
                  "No covert data collection", "No unlicensed voice imitation"),
        provenance=("repository configuration",),
        known_failures=("Planning output is not evidence of platform performance",),
    )


def manifest() -> dict[str, object]:
    return {
        "system_identity": asdict(default_identity()),
        "virtual_artist": asdict(VirtualArtistProfile("neon-zero", "NEON-ZERO")),
        "campaign_policy": {
            "mode": "planning_only",
            "data_basis": "first_party_aggregated_opt_in",
            "human_approval_required": True,
            "external_publish_enabled": False,
            "budget_spend_enabled": False,
            "prohibited_tactics": sorted(PROHIBITED_TACTICS),
        },
    }


def write_manifest(destination: str | Path) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="synapse-ava-plan")
    parser.add_argument("--out", type=Path, default=Path("reports/ava_campaign_plan.json"))
    args = parser.parse_args(argv)
    target = write_manifest(args.out)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
