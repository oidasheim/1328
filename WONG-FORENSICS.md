# WONG — Forensic Intelligence & Forecasting

`synapse.wong` adds a local, inspectable forecasting layer for evidence
provenance, competing explanations, scenario comparison, source-quality
tracking, confidence evaluation, trend-state heuristics, and forecast postmortems.
It is an analytical scaffold, not a claim that the repository contains validated
market data or a production-trained predictor.

## Core cycle

```text
observation → provenance/evidence → competing hypotheses → forecast
            → observed outcome → scoring/calibration → autopsy → revision
```

Evidence can record source, timestamp, metric, context, transformation, and
whether it supports or contradicts a claim. Forecasts should include a horizon,
risks, evidence references, and a falsification test. Outcomes are recorded
separately so the original forecast remains auditable.

## Source quality and uncertainty

`SourceQuality.weight` is a transparent heuristic over historical accuracy,
freshness, authenticity, coverage, noise, bot-risk, and directional bias. It is
not a probability. `classify_bot_risk` returns an anomaly category and score;
suspicion is explicitly not proof of artificial activity.

Hypothesis scores are normalized for ranking but are marked as heuristic weights,
not Bayesian posterior probabilities. Scenario changes are user-supplied deltas
and explicitly labeled illustrative rather than causal estimates.

## Forecast evaluation

Use proper scoring and a reliability curve after outcomes are observed:

```python
from synapse.wong import brier_score, calibration_bins

score = brier_score([0.8, 0.4], [1, 0])
curve = calibration_bins([0.8, 0.4], [1, 0], bins=10)
```

Brier score is the mean squared error for binary probabilistic forecasts; lower
is better. Calibration buckets compare mean predicted probability with observed
frequency. Report sample counts, horizon, selection process, and uncertainty:
small or selectively labeled samples can make source/agent leaderboards
misleading. Do not automatically change source weights or release policies from
small samples.

CSV evaluation expects `probability,outcome,agent,source`:

```bash
synapse-wong forecast-results.csv --bins 10 --out reports/wong-calibration.json
```

## Scenario, trend, and postmortem utilities

```python
from synapse.wong import (
    Forecast, ForecastOutcome, create_autopsy, compare_scenarios,
    detect_trend_state,
)

scenarios = compare_scenarios(0.55, {"release now": 0.05, "wait 30 days": -0.08})
state = detect_trend_state([10, 13, 19, 28, 42, 63])
```

Trend-state detection is a simple directional heuristic. It is not a trained
regime detector. `create_autopsy` records signed forecast error alongside root
cause, feature/source/model failure descriptions, and a proposed policy change;
these fields should be completed through evidence review, not automatically
guessed from the prediction miss.

`WONGStore` persists evidence, forecasts, observed outcomes, and autopsies in a
SQLite WAL database. The store is append-oriented for observed outcomes and
retains the forecast payload for later audit. Do not store credentials or
sensitive personal data in evidence contexts.

Run the unit tests with:

```bash
pytest tests/test_wong.py -q
```
