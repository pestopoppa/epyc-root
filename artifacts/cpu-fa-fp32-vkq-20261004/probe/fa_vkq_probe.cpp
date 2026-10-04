// fa_nan_probe.cpp — DF2-9 non-finite localiser (llama-server-free).
//
// Loads a model through the public llama.h API, evaluates one or more prompts with
// n_batch = n_ubatch = R (one ubatch per llama_decode, R query rows each, against a growing
// KV), and uses the ggml eval callback (llama_context_params.cb_eval) to inspect:
//   * every GGML_OP_FLASH_ATTN_EXT output (+ max|Q|, max|K|, max|V|, max_c |sum_kv V[:,c]|,
//     non-finite counts of K and V as the kernel sees them — V/K may be q8_0 or f16 and are
//     dequantised on the host via ggml_get_type_traits()->to_float),
//   * every tensor whose name prefix (before "-<il>") is in --watch (default l_out,result_norm,
//     result_output), i.e. every layer output and the final logits,
//   * optionally every node of one chosen ubatch (--all-nodes-ubatch), to localise the first op.
// It also enables the exact DFlash2 extraction path (llama_set_embeddings_layer_inp for the
// drafter's target layers, default 6,20,34,48,62 on a 64-layer target) and counts non-finite
// target features per ubatch the same way common/speculative.cpp does.
//
// It never aborts on NaN: it only counts. No sampling is done.
// Arm identity: the resolved paths of libggml-hip.so / libggml-base.so / libllama.so are read
// from /proc/self/maps after model load and printed + written to <out>/maps.txt.
//
// Build (no RUNPATH; the arm is chosen at runtime with LD_LIBRARY_PATH=<arm>/bin):
//   g++ -O2 -std=c++17 -I<src>/include -I<src>/ggml/include fa_nan_probe.cpp -o fa_nan_probe
//       -L<bin> -Wl,--as-needed -lllama -lggml -lggml-base -lpthread
//
// Exit: 0 = all finite, 3 = non-finite found somewhere, 2 = usage/load error, 4 = time cap hit
// (with partial results; still 3 if anything non-finite was seen).

#include "llama.h"
#include "ggml.h"
#include "ggml-backend.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>
#include <thread>
#include <atomic>

// llama-ext.h (src/, C++ linkage) — identical signatures in the champion and in master @11fe02151.
LLAMA_API void    llama_set_embeddings_layer_inp(struct llama_context * ctx, uint32_t lid, bool value);
LLAMA_API float * llama_get_embeddings_layer_inp(struct llama_context * ctx, uint32_t lid);

using clk = std::chrono::steady_clock;

struct prompt_spec {
    std::string      path;
    std::vector<int> R;   // empty = use global
};

struct opts {
    std::string              model;
    std::vector<prompt_spec> prompts;
    std::vector<int>         R      = {9, 36, 512};
    std::vector<std::string> kv     = {"q8_0"};
    int                      ngl    = 999;
    int                      ctx    = 8192;
    int                      np     = 1;
    bool                     kvu    = true;
    int                      threads = 8;
    std::string              out    = ".";
    std::string              tag    = "probe";
    std::vector<std::string> watch  = {"l_out", "result_norm", "result_output"};
    std::string              feat_layers = "auto";
    bool                     layer_inp = true;
    int                      all_nodes_ubatch = -1;
    int                      max_ubatches = -1;
    double                   time_cap = 0.0;   // seconds, 0 = none
    bool                     fa_kv_stats = true;
    int                      kv_every = 0;     // K/V/Q stats every N ubatches (0 = auto: ~8 samples per run + last ubatch)
    bool                     verbose_llama = false;
    int                      tail = 0;         // last `tail` tokens are fed in ubatches of tail_R (verify-like)
    int                      tail_R = 5;
    int                      acc_max_q = 64;   // exact VKQ-peak replay only on FA nodes with n_q <= this (one_chunk path)
};

static std::vector<std::string> split(const std::string & s, char d) {
    std::vector<std::string> r; std::string cur; std::stringstream ss(s);
    while (std::getline(ss, cur, d)) if (!cur.empty()) r.push_back(cur);
    return r;
}
static std::vector<int> split_int(const std::string & s) {
    std::vector<int> r; for (auto & x : split(s, ',')) r.push_back(std::atoi(x.c_str())); return r;
}

// ------------------------------------------------------------------------------------------------
// per-run callback state

