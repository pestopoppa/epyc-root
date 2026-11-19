"""Fail-closed v10 server completion port; no production edits or model runs.

Request setup must begin an assigned lifecycle and attach it to cafe3_rounds.
Selection and durable writer installation are intentionally separate seams.
"""
from native_port import replace_once


def server_context(source):
    source = replace_once(source, '#include "speculative.h"',
                          '#include "speculative.h"\n#include "round_lifecycle.h"')
    source = replace_once(source, '    common_speculative * spec;', '''    common_speculative * spec;

    // Empty preserves legacy behavior. Request setup must call begin(id, ...)
    // before attaching; release detaches so recycled slots cannot train it.
    std::shared_ptr<cafe3::round_lifecycle> cafe3_rounds;
    void cafe3_cancel() {
        if (cafe3_rounds) cafe3_rounds->cancel(id);
    }
    void cafe3_finish(int width, int accepted) {
        if (cafe3_rounds) cafe3_rounds->finish(id, width, accepted);
    }
    void cafe3_release() {
        if (cafe3_rounds) {
            cafe3_rounds->release(id);
            cafe3_rounds.reset();
        }
    }''')
    source = replace_once(source, '    void release() {\n',
                          '    void release() {\n        cafe3_release();\n')
    source = replace_once(source, '                common_context_seq_rm (ctx_tgt, slot.id, n_keep',
                          '                slot.cafe3_cancel(); // context shift invalidates timing\n                common_context_seq_rm (ctx_tgt, slot.id, n_keep')
    # Scope to decode(): other return-code handling has different slot ownership.
    start = source.index('    bool decode(int32_t & n_batch,')
    end = source.index('    // at temp 0', start)
    decode = source[start:end]
    decode = replace_once(decode, '        if (ret != 0) {', '''        if (ret != 0) {
            // Shared-batch failure/retry invalidates all pending round timings.
            for (auto & slot : slots) slot.cafe3_cancel();''')
    decode = replace_once(decode, '            throw std::runtime_error("failed to process speculative batch");',
                          '            for (auto & slot : slots) slot.cafe3_cancel();\n            throw std::runtime_error("failed to process speculative batch");')
    source = source[:start] + decode + source[end:]
    source = replace_once(source, '            common_sampler_accept(slot.smpl.get(), id, true);\n\n            // here',
                          '            common_sampler_accept(slot.smpl.get(), id, true);\n\n            slot.cafe3_finish(0, 0); // includes confidence + target decode\n\n            // here')
    source = replace_once(source, '                        // partial acceptance is not supported by the context -> truncate the draft and restore the state',
                          '                        slot.cafe3_cancel(); // replay is not the selected-width trial\n\n                        // partial acceptance is not supported by the context -> truncate the draft and restore the state')
    anchor = '''            common_context_seq_rm(slot.ctx_tgt, slot.id, slot.prompt.tokens.pos_next(), -1);
            if (slot.ctx_dft) {
                common_context_seq_rm(slot.ctx_dft, slot.id, slot.prompt.tokens.pos_next(), -1);
            }

            for (size_t i = 0; i < ids.size(); ++i) {'''
    source = replace_once(source, anchor, anchor.replace('\n\n            for',
                          '\n\n            slot.cafe3_finish((int) n_draft, (int) ids.size() - 1);\n\n            for'))
    return source
