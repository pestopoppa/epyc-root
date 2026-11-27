# MI210 V5I Q8_0 conversion core

Run `python3 replay.py` in a copy of this directory on the EPYC host, pinned to the CPUs of a build grant. This reads and hashes the local archives, extracts gfx90a ELF images with the existing research `gfx90a_isa_audit.py`, disassembles the two recorded symbols, validates their nonflush control flow, and writes `audit.json` and the two ISA listings. The SHA-256 manifests pass for all four historical stores. No device access is needed.

## Provenance

The `5d85e7e737d5557cd38d86a39a07a37e35b2f12f` servedperf store produced the historical knee op trace for attn_q, 12288 × 5120 at width 8. The trace records 15,801 instances of `_ZL13q8mf6_mul_matILi2ELi2EEvPKcjS1_jiiiiPfl.kd`, all 416 workgroups × 256 threads, with 15,360 B LDS, 0 B private. This is `q8mf6_mul_mat<2,2>`. The accompanying op log confirms stage-contiguous Q8_0 packing and MF=6, P=2, slc=1. The loader is `test-backend-ops`; the measured program is a served-shape reproduction. The matching function in the library's gfx90a code object starts at address 0x10800 and has 5184 bytes. The ELF starts at library file offset 0x67b000, with SHA-256 `a087dd97647819bed290a3f5d9c5d6484d28cb64b2944878dee21b286bb4bf8f`. The function's SHA-256 is `62a9267aca1923209bbbae7105cd2405e45293db3756bc57e60ae40a7f51d7e8`.

The real 27B DFlash2 served OFF trace in `ak-27b-served-decode-profile-gpu-20261125` ran `llama-server` from `13b59e593-q8wpip`. All 68,025 raw q8mf kernel-family GEMV dispatches have the same exact symbol and launch resources. Its decode-window report `out/profile.md` attributes 28.250 ms of the 64.23 ms traced step to that family (44.0%). The target-verify width-8 portion is 24.477 ms/step. Raw dispatch counts include work outside the decode windows. The 28.250 excludes the separate 1.886 ms/step activation quantizer.

The `ak-c22-q8wt-op-diag-gpu-20261125` V5I hardware-counter reference runs the `59cc19096-q8wt` store in the baseline configuration. Its `out/RESULT.json` reports the width-8 V5I aggregate at 28.996 `SQ_INSTS_VALU`, 11.027 `SQ_INSTS_LDS`, and 3.765 `SQ_INSTS_MFMA` per KiB of analytical weight traffic. S16 streaming is 9.319 VALU/KiB. This was an op diagnostic. Its verdict correction disqualifies the wait-any direction as a test for absence of over-subscription. The corrected reading is high issue activity and dependency waits alongside near over-subscription.

The V5I function bytes are identical across all four stores, including the I8PC OFF comparator. Their descriptors differ only in the ELF-relative entry offset. Archive paths, file hashes, compiled ELF hashes, and trace digests are retained in `audit.json`.

## Steady-state ISA

The source is `ggml/src/ggml-cuda/mmq-q8-mf.cu` at `5d85e7e73`, lines 1326–1490. The compiler unrolls P=2. The replay takes the path +0xa20 through +0xd68, then +0xf40 through +0x1270, with the conditional jumps taken at both ends to skip the half-tile flush. Each unit covers 8704 bytes of weights and uses four wave64s. The table counts each issued opcode once per wave on the stated static path. It excludes prologue, final/tail/flush blocks, and the separate pre-pass.

| Instruction class | V5I per unit per wave | I8PC per unit per wave |
|---|---:|---:|
| i32 → f32 conversion of dot-product results | 16 | 16 |
| f16 → f32 conversion of weight block scales | 4 | 0 |
| Packed f32 scale multiply | 8 | 0 |
| Packed f32 FMA | 8 | 8 |
| Align-byte for misaligned packed int8 operands | 4 | 0 |
| Vector address add | 5 | 4 |
| **Non-MFMA VALU** | **45** | **28** |
| MFMA i32 16×16×16 i8 | 8 | 8 |
| LDS reads | 18 | 12 |
| LDS writes | 5 | 4 |
| VMEM loads | 5 | 4 |
| Barrier | 2 | 2 |
| Waitcnt | 17 | 12 or 14 |
| Total including SALU and NOP | 152 or 146 | 121 or 119 |

Two i8 MFMA instructions are already issued directly on packed int8 operands for each K=32 block. They produce four signed i32 result components per lane. Four conversions per block × four blocks per wave account for 16 per wave. The f16 conversions widen the weight scales. Packed f32 multiply forms the product of the source's half-scale and the activation's float scale, and packed f32 FMA applies it while accumulating. Thus switching to int8 MFMA cannot address the i32 result conversion because V5I already uses that operand path. Arbitrary Q8_0 block scales also prevent hoisting all scale products beyond the block. Replacing all 16 conversions with zero instructions would leave 29 non-MFMA VALU per unit, from 21.18 to 13.65 static VALU/KiB. The 9.319 streaming count remains a comparator that lacks the GEMV arithmetic. The replay does not assign the difference between static and hardware-counter figures to a particular instruction group.

