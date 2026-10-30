#include "whisper.h"
#include <vector>
#include <cstdint>
extern "C" {
void * lid_open(const char * p) { auto c=whisper_context_default_params(); c.use_gpu=false; return whisper_init_from_file_with_params(p,c); }
int lid_max(){return whisper_lang_max_id();}
int lid_id(const char * s){return whisper_lang_id(s);}
int lid_detect(void * p,const int16_t * samples,int n,float * probs) { std::vector<float> x(n); for(int i=0;i<n;i++) x[i]=samples[i]/32768.0f; auto c=(whisper_context*)p; int r=whisper_pcm_to_mel(c,x.data(),n,1); if(r) return -1000+r; return whisper_lang_auto_detect(c,0,1,probs); }
void lid_close(void * p){whisper_free((whisper_context*)p);}
}
