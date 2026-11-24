# Semantic OpenCLIP + DuckDB workflow

This optional workflow indexes video frames with OpenCLIP ViT-B-32 and stores
normalized 512-D image embeddings in DuckDB. During planning, each beat's
energy prompt can be augmented with a local lyric line from TXT or HTML, then
compared in the shared OpenCLIP text/image embedding space. Lyrics are not
forced-aligned to timestamps: text is divided across beat segments in order and
should be treated as coarse semantic context, not word-level synchronization.

## Setup and index

```bash
python -m pip install -e '.[semantic]'
synapse-index-clips ./clips --db ./database/clips_semantic.duckdb
```

Generate a plan first and optionally use one usage ledger across projects:

```bash
synapse-semantic-render ./track.mp3 --lyrics ./lyrics.html \
  --db ./database/clips_semantic.duckdb \
  --global-usage ./database/global_clip_usage.json --seed 42 --dry-run
```

Render when the plan has been reviewed:

```bash
synapse-semantic-render ./track.mp3 --lyrics ./lyrics.txt \
  --db ./database/clips_semantic.duckdb \
  --global-usage ./database/global_clip_usage.json --aspect 9:16 \
  --output ./output/track.mp4
```

Selection requests a wider candidate set, excludes recent choices where
possible, and uses seeded weighted sampling. A logarithmic penalty for
cross-project usage helps reduce repetition while similarity remains the main
ranking signal. The global ledger is updated only after a successful render;
plan-only runs do not mutate it. The sample middle-frame index can still miss
important scene changes; multi-frame indexing and model-consistent re-embedding
are future improvements. Existing indexes are retained, not repaired or
re-embedded automatically. No virality or audience outcome is predicted.
