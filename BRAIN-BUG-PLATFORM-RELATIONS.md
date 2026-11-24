# CREATIVE_GENOME_OS 4.1 / brain.bug Platform Relations v1

This repository integration separates **production**, **knowledge and routing**,
and **external publication**. Platform percentages are internal routing
parameters, not measured facts about TikTok, Instagram, YouTube or another
provider. The system does not promise reach, algorithm access or financial ROI.

## Hierarchy

```text
brain.bug -> knowledge and memory
durak.kolecktiv -> creative corpus metadata
platform_relations_vector -> routing priority graph
CREATIVE_GENOME_OS -> samplechop / rough cut / finishing / QC / publish
stats_aggregator -> observed real-world events
wissens.destillat -> validated learning from telemetry
publisher_gate -> approve / hold / reject
```

## Feedback circuit

```text
published_asset_events
  -> stats_aggregator
  -> validated_telemetry
  -> wissens_destillat
  -> distilled_rule
  -> brain_bug_hub
```

The distillation circuit has no authority over its own evidence: forecasts never
become ground truth, and real events are not synthesized from predictions.

## Cross-system production stages

1. `samplechop` creates reusable audio assets.
2. `auto_mv_pro` creates only the rough cut.
3. `cinecutter` performs reviewable cinematic assembly.
4. `color_grader` applies non-destructive look decisions.
5. `qc` validates dimensions, duration, stream mapping, loudness profile,
   metadata, rights and human review status.
6. `publisher` is an explicit, human-confirmed external-action boundary.

## Meter and delivery

Beat synchronization is track-specific. A 4/4 assumption is not a universal
rule. The render plan must carry tempo, time signature, pickup bars, per-bar
meter, downbeat position, tempo and phrase/section markers when available.
Loudness is represented by named delivery profiles rather than one universal
LUFS target.

## Hard publisher gates

A route may only become `approve` when:

- content has been approved for release;
- a human explicitly confirms the release;
- rights/usage have been verified;
- QC has passed.

Without all four conditions, the result is `hold` or `reject`. The graph never
posts content or changes ad budgets. API credentials and external platform
calls should live behind separate, reviewed integrations.

## CLI

```bash
synapse-platform-vector export --out reports/platform_vector.json
synapse-platform-vector route asset-001 --target tiktok --target youtube_shorts
synapse-platform-vector gate asset-001 --approved --human-confirmed --rights-verified --qc-passed
```
