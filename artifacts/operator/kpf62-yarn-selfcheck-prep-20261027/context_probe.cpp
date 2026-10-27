// PROPOSAL: compile in a private owner CPU build against the accepted source.
// A context load is allowed only within the booked native job, not preflight.
#include "llama.h"
#include "llama-context.h"
#include "llama-cparams.h"
#include "llama-ext.h"
#include "ggml-backend.h"
#include <initializer_list>
#include <limits>
#include <cstdio>
#include <cmath>
int main(int argc, char **argv) {
    if (argc != 2) return 64;
    ggml_backend_load_all_from_path("/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build/build/bin");
    llama_backend_init();
    auto mp = llama_model_default_params();
    mp.n_gpu_layers = 0;
    llama_model *model = llama_model_load_from_file(argv[1], mp);
    if (!model) return 65;
    auto cp = llama_context_default_params();
    cp.n_ctx = 8192;
    cp.n_seq_max = 8;
    cp.n_batch = 512;
    cp.n_ubatch = 512;
    cp.type_k = GGML_TYPE_F32;
    cp.type_v = GGML_TYPE_F32;
    cp.n_threads = 1;
    cp.n_threads_batch = 1;
    llama_context *ctx = llama_init_from_model(model, cp);
    if (!ctx) { llama_model_free(model); return 66; }
    const auto &actual = ctx->get_cparams();
    printf("freq_scale=%.9g yarn_ext_factor=%.9g yarn_attn_factor=%.9g ggml_mscale=%.9g\n", actual.rope_freq_scale, actual.yarn_ext_factor, actual.yarn_attn_factor, actual.yarn_attn_factor * (1.0f + 0.1f * logf(1.0f / actual.rope_freq_scale)));
    bool ok = fabsf(actual.rope_freq_scale - 0.25f) < 1e-6f && fabsf(actual.yarn_ext_factor - 1.0f) < 1e-6f && fabsf(actual.yarn_attn_factor - 1.25f) < 1e-5f;
    for (llama_pos d : {1, 17, 300, 4096}) {
        double nmse = -1.0;
        bool passed = llama_chunk_kv_rope_selfcheck(ctx, d, &nmse);
        printf("delta=%d selfcheck=%d nmse=%.17g\n", d, passed, nmse);
        ok = ok && passed && std::isfinite(nmse) && nmse >= 0.0 && nmse <= 1e-6;
    }
    double invalid_nmse = -1.0;
    bool invalid_result = llama_chunk_kv_rope_selfcheck(ctx, std::numeric_limits<llama_pos>::max(), &invalid_nmse);
    printf("invalid_delta_refused=%d\n", !invalid_result);
    ok = ok && !invalid_result;
    llama_free(ctx); llama_model_free(model); llama_backend_free();
    return ok ? 0 : 67;
}
