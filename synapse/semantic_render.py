"""Beat-aligned semantic clip selection and FFmpeg rendering."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import shutil
import subprocess

from .director_ai import (DirectorProfile, compose_visual_prompt, confidence_margin,
                          pacing_window, select_diverse)
from .semantic_index import DuckDBSemanticIndex, encode_text, load_openclip


def prompt_for_energy(energy: float, threshold: float, lyrics: str = "", bpm: float = 120.0,
                      profile: DirectorProfile | None = None) -> str:
    """Backward-compatible prompt helper, now with local lyric/BPM context."""
    normalized_energy = 0.75 if energy >= threshold else 0.25
    prompt, _ = compose_visual_prompt(normalized_energy, lyrics, bpm, profile)
    return prompt


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


def read_lyrics(path: Path | None) -> list[str]:
    if path is None:
        return []
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".html", ".htm"}:
        from html.parser import HTMLParser
        class TextParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts = []
                self.hidden = 0
            def handle_starttag(self, tag, attrs):
                if tag in {"script", "style", "noscript"}: self.hidden += 1
            def handle_endtag(self, tag):
                if tag in {"script", "style", "noscript"} and self.hidden: self.hidden -= 1
            def handle_data(self, data):
                if not self.hidden and data.strip(): self.parts.append(data.strip())
        parser = TextParser()
        parser.feed(text)
        text = "\n".join(parser.parts)
    return [line.strip() for line in text.splitlines() if line.strip()]


def _segment_lyric(lines: list[str], index: int, count: int) -> str:
    if not lines:
        return ""
    return lines[min(len(lines) - 1, index * len(lines) // max(count, 1))][:180]


def read_usage(path: Path | None) -> dict[str, int]:
    if path is None or not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    usage = value.get("usage", value) if isinstance(value, dict) else None
    if not isinstance(usage, dict):
        raise ValueError("usage file must contain an object or an object under 'usage'")
    counts = {str(Path(key).resolve()): int(count) for key, count in usage.items()}
    if any(count < 0 for count in counts.values()):
        raise ValueError("usage counts cannot be negative")
    return counts


def write_usage(path: Path, usage: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps({"version": 1, "usage": usage}, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def build_plan(song: Path, index: DuckDBSemanticIndex, model_bundle,
               candidate_count: int = 8, seed: int = 42, *, lyrics: list[str] | None = None,
               usage: dict[str, int] | None = None,
               profile: DirectorProfile | None = None) -> list[dict]:
    if candidate_count < 1:
        raise ValueError("candidate_count must be positive")
    duration, beat_energy = audio_beats_and_energy(song)
    if len(beat_energy) < 2:
        raise ValueError("Audio analysis did not find enough beat boundaries")
    threshold = sorted(value for _, value in beat_energy)[len(beat_energy) // 2]
    rng = random.Random(seed)
    counts = usage if usage is not None else {}
    recent: list[str] = []
    plan: list[dict] = []

    for i, (start, energy) in enumerate(beat_energy):
        end = beat_energy[i + 1][0] if i + 1 < len(beat_energy) else duration
        length = end - start
        if length <= 0:
            continue
        bpm = 60.0 / length
        lyric = _segment_lyric(lyrics or [], i, len(beat_energy))
        prompt, themes = compose_visual_prompt(0.75 if energy >= threshold else 0.25,
                                               lyric, bpm, profile)
        query = encode_text(prompt, model_bundle)
        candidates = index.search(query, limit=max(candidate_count * 4, candidate_count),
                                  excluded_paths=recent[-(profile.max_recent_reuse if profile else 3):])
        if not candidates:
            candidates = index.search(query, limit=max(candidate_count * 4, candidate_count))
        if not candidates:
            raise RuntimeError("Semantic index has no matching clips")
        selected = select_diverse(candidates[:candidate_count * 4], counts, recent[-3:], rng, profile)
        path = str(Path(selected.path).resolve())
        plan.append({"start_time": start, "duration": length, "clip_path": path,
                     "similarity": float(selected.score), "prompt": prompt,
                     "lyric_context": lyric, "themes": list(themes), "energy": energy,
                     "estimated_bpm": bpm, "pacing_window_seconds": list(pacing_window(bpm, profile)),
                     "candidate_margin": confidence_margin(candidates),
                     "usage_before": int(counts.get(path, 0))})
        recent.append(path)
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
    filters, labels = [], []
    for i, row in enumerate(plan):
        source_index = unique_paths.index(str(Path(row["clip_path"]).resolve())) + 1
        length = max(float(row["duration"]), 1.0 / fps)
        label = f"v{i}"
        filters.append(f"[{source_index}:v]trim=start=0:duration={length:.6f},setpts=PTS-STARTPTS,"
                       f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                       f"crop={width}:{height},fps={fps},format=yuv420p[{label}]")
        labels.append(f"[{label}]")
    filters.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[outv]")
    encoders = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True,
                              text=True, check=False).stdout
    video_codec = "h264_nvenc" if "h264_nvenc" in encoders else "libx264"
    command.extend(["-filter_complex", ";".join(filters), "-map", "[outv]", "-map", "0:a:0",
                    "-shortest", "-map_metadata", "-1", "-map_chapters", "-1", "-sn", "-dn",
                    "-c:v", video_codec])
    command.extend(["-preset", "p4", "-cq", "19"] if video_codec == "h264_nvenc"
                    else ["-preset", "medium", "-crf", "20"])
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
    parser.add_argument("--lyrics", type=Path, help="optional local TXT/HTML lyrics for semantic context")
    parser.add_argument("--global-usage", type=Path, help="shared JSON reuse ledger; updated after successful render")
    parser.add_argument("--candidate-count", type=int, default=8)
    parser.add_argument("--plan-only", "--dry-run", dest="plan_only", action="store_true")
    args = parser.parse_args()
    if not args.song.is_file(): parser.error(f"Song not found: {args.song}")
    if args.lyrics and not args.lyrics.is_file(): parser.error(f"Lyrics not found: {args.lyrics}")
    if args.candidate_count < 1: parser.error("--candidate-count must be positive")
    lyrics = read_lyrics(args.lyrics)
    usage = read_usage(args.global_usage)
    model_bundle = load_openclip(args.device)
    index = DuckDBSemanticIndex(args.db)
    try:
        plan = build_plan(args.song, index, model_bundle, args.candidate_count, args.seed,
                          lyrics=lyrics, usage=usage)
        output = args.output or Path("output") / f"{args.song.stem}_semantic.mp4"
        if args.plan_only:
            output.parent.mkdir(parents=True, exist_ok=True)
            plan_path = output.with_suffix(".json")
            plan_path.write_text(json.dumps({"version": 1, "seed": args.seed, "shots": plan},
                                            indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Wrote reviewable AI director plan: {plan_path}")
        else:
            width, height = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}[args.aspect]
            render_plan(args.song, plan, output, width, height)
            if args.global_usage:
                for row in plan:
                    clip = row["clip_path"]
                    usage[clip] = usage.get(clip, 0) + 1
                write_usage(args.global_usage, usage)
            print(f"Rendered: {output}")
    finally:
        index.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
