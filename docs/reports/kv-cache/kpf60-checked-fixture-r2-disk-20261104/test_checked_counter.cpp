#ifdef NDEBUG
#error "NDEBUG disables required fixture checks"
#endif
#include "checked_counter.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using namespace kpf60;
int main() {
    totals t{}; checked_counter c;
    assert(c.metadata(8));
    assert(c.tensor(0, false, 0, true, true, 8, 64, 1, 3, 8, 16));
    assert(c.tensor(0, true, 0, true, true, 4, 32, 1, 3, 4, 8));
    const std::vector<expected_tensor> expected{{{0,0,false},{{1,3}}},{{0,0,true},{{1,3}}}};
    assert(c.finish(expected, t) && t.k == 16 && t.v == 8 && t.metadata == 8 && t.serialized == 32);
    checked_counter overflow; t = {7,7,7,7};
    assert(!overflow.tensor(0, false, 0, true, true, 8, UINT64_MAX, UINT64_MAX / 8, UINT64_MAX, 0, 0));
    assert(!overflow.finish(expected, t) && t.k == 7);
    checked_counter overlap;
    assert(overlap.tensor(0, false, 0, true, true, 8, 64, 0, 2, 0, 16));
    assert(!overlap.tensor(0, false, 0, true, true, 8, 64, 1, 3, 8, 16));
    assert(!overlap.finish(expected, t));
    checked_counter unsupported;
    assert(!unsupported.tensor(0, true, 0, true, false, 8, 64, 0, 1, 0, 8));
    assert(!unsupported.finish(expected, t));
    checked_counter mismatch;
    assert(!mismatch.tensor(0, false, 0, true, true, 8, 64, 0, 2, 0, 15));
    assert(!mismatch.finish(expected, t));
}
