import csv

import pytest

from synapse.wong import (
    Evidence, Forecast, ForecastOutcome, Hypothesis, SourceQuality,
    TrendState, WONGStore, brier_score, calibration_bins,
    classify_bot_risk, compare_scenarios, create_autopsy,
    detect_trend_state, normalized_hypothesis_scores,
)
from synapse.wong_cli import evaluate_csv

TS = "2026-01-01T00:00:00Z"


def make_forecast(identifier="f1", probability=0.8, agent="WONG", sources=("source-a",)):
    return Forecast(identifier, "breakout within 30d", 30, probability, 0.4, 0.7,
                    TS, agent, sources, ("platform saturation",), "growth fails to persist", ("e1",))


def test_source_quality_weight_decreases_with_risk():
    good = SourceQuality("a", historical_accuracy=0.9)
    risky = SourceQuality("b", historical_accuracy=0.9, bot_risk=0.8, noise=0.5)
    assert good.weight > risky.weight


def test_evidence_validates_timestamp_and_preserves_counter_evidence():
    evidence = Evidence("e1", "trend growth", "source-a", TS, "views", 100,
                        context={"region": "DE"}, supports_claim=False)
    assert not evidence.supports_claim
    with pytest.raises(ValueError):
        Evidence("e2", "x", "s", "not-a-date", "metric", 1)


def test_brier_and_calibration():
    assert brier_score([0.8, 0.2], [1, 0]) == pytest.approx(0.04)
    bins = calibration_bins([0.8, 0.8, 0.2], [1, 0, 0], bins=5)
    assert len(bins) == 2
    high = next(bucket for bucket in bins if bucket["mean_probability"] > 0.5)
    assert high["observed_frequency"] == 0.5


def test_scenario_changes_are_bounded_and_labeled():
    rows = compare_scenarios(0.8, {"wait 30 days": -0.4, "creative strategy": 0.5})
    assert rows[1]["probability"] == pytest.approx(0.4)
    assert rows[2]["probability"] == 1.0
    assert "not causal" in rows[1]["assumptions"][0]


def test_hypothesis_scores_are_not_presented_as_posterior():
    rows = normalized_hypothesis_scores([Hypothesis("h1", "audio", 2), Hypothesis("h2", "creator", 1)])
    assert sum(row["weight"] for row in rows) == pytest.approx(1.0)
    assert "not a calibrated probability" in rows[0]["interpretation"]


def test_bot_risk_is_uncertainty_not_accusation():
    result = classify_bot_risk({"synchronized_timing": 0.9, "low_account_diversity": 0.8})
    assert result["label"] == "suspicious"
    assert "not proof" in result["disclaimer"]


def test_trend_state_basic_cases():
    assert detect_trend_state([1, 1, 2, 4, 8, 16]) == TrendState.ACCELERATION
    assert detect_trend_state([10, 9, 8, 7, 5, 3]) == TrendState.DECAY
    assert detect_trend_state([1, 1]) == TrendState.INSUFFICIENT_DATA


def test_autopsy_signed_error_and_id_check():
    forecast = make_forecast(probability=0.8)
    autopsy = create_autopsy(forecast, ForecastOutcome("f1", False, TS), root_cause="overestimated adoption")
    assert autopsy.signed_error == pytest.approx(-0.8)
    with pytest.raises(ValueError):
        create_autopsy(forecast, ForecastOutcome("other", True, TS), root_cause="mismatch")


def test_store_persists_evidence_forecast_outcome_and_autopsy(tmp_path):
    store = WONGStore(tmp_path / "wong.db")
    store.add_evidence(Evidence("e1", "claim", "source-a", TS, "views", 200))
    forecast = make_forecast()
    store.add_forecast(forecast)
    store.add_outcome(ForecastOutcome("f1", True, TS))
    autopsy = create_autopsy(forecast, ForecastOutcome("f1", True, TS), root_cause="confirmed")
    store.save_autopsy(autopsy)
    completed = store.completed_forecasts()
    assert len(completed) == 1
    assert completed[0][0].forecast_id == "f1"
    store.close()


def test_csv_report_and_leaderboards(tmp_path):
    path = tmp_path / "scores.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["probability", "outcome", "agent", "source"])
        writer.writeheader()
        writer.writerow({"probability": 0.8, "outcome": 1, "agent": "DE Scout", "source": "Bandcamp"})
        writer.writerow({"probability": 0.7, "outcome": 0, "agent": "DE Scout", "source": "TikTok"})
    report = evaluate_csv(path, bins=5)
    assert report["count"] == 2
    assert len(report["leaderboards"]["agent"]) == 1
    assert report["brier_score"] == pytest.approx(0.265)
