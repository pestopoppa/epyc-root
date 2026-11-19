// Execute the ported native draft methods with deterministic decoder/sampler
// spies. No model, production library, kernel or throughput claim is involved.
#include "model_boundary.h"
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <functional>
#include <iostream>
#include <memory>
#include <random>
#include <vector>

using llama_seq_id = int;
using llama_token = int;
using llama_tokens = std::vector<int>;
using common_speculative_type = int;
constexpr int LLAMA_DEFAULT_SEED = 123;
#define GGML_ASSERT(x) assert(x)
#define LOG_WRN(...) ((void)0)
#define LOG_DBG(...) ((void)0)
#define SPC_ERR(...) ((void)0)
#define SPC_DBG(...) ((void)0)
struct Context {};
struct Batch { int n_tokens = 0; float storage[4096]{}; float * embd = storage; };
struct Candidate { int id; float p; };
struct Candidates { size_t size = 2; Candidate data[2]{{21,.75f},{22,.25f}}; };
struct Sampler { Candidates candidates; };
struct Params { Context * ctx_dft; int n_max = 3, n_min = 0; float p_min = 0; };
struct common_speculative_token_dist { llama_tokens ids; std::vector<float> probs; };
struct DraftParams {
    bool drafting = true;
    int n_max = 3, n_past = 3, id_last = 20;
    llama_tokens * result;
    std::vector<common_speculative_token_dist> * dists = nullptr;
    float temperature = 0;
    uint32_t seed = 12;
    std::function<int(int,int,double)> cafe3_select;
    bool cafe3_selected = false;
};
using common_speculative_draft_params_vec = std::vector<DraftParams>;
int decodes = 0, samples = 0, accepts = 0, fail_decode = 0;
float lattice[128];
void common_batch_clear(Batch & b) { b.n_tokens = 0; }
void common_batch_add(Batch & b, int, int, std::initializer_list<int>, bool) { ++b.n_tokens; }
int llama_decode(Context *, const Batch &) { ++decodes; return fail_decode; }
void common_sampler_reset(Sampler *) {}
void common_sampler_sample(Sampler *, Context *, int, bool) { ++samples; }
const Candidates * common_sampler_get_candidates(Sampler * s, bool) { return &s->candidates; }
void common_sampler_accept(Sampler *, int, bool) { ++accepts; }
const float * llama_get_embeddings_nextn(Context *) { return lattice; }
const float * llama_get_embeddings_nextn_ith(Context *, int) { return lattice; }
void * llama_get_memory(Context *) { return nullptr; }
void llama_memory_seq_rm(void *, int, int, int) {}
void llama_set_nextn_layer_offset(Context *, int) {}

struct SamplerHandle { Sampler value; Sampler * get() { return &value; } };
struct Base {
    int t_draft_us = 0, n_call_draft = 0, n_gen_drafts = 0, n_gen_tokens = 0;
    bool gen_perf = false;
    virtual void draft(common_speculative_draft_params_vec &) = 0;
    virtual ~Base() = default;
};
struct Mtp : Base {
    Context ctx;
    Params params{&ctx};
    Batch batch;
    unsigned n_seq = 2;
    int n_embd = 6, type = 1;
    bool chain_heads = false, is_mem_shared = false;
    std::vector<SamplerHandle> smpls{2};
    std::vector<std::vector<float>> pending_h{2, std::vector<float>(6)};
    std::vector<std::vector<float>> chain_h{2};
    std::vector<int> i_last{0,0};
#include "native_mtp.inc"
};
struct Dflash : Base {
    Context ctx;
    Params params{&ctx};
    Batch batch;
    unsigned n_seq = 2;
    int n_embd_dec = 6, type = 2, mask_token_id = -1, selector_top_k = 2;
    bool is_dspark = false, is_dflash2 = false;
    std::vector<SamplerHandle> smpls{2};
    std::vector<bool> selector_reset{true,true};
    std::vector<std::mt19937> selector_rng{2};
#include "native_dflash.inc"
};
struct common_time_meas { common_time_meas(int &, bool) {} };
struct common_speculative {
    common_speculative_draft_params_vec dparams;
    std::vector<std::unique_ptr<Base>> impls;
    std::vector<Base *> impl_last{nullptr,nullptr};
};
#include "native_dispatch.inc"
struct Fallback : Base {
    int & calls;
    explicit Fallback(int & count) : calls(count) {}
    void draft(common_speculative_draft_params_vec &) override { ++calls; }
};

