// SOURCE-ONLY CANDIDATE: no native execution, rollback or CAFE-4 verdict.
// Exercises the real single-sequence MTP lifecycle through a target verify
// batch. It always returns UNKNOWN until rollback and fault checks are wired.
#include "llama.h"
#include "speculative.h"
#include "mtp_draft_bridge.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

static llama_token argmax(llama_context *ctx, const llama_vocab *vocab, int row) {
    const float *logits = llama_get_logits_ith(ctx, row);
    const int n = llama_vocab_n_tokens(vocab);
    if (!logits || n <= 0) return -1;
    int best = 0;
    for (int i = 1; i < n; ++i) if (logits[i] > logits[best]) best = i;
    return best;
}

int main(int argc, char **argv) {
    if (argc != 2 || !argv[1][0]) { std::fprintf(stderr, "usage: %s model.gguf\n", argv[0]); return 2; }
    llama_backend_init();
    auto mp = llama_model_default_params(); mp.n_gpu_layers = 0; mp.load_mtp = true;
    llama_model *model = llama_model_load_from_file(argv[1], mp);
    if (!model) { std::fprintf(stderr, "UNKNOWN model load\n"); llama_backend_free(); return 2; }
    int result = 2;
    {
        const llama_vocab *vocab = llama_model_get_vocab(model);
        auto cp = llama_context_default_params();
        cp.n_ctx = 512; cp.n_batch = 128; cp.n_ubatch = 128; cp.n_rs_seq = 8;
        llama_context *ctx = llama_init_from_model(model, cp);
        if (ctx && vocab && llama_model_n_layer_nextn(model) > 0) {
            common_params params;
            params.n_ctx = cp.n_ctx; params.n_batch = cp.n_batch; params.n_ubatch = cp.n_ubatch;
            params.speculative.types = { COMMON_SPECULATIVE_TYPE_DRAFT_MTP };
            params.speculative.draft.n_max = 3;
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
                                    if (cafe4_mtp_draft(spec.get(), 0, n, boundary, prompt, 3, draft)) {
                                        llama_batch verify = llama_batch_init(draft.size() + 1, 0, 1);
                                        bool verify_ok = verify.token && verify.pos && verify.n_seq_id && verify.seq_id && verify.logits;
                                        if (verify_ok) for (size_t i = 0; i <= draft.size(); ++i) verify_ok = verify_ok && verify.seq_id[i];
                                        if (verify_ok) {
                                            verify.n_tokens = (int) draft.size() + 1;
                                            for (int i = 0; i < verify.n_tokens; ++i) {
                                                verify.token[i] = i ? draft[i-1] : boundary; verify.pos[i] = n + i;
                                                verify.n_seq_id[i] = 1; verify.seq_id[i][0] = 0; verify.logits[i] = true;
                                            }
                                            if (llama_decode(ctx, verify) == 0 && common_speculative_process(spec.get(), verify)) {
                                                unsigned accepted = 0;
                                                for (size_t i = 0; i < draft.size(); ++i) {
                                                    if (argmax(ctx, vocab, (int)i) != draft[i]) break;
                                                    ++accepted;
                                                }
                                                common_speculative_accept(spec.get(), 0, (uint16_t) accepted);
                                                std::fprintf(stderr, "MTP_LIFECYCLE width=%zu accepted=%u\n", draft.size(), accepted);
                                            }
                                        }
                                        llama_batch_free(verify);
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
    std::fprintf(stderr, "UNKNOWN rollback and fault controls unimplemented\n");
    return result;
}
