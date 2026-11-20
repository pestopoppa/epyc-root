#pragma once
#include <cmath>
#include <cstddef>
#include <stdexcept>

// Producer-side full-vocabulary reduction. No top-k approximation or sampled
// coordinates: every logit contributes, including ties (lowest ID wins).
struct precision_witness {
    std::size_t count = 0, verify_argmax = 0;
    double max_abs = 0, sum_squared = 0;
};

inline precision_witness precision_compare(const float * verify, const float * serial, std::size_t n) {
    if (!verify || !serial || !n) throw std::runtime_error("empty logits");
    precision_witness w;
    w.count = n;
    double correction = 0;
    for (std::size_t i = 0; i < n; ++i) {
        if (!std::isfinite(verify[i]) || !std::isfinite(serial[i]))
            throw std::runtime_error("nonfinite logits");
        const double d = double(verify[i]) - double(serial[i]);
        w.max_abs = std::fmax(w.max_abs, std::fabs(d));
        const double term = d * d - correction;
        const double sum = w.sum_squared + term;
        correction = (sum - w.sum_squared) - term;
        w.sum_squared = sum;
        if (verify[i] > verify[w.verify_argmax]) w.verify_argmax = i;
    }
    if (!std::isfinite(w.sum_squared)) throw std::runtime_error("divergence overflow");
    return w;
}
