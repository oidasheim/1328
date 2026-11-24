# 1328 — Oidasheim SYNAPSE / WE.ED.IT

Lokale, Python-first Plattform für Musikproduktion, Beat-Synchronisation, semantische Clip-Auswahl und native WE.ED.IT-Workflows.

Der Repository-Stack kombiniert eine Python-CLI, lokale Datenbanken, C++-/CMake-Komponenten und verifizierte Offline-Prüfungen. Die implementierten Standardabläufe führen keine versteckten Veröffentlichungen, Werbeausgaben oder Cloud-Synchronisationen aus.

## Hauptbereiche

- **SYNAPSE** – Produktions- und Release-Planung sowie lokale JSON-Manifeste.
- **WE.ED.IT Native** – Director-, Lipsync-, Vocal-Stems-, Art-Director- und Diagnosebefehle.
- **Fullstack v9** – deterministische lokale Workflow-Profile und JSON-Ledgers.
- **Semantik und Analytics** – optionaler Clip-Index, Embeddings und evidenzbasierte Auswertungen.
- **Portable Setup** – lokale Verzeichnisse, SQLite-Initialisierung, Diagnose und Tests.

Der Python-Anteil bildet den Hauptteil des Projekts; C++20/CMake bietet native Komponenten für Performance-Spezialfälle.

## Schnellstart

Python 3.10 oder neuer wird benötigt.

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\python.exe -m pip install -e .
```

Linux/macOS:

```bash
.venv/bin/python -m pip install -e .
```

Optionales Test- und Vision-Setup:

```bash
python -m pip install -e '.[test,vision]'
pytest tests/ -q
```

## Typische Befehle

### SYNAPSE planen

```bash
synapse-plan path/to/track.mp3 --artist "Artist" --title "Titel" --genre "Genre"
```

Alternativ über Python:

```bash
python synapse_cli.py path/to/track.mp3 --artist "Artist" --title "Titel"
```

### WE.ED.IT Native CLI

```bash
python -m weedit_native.cli doctor --deep
python -m weedit_native.cli verify
python -m weedit_native.cli benchmark --iterations 250
python -m weedit_native.cli scan path/to/clips
python -m weedit_native.cli compile path/to/track.mp3
python -m weedit_native.cli report
```

Nach der Paketinstallation sind außerdem die konsolidierten Skript-Einstiege verfügbar, beispielsweise:

```bash
weed doctor
weed verify
weedit-art-director --help
weedit-lipsync --help
weedit-separate-vocals --help
```

### Fullstack v9

Der Workflow erzeugt nur lokale Prüf-, Vorschau- und Ledger-Artefakte. Der Standard ist `--dry-run`.

```bash
python src/fullstack_v9_workflow.py --eval
python src/fullstack_v9_workflow.py --profile full --dry-run
python src/fullstack_v9_workflow.py --profile dual --dry-run \
  --song path/to/music --clips path/to/clips --output output
```

Windows-Einstieg:

```bat
1CLICK_FULLSTACK_V9_WORKFLOW.bat --profile fast --dry-run
```

Verfügbare Profile:

| Profil | Enthaltene Stufen |
|---|---|
| `full` | Pfadprüfung, Audio/Beat, Distillation, Clips, lokale Vorschau, Audit, Ledger |
| `dual` | Pfadprüfung, Audio/Beat, Clips, lokale Vorschau, Ledger |
| `fast` | Pfadprüfung, Audio/Beat, lokale Vorschau, Ledger |
| `noparm` | Pfadprüfung, Audio/Beat, Verzeichnis-Snapshot, Clips, Vorschau, Ledger |
| `distill` | Pfadprüfung, Audio/Beat, lokale Wissensmetadaten, Clips |
| `sync` | Pfadprüfung, Audit, Ledger und blockierte Sync-Platzhalterstufe |

Für die externe Sync-Stufe ist ein gesondert geprüfter Adapter erforderlich. Ohne Adapter bleibt die Ausführung deaktiviert.

## Portables Setup

Das portable Setup-Skript legt lokale Verzeichnisse an, erstellt beziehungsweise aktualisiert die Genome-SQLite-Datenbank und erzeugt einen JSON-Bericht.

```bash
python scripts/portable_install.py --non-interactive --skip-tests
```

Mit Abhängigkeiten und Tests:

```bash
python scripts/portable_install.py --non-interactive --install-deps
```

Der Bericht wird unter `reports/portable-install-latest.json` geschrieben.

## Lokale Paket-Suche

Gefundene lokale Python-Pakete und Requirements können erst geprüft und danach in `.venv` installiert werden:

```bash
python scripts/install_candidates.py
python scripts/install_candidates.py --install
```

Die Installation wirkt nur auf das lokale Projekt-Environment. Virtuelle Umgebungen, VCS-Verzeichnisse, Build-Ausgaben und Vendor-Pfade werden ausgelassen.

## Ausgabeverzeichnisse

Standardmäßig werden lokale Laufzeitergebnisse unter diesen Pfaden abgelegt:

- `output/` – lokale Workflow-Ausgaben
- `reports/` – Diagnose-, Audit- und Run-Berichte
- `database/` – SQLite-Datenbanken
- `cache/` – Index- und Laufzeitdaten
- `models/` – optional manuell bereitgestellte Modelle
- `temp/` – temporäre Dateien

## Sicherheit und Grenzen

- Keine automatische Social-Media-Veröffentlichung.
- Keine autonome Werbeausgabe oder Budgeterhöhung.
- Keine Cloud-Synchronisation in den Standard-Workflows.
- Keine Behauptung von Modelltraining aus leerer oder synthetischer Inventur.
- Externe Aktionen, Rendering und Distribution erfordern getrennte Implementierung, Prüfung und menschliche Freigabe.
- Lizenz-, Rechte-, Sample- und Persönlichkeitsrechte bleiben bei der verantwortlichen Person.

## Dokumentation

- [INSTALLING.md](INSTALLING.md) – Installation und portable Einrichtung
- [FULLSTACK-V9.md](FULLSTACK-V9.md) – Fullstack-v9-Stufen und Profile
- [SYNAPSE-MODULE.md](SYNAPSE-MODULE.md) – SYNAPSE-Modulübersicht
- [WEEDIT-NATIVE.md](WEEDIT-NATIVE.md) – native WE.ED.IT-Befehle
- [POLYRHYTHMIK-KOMPENDIUM.md](POLYRHYTHMIK-KOMPENDIUM.md) – Rhythmus- und Takt-Spezifikation
- [FEEDBACK-ANALYTICS.md](FEEDBACK-ANALYTICS.md) – Feedback- und Messkonzept

Weitere Architektur- und Fachunterlagen befinden sich als Markdown-Dateien im Repository.

## Tests

```bash
pytest tests/ -v
```

## Lizenz

MIT License. Entwickelt durch das Oidasheim / OIDA Engine Team.
