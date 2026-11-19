#include "llama-model.h"
#include "llama-kv-cache.h"
#include "llama-batch.h"
#include <memory>
#include <iostream>
#include <unistd.h>
#include <cstring>
int main(int argc, char **argv) {
    if (argc != 2 || (std::strcmp(argv[1], "honest") && std::strcmp(argv[1], "skip_apply"))) return 20;
    bool mutant = !std::strcmp(argv[1], "skip_apply");
    std::cout << "READY " << getpid() << std::endl;
    char go; if (!(std::cin >> go) || go != 'g') return 21;
    auto params = llama_model_default_params();
    std::unique_ptr<llama_model> model(llama_model_create(LLM_ARCH_QWEN2, params));
    if (!model) return 22;
    llama_hparams hp{};
    llama_kv_cache cache(*model, hp, GGML_TYPE_F16, GGML_TYPE_F16, false, false, true, 8, 1, 1, 0, LLAMA_SWA_TYPE_NONE, nullptr, {}, {}, {}, "observer-fixture");
    llama_seq_id id=0; llama_seq_id* row_ids[2]={&id,&id}; int32_t n_seq[2]={1,1}; llama_pos pos[2]={0,1};
    llama_ubatch batch{}; batch.n_tokens=2; batch.n_seqs=1; batch.n_seqs_unq=1; batch.n_seq_tokens=2; batch.n_pos=1; batch.seq_id_unq=&id; batch.n_seq_id=n_seq; batch.seq_id=row_ids; batch.pos=pos;
    auto a=cache.find_slot(batch,false);
    if (a.idxs.size()!=1 || a.idxs[0].size()!=2 || a.idxs[0][0]!=0 || a.idxs[0][1]!=1) return 23;
    if (!mutant) cache.apply_ubatch(a,batch);
    auto b=cache.find_slot(batch,false);
    if (b.idxs.size()!=1 || b.idxs[0].size()!=2) return 24;
    bool expected = b.idxs[0][0]==2 && b.idxs[0][1]==3;
    bool mutation_seen = b.idxs[0][0]==0 && b.idxs[0][1]==1;
    if ((!mutant && !expected) || (mutant && !mutation_seen)) return 25;
    std::cout << "RESULT " << (mutant ? "DETECTED" : "PASS") << ' ' << b.idxs[0][0] << ' ' << b.idxs[0][1] << std::endl;
    char done; if (!(std::cin >> done) || done != 'q') return 26;
    return 0;
}
