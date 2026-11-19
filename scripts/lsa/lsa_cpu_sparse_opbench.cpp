// LSA-CPU-SPARSE op-level gate bench (standalone; touches no llama.cpp tree, links nothing from it).
//
// Question: on pure CPU, does D-LSA flat key selection (persistent projected-key cache + AVX512 scoring
// + exact top-k + indexed exact attention) beat dense decode attention at 32k KV by >= 1.10x per token?
//
// Shape = Qwen3.8-27B global attention (24 q heads / 4 kv heads / head_dim 256 / rope 64, 16 global layers),
// ONE decode token (query at position T-1), f16 KV.  Layers use distinct buffers so KV is streamed from DRAM
// like real decode, not replayed from L3.  Both arms use the SAME attention kernel (f16 K/V -> f32 FMA,
// vector exp, split over (kv head x key chunk), exact merge); the sparse arm only gathers the selected keys,
// so the ratio isolates the algorithmic choice, not kernel quality.  Integration against ggml's own FA stays a
// separate check.
//
// Selection = paper budget: top_k long-range keys by cosine(q_idx, k_idx) + `window` newest + `sink` oldest.
// The index key is k projected to 64 dims (W_K, RoPE-free dims, L2-normalised) and cached as BF16 per cell
// (written once per token; its cost is accounted in --append, not in the decode loop).  Random data: the
// selected set is a random scatter, the worst case for the gather.
//
//   build:  g++ -O3 -march=native -fopenmp -std=c++17 lsa_cpu_sparse_opbench.cpp -o lsa_cpu_sparse_opbench
//   check:  ./lsa_cpu_sparse_opbench --check            (small, exact, single/multi thread; exit 0 = PASS)
//   bench:  OMP_NUM_THREADS=N ./lsa_cpu_sparse_opbench --kv 32768 --layers 16 --reps 40 --json out.json
#include <immintrin.h>
#include <omp.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <numeric>
#include <random>
#include <string>
#include <vector>

constexpr int KVH = 4, G = 6, QH = 24, D = 256, ROPE = 64, FREE = D - ROPE, IDX = 64, ROWS = KVH * FREE;

typedef uint16_t half_t;

static float h2f(half_t h) { return _cvtsh_ss(h); }
static half_t f2h(float f) { return _cvtss_sh(f, 0); }
static half_t f2bf(float f) { uint32_t u; memcpy(&u, &f, 4); return (half_t) ((u + 0x7FFF + ((u >> 16) & 1)) >> 16); }
static float bf2f(half_t b) { uint32_t u = (uint32_t) b << 16; float f; memcpy(&f, &u, 4); return f; }

static double now() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }

// 16 lanes exp(x), x <= 0 region mostly; relative error ~2e-7
static inline __m512 vexp(__m512 x) {
    x = _mm512_max_ps(x, _mm512_set1_ps(-87.0f));
    __m512 t = _mm512_mul_ps(x, _mm512_set1_ps(1.4426950408889634f));
    __m512 n = _mm512_roundscale_ps(t, _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);
    __m512 f = _mm512_fnmadd_ps(n, _mm512_set1_ps(0.6931471805599453f), x);
    __m512 p = _mm512_set1_ps(1.0f / 720.0f);
    p = _mm512_fmadd_ps(p, f, _mm512_set1_ps(1.0f / 120.0f));
    p = _mm512_fmadd_ps(p, f, _mm512_set1_ps(1.0f / 24.0f));
    p = _mm512_fmadd_ps(p, f, _mm512_set1_ps(1.0f / 6.0f));
    p = _mm512_fmadd_ps(p, f, _mm512_set1_ps(0.5f));
    p = _mm512_fmadd_ps(p, f, _mm512_set1_ps(1.0f));
    p = _mm512_fmadd_ps(p, f, _mm512_set1_ps(1.0f));
    return _mm512_scalef_ps(p, n);
}

struct Layer {
    half_t * k, * v;  // [T][KVH][D]
    half_t * ik;      // [T][IDX] bf16 index keys (L2-normalised)
    std::vector<float> wq;  // [ROWS][IDX]
};

