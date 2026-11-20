// Diagnostic executable for worker.py, built ONLY against an experimental tree.
// Fresh contexts per block deliberately avoid hybrid partial-rollback ambiguity.
// This is a numerical/acceptance probe, never a throughput benchmark.
#include "common.h"
#include "speculative.h"
#include "json.hpp"
#include "native_witness.h"
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <memory>
#include <set>

using json = nlohmann::json;
using context_ptr = std::unique_ptr<llama_context, decltype(&llama_free)>;

static void require(bool condition, const char * why) {
    if (!condition) throw std::runtime_error(why);
}

static void keys(const json & value, std::set<std::string> expected) {
    require(value.is_object(), "settings must be an object");
    for (auto it = value.begin(); it != value.end(); ++it)
        require(expected.erase(it.key()) == 1, "unsupported setting");
    require(expected.empty(), "missing explicit setting");
}

static int integer(const json & value, int low, int high) {
    require(value.is_number_integer(), "expected integer setting");
    const auto n = value.get<int64_t>();
    require(n >= low && n <= high, "setting outside diagnostic bound");
    return int(n);
}

struct batch_guard {
    llama_batch value;
    explicit batch_guard(int n) : value(llama_batch_init(n, 0, 1)) {}
    ~batch_guard() { llama_batch_free(value); }
};

static context_ptr context(llama_model * model, const common_params & p) {
    context_ptr ctx(llama_init_from_model(model, common_context_params_to_llama(p)), llama_free);
    require(bool(ctx), "target context initialization failed");
    return ctx;
}

static void decode(llama_context * ctx, llama_batch & batch) {
    require(llama_decode(ctx, batch) == 0, "target decode failed");
}

