# 2b-A — QuixiAI/llama.cpp + QuixiFlow

## HEADLINE: from the two ASSIGNED repos, essentially NOTHING. But the dive found the real thing next door.

## QuixiAI/llama.cpp = A ZERO-DELTA MIRROR. Not one line of its own.
GET /repos/ggml-org/llama.cpp/compare/master...QuixiAI:llama.cpp:master ->
  **status=behind, ahead_by=0, behind_by=108, total_commits=0, files changed=0**
merge_base = 8bb909374d04... = **IDENTICAL TO THE FORK'S OWN HEAD.** A fork whose merge-base equals
its tip has contributed zero commits. Branches: master only. Tags: none. Commits by ehartford: **0**.
All 20 most recent commits are UPSTREAM commits by upstream authors. Created 2026-07-25, last push
2026-07-26, 0 stars, 0 forks — **a snapshot taken and abandoned within ~26 hours.**

### CORRECTION TO MY OWN BRIEF
I called it "a fork of OUR PRODUCTION KERNEL". **It is not.** It is a SIBLING fork off ggml-org.
67a433bf4 (our v8 freeze) -> 8bb909374d (their fork point): status=diverged, ahead_by=86, behind_by=62,
merge_base a8dc0e3269a5 (2026-07-16). Both descend from upstream, diverging ~10 days apart.
No relationship beyond common ancestry.

## QuixiFlow — main is ALSO zero-delta; all content in 3 stale branches
main: ahead_by=0, behind_by=329, merge_base == its own HEAD. Three branches, ALL **6518 commits behind
main**, all merge-basing at cc410e864480 (2026-01-02, ~7 months stale), all by Eric Hartford, **never
merged even to the fork's own main.**

### `rocm-fp8-marlin` — THE FLAGSHIP BRANCH IS PROVABLY NON-BUILDING
- CMakeLists.txt:9-10 appends `csrc/quantization/fp8/gptq_marlin_repack_hip.cu` and
  `csrc/quantization/fp8/fp8_marlin_hip.cu` to VLLM_EXT_SRC. **BOTH RETURN HTTP 404 at that ref** —
  as does the entire csrc/quantization/fp8/ directory (upstream vLLM keeps FP8 under csrc/quantization/w8a8/).
  All three files named in the design doc's "File Layout" are ABSENT.
- csrc/torch_bindings.cpp:46 does ops.impl("fp8_marlin_gemm", torch::kCUDA, &fp8_marlin_gemm) against a
  symbol declared in csrc/ops.h:23-26 but **never defined anywhere** -> link failure even if CMake got
  that far. Lines 49-51 ops.def(...) with NO matching ops.impl.
- So ~150 lines of Python dispatch route to a kernel **that was never written**. A design doc plus
  plumbing, with the interesting half missing.
- Code-quality signal: marlin_utils_fp8.py:336 gates on `any(gfx in gcn_arch for gfx in ["gfx90",...])`
  — the bare prefix "gfx90" ALSO MATCHES gfx900/gfx906/gfx90c (Vega-era), which have no MFMA at all.

### `rocm-flash-attn` — real and working, but ZERO KERNEL CODE
An adaptation layer letting vLLM's FLASH_ATTN backend be selected on ROCm by wrapping the EXTERNAL
flash_attn package. fa_utils.py:225-308 is a shim dropping CUDA-only args and forwarding. Bulk of the
869-line diff threads a new cu_seqlens_k field through CommonAttentionMetadata because ROCm flash-attn
needs cumulative KV seqlens where CUDA vLLM uses seqused_k. rocm.py:356-366 inserts FLASH_ATTN BELOW
AITER in priority.
Honest self-documented defects: tree-attn correctness SKIPPED on ROCm — "ROCm FlashAttention has known
BF16 numerical divergence vs tree attention"; FlashAttention-MLA remains CUDA-only.
No arch gating, so it WOULD engage on gfx90a — but it delivers no new kernel, only backend SELECTION.

