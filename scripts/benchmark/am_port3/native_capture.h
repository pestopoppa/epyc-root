#pragma once
// Diagnostic callback for the pinned c9f2e34ce ggml API. No graph mutation.
#include "ggml.h"
#include "ggml-backend.h"

#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace am_capture {

// Canonical dump order is [ne3, ne2, ne1, ne0], native little-endian float32.
// Read each row independently: Q is permuted and cached K/V may be quantized.
inline void dump_tensor(const ggml_tensor * t, const std::filesystem::path & path) {
    if (!t || t->nb[0] != ggml_type_size(t->type) ||
        t->ne[0] % ggml_blck_size(t->type) != 0) {
        throw std::runtime_error("unsupported strided dimension zero");
    }
    const auto * traits = ggml_get_type_traits(t->type);
    if (t->type != GGML_TYPE_F32 && !traits->to_float) {
        throw std::runtime_error("tensor type has no dequantizer");
    }
    const auto row_bytes = ggml_row_size(t->type, t->ne[0]);
    std::vector<uint8_t> raw(row_bytes);
    std::vector<float> row(t->ne[0]);
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("cannot create capture tensor");
    for (int64_t i3 = 0; i3 < t->ne[3]; ++i3) {
        for (int64_t i2 = 0; i2 < t->ne[2]; ++i2) {
            for (int64_t i1 = 0; i1 < t->ne[1]; ++i1) {
                const size_t offset = i3*t->nb[3] + i2*t->nb[2] + i1*t->nb[1];
                ggml_backend_tensor_get(t, raw.data(), offset, row_bytes);
                if (t->type == GGML_TYPE_F32) {
                    std::memcpy(row.data(), raw.data(), row_bytes);
                } else {
                    traits->to_float(raw.data(), row.data(), t->ne[0]);
                }
                out.write(reinterpret_cast<const char *>(row.data()), row.size()*sizeof(float));
            }
        }
    }
    out.close();
    if (!out) throw std::runtime_error("capture tensor write failed");
}

inline int query_layer(const ggml_tensor * q) {
    // Qwen35 names the post-RoPE tensor Qcur-<layer>. Walk only unary
    // reshape/permute/view/cast ancestors, never back into a projection.
    for (int depth = 0; q && depth < 12; ++depth) {
        const std::string name = ggml_get_name(q);
        const std::string prefix = "Qcur-";
        if (name.rfind(prefix, 0) == 0) {
            const auto suffix = name.substr(prefix.size());
            if (!suffix.empty() && suffix.find_first_not_of("0123456789") == std::string::npos) {
                return std::stoi(suffix);
            }
        }
        if (q->op != GGML_OP_VIEW && q->op != GGML_OP_RESHAPE &&
            q->op != GGML_OP_PERMUTE && q->op != GGML_OP_TRANSPOSE &&
            q->op != GGML_OP_CPY && q->op != GGML_OP_CONT) break;
        q = q->src[0];
    }
    return -1;
}

struct state {
    bool enabled = false;
    std::string error;
    std::filesystem::path directory;
    std::set<int> expected, seen;
    size_t bytes = 0;
    size_t max_bytes = size_t(4) << 30;
    int64_t max_kv = 36864, max_queries = 512, max_width = 512;

    // The driver arms for exactly ONE llama_decode call/ubatch. It must supply
    // the model's actual global-attention layer IDs and persist identity first.
    void begin(const std::filesystem::path & path, const std::set<int> & layers) {
        const uint16_t endian = 1;
        if (*reinterpret_cast<const uint8_t *>(&endian) != 1 || sizeof(float) != 4) {
            throw std::runtime_error("capture requires little-endian float32 host");
        }
        if (enabled || layers.empty() || *layers.begin() < 0) {
            throw std::runtime_error("invalid capture activation");
        }
        if (!std::filesystem::create_directory(path)) {
            throw std::runtime_error("capture directory already exists");
        }
        directory = path; expected = layers; seen.clear(); bytes = 0; error.clear(); enabled = true;
    }

    size_t budget(const ggml_tensor * t) const {
        if (!t) return 0;
        size_t n = sizeof(float);
        for (auto dim : t->ne) {
            if (dim <= 0 || size_t(dim) > max_bytes/n) {
                throw std::runtime_error("capture tensor exceeds byte budget");
            }
            n *= size_t(dim);
        }
        return n;
    }

