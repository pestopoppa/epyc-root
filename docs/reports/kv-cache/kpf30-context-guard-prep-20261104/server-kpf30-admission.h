#pragma once

#include <cstring>

// Diagnostic-only admission. Other values retain the observer's disabled semantics.
inline bool server_kpf30_observing(const char * value) {
    return value != nullptr && std::strcmp(value, "1") == 0;
}

// No target-vs-draft identity is present in the current native observation schema.
inline bool server_kpf30_refuse_spec(const char * value, bool has_spec) {
    return server_kpf30_observing(value) && has_spec;
}
