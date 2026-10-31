#include "ggml-backend.h"
#include "ggml-cpu.h"
#include "llama.h"
#include "qkv_snapshot.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
using qkv::Capture;
int main(int argc, char **argv) {
  if (argc != 6) {
    std::fprintf(stderr, "usage MODEL PREFIX THREADS VARIANT PROMPT\n");
    return 2;
  }
  const int threads = std::atoi(argv[3]);
  const std::string variant = argv[4];
  if (threads < 1 || threads > 96 ||
      (variant != "baseline" && variant != "candidate-on") ||
      !std::filesystem::path(argv[1]).is_absolute() ||
      !std::filesystem::path(argv[2]).is_absolute())
    return 2;
  llama_backend_init();
  auto reg = ggml_backend_cpu_reg();
  auto get = reinterpret_cast<ggml_backend_cpu_get_iqk_fa_t>(
      ggml_backend_reg_get_proc_address(reg, "ggml_backend_cpu_get_iqk_fa"));
  if (variant == "candidate-on") {
    auto set = reinterpret_cast<ggml_backend_cpu_set_iqk_fa_t>(
        ggml_backend_reg_get_proc_address(reg, "ggml_backend_cpu_set_iqk_fa"));
    if (!set || !get)
      return 3;
    set(true);
    if (!get())
      return 3;
  } else if (get && get())
    return 3;
  auto mp = llama_model_default_params();
  mp.n_gpu_layers = 0;
  mp.use_mmap = true;
  mp.use_mlock = false;
  auto *model = llama_model_load_from_file(argv[1], mp);
  if (!model)
    return 4;
  Capture c{};
  c.prefix = argv[2];
  c.threads = threads;
  c.iqk_on = variant == "candidate-on";
  auto cp = llama_context_default_params();
  cp.n_ctx = 512;
  cp.n_batch = 512;
  cp.n_ubatch = 512;
  cp.n_threads = threads;
  cp.n_threads_batch = threads;
  cp.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_ENABLED;
  cp.cb_eval = qkv::callback;
  cp.cb_eval_user_data = &c;
  auto *ctx = llama_init_from_model(model, cp);
  if (!ctx)
    return 5;
  auto *v = llama_model_get_vocab(model);
  std::vector<llama_token> tokens(std::strlen(argv[5]) + 16);
  int n = llama_tokenize(v, argv[5], std::strlen(argv[5]), tokens.data(),
                         tokens.size(), llama_vocab_get_add_bos(v), false);
  if (n <= 0 || n > 512) {
    return 6;
  }
  auto batch = llama_batch_get_one(tokens.data(), n);
  int rc = llama_decode(ctx, batch);
  auto *logits = llama_get_logits_ith(ctx, -1);
  int nv = llama_vocab_n_tokens(v);
  if (rc || c.failed || !c.count || !logits || nv <= 0)
    return 7;
  for (int i = 0; i < nv; i++) {
    if (!std::isfinite(logits[i]))
      return 9;
  }
  int top = std::max_element(logits, logits + nv) - logits;
  std::ofstream out(c.prefix + ".logits.f32", std::ios::binary);
  out.write(reinterpret_cast<const char *>(logits), nv * sizeof(float));
  out.close();
  if (!out)
    return 8;
  std::ofstream summary(c.prefix + ".summary.txt");
  summary << "variant=" << variant << "\nthreads=" << threads
          << "\nnodes=" << c.count << "\nvocab=" << nv << "\nprompt=" << argv[5]
          << "\nfirst_generated_token=" << top << "\ntokens=";
  for (int i = 0; i < n; i++)
    summary << (i ? "," : "") << tokens[i];
  summary << "\n";
  if (!summary)
    return 8;
  llama_free(ctx);
  llama_model_free(model);
  llama_backend_free();
  return 0;
}
