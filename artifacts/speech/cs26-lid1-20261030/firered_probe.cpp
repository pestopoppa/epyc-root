#include "firered_asr.h"
#include <vector>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
extern "C" int cs26_firered_scores(firered_asr_context*,const float*,int,float*,int,char**);
int main(int argc,char**argv){
 if(argc!=3)return 64;FILE*f=fopen(argv[2],"rb");if(!f)return 65;std::vector<float>x;int16_t v;while(fread(&v,2,1,f)==1)x.push_back(v/32768.f);fclose(f);
 auto params=firered_asr_context_default_params();params.n_threads=1;params.verbosity=0;auto*c=firered_asr_init_from_file(argv[1],params);if(!c)return 66;
 std::vector<float> logits(256);char* original=nullptr;int n=cs26_firered_scores(c,x.data(),x.size(),logits.data(),logits.size(),&original);if(n<0)return 67;int best=0;for(int i=1;i<n;i++)if(logits[i]>logits[best])best=i;
 printf("original=%s scored_top=%s\n",original,firered_asr_token_text(c,best));for(int i=0;i<n;i++)printf("%d\t%s\t%.9g\n",i,firered_asr_token_text(c,i),logits[i]);free(original);firered_asr_free(c);
}
