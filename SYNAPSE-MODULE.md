# Modular SYNAPSE workflow

The `synapse/` package models the real-world production handoff:

```text
Artist → KAIRO → VEGA → JINX → ORION → ATLAS → approval gates
```

Run a plan without publishing, spending money, or executing financial transfers:

```bash
python synapse_cli.py input/track.mp3 \
  --artist OIDAHEIM \
  --title "Weiß Wurscht des Musik" \
  --genre "Bavarian Hip-Hop" \
  --out reports/distribution_manifest.json
```

The manifest records audio analysis, mastering/QC, visual formats, distribution
channels, and finance status. External social posting, advertisements, creator
outreach, and royalty settlement are intentionally represented as approval gates;
credentials, rights checks, platform terms, budgets, and legal review must be
handled by explicit integrations.

Run tests with:

```bash
pytest tests/test_synapse_pipeline.py -q
```
