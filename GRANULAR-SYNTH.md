# Granular audio synthesis kernel (C++20)

`native/granular_synth.*` is a small, dependency-free reference kernel for
windowed, overlapping grain playback. A fixed 256-slot pool, cubic-Hermite
interpolation, a precomputed Hann table, stereo gains, source-buffer wraparound,
and block-spanning grains are included. `process()` allocates no memory and
performs no locking or I/O; `spawn()` must not race the audio callback.

This is a scalar baseline, not an AVX2 implementation or a complete DAW plugin.
The per-grain interpolation has dependencies and should be profiled before SIMD
work. Upward resampling can alias; production use should add band-limited
resampling or mipmapped source buffers. The kernel expects a power-of-two source
buffer and accumulates into output spans, so clear the output block before use
when replacement rather than mixing is desired.

Build and run the native test:

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

This DSP feature is an artistic synthesis tool. Avoid excessive playback levels;
limit peaks and audition on headphones and speakers.