struct Partial { float m[G], l[G]; float acc[G][D]; };

// attention over keys [lo,hi) (dense) or idx[lo..hi) (gather) for kv head g; returns online-softmax partial
static void attn_chunk(const Layer & L, int T, int g, const float * q /*[QH][D]*/, const int32_t * idx, int lo, int hi, float scale, Partial & p) {
    const int n = hi - lo;
    float sc[G][512];
    for (int h = 0; h < G; ++h) { p.m[h] = -INFINITY; p.l[h] = 0; memset(p.acc[h], 0, sizeof(p.acc[h])); }
    for (int base = 0; base < n; base += 512) {
        const int c = std::min(512, n - base);
        for (int j = 0; j < c; ++j) {
            const int key = idx ? idx[lo + base + j] : lo + base + j;
            const half_t * kr = L.k + ((size_t) key * KVH + g) * D;
            __m512 a[G];
            for (int h = 0; h < G; ++h) a[h] = _mm512_setzero_ps();
            for (int d = 0; d < D; d += 16) {
                __m512 kv = _mm512_cvtph_ps(_mm256_loadu_si256((const __m256i *) (kr + d)));
                for (int h = 0; h < G; ++h) a[h] = _mm512_fmadd_ps(kv, _mm512_loadu_ps(q + (g * G + h) * D + d), a[h]);
            }
            for (int h = 0; h < G; ++h) sc[h][j] = _mm512_reduce_add_ps(a[h]) * scale;
        }
        for (int h = 0; h < G; ++h) {
            float mx = p.m[h];
            for (int j = 0; j < c; ++j) mx = std::max(mx, sc[h][j]);
            const float corr = std::exp(p.m[h] - mx);  // 0 on first chunk (m = -inf)
            p.l[h] *= corr;
            for (int d = 0; d < D; ++d) p.acc[h][d] *= corr;
            p.m[h] = mx;
            const __m512 vm = _mm512_set1_ps(mx);
            float s = 0;
            int j = 0;
            for (; j + 16 <= c; j += 16) {
                __m512 e = vexp(_mm512_sub_ps(_mm512_loadu_ps(&sc[h][j]), vm));
                _mm512_storeu_ps(&sc[h][j], e);
                s += _mm512_reduce_add_ps(e);
            }
            for (; j < c; ++j) { sc[h][j] = std::exp(sc[h][j] - mx); s += sc[h][j]; }
            p.l[h] += s;
        }
        // V accumulate, register-blocked: 4 x 16 output dims x 6 heads live in registers across the whole chunk
        for (int db = 0; db < D; db += 64) {
            __m512 a[G][4];
            for (int h = 0; h < G; ++h)
                for (int i = 0; i < 4; ++i) a[h][i] = _mm512_loadu_ps(&p.acc[h][db + 16 * i]);
            for (int j = 0; j < c; ++j) {
                const int key = idx ? idx[lo + base + j] : lo + base + j;
                const half_t * vr = L.v + ((size_t) key * KVH + g) * D + db;
                __m512 vv[4];
                for (int i = 0; i < 4; ++i) vv[i] = _mm512_cvtph_ps(_mm256_loadu_si256((const __m256i *) (vr + 16 * i)));
                for (int h = 0; h < G; ++h) {
                    const __m512 w = _mm512_set1_ps(sc[h][j]);
                    for (int i = 0; i < 4; ++i) a[h][i] = _mm512_fmadd_ps(w, vv[i], a[h][i]);
                }
            }
            for (int h = 0; h < G; ++h)
                for (int i = 0; i < 4; ++i) _mm512_storeu_ps(&p.acc[h][db + 16 * i], a[h][i]);
        }
    }
    (void) T;
}

