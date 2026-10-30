#include "firered_asr.h"
#include <cstdlib>
extern "C" int cs26_firered_scores(firered_asr_context*,const float*,int,float*,int,char**);
extern "C" {
void* cs26_fire_open(const char* p){auto x=firered_asr_context_default_params();x.n_threads=1;x.verbosity=0;x.use_gpu=false;return firered_asr_init_from_file(p,x);}
int cs26_fire_detect(void* c,const float* s,int n,float* out,int cap,char** text){return cs26_firered_scores((firered_asr_context*)c,s,n,out,cap,text);}
const char* cs26_fire_token(void* c,int i){return firered_asr_token_text((firered_asr_context*)c,i);}
void cs26_fire_close(void* c){firered_asr_free((firered_asr_context*)c);}
void cs26_fire_free(char* p){free(p);}
}
