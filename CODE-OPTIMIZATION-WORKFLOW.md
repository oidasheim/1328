# Code- und Logikoptimierung: Stackübergreifender Workflow

Dieses Handbuch beschreibt einen reproduzierbaren Prozess zur Verbesserung von Code, Workflows und Renderlogik in den Stacks dieses Repositorys. Ziel ist eine nachweisbare Verbesserung ohne Funktionsverlust. Es führt keine automatische Codeumschreibung oder externe Aktion aus.

## Grundregeln

- **Erst messen, dann ändern.** Lege die Baseline mit denselben Eingaben, Python-/C++-Versionen und optionalen Abhängigkeiten fest.
- **Korrektheit vor Geschwindigkeit.** Tests, Datenintegrität und reproduzierbares Verhalten sind harte Gates.
- **Eine Hypothese pro Änderung.** Kleine Diffs erleichtern Review und Regressionserkennung.
- **Nur echte Messungen berichten.** Unverfügbare GPU-, Render- oder Plattformdaten nicht durch Schätzungen ersetzen.
- **Optionales bleibt optional.** CPU-/Kernpfad darf nicht stillschweigend GPU, Netzwerk, Modell-Downloads oder fremde Dienste erfordern.
- **Sichtbare Grenzen erhalten.** Rendern, Posting, Cloud-Sync und Ausgaben nur in ausdrücklich dafür vorgesehenen, geprüften Abläufen.

## Ablauf

### 1. Ziel und Messgröße bestimmen

Notiere Problem, betroffenen Stack, Eingabefall, aktuelle Ausgabe und Erfolgskriterium. Geeignete Ziele sind zum Beispiel:

- weniger Laufzeit oder Speicher für dieselbe Eingabe;
- geringere Anzahl unnötiger Datei-/Datenbankoperationen;
- stabile Shot-Reihenfolge und vollständige Timeline-Abdeckung;
- klarere Fehler bei ungültigen Pfaden, Trims oder Konfigurationen;
- weniger optionale Abhängigkeiten auf dem Kernpfad.

Lege vorab eine akzeptable Toleranz fest. Semantische Änderungen (z. B. andere Clip-Auswahl) dürfen nicht als reine Performance-Optimierung ausgegeben werden.

### 2. Baseline sichern

Arbeite mit reproduzierbaren lokalen Eingaben. Erfasse Commit/Arbeitsstand, Konfiguration, Plattform, Laufzeit, Ergebnisstatus und Testausgabe. Bei Medien sind Quelldateien, Clip-Datenbank, BPM-/Beat-Eingaben, Ausgabeformat und Seed festzuhalten.

```bash
python -m pytest tests/ -q
weed verify --db database/genome.sqlite3
weed benchmark --db database/genome.sqlite3 --iterations 1000
```

Der `weed benchmark`-Befehl misst SQLite-Count-Roundtrips. Er misst **nicht** semantisches Matching, Kandidatenscoring, FFmpeg oder GPU-Durchsatz.

### 3. Betroffenen Stack zuordnen

| Stack | Optimierungsfläche | Korrektheits-/Mess-Gate |
|---|---|---|
| **SYNAPSE** (`synapse/`) | Manifest-Erzeugung, Stufenübergänge und Freigabezustände | `pytest tests/test_synapse_pipeline.py -q`; Manifest und Approval-Gates vergleichen |
| **WE.ED.IT Native** (`weedit_native/`) | Clip-Scan/Cache, Resolver, Shot-Timing, RenderAST-Pässe, Reports | `pytest tests/test_weedit_native.py tests/test_native_genome3.py -q`; AST-Kontinuität und Coverage prüfen |
| **SYNAPSE Fullstack** (`synapse/fullstack.py`) | Pfadprüfung, Input-Inventar, Stage-Status und lokale Reports | `pytest tests/test_fullstack.py -q`; PASS/WARN/FAIL-Zustände vergleichen |
| **Fullstack v9** (`src/fullstack_v9_workflow.py`) | Pfadauflösung, Batch-Audit und Ledger-Erzeugung | `pytest tests/test_fullstack_v9.py -q`; Profil und Audit-Constraints prüfen |
| **Audio, Vision und Semantic** (`synapse/`, optionale Extras) | Feature-Extraktion, Indexierung und optionale Abhängigkeiten | passendes Testmodul mit/ohne Extra ausführen; Fallbacks und Warnungen prüfen |
| **Portable Setup** (`scripts/portable_install.py`) | Verifikation, Datenbankinitialisierung und Berichtserzeugung | `pytest tests/test_portable_workflow.py -q`; Report-Stages und SQLite-Integrität prüfen |
| **Native C++20** (`native/`) | Granular-Synth-Kernel und Speicher-/DSP-Hotspots | CMake/CTest; dieselben Testvektoren vor und nach der Änderung |

### 4. Implementieren und reviewen

