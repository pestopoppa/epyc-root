# Dive — kshiftrepo — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://github.com/cmu-l3/kernel-shift", retrieved: "2026-11-24", sha256: "faffb712dcdd"}
> Extra reading (not an anchor source): shallow clone at `/mnt/raid0/llm/tmp/dive-ak-1124/kshiftrepo/repo/`, HEAD `610e835cefc38c1047b724231c91cd67495aedc1` (same SHA the bearing dive read).

Stage 2b wave 1 (light dive), expanded from intake-2871 (kernelshift). Question to settle: can `kgen capture/calibrate` and the e2e step emit x86/AVX-512 task files, what is the license, and what is the effort to reuse it for kernelshift row 1 (a KernelShift-format task set for served CPU ops at verify widths).

## 1. Stage-1 fields
- title: KernelShift: Kernel Optimization Across Evolving Hardware (repo cmu-l3/kernel-shift; paper arXiv 2611.29590, already in the index)
- authors: repo credits The KernelShift Authors; citation lists Shuaiwei Huang, Weihua Du, Allen Wu, Ivan Fox, Manupa Karunaratne, Yiming Yang, Sean Welleck (CMU L3 lab).
- state: public, main, 6 commits, 4 stars, 0 forks at fetch time. License Apache-2.0.
- categories: autonomous_research, hardware_optimization, benchmark_methodology, tool_implementation
- novelty: medium. relevance: medium (task format, baseline-relative SQNR calibration, autovec control are reusable ideas; the harness is Arm-only).
- credibility_score: 2 = not peer-reviewed 0, within 12 months +1, known group (CMU L3) +1, corroboration 0.
- verdict: adopt_patterns. Reuse the task format and two checks; do not expect to run the evaluator on x86 unmodified.

## 2. Key claims
0. CONFIRMED. Scope: Arm Neon, SVE, SVE2, SME2 only. 144 definitions / 99 in the evaluation set across ncnn, llama.cpp (GEMM, MoE, attention, RMSNorm: 26), Arm SIMD Loops, KleidiAI, plus 18 end-to-end llama.cpp quantized-GEMM definitions (Qwen3.5-4B, Llama-3.1-8B-Instruct). Anchors 0, 1, 2.
1. CONFIRMED. Scoring: a kernel counts only if correct on every workload; score is speedup over the expert implementation. Anchor 3.
2. PARTIAL (page plus code read). The evaluator and `kgen` execution legs are aarch64-only: the README says kernels run only on hardware that has their instructions; in code `kgen/check.py:120-121` skips execution legs when `platform.machine()` is not aarch64/arm64, `kgen/autovec.py:85-86` raises on non-aarch64, `kgen calibrate` is documented "runs kernels: aarch64" (`kgen/cli.py:90`), and the ISA table in `config/kernel_contracts.yaml:142-183` has only neon/sve/sve2/sme2 tiers (march strings armv8-a, armv8.2-a+sve, armv9-a+sve2, apple-m4) each tied to an EC2 instance type. The only x86 mention in the tree is the `perf_event_open` syscall number 298 in `bench/runtime/perf_counters.py:63`. Anchor 4 (page); code facts at SHA 610e835 (no page anchor).
3. PARTIAL. `kgen collect`/`capture` are PyTorch-hook based and ISA-independent in logic (they save real activations as .npy and tag workloads `inputs: real-activations`), but need a loader that runs the model in PyTorch; they would feed float activations from an HF checkpoint, not the quantised GGUF path ggml runs (inference). `kgen calibrate` records the baseline's SQNR per workload and gates candidates at baseline minus a margin (`EvalConfig.sqnr_margin_db`, default 1 dB per `kgen/README.md`), but it runs kernels through the Arm evaluator. Anchors 5, 6 (page: task artifacts, local bench).
4. CONFIRMED. The e2e step is Arm-specific: its hook is `armbench_override` patched onto llama.cpp v0.4.1 (commit b29c606), builds with clang++-18 aarch64 on Graviton boxes, and replaces only `mul_mat` and `rms_norm` (`e2e/README.md`, `e2e/override/README.md`, `e2e/override/armbench_override.c:76`). Not reusable against C21 without a new hook.
5. CONFIRMED. License: repo Apache-2.0 (LICENSE, NOTICE); `loops/` and generated `dataset/problems/` are under Arm's BSD 3-Clause; parts of `bench/data/` adapted from FlashInfer-Bench (Apache-2.0). HF dataset l3lab/KernelShift license: NOT-FOUND-IN-SOURCE. Anchors 7, 8 (page).

