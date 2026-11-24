# WE.ED.IT portable batch workflow

This repository provides a real, local-first subset of the proposed unified
stack. It does not claim that external agent swarms, APIs, model weights,
posting agents, ad systems, causal models, or smart contracts are present.

## Run the complete setup and verification batch

Windows:

```bat
PORTABLE_INSTALL.bat --non-interactive
```

Optional dependency installation is explicit (requires network/package index):

```bat
PORTABLE_INSTALL.bat --install-deps --non-interactive
```

Cross-platform equivalent:

```bash
python scripts/portable_install.py --non-interactive
```

The batch runs local directory setup, optional dependency checks, doctor,
seven deterministic style installs, invariant verification, a measured SQLite
roundtrip benchmark, genome schema initialization, pytest when available, and
an inventory/integrity report. It writes `reports/portable-install-latest.json`.
Warnings such as missing FFmpeg or pytest are reported; they do not masquerade
as successful checks. Use `--keep-going` to collect all stage results after a
failure. No external drive paths are required.

## CLI

```bash
weed doctor --deep
weed toolchain
weed verify
weed scan assets/clips --db database/genome.sqlite3
weed style list
weed style install cinematic
weed benchmark --db database/genome.sqlite3 --iterations 1000
weed make assets/music/song.mp3 assets/clips --db database/genome.sqlite3 --ast reports/song.json --out output/song.mp4
weed report reports/song.json --out reports/song.html
weed replay shot-id --db database/replay.sqlite3
```

The `benchmark` reports only measurements performed on the current host. The
style packages are declarative starter constraints, not external LUTs or
trained creative models. Automatic posting, ad spend, hidden identity use, and
on-chain transactions are deliberately not implemented.
