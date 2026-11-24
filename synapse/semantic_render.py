"""Beat-aligned semantic clip selection and FFmpeg rendering."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess

from .semantic_index import DuckDBSemanticIndex, encode_text, load_openclip


class _VisibleText(HTMLParser):
    """Extract visible text without scripts/styles from an optional HTML lyric export."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def load_lyrics(path: Path | None) -> str:
    """Read a plain-text or HTML lyric source; no network access is performed."""
    if path is None:
        return ""
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".html", ".htm"}:
        parser = _VisibleText()
        parser.feed(text)
        text = " ".join(parser.parts)
    return " ".join(text.split())


def _lyric_for_segment(lyrics: str, index: int, count: int) -> str:
    if not lyrics.strip():
        return ""
    # Divide on line/section boundaries first, then sentence boundaries. This
    # provides local text context without claiming forced word-level alignment.
    chunks = [part.strip() for part in lyrics.replace("\r", "").split("\n") if part.strip()]
    if len(chunks) <= 1:
        chunks = [part.strip() for part in lyrics.replace("!", ".").replace("?", ".").split(".") if part.strip()]
    if not chunks:
        return ""
    start = min(len(chunks) - 1, index * len(chunks) // max(1, count))
    return chunks[start][:240]


def prompt_for_energy(energy: float, threshold: float, lyrics: str = "") -> str:
    if energy >= threshold:
        base = "cinematic urban night scene, vivid neon color, energetic movement, dramatic lighting"
    else:
        base = "cinematic quiet urban scene, atmospheric shadows, restrained movement, soft contrast"
    context = " ".join(lyrics.split())[:240]
    return f"{base}; lyric context: {context}" if context else base


def audio_beats_and_energy(song: Path) -> tuple[float, list[tuple[float, float]]]:
    try:
        import librosa
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Install semantic extras: pip install '.[semantic]'") from exc
    signal, sr = librosa.load(str(song), sr=22050, mono=True)
    duration = float(librosa.get_duration(y=signal, sr=sr))
    tempo, beat_frames = librosa.beat.beat_track(y=signal, sr=sr, units="frames")
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    if not beat_times or beat_times[0] > 0.05:
        beat_times.insert(0, 0.0)
    beat_times = sorted(set(float(t) for t in beat_times if 0 <= t < duration))
    rms = librosa.feature.rms(y=signal)[0]
    rms_times = librosa.frames_to_time(range(len(rms)), sr=sr)
    values = [float(rms[np.argmin(np.abs(rms_times - t))]) for t in beat_times]
    if values:
        scale = max(values) or 1.0
        values = [v / scale for v in values]
    return duration, list(zip(beat_times, values))


def _usage_counts(path: Path | None) -> dict[str, int]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("usage", data) if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        raise ValueError("global usage JSON must be an object or contain an object 'usage'")
    counts: dict[str, int] = {}
    for key, value in raw.items():
        count = int(value)
        if count < 0:
            raise ValueError("global usage counts must be non-negative")
        counts[str(Path(key).resolve())] = count
    return counts


def _save_usage(path: Path, counts: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps({"version": 1, "usage": counts}, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    os.replace(temp, path)


def _choose_diverse(matches, usage: dict[str, int], chooser: random.Random,
                    recent: set[str], temperature: float = 0.08):
    candidates = [m for m in matches if str(Path(m.path).resolve()) not in recent]
    if not candidates:
        candidates = list(matches)
    if not candidates:
        raise ValueError("No semantic candidates")
    # Penalize cross-project frequency while retaining similarity as the main
    # signal. The transformed score is for ranking/sampling, not a probability.
    scored = [(m, float(m.score) - 0.025 * math.log1p(usage.get(str(Path(m.path).resolve()), 0)))
              for m in candidates]
    best = max(score for _, score in scored)
    weights = [math.exp(max(-50.0, (score - best) / temperature)) for _, score in scored]
    return chooser.choices([item[0] for item in scored], weights=weights, k=1)[0]


def build_plan(song: Path, index: DuckDBSemanticIndex, model_bundle,
               candidate_count: int = 8, seed: int = 42, *, lyrics: str = "",
               usage: dict[str, int] | None = None) -> list[dict]:
    if candidate_count < 1:
        raise ValueError("candidate_count must be positive")
    duration, beat_energy = audio_beats_and_energy(song)
    if len(beat_energy) < 2:
        raise ValueError("Audio analysis did not find enough beat boundaries")
    threshold = sorted(value for _, value in beat_energy)[len(beat_energy) // 2]
    chooser = random.Random(seed)
    global_counts = usage or {}
    used: list[str] = []
    plan: list[dict] = []

    for i, (start, energy) in enumerate(beat_energy):
        end = beat_energy[i + 1][0] if i + 1 < len(beat_energy) else duration
        segment_duration = end - start
        if segment_duration <= 0:
            continue
        lyric_context = _lyric_for_segment(lyrics, i, len(beat_energy))
        prompt = prompt_for_energy(energy, threshold, lyric_context)
        query = encode_text(prompt, model_bundle)
        # Request a wider candidate set so novelty/diversity can rerank beyond
        # the same global top few, and exclude recent choices where possible.
        matches = index.search(query, limit=max(candidate_count * 4, candidate_count),
                               excluded_paths=used[-3:])
        if not matches:
            matches = index.search(query, limit=max(candidate_count * 4, candidate_count))
        if not matches:
            raise RuntimeError("Semantic index has no matching clips")
        selected = _choose_diverse(matches[:candidate_count * 4], global_counts,
                                   chooser, set(used[-3:]))
        selected_path = str(Path(selected.path).resolve())
        plan.append({"start_time": start, "duration": segment_duration,
                     "clip_path": selected_path, "similarity": selected.score,
                     "prompt": prompt, "energy": energy,
                     "global_usage_count": global_counts.get(selected_path, 0)})
        used.append(selected_path)
    return plan


def render_plan(song: Path, plan: list[dict], output: Path, width: int = 1080,
                height: int = 1920, fps: int = 30) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg must be installed and available on PATH")
    if not plan:
        raise ValueError("Cannot render an empty plan")
    if width <= 0 or height <= 0 or fps <= 0:
        raise ValueError("width, height, and fps must be positive")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output}")
    unique_paths = list(dict.fromkeys(str(Path(row["clip_path"]).resolve()) for row in plan))
    command = [ffmpeg, "-hide_banner", "-y", "-i", str(song)]
    for path in unique_paths:
        command.extend(["-i", path])

    filters: list[str] = []
    labels: list[str] = []
    for i, row in enumerate(plan):
        source_index = unique_paths.index(str(Path(row["clip_path"]).resolve())) + 1
        length = max(float(row["duration"]), 1.0 / fps)
        label = f"v{i}"
        filters.append(
            f"[{source_index}:v]trim=start=0:duration={length:.6f},setpts=PTS-STARTPTS,"
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},format=yuv420p[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[outv]")

    encoders = subprocess.run([ffmpeg, "-hide_banner", "-encoders"],
                              capture_output=True, text=True, check=False).stdout
    video_codec = "h264_nvenc" if "h264_nvenc" in encoders else "libx264"
    command.extend(["-filter_complex", ";".join(filters),
                    "-map", "[outv]", "-map", "0:a:0", "-shortest",
                    "-map_metadata", "-1", "-map_chapters", "-1", "-sn", "-dn",
                    "-c:v", video_codec])
    if video_codec == "h264_nvenc":
        command.extend(["-preset", "p4", "-cq", "19"])
    else:
        command.extend(["-preset", "medium", "-crf", "20"])
    command.extend(["-c:a", "aac", "-b:a", "320k", "-r", str(fps), str(output)])
    subprocess.run(command, check=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", type=Path)
    parser.add_argument("--db", type=Path, default=Path("database/clips_semantic.duckdb"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--aspect", choices=["16:9", "9:16", "1:1"], default="9:16")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cpu", "cuda"], default=None)
    parser.add_argument("--lyrics", type=Path, help="optional local TXT/HTML lyrics for text-image semantic context")
    parser.add_argument("--global-usage", type=Path, help="shared JSON usage ledger across renders")
    parser.add_argument("--candidate-count", type=int, default=8)
    parser.add_argument("--plan-only", "--dry-run", dest="plan_only", action="store_true")
    args = parser.parse_args()
    if not args.song.is_file():
        parser.error(f"Song not found: {args.song}")
    if args.lyrics and not args.lyrics.is_file():
        parser.error(f"Lyrics file not found: {args.lyrics}")
    if args.candidate_count < 1:
        parser.error("--candidate-count must be positive")

    lyrics = load_lyrics(args.lyrics)
    usage = _usage_counts(args.global_usage)
    model_bundle = load_openclip(args.device)
    index = DuckDBSemanticIndex(args.db)
    try:
        plan = build_plan(args.song, index, model_bundle,
                          candidate_count=args.candidate_count, seed=args.seed,
                          lyrics=lyrics, usage=usage)
        output = args.output or Path("output") / f"{args.song.stem}_semantic.mp4"
        if args.plan_only:
            output.parent.mkdir(parents=True, exist_ok=True)
            output = output.with_suffix(".json")
            output.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Wrote semantic edit plan: {output}")
        else:
            width, height = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}[args.aspect]
            render_plan(args.song, plan, output, width, height)
            # Update shared usage only after a successful render. Dry-runs and
            # failed renders do not poison the cross-project diversity ledger.
            if args.global_usage:
                for row in plan:
                    clip = str(Path(row["clip_path"]).resolve())
                    usage[clip] = usage.get(clip, 0) + 1
                _save_usage(args.global_usage, usage)
            print(f"Rendered: {output}")
    finally:
        index.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
