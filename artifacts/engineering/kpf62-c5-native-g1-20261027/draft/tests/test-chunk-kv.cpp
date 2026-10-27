// chunk-KV reuse, phase P1 slice 1: libllama range export / inject, RoPE re-rotation and its self-check.
//
// Run with -m <attention-only gguf> -ctk f32 -ctv f32 (the f32 K cache is what G1 prescribes; a quantized K cache
// re-quantizes on shift and is not an exactness test). With a hybrid / recurrent model the same binary asserts the
// clean REFUSAL instead (return 0 / false, cache and decode untouched), which is the phase-1 contract.
// Optional --g1-capture-jsonl PATH writes per-position G1 sufficient statistics for prospective native capture.
//
// Gates (P0_THRESHOLDS.md, section 2): K/V NMSE <= 1e-6 after a shift with no recompute, logits NMSE <= 1e-5 at the
// suffix, round-trip self-check NMSE <= 1e-6. The measured values are printed so the margin is visible.
#undef NDEBUG
#include "arg.h"
#include "common.h"
#include "llama.h"
#include "llama-ext.h"

#include <algorithm>
#include <clocale>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <random>
#include <string>
#include <vector>

static int n_fail = 0;
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); n_fail++; } } while (0)

static double nmse(const std::vector<float> & x, const std::vector<float> & ref) {
    double num = 0.0, den = 0.0;
    for (size_t i = 0; i < ref.size(); ++i) {
        const double d = (double) x[i] - (double) ref[i];
        num += d*d;
        den += (double) ref[i]*(double) ref[i];
    }
    return den > 0.0 ? num/den : num;
}

using tokens_t = std::vector<llama_token>;

static tokens_t rand_tokens(std::mt19937 & rng, int n, int n_vocab) {
    tokens_t t(n);
    for (auto & x : t) {
        x = (llama_token) (rng() % (uint32_t) n_vocab);
    }
    return t;
}

// decode toks at positions pos0.. in seq; returns logits of every token (n x n_vocab) when want_logits
static bool decode(llama_context * ctx, const tokens_t & toks, llama_pos pos0, llama_seq_id seq, int n_vocab,
        std::vector<float> * logits = nullptr) {
    llama_batch batch = llama_batch_init((int32_t) toks.size(), 0, 1);
    for (size_t i = 0; i < toks.size(); ++i) {
        common_batch_add(batch, toks[i], pos0 + (llama_pos) i, { seq }, true);
    }
    const bool ok = llama_decode(ctx, batch) == 0;
    if (ok && logits) {
        logits->assign((size_t) toks.size()*n_vocab, 0.0f);
        for (size_t i = 0; i < toks.size(); ++i) {
            memcpy(logits->data() + i*n_vocab, llama_get_logits_ith(ctx, (int32_t) i), n_vocab*sizeof(float));
        }
    }
    llama_batch_free(batch);
    return ok;
}

static bool read_kv(llama_context * ctx, llama_seq_id seq, llama_pos p0, llama_pos p1,
        std::vector<float> & k, std::vector<float> & v) {
    size_t n_v = 0;
    const size_t n_k = llama_chunk_kv_read_f32(ctx, seq, p0, p1, nullptr, nullptr, &n_v);
    if (n_k == 0) {
        return false;
    }
    k.assign(n_k, 0.0f);
    v.assign(n_v, 0.0f);
    return llama_chunk_kv_read_f32(ctx, seq, p0, p1, k.data(), v.data(), &n_v) == n_k;
}