struct node_stat {
    std::string name, op;
    int     layer = -1;
    int64_t n_nonfinite = 0, n_total = 0;
    double  max_abs = 0.0;
    int64_t first_bad_tok = -1;
    // FA extras
    int64_t n_kv = -1, n_q = -1;
    double  q_max = -1, k_max = -1, v_max = -1, v_chansum = -1;
    int64_t k_nonfinite = -1, v_nonfinite = -1;
    std::string k_type, v_type;
    double acc_peak = -1, acc_final = -1;  // exact (double) replay of one_chunk's un-normalised accumulator
    int64_t acc_vis_max = -1;               // max visible (unmasked) cells over the replayed rows
};

struct run_state {
    const opts * o = nullptr;
    int     ubatch = -1;
    int64_t pos0 = 0;
    int     n_tokens = 0;
    bool    active = false;
    bool    kv_this_ub = true;             // compute the (host-side, costly) Q/K/V stats in this ubatch
    std::vector<node_stat> nodes;          // this ubatch
    // run-level
    bool        any_bad = false;
    std::string first_bad;                 // description of first non-finite node in execution order
    int64_t     fa_ops = 0, fa_bad_ops = 0;
    double      max_fa_out = 0, max_v = 0, max_vchansum = 0, max_acc_peak = 0, max_acc_final = 0;
    int64_t     max_vis = 0;
    std::vector<uint8_t> raw;
    std::vector<float>   row;
};

static int parse_layer(const char * name) {
    if (!name) return -1;
    std::string s(name);
    // "<prefix>-<il>" possibly followed by " (view)" etc.
    size_t sp = s.find(' ');
    std::string head = sp == std::string::npos ? s : s.substr(0, sp);
    size_t dash = head.rfind('-');
    if (dash != std::string::npos && dash + 1 < head.size()) {
        bool digits = true;
        for (size_t i = dash + 1; i < head.size(); ++i) if (head[i] < '0' || head[i] > '9') { digits = false; break; }
        if (digits) return std::atoi(head.c_str() + dash + 1);
    }
    // "cache_k_l12" style
    size_t l = head.rfind("_l");
    if (l != std::string::npos && l + 2 < head.size()) {
        bool digits = true;
        for (size_t i = l + 2; i < head.size(); ++i) if (head[i] < '0' || head[i] > '9') { digits = false; break; }
        if (digits) return std::atoi(head.c_str() + l + 2);
    }
    return -1;
}

static std::string name_prefix(const char * name) {
    std::string s(name ? name : "");
    size_t dash = s.rfind('-');
    if (dash != std::string::npos) {
        bool digits = dash + 1 < s.size();
        for (size_t i = dash + 1; i < s.size(); ++i) if (s[i] < '0' || s[i] > '9') { digits = false; break; }
        if (digits) return s.substr(0, dash);
    }
    return s;
}

// Copy a (possibly strided, possibly quantised) tensor to host and walk it row by row (dim 0
// must be element-contiguous, which holds for every tensor we look at). fn(row_ptr, ne0, i1, i2, i3).
template <typename F>
static bool walk_rows(run_state & st, const ggml_tensor * t, F && fn) {
    if (!t || !t->buffer || !t->data) return false;
    const ggml_type_traits * tr = ggml_get_type_traits(t->type);
    if (!tr) return false;
    const size_t nbytes = ggml_nbytes(t);
    if (nbytes == 0) return true;
    const uint8_t * base = nullptr;
    if (ggml_backend_buffer_is_host(t->buffer)) {
        base = (const uint8_t *) t->data;
    } else {
        st.raw.resize(nbytes);
        ggml_backend_tensor_get(t, st.raw.data(), 0, nbytes);
        base = st.raw.data();
    }
    const int64_t ne0 = t->ne[0];
    const bool row_contig = (size_t) t->nb[0] == ggml_type_size(t->type) || ggml_blck_size(t->type) > 1;
    st.row.resize(ne0);
    for (int64_t i3 = 0; i3 < t->ne[3]; ++i3)
    for (int64_t i2 = 0; i2 < t->ne[2]; ++i2)
    for (int64_t i1 = 0; i1 < t->ne[1]; ++i1) {
        const uint8_t * rp = base + i1 * t->nb[1] + i2 * t->nb[2] + i3 * t->nb[3];
        if (t->type == GGML_TYPE_F32 && row_contig) {
            std::memcpy(st.row.data(), rp, ne0 * sizeof(float));
        } else if (row_contig && tr->to_float) {
            tr->to_float(rp, st.row.data(), ne0);
        } else if (t->type == GGML_TYPE_F32) {
            for (int64_t i0 = 0; i0 < ne0; ++i0) st.row[i0] = *(const float *) (rp + i0 * t->nb[0]);
        } else if (t->type == GGML_TYPE_F16) {
            for (int64_t i0 = 0; i0 < ne0; ++i0) st.row[i0] = ggml_fp16_to_fp32(*(const ggml_fp16_t *) (rp + i0 * t->nb[0]));
        } else {
            return false;
        }
        fn(st.row.data(), ne0, i1, i2, i3);
    }
    return true;
}