    void capture(ggml_tensor * t, int layer) {
        if (seen.count(layer)) throw std::runtime_error("duplicate layer: multiple ubatches in capture window");
        const auto * q = t->src[0];
        const auto * k = t->src[1];
        const auto * v = t->src[2];
        const auto * mask = t->src[3];
        float params[3];
        std::memcpy(params, t->op_params, sizeof(params));
        if (!q || !k || !v || q->ne[3] != 1 || k->ne[3] != 1 || v->ne[3] != 1 ||
            q->ne[0] > max_width || v->ne[0] > max_width ||
            k->ne[1] > max_kv || q->ne[1] > max_queries ||
            k->ne[0] != q->ne[0] || k->ne[1] != v->ne[1] ||
            k->ne[2] != v->ne[2] || k->ne[2] <= 0 || q->ne[2] % k->ne[2] != 0 ||
            (mask && (mask->ne[0] != k->ne[1] || mask->ne[1] < q->ne[1] ||
                      mask->ne[2] != 1 || mask->ne[3] != 1)) ||
            !std::isfinite(params[0]) || params[0] <= 0 || params[1] != 0 || params[2] != 0 || t->src[4]) {
            throw std::runtime_error("unsupported attention geometry, bias, softcap, sinks or capture limits");
        }
        size_t need = 0;
        for (const auto * x : {q, k, v, mask, static_cast<const ggml_tensor *>(t)}) {
            const auto n = budget(x);
            if (n > max_bytes - need) throw std::runtime_error("capture exceeds byte budget");
            need += n;
        }
        if (need > max_bytes - bytes) throw std::runtime_error("capture exceeds total byte budget");
        const auto stem = std::string("layer-") + std::to_string(layer);
        const auto partial = directory / (stem + ".partial.json");
        std::ofstream manifest(partial);
        if (!manifest) throw std::runtime_error("cannot create capture manifest");
        manifest.precision(9);
        manifest << "{\"schema\":\"epyc.am.native-layer.v1\",\"layer\":" << layer
                 << ",\"attention_scale\":" << params[0] << ",\"tensors\":{";
        const ggml_tensor * tensors[] = {q, k, v, mask, t};
        const char * names[] = {"Q", "K", "V", "mask", "output"};
        bool first = true;
        for (size_t i = 0; i < 5; ++i) {
            const auto * x = tensors[i];
            if (!x) continue;
            if (!first) manifest << ',';
            first = false;
            const auto file = stem + "-" + names[i] + ".f32";
            dump_tensor(x, directory / file);
            manifest << '"' << names[i] << "\":{\"file\":\"" << file << "\",\"ne\":[";
            for (int d = 0; d < 4; ++d) manifest << (d ? "," : "") << x->ne[d];
            manifest << "],\"original_type\":\"" << ggml_type_name(x->type) << "\"}";
        }
        manifest << "}}\n";
        manifest.close();
        if (!manifest) throw std::runtime_error("capture manifest write failed");
        std::filesystem::rename(partial, directory / (stem + ".json"));
        bytes += need; seen.insert(layer);
    }

    void finish() {
        if (!enabled) throw std::runtime_error("capture is not active");
        enabled = false;
        if (!error.empty()) throw std::runtime_error(error);
        if (seen != expected) throw std::runtime_error("capture is missing expected global-attention layers");
        std::ofstream out(directory / "COMPLETE.partial.json");
        out << "{\"schema\":\"epyc.am.native-capture.v1\",\"bytes\":" << bytes << ",\"layers\":[";
        bool first = true;
        for (int layer : seen) { out << (first ? "" : ",") << layer; first = false; }
        out << "]}\n";
        out.close();
        if (!out) throw std::runtime_error("capture completion write failed");
        std::filesystem::rename(directory / "COMPLETE.partial.json", directory / "COMPLETE.json");
    }
};

inline bool callback(ggml_tensor * t, bool ask, void * userdata) noexcept {
    auto & s = *static_cast<state *>(userdata);
    if (!s.enabled || !s.error.empty()) return !ask;
    try {
        if (t->op != GGML_OP_FLASH_ATTN_EXT) return !ask;
        const int layer = query_layer(t->src[0]);
        if (!s.expected.count(layer)) {
            throw std::runtime_error("unidentified or unexpected flash-attention layer");
        }
        if (ask) return true;
        s.capture(t, layer);
    } catch (const std::exception & e) {
        s.error = e.what();
        // Do not interrupt native evaluation: the driver MUST call finish(),
        // which refuses incomplete/error captures even if llama_decode returns 0.
    } catch (...) {
        s.error = "unknown capture exception";
    }
    return !ask;
}

} // namespace am_capture
