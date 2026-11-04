#pragma once
// Prospective arithmetic core only. No GGML types, I/O or cache access.
#include <cstdint>
#include <cstddef>
#include <limits>
#include <map>
#include <utility>
#include <vector>

namespace kpf60 {
struct read_range { uint64_t begin, end; };
struct key {
    uint32_t layer, stream;
    bool value;
    bool operator<(const key & other) const {
        if (layer != other.layer) return layer < other.layer;
        if (stream != other.stream) return stream < other.stream;
        return value < other.value;
    }
};
struct totals { uint64_t k = 0, v = 0, metadata = 0, serialized = 0; };
struct expected_tensor { key id; std::vector<read_range> cells; };

// FAIL-CLOSED: after any refusal finish() never returns numeric totals.
// Range offsets are recomputed from cell geometry before comparing with the
// actual I/O event; callers must supply the true tensor capacity and row size.
class checked_counter {
    struct row {
        uint64_t row_bytes, capacity;
        std::vector<read_range> cells;
    };
    bool valid_ = true;
    uint64_t metadata_ = 0, k_ = 0, v_ = 0;
    std::map<key, row> rows_;
    static bool add(uint64_t a, uint64_t b, uint64_t & out) {
        if (b > std::numeric_limits<uint64_t>::max() - a) return false;
        out = a + b; return true;
    }
    static bool mul(uint64_t a, uint64_t b, uint64_t & out) {
        if (a && b > std::numeric_limits<uint64_t>::max() / a) return false;
        out = a * b; return true;
    }
public:
    bool metadata(uint64_t n) {
        uint64_t next;
        if (!valid_ || !add(metadata_, n, next)) return valid_ = false;
        metadata_ = next; return true;
    }
    bool tensor(uint32_t layer, bool value, uint32_t stream,
                bool f16, bool row_major, uint64_t row_bytes,
                uint64_t capacity, uint64_t begin, uint64_t end,
                uint64_t observed_offset, uint64_t observed_length) {
        uint64_t offset, length, limit, next;
        if (!valid_ || !f16 || !row_major || !row_bytes || (row_bytes % 2) ||
            begin >= end || !mul(begin, row_bytes, offset) ||
            !mul(end - begin, row_bytes, length) || !add(offset, length, limit) ||
            limit > capacity || offset != observed_offset || length != observed_length)
            return valid_ = false;
        const key id{layer, stream, value};
        auto it = rows_.find(id);
        if (it == rows_.end()) it = rows_.emplace(id, row{row_bytes, capacity, {}}).first;
        row & r = it->second;
        if (r.row_bytes != row_bytes || r.capacity != capacity ||
            (!r.cells.empty() && begin < r.cells.back().end)) return valid_ = false;
        uint64_t & subtotal = value ? v_ : k_;
        if (!add(subtotal, length, next)) return valid_ = false;
        subtotal = next; r.cells.push_back({begin, end}); return true;
    }
    // Expected tensors and selected ranges must come from independently validated
    // cache geometry and selection; this class cannot discover missing layers.
    bool finish(const std::vector<expected_tensor> & expected, totals & out) const {
        if (!valid_ || !k_ || expected.empty() || expected.size() != rows_.size()) return false;
        std::map<key, bool> seen;
        for (const auto & x : expected) {
            if (!seen.emplace(x.id, true).second) return false;
            const auto found = rows_.find(x.id);
            if (found == rows_.end() || x.cells.empty() || x.cells.size() != found->second.cells.size()) return false;
            for (std::size_t i = 0; i < x.cells.size(); ++i)
                if (x.cells[i].begin != found->second.cells[i].begin || x.cells[i].end != found->second.cells[i].end) return false;
        }
        uint64_t payload, total;
        if (!add(k_, v_, payload) || !add(payload, metadata_, total)) return false;
        out = {k_, v_, metadata_, total}; return true;
    }
};
} // namespace kpf60
