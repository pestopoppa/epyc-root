// test-fa-rowexact.cpp: [AKX-ALL-LB4] CPU FLASH_ATTN_EXT: candidate vs reference, and row-exactness N=1 vs N=5.
//
// AKX-ALL-LB4.2: the first version compared the build under test only with itself (N=1 vs N=5) and
// used a binary {0, -inf} causal mask, so it could not see the iqk kernel reading the additive
// FLASH_ATTN_EXT mask as binary (fixed in 629b545e0). This version, per (K/V type, n_kv, mask kind):
//
//   candidate  N=5, and N=1 per row, on the normal CPU path: the iqk kernel when compiled in and
//              enabled (counted through the CPU backend's ggml_backend_cpu_iqk_fa_n_calls), else the
//              ggml kernel
//   reference  N=5 with cplan.use_ref = true: the mainline ggml vec kernel (iqk never runs under
//              use_ref). Its F16-V accumulator is FP32 here (GGML_FA_VKQ_F32=1 is set before the first
//              compute unless --ref-vkq default): the default FP16 accumulator is ~7e-4 off at long n_kv
//              (AKX-ALL-LB4.3) and would hide the candidate's error behind the reference's own
//   oracle     double-precision softmax(scale*q.k + mask) v over the dequantised K/V (exact f32 Q)
//
// Gate (verdict=PASS): the candidate N=5 and every candidate N=1 row within NMSE <= tol of the
// reference, the candidate N=5 within tol of the oracle, everything finite, and the iqk kernel ran
// exactly when expected (every candidate compute counted when it is on, none when it is off, and
// never for the reference). Row-exactness (N=1 vs N=5 bytes) is RECORDED
// (rowexact=ROW_EXACT|NOT_ROW_EXACT), never gated: the kernels pick different paths per N (ggml:
// split-KV only at N=1 for f16 at n_kv >= 512; iqk: the GQA split-KV path only at N=1).
//
// Mask kinds (--masks, default all five):
//   causal    binary verify edge: row r sees [0, n_kv - N + r] (0), the rest -inf (the old mask)
//   additive  the causal edge, with uniform finite values in [-1, 1] on every visible cell
//   ragged    additive values; per-row extents that end in different 32-cell KV blocks (the last
//             block is -inf in rows 1-4 but not in row 0), one block -inf in every row (middle) and
//             one block -inf in rows 1 and 3 only
//   finite    no -inf anywhere: an ALiBi-like ramp from 0 (newest cell) to -16 (oldest) plus noise
//             (a reader that treats any non-zero mask value as masked sees every cell masked)
//   deadrow   additive causal rows, except row 0 is -inf everywhere (expected output: zeros)
//   emptytg   every row -inf everywhere (AKX-ALL-LB4.7): each N=1 call is an empty TG row; at n_kv > 256
//             the iqk runtime range trim narrows nek1 to 0 (ik_llama master aborts there, #1923), at
//             n_kv 256 there is no trim and the row goes through a split-KV combine with every partial
//             fully masked. Expected output: zeros, equal to the mainline reference
//   swa       sliding window (AKX-ALL-LB4.8): row r sees the W cells ending at its causal edge,
//             (n_kv - N + r - W, n_kv - N + r], additive values, -inf elsewhere. "swa" is W = n_kv/2;
//             "swa:W" sets W (e.g. swa:7000). W <= 3/4 n_kv: the iqk N=1 range trim cuts both ends
//             (trailing trim). W > 3/4 n_kv (n_kv 8192, swa:7000): no trim, so the N=1 split-KV path
//             sees the ~1188-cell masked prefix: whole leading chunks fully masked once the chunks are
//             shorter (default heads: 16+ threads, 1024-cell chunks), masked leading k-blocks inside
//             the first chunk below that. At N=5 with q8_0 K, a thread that owns all 5 rows of a head
//             (threads dividing the Q head count: 1, 4, 8 at 24 heads) runs the q_step 4 tile through
//             the q_step >= 4 Q8_0 repack branch (the ik_llama #1205 failure class)
//
// Every candidate output is NaN-filled before its compute (AKX-ALL-LB4.7), so a kernel that leaves a
// row unwritten is finite=0, never a pass on stale memory. --stale-control is the positive control:
// the candidates stay NaN-filled and are never computed, so every RESULT line must read
// "control=stale ... finite=0 ... verdict=FAIL" (exit 1).
//
// Row-exactness is not an iqk property (AKX-ALL-LB4.8): the iqk split-KV paths run only at
// neq1 == 1, and their partition depends on the thread count and on the mask-driven range trim, so
// N=1 vs N=5 bytes differ by design. rowexact=NOT_ROW_EXACT is the EXPECTED iqk verdict, and the fold
// gate is the tolerance route against the use_ref reference and the oracle, never byte identity.
//
// Shape: the Q38FN-class CPU long-context attention (D 256, 2 KV heads, GQA 12). Inputs deterministic.
// The iqk split-KV combines run at N=1 only. --kv-heads 1 reaches the nek2 == 1 ones: at n_kv 256
// (8 KV chunks, GQA 12) P1 with 1-2 threads and P2 with 4, 8 or 16; the default 2 reaches the GQA one
// (P3) while 2*n_kv >= 32*threads. So deadrow or emptytg at n_kv 256 with FA_ROWEXACT_THREADS <= 16
// sends a fully masked N=1 row through a split-KV combine (no range trim below n_kv 288).
//
// usage: test-fa-rowexact [--iqk-fa 0|1] [--masks k1,k2,..] [--tol X] [--ref-vkq f32|default]
//                         [--kv-heads N] [--gqa N] [--stale-control] [n_kv ...]
//        (default n_kv: 8192 65536; --iqk-fa unset = the build default, on when compiled in;
//         default masks: causal,additive,ragged,finite,deadrow; n_kv a multiple of 32, >= 256)
//   env  FA_ROWEXACT_THREADS (default 8), FA_ROWEXACT_TYPES=f16,q8_0 (default both)
// One RESULT line per (type, n_kv, mask): types x n_kv x masks lines. Exit 0 iff every case is PASS,
// 1 if any FAIL, 2 on a setup error (bad argument, --iqk-fa 1 on a build without the iqk kernel,
// allocation or compute failure).

