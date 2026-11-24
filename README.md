# 1328 — WE.ED.IT / Oidasheim Ecosystem

> Lokale, hardwarebewusste Musik-, Visual- und Distributions-Engine für autonome Musikvideo-Produktion.

Diese Repository vereint die Leitlinien und Architekturen von **WE.ED.IT**, **Native Genome Engine**, **SYNAPSE AUDIO DYNAMICS** und BeatSync zu einem gemeinsamen Produktionssystem.

## Kernvision

Die Pipeline behandelt einen MP3-Track wie Quellcode:

```text
MP3 → Beat-/Audio-Analyse → Song-AST → Director-Absichten
    → Shot-AST → Optimierungs-Pässe → Kandidatensuche
    → Render-IR → FFmpeg/NVENC → MP4 + OTIO
```

Traditionelles Schnittskript wird durch einen Compiler-Ansatz ersetzt:

- Der Track bestimmt Dauer, Beats, Phrasen, Drops und Energieverlauf.
- Die Clip-Bibliothek bildet die persistente Standard-Library.
- Director-Presets erzeugen Shot-Absichten statt starre Clip-Zuweisungen.
- Optimierer reduzieren Wiederholungen, halten Kamerakontinuität und sichern den Rhythmus.
- Der Renderer ist deterministisch und besitzt keine kreative Entscheidungslogik.

## WE.ED.IT Director 4.0

WE.ED.IT Director ist eine professionelle, weitgehend autonome Videoproduktions-Engine für Hip-Hop, Deutschrap, 140-BPM-Trap, Boom-Bap und elektronische Musik.

### Hauptmodule

- **Audio-DSP**: Beat-Tracking, Transient-Snapping, Felt-Tempo, Onsets und Drop-Erkennung.
- **MixMeister-Fallback**: Professionelle BPM-Erkennung bei schwer analysierbaren Tracks.
- **Stem-Separation**: 4-Stem-Demucs mit Vocals, Drums, Bass und Other.
- **Vocal-Ducking**: Dynamisches Sidechain-Ducking und Stereo-Vocal-Doubler.
- **Clip-Highlights**: Schärfe, Dynamik, Farbtemperatur, Rule-of-Thirds und Horizontalausgleich.
- **140-BPM-Sync**: On-Beat-Schnitte auf 3–4 Bars oder Hold-Fenster auf besonders starken Highlights.
- **Director Council**: `HYPER_STREET`, `CINEMATIC_PUNCH`, `VIRAL_TIKTOK`, `MINIMAL_DARK` und `NARRATIVE_FLOW`.
- **Cinematic Kinematics**: Smoothstep, Beat-Groove, Rubber-Band-Kameraeffekte und 2.5D-Perspektivwarping.
- **Native Acceleration**: C++20/AVX2-SIMD für Kandidatenscoring und Cosinus-Ähnlichkeit.
- **Lernschleife**: Bandit-basiertes Lernen erfolgreicher Director-Pacing-Kombinationen.

### Self-Learning Clip-Pool

```text
30.000+ Clips
    → Re-Embedding / Visual Genome
    → Motion-, Farbe-, Angle- und Emotions-Tags
    → Semantisches Matching
    → Anti-Repetition-Guard
    → Diversity-Sampling
    → Deterministischer Timeline-Plan
```

## Native Genome Compiler

### Optimierungspässe

| Pass | Name | Verantwortung |
|---|---|---|
| 1 | `BeatAlignmentPass` | Schnitte auf Downbeat- und Bar-Grenzen ausrichten |
| 2 | `CameraContinuityPass` | Sprünge und Kamerajitter vermeiden |
| 3 | `MotionFlowPass` | Clip-Bewegung mit BPM- und Energiekurve harmonisieren |
| 4 | `ColorHarmonyPass` | Farbverläufe konsistent halten |
| 5 | `FaceDiversityPass` | Gesicht- und Perspektivwiederholung begrenzen |
| 6 | `TransitionSimplificationPass` | Schnitte statt redundanter Blenden wählen |
| 7 | `SurprisePlacementPass` | VSFX und Scratches auf Drops platzieren |
| 8 | `RLRefinementPass` | Bandit-Rewards kontextuell optimieren |
| 9 | `RuntimeReductionPass` | Null-Frames und sehr kurze Trims entfernen |
| 10 | `RenderValidationPass` | Stream-Mapping und Zero-Tagging validieren |

### Visual Genome Daten

- `motion_score`
- `energy_level`
- `camera_angle`
- `dominant_colors`
- Top-Auto-Tags
- CLIP-Text-/Bild-Embeddings
- Nutzungshistorie und Anti-Repetition-Metriken

## SYNAPSE AUDIO DYNAMICS

SYNAPSE ist das autonome Musik-Operating-System hinter Produktion, Visualisierung, Vermarktung und Distribution.

### Apex-Departments

- **KAIRO** – Produktion, Psychoakustik und Hook-Strukturen
- **VEGA** – Mastering und Frequenzkontrolle
- **JINX** – Visuals, CLAW2 und Community-Content
- **ORION** – Distribution, Kuratoren und Sync-Lizenzierung
- **ATLAS** – Finanzen, Ad-Scaling und Revenue-Splits
- **PHOENIX** – System-Code, Lyrics und API-Architektur
- **KREON** – Web, Interface und Merch-Design
- **ARTIST** – Authentischer Songwriter und Performer