## NO BENCHMARKS ANYWHERE (exhaustive, not sampled)
Complete changed-file lists for all three branches (13 and 11 files) contain **no benchmark, no results
file, no perf number.** README on main is byte-identical upstream. The design doc DEFERS measurement:
"Kernel perf smoke tests using vLLM benchmarks on CDNA1/2/3" — future tense, never done.
Neither repo explains why llama.cpp is slower than vLLM. Only indirect AMD/NVIDIA content is a
FLEET-LONGEVITY argument (rocm_marlin_fp8.md:66-69): FP8 "must not be limited to the newest AMD parts...
with mandatory emulation for older fleets so they remain useful for inference workloads."

## CHERRY-PICKABLE: NOTHING.
The ONE transferable IDEA (not a patch): the rocm-flash-attn POSTURE — when AITER is unavailable or has
dropped your arch, route to a GENERIC ROCm flash-attn rather than a vendor-optimized path. Given AITER's
CDNA2 drop that is a strategically relevant fallback SHAPE for gfx90a. Costs nothing to note; not worth
a cherry-pick.

## 🔑 THE REAL FIND, NEXT DOOR: QuixiAI/QuixiCore-ROCm
A **77-COMMITS-AHEAD fork of HazyResearch/HipKittens**, 300 files, with REAL measured kernel work:
  "elementwise: land 64-lane wavefront widening for norm/row kernels (+30-71%)"
  "attention: MFMA-tile the GQA forward flash kernel (13-16x over naive)"
  "qgemm: wide N-tile X-reuse kernel, occupancy-picked (+47-54% at M>=256)"
Measured on **MI300X gfx942 / ROCm 7.2.4 — NOT our arch, NOT our ROCm.**
**AND IT HAS AN EXPLICIT ACCEPT/REJECT DISCIPLINE IN THE COMMIT LOG** — commits record REJECTED
experiments: "reject LDS-B experiment (inconsistent across shapes)", "reject (CU contention)".
**Methodologically close to our own measurement constitution** — this is the single most interesting
thing the dive produced.
CDNA2 SUPPORT: **OVERTURNED.** .quixicore/backend.yaml DECLARES targets [cdna2, cdna3, cdna4], but the
1759-path tree has **ZERO paths matching cdna2/gfx90a/gfx908** (cdna3: 583, cdna4: 347). Its own README
states flatly "We support CDNA3 and CDNA 4." **DECLARED != IMPLEMENTED.**

## A ROOFLINE CROSS-CHECK THE AGENT CORRECTLY REFUSED
perf/results/2026-08-02/mxfp4-gguf/bench.txt reports mxfp4_gemv_q8_1 4096x4096: 0.0050 ms,
**1792.8 GB/s (weight-bound)** on MI300X/ROCm 7.2.4. Tempting to compare against our Q4_K 34% rung.
**UNSAFE**: the ~8.9 MB weight working set FITS MI300X's 256 MB Infinity Cache, so the figure is NOT
HBM-limited and the "% of peak" framing does not apply. Different arch, quant and ROCm. DO NOT enter
as a rung.

## THIRD INDEPENDENT CONFIRMATION OF CDNA2 ECOSYSTEM ABANDONMENT
AITER dropped CDNA2; HipKittens never supported it; QuixiCore-ROCm declares cdna2 in metadata and ships
zero cdna2 code. **Every modern AMD kernel library targets gfx942+ only. gfx90a optimization is
unavoidably IN-HOUSE.** The agent flags this as a STRATEGIC INPUT TO THE AUTOKERNEL GO/NO-GO and
arguably the most decision-relevant thing in the dive.

## NEW INDEX ENTRY PROPOSALS
1. QuixiAI/llama.cpp — novelty none, relevance none, credibility null, verdict **not_applicable**.
   Index ONLY AS A TOMBSTONE so no future dive re-fetches it.
