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
 auto &a=const_cast<llama_kv_cells&>(cache.get_cells(0));
 auto &b=const_cast<llama_kv_cells&>(cache.get_cells(1));
 a.pos_set(0,mode=="pos"?17:7); a.seq_add(0,0); if(mode=="owner") a.seq_add(0,65);
 b.pos_set(3,11); b.seq_add(3,255);
 std::cout << "READY " << getpid() << ' ' << (uintptr_t)&a << ' ' << (uintptr_t)&b << ' ' << a.size() << ' ' << b.size() << ' ' << a.pos_get(0) << ' ' << a.seq_has(0,0) << ' ' << a.seq_has(0,65) << ' ' << b.pos_get(3) << ' ' << b.seq_has(3,255) << std::endl;
 raise(SIGSTOP); return 0;
}