### Revenue Split

- 40 % Artist / Creator
- 20 % Label / Sound Architect
- 15 % Producer / Frequency QC
- 15 % Promo / Visuals
- 10 % Syndicate Growth Treasury

### Kernprinzipien

- Live Shared Knowledge Base statt isolierter Abteilungen.
- Mastering- und Publikumsdaten steuern Schneidepunkte und Kampagnen.
- 320-kbps-AAC, EBU-R128-Mastering und saubere NVENC-Exporte.
- 66,7-%-Catalog-Lockout verhindert Clip-Wiederholungen.
- Fehler werden diagnostiziert, codifiziert und als Systemwissen wiederverwendet.

## Schneller Start

### Umgebungsprüfung

```bat
setup_env.bat
```

Optional kann ein vollständiges Setup über die bereitgestellten Skripte ausgeführt werden:

```bash
bash setup.sh
# oder
python install_update_fix_all.py
```

### Clips reparieren und katalogisieren

```bash
python 00_repair_clips_db.py "D:\Oidasheim\weedit\data\clips.db"

python 01_tag_and_embed_clips.py \
  --db "D:\Oidasheim\weedit\data\clips.db" \
  --reembed
```

### Musikvideo rendern

```bash
python run_semantic_render.py \
  --mp3 "D:\Oidasheim\weedit\data\current_track.mp3" \
  --html "D:\Oidasheim\weedit\tmp.html" \
  --clips-db "D:\Oidasheim\weedit\data\clips.db" \
  --out "D:\Oidasheim\NFOs\done\Semantic_Render_v1.mp4" \
  --global-usage "D:\Oidasheim\weedit\data\global_clip_usage.json" \
  --seed 42
```

### WE.ED.IT CLI

```bash
weed doctor
weed benchmark
weed scan path/to/clips
weed compile song.mp3
weed render --mp3 song.mp3
weed report
```

### Direkte Weedit-Workflows

```bash
python weedit_director.py single "J:\MyMusic\track.mp3"
python weedit_director.py batch "J:\MyMusic" --rebuild-globe --limit 10
python main.py "J:\MyMusic\track.mp3" --platform vertical --tiktok-mode
python main.py "J:\MyMusic\track.mp3" --export-otio
```

## Virale Video-Strategie

Virale Musikclips folgen typischen Mustern:

1. **Starker Hook** in den ersten 1–3 Sekunden.
2. **Kurze, loopfähige Ausschnitte** von 15–30 Sekunden.
3. **Schnitte zum Beat und Drop** mit klarer visueller Hierarchie.
4. **Untertitel und Lyrics**, auch bei deaktiviertem Ton.
5. **UGC-freundliche Konzepte** wie Tanz-, Lipsync- oder Meme-Challenges.
6. **Crossposting** auf TikTok, Instagram Reels und YouTube Shorts.
7. **Micro-Influencer-Seeding** vor der offiziellen Kampagne.
8. **Retention-Tracking** und schnelle Iteration in den ersten Upload-Stunden.

### Plattform-Fokus

- **TikTok:** Höchstes UGC- und Viralitätspotenzial.
- **Instagram Reels:** Starke Musikentdeckung, markenorientiertes Crossposting.
- **YouTube:** Größte Reichweite, MV, Shorts und kollaborative Empfehlungen.
- **X:** Primär Industrie-, Community- und Diskussionskanal.

Wichtige KPIs sind Wiedergabezeit, Completion Rate, Shares, Virality-Rate, Creation Count und Streaming-/Chart-Conversion.

## Hardware-Profil

- Intel Core i5-9400F
- 6 physische Kerne / 6 Threads
- NVIDIA GeForce GTX 1650, Turing NVENC
- Supervisor/API: Kerne 0–1
- Rendering/DSP: Kerne 2–5

### FFmpeg

```text
-hwaccel cuda -c:v h264_nvenc -preset p4 -profile:v high -rc vbr -cq 19 -bf:v 3
```

CPU-Fallback:

```text
-c:v libx264 -preset ultrafast -crf 22 -c:a aac -b:a 192k
```

## Rendering-Invarianten

- `-map 0:v -map 1:a`
- Keine Metadaten oder Kapitel: `-map_metadata -1 -map_chapters -1 -sn -dn`
- Audio: konstant 320 kbps AAC
- Hardware-Rendering bevorzugt, deterministischer CPU-Fallback
- 1080p / 4K adaptive Worker-Verteilung
- Keine Clip-Wiederholungen oberhalb des 66,7-%-Catalog-Limits
- Export als MP4 und optional OpenTimelineIO

## Tests

```bash
pytest tests/ -v
pytest tests/ -q
```

## Verknüpfte Projekte

- [la.bat.ne.da](https://github.com/oidasheim/la.bat.ne.da.git)
- [beatsync](https://github.com/oidasheim/beatsync.git)

## Lizenz

MIT License. Developed by the Oidasheim / OIDA Engine Team.
