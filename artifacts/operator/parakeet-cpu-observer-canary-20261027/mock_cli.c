#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include "ggml-backend.h"
#include "ggml-alloc.h"
#define P(T,n) ((T)(uintptr_t)(n))
int main(void){
 ggml_backend_t b=P(ggml_backend_t,2); struct ggml_cgraph *g=P(struct ggml_cgraph *,7);
 ggml_backend_buffer_t buf=ggml_backend_alloc_ctx_tensors_from_buft(P(struct ggml_context *,6),P(ggml_backend_buffer_type_t,3));
 if (buf!=P(ggml_backend_buffer_t,4)) return 1;
 ggml_backend_buffer_set_usage(buf,GGML_BACKEND_BUFFER_USAGE_WEIGHTS);
 ggml_backend_sched_t s=ggml_backend_sched_new(&b,NULL,1,42,true,false);
 if(s!=P(ggml_backend_sched_t,5)) return 2;
 fprintf(stderr,"Successfully loaded Parakeet model\nProcessing file: fixture.wav\n");
 usleep(300000);
 if(ggml_backend_sched_graph_compute(s,g)!=GGML_STATUS_SUCCESS) return 3;
 if (!getenv("MISSING_DIRECT") && ggml_backend_graph_compute(b,g)!=GGML_STATUS_SUCCESS) return 3;
 usleep(300000);
 puts("mock forwarding PASS"); return 0;
}