#include "ggml.h"
#include "ggml-cpu.h"
#include "ggml-backend.h"
// C5 lacks optional iqk flash counter typedefs. Resolve may return null; no iqk claim.
typedef void (*ggml_backend_cpu_set_iqk_fa_t)(bool);
typedef bool (*ggml_backend_cpu_get_iqk_fa_t)(void);
typedef uint64_t (*ggml_backend_cpu_iqk_fa_n_calls_t)(void);

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <thread>
#include <vector>

static constexpr int64_t D      = 256;
static int64_t           NH_KV  = 2;            // --kv-heads (AKX-ALL-LB4.7: 1 reaches the nek2 == 1 iqk paths)
static int64_t           GQA    = 12;           // --gqa
static int64_t           NH_Q   = NH_KV * GQA;  // set again after the arguments are parsed
static constexpr int64_t NQ     = 5;
static constexpr int64_t KV_BLK = 32;

static uint64_t g_state = 0x9E3779B97F4A7C15ull;
static float rnd(float lo, float hi) {
    g_state ^= g_state << 13; g_state ^= g_state >> 7; g_state ^= g_state << 17;
    const double u = (double) (g_state >> 11) * 0x1.0p-53;
    return (float) (lo + (hi - lo) * u);
}

// ---------------------------------------------------------------- iqk runtime switch (AKX-ALL-LB4.5)
static ggml_backend_cpu_set_iqk_fa_t     g_set_iqk  = nullptr;
static ggml_backend_cpu_get_iqk_fa_t     g_get_iqk  = nullptr;
static ggml_backend_cpu_iqk_fa_n_calls_t g_iqk_ncal = nullptr;

