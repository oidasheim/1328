# WE.ED.IT Native Genome 3.0 upgrade

This upgrade adds the repository's next compiler layer:

- ten named LLVM-style optimization passes;
- frame-snapped beat alignment;
- sub-150 ms runtime removal;
- contiguous-shot and even-dimension validation;
- replay ledger in SQLite with input hash and pass evidence;
- HTML/JSON compilation reports;
- deterministic built-in style packages;
- catalog usage threshold guard;
- explicit opt-in interfaces for local reward and face metadata; no fabricated learning claims.

## Passes

`BeatAlignmentPass`, `CameraContinuityPass`, `MotionFlowPass`,
`ColorHarmonyPass`, `FaceDiversityPass`, `TransitionSimplificationPass`,
`SurprisePlacementPass`, `RLRefinementPass`, `RuntimeReductionPass`, and
`RenderValidationPass` execute as an ordered pipeline. Placeholder passes are
clearly marked and never pretend to perform unavailable face or effect analysis.

## Replay

Each shot decision can be stored with candidate IDs, selected score, optional
human-provided reward, pass evidence, and a SHA-256 hash of the inputs.

```python
ledger = ReplayLedger("cache/replay.sqlite3")
ledger.record("render-001", "shot-00001", shot, ["clip-a", "clip-b"], evidence, input_hash)
print(ledger.replay("shot-00001"))
ledger.close()
```

## Style package

```python
from weedit_native.styles import install_style
install_style(".", "cinematic")
```

Run tests with:

```bash
pytest tests/test_native_genome3.py -q
```
