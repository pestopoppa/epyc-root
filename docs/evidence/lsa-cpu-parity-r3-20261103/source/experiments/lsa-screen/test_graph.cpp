#include "ggml.h"
#include "ggml-cpu.h"
#include "../../src/models/lsa-screen-reference.h"
#include <cmath>
#include <cstdio>
#include <algorithm>

int main() {
    ggml_init_params p = { 16*1024*1024, nullptr, false };
    ggml_context * ctx = ggml_init(p);
    auto * m = ggml_new_tensor_4d(ctx, GGML_TYPE_F32, 32, 4, 1, 1);
    auto * qs = ggml_new_tensor_3d(ctx, GGML_TYPE_F32, 512, 24, 2);
    auto * ks = ggml_new_tensor_4d(ctx, GGML_TYPE_F32, 512, 4, 32, 1);
    auto * q = ggml_view_3d(ctx, qs, 256, 24, 2, qs->nb[1], qs->nb[2], 0);
    auto * k = ggml_view_4d(ctx, ks, 256, 4, 32, 1, ks->nb[1], ks->nb[2], ks->nb[3], 0);
    for (int i = 0; i < 2; ++i) for (int h = 0; h < 24; ++h) for (int d = 0; d < 512; ++d)
        static_cast<float *>(qs->data)[(i*24+h)*512+d] = float(i*100000+h*512+d);
    for (int i = 0; i < 32; ++i) for (int h = 0; h < 4; ++h) for (int d = 0; d < 512; ++d)
        static_cast<float *>(ks->data)[(i*4+h)*512+d] = float(i*10000+h*512+d);
    auto * data = static_cast<float *>(m->data);
    for (int i = 0; i < 4; ++i) for (int j = 0; j < 32; ++j)
        data[i*32+j] = j <= 16+i ? 0.0f : -INFINITY;
    auto * result = ggml_map_custom3(ctx, m, q, k, lsa_screen_mask, 1, reinterpret_cast<void *>(3));
    auto * graph = ggml_new_graph(ctx);
    ggml_build_forward_expand(graph, result);
    if (ggml_graph_compute_with_ctx(ctx, graph, 1) != GGML_STATUS_SUCCESS) return 2;
    if (ggml_graph_compute_with_ctx(ctx, graph, 4) != GGML_STATUS_SUCCESS) return 2;
    auto * actual = static_cast<float *>(result->data);
    for (int i = 0; i < 128; ++i) if (actual[i] != data[i]) return 3;
    auto * multi = ggml_map_custom3(ctx, m, q, k, lsa_screen_mask, GGML_N_TASKS_MAX, reinterpret_cast<void *>(3));
    auto * graph_multi = ggml_new_graph(ctx);
    ggml_build_forward_expand(graph_multi, multi);
    if (ggml_graph_compute_with_ctx(ctx, graph_multi, 4) != GGML_STATUS_SUCCESS) return 2;
    actual = static_cast<float *>(multi->data);
    for (int i = 0; i < 128; ++i) if (actual[i] != data[i]) return 3;
    ggml_free(ctx);
    std::puts("custom mask graph: OK (1 and 4 threads, one and all tasks)");
}