## 3. Reported results (as stated)
None in the repo page (it points to the paper and a project site). Repo statistics only: 144 definitions, 403 solutions, 1,968 workloads from `bench.cli summary` (page excerpt).

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 EPYC 9655 |
|---|---|---|
| Task = definition (axes, tensors, Python reference) + hidden workloads + reference-scalar solution + library baseline | YES (format). Could carry MFMA-shaped tasks; the reference/oracle structure is ISA-neutral. | YES (format). All four artifacts are plain JSON/JSONL/C++; an x86 tier needs a new ISA row and baseline wrapper. |
| Correct on every workload before timing; geomean over shapes | YES (method). | YES (method); matches our served-shape cases. |
| Baseline-relative SQNR floor (baseline SQNR minus 1 dB) on real activations | PARTIAL. We gate GPU spec work by in-row identity bands rather than SQNR. | YES in spirit: the in-row reference-build bands (SPEC-ID-GATE) are also baseline-relative; real activations are the new ingredient. |
| Autovectorised-scalar control (flag a baseline more than 2x slower than the autovec build of the scalar start) | PARTIAL. | YES. Cheap sanity arm for row 2: scalar reference at `-O3 -march=znver5` timed against iqk. |
| Per-kernel timing against repack/norepack across M (`kvr`) | PARTIAL. | PARTIAL. Arm repack paths; x86 would compare against tinyBLAS/iqk/repack. |

## 5. In-house state
- No KernelShift-format task set exists in the lane. The AK loop probes with llama-bench and `test-backend-ops -o OP --perf`, with independent CPU references (`cpu_quant_reference.py`, `cpu_norm_reference.py`, `cpu_fusion_reference.py`, `cpu_fa_reference.py`) and a CPU_REPACK oracle (`loop/program.md` L24-45, per the kernelshift dive). Served-shape cases and the quarter-24t shape are the current screen.
- Lane CPU boxes: `handoffs/active/autokernel-loop.md` (AK-CPU-A3B-MMID-GATEUP-BW at :8548, ceiling re-base note :8568 @ f74b175).

## 6. Derived-actionables ledger
| # | Draft task | Owner | Compute | Stop / decision rule |
|---|---|---|---|---|
| K1 | Refines kernelshift row 1 (do one op first, not four): in a research-repo scratch copy of kernel-shift, remove the two explicit aarch64 guards (`kgen/check.py:120`, `kgen/autovec.py:85`; `kgen/calibrate.py` has no guard of its own but runs through the Arm-only ISA table), add one x86 ISA tier (`-march=znver5`, features avx512f/vnni/bf16/vbmi, local host, no instance type), and port ONE op, Q8_0 mul_mat at verify widths N=1-16, as a definition + served-shape workloads + scalar reference + ggml-iqk baseline wrapper. | `autokernel-loop.md` (AK-CPU rows) | code first; one CPU row (single quarter, off q3) for the baseline geomean | Question: does a hidden-shape task reproduce the existing served-shape verdicts for C21 iqk? Stop when the baseline geomean vs the task's scalar reference is recorded with an A/A floor; futility if it reproduces the served-shape verdicts on that op (then do not port the other three). Estimate (own inference, unmeasured): a few engineer-days for the one-op pilot. |
| K2 | Refines kernelshift row 4: when row 4 runs, take `kgen/calibrate.py` semantics (per-workload baseline SQNR from the baseline kernel on real activations, candidate gated at baseline minus 1 dB) as the reference design and compare against the present in-row band for the same op. | `autokernel-loop.md` / SPEC-ID-GATE boxes | code/doc-only | Same stop rule as row 4: stop on the first op where the SQNR floor and the in-row band agree. |
| K3 | Refines kernelshift row 2 (control arm only): add the autovec control (scalar start compiled with the tier's `-march`) to the ISA ladder, as `kgen autovec` does for Arm. | `autokernel-loop.md` | code/doc-only | Same as simdbench M1; no new stop rule. |
| K4 | DECLINE: reuse the e2e llama.cpp override hook. Reason specific to this entry: it is a patch to llama.cpp v0.4.1 replacing only `mul_mat` and `rms_norm` through an Arm-only build and Graviton provisioning; our keeps go through source-level branches gated by the loop, and the hook would need a rewrite against C21 for no new information. | n/a | n/a | n/a |
| K5 | DECLINE: ingest the HF dataset l3lab/KernelShift or its Arm tasks. Reason: every task and expert baseline is Arm; it would not change K1-K3. | n/a | n/a | n/a |

## 7. Dive-surfaced sources
- HF dataset l3lab/KernelShift (TASKS.md, expected_sets.json): decline (K5). Intake index: `cmu-l3/kernel-shift` has 1 hit (the bearing entry's own note), the paper 2611.29590 is in the index.
- No other source changes a ledger row.

## 8. Contradiction / adversarial pass
- Repo is young (6 commits, 4 stars, 0 forks); no issues or independent users visible on the page.
- Task provenance: `loops/` and the generated definitions carry Arm's BSD license; license terms of the HF dataset are not stated on the repo page.
- The page claims "evolving CPU architectures" but only Arm tiers exist; x86 is not a stated roadmap item on the page (NOT-FOUND-IN-SOURCE).
- The bearing dive's paper-side caveat stands: speedup over a weak baseline is not fraction of ceiling.

## 9. read_depth
PARTIAL. Page (README) read in full; code read: `kgen/README.md`, `kgen/check.py`, `kgen/autovec.py`, `kgen/calibrate.py`, `kgen/capture.py` (docstring), `config/kernel_contracts.yaml` ISA table, `contracts.py`, `e2e/README.md`, `e2e/override/README.md`, grep of `bench/`, `eval/`, `mcp_app/`. Not read: `eval/` agent loop, `mcp_app/` server, `provisioning/`, `terraform/`, the HF dataset. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
