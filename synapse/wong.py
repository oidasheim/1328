"""WONG forensic intelligence, forecast evaluation, and source-quality tools.

This module records evidence and evaluates probabilistic forecasts. Scenario
outputs are assumption-driven comparisons, not causal estimates. Bot-risk
signals are uncertainty flags, not proof of manipulation or wrongdoing.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import math
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Sequence


def _bounded(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be a finite value between 0 and 1")
    return value


def _timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result


class TruthStatus(str, Enum):
    VERIFIED = "verified"
    PROBABLE = "probable"
    SPECULATIVE = "speculative"
    REFUTED = "refuted"
    UNKNOWN = "unknown"


class TrendState(str, Enum):
    EMERGENCE = "emergence"
    ACCELERATION = "acceleration"
    PEAK = "peak"
    PLATEAU = "plateau"
    FATIGUE = "fatigue"
    DECAY = "decay"
    REVIVAL = "revival"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class SourceQuality:
    source_id: str
    historical_accuracy: float = 0.5
    freshness: float = 1.0
    authenticity: float = 1.0
    coverage: float = 1.0
    noise: float = 0.0
    bot_risk: float = 0.0
    bias: float = 0.0  # signed direction indicator in [-1, 1]

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id cannot be empty")
        for name in ("historical_accuracy", "freshness", "authenticity", "coverage", "noise", "bot_risk"):
            _bounded(name, getattr(self, name))
        if not math.isfinite(float(self.bias)) or not -1.0 <= float(self.bias) <= 1.0:
            raise ValueError("bias must be finite and between -1 and 1")

    @property
    def weight(self) -> float:
        """Transparent quality heuristic; not a statistically learned posterior."""
        bias_factor = 1.0 - abs(float(self.bias))
        return (self.historical_accuracy * self.freshness * self.authenticity
                * self.coverage * (1.0 - self.noise) * (1.0 - self.bot_risk)
                * bias_factor)


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    claim: str
    source_id: str
    observed_at: str
    metric: str
    value: float | str
    context: dict[str, Any] = field(default_factory=dict)
    transformation: str = "raw observation"
    supports_claim: bool = True

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.claim or not self.source_id or not self.metric:
            raise ValueError("evidence_id, claim, source_id, and metric are required")
        _timestamp(self.observed_at)


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    description: str
    score: float
    evidence_ids: tuple[str, ...] = ()
    counter_evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.description:
            raise ValueError("hypothesis id and description are required")
        if not math.isfinite(float(self.score)):
            raise ValueError("hypothesis score must be finite")


@dataclass(frozen=True)
class Forecast:
    forecast_id: str
    target: str
    horizon_days: int
    probability: float
    expected_magnitude: float
    confidence: float
    issued_at: str
    agent: str = "WONG"
    source_ids: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    falsification_test: str = ""
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.forecast_id or not self.target or not self.agent:
            raise ValueError("forecast id, target, and agent are required")
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive")
        _bounded("probability", self.probability)
        _bounded("confidence", self.confidence)
        if not math.isfinite(float(self.expected_magnitude)):
            raise ValueError("expected_magnitude must be finite")
        _timestamp(self.issued_at)


@dataclass(frozen=True)
class ForecastOutcome:
    forecast_id: str
    observed: bool
    observed_at: str
    notes: str = ""

    def __post_init__(self) -> None:
        _timestamp(self.observed_at)


def brier_score(probabilities: Sequence[float], outcomes: Sequence[int | bool]) -> float:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("probabilities and outcomes must have equal, non-zero lengths")
    scores = []
    for probability, outcome in zip(probabilities, outcomes):
        p = _bounded("probability", probability)
        if outcome not in (0, 1, False, True):
            raise ValueError("outcomes must be binary")
        scores.append((p - int(outcome)) ** 2)
    return sum(scores) / len(scores)


def calibration_bins(probabilities: Sequence[float], outcomes: Sequence[int | bool], bins: int = 10) -> list[dict[str, float | int]]:
    """Return reliability-curve buckets with sample counts and observed rates."""
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("probabilities and outcomes must have equal, non-zero lengths")
    if bins <= 0:
        raise ValueError("bins must be positive")
    groups: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for probability, outcome in zip(probabilities, outcomes):
        p = _bounded("probability", probability)
        if outcome not in (0, 1, False, True):
            raise ValueError("outcomes must be binary")
        index = min(int(p * bins), bins - 1)
        groups[index].append((p, int(outcome)))
    result = []
    for index, group in enumerate(groups):
        if group:
            result.append({
                "lower": index / bins,
                "upper": (index + 1) / bins,
                "count": len(group),
                "mean_probability": sum(p for p, _ in group) / len(group),
                "observed_frequency": sum(y for _, y in group) / len(group),
            })
    return result


def compare_scenarios(baseline_probability: float, scenarios: dict[str, float]) -> list[dict[str, Any]]:
    """Compare explicitly supplied probability deltas; no causal claim is implied."""
    baseline = _bounded("baseline_probability", baseline_probability)
    result = [{"scenario": "baseline", "probability": baseline, "assumptions": []}]
    for name, delta in scenarios.items():
        if not math.isfinite(float(delta)):
            raise ValueError("scenario deltas must be finite")
        result.append({
            "scenario": name,
            "probability": min(1.0, max(0.0, baseline + float(delta))),
            "assumptions": ["user-supplied delta; illustrative, not causal"],
        })
    return result


def normalized_hypothesis_scores(hypotheses: Sequence[Hypothesis]) -> list[dict[str, Any]]:
    """Normalize declared scores for ranking; scores are not Bayesian posteriors."""
    if not hypotheses:
        return []
    maximum = max(h.score for h in hypotheses)
    weights = [math.exp(max(-700.0, min(0.0, h.score - maximum))) for h in hypotheses]
    total = sum(weights)
    return [{
        "hypothesis_id": h.hypothesis_id,
        "description": h.description,
        "weight": weight / total,
        "evidence_ids": list(h.evidence_ids),
        "counter_evidence_ids": list(h.counter_evidence_ids),
        "interpretation": "normalized heuristic weight, not a calibrated probability",
    } for h, weight in zip(hypotheses, weights)]


def classify_bot_risk(signals: dict[str, float]) -> dict[str, Any]:
    """Coarse anomaly flag. It must not be interpreted as proof of inauthenticity."""
    keys = ("repetitive_accounts", "synchronized_timing", "comment_bursts", "low_account_diversity", "network_overlap")
    present = {key: _bounded(key, signals.get(key, 0.0)) for key in keys}
    score = sum(present.values()) / len(present)
    label = "organic" if score < 0.2 else "mixed" if score < 0.45 else "suspicious" if score < 0.7 else "high_risk"
    return {"label": label, "score": score, "signals": present,
            "disclaimer": "Anomaly suspicion is not proof of bots or misconduct."}


def detect_trend_state(values: Sequence[float]) -> TrendState:
    """Classify a small metric series using transparent directional heuristics."""
    if len(values) < 4 or any(not math.isfinite(float(v)) for v in values):
        return TrendState.INSUFFICIENT_DATA
    series = [float(v) for v in values]
    if any(v < 0 for v in series):
        raise ValueError("trend values must be non-negative")
    if max(series) == 0:
        return TrendState.PLATEAU
    midpoint = len(series) // 2
    first = sum(series[:midpoint]) / midpoint
    second = sum(series[midpoint:]) / (len(series) - midpoint)
    peak_index = max(range(len(series)), key=series.__getitem__)
    relative = (second - first) / max(first, 1e-9)
    if peak_index < len(series) - 2 and relative < -0.15:
        return TrendState.DECAY
    if relative > 0.25:
        return TrendState.ACCELERATION if second > series[0] * 1.5 else TrendState.EMERGENCE
    if relative < -0.35:
        return TrendState.FATIGUE
    if peak_index == len(series) - 1 and relative > 0.1:
        return TrendState.REVIVAL
    if abs(relative) <= 0.1:
        return TrendState.PLATEAU
    return TrendState.PEAK


@dataclass(frozen=True)
class Autopsy:
    forecast_id: str
    predicted_probability: float
    observed_outcome: bool
    signed_error: float
    root_cause: str
    feature_failure: str
    source_failure: str
    model_failure: str
    policy_revision: str
    evidence_ids: tuple[str, ...] = ()


def create_autopsy(forecast: Forecast, outcome: ForecastOutcome, *, root_cause: str,
                   feature_failure: str = "", source_failure: str = "",
                   model_failure: str = "", policy_revision: str = "") -> Autopsy:
    if forecast.forecast_id != outcome.forecast_id:
        raise ValueError("forecast and outcome IDs do not match")
    observed = 1.0 if outcome.observed else 0.0
    return Autopsy(
        forecast_id=forecast.forecast_id,
        predicted_probability=forecast.probability,
        observed_outcome=outcome.observed,
        signed_error=observed - forecast.probability,
        root_cause=root_cause,
        feature_failure=feature_failure,
        source_failure=source_failure,
        model_failure=model_failure,
        policy_revision=policy_revision,
        evidence_ids=forecast.evidence_ids,
    )


class WONGStore:
    """Small SQLite evidence/forecast store with append-only outcome records."""
    def __init__(self, path: str | Path = "database/wong.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY, claim TEXT NOT NULL, source_id TEXT NOT NULL,
                observed_at TEXT NOT NULL, metric TEXT NOT NULL, value_json TEXT NOT NULL,
                context_json TEXT NOT NULL, transformation TEXT NOT NULL,
                supports_claim INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS forecasts (
                forecast_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, forecast_id TEXT NOT NULL,
                observed INTEGER NOT NULL, observed_at TEXT NOT NULL, notes TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_outcomes_forecast ON outcomes(forecast_id);
            CREATE TABLE IF NOT EXISTS autopsies (
                forecast_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL
            );
        """)
        self.connection.commit()

    def add_evidence(self, item: Evidence) -> None:
        self.connection.execute("""INSERT OR REPLACE INTO evidence VALUES(?,?,?,?,?,?,?,?,?)""", (
            item.evidence_id, item.claim, item.source_id, item.observed_at, item.metric,
            json.dumps(item.value), json.dumps(item.context, sort_keys=True),
            item.transformation, int(item.supports_claim),
        ))
        self.connection.commit()

    def add_forecast(self, item: Forecast) -> None:
        self.connection.execute("INSERT OR REPLACE INTO forecasts VALUES(?,?)",
                                (item.forecast_id, json.dumps(asdict(item), sort_keys=True)))
        self.connection.commit()

    def add_outcome(self, item: ForecastOutcome) -> None:
        if not self.connection.execute("SELECT 1 FROM forecasts WHERE forecast_id=?", (item.forecast_id,)).fetchone():
            raise KeyError(f"Unknown forecast: {item.forecast_id}")
        self.connection.execute("INSERT INTO outcomes(forecast_id,observed,observed_at,notes) VALUES(?,?,?,?)",
                                (item.forecast_id, int(item.observed), item.observed_at, item.notes))
        self.connection.commit()

    def save_autopsy(self, item: Autopsy) -> None:
        self.connection.execute("INSERT OR REPLACE INTO autopsies VALUES(?,?)",
                                (item.forecast_id, json.dumps(asdict(item), sort_keys=True)))
        self.connection.commit()

    def completed_forecasts(self) -> list[tuple[Forecast, ForecastOutcome]]:
        rows = self.connection.execute("""
            SELECT f.payload_json, o.forecast_id, o.observed, o.observed_at, o.notes
            FROM forecasts f JOIN outcomes o USING(forecast_id)
            WHERE o.id = (SELECT MAX(o2.id) FROM outcomes o2 WHERE o2.forecast_id=f.forecast_id)
            ORDER BY o.id
        """).fetchall()
        results = []
        for row in rows:
            raw = json.loads(row["payload_json"])
            for key in ("source_ids", "risks", "evidence_ids"):
                raw[key] = tuple(raw.get(key, ()))
            forecast = Forecast(**raw)
            outcome = ForecastOutcome(row["forecast_id"], bool(row["observed"]), row["observed_at"], row["notes"])
            results.append((forecast, outcome))
        return results

    def close(self) -> None:
        self.connection.close()
