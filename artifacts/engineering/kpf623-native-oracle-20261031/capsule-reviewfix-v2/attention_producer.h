#pragma once
#include "attention_capture.h"
#include "position_map.h"

namespace aux_capture {
// The provider must snapshot exactly tensor.ne[0] physical KV cells for the
// current single stream, at callback time, from the active context. The producer
// cannot infer or certify that snapshot: caller/owner must establish its custody.
struct producer {
    capture captured;
    int32_t sequence=-1;
    std::vector<int64_t> chunk_positions, query_positions;
    std::vector<cell> query_batch_rows;
    bool (*snapshot)(void *, int32_t, int64_t, std::vector<cell>&)=nullptr;
    void * snapshot_data=nullptr;
    bool armed=false, failed=false;
    bool finish() const { return !failed && captured.finish(); }
};
inline bool producer_callback(ggml_tensor * t, bool ask, void * user) {
    auto * p=static_cast<producer *>(user);
    if (!p || !t) return false;
    if (!p->armed || p->captured.name != t->name) return false;
    if (ask) return true;
    if (!p->snapshot || p->captured.seen) { p->failed=true; return true; }
    try {
        std::vector<cell> cells;
        if (!p->snapshot(p->snapshot_data,p->sequence,t->ne[0],cells) ||
            cells.size()!=size_t(t->ne[0]) || p->query_batch_rows.size()!=size_t(t->ne[1])) {
            p->failed=true; return true;
        }
        for (const auto & row : p->query_batch_rows)
            if (row.sequence != p->sequence || row.position < 0) { p->failed=true; return true; }
        auto m=resolve(cells,p->query_batch_rows,p->sequence,p->chunk_positions,p->query_positions);
        p->captured.key_cells=std::move(m.key_cells); p->captured.query_rows=std::move(m.query_rows);
        return callback(t,false,&p->captured);
    } catch (...) { p->failed=true; return true; }
}
}
