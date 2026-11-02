#include "llama.h"
#include <iostream>
#include <iterator>
#include <vector>
#include <cstdint>
int main(int argc, char **argv) {
    if (argc != 2) return 64;
    auto p=llama_model_default_params(); p.vocab_only=true;
    auto *m=llama_model_load_from_file(argv[1],p); if(!m) return 2;
    auto *v=llama_model_get_vocab(m);
    std::string s((std::istreambuf_iterator<char>(std::cin)),{});
    int n=llama_tokenize(v,s.data(),s.size(),nullptr,0,false,false);
    if (n==INT32_MIN || n>0) return 3;
    std::vector<llama_token> ids(-n);
    n=llama_tokenize(v,s.data(),s.size(),ids.data(),ids.size(),false,false);
    if(n<0 || n!=(int)ids.size()) return 4;
    std::cout.write(reinterpret_cast<const char*>(ids.data()),ids.size()*sizeof(llama_token));
    llama_model_free(m); return std::cout.good()?0:5;
}
