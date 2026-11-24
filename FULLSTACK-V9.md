# Fullstack v9 workflow

The v9 orchestrator is a deterministic, reviewable stage registry. It resolves
local paths, inventories legacy `.bat` files, creates a JSON audit/ledger and
supports dry-run profile selection. It does not execute external publishing,
cloud sync, ad spending or hidden workflow subprocesses.

## Stages

- `S0` resolve and verify paths
- `S1` build audio and beat report
- `S2` scan an explicitly supplied input directory
- `S3` distill local knowledge metadata
- `S4` prepare clip candidates
- `S5` prepare a local preview (no external action)
- `S6` create a review-only audit report
- `S7` write the JSON run ledger
- `S8` external-sync placeholder, blocked until a reviewed adapter is supplied

## Profiles

```text
full:   S0 S1 S3 S4 S5 S6 S7
dual:   S0 S1 S4 S5 S7
fast:   S0 S1 S5 S7
noparm: S0 S1 S2 S4 S5 S7
distill:S0 S1 S3 S4
sync:   S0 S6 S7 S8
```

The sync profile remains review-only and refuses external execution.

```bash
python src/fullstack_v9_workflow.py --eval
python src/fullstack_v9_workflow.py --profile full --dry-run
1CLICK_FULLSTACK_V9_WORKFLOW.bat --profile dual --dry-run
```

Environment fallbacks are optional: `OIDA_MUSIC_DIR`, `MUSIC_DIR`,
`OIDA_CLIPS_DIR`, `CLIPS_DIR`, `OIDA_OUTPUT_DIR`, and `OUTPUT_DIR`. Explicit
arguments take precedence.
