#pragma once

// Internal C++ integration for the pinned experimental kernel; no public ABI.
#include "native_carrier.h"
#include "llama-kv-cache.h"
#include "llama-memory-hybrid.h"
#include <algorithm>
#include <functional>

namespace am_carrier {

inline row_binding resolve_positions(const llama_kv_cells & cells, llama_seq_id seq,
                                     const std::vector<int64_t> & positions, int64_t capacity) {
    require(!positions.empty() && positions.front() >= 0 &&
            std::is_sorted(positions.begin(), positions.end()) &&
            std::adjacent_find(positions.begin(), positions.end()) == positions.end(),
            "invalid common retained positions");
    require(seq >= 0 && seq < LLAMA_MAX_SEQ, "invalid AM sequence");
    require(!cells.get_has_shift(), "AM cache has pending position shifts");
    row_binding out{positions, std::vector<int64_t>(positions.size(), -1)};
    for (uint32_t row = 0; row < cells.size(); ++row) {
        if (cells.is_empty(row)) continue;
        require(cells.seq_count(row) == 1 && cells.seq_has(row, seq),
                "AM requires an exclusive single-sequence cache");
        const auto p = cells.pos_get(row);
        const auto it = std::lower_bound(positions.begin(), positions.end(), p);
        if (it == positions.end() || *it != p) continue;
        const auto i = size_t(it - positions.begin());
        require(out.rows[i] == -1, "duplicate native retained position");
        require(cells.ext_get(row).beta == 0.f, "PORT-1 scalar beta must be zero");
        out.rows[i] = row;
    }
    for (auto row : out.rows) require(row >= 0 && row < capacity, "missing or cropped retained native row");
    return out;
}

inline llama_kv_cache * attention_cache(llama_memory_t memory) {
    if (auto * kv = dynamic_cast<llama_kv_cache *>(memory)) return kv;
    if (auto * hybrid = dynamic_cast<llama_memory_hybrid *>(memory)) return hybrid->get_mem_attn();
    throw std::invalid_argument("AM requires a plain or hybrid attention cache");
}

struct context_state {
    llama_kv_cache * cache;
    llama_seq_id seq;
    uint64_t epoch;
    llama_pos frozen_end;
    std::vector<layer_fit> layers;

    context_state(llama_kv_cache * cache, llama_seq_id seq, std::vector<layer_fit> fits)
        : cache(cache), seq(seq), epoch(0), frozen_end(-1), layers(std::move(fits)) {
        require(cache && seq == 0, "AM currently requires sequence zero");
        require(cache->get_n_stream() == 1 && !cache->get_v_trans() && !cache->get_shares_cells(),
                "AM requires untransposed exclusive single-stream storage");
        require(!cache->am_has_rotation(), "AM rotated cache coordinates are unsupported");
        require(!llama_kv_am_beta_enabled(), "disable LLAMA_KV_AM_BETA for head-specific beta");
        validate_layers(layers);
        auto ids = cache->get_layer_ids();
        std::sort(ids.begin(), ids.end());
        std::vector<uint32_t> supplied;
        for (const auto & fit : layers) supplied.push_back(fit.layer);
        std::sort(supplied.begin(), supplied.end());
        require(ids == supplied, "AM must supply every native attention layer exactly once");
        epoch = cache->am_epoch();
        const auto & cells = cache->get_cells(seq);
        require(cells.get_used() == layers.front().positions.size(), "prune unselected original rows before AM install");
        frozen_end = cells.seq_pos_max(seq);
        std::vector<value_plan> plans;
        for (const auto & fit : layers) {
            auto binding = resolve_positions(cells, seq, fit.positions, cache->get_size());
            plans.push_back(prepare_values(cache->get_v_layer_raw(fit.layer), fit.layer, fit, binding));
        }
        // Across ALL layers, finish validation/quantization before any write.
        for (const auto & plan : plans) plan.write();
    }

    const layer_fit & layer(int id) const {
        for (const auto & fit : layers) if (fit.layer == id) return fit;
        throw std::invalid_argument("AM graph requested an unfitted layer");
    }

    row_binding bind(int id, int64_t capacity) const {
        require(cache->am_epoch() == epoch, "AM invalidated by cache mutation; reinstall from original capture");
        require(!llama_kv_am_beta_enabled(), "PORT-1 beta activated after AM install");
        return resolve_positions(cache->get_cells(seq), seq, layer(id).positions, capacity);
    }

    void validate_batch(const llama_ubatch & batch) const {
        require(batch.pos && batch.n_seq_id && batch.seq_id && batch.seq_id_unq &&
                batch.n_seqs_unq == 1 && batch.seq_id_unq[0] == seq,
                "AM decode requires its single fitted sequence");
        for (uint32_t i = 0; i < batch.n_tokens; ++i) {
            require(batch.n_seq_id[i] == 1 && batch.seq_id[i][0] == seq && batch.pos[i] > frozen_end,
                    "AM requires append-only queries beyond the frozen original cache");
        }
    }
};

// One input per layer. Re-resolve physical rows and upload on EVERY evaluation,
// including graph reuse. A cached graph must never retain a stale beta snapshot.
class graph_input : public llm_graph_input_i {
public:
    graph_mask mask;
    const layer_fit fit;
    int query_heads;
    std::function<row_binding(int64_t)> resolve;
    std::function<void(const llama_ubatch &)> check_batch;

    graph_input(ggml_context * ctx, ggml_tensor * base, int heads, const layer_fit & fit,
                std::function<row_binding(int64_t)> resolve,
                std::function<void(const llama_ubatch &)> check_batch)
        : fit(fit), query_heads(heads), resolve(std::move(resolve)), check_batch(std::move(check_batch)) {
        auto binding = this->resolve(base->ne[0]);
        mask = build_mask(ctx, base, heads, &this->fit, &binding);
    }

    void set_input(const llama_ubatch * batch) override {
        require(batch, "missing AM ubatch");
        check_batch(*batch);
        auto binding = resolve(mask.input->ne[0]);
        std::fill(mask.data.begin(), mask.data.end(), 0.f);
        for (int h = 0; h < query_heads; ++h) {
            const int kvh = h / (query_heads / fit.kv_heads);
            for (size_t i = 0; i < binding.rows.size(); ++i) {
                mask.data[size_t(h)*mask.input->ne[0] + binding.rows[i]] =
                    fit.beta[size_t(kvh)*fit.positions.size() + i];
            }
        }
        mask.upload();
    }

    bool can_reuse(const llm_graph_params &) override { return true; }
};

} // namespace am_carrier
