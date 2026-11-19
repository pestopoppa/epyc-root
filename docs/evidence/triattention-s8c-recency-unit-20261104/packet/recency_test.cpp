// Exercise the compiled candidate's actual eviction function with deterministic
// scoring and memory doubles. The executable exports these doubles through PLT.
#include "llama-kv-compress.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <utility>
#include <iostream>
#include <limits>
#include <set>
#include <string>
#include <vector>

static std::vector<float> scores;
static std::set<int> occupied;
static int actual_removed = 0, score_calls = 0, rm_calls = 0;
static bool reject_rm = false;
extern "C" llama_memory_t llama_get_memory(const llama_context *) { return reinterpret_cast<llama_memory_t>(0x1234); }
extern "C" llama_pos llama_memory_seq_pos_max(llama_memory_t, llama_seq_id) { return occupied.empty() ? -1 : *occupied.rbegin(); }
extern "C" bool llama_memory_seq_rm(llama_memory_t, llama_seq_id, llama_pos start, llama_pos end) {
    ++rm_calls; if (reject_rm) return false;
    for (int p = start; p < end; ++p) actual_removed += static_cast<int>(occupied.erase(p));
    return true;
}
extern "C" void llama_memory_seq_add(llama_memory_t, llama_seq_id, llama_pos, llama_pos, llama_pos) { std::abort(); }
std::vector<float> llama_kv_compress_score(llama_context *, llama_seq_id, const llama_kv_compress_params &) { ++score_calls; return scores; }
static void setup(std::vector<float> s, std::set<int> slots, bool reject = false) {
    scores=std::move(s); occupied=std::move(slots); reject_rm=reject; actual_removed=score_calls=rm_calls=0;
}
static int invoke(const llama_kv_compress_params & p) { return llama_kv_compress_evict(reinterpret_cast<llama_context *>(0x1), 0, p); }
static int failed=0;
static void record(const char * name, bool ok, int reported, const char * why) {
    failed += !ok;
    std::cout << "{\"case\":\"" << name << "\",\"pass\":" << (ok?"true":"false")
      << ",\"reported_evicted\":" << reported << ",\"actual_removed\":" << actual_removed
      << ",\"score_calls\":" << score_calls << ",\"rm_calls\":" << rm_calls << ",\"detail\":\"" << why << "\"}\n";
}
int main() {
    llama_kv_compress_params p;
    setup({8,7,6,5,4,3,2,1},{0,1,2,3,4,5,6,7});p.n_sink=1;p.compression_ratio=.5f;
    int got=invoke(p);record("legacy_default", got==3 && actual_removed==3 && occupied==std::set<int>({0,1,2,3,4}) && score_calls==1,got,"disabled recency matches legacy threshold");
    setup({0,1,2,3,4,5,6,7},{0,1,2,3,4,5,6,7});p.n_sink=2;p.compression_ratio=.5f;p.keep_recent=2;
    got=invoke(p);record("recent_absolute",got==3 && occupied==std::set<int>({0,1,5,6,7}) && score_calls==1,got,"sink and two recent positions protected");
    setup({0,1,2,3,4,5,6,7},{0,1,2,3,4,5,6,7});p.keep_recent=0;p.recency_ratio=.4f;
    got=invoke(p);record("recent_ratio",got==3 && occupied==std::set<int>({0,1,5,6,7}),got,"40 percent of retained budget protects two positions");
    setup({0,1,2,3,4,5,6,7},{0,1,2,3,4,5,6,7});p.keep_recent=100;p.recency_ratio=0;p.compression_ratio=.75f;
    got=invoke(p);record("overlap_budget",got==4 && occupied==std::set<int>({0,1,6,7}),got,"recent count clamped to kept non-sink budget");
    setup({9,1,1,1,1,1},{0,1,2,3,4,5});p.n_sink=1;p.keep_recent=0;p.compression_ratio=.5f;
    got=invoke(p);record("legacy_ties",got==0 && occupied.size()==6,got,"legacy tied threshold retains equal scores");
    setup({0,1,2,3,4,5},{0,1,2,3,4,5});p.compression_ratio=1.0f;
    got=invoke(p);record("legacy_full_compression",got==4 && occupied==std::set<int>({0,5}),got,"legacy max scored position retained");
    setup({0,1,2,3},{0,1,2,3});p.n_sink=4;p.compression_ratio=.5f;
    got=invoke(p);record("all_sink",got==0 && occupied.size()==4 && score_calls==0,got,"sink overlap protects all positions");
    p.n_sink=1;p.keep_recent=1;p.recency_ratio=.5f;
    got=invoke(p);record("conflicting_controls",got==-1 && rm_calls==0,got,"absolute and relative controls rejected together");
    p.keep_recent=0;p.recency_ratio=std::numeric_limits<float>::quiet_NaN();got=invoke(p);
    record("invalid_nan",got==-1 && rm_calls==0,got,"non-finite ratio rejected");
    setup({10,9,0,0,4,3,2,1},{0,1,4,5,6,7});p.n_sink=2;p.recency_ratio=0;p.compression_ratio=.5f;
    got=invoke(p);record("gapped_kv_accounting",got==actual_removed,got,"reported count must equal physically removed occupied positions");
    setup({0,1,2,3,4,5,6,7},{0,1,2,3,4,5,6,7},true);p.n_sink=2;p.compression_ratio=.5f;
    got=invoke(p);record("seq_rm_failure",got==-1 && actual_removed==0,got,"failed memory removal must be surfaced");
    return failed ? 1 : 0;
}
