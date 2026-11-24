# WE.ED.IT OIDA Native Genome — vertical slice

This repository includes a modular compiler foundation for the MP3 → SongAST →
Intent → ClipDNA resolver → optimized RenderAST → FFmpeg path. It provides
functional scan, compile, render, make, and doctor commands. Audio decoding and
video feature scanning are optional extras; the AST/compiler tests can run
without model downloads or a GPU.

## Install

```bash
python -m pip install -e '.[test,audio,vision]'
```

FFmpeg must be installed separately and available on `PATH`. For clip scanning,
OpenCV is required. Audio feature extraction uses librosa. GPU inference is not
required by this baseline.

## One-command workflow

```bash
weed scan ./clips --db ./cache/genome.sqlite3
weed compile ./music/song.mp3 ./clips --db ./cache/genome.sqlite3 --out ./reports/song.render.json
weed render ./reports/song.render.json --out ./output/song.mp4
```

Or compile and render in one call (scans when the DB does not exist):

```bash
weed make ./music/song.mp3 ./clips --db ./cache/genome.sqlite3 \
  --ast ./reports/song.render.json --out ./output/song.mp4
```

`weed make` does not silently overwrite an existing render. Use a new output
path for each render. Keep inputs licensed and review the timeline before
publication.

## Architecture boundary

- `compiler.py`: audio → SongAST; deterministic fallbacks and warnings.
- `genome.py`: cached OpenCV clip features, keyed by file size and mtime.
- `director.py`: turns musical sections into human-readable shot intentions.
- `resolver.py`: scores candidates, applies recent-use novelty, and offers a
  small UCB1 selection interface; no external platform metrics are fabricated.
- `optimizer.py`: validates and normalizes shot timing before IR emission.
- `renderer.py`: FFmpeg backend only executes RenderAST; it makes no creative
  choices and always uses the source track as the sole audio input.

The initial feature scanner uses motion, brightness, saturation, and simple tags;
it does not claim face/emotion/object recognition. The `synapse` package already
contains optional OpenCLIP/DuckDB semantic indexing that can be integrated as a
resolver plugin. External BeatSync-Engine and CutClaw repositories are not
silently cloned or executed; adapters can be added behind these interfaces after
reviewing their licenses and APIs.

Run core tests with `pytest tests/test_weedit_native.py -q`.
