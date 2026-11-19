#include "round_lifecycle.h"
#include <cassert>
#include <iostream>
#include <limits>

using cafe3::implementation;
constexpr auto mtp = implementation::mtp;
template<class E, class F> void rejects(F f) {
    bool caught = false;
    try { f(); } catch (const E &) { caught = true; }
    assert(caught);
}

int main() {
    double now = 100;
    bool fail_write = false;
    bool fail_clock = false;
    std::vector<cafe3::round_observation> records;
    cafe3::round_lifecycle rounds(3, [&] {
        if (fail_clock) throw std::runtime_error("clock failure");
        return now;
    }, [&](const auto & r) {
        if (fail_write) throw std::runtime_error("disk failure");
        records.push_back(r);
    });
    rejects<std::logic_error>([&] { rounds.select(0, mtp, 3, 3, .7); });
    rounds.begin(0, 10, "1");
    rounds.begin(1, 11, "1");
    auto c = rounds.select(0, mtp, 3, 3, .7);
    assert(c.width == 0);
    rejects<std::logic_error>([&] { rounds.select(0, mtp, 3, 3, .7); });
    now = 105;
    assert(rounds.select(1, mtp, 3, 3, .2).width == 0);
    now = 120;
    assert(rounds.finish(1, 0, 0));
    now = 130;
    assert(rounds.finish(0, 0, 0));
    assert(records.size() == 2);
    assert(records[0].sequence == 1 && records[0].elapsed_us == 15);
    assert(records[1].request == 10 && records[1].elapsed_us == 30);
    assert(records[1].position_zero_probability == .7);
    assert(!rounds.finish(0, 0, 0)); // duplicate completion cannot train

    // Cancellation, shortening, invalid counts and failed decode do not train.
    assert(rounds.select(0, mtp, 3, 3, .7).width == 1);
    now += 10;
    assert(!rounds.finish(0, 0, 0));
    assert(rounds.select(0, mtp, 3, 3, .7).width == 1);
    rejects<std::invalid_argument>([&] { rounds.finish(0, 1, 2); });
    rounds.cancel(0);
    assert(rounds.select(0, mtp, 3, 3, .7).width == 1);
    now += 10;
    assert(rounds.finish(0, 1, 1));
    assert(records.back().round == 2 && records.back().accepted == 1);

    // Separate model implementation has separate width/cost history.
    assert(rounds.select(0, implementation::dflash2, 3, 3, .3).width == 0);
    now += 10;
    rounds.finish(0, 0, 0);
    assert(records.back().impl == implementation::dflash2);
    assert(rounds.select(0, mtp, 3, 3, .7).width == 2);
    rounds.cancel(0);

    // Writer failure cancels without consuming the next mandatory width probe.
    fail_write = true;
    rounds.select(0, mtp, 3, 3, .7);
    now += 10;
    rejects<std::runtime_error>([&] { rounds.finish(0, 2, 1); });
    fail_write = false;
    assert(rounds.select(0, mtp, 3, 3, .7).width == 2);
    rounds.cancel(0);
    assert(records.size() == 4);

    // Clock errors neither train nor strand a ticket.
    rounds.select(0, mtp, 3, 3, .7);
    rejects<std::invalid_argument>([&] { rounds.finish(0, 2, 1); });
    now = std::numeric_limits<double>::quiet_NaN();
    rejects<std::invalid_argument>([&] { rounds.select(0, mtp, 3, 3, .7); });
    now = 200;
    assert(rounds.select(0, mtp, 3, 3, .7).width == 2);
    fail_clock = true;
    rejects<std::runtime_error>([&] { rounds.finish(0, 2, 1); });
    fail_clock = false;
    assert(rounds.select(0, mtp, 3, 3, .7).width == 2);

    // Reassignment cancels old work, resets policy and samples env only once.
    rounds.begin(0, 12, "1");
    assert(rounds.select(0, mtp, 3, 3, .7).width == 0);
    rounds.cancel(0);
    rejects<std::logic_error>([&] { rounds.begin(0, 12, "1"); });
    rounds.begin(0, 13, nullptr);
    now = std::numeric_limits<double>::quiet_NaN();
    assert(!rounds.select(0, mtp, 2, 3, .7).adaptive);
    assert(!rounds.finish(0, 2, 1));
    rounds.begin(0, 14, "1");
    assert(!rounds.select(0, implementation::other, 2, 3, .7).adaptive);
    assert(!rounds.finish(0, 2, 1));
    rounds.release(0);
    rejects<std::logic_error>([&] { rounds.finish(0, 0, 0); });
    now = 300;
    rounds.begin(0, 10, "1"); // recycled id gets a distinct request epoch
    rounds.select(0, mtp, 3, 3, .7);
    now += 10;
    rounds.finish(0, 0, 0);
    assert(records.back().request_epoch != records[1].request_epoch);
    // A native confidence forward pass is part of width-zero round cost.
    rounds.begin(2, 20, "1");
    now = 400;
    assert(rounds.prepare(2, mtp));
    rejects<std::logic_error>([&] { rounds.prepare(2, mtp); });
    rejects<std::logic_error>([&] { rounds.select(2, implementation::dflash, 3, 3, .7); });
    now = 450; // decoder produces current confidence only now
    assert(rounds.select(2, mtp, 3, 3, .7).width == 0);
    now = 460;
    assert(rounds.finish(2, 0, 0));
    assert(records.back().elapsed_us == 60); // not merely the final 10 us
    rounds.prepare(2, mtp);
    rounds.cancel(2); // confidence decode failed before selection
    assert(rounds.prepare(2, mtp));
    rounds.cancel(2);
    rounds.begin(3, 30, nullptr);
    now = std::nan("");
    assert(!rounds.prepare(3, mtp)); // off never reads instrumentation clock
    assert(!rounds.prepare(2, implementation::other));
    std::cout << "PASS round lifecycle: isolation, zero rounds, cancellation, write failures, clocks, reset\n";
}