V5I resource metadata is 118 VGPRs, 55 SGPRs, 0 AGPRs, 0 spills, 0 private and 15,360 B LDS. The two LDS writes attributed to V5I in the older q8lean note are executed on the separate conditional flush. There are five writes in either nonflush unit.

## Precedents and dependencies

- `59cc19096` q8wt throttled the grid and lost to V5I (served 0.955 [0.943, 0.968], op 0.77–0.86×). `b3365430c` q8lean removes LDS staging and address instructions while retaining all 40 conversion/scale/operand ALU operations, and lost about 31% served. `fbeb23c45` knee-batch reached flat op bandwidth, failed correctness in r3, and r4 was withdrawn at futility without a terminal JSON. None changes the MFMA result conversion.
- `1d4874a8a` register-direct MFMA q8wm lost (0.478× at YT2 vs stock q8wv) with scattered weight loads. `5b5f2deaa` q8wp moved weights to MFMA operand order and `13b59e593` added the usable in-place implementation. q8wp passed a 1.316× op test against stock q8wv, then 1.006 [0.998, 1.014] served against V5I, so the op ratio was a different comparator. `14118be51` / `121d8caf4` DET/DET2 change partial reductions/split geometry, outside this conversion loop. `ef0a8864a` fuses SwiGLU into the pre-pass.
- The positive prior is `6aedfd2ac` I8PC, folded on the C22 experimental composite by `2eb18341f` with a default-off switch. It requantizes weights to a single scale per output row. This moves that scale to the output flush, reduces weight payload to 8192 B per unit, and strips align-byte/scale work while leaving 16 conversions of i32 MFMA outputs. The archived r6 gate recorded KEEP, op 1.0883× overall and 1.1053× at w8, served 1.0565 [1.0378, 1.0756], KLD 0.000919. This is a numerically gated change to the original weights. It does not resolve exact Q8_0 conversion optimization. I8PC resource metadata is 98 VGPRs, 60 SGPRs, with the same zero scratch/spills and 15,360 B LDS.

## Experimental comparison

The operator granted a named exception to OP-AK-HOLD on 2026-11-27 for Q8-GEMV-CONVCORE-1, covering its MI210 correctness and timing after build and offline verification. The counter diagnostic, served trace and proposed new run have different observation windows. A 10% reduction in the full 28.250 ms family would save 2.825 ms per traced step if other costs held fixed. The narrower width-eight target portion would save 2.448 ms under the same assumption.

The proposed candidate seeds the first i8 matrix instruction with integer bits 0x4b400000. A pair of matrix instructions sums 32 signed-byte products. Their sum has absolute value at most 524288. Adding that integer to the bias gives an FP32 bit pattern in a region with spacing exactly one. Reinterpreting the bits and subtracting 12582912.0f therefore produces the same FP32 dot product, including positive zero under round-to-nearest. Two packed subtracts can recover four results. The compiled dependency chain and register traffic determine how much of that saving survives.

Both baseline visits use the candidate binary with the conversion switch off and the original served V5I settings. The study uses single-request greedy Qwen3.8-27B Q8_0 with DFlash2, draft maximum seven. The correctness gate compares against the CPU operator and bounds mean KLD at 0.003 for microbatch sizes 8, 4, 16 and 512. The performance gate follows the previous conversion-adjacent Q8LEAN study. It requires the lower end of the 95% confidence interval on served baseline/candidate ms per round to exceed 1.01 over eight scored blocks. Baseline repeats must agree within 2%. The block-four interim check can stop for futility only. The 10% kernel time saving is a planning scenario.

## Candidate build

Experimental kernel commit `5c061bf85ea4e3e855216f33bf31cf1febbde6c6` is based on servedperf `5d85e7e737d5557cd38d86a39a07a37e35b2f12f`, a descendant of frozen v10. The historical source differs from C21 by its served-shape test fixture. Apply the [kernel patch](convcore.patch) to that experimental parent to reproduce the source. Select the new path with `GGML_HIP_Q8_MF6_CONVCORE=1` on the existing MF=6 route.

In both SLC configurations the compiled OFF function's 5,184 instruction bytes match the historical V5I function. In the linked ON image the two unrolled units contain 16 packed FP32 adds in place of 32 scalar conversions. Both arms have 15,360 bytes of LDS per workgroup, zero private scratch and the same compiler-reported occupancy of four waves per SIMD. ON uses 126 vector registers per lane and OFF uses 118. The [ISA receipt](candidate-isa.json) records each specialization. The [host oracle](check-bias.cpp), built with `c++ -std=c++20 -O2`, checked every integer in the inclusive range −524288 to +524288 and found zero FP32 bit mismatches.

The [build manifest](build-identity.json) pins the private HIP library to SHA-256 `100b71f4551de8f5cb370fd6d76467090b009a591ca7de970bf0dda85ffde445`. Reapplying the patch to the parent reproduces candidate tree `f05d4b71f91f6cb8669a844d0426937ad33f50b8`. The C21 host frontends and servedperf test executable share the same private library set. Clean-source recompilation reproduced the GPU text, constant data and metadata and the host text. ELF symbol ordering differed between the two objects. File and source identities for the separate frontends are in the manifest.

The target model SHA-256 is `a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348`. The DFlash2 draft SHA-256 is `7f1c9a31a6ed40044c69f6508b50fd63b87abd8e1fb7fe4290303df549153751`.
