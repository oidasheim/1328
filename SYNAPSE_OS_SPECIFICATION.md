# Synapse OS: Core Technical Specification

**Version**: v3.1 / Core Manual 01: CLAW2 & WE.ED.IT  
**Status**: Foundational Contract  
**Last Updated**: 2026-09-12

---

## I. System Architecture & Ingestion Pipeline

### Autonomous File System Intercepts

The Synapse ingestion engine monitors three distinct hardware pathways:

| Drive | Path | Asset Classification | Protocol |
|-------|------|----------------------|----------|
| **I:** | `I:\Oidasheim\Sound\` | Master Audio Tracks & Stem Pools | Local SATA / HDD |
| **D:** | `D:\Oidasheim\NFOs\Clips\` | Metadata Sheets & Raw Video Clips | Local NVMe M.2 SSD |
| **H:** | Network Repository | High-Fidelity Archive & Master Exports | Network-Attached Storage (NAS) |

**Asset Monitoring Module**: Directory-watching routines detect new files and route them based on file extension classification.

---

## II. Multi-Threaded Chunking Ingestion

### Thread Pool Architecture

**Problem**: Standard `ThreadPoolExecutor` exposes system to memory exhaustion at scale.

**Solution**: Two-tier workaround:

1. **Bounded Task Queues** via `ThreadPoolExecutorWithQueueSizeLimit`
   - Override internal work queue with `queue.Queue(maxsize=maxsize)`
   - Block main thread submissions when queue is saturated

2. **Active Futures Throttling**
   - Monitor active futures using `concurrent.futures.wait(RETURN_WHEN=FIRST_COMPLETED)`
   - Submit new task only when worker thread frees up

**Configuration**:
```python
CONFIG.CHUNK_SIZE = 1000  # Asset parsing batch boundary
CONFIG.MAX_QUEUE_SIZE = 5000  # Bounded queue limit
CONFIG.WORKER_THREADS = 6  # CPU-affinity isolated threads
```

---

## III. Hardware Profile Targeting

### Baseline Node Specification

- **CPU**: Intel i5-9400F (6 physical cores, 6 threads, no hyper-threading)
- **GPU**: NVIDIA GeForce GTX 1650 (Turing architecture, NVENC hardware encoder)
- **Storage**: NVMe M.2 SSD for metadata, SATA HDD for asset pool

### CPU Affinity Isolation

Cores 0-1 reserved for background operations; cores 2-5 for rendering.

```python
import psutil
import os

process = psutil.Process(os.getpid())
process.set_cpu_affinity([2, 3, 4, 5])  # Render threads only
```

### FFmpeg Hardware Acceleration

| Parameter | Value | Benefit |
|-----------|-------|---------|
| `-hwaccel` | `cuda` | Hardware-accelerated decoding |
| `-c:v` | `h264_nvenc` | Turing NVENC encoding |
| `-preset` | `p4` / `medium` | Speed/quality baseline |
| `-profile:v` | `high` | Advanced syntax features |
| `-rc` | `vbr` | Variable bitrate optimization |
| `-cq` | `19` | Constant quantization target |
| `-bf:v` | `3` | Bidirectional predictive frames |

---

## IV. Core Team Nodes & Technical Handshakes

### Specialized Entities

| Node | Role | Responsibility |
|------|------|-----------------|
| **Kairo** | Neuro-Audio Architecture | Executive Producer; frequency-level track structuring |
| **Vega** | Frequency Surgeon | Mastering & QC; analog/digital treatments (EBU R128) |
| **Phoenix** | Synthesizer / Coder | C++/Python/Rust automation; metadata & documentation |
| **Jinx** | Creative Director & VFX | Visual editing + beat-sync filters; viral asset synthesis |

### Competence-Weighted Consensus Engine

Dynamic vote weighting by domain specialization:
- **Visual Branding**: Jinx 60%, Kreon 20%, Atlas 10%, Kairo 10%
- **Budget Scaling**: Atlas 70%, Vega 20%, Phoenix 10%

---

## V. Offline-First & Local-First Mesh Network (v3.0)

**Operational Sovereignty**: Render nodes synchronize via local SQLite over multi-gigabit LAN.

**Mobile Deployments**: P2P mesh network using encrypted LAN or LoRa frequencies.

**Database Synchronization**: Solid-state NVMe server arrays with deterministic conflict resolution.

---

## VI. The Unbreakable Render Engine (v16.3 Matrix)

### Mathematical Beat-Sync Slicing

Tempo (BPM) → exact video frame boundaries (eliminates drift in manual workflows).

**Fundamental Equations**:

```
Seconds per Beat = 60 / BPM
Seconds per Bar = (60 / BPM) × Beats per Bar
Frames per Beat = (FPS × 60) / BPM
Frames per Bar = (FPS × 60 × Beats per Bar) / BPM
```

**Example at 30 FPS**:

| BPM | Seconds per Beat | Frames per Beat | Frames per Bar (4/4) |
|-----|------------------|-----------------|----------------------|
| 100 | 0.600 s | 18.00 | 72.00 |
| 120 | 0.500 s | 15.00 | 60.00 |
| 150 | 0.400 s | 12.00 | 48.00 |

**FFmpeg Concat-Demuxer**: Generates exact cut intervals via frame-precise concatenation (no full-file decode).

### Kinetic Perspective Engine

**Problem**: FFmpeg `zoompan` filter crashes under high-load (exit code 3199971767) and exhibits sub-pixel jitter.

**Root Causes**:
- Heap buffer overflows (CVE-2026-30999 in `av_bprint_finalize()`)
- Integer arithmetic underflows (CVE-2025-63757 in `libswscale`)
- Bitstream corruption in H.264 decoder

**Solution**: Two-step Scale + Crop workaround:

1. **Deterministic Upscaling** (1.15x multiplier)
   - Source: 1920×1080 → 2208×1242 (Lanczos3)
   - Spreads rounding errors across larger pixel grid

2. **Sinus-Driven Coordinate Panning**
   - Replace `zoompan` with `crop` filter + sinusoidal expressions
   - Safe within standard memory allocation routines

```
crop=1920:1080:(iw-ow)/2+50*sin(2*PI*t/d):(ih-oh)/2+50*cos(2*PI*t/d)
```

### Zero-Fidelity Degradation Mandate

**Rule**: Block low-quality color manipulation filters and high-compression codecs.

**Enforcement**:
- Bypass artificial LUTs, vintage color matrices, high-contrast styling
- Direct stream-mapping to output container (no transcoding)

```bash
ffmpeg -f concat -safe 0 -i cut_sheet.txt \
  -map 0:v -map 1:a \
  -c:v h264_nvenc -crf 18 \
  -c:a aac -b:a 320k \
  output.mp4