static bool write_g1_position_rows(std::ofstream & out, llama_pos delta, const char * component,
        const char * comparison, const std::vector<float> & values, const std::vector<float> & reference,
        size_t n_layers, size_t n_positions, llama_pos first_position) {
    if (values.size() != reference.size() || n_layers == 0 || n_positions == 0 ||
            values.size() % (n_layers*n_positions) != 0) {
        return false;
    }
    out << std::setprecision(17);
    const size_t width = values.size() / (n_layers*n_positions);
    for (size_t p = 0; p < n_positions; ++p) {
        double sum_sq_error = 0.0;
        double reference_sq_norm = 0.0;
        size_t element_count = 0;
        size_t mismatch_count = 0;
        for (size_t layer = 0; layer < n_layers; ++layer) {
            const size_t base = (layer*n_positions + p)*width;
            for (size_t j = 0; j < width; ++j) {
                const float value = values[base + j];
                const float ref = reference[base + j];
                const double difference = (double) value - (double) ref;
                sum_sq_error += difference*difference;
                reference_sq_norm += (double) ref*(double) ref;
                mismatch_count += component[0] == 'l'
                    ? (memcmp(&value, &ref, sizeof(float)) != 0)
                    : (value != ref);
                ++element_count;
            }
        }
        if (!std::isfinite(sum_sq_error) || !std::isfinite(reference_sq_norm)) {
            return false;
        }
        out << "{\"schema\":\"epyc.chunk_kv.g1_position.v1\",\"delta\":" << delta
            << ",\"position\":" << (first_position + (llama_pos) p)
            << ",\"component\":\"" << component << "\",\"comparison\":\"" << comparison
            << "\",\"sum_sq_error\":" << sum_sq_error << ",\"reference_sq_norm\":" << reference_sq_norm
            << ",\"element_count\":" << element_count << ",\"mismatch_count\":" << mismatch_count << "}\n";
    }
    return (bool) out;
}

static llama_context * make_ctx(const common_params & params, llama_model * model, uint32_t n_ctx_seq = 1024) {
    auto cparams = common_context_params_to_llama(params);
    cparams.n_seq_max = 8;
    cparams.n_ctx     = 8*n_ctx_seq;
    cparams.n_batch   = 512;
    cparams.n_ubatch  = 512;
    return llama_init_from_model(model, cparams);
}

// the phase-1 contract on memory it cannot serve: refuse everything, leave the context usable
static void test_refusal(const common_params & params, llama_model * model, int n_vocab) {
    llama_context * ctx = make_ctx(params, model);
    CHECK(ctx != nullptr);
    if (!ctx) return;

    char why[256] = {0};
    CHECK(!llama_chunk_kv_supported(ctx, why, sizeof(why)));
    CHECK(why[0] != 0);
    printf("refusal reason: %s\n", why);

    std::mt19937 rng(7);
    const tokens_t toks = rand_tokens(rng, 16, n_vocab);
    CHECK(decode(ctx, toks, 0, 0, n_vocab));

    std::vector<uint8_t> blob(1 << 20);
    CHECK(llama_chunk_kv_export(ctx, nullptr, 0, 0, 0, 16) == 0);
    CHECK(llama_chunk_kv_export(ctx, blob.data(), blob.size(), 0, 0, 16) == 0);
    CHECK(llama_chunk_kv_inject(ctx, blob.data(), blob.size(), 1, 32) == 0);
    double e = -1.0;
    CHECK(!llama_chunk_kv_rope_selfcheck(ctx, 64, &e));
    CHECK(!llama_chunk_kv_apply_shift(ctx) || true); // no pending shift; must not crash

    // the context still decodes after the refusals
    CHECK(decode(ctx, rand_tokens(rng, 4, n_vocab), 16, 0, n_vocab));

    llama_free(ctx);
}

