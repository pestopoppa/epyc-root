// CAFE-2 raw target-verify timing candidate. Build-only preparation.
// Real MTP chain, same target-state snapshot before every width.
// Expert-union census and matched numerical floor are required before a CAFE-2 verdict.
#include "llama.h"
#include "speculative.h"
#include "mtp_draft_bridge.hpp"
#include "expert_union.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <chrono>
#include <cmath>
#include <algorithm>

static llama_token argmax(llama_context *ctx, const llama_vocab *vocab, int row) {
    const float *logits = llama_get_logits_ith(ctx, row);
    const int n = llama_vocab_n_tokens(vocab);
    if (!logits || n <= 0) return -1;
    for (int i = 0; i < n; ++i) if (!std::isfinite(logits[i])) return -1;
    int best = 0;
    for (int i = 1; i < n; ++i) if (logits[i] > logits[best]) best = i;
    return best;
}

int main(int argc, char **argv) {
    const bool expert_census = argc == 3 && std::strcmp(argv[2], "--expert-census") == 0;
    if ((argc != 2 && !expert_census) || !argv[1][0]) { std::fprintf(stderr, "usage: %s model.gguf [--expert-census]\n", argv[0]); return 2; }
    llama_backend_init();
    auto mp = llama_model_default_params(); mp.n_gpu_layers = 0; mp.load_mtp = true;
    llama_model *model = llama_model_load_from_file(argv[1], mp);
    if (!model) { std::fprintf(stderr, "UNKNOWN model load\n"); llama_backend_free(); return 2; }
    int result = 2;
    {
        const llama_vocab *vocab = llama_model_get_vocab(model);
        Cafe2ExpertUnion census;
        if (expert_census && !census.configure(model)) {
            std::fprintf(stderr, "UNKNOWN expected qwen35moe E256/K8/40-layer carrier missing\n");
            llama_model_free(model); llama_backend_free(); return 2;
        }
        auto cp = llama_context_default_params();
        if (expert_census) { cp.cb_eval = Cafe2ExpertUnion::callback; cp.cb_eval_user_data = &census; }
        cp.n_ctx = 512; cp.n_batch = 128; cp.n_ubatch = 128; cp.n_rs_seq = 8;
        llama_context *ctx = llama_init_from_model(model, cp);
        if (ctx && vocab && llama_model_n_layer_nextn(model) > 0) {
            common_params params;
            params.n_ctx = cp.n_ctx; params.n_batch = cp.n_batch; params.n_ubatch = cp.n_ubatch;
            params.speculative.types = { COMMON_SPECULATIVE_TYPE_DRAFT_MTP };
            params.speculative.draft.n_max = 8;
            params.speculative.draft.backend_sampling = false;
            auto dft = common_speculative_init_from_params(params, model, ctx);
            if (dft && dft->context()) {
                params.speculative.draft.ctx_tgt = ctx;
                params.speculative.draft.ctx_dft = dft->context();
                common_speculative_ptr spec(common_speculative_init(params.speculative, 1));
                if (spec && common_speculative_need_embd_nextn(spec.get())) {
                    const char *text = "Explain a jet engine briefly.";
                    int n = -llama_tokenize(vocab, text, std::strlen(text), nullptr, 0, true, true);
                    if (n > 0 && n < 120) {
                        llama_tokens prompt(n);
                        if (llama_tokenize(vocab, text, std::strlen(text), prompt.data(), n, true, true) == n) {
                            llama_batch batch = llama_batch_init(n, 0, 1);
                            bool batch_ok = batch.token && batch.pos && batch.n_seq_id && batch.seq_id && batch.logits;
                            if (batch_ok) for (int i = 0; i < n; ++i) batch_ok = batch_ok && batch.seq_id[i];
                            if (batch_ok) {
                                batch.n_tokens = n;
                                for (int i = 0; i < n; ++i) {
                                    batch.token[i] = prompt[i]; batch.pos[i] = i;
                                    batch.n_seq_id[i] = 1; batch.seq_id[i][0] = 0; batch.logits[i] = true;
                                }
                                if (llama_decode(ctx, batch) == 0 && common_speculative_process(spec.get(), batch)) {
                                    common_speculative_begin(spec.get(), 0, prompt);
                                    llama_token boundary = argmax(ctx, vocab, -1);
                                    llama_tokens draft;
                                    if (cafe4_mtp_draft(spec.get(), 0, n, boundary, prompt, 8, draft) && draft.size() == 8) {
                                        llama_synchronize(ctx);
                                        std::vector<uint8_t> state(llama_state_get_size(ctx));
                                        if (state.empty() || llama_state_get_data(ctx, state.data(), state.size()) != state.size() ||
                                            !cafe2_plan(expert_census, prompt, boundary, draft)) {
                                            std::fprintf(stderr, "UNKNOWN snapshot failed\n");
                                        } else {
                                            unsigned samples = 0;
                                            // Fixed interleaved width schedules, each with an independent
                                            // width-1 repeat. These are raw samples, not an A/A verdict.
                                            const int order[5][11] = {
                                                {1,5,9,2,6,3,7,4,8,1,5},
                                                {9,1,8,3,7,4,6,2,5,1,5},
                                                {5,2,8,1,7,3,9,4,6,1,5},
                                                {2,6,4,8,1,9,3,7,5,1,5},
                                                {8,4,7,2,9,5,3,1,6,1,5}};
                                            bool valid = true;
                                            for (int rep = 0; rep < 5 && valid; ++rep) {
                                                for (int cell = 0; cell < 11 && valid; ++cell) {
                                                    const int rows = order[rep][cell];
                                                    llama_synchronize(ctx);
                                                    if (llama_state_set_data(ctx, state.data(), state.size()) != state.size()) { valid = false; break; }
                                                    std::vector<uint8_t> restored(state.size());
                                                    if (llama_state_get_data(ctx, restored.data(), restored.size()) != state.size() || restored != state) { valid = false; break; }
                                                    llama_batch verify = llama_batch_init(rows, 0, 1);
                                                    bool ok = verify.token && verify.pos && verify.n_seq_id && verify.seq_id && verify.logits;
                                                    if (ok) for (int i = 0; i < rows; ++i) ok = ok && verify.seq_id[i];
                                                    if (ok) {
                                                        verify.n_tokens = rows;
                                                        for (int i = 0; i < rows; ++i) {
                                                            verify.token[i] = i ? draft[i-1] : boundary; verify.pos[i] = n + i;
                                                            verify.n_seq_id[i] = 1; verify.seq_id[i][0] = 0; verify.logits[i] = true;
                                                        }
                                                        if (expert_census) {
                                                            llama_tokens window{boundary};
                                                            window.insert(window.end(), draft.begin(), draft.begin() + rows - 1);
                                                            ok = census.begin(rep, cell, rows, n, window);
                                                            if (ok) {
                                                                const int rc = llama_decode(ctx, verify);
                                                                llama_synchronize(ctx);
                                                                ok = census.finish(rc);
                                                            }
                                                            if (ok) ++samples;
                                                        } else {
                                                            // No callback is installed on this timing context.
                                                            const auto begin = std::chrono::steady_clock::now();
                                                            const int rc = llama_decode(ctx, verify);
                                                            llama_synchronize(ctx);
                                                            const double ns = std::chrono::duration<double,std::nano>(std::chrono::steady_clock::now()-begin).count();
                                                            ok = rc == 0 && std::isfinite(ns) && ns >= 1000.0;
                                                            if (ok) {
                                                                ++samples;
                                                                ok = std::printf("{\"schema\":\"cafe2.verify.raw.v1\",\"window\":%d,\"rep\":%d,\"cell\":%d,\"rows\":%d,\"position_start\":%d,\"ns\":%.0f,\"draft_n\":8,\"state_equal\":true,\"expert_union\":null}\n",rep*11+cell,rep,cell,rows,n,ns) >= 0 && std::fflush(stdout) == 0 && !std::ferror(stdout);
                                                            }
                                                        }
                                                    }
                                                    llama_batch_free(verify);
                                                    valid = ok;
                                                }
                                            }
                                            if (valid && samples == 55) {
                                                std::fprintf(stderr, "CAFE2_VERIFY_RAW samples=55 arm=%s expert_union=%s\n", expert_census ? "expert_census" : "timing_no_callback", expert_census ? "COMPLETE_ROUTED_IDS_ONLY" : "UNKNOWN");
                                                result = 0;
                                            }
                                        }
                                    }
                                }
                            }
                            llama_batch_free(batch);
                        }
                    }
                }
            }
        }
        if (ctx) llama_free(ctx);
    }
    llama_model_free(model); llama_backend_free();
    if (result != 0) std::fprintf(stderr, "UNKNOWN missing or invalid verify timing/census cell\n");
    return result;
}
