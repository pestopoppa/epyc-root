#include "llama-batch.h"
#include "llama-model.h"
#include "llama-kv-cache.h"
#include <memory>
#include <iostream>
#include <string>
#include <csignal>
#include <unistd.h>
int main(int argc, char **argv) {
 if (argc != 2) return 20;
 std::string mode=argv[1]; if(mode!="honest" && mode!="pos" && mode!="owner") return 21;
 auto params=llama_model_default_params();
 std::unique_ptr<llama_model> model(llama_model_create(LLM_ARCH_QWEN2,params)); if(!model) return 22;
 llama_hparams hp{};
 llama_kv_cache cache(*model,hp,GGML_TYPE_F16,GGML_TYPE_F16,false,false,false,8,2,1,0,LLAMA_SWA_TYPE_NONE,nullptr,{},{},{},"abi-qualification");
 llama_batch_allocr allocator(1);
 auto batch=allocator.ubatch_reserve(2,2);
 llama_seq_id owners[4][2]={{1,2},{1,0},{2,0},{1,2}};
 for(int i=0;i<4;i++){batch.pos[i]=10+i; batch.n_seq_id[i]=(i==0||i==3)?2:1; batch.seq_id[i]=owners[i];}
 if(mode=="pos") batch.pos[1]=91;
 if(mode=="owner") owners[3][1]=7;
 std::cout << "READY " << getpid() << ' ' << (uintptr_t)&batch << std::endl;
 raise(SIGSTOP); return 0;
}
