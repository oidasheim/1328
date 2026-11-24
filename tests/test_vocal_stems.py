import json

import numpy as np
import pytest

from weedit_native.vocal_stems import separate_vocal_stem


def test_fallback_stem_separation_is_cached_by_content(tmp_path, monkeypatch):
    import soundfile as sf
    source = tmp_path / "source.wav"
    sf.write(source, np.sin(np.arange(4800) * 0.05).astype(np.float32), 48000)
    class FakeLibrosa:
        @staticmethod
        def load(*args, **kwargs):
            return np.sin(np.arange(4800) * 0.05).astype(np.float32), 48000
        class effects:
            @staticmethod
            def hpss(audio, margin=2.0):
                return audio, np.zeros_like(audio)
        @staticmethod
        def stft(audio, n_fft, hop_length):
            return np.ones((n_fft // 2 + 1, max(1, len(audio) // hop_length)), dtype=np.complex64)
        @staticmethod
        def fft_frequencies(sr, n_fft):
            return np.linspace(0, sr / 2, n_fft // 2 + 1)
        @staticmethod
        def istft(spec, hop_length, length):
            return np.ones(length, dtype=np.float32) * 0.1
    monkeypatch.setitem(__import__("sys").modules, "librosa", FakeLibrosa)
    first = separate_vocal_stem(source, tmp_path / "cache", method="fallback")
    second = separate_vocal_stem(source, tmp_path / "cache", method="fallback")
    assert first.method == "mid_hpss_proxy"
    assert not first.cached and second.cached
    assert (tmp_path / "cache" / first.source_sha256 / "vocals_48k.wav").exists()


def test_model_separator_requires_explicit_permission(tmp_path, monkeypatch):
    source = tmp_path / "source.wav"
    source.write_bytes(b"not actually audio")
    monkeypatch.setattr("weedit_native.vocal_stems._fallback_mid_hpss",
                        lambda source, vocals, backing: (vocals.write_bytes(b"fake"), backing.write_bytes(b"fake")))
    # Invalid source should be rejected before attempting to process.
    with pytest.raises(Exception):
        separate_vocal_stem(source, tmp_path / "cache", method="fallback")
