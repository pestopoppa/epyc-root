#pragma once
#include <charconv>
#include <cstring>
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
} // namespace cafe4
