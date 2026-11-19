"""Fail-closed v10 server completion port; no production edits or model runs.

Request setup attaches a lifecycle through the required factory. Model calls
prepare before confidence acquisition; durable factory installation remains a
separate seam and enabling without one fails closed.
"""
from native_port import replace_once


def server_context(source):
    source = replace_once(source, '#include "speculative.h"',
                          '#include "speculative.h"\n#include "round_lifecycle.h"')
    source = replace_once(source, '    common_speculative * spec;', '''    common_speculative * spec;

    // Empty preserves legacy behavior. Request setup must call begin(id, ...)
    // before attaching; release detaches so recycled slots cannot train it.
    std::shared_ptr<cafe3::round_lifecycle> cafe3_rounds;
    cafe3::implementation cafe3_impl = cafe3::implementation::other;
    // Factory installation is mandatory before enabling native execution.
    // A missing factory fails closed instead of silently losing observations.
    std::function<std::shared_ptr<cafe3::round_lifecycle>(int)> cafe3_factory;
    void cafe3_attach(std::uint64_t request, int cap, const char * env) {
        cafe3_release();
        if (!cafe3::enabled(env)) return;
        if (!cafe3_factory) throw std::logic_error("CAFE3 durable lifecycle factory required");
        auto rounds = cafe3_factory(cap);
        if (!rounds) throw std::logic_error("CAFE3 null lifecycle factory");
        rounds->begin(id, request, env);
        cafe3_rounds = std::move(rounds);
    }
    template<class Params> void cafe3_bind(Params & dp) {
        if (!cafe3_rounds) return;
        dp.cafe3_selected = false;
        dp.cafe3_prepare = [this](common_speculative_type type, bool selector) {
            cafe3_cancel(); // discard failed/unselected earlier implementation
            cafe3_impl = type == COMMON_SPECULATIVE_TYPE_DRAFT_MTP
                ? cafe3::implementation::mtp
                : type == COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH
                    ? (selector ? cafe3::implementation::dflash2 : cafe3::implementation::dflash)
                    : cafe3::implementation::other;
            cafe3_rounds->prepare(id, cafe3_impl);
        };
        const int static_width = dp.n_max;
        dp.cafe3_select = [this, static_width](common_speculative_type type, int cap, double p) {
            const bool matching = (type == COMMON_SPECULATIVE_TYPE_DRAFT_MTP && cafe3_impl == cafe3::implementation::mtp)
                || (type == COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH &&
                    (cafe3_impl == cafe3::implementation::dflash || cafe3_impl == cafe3::implementation::dflash2));
            if (!matching) throw std::logic_error("CAFE3 selection without matching preparation");
            return cafe3_rounds->select(id, cafe3_impl, cap, static_width, p).width;
        };
    }
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
    source = replace_once(source, '        slot.task = std::make_unique<const server_task>(std::move(task));',
                          '        slot.task = std::make_unique<const server_task>(std::move(task));\n'
                          '        slot.cafe3_attach(slot.task->id, slot.task->params.speculative.draft.n_max, std::getenv("LLAMA_CAFE3_ADAPTIVE"));')
    source = replace_once(source, '                        drafting.push_back(&slot);',
                          '                        slot.cafe3_bind(common_speculative_get_draft_params(spec.get(), slot.id));\n\n'
                          '                        drafting.push_back(&slot);')
    return source
