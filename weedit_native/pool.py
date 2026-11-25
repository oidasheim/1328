"""Deterministic, global clip reservation for a batch of songs."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

from .compiler import compile_song
from .director import generate_intents
from .genome import GenomeDB
from .models import ClipDNA, ShotNeed
from .resolver import build_shot_needs, resolve


@dataclass(frozen=True)
class SongPool:
    song: str
    clip_paths: tuple[str, ...]
    scores: tuple[tuple[str, float], ...]
    shared_fallbacks: tuple[str, ...] = ()


@dataclass(frozen=True)
class PoolPlan:
    schema_version: int
    pool_size: int
    songs: tuple[SongPool, ...]
    unassigned_clips: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": self.schema_version,
                "allocation": "exclusive-first-round-robin",
                "pool_size": self.pool_size,
                "songs": [asdict(song) for song in self.songs],
                "unassigned_clips": list(self.unassigned_clips),
                "warnings": list(self.warnings)}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "PoolPlan":
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported pool-plan schema_version")
        raw_songs = data.get("songs")
        if not isinstance(raw_songs, list):
            raise ValueError("Pool plan must contain a songs list")
        songs = []
        for entry in raw_songs:
            if not isinstance(entry, dict) or not isinstance(entry.get("song"), str):
                raise ValueError("Malformed song entry in pool plan")
            paths, scores = entry.get("clip_paths", []), entry.get("scores", [])
            fallbacks = entry.get("shared_fallbacks", [])
            if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
                raise ValueError("Malformed clip_paths in pool plan")
            if not isinstance(scores, list):
                raise ValueError("Malformed scores in pool plan")
            parsed_scores = []
            for item in scores:
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    raise ValueError("Each pool score must be a [path, score] pair")
                score = float(item[1])
                if not math.isfinite(score):
                    raise ValueError("Pool scores must be finite")
                parsed_scores.append((str(item[0]), score))
            if not isinstance(fallbacks, list):
                raise ValueError("Malformed shared_fallbacks in pool plan")
            songs.append(SongPool(entry["song"], tuple(paths), tuple(parsed_scores),
                                  tuple(str(p) for p in fallbacks)))
        pool_size = int(data.get("pool_size", 0))
        if pool_size < 1:
            raise ValueError("pool_size must be positive")
        return cls(1, pool_size, tuple(songs),
                   tuple(str(p) for p in data.get("unassigned_clips", [])),
                   tuple(str(w) for w in data.get("warnings", [])))

    def clips_for(self, song: str | Path, indexed_clips: Sequence[ClipDNA]) -> list[ClipDNA]:
        key = str(Path(song).expanduser().resolve())
        entry = next((item for item in self.songs if item.song == key), None)
        if entry is None:
            raise ValueError(f"Song is absent from pool plan: {key}")
        by_path = {clip.path: clip for clip in indexed_clips}
        missing = [path for path in entry.clip_paths if path not in by_path]
        if missing:
            raise ValueError(f"Pool plan references clips absent from the current index: {missing[0]}")
        if not entry.clip_paths:
            raise ValueError(f"Pool plan assigned no clips to {key}")
        return [by_path[path] for path in entry.clip_paths]


def _usable(clip: ClipDNA) -> bool:
    return (math.isfinite(clip.duration) and clip.duration > 0 and bool(clip.path)
            and math.isfinite(clip.motion) and 0 <= clip.motion <= 1
            and math.isfinite(clip.brightness) and 0 <= clip.brightness <= 1
            and math.isfinite(clip.saturation) and 0 <= clip.saturation <= 1)


def _song_score(needs: Sequence[ShotNeed], clips: Sequence[ClipDNA]) -> dict[str, float]:
    """Average representative matches across the song, including later sections."""
    if not needs:
        return {clip.path: 0.0 for clip in clips if _usable(clip)}
    sample_count = min(32, len(needs))
    indices = sorted({round(i * (len(needs) - 1) / max(1, sample_count - 1))
                      for i in range(sample_count)})
    result = {}
    for clip in clips:
        if not _usable(clip):
            continue
        values = [resolve(need, [clip], top_k=1)[0][1]
                  if resolve(need, [clip], top_k=1) else 0.0 for need in (needs[i] for i in indices)]
        result[clip.path] = sum(values) / len(values)
    return result


def allocate_song_pools(song_needs: Mapping[str, Sequence[ShotNeed]], clips: Sequence[ClipDNA], *,
                        pool_size: int = 25) -> PoolPlan:
    """Reserve clips fairly and exclusively across all songs before rendering."""
    if pool_size < 1:
        raise ValueError("pool_size must be positive")
    songs = sorted((str(Path(key).expanduser().resolve()), tuple(needs))
                   for key, needs in song_needs.items())
    if not songs:
        raise ValueError("At least one song with shot needs is required")
    unique = {clip.path: clip for clip in clips if _usable(clip)}
    if not unique:
        raise ValueError("No usable clips available for global allocation")
    inventory = list(unique.values())
    scores = {song: _song_score(needs, inventory) for song, needs in songs}
    assigned = {song: [] for song, _ in songs}
    assigned_scores = {song: [] for song, _ in songs}
    remaining = set(unique)

    # Each song receives one exclusive reservation in a round before any song
    # receives its next one. Specialist clips receive a small fit advantage.
    for _ in range(pool_size):
        for song, _needs in songs:
            if not remaining:
                break
            def rank(path: str) -> tuple[float, float, str]:
                own = scores[song].get(path, 0.0)
                other_best = max((scores[other].get(path, 0.0)
                                  for other, _ in songs if other != song), default=0.0)
                return (own + 0.12 * (own - other_best), own, path)
            chosen = max(remaining, key=rank)
            remaining.remove(chosen)
            assigned[song].append(chosen)
            assigned_scores[song].append((chosen, scores[song].get(chosen, 0.0)))

    warnings = []
    if remaining:
        warnings.append(f"{len(remaining)} usable clips were not needed by requested pool sizes")
    if len(unique) < len(songs) * pool_size:
        warnings.append("Clip inventory is smaller than total reserved capacity; shared fallbacks were added")
    planned = []
    all_paths = sorted(unique)
    for song, _needs in songs:
        fallbacks = []
        if len(assigned[song]) < pool_size:
            for path in sorted(all_paths, key=lambda p: (-scores[song].get(p, 0.0), p)):
                if path in assigned[song]:
                    continue
                assigned[song].append(path)
                assigned_scores[song].append((path, scores[song].get(path, 0.0)))
                fallbacks.append(path)
                if len(assigned[song]) == pool_size:
                    break
        planned.append(SongPool(song, tuple(assigned[song]), tuple(assigned_scores[song]), tuple(fallbacks)))
    return PoolPlan(1, pool_size, tuple(planned), tuple(sorted(remaining)), tuple(warnings))


def plan_songs(song_paths: Sequence[str | Path], clips: Sequence[ClipDNA], *,
               pool_size: int = 25, fps: int = 30) -> PoolPlan:
    if fps <= 0:
        raise ValueError("fps must be positive")
    needs = {}
    for raw_path in sorted((Path(p).expanduser().resolve() for p in song_paths), key=str):
        song = compile_song(raw_path)
        needs[str(raw_path)] = build_shot_needs(generate_intents(song), song.beats, fps=fps)
    return allocate_song_pools(needs, clips, pool_size=pool_size)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic global clip reservation for a song batch")
    parser.add_argument("songs", type=Path, nargs="+")
    parser.add_argument("--db", type=Path, default=Path("database/genome.sqlite3"))
    parser.add_argument("--out", type=Path, default=Path("reports/song-pool-plan.json"))
    parser.add_argument("--pool-size", type=int, default=25)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()
    if args.pool_size < 1 or args.fps < 1:
        parser.error("--pool-size and --fps must be positive")
    genome = GenomeDB(args.db)
    try:
        clips = genome.all()
    finally:
        genome.close()
    plan = plan_songs(args.songs, clips, pool_size=args.pool_size, fps=args.fps)
    target = args.out.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".tmp")
    temp.write_text(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(target)
    print(json.dumps({"plan": str(target), "songs": len(plan.songs),
                      "warnings": list(plan.warnings)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