static void resolve_iqk() {
    ggml_backend_reg_t reg = ggml_backend_cpu_reg();
    g_set_iqk  = (ggml_backend_cpu_set_iqk_fa_t)     ggml_backend_reg_get_proc_address(reg, "ggml_backend_cpu_set_iqk_fa");
    g_get_iqk  = (ggml_backend_cpu_get_iqk_fa_t)     ggml_backend_reg_get_proc_address(reg, "ggml_backend_cpu_get_iqk_fa");
    g_iqk_ncal = (ggml_backend_cpu_iqk_fa_n_calls_t) ggml_backend_reg_get_proc_address(reg, "ggml_backend_cpu_iqk_fa_n_calls");
}
static bool     iqk_on()    { return g_get_iqk && g_get_iqk(); }
static uint64_t iqk_calls() { return g_iqk_ncal ? g_iqk_ncal() : 0; }

// ---------------------------------------------------------------- inputs
static void fill_kv(ggml_tensor * t, int64_t n_kv) {
    std::vector<float> src(D * n_kv * NH_KV);
    for (auto & x : src) { x = rnd(-1.0f, 1.0f); }
    if (t->type == GGML_TYPE_F16) {
        ggml_fp32_to_fp16_row(src.data(), (ggml_fp16_t *) t->data, (int64_t) src.size());
    } else {
        ggml_quantize_chunk(t->type, src.data(), t->data, 0, n_kv * NH_KV, D, nullptr);
    }
}

// mask value for row r (0..NQ-1), cell j; -INFINITY = masked
static float mask_value(const std::string & kind, int64_t n_kv, int64_t r, int64_t j) {
    const int64_t causal_last = n_kv - NQ + r;
    if (kind == "causal") {
        return j <= causal_last ? 0.0f : -INFINITY;
    }
    if (kind == "additive") {
        return j <= causal_last ? rnd(-1.0f, 1.0f) : -INFINITY;
    }
    if (kind == "deadrow") {
        if (r == 0) { return -INFINITY; }
        return j <= causal_last ? rnd(-1.0f, 1.0f) : -INFINITY;
    }
    if (kind == "emptytg") {
        return -INFINITY;
    }
    if (kind == "swa" || kind.rfind("swa:", 0) == 0) {
        int64_t w = n_kv / 2;
        if (kind != "swa") {
            char * end = nullptr;
            w = strtoll(kind.c_str() + 4, &end, 10);
            if (end == kind.c_str() + 4 || *end != '\0' || w < 1) {
                fprintf(stderr, "mask kind '%s': the window must be a positive integer (swa:W)\n", kind.c_str());
                exit(2);
            }
        }
        return j <= causal_last && j > causal_last - w ? rnd(-1.0f, 1.0f) : -INFINITY;
    }
    if (kind == "ragged") {
        const int64_t nb   = n_kv / KV_BLK;
        // row 0 sees every cell; rows 1-4 end 53, 79, 131, 157 cells before the end (blocks nb-2, nb-3, nb-5, nb-5)
        const int64_t last = n_kv - 1 - r * (KV_BLK + 7) - (r % 2) * 13;
        const int64_t hole = nb / 2;                    // block -inf in every row
        const int64_t part = nb / 3;                    // block -inf in rows 1 and 3 only
        const int64_t b    = j / KV_BLK;
        if (j > last)                          { return -INFINITY; }
        if (b == hole)                         { return -INFINITY; }
        if (b == part && (r == 1 || r == 3))   { return -INFINITY; }
        return rnd(-1.0f, 1.0f);
    }
    if (kind == "finite") {
        return -16.0f * (float) (n_kv - 1 - j) / (float) n_kv + rnd(-0.5f, 0.5f);
    }
    fprintf(stderr, "unknown mask kind '%s' (causal, additive, ragged, finite, deadrow, emptytg, swa, swa:W)\n", kind.c_str());
    exit(2);
}

