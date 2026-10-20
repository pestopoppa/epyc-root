#include <hip/hip_runtime.h>
#include <tl_templates/hip/gemm.h>
#include <tl_templates/hip/copy.h>
#include <tl_templates/hip/reduce.h>
#include <tl_templates/hip/scan.h>
#include <tl_templates/hip/ldsm.h>
#include <tl_templates/hip/threadblock_swizzle.h>
#include <tl_templates/hip/debug.h>

extern "C" __global__ void __launch_bounds__(128) matmul_kernel(half_t* __restrict__ A, half_t* __restrict__ B, half_t* __restrict__ C) {
  extern __shared__ __align__(1024) uchar buf_dyn_shmem[];
  void* A_shared = ((void*)((char*)buf_dyn_shmem + 0));
  void* B_shared = ((void*)((char*)buf_dyn_shmem + 4096));
  float C_local[32];
  #pragma unroll
  for (int i = 0; i < 8; ++i) {
    float broadcast_var = 0.000000e+00f;
    *(float4*)(C_local + (i * 4)) = make_float4(broadcast_var, broadcast_var, broadcast_var, broadcast_var);
  }
  for (int k = 0; k < 32; ++k) {
    __syncthreads();
    #pragma unroll
    for (int i_1 = 0; i_1 < 2; ++i_1) {
      *(uint4*)(((half_t*)A_shared) + ((((i_1 * 1024) + ((((int)threadIdx.x) >> 2) * 32)) + (((((((int)threadIdx.x) & 31) >> 4) + ((((int)threadIdx.x) & 3) >> 1)) & 1) * 16)) + (((((((int)threadIdx.x) & 15) >> 3) + (((int)threadIdx.x) & 1)) & 1) * 8))) = *(uint4*)(A + (((((((int)blockIdx.y) * 65536) + (i_1 * 32768)) + ((((int)threadIdx.x) >> 2) * 1024)) + (k * 32)) + ((((int)threadIdx.x) & 3) * 8)));
    }
    #pragma unroll
    for (int i_2 = 0; i_2 < 2; ++i_2) {
      *(uint4*)(((half_t*)B_shared) + (((((i_2 * 1024) + ((((int)threadIdx.x) >> 3) * 64)) + (((((((int)threadIdx.x) & 63) >> 5) + ((((int)threadIdx.x) & 7) >> 2)) & 1) * 32)) + (((((((int)threadIdx.x) & 31) >> 4) + ((((int)threadIdx.x) & 3) >> 1)) & 1) * 16)) + (((((((int)threadIdx.x) & 15) >> 3) + (((int)threadIdx.x) & 1)) & 1) * 8))) = *(uint4*)(B + (((((k * 32768) + (i_2 * 16384)) + ((((int)threadIdx.x) >> 3) * 1024)) + (((int)blockIdx.x) * 64)) + ((((int)threadIdx.x) & 7) * 8)));
    }
    {
      half_t A_local[8];
      half_t B_local[16];
      __syncthreads();
      for (int ki = 0; ki < 2; ++ki) {
        for (int i_3 = 0; i_3 < 2; ++i_3) {
          *(uint2*)(A_local + (i_3 * 4)) = *(uint2*)(((half_t*)A_shared) + (((((((((int)threadIdx.x) >> 6) * 1024) + (i_3 * 512)) + ((((int)threadIdx.x) & 15) * 32)) + (((((((int)threadIdx.x) & 7) >> 2) + ki) & 1) * 16)) + (((((((int)threadIdx.x) & 63) >> 5) + ((((int)threadIdx.x) & 3) >> 1)) & 1) * 8)) + (((((int)threadIdx.x) & 31) >> 4) * 4)));
        }
        for (int j = 0; j < 4; ++j) {
          for (int local_id = 0; local_id < 4; ++local_id) {
            B_local[((j * 4) + local_id)] = ((half_t*)B_shared)[(((((((ki * 1024) + (((((int)threadIdx.x) & 63) >> 4) * 256)) + (local_id * 64)) + (((((((int)threadIdx.x) & 31) >> 4) + (j >> 1)) & 1) * 32)) + ((((local_id >> 1) + (j & 1)) & 1) * 16)) + (((((((int)threadIdx.x) & 15) >> 3) + (local_id & 1)) & 1) * 8)) + (((int)threadIdx.x) & 7))];
          }
        }
        for (int i_4 = 0; i_4 < 2; ++i_4) {
          for (int j_1 = 0; j_1 < 4; ++j_1) {
            {
      *(((float32x4*)C_local) + ((i_4 * 4) + j_1)) = __builtin_amdgcn_mfma_f32_16x16x16f16(*(((float16x4*)B_local) + j_1),
                    *(((float16x4*)A_local) + i_4),
                    *(((float32x4*)C_local) + ((i_4 * 4) + j_1)), 0, 0, 0);
    };
          }
        }
      }
    }
  }
  #pragma unroll
  for (int i_5 = 0; i_5 < 8; ++i_5) {
    half_t C_local_cast[4];
    uint2 __1;
    float4 v_ = *(float4*)(C_local + (i_5 * 4));
    *((half_t*)(&(((half2*)(&(__1.x)))->x))) = (half_t)(v_.x);
    *((half_t*)(&(((half2*)(&(__1.x)))->y))) = (half_t)(v_.y);
    *((half_t*)(&(((half2*)(&(__1.y)))->x))) = (half_t)(v_.z);
    *((half_t*)(&(((half2*)(&(__1.y)))->y))) = (half_t)(v_.w);
    *(uint2*)(C_local_cast + 0) = __1;
    *(uint2*)(C + (((((((((int)blockIdx.y) * 65536) + ((((int)threadIdx.x) >> 6) * 32768)) + ((i_5 >> 2) * 16384)) + ((((int)threadIdx.x) & 15) * 1024)) + (((int)blockIdx.x) * 64)) + ((i_5 & 3) * 16)) + (((((int)threadIdx.x) & 63) >> 4) * 4))) = *(uint2*)(C_local_cast + 0);
  }
}

