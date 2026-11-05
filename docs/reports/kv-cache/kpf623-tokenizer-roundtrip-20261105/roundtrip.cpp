#include "llama.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>
#include <sstream>
int main(int argc,char**argv) {
 if(argc==2 && std::string(argv[1])=="--smoke") { std::puts("SMOKE_COMPILED"); return 0; }
 if(argc!=4)return 64;
 auto p=llama_model_default_params();p.vocab_only=true;p.n_gpu_layers=0;p.load_mtp=false;p.use_mmap=false;
 auto*m=llama_model_load_from_file(argv[1],p);if(!m)return 65;auto*v=llama_model_get_vocab(m);
 std::ifstream in(argv[2]); FILE*out=fopen(argv[3],"wx"); if(!in||!out)return 66;
 std::ifstream maps("/proc/self/maps");std::ofstream mapout(std::string(argv[3])+".maps");mapout<<maps.rdbuf();mapout.close();
 std::string line;int count=0;
 while(std::getline(in,line)) {
  auto a=line.find('\t'),b=line.find('\t',a+1);if(a==std::string::npos||b==std::string::npos)return 67;
  std::string hex=line.substr(a+1,b-a-1),bytes; if(hex.empty()||hex.size()%2)return 68;
  for(size_t i=0;i<hex.size();i+=2){char h[3]={hex[i],hex[i+1],0};char*end;long q=strtol(h,&end,16);if(*end)return 69;bytes.push_back((char)q);}
  std::vector<llama_token> tok(4096);int n=llama_tokenize(v,bytes.data(),bytes.size(),tok.data(),tok.size(),false,false);
  if(n<0||n>(int)tok.size()){fprintf(out,"%s\tUNKNOWN\n",line.substr(0,a).c_str());count++;continue;}
  std::string reconstructed,ids;std::vector<char>buf(65536);bool good=true;
  for(int i=0;i<n;i++){int z=llama_token_to_piece(v,tok[i],buf.data(),buf.size(),0,true);if(z<0||z>(int)buf.size()){good=false;break;}reconstructed.append(buf.data(),z);if(i)ids+=",";ids+=std::to_string(tok[i]);}
  const char*verdict=!good?"UNKNOWN":(reconstructed==bytes?(ids==line.substr(b+1)?"EXACT":"DIFFERENT_IDS"):"DIFFERENT_BYTES");
  fprintf(out,"%s\t%s\t%s\n",line.substr(0,a).c_str(),verdict,ids.c_str());count++;
 }
 if(fclose(out))return 70;llama_model_free(m);printf("ROUNDTRIP_COMPLETE %d\n",count);return count==256?0:71;
}
