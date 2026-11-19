#include <hip/hip_runtime.h>
#include <chrono>
#include <cstdio>
#include <thread>
__global__ void witness(unsigned *p) { if (!threadIdx.x && !blockIdx.x) *p = 0x50504b46U; }
int main() {
 unsigned *p = nullptr, v = 0;
 if (hipMalloc(&p, 192ull*1024*1024) != hipSuccess) return 1;
 if (hipMemset(p, 0, 192ull*1024*1024) != hipSuccess) return 2;
 auto b = std::chrono::steady_clock::now().time_since_epoch().count();
 hipLaunchKernelGGL(witness, dim3(1), dim3(64), 0, 0, p);
 if (hipGetLastError() != hipSuccess || hipDeviceSynchronize() != hipSuccess) return 3;
 auto e = std::chrono::steady_clock::now().time_since_epoch().count();
 if (hipMemcpy(&v, p, sizeof(v), hipMemcpyDeviceToHost) != hipSuccess || v != 0x50504b46U) return 4;
 std::this_thread::sleep_for(std::chrono::seconds(8));
 if (hipFree(p) != hipSuccess) return 5;
 std::printf("KPF50_CLOCK_WITNESS begin_ns=%lld end_ns=%lld\n", (long long)b, (long long)e);
}
