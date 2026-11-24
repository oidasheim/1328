# Vocal stems: optional, local-first analysis

Use `synapse-art-director --analyze-vocals ...` or the standalone CLI to create
cached mono 48 kHz PCM stems. Cache keys use the source SHA-256, so renames do
not create duplicate cache entries.

```bash
weedit-separate-vocals song.wav --cache cache/stems
synapse-art-director song.wav assets/clips --analyze-vocals --stem-method fallback
```

The built-in centered-mid + HPSS + 180–6500 Hz filter is only an approximate
proxy and is explicitly labeled `mid_hpss_proxy`. For actual model-based
separation, install and configure Demucs or audio-separator locally and opt in:

```bash
weedit-separate-vocals song.wav --method demucs --allow-model-download
```

Model loading may consume GPU memory or retrieve weights depending on the local
installation. The code performs best-effort Python/CUDA cache cleanup, but does
not promise a fixed VRAM ceiling or an empty device. The default does not invoke
model-based separation or download weights. Formant-energy analysis is run on
the cached vocal output; WhisperX forced alignment remains a separate explicit
step and is not silently launched by the build.
