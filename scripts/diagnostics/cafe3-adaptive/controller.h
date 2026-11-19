#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

// Model-free candidate policy. One instance per request/sequence and draft impl.
// No token, sampler, KV, server, or production integration is performed here.
namespace cafe3 {
enum class implementation { mtp, dflash, dflash2, other };

inline bool enabled(const char * value) {
    return value && std::string(value) == "1";
}

class controller {
public:
    struct choice {
        int width;
        bool adaptive;
        bool probe;
        std::uint64_t ticket;
    };

    explicit controller(int max_width, bool on = false, double alpha = 0.2,
                        unsigned max_gap = 64)
        : max_(checked_width(max_width)), on_(on), alpha_(alpha), gap_(max_gap),
          costs_(max_ + 1, 0), seen_(max_ + 1, false), last_(max_ + 1, 0),
          acceptance_(max_, 0) {
        if (!std::isfinite(alpha) || alpha <= 0 || alpha > 1 || max_gap < unsigned(max_ + 1)) {
            throw std::invalid_argument("invalid EMA or exploration gap");
        }
        for (int i = 0; i < max_; ++i) acceptance_[i] = std::pow(0.5, i + 1);
    }

    choice select(implementation impl, int cap, int static_width, double p0) {
        if (pending_) throw std::logic_error("unobserved round");
        if (cap < 0 || static_width < 0) throw std::invalid_argument("negative width");
        if (!on_ || impl == implementation::other) {
            return {std::min(cap, static_width), false, false, 0};
        }
        if (!std::isfinite(p0) || p0 < 0 || p0 > 1) {
            throw std::invalid_argument("invalid position-zero probability");
        }
        const int limit = std::min(cap, max_);
        int selected = -1;
        bool probe = false;
        // A cost prediction never vetoes an unmeasured width.
        for (int w = 0; w <= limit; ++w) {
            if (!seen_[w]) { selected = w; probe = true; break; }
        }
        // Every eligible width is refreshed; zero cannot become absorbing.
        if (selected < 0) {
            for (int w = 0; w <= limit; ++w) {
                if (round_ - last_[w] >= gap_ &&
                    (selected < 0 || last_[w] < last_[selected])) {
                    selected = w;
                    probe = true;
                }
            }
        }
        if (selected < 0) {
            selected = 0;
            for (int w = 1; w <= limit; ++w) {
                if (score(w, p0) > score(selected, p0)) selected = w;
            }
            if (selected == 0 && limit > 0 && round_ >= next_zero_probe_) {
                selected = 1 + (probe_cursor_++ % limit);
                probe = true;
                zero_probe_ = true;
            }
        }
        pending_ = true;
        p0_ = p0;
        current_ = {selected, true, probe, ++ticket_};
        return current_;
    }

    // Width is the ACTUAL number drafted/verified, including width zero's
    // target-only round. Timing must cover draft + verify + accept/rollback.
    // Capped/shortened drafts must be cancelled and selected again, not relabelled.
    void observe(choice c, int accepted, double round_us) {
        if (!pending_ || !c.adaptive || c.ticket != current_.ticket ||
            c.width != current_.width || c.probe != current_.probe) {
            throw std::logic_error("feedback does not match selection");
        }
        if (accepted < 0 || accepted > c.width || !std::isfinite(round_us) || round_us <= 0) {
            throw std::invalid_argument("invalid round observation");
        }
        int w = c.width;
        costs_[w] = seen_[w] ? ema(costs_[w], round_us) : round_us;
        seen_[w] = true;
        last_[w] = ++round_;
        // Prefix-survival probabilities: rejected suffixes count as zero.
        // Positions outside the actual draft are censored and never updated.
        for (int i = 0; i < w; ++i) acceptance_[i] = ema(acceptance_[i], i < accepted ? 1 : 0);
        if (zero_probe_) {
            zero_backoff_ = score(w, p0_) > score(0, p0_) ? 1 :
                std::min(gap_, zero_backoff_ * 2);
            next_zero_probe_ = round_ + zero_backoff_;
        }
        pending_ = false;
        zero_probe_ = false;
    }

    // Failed decode, shortened proposal or cancelled request supplies no sample.
    void cancel(choice c) {
        if (!pending_ || c.ticket != current_.ticket || c.width != current_.width) {
            throw std::logic_error("cancel does not match selection");
        }
        pending_ = false;
        zero_probe_ = false;
    }

    double acceptance(int position) const { return acceptance_.at(position); }
    double cost(int width) const { return costs_.at(width); }

private:
    static int checked_width(int n) {
        if (n < 1 || n > 64) throw std::invalid_argument("width outside 1..64");
        return n;
    }
    double ema(double old, double sample) const { return old + alpha_ * (sample - old); }
    double score(int w, double p0) const {
        double tokens = 1; // One target correction/bonus per completed round.
        double prefix = p0;
        for (int i = 0; i < w; ++i) {
            if (i > 0) {
                prefix *= acceptance_[i - 1] > 0 ?
                    std::clamp(acceptance_[i] / acceptance_[i - 1], 0.0, 1.0) : 0;
            }
            tokens += prefix;
        }
        return tokens / costs_[w];
    }
    int max_;
    bool on_;
    double alpha_;
    unsigned gap_;
    std::vector<double> costs_;
    std::vector<bool> seen_;
    std::vector<std::uint64_t> last_;
    std::vector<double> acceptance_;
    std::uint64_t round_ = 0, ticket_ = 0, next_zero_probe_ = 0;
    unsigned zero_backoff_ = 1, probe_cursor_ = 0;
    bool pending_ = false, zero_probe_ = false;
    double p0_ = 0;
    choice current_{};
};
} // namespace cafe3