// ---------------------------------------------------------------- compute helpers
static bool compute(ggml_context * ctx, ggml_tensor * out, int n_threads, bool use_ref) {
    ggml_cgraph * g = ggml_new_graph(ctx);
    ggml_build_forward_expand(g, out);
    ggml_cplan plan = ggml_graph_plan(g, n_threads, nullptr);
    std::vector<uint8_t> work(plan.work_size + 1);
    plan.work_data = work.data();
    plan.use_ref   = use_ref;
    return ggml_graph_compute(g, &plan) == GGML_STATUS_SUCCESS;
}

// out [D, NH_Q, N, 1]: element (d, h, r)
static inline float out_at(const ggml_tensor * t, int64_t d, int64_t h, int64_t r) {
    return *(const float *) ((const char *) t->data + r*t->nb[2] + h*t->nb[1] + d*sizeof(float));
}

struct err_acc {
    double num = 0.0, den = 0.0, max_abs = 0.0;
    bool finite = true;
    void add(double a, double b) {
        if (!std::isfinite(a) || !std::isfinite(b)) { finite = false; return; }
        num += (a - b) * (a - b);
        den += b * b;
        max_abs = std::max(max_abs, std::fabs(a - b));
    }
    // NMSE as test-backend-ops: sum (a-b)^2 / sum b^2; an all-zero reference matched exactly = 0
    double nmse() const { return den > 0.0 ? num / den : (num > 0.0 ? INFINITY : 0.0); }
};

// AKX-ALL-LB4.7: every candidate output starts as NaN, so a kernel that skips writing a row (stale
// dst) shows up as finite=0 instead of passing on whatever the allocator left there
static void nan_fill(ggml_tensor * t) {
    float * x = (float *) t->data;
    for (int64_t i = 0; i < ggml_nelements(t); ++i) { x[i] = NAN; }
}

static bool g_stale_control = false; // --stale-control: candidates are NaN-filled and never computed
static bool g_mutate_control = false; // fixture-only finite output corruption; never changes kernel