static json produce(const json & request) {
    require(request.at("schema") == "epyc.target-precision.native-trace.v1", "wrong protocol");
    require(request.at("trace_semantics") == "greedy_prefix_acceptance_and_same_prefix_verify_vs_serial_logits",
            "unsupported trace semantics");
    const auto & settings = request.at("settings");
    const auto & v = settings.at("verification");
    keys(v, {"mode", "ubatch", "batch", "context", "draft_max", "blocks", "threads", "flash_attention", "kv_type", "replay"});
    require(v.at("mode") == "block" && v.at("replay") == "fresh-block-serial-v1", "unsupported replay mode");
    require(v.at("kv_type") == "f16", "only explicit f16 KV supported");
    const auto & sampling = settings.at("sampling");
    keys(sampling, {"temperature", "top_k"});
    require(sampling.at("temperature").is_number() && sampling.at("temperature") == 0 &&
            integer(sampling.at("top_k"), 1, 1) == 1, "only greedy sampling supported");
    const auto seed = request.at("case").at("seed");
    require(seed.is_number_unsigned() || seed.is_number_integer(), "invalid seed");
    require(seed.get<int64_t>() >= 0 && seed.get<uint64_t>() <= UINT32_MAX, "seed outside uint32");
    common_params p;
    p.n_ctx = integer(v.at("context"), 32, 8192);
    p.n_batch = integer(v.at("batch"), 2, 8192);
    p.n_ubatch = integer(v.at("ubatch"), 2, p.n_batch);
    const int width = integer(v.at("draft_max"), 1, 16);
    const int blocks = integer(v.at("blocks"), 1, 16);
    require(width + 1 <= p.n_ubatch, "verify block must fit one ubatch");
    p.cpuparams.n_threads = p.cpuparams_batch.n_threads = integer(v.at("threads"), 1, 256);
    const auto backend = settings.at("backend");
    require(backend == "cpu" || backend == "hip", "unsupported backend");
    p.n_gpu_layers = backend == "cpu" ? 0 : 99;
    p.flash_attn_type = v.at("flash_attention") == "on" ? LLAMA_FLASH_ATTN_TYPE_ENABLED : LLAMA_FLASH_ATTN_TYPE_DISABLED;
    require(v.at("flash_attention") == "on" || v.at("flash_attention") == "off", "flash setting required");
    p.cache_type_k = p.cache_type_v = GGML_TYPE_F16;
    p.n_outputs_max = p.n_batch;
    p.warmup = false;
    p.sampling.temp = 0;
    p.sampling.top_k = 1;
    p.sampling.seed = seed.get<uint32_t>();
    const auto & runtime = request.at("runtime");
    p.model.path = runtime.at("targets").at(request.at("case").at("target_quant").get<std::string>()).get<std::string>();
    p.speculative.types = {COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH};
    p.speculative.draft.mparams.path = runtime.at("drafter").get<std::string>();
    p.speculative.draft.n_gpu_layers = p.n_gpu_layers;
    p.speculative.draft.cpuparams = p.cpuparams;
    p.speculative.draft.cpuparams_batch = p.cpuparams_batch;
    p.speculative.draft.cache_type_k = p.speculative.draft.cache_type_v = GGML_TYPE_F16;
    p.speculative.draft.n_max = width;
    p.speculative.draft.p_min = 0;
    auto target = common_init_from_params(p, true);
    require(bool(target) && target->model(), "target model loading failed");
    auto * model = target->model();
    auto prefix = common_tokenize(llama_model_get_vocab(model), request.at("prompt").get<std::string>(), true, true);
    require(!prefix.empty(), "empty tokenized prompt");
    const int vocab = llama_vocab_n_tokens(llama_model_get_vocab(model));
    require(vocab > 0 && vocab <= 1000000, "vocabulary outside diagnostic bound");
    json trace = {{"request", request}, {"status", "ok"}, {"spec_type", "draft-dflash"}, {"blocks", json::array()},
                  {"numerical_encoding", "full-vocabulary-moments-v1"}};
    for (int b = 0; b < blocks; ++b) {
        require(prefix.size() + width < size_t(p.n_ctx), "context exhausted before declared blocks");
        auto verify = context(model, p);
        auto draft_params = common_base_params_to_speculative(p);
        auto draft_init = common_speculative_init_from_params(draft_params, model, verify.get());
        require(bool(draft_init) && draft_init->context(), "draft model initialization failed");
        p.speculative.draft.ctx_tgt = verify.get();
        p.speculative.draft.ctx_dft = draft_init->context();
        common_speculative_ptr spec(common_speculative_init(p.speculative, 1));
        require(bool(spec), "DFlash initialization failed");
        // Feed every physical prefill ubatch through the DFlash feature hook.
        for (size_t start = 0; start + 1 < prefix.size();) {
            const auto end = std::min(prefix.size() - 1, start + size_t(p.n_ubatch));
            batch_guard batch(int(end - start));
            for (auto i = start; i < end; ++i) common_batch_add(batch.value, prefix[i], i, {0}, false);
            decode(verify.get(), batch.value);
            require(common_speculative_process(spec.get(), batch.value), "DFlash prefill feature processing failed");
            start = end;
        }
        llama_tokens past(prefix.begin(), prefix.end() - 1), draft;
        common_speculative_begin(spec.get(), 0, past);
        auto & dp = common_speculative_get_draft_params(spec.get(), 0);
        dp.drafting = true; dp.n_max = width; dp.n_past = past.size();
        dp.id_last = prefix.back(); dp.prompt = &past; dp.result = &draft;
        dp.temperature = 0; dp.seed = p.sampling.seed;
        common_speculative_draft(spec.get());
        require(!draft.empty() && draft.size() <= size_t(width), "DFlash produced invalid width");
        batch_guard batch(draft.size() + 1);
        common_batch_add(batch.value, prefix.back(), past.size(), {0}, true);
        for (size_t i = 0; i < draft.size(); ++i) common_batch_add(batch.value, draft[i], prefix.size() + i, {0}, true);
        decode(verify.get(), batch.value);
        // Serial reference: fresh context, same explicit tokens, one token per
        // decode. Never compare independently generated continuations.
        auto serial = context(model, p);
        for (size_t i = 0; i + 1 < prefix.size(); ++i) {
            batch_guard one(1); common_batch_add(one.value, prefix[i], i, {0}, true);
            decode(serial.get(), one.value);
        }
        json rows = json::array();
        auto row_prefix = prefix;
        size_t accepted = 0;
        int bonus = -1;
        for (size_t i = 0; i <= draft.size(); ++i) {
            batch_guard one(1);
            common_batch_add(one.value, row_prefix.back(), row_prefix.size() - 1, {0}, true);
            decode(serial.get(), one.value);
            const auto w = precision_compare(llama_get_logits_ith(verify.get(), i), llama_get_logits_ith(serial.get(), 0), vocab);
            rows.push_back({{"verify_prefix", row_prefix}, {"serial_prefix", row_prefix},
                            {"witness", {{"count", w.count}, {"verify_argmax", w.verify_argmax},
                                         {"max_abs", w.max_abs}, {"sum_squared", w.sum_squared}}}});
            if (i == accepted) {
                bonus = int(w.verify_argmax);
                if (i < draft.size() && draft[i] == bonus) ++accepted;
            }
            if (i < draft.size()) row_prefix.push_back(draft[i]);
        }
        trace["blocks"].push_back({{"block", b}, {"draft_tokens", draft}, {"accepted", accepted}, {"logits", rows}});
        prefix.insert(prefix.end(), draft.begin(), draft.begin() + accepted);
        prefix.push_back(bonus);
    }
    return trace;
}

int main(int argc, char ** argv) {
    if (argc != 5 || std::string(argv[1]) != "--request" || std::string(argv[3]) != "--output") return 2;
    // Acquire output custody before loading models; a duplicate invocation
    // must not repeat expensive model work before discovering the collision.
    FILE * out = std::fopen(argv[4], "wx");
    if (!out) return 4;
    json request, trace;
    try {
        std::ifstream in(argv[2]); require(bool(in), "missing request"); in >> request;
        common_init(); llama_backend_init();
        trace = produce(request);
    } catch (const std::exception & e) {
        trace = {{"request", request}, {"status", "failed"}, {"error", e.what()}};
    }
    const auto bytes = trace.dump();
    if (bytes.size() > 16 * 1024 * 1024) { std::fclose(out); return 3; }
    const bool written = std::fwrite(bytes.data(), 1, bytes.size(), out) == bytes.size();
    const int closed = std::fclose(out);
    return written && closed == 0 ? 0 : 5;
}
