// Native metadata-only regression probe. Link to the experimental build under test.
// Never creates a context, reads weight payloads, or runs inference.
#include "llama.h"
#include "llama-model-loader.h"
#include "ggml-backend.h"
#include "gguf.h"
#include <cstdio>
#include <string>
#include <vector>
#include <stdexcept>

static void require(bool ok, const std::string & why) {
    if (!ok) throw std::runtime_error(why);
}
int main(int argc, char ** argv) {
    if (argc != 2) return 2;
    try {
        // Explicit CPU backend: don't discover or load a GPU backend on this shared host.
        require(ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_CPU) != nullptr,
                "CPU backend unavailable");
        auto params = llama_model_default_params();
        params.n_gpu_layers = 0;
        params.no_alloc = true;
        params.use_mmap = false;
        params.use_mlock = false;
        params.use_extra_bufts = false;
        params.n_load_threads = 1;
        // Unlike vocab_only, no_alloc traverses load_arch_tensors/check_tensor_dims and
        // backend weight-type support, then returns before load_all_data.
        auto * model = llama_model_load_from_file(argv[1], params);
        require(model != nullptr, "native metadata-only model load failed");
        llama_model_free(model);

        std::vector<std::string> splits;
        llama_model_loader ml(nullptr, nullptr, nullptr, argv[1], splits, nullptr,
                              false, false, false, true, false, nullptr, nullptr);
        require(ml.get_arch() == LLM_ARCH_DEEPSEEK41, "architecture registration mismatch");
        const std::vector<llm_kv> aliases = {
            LLM_KV_CONTEXT_LENGTH, LLM_KV_EMBEDDING_LENGTH, LLM_KV_BLOCK_COUNT,
            LLM_KV_EXPERT_COUNT, LLM_KV_EXPERT_USED_COUNT, LLM_KV_EXPERT_FEED_FORWARD_LENGTH,
            LLM_KV_EXPERT_SHARED_COUNT, LLM_KV_EXPERT_WEIGHTS_SCALE, LLM_KV_EXPERT_WEIGHTS_NORM,
            LLM_KV_EXPERT_GATING_FUNC, LLM_KV_SWIGLU_CLAMP_EXP, LLM_KV_ATTENTION_HEAD_COUNT,
            LLM_KV_ATTENTION_HEAD_COUNT_KV, LLM_KV_ATTENTION_KEY_LENGTH,
            LLM_KV_ATTENTION_VALUE_LENGTH, LLM_KV_ATTENTION_LAYERNORM_RMS_EPS,
            LLM_KV_ATTENTION_Q_LORA_RANK, LLM_KV_ATTENTION_SLIDING_WINDOW,
            LLM_KV_ATTENTION_OUTPUT_GROUP_COUNT, LLM_KV_ATTENTION_OUTPUT_LORA_RANK,
            LLM_KV_ATTENTION_COMPRESS_RATIOS, LLM_KV_ATTENTION_INDEXER_HEAD_COUNT,
            LLM_KV_ATTENTION_INDEXER_KEY_LENGTH, LLM_KV_ATTENTION_INDEXER_TOP_K,
            LLM_KV_HYPER_CONNECTION_COUNT, LLM_KV_HYPER_CONNECTION_SINKHORN_ITERATIONS,
            LLM_KV_HYPER_CONNECTION_EPSILON, LLM_KV_ROPE_DIMENSION_COUNT,
            LLM_KV_ROPE_SCALING_FACTOR
        };
        unsigned resolved = 0;
        for (auto key : aliases) {
            auto name = ml.kv_name(key);
            require(gguf_find_key(ml.metadata, name.c_str()) >= 0,
                    "unresolved antirez metadata alias: " + name);
            ++resolved;
        }
        // A canonical key must take precedence when both spellings are present.
        const auto canonical = ml.llm_kv(LLM_KV_CONTEXT_LENGTH);
        gguf_set_val_u32(ml.metadata, canonical.c_str(), 12345);
        uint32_t context = 0;
        ml.get_key(LLM_KV_CONTEXT_LENGTH, context);
        require(context == 12345, "canonical metadata precedence failed");

        unsigned shapes = 0, rejected = 0, types = 0;
        for (const auto & entry : ml.weights_map) {
            const auto & name = entry.first;
            auto * t = entry.second.tensor;
            require(t->type >= 0 && t->type < GGML_TYPE_COUNT, "invalid tensor type: " + name);
            require(ggml_type_size(t->type) > 0 && t->ne[0] % ggml_blck_size(t->type) == 0,
                    "invalid quantized row layout: " + name);
            ++types;
            std::vector<int64_t> expected(t->ne, t->ne + GGML_MAX_DIMS);
            ml.check_tensor_dims(name, expected, true, false);
            ++shapes;
            // Exercise the same native shape guard used by create_tensor, for EVERY tensor.
            ++expected[0];
            bool refused = false;
            try { ml.check_tensor_dims(name, expected, true, false); }
            catch (const std::runtime_error & err) {
                const std::string text = err.what();
                refused = text.find(name) != std::string::npos &&
                          text.find("wrong shape") != std::string::npos;
            }
            require(refused, "malformed tensor shape accepted: " + name);
            ++rejected;
        }
        require(shapes > 0, "empty model");
        std::printf("PASS arch=deepseek41 aliases=%u canonical_precedence=1 shapes=%u "
                    "shape_rejections=%u type_layouts=%u no_alloc=1 weight_reads=0\n",
                    resolved, shapes, rejected, types);
        return 0;
    } catch (const std::exception & err) {
        std::fprintf(stderr, "FAIL: %s\n", err.what());
        return 1;
    }
}
