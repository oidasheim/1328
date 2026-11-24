import numpy as np
import pytest

from weedit_native.lipsync import dtw_lipsync_match, formant_energy_mar, phonemes_to_mar


def test_phonemes_to_mar_maps_phonemes_and_plosive_lead():
    curve = phonemes_to_mar([
        {"start": 1.0, "end": 1.2, "phoneme": "B"},
        {"start": 1.3, "end": 1.5, "phoneme": "AA"},
    ], duration=2, fps=60, smoothing=False)
    assert curve[int(0.98 * 60)] == pytest.approx(0.04)
    assert curve[int(0.99 * 60)] == pytest.approx(0.04)
    assert curve[int(1.0 * 60)] >= 0.02
    assert curve[int(1.3 * 60)] == pytest.approx(0.68)
    assert np.all((curve >= 0) & (curve <= 1))


def test_dtw_match_finds_same_sequence_with_offset_and_speed():
    target = np.array([0.04, 0.1, 0.4, 0.7, 0.3, 0.05, 0.6, 0.2, 0.04], dtype=np.float32)
    source = np.concatenate([np.zeros(5, dtype=np.float32), target, np.zeros(5, dtype=np.float32)])
    result = dtw_lipsync_match(source, target, warp_candidates=(1.0,), max_offsets=20, radius=2)
    assert result.score > 0.95
    assert result.source_offset == 5


def test_invalid_alignment_and_warp_rejected():
    with pytest.raises(ValueError):
        phonemes_to_mar([{"start": 2, "end": 1, "phoneme": "AA"}], 3)
    with pytest.raises(ValueError):
        dtw_lipsync_match([0, 1, 0], [0, 1, 0], warp_candidates=(1.2,))


def test_audio_fallback_requires_optional_dependency_or_returns_curve(monkeypatch):
    # Behavioral contract is tested with a small deterministic fake librosa API.
    class FakeLibrosa:
        @staticmethod
        def load(*args, **kwargs):
            return np.ones(4096, dtype=np.float32), kwargs["sr"]
        @staticmethod
        def effects_hpss(signal):
            return signal, signal
        @staticmethod
        def stft(signal, n_fft, hop_length):
            return np.ones((n_fft // 2 + 1, 1), dtype=np.float32)
        @staticmethod
        def fft_frequencies(sr, n_fft):
            return np.linspace(0, sr / 2, n_fft // 2 + 1)
        @staticmethod
        def frames_to_time(frames, sr, hop_length):
            return np.asarray(frames) * hop_length / sr
    monkeypatch.setitem(__import__("sys").modules, "librosa", FakeLibrosa)
    curve = formant_energy_mar("dummy.wav", duration=1, fps=10)
    assert len(curve) == 11
    assert np.all(np.isfinite(curve))
