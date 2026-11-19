#include <hip/hip_runtime.h>
#include <dlfcn.h>
#include <cstdio>
#include <unistd.h>
int main(int argc, char** argv) {
    if (argc != 2 || !dlopen(argv[1], RTLD_NOW | RTLD_LOCAL)) { fprintf(stderr,"backend load failed: %s\n", dlerror()); return 2; }
    void* p = nullptr;
    if (hipSetDevice(0) != hipSuccess || hipMalloc(&p, 192ULL*1024*1024) != hipSuccess || hipMemset(p, 7, 192ULL*1024*1024) != hipSuccess || hipDeviceSynchronize() != hipSuccess) return 3;
    puts("READY"); fflush(stdout);
    char c; (void)read(STDIN_FILENO, &c, 1);
    return hipFree(p) == hipSuccess ? 0 : 4;
}
