#define _GNU_SOURCE
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdatomic.h>
static atomic_long n;
int pthread_create(pthread_t *t, const pthread_attr_t *a, void *(*f)(void *), void *arg) {
    static int (*real)(pthread_t *, const pthread_attr_t *, void *(*)(void *), void *);
    if (!real) real = dlsym(RTLD_NEXT, "pthread_create");
    atomic_fetch_add(&n, 1);
    return real(t, a, f, arg);
}
__attribute__((destructor)) static void fin(void) { fprintf(stderr, "[count_pthread] pthread_create calls: %ld\n", (long)atomic_load(&n)); }
