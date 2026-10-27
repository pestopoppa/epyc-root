#include <hip/hip_runtime.h>
#include <cstdio>
int main() {
    int count=0; char bdf[32] = {};
    if (hipGetDeviceCount(&count) != hipSuccess || count < 1 || hipDeviceGetPCIBusId(bdf, sizeof bdf, 0) != hipSuccess) return 1;
    std::printf("%s\n", bdf); return 0;
}
