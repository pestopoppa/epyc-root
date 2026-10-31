#include "ggml-cpu.h"
#include "qkv_snapshot.h"
#include <cmath>
#include <map>
#include <sstream>
static bool run(ggml_context *c, ggml_tensor *t, int nth, bool ref) {
  auto *g = ggml_new_graph(c);
  ggml_build_forward_expand(g, t);
  auto p = ggml_graph_plan(g, nth, nullptr);
  std::vector<unsigned char> w(p.work_size + 64, 0xa5);
  p.work_data = w.data();
  p.use_ref = ref;
  bool ok = ggml_graph_compute(g, &p) == GGML_STATUS_SUCCESS;
  for (size_t i = p.work_size; i < w.size(); i++)
    ok &= w[i] == 0xa5;
  return ok;
}
int main(int argc, char **argv) {
  try {
    if (argc != 3)
      throw std::runtime_error("usage PREFIX THREADS");
    std::string pre = argv[1];
    int nth = std::stoi(argv[2]);
    if (nth < 1 || nth > 96)
      throw std::runtime_error("threads");
    std::map<std::string, std::string> fields;
    std::ifstream m(pre + ".meta");
    std::string line;
    while (std::getline(m, line)) {
      const auto eq = line.find('=');
      if (eq == std::string::npos ||
          !fields.emplace(line.substr(0, eq), line.substr(eq + 1)).second)
        throw std::runtime_error("malformed/duplicate metadata");
    }
    if (!m.eof() || fields.at("schema") != "1" ||
        fields.at("phase") != "after_backend_synchronize")
      throw std::runtime_error(
          "unknown schema or unsynchronized capture phase");
    auto integer = [&](const std::string &key) {
      const auto &text = fields.at(key);
      size_t end = 0;
      int value = std::stoi(text, &end);
      if (end != text.size())
        throw std::runtime_error("noninteger metadata");
      return value;
    };
    std::map<std::string, int> meta;
    meta["threads"] = integer("threads");
    meta["iqk_on"] = integer("iqk_on");
    if (meta.at("threads") < 1 || meta.at("threads") > 96 ||
        (meta.at("iqk_on") != 0 && meta.at("iqk_on") != 1))
      throw std::runtime_error("invalid source threads/iqk");
    for (int i = 0; i < 5; ++i) {
      auto key = "present" + std::to_string(i);
      meta[key] = integer(key);
      if (meta.at(key) != 0 && meta.at(key) != 1)
        throw std::runtime_error("nonbinary source presence");
      if (i < 3 && !meta.at(key))
        throw std::runtime_error("QKV missing");
      if (meta.at(key)) {
        auto ak = "alias" + std::to_string(i);
        meta[ak] = integer(ak);
        int alias = meta.at(ak);
        if (alias < -1 || alias >= i ||
            (alias >= 0 && !meta.at("present" + std::to_string(alias))))
          throw std::runtime_error("invalid source alias");
      }
    }
    auto output = qkv::load(pre + ".out");
    auto *c = ggml_init({size_t(64) * 1024 * 1024, nullptr, true});
    if (!c)
      throw std::runtime_error("context");
    std::array<qkv::Tensor, 5> b;
    std::array<ggml_tensor *, 5> t{};
    for (int i = 0; i < 5; i++)
      if (meta.at("present" + std::to_string(i))) {
        b[i] = qkv::load(pre + ".src" + std::to_string(i));
        t[i] = qkv::restore(c, b[i]);
        int alias = meta.at("alias" + std::to_string(i));
        if (alias >= 0) {
          if (alias >= i || b[i].raw != b[alias].raw)
            throw std::runtime_error("alias mismatch");
          t[i]->data = t[alias]->data;
        }
      }
    if (output.type != GGML_TYPE_F32) {
      throw std::runtime_error("output is not f32");
    }
    float scale, maxbias, softcap;
    std::memcpy(&scale, &output.params[0], 4);
    std::memcpy(&maxbias, &output.params[1], 4);
    std::memcpy(&softcap, &output.params[2], 4);
    auto reg = ggml_backend_cpu_reg();
    auto set = (ggml_backend_cpu_set_iqk_fa_t)ggml_backend_reg_get_proc_address(
        reg, "ggml_backend_cpu_set_iqk_fa");
    auto get = (ggml_backend_cpu_get_iqk_fa_t)ggml_backend_reg_get_proc_address(
        reg, "ggml_backend_cpu_get_iqk_fa");
    auto count =
        (ggml_backend_cpu_iqk_fa_n_calls_t)ggml_backend_reg_get_proc_address(
            reg, "ggml_backend_cpu_iqk_fa_n_calls");
    if (!set || !get || !count)
      throw std::runtime_error("iqk APIs missing");
    set(true);
    if (!get())
      throw std::runtime_error("iqk not enabled");
    int failed = 0;
    // Reproduce the captured output with the source's native knob before
    // comparing counterfactuals.
    {
      auto *o = ggml_flash_attn_ext(c, t[0], t[1], t[2], t[3], scale, maxbias,
                                    softcap);
      std::memcpy(o->op_params, output.params.data(), GGML_MAX_OP_PARAMS);
      if (t[4])
        ggml_flash_attn_ext_add_sinks(o, t[4]);
      std::vector<unsigned char> bytes(ggml_nbytes(o));
      o->data = bytes.data();
      set(meta.at("iqk_on"));
      if (!run(c, o, meta.at("threads"), false) || bytes != output.raw)
        throw std::runtime_error("native captured-output roundtrip mismatch");
      printf("ROUNDTRIP captured_output_bitwise_equal=1 source_threads=%d "
             "source_iqk=%d\n",
             meta.at("threads"), meta.at("iqk_on"));
      set(true);
    }

    for (auto mode : {"original", "zero-present", "null"}) {
      if (std::string(mode) == "zero-present" && !t[4])
        continue;
      // A zero-sink intervention must not mutate another input even if the
      // original sink shared storage. Original mode retains all native aliases.
      auto *sink = t[4];
      auto zero = b[4];
      if (sink) {
        if (sink->type != GGML_TYPE_F32)
          throw std::runtime_error("sinks not f32");
        if (std::string(mode) == "zero-present") {
          std::fill(zero.raw.begin(), zero.raw.end(), 0);
          sink = qkv::restore(c, zero);
        }
      }
      std::array<std::vector<unsigned char>, 2> raw;
      for (int arm = 0; arm < 2; arm++) {
        auto *o = ggml_flash_attn_ext(c, t[0], t[1], t[2], t[3], scale, maxbias,
                                      softcap);
        std::memcpy(o->op_params, output.params.data(), GGML_MAX_OP_PARAMS);
        if (sink && std::string(mode) != "null")
          ggml_flash_attn_ext_add_sinks(o, sink);
        raw[arm].resize(ggml_nbytes(o));
        o->data = raw[arm].data();
        auto before = count();
        if (raw[arm].size() != output.raw.size() || !run(c, o, nth, arm == 0))
          throw std::runtime_error("compute/output shape");
        auto delta = count() - before;
        if ((arm == 0 && delta != 0) || (arm == 1 && delta == 0))
          throw std::runtime_error("reference/iqk route not observed");
      }
      double max = 0, mean = 0, err = 0, den = 0;
      auto *a = (float *)raw[0].data();
      auto *z = (float *)raw[1].data();
      for (size_t i = 0; i < raw[0].size() / 4; i++) {
        if (!std::isfinite(a[i]) || !std::isfinite(z[i]))
          throw std::runtime_error("nonfinite");
        double d = double(a[i]) - z[i];
        max = std::max(max, std::abs(d));
        mean += std::abs(d);
        err += d * d;
        den += double(a[i]) * a[i];
      }
      double nmse = den ? err / den : err ? INFINITY : 0;
      printf("RESULT sinks=%s nth=%d nmse=%.12g max_abs=%.12g mean_abs=%.12g "
             "threshold=0.0005 verdict=%s\n",
             mode, nth, nmse, max, mean / (raw[0].size() / 4),
             nmse <= 5e-4 ? "PASS" : "FAIL");
      failed |= nmse > 5e-4;
    }
    ggml_free(c);
    return failed;
  } catch (const std::exception &e) {
    fprintf(stderr, "REFUSED %s\n", e.what());
    return 2;
  }
}
