# 1328 — Oidasheim SYNAPSE / WE.ED.IT

Lokale, Python-first Werkzeugkette für Musik- und Clip-Analyse, Produktionsplanung, Timeline-Kompilierung und nachvollziehbare Workflow-Prüfungen. Der Code umfasst mehrere zusammenarbeitende, aber eigenständig nutzbare Stacks. C++20/CMake ist für den nativen Granular-Synth-Kern vorgesehen; die Haupt-CLI und die meisten Workflows sind Python.

## Stacks im Überblick

| Stack | Aufgabe | Einstiegspunkt |
|---|---|---|
| **SYNAPSE** | Lokale Produktions-/Release-Pläne und JSON-Manifeste mit expliziten Freigabegrenzen | `synapse-plan`, `synapse/` |
| **WE.ED.IT Native** | Clip-Index, SongAST, Shot-Intents, Resolver, optimierte RenderAST, Reports und optionales FFmpeg-Rendering | `weed`, `weedit_native/` |
| **SYNAPSE Fullstack** | Lokale Eingabeprüfung und gestufte Orchestrierung mit Berichten | `synapse-fullstack` |
| **Fullstack v9** | Reviewbarer Stage-Plan, lokaler Batch-Datei-Audit und JSON-Ledger; kein externer Sync | `synapse-fullstack-v9`, `src/fullstack_v9_workflow.py` |
| **Audio-/Semantik-Tools** | Optionale Audio-, Vision-, Embedding-, Feedback-, Stem- und Evidenz-Funktionen | `synapse/`, `weedit_native/` |
| **Native C++** | C++20-Granular-Synth-Bibliothek mit CTest-Test | `native/`, `CMakeLists.txt` |
| **Portable Setup** | Lokale Verzeichnisse, Datenbankinitialisierung, Diagnose und Testbericht | `scripts/portable_install.py` |

Die optionale Abhängigkeitsgruppen und ausführbaren Paketbefehle sind in [`pyproject.toml`](pyproject.toml) definiert. GPU, Modellgewichte und optionale Medienbibliotheken sind keine Voraussetzung für die Kern- und AST-Tests.

## Schnellstart

Voraussetzung: Python 3.10 oder neuer.

```bash
python -m venv .venv
```

Windows (PowerShell):

```powershell
.venv\Scripts\python.exe -m pip install -e '.[test]'
.venv\Scripts\weed.exe doctor
```

Linux/macOS:

```bash
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/weed doctor
```

Für Audio-Analyse und Clip-Scanning installiere die passenden optionalen Extras sowie FFmpeg separat:

```bash
python -m pip install -e '.[audio,vision]'
```

## Typische Workflows

### SYNAPSE: Release-Plan erstellen

```bash
synapse-plan path/to/track.mp3 \
  --artist "Artist" --title "Track" --genre "Genre" \
  --out reports/synapse_manifest.json
```

Der Plan ist lokal. Posting, Anzeigen, Outreach und finanzielle Transfers sind keine automatischen CLI-Aktionen und benötigen gesonderte Integrationen und Freigaben.

### WE.ED.IT: scannen, kompilieren und rendern

```bash
weed scan ./clips --db ./database/genome.sqlite3
weed compile ./music/song.mp3 ./clips \
  --db ./database/genome.sqlite3 --out ./reports/song.render.json
weed render ./reports/song.render.json --out ./output/song.mp4
```

Oder als expliziter Ein-Aufruf-Workflow:

```bash
weed make ./music/song.mp3 ./clips \
  --db ./database/genome.sqlite3 \
  --ast ./reports/song.render.json \
  --out ./output/song.mp4
```

`weed make` rendert nur, wenn `--out` angegeben ist. Das Render-Backend benötigt FFmpeg. Prüfe Timeline, Quellenrechte und Ergebnis vor einer Veröffentlichung. Siehe [`WEEDIT-NATIVE.md`](WEEDIT-NATIVE.md).

### Fullstack v9: lokale Planung und Audit

```bash
python src/fullstack_v9_workflow.py --eval
python src/fullstack_v9_workflow.py --profile full --dry-run
python src/fullstack_v9_workflow.py --profile dual --song ./music \
  --clips ./clips --output ./output
```

Der Standard ist Dry-Run. Der `sync`-Profilplatzhalter blockiert externe Ausführung; die Orchestrierung veröffentlicht, synchronisiert keine Cloud und gibt kein Werbebudget aus. Details in [`FULLSTACK-V9.md`](FULLSTACK-V9.md).

