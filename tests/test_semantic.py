from synapse.semantic_index import validate_embedding
from synapse.semantic_render import (_choose_diverse, _lyric_for_segment, load_lyrics,
                                     prompt_for_energy)


class Match:
    def __init__(self, path, score):
        self.path = path
        self.score = score


def test_prompt_changes_with_energy():
    assert "energetic" in prompt_for_energy(0.9, 0.5)
    assert "quiet" in prompt_for_energy(0.1, 0.5)


def test_embedding_validation_normalizes_vector():
    result = validate_embedding([3.0, 4.0], dimension=2)
    assert result == [0.6, 0.8]


def test_embedding_rejects_bad_dimension():
    try:
        validate_embedding([1.0], dimension=2)
    except ValueError as exc:
        assert "dimension" in str(exc)
    else:
        raise AssertionError("Expected invalid dimensions to fail")


def test_html_lyrics_ignores_scripts_and_adds_text_context(tmp_path):
    html = tmp_path / "lyrics.html"
    html.write_text("<html><body><div>[Verse] Beton im Regen</div><script>hidden data</script></body></html>", encoding="utf-8")
    lyrics = load_lyrics(html)
    assert "Beton im Regen" in lyrics
    assert "hidden data" not in lyrics
    assert "Beton" in prompt_for_energy(0.8, 0.5, lyrics)


def test_diversity_penalizes_reused_clip_deterministically(tmp_path):
    fresh = Match(str(tmp_path / "fresh.mp4"), 0.30)
    reused = Match(str(tmp_path / "reused.mp4"), 0.31)
    usage = {reused.path: 100}
    import random
    selected = _choose_diverse([reused, fresh], usage, random.Random(12), set())
    assert selected.path == fresh.path


def test_lyric_segment_distribution():
    assert _lyric_for_segment("line one\nline two", 0, 2) == "line one"
    assert _lyric_for_segment("line one\nline two", 1, 2) == "line two"
