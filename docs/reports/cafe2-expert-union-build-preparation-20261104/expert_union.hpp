#pragma once
// UNBUILT proposal. Observe target-only qwen35moe routed expert IDs.
// A callback-bearing context is NEVER the timing arm: the scheduler changes
// evaluation boundaries and synchronizes for observed nodes.
#include "llama.h"
#include "speculative.h"
#include "ggml.h"
#include "ggml-backend.h"
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <set>
#include <string>
#include <vector>

inline bool cafe2_tokens(const llama_tokens & tokens) {
    if (std::fputc('[', stdout) == EOF) return false;
    for (size_t i = 0; i < tokens.size(); ++i)
        if (std::fprintf(stdout, "%s%d", i ? "," : "", (int) tokens[i]) < 0) return false;
    return std::fputc(']', stdout) != EOF;
}
inline bool cafe2_plan(bool census, const llama_tokens & prompt,
                       llama_token boundary, const llama_tokens & draft) {
    if (std::fprintf(stdout, "{\"schema\":\"cafe2.verify.plan.v1\",\"arm\":\"%s\",\"boundary\":%d,\"prompt_tokens\":",
                     census ? "expert_census" : "timing_no_callback", (int) boundary) < 0 ||
        !cafe2_tokens(prompt) || std::fprintf(stdout, ",\"draft_tokens\":") < 0 ||
        !cafe2_tokens(draft) || std::fprintf(stdout, "}\n") < 0) return false;
    return std::fflush(stdout) == 0 && !std::ferror(stdout);
}
struct Cafe2ExpertUnion {
    bool active = false, failed = false;
    int layers = 0, experts = 0, used = 0;
    int rep = -1, cell = -1, rows = 0, start = -1;
    std::vector<unsigned> observed;
    uint64_t layer_union_sum = 0;

