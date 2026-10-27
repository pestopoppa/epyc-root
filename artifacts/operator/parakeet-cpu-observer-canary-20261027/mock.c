#include <stdint.h>
#include <stdlib.h>
#include "ggml-backend.h"
#include "ggml-alloc.h"
#define P(T,n) ((T)(uintptr_t)(n))
static void must(int x) { if (!x) abort(); }
size_t ggml_backend_dev_count(void){return 1;}
ggml_backend_dev_t ggml_backend_dev_get(size_t i){must(i==0);return P(ggml_backend_dev_t,1);}
enum ggml_backend_dev_type ggml_backend_dev_type(ggml_backend_dev_t d){must(d==P(ggml_backend_dev_t,1));return (enum ggml_backend_dev_type)atoi(getenv("MOCK_DEVICE") ? getenv("MOCK_DEVICE") : "0");}
const char *ggml_backend_dev_name(ggml_backend_dev_t d){must(d==P(ggml_backend_dev_t,1));return "mock";}
ggml_backend_dev_t ggml_backend_get_device(ggml_backend_t b){must(b==P(ggml_backend_t,2));return P(ggml_backend_dev_t,1);}
ggml_backend_dev_t ggml_backend_buft_get_device(ggml_backend_buffer_type_t b){must(b==P(ggml_backend_buffer_type_t,3));return P(ggml_backend_dev_t,1);}
const char *ggml_backend_buffer_name(ggml_backend_buffer_t b){must(b==P(ggml_backend_buffer_t,4));return "mock";}
bool ggml_backend_buffer_is_host(ggml_backend_buffer_t b){must(b==P(ggml_backend_buffer_t,4));return true;}
size_t ggml_backend_buffer_get_size(ggml_backend_buffer_t b){must(b==P(ggml_backend_buffer_t,4));return 123;}
ggml_backend_buffer_type_t ggml_backend_buffer_get_type(ggml_backend_buffer_t b){must(b==P(ggml_backend_buffer_t,4));return P(ggml_backend_buffer_type_t,3);}
int ggml_backend_sched_get_n_backends(ggml_backend_sched_t s){must(s==P(ggml_backend_sched_t,5));return 1;}
ggml_backend_t ggml_backend_sched_get_backend(ggml_backend_sched_t s,int i){must(s==P(ggml_backend_sched_t,5)&&i==0);return P(ggml_backend_t,2);}
ggml_backend_sched_t ggml_backend_sched_new(ggml_backend_t *b,ggml_backend_buffer_type_t *bt,int n,size_t sz,bool p,bool o){must(b[0]==P(ggml_backend_t,2)&&bt==NULL&&n==1&&sz==42&&p&& !o);return P(ggml_backend_sched_t,5);}
ggml_backend_buffer_t ggml_backend_alloc_ctx_tensors_from_buft(struct ggml_context *c,ggml_backend_buffer_type_t bt){must(c==P(struct ggml_context *,6)&&bt==P(ggml_backend_buffer_type_t,3));return P(ggml_backend_buffer_t,4);}
void ggml_backend_buffer_set_usage(ggml_backend_buffer_t b,enum ggml_backend_buffer_usage u){must(b==P(ggml_backend_buffer_t,4)&&u==GGML_BACKEND_BUFFER_USAGE_WEIGHTS);}
enum ggml_status ggml_backend_sched_graph_compute(ggml_backend_sched_t s,struct ggml_cgraph *g){must(s==P(ggml_backend_sched_t,5)&&g==P(struct ggml_cgraph *,7));return GGML_STATUS_SUCCESS;}
enum ggml_status ggml_backend_graph_compute(ggml_backend_t b,struct ggml_cgraph *g){must(b==P(ggml_backend_t,2)&&g==P(struct ggml_cgraph *,7));return GGML_STATUS_SUCCESS;}
