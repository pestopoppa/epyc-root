#pragma once

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cafe3 {
// DFlash2 greedy selector scores are not probabilities. Use the maximum
// softmax mass (T=1 for greedy, sampling temperature otherwise), without
// consuming a random number or accepting a token into sampler state.
inline double selector_confidence(const float * scores, int count, double temperature) {
    if (!scores || count <= 0 || !std::isfinite(temperature) || temperature < 0) {
        throw std::invalid_argument("invalid selector confidence input");
    }
    const double scale = temperature > 0 ? temperature : 1;
    double maximum = scores[0];
    for (int i = 0; i < count; ++i) {
        if (!std::isfinite(scores[i])) throw std::invalid_argument("nonfinite selector score");
        maximum = std::max(maximum, double(scores[i]));
    }
    double sum = 0;
    for (int i = 0; i < count; ++i) sum += std::exp((double(scores[i]) - maximum) / scale);
    return 1 / sum;
}

// One callback per sequence and model implementation, on the CURRENT first
// proposal distribution. The caller starts timing before its confidence decode.
// No callback means exact legacy behavior, including no confidence validation.
template<class Params, class Impl>
int model_width(Params & dp, Impl impl, int configured_cap, double probability) {
    if (!dp.cafe3_select) return configured_cap;
    if (dp.cafe3_selected) throw std::logic_error("duplicate confidence selection");
    if (configured_cap < 0 || !std::isfinite(probability) || probability < 0 || probability > 1) {
        throw std::invalid_argument("invalid model confidence or cap");
    }
    const int cap = dp.n_max < 0 ? configured_cap : std::min(configured_cap, int(dp.n_max));
    const int width = dp.cafe3_select(impl, cap, probability);
    if (width < 0 || width > cap) throw std::invalid_argument("selected width exceeds model cap");
    dp.cafe3_selected = true;
    return width;
}
} // namespace cafe3
