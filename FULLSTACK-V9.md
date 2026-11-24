# Fullstack v9 workflow

The v9 orchestrator is a deterministic, reviewable stage registry. It resolves local paths, inventories legacy `.bat` files, creates a JSON audit/ledger and supports dry-run profile selection. It does not execute external publishing, cloud sync, ad spending, rendering, or arbitrary workflow subprocesses.

## Stages

| ID | Stage | Behavior |
|---|---|---|
| `S0` | Resolve paths | Resolve explicit paths, optional environment variables, then local fallbacks. |
| `S1` | Audio and beat report | Stage is declared in the profile; this orchestrator writes a local plan and does not execute an audio-render pipeline. |
| `S2` | Input-directory scan | Stage is declared for an explicitly provided input directory. |
| `S3` | Local knowledge metadata | Stage is declared in selected profiles; no model training is claimed. |
| `S4` | Clip candidates | Local candidate-preparation stage in the plan. |
| `S5` | Local preview | Preview stage only; this orchestrator does not render media. |
| `S6` | Review-only audit | Inventory `.bat` files and flag simple portability/external-action patterns. Findings require human review. |
| `S7` | JSON run ledger | Write a local report with profile, path resolution, audit and constraints. |
| `S8` | External-sync placeholder | Requires a separately reviewed adapter; external execution is blocked. |

The profile registry is defined in `src/fullstack_v9_workflow.py`. A profile selects stages for planning; it should not be read as proof that an audio render, upload, or external synchronization happened.

## Profiles

```text
full:    S0 S1 S3 S4 S5 S6 S7
dual:    S0 S1 S4 S5 S7
fast:    S0 S1 S5 S7
noparm:  S0 S1 S2 S4 S5 S7
distill: S0 S1 S3 S4
sync:    S0 S6 S7 S8
```

`sync` remains review-only and refuses external execution.

## Run

```bash
python src/fullstack_v9_workflow.py --eval
python src/fullstack_v9_workflow.py --profile full --dry-run
python src/fullstack_v9_workflow.py --profile dual \
  --song ./music --clips ./clips --output ./output
```

On Windows:

```bat
1CLICK_FULLSTACK_V9_WORKFLOW.bat --profile fast --dry-run
```

Optional environment fallbacks are `OIDA_MUSIC_DIR`, `MUSIC_DIR`, `OIDA_CLIPS_DIR`, `CLIPS_DIR`, `OIDA_OUTPUT_DIR`, and `OUTPUT_DIR`. Explicit arguments take precedence. `--ledger` chooses the JSON report destination; otherwise the workflow writes under `reports/`.

`--dry-run` is the default and currently the only exposed mode. It is an `argparse` flag with a true default; there is no command-line option to disable it. `--eval` writes a review-only batch-file inventory report.

## Optimization and testing

Use the stack-wide baseline → small change → regression tests → repeat measurement process in [`CODE-OPTIMIZATION-WORKFLOW.md`](CODE-OPTIMIZATION-WORKFLOW.md). For this orchestrator, verify path resolution, profile-stage lists, audit findings, and ledger constraints rather than claiming render-speed gains.

```bash
python -m pytest tests/test_fullstack_v9.py -q
```
