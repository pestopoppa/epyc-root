#include "native_carrier.h"
#include "ggml-cpu.h"

#include <algorithm>
#include <iostream>

static void check(bool ok, const char * message) {
    if (!ok) throw std::runtime_error(message);
}

static std::vector<uint8_t> bytes(ggml_tensor * t) {
    std::vector<uint8_t> result(ggml_nbytes(t));
    ggml_backend_tensor_get(t, result.data(), 0, result.size());
    return result;
}

template<class F> static void refuses(F action, const char * message) {
    bool rejected = false;
    try { action(); } catch (const std::invalid_argument &) { rejected = true; }
    check(rejected, message);
}

int main() {
    try {
        constexpr int D = 64, H = 4, KV = 2, T = 5, Q = 2;
        auto backend = ggml_backend_cpu_init();
        check(backend != nullptr, "no CPU backend");
        ggml_backend_cpu_set_n_threads(backend, 1);
        auto ctx = ggml_init({4*1024*1024, nullptr, true});
        check(ctx != nullptr, "no tensor context");
        auto * q = ggml_new_tensor_3d(ctx, GGML_TYPE_F32, D, Q, H);
        auto * k = ggml_new_tensor_3d(ctx, GGML_TYPE_F16, D, T, KV);
        auto * base = ggml_new_tensor_2d(ctx, GGML_TYPE_F16, T, 32);
        for (auto * t : {q, k, base}) ggml_set_input(t);
        auto off = am_carrier::build_mask(ctx, base, H, nullptr, nullptr);
        check(off.mask == base && off.input == nullptr && off.data.empty(), "default-off graph changed");
        off.upload();

        am_carrier::layer_fit fit;
        fit.layer = 3; fit.kv_heads = KV; fit.value_width = D;
        fit.positions = {10, 13};
        fit.beta = {std::log(4.f), -1.f, -2.f, std::log(5.f)};
        fit.values.resize(KV*2*D);
        for (size_t i = 0; i < fit.values.size(); ++i) fit.values[i] = float(int(i%19)-9)*0.15f;
        am_carrier::row_binding binding{{10, 13}, {1, 4}};
        auto fit2 = fit;
        fit2.layer = 7;
        for (auto & b : fit2.beta) b = -b;
        am_carrier::validate_layers({fit, fit2});
        auto different_positions = fit2;
        different_positions.positions.back() = 14;
        refuses([&] { am_carrier::validate_layers({fit, different_positions}); },
                "different layer selections accepted");
        refuses([&] { am_carrier::validate_layers({fit, fit}); }, "duplicate layer accepted");
        auto m0 = am_carrier::build_mask(ctx, base, H, &fit, &binding);
        auto m1 = am_carrier::build_mask(ctx, base, H, &fit2, &binding);
        check(m0.input != m1.input && m0.data != m1.data, "layers share beta storage");
        for (int h = 0; h < H; ++h) {
            check(m0.data[h*T + 1] == fit.beta[(h/2)*2], "GQA group mapping wrong");
            check(m0.data[h*T] == 0.f, "new/unfitted cell received beta");
        }
        auto * raw = ggml_new_tensor_2d(ctx, GGML_TYPE_Q8_0, KV*D, T);
        ggml_set_input(raw);
        auto * v = ggml_view_3d(ctx, raw, D, T, KV, raw->nb[1], ggml_row_size(raw->type, D), 0);
        auto * y0 = ggml_flash_attn_ext(ctx, q, k, v, m0.mask, 0.125f, 0.f, 0.f);
        auto * y1 = ggml_flash_attn_ext(ctx, q, k, v, m1.mask, 0.125f, 0.f, 0.f);
        for (auto * y : {y0, y1}) {
            ggml_set_output(y);
            ggml_flash_attn_ext_set_prec(y, GGML_PREC_F32);
        }
        auto * graph = ggml_new_graph(ctx);
        ggml_build_forward_expand(graph, y0);
        ggml_build_forward_expand(graph, y1);
        ggml_backend_t backends[] = {backend};
        auto sched = ggml_backend_sched_new(backends, nullptr, 1, 2048, false, false);
        check(ggml_backend_sched_alloc_graph(sched, graph), "graph allocation failed");
        std::vector<float> qf(D*Q*H);
        for (size_t i = 0; i < qf.size(); ++i) qf[i] = float(int(i%11)-5)*0.07f;
        ggml_backend_tensor_set(q, qf.data(), 0, qf.size()*sizeof(float));
        std::vector<float> kf(D*T*KV);
        std::vector<ggml_fp16_t> kh(kf.size());
        for (size_t i = 0; i < kf.size(); ++i) {
            kh[i] = ggml_fp32_to_fp16(float(int(i%17)-8)*0.06f);
            kf[i] = ggml_fp16_to_fp32(kh[i]);
        }
        ggml_backend_tensor_set(k, kh.data(), 0, kh.size()*sizeof(ggml_fp16_t));
        std::vector<ggml_fp16_t> bm(T*32, ggml_fp32_to_fp16(-INFINITY));
        // Query 0 sees selected cells; query 1 also sees a newly appended cell.
        bm[1] = bm[4] = bm[T] = bm[T+1] = bm[T+4] = ggml_fp32_to_fp16(0.f);
        ggml_backend_tensor_set(base, bm.data(), 0, bm.size()*sizeof(ggml_fp16_t));
        std::vector<float> initial(KV*D*T, 0.25f);
        std::vector<uint8_t> packed(ggml_nbytes(raw));
        ggml_get_type_traits(raw->type)->from_float_ref(initial.data(), packed.data(), initial.size());
        ggml_backend_tensor_set(raw, packed.data(), 0, packed.size());
        am_carrier::load_values(raw, 3, fit, binding);
        const auto written = bytes(raw);
        // Unselected rows stay bit-for-bit unchanged; selected rows are decoded
        // from the REAL Q8_0 storage for the independent attention oracle below.
        for (int row : {0, 2, 3}) {
            check(std::memcmp(written.data() + row*raw->nb[1], packed.data() + row*raw->nb[1],
                              raw->nb[1]) == 0, "unselected cache row changed");
        }
        std::vector<float> vf(initial.size());
        ggml_get_type_traits(raw->type)->to_float(written.data(), vf.data(), vf.size());
        double value_error = 0.;
        for (int h = 0; h < KV; ++h) for (int i = 0; i < 2; ++i) for (int d = 0; d < D; ++d) {
            value_error = std::max(value_error, std::abs(double(vf[binding.rows[i]*KV*D+h*D+d]) -
                                                       fit.values[(h*2+i)*D+d]));
        }
        check(value_error < 0.02, "C2 round-trip error too large");
        m0.upload(); m1.upload();
        check(ggml_backend_sched_graph_compute(sched, graph) == GGML_STATUS_SUCCESS, "carrier evaluation failed");
        std::vector<float> previous;
        double max_error = 0., effect = 0.;
        for (int layer = 0; layer < 2; ++layer) {
            const auto & gm = layer == 0 ? m0 : m1;
            auto * y = layer == 0 ? y0 : y1;
            std::vector<float> actual(ggml_nelements(y));
            ggml_backend_tensor_get(y, actual.data(), 0, actual.size()*sizeof(float));
            for (int t = 0; t < Q; ++t) for (int h = 0; h < H; ++h) {
                double scores[T], total = 0.;
                for (int row = 0; row < T; ++row) {
                    double score = 0.;
                    for (int d = 0; d < D; ++d) score += qf[(h*Q+t)*D+d]*double(kf[((h/2)*T+row)*D+d]);
                    const double mask = ggml_fp16_to_fp32(ggml_fp32_to_fp16(
                        ggml_fp16_to_fp32(bm[t*T+row]) + gm.data[h*T+row]));
                    scores[row] = std::exp(score*0.125 + mask);
                    total += scores[row];
                }
                for (int d = 0; d < D; ++d) {
                    double expected = 0.;
                    for (int row = 0; row < T; ++row) expected += scores[row]/total*vf[row*KV*D+(h/2)*D+d];
                    const size_t index = (t*H+h)*D+d;
                    max_error = std::max(max_error, std::abs(actual[index]-expected));
                    if (!previous.empty()) effect = std::max(effect, std::abs(double(actual[index]-previous[index])));
                }
            }
            previous = actual;
        }
        check(max_error < 0.002, "per-head native attention differs from independent oracle");
        check(effect > 0.1, "distinct layer beta has no measurable effect");

        // Refusals must leave EVERY byte unchanged, including earlier valid heads.
        auto bad = fit;
        bad.values.back() = NAN;
        refuses([&] { am_carrier::load_values(raw, 3, bad, binding); }, "nonfinite C2 accepted");
        refuses([&] { am_carrier::load_values(raw, 7, fit, binding); }, "wrong layer accepted");
        auto duplicate = binding; duplicate.rows[1] = duplicate.rows[0];
        refuses([&] { am_carrier::load_values(raw, 3, fit, duplicate); }, "duplicate physical row accepted");
        auto wrong = binding; wrong.positions[1] = 14;
        refuses([&] { am_carrier::load_values(raw, 3, fit, wrong); }, "wrong position binding accepted");
        auto out_of_range = binding; out_of_range.rows[1] = T;
        refuses([&] { am_carrier::load_values(raw, 3, fit, out_of_range); }, "out-of-range row accepted");
        refuses([&] { am_carrier::build_mask(ctx, base, 3, &fit, &binding); }, "nonintegral GQA accepted");
        refuses([&] { am_carrier::build_mask(ctx, base, H, &fit, &binding, 64); }, "mask byte budget ignored");
        bad = fit; bad.beta.back() = INFINITY;
        refuses([&] { am_carrier::build_mask(ctx, base, H, &bad, &binding); }, "nonfinite beta accepted");
        check(bytes(raw) == written, "refused load changed cache bytes");

        // Test F16 overflow after valid rows: two-phase conversion must refuse
        // before writing the first valid row. Also exercise F32/F16 success.
        auto aux = ggml_init({1024*1024, nullptr, true});
        auto * f16 = ggml_new_tensor_2d(aux, GGML_TYPE_F16, KV*D, T);
        auto * f32 = ggml_new_tensor_2d(aux, GGML_TYPE_F32, KV*D, T);
        auto buf = ggml_backend_alloc_ctx_tensors(aux, backend);
        check(buf != nullptr, "auxiliary allocation failed");
        ggml_backend_buffer_clear(buf, 0);
        const auto zero = bytes(f16);
        bad = fit; bad.values.back() = 1.e10f;
        refuses([&] { am_carrier::load_values(f16, 3, bad, binding); }, "F16 overflow accepted");
        check(bytes(f16) == zero, "overflow wrote earlier valid C2 rows");
        for (auto * target : {f16, f32}) am_carrier::load_values(target, 3, fit, binding);
        ggml_backend_buffer_free(buf); ggml_free(aux);
        ggml_backend_sched_free(sched); ggml_free(ctx); ggml_backend_free(backend);
        std::cout << "PASS carrier: two layers, 4Q/2KV GQA, sparse rows, Q8_0 C2, mask padding, "
                     "F32/F16 loading, default-off identity, validation atomicity\n"
                  << "max_attention_abs_error=" << max_error << " beta_layer_effect=" << effect
                  << " max_q8_value_error=" << value_error << '\n';
        return 0;
    } catch (const std::exception & e) {
        std::cerr << "FAIL " << e.what() << '\n'; return 1;
    }
}