static void test_attention(const common_params & params, llama_model * model, int n_vocab,
        const std::string & g1_capture_path) {
    // CKV_N_CHUNK (default 24, clamped to [24, 512]): a longer chunk gives rounding drift in the G1-ref reference more chances to show
    // (it scales with tokens x dims x depth); the KPF-62.8 k-quant fixture runs it at 512.
    const int n_chunk  = std::min(512, std::max(24, getenv("CKV_N_CHUNK") ? atoi(getenv("CKV_N_CHUNK")) : 24)); // <= n_batch
    const int n_suffix = 6;

    uint32_t n_ctx_seq = 1024;
    while (n_ctx_seq < (uint32_t) (2*n_chunk + 400)) {
        n_ctx_seq *= 2;
    }

    llama_context * ctx = make_ctx(params, model, n_ctx_seq);
    CHECK(ctx != nullptr);
    if (!ctx) return;

    std::ofstream g1_capture;
    if (!g1_capture_path.empty()) {
        g1_capture.open(g1_capture_path, std::ios::out | std::ios::trunc);
        if (!g1_capture) {
            fprintf(stderr, "cannot open G1 capture %s\n", g1_capture_path.c_str());
            n_fail++;
            llama_free(ctx);
            return;
        }
    }

    char why[256] = {0};
    CHECK(llama_chunk_kv_supported(ctx, why, sizeof(why)));

    std::mt19937 rng(1234);

    const tokens_t chunk  = rand_tokens(rng, n_chunk,  n_vocab);
    const tokens_t suffix = rand_tokens(rng, n_suffix, n_vocab);

    // 1. self-check: round trip +d / -d
    for (llama_pos d : { 1, 17, 300, 4096 }) {
        double e = -1.0;
        CHECK(llama_chunk_kv_rope_selfcheck(ctx, d, &e));
        CHECK(!llama_chunk_kv_rope_selfcheck(ctx, std::numeric_limits<llama_pos>::max(), &e));
        printf("rope round-trip delta=%5d  NMSE=%.3e\n", (int) d, e);
        CHECK(e >= 0.0 && e <= 1e-6);
    }

    // 2. isolated encode at offset 0 in seq 0, export
    std::vector<float> logits_dummy;
    CHECK(decode(ctx, chunk, 0, 0, n_vocab));

    const size_t need = llama_chunk_kv_export(ctx, nullptr, 0, 0, 0, n_chunk);
    CHECK(need > 0);
    std::vector<uint8_t> blob(need);
    CHECK(llama_chunk_kv_export(ctx, blob.data(), blob.size(), 0, 0, n_chunk) == need);

    // export is read-only: the source sequence is intact
    CHECK(llama_memory_seq_pos_min(llama_get_memory(ctx), 0) == 0);
    CHECK(llama_memory_seq_pos_max(llama_get_memory(ctx), 0) == n_chunk - 1);

    std::vector<float> k_src, v_src;
    CHECK(read_kv(ctx, 0, 0, n_chunk, k_src, v_src));

    // 3. G1 for several deltas. The same chunk is placed at [delta, delta + n_chunk) three ways, each in its own sequence
    //    (separate KV streams, identical cell layout):
    //      s_inj  the exported blob injected at +delta                                      (the feature under test)
    //      s_add  encoded in place at 0, then moved by llama_memory_seq_add(+delta)         (the in-tree K-shift, i.e. --cache-reuse)
    //      s_ref  encoded in place at delta, same isolated context                          (the pre-registered G1 reference)
    //
    //    G1a (plumbing exactness, always gated): s_inj == s_add BIT-FOR-BIT in K, V and suffix logits. Both start from the same
    //    encode at 0 and go through the same K-shift graph, so any difference is an inject defect, on any model and any weight type.
    //
    //    G1-ref (P0_THRESHOLDS section 2): s_inj vs s_ref. Exact RoPE attention is translation-invariant, but in f32 the q.k of a
    //    chunk encoded at delta differs from the one encoded at 0 in the last ulp, and that propagates through the layers. On the
    //    2-layer generated fixtures it stays at V NMSE <= 1e-19 (visible with CKV_N_CHUNK=512). On a deep k-quant MoE it is
    //    amplified: every matmul re-quantizes its activations to q8 blocks (an ulp on a rounding boundary flips a whole q8 step)
    //    and a flipped router top-k compounds it, so the reference itself drifts (KPF-62.8, 2026-10-22: Qwen3-VL-30B-A3B Q4_K_M,
    //    48 layers, layer-0 K NMSE 7e-15, V NMSE 6e-3 with the injected V bit-identical to the source -- the drift is in the
    //    reference encode, not in the inject). s_add vs s_ref shows the in-tree shift carries the identical drift.
    //    G1-ref gates unless CKV_G1_REF_INFORMATIONAL=1, in which case it is printed with its verdict and not gated.
    const bool ref_info = getenv("CKV_G1_REF_INFORMATIONAL") && *getenv("CKV_G1_REF_INFORMATIONAL") && strcmp(getenv("CKV_G1_REF_INFORMATIONAL"), "0") != 0;
    const int  n_layer  = llama_model_n_layer(model);
    bool g1_ref_pass = true;
    bool g1a_pass    = true;
    for (llama_pos delta : { 1, 17, 300 }) {
        const llama_seq_id s_inj = 1;
        const llama_seq_id s_add = 2;
        const llama_seq_id s_ref = 3;

        CHECK(llama_chunk_kv_inject(ctx, blob.data(), blob.size(), s_inj, delta) == blob.size());

        CHECK(decode(ctx, chunk, 0, s_add, n_vocab));
        llama_memory_seq_add(llama_get_memory(ctx), s_add, 0, -1, delta);

        // in place, same isolated context (no predecessor), same positions
        CHECK(decode(ctx, chunk, delta, s_ref, n_vocab));

        std::vector<float> k_i, v_i, k_a, v_a, k_r, v_r;
        CHECK(read_kv(ctx, s_inj, delta, delta + n_chunk, k_i, v_i));
        CHECK(read_kv(ctx, s_add, delta, delta + n_chunk, k_a, v_a));
        CHECK(read_kv(ctx, s_ref, delta, delta + n_chunk, k_r, v_r));
        CHECK(k_i.size() == k_r.size() && v_i.size() == v_r.size());
        CHECK(k_i.size() == k_a.size() && v_i.size() == v_a.size());

        // V is position-free: it must be a bit-exact copy of the source
        CHECK(v_i == v_src);

        // continuation: decode the suffix on all three and compare logits
        std::vector<float> l_i, l_a, l_r;
        CHECK(decode(ctx, suffix, delta + n_chunk, s_inj, n_vocab, &l_i));
        CHECK(decode(ctx, suffix, delta + n_chunk, s_add, n_vocab, &l_a));
        CHECK(decode(ctx, suffix, delta + n_chunk, s_ref, n_vocab, &l_r));

        // G1a: bit-for-bit
        const bool k_eq = k_i == k_a;
        const bool v_eq = v_i == v_a;
        const bool l_eq = l_i.size() == l_a.size() && memcmp(l_i.data(), l_a.data(), l_i.size()*sizeof(float)) == 0;
        printf("G1a delta=%4d  inject vs seq_add: K %s  V %s  logits %s  (K NMSE=%.3e logits NMSE=%.3e)\n", (int) delta,
                k_eq ? "bit-identical" : "DIFFER", v_eq ? "bit-identical" : "DIFFER", l_eq ? "bit-identical" : "DIFFER",
                nmse(k_i, k_a), nmse(l_i, l_a));
        CHECK(k_eq);
        CHECK(v_eq);
        CHECK(l_eq);
        g1a_pass = g1a_pass && k_eq && v_eq && l_eq;

        // G1-ref
        const double nk = nmse(k_i, k_r);
        const double nv = nmse(v_i, v_r);
        const double nl = nmse(l_i, l_r);
        const double nk_add = nmse(k_a, k_r);
        const double nv_add = nmse(v_a, v_r);
        const double nl_add = nmse(l_a, l_r);

        if (g1_capture.is_open()) {
            const size_t n_layer_pos = (size_t) n_layer;
            const bool captured =
                write_g1_position_rows(g1_capture, delta, "k", "inject_vs_seq_add", k_i, k_a, n_layer_pos,
                                       (size_t) n_chunk, delta) &&
                write_g1_position_rows(g1_capture, delta, "v", "inject_vs_seq_add", v_i, v_a, n_layer_pos,
                                       (size_t) n_chunk, delta) &&
                write_g1_position_rows(g1_capture, delta, "logits", "inject_vs_seq_add", l_i, l_a, 1,
                                       (size_t) n_suffix, delta + n_chunk) &&
                write_g1_position_rows(g1_capture, delta, "k", "inject_vs_in_place_ref", k_i, k_r,
                                       n_layer_pos, (size_t) n_chunk, delta) &&
                write_g1_position_rows(g1_capture, delta, "v", "inject_vs_in_place_ref", v_i, v_r,
                                       n_layer_pos, (size_t) n_chunk, delta) &&
                write_g1_position_rows(g1_capture, delta, "logits", "inject_vs_in_place_ref", l_i, l_r, 1,
                                       (size_t) n_suffix, delta + n_chunk);
            CHECK(captured);
        }

        if (nk > 1e-6 || nv > 1e-6) { // diagnostic: where does the error sit? (V is position-free: any V error is drift of the reference encode)
            const size_t per_k = k_i.size() / n_layer;
            const size_t per_v = v_i.size() / n_layer;
            for (int il = 0; il < n_layer; ++il) {
                std::vector<float> a(k_i.begin() + il*per_k, k_i.begin() + (il+1)*per_k), b(k_r.begin() + il*per_k, k_r.begin() + (il+1)*per_k);
                std::vector<float> c(v_i.begin() + il*per_v, v_i.begin() + (il+1)*per_v), d(v_r.begin() + il*per_v, v_r.begin() + (il+1)*per_v);
                printf("  layer %d K NMSE=%.3e  V NMSE=%.3e\n", il, nmse(a, b), nmse(c, d));
            }
        }

        printf("G1 delta=%4d  K NMSE=%.3e  V NMSE=%.3e  logits NMSE=%.3e   (in-tree seq_add vs ref: K %.3e V %.3e logits %.3e)\n",
                (int) delta, nk, nv, nl, nk_add, nv_add, nl_add);

        // llama-dense from test-llama-archs carries RANDOM rope_freqs (|f| ~ 0.02), which inflates angles 50-3000x and
        // makes f32 trig rounding visible in K; the K gate is informational there (CKV_SKIP_K_GATE=1). Logits still gate.
        const bool skip_k = getenv("CKV_SKIP_K_GATE") && *getenv("CKV_SKIP_K_GATE");
        const bool pass   = (skip_k || nk <= 1e-6) && nv <= 1e-6 && nl <= 1e-5;
        g1_ref_pass = g1_ref_pass && pass;
        if (!ref_info) {
            if (!skip_k) {
                CHECK(nk <= 1e-6);
            }
            CHECK(nv <= 1e-6);
            CHECK(nl <= 1e-5);
        }

        llama_memory_seq_rm(llama_get_memory(ctx), s_inj, -1, -1);
        llama_memory_seq_rm(llama_get_memory(ctx), s_add, -1, -1);
        llama_memory_seq_rm(llama_get_memory(ctx), s_ref, -1, -1);
    }

    // encoder floor without any shift: the same chunk at the same positions [0, n_chunk), re-encoded in two ubatches instead of one.
    // Identical in exact arithmetic; whatever this prints is the reference's own rounding-propagation floor on this model.
    {
        const llama_seq_id s = 4;
        const tokens_t h0(chunk.begin(), chunk.begin() + n_chunk/2);
        const tokens_t h1(chunk.begin() + n_chunk/2, chunk.end());
        CHECK(decode(ctx, h0, 0, s, n_vocab));
        CHECK(decode(ctx, h1, n_chunk/2, s, n_vocab));
        std::vector<float> k, v;
        CHECK(read_kv(ctx, s, 0, n_chunk, k, v));
        printf("floor: same positions, ubatch split %d+%d vs one ubatch: K NMSE=%.3e  V NMSE=%.3e\n",
                n_chunk/2, n_chunk - n_chunk/2, nmse(k, k_src), nmse(v, v_src));
        llama_memory_seq_rm(llama_get_memory(ctx), s, -1, -1);
    }

    printf("VERDICT G1a (inject == in-tree seq_add, bit-for-bit): %s\n", g1a_pass ? "PASS" : "FAIL");
    printf("VERDICT G1-ref (pre-registered, ref = encode in place at delta; K/V <= 1e-6, logits <= 1e-5): %s%s\n",
            g1_ref_pass ? "PASS" : "FAIL", ref_info ? " (informational: CKV_G1_REF_INFORMATIONAL=1)" : "");
    if (g1_capture.is_open()) {
        g1_capture.flush();
        CHECK((bool) g1_capture);
    }

    // 4. delta = 0 is an exact copy (no rotation is queued), also for a range that does not start at 0
    {
        const llama_seq_id s = 7;
        CHECK(llama_chunk_kv_inject(ctx, blob.data(), blob.size(), s, 0) == blob.size());
        std::vector<float> k, v;
        CHECK(read_kv(ctx, s, 0, n_chunk, k, v));
        CHECK(k == k_src);
        CHECK(v == v_src);
        llama_memory_seq_rm(llama_get_memory(ctx), s, -1, -1);

        // [8, 24) of seq 0 re-placed at +100: positions 108..123, V identical to the source's V[8..24)
        const size_t need2 = llama_chunk_kv_export(ctx, nullptr, 0, 0, 8, 24);
        CHECK(need2 > 0 && need2 < need);
        std::vector<uint8_t> blob2(need2);
        CHECK(llama_chunk_kv_export(ctx, blob2.data(), blob2.size(), 0, 8, 24) == need2);
        CHECK(llama_chunk_kv_inject(ctx, blob2.data(), blob2.size(), s, 100) == blob2.size());
        std::vector<float> k2, v2, ks, vs;
        CHECK(read_kv(ctx, s, 108, 124, k2, v2));
        CHECK(read_kv(ctx, 0, 8, 24, ks, vs));
        CHECK(v2 == vs);
        CHECK(llama_memory_seq_pos_min(llama_get_memory(ctx), s) == 108);
        CHECK(llama_memory_seq_pos_max(llama_get_memory(ctx), s) == 123);
        llama_memory_seq_rm(llama_get_memory(ctx), s, -1, -1);
    }

    // 5. refusals leave the cache untouched
    {
        const llama_seq_id s = 7;
        CHECK(llama_chunk_kv_inject(ctx, blob.data(), blob.size(), s, 50) == blob.size());
        // overlapping range in the same sequence
        CHECK(llama_chunk_kv_inject(ctx, blob.data(), blob.size(), s, 60) == 0);
        CHECK(llama_memory_seq_pos_min(llama_get_memory(ctx), s) == 50);
        CHECK(llama_memory_seq_pos_max(llama_get_memory(ctx), s) == 50 + n_chunk - 1);
        // an adjacent, non-overlapping second chunk is accepted (multi-chunk assembly)
        CHECK(llama_chunk_kv_inject(ctx, blob.data(), blob.size(), s, 50 + n_chunk) == blob.size());
        CHECK(llama_memory_seq_pos_max(llama_get_memory(ctx), s) == 50 + 2*n_chunk - 1);
        // negative start
        CHECK(llama_chunk_kv_inject(ctx, blob.data(), blob.size(), 6, -5) == 0);
        // corrupt magic
        std::vector<uint8_t> bad = blob;
        bad[0] ^= 0xff;
        CHECK(llama_chunk_kv_inject(ctx, bad.data(), bad.size(), 6, 5) == 0);
        // truncated blob
        CHECK(llama_chunk_kv_inject(ctx, blob.data(), blob.size() / 2, 6, 5) == 0);
        CHECK(llama_memory_seq_pos_max(llama_get_memory(ctx), 6) < 0);
        // Reject invalid IDs, overflow and serialized cells outside their header range.
        CHECK(llama_chunk_kv_export(ctx, nullptr, 0, -1, 0, 1) == 0);
        CHECK(llama_chunk_kv_inject(ctx, blob.data(), blob.size(), -1, 0) == 0);
        CHECK(llama_chunk_kv_read_f32(ctx, -1, 0, 1, nullptr, nullptr, nullptr) == 0);
        CHECK(llama_chunk_kv_inject(ctx, blob.data(), blob.size(), 6, std::numeric_limits<llama_pos>::max()) == 0);
        std::vector<uint8_t> bad_pos = blob;
        const size_t first_pos_offset = sizeof(uint32_t) + 2*sizeof(llama_pos) + sizeof(uint32_t);
        CHECK(bad_pos.size() >= first_pos_offset + sizeof(llama_pos));
        if (bad_pos.size() >= first_pos_offset + sizeof(llama_pos)) {
            const llama_pos outside = n_chunk;
            memcpy(bad_pos.data() + first_pos_offset, &outside, sizeof(outside));
            CHECK(llama_chunk_kv_inject(ctx, bad_pos.data(), bad_pos.size(), 6, 5) == 0);
            CHECK(llama_memory_seq_pos_max(llama_get_memory(ctx), 6) < 0);
        }
        // a hole in the source range refuses the export
        llama_memory_seq_rm(llama_get_memory(ctx), 0, 12, 13);
        CHECK(llama_chunk_kv_export(ctx, nullptr, 0, 0, 8, 24) == 0);
        CHECK(llama_chunk_kv_export(ctx, nullptr, 0, 0, 0, 12) > 0);
        llama_memory_seq_rm(llama_get_memory(ctx), s, -1, -1);
    }

    llama_free(ctx);
}

