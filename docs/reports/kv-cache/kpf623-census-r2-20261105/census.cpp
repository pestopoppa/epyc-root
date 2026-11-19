#include "llama.h"
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <fstream>
#include <string>
int main(int argc,char **argv) {
 if(argc!=4)return 64;
 auto p=llama_model_default_params(); p.vocab_only=true;p.n_gpu_layers=0;p.load_mtp=false;p.use_mmap=false;
 auto *m=llama_model_load_from_file(argv[1],p);if(!m)return 65;
 auto *v=llama_model_get_vocab(m);int n=llama_vocab_n_tokens(v);if(n<1||n>500000)return 66;
 FILE *f=fopen(argv[2],"wx");if(!f)return 67;
 int total=n; std::ifstream maps("/proc/self/maps"); std::ofstream witness(std::string(argv[2])+".maps"); witness<<maps.rdbuf();witness.close();
 int limit=atoi(argv[3]);if(limit>0&&n>limit)n=limit;
 std::vector<char>b(65536); size_t written=0;
 for(int i=0;i<n;i++) {int z=llama_token_to_piece(v,i,b.data(),b.size(),0,true);if(z<0||z>65536)return 68;
 written+=32+2*size_t(z);if(written>67108864)return 70;
 fprintf(f,"%d\t",i);for(int j=0;j<z;j++)fprintf(f,"%02x",(unsigned char)b[j]);fputc('\n',f);}
 if(fclose(f))return 69;llama_model_free(m);printf("PIECES_COMPLETE %d N_VOCAB %d\n",n,total);return 0;
}