```

---

## VII. Database Schema & Cooldown Enforcement

### SQLite Row-Factory Architecture

**Problem**: Standard tuple-based rows force hardcoded index lookups (high brittleness).

**Solution**: Use `sqlite3.Row` for all connections (dict-like interface, low overhead).

```python
import sqlite3

def get_database_connection(db_path):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection
```

**Safe Column Access**:
```python
row = cursor.fetchone()
path = row["filepath"]  # Named access, no index mismatch
timestamp = row["last_used_timestamp"]
```

### Twelve-Hour Blacklist Guard

**Rule**: No raw asset can appear in consecutive renders within 12 hours (visual diversity mandate).

**Enforcement**:
```sql
SELECT id, filepath, duration 
FROM clip_registry 
WHERE status = 'active' 
  AND (last_used_timestamp IS NULL OR last_used_timestamp < strftime('%s', 'now') - 43200)
ORDER BY RANDOM() 
LIMIT 1;
```

**Update After Render**:
```sql
UPDATE clip_registry 
SET last_used_timestamp = strftime('%s', 'now') 
WHERE id = :target_id;
```

### Schema Hot-Migrations

**4-Stage Migration Flow**:

1. **Inspection**: `PRAGMA table_info(clip_registry)`
2. **Verification**: Python schema matcher
3. **Alteration**: `ALTER TABLE ... ADD COLUMN`
4. **Validation**: `PRAGMA user_version`

**12-Step Transition for Complex Migrations**:

```
PRAGMA foreign_keys=OFF 
  → BEGIN TRANSACTION 
  → CREATE TABLE new_table 
  → INSERT INTO new_table SELECT 
  → DROP TABLE old_table 
  → ALTER TABLE new_table RENAME TO old_table 
  → PRAGMA user_version 
  → COMMIT 
  → PRAGMA foreign_keys=ON
```

---

## VIII. Metadata & Label Operations

### FAVs07072026.html Protocol

**Workflow**:
```
[FAVs07072026.html] 
  → [Metadata Extraction Module] 
  → [./date/FAVS.html] 
  → [SQLite Database]
```

- Parse DOM structure via regex + HTML parser
- Extract curated tracks, ratings, custom metadata
- Copy source to target path with archive backup
- Push extracted dataset into central database schema

### Semantic Tagging & Classification

**Filename Pattern Routing**:

| Regex | Genre | Aesthetic Pool | Visual Focus |
|-------|-------|-----------------|--------------|
| `(drift\|phonk)` | Drift / Phonk | Cyberpunk Urban | High-Speed Tracking |
| `(drill\|grime)` | Drill / Grime | Industrial Gritty | Low-Angle Panning |
| `(rap\|hiphop)` | Rap / Hip-Hop | Classic Urban | Raw Performance, Center Zoom |
| `(boombap\|jazzhop)` | Boom Bap / Jazz Hop | Nostalgic / Retro | Soft Oscillating Movement |

**Ingestion Pipeline**:
1. Strip special characters, normalize to lowercase
2. Match against genre pattern dictionary
3. Tag asset with `Aesthetic` label in database
4. Isolate clips for downstream render loops

### Relational Database: weed_it_dog_pipe-v3.1-Clip.db Standard

```sql
CREATE TABLE IF NOT EXISTS clip_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    duration_seconds REAL NOT NULL,
    aesthetic_tag TEXT NOT NULL,
    resolution_width INTEGER NOT NULL,
    resolution_height INTEGER NOT NULL,
    last_used_timestamp INTEGER DEFAULT 0,
    rating INTEGER DEFAULT 5
);
```

---

## IX. Fault Tolerance & Resource Isolation

### Isolated Render Job Execution

**Subprocess Isolation Pattern**:

```python
import subprocess
import sys

