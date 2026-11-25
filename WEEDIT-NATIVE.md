# WE.ED.IT Native Genome — Compiler und Renderpipeline

WE.ED.IT stellt eine lokale Compiler-Pipeline bereit:

```text
Audio → SongAST → Shot-Intents → ClipDNA-Resolver → RenderAST
     → deterministische Optimierungspässe → optionales FFmpeg-Rendering
```

Kern-AST und Resolver benötigen weder GPU noch heruntergeladene Modelle. Audioanalyse,
Clip-Scanning, semantische Suche und Stem-Separation verwenden optionale Abhängigkeiten.

## Installation und lokaler Workflow

```bash
python -m pip install -e '.[test,audio,vision]'
weed scan ./clips --db ./database/genome.sqlite3
weed pool-plan ./music/song-a.mp3 ./music/song-b.mp3 \
  --db ./database/genome.sqlite3 --pool-size 25 --out ./reports/song-pool-plan.json
weed compile ./music/song-a.mp3 ./clips --db ./database/genome.sqlite3 \
  --pool-plan ./reports/song-pool-plan.json --out ./reports/song-a.json
weed report ./reports/song-a.json --out ./reports/song-a.html
weed render ./reports/song-a.json --out ./output/song-a.mp4
```

FFmpeg muss für Rendering separat installiert und über `PATH` erreichbar sein.
`weed compile` funktioniert weiterhin ohne Poolplan und verwendet dann den gesamten
indizierten Clipbestand. `weed make` kann ebenfalls `--pool-plan` verwenden. Rendert
nur bei explizitem `--out`; vorhandene Renderziele werden nicht überschrieben.

## Komponenten und Garantien

- `compiler.py`: Audio- und Beat-Eingaben in ein SongAST umsetzen.
- `genome.py`: lokale Clip-Metadaten indizieren und Dateiänderungen im Cache erkennen.
- `director.py`: musikalische Abschnitte in Shot-Intents übersetzen.
- `resolver.py`: Shot-Bedarf aus Beats aufbauen, Qualitätsgrenzen prüfen, Kandidaten
  deterministisch bewerten und Wiederholungen diversifizieren.
- `pool.py`: Songanforderungen gemeinsam bewerten und Kandidaten global reservieren.
- `optimizer.py` und `passes.py`: RenderAST validieren; deklarative oder nicht
  implementierte Analysen bleiben als solche kenntlich.
- `renderer.py`: FFmpeg führt die RenderAST aus; kreative Auswahl bleibt außerhalb.
- `replay.py`: lokale Entscheidungen zur späteren Prüfung speichern.

Der Scanner misst Bewegung, Helligkeit und Sättigung sowie einfache Tags. Er behauptet
keine Gesichts-, Emotions- oder Objekterkennung. Farbfilterung ist absichtlich minimal;
Details und Poolplan-Schema stehen in [`CLIP-POOL-PLANNING.md`](CLIP-POOL-PLANNING.md).

## Validierung und Grenzen

Die Song-Pool-Zuweisung ist global, deterministisch und exklusiv, solange genug Clips
vorhanden sind. Bei knapper Bibliothek werden Wiederverwendungen explizit markiert,
nicht verdeckt. Veraltete Planpfade brechen mit einem Diagnosefehler ab. Shotbedarf
wird aus expliziten Beats abgeleitet und schließt Abschnittsenden ohne stille Lücken.

```bash
python -m pytest tests/test_pool_planning.py tests/test_weedit_native.py -q
weed verify --db ./database/genome.sqlite3
```

Der Bestand implementiert keine AVX2-Bindings, GTX-1650-spezifische VRAM-Steuerung,
ComfyUI-Automation, DiD-Auswertung oder Multi-Agent-Schwärme. Hardwaregrenzen und
fehlende Komponenten werden nicht als implementierte Funktionen ausgegeben.
