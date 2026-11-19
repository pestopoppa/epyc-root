#include "controller.h"
#include <cassert>
#include <limits>
#include <iostream>

using cafe3::controller;
using cafe3::implementation;
constexpr auto mtp = implementation::mtp;
template<class E, class F> void rejects(F f) {
    bool caught = false;
    try { f(); } catch (const E &) { caught = true; }
    assert(caught);
}

int main() {
    // Default-off, strict environment opt-in, and excluded implementations.
    assert(!cafe3::enabled(nullptr) && !cafe3::enabled("0") && !cafe3::enabled("true"));
    assert(cafe3::enabled("1"));
    controller off(3);
    assert(!off.select(mtp, 2, 3, 0.9).adaptive);
    assert(off.select(mtp, 2, 3, 0.9).width == 2);
    controller excluded(3, true);
    assert(!excluded.select(implementation::other, 3, 2, 0.9).adaptive);

    // Probe every legal width before rejecting even obviously costly drafts.
    for (auto impl : {mtp, implementation::dflash, implementation::dflash2}) {
        controller c(3, true);
        for (int w = 0; w <= 3; ++w) {
            auto x = c.select(impl, 3, 3, 0.1);
            assert(x.width == w && x.probe);
            c.observe(x, 0, 10 + w * 100);
        }
    }

    // Round time EMA, censored positions, and position-prefix EMA.
    controller c(3, true, 0.5);
    auto x = c.select(mtp, 1, 1, 0.5); c.observe(x, 0, 10);
    x = c.select(mtp, 1, 1, 0.5); c.observe(x, 1, 20);
    assert(c.acceptance(0) == 0.75 && c.acceptance(1) == 0.25);
    x = c.select(mtp, 1, 1, 1); c.cancel(x);
    assert(c.cost(1) == 20);
    x = c.select(mtp, 0, 1, 0.5); c.observe(x, 0, 30);
    assert(c.cost(0) == 20); // 0.5 * old 10 + 0.5 * new 30

    // Zero retry delay grows after failed probes but remains bounded.
    controller backoff(1, true, 1, 16);
    int previous = -1, first_delay = -1, largest_delay = 0;
    for (int n = 0; n < 100; ++n) {
        x = backoff.select(mtp, 1, 1, 0.1);
        if (x.width == 1) {
            if (previous >= 0) {
                int delay = n - previous;
                if (first_delay < 0) first_delay = delay;
                largest_delay = std::max(largest_delay, delay);
                assert(delay <= 17);
            }
            previous = n;
        }
        backoff.observe(x, 0, x.width ? 1000 : 10);
    }
    assert(largest_delay > first_delay);

    // High confidence prefers a productive draft; p0=0 prefers target-only.
    controller confidence(1, true, 1);
    x = confidence.select(mtp, 1, 1, 1); confidence.observe(x, 0, 10);
    x = confidence.select(mtp, 1, 1, 1); confidence.observe(x, 1, 15);
    x = confidence.select(mtp, 1, 1, 1); assert(x.width == 1 && !x.probe);
    confidence.observe(x, 1, 15);
    x = confidence.select(mtp, 1, 1, 0); // zero re-probe can intervene once
    confidence.observe(x, x.width, x.width ? 15 : 10);
    x = confidence.select(mtp, 1, 1, 0); assert(x.width == 0);
    confidence.observe(x, 0, 20); assert(confidence.cost(0) == 20);

    // Absorbing-state adversary: all positive widths fail, then all improve.
    // Every width must be retried in bounded rounds and policy must recover.
    controller recovery(3, true, 1, 16);
    int counts[4] = {};
    for (int n = 0; n < 100; ++n) {
        x = recovery.select(mtp, 3, 3, 0.9); ++counts[x.width];
        recovery.observe(x, 0, x.width ? 1000 : 10);
    }
    for (int w = 0; w <= 3; ++w) assert(counts[w] > 1);
    bool recovered = false;
    for (int n = 0; n < 40; ++n) {
        x = recovery.select(mtp, 3, 3, 1);
        if (x.width > 0 && !x.probe) recovered = true;
        recovery.observe(x, x.width, 10);
    }
    assert(recovered);

    // Dynamic cap never expands draft width or labels unseen positions.
    controller cap(3, true);
    for (int n = 0; n < 100; ++n) {
        x = cap.select(mtp, 0, 3, 1); assert(x.width == 0);
        cap.observe(x, 0, 10);
    }
    x = cap.select(mtp, 3, 3, 1); assert(x.width == 1 && x.probe); cap.cancel(x);

    // Invalid/cross-round feedback leaves a pending choice retryable.
    controller valid(2, true);
    x = valid.select(mtp, 2, 2, 0.5);
    rejects<std::logic_error>([&]{ valid.select(mtp, 2, 2, 0.5); });
    rejects<std::invalid_argument>([&]{ valid.observe(x, 1, 10); });
    rejects<std::invalid_argument>([&]{ valid.observe(x, 0, 0); });
    rejects<std::invalid_argument>([&]{ valid.observe(x, 0, std::numeric_limits<double>::quiet_NaN()); });
    auto wrong = x; ++wrong.ticket;
    rejects<std::logic_error>([&]{ valid.observe(wrong, 0, 10); });
    valid.observe(x, 0, 10);
    rejects<std::logic_error>([&]{ valid.observe(x, 0, 10); });
    rejects<std::invalid_argument>([&]{ valid.select(mtp, 2, 2, 1.1); });
    rejects<std::invalid_argument>([]{ controller bad(-1); });
    rejects<std::invalid_argument>([]{ controller bad(3, true, 0); });
    rejects<std::invalid_argument>([]{ controller bad(3, true, 0.2, 2); });
    std::cout << "PASS: opt-in, implementation scope, unseen probes, EMA/censoring, confidence, zero recovery, caps, feedback\n";
}
