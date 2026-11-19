#include "kpf17-mutation-oracle.h"
#include <cassert>
#include <string>

int main() {
    using R = kpf17_mutation_result;
    auto check = [](bool valid, bool witness, bool reset, bool copy, bool set, R stale,
                    R expected, bool expected_detected, const std::string & want) {
        std::string calls;
        auto result = kpf17_mutation_oracle(
            [&] { calls += 'V'; return valid; },
            [&] { calls += 'W'; return witness; },
            [&] { calls += 'R'; return reset; },
            [&] { calls += 'C'; return copy; },
            [&] { calls += 'S'; return set; },
            [&] { calls += 'D'; return stale; });
        assert(result == expected && calls == want);
        assert(kpf17_mutation_detected(result) == expected_detected);
        assert(std::string(kpf17_mutation_result_name(result)) != "invalid_unknown");
    };
    check(false,true,true,true,true,R::stale_diverged,R::valid_restore_failed,false,"V");
    check(true,false,true,true,true,R::stale_diverged,R::valid_witness_failed,false,"VW");
    check(true,true,false,true,true,R::stale_diverged,R::reset_failed,false,"VWR");
    check(true,true,true,false,true,R::stale_diverged,R::stale_attention_copy_failed,false,"VWRC");
    check(true,true,true,true,false,R::stale_diverged,R::stale_state_set_rejected,true,"VWRCS");
    check(true,true,true,true,true,R::stale_decode_failed,R::stale_decode_failed,true,"VWRCSD");
    check(true,true,true,true,true,R::stale_nonfinite,R::stale_nonfinite,false,"VWRCSD");
    check(true,true,true,true,true,R::stale_within_floor,R::stale_within_floor,false,"VWRCSD");
    check(true,true,true,true,true,R::stale_diverged,R::stale_diverged,true,"VWRCSD");
}
