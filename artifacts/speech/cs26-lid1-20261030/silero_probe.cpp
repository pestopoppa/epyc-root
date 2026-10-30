#include "silero_lid.h"
#include <vector>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cmath>
extern "C" int cs26_silero_scores(silero_lid_context*,const float*,int,float*,int);
extern "C" const char* cs26_silero_lang(silero_lid_context*,int);
int main(int argc,char**argv){
 if(argc!=3)return 64; FILE*f=fopen(argv[2],"rb");if(!f)return 65;std::vector<float> x;int16_t v;while(fread(&v,2,1,f)==1)x.push_back(v/32768.f);fclose(f);
 auto*c=silero_lid_init(argv[1],1);if(!c)return 66;float original_conf=0;const char*orig=silero_lid_detect(c,x.data(),x.size(),&original_conf);std::vector<float> logits(256);int n=cs26_silero_scores(c,x.data(),x.size(),logits.data(),logits.size());if(n<0)return 67;int best=0;for(int i=1;i<n;i++)if(logits[i]>logits[best])best=i;
 printf("original=%s confidence=%.9g scored_top=%s\n",orig?orig:"NULL",original_conf,cs26_silero_lang(c,best));for(int i=0;i<n;i++)printf("%d\t%s\t%.9g\n",i,cs26_silero_lang(c,i),logits[i]);silero_lid_free(c);
}