int main() {
    // Confidence is stable under score shifts and sharp temperatures, and
    // rejects corrupt scores instead of training from NaN/Inf.
    const float equal[]{3,3}, shifted[]{1002,1000}, ordinary[]{2,0};
    assert(cafe3::selector_confidence(equal,2,0) == .5);
    assert(cafe3::selector_confidence(shifted,2,0) == cafe3::selector_confidence(ordinary,2,0));
    assert(cafe3::selector_confidence(ordinary,2,.001) == 1);
    const float corrupt[]{std::numeric_limits<float>::infinity()};
    bool rejected = false;
    try { cafe3::selector_confidence(corrupt,1,0); }
    catch (const std::invalid_argument &) { rejected = true; }
    assert(rejected);
    DraftParams checked{};
    checked.n_max = 1;
    checked.cafe3_select = [](int,int cap,double) { assert(cap == 1); return 2; };
    rejected = false;
    try { cafe3::model_width(checked,1,3,.75); }
    catch (const std::invalid_argument &) { rejected = true; }
    assert(rejected && !checked.cafe3_selected);
    checked.cafe3_select = {};
    assert(cafe3::model_width(checked,1,3,std::nan("")) == 3);
    for (int i = 0; i < 20; ++i) {
        float row[]{11,12,2,0,0,2};
        std::memcpy(lattice + 6*i, row, sizeof(row));
    }
    for (int mode = 0; mode < 3; ++mode) {
        for (int width : {0,1,2,3}) {
            Mtp mtp;
            Dflash flash;
            flash.is_dflash2 = mode == 2;
            Base & model = mode == 0 ? static_cast<Base &>(mtp) : static_cast<Base &>(flash);
            llama_tokens out;
            common_speculative_draft_params_vec dp(2, DraftParams{});
            dp[0].result = &out;
            dp[1].drafting = false;
            int callbacks = 0;
            dp[0].cafe3_select = [&](int impl, int cap, double p0) {
                ++callbacks;
                assert(impl == (mode == 0 ? 1 : 2) && cap == 3);
                assert(decodes == 1 && accepts == 0);
                assert(mode == 2 ? p0 > .88 && p0 < .89 : p0 == .75);
                return width;
            };
            decodes = samples = accepts = 0;
            model.draft(dp);
            assert(callbacks == 1 && dp[0].cafe3_selected);
            assert(out.size() == size_t(width));
            assert(decodes == (mode == 0 ? std::max(1,width) : 1));
            assert(accepts == (mode == 2 ? 0 : width));
            assert(width == 0 || out.front() == (mode == 2 ? 11 : 21));
            if (mode == 2 && width == 0) assert(flash.selector_reset[0]);
        }
    }
    // Disabled callback preserves static output and never validates confidence.
    for (int mode = 0; mode < 3; ++mode) {
        Mtp mtp; Dflash flash; flash.is_dflash2 = mode == 2;
        Base & native = mode == 0 ? static_cast<Base &>(mtp) : static_cast<Base &>(flash);
        llama_tokens out;
        common_speculative_draft_params_vec legacy(2, DraftParams{});
        legacy[0].result = &out; legacy[1].drafting = false;
        native.draft(legacy);
        assert(out.size() == 3 && !legacy[0].cafe3_selected);
    }
    // DFlash2 stochastic drafting must retain the static sampler trajectory.
    // The confidence query itself consumes no RNG, including a zero choice.
    std::vector<llama_tokens> trajectories;
    for (bool adaptive : {false,true}) {
        Dflash flash; flash.is_dflash2 = true;
        llama_tokens out;
        std::vector<common_speculative_token_dist> distributions;
        common_speculative_draft_params_vec stochastic(2, DraftParams{});
        stochastic[0].result = &out; stochastic[0].dists = &distributions;
        stochastic[0].temperature = 1;
        stochastic[1].drafting = false;
        if (adaptive) stochastic[0].cafe3_select = [](int,int,double) { return 3; };
        flash.draft(stochastic);
        assert(distributions.size() == 3);
        trajectories.push_back(out);
    }
    assert(trajectories[0] == trajectories[1]);
    // Unequal per-sequence widths must neither stop nor extend each other.
    Mtp model;
    llama_tokens a, b;
    common_speculative_draft_params_vec dp(2, DraftParams{});
    dp[0].result = &a; dp[1].result = &b;
    dp[0].cafe3_select = [](int,int,double) { return 0; };
    dp[1].cafe3_select = [](int,int,double) { return 2; };
    model.draft(dp);
    assert(a.empty() && b.size() == 2);
    // A failed confidence decode must never select a width from stale logits.
    dp[0].cafe3_selected = dp[1].cafe3_selected = false;
    b.clear(); fail_decode = 1;
    model.draft(dp);
    assert(!dp[0].cafe3_selected && !dp[1].cafe3_selected);
    fail_decode = 0;
    // Execute the real common dispatcher too: width zero owns the chain and
    // cannot accidentally turn into an ngram/other-model fallback round.
    common_speculative chain;
    int fallback_calls = 0;
    chain.impls.push_back(std::make_unique<Mtp>());
    chain.impls.push_back(std::make_unique<Fallback>(fallback_calls));
    chain.dparams = dp;
    chain.dparams[1].drafting = false;
    chain.dparams[0].cafe3_select = [](int,int,double) { return 0; };
    common_speculative_draft(&chain);
    assert(fallback_calls == 0 && !chain.dparams[0].drafting);
    assert(chain.impl_last[0] == chain.impls[0].get() && a.empty());
    std::cout << "PASS native method spies: MTP/DFlash/DFlash2 widths 0..3, current confidence, no zero RNG, decode failure\n";
}
