#pragma once

// Experimental, explicit AM carrier primitives for c9f2e34ce's ggml API.
// No global state, environment switches, cache movement or implicit activation.
#include "ggml.h"
#include "ggml-backend.h"

#include <cmath>
#include <cstring>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace am_carrier {

inline void require(bool ok, const char * why) {
    if (!ok) throw std::invalid_argument(why);
}

struct layer_fit {
    int layer = -1;
    int kv_heads = 0;
    int value_width = 0;
    std::vector<int64_t> positions; // common, sorted ORIGINAL positions
    std::vector<float> beta;       // [kv_head][selected position]
    std::vector<float> values;     // [kv_head][selected position][value width]

    void validate() const {
        require(layer >= 0 && kv_heads > 0 && kv_heads <= 256 &&
                value_width > 0 && value_width <= 512, "invalid layer/head/value dimensions");
        require(!positions.empty() && positions.size() <= 36864, "invalid retained position count");
        int64_t previous = -1;
        for (auto p : positions) {
            require(p >= 0 && p > previous, "retained positions must be sorted and unique");
            previous = p;
        }
        require(beta.size() == size_t(kv_heads)*positions.size() &&
                values.size() == beta.size()*size_t(value_width), "incomplete layer carrier");
        for (float x : beta) require(std::isfinite(x) && std::abs(x) <= 60000.f,
                                    "beta must be finite and representable in the F16 mask");
        for (float x : values) require(std::isfinite(x), "C2 must be finite");
    }
};

// The caller resolves ORIGINAL positions to CURRENT physical cache rows, while
// synchronized. This binding expires on cache mutation/defrag/state restoration.
// No positional inference from a tensor index is safe in a sparse native cache.
struct row_binding {
    std::vector<int64_t> positions;
    std::vector<int64_t> rows;

    void validate(const layer_fit & fit, int64_t capacity) const {
        fit.validate();
        require(positions == fit.positions && rows.size() == positions.size(),
                "physical row binding differs from common retained positions");
        std::set<int64_t> seen;
        for (auto row : rows) {
            require(row >= 0 && row < capacity && seen.insert(row).second,
                    "physical rows must be unique and within the current cache view");
        }
    }
};

inline void validate_layers(const std::vector<layer_fit> & layers) {
    require(!layers.empty(), "empty carrier bundle");
    std::set<int> seen;
    for (const auto & layer : layers) {
        layer.validate();
        require(seen.insert(layer.layer).second, "duplicate carrier layer");
        require(layer.positions == layers.front().positions,
                "all layers must retain the same original positions");
    }
}

struct graph_mask {
    ggml_tensor * mask = nullptr;
    ggml_tensor * input = nullptr;
    std::vector<float> data;

    // Call after graph allocation, before every evaluation (including reuse).
    void upload() const {
        if (!input) return;
        require(input->buffer != nullptr, "beta graph input has not been allocated");
        require(ggml_nbytes(input) == data.size()*sizeof(float), "beta graph shape changed");
        ggml_backend_tensor_set(input, data.data(), 0, data.size()*sizeof(float));
    }
};

