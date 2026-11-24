# Portable WE.ED.IT Workflow

Dieses Repository enthält einen lokalen, ausführbaren Teil des vorgeschlagenen SYNAPSE/WE.ED.IT-Stacks. Die portable Einrichtung behauptet nicht, externe Agent-Swarms, Posting-APIs, Anzeigen, Kausalmodelle oder Smart Contracts bereitzustellen.

## Setup und Verifikation

Windows:

```bat
PORTABLE_INSTALL.bat --non-interactive
```

Optionale Dependency-Installation explizit aktivieren (Paketindex/Netzwerk erforderlich):

```bat
PORTABLE_INSTALL.bat --install-deps --non-interactive
```

Cross-platform:

```bash
python scripts/portable_install.py --non-interactive
```

Der Batch richtet lokale Verzeichnisse ein, prüft Toolchain und Invarianten, installiert deklarative Styles, misst SQLite-Roundtrips, initialisiert das Genome-Schema und führt pytest aus, wenn verfügbar. Ergebnisse werden in `reports/portable-install-latest.json` gespeichert. `--keep-going` sammelt weitere Stufenergebnisse nach einem Fehler; `--skip-tests` überspringt Tests.

## Haupt-CLI

```bash
weed doctor --deep
weed toolchain
weed verify
weed scan assets/clips --db database/genome.sqlite3
weed style list
weed style install cinematic
weed benchmark --db database/genome.sqlite3 --iterations 1000
weed make assets/music/song.mp3 assets/clips \
  --db database/genome.sqlite3 \
  --ast reports/song.json --out output/song.mp4
weed report reports/song.json --out reports/song.html
weed replay shot-id --db database/replay.sqlite3
```

Für die SYNAPSE-Planung und den Fullstack-v9-Dry-Run siehe [`README.md`](README.md) und [`FULLSTACK-V9.md`](FULLSTACK-V9.md).

## Optimierung und Wartung

- Erst Baseline und relevante pytest-Suite sichern, danach eine Hypothese pro Änderung umsetzen.
- SQLite-Benchmark nur für lokale DB-Count-Roundtrips auswerten; er ist kein Render- oder Kandidatenscoring-Benchmark.
- Nach Workflow- oder Datenbankänderungen Stage-Bericht, SQLite-Integrität und Regressionstests prüfen.
- Performancevergleiche auf demselben Host und mit derselben Konfiguration durchführen.

Der ausführliche stackübergreifende Prozess steht in [`CODE-OPTIMIZATION-WORKFLOW.md`](CODE-OPTIMIZATION-WORKFLOW.md).

## Grenzen

Die Messungen beziehen sich auf den aktuellen Host. Styles sind deklarative Startbedingungen, keine trainierten kreativen Modelle. Automatisches Posting, Werbeausgaben, Identitätsnutzung und On-Chain-Transaktionen sind nicht implementiert.
