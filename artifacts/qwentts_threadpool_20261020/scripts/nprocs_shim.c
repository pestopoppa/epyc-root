// Re-creation of the CS-45 nprocs shim (the original /mnt/raid0/llm/tmp/cs45/nprocs_shim.so was deleted during this task):
// make std::thread::hardware_concurrency() / get_nprocs() / sysconf(_SC_NPROCESSORS_*) report $SHIM_NPROCS, which is the
// only way to set the production qwen-tts thread count (default hardware_concurrency()/2).
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/sysinfo.h>
static int n_from_env(int fallback) { const char *e = getenv("SHIM_NPROCS"); int v = e ? atoi(e) : 0; return v > 0 ? v : fallback; }
int get_nprocs(void) { return n_from_env(192); }
int get_nprocs_conf(void) { return n_from_env(192); }
long sysconf(int name) {
    static long (*real)(int);
    if (!real) real = dlsym(RTLD_NEXT, "sysconf");
    if (name == _SC_NPROCESSORS_ONLN || name == _SC_NPROCESSORS_CONF) return n_from_env((int) real(name));
    return real(name);
}
