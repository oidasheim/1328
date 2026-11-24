# SYNAPSE local release feedback

The feedback module stores a release queue and observed platform metrics in a
SQLite WAL database. It does not scrape, authenticate, post, purchase engagement,
scrape private profiles, or claim that a pattern caused viral reach.

Only import official API exports or metrics that you collected and are authorized
to use. For every observation, preserve the platform, source, observation time,
and original export fields.

## Queue and record

```python
from synapse.feedback import Feedback, FeedbackStore, QueueItem

store = FeedbackStore("database/viral_feedback.db")
store.enqueue(QueueItem("clip-001", "tiktok", source_render="output/clip.mp4"))
store.record(Feedback("clip-001", "tiktok", "2026-07-01T12:00:00Z",
                     "official-api-export", views=10000, likes=900,
                     shares=240, completion_rate=0.62))
print(store.deep_insights())
store.close()
```

## CSV import

Required columns: `clip_id,platform,observed_at,source`. Optional numeric columns:
`views,likes,comments,shares,saves,completion_rate,watch_time,followers_delta`.

```bash
synapse-feedback import --db database/viral_feedback.db metrics.csv
synapse-feedback report --db database/viral_feedback.db --out reports/deep-insights.json
```

The report contains platform-level descriptive aggregates. Minimum sample sizes,
confidence intervals, source bias checks, and platform-specific models should be
added only after enough representative labeled observations exist.
