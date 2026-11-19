#!/usr/bin/env python3
"""Pure source port for the frozen v10 model-confidence boundary.

The owning row builder applies these transformations to a fresh experimental
worktree. This module never edits the production tree or builds/runs models.
"""
PRODUCTION = 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115'


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f'expected one native anchor: {old!r}')
    return source.replace(old, new)


def header(source):
    source = replace_once(source, '#include "common.h"', '#include "common.h"\n#include <functional>')
    return replace_once(source, '    uint32_t seed = LLAMA_DEFAULT_SEED;', '''    uint32_t seed = LLAMA_DEFAULT_SEED;

    // Experimental CAFE3 only. Install at request/round setup, after starting
    // the round timer. Empty preserves legacy behavior. Selection of zero
    // terminates this chain, rather than falling through to another drafter.
    std::function<int(common_speculative_type, int, double)> cafe3_select = {};
    bool cafe3_selected = false;''')


def implementation(source):
    source = replace_once(source, '#include "speculative.h"',
                          '#include "speculative.h"\n#include "model_boundary.h"')
    # Restrict transforms to their implementation: never touch other drafters.
    dstart = source.index('struct common_speculative_impl_draft_dflash :')
    mstart = source.index('struct common_speculative_impl_draft_mtp :')
    mend = source.index('struct common_speculative_impl_ngram_simple :')
    before, dflash, mtp, after = source[:dstart], source[dstart:mstart], source[mstart:mend], source[mend:]
    mtp = replace_once(mtp, '        int i = 0;',
                       '        std::vector<int> cafe3_width(n_seq, params.n_max);\n        int i = 0;')
    mtp = replace_once(mtp, '                // add drafted token for each sequence', '''                auto & cafe3_dp = dparams[seq_id];
                if (i == 0 && cafe3_dp.cafe3_select) {
                    cafe3_width[seq_id] = cafe3::model_width(cafe3_dp, type, params.n_max, cur_p->data[0].p);
                    if (cafe3_width[seq_id] == 0) {
                        drafting[seq_id] = false;
                        n_drafting--;
                        continue;
                    }
                }

                // add drafted token for each sequence''')
    mtp = replace_once(mtp, 'if (params.n_max <= (int) result.size())',
                       'if (cafe3_width[seq_id] <= (int) result.size())')
    # DFlash is block diffusion: retain the original full noise-block decode.
    # Reading fewer outputs must never be presented as reduced draft FLOPs.
    dflash = replace_once(dflash, '            if (is_dflash2) {\n                GGML_ASSERT',
                          '            int cafe3_width = params.n_max;\n\n            if (is_dflash2) {\n                GGML_ASSERT')
    dflash = replace_once(dflash, '                if (selector_reset[seq_id]) {', '''                if (dp.cafe3_select) {
                    const float * scores = lattice + (size_t) (beg + 1) * n_embd_dec + selector_top_k;
                    const double confidence = cafe3::selector_confidence(scores, selector_top_k, dp.temperature);
                    cafe3_width = cafe3::model_width(dp, type, params.n_max, confidence);
                    if (cafe3_width == 0) continue; // no RNG seed/draw or sampler acceptance
                }

                if (selector_reset[seq_id]) {''')
    loop = 'for (int32_t i = 1; i < n_block_tokens; ++i) {'
    if dflash.count(loop) != 2:
        raise ValueError('expected DFlash and DFlash2 output loops')
    dflash = dflash.replace(loop, 'for (int32_t i = 1; i < n_block_tokens && i <= cafe3_width; ++i) {')
    # Only the generic DFlash loop (DSpark remains excluded).
    anchor = '                    const llama_token id = cur_p->data[0].id;'
    pos = dflash.index('// greedily read the predicted block')
    tail = replace_once(dflash[pos:], anchor, '''                    if (i == 1 && dp.cafe3_select) {
                        cafe3_width = cafe3::model_width(dp, type, params.n_max, cur_p->data[0].p);
                        if (cafe3_width == 0) break;
                    }

''' + anchor)
    dflash = dflash[:pos] + tail
    source = before + dflash + mtp + after
    return replace_once(source, '            // a new draft has been sampled', '''            // A selected model round owns this sequence even if its width is
            // zero or confidence truncation produced no tokens. No fallback
            // may silently replace the selected implementation/timing sample.
            if (dp.drafting && dp.cafe3_selected) {
                spec->impl_last[seq_id] = impl.get();
                if (result.empty()) dp.drafting = false;
            }

            // a new draft has been sampled''')
