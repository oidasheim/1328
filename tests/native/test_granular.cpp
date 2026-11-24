#include "granular_synth.hpp"

#include <array>
#include <cassert>
#include <cmath>
#include <cstddef>
#include <vector>

using synapse::audio::GrainPool;

int main() {
    GrainPool pool;
    std::array<float, 8> source{0.0f, 1.0f, 0.0f, -1.0f,
                                0.0f, 1.0f, 0.0f, -1.0f};
    std::array<float, 16> left{};
    std::array<float, 16> right{};

    assert(!pool.spawn(0, 0.0, 1.0f, 1, 1.0f, 1.0f));
    assert(pool.spawn(0, 0.0, 1.0f, 8, 0.5f, 0.5f));
    assert(pool.active_count() == 1);
    assert(pool.process(source, left, right));
    assert(pool.active_count() == 0);
    assert(left == right);
    assert(std::abs(left[0]) < 1e-6f);  // Hann begins at zero.
    assert(std::abs(left[7]) < 1e-6f);  // Hann ends at zero.
    assert(std::abs(left[2]) > 0.01f);

    GrainPool delayed;
    std::array<float, 4> block_l{};
    std::array<float, 4> block_r{};
    assert(delayed.spawn(1, 0.0, 1.0f, 4, 1.0f, 1.0f, 6));
    assert(delayed.process(source, block_l, block_r));
    assert(delayed.active_count() == 1);
    assert(delayed.process(source, block_l, block_r));
    assert(delayed.active_count() == 1);
    assert(delayed.process(source, block_l, block_r));
    assert(delayed.active_count() == 0);

    std::array<float, 3> invalid_source{};
    assert(!pool.process(invalid_source, left, right));
    assert(!pool.spawn(GrainPool::max_grains, 0.0, 1.0f, 8, 1.0f, 1.0f));
    assert(!pool.spawn(1, 0.0, -1.0f, 8, 1.0f, 1.0f));
    return 0;
}