// full decode attention: dense (idx == nullptr, n = T keys) or gathered (n = idx count); out [QH][D]
static void attention(const Layer & L, int T, const float * q, const int32_t * idx, int n, float scale, float * out, int chunk, std::vector<Partial> & ws) {
    const int nch = (n + chunk - 1) / chunk;
    ws.resize((size_t) KVH * nch);
#pragma omp parallel for schedule(dynamic, 1) collapse(2)
    for (int g = 0; g < KVH; ++g)
        for (int c = 0; c < nch; ++c)
            attn_chunk(L, T, g, q, idx, c * chunk, std::min(n, (c + 1) * chunk), scale, ws[(size_t) g * nch + c]);
    for (int g = 0; g < KVH; ++g)
        for (int h = 0; h < G; ++h) {
            float m = -INFINITY;
            for (int c = 0; c < nch; ++c) m = std::max(m, ws[(size_t) g * nch + c].m[h]);
            float l = 0;
            float * o = out + (g * G + h) * D;
            memset(o, 0, D * sizeof(float));
            for (int c = 0; c < nch; ++c) {
                const Partial & p = ws[(size_t) g * nch + c];
                const float w = std::exp(p.m[h] - m);
                l += p.l[h] * w;
                for (int d = 0; d < D; ++d) o[d] += p.acc[h][d] * w;
            }
            for (int d = 0; d < D; ++d) o[d] /= l;
        }
}

struct Sel { int top_k, window, sink; };

struct Scratch {
    std::vector<float> score;
    std::vector<int32_t> idx;
    std::vector<uint8_t> mark;
    std::vector<std::vector<int32_t>> cand, part;
    std::vector<std::vector<uint32_t>> hist;
};

// q_idx = l2( group-sum(q free dims) @ Wq )
static void project_q(const Layer & L, const float * q, float * qi) {
    float qs[ROWS];
    for (int g = 0; g < KVH; ++g)
        for (int d = 0; d < FREE; ++d) {
            float s = 0;
            for (int h = 0; h < G; ++h) s += q[(g * G + h) * D + ROPE + d];
            qs[g * FREE + d] = s;
        }
    for (int o = 0; o < IDX; ++o) qi[o] = 0;
    for (int r = 0; r < ROWS; ++r)
        for (int o = 0; o < IDX; o += 16)
            _mm512_storeu_ps(qi + o, _mm512_fmadd_ps(_mm512_set1_ps(qs[r]), _mm512_loadu_ps(&L.wq[(size_t) r * IDX + o]), _mm512_loadu_ps(qi + o)));
    float nrm = 0;
    for (int o = 0; o < IDX; ++o) nrm += qi[o] * qi[o];
    nrm = 1.0f / std::max(std::sqrt(nrm), 1e-30f);
    for (int o = 0; o < IDX; ++o) qi[o] *= nrm;
}

static inline uint32_t bin_of(float s) { s = std::min(1.0f, std::max(-1.0f, s)); return (uint32_t) ((s + 1.0f) * 2047.999f); }

