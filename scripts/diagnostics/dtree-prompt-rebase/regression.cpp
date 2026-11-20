// Model-free doubles around the actual pinned server resolve/accept statements.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>
using llama_seq_id = int;
using llama_token = int;
#define GGML_ASSERT(x) assert(x)
#define SLT_ERR(...) assert(false)
struct llama_batch {
    int n_tokens;
    int ** seq_id;
    int * parent;
};
struct tokens_type {
    std::vector<int> data;
    void keep_first(size_t n) { assert(n <= data.size()); data.resize(n); }
    void insert(const std::vector<int> & v) { data.insert(data.end(), v.begin(), v.end()); }
};
struct prompt_type {
    tokens_type tokens;
    size_t n_tokens() const { return tokens.data.size(); }
};
struct server_slot {
    bool spec_tree_batch_round = true, spec_tree_batch = true;
    std::vector<std::vector<int>> spec_tree_i_batch, spec_tree_alts;
    std::vector<int> spec_i_batch, spec_draft;
    int id = 0, spec_tree_seq0 = 1, n_tree_rounds = 0;
    int n_tree_alt_wins = 0, n_tree_alt_extra = 0, sampled = -1;
    prompt_type prompt;
};
static int main_accept, alt_accept, committed_columns;
int common_dtree_greedy_accept_len(void *, const std::vector<int> &, const std::vector<int> & draft) {
    return draft.front() == 100 ? main_accept : alt_accept;
}
void * llama_get_memory(void * p) { return p; }
bool llama_memory_tree_accept(void *, int, const int *, int n) { committed_columns = n; return true; }
void common_dtree_promote(void *, int, int) {}
void common_dtree_drop(void *, int) {}
struct params_type { struct { int tree_seqs_per_slot() { return 2; } } speculative; };
struct server_type {
    std::vector<server_slot> slots;
    void * ctx_tgt = nullptr;
    params_type params_base;
    // INSERT_PINNED_RESOLVE
};

int main() {
    int cases = 0;
    for (int main_len = 1; main_len <= 7; ++main_len) {
        for (int alt_len = 1; alt_len <= 9; ++alt_len) {
            for (int accepted = 1; accepted <= alt_len; ++accepted) {
                for (bool wins : {false, true}) {
                    server_type server;
                    server.slots.emplace_back();
                    auto & slot = server.slots[0];
                    const std::vector<int> prefix = {5, 6, 7};
                    const int anchor = 42;
                    slot.prompt.tokens.data = prefix;
                    slot.prompt.tokens.data.push_back(anchor);
                    for (int j = 0; j < main_len; ++j) slot.spec_draft.push_back(100+j);
                    std::vector<int> alt;
                    for (int j = 0; j < alt_len; ++j) alt.push_back(200+j);
                    slot.prompt.tokens.insert(slot.spec_draft);
                    for (int j = 0; j <= main_len; ++j) slot.spec_i_batch.push_back(j);
                    std::vector<int> rows = {0};
                    for (int j = 0; j < alt_len; ++j) rows.push_back(main_len+1+j);
                    slot.spec_tree_i_batch = {rows};
                    slot.spec_tree_alts = {alt};
                    main_accept = wins ? 0 : 1;
                    alt_accept = wins ? accepted : 0;
                    const auto winner = wins ? alt : slot.spec_draft;
                    const int keep = wins ? accepted : 1;
                    const int width = main_len + 1 + alt_len;
                    std::vector<int> seqs(width, 0), parents(width, -1);
                    std::vector<int *> seq_ptrs;
                    for (auto & s : seqs) seq_ptrs.push_back(&s);
                    llama_batch view{width, seq_ptrs.data(), parents.data()}, proc = view;
                    assert(server.spec_tree_resolve(0, view, proc));
                    assert(committed_columns == keep+1);
                    assert(slot.spec_draft == winner);
                    assert(proc.parent == nullptr);
                    const size_t n_draft = slot.spec_draft.size();
                    std::vector<int> ids(winner.begin(), winner.begin()+keep);
                    ids.push_back(999); // sampled bonus/correction, not yet decoded
                    // INSERT_PINNED_ACCEPT
                    std::vector<int> expected = prefix;
                    expected.push_back(anchor);
                    expected.insert(expected.end(), winner.begin(), winner.begin()+keep);
                    if (slot.prompt.tokens.data != expected) {
                        std::cerr << "wrong prefix/next-position: main=" << main_len
                                  << " alt=" << alt_len << " accepted=" << keep << " wins=" << wins << '\n';
                        return 1;
                    }
                    assert(slot.sampled == 999);
                    assert(slot.n_tree_alt_wins == (wins ? 1 : 0));
                    ++cases;
                }
            }
        }
    }
    std::cout << cases << " resolve/accept cases passed\n";
}