2. QuixiAI/QuixiFlow — novelty low, relevance low, credibility 2, verdict **not_applicable**.
   (2 because the FA branch is genuine tested code with honest defect annotations, while the flagship
   Marlin branch is a design doc whose CMake references 404 files.)
3. QuixiAI/QuixiCore-ROCm — novelty high, relevance high(method)/none(our silicon), credibility 5,
   verdict **worth_investigating**. Peer-reviewed MLSys 2026 upstream + landed in AITER = independent
   third-party validation, not self-report.

## LEDGER: 3 drafts, 4 declines
1 extract the 8-wave ping-pong / 4-wave interleave schedules for gfx90a portability ->
  mi210-kernel-rnd-loop-proposal.md (note CDNA2 has 4 MFMA-capable SIMDs/CU and no CDNA3 async-copy —
  establish whether the schedule SURVIVES THE PORT before committing kernel effort)
2 record the CDNA2 ECOSYSTEM-ABANDONMENT datapoint -> mi210-kernel-rnd-loop-proposal.md, weighed
  against ACQUIRING CDNA3 SILICON before funding a long CDNA2 kernel program
3 read arXiv 2511.08083 as primary autokernel methodology input -> inference-acceleration-index.md
DECLINE 4 the AITER-fallback pattern (vLLM backend-selection concern; our path is llama.cpp)
DECLINE 5 cherry-pick ROCm FP8 Marlin emulation (kernel does not exist; and the CONCEPT — decode FP8 to
  FP16 in registers, fuse scale during decode, MFMA with FP32 accumulate — is EXACTLY what our existing
  MMQ/dequant path already does for K-quants, so there is no new idea either)
DECLINE 6 evaluate vLLM-via-QuixiFlow on MI210 (QuixiFlow offers nothing over stock vLLM; a
  stock-vLLM-on-gfx90a number is a NEW MEASUREMENT TASK, not an intake item)
DECLINE 7 use QuixiCore-ROCm MI300X numbers as a roofline cross-check (cache-resident, see above)

## FURTHER SOURCES SURFACED
- **github.com/QuixiAI/QuixiCore-ROCm** — HIGHEST VALUE. 77 commits of real CDNA3/4 MFMA work with
  quantified per-kernel gains AND an explicit A/B accept/reject discipline. Would settle what a
  disciplined from-scratch AMD kernel program looks like, and the true cost of a CDNA3->CDNA2 port.
- arxiv.org/abs/2511.08083 HipKittens (MLSys 2026) — the primary peer-reviewed source on WHICH CUDA
  primitives transfer to AMD and which must be redesigned. Directly answers the operator's question at
  the primitive level.
- github.com/ROCm/aiter/pull/2039 — would show exactly which ARCH GATES were applied, i.e. whether
  CDNA2 exclusion is a POLICY CHOICE or a HARDWARE CONSTRAINT.
- hazyresearch.stanford.edu/blog/2025-11-09-amd-brr and /2025-11-09-hk — the narrative AMD-vs-NVIDIA
  efficiency argument, likely with head-to-head MI355X-vs-B200 numbers.
- **github.com/QuixiAI/QuixiCore matrices/capability-map.md — a 263-OPERATION SEMANTIC UNION + 17
  QUANT-FORMAT IDs across six backends. A ready-made kernel-coverage taxonomy; could serve as a
  CHECKLIST FOR WHAT AN AUTOKERNEL STACK MUST IMPLEMENT.**
- github.com/QuixiAI/QuixiCore-CPU — non-fork, C++, actively pushed. Our CPU decode is bandwidth-bound
  on EPYC; worth checking for AVX-512/Zen5 work bearing on our repack/quant kernels.
- github.com/QuixiAI/SlimServe (pushed 2026-08-02, the org's newest) — where this team's serving effort
  actually went after abandoning both assigned forks.

PROCESS: api.github.com and raw.githubusercontent.com only. Nothing cloned, nothing built,
/mnt/raid0/llm/llama.cpp never accessed — the ancestry question was answered via GitHub's compare API.