// returns 0 PASS, 1 FAIL, 2 setup error
static int run_case(ggml_type type_kv, int64_t n_kv, const std::string & mkind, int n_threads, double tol) {
    const size_t kv_bytes = ggml_row_size(type_kv, D) * n_kv * NH_KV;
    const size_t mem = 2*kv_bytes + (size_t) (2*NQ + 1) * n_kv * sizeof(ggml_fp16_t) +
                       (size_t) 64 * D * NH_Q * NQ * sizeof(float) + (size_t) 256 * 1024 * 1024;
    ggml_init_params ip = { mem, nullptr, false };
    ggml_context * ctx = ggml_init(ip);
    if (!ctx) { fprintf(stderr, "ggml_init(%zu) failed\n", mem); return 2; }

    ggml_tensor * q  = ggml_new_tensor_4d(ctx, GGML_TYPE_F32, D, NQ, NH_Q, 1);
    ggml_tensor * k  = ggml_new_tensor_4d(ctx, type_kv, D, n_kv, NH_KV, 1);
    ggml_tensor * v  = ggml_new_tensor_4d(ctx, type_kv, D, n_kv, NH_KV, 1);
    ggml_tensor * m5 = ggml_new_tensor_4d(ctx, GGML_TYPE_F16, n_kv, NQ, 1, 1);
    for (int64_t i = 0; i < ggml_nelements(q); ++i) { ((float *) q->data)[i] = rnd(-1.0f, 1.0f); }
    fill_kv(k, n_kv);
    fill_kv(v, n_kv);
    for (int64_t r = 0; r < NQ; ++r) {
        ggml_fp16_t * row = (ggml_fp16_t *) ((char *) m5->data + r*m5->nb[1]);
        for (int64_t j = 0; j < n_kv; ++j) { row[j] = ggml_fp32_to_fp16(mask_value(mkind, n_kv, r, j)); }
    }

    const float scale = 1.0f / sqrtf((float) D);
    const bool  iqk_expected = iqk_on();
    bool        iqk_count_ok = true;
    uint64_t    iqk_n = 0;

    // candidate N=5
    ggml_tensor * out5 = ggml_flash_attn_ext(ctx, q, k, v, m5, scale, 0.0f, 0.0f);
    ggml_flash_attn_ext_set_prec(out5, GGML_PREC_F32);
    nan_fill(out5);
    uint64_t c0 = iqk_calls();
    if (!g_stale_control && !compute(ctx, out5, n_threads, false)) { ggml_free(ctx); return 2; }
    uint64_t dc = iqk_calls() - c0;
    iqk_n += dc;
    if ((dc > 0) != iqk_expected) { iqk_count_ok = false; }

    // reference N=5: the mainline ggml vec kernel under use_ref
    ggml_tensor * ref5 = ggml_flash_attn_ext(ctx, q, k, v, m5, scale, 0.0f, 0.0f);
    ggml_flash_attn_ext_set_prec(ref5, GGML_PREC_F32);
    c0 = iqk_calls();
    if (!compute(ctx, ref5, n_threads, true)) { ggml_free(ctx); return 2; }
    const bool ref_used_iqk = iqk_calls() != c0;

    err_acc e_c5_ref;
    double  c1_ref_nmse_max = 0.0;
    double  n1_n5_max_abs   = 0.0;
    bool    c1_finite       = true;
    std::vector<ggml_tensor *> out1_rows;
    int     n_diff_rows     = 0;
    for (int64_t r = 0; r < NQ; ++r) {
        for (int64_t h = 0; h < NH_Q; ++h) {
            for (int64_t d = 0; d < D; ++d) { e_c5_ref.add(out_at(out5, d, h, r), out_at(ref5, d, h, r)); }
        }
        // candidate N=1 for row r (same K/V, that row's mask)
        ggml_tensor * qr = ggml_view_4d(ctx, q, D, 1, NH_Q, 1, q->nb[1], q->nb[2], q->nb[3], r*q->nb[1]);
        ggml_tensor * mr = ggml_new_tensor_4d(ctx, GGML_TYPE_F16, n_kv, 1, 1, 1);
        memcpy(mr->data, (char *) m5->data + r*m5->nb[1], n_kv*sizeof(ggml_fp16_t));
        ggml_tensor * out1 = ggml_flash_attn_ext(ctx, qr, k, v, mr, scale, 0.0f, 0.0f);
        ggml_flash_attn_ext_set_prec(out1, GGML_PREC_F32);
        nan_fill(out1);
        c0 = iqk_calls();
        if (!g_stale_control && !compute(ctx, out1, n_threads, false)) { ggml_free(ctx); return 2; }
        if (g_mutate_control) { ((float *) out1->data)[0] += 1.0f; }
        out1_rows.push_back(out1);
        dc = iqk_calls() - c0;
        iqk_n += dc;
        if ((dc > 0) != iqk_expected) { iqk_count_ok = false; }

        err_acc e_row_ref, e_row_x;
        for (int64_t h = 0; h < NH_Q; ++h) {
            for (int64_t d = 0; d < D; ++d) {
                e_row_ref.add(out_at(out1, d, h, 0), out_at(ref5, d, h, r));
                e_row_x.add(out_at(out1, d, h, 0), out_at(out5, d, h, r));
            }
        }
        const float * a = (const float *) ((const char *) out5->data + r*out5->nb[2]);
        const bool same = memcmp(a, out1->data, D*NH_Q*sizeof(float)) == 0;
        if (!same) { n_diff_rows++; }
        c1_ref_nmse_max = std::max(c1_ref_nmse_max, e_row_ref.nmse());
        c1_finite       = c1_finite && e_row_ref.finite && e_row_x.finite;
        n1_n5_max_abs   = std::max(n1_n5_max_abs, e_row_x.max_abs);
        printf("  type=%s n_kv=%lld mask=%s row=%lld bitexact_n1_n5=%d max_abs_n1_n5=%.3e nmse_n1_ref=%.3e\n",
               ggml_type_name(type_kv), (long long) n_kv, mkind.c_str(), (long long) r, (int) same,
               e_row_x.max_abs, e_row_ref.nmse());
    }

    // oracle: double precision over the dequantised K/V, exact f32 Q, the fp16 mask values
    std::vector<float> kf((size_t) D * n_kv * NH_KV), vf((size_t) D * n_kv * NH_KV);
    {
        const auto * tr = ggml_get_type_traits(type_kv);
        for (int64_t row = 0; row < n_kv * NH_KV; ++row) {
            tr->to_float((const char *) k->data + row*k->nb[1], kf.data() + row*D, D);
            tr->to_float((const char *) v->data + row*v->nb[1], vf.data() + row*D, D);
        }
    }
    std::vector<float> mf((size_t) NQ * n_kv);
    for (int64_t r = 0; r < NQ; ++r) {
        const ggml_fp16_t * row = (const ggml_fp16_t *) ((const char *) m5->data + r*m5->nb[1]);
        for (int64_t j = 0; j < n_kv; ++j) { mf[r*n_kv + j] = ggml_fp16_to_fp32(row[j]); }
    }
    std::vector<double> oracle((size_t) NQ * NH_Q * D, 0.0);
    {
        const int64_t n_tasks = NQ * NH_Q;
        const int nt = std::max(1, std::min<int>(n_threads, (int) n_tasks));
        std::vector<std::thread> workers;
        for (int t = 0; t < nt; ++t) {
            workers.emplace_back([&, t]() {
                std::vector<double> s(n_kv), acc(D);
                for (int64_t task = t; task < n_tasks; task += nt) {
                    const int64_t r = task / NH_Q, h = task % NH_Q, hk = h / GQA;
                    const float * qv = (const float *) ((const char *) q->data + h*q->nb[2] + r*q->nb[1]);
                    double M = -INFINITY;
                    for (int64_t j = 0; j < n_kv; ++j) {
                        const float mv = mf[r*n_kv + j];
                        if (std::isinf(mv) && mv < 0.0f) { s[j] = -INFINITY; continue; }
                        const float * kr = kf.data() + (hk*n_kv + j)*D;
                        double dot = 0.0;
                        for (int64_t d = 0; d < D; ++d) { dot += (double) qv[d] * kr[d]; }
                        s[j] = (double) scale * dot + mv;
                        M = std::max(M, s[j]);
                    }
                    std::fill(acc.begin(), acc.end(), 0.0);
                    double S = 0.0;
                    if (M != -INFINITY) {
                        for (int64_t j = 0; j < n_kv; ++j) {
                            if (s[j] == -INFINITY) { continue; }
                            const double w = std::exp(s[j] - M);
                            S += w;
                            const float * vr = vf.data() + (hk*n_kv + j)*D;
                            for (int64_t d = 0; d < D; ++d) { acc[d] += w * vr[d]; }
                        }
                    }
                    for (int64_t d = 0; d < D; ++d) { oracle[(r*NH_Q + h)*D + d] = S > 0.0 ? acc[d] / S : 0.0; }
                }
            });
        }
        for (auto & w : workers) { w.join(); }
    }
    err_acc e_c5_or, e_ref_or;
    std::vector<err_acc> e_c1_or(NQ);
    for (int64_t r = 0; r < NQ; ++r) {
        for (int64_t h = 0; h < NH_Q; ++h) {
            for (int64_t d = 0; d < D; ++d) {
                const double o = oracle[(r*NH_Q + h)*D + d];
                e_c5_or.add(out_at(out5, d, h, r), o);
                e_c1_or[r].add(out_at(out1_rows[r], d, h, 0), o);
                e_ref_or.add(out_at(ref5, d, h, r), o);
            }
        }
    }
    ggml_free(ctx);

    double c1_oracle_nmse_max = 0.0;
    bool c1_oracle_finite = true;
    for (const auto & e : e_c1_or) { c1_oracle_nmse_max = std::max(c1_oracle_nmse_max, e.nmse()); c1_oracle_finite = c1_oracle_finite && e.finite; }
    const bool finite = e_c5_ref.finite && c1_finite && e_c5_or.finite && e_ref_or.finite && c1_oracle_finite;
    const bool pass   = finite && iqk_count_ok && !ref_used_iqk &&
                        e_c5_ref.nmse() <= tol && c1_ref_nmse_max <= tol && e_c5_or.nmse() <= tol && c1_oracle_nmse_max <= tol;
    printf("ORACLE_1ROW max_nmse=%.9g tol=%.9g finite=%d mutation=%d\n", c1_oracle_nmse_max, tol, (int) c1_oracle_finite, (int) g_mutate_control);
    printf("RESULT %stype=%s n_kv=%lld mask=%s D=%lld kv_heads=%lld gqa=%lld N=%lld iqk=%s iqk_calls=%llu iqk_count_ok=%d ref_used_iqk=%d "
           "nmse_cand_ref=%.3e max_abs_cand_ref=%.3e nmse_cand1_ref_max=%.3e nmse_cand_oracle=%.3e nmse_ref_oracle=%.3e "
           "rows_differing=%d max_abs_n1_n5=%.3e rowexact=%s finite=%d tol=%.1e verdict=%s\n",
           g_stale_control ? "control=stale " : "",
           ggml_type_name(type_kv), (long long) n_kv, mkind.c_str(), (long long) D, (long long) NH_KV, (long long) GQA, (long long) NQ,
           iqk_expected ? "on" : "off", (unsigned long long) iqk_n, (int) iqk_count_ok, (int) ref_used_iqk,
           e_c5_ref.nmse(), e_c5_ref.max_abs, c1_ref_nmse_max, e_c5_or.nmse(), e_ref_or.nmse(),
           n_diff_rows, n1_n5_max_abs, n_diff_rows == 0 ? "ROW_EXACT" : "NOT_ROW_EXACT", (int) finite, tol,
           pass ? "PASS" : "FAIL");
    fflush(stdout);
    return pass ? 0 : 1;
}

