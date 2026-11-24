# Portable Art Director pipeline

`weedit_native.art_director` connects the existing scan, song compiler, genome
resolver, ten-pass RenderAST validation, report generation and SQLite replay
ledger into one local build command. Unlike the Windows-specific example, it
uses caller-provided paths and does not assume CUDA, DuckDB schemas, AVX2
bindings, a GPU, or a particular CPU layout.

Compile and validate, without rendering:

```bash
synapse-art-director assets/music/song.wav assets/clips --db database/genome.sqlite3
```

Render explicitly with the available FFmpeg backend:

```bash
synapse-art-director assets/music/song.wav assets/clips --render --output output/song.mp4
```

Artifacts are written to `reports/`: versioned AST JSON, HTML report, and a
manifest with source metadata fingerprints, optimizer evidence, replay-ledger
location, and limitations. The replay ledger is placed beside the configured
genome DB. `--cpu` disables the backend's NVENC preference. Outputs are
non-overwriting for rendered media, matching the existing renderer policy.

## Native boundary

The supplied C++ sample cannot safely be built as-is: its AVX2 header and CUDA
kernel are not present in the repository; the DuckDB schema is not defined by
this project; and a raw `__cuda_array_interface__` pointer alone does not ensure
allocation lifetime, device/context compatibility, shape/stride correctness,
or producer/consumer stream ordering. Therefore this integration deliberately
uses the tested Python path and makes no zero-copy or sub-millisecond claims.
A native backend should be added only with its ABI, ownership, stream semantics,
feature schema, and CPU fallback specified and tested.
