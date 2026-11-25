"""Orchestration for scan → song compile → director → resolver → optimizer."""
from __future__ import annotations

from pathlib import Path
import json
from typing import Sequence

from .compiler import compile_song
from .director import generate_intents
from .genome import GenomeDB
from .models import ClipDNA, RenderAST
from .optimizer import optimize_render
from .resolver import resolve_intents


def compile_project(song_path: str | Path, clips_dir: str | Path, database: str | Path,
                    *, bpm: float | None = None, beat_times: list[float] | None = None,
                    duration: float | None = None, width: int = 1920,
                    height: int = 1080, fps: int = 30,
                    clip_pool: Sequence[ClipDNA] | None = None) -> RenderAST:
    song = compile_song(song_path, bpm=bpm, beat_times=beat_times, duration=duration)
    if clip_pool is None:
        genome = GenomeDB(database)
        try:
            clips = genome.all()
        finally:
            genome.close()
    else:
        clips = list(clip_pool)
    if not clips:
        raise RuntimeError(f"No indexed clips in {database}; run `weed scan {clips_dir}` first")
    intents = generate_intents(song)
    shots = resolve_intents(intents, clips, beat_grid=song.beats, fps=fps)
    ast = RenderAST(song.source, tuple(shots), song.duration, width, height, fps,
                    metadata={"bpm": song.bpm, "warnings": list(song.warnings),
                              "section_count": len(song.sections),
                              "clip_pool_mode": "global-reservation" if clip_pool is not None else "shared-index",
                              "clip_pool_size": len(clips)})
    return optimize_render(ast)


def write_ast(ast: RenderAST, destination: str | Path) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(ast.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