struct simple_stat { int64_t bad = 0, total = 0; double max_abs = 0; int64_t first_bad_i1 = -1, first_bad_i2 = -1; };

static simple_stat tensor_stat(run_state & st, const ggml_tensor * t) {
    simple_stat s;
    walk_rows(st, t, [&](const float * r, int64_t n, int64_t i1, int64_t i2, int64_t) {
        for (int64_t i = 0; i < n; ++i) {
            const float v = r[i];
            if (!std::isfinite(v)) {
                if (s.bad == 0) { s.first_bad_i1 = i1; s.first_bad_i2 = i2; }
                ++s.bad;
            } else {
                const double a = std::fabs((double) v);
                if (a > s.max_abs) s.max_abs = a;
            }
        }
        s.total += n;
    });
    return s;
}

// V: [D, n_kv, n_head_kv, ns] after llama's permute; channel sum over the kv dim (i1).
static void v_stats(run_state & st, const ggml_tensor * v, double & vmax, double & chansum, int64_t & bad) {
    vmax = 0; chansum = 0; bad = 0;
    const int64_t D = v->ne[0];
    std::vector<double> acc((size_t) D * v->ne[2] * v->ne[3], 0.0);
    walk_rows(st, v, [&](const float * r, int64_t n, int64_t /*i1*/, int64_t i2, int64_t i3) {
        double * a = acc.data() + ((size_t) i3 * v->ne[2] + i2) * D;
        for (int64_t i = 0; i < n; ++i) {
            const float x = r[i];
            if (!std::isfinite(x)) { ++bad; continue; }
            const double ax = std::fabs((double) x);
            if (ax > vmax) vmax = ax;
            a[i] += x;
        }
    });
    for (double x : acc) chansum = std::max(chansum, std::fabs(x));
}

// Dequantise a 4-D tensor to a dense float array [ne3][ne2][ne1][ne0].
static std::vector<float> dense(run_state & st, const ggml_tensor * t) {
    std::vector<float> out((size_t) ggml_nelements(t));
    const int64_t ne0 = t->ne[0];
    walk_rows(st, t, [&](const float * r, int64_t n, int64_t i1, int64_t i2, int64_t i3) {
        std::memcpy(out.data() + ((i3 * t->ne[2] + i2) * t->ne[1] + i1) * ne0, r, n * sizeof(float));
    });
    return out;
}

// Exact replay (double) of ggml_compute_forward_flash_attn_ext_f16_one_chunk's online softmax over the
// whole visible KV in cell order: acc = sum_i exp(s_i - M_running) v_i. Records max over (row, head, channel,
// step) of |acc| (the value an FP16 VKQ accumulator must hold; overflow at 65504) and of the final |acc|.
static void acc_replay(run_state & st, const ggml_tensor * fa, const ggml_tensor * q, const ggml_tensor * k,
                       const ggml_tensor * v, const ggml_tensor * mask, double & peak, double & fin, int64_t & vismax) {
    peak = 0; fin = 0; vismax = 0;
    float scale = 1.0f, max_bias = 0.0f, softcap = 0.0f;
    std::memcpy(&scale,    (const float *) fa->op_params + 0, sizeof(float));
    std::memcpy(&max_bias, (const float *) fa->op_params + 1, sizeof(float));
    std::memcpy(&softcap,  (const float *) fa->op_params + 2, sizeof(float));
    if (softcap != 0) scale /= softcap;
    const std::vector<float> Q = dense(st, q), K = dense(st, k), V = dense(st, v);
    std::vector<float> Mk; if (mask) Mk = dense(st, mask);
    const int64_t DK = k->ne[0], DV = v->ne[0], nkv = k->ne[1], nq = q->ne[1], nh = q->ne[2];
    const int64_t nhk = k->ne[2], nhv = v->ne[2];
    const int64_t rk = nh / nhk, rv = nh / nhv;
    const int64_t nitems = nq * nh * q->ne[3];
    std::atomic<int64_t> next{0};
    const int nth = std::max(1, std::min(st.o->threads, 24));
    std::vector<double> pk(nth, 0), fn(nth, 0); std::vector<int64_t> vm(nth, 0);
    auto work = [&](int tid) {
        std::vector<double> acc(DV);
        for (int64_t it; (it = next++) < nitems; ) {
            const int64_t iq3 = it / (nh * nq), iq2 = (it / nq) % nh, iq1 = it % nq;
            const int64_t ik3 = iq3 / std::max<int64_t>(1, q->ne[3] / k->ne[3]);
            const float * qr = Q.data() + ((iq3 * nh + iq2) * nq + iq1) * DK;
            const float * mr = mask ? Mk.data() + (((iq3 % mask->ne[3]) * mask->ne[2] + (iq2 % mask->ne[2])) * mask->ne[1] + iq1) * mask->ne[0] : nullptr;
            std::fill(acc.begin(), acc.end(), 0.0);
            double M = -INFINITY; int64_t vis = 0;
            for (int64_t ic = 0; ic < nkv; ++ic) {
                const double mv = mr ? (double) mr[ic] : 0.0;
                if (mv == -INFINITY) continue;
                ++vis;
                const float * kr = K.data() + ((ik3 * nhk + iq2 / rk) * nkv + ic) * DK;
                const float * vr = V.data() + ((ik3 * nhv + iq2 / rv) * nkv + ic) * DV;
                double sdot = 0; for (int64_t d = 0; d < DK; ++d) sdot += (double) qr[d] * kr[d];
                double sv = sdot * scale; if (softcap != 0) sv = softcap * std::tanh(sv); sv += mv;
                double w = 1.0;
                if (sv > M) { const double ms = std::exp(M - sv); M = sv; for (auto & a : acc) a *= ms; }
                else w = std::exp(sv - M);
                double rowmax = 0;
                for (int64_t d = 0; d < DV; ++d) { acc[d] += w * vr[d]; rowmax = std::max(rowmax, std::fabs(acc[d])); }
                pk[tid] = std::max(pk[tid], rowmax);
            }
            for (int64_t d = 0; d < DV; ++d) fn[tid] = std::max(fn[tid], std::fabs(acc[d]));
            vm[tid] = std::max(vm[tid], vis);
        }
    };
    std::vector<std::thread> th; for (int t = 0; t < nth; ++t) th.emplace_back(work, t);
    for (auto & t : th) t.join();
    for (int t = 0; t < nth; ++t) { peak = std::max(peak, pk[t]); fin = std::max(fin, fn[t]); vismax = std::max(vismax, vm[t]); }
    (void) max_bias;
}