// exact top-k among positions [sink, T-window) by score (ties by lower index), plus forced window/sink; sorted idx out
static int select_keys(const Layer & L, int T, const float * qi, const Sel & S, Scratch & X, double * t_score, double * t_topk) {
    const int nt = omp_get_max_threads();
    X.score.resize(T);
    X.mark.assign(T, 0);
    X.hist.assign(nt, std::vector<uint32_t>(4096, 0));
    X.cand.assign(nt, {});
    X.part.assign(nt, {});
    const int lo = S.sink, hi = std::max(S.sink, T - S.window);  // eligible long range
    double t0 = now();
#pragma omp parallel
    {
        auto & h = X.hist[omp_get_thread_num()];
        __m512 qv[4];
        for (int i = 0; i < 4; ++i) qv[i] = _mm512_loadu_ps(qi + 16 * i);
#pragma omp for schedule(static)
        for (int j = lo; j < hi; ++j) {
            const half_t * r = L.ik + (size_t) j * IDX;
            __m512 a = _mm512_setzero_ps();
            for (int i = 0; i < 4; ++i) {
                __m512i w = _mm512_slli_epi32(_mm512_cvtepu16_epi32(_mm256_loadu_si256((const __m256i *) (r + 16 * i))), 16);
                a = _mm512_fmadd_ps(_mm512_castsi512_ps(w), qv[i], a);
            }
            const float s = _mm512_reduce_add_ps(a);
            X.score[j] = s;
            h[bin_of(s)]++;
        }
    }
    double t1 = now();
    const int want = std::min(S.top_k, hi - lo);
    std::vector<uint32_t> tot(4096, 0);
    for (auto & h : X.hist) for (int b = 0; b < 4096; ++b) tot[b] += h[b];
    int cut = 4095;
    long above = 0;
    for (; cut >= 0; --cut) { if (above + tot[cut] >= want) break; above += tot[cut]; }
    cut = std::max(cut, 0);
#pragma omp parallel
    {
        auto & c = X.cand[omp_get_thread_num()];
#pragma omp for schedule(static)
        for (int j = lo; j < hi; ++j) {
            const uint32_t b = bin_of(X.score[j]);
            if (b > (uint32_t) cut) X.mark[j] = 1;
            else if (b == (uint32_t) cut) c.push_back(j);
        }
    }
    std::vector<int32_t> cand;
    for (auto & c : X.cand) cand.insert(cand.end(), c.begin(), c.end());
    const int need = want - (int) above;
    if (need > 0) {
        auto better = [&](int32_t a, int32_t b) { return X.score[a] > X.score[b] || (X.score[a] == X.score[b] && a < b); };
        if ((int) cand.size() > need) std::nth_element(cand.begin(), cand.begin() + need, cand.end(), better);
        for (int i = 0; i < std::min(need, (int) cand.size()); ++i) X.mark[cand[i]] = 1;
    }
    for (int j = 0; j < std::min(S.sink, T); ++j) X.mark[j] = 1;
    for (int j = std::max(0, T - S.window); j < T; ++j) X.mark[j] = 1;
#pragma omp parallel
    {
        auto & p = X.part[omp_get_thread_num()];
#pragma omp for schedule(static)
        for (int j = 0; j < T; ++j) if (X.mark[j]) p.push_back(j);
    }
    X.idx.clear();
    for (auto & p : X.part) X.idx.insert(X.idx.end(), p.begin(), p.end());  // static schedule => thread order == key order
    double t2 = now();
    if (t_score) *t_score += t1 - t0;
    if (t_topk) *t_topk += t2 - t1;
    return (int) X.idx.size();
}

static void make_layer(Layer & L, int T, uint32_t seed, bool init_kv) {
    std::mt19937 rng(seed);
    std::normal_distribution<float> nd(0.f, 1.f);
    const size_t n = (size_t) T * KVH * D;
    L.k = (half_t *) aligned_alloc(64, n * 2);
    L.v = (half_t *) aligned_alloc(64, n * 2);
    L.ik = (half_t *) aligned_alloc(64, (size_t) T * IDX * 2);
    L.wq.resize((size_t) ROWS * IDX);
    for (auto & w : L.wq) w = nd(rng) / std::sqrt((float) ROWS);
    // first touch in parallel (spreads pages like the real KV allocation would not; kept simple, same for both arms)
#pragma omp parallel for schedule(static)
    for (int t = 0; t < T; ++t) {
        std::mt19937 r(seed * 7919u + t);
        std::normal_distribution<float> g(0.f, 1.f);
        for (int i = 0; i < KVH * D; ++i) { L.k[(size_t) t * KVH * D + i] = f2h(g(r)); L.v[(size_t) t * KVH * D + i] = f2h(g(r)); }
        float v[IDX], nrm = 0;
        for (int o = 0; o < IDX; ++o) { v[o] = g(r); nrm += v[o] * v[o]; }
        nrm = 1.f / std::sqrt(nrm);
        for (int o = 0; o < IDX; ++o) L.ik[(size_t) t * IDX + o] = f2bf(v[o] * nrm);
    }
    (void) init_kv;
}

