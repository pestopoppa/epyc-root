// Public-API default-off control. Compile identical bytes against baseline and
// patched builds. No AM internal headers, callback, carrier or cache mutation.
#include "llama.h"
#include "ggml-backend.h"
#include "nlohmann/json.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <set>
#include <stdexcept>
#include <vector>

using json = nlohmann::ordered_json;
static void require(bool ok, const char * message) {
    if (!ok) throw std::runtime_error(message);
}

static void decode(llama_context * ctx, const std::vector<llama_token> & tokens, int start) {
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
    require(rc == 0, "control decode refused");
}

int main(int argc, char ** argv) try {
    require(argc == 2, "usage: am-control prepared-config.json");
    std::ifstream input(argv[1]); json c; input >> c;
    require(c.at("mode") == "control", "mode must be control");
    const auto prefix = c.at("prefix_tokens").get<std::vector<llama_token>>();
    const auto warmup = c.at("warmup_tokens").get<std::vector<llama_token>>();
    const auto probe = c.at("probe_tokens").get<std::vector<llama_token>>();
    const int nctx = c.at("n_ctx"), threads = c.at("threads"), ngl = c.at("n_gpu_layers");
    require(prefix.size() >= 2 && prefix.size() <= 32768 && !warmup.empty() && warmup.size() <= 256
            && !probe.empty() && probe.size() <= 256, "bounded prepared token arrays required");
    require(nctx <= 36864 && nctx >= int(prefix.size() + warmup.size() + probe.size())
            && threads > 0 && ngl >= 0, "invalid context/threads/GPU layers");
    const std::filesystem::path out = c.at("out").get<std::string>();
    require(!std::filesystem::exists(out), "output already exists");
    // Trace format is deliberately fixed to little-endian IEEE float32.
    const uint32_t endian = 1;
    require(*reinterpret_cast<const uint8_t *>(&endian) == 1 && sizeof(float) == 4
            && std::numeric_limits<float>::is_iec559, "unsupported trace representation");
    ggml_backend_load_all();
    llama_backend_init();
    auto mp = llama_model_default_params(); mp.n_gpu_layers = ngl;
    std::unique_ptr<llama_model, decltype(&llama_model_free)> model(
        llama_model_load_from_file(c.at("model").get<std::string>().c_str(), mp), llama_model_free);
    require(bool(model), "model load failed");
    const int nvocab = llama_vocab_n_tokens(llama_model_get_vocab(model.get()));
    require(nvocab > 0 && uint64_t(nvocab) * probe.size() * 4 <= 512ull * 1024 * 1024,
            "logit trace exceeds 512 MiB bound");
    for (const auto * tokens : {&prefix, &warmup, &probe}) {
        for (auto t : *tokens) require(t >= 0 && t < nvocab, "invalid prepared token ID");
    }
    auto cp = llama_context_default_params();
    cp.n_ctx = nctx; cp.n_batch = 512; cp.n_ubatch = 512; cp.n_seq_max = 1;
    cp.n_threads = threads; cp.n_threads_batch = threads;
    cp.type_k = GGML_TYPE_F16; cp.type_v = GGML_TYPE_F16;
    cp.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_ENABLED;
    cp.cb_eval = nullptr; cp.cb_eval_user_data = nullptr;
    std::unique_ptr<llama_context, decltype(&llama_free)> ctx(llama_init_from_model(model.get(), cp), llama_free);
    require(bool(ctx), "context load failed");
    std::filesystem::create_directories(out);
    for (size_t i = 0; i < prefix.size(); i += 512) {
        const auto end = std::min(prefix.size(), i + 512);
        decode(ctx.get(), std::vector<llama_token>(prefix.begin() + i, prefix.begin() + end), i);
    }
    int pos = prefix.size();
    for (auto token : warmup) decode(ctx.get(), {token}, pos++);
    std::ofstream trace(out / "logits.f32", std::ios::binary);
    require(bool(trace), "trace open failed");
    std::vector<double> seconds;
    for (auto token : probe) {
        const auto start = std::chrono::steady_clock::now();
        decode(ctx.get(), {token}, pos++);
        const auto stop = std::chrono::steady_clock::now();
        // Time only synchronized native decode. Logit transfer/checks/file I/O
        // remain outside the interval, identically for both build variants.
        seconds.push_back(std::chrono::duration<double>(stop - start).count());
        const auto * logits = llama_get_logits_ith(ctx.get(), -1);
        require(logits != nullptr, "missing probe logits");
        for (int j = 0; j < nvocab; ++j) require(std::isfinite(logits[j]), "nonfinite probe logits");
        trace.write(reinterpret_cast<const char *>(logits), nvocab * sizeof(float));
        require(bool(trace), "trace write failed");
    }
    trace.close(); require(bool(trace), "trace close failed");
    // Residency evidence for library selection, not GPU residency. Bind these
    // actual mapped paths in the Python wrapper (dlopen bypasses executable ldd).
    std::ifstream maps("/proc/self/maps"); require(bool(maps), "process maps unavailable");
    std::set<std::string> libraries;
    for (std::string line; std::getline(maps, line);) {
        const auto p = line.find('/');
        if (p == std::string::npos) continue;
        const auto path = line.substr(p);
        const auto name = std::filesystem::path(path).filename().string();
        if (name.rfind("libllama", 0) == 0 || name.rfind("libggml", 0) == 0) libraries.insert(path);
    }
    json result = {{"schema", "epyc.am.default-off-control.v1"}, {"mode", "control"},
                   {"model_identity", c.at("model_identity")}, {"source_commit", c.at("source_commit")},
                   {"n_vocab", nvocab}, {"probe_steps", probe.size()}, {"decode_seconds", seconds},
                   {"mapped_libraries", libraries}, {"trace", "logits.f32"},
                   {"timing_scope", "synchronized decode only; excludes logit read/trace I/O"}};
    std::ofstream record(out / "RESULT.json"); record << result.dump(2) << '\n';
    require(bool(record), "result write failed");
    return 0;
} catch (const std::exception & e) {
    std::cerr << "AM control refused: " << e.what() << '\n'; return 1;
}
