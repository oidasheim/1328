#include "granular_synth.hpp"

#include <cmath>
#include <limits>

namespace synapse::audio {
namespace {
constexpr double two_pi = 6.283185307179586476925286766559;

bool finite(float value) noexcept { return std::isfinite(value); }
bool finite(double value) noexcept { return std::isfinite(value); }
} // namespace

GrainPool::GrainPool() noexcept {
    // Precompute outside the audio callback: process() only interpolates this
    // table and does not call trigonometric functions.
    for (std::size_t i = 0; i <= window_table_size; ++i) {
        const double phase = static_cast<double>(i) / window_table_size;
        hann_[i] = static_cast<float>(0.5 * (1.0 - std::cos(two_pi * phase)));
    }
}

bool GrainPool::spawn(std::size_t slot, double source_phase, float rate,
                      std::size_t length_samples, float gain_left,
                      float gain_right, std::size_t start_offset) noexcept {
    if (slot >= max_grains || grains_[slot].active || !finite(source_phase) ||
        !finite(rate) || rate <= 0.0f || length_samples < 2 ||
        !finite(gain_left) || !finite(gain_right)) {
        return false;
    }
    grains_[slot] = Grain{source_phase, rate, gain_left, gain_right,
                          0, length_samples, start_offset, true};
    return true;
}

float GrainPool::window(float phase) const noexcept {
    const float clamped = phase < 0.0f ? 0.0f : (phase > 1.0f ? 1.0f : phase);
    const float position = clamped * static_cast<float>(window_table_size);
    const auto index = static_cast<std::size_t>(position);
    if (index >= window_table_size) return hann_[window_table_size];
    const float fraction = position - static_cast<float>(index);
    return hann_[index] + fraction * (hann_[index + 1] - hann_[index]);
}

float GrainPool::cubic_hermite(std::span<const float> source,
                               std::size_t mask,
                               double phase) noexcept {
    const double base = std::floor(phase);
    const auto i1 = static_cast<std::size_t>(base) & mask;
    const float t = static_cast<float>(phase - base);
    const float y0 = source[(i1 - 1) & mask];
    const float y1 = source[i1];
    const float y2 = source[(i1 + 1) & mask];
    const float y3 = source[(i1 + 2) & mask];

    const float c0 = y1;
    const float c1 = 0.5f * (y2 - y0);
    const float c2 = y0 - 2.5f * y1 + 2.0f * y2 - 0.5f * y3;
    const float c3 = 0.5f * (y3 - y0) + 1.5f * (y1 - y2);
    return ((c3 * t + c2) * t + c1) * t + c0;
}

bool GrainPool::process(std::span<const float> source,
                        std::span<float> output_left,
                        std::span<float> output_right) noexcept {
    if (source.size() < 4 || (source.size() & (source.size() - 1)) != 0 ||
        output_left.size() != output_right.size()) {
        return false;
    }
    const std::size_t mask = source.size() - 1;

    for (auto& grain : grains_) {
        if (!grain.active) continue;
        if (!finite(grain.phase) || !finite(grain.rate) || grain.rate <= 0.0f) {
            grain.active = false;
            continue;
        }

        std::size_t frame = grain.delay;
        grain.delay = 0;
        if (frame >= output_left.size()) {
            // Preserve the remaining offset relative to the next block.
            grain.delay = frame - output_left.size();
            continue;
        }

        for (; frame < output_left.size() && grain.age < grain.length; ++frame) {
            const float env_phase = static_cast<float>(grain.age) /
                                    static_cast<float>(grain.length - 1);
            const float env = window(env_phase);
            const float sample = cubic_hermite(source, mask, grain.phase) * env;
            output_left[frame] += sample * grain.gain_left;
            output_right[frame] += sample * grain.gain_right;

            grain.phase += static_cast<double>(grain.rate);
            if (grain.phase >= static_cast<double>(source.size())) {
                grain.phase = std::fmod(grain.phase, static_cast<double>(source.size()));
            }
            ++grain.age;
        }
        if (grain.age >= grain.length) grain.active = false;
    }
    return true;
}

std::size_t GrainPool::active_count() const noexcept {
    std::size_t count = 0;
    for (const auto& grain : grains_) count += grain.active ? 1U : 0U;
    return count;
}

} // namespace synapse::audio
