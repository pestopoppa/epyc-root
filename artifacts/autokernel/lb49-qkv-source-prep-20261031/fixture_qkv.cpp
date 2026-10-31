#include "ggml-cpu.h"
#include "qkv_snapshot.h"
#include <cmath>
int main(int argc, char **argv) {
  try {
    if (argc != 2)
      return 2;
    auto reg = ggml_backend_cpu_reg();
    auto set = (ggml_backend_cpu_set_iqk_fa_t)ggml_backend_reg_get_proc_address(
        reg, "ggml_backend_cpu_set_iqk_fa");
    if (!set)
      throw std::runtime_error("missing setter");
    set(false);
    constexpr int D = 64, H = 4, N = 2, K = 32;
    auto *c = ggml_init({1024 * 1024, nullptr, true});
    auto *q0 = ggml_new_tensor_3d(c, GGML_TYPE_F32, D, H, N);
    auto *k0 = ggml_new_tensor_3d(c, GGML_TYPE_F32, D, K, 1);
    auto *m0 = ggml_new_tensor_4d(c, GGML_TYPE_F32, K, 32, 1, 1);
    auto *s0 = ggml_new_tensor_1d(c, GGML_TYPE_F32, H);
    auto *q = ggml_permute(c, ggml_scale(c, q0, 0.5f), 0, 2, 1, 3);
    auto *k = ggml_cast(c, ggml_scale(c, k0, 0.25f), GGML_TYPE_F16);
    auto *mask = ggml_cast(c, ggml_scale(c, m0, 1.0f), GGML_TYPE_F16);
    auto *sinks = ggml_scale(c, s0, 0.5f);
    auto *out = ggml_flash_attn_ext(c, q, k, k, mask, 1.0f / sqrtf(D), 0, 0);
    ggml_flash_attn_ext_add_sinks(out, sinks);
    auto *g = ggml_new_graph(c);
    ggml_build_forward_expand(g, out);
    auto backend = ggml_backend_cpu_init();
    ggml_backend_t bs[] = {backend};
    auto sched = ggml_backend_sched_new(bs, nullptr, 1, GGML_DEFAULT_GRAPH_SIZE,
                                        false, false);
    qkv::Capture cap{};
    cap.prefix = argv[1];
    cap.probe_early = true;
    ggml_backend_sched_set_eval_callback(sched, qkv::callback, &cap);
    if (!ggml_backend_sched_alloc_graph(sched, g))
      throw std::runtime_error("allocation");
    for (int i = 0; i < ggml_graph_n_nodes(g); i++) {
      auto *t = ggml_graph_node(g, i);
      std::vector<unsigned char> poison(ggml_nbytes(t), 0xff);
      ggml_backend_tensor_set(t, poison.data(), 0, poison.size());
    }
    for (auto *t : {q0, k0, m0, s0}) {
      std::vector<float> v(ggml_nelements(t));
      for (size_t i = 0; i < v.size(); i++)
        v[i] = t == m0 ? 0.0f : float(int(i % 31) - 15) / 31;
      ggml_backend_tensor_set(t, v.data(), 0, v.size() * 4);
    }
    if (ggml_backend_sched_graph_compute(sched, g) != GGML_STATUS_SUCCESS ||
        cap.failed || cap.count != 1)
      throw std::runtime_error("compute/capture");
    auto qgot = qkv::load(std::string(argv[1]) + ".src0");
    if (cap.early[0] == qgot.raw)
      throw std::runtime_error("early capture negative control did not differ");
    for (int h = 0; h < H; h++)
      for (int n = 0; n < N; n++)
        for (int d = 0; d < D; d++) {
          float got;
          std::memcpy(&got,
                      qgot.raw.data() + d * qgot.nb[0] + n * qgot.nb[1] +
                          h * qgot.nb[2],
                      4);
          float want = float((d + D * h + D * H * n) % 31 - 15) / 31 * 0.5f;
          if (got != want)
            throw std::runtime_error("after capture incorrect");
        }
    if (qgot.nb[1] <= qgot.nb[2])
      throw std::runtime_error("fixture is contiguous");
    auto captured = qkv::load(std::string(argv[1]) + ".out");
    auto actual = qkv::take(out);
    if (captured.raw != actual.raw)
      throw std::runtime_error("output mismatch");
    printf("PASS prior-op-derived QKV/mask/sinks; noncontiguous Q; K=V alias; "
           "ask-time poisoned negative control; synchronized output exact\n");
    ggml_backend_sched_free(sched);
    ggml_backend_free(backend);
    ggml_free(c);
    return 0;
  } catch (const std::exception &e) {
    fprintf(stderr, "FAIL %s\n", e.what());
    return 1;
  }
}