// OFF means identical: a context that exported and was refused an inject decodes bit-for-bit like one that never
// touched the API
static void test_off_identical(const common_params & params, llama_model * model, int n_vocab) {
    std::mt19937 rng(99);
    const tokens_t a = rand_tokens(rng, 20, n_vocab);
    const tokens_t b = rand_tokens(rng, 8,  n_vocab);

    llama_context * c1 = make_ctx(params, model);
    llama_context * c2 = make_ctx(params, model);
    CHECK(c1 && c2);
    if (!c1 || !c2) return;

    std::vector<float> l1, l2;
    CHECK(decode(c1, a, 0, 0, n_vocab));
    CHECK(decode(c2, a, 0, 0, n_vocab));

    std::vector<uint8_t> blob(1 << 22);
    const size_t n = llama_chunk_kv_export(c2, blob.data(), blob.size(), 0, 0, 20);
    (void) n;
    CHECK(llama_chunk_kv_inject(c2, blob.data(), 12, 1, 5) == 0); // truncated -> refused

    CHECK(decode(c1, b, 20, 0, n_vocab, &l1));
    CHECK(decode(c2, b, 20, 0, n_vocab, &l2));
    CHECK(l1.size() == l2.size() && memcmp(l1.data(), l2.data(), l1.size()*sizeof(float)) == 0);

    llama_free(c1);
    llama_free(c2);
}

