// Model-free CPU cache fixture. Test-only friend declaration is in the companion patch.
#undef NDEBUG
#include "llama-kv-cache.h"
#include "llama-model.h"
#include "llama-arch.h"
#include "llama-io.h"
#include "ggml-backend.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <memory>
#include <vector>

struct bytes_sink final : llama_io_write_i {
    std::vector<uint8_t> bytes;
    void write(const void * p, size_t n) override {
        auto * b = static_cast<const uint8_t *>(p);
        bytes.insert(bytes.end(), b, b + n);
    }
    void write_tensor(ggml_tensor * t, size_t offset, size_t n) override {
        auto old = bytes.size(); bytes.resize(old+n);
        ggml_backend_tensor_get(t, bytes.data()+old, offset, n);
    }
    size_t n_bytes() override { return bytes.size(); }
};

struct kpf60_fixture_access {
    using ranges = llama_kv_cache::cell_ranges_t;
    static bool count(const llama_kv_cache & c, const ranges & r,
                      const std::vector<kpf60::expected_tensor> & e, kpf60::totals & out) {
        return c.count_state_data_for_test(r,e,out);
    }
    static void write(const llama_kv_cache & c, const ranges & r, bytes_sink & out) {
        c.state_write_data(out,r);
    }
    static void populate(llama_kv_cache & c) {
        for (uint32_t i=0;i<8;i++) {
            c.v_cells[0].pos_set(i, static_cast<llama_pos>(i));
            c.v_cells[0].seq_add(i,0);
        }
        // The same selected physical cells have two owners, but must be counted once.
        for (uint32_t i : {1u,2u,5u}) c.v_cells[0].seq_add(i,1);
        for (auto & l : c.layers) {
            for (auto * t : {l.k, l.v}) {
                if (!t) continue;
                std::vector<uint8_t> value(ggml_nbytes(t));
                for (size_t i=0;i<value.size();i++) value[i] = uint8_t((i+31*l.il+(t==l.v ? 79 : 0)) & 255);
                ggml_backend_tensor_set(t,value.data(),0,value.size());
            }
        }
    }
};

int main() {
    std::unique_ptr<llama_model> model(llama_model_create(LLM_ARCH_LLAMA, llama_model_default_params()));
    assert(model);
    llama_hparams h{}; h.n_layer_all=2; h.n_embd_head_k_full=4; h.n_embd_head_v_full=4;
    h.n_head_arr[0]=h.n_head_arr[1]=1; h.n_head_kv_arr[0]=h.n_head_kv_arr[1]=1;
    llama_kv_cache c(*model,h,GGML_TYPE_F16,GGML_TYPE_F16,false,false,true,8,2,1,0,
                     LLAMA_SWA_TYPE_NONE,nullptr,{}, {}, {});
    kpf60_fixture_access::populate(c);
    const kpf60_fixture_access::ranges r{0,{{1,3},{5,6}}};
    const std::vector<kpf60::expected_tensor> expected={
        {{0,0,false},{{1,3},{5,6}}},{{1,0,false},{{1,3},{5,6}}},
        {{0,0,true}, {{1,3},{5,6}}},{{1,0,true}, {{1,3},{5,6}}}};
    kpf60::totals t{99,99,99,99};
    assert(kpf60_fixture_access::count(c,r,expected,t));
    // Two layers, each K/V row = 4 F16 elements, three physical cells.
    assert(t.k==48 && t.v==48 && t.metadata==56 && t.serialized==152);
    bytes_sink sink; kpf60_fixture_access::write(c,r,sink);
    assert(sink.bytes.size()==t.serialized);
    auto bad=expected; bad.pop_back(); t={99,99,99,99};
    assert(!kpf60_fixture_access::count(c,r,bad,t));
    assert(t.k==99 && t.serialized==99);
    const kpf60_fixture_access::ranges overlap{0,{{1,3},{2,4}}};
    assert(!kpf60_fixture_access::count(c,overlap,expected,t));
    const kpf60_fixture_access::ranges empty{0,{}};
    assert(!kpf60_fixture_access::count(c,empty,expected,t));
    llama_kv_cache swa(*model,h,GGML_TYPE_F16,GGML_TYPE_F16,false,false,true,8,2,1,4,
                       LLAMA_SWA_TYPE_STANDARD,nullptr,{}, {}, {});
    assert(!kpf60_fixture_access::count(swa,r,expected,t));
    llama_kv_cache mirror(*model,h,GGML_TYPE_F16,GGML_TYPE_F16,false,false,true,8,2,1,0,
                          LLAMA_SWA_TYPE_NONE,&c,{}, {}, {});
    assert(!kpf60_fixture_access::count(mirror,r,expected,t));
    return 0;
}
