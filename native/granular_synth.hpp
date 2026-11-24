#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace synapse::audio {

class GrainPool {
public:
    static constexpr std::size_t max_grains = 256;
    static constexpr std::size_t window_table_size = 2048;

    GrainPool() noexcept;

    // Schedule a grain in a free slot. start_offset is measured from the start
    // of the next process() call. Returns false for invalid parameters or when
    // the slot is already active. Call from the control thread, not concurrently
    // with process().
    bool spawn(std::size_t slot, double source_phase, float rate,
               std::size_t length_samples, float gain_left, float gain_right,
               std::size_t start_offset = 0) noexcept;

    // Adds this pool's signal into caller-provided output buffers; it does not
    // clear them. The source must have a power-of-two length and remain alive
    // for the duration of the call. No allocation, locks, or I/O occur here.
    // Call spawn/process from the same audio thread or synchronize externally.
    bool process(std::span<const float> source,
                 std::span<float> output_left,
                 std::span<float> output_right) noexcept;

    [[nodiscard]] std::size_t active_count() const noexcept;

private:
    struct Grain {
        double phase = 0.0;
        float rate = 1.0f;
        float gain_left = 0.0f;
        float gain_right = 0.0f;
        std::size_t age = 0;
        std::size_t length = 0;
        std::size_t delay = 0;
        bool active = false;
    };

    std::array<Grain, max_grains> grains_{};
    std::array<float, window_table_size + 1> hann_{};

    [[nodiscard]] float window(float phase) const noexcept;
    [[nodiscard]] static float cubic_hermite(std::span<const float> source,
                                             std::size_t mask,
                                             double phase) noexcept;
};

} // namespace synapse::audio
