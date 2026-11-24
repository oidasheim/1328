"""Beat-aligned semantic clip selection and FFmpeg rendering."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

from .semantic_index import DuckDBSemanticIndex, encode_text, load_openclip


def prompt_for_energy(energy: float, threshold: float) -> str:
    if energy >= threshold:
        return "cinematic urban night scene, vivid neon color, energetic movement, dramatic lighting"
    return "cinematic quiet urban scene, atmospheric shadows, restrained movement, soft contrast"


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


def build_plan(song: Path, index: DuckDBSemanticIndex, model_bundle,
               candidate_count: int = 8, seed: int = 42) -> list[dict]:
    import random
    duration, beat_energy = audio_beats_and_energy(song)
    if len(beat_energy) < 2:
        raise ValueError("Audio analysis did not find enough beat boundaries")
    threshold = sorted(value for _, value in beat_energy)[len(beat_energy) // 2]
    chooser = random.Random(seed)
    used: list[str] = []
    plan: list[dict] = []

    for i, (start, energy) in enumerate(beat_energy):
        end = beat_energy[i + 1][0] if i + 1 < len(beat_energy) else duration
        segment_duration = end - start
        if segment_duration <= 0:
            continue
        prompt = prompt_for_energy(energy, threshold)
        query = encode_text(prompt, model_bundle)
        matches = index.search(query, limit=candidate_count, excluded_paths=used[-3:])
        if not matches:
            matches = index.search(query, limit=candidate_count)
        if not matches:
            raise RuntimeError("Semantic index has no matching clips")
        # Randomize among strong matches while preserving a preference for top similarity.
        shortlist = matches[:min(3, len(matches))]
        selected = chooser.choice(shortlist)
        plan.append({
            "start_time": start,
            "duration": segment_duration,
            "clip_path": selected.path,
            "similarity": selected.score,
            "prompt": prompt,
            "energy": energy,
        })
        used.append(selected.path)
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
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[outv]", "-map", "0:a:0", "-shortest",
        "-map_metadata", "-1", "-map_chapters", "-1", "-sn", "-dn",
        "-c:v", video_codec,
    ])
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
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    if not args.song.is_file():
        parser.error(f"Song not found: {args.song}")

    model_bundle = load_openclip(args.device)
    index = DuckDBSemanticIndex(args.db)
    try:
        plan = build_plan(args.song, index, model_bundle, seed=args.seed)
        output = args.output or Path("output") / f"{args.song.stem}_semantic.mp4"
        if args.plan_only:
            output.parent.mkdir(parents=True, exist_ok=True)
            output = output.with_suffix(".json")
            output.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Wrote semantic edit plan: {output}")
        else:
            width, height = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}[args.aspect]
            render_plan(args.song, plan, output, width, height)
            print(f"Rendered: {output}")
    finally:
        index.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