static std::vector<std::string> split_csv(const std::string & s) {
    std::vector<std::string> out;
    size_t p = 0;
    while (p <= s.size()) {
        const size_t c = s.find(',', p);
        const std::string t = s.substr(p, c == std::string::npos ? std::string::npos : c - p);
        if (!t.empty()) { out.push_back(t); }
        if (c == std::string::npos) { break; }
        p = c + 1;
    }
    return out;
}

int main(int argc, char ** argv) {
    std::vector<int64_t>     kvs;
    std::vector<std::string> masks = { "causal", "additive", "ragged", "finite", "deadrow" };
    int    iqk_arg     = -1;
    double tol         = 5e-4;   // test-backend-ops FLASH_ATTN_EXT max_nmse_err
    bool   ref_vkq_f32 = true;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        auto next = [&]() -> std::string {
            if (i + 1 >= argc) { fprintf(stderr, "%s needs a value\n", a.c_str()); exit(2); }
            return argv[++i];
        };
        if (a == "--iqk-fa") {
            const std::string v = next();
            if (v == "1" || v == "on") { iqk_arg = 1; } else if (v == "0" || v == "off") { iqk_arg = 0; }
            else { fprintf(stderr, "--iqk-fa expects 0|1\n"); return 2; }
        } else if (a == "--masks") {
            masks = split_csv(next());
            for (const auto & m : masks) { mask_value(m, 4*KV_BLK, 0, 0); } // validates the names (exits 2)
        } else if (a == "--kv-heads") {
            NH_KV = atoll(next().c_str());
            if (NH_KV < 1) { fprintf(stderr, "--kv-heads expects a positive integer\n"); return 2; }
        } else if (a == "--gqa") {
            GQA = atoll(next().c_str());
            if (GQA < 1) { fprintf(stderr, "--gqa expects a positive integer\n"); return 2; }
        } else if (a == "--stale-control") {
            g_stale_control = true;
        } else if (a == "--mutate-output") {
            g_mutate_control = true;
        } else if (a == "--tol") {
            tol = atof(next().c_str());
        } else if (a == "--ref-vkq") {
            const std::string v = next();
            if (v == "f32") { ref_vkq_f32 = true; } else if (v == "default") { ref_vkq_f32 = false; }
            else { fprintf(stderr, "--ref-vkq expects f32|default\n"); return 2; }
        } else if (!a.empty() && a[0] == '-') {
            fprintf(stderr, "unknown option %s\n", a.c_str());
            return 2;
        } else {
            kvs.push_back(atoll(a.c_str()));
        }
    }
    if (kvs.empty()) { kvs = { 8192, 65536 }; }
    NH_Q = NH_KV * GQA;
    g_state = 0x9E3779B97F4A7C15ull; // the --masks validation above consumed random numbers

    // The ggml kernel reads GGML_FA_VKQ_F32 once, at its first FLASH_ATTN_EXT: set it before any compute.
    // It affects the ggml kernel only (the reference, and the candidate when iqk is off), never iqk.
    if (ref_vkq_f32) { setenv("GGML_FA_VKQ_F32", "1", 0); }

    resolve_iqk();
    if (iqk_arg == 1 && !g_set_iqk) {
        fprintf(stderr, "--iqk-fa 1: this build has no iqk CPU flash attention (-DGGML_IQK_FLASH_ATTENTION=OFF)\n");
        printf("RESULT verdict=NO_IQK\n");
        return 2;
    }
    if (iqk_arg >= 0 && g_set_iqk) { g_set_iqk(iqk_arg == 1); }

    int n_threads = 8;
    if (const char * e = getenv("FA_ROWEXACT_THREADS")) { n_threads = atoi(e); }
    std::string types = "f16,q8_0";
    if (const char * e = getenv("FA_ROWEXACT_TYPES")) { types = e; }

    printf("test-fa-rowexact: threads=%d iqk=%s kv_heads=%lld gqa=%lld%s GGML_FA_VKQ_F32=%s GGML_FA_SPLIT_KV=%s tol=%.1e masks=",
           n_threads, !g_set_iqk ? "not_compiled" : (iqk_on() ? "on" : "off"), (long long) NH_KV, (long long) GQA,
           g_stale_control ? " control=stale" : "",
           getenv("GGML_FA_VKQ_F32") ? getenv("GGML_FA_VKQ_F32") : "(unset)",
           getenv("GGML_FA_SPLIT_KV") ? getenv("GGML_FA_SPLIT_KV") : "(unset)", tol);
    for (size_t i = 0; i < masks.size(); ++i) { printf("%s%s", i ? "," : "", masks[i].c_str()); }
    printf("\n");

    int rc = 0;
    for (const char * tname : { "f16", "q8_0" }) {
        if (types.find(tname) == std::string::npos) { continue; }
        const ggml_type t = std::string(tname) == "f16" ? GGML_TYPE_F16 : GGML_TYPE_Q8_0;
        for (int64_t kv : kvs) {
            if (kv % KV_BLK != 0 || kv < 8*KV_BLK) {
                fprintf(stderr, "n_kv %lld must be a multiple of 32 and >= 256\n", (long long) kv);
                return 2;
            }
            for (const auto & m : masks) {
                const int r = run_case(t, kv, m, n_threads, tol);
                if (r == 2) { return 2; }
                rc |= r;
            }
        }
    }
    return rc;
}