static bool want_node(const run_state & st, const ggml_tensor * t) {
    if (!st.active) return false;
    if (st.o->all_nodes_ubatch >= 0 && st.ubatch == st.o->all_nodes_ubatch) return true;
    if (t->op == GGML_OP_FLASH_ATTN_EXT) return true;
    const std::string p = name_prefix(t->name);
    for (auto & w : st.o->watch) if (p == w) return true;
    return false;
}

static bool eval_cb(struct ggml_tensor * t, bool ask, void * ud) {
    run_state & st = *(run_state *) ud;
    if (ask) return want_node(st, t);
    if (!want_node(st, t)) return true;

    node_stat ns;
    ns.name  = t->name;
    ns.op    = ggml_op_name(t->op);
    ns.layer = parse_layer(t->name);
    const bool is_fa = t->op == GGML_OP_FLASH_ATTN_EXT;
    if (is_fa && ns.layer < 0) {
        for (int k = 0; k < 3 && ns.layer < 0; ++k) if (t->src[k]) ns.layer = parse_layer(t->src[k]->name);
    }
    simple_stat s = tensor_stat(st, t);
    ns.n_nonfinite = s.bad; ns.n_total = s.total; ns.max_abs = s.max_abs;
    // FA output is [D, n_head, n_tokens, 1]: token = i2. 2-D activations [n_embd, n_tokens]: token = i1.
    if (s.bad > 0) ns.first_bad_tok = is_fa ? s.first_bad_i2 : s.first_bad_i1;

    if (is_fa) {
        st.fa_ops++;
        if (s.bad > 0) st.fa_bad_ops++;
        st.max_fa_out = std::max(st.max_fa_out, s.max_abs);
        const ggml_tensor * q = t->src[0], * k = t->src[1], * v = t->src[2];
        if (k) { ns.n_kv = k->ne[1]; ns.k_type = ggml_type_name(k->type); }
        if (q) ns.n_q = q->ne[1];
        if (v) ns.v_type = ggml_type_name(v->type);
        if (st.o->fa_kv_stats && (st.kv_this_ub || s.bad > 0)) {
            if (q) { simple_stat qs = tensor_stat(st, q); ns.q_max = qs.max_abs; }
            if (k) { simple_stat ks = tensor_stat(st, k); ns.k_max = ks.max_abs; ns.k_nonfinite = ks.bad; }
            if (v) { v_stats(st, v, ns.v_max, ns.v_chansum, ns.v_nonfinite); }
            st.max_v = std::max(st.max_v, ns.v_max);
            st.max_vchansum = std::max(st.max_vchansum, ns.v_chansum);
        }
        if (q && k && v && q->ne[1] <= st.o->acc_max_q && (st.kv_this_ub || s.bad > 0)) {
            acc_replay(st, t, q, k, v, t->src[3], ns.acc_peak, ns.acc_final, ns.acc_vis_max);
            st.max_acc_peak  = std::max(st.max_acc_peak,  ns.acc_peak);
            st.max_acc_final = std::max(st.max_acc_final, ns.acc_final);
            st.max_vis       = std::max(st.max_vis,       ns.acc_vis_max);
        }
    }
    if (s.bad > 0 && !st.any_bad) {
        st.any_bad = true;
        char buf[512];
        snprintf(buf, sizeof buf, "ubatch=%d pos0=%lld node=%s op=%s layer=%d tok=%lld bad=%lld/%lld",
                 st.ubatch, (long long) st.pos0, ns.name.c_str(), ns.op.c_str(), ns.layer,
                 (long long) ns.first_bad_tok, (long long) s.bad, (long long) s.total);
        st.first_bad = buf;
    }
    st.nodes.push_back(std::move(ns));
    return true;
}

