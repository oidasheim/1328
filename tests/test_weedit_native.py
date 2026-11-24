import json
from pathlib import Path

import pytest

from weedit_native.compiler import compile_song
from weedit_native.director import generate_intents
from weedit_native.models import ClipDNA, RenderAST, RenderShot
from weedit_native.optimizer import optimize_render
from weedit_native.pipeline import compile_project
from weedit_native.resolver import resolve, resolve_intents, set_beat_grid


def test_song_compiler_uses_explicit_analysis_without_optional_libs(tmp_path):
    audio = tmp_path / "song.mp3"
    audio.write_bytes(b"not decoded in explicit mode")
    song = compile_song(audio, bpm=120, beat_times=[0, .5, 1, 1.5], duration=2)
    assert song.bpm == 120
    assert len(song.beats) == 4
    assert song.sections[0].start == 0


def test_resolver_and_optimizer_produce_contiguous_render_ast(tmp_path):
    audio = tmp_path / "track.mp3"
    audio.touch()
    clips = [ClipDNA("a", str(tmp_path / "a.mp4"), 4, motion=.8, tags=("fast",)),
             ClipDNA("b", str(tmp_path / "b.mp4"), 4, motion=.1, tags=("atmosphere",))]
    set_beat_grid((0, .5, 1, 1.5, 2))
    intents = generate_intents(compile_song(audio, bpm=120, beat_times=[0,.5,1,1.5], duration=2))
    shots = resolve_intents(intents, clips)
    ast = optimize_render(RenderAST(str(audio), tuple(shots), 2))
    assert ast.shots[0].timeline_start == 0
    assert ast.metadata["optimizer_passes"]


def test_render_ast_roundtrip():
    ast = RenderAST("song.mp3", (RenderShot("clip.mp4", 0, 3, 0),), 3)
    restored = RenderAST.from_dict(json.loads(json.dumps(ast.to_dict())))
    assert restored == ast


def test_optimizer_rejects_insufficient_coverage():
    with pytest.raises(ValueError, match="cover"):
        optimize_render(RenderAST("song.mp3", (RenderShot("c.mp4", 0, 1, 0),), 4))


def test_resolver_deterministic_tie_break():
    need = __import__("weedit_native.models", fromlist=["ShotNeed"]).ShotNeed("x", 0, 1, .5, ("fast",), .5)
    clips = [ClipDNA("b", "/z.mp4", 2, motion=.5, tags=("fast",)), ClipDNA("a", "/a.mp4", 2, motion=.5, tags=("fast",))]
    assert resolve(need, clips)[0][0].path == "/a.mp4"
