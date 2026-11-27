#include <bit>
#include <cstdint>
#include <cstdio>
#include <limits>

int main() {
    static_assert(std::numeric_limits<float>::is_iec559 && sizeof(float) == sizeof(std::int32_t));
    constexpr float bias = 12582912.0f;
    constexpr auto seed = std::bit_cast<std::int32_t>(bias);
    static_assert(seed == 0x4b400000);
    constexpr int max_dot = 32 * 128 * 128;
    for (int dot = -max_dot; dot <= max_dot; ++dot) {
        const float biased = std::bit_cast<float>(seed + dot);
        const float got = biased - bias;
        const float want = static_cast<float>(dot);
        if (std::bit_cast<std::uint32_t>(got) != std::bit_cast<std::uint32_t>(want)) {
            std::fprintf(stderr, "Mismatch at dot %d\n", dot);
            return 1;
        }
    }
    std::printf("PASS: %d int32 dot values [-%d, +%d] convert to bit-identical FP32\n", 2 * max_dot + 1, max_dot, max_dot);
}
