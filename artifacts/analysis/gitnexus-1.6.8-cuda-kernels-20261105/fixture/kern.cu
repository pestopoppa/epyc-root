#include <cuda_runtime.h>

template<int D, bool fuse = false>
__launch_bounds__(get_nthreads(D), 1)
static __global__ void flash_attn_ext_vec(const float * x, float * y) {
    y[threadIdx.x] = x[threadIdx.x];
}

__global__ void plain_kernel(float * y) {
    y[0] = 0.0f;
}

void launch_direct(const float * x, float * y, cudaStream_t s) {
    flash_attn_ext_vec<64, true><<<dim3(4, 1, 1), 32, 0, s>>>(x, y);
    plain_kernel<<<1, 1>>>(y);
}

typedef void (*fattn_kernel_t)(const float *, float *);
void launch_fattn(fattn_kernel_t k, const float * x, float * y);

void case_impl(const float * x, float * y) {
    fattn_kernel_t fattn_kernel = flash_attn_ext_vec<64, false>;
    launch_fattn(fattn_kernel, x, y);
}

void fused(const float * x, float * y) {
    const auto producer_kernel = flash_attn_ext_vec<64, false>;
    launch_fattn(producer_kernel, x, y);
}
