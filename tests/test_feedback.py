import pytest

from synapse.feedback import Feedback, FeedbackStore, QueueItem


def test_feedback_store_rejects_unknown_clip(tmp_path):
    store = FeedbackStore(tmp_path / "feedback.db")
    with pytest.raises(KeyError):
        store.record(Feedback("missing", "tiktok", "2026-01-01T00:00:00Z", "official-export", views=1))
    store.close()


def test_feedback_store_import_and_descriptive_report(tmp_path):
    store = FeedbackStore(tmp_path / "feedback.db")
    store.enqueue(QueueItem("clip-1", "tiktok", source_render="clip.mp4", predicted_probability=0.7))
    store.record(Feedback("clip-1", "tiktok", "2026-01-01T00:00:00Z", "official-export",
                         views=100, shares=10, saves=5, completion_rate=0.6))
    report = store.deep_insights()
    assert report["platforms"][0]["clips"] == 1
    assert report["platforms"][0]["share_rate"] == pytest.approx(0.1)
    assert "causality" in report["warnings"][1]
    store.close()
