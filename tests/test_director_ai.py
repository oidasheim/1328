from synapse.director_ai import (DirectorProfile, compose_visual_prompt, confidence_margin,
                                 infer_themes, pacing_window, select_diverse)
from synapse.semantic_index import validate_embedding
from synapse.semantic_render import prompt_for_energy


class Match:
    def __init__(self, path, score):
        self.path = path
        self.score = score


def test_prompt_changes_with_energy_and_keywords():
    high = prompt_for_energy(0.9, 0.5)
    low = prompt_for_energy(0.1, 0.5)
    assert "high-energy" in high
    assert "restrained" in low
    prompt, themes = compose_visual_prompt(0.8, "Oida, nachts am Beton mit 808", 145)
    assert {"urban", "bass_drop", "bavarian"}.issubset(set(themes))
    assert "rapid rhythmic cuts" in prompt


def test_bpm_pacing_profile_and_validation():
    assert pacing_window(105) == (1.4, 2.4)
    assert pacing_window(145) == (0.65, 1.25)
    assert pacing_window(90) == (2.2, 3.8)
    try:
        pacing_window(0)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid BPM should fail")


def test_semantic_selection_respects_recent_and_usage_penalties():
    fresh = Match("fresh.mp4", 0.30)
    reused = Match("reused.mp4", 0.31)
    import random
    selected = select_diverse([reused, fresh], {"reused.mp4": 100}, [], random.Random(7))
    assert selected.path == "fresh.mp4"
    selected = select_diverse([fresh, reused], {}, ["fresh.mp4"], random.Random(7))
    assert selected.path == "reused.mp4"


def test_confidence_margin_is_descriptive_margin():
    assert confidence_margin([Match("a", 0.8), Match("b", 0.6)]) == 0.2
    assert confidence_margin([]) == 0.0


def test_embedding_validation_remains_normalized():
    assert validate_embedding([3.0, 4.0], dimension=2) == [0.6, 0.8]