// Called on the FA-coordinate mask [cache row, padded query, 1, 1]. GQA heads
// share a KV head in CONTIGUOUS groups, not head % n_kv_heads. Explicit expansion
// to all query heads avoids modulo-broadcast mapping in ggml FA.
inline graph_mask build_mask(ggml_context * ctx, ggml_tensor * base, int query_heads,
                             const layer_fit * fit, const row_binding * binding,
                             size_t max_mask_bytes = size_t(256) << 20) {
    if (!fit) return {base, nullptr, {}}; // exact default-off tensor/node identity
    require(ctx && base && binding, "missing mask context or row binding");
    fit->validate();
    require(base->ne[2] == 1 && base->ne[3] == 1 &&
            (base->type == GGML_TYPE_F16 || base->type == GGML_TYPE_F32),
            "carrier requires a single-stream base mask");
    require(query_heads > 0 && query_heads <= 256 && query_heads % fit->kv_heads == 0,
            "query heads must form integral GQA groups");
    require(base->ne[0] > 0 && base->ne[0] <= 36864 && base->ne[1] > 0 && base->ne[1] <= 512,
            "mask exceeds bounded cache/query dimensions");
    require(size_t(base->ne[0])*base->ne[1]*query_heads <= max_mask_bytes/sizeof(float),
            "expanded per-layer mask exceeds byte budget");
    binding->validate(*fit, base->ne[0]);
    graph_mask result;
    result.data.assign(size_t(base->ne[0])*query_heads, 0.f);
    for (int h = 0; h < query_heads; ++h) {
        const int kvh = h / (query_heads / fit->kv_heads);
        for (size_t i = 0; i < binding->rows.size(); ++i) {
            result.data[size_t(h)*base->ne[0] + binding->rows[i]] =
                fit->beta[size_t(kvh)*fit->positions.size() + i];
        }
    }
    result.input = ggml_new_tensor_4d(ctx, GGML_TYPE_F32, base->ne[0], 1, query_heads, 1);
    ggml_set_input(result.input);
    ggml_format_name(result.input, "am_beta_l%d", fit->layer);
    auto * full = base->type == GGML_TYPE_F32 ? base : ggml_cast(ctx, base, GGML_TYPE_F32);
    full = ggml_repeat_4d(ctx, full, base->ne[0], base->ne[1], query_heads, 1);
    result.mask = ggml_cast(ctx, ggml_add(ctx, full, result.input), GGML_TYPE_F16);
    ggml_format_name(result.mask, "am_mask_l%d", fit->layer);
    return result;
}

// Prepare EVERY row before the first backend write. Invalid inputs, unsupported
// layouts or quantization overflow therefore leave the cache bytes unchanged.
// Backend transfer failure is fatal in ggml, not a recoverable transaction.
inline void load_values(ggml_tensor * cache, int actual_layer,
                        const layer_fit & fit, const row_binding & binding) {
    fit.validate();
    require(cache && cache->buffer && actual_layer == fit.layer,
            "missing allocated cache or layer identity mismatch");
    require(cache->ne[0] == int64_t(fit.value_width)*fit.kv_heads &&
            cache->ne[2] == 1 && cache->ne[3] == 1 && ggml_is_contiguous(cache),
            "C2 requires untransposed single-stream [head*width,cache row] storage");
    require(cache->type == GGML_TYPE_F32 || cache->type == GGML_TYPE_F16 ||
            cache->type == GGML_TYPE_Q8_0, "unsupported C2 cache type");
    require(fit.value_width % ggml_blck_size(cache->type) == 0,
            "value head width must align with quantization blocks");
    binding.validate(fit, cache->ne[1]);
    const auto * traits = ggml_get_type_traits(cache->type);
    const size_t head_bytes = ggml_row_size(cache->type, fit.value_width);
    const size_t n = fit.positions.size();
    std::vector<uint8_t> packed(n*fit.kv_heads*head_bytes);
    std::vector<float> check(fit.value_width);
    for (size_t h = 0; h < size_t(fit.kv_heads); ++h) {
        for (size_t i = 0; i < n; ++i) {
            const float * src = fit.values.data() + (h*n + i)*fit.value_width;
            uint8_t * dst = packed.data() + (h*n + i)*head_bytes;
            if (cache->type == GGML_TYPE_F32) std::memcpy(dst, src, head_bytes);
            else {
                require(traits->from_float_ref && traits->to_float, "missing cache quantizer");
                traits->from_float_ref(src, dst, fit.value_width);
                traits->to_float(dst, check.data(), fit.value_width);
                for (float x : check) require(std::isfinite(x), "C2 overflows cache representation");
            }
        }
    }
    for (size_t h = 0; h < size_t(fit.kv_heads); ++h) {
        for (size_t i = 0; i < n; ++i) {
            const size_t offset = size_t(binding.rows[i])*cache->nb[1] + h*head_bytes;
            ggml_backend_tensor_set(cache, packed.data() + (h*n + i)*head_bytes, offset, head_bytes);
        }
    }
}

} // namespace am_carrier
