#pragma once
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace aux_capture {
struct cell { int64_t position; int32_t sequence; }; // position -1 marks empty/padding
struct mapping { std::vector<int64_t> key_cells, query_rows; };
inline mapping resolve(const std::vector<cell>& cells, const std::vector<cell>& rows,
        int32_t sequence, const std::vector<int64_t>& keys, const std::vector<int64_t>& queries) {
    if (sequence < 0 || keys.empty() || queries.empty()) throw std::invalid_argument("empty or invalid request");
    auto find = [sequence](const std::vector<cell>& entries, int64_t pos) {
        if (pos < 0) throw std::invalid_argument("invalid logical position");
        int64_t found=-1;
        for (size_t i=0; i<entries.size(); ++i) if (entries[i].sequence==sequence && entries[i].position==pos) {
            if (found!=-1) throw std::invalid_argument("ambiguous position");
            found=int64_t(i);
        }
        if (found==-1) throw std::invalid_argument("missing position");
        return found;
    };
    mapping m;
    for (auto pos:keys) {
        for (size_t j=0;j<m.key_cells.size();++j) if (keys[j]==pos) throw std::invalid_argument("duplicate key request");
        m.key_cells.push_back(find(cells,pos));
    }
    for (auto pos:queries) {
        for (auto key:keys) if (key==pos) throw std::invalid_argument("query overlaps chunk");
        for (size_t j=0;j<m.query_rows.size();++j) if (queries[j]==pos) throw std::invalid_argument("duplicate query request");
        m.query_rows.push_back(find(rows,pos));
    }
    return m;
}
}
