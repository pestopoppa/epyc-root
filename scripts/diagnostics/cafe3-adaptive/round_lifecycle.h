#pragma once

#include "controller.h"
#include <functional>
#include <map>
#include <memory>

namespace cafe3 {

// Native callers supply a monotonic clock and a durable observation writer.
// No clock, environment, token, sampler or KV operation is hidden in this layer.
struct round_observation {
    std::uint64_t request, request_epoch, round, ticket;
    int sequence;
    implementation impl;
    int selected_width, actual_width, accepted;
    double position_zero_probability, elapsed_us;
    bool probe;
};

class round_lifecycle {
public:
    using clock = std::function<double()>;
    using writer = std::function<void(const round_observation &)>;

    round_lifecycle(int max_width, clock now, writer write)
        : max_(max_width), now_(std::move(now)), write_(std::move(write)) {
        // Validate construction even before any request arrives.
        controller check(max_);
        if (!now_ || !write_) throw std::invalid_argument("clock and writer required");
    }

    // Invoke at request assignment, not prompt-cache reuse or each decode step.
    // A monotonic epoch disambiguates recycled caller request ids, without
    // retaining every finished request forever. Environment is sampled by the
    // caller here, once, using getenv("LLAMA_CAFE3_ADAPTIVE").
    void begin(int sequence, std::uint64_t request, const char * env_value) {
        if (sequence < 0) throw std::invalid_argument("negative sequence");
        auto old = sequences_.find(sequence);
        if (old != sequences_.end() && old->second->request == request) {
            throw std::logic_error("request already assigned");
        }
        auto fresh = std::make_unique<sequence_state>();
        fresh->request = request;
        fresh->epoch = ++epoch_;
        fresh->on = enabled(env_value);
        // Reassignment discards any cancelled/failed round without observing it.
        sequences_[sequence] = std::move(fresh);
    }

    controller::choice select(int sequence, implementation impl, int cap,
                              int static_width, double p0) {
        auto & s = state(sequence);
        if (s.active) throw std::logic_error("round already active");
        auto & policy = s.policies[impl];
        if (!policy) policy = std::make_unique<controller>(max_, s.on);
        auto c = policy->select(impl, cap, static_width, p0);
        if (c.adaptive) {
            // Off/excluded rounds never touch the instrumentation clock.
            double start;
            try {
                start = now_();
                if (!std::isfinite(start)) throw std::invalid_argument("invalid start clock");
            } catch (...) {
                policy->cancel(c);
                throw;
            }
            s.active = true;
            s.impl = impl;
            s.choice = c;
            s.start = start;
            s.p0 = p0;
        }
        return c;
    }

    // Invoke after target verification AND draft/target acceptance + KV rollback.
    // Width zero uses this same hook after its target-only decode, with (0,0).
    // Shortened proposals cancel the sample; they cannot train another width.
    bool finish(int sequence, int actual_width, int accepted) {
        auto & s = state(sequence);
        if (!s.active) return false; // off/excluded/no pending round
        if (actual_width < 0 || accepted < 0 || accepted > actual_width) {
            throw std::invalid_argument("invalid actual round counts");
        }
        if (actual_width != s.choice.width) {
            cancel(sequence);
            return false;
        }
        double elapsed;
        try {
            elapsed = now_() - s.start;
            if (!std::isfinite(elapsed) || elapsed <= 0) {
                throw std::invalid_argument("nonpositive round time");
            }
        } catch (...) {
            cancel(sequence);
            throw;
        }
        const round_observation observation{
            s.request, s.epoch, s.completed + 1, s.choice.ticket, sequence, s.impl,
            s.choice.width, actual_width, accepted, s.p0, elapsed, s.choice.probe};
        // Persistence precedes policy mutation. A failed writer cancels the
        // round and propagates failure; it never silently trains from lost data.
        try {
            write_(observation);
        } catch (...) {
            cancel(sequence);
            throw;
        }
        s.policies.at(s.impl)->observe(s.choice, accepted, elapsed);
        s.active = false;
        ++s.completed;
        return true;
    }

    // Decode error, request cancellation, context shift or partial-draft replay.
    void cancel(int sequence) {
        auto & s = state(sequence);
        if (!s.active) return;
        s.policies.at(s.impl)->cancel(s.choice);
        s.active = false;
    }

    void release(int sequence) {
        cancel(sequence);
        sequences_.erase(sequence);
    }

private:
    struct sequence_state {
        std::uint64_t request = 0, epoch = 0, completed = 0;
        bool on = false, active = false;
        implementation impl = implementation::other;
        controller::choice choice{};
        double start = 0, p0 = 0;
        std::map<implementation, std::unique_ptr<controller>> policies;
    };
    sequence_state & state(int sequence) {
        auto it = sequences_.find(sequence);
        if (it == sequences_.end()) throw std::logic_error("sequence has no request");
        return *it->second;
    }
    int max_;
    clock now_;
    writer write_;
    std::map<int, std::unique_ptr<sequence_state>> sequences_;
    std::uint64_t epoch_ = 0;
};
} // namespace cafe3
