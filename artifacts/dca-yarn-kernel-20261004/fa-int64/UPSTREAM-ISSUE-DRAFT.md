# Draft — ggml-cuda FlashAttention: widen stride products before address calculation

**DRAFT FOR REVIEW; NOT POSTED.** The upstream source revision inspected is `11fe02151f79c41d0d4af7da708755d73b9c0da6` (a snapshot from 2026-10-04), not a statement about current upstream. The historical GPU reproduction below used a downstream ROCm/WMMA champion, not that upstream revision; reproducing the surviving tile/MMA/vec paths directly on an identified upstream build remains necessary before posting.

## Problem

At the inspected revision, several FlashAttention kernels receive byte strides as `int32_t` and multiply them by an `int` index before adding the result to a pointer. The product can overflow even when each individual stride fits in 32 bits. Promotion caused by an adjacent 64-bit pointer offset is too late if the multiplication itself is evaluated in 32-bit arithmetic. Signed overflow is undefined behavior; a wrapped address, wrong output or a device fault are possible outcomes, not guaranteed behavior for every compiler and shape.

Examples at the pinned revision:

- `ggml/src/ggml-cuda/fattn-tile.cuh:856-858`: `nb02 * head0`, `nb12 * (head0 / gqa_ratio)`, and `nb22 * (head0 / gqa_ratio)`.
- `ggml/src/ggml-cuda/fattn-mma-f16.cuh:1931-1932,1980-1981`: `nb02 * zt_Q`, `nb12 * z_KV`, and the adjacent V stride product.
- `ggml/src/ggml-cuda/fattn-vec.cuh:109-113`: Q/K/V stride products and `nb31 * ic0` for the mask.

For example, with f16-converted K, head dimension 256 and `n_kv=1,398,272`, a head stride is `1,398,272 * 256 * 2 = 715,915,264` bytes, which fits int32; multiplying it by KV-head index 3 gives `2,147,745,792` bytes, exceeding `INT32_MAX`. This is an arithmetic example of a hazardous K product, not a measured upstream failure or a claim that every model dispatches that shape. Likewise, a mask row stride of `557,056 * 2 = 1,114,112` bytes times a query offset 2016 gives 2,246,049,792 bytes. A large row stride can trigger the issue even when `kv=512` in a synthetic test.

## Historical downstream test and its scope

On 2026-10-04, a downstream gfx90a / AMD Instinct MI210 ROCm build with a WMMA FlashAttention path was tested against its CPU backend using a new `test-backend-ops` wide-mask fixture: `hsk=hsv=256`, `nh=4`, `nr23=[6,1]`, `kv=512`, `mask_ne0=557056`, f16 K/V, and query batches 64 and 2048, each with f32 and default precision. Largest wide mask is about 2.1 GiB. The unpatched downstream champion `90c12df4247e417053ffc59e2188294826d04ca2` libraries, used with the new test binary, passed 1/4; the f32 2048 case reported ERR 0.028597042 against 0.0005 tolerance, while f32 64 passed. Both default-precision cases also failed; the 64-query failure may involve a separate mask-row-stride defect, so it must not be attributed to int32 overflow. A downstream candidate incorporating WMMA and other changes passed 4/4, the full tested `FLASH_ATTN_EXT` suite 2872/2872, and 119 existing below-threshold comparisons were bit-identical to the champion. These are downstream measurements; they do **not** demonstrate a failure in upstream's tile, MMA, or vec implementations.

The test was run with `test-backend-ops test -o FLASH_ATTN_EXT -b ROCm0 -p mask_ne0`, after adding the fixture in downstream commit `4f21c34779ce50d940a02d0b1272c3dc20892afb`; those options and filter require that fixture, which is not claimed to be present in upstream. Historical fixed candidate `0c480112766f59eeb9f4587b952c1d5e29b0df81` contained the fixture plus the WMMA fix and the tile/MMA/vec changes; its ROCm build used `GGML_HIP=ON`, `AMDGPU_TARGETS=gfx90a`, and `GGML_HIP_ROCWMMA_FATTN=ON`. Therefore the difference is not an isolated test of the upstream paths. The historic source note says upstream's WMMA half was removed by #26046; this report proposes examining only the tile/MMA/vec paths at the pinned upstream revision. Relationship to issue #27090 is unverified and should be checked before posting.

## Suggested fix and upstream reproduction

Promote each stride operand **before** multiplication, e.g. `int64_t(nb12) * z_KV`, and audit all analogous pointer-offset products. Separately guard or widen the launch ABI where a single stride may exceed `INT32_MAX`; widening only the multiplication cannot recover an already truncated stride. A downstream patch at `0c480112766f59eeb9f4587b952c1d5e29b0df81` is a candidate starting point, not an upstream-tested patch. Review which stride fields are actually used in each kernel and avoid rejecting a large unused mask-plane stride.

To make an upstream-quality report, pin an actual upstream SHA and build artifact, construct a fixture selecting each tile/MMA/vec path with a large enough **individual product** while each stride is representable, prove the dispatched kernel and GPU residency, compare against CPU/reference, and rerun with only the widening patch. Include below-threshold controls and record exact shape, selected kernel, backend, compiler, logs and runtime linkage. The existing WMMA wide-mask fixture is useful prior art but does not establish upstream tile/MMA/vec failure; no upstream build or current-upstream retest is claimed here.