// --check: exactness at small size: selection == brute-force exact top-k; sparse attention == double reference over the same set
static int check() {
    int fails = 0;
    for (int T : {700, 2048, 5000}) {
        for (int thr : {1, 3, 8}) {
            omp_set_num_threads(thr);
            Layer L; make_layer(L, T, 17 + T, true);
            Sel S{T / 5, 64, 4};
            std::mt19937 rng(5);
            std::normal_distribution<float> nd(0.f, 1.f);
            std::vector<float> q(QH * D), qi(IDX);
            for (auto & x : q) x = nd(rng);
            project_q(L, q.data(), qi.data());
            Scratch X;
            const int n = select_keys(L, T, qi.data(), S, X, nullptr, nullptr);
            // brute force
            std::vector<int> ord;
            for (int j = S.sink; j < T - S.window; ++j) ord.push_back(j);
            auto sc = [&](int j) { double a = 0; for (int o = 0; o < IDX; ++o) a += (double) bf2f(L.ik[(size_t) j * IDX + o]) * qi[o]; return a; };
            std::vector<double> s(T, 0);
            for (int j : ord) s[j] = sc(j);
            std::sort(ord.begin(), ord.end(), [&](int a, int b) { return s[a] > s[b] || (s[a] == s[b] && a < b); });
            std::vector<uint8_t> want(T, 0);
            for (int i = 0; i < std::min((int) ord.size(), S.top_k); ++i) want[ord[i]] = 1;
            for (int j = 0; j < S.sink; ++j) want[j] = 1;
            for (int j = T - S.window; j < T; ++j) want[j] = 1;
            // allow disagreement only between keys whose float32 score differs from the double score by < 2e-6 (boundary)
            int bad = 0;
            for (int j = 0; j < T; ++j) if (want[j] != X.mark[j]) {
                const double bound = S.top_k - 1 < (int) ord.size() ? s[ord[S.top_k - 1]] : -2;
                if (std::fabs(s[j] - bound) > 2e-6) bad++;
            }
            if (bad || !std::is_sorted(X.idx.begin(), X.idx.end())) { printf("FAIL select T=%d thr=%d bad=%d\n", T, thr, bad); fails++; }
            // attention vs double reference over the selected set, and dense vs reference over all keys
            std::vector<Partial> ws;
            std::vector<float> o1(QH * D), o2(QH * D);
            const float scale = 1.f / 16.f;
            for (int dense = 0; dense < 2; ++dense) {
                std::vector<int32_t> all(T);
                std::iota(all.begin(), all.end(), 0);
                const std::vector<int32_t> & set = dense ? all : X.idx;
                attention(L, T, q.data(), dense ? nullptr : set.data(), (int) set.size(), scale, o1.data(), 64, ws);
                double maxerr = 0;
                for (int h = 0; h < QH; ++h) {
                    const int g = h / G;
                    std::vector<double> lg(set.size());
                    double m = -1e300;
                    for (size_t i = 0; i < set.size(); ++i) {
                        double a = 0;
                        for (int d = 0; d < D; ++d) a += (double) q[h * D + d] * h2f(L.k[((size_t) set[i] * KVH + g) * D + d]);
                        lg[i] = a * scale; m = std::max(m, lg[i]);
                    }
                    double z = 0;
                    for (auto & x : lg) { x = std::exp(x - m); z += x; }
                    for (int d = 0; d < D; ++d) {
                        double a = 0;
                        for (size_t i = 0; i < set.size(); ++i) a += lg[i] / z * h2f(L.v[((size_t) set[i] * KVH + g) * D + d]);
                        maxerr = std::max(maxerr, std::fabs(a - o1[h * D + d]));
                    }
                }
                if (maxerr > 2e-5) { printf("FAIL attn T=%d thr=%d dense=%d maxerr=%g\n", T, thr, dense, maxerr); fails++; }
            }
            (void) n; (void) o2;
            free(L.k); free(L.v); free(L.ik);
        }
    }
    printf(fails ? "CHECK FAIL (%d)\n" : "CHECK PASS\n", fails);
    return fails ? 1 : 0;
}