### Portable Diagnose und Tests

```bash
python scripts/portable_install.py --non-interactive --skip-tests
python -m pytest tests/ -q
```

Der Diagnosebericht liegt anschließend in `reports/portable-install-latest.json`. Dependencies werden nur mit `--install-deps` installiert.

### C++20-Granular-Synth testen

```bash
cmake -S . -B build -DBUILD_TESTING=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

## Optimierungsworkflow für Code und Logik

Vor einer Optimierung Messbasis und Regressionstests festlegen; nur eine verhaltensrelevante Änderung pro Schritt vornehmen. Den Compiler-/RenderAST-Pass-Ablauf und die stackübergreifende Code-Optimierung dokumentiert [`CODE-OPTIMIZATION-WORKFLOW.md`](CODE-OPTIMIZATION-WORKFLOW.md).

Kurzablauf:

1. Baseline, Eingaben, Umgebung und erwartetes Verhalten dokumentieren.
2. Relevante Tests und einen reproduzierbaren lokalen Benchmark ausführen.
3. Eng begrenzte Änderung implementieren; keine ungemessenen Parallelisierungs- oder GPU-Annahmen.
4. Tests erneut ausführen und Ausgabe, Laufzeit sowie Speicher-/Datenintegrität vergleichen.
5. Änderungen mit messbarem Gewinn und ohne Regression behalten; JSON-Bericht und Entscheidung protokollieren.

```bash
python -m pytest tests/ -q
weed benchmark --db database/genome.sqlite3 --iterations 1000
```

Der WE.ED.IT-Benchmark misst lokale SQLite-Count-Roundtrips, nicht Clip-Scoring oder Rendergeschwindigkeit. Benchmarkwerte sind hostabhängig.

## Optionale Extras

| Extra | Zweck |
|---|---|
| `audio` | librosa, NumPy und SoundFile für Audioanalyse |
| `vision` | OpenCV und NumPy für Clip-Features |
| `semantic` | DuckDB, OpenCLIP, Torch, Pillow, OpenCV, NumPy und librosa |
| `stems` | Demucs und audio-separator für optionale Stem-Trennung |
| `cuda` | CuPy-CUDA-12-Option; erfordert passende lokale CUDA-Umgebung |
| `test` | pytest und NumPy für Tests |
| `cliruntime` | Rich für optionale CLI-Darstellung |

Nur installieren, was für den eigenen Workflow gebraucht wird:

```bash
python -m pip install -e '.[audio,vision]'
python -m pip install -e '.[semantic]'
```

## Dokumentation

- [`INSTALLING.md`](INSTALLING.md) – lokale Paketinstallation und Candidate-Scanner
- [`PORTABLE-WORKFLOW.md`](PORTABLE-WORKFLOW.md) – portable Einrichtung und CLI
- [`WEEDIT-NATIVE.md`](WEEDIT-NATIVE.md) – WE.ED.IT Pipeline und RenderAST-Optimierung
- [`NATIVE-GENOME-3.md`](NATIVE-GENOME-3.md) – Render-Pässe, Replay-Ledger und Styles
- [`CODE-OPTIMIZATION-WORKFLOW.md`](CODE-OPTIMIZATION-WORKFLOW.md) – messbarer Optimierungsprozess für alle Stacks
- [`SYNAPSE-MODULE.md`](SYNAPSE-MODULE.md) – SYNAPSE-Manifeste und Freigabegrenzen
- [`FULLSTACK-V9.md`](FULLSTACK-V9.md) – v9-Profile und lokaler Audit
- [`POLYRHYTHMIK-KOMPENDIUM.md`](POLYRHYTHMIK-KOMPENDIUM.md) – Rhythmus-Referenz

## Sicherheit und Grenzen

- Standardabläufe sind lokal; Posting, Werbeausgaben und Cloud-Synchronisation sind nicht aktiv.
- Optionale Pakete können Modelle oder weitere Runtime-Komponenten benötigen; Installationen aus Paketindizes nur nach eigener Prüfung ausführen.
- Der einfache Clip-Scanner behauptet keine Gesichts-, Emotions- oder Objekterkennung.
- Optimierungspässe mit nicht implementierter Analyse sind als Platzhalter gekennzeichnet und erzeugen keine fingierten Reward- oder Trainingsdaten.
- Medien müssen lizenziert sein; externe Aktionen benötigen getrennte Prüfung und Freigabe.

## Lizenz

MIT License. Entwickelt durch das Oidasheim / OIDA Engine Team.
