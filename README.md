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
- **MixMeister-Fallback**: BPM-Erkennung bei schwer analysierbaren Tracks.
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
Clip-Pool → Re-Embedding / Visual Genome
          → Motion-, Farb-, Angle- und Emotions-Tags
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

- `motion_score`, `energy_level`, `camera_angle` und `dominant_colors`
- Top-Auto-Tags und CLIP-Text-/Bild-Embeddings
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

- **TikTok:** UGC- und Viralitätspotenzial.
- **Instagram Reels:** Musikentdeckung und markenorientiertes Crossposting.
- **YouTube:** Musikvideos, Shorts und Empfehlungen.
- **X:** Industrie-, Community- und Diskussionskanal.

Wichtige KPIs sind Wiedergabezeit, Completion Rate, Shares, Virality-Rate, Creation Count und Streaming-/Chart-Conversion.

## Portable Unified Edition v8.0

Die portable Edition bündelt fünf Stacks in einem lokalen Workspace. Runtimes, Datenbanken, Berichte, Caches und Render-Outputs bleiben im Projektverzeichnis isoliert.

| Stack | Bereiche | Kernfunktionen |
|---|---|---|
| **SYNAPSE Audio Dynamics** | `core/`, `weedit/`, `claw2/`, `viral/`, `content/`, `portals/`, `agents/` | Native Genome Compiler, Hardware-Isolation, 2/3 SQLite Lock, Rhythm Semantic Engine, Semantic Tree und Agent Swarm |
| **SYNAPSE Full-Stack v4.0** | `core/synapse_apex_kernel.py` | 10 Departments, deklarative DAG-Workflows, hash-verkettetes Event Ledger, DLQ, CAS-Leases, Gates, Circuit Breaker, LinUCB und Dashboard |
| **MMIS + PROMO.ED** | `mmis/`, `promo_ed/`, `cpp/`, `sql/` | Causal DiD, Attribution, Forecasting, DuckDB-Analysen und 10-Agenten-Projekt-Lifecycle |
| **WE.ED.IT 420-Mode** | `weedit_420mode/` | UCB1 Director, STFT-DSP, Entropie-Fusion, Catalog Lock, Outro-Schutz und Oracle-Autopsie |
| **Semantic Beat-Synced** | `semantic_beatsync/` | Beat-Grid, Energie- und Section-Erkennung, A/V-Planung, Multi-Aspect-Clip-Pools und Playlist-Orchestrierung |

### Portables Layout

```text
./
├── assets/                 # Banner und Beispieldateien
├── bin/                    # Optionale gebündelte Tools und native Binaries
├── config/                 # Clip-Pools, Music-Dirs und Blacklists
├── core/                   # Apex Kernel, Semantic Engine und API
├── cpp/                    # C++20 / AVX2 Build-Sourcen
├── database/               # Lokale Datenbanken
├── docs/                   # Architektur, Catalyst Protocol, Oracle-Autopsie
├── mmis/                   # Analytics und Forecasting
├── promo_ed/               # Promo-Lifecycle
├── semantic_beatsync/      # Beat-Sync-Pipeline
├── tests/                  # Pytest-Suiten
├── web/                    # Cockpit UI
├── weedit/                 # Genome Compiler
├── weedit_420mode/         # 420-Mode
├── PORTABLE_INSTALL.bat    # Portables Setup und Verifikation
├── PORTABLE_START.bat      # Launcher für CLI, Cockpit und Tests
├── portable_env.bat        # Isolierte Umgebungsvariablen
└── weed.bat / weed.py      # Vereinheitlichte CLI
```

Große GGUF-Modelle werden separat in `./models/` oder über `WEEDIT_MODELS_FALLBACK_DIR` eingebunden und nicht in ein Source-Release-ZIP dupliziert.

### Portable Quickstart und CLI

```bat
PORTABLE_INSTALL.bat
PORTABLE_START.bat
```

Unbeaufsichtigte Installation:

```bat
cmd /c "set SYNAPSE_NO_PAUSE=1 && PORTABLE_INSTALL.bat"
```

Beispiele der vereinheitlichten v8-CLI:

```powershell
.\weed.bat doctor
.\weed.bat toolchain
.\weed.bat verify
.\weed.bat compile --song "I:\Oidasheim\Sound\Track.mp3" --style drill --export-genome-bundle
.\weed.bat apex run
.\weed.bat apex evolution --tier 1
.\weed.bat apex verify
.\weed.bat mmis demo
.\weed.bat mmis research
.\weed.bat promo --project "Beton_&_Bass" --artist "OIDAHEIM" --genre "Bavarian Drill"
.\weed.bat 420mode --analyze "assets\suno_downloads\track.mp3"
.\weed.bat rhythm --song "assets\suno_downloads\track.mp3" --style drill --out "reports\rhythm_plan.json"
.\weed.bat semantic-beatsync status
.\weed.bat semantic-beatsync pools --aspect 16:9
.\weed.bat serve --port 8089
```

### REST API

Die v8-API stellt unter anderem `/health`, `/api/v1/banner`, `/api/v1/apex/run`, `/api/v1/apex/verify`, `/api/v1/mmis/research`, `/api/v1/promo/run`, `/api/v1/rhythm/plan` und `/api/v1/semantic-beatsync/pools` bereit. Ältere Mesh-, Tree-, Provider- und Viral-Prediction-Endpunkte können parallel verfügbar sein.

