// Experimental internal-API runner; link ONLY against the full patched kernel.
// No tokenization/download/hash of weights, no serving changes. Config contains
// prepared token IDs. Capture and reload are separate invocations/contexts.
#include "llama-context.h"
#include <native_runtime.h>
#include "native_capture.h"
#include "native_bundle.h"
#include "nlohmann/json.hpp"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <memory>

using json = nlohmann::ordered_json;
using am_carrier::require;

static void save_json(const std::filesystem::path & path, const json & value) {
    require(!std::filesystem::exists(path), "output already exists");
    std::ofstream out(path); out << value.dump(2) << '\n';
    require(bool(out), "JSON write failed");
}

static void decode(llama_context * ctx, const std::vector<llama_token> & tokens, int start) {
    require(!tokens.empty() && tokens.size() <= 512, "decode batch must contain 1..512 tokens");
    auto batch = llama_batch_init(tokens.size(), 0, 1);
    batch.n_tokens = tokens.size();
    for (size_t i = 0; i < tokens.size(); ++i) {
        batch.token[i] = tokens[i]; batch.pos[i] = start + i;
        batch.n_seq_id[i] = 1; batch.seq_id[i][0] = 0;
        batch.logits[i] = i + 1 == tokens.size();
    }
    const int rc = llama_decode(ctx, batch);
    llama_batch_free(batch);
    llama_synchronize(ctx);
    require(rc == 0, "native decode refused");
}