1. Füge bei Verhaltensänderung zuerst einen fokussierten Regressionstest hinzu.
2. Miss bei vermuteten Hotspots den betroffenen Abschnitt; optimiere keine unbewiesenen Engpässe.
3. Bewahre öffentliche CLI-Optionen, JSON-Felder und Datenbankschemata, oder dokumentiere explizit eine Migration.
4. Bei optimierten Auswahlalgorithmen stabile Tie-Breaks, Seeds und Sortierung erhalten.
5. Bei Timeline-/Media-Änderungen Frame-Rundung, positive Dauer, zusammenhängende Starts und vollständige Song-Coverage validieren.
6. Bei Datenbankänderungen Transaktionsgrenzen, Schema-Upgrade, Integrität und Reopen/Replay testen.
7. Platzhalterpass oder „not implemented“-Befund nicht in eine behauptete KI-/Lernfunktion umbenennen.

### 5. Nachher-Messung und Entscheidung

Führe dieselben Tests und denselben Benchmark mit denselben Eingaben aus. Vergleiche:

- Teststatus und beobachtbare Ausgaben;
- mediane Laufzeit bei mehreren Läufen (bei kleinen Differenzen Rauschen berücksichtigen);
- Speicher-/Datei-/Datenbankverhalten, soweit tatsächlich gemessen;
- neue optionale Abhängigkeiten und Plattformvoraussetzungen;
- JSON-/AST-/Ledger-Diff und Replay-Verhalten.

Akzeptiere nur, wenn die Korrektheits-Gates bestehen und der Effekt reproduzierbar ist. Bei keiner messbaren Verbesserung, Regression oder größerem Komplexitätsaufwand Änderung zurücknehmen oder als Wartbarkeit statt Performance klassifizieren.

### 6. Ergebnis dokumentieren

In Pull Request oder Änderungsnotiz festhalten:

```text
Stack/Datei:
Hypothese:
Eingaben und Umgebung:
Baseline und Messbefehl:
Änderung:
Tests vorher/nachher:
Messwerte vorher/nachher:
Korrektheits-/Datenintegritätsprüfung:
Limitierungen und optionale Abhängigkeiten:
Entscheidung:
```

Keine absoluten Performance-Versprechen aus einem einzelnen Hostlauf ableiten.

## WE.ED.IT Renderlogik: existierende Optimierungspässe

Die Kompilierpipeline läuft als `scan → SongAST → Director-Intents → Clip-Resolver → RenderAST → Optimierung`. `weedit_native/passes.py` führt die zehn benannten Pässe in festgelegter Reihenfolge aus. Die Evidenz wird pro Pass gesammelt und ist für Reports/Replay nutzbar.

| Pass | Implementiertes Verhalten |
|---|---|
| `BeatAlignmentPass` | Shot-Zeit und Dauer auf Frames runden, Shots anschließend lückenlos anordnen |
| `CameraContinuityPass` | Kamerawechsel zählen und als Evidenz berichten; keine automatische Kameraänderung |
| `MotionFlowPass` | Motion-Policy dokumentieren; keine zusätzliche Motion-Analyse |
| `ColorHarmonyPass` | vorhandene Farbwerte und Anzahl unterschiedlicher Farben berichten |
| `FaceDiversityPass` | erforderliche Metadaten/Policy kennzeichnen; keine Gesichtserkennung |
| `TransitionSimplificationPass` | Hard-Cut-Default berichten; Vereinfachung als nicht implementiert markieren |
| `SurprisePlacementPass` | nur Policy für freigegebene Effekte berichten; nicht implementiert |
| `RLRefinementPass` | mittleren Kandidatenscore deskriptiv berechnen; keine künstlichen Rewards |
| `RuntimeReductionPass` | Shots unter 150 ms entfernen und Timeline neu anordnen |
| `RenderValidationPass` | Shots, Maße, FPS, Dauer, Kontinuität und Song-Coverage prüfen |

`weedit_native/optimizer.py` bietet zusätzlich grundlegende RenderAST-Prüfung und Zeitnormalisierung. Die zehn Passes und der Basis-Optimizer sind verschiedene Schichten; Tests beider Schichten sollten mitlaufen.

```bash
python -m pytest tests/test_weedit_native.py tests/test_native_genome3.py -q
weed compile ./music/song.mp3 ./clips \
  --db ./database/genome.sqlite3 --out ./reports/song.render.json
weed report ./reports/song.render.json --out ./reports/song.html
```

Rendern nur explizit und mit geprüftem FFmpeg-Toolchain-Aufruf starten. Pass-Evidenz, AST und Renderreport nicht mit externer Performance-/Publikumswirkung verwechseln.

## Native C++-Änderungen

Der konfigurierte C++-Bereich ist `native/granular_synth.cpp`, gebaut als C++20-Static-Library. Das Projekt behauptet keine AVX2-/CUDA-Integration in dieser CMake-Zieldefinition.

```bash
cmake -S . -B build -DBUILD_TESTING=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

Bei DSP-Optimierungen dieselben deterministischen Testvektoren verwenden. Compiler-Flags, Compiler/Version und Build-Konfiguration dokumentieren; erst nach Korrektheit benchmarken.

## Sicherheits- und Betriebsgrenzen

- Das Handbuch beschreibt einen kontrollierten Entwicklungsprozess und keinen autonomen Optimierer, der Quellcode bearbeitet oder Befehle ausführt.
- Keine ungeprüfte Eingabe als Shell-Kommando ausführen.
- Paketinstallation, Modelle und optionale Native-Toolchains nur bewusst aktivieren.
- Externe Veröffentlichung, Cloud-Sync, Werbeausgaben und finanzielle Operationen sind keine Optimierungsziele des lokalen Baseline-Workflows.
