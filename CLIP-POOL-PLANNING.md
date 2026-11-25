# Global song-pool planning

WE.ED.IT can now reserve a global clip inventory across a batch of songs before
individual timelines are compiled. This prevents the first song processed from
claiming every strong match that a later song needs. Reservations are deterministic,
exclusive while inventory permits, and scored against representative shot needs
from across each complete song (not just its opening section).

## Setup

Install the local project with the audio and vision extras, index the authorized
local clip library once, then create one plan for the whole song batch:

```bash
python -m pip install -e '.[audio,vision,test]'
weed scan ./clips --db ./database/genome.sqlite3
weed pool-plan ./music/song-a.mp3 ./music/song-b.mp3 ./music/song-c.mp3 \
  --db ./database/genome.sqlite3 --pool-size 25 --out ./reports/song-pool-plan.json
```

Compile each song against its reservation:

```bash
weed compile ./music/song-a.mp3 ./clips --db ./database/genome.sqlite3 \
  --pool-plan ./reports/song-pool-plan.json --out ./reports/song-a.json
weed make ./music/song-b.mp3 ./clips --db ./database/genome.sqlite3 \
  --pool-plan ./reports/song-pool-plan.json --ast ./reports/song-b.json
```

Audio analysis uses the optional `audio` dependencies. Existing explicit-audio
analysis APIs remain available to Python callers. The global plan does not move,
rename, delete, synthesize, or modify source clips. `--pool-size` controls the
number of reserved candidates per song; it is not a promise that every reservation
will be used in the final timeline.

## Allocation and failure behavior

- Songs and clips use canonical absolute paths and stable tie-breaking, so input
  ordering does not alter the plan.
- Clip-to-song compatibility averages candidate scores over up to 32 evenly spaced
  shot needs, bounding planning work on long tracks while covering the whole song.
- Reservation runs in fair rounds. A modest specificity bonus prefers a clip for a
  song where it is unusually suitable, rather than letting an early song consume
  generic high-scoring clips first.
- When the clip count is below `song_count × pool_size`, the plan shares the best
  remaining candidates explicitly and reports the shortfall. No song is silently
  left with an empty pool if at least one usable clip exists.
- `--pool-plan` fails closed if the song key is missing or a reserved clip is no
  longer present in the current index. Re-index and re-plan after changing the
  media library rather than silently substituting different footage.

A pool is a reservation layer, not a hard no-reuse license. Shared fallbacks are
marked in the JSON plan so the operator can review scarcity. The planner does not
currently use cross-release history, face identity, semantic embeddings, or
unverified feedback to influence allocation.

## Minimal quality and color handling

The resolver excludes invalid feature records and near-black / near-white clips
(brightness outside `[0.03, 0.99]`) by default. This is intentionally a small,
reviewable guard against unusable frames, not a cinematic color classifier. It
uses measured brightness and saturation only; it does not infer hue or apply a
color grade. `warm` versus `natural` is only a light brightness preference. If
filtering leaves no candidates, compilation fails with a diagnostic instead of
creating a dead-end timeline or pretending a bad clip is acceptable.

## Audit and tests

The plan is JSON (`schema_version: 1`) with per-song clip paths, descriptive scores,
shared fallbacks, and unassigned inventory. Keep it alongside the render AST for
reproducibility. Run focused regression coverage with:

```bash
python -m pytest tests/test_pool_planning.py tests/test_weedit_native.py -q
```

This feature does not claim C++/AVX2 acceleration, GPU scheduling, causal DiD,
remote agents, portal publishing, or measured hardware speedups. Those require
separate implementations, reviewable tests, and benchmarks on the target machine.