def execute_isolated_render_job(arguments_list):
    # Spawn in separate process; memory freed on exit
    render_process = subprocess.Popen(
        [sys.executable, "render_worker.py"] + arguments_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = render_process.communicate()
    return render_process.returncode
```

**Benefits**:
- All allocated memory released by OS upon completion
- GPU handles & file descriptors freed
- Prevents memory creep across long batch jobs

### Fault-Tolerant Render Safehouse Loops

**Two-Tier Fallback**:
1. **Primary**: Hardware-accelerated encoding (h264_nvenc)
2. **Fallback**: Software-based encoding (libx264 ultrafast)

```bash
# Fallback command on codec/file corruption error
ffmpeg -f concat -safe 0 -i cut_sheet.txt \
  -c:v libx264 -preset ultrafast -crf 22 \
  -c:a aac -b:a 192k \
  output_safe.mp4
```

**Behavior**: Catches corrupted frames, bypasses GPU memory registers, flags problematic files for manual review without halting batch queue.

---

## X. Automated Release Infrastructure

### Version Control & Output Tracking

**Naming Convention**:
```
WE_ED_IT_OIDA_[ProjectName]_[Version].mp4
```

**Example**:
```
WE_ED_IT_OIDA_Goettermodus_v1.mp4
```

**Sanitization Pipeline**:
```python
import re

def sanitize_release_filename(raw_filename):
    # Remove emojis, special characters, double spaces
    clean_name = re.sub(r"[^\w\-\.]", "", raw_filename.replace(" ", "_"))
    return clean_name
```

### Deployment Automation & Cloud Escalation

**Scaling Strategy**:
1. **Local Nodes**: Intel i5-9400F + GTX 1650
2. **Cloud GPU Instances**: High-performance NVIDIA Tesla / A100
3. **Containerized Environments**: Docker packaging (engine + deps + DB + FFmpeg)
4. **Automated Queue Routing**: Secure network sync; parallel cloud processing

---

## XI. The Synapse Distribution Matrix (5 Nodes)

| Node | Operation | Target Audience | Revenue Trigger |
|------|-----------|-----------------|-----------------|
| **Node 1** | Algorithmic DSP Grid | Global streaming DSPs | Streaming royalties & playlist placement |
| **Node 2** | Creator Syndicate | 10k+ micro-creators | UGC virality & smart-contract micro-splits |
| **Node 3** | Sync & Brand API | B2B (Netflix, Ubisoft, ads) | Premium upfront sync fees |
| **Node 4** | Direct-to-Fan Vault | Super-fan core community | Physical merch, vinyl, sample packs |
| **Node 5** | White-Label SaaS | External labels & agencies | High-yield Monthly Recurring Revenue (MRR) |

---

## XII. Operational Constraints & Hard Limits

### Resource Governor Mandates

```python
execution = {
    "max_video_parallelism": 1,      # ONE render at a time
    "max_decoders": 1,               # Single FFmpeg decoder instance
    "max_encoders": 1,               # Single NVENC encoder instance
    "max_heavy_workers": 1,          # One heavy computation thread
}

memory_pressure = {
    "GREEN": "normal operation",
    "YELLOW": "reduce cache",
    "ORANGE": "degrade analysis",
    "RED": "pause workers / recover",
}
```

### Deterministic Seeding

All non-cryptographic randomization uses deterministic seeds:
```python
CONFIG.SONG_TOUCH_SEED_SALT = "synapse_v3.1"
```

Ensures reproducible clip selection, camera angles, and styling across identical input conditions.

---

## XIII. Known Constraints & Future Extensions

### Stable Core (Current Scope)

✓ SQLite state management  
✓ Event-based state mutations  
✓ Bounded task queues & resource governor  
✓ Sequential media worker  
✓ Fault-tolerant rendering  
✓ 12-hour clip cooldown enforcement  
✓ Hot-migration database schema  

### Future Layers (Behind Stable Contracts)

- Deep reinforcement learning for clip scoring
- Self-modifying code & unversioned genome mutation
- Direct LLM → Renderer commands
- Untrusted plugin execution
- Automatic architecture changes
- Large multi-agent swarm orchestration

---

## XIV. References & Implementation Files

**Core Implementation Modules**:
- `kernel.py` — State, Events, Provenance
- `state.py` — SQLite state management + row factory
- `events.py` — Event store + mutation reducer
- `resource_governor.py` — CPU/GPU/Memory constraints
- `task_queue.py` — Bounded `ThreadPoolExecutor` subclass
- `sequential_worker.py` — Media rendering pipeline
- `hot_migration.py` — Schema evolution + data safety
- `clip_cooldown.py` — 12-hour blacklist enforcement
- `post_agent.py` — Browser emulation + social distribution

---

**End of Synapse OS Specification v3.1**
