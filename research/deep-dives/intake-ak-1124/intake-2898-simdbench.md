# Dive — simdbench — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2507.15224v1", retrieved: "2026-11-24", sha256: "9ee8c52fe47c"}

Stage 2b wave 1 (light dive), expanded from intake-2871 (kernelshift). Question to settle: LLM SIMD-intrinsic generation quality on x86 AVX-512 specifically (pass rates, common failure idioms) and whether it changes kernelshift row 2's expectation.

## 1. Stage-1 fields
- title: SimdBench: Benchmarking Large Language Models for SIMD-Intrinsic Code Generation
- authors: Yibo He, Shuoran Zhao, Jiaming Huang, Yingjie Fu, Hao Yu, Cunjian Huang, Tao Xie (Peking University, CUHK-Shenzhen, HKUST, Alibaba DAMO). v1, 21 Jul 2025, cs.SE.
- categories: benchmark_methodology, hardware_optimization, tool_implementation
- novelty: medium (first benchmark of SIMD-intrinsic generation; claim is the authors').
- relevance: low. It cannot answer the AVX-512 question it was surfaced for (see claim 0).
- credibility_score: 1 = peer-reviewed 0 (no venue stated on the page), within 12 months 0 (Jul 2025 is 16 months before 2026-11-24), known contributor +1 (Tao Xie, PKU software-engineering group), corroboration 0.
- verdict: adopt_patterns. Cite only for the failure-type taxonomy and the oracle design (differential test against a scalar canonical solution). Do not cite for any AVX-512 or VNNI/BF16/VBMI expectation.

## 2. Key claims
0. OVERTURNED as framed by the bearing dive (the paper was expected to speak to x86 AVX-512). The "AVX" column is compiled with `-mavx -mavx2`, the x86 host is an AMD EPYC 7H12 (Zen 2, no AVX-512; uncited general knowledge), and "only the basic and complete versions" of each extension are used. There is no AVX-512, no VNNI, no BF16, no VBMI measurement. Anchors 0, 1, 2.
1. CONFIRMED. On the AVX (AVX/AVX2) column LLMs are the strongest of the five extensions: 17 of 18 models have their best pass@5 on AVX; DeepSeek-R1 70.29 pass@1 / 87.50 pass@5, Gemini-2.5-Flash 60.29 / 86.03, Claude-3.5-Sonnet 38.09 / 52.21. Anchors 3, 4, 5.
2. CONFIRMED. AVX failures are logic bugs first: wrong result 47.41%, undeclared identifier 18.16%, core dump 7.64% of invalid AVX cases (compile errors dominate only for SVE/RVV). Anchor 6.
3. CONFIRMED. Tasks are basic: six operation classes (data movement, integer, floating-point, comparison, logical, reinterpret cast) at 8-64-bit integer and 32/64-bit float types plus HumanEval-derived ones; 136 tasks. No quantised dot products, permutes beyond basic ops, or matrix tiles. Anchor 7.
4. CONFIRMED, narrow. Valid SIMD code often beats scalar at -O3 but not always (Qwen2.5-Turbo AVX: 10 of 24 valid samples faster than scalar at -O3 after 23 of 24 at -O0). The baseline is scalar compiled code, not a tuned library. Anchor 8.
5. CONFIRMED. Setup is single-shot API generation at T=0.2, N=5 samples, no compile-and-test feedback loop, 18 models of 2024-2025 vintage. Anchor 9.

## 3. Reported results (as stated)
- 136 tasks x 5 extensions (SSE, AVX, Neon, SVE, RVV), 18 LLMs. DeepSeek-R1 best, average pass@5 75.44% across the five extensions.
- Scalar baseline pass@1 above 75% for all but GPT-3.5-Turbo and Qwen-Coder-Turbo; SIMD pass@k falls for every model; seven models at or below 15% pass@1 on all five intrinsics.
- Correctness on x86 docker (Ubuntu 24.04, clang 18.1.3, two EPYC 7H12), -O0; performance on the same host for SSE/AVX, Graviton2/4 for Neon/SVE, -O0 and -O3. Speedup is trimmed mean after dropping top and bottom 20%; efficient@k counts samples with speedup above 1.0.
- Top error types per extension in Table 5; RVV failures are 88.91% undeclared identifier (missing `__riscv_` prefix, attributed to stale training data).

## 4. Performance-principles table
| Principle (mechanism) | MI210 gfx90a | Zen 5 EPYC 9655 |
|---|---|---|
| Differential test of generated SIMD code against a scalar canonical solution over 1,000 test iterations | YES (method). Same oracle idea as the independent references in the AK loop. | YES (method); `cpu_quant_reference.py` already plays this role. |
| Models know AVX/AVX2 intrinsics well, SVE/RVV poorly (data freshness of intrinsic names) | NO direct evidence: wave64 HIP intrinsics are not in the benchmark. | PARTIAL. Supports expecting AVX2 fluency; AVX-512 intrinsics (mask registers, `vpdpbusd`, `vdpbf16ps`, `vpermb`) are untested, so row 2's VNNI/BF16/VBMI question stays open. |
| Intrinsics beat compiler auto-vectorisation only sometimes (-O3 narrows the gap) | PARTIAL. HIP kernels are intrinsic-heavy already. | YES (inference). Argues for an auto-vectorised-scalar control arm in row 2 so the ladder has a floor. |
| Retrieval of intrinsic docs fixes identifier errors (paper's suggestion, not tested) | PARTIAL. | PARTIAL. Identifier errors are only 18% of AVX failures; the dominant class is wrong results, which our reference oracle already catches. |

## 5. In-house state
- x86 idioms the planner can imitate are already in C21: `_mm512_dpbusd_epi32` at `ggml/src/ggml-cpu/arch/x86/repack.cpp:125`, `_mm512_dpbf16_ps` at `ggml/src/ggml-cpu/iqk/iqk_gemm_floats.cpp:357-364`, `_mm512_permutexvar_epi8` at `ggml/src/ggml-cpu/exl3.cpp:421-433` @ 98ff8a4 (per the kernelshift dive).
- The AK loop already rejects wrong-result candidates via independent references and A/B (`loop/program.md` L24-45, per the kernelshift dive); a compile-error or wrong-result candidate costs a build, not a bad keep.

## 6. Derived-actionables ledger
| # | Draft task | Owner | Compute | Stop / decision rule |
|---|---|---|---|---|
| M1 | Refines kernelshift row 2 (not a duplicate): record each ladder candidate's outcome class using SimdBench's taxonomy (compiles / wrong result / undeclared identifier or no-matching-function / core dump / no intrinsic emitted) and add an auto-vectorised scalar control arm (`-O3 -march=znver5`, no intrinsics) to the same ladder. | `autokernel-loop.md` | code/doc-only classification inside row 2's analysis; the control arm is one more compile of the same candidate | Question: does the planner emit AVX-512 idioms, and do failures look like SimdBench's AVX profile (logic bugs, not names)? Decision: no change to row 2's stop rule (VNNI arm within the 4.5% seed spread of AVX2 arm = stop); the classification is free once row 2 runs. |
| M2 | DECLINE: adopt SimdBench tasks or pass rates as an expected prior for row 2. Reason specific to this entry: no AVX-512, VNNI, BF16 or VBMI task exists, the models are 2024-25 single-shot, and AVX here means AVX/AVX2; a prior drawn from it would be unsupported. | n/a | n/a | n/a |
| M3 | DECLINE: run SimdBench itself against our planner. Reason: its tasks are basic element-wise operations at 128/256-bit widths; they do not exercise served quantised-GEMM idioms, so the result would not predict row 2. | n/a | n/a | n/a |

## 7. Dive-surfaced sources
- The repository is an anonymous 4open.science link in the paper; not fetched. Decline: it would not change M1 (taxonomy is in the paper text).
- No other source found that would change a ledger row. Intake index: SimdBench absent (0 hits for 2507.15224).

## 8. Contradiction / adversarial pass
- Authors state compilation-target errors arise when models ignore the allowed SSE versions; performance is evaluated against scalar code only; RVV excluded from performance.
- N=5 samples (budget-limited, authors say more are encouraged), T=0.2, API models, so pass@k is a lower bound for an agent with tool feedback.
- No independent replication; no later restatement found in the source.

## 9. read_depth
FULL (text, Tables 1-5; figures 3-5 not viewable, so the speedup distribution and efficient@5 ranking are unread). lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