int main(int argc, char ** argv) {
    int T = 32768, NL = 16, reps = 40, topk = 4096, win = 512, sink = 4, chunk = 512;
    std::string json;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto nxt = [&] { return std::string(argv[++i]); };
        if (a == "--check") return check();
        else if (a == "--kv") T = atoi(nxt().c_str());
        else if (a == "--layers") NL = atoi(nxt().c_str());
        else if (a == "--reps") reps = atoi(nxt().c_str());
        else if (a == "--topk") topk = atoi(nxt().c_str());
        else if (a == "--chunk") chunk = atoi(nxt().c_str());
        else if (a == "--json") json = nxt();
        else { fprintf(stderr, "unknown arg %s\n", a.c_str()); return 2; }
    }
    const int nt = omp_get_max_threads();
    std::vector<Layer> Ls(NL);
    for (int l = 0; l < NL; ++l) make_layer(Ls[l], T, 100 + l, true);
    std::mt19937 rng(9);
    std::normal_distribution<float> nd(0.f, 1.f);
    std::vector<float> q(QH * D), qi(IDX), out(QH * D);
    for (auto & x : q) x = nd(rng);
    Sel S{topk, win, sink};
    Scratch X;
    std::vector<Partial> ws;
    std::vector<double> dense_t, lsa_t, sc_t, tk_t, at_t, pj_t;
    long nsel = 0;
    const float scale = 1.f / 16.f;
    for (int rep = -3; rep < reps; ++rep) {
        double td = 0, tl = 0, ts = 0, tt = 0, ta = 0, tp = 0;
        for (int l = 0; l < NL; ++l) {
            double t0 = now();
            attention(Ls[l], T, q.data(), nullptr, T, scale, out.data(), chunk, ws);
            td += now() - t0;
        }
        for (int l = 0; l < NL; ++l) {
            double t0 = now();
            project_q(Ls[l], q.data(), qi.data());
            double t1 = now();
            const int n = select_keys(Ls[l], T, qi.data(), S, X, &ts, &tt);
            double t2 = now();
            attention(Ls[l], T, q.data(), X.idx.data(), n, scale, out.data(), chunk, ws);
            double t3 = now();
            tp += t1 - t0; ta += t3 - t2; tl += t3 - t0; nsel = n;
        }
        if (rep >= 0) { dense_t.push_back(td); lsa_t.push_back(tl); sc_t.push_back(ts); tk_t.push_back(tt); at_t.push_back(ta); pj_t.push_back(tp); }
    }
    auto med = [](std::vector<double> v) { std::sort(v.begin(), v.end()); return v[v.size() / 2]; };
    const double md = med(dense_t), ml = med(lsa_t);
    printf("threads=%d kv=%d layers=%d reps=%d selected=%ld\n", nt, T, NL, reps, nsel);
    printf("dense   per-token attention : %9.1f us\n", md * 1e6);
    printf("lsa     per-token total     : %9.1f us  (project_q %.1f, score %.1f, topk+mask %.1f, sparse attn %.1f)\n", ml * 1e6, med(pj_t) * 1e6, med(sc_t) * 1e6, med(tk_t) * 1e6, med(at_t) * 1e6);
    printf("dense/lsa = %.3f\n", md / ml);
    if (!json.empty()) {
        FILE * f = fopen(json.c_str(), "w");
        fprintf(f, "{\"threads\":%d,\"kv\":%d,\"layers\":%d,\"reps\":%d,\"selected\":%ld,\"dense_us\":%.3f,\"lsa_us\":%.3f,"
                   "\"project_us\":%.3f,\"score_us\":%.3f,\"topk_us\":%.3f,\"sparse_attn_us\":%.3f,\"dense_over_lsa\":%.5f,\"dense_us_all\":[",
                nt, T, NL, reps, nsel, md * 1e6, ml * 1e6, med(pj_t) * 1e6, med(sc_t) * 1e6, med(tk_t) * 1e6, med(at_t) * 1e6, md / ml);
        for (size_t i = 0; i < dense_t.size(); ++i) fprintf(f, "%s%.3f", i ? "," : "", dense_t[i] * 1e6);
        fprintf(f, "],\"lsa_us_all\":[");
        for (size_t i = 0; i < lsa_t.size(); ++i) fprintf(f, "%s%.3f", i ? "," : "", lsa_t[i] * 1e6);
        fprintf(f, "]}\n");
        fclose(f);
    }
    return 0;
}
