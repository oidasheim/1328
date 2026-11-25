# Global song-pool planning

WE.ED.IT can reserve a global clip inventory across a batch of songs before individual
timelines are compiled. This prevents a song processed first from consuming every
strong match that a later song needs. Reservations are deterministic, exclusive while
inventory permits, and scored against representative shot needs across each song.

## Setup and use

Install the local project with the optional audio and vision dependencies, index the
authorized local clip library, then make one plan for the complete batch:

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

Audio analysis uses the optional `audio` dependencies. `--pool-size` is the candidate
reservation count per song, not a promise that every reservation appears in the final
render. Planning never modifies, deletes, synthesizes, or publishes source clips.

## Allocation and safeguards

- Songs and clips use canonical paths and stable tie-breaking, so input ordering does
  not alter the plan.
- Matching averages scores over up to 32 evenly spaced shot needs from the entire
  song, rather than evaluating only the opening.
- Fair reservation rounds and a modest specificity bonus reduce first-song bias.
- When the inventory is smaller than total requested capacity, remaining candidates
  are shared explicitly as fallbacks and the plan contains a warning. A song is not
  silently given an empty pool if at least one usable clip exists.
- `--pool-plan` fails with a diagnostic if the song key or indexed clip is missing.
  Re-index and re-plan after changing the source library; do not silently substitute.

This is a deterministic reservation plan, not an optimal global assignment solver and
not a guarantee of release-level exclusivity. Shared fallbacks are visible in JSON.
No cross-release history, face identity, semantic embeddings, or unverified feedback
are used in allocation.

## Minimal quality and color filtering

Resolver defaults exclude invalid feature values and near-black/near-white samples
(brightness outside `[0.03, 0.99]`). This is a conservative usability guard, not a
cinematic color classifier. It uses measured brightness and saturation only; it does
not infer hue or apply grading. If the filter leaves no candidates, compilation fails
with a clear error rather than emitting an unusable or incomplete timeline.

## Plan and tests

The JSON plan uses `schema_version: 1` and records per-song clip paths, descriptive
scores, shared fallbacks, and unassigned inventory. Keep it with the AST for review.

```bash
python -m pytest tests/test_pool_planning.py tests/test_weedit_native.py -q
```

The repository does not thereby gain claimed C++/AVX2 acceleration, autonomous
ad-spend, trend scraping, external API publishing, multi-agent orchestration, or
hardware-specific performance. Those require separate, authorized implementations
and tests on the target machine.
