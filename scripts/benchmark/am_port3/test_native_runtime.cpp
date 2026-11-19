#include "native_runtime.h"
#include "ggml-cpu.h"
#include <iostream>

static void check(bool ok, const char * why) {
    if (!ok) throw std::runtime_error(why);
}
template<class F> static void refuses(F f) {
    bool refused = false;
    try { f(); } catch (const std::invalid_argument &) { refused = true; }
    check(refused, "invalid native binding accepted");
}
static void cell(llama_kv_cells & cells, int row, int pos, int seq = 0) {
    cells.pos_set(row, pos);
    cells.seq_add(row, seq);
}

int main() {
    try {
        llama_kv_cells cells;
        cells.resize(8);
        cell(cells, 1, 10); cell(cells, 6, 20);
        am_carrier::layer_fit fit{3, 2, 64, {10, 20}, {1.f, 2.f, 3.f, 4.f}, std::vector<float>(256, 0.f)};
        fit.validate();
        auto resolve = [&](int64_t capacity) {
            return am_carrier::resolve_positions(cells, 0, fit.positions, capacity);
        };
        check(resolve(8).rows == std::vector<int64_t>({1, 6}), "physical rows inferred from positions");
        refuses([&] { resolve(6); });
        cell(cells, 2, 10);
        refuses([&] { resolve(8); });
        cells.rm(2);
        cells.seq_add(1, 1);
        refuses([&] { resolve(8); });
        cells.seq_rm(1, 1);
        cells.ext_set(1, llama_kv_cell_ext{});
        auto ext = cells.ext_get(1); ext.beta = 0.5f; cells.ext_set(1, ext);
        refuses([&] { resolve(8); });
        cells.ext_set(1, llama_kv_cell_ext{});
        cells.pos_add(6, 1);
        refuses([&] { resolve(8); });
        cells.reset(); cell(cells, 1, 10); cell(cells, 6, 20);

        auto backend = ggml_backend_cpu_init();
        check(backend != nullptr, "no CPU backend");
        ggml_backend_cpu_set_n_threads(backend, 1);
        auto ctx = ggml_init({4*1024*1024, nullptr, true});
        auto * base = ggml_new_tensor_2d(ctx, GGML_TYPE_F16, 8, 32);
        ggml_set_input(base);
        int checks = 0;
        auto batch_check = [&](const llama_ubatch &) { ++checks; };
        am_carrier::graph_input first(ctx, base, 4, fit, resolve, batch_check);
        auto second_fit = fit; second_fit.layer = 7;
        for (auto & beta : second_fit.beta) beta *= -1.f;
        am_carrier::graph_input second(ctx, base, 4, second_fit, resolve, batch_check);
        auto * graph = ggml_new_graph(ctx);
        for (auto * input : {&first, &second}) {
            ggml_set_output(input->mask.mask);
            ggml_build_forward_expand(graph, input->mask.mask);
        }
        ggml_backend_t backends[] = {backend};
        auto sched = ggml_backend_sched_new(backends, nullptr, 1, 2048, false, false);
        check(ggml_backend_sched_alloc_graph(sched, graph), "allocation failed");
        std::vector<ggml_fp16_t> zero(8*32, ggml_fp32_to_fp16(0.f));
        zero[0] = ggml_fp32_to_fp16(-INFINITY);
        ggml_backend_tensor_set(base, zero.data(), 0, zero.size()*sizeof(ggml_fp16_t));
        llama_ubatch batch{};
        for (int iteration = 0; iteration < 2; ++iteration) {
            if (iteration) {
                // Same allocated graph; resolve a changed physical layout.
                cells.reset(); cell(cells, 3, 10); cell(cells, 5, 20); cell(cells, 7, 21);
            }
            first.set_input(&batch); second.set_input(&batch);
            check(ggml_backend_sched_graph_compute(sched, graph) == GGML_STATUS_SUCCESS, "compute failed");
            for (auto * input : {&first, &second}) {
                std::vector<ggml_fp16_t> output(8*32*4);
                ggml_backend_tensor_get(input->mask.mask, output.data(), 0, output.size()*sizeof(ggml_fp16_t));
                for (int h = 0; h < 4; ++h) for (int q = 0; q < 32; ++q) for (int row = 0; row < 8; ++row) {
                    float expected = 0.f;
                    if (q == 0 && row == 0) expected = -INFINITY;
                    const auto rows = resolve(8).rows;
                    for (size_t i = 0; i < rows.size(); ++i) {
                        if (row == rows[i]) expected += input->fit.beta[(h/2)*2 + i];
                    }
                    check(ggml_fp16_to_fp32(output[(h*32 + q)*8 + row]) == expected,
                          "reused graph has stale or cross-layer beta");
                }
            }
        }
        check(checks == 4, "batch checks skipped on graph reuse");
        cells.rm(5);
        refuses([&] { first.set_input(&batch); });
        ggml_backend_sched_free(sched); ggml_free(ctx); ggml_backend_free(backend);
        std::cout << "PASS runtime: real native cells, sparse physical binding, two layers, "
                     "4Q/2KV GQA, allocated-graph reuse/upload, original mask holes, "
                     "new rows zero, missing/duplicate/shared/shifted/scalar-beta refusals\n";
        return 0;
    } catch (const std::exception & e) {
        std::cerr << "FAIL " << e.what() << '\n'; return 1;
    }
}
