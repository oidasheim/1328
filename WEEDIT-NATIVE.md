# WE.ED.IT OIDA Native Genome — Compiler und Renderpipeline

WE.ED.IT stellt eine lokale Compiler-Pipeline bereit:

```text
Audio → SongAST → Shot-Intents → ClipDNA-Resolver → RenderAST
     → deterministische Optimierungspässe → optionales FFmpeg-Rendering
```

Die Kern- und AST-Tests benötigen weder GPU noch heruntergeladene Modelle. Audioanalyse, Clip-Scanning, semantische Suche und Stem-Separation verwenden optionale Abhängigkeiten.

## Installieren

```bash
python -m pip install -e '.[test,audio,vision]'
```

FFmpeg muss separat installiert und über `PATH` erreichbar sein, wenn gerendert werden soll. OpenCV wird für Clip-Scanning und librosa für optionale Audio-Feature-Extraktion benötigt.

## Workflow

```bash
weed scan ./clips --db ./database/genome.sqlite3
weed compile ./music/song.mp3 ./clips \
  --db ./database/genome.sqlite3 --out ./reports/song.render.json
weed report ./reports/song.render.json --out ./reports/song.html
weed render ./reports/song.render.json --out ./output/song.mp4
```

`weed make` kann Scan (falls die Datenbank noch fehlt), Kompilierung und optionales Rendern bündeln:

```bash
weed make ./music/song.mp3 ./clips \
  --db ./database/genome.sqlite3 \
  --ast ./reports/song.render.json \
  --out ./output/song.mp4
```

Lasse `--out` weg, wenn nur das AST erzeugt werden soll. Render-Ausgaben werden nicht stillschweigend überschrieben. Benutze für jeden Render einen neuen Zielpfad und prüfe das Ergebnis vor Veröffentlichung.

## Stack und Grenzen

- `compiler.py`: Audio- und Beat-Eingaben in ein SongAST umsetzen; deterministische Fallbacks und Warnungen.
- `genome.py`: lokale Clip-Metadaten/Features indizieren und zwischenspeichern.
- `director.py`: musikalische Abschnitte in Shot-Intents übersetzen.
- `resolver.py`: Kandidaten bewerten, Tie-Breaks stabil halten und Auswahl gegen kürzliche Wiederverwendung diversifizieren.
- `passes.py`: geordnete zehnstufige Optimierung und Validierung; nicht implementierte Analysen werden als solche ausgewiesen.
- `optimizer.py`: Basisprüfungen für Quelle, Trims, Timeline, Maße, FPS und Song-Coverage.
- `replay.py`: lokale Entscheidungen und Evidenz für spätere Prüfung speichern.
- `renderer.py`: FFmpeg führt die RenderAST aus; kreative Auswahl bleibt außerhalb des Renderers. Der Source-Track ist die Audioquelle.

Der einfache Feature-Scanner ermittelt Bewegung, Helligkeit, Sättigung und einfache Tags. Er behauptet keine Gesichts-, Emotions- oder Objekterkennung. `synapse/` bietet optionale semantische Indizierung, die nicht automatisch vorausgesetzt wird. Fremde Engines werden nicht ohne explizite Adapterintegration geklont oder ausgeführt.

## Zehn Render-Pässe

In der Reihenfolge von `weedit_native/passes.py`:

1. `BeatAlignmentPass` – Zeitwerte auf Frames runden und Shots lückenlos ordnen.
2. `CameraContinuityPass` – Kamerawechsel als Evidenz zählen.
3. `MotionFlowPass` – deklarierte Motion-Policy berichten.
4. `ColorHarmonyPass` – vorhandene Farbwerte zusammenfassen.
5. `FaceDiversityPass` – Metadatenanforderung dokumentieren; keine Gesichtserkennung.
6. `TransitionSimplificationPass` – Hard-Cut-Default berichten; Vereinfachung derzeit nicht implementiert.
7. `SurprisePlacementPass` – freizugebende Effekt-Policy berichten; nicht implementiert.
8. `RLRefinementPass` – Kandidatenscore deskriptiv zusammenfassen, ohne Reward zu erfinden.
9. `RuntimeReductionPass` – Sub-150-ms-Shots entfernen.
10. `RenderValidationPass` – Dimensions-, FPS-, Shot-, Kontinuitäts- und Coverage-Invarianten prüfen.

Nicht jeder benannte Pass transformiert die Timeline. Die Pass-Evidenz unterscheidet Messung/Policy von tatsächlich implementierter Veränderung.

## Diagnose, Styles, Replay und Benchmark

```bash
weed doctor --deep
weed verify --db ./database/genome.sqlite3
weed style list
weed style install cinematic
weed replay shot-id --db ./database/replay.sqlite3
weed benchmark --db ./database/genome.sqlite3 --iterations 1000
```

Der Benchmark misst lokale SQLite-Count-Roundtrips, kein Vector-Scoring oder Rendern. Styles sind deklarative Startkonfigurationen, keine trainierten Modelle oder externen LUTs. Replay-Daten dienen der Nachvollziehbarkeit und sind für sich allein kein Beleg für lernende Performance.

## Tests

```bash
python -m pytest tests/test_weedit_native.py tests/test_native_genome3.py -q
```

Für eine systematische Codeoptimierung inklusive Vorher-/Nachher-Messung siehe [`CODE-OPTIMIZATION-WORKFLOW.md`](CODE-OPTIMIZATION-WORKFLOW.md).
