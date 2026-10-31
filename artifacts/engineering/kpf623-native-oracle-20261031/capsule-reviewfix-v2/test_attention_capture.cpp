#include "attention_capture.h"
#include <cassert>
#include <cmath>
#include <vector>
static void read_fixture(const ggml_tensor *t, void * out, size_t off, size_t n) { std::memcpy(out,static_cast<const char *>(t->data)+off,n); }
int main() {
    ggml_init_params p{1024*1024,nullptr,false}; auto * ctx=ggml_init(p); assert(ctx);
    auto * t=ggml_new_tensor_4d(ctx,GGML_TYPE_F32,4,2,2,1); ggml_set_name(t,"kq_soft_max-3");
    std::vector<float> weights(16,0.0f);
    // [key, query, head, stream] indexed k+4*q+8*h.
    weights[1]=.2f; weights[2]=.8f; weights[5]=.4f; weights[6]=.6f;
    weights[9]=.6f; weights[10]=.4f; weights[13]=.8f; weights[14]=.2f;
    std::memcpy(t->data,weights.data(),weights.size()*sizeof(float));
    aux_capture::capture c; c.name="kq_soft_max-3"; c.key_cells={1,2}; c.query_rows={0,1}; c.read=read_fixture;
    assert(aux_capture::callback(t,true,&c)); assert(aux_capture::callback(t,false,&c)); assert(c.finish());
    assert(std::abs(c.means[0]-.5)<1e-6 && std::abs(c.means[1]-.5)<1e-6);
    aux_capture::callback(t,false,&c); assert(!c.finish());
    aux_capture::capture absent; absent.name="kq_soft_max-4"; assert(!aux_capture::callback(t,true,&absent)); assert(!absent.finish());
    aux_capture::capture bad; bad.name="kq_soft_max-3"; bad.key_cells={1,1}; bad.query_rows={0}; bad.read=read_fixture;
    aux_capture::callback(t,false,&bad); assert(!bad.finish());
    aux_capture::capture invalid; invalid.name="kq_soft_max-3"; invalid.key_cells={4}; invalid.query_rows={0}; invalid.read=read_fixture;
    aux_capture::callback(t,false,&invalid); assert(!invalid.finish());
    aux_capture::capture tiny; tiny.name="kq_soft_max-3"; tiny.key_cells={1}; tiny.query_rows={0}; tiny.read=read_fixture; tiny.max_bytes=1;
    aux_capture::callback(t,false,&tiny); assert(!tiny.finish());
    auto * f16=ggml_new_tensor_4d(ctx,GGML_TYPE_F16,4,2,2,1); ggml_set_name(f16,"kq_soft_max-3");
    aux_capture::capture dtype; dtype.name="kq_soft_max-3"; dtype.key_cells={1}; dtype.query_rows={0}; dtype.read=read_fixture;
    aux_capture::callback(f16,false,&dtype); assert(!dtype.finish());
    auto * streams=ggml_new_tensor_4d(ctx,GGML_TYPE_F32,4,2,2,2); ggml_set_name(streams,"kq_soft_max-3");
    aux_capture::capture multi; multi.name="kq_soft_max-3"; multi.key_cells={1}; multi.query_rows={0}; multi.read=read_fixture;
    aux_capture::callback(streams,false,&multi); assert(!multi.finish());
    aux_capture::capture missing; missing.name="kq_soft_max-3"; missing.key_cells={1}; missing.query_rows={0}; assert(!missing.finish());
    weights[1]=NAN; std::memcpy(t->data,weights.data(),weights.size()*sizeof(float));
    aux_capture::capture nan; nan.name="kq_soft_max-3"; nan.key_cells={1}; nan.query_rows={0}; nan.read=read_fixture;
    aux_capture::callback(t,false,&nan); assert(!nan.finish());
    ggml_free(ctx);
}
