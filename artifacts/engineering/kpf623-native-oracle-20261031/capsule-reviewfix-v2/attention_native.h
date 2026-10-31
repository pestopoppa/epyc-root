#pragma once
#include "attention_producer.h"
#include "native-draft/llama-ext.h"
namespace aux_capture {
// Invoked synchronously in the graph callback; no decode/synchronize here.
inline bool native_snapshot(void * data, int32_t seq, int64_t n, std::vector<cell> & out) {
    auto * ctx=static_cast<llama_context *>(data);
    if (!ctx || seq<0 || n<=0 || n>1000000) return false;
    std::vector<llama_pos> positions(size_t(n),-1);
    if (!llama_aux_attention_snapshot_cells(ctx,seq,positions.size(),positions.data())) return false;
    out.clear(); out.reserve(positions.size());
    for (auto pos:positions) out.push_back({pos,pos<0 ? -1 : seq});
    return true;
}
}
