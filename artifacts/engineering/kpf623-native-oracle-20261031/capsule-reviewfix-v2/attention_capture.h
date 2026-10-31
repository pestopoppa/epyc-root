#pragma once
#include "ggml.h"
#include "ggml-backend.h"
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

namespace aux_capture {
// Physical key cells and query rows must come from a separately verified KV/batch
// mapping. Never infer these indices from logical token positions.
struct capture {
    std::string name;
    std::vector<int64_t> key_cells, query_rows;
    std::vector<double> means;
    bool seen=false, failed=false;
    size_t max_bytes=64u*1024u*1024u;
    void (*read)(const ggml_tensor *, void *, size_t, size_t)=ggml_backend_tensor_get;
    bool finish() const { return seen && !failed && means.size()==key_cells.size(); }
};
inline bool unique_in_range(const std::vector<int64_t>& xs, int64_t n) {
    if (xs.empty() || n<=0) return false;
    for (size_t i=0;i<xs.size();++i) {
        if (xs[i]<0 || xs[i]>=n) return false;
        for (size_t j=0;j<i;++j) if (xs[i]==xs[j]) return false;
    }
    return true;
}
inline bool callback(ggml_tensor * t, bool ask, void * data) {
    auto * c=static_cast<capture *>(data);
    if (!c || !t) return false;
    if (c->name != t->name) return false;
    if (ask) return true;
    if (c->seen) { c->failed=true; return true; }
    c->seen=true;
    if (t->type!=GGML_TYPE_F32 || t->ne[3]!=1 || t->ne[2]<=0 ||
        !unique_in_range(c->key_cells,t->ne[0]) || !unique_in_range(c->query_rows,t->ne[1])) {
        c->failed=true; return true;
    }
    const size_t bytes=ggml_nbytes(t);
    if (!bytes || bytes>c->max_bytes) { c->failed=true; return true; }
    std::vector<uint8_t> raw(bytes);
    c->read(t,raw.data(),0,bytes);
    c->means.assign(c->key_cells.size(),0.0);
    for (size_t i=0;i<c->key_cells.size();++i) for (auto q:c->query_rows)
        for (int64_t h=0;h<t->ne[2];++h) {
            const size_t idx[3]={size_t(c->key_cells[i]),size_t(q),size_t(h)};
            size_t offset=0;
            for (int d=0; d<3; ++d) {
                if (idx[d] && t->nb[d] > (std::numeric_limits<size_t>::max()-offset)/idx[d]) {
                    c->failed=true; return true;
                }
                offset += idx[d]*t->nb[d];
            }
            if (offset>bytes || bytes-offset<sizeof(float)) { c->failed=true; return true; }
            float v; std::memcpy(&v,raw.data()+offset,sizeof(v));
            if (!std::isfinite(v) || v<0.0f || v>1.0f) { c->failed=true; return true; }
            c->means[i]+=double(v)/(double(c->query_rows.size())*double(t->ne[2]));
        }
    return true;
}
} // namespace aux_capture