int main(int argc, char ** argv) {
    std::setlocale(LC_NUMERIC, "C");

    std::string g1_capture_path;
    std::vector<char *> llama_argv = { argv[0] };
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--g1-capture-jsonl") == 0) {
            if (i + 1 >= argc || !g1_capture_path.empty()) {
                fprintf(stderr, "--g1-capture-jsonl needs one path and may be specified once\n");
                return 2;
            }
            g1_capture_path = argv[++i];
        } else {
            llama_argv.push_back(argv[i]);
        }
    }
    llama_argv.push_back(nullptr);

    common_params params;
    params.sampling.seed = 1234;
    params.n_predict = 1;

    common_init();

    if (!common_params_parse((int) llama_argv.size() - 1, llama_argv.data(), params, LLAMA_EXAMPLE_COMMON)) {
        return 1;
    }

    ggml_backend_load_all();

    common_init_result_ptr llama_init = common_init_from_params(params);
    llama_model * model = llama_init->model();
    if (model == nullptr) {
        fprintf(stderr, "%s : failed to init model\n", __func__);
        return 1;
    }

    const int n_vocab = llama_vocab_n_tokens(llama_model_get_vocab(model));

    const bool attention_only = !llama_model_is_recurrent(model) && !llama_model_is_hybrid(model);

    if (attention_only) {
        test_attention(params, model, n_vocab, g1_capture_path);
    } else {
        if (!g1_capture_path.empty()) {
            fprintf(stderr, "G1 capture requires an attention-only model\n");
            return 2;
        }
        test_refusal(params, model, n_vocab);
    }
    test_off_identical(params, model, n_vocab);

    if (n_fail) {
        fprintf(stderr, "%d check(s) failed\n", n_fail);
        return 1;
    }
    printf("OK (%s)\n", attention_only ? "attention-only" : "refusal");
    return 0;
}
