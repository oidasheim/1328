# Optional local lip-sync analysis

The `weedit_native.lipsync` module adds phoneme-alignment-to-MAR conversion,
a local audio formant-energy proxy, and bounded DTW-style matching for a
provided clip MAR curve. It does not identify faces, infer identity, or run
transcription. Supply time-aligned phoneme records explicitly (for example,
from a locally run aligner) and a per-clip MAR curve produced by an authorized
visual-analysis pipeline.

```json
[
  {"start": 0.12, "end": 0.22, "phoneme": "B"},
  {"start": 0.22, "end": 0.41, "phoneme": "AA"}
]
```

Generate a target curve and compare it with a clip curve:

```bash
weedit-lipsync compile alignments.json --duration 4.2 --fps 60 --out reports/target-mar.npy
weedit-lipsync match assets/clip-mar.npy reports/target-mar.npy
```

For an unaligned audio signal, the optional fallback is a broad 300–3400 Hz
formant-energy **proxy**, not a phoneme-level or accurate lip-sync solution:

```bash
weedit-lipsync fallback vocal.wav --duration 4.2 --fps 60 --out reports/audio-proxy.npy
```

The matcher tests bounded speed factors in `[0.94, 1.06]` and a finite offset
grid. Its score is descriptive curve similarity, not a probability. It does not
perform GPU rendering or alter video frames. Do not treat generic audio energy
as phoneme alignment; use a reviewed alignment when synchronization matters.