## Catalyst Protocol v4.0

**„From the Gutter to the Top 1“** beschreibt einen vierphasigen Release- und Entwicklungsprozess, der Authentizität bewahren und Musik, Visuals, Distribution und Feedback miteinander verbinden soll.

### Phase 1 — Raw Ore

- **KAIRO** analysiert Frequenzfundamente, Vocals, Timbre und Transienten.
- **JINX** entwickelt eine ungeschönte, lokal verankerte visuelle Erzählung.

### Phase 2 — The Chrysalis

- **KAIRO & VEGA** gestalten Vocal Chains und Mastering; als Ziel wird EBU R128 um −14 LUFS mit geschützter Dynamik genannt.
- **JINX & CLAW2** verbinden Visual Vector Matching, Beat-Sync und die Kinetic Perspective Engine.
- Der Clip-Katalog-Lock soll repetitive Nutzung begrenzen.

### Phase 3 — Hyper-Local to Global Seeding

- **ORION** priorisiert passende Nischen-Playlists, Communities und Kuratoren.
- **JINX / Ghost_Writer** bereitet plattformgerechte Kurzformate und Teaser für TikTok, Instagram Reels und YouTube Shorts vor.

### Phase 4 — Financial Scaling

Die vorgeschlagenen Schwellenwerte dienen als konfigurierbare Workflow-Parameter, nicht als Garantie für Reichweite oder Conversion:

- Engagement Rate ≥ 15 %
- Completion Rate ≥ 70 %
- Composite Viral Score ≥ 75/100
- Vorgeschlagene Verteilung des Testbudgets: 50 % TikTok, 30 % Reels, 20 % YouTube Shorts
- Vorgeschlagener Royalty Split: 40 % Artist, 20 % Label/KAIRO, 15 % Producer/VEGA, 15 % Promo/JINX, 10 % Treasury/ATLAS

Ad-Ausgaben und Royalty-Zahlungen sollten vor Ausführung menschlich freigegeben und durch Budgetlimits, Berechtigungsprüfungen und nachvollziehbare Abrechnungen abgesichert werden.

### 7-Tage Release-Aktionsplan

| Tag | Verantwortliche | Aktion |
|---|---|---|
| 1 | KAIRO | Audio-Import, Transienten-Analyse und Stem-Vorbereitung |
| 2 | VEGA | Mastering, Loudness- und True-Peak-QC |
| 3 | JINX | Beat-Sync-Video und Clip-Diversity-Prüfung |
| 4 | Self-Critic / LinUCB | Schnittdichte prüfen, Hektik-Check und Reward-Update |
| 5 | ORION / Ghost_Writer | Teaser und Playlist-Pitch vorbereiten |
| 6 | ATLAS | Release-Monitoring und Budgetstatus prüfen |
| 7 | ATLAS / Team | Feedback auswerten, Ergebnisse dokumentieren und Scaling-Entscheidungen freigeben |

## Rekursive Oracle-Autopsie

Der Feedback-Loop soll Prognosen und Release-Metriken stufenweise prüfen:

1. **L1 — Klassifikationskorrektur:** BPM-, Tonart-, Genre- und Zielgruppen-Tags überprüfen.
2. **L2 — Ledger-Abgleich:** Ergebnisse mit dem historischen Release-Ledger vergleichen; vorgeschlagene Mindestwerte sind Precision > 80 % und Recall > 70 %.
3. **L3 — Entropie- und Konsensprüfung:** Unsichere Vorhersagen neu bewerten und Agenten-Konsens nachvollziehbar protokollieren.

Als operative Leitplanken sind höchstens drei Iterationen, eine relative Delta-Schranke unter 2 % und ein transaktionaler Rollback-Ledger vorgesehen. Prognosen und Schwellenwerte müssen mit realen Daten validiert werden.

## Hardware-Profil

- Intel Core i5-9400F, 6 physische Kerne / 6 Threads
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

- Getrenntes Stream-Mapping: `-map 0:v -map 1:a`
- Keine Metadaten oder Kapitel: `-map_metadata -1 -map_chapters -1 -sn -dn`
- Audio: 320-kbps-AAC als Projektvorgabe
- Hardware-Rendering bevorzugt, CPU-Fallback verfügbar
- Adaptive Worker-Verteilung für 1080p und 4K
- Anti-Repetition über Catalog-Lock und Nutzungshistorie
- Export als MP4 und optional OpenTimelineIO

## Tests und Release-Paket

```bash
pytest tests/ -v
```

Portables Source-Release-ZIP kann über das Projekt-Skript erzeugt werden:

```powershell
.\venv\Scripts\python.exe scripts\build_release_zip.py
```

Die vollständige Hardware- und Regelwerks-Spezifikation ist in `docs/ARCHITECTURE.md` vorgesehen; ergänzende Protokolle können in `docs/CATALYST_PROTOCOL.md` und `docs/ORACLE_AUTOPSIE.md` liegen.

## Verknüpfte Projekte

- [la.bat.ne.da](https://github.com/oidasheim/la.bat.ne.da.git)
- [beatsync](https://github.com/oidasheim/beatsync.git)

## Lizenz

MIT License. Developed by the Oidasheim / OIDA Engine Team.
