#pragma once
#include <charconv>
#include <cstring>
#include <cstdio>
#include <string>

namespace cafe4 {
struct Options {
    std::string model;
    int gpu_layers = 0;
    int width = 3;
    bool fault_injection = false;
};

inline bool integer(const char * text, int & out) {
    if (!text || !*text) return false;
    const char * end = text + std::strlen(text);
    const auto r = std::from_chars(text, end, out);
    return r.ec == std::errc{} && r.ptr == end;
}

inline bool parse(int argc, char ** argv, Options & out) {
    Options next;
    bool ngl = false, width = false;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "-ngl" || arg == "--verify-batch") {
            const bool gpu = arg == "-ngl";
            if ((gpu ? ngl : width) || ++i == argc) return false;
            int value;
            if (!integer(argv[i], value)) return false;
            if (gpu) {
                if (value < 0) return false;
                next.gpu_layers = value;
                ngl = true;
            } else {
                // Prompt <=120, verify width+1 <=64, context=512, batch=128.
                // Width >=2 is necessary for strict partial acceptance.
                if (value < 2 || value > 63) return false;
                next.width = value;
                width = true;
            }
        } else if (arg == "--fault-injection") {
            if (next.fault_injection) return false;
            next.fault_injection = true;
        } else {
            if (arg.empty() || arg[0] == '-' || !next.model.empty()) return false;
            next.model = arg;
        }
    }
    if (next.model.empty()) return false;
    out = next;
    return true;
}

// UNKNOWN cannot pass the intentional-failure control. Only a demonstrated
// divergence after the matched nonfault controls produces the expected rc1.
inline int finish(bool nonfault_ok, bool fault_detected, bool injected) {
    if (!nonfault_ok || !fault_detected) return 2;
    return injected ? 1 : 0;
}

// These are the tokens already chosen by the native path. Printing them must
// not call a sampler, substitute tokens, or change the acceptance decision.
inline void boundary_witness(int mode, int width, int boundary) {
    std::fprintf(stderr, "CAFE4_BOUNDARY mode=%d width=%d token=%d\n", mode, width, boundary);
}

template<class Tokens>
void proposal_witness(int mode, int width, const Tokens & draft) {
    std::fprintf(stderr, "CAFE4_PROPOSAL mode=%d width=%d count=%zu tokens=", mode, width, draft.size());
    for (size_t i = 0; i < draft.size(); ++i) {
        std::fprintf(stderr, "%s%d", i ? "," : "", (int)draft[i]);
    }
    std::fprintf(stderr, "\n");
}

inline void verification_witness(int mode, int width, size_t index, int proposed, int predicted) {
    std::fprintf(stderr, "CAFE4_VERIFY_TOKEN mode=%d width=%d index=%zu proposed=%d predicted=%d\n",
                 mode, width, index, proposed, predicted);
}

// Preserve UNKNOWN and report the last failed native operation before any
// contexts are destroyed. No numerical or acceptance criterion changes here.
template<class Observation>
Observation trial_failure(const Observation & o, int mode, int width, const char * stage) {
    std::fprintf(stderr, "CAFE4_TRIAL_FAILURE mode=%d width=%d stage=%s draft=%zu accepted=%d sampled=%d selected=%llu faulted=%llu\n",
                 mode, width, stage, o.draft.size(), o.accepted, o.sampled,
                 (unsigned long long)o.selected, (unsigned long long)o.faulted);
    return o;
}

inline bool control(bool ok, const char * name) {
    if (!ok) std::fprintf(stderr, "CAFE4_CONTROL_FAILURE control=%s\n", name);
    return ok;
}

template<class Tokens>
bool tokens_match(const Tokens & a, const Tokens & b, const char * name) {
    if (a == b) return true;
    size_t i = 0;
    while (i < a.size() && i < b.size() && a[i] == b[i]) ++i;
    std::fprintf(stderr, "CAFE4_CONTROL_FAILURE control=%s left_size=%zu right_size=%zu first_diff=%zu left=%d right=%d\n",
                 name, a.size(), b.size(), i,
                 i < a.size() ? (int)a[i] : -1, i < b.size() ? (int)b[i] : -1);
    return false;
}

template<class Observation>
bool matched_controls(const Observation & off, const Observation & observe, const Observation & fault) {
    bool ok = true;
    // Evaluate every predicate, even when an earlier one fails.
    ok = control(off.ok, "off-lifecycle") && ok;
    ok = control(observe.ok, "observe-lifecycle") && ok;
    ok = control(fault.ok, "fault-lifecycle") && ok;
    ok = tokens_match(off.prefix, observe.prefix, "off-observe-prefix") && ok;
    ok = tokens_match(off.prefix, fault.prefix, "off-fault-prefix") && ok;
    ok = tokens_match(off.draft, observe.draft, "off-observe-draft") && ok;
    ok = tokens_match(off.draft, fault.draft, "off-fault-draft") && ok;
    return ok;
}
} // namespace cafe4
