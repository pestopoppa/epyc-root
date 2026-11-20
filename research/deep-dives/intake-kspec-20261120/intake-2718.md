# llama.cpp PR #32613: Q8_0 - Block Interleaving Implementation for x86 SIMD (AVX512/AVX2)

- **Intake**: intake-2718 (`intake-2718#record`)
- **Source**: https://github.com/ggml-org/llama.cpp/pull/32613
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: cpu-decode-roofline-program.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Cite the PR scope and its own 9600X numbers only. Do not file it as the XFER-4b A/B: on C14 with GGML_IQK=1 Q8_0 is served by iqk Option R and this repack never runs. Do not write an AVX-512 Q8_0 GEMV for decode.

## Key claims (anchored)

0. PR #32613 adds a Q8_0 8x8 repack for x86 with GEMM on AVX512/AVX2 and GEMV on AVX2 only.
   - PR body Overview: "The GEMM function was implemented for AVX512/AVX2 and GEMV functions are implemented for the AVX2 architecture"
1. The reported prefill gain is from the AVX512 GEMM build (7B Q8_0 pp512 73.65 -> 134.55 t/s, +82.69%, 6 threads, Ryzen 9600X); tg128 is flat to slightly negative and PPL over 655 chunks is unchanged.
   - PR body benchmark table: "llama 7B Q8_0 6.67 GiB 6.74 B CPU 6 pp 512 134.55 ± 0.44 82.69"
   - PR body PPL table: "llama 7B Q8_0 5.7996 ± 0.03238"
2. The PR is open and unreviewed, the author discloses AI drafted the AVX512 path, and the branch was force-pushed after the benchmark commit.
   - PR body AI disclosure: "AI usage disclosure: YES Used AI to generate an initial draft of the AVX512 path"
   - timeline: "force-pushed the Block_Interleaving_q80 branch from 089c72a to 298c40b"
   - PR body test platform: "The PR was tested in AMD Granite Ridge 9600X"

## Claim corrections

- claim 0: **unaffected** — Stage-1 description of the kernel scope confirmed by the body and the diff guards (GEMV under __AVX2__, GEMM AVX512 under __AVX512BW__ && __AVX512DQ__).
- claim 1: **narrowed** — The +82.7% is AVX512-build only (AVX2 build +14.91%); numbers were measured at 089c72a, before the force-push to 298c40b.
- claim 2: **unaffected** — Open, unreviewed, AI-drafted AVX512 path confirmed.

## Dive record

2026-11-20 Stage-2 dive (sonnet; PR page, gh JSON and diff read; C14 eee3da838 and v10 ffc1bac82 read via git show). OVERTURNS the steering premise that this is an A/B candidate for XFER-4b: XFER-4b (cpu-decode-roofline-program.md:L247 @1650e3d) is the iqk IQ4_NL/MXFP4 allowlist 8c4b282ae, and this PR is Q8_0-only, non-iqk. On C14 with GGML_IQK=1 the repack picker returns nullptr for Q8_0 (repack.cpp ~L4545-4566 @eee3da8) and Option R routes Q8_0 prefill to iqk Q8_0_R8 (iqk/iqk_dispatch.cpp L87-104 @eee3da8; operator kept Option R 2026-11-11, kernel-champion-and-promotion.md:L324-330 @1650e3d), so the PR kernel is unreachable on the served config; it runs only on a GGML_IQK=0 arm. C14/v10 have no x86 Q8_0 repack (only NEON/RISC-V branches). Hunk check: arch/x86/repack.cpp hunks apply; repack.cpp/arch-fallback.h/repack.h fail only on q1_0 context lines our older upstream base lacks. tg-flat is bandwidth: 6.67 GiB x 8.18 t/s ~ 58.6 GB/s (derived); an AVX-512 Q8_0 GEMV cannot move EPYC decode (barrier/bandwidth/attention-bound, autokernel-akx-program.md:L1292-1293 @1650e3d). Natural comparator: iqk Q8_0_R8 prefill on a dense Q8_0 model. lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d)
