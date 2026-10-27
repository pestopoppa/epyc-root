#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "ggml-backend.h"
#include "ggml-alloc.h"

/* Prototype only: never use as warrant until reviewed and fixture-tested. */
static void *next(const char *name) {
    void *p = dlsym(RTLD_NEXT, name);
    if (!p) { fprintf(stderr, "CPU_OBSERVER missing=%s\n", name); _exit(125); }
    return p;
}
static void inventory(const char *event, ggml_backend_t *backends, int count) {
    size_t n = ggml_backend_dev_count();
    fprintf(stderr, "CPU_OBSERVER %s pid=%ld devices=%zu backends=%d\n", event, (long)getpid(), n, count);
    for (size_t i=0; i<n; ++i) {
        ggml_backend_dev_t d = ggml_backend_dev_get(i);
        if (!d) _exit(125);
        fprintf(stderr, "CPU_OBSERVER device index=%zu type=%d name=%s\n", i, (int)ggml_backend_dev_type(d), ggml_backend_dev_name(d));
    }
    for (int i=0; i<count; ++i) {
        ggml_backend_dev_t d = ggml_backend_get_device(backends[i]);
        if (!d) _exit(125);
        fprintf(stderr, "CPU_OBSERVER backend index=%d type=%d name=%s\n", i, (int)ggml_backend_dev_type(d), ggml_backend_dev_name(d));
    }
}
ggml_backend_sched_t ggml_backend_sched_new(ggml_backend_t *b, ggml_backend_buffer_type_t *bt, int n, size_t s, bool p, bool o) {
    typedef ggml_backend_sched_t (*fn)(ggml_backend_t *, ggml_backend_buffer_type_t *, int, size_t, bool, bool);
    fn f = (fn)next("ggml_backend_sched_new");
    const char *names[]={"ggml_backend_sched_new","ggml_backend_alloc_ctx_tensors_from_buft","ggml_backend_buffer_set_usage","ggml_backend_sched_graph_compute","ggml_backend_graph_compute"};
    void *hooks[]={(void *)ggml_backend_sched_new,(void *)ggml_backend_alloc_ctx_tensors_from_buft,(void *)ggml_backend_buffer_set_usage,(void *)ggml_backend_sched_graph_compute,(void *)ggml_backend_graph_compute};
    for (int i=0;i<5;i++) if (dlsym(RTLD_DEFAULT,names[i])!=hooks[i] || !dlsym(RTLD_NEXT,names[i])) { fprintf(stderr,"CPU_OBSERVER hook_failure pid=%ld name=%s\n",(long)getpid(),names[i]); _exit(125); }
    fprintf(stderr,"CPU_OBSERVER hooks pid=%ld count=5\n",(long)getpid());
    inventory("sched_new", b, n);
    return f(b,bt,n,s,p,o);
}
ggml_backend_buffer_t ggml_backend_alloc_ctx_tensors_from_buft(struct ggml_context *ctx, ggml_backend_buffer_type_t buft) {
    typedef ggml_backend_buffer_t (*fn)(struct ggml_context *, ggml_backend_buffer_type_t);
    fn f = (fn)next("ggml_backend_alloc_ctx_tensors_from_buft");
    ggml_backend_buffer_t b = f(ctx,buft);
    if (b) {
        ggml_backend_dev_t d = ggml_backend_buft_get_device(buft);
        fprintf(stderr, "CPU_OBSERVER buffer pid=%ld name=%s host=%d size=%zu device_type=%d\n", (long)getpid(), ggml_backend_buffer_name(b), ggml_backend_buffer_is_host(b), ggml_backend_buffer_get_size(b), d ? (int)ggml_backend_dev_type(d) : -1);
    }
    return b;
}
enum ggml_status ggml_backend_sched_graph_compute(ggml_backend_sched_t sched, struct ggml_cgraph *graph) {
    typedef enum ggml_status (*fn)(ggml_backend_sched_t, struct ggml_cgraph *);
    fn f = (fn)next("ggml_backend_sched_graph_compute");
    int n=ggml_backend_sched_get_n_backends(sched);
    fprintf(stderr, "CPU_OBSERVER graph pid=%ld backends=%d\n", (long)getpid(), n);
    for (int i=0; i<n; ++i) {
        ggml_backend_t b=ggml_backend_sched_get_backend(sched,i);
        ggml_backend_dev_t d=b ? ggml_backend_get_device(b) : NULL;
        if (!d) _exit(125);
        fprintf(stderr, "CPU_OBSERVER graph_backend index=%d type=%d\n",i,(int)ggml_backend_dev_type(d));
    }
    return f(sched,graph);
}
void ggml_backend_buffer_set_usage(ggml_backend_buffer_t b, enum ggml_backend_buffer_usage usage) {
    typedef void (*fn)(ggml_backend_buffer_t, enum ggml_backend_buffer_usage);
    fn f = (fn)next("ggml_backend_buffer_set_usage");
    ggml_backend_buffer_type_t bt=ggml_backend_buffer_get_type(b);
    ggml_backend_dev_t d=bt ? ggml_backend_buft_get_device(bt) : NULL;
    fprintf(stderr, "CPU_OBSERVER usage pid=%ld usage=%d name=%s host=%d size=%zu device_type=%d\n", (long)getpid(), (int)usage, ggml_backend_buffer_name(b), ggml_backend_buffer_is_host(b), ggml_backend_buffer_get_size(b), d ? (int)ggml_backend_dev_type(d) : -1);
    f(b,usage);
}
enum ggml_status ggml_backend_graph_compute(ggml_backend_t backend, struct ggml_cgraph *graph) {
    typedef enum ggml_status (*fn)(ggml_backend_t, struct ggml_cgraph *);
    fn f=(fn)next("ggml_backend_graph_compute");
    ggml_backend_dev_t d=backend ? ggml_backend_get_device(backend) : NULL;
    fprintf(stderr, "CPU_OBSERVER direct_graph pid=%ld device_type=%d\n", (long)getpid(), d ? (int)ggml_backend_dev_type(d) : -1);
    return f(backend,graph);
}
