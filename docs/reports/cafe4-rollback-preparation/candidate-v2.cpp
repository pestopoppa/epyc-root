// UNVALIDATED SOURCE CANDIDATE: no G3/CAFE-4 verdict or runnable row.
// Recurrent snapshot execution and state-specific fault control remain unproved.
// Correctness harness for the recurrent-state snapshot ring (n_rs_seq > 0).
//
// A forward-only generation never reads the snapshot slots back, so it cannot
// catch a bad snapshot write. This does:
//
//   pass A (reference): greedily generate N tokens straight through.
//   pass B (rollback):  generate the same N tokens, but every S tokens
//                       over-generate by R, then llama_memory_seq_rm() those R
//                       positions away and re-generate them.
//
// Pass B only lands on the same tokens if the state restored from the snapshot
// ring is exactly the state that produced them the first time. Any error in the
// conv-window or SSM snapshot write shows up as a token mismatch.
#include "llama.h"

#include <algorithm>
#include <cmath>
#include <cerrno>
#include <climits>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

static bool parse_nonnegative_int(const char * text, int & value) {
    if (!text || !*text) return false;
    char * end = nullptr;
    errno = 0;
    const long parsed = strtol(text, &end, 10);
    if (errno || end == text || *end || parsed < 0 || parsed > INT_MAX) return false;
    value = static_cast<int>(parsed);
    return true;
}

static llama_token greedy_row(llama_context * ctx, const llama_vocab * vocab, int row) {
    const int     n_vocab = llama_vocab_n_tokens(vocab);
    const float * logits  = llama_get_logits_ith(ctx, row);

    if (!logits || n_vocab <= 0) return -1;
    llama_token best   = 0;
    float       best_v = logits[0];
    for (int i = 1; i < n_vocab; i++) {
        if (logits[i] > best_v) {
            best_v = logits[i];
            best   = i;
        }
    }
    return best;
}

static llama_token greedy(llama_context * ctx, const llama_vocab * vocab) { return greedy_row(ctx, vocab, -1); }

