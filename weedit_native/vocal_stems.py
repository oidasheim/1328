"""Explicit, cached vocal stem separation with transparent CPU fallback.

External separators may download large model weights and consume GPU memory.
They are therefore never invoked unless ``allow_model_download`` is explicitly
set by the caller. The built-in HPSS/mid-channel path is an approximate signal
proxy, not source separation with guaranteed isolation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Literal


Method = Literal["auto", "roformer", "demucs", "fallback"]


@dataclass(frozen=True)
class StemResult:
    vocals: str
    accompaniment: str
    method: str
    source_sha256: str
    cached: bool
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _valid_audio(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 128:
        return False
    try:
        import soundfile as sf
        info = sf.info(str(path))
        return info.frames > 0 and info.samplerate > 0
    except Exception:
        return False


def _write_pcm(source: Path, destination: Path) -> None:
    import librosa
    import soundfile as sf
    audio, _ = librosa.load(str(source), sr=48_000, mono=True)
    if audio.size == 0:
        raise ValueError(f"separator produced an empty audio file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(destination), audio, 48_000, subtype="PCM_24")


def _run_roformer(source: Path, work: Path) -> tuple[Path, Path] | None:
    try:
        from audio_separator.separator import Separator
    except ImportError:
        return None
    separator = Separator(output_dir=str(work), output_format="WAV", use_autocast=True,
                          mdx_params={"hop_length": 1024, "segment_size": 256,
                                      "overlap": 0.25, "batch_size": 1})
    separator.load_model(model_filename="model_bs_roformer_ep_317_sdr_12.9755.ckpt")
    outputs = separator.separate(str(source))
    del separator
    paths = [Path(item) if Path(item).is_absolute() else work / Path(item).name for item in outputs]
    vocal = next((p for p in paths if "vocal" in p.name.lower()), None)
    backing = next((p for p in paths if any(word in p.name.lower()
                   for word in ("instrumental", "no_vocals", "no-vocals"))), None)
    if vocal and vocal.is_file():
        return vocal, backing if backing and backing.is_file() else source
    return None


def _run_demucs(source: Path, work: Path) -> tuple[Path, Path] | None:
    executable = shutil.which("demucs")
    if not executable:
        return None
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        device = "cpu"
    command = [executable, "--two-stems=vocals", "-n", "htdemucs_ft",
               "--device", device, "--segment", "7", "--shifts", "1",
               "-o", str(work), str(source)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    directory = work / "htdemucs_ft" / source.stem
    vocals, accompaniment = directory / "vocals.wav", directory / "no_vocals.wav"
    if vocals.is_file():
        return vocals, accompaniment if accompaniment.is_file() else source
    return None


def _fallback_mid_hpss(source: Path, vocals_out: Path, backing_out: Path) -> None:
    """Approximate centered vocal proxy; not a substitute for a separator."""
    import librosa
    import numpy as np
    import soundfile as sf

    stereo, sr = librosa.load(str(source), sr=48_000, mono=False)
    if stereo.ndim == 2:
        mono = np.mean(stereo, axis=0, dtype=np.float32)
    else:
        mono = np.asarray(stereo, dtype=np.float32)
    if mono.size == 0:
        raise ValueError(f"audio source contains no samples: {source}")
    harmonic, _percussive = librosa.effects.hpss(mono, margin=2.0)
    spectrum = librosa.stft(harmonic, n_fft=2048, hop_length=512)
    frequencies = librosa.fft_frequencies(sr=sr, n_fft=2048)
    band = ((frequencies >= 180.0) & (frequencies <= 6500.0)).astype(np.float32)[:, None]
    vocal_proxy = librosa.istft(spectrum * band, hop_length=512, length=len(mono))
    residual = mono - vocal_proxy
    vocals_out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(vocals_out), vocal_proxy, sr, subtype="PCM_24")
    sf.write(str(backing_out), residual, sr, subtype="PCM_24")


def separate_vocal_stem(audio_path: str | Path, cache_dir: str | Path, *,
                        method: Method = "auto", allow_model_download: bool = False) -> StemResult:
    """Separate vocals locally and cache outputs by source content hash.

    ``auto`` attempts RoFormer and then Demucs only when explicit model-download
    permission is supplied; otherwise it uses the CPU HPSS/mid-channel proxy.
    No VRAM ceiling is promised: actual use depends on installed versions,
    model configuration and other GPU processes.
    """
    source = Path(audio_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if method not in {"auto", "roformer", "demucs", "fallback"}:
        raise ValueError("method must be auto, roformer, demucs, or fallback")
    digest = _sha256(source)
    destination = Path(cache_dir).expanduser().resolve() / digest
    vocals_out, backing_out = destination / "vocals_48k.wav", destination / "accompaniment_48k.wav"
    manifest_path = destination / "stems.json"
    if manifest_path.is_file() and _valid_audio(vocals_out) and _valid_audio(backing_out):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source_sha256") == digest and (method == "auto" or manifest.get("method") == method):
            return StemResult(str(vocals_out), str(backing_out), str(manifest["method"]), digest, True,
                              tuple(manifest.get("warnings", [])))

    warnings: list[str] = []
    requested = [method] if method != "auto" else ["roformer", "demucs", "fallback"]
    if not allow_model_download and any(name in requested for name in ("roformer", "demucs")):
        warnings.append("Model-based separators skipped; pass allow_model_download=True to permit model loading/downloads.")
        requested = [name for name in requested if name not in {"roformer", "demucs"}]
        if method != "fallback":
            requested.append("fallback")

    destination.mkdir(parents=True, exist_ok=True)
    selected = "fallback"
    with tempfile.TemporaryDirectory(prefix="separator-", dir=str(destination)) as temp_name:
        work = Path(temp_name)
        separated: tuple[Path, Path] | None = None
        for candidate in requested:
            if candidate == "fallback":
                break
            try:
                separated = _run_roformer(source, work) if candidate == "roformer" else _run_demucs(source, work)
                if separated is not None and _valid_audio(separated[0]):
                    selected = candidate
                    break
                warnings.append(f"{candidate} unavailable or returned no usable vocal stem")
            except Exception as exc:
                warnings.append(f"{candidate} failed: {type(exc).__name__}: {exc}")
                _release_accelerator_memory()

        if separated is None or selected == "fallback":
            _fallback_mid_hpss(source, vocals_out, backing_out)
            selected = "mid_hpss_proxy"
        else:
            _write_pcm(separated[0], vocals_out)
            if separated[1] != source and _valid_audio(separated[1]):
                _write_pcm(separated[1], backing_out)
            else:
                import librosa
                import numpy as np
                import soundfile as sf
                mix, _ = librosa.load(str(source), sr=48_000, mono=True)
                vocal, _ = librosa.load(str(vocals_out), sr=48_000, mono=True)
                length = min(len(mix), len(vocal))
                sf.write(str(backing_out), mix[:length] - vocal[:length], 48_000, subtype="PCM_24")

    _release_accelerator_memory()
    if not _valid_audio(vocals_out) or not _valid_audio(backing_out):
        raise RuntimeError("stem extraction did not produce valid audio files")
    manifest = {"source_sha256": digest, "source": str(source), "method": selected,
                "sample_rate": 48_000, "warnings": warnings,
                "note": "mid_hpss_proxy is approximate and is not guaranteed vocal isolation"}
    temporary_manifest = manifest_path.with_suffix(".json.tmp")
    temporary_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary_manifest, manifest_path)
    return StemResult(str(vocals_out), str(backing_out), selected, digest, False, tuple(warnings))


def _release_accelerator_memory() -> None:
    """Best-effort cleanup; does not guarantee a device's VRAM is empty."""
    import gc
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except (ImportError, RuntimeError):
        pass
