"""LLVM-style deterministic passes over the render IR."""
from __future__ import annotations

from dataclasses import replace
from .models import RenderAST


def optimize_render(ast: RenderAST) -> RenderAST:
    if not ast.shots:
        raise ValueError("Render AST has no shots")
    if ast.width <= 0 or ast.height <= 0 or ast.width % 2 or ast.height % 2:
        raise ValueError("Output dimensions must be positive even integers")
    if ast.fps <= 0 or ast.duration <= 0:
        raise ValueError("FPS and duration must be positive")
    cursor = 0.0
    optimized = []
    for shot in ast.shots:
        if shot.duration <= 0 or shot.source_in < 0:
            raise ValueError("Shot trim and duration are invalid")
        if not shot.clip_path:
            raise ValueError("Shot is missing a clip path")
        optimized.append(replace(shot, timeline_start=cursor))
        cursor += shot.duration
    if cursor + 1.0 / ast.fps < ast.duration:
        raise ValueError("Render shots do not cover the song duration")
    return replace(ast, shots=tuple(optimized), duration=min(ast.duration, cursor),
                   metadata={**ast.metadata, "optimizer_passes": ["beat_order", "trim_validation", "continuity", "render_validation"]})
