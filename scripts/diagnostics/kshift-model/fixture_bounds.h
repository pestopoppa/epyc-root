#pragma once

#include <cstddef>

// The harness skips a corpus header before slicing prefix and probe tokens.
// Subtract from the available size instead of adding signed user inputs.
inline bool kshift_fixture_fits(std::size_t available, int prefix, int probe) {
    constexpr std::size_t skip = 200;
    if (prefix <= 0 || probe <= 0 || available < skip) {
        return false;
    }
    available -= skip;
    if (static_cast<std::size_t>(prefix) > available) {
        return false;
    }
    return static_cast<std::size_t>(probe) <= available - static_cast<std::size_t>(prefix);
}
