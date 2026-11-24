from synapse.semantic_index import validate_embedding
from synapse.semantic_render import prompt_for_energy


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
