# SYNAPSE Master Art Director

The repository now includes a portable, reviewable master-art-director baseline:

- optional 48 kHz audio feature analysis through `librosa`;
- bar/section/tension/delta-energy features;
- optional DuckDB `clip_master_index` loading;
- 32-byte-aligned NumPy allocator for future AVX2/native bindings;
- transparent recent-use and 66.7-percentile-style cooldown filtering;
- buildup end blackouts, but no strobe or forced psychoacoustic effect;
- a JSON timeline IR with source and frame boundaries;
- FFmpeg fallback rendering and optional NVENC detection;
- loudnorm target `I=-14 LUFS`, `TP=-1 dBTP`, `LRA=11`, 320 kbps AAC, 48 kHz;
- no hard-coded `K:\` paths, credentials, GPU assumptions, or publishing steps.

## CLI

```bash
synapse-art-director ./track.mp3 --db ./clips.duckdb --out ./reports/timeline.json
synapse-art-director ./track.mp3 --db ./clips.duckdb --out ./reports/timeline.json --render ./output/master.mp4
```

The CLI prints a plan and can write the JSON timeline before rendering. Existing
render targets are never overwritten. The FFmpeg branch uses source audio only;
no clip audio is mixed into the master.

## Native/CUDA boundary

The native C++20 binding is intentionally not loaded by default. A future
`cxx_accel` ABI must verify array alignment, dimensions, dtype, source lifetime,
and stream ownership before it receives pointers. CuPy/PyTorch tensor interfaces
must expose valid device pointers and shapes. Kernel output and stream completion
must be synchronized where the caller consumes host memory.

## DuckDB schema

The loader currently expects:

```sql
clip_id, file_path, scene_group_id, usable_frames, last_used_bar,
shot_scale, mean_luma, dominant_hue, motion_vec_x, motion_vec_y,
lip_motion_score, semantic_role, use_count
```

Missing columns or malformed values fail explicitly. The baseline's benchmarked
frame selection is not claimed; run representative hardware tests before
publishing performance figures.

## Tests

```bash
pytest tests/test_art_director.py -q
```
