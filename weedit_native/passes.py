"""Next-level WE.ED.IT LLVM-style pass infrastructure."""
from __future__ import annotations

from dataclasses import replace
from typing import Callable, Iterable

from .models import RenderAST


Pass = Callable[[RenderAST], tuple[RenderAST, dict[str, object]]]


def beat_alignment_pass(ast: RenderAST) -> tuple[RenderAST, dict[str, object]]:
    fps = ast.fps
    snaps = []
    normalized = []
    for shot in ast.shots:
        start = round(shot.timeline_start * fps) / fps
        duration = round(shot.duration * fps) / fps
        duration = max(duration, 0.15)
        normalized.append(replace(shot, timeline_start=start, duration=duration))
        snaps.append({"start_frame": round(start * fps), "duration_frames": round(duration * fps)})
    cursor = 0.0
    contiguous = []
    for shot in normalized:
        contiguous.append(replace(shot, timeline_start=cursor))
        cursor += shot.duration
    result = replace(ast, shots=tuple(contiguous), duration=min(ast.duration, cursor))
    return result, {"snaps": snaps}


def camera_continuity_pass(ast: RenderAST) -> tuple[RenderAST, dict[str, object]]:
    previous = None
    changes = 0
    shots = []
    for shot in ast.shots:
        camera = shot.camera
        if previous is not None and camera != previous:
            changes += 1
        shots.append(shot)
        previous = camera
    return replace(ast, shots=tuple(shots)), {"camera_changes": changes}


def motion_flow_pass(ast: RenderAST) -> tuple[RenderAST, dict[str, object]]:
    return ast, {"motion_policy": "shot-duration weighted; source analysis remains in ClipDNA"}


def color_harmony_pass(ast: RenderAST) -> tuple[RenderAST, dict[str, object]]:
    colors = [shot.color for shot in ast.shots]
    return ast, {"colors": colors, "unique_colors": len(set(colors))}


def face_diversity_pass(ast: RenderAST) -> tuple[RenderAST, dict[str, object]]:
    return ast, {"face_metadata_required": True, "policy": "avoid recent scene and clip repetition"}


def transition_simplification_pass(ast: RenderAST) -> tuple[RenderAST, dict[str, object]]:
    return ast, {"transitions": "hard-cut-default", "implemented": False}


def surprise_placement_pass(ast: RenderAST) -> tuple[RenderAST, dict[str, object]]:
    return ast, {"policy": "reserved for user-approved effects", "implemented": False}


def rl_refinement_pass(ast: RenderAST) -> tuple[RenderAST, dict[str, object]]:
    mean = sum(shot.score for shot in ast.shots) / len(ast.shots) if ast.shots else 0.0
    return ast, {"mean_candidate_score": mean, "note": "descriptive; no fabricated reward"}


def runtime_reduction_pass(ast: RenderAST) -> tuple[RenderAST, dict[str, object]]:
    removed = 0
    kept = []
    cursor = 0.0
    for shot in ast.shots:
        if shot.duration < 0.15:
            removed += 1
            continue
        kept.append(replace(shot, timeline_start=cursor))
        cursor += shot.duration
    return replace(ast, shots=tuple(kept), duration=min(ast.duration, cursor)), {"removed_sub_150ms": removed}


def render_validation_pass(ast: RenderAST) -> tuple[RenderAST, dict[str, object]]:
    if not ast.shots:
        raise ValueError("Render IR has no shots")
    if ast.width <= 0 or ast.height <= 0 or ast.width % 2 or ast.height % 2:
        raise ValueError("Output dimensions must be positive even integers")
    if ast.fps <= 0 or ast.duration <= 0:
        raise ValueError("FPS and duration must be positive")
    cursor = 0.0
    for shot in ast.shots:
        if shot.duration < 0.15:
            raise ValueError("Render IR contains a sub-150ms shot")
        if shot.timeline_start != cursor:
            raise ValueError("Shots are not contiguous")
        cursor += shot.duration
    if cursor + 1.0 / ast.fps < ast.duration:
        raise ValueError("Render shots do not cover the song duration")
    return replace(ast, duration=min(ast.duration, cursor)), {"video_tags": "zero-metadata-mandate", "stream_map": "video+source-audio"}


PASS_PIPELINE: tuple[tuple[str, Pass], ...] = (
    ("BeatAlignmentPass", beat_alignment_pass),
    ("CameraContinuityPass", camera_continuity_pass),
    ("MotionFlowPass", motion_flow_pass),
    ("ColorHarmonyPass", color_harmony_pass),
    ("FaceDiversityPass", face_diversity_pass),
    ("TransitionSimplificationPass", transition_simplification_pass),
    ("SurprisePlacementPass", surprise_placement_pass),
    ("RLRefinementPass", rl_refinement_pass),
    ("RuntimeReductionPass", runtime_reduction_pass),
    ("RenderValidationPass", render_validation_pass),
)


def run_pass_pipeline(ast: RenderAST) -> tuple[RenderAST, dict[str, object]]:
    evidence: dict[str, object] = {"passes": []}
    current = ast
    for name, pass_fn in PASS_PIPELINE:
        current, details = pass_fn(current)
        evidence["passes"].append({"name": name, "details": details})
    evidence["pass_count"] = len(PASS_PIPELINE)
    return current, evidence