    static bool meta(const llama_model * model, const char * key, const char * value) {
        char b[128] = {};
        int n = llama_model_meta_val_str(model, key, b, sizeof b);
        return n > 0 && n < (int) sizeof b && std::strcmp(b, value) == 0;
    }
    bool configure(const llama_model * model) {
        // Exact intended E=256,K=8,40-trunk-layer carrier. All trunk FFNs in
        // pinned qwen35moe graph use build_moe_ffn; exclude MTP-only layers.
        if (!model || !meta(model, "general.architecture", "qwen35moe") ||
            !meta(model, "qwen35moe.expert_count", "256") ||
            !meta(model, "qwen35moe.expert_used_count", "8") ||
            llama_model_n_layer(model) != 40) return false;
        layers = 40; experts = 256; used = 8;
        return true;
    }
    bool begin(int r, int c, int width, int position, const llama_tokens & tokens) {
        if (active || !layers || width < 1 || width > 9 ||
            tokens.size() != (size_t) width || position < 0) return false;
        rep = r; cell = c; rows = width; start = position;
        failed = false; layer_union_sum = 0; observed.assign(layers, 0); active = true;
        bool ok = std::fprintf(stdout, "{\"schema\":\"cafe2.expert.window.begin.v1\",\"window\":%d,\"rep\":%d,\"cell\":%d,\"rows\":%d,\"position_start\":%d,\"expected_layers\":%d,\"experts\":%d,\"topk\":%d,\"target_tokens\":",
             rep * 11 + cell, rep, cell, rows, start, layers, experts, used) >= 0 &&
             cafe2_tokens(tokens) && std::fprintf(stdout, "}\n") >= 0 &&
             std::fflush(stdout) == 0 && !std::ferror(stdout);
        if (!ok) failed = true;
        return ok;
    }
    static bool callback(ggml_tensor * t, bool ask, void * data) noexcept {
        auto * self = static_cast<Cafe2ExpertUnion *>(data);
        if (!self || !self->active) return ask ? false : true;
        try { return self->observe(t, ask); }
        catch (...) { self->failed = true; return false; }
    }
    bool observe(ggml_tensor * t, bool ask) {
        const char * prefix = "ffn_moe_topk-";
        if (!t || std::strncmp(t->name, prefix, std::strlen(prefix)) != 0)
            return ask ? false : true;
        char * end = nullptr; errno = 0;
        const char * suffix = t->name + std::strlen(prefix);
        long layer = std::strtol(suffix, &end, 10);
        bool valid = suffix[0] >= '0' && suffix[0] <= '9' && !errno && end && !*end &&
             layer >= 0 && layer < layers && t->type == GGML_TYPE_I32 &&
             t->ne[0] == used && t->ne[1] == rows && t->ne[2] == 1 && t->ne[3] == 1 &&
             t->nb[0] == sizeof(int32_t) && t->nb[1] >= used * sizeof(int32_t) &&
             t->nb[1] <= experts * sizeof(int32_t);
        if (!valid) { failed = true; return false; }
        if (ask) return true;
        // argsort_top_k is a view of the full E-wide argsort. nb[1] is
        // generally E*4, not K*4: read each token's K IDs at its actual stride.
        if (failed || observed[layer]++ || !t->buffer || !t->data) {
            failed = true; return false;
        }
        std::vector<int32_t> ids((size_t) rows * used);
        std::set<int32_t> united;
        for (int row = 0; row < rows; ++row) {
            size_t offset = (size_t) row * t->nb[1], bytes = (size_t) used * sizeof(int32_t);
            if (offset > ggml_nbytes(t) || bytes > ggml_nbytes(t) - offset) {
                failed = true; return false;
            }
            ggml_backend_tensor_get(t, ids.data() + row * used, offset, bytes);
            std::set<int32_t> token_ids;
            for (int k = 0; k < used; ++k) {
                int32_t id = ids[(size_t) row * used + k];
                if (id < 0 || id >= experts || !token_ids.insert(id).second) {
                    failed = true; return false;
                }
                united.insert(id);
            }
        }
        bool ok = std::fprintf(stdout, "{\"schema\":\"cafe2.expert.layer.v1\",\"window\":%d,\"rep\":%d,\"cell\":%d,\"layer\":%ld,\"tensor\":\"ffn_moe_topk-%ld\",\"rows\":%d,\"position_start\":%d,\"shape\":[%lld,%lld,%lld,%lld],\"strides_bytes\":[%zu,%zu,%zu,%zu],\"experts\":%d,\"topk\":%d,\"expert_ids_by_token\":[",
            rep * 11 + cell, rep, cell, layer, layer, rows, start,
            (long long)t->ne[0], (long long)t->ne[1], (long long)t->ne[2], (long long)t->ne[3],
            t->nb[0],t->nb[1],t->nb[2],t->nb[3],experts,used) >= 0;
        for (int row = 0; row < rows && ok; ++row) {
            ok = std::fprintf(stdout, "%s[", row ? "," : "") >= 0;
            for (int k = 0; k < used && ok; ++k)
                ok = std::fprintf(stdout, "%s%d", k ? "," : "", ids[(size_t)row * used + k]) >= 0;
            ok = ok && std::fprintf(stdout, "]") >= 0;
        }
        ok = ok && std::fprintf(stdout, "],\"union_count\":%zu,\"union_ids\":[", united.size()) >= 0;
        bool first = true;
        for (int id : united) {
            ok = ok && std::fprintf(stdout, "%s%d", first ? "" : ",", id) >= 0; first = false;
        }
        ok = ok && std::fprintf(stdout, "]}\n") >= 0 && std::fflush(stdout) == 0 && !std::ferror(stdout);
        if (!ok) { failed = true; return false; }
        layer_union_sum += united.size();
        return true;
    }
    bool finish(int decode_rc) {
        active = false;
        unsigned seen = 0;
        for (unsigned count : observed) { if (count == 1) ++seen; else failed = true; }
        bool complete = decode_rc == 0 && !failed && seen == (unsigned) layers;
        bool ok = std::fprintf(stdout, "{\"schema\":\"cafe2.expert.window.end.v1\",\"window\":%d,\"rep\":%d,\"cell\":%d,\"rows\":%d,\"position_start\":%d,\"decode_rc\":%d,\"expected_layers\":%d,\"observed_layers\":%u,\"coverage_complete\":%s,\"state_equal\":true,\"layer_union_sum\":",
             rep * 11 + cell, rep, cell, rows, start, decode_rc, layers, seen,
             complete ? "true" : "false") >= 0;
        if (complete) ok = ok && std::fprintf(stdout, "%llu", (unsigned long long) layer_union_sum) >= 0;
        else ok = ok && std::fprintf(stdout, "null") >= 0;
        ok = ok && std::fprintf(stdout, ",\"status\":\"%s\"}\n", complete ? "COMPLETE" : "UNKNOWN") >= 0 &&
             std::fflush(stdout) == 0 && !std::ferror(stdout);
        return complete && ok;
    }
};
