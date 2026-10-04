// CPU proof for FA-INT64-OFFSET: the 64-bit offsets equal the old 32-bit ones (as the GPU computes them,
// two's-complement wrap of int32*int) everywhere the old ones did not overflow, and differ exactly where
// they did. Enumerates the llama.cpp parameter space: n_kv multiple of 256 (FATTN_KQ_STRIDE) up to 2M,
// ubatch 512..4096, block column counts 8..64, D 128/256, KV heads 2..8.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <initializer_list>

static int32_t mul_i32_wrap(int32_t a, int32_t b) {  // what the kernel's int32*int computes
    uint32_t r = (uint32_t) a * (uint32_t) b;
    int32_t out; memcpy(&out, &r, 4); return out;
}

int main() {
    bool ok = true;
    // 1. WMMA mask offset: nb31*ic0, nb31 = 2*n_kv bytes (f16 mask row), ic0 = ncols*blockIdx.x <= ubatch - ncols
    for (int ub : {512, 1024, 2048, 4096}) {
        long first_bad = -1; long n_cases = 0, n_diff = 0;
        for (long n_kv = 256; n_kv <= 2L*1024*1024; n_kv += 256) {
            const int32_t nb31 = (int32_t) (2*n_kv);
            for (int ncols : {8, 16, 32, 64}) {
                for (int ic0 = 0; ic0 + ncols <= ub; ic0 += ncols) {
                    n_cases++;
                    const int64_t o64 = int64_t(nb31)*ic0;
                    const int64_t o32 = mul_i32_wrap(nb31, ic0);
                    const bool overflow = o64 > INT32_MAX;
                    if ((o64 != o32) != overflow) { ok = false; printf("INCONSISTENT n_kv=%ld ic0=%d\n", n_kv, ic0); }
                    if (o64 != o32) { n_diff++; if (first_bad < 0) first_bad = n_kv; }
                }
            }
        }
        printf("mask nb31*ic0  ub=%4d: %ld cases, %ld differ; first n_kv with a wrapped offset = %ld\n", ub, n_cases, n_diff, first_bad);
        if (ub <= 2048 && first_bad >= 0 && first_bad <= 524288) { ok = false; printf("  FAIL: differs at n_kv <= 524288\n"); }
    }
    // 2. K/V head offset: nb12*(head/gqa), nb12 = n_kv*D*2 bytes (f16-converted, non-contiguous K view)
    for (int D : {128, 256}) {
        for (int hkv : {2, 4, 8}) {
            long first_bad = -1;
            for (long n_kv = 256; n_kv <= 4L*1024*1024 && first_bad < 0; n_kv += 256) {
                const long nb12l = n_kv*D*2;
                if (nb12l > INT32_MAX) { break; } // the kernel ABI itself (now asserted in launch_fattn)
                for (int h = 0; h < hkv; h++) {
                    const int64_t o64 = int64_t((int32_t) nb12l)*h;
                    if (o64 != mul_i32_wrap((int32_t) nb12l, h)) { first_bad = n_kv; break; }
                }
            }
            printf("K nb12*(head/gqa) D=%d n_head_kv=%d: first n_kv with a wrapped offset = %ld\n", D, hkv, first_bad);
            if (first_bad >= 0 && first_bad <= 524288) { ok = false; printf("  FAIL: differs at n_kv <= 524288\n"); }
        }
    }
    printf(ok ? "OK: identical offsets wherever int32 did not overflow; all differences are overflows\n" : "FAIL\n");
    return ok ? 0 : 1;
}
