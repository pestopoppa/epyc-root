// Direct Meta subgraph fixture: a real host MEAN_D1 view follows a partial
// two-device matmul, as scheduler graph views can contain foreign view nodes.
// Built against candidate libraries. --reject must abort on foreign compute.
#ifndef META_SOURCE
#define META_SOURCE "/mnt/raid0/llm/worktrees/meta-fix-c5/ggml/src/ggml-backend-meta.cpp"
#endif
#include META_SOURCE
#include "ggml-alloc.h"
#include "ggml-cpu.h"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdlib>

static void require(bool b, const char * m) { if (!b) { std::fprintf(stderr, "%s\n", m); std::exit(1); } }
static ggml_backend_meta_split_state split(const ggml_tensor *, void *) {
    ggml_backend_meta_split_state s{};
    s.axis = GGML_BACKEND_SPLIT_AXIS_0;
    s.ne[0] = 2; s.ne[1] = 2; s.nr[0] = 1; s.n_segments = 1;
    return s;
}
static void quiet_abort(const char * message) { std::fprintf(stderr, "FIXTURE_ABORT:%s\n", message); }
int main(int argc, char ** argv) {
    const bool reject = argc == 2 && std::strcmp(argv[1], "--reject") == 0;
    require(argc == 1 || reject, "bad argument");
    ggml_backend_dev_t cpu_dev = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_CPU);
    require(cpu_dev != nullptr, "CPU device missing");
    ggml_backend_dev_t devices[] = { cpu_dev, cpu_dev };
    ggml_backend_t meta = ggml_backend_dev_init(ggml_backend_meta_device(devices, 2, split, nullptr), nullptr);
    ggml_backend_t cpu = ggml_backend_dev_init(cpu_dev, nullptr);
    require(meta && cpu, "backend init failed");
    ggml_init_params p = { 8 * 1024 * 1024, nullptr, true };
    ggml_context * weights = ggml_init(p);
    ggml_context * work = ggml_init(p);
    ggml_context * host = ggml_init(p);
    require(weights && work && host, "context init failed");
    ggml_tensor * a = ggml_new_tensor_2d(weights, GGML_TYPE_F32, 4, 1);
    ggml_tensor * b = ggml_new_tensor_2d(weights, GGML_TYPE_F32, 4, 1);
    ggml_backend_buffer_t wb = ggml_backend_alloc_ctx_tensors(weights, meta);
    require(wb, "weight allocation failed");
    ggml_backend_buffer_set_usage(wb, GGML_BACKEND_BUFFER_USAGE_WEIGHTS);
    const float av[] = {1, 2, 3, 4}, bv[] = {5, 6, 7, 8};
    ggml_backend_tensor_set(a, av, 0, sizeof av);
    ggml_backend_tensor_set(b, bv, 0, sizeof bv);
    ggml_tensor * dot = ggml_mul_mat(work, a, b);
    ggml_cgraph * graph = ggml_new_graph_custom(work, 32, false);
    ggml_build_forward_expand(graph, dot);
    ggml_gallocr_t alloc = ggml_gallocr_new(ggml_backend_get_default_buffer_type(meta));
    require(alloc && ggml_gallocr_alloc_graph(alloc, graph), "meta graph allocation failed");
    require(ggml_backend_meta_get_split_state(dot, false).axis == GGML_BACKEND_SPLIT_AXIS_PARTIAL,
            "fixture did not produce a partial matmul");
    ggml_tensor * x = ggml_new_tensor_2d(host, GGML_TYPE_F32, 2, 2);
    ggml_tensor * mean = ggml_mean_d1(host, x);
    ggml_tensor * view = ggml_reshape_1d(host, mean, 2);
    ggml_cgraph * hg = ggml_new_graph_custom(host, 32, false);
    ggml_build_forward_expand(hg, view);
    ggml_backend_buffer_t hb = ggml_backend_alloc_ctx_tensors(host, cpu);
    require(hb, "host allocation failed");
    const float hv[] = {1, 2, 3, 4};
    ggml_backend_tensor_set(x, hv, 0, sizeof hv);
    require(ggml_backend_graph_compute(cpu, hg) == GGML_STATUS_SUCCESS, "host mean failed");
    float expected_host[2]; ggml_backend_tensor_get(view, expected_host, 0, sizeof expected_host);
    require(expected_host[0] == 2 && expected_host[1] == 3, "host mean wrong");
    ggml_tensor * tail = reject ? mean : view;
    ggml_graph_add_node(graph, tail);
    const size_t pos = ggml_hash_insert(&graph->visited_hash_set, tail);
    graph->use_counts[pos] = 0;
    ggml_set_abort_callback(quiet_abort);
    std::fprintf(stderr, "FIXTURE_READY partial=1 host_mean=2,3 tail=%s\n", reject ? "foreign-compute" : "host-view");
    require(ggml_backend_graph_compute(meta, graph) == GGML_STATUS_SUCCESS, "Meta graph failed");
    require(!reject, "foreign compute was accepted");
    for (size_t j = 0; j < 2; ++j) {
        const ggml_tensor * simple = ggml_backend_meta_buffer_simple_tensor(dot, j);
        require(simple != nullptr, "missing simple result tensor");
        float actual = 0; ggml_backend_tensor_get(simple, &actual, 0, sizeof actual);
        require(std::fabs(actual - 70.0f) < 1e-5f, "partial reduction produced wrong dot product");
    }
    float observed[2]; ggml_backend_tensor_get(view, observed, 0, sizeof observed);
    require(observed[0] == expected_host[0] && observed[1] == expected_host[1], "host view changed");
    std::puts("PASS mixed Meta/host trailing view and two-device partial reduction");
    ggml_gallocr_free(alloc); ggml_backend_buffer_free(hb); ggml_backend_buffer_free(wb);
    ggml_free(host); ggml_free(work); ggml_free(weights); ggml_backend_free(cpu); ggml_backend_free(meta);
}