// ------------------------------------------------------------------------------------------------

static void print_maps(const std::string & path_out) {
    std::ifstream f("/proc/self/maps");
    std::map<std::string, bool> seen;
    std::string line;
    std::ofstream o(path_out);
    const char * keys[] = {"libggml-hip.so", "libggml-cuda.so", "libggml-base.so", "libggml-cpu.so", "libggml.so", "libllama.so"};
    while (std::getline(f, line)) {
        size_t p = line.find('/');
        if (p == std::string::npos) continue;
        std::string path = line.substr(p);
        for (auto * k : keys) {
            if (path.find(std::string("/") + k) != std::string::npos && !seen[path]) {
                seen[path] = true;
                fprintf(stdout, "MAPS %s\n", path.c_str());
                o << path << "\n";
            }
        }
    }
    bool hip = false;
    for (auto & kv : seen) if (kv.first.find("libggml-hip.so") != std::string::npos) hip = true;
    if (!hip) { fprintf(stdout, "MAPS libggml-hip.so: NOT LOADED (CPU-only run)\n"); o << "libggml-hip.so: NOT LOADED\n"; }
    fflush(stdout);
}

static std::string read_file(const std::string & p) {
    std::ifstream f(p, std::ios::binary);
    std::stringstream ss; ss << f.rdbuf();
    return ss.str();
}

static ggml_type kv_type(const std::string & s) {
    if (s == "f16")  return GGML_TYPE_F16;
    if (s == "q8_0") return GGML_TYPE_Q8_0;
    if (s == "f32")  return GGML_TYPE_F32;
    if (s == "q4_0") return GGML_TYPE_Q4_0;
    fprintf(stderr, "unknown kv type %s\n", s.c_str()); exit(2);
}

static void usage(const char * a0) {
    fprintf(stderr,
        "usage: %s -m MODEL -p PROMPT_FILE[:R1,R2,..] [-p ...] [options]\n"
        "  --R 9,36,512          ubatch sizes (n_batch = n_ubatch = R) for prompts without :R override\n"
        "  --kv q8_0[,f16]       KV cache types (K and V both); one fresh context per (kv, prompt, R)\n"
        "  --ngl N (999)  --ctx N (8192)  --np N (1)  --kvu 0|1 (1)  -t N (8)\n"
        "  --out DIR  --tag NAME\n"
        "  --watch l_out,result_norm,result_output   name prefixes to inspect besides every FLASH_ATTN_EXT\n"
        "  --feat-layers auto|6,20,34,48,62|none     DFlash target layers (layer-input extraction)\n"
        "  --all-nodes-ubatch K  inspect every node in ubatch K (slow; localisation)\n"
        "  --kv-every N (0=auto ~8/run)  --max-ubatches N  --time-cap SEC  --no-kv-stats  --verbose\n"
        "  Q/K/V stats (q_max,k_max,v_max,v_max_chansum,*_nonfinite) are -1 on ubatches where they were not sampled;\n"
        "  they are always computed when the FA output itself has a non-finite value.\n", a0);
}

static void llama_log_quiet(enum ggml_log_level level, const char * text, void * ud) {
    const bool verbose = *(bool *) ud;
    if (verbose || level >= GGML_LOG_LEVEL_WARN) fputs(text, stderr);
}

