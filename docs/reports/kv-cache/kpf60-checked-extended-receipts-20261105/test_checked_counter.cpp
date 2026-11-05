#ifdef NDEBUG
#error "NDEBUG disables required fixture checks"
#endif
#include "checked_counter.hpp"
#include <cassert>
#include <cstdint>
#include <vector>
using namespace kpf60;

static bool unchanged(const totals & t) {
    return t.k == 11 && t.v == 13 && t.metadata == 17 && t.serialized == 19;
}

int main() {
    const totals sentinel{11, 13, 17, 19};
    const std::vector<expected_tensor> one{{{0, 0, false}, {{0, 2}}}};
    {
        // Two disjoint ranges and an independent V tensor, with explicit
        // inventory: accepting a partial inventory would hide missing reads.
        checked_counter c;
        assert(c.metadata(8));
        assert(c.tensor(0, false, 0, true, true, 8, 64, 0, 2, 0, 16));
        assert(c.tensor(0, false, 0, true, true, 8, 64, 5, 6, 40, 8));
        assert(c.tensor(0, true, 0, true, true, 4, 32, 0, 2, 0, 8));
        const std::vector<expected_tensor> expected{
            {{0, 0, false}, {{0, 2}, {5, 6}}}, {{0, 0, true}, {{0, 2}}}};
        totals out = sentinel;
        assert(c.finish(expected, out));
        assert(out.k == 24 && out.v == 8 && out.metadata == 8 && out.serialized == 40);
        out = sentinel;
        assert(!c.finish({expected[0]}, out) && unchanged(out));
        out = sentinel;
        assert(!c.finish({expected[0], expected[0]}, out) && unchanged(out));
        out = sentinel;
        auto wrong = expected; wrong[0].cells[1] = {4, 6};
        assert(!c.finish(wrong, out) && unchanged(out));
    }
    {
        // A refusal is sticky and every output field remains untouched.
        checked_counter c; totals out = sentinel;
        assert(c.metadata(UINT64_MAX));
        assert(!c.metadata(1));
        assert(!c.tensor(0, false, 0, true, true, 8, 64, 0, 2, 0, 16));
        assert(!c.finish(one, out) && unchanged(out));
    }
    {
        // Individually representable metadata and K payload must not wrap at
        // the final serialized-total addition.
        checked_counter c; totals out = sentinel;
        assert(c.metadata(UINT64_MAX));
        assert(c.tensor(0, false, 0, true, true, 8, 64, 0, 2, 0, 16));
        assert(!c.finish(one, out) && unchanged(out));
    }
    {
        // The multiplication fits, but offset + length overflows.
        checked_counter c; totals out = sentinel;
        assert(!c.tensor(0, false, 0, true, true, 2, UINT64_MAX,
                         UINT64_MAX / 2, UINT64_MAX / 2 + 1, UINT64_MAX - 1, 2));
        assert(!c.finish(one, out) && unchanged(out));
    }
    {
        // Individually valid disjoint streams overflow the K subtotal.
        checked_counter c; totals out = sentinel;
        assert(c.tensor(0, false, 0, true, true, 2, UINT64_MAX,
                        0, UINT64_MAX / 2, 0, UINT64_MAX - 1));
        assert(!c.tensor(0, false, 1, true, true, 2, 2, 0, 1, 0, 2));
        assert(!c.finish(one, out) && unchanged(out));
    }
    {
        checked_counter c; totals out = sentinel;
        assert(!c.tensor(0, false, 0, true, true, 8, 15, 0, 2, 0, 16));
        assert(!c.finish(one, out) && unchanged(out));
    }
    {
        checked_counter c; totals out = sentinel;
        assert(!c.tensor(0, false, 0, true, true, 3, 64, 0, 1, 0, 3));
        assert(!c.finish(one, out) && unchanged(out));
    }
    {
        checked_counter c; totals out = sentinel;
        assert(!c.tensor(0, false, 0, false, true, 8, 64, 0, 2, 0, 16));
        assert(!c.finish(one, out) && unchanged(out));
    }
    {
        checked_counter c; totals out = sentinel;
        assert(c.tensor(0, false, 0, true, true, 8, 64, 0, 2, 0, 16));
        // A later event for this tensor cannot silently change its geometry.
        assert(!c.tensor(0, false, 0, true, true, 4, 64, 3, 4, 12, 4));
        assert(!c.finish(one, out) && unchanged(out));
    }
}