int main(int argc, char ** argv) try {
    require(argc == 2, "usage: am-driver prepared-config.json");
    std::ifstream config_file(argv[1]); json config; config_file >> config;
    const auto mode = config.at("mode").get<std::string>();
    require(mode == "capture" || mode == "reload", "mode must be capture or reload");
    const std::filesystem::path out = config.at("out").get<std::string>();
    require(!std::filesystem::exists(out), "output directory already exists");
    const auto prefix = config.at("prefix_tokens").get<std::vector<llama_token>>();
    require(prefix.size() >= 2 && prefix.size() <= 32768, "prefix must contain 2..32768 tokens");
    const int nctx = config.at("n_ctx");
    require(nctx > int(prefix.size()) && nctx <= 36864, "invalid bounded context size");
    auto mp = llama_model_default_params();
    mp.n_gpu_layers = config.at("n_gpu_layers");
    auto cp = llama_context_default_params();
    cp.n_ctx = nctx; cp.n_batch = 512; cp.n_ubatch = 512; cp.n_seq_max = 1;
    cp.n_threads = config.at("threads"); cp.n_threads_batch = cp.n_threads;
    require(cp.n_threads > 0, "invalid thread count");
    cp.type_k = GGML_TYPE_F16; cp.type_v = GGML_TYPE_F16;
    cp.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_ENABLED;
    am_capture::state capture;
    cp.cb_eval = am_capture::callback; cp.cb_eval_user_data = &capture;
    ggml_backend_load_all();
    std::unique_ptr<llama_model, decltype(&llama_model_free)> model(
        llama_model_load_from_file(config.at("model").get<std::string>().c_str(), mp), llama_model_free);
    require(bool(model), "model load failed");
    std::unique_ptr<llama_context, decltype(&llama_free)> ctx(llama_init_from_model(model.get(), cp), llama_free);
    require(bool(ctx), "context load failed");
    auto * kv = am_carrier::attention_cache(llama_get_memory(ctx.get()));
    require(!kv->am_has_rotation() && kv->type_k() == GGML_TYPE_F16 && kv->type_v() == GGML_TYPE_F16,
            "driver requires unrotated F16 KV");
    require(!llama_kv_am_beta_enabled(), "PORT-1 beta must be disabled");
    for (auto token : prefix) require(token >= 0 && token < llama_vocab_n_tokens(llama_model_get_vocab(model.get())),
                                      "invalid prepared prefix token ID");
    std::filesystem::create_directories(out);
    json result = {{"schema", "epyc.am.native-driver.v1"}, {"mode", mode},
                   {"prefix_tokens", prefix.size()}, {"scope", "engineering run; no automatic quality verdict"}};
    if (mode == "capture") {
        for (size_t i = 0; i < prefix.size(); i += 512) {
            const auto end = std::min(prefix.size(), i + 512);
            decode(ctx.get(), std::vector<llama_token>(prefix.begin() + i, prefix.begin() + end), i);
        }
        const auto * prefix_logits = llama_get_logits_ith(ctx.get(), -1);
        const int vocab_size = llama_vocab_n_tokens(llama_model_get_vocab(model.get()));
        require(prefix_logits != nullptr, "missing full-prefix logits");
        for (int i = 0; i < vocab_size; ++i) require(std::isfinite(prefix_logits[i]), "nonfinite prefix logits");
        result["prefix_greedy_token"] = std::max_element(prefix_logits, prefix_logits + vocab_size) - prefix_logits;
        const auto snapshot = out / "prefix.state";
        require(llama_state_seq_save_file(ctx.get(), snapshot.c_str(), 0, prefix.data(), prefix.size()) > 0,
                "prefix state save failed");
        const auto suffix = config.at("calibration_tokens").get<std::vector<llama_token>>();
        require(suffix.size() >= 2 && suffix.size() <= 512 && prefix.size() + suffix.size() <= size_t(nctx),
                "invalid calibration suffix length");
        for (auto token : suffix) require(token >= 0 && token < llama_vocab_n_tokens(llama_model_get_vocab(model.get())),
                                          "invalid prepared calibration token ID");
        auto ids = kv->get_layer_ids();
        capture.begin(out / "native", std::set<int>(ids.begin(), ids.end()));
        decode(ctx.get(), suffix, prefix.size());
        capture.finish();
        std::vector<int> rows, queries, fit, evaluation;
        const auto & cells = kv->get_cells(0);
        for (uint32_t r = 0; r < cells.size(); ++r) {
            rows.push_back(cells.is_empty(r) ? -1 : cells.pos_get(r));
        }
        // Native FA may crop physical cache padding; bind exactly its K axis.
        std::ifstream layer_file(out / "native" / ("layer-" + std::to_string(ids.front()) + ".json"));
        json layer; layer_file >> layer;
        const size_t captured_rows = layer.at("tensors").at("K").at("ne").at(1);
        require(captured_rows <= rows.size(), "captured cache exceeds native cell map");
        rows.resize(captured_rows);
        for (size_t i = 0; i < suffix.size(); ++i) {
            const int pos = prefix.size() + i; queries.push_back(pos);
            (i % 2 == 0 ? fit : evaluation).push_back(pos);
        }
        std::sort(ids.begin(), ids.end());
        json p = {{"schema", "epyc.am.calibration-provenance.v1"}, {"sequence", 0},
                  {"source_commit", config.at("source_commit")}, {"model_identity", config.at("model_identity")},
                  {"capture_id", config.at("capture_id")}, {"prefix_tokens", prefix.size()},
                  {"cache_row_positions", rows}, {"query_positions", queries}, {"fit_positions", fit},
                  {"eval_positions", evaluation}, {"layers", ids}};
        // Python seal_provenance binds the completion marker and saved prefix
        // bytes. This raw record alone is NOT accepted by the converter.
        save_json(out / "PROVENANCE.raw.json", p);
        result["captured_query_tokens"] = suffix.size();
    } else {
        const auto state = config.at("prefix_state").get<std::string>();
        std::vector<llama_token> restored(prefix.size()); size_t restored_count = 0;
        require(llama_state_seq_load_file(ctx.get(), state.c_str(), 0, restored.data(), restored.size(), &restored_count) > 0
                && restored_count == prefix.size() && restored == prefix, "prefix state/token restore mismatch");
        auto fits = am_carrier::read_bundle(config.at("carrier").get<std::string>());
        const auto & positions = fits.front().positions;
        require(positions.front() == 0 && positions.back() == int64_t(prefix.size() - 1),
                "carrier must preserve prefix endpoints");
        // Prune only attention storage. The restored recurrent prefix state is
        // kept whole. Never remove a hybrid suffix as a proxy for restoration.
        size_t next = 0;
        for (int pos = 0; pos < int(prefix.size());) {
            if (next < positions.size() && positions[next] == pos) { ++next; ++pos; continue; }
            const int end = next < positions.size() ? positions[next] : prefix.size();
            require(kv->seq_rm(0, pos, end), "native attention prune refused"); pos = end;
        }
        ctx->am_install(std::move(fits), 0);
        const int steps = config.at("decode_steps");
        require(steps > 0 && steps <= 32768 && prefix.size() + steps <= size_t(nctx),
                "decode steps exceed bounded append capacity");
        // Caller prepares the first token from FULL-prefix logits; subsequent
        // tokens are greedy. EOS does not truncate this fixed stability probe.
        llama_token token = config.at("first_decode_token");
        const int nvocab = llama_vocab_n_tokens(llama_model_get_vocab(model.get()));
        require(token >= 0 && token < nvocab, "invalid first decode token");
        for (int i = 0; i < steps; ++i) {
            decode(ctx.get(), {token}, prefix.size() + i);
            auto * logits = llama_get_logits_ith(ctx.get(), -1);
            require(logits != nullptr, "missing append logits");
            for (int j = 0; j < nvocab; ++j) require(std::isfinite(logits[j]), "nonfinite append logits");
            token = std::max_element(logits, logits + nvocab) - logits;
        }
        result["decoded_tokens"] = steps;
    }
    save_json(out / "RESULT.json", result);
    std::cout << result.dump() << '\n';
    return 0;
} catch (const std::exception & e) {
    std::cerr << "AM driver refused: " << e.what() << '\n'; return 1;
}