int main(int argc, char ** argv) {
    opts o;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto next = [&]() -> std::string { if (i + 1 >= argc) { usage(argv[0]); exit(2); } return argv[++i]; };
        if (a == "-m") o.model = next();
        else if (a == "-p") {
            std::string v = next(); prompt_spec ps;
            size_t c = v.rfind(':');
            if (c != std::string::npos && c + 1 < v.size() && v.find('/', c) == std::string::npos) {
                ps.path = v.substr(0, c); ps.R = split_int(v.substr(c + 1));
            } else ps.path = v;
            o.prompts.push_back(ps);
        }
        else if (a == "--R") o.R = split_int(next());
        else if (a == "--kv") o.kv = split(next(), ',');
        else if (a == "--ngl") o.ngl = std::atoi(next().c_str());
        else if (a == "--ctx") o.ctx = std::atoi(next().c_str());
        else if (a == "--np") o.np = std::atoi(next().c_str());
        else if (a == "--kvu") o.kvu = std::atoi(next().c_str()) != 0;
        else if (a == "-t") o.threads = std::atoi(next().c_str());
        else if (a == "--out") o.out = next();
        else if (a == "--tag") o.tag = next();
        else if (a == "--watch") o.watch = split(next(), ',');
        else if (a == "--feat-layers") o.feat_layers = next();
        else if (a == "--all-nodes-ubatch") o.all_nodes_ubatch = std::atoi(next().c_str());
        else if (a == "--max-ubatches") o.max_ubatches = std::atoi(next().c_str());
        else if (a == "--time-cap") o.time_cap = std::atof(next().c_str());
        else if (a == "--no-kv-stats") o.fa_kv_stats = false;
        else if (a == "--kv-every") o.kv_every = std::atoi(next().c_str());
        else if (a == "--verbose") o.verbose_llama = true;
        else if (a == "--tail") o.tail = std::atoi(next().c_str());
        else if (a == "--tail-R") o.tail_R = std::atoi(next().c_str());
        else if (a == "--acc-max-q") o.acc_max_q = std::atoi(next().c_str());
        else { usage(argv[0]); return 2; }
    }
    if (o.model.empty() || o.prompts.empty()) { usage(argv[0]); return 2; }

    const auto t_start = clk::now();
    auto elapsed = [&]() { return std::chrono::duration<double>(clk::now() - t_start).count(); };

    llama_log_set(llama_log_quiet, &o.verbose_llama);
    llama_backend_init();

    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = o.ngl;
    llama_model * model = llama_model_load_from_file(o.model.c_str(), mp);
    if (!model) { fprintf(stderr, "ERROR: model load failed\n"); return 2; }
    fprintf(stdout, "LOADED %s in %.1fs (n_layer=%d n_embd=%d)\n", o.model.c_str(), elapsed(),
            llama_model_n_layer(model), llama_model_n_embd(model));
    print_maps(o.out + "/" + o.tag + ".maps.txt");

    const llama_vocab * vocab = llama_model_get_vocab(model);
    const int n_layer = llama_model_n_layer(model);
    const int n_embd  = llama_model_n_embd(model);

    std::vector<int> feat;
    if (o.feat_layers == "auto") {
        if (n_layer == 64) feat = {6, 20, 34, 48, 62};
        else feat = {1, n_layer / 2, n_layer - 1};
    } else if (o.feat_layers != "none") {
        feat = split_int(o.feat_layers);
    }
    if (!o.layer_inp) feat.clear();

    const std::string tsv_nodes = o.out + "/" + o.tag + ".nodes.tsv";
    const std::string tsv_ub    = o.out + "/" + o.tag + ".ubatch.tsv";
    const std::string sum_path  = o.out + "/" + o.tag + ".summary.txt";
    FILE * fn = fopen(tsv_nodes.c_str(), "w");
    FILE * fu = fopen(tsv_ub.c_str(), "w");
    FILE * fs = fopen(sum_path.c_str(), "w");
    if (!fn || !fu || !fs) { fprintf(stderr, "ERROR: cannot write to %s\n", o.out.c_str()); return 2; }
    fprintf(fn, "tag\tkv\tR\tprompt\tubatch_idx\tpos0\tn_tokens\tn_kv\tlayer\tnode\top\tn_nonfinite\tn_total\tmax_abs_out\tfirst_bad_tok\tn_q\tk_type\tv_type\tq_max\tk_max\tk_nonfinite\tv_max\tv_max_chansum\tv_nonfinite\tacc_peak\tacc_final\tvis_max\n");
    fprintf(fu, "tag\tkv\tR\tprompt\tubatch_idx\tpos0\tn_tokens\tdecode_rc\tfeat_nonfinite\tfeat_total\tfeat_max_abs\tlogits_nonfinite\tfa_bad_ops\tt_ms\n");

    bool any_bad_global = false, timed_out = false;
    int  n_runs = 0, n_runs_bad = 0;

    for (const auto & kvs : o.kv) {
        for (const auto & ps : o.prompts) {
            const std::string text = read_file(ps.path);
            std::vector<llama_token> toks(text.size() + 16);
            int n = llama_tokenize(vocab, text.c_str(), (int32_t) text.size(), toks.data(), (int32_t) toks.size(), true, true);
            if (n < 0) { toks.resize(-n); n = llama_tokenize(vocab, text.c_str(), (int32_t) text.size(), toks.data(), (int32_t) toks.size(), true, true); }
            if (n <= 0) { fprintf(stderr, "ERROR: tokenize %s failed\n", ps.path.c_str()); return 2; }
            toks.resize(n);
            std::string pname = ps.path.substr(ps.path.find_last_of('/') + 1);
            const std::vector<int> & Rs = ps.R.empty() ? o.R : ps.R;

            for (int R : Rs) {
                if (o.time_cap > 0 && elapsed() > o.time_cap) { timed_out = true; break; }
                run_state st; st.o = &o;

                llama_context_params cp = llama_context_default_params();
                cp.n_ctx           = (uint32_t) std::max(o.ctx, n + 16);
                cp.n_batch         = (uint32_t) R;
                cp.n_ubatch        = (uint32_t) R;
                cp.n_seq_max       = (uint32_t) o.np;
                cp.n_threads       = o.threads;
                cp.n_threads_batch = o.threads;
                cp.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_ENABLED;
                cp.type_k          = kv_type(kvs);
                cp.type_v          = kv_type(kvs);
                cp.kv_unified      = o.kvu;
                cp.offload_kqv     = true;
                cp.no_perf         = true;
                cp.cb_eval         = eval_cb;
                cp.cb_eval_user_data = &st;

                llama_context * ctx = llama_init_from_model(model, cp);
                if (!ctx) { fprintf(stderr, "ERROR: context init failed (kv=%s R=%d)\n", kvs.c_str(), R); return 2; }
                for (int l : feat) if (l >= 0 && l <= n_layer) llama_set_embeddings_layer_inp(ctx, (uint32_t) l, true);

                llama_batch batch = llama_batch_init(R, 0, 1);
                int64_t feat_bad_run = 0, feat_tot_run = 0, logits_bad_run = 0;
                int ub = 0; int rc_last = 0;
                const int tail = std::min(o.tail, n - 1);
                const int head_n = n - tail;
                const int n_ub_total = (head_n + R - 1) / R + (tail > 0 ? (tail + o.tail_R - 1) / o.tail_R : 0);
                const int kv_every = o.kv_every > 0 ? o.kv_every : std::max(1, n_ub_total / 8);
                std::string first_feat_bad;
                for (int p0 = 0, nt = 0; p0 < n; p0 += nt, ++ub) {
                    if (o.max_ubatches >= 0 && ub >= o.max_ubatches) break;
                    if (o.time_cap > 0 && elapsed() > o.time_cap) { timed_out = true; break; }
                    nt = p0 < head_n ? std::min(R, head_n - p0) : std::min(o.tail_R, n - p0);
                    batch.n_tokens = nt;
                    for (int i = 0; i < nt; ++i) {
                        batch.token[i] = toks[p0 + i]; batch.pos[i] = p0 + i;
                        batch.n_seq_id[i] = 1; batch.seq_id[i][0] = 0;
                        batch.logits[i] = (i == nt - 1);
                    }
                    st.ubatch = ub; st.pos0 = p0; st.n_tokens = nt; st.active = true; st.nodes.clear();
                    st.kv_this_ub = (ub % kv_every == 0) || (ub >= n_ub_total - 2) || (p0 >= head_n);
                    const auto t0 = clk::now();
                    const int rc = llama_decode(ctx, batch);
                    llama_synchronize(ctx);
                    st.active = false;
                    const double tms = std::chrono::duration<double, std::milli>(clk::now() - t0).count();
                    rc_last = rc;

                    int64_t fb = 0, ft = 0; double fmax = 0;
                    if (rc == 0) {
                        for (int l : feat) {
                            const float * d = llama_get_embeddings_layer_inp(ctx, (uint32_t) l);
                            if (!d) continue;
                            int64_t lb = 0;
                            for (int64_t i = 0; i < (int64_t) nt * n_embd; ++i) {
                                const float v = d[i];
                                if (!std::isfinite(v)) ++lb; else fmax = std::max(fmax, (double) std::fabs(v));
                            }
                            fb += lb; ft += (int64_t) nt * n_embd;
                            if (lb > 0 && first_feat_bad.empty()) {
                                first_feat_bad = "ubatch=" + std::to_string(ub) + " feat_layer=" + std::to_string(l) +
                                                 " bad=" + std::to_string(lb) + "/" + std::to_string((int64_t) nt * n_embd);
                            }
                        }
                    }
                    int64_t lgb = 0;
                    if (rc == 0) {
                        const float * lg = llama_get_logits_ith(ctx, nt - 1);
                        const int nv = llama_vocab_n_tokens(vocab);
                        if (lg) for (int i = 0; i < nv; ++i) if (!std::isfinite(lg[i])) ++lgb;
                    }
                    feat_bad_run += fb; feat_tot_run += ft; logits_bad_run += lgb;

                    int64_t fa_bad_ub = 0;
                    for (auto & ns : st.nodes) {
                        if (ns.op == std::string(ggml_op_name(GGML_OP_FLASH_ATTN_EXT)) && ns.n_nonfinite > 0) ++fa_bad_ub;
                        fprintf(fn, "%s\t%s\t%d\t%s\t%d\t%d\t%d\t%lld\t%d\t%s\t%s\t%lld\t%lld\t%.6g\t%lld\t%lld\t%s\t%s\t%.6g\t%.6g\t%lld\t%.6g\t%.6g\t%lld\t%.6g\t%.6g\t%lld\n",
                                o.tag.c_str(), kvs.c_str(), R, pname.c_str(), ub, p0, nt, (long long) ns.n_kv, ns.layer,
                                ns.name.c_str(), ns.op.c_str(), (long long) ns.n_nonfinite, (long long) ns.n_total, ns.max_abs,
                                (long long) ns.first_bad_tok, (long long) ns.n_q,
                                ns.k_type.empty() ? "-" : ns.k_type.c_str(), ns.v_type.empty() ? "-" : ns.v_type.c_str(),
                                ns.q_max, ns.k_max, (long long) ns.k_nonfinite, ns.v_max, ns.v_chansum, (long long) ns.v_nonfinite,
                                ns.acc_peak, ns.acc_final, (long long) ns.acc_vis_max);
                    }
                    fprintf(fu, "%s\t%s\t%d\t%s\t%d\t%d\t%d\t%d\t%lld\t%lld\t%.6g\t%lld\t%lld\t%.1f\n",
                            o.tag.c_str(), kvs.c_str(), R, pname.c_str(), ub, p0, nt, rc, (long long) fb, (long long) ft, fmax,
                            (long long) lgb, (long long) fa_bad_ub, tms);
                    fflush(fn); fflush(fu);
                    if (rc != 0) { fprintf(stderr, "WARN: llama_decode rc=%d at ubatch %d (kv=%s R=%d)\n", rc, ub, kvs.c_str(), R); break; }
                }
                llama_batch_free(batch);
                llama_free(ctx);

                const bool bad = st.any_bad || feat_bad_run > 0 || logits_bad_run > 0;
                any_bad_global |= bad; ++n_runs; if (bad) ++n_runs_bad;
                char line[2048];
                snprintf(line, sizeof line,
                    "SUMMARY tag=%s kv=%s R=%d prompt=%s n_tokens=%d ubatches=%d decode_rc=%d fa_ops=%lld fa_nonfinite_ops=%lld "
                    "feat_nonfinite=%lld/%lld logits_nonfinite=%lld max_fa_out=%.6g max_v=%.6g max_v_chansum=%.6g acc_peak=%.6g acc_final=%.6g vis_max=%lld tail=%d tail_R=%d "
                    "first_bad_node=[%s] first_bad_feat=[%s] t=%.1fs VERDICT=%s%s\n",
                    o.tag.c_str(), kvs.c_str(), R, pname.c_str(), n, ub, rc_last, (long long) st.fa_ops, (long long) st.fa_bad_ops,
                    (long long) feat_bad_run, (long long) feat_tot_run, (long long) logits_bad_run,
                    st.max_fa_out, st.max_v, st.max_vchansum, st.max_acc_peak, st.max_acc_final, (long long) st.max_vis, tail, o.tail_R,
                    st.first_bad.empty() ? "none" : st.first_bad.c_str(),
                    first_feat_bad.empty() ? "none" : first_feat_bad.c_str(), elapsed(),
                    rc_last != 0 ? "ERROR" : (bad ? "FAIL" : "PASS"), timed_out ? " (TIME-CAP)" : "");
                fputs(line, stdout); fputs(line, fs); fflush(stdout); fflush(fs);
                if (timed_out) break;
            }
            if (timed_out) break;
        }
        if (timed_out) break;
    }

    char fin[512];
    snprintf(fin, sizeof fin, "FINAL tag=%s runs=%d runs_nonfinite=%d timed_out=%d wall=%.1fs VERDICT=%s\n",
             o.tag.c_str(), n_runs, n_runs_bad, timed_out ? 1 : 0, elapsed(), any_bad_global ? "FAIL" : (timed_out ? "INCOMPLETE" : "PASS"));
    fputs(fin, stdout); fputs(fin, fs);
    fclose(fn); fclose(fu); fclose(fs);
    llama_model_free(model);
    llama_backend_free();
    if (any_bad_global) return 3;
    return timed_out ? 4 : 0;
}
