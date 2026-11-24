# SYNAPSE AUDIO DYNAMICS integration

The repository now contains portable configuration primitives in
`synapse.dynamics` and a safe full-stack runner in `synapse.fullstack`.

## Scope

- validates FPS, dimensions, sample rate, loudness and catalog-lock parameters;
- exposes CPU/NVENC FFmpeg argument builders;
- reports available local tools without assuming CUDA or a particular GPU;
- validates CPU affinity values without mutating process affinity;
- evaluates configured music and clip directories;
- writes a version ledger and JSON report;
- keeps rendering, publishing, ad scaling, and account automation explicit.

Run a local dry run:

```bash
synapse-fullstack --root . --music music --clips clips --reports reports
```

The baseline intentionally does not implement autonomous posting, purchased
engagement, hidden identities, wallet operations, or smart-contract deployment.
A real renderer can consume the existing art-director timeline after an explicit
review step. Hardware performance claims must be measured on the target machine;
configuration values are not benchmarks.
