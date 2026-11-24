import json

from synapse.creative_identity import (CampaignPlan, IdentityRevision,
                                       VirtualArtistProfile, manifest,
                                       review_campaign, write_manifest)


def test_virtual_artist_plan_requires_disclosure_human_and_opt_in_data():
    profile = VirtualArtistProfile("neon-zero", "NEON-ZERO")
    plan = CampaignPlan("launch-1", "neon-zero", ("youtube_shorts",), ("clip-1.mp4",))
    result = review_campaign(profile, plan)
    assert result.status == "review_ready"
    assert result.publish_enabled is False
    assert result.budget_spend_enabled is False


def test_unsafe_campaign_tactics_are_held():
    profile = VirtualArtistProfile("neon-zero", "NEON-ZERO")
    plan = CampaignPlan("launch-1", "neon-zero", ("tiktok",), ("clip.mp4",),
                        tactics=("fake_trend", "fake_beef"))
    result = review_campaign(profile, plan)
    assert result.status == "hold"
    assert any("prohibited tactics" in reason for reason in result.reasons)


def test_unlicensed_voice_and_personal_data_are_held():
    profile = VirtualArtistProfile("ava", "AVA", voice_source="voice_likeness",
                                   personal_data_collection=True)
    plan = CampaignPlan("launch", "ava", ("instagram_reels",), ("asset.mp4",))
    result = review_campaign(profile, plan)
    assert result.status == "hold"
    assert any("voice likeness" in reason for reason in result.reasons)
    assert any("personal-data" in reason for reason in result.reasons)


def test_identity_revision_requires_traceable_review():
    revision = IdentityRevision("r1", "11.0", "12.0", ("event:42",),
                                "Review showed the old policy was ambiguous.",
                                ("Clarify human gate",))
    revision.validate()
    bad = IdentityRevision("r2", "11.0", "12.0", (), "", (), approved=True)
    try:
        bad.validate()
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete revision must fail validation")


def test_governance_manifest_export(tmp_path):
    assert manifest()["campaign_policy"]["external_publish_enabled"] is False
    target = write_manifest(tmp_path / "manifest.json")
    assert json.loads(target.read_text())["virtual_artist"]["ai_disclosure"] is True