int main(int argc, char ** argv) {
    std::string model_path;
    std::string prompt    = "Explain how a jet engine works, step by step.";
    int         n_predict = 128;
    int         stride    = 16;  // roll back every `stride` accepted tokens
    int         rewind    = 4;   // how many tokens to discard and re-generate
    int         verify_batch = 0; // 0 selects the original one-token mode
    bool        inject_fault = false;
    int         n_gpu_layers = 0;  // explicit CPU default; pass -ngl to offload
    int         n_rs_seq  = 8;   // snapshot ring depth; must be >= rewind + 1

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--verify-batch")) {
            if (i + 1 >= argc) { fprintf(stderr, "missing --verify-batch value\n"); return 1; }
            char * end = nullptr; errno = 0;
            const long parsed = strtol(argv[++i], &end, 10);
            if (errno || !end || *end || end == argv[i] || parsed < 2 || parsed > INT_MAX - 1) {
                fprintf(stderr, "--verify-batch requires an integer >= 2\n"); return 1;
            }
            verify_batch = (int) parsed;
        } else if (!strcmp(argv[i], "--fault-inject")) {
            inject_fault = true;
        } else if (!strcmp(argv[i], "-ngl")) {
            if (i + 1 >= argc) { fprintf(stderr, "missing -ngl value\n"); return 1; }
            char * end = nullptr;
            errno = 0;
            const long parsed = strtol(argv[++i], &end, 10);
            if (errno || !end || *end || end == argv[i] || parsed < 0 || parsed > INT_MAX) {
                fprintf(stderr, "invalid -ngl value\n"); return 1;
            }
            n_gpu_layers = (int) parsed;
        } else if (!strcmp(argv[i], "-m")) {
            if (i + 1 >= argc) { fprintf(stderr, "missing -m value\n"); return 1; }
            model_path = argv[++i];
        } else if (!strcmp(argv[i], "-n") || !strcmp(argv[i], "-s") ||
                   !strcmp(argv[i], "-r") || !strcmp(argv[i], "-k")) {
            const char * flag = argv[i];
            int * dest = !strcmp(flag, "-n") ? &n_predict : !strcmp(flag, "-s") ? &stride :
                         !strcmp(flag, "-r") ? &rewind : &n_rs_seq;
            if (i + 1 >= argc || !parse_nonnegative_int(argv[++i], *dest)) {
                fprintf(stderr, "invalid %s value\n", flag); return 1;
            }
        } else if (argv[i][0] != '-') {
            prompt = argv[i];
        } else {
            fprintf(stderr, "unknown option: %s\n", argv[i]); return 1;
        }
    }
    if (n_predict <= 0 || stride <= 0 || rewind <= 0 || n_rs_seq <= 0 ||
        (verify_batch && (verify_batch > INT_MAX - 2 || n_rs_seq < verify_batch + 1 + (inject_fault ? 1 : 0) ||
                          static_cast<long long>(n_predict) <= static_cast<long long>(stride) + verify_batch)) ||
        (!verify_batch && static_cast<long long>(n_rs_seq) < static_cast<long long>(rewind) + 1) ||
        (inject_fault && !verify_batch)) {
        fprintf(stderr, "invalid sizes: verify needs n_rs_seq >= batch+1, n_predict > stride+batch; fault requires verify mode\n");
        return 1;
    }
    if (model_path.empty()) {
        fprintf(stderr, "usage: %s -m model.gguf [-n N] [-s stride] [-r rewind] [-k n_rs_seq] [-ngl N] [--verify-batch D] [--fault-inject]\n", argv[0]);
        return 1;
    }

    // An extra position removal is not a recurrent-state-specific fault:
    // a position/KV gap could explain a mismatch. Do not call it detected.
    if (inject_fault) {
        fprintf(stderr, "UNKNOWN state-specific fault injection not implemented\n");
        return 2;
    }

    llama_backend_init();

    llama_model_params mparams = llama_model_default_params();
    mparams.n_gpu_layers       = n_gpu_layers;
    llama_model * model        = llama_model_load_from_file(model_path.c_str(), mparams);
    if (!model) {
        fprintf(stderr, "failed to load model\n");
        return 1;
    }

    const llama_vocab * vocab = llama_model_get_vocab(model);

    if (!vocab || prompt.size() > INT_MAX) {
        fprintf(stderr, "invalid vocabulary or prompt\n"); llama_model_free(model); llama_backend_free(); return 1;
    }
    const int                n_prompt = -llama_tokenize(vocab, prompt.c_str(), prompt.size(), NULL, 0, true, true);
    if (!vocab || n_prompt <= 0 || static_cast<long long>(n_prompt) + n_predict + 64 > INT_MAX) {
        fprintf(stderr, "invalid prompt or context size\n"); llama_model_free(model); llama_backend_free(); return 1;
    }
    std::vector<llama_token> ptoks(n_prompt);
    if (llama_tokenize(vocab, prompt.c_str(), prompt.size(), ptoks.data(), ptoks.size(), true, true) != n_prompt) {
        fprintf(stderr, "tokenization failed\n"); llama_model_free(model); llama_backend_free(); return 1;
    }

    int n_rollbacks = 0;
    int injected = 0;
    std::vector<llama_token> ref, rb;
    std::vector<std::vector<float>> oracle_logits; // independently serial target run
    const int n_vocab = llama_vocab_n_tokens(vocab);
    constexpr size_t oracle_budget = 256ULL * 1024 * 1024;
    if (n_vocab <= 0 || static_cast<size_t>(n_predict) + 1 >
            oracle_budget / sizeof(float) / static_cast<size_t>(n_vocab)) {
        fprintf(stderr, "UNKNOWN serial logits exceed 256 MiB budget\n");
        llama_model_free(model); llama_backend_free(); return 2;
    }
    auto logit_error = [&](const float * actual, size_t index, double & max_error) -> bool {
        if (!actual || index >= oracle_logits.size() || n_vocab <= 0) return false;
        max_error = 0;
        for (int k = 0; k < n_vocab; ++k) {
            const double a = actual[k], b = oracle_logits[index][k];
            if (!std::isfinite(a) || !std::isfinite(b)) return false;
            max_error = std::max(max_error, std::abs(a - b));
        }
        return true;
    };

    auto run = [&](bool with_rollback, std::vector<llama_token> & out) -> bool {
        llama_context_params cparams = llama_context_default_params();
        cparams.n_ctx                = n_prompt + n_predict + 64;
        cparams.n_batch              = n_prompt + 64;
        if (verify_batch + 1 > (int) cparams.n_batch) cparams.n_batch = verify_batch + 1;
        if (verify_batch + 1 > (int) cparams.n_ubatch) cparams.n_ubatch = verify_batch + 1;
        cparams.n_rs_seq             = n_rs_seq;
        llama_context * ctx          = llama_init_from_model(model, cparams);
        if (!ctx) {
            fprintf(stderr, "failed to create context\n");
            return false;
        }
        if (with_rollback && verify_batch && (llama_n_batch(ctx) < (uint32_t) (verify_batch + 1) ||
            llama_n_ubatch(ctx) < (uint32_t) (verify_batch + 1))) {
            fprintf(stderr, "UNKNOWN effective batch capacity below D+1\n");
            llama_free(ctx); return false;
        }
        if (with_rollback && verify_batch && llama_n_rs_seq(ctx) < (uint32_t) (verify_batch + 1 + (inject_fault ? 1 : 0))) {
            fprintf(stderr, "UNKNOWN effective snapshot ring below requested capacity\n");
            llama_free(ctx); return false;
        }
        llama_memory_t mem = llama_get_memory(ctx);
        if (!mem) { llama_free(ctx); return false; }

        llama_batch batch = llama_batch_get_one(ptoks.data(), ptoks.size());
        if (llama_decode(ctx, batch)) {
            fprintf(stderr, "decode(prompt) failed\n");
            return false;
        }
        int n_pos = n_prompt;

        int since = 0;
        while ((int) out.size() < n_predict) {
            if (!with_rollback) {
                const float * logits = llama_get_logits_ith(ctx, -1);
                if (!logits || n_vocab <= 0) { llama_free(ctx); return false; }
                oracle_logits.emplace_back(logits, logits + n_vocab);
            }
            llama_token tok = greedy(ctx, vocab);
            if (tok < 0) { llama_free(ctx); return false; }
            out.push_back(tok);

            batch = llama_batch_get_one(&tok, 1);
            if (llama_decode(ctx, batch)) {
                fprintf(stderr, "decode failed\n");
                return false;
            }
            n_pos++;
            since++;

            if (with_rollback && verify_batch && since >= stride &&
                static_cast<long long>(out.size()) + verify_batch <= n_predict) {
                const size_t before = out.size();
                if (n_vocab < 2 || oracle_logits.size() <= before + (size_t) verify_batch ||
                    ref.size() < before + (size_t) verify_batch ||
                    !std::equal(out.begin(), out.end(), ref.begin())) {
                    fprintf(stderr, "UNKNOWN serial oracle/prefix unavailable or diverged\n"); return false;
                }
                // Generate the proposed draft independently in a fresh context using
                // only the candidate's own current token prefix, never reference IDs.
                llama_context_params dparams = cparams; dparams.n_rs_seq = 0;
                llama_context * draft_ctx = llama_init_from_model(model, dparams);
                if (!draft_ctx) { fprintf(stderr, "UNKNOWN draft context unavailable\n"); return false; }
                llama_batch db = llama_batch_get_one(ptoks.data(), ptoks.size());
                if (llama_decode(draft_ctx, db)) { llama_free(draft_ctx); return false; }
                for (llama_token token : out) {
                    db = llama_batch_get_one(&token, 1);
                    if (llama_decode(draft_ctx, db)) { llama_free(draft_ctx); return false; }
                }
                std::vector<llama_token> draft;
                for (int j = 0; j < verify_batch; ++j) {
                    llama_token token = greedy(draft_ctx, vocab);
                    if (token < 0) { llama_free(draft_ctx); return false; }
                    // Force a rejection halfway without borrowing any oracle token.
                    if (j == verify_batch / 2) token = (token + 1) % n_vocab;
                    draft.push_back(token);
                    db = llama_batch_get_one(&token, 1);
                    if (llama_decode(draft_ctx, db)) { llama_free(draft_ctx); return false; }
                }
                llama_free(draft_ctx);
                // Remove the already processed sampled boundary token so that the
                // target sees the same D+1 geometry as the server: sampled + draft.
                const llama_pos start = n_pos - 1;
                if (start < 1 || !llama_memory_seq_rm(mem, 0, start, -1)) {
                    fprintf(stderr, "UNKNOWN boundary rewind refused\n"); return false;
                }
                n_pos = start;
                llama_batch verify = llama_batch_init(verify_batch + 1, 0, 1);
                if (!verify.token || !verify.pos || !verify.n_seq_id || !verify.seq_id || !verify.logits) {
                    llama_batch_free(verify); fprintf(stderr, "UNKNOWN batch allocation\n"); return false;
                }
                verify.n_tokens = verify_batch + 1;
                for (int j = 0; j <= verify_batch; ++j) {
                    if (!verify.seq_id[j]) { llama_batch_free(verify); fprintf(stderr, "UNKNOWN batch row allocation\n"); return false; }
                    verify.token[j] = j == 0 ? out.back() : draft[j - 1];
                    verify.pos[j] = start + j;
                    verify.n_seq_id[j] = 1; verify.seq_id[j][0] = 0; verify.logits[j] = true;
                }
                const int rc = llama_decode(ctx, verify);
                llama_batch_free(verify);
                if (rc != 0) { fprintf(stderr, "UNKNOWN decode(verify) rc=%d\n", rc); return false; }
                n_pos += verify_batch + 1;
                // Even the first proposed token must be compared from the same
                // boundary state; otherwise a zero-accept rollback can pass
                // without checking the batched boundary against the oracle.
                double boundary_error = 0;
                if (!logit_error(llama_get_logits_ith(ctx, 0), before, boundary_error) || boundary_error > 1e-5) {
                    fprintf(stderr, "UNKNOWN verify boundary differs from serial oracle\n"); return false;
                }
                int accept = 0;
                for (int j = 0; j < verify_batch; ++j) {
                    const llama_token prediction = greedy_row(ctx, vocab, j);
                    if (prediction < 0) return false;
                    if (prediction != draft[j]) break;
                    // Compare row logits only where accepted prefix agrees with the
                    // independent serial oracle; batch numerical drift is explicit.
                    if (draft[j] != ref[before + (size_t) j]) {
                        fprintf(stderr, "UNKNOWN accepted draft disagrees with serial token oracle\n"); return false;
                    }
                    double err = 0;
                    if (!logit_error(llama_get_logits_ith(ctx, j + 1), before + (size_t) j + 1, err)) {
                        fprintf(stderr, "UNKNOWN missing or nonfinite row logits\n"); return false;
                    }
                    fprintf(stderr, "VERIFY_ROW row=%d oracle_index=%zu max_abs=%.9g\n", j, before + (size_t) j + 1, err);
                    if (err > 1e-5) { fprintf(stderr, "UNKNOWN batched-vs-serial row tolerance exceeded\n"); return false; }
                    ++accept;
                }
                if (accept <= 0 || accept >= verify_batch) {
                    fprintf(stderr, "UNKNOWN no strict partial acceptance (accepted=%d width=%d)\n", accept, verify_batch);
                    llama_free(ctx); return false;
                }
                // Server keeps the boundary plus accepted drafts, removes only
                // rejected suffix, and sets the newly sampled token aside for
                // the next decode. It does not rewind/redecode the kept token.
                const llama_token sampled = greedy_row(ctx, vocab, accept);
                const llama_pos keep = start + 1 + accept;
                if (sampled < 0 || !llama_memory_seq_rm(mem, 0, keep, -1)) {
                    fprintf(stderr, "UNKNOWN server-equivalent suffix removal refused\n");
                    llama_free(ctx); return false;
                }
                n_pos = keep;
                for (int j = 0; j < accept; ++j) out.push_back(draft[j]);
                if (out.size() >= ref.size() || sampled != ref[out.size()]) {
                    fprintf(stderr, "UNKNOWN sampled token differs from serial oracle\n");
                    llama_free(ctx); return false;
                }
                // This decode models the server's next pass, not a replay of
                // the already retained boundary or last accepted draft token.
                llama_batch next = llama_batch_init(1, 0, 1);
                if (!next.token || !next.pos || !next.n_seq_id || !next.seq_id ||
                    !next.seq_id[0] || !next.logits) {
                    llama_batch_free(next); llama_free(ctx);
                    fprintf(stderr, "UNKNOWN next-token allocation\n"); return false;
                }
                next.n_tokens = 1; next.token[0] = sampled; next.pos[0] = keep;
                next.n_seq_id[0] = 1; next.seq_id[0][0] = 0; next.logits[0] = true;
                const int next_rc = llama_decode(ctx, next);
                llama_batch_free(next);
                if (next_rc != 0) {
                    fprintf(stderr, "UNKNOWN decode(next sampled) rc=%d\n", next_rc);
                    llama_free(ctx); return false;
                }
                out.push_back(sampled); ++n_pos; ++n_rollbacks;
                double err = 0;
                if (!logit_error(llama_get_logits_ith(ctx, -1), out.size(), err) || err > 1e-5) {
                    fprintf(stderr, "UNKNOWN next-token logits differ from serial oracle\n");
                    llama_free(ctx); return false;
                }
                fprintf(stderr, "STRICT_PARTIAL width=%d accepted=%d keep=%d max_abs=%.9g\n",
                        verify_batch, accept, (int) keep, err);
                since = 0;
            } else if (with_rollback && !verify_batch && since >= stride && static_cast<long long>(out.size()) + rewind < n_predict) {
                n_rollbacks++;
                // over-generate `rewind` tokens, then throw them away
                for (int r = 0; r < rewind; r++) {
                    llama_token t = greedy(ctx, vocab);
                    batch         = llama_batch_get_one(&t, 1);
                    if (llama_decode(ctx, batch)) {
                        fprintf(stderr, "decode(draft) failed\n");
                        return false;
                    }
                    n_pos++;
                }
                // Drop the drafts AND the last accepted token in one go, then
                // re-decode the accepted token so the logits are valid again.
                // This forces the state to be restored from a snapshot taken
                // (rewind + 1) steps back -- needs n_rs_seq >= rewind + 1.
                const llama_pos keep = n_pos - rewind - 1;
                if (!llama_memory_seq_rm(mem, 0, keep, -1)) {
                    fprintf(stderr, "ROLLBACK REFUSED: keep=%d n_pos=%d rewind=%d\n", keep, n_pos, rewind);
                    return false;
                }
                n_pos = keep;

                batch = llama_batch_get_one(&out.back(), 1);
                if (llama_decode(ctx, batch)) {
                    fprintf(stderr, "decode(replay) failed\n");
                    return false;
                }
                n_pos++;
                since = 0;
            }
        }
        if (!with_rollback) {
            const float * logits = llama_get_logits_ith(ctx, -1);
            if (!logits || n_vocab <= 0) { llama_free(ctx); return false; }
            oracle_logits.emplace_back(logits, logits + n_vocab);
        }
        llama_free(ctx);
        return true;
    };

    bool ok = true;

    if (!run(false, ref)) {
        return 1;
    }
    if (!run(true, rb)) {
        return 1;
    }

    size_t n        = ref.size() < rb.size() ? ref.size() : rb.size();
    size_t mismatch = 0;
    int    first    = -1;
    for (size_t i = 0; i < n; i++) {
        if (ref[i] != rb[i]) {
            if (first < 0) {
                first = (int) i;
            }
            mismatch++;
        }
    }

    printf("\n=== rs-rollback ===\n");
    printf("tokens compared : %zu\n", n);
    printf("mismatches      : %zu\n", mismatch);
    printf("rollbacks done  : %d\n", n_rollbacks);
    // a run that never entered the rollback branch compared two identical
    // straight-through generations and proved nothing, so it is not a pass
    if (inject_fault && injected == 0) {
        fprintf(stderr, "RESULT: FAIL (requested fault never injected)\n");
        ok = false;
    } else if (n_rollbacks == 0) {
        printf("RESULT: FAIL (no rollback was attempted: need n_predict > stride + rewind, "
               "got n_predict=%d stride=%d rewind=%d)\n", n_predict, stride, rewind);
        ok = false;
    } else if (mismatch || ref.size() != rb.size()) {
        if (first >= 0) printf("first mismatch  : index %d (ref=%d rb=%d)\n", first, ref[first], rb[first]);
        else printf("length mismatch : ref=%zu rb=%zu\n", ref.size(), rb.size());
        printf("RESULT: FAIL\n");
        ok = false;
    } else {
        if (verify_batch) {
            printf("RESULT: UNKNOWN (token consistency observed; recurrent snapshot execution and fault control unproven)\n");
            ok = false;
        } else {
            printf("RESULT: PASS (rollback reproduces the straight-through sequence)\n");
        }
    }

    llama_model_free(model);
    llama_backend_free();
    return ok ? 0 : 1;
}
