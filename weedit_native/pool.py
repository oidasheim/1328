"""Deterministic, global clip reservation for a batch of songs.

Reservations are exclusive when possible: a strong clip for a later song is not
consumed merely because that song was compiled later. If capacity is exhausted,
the planner records explicit shared fallbacks rather than silently dropping a
song from the batch.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .compiler import compile_song
from .director import generate_intents
from .genome import GenomeDB
from .models import ClipDNA, Intent, ShotNeed
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
        return {
            "schema_version": self.schema_version,
            "allocation": "exclusive-first-round-robin",
            "pool_size": self.pool_size,
            "songs": [asdict(song) for song in self.songs],
            "unassigned_clips": list(self.unassigned_clips),
            "warnings": list(self.warnings),
        }

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
            paths = entry.get("clip_paths", [])
            scores = entry.get("scores", [])
            fallbacks = entry.get("shared_fallbacks", [])
            if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
                raise ValueError("Malformed clip_paths in pool plan")
            if not isinstance(scores, list):
                raise ValueError("Malformed scores in pool plan")
            songs.append(SongPool(entry["song"], tuple(paths), tuple((str(p), float(s)) for p, s in scores),
                                  tuple(str(p) for p in fallbacks)))
        pool_size = int(data.get("pool_size", 0))
        if pool_size < 1:
            raise ValueError("pool_size must be positive")
        return cls(1, pool_size, tuple(songs), tuple(str(p) for p in data.get("unassigned_clips", [])),
                   tuple(str(w) for w in data.get("warnings", [])))

    def clips_for(self, song: str | Path, indexed_clips: Sequence[ClipDNA]) -> list[ClipDNA]:
        """Resolve a planned song key to current indexed clip records; fail closed on stale plans."""
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


def _song_score(needs: Sequence[ShotNeed], clips: Sequence[ClipDNA]) -> dict[str, float]:
    """Score a clip for a song using its best fit across representative shot needs."""
    if not needs:
        return {clip.path: 0.0 for clip in clips if _usable(clip)}
    # Sampling evenly bounds work for long songs without favoring their opening.
    count = min(32, len(needs))
    indices = sorted({round(i * (len(needs) - 1) / max(1, count - 1)) for i in range(count)})
    sampled = [needs[i] for i in indices]
    result: dict[str, float] = {}
    for clip in clips:
        if not _usable(clip):
            continue
        values = [next((score for candidate, score in resolve(need, [clip], top_k=1)), 0.0)
                  for need in sampled]
        result[clip.path] = sum(values) / len(values)
    return result


def _usable(clip: ClipDNA) -> bool:
    return (math.isfinite(clip.duration) and clip.duration > 0 and bool(clip.path)
            and math.isfinite(clip.motion) and 0 <= clip.motion <= 1
            and math.isfinite(clip.brightness) and 0 <= clip.brightness <= 1
            and math.isfinite(clip.saturation) and 0 <= clip.saturation <= 1)


def allocate_song_pools(song_needs: Mapping[str, Sequence[ShotNeed]], clips: Sequence[ClipDNA], *,
                        pool_size: int = 25) -> PoolPlan:
    """Allocate exclusive per-song pools globally with deterministic fair rounds.

    Clips with a distinctive fit receive a modest specificity bonus. Every song
    gets one reservation per round before the next round starts. When there are
    fewer clips than requested slots, the remaining slots are filled with
    explicitly marked shared fallbacks; no clip is deleted from the source pool.
    """
    if pool_size < 1:
        raise ValueError("pool_size must be positive")
    songs = sorted((str(Path(key).expanduser().resolve()), tuple(needs))
                   for key, needs in song_needs.items())
    if not songs:
        raise ValueError("At least one song with shot needs is required")
    unique_clips = {clip.path: clip for clip in clips if _usable(clip)}
    if not unique_clips:
        raise ValueError("No usable clips available for global allocation")
    scores = {song: _song_score(needs, list(unique_clips.values())) for song, needs in songs}
    assigned: dict[str, list[str]] = {song: [] for song, _ in songs}
    assigned_scores: dict[str, list[tuple[str, float]]] = {song: [] for song, _ in songs}
    remaining = set(unique_clips)

    for _round in range(pool_size):
        # Song order is fixed and output is independent of input mapping order.
        for song, _needs in songs:
            if not remaining:
                break
            others = [scores[other][path] for other, _ in songs if other != song
                      for path in remaining if path in scores[other]]
            # Rank candidates by song fit plus a small specialization preference.
            def rank(path: str) -> tuple[float, float, str]:
                own = scores[song].get(path, 0.0)
                other_best = max((scores[other].get(path, 0.0) for other, _ in songs if other != song),
                                 default=0.0)
                return (own + 0.12 * (own - other_best), own, path)
            chosen = max(remaining, key=rank)
            remaining.remove(chosen)
            assigned[song].append(chosen)
            assigned_scores[song].append((chosen, scores[song].get(chosen, 0.0)))

    warnings = []
    if remaining:
        warnings.append(f"{len(remaining)} usable clips were not needed by the requested pool sizes")
    if len(unique_clips) < len(songs) * pool_size:
        warnings.append("Clip inventory is smaller than total reserved capacity; shared fallbacks were added")
    planned = []
    all_paths = sorted(unique_clips)
    for song, _needs in songs:
        paths = assigned[song]
        fallbacks: list[str] = []
        if len(paths) < pool_size:
            for path in sorted(all_paths, key=lambda p: (-scores[song].get(p, 0.0), p)):
                if path in paths:
                    continue
                paths.append(path)
                fallbacks.append(path)
                assigned_scores[song].append((path, scores[song].get(path, 0.0)))
                if len(paths) == pool_size:
                    break
        planned.append(SongPool(song, tuple(paths), tuple(assigned_scores[song]), tuple(fallbacks)))
    return PoolPlan(1, pool_size, tuple(planned), tuple(sorted(remaining)), tuple(warnings))


def plan_songs(song_paths: Iterable[str | Path], clips: Sequence[ClipDNA], *,
               pool_size: int = 25, fps: int = 30) -> PoolPlan:
    if fps <= 0:
        raise ValueError("fps must be positive")
    needs: dict[str, list[ShotNeed]] = {}
    for raw_path in sorted((Path(p).expanduser().resolve() for p in song_paths), key=str):
        song = compile_song(raw_path)
        intents = generate_intents(song)
        needs[str(raw_path)] = build_shot_needs(intents, song.beats, fps=fps)
    return allocate_song_pools(needs, clips, pool_size=pool_size)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic global clip reservation for a song batch")
    parser.add_argument("songs", type=Path, nargs="+", help="audio files; analysis uses the optional audio extra")
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
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(json.dumps({"plan": str(target), "songs": len(plan.songs),
                      "reserved_clips": sum(len(item.clip_paths) for item in plan.songs),
                      "warnings": list(plan.warnings)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
