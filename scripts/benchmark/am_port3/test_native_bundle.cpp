#include "native_bundle.h"
#include <iostream>

int main(int argc, char ** argv) try {
    am_carrier::require(argc == 2, "expected one bundle file");
    auto layers = am_carrier::read_bundle(argv[1]);
    am_carrier::require(layers.size() == 2 && layers[0].layer == 3 && layers[1].layer == 7,
                        "expected two distinct layers");
    for (const auto & layer : layers) {
        am_carrier::require(layer.kv_heads == 2 && layer.value_width == 3 &&
                            layer.positions == std::vector<int64_t>({0, 9}), "wrong native geometry/positions");
        for (float beta : layer.beta) am_carrier::require(std::abs(beta - std::log(5.f)) < 1e-5,
                                                         "wrong beta ordering/value");
        for (int head = 0; head < 2; ++head) {
            for (size_t i = 0; i < 2; ++i) for (int d = 0; d < 3; ++d) {
                const float expected = layer.layer + head*3 + d + 1;
                am_carrier::require(std::abs(layer.values[(head*2+i)*3+d] - expected) < 1e-5,
                                    "wrong C2 layer/head/position/value axis");
            }
        }
    }
    std::cout << "PASS native bundle: two layers, 2 KV heads, original endpoints, beta=log(5), C2 axes\n";
    return 0;
} catch (const std::exception & e) {
    std::cerr << e.what() << '\n'; return 1;
}
