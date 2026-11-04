#pragma once
// Source-only CAFE-4 adapter. The owner must initialize a single MTP-only
// common_speculative instance, bind its target/draft contexts, and call
// common_speculative_process() for the target batches before using this seam.
// This adapter does not perform target verification, rollback, or prove MTP.
#include "speculative.h"
#include <cstdint>

inline bool cafe4_mtp_draft(common_speculative * spec, llama_seq_id seq_id,
                            int32_t n_past, llama_token boundary,
                            const llama_tokens & prefix, int32_t width,
                            llama_tokens & draft) {
    draft.clear();
    if (!spec || seq_id < 0 || n_past < 0 || boundary < 0 || width < 2 ||
        static_cast<size_t>(n_past) != prefix.size()) return false;
    auto & p = common_speculative_get_draft_params(spec, seq_id);
    p = {};
    p.drafting = true;
    p.n_max = width;
    p.n_past = n_past;
    p.id_last = boundary;
    p.prompt = &prefix;
    p.result = &draft;
    p.temperature = 0.0f;
    p.seed = LLAMA_DEFAULT_SEED;
    common_speculative_draft(spec);
    if (draft.empty() || draft.size() > static_cast<size_t>(width)) {
        draft.clear();
        return false;
    }
    for (const auto token : draft) {
        if (token < 0) { draft.clear(); return false; }
    }
    return true;
}
