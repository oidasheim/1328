# ART.WE.ED.IT — AI Music Video Director

The optional semantic workflow now joins the existing components into an
explainable editing loop:

1. `librosa` estimates beat times and per-beat energy.
2. Optional local TXT/HTML lyrics contribute coarse semantic context (not
   forced alignment or word-level timing).
3. The `DirectorProfile` maps BPM bands to configurable shot-duration windows
   and maps a small transparent keyword lexicon to visual prompt cues.
4. OpenCLIP text embeddings retrieve relevant clip frames from the existing
   DuckDB semantic index.
5. A seeded diversity selector reranks retrieved candidates with recent-use
   and cross-project usage penalties.
6. A reviewable plan records prompt, BPM, pacing window, selected similarity,
   themes, and top-two candidate margin; FFmpeg renders only when explicitly
   requested (normal mode), and output files are not overwritten.

## Run

```bash
python -m pip install -e '.[semantic]'
synapse-index-clips ./clips --db ./database/clips_semantic.duckdb
synapse-semantic-render ./track.mp3 --lyrics ./lyrics.txt \
  --db ./database/clips_semantic.duckdb --global-usage ./database/clip_usage.json \
  --seed 42 --plan-only
```

Review the JSON shot plan, then render with `--aspect 9:16 --output ./output/track.mp4`.
The shared usage ledger is updated only after a successful render. It can be
omitted for isolated/reproducible planning. The score margin is a descriptive
cosine retrieval gap, not calibrated model confidence.

## Scope and limitations

The system uses CLIP image/text semantics, beat/energy features, and explicit
heuristics; it does not use a hidden agent swarm, train an RL model, predict
virality, or claim platform algorithm knowledge. The included BPM ranges and
keyword mappings are editable starting heuristics, not empirical guarantees.
The current index embeds a representative frame per clip, so multi-frame
indexing, temporal scene understanding, captions/ASR alignment, and direct
integration into the native `RenderAST` resolver remain future work. Plan first;
review creative choices and media rights before publication.
