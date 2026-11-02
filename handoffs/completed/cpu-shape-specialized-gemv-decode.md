# CPU Shape-Specialized GEMV Microkernel for Zen 5 Decode


> **⚠ BRANCH RESCUE 2026-09-08 — the branches this handoff tells you to fork from were nearly lost.**
> `/mnt/raid0/llm/tmp/ak-loop-tree`, the `origin` remote of the CPU fusion tree, was deleted from
> scratch. **31 refs then existed nowhere on disk but one clone's object store**, referenced only by
> remote-tracking refs into that dead remote — one `git gc` from collection. Two of them are cited as
> live work *by this file*: **`cpu-optimization/q8-8x8-avx512bw`** (§ suggested first step, and the
> 4 commits on `138b26cd4` incl. the RMS_NORM intra-op reduction at `0467a5c17`, PPL 6.6767) and
> **`inf10-gemv-fusion` @ `ea8ca0609`** (build 10126, env-gated default OFF, correctness PASSED).
> Had they been collected, this handoff's own instructions would have been unfollowable.
>
> **Both are now on the GitHub fork** (`pestopoppa/llama.cpp`) as `rescued-cpu-opt-q8-8x8-avx512bw`
> and `rescued-inf10-gemv-fusion`, alongside 29 other rescued refs. Full object store bundled at
> `/mnt/raid0/llm/backups/inf70-refs/fusion-ALL-refs-20260908.bundle` (7,556 refs, verified).
> **Fetch from the fork, not from `origin`** — that remote no longer exists.
>
> ~~Whether either belongs in the consolidated champion is an open question for the operator, not a~~
> ~~given: both are old (`inf10-gemv-fusion` is build 10126 against a 10241 champion), so folding~~
> ~~either means a re-base and a re-measure at the current floor. The loss risk is closed; the~~
> ~~keep decision is not made.~~
>
> **CORRECTED 2026-09-08 (INF-70 audit) — the keep decision is NOT open; both branches are already
> answered from this file's own record.**
> - **`inf10-gemv-fusion` — MEASURED AND REFUTED 2026-08-27** (the two boxes in *THE LIVE LEVER*
>   below): gate+up −2.11%, qkv +0.25%, both −0.57%; correctness passed; 5×4 rotated, region-locked.
>   Mechanism: removing ~50 of ~590 barriers/token does not move wall-clock. The +2.6% precedent was
>   the DeltaNet NATIVE-fused cluster, not these arms.
> - **`cpu-optimization/q8-8x8-avx512bw` — the Q8 axis is CLOSED as architecture-bound** (§Session 15,
>   *CPU2 closes here for Q8 specifically*): the parallel RMS_NORM angle measured **−8.8%**, and the
>   SIMD ukernel plan below is a **closed appendix**, not a live plan.
>
> **A measured refutation is not a keep, and re-measuring a refuted lever is new research.** Neither
> branch is a fold candidate; either would have to be re-proposed as new research, under the operator
> directive that lever research is STOPPED until a fully consolidated champion exists. What the rescue
> bought is the *record* — the ability to inspect a refuted arm — not a pending keep. The loss risk is
> closed.

**Status**: **Phase 1 AVX-512BW 8x8 Q8_0 kernel LANDED + NUMA fix LANDED 2026-04-24 — production-viable without env vars.** Kernel correctly emits `vpmaddubsw`+`vpmaddwd` on Zen 5, +31.8% at 1 thread, +1-3% at 12-96 threads (Qwen3.6-27B Q8_0 caps at ~4.4 t/s). PPL preserved. NUMA first-touch of CPU_REPACK buffer was the dominant root cause of the initial 2.8× multi-thread regression — fixed by auto-mbind(MPOL_INTERLEAVE) inside the buffer allocator. **The 4.4 t/s ceiling is NOT memory-bandwidth — only 26% of theoretical 460 GB/s, vs Qwen2.5-Coder-32B dense at 41% on same hardware.** A DeltaNet parallelism refactor was probed and disproved (k_per_head ∈ {1,6,16} all give 4.43 t/s). Real bottleneck still unidentified — most likely barrier overhead × hybrid-architecture op count. Next investigation should be a `GGML_PERF=1` profile, not more kernel work. See §Session 15 below.
**Created**: 2026-04-23 (via session discussion of CPU fusion viability)
**Priority**: ~~MEDIUM~~ DEPRIORITIZED for the *SIMD ukernel*; **but the barrier/op-count sub-lever is RE-ELEVATED** by fable5-window2-findings-05 (2026-07-03): the roofline sweep confirms this handoff's own diagnosis (frontdoor Q8_0 decode is barrier/op-count-bound at 13.8% of 460 GB/s, not BW-bound; 45% of Q4_K decode cycles are libomp barrier at 96t). The **#2 cross-substrate kernel ROI** is **frontdoor Q8_0 operator/graph fusion to cut barrier COUNT** (fuse expert gate+up, fuse the attn QKV cluster) — est +10–15% decode, one cluster already measured +2.6%. Cheapest test: llama-bench tg128 frontdoor Q8_0, fusion flag on/off, same window. This is the fusion path, NOT more SIMD. See findings-05 §3/§6.
**Categories**: hardware_optimization, inference_serving, local_inference
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md)
**Related**:
- [`llama-cpp-kernel-push-rebase.md`](../completed/llama-cpp-kernel-push-rebase.md) — historical v4 kernel-push record (archived 2026-06-12)
- [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) — orthogonal throughput lever (KV-side)
- [`gpu-acceleration-path.md`](gpu-acceleration-path.md) — where TensileLite shape-specialization discussion originated
- [`llama-cpp-v3-upstream-rebuild.md`](../completed/llama-cpp-v3-upstream-rebuild.md) — paged attention / OpenMP repack / MoE expert reduction context
- [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) — where the CPU18 MegaBlocks indexing port (below) compounds

> **Fable 5 review (2026-06-12)**: E3 (the 8x8 GEMM SIMD body this file would land) is gated and owned by [batched-decode-measurement.md](batched-decode-measurement.md) — claim E3 there.

## ★ THE LIVE LEVER — frontdoor Q8_0 graph fusion (re-anchored 2026-08-11, A17)

**These two boxes are the whole live surface of this handoff.** The *Phased Work Plan*
is the deprioritized SIMD ukernel plan, a closed appendix now held in the archived history (see
*Completed Scope* below). The re-anchor is
the point: this file carried 38 open boxes of which 36 were the shelved SIMD plan, so the two tasks
that are actually live were invisible, and the handoff read as a large stale mass rather than a
small live one.

Diagnosis this rests on, from this file's own profiling and confirmed by
`fable5-window2-findings-05` (2026-07-03): frontdoor Q8_0 decode is **barrier/op-count-bound at
13.8% of 460 GB/s — not BW-bound**, and 45% of Q4_K decode cycles are libomp barrier at 96t. The
lever is therefore cutting barrier COUNT, **not more SIMD**.

- [x] **Fuse the expert gate+up operators (frontdoor Q8_0)** to cut barrier count. Est. +10–15%
  decode across the pair with the QKV fusion; one cluster already measured **+2.6%**. Cheapest
  test: `llama-bench tg128`, frontdoor Q8_0, fusion flag on/off, same window. **Needs an inference
  window — do not start without one.** ✅ 2026-08-27 — **REFUTED, null result**: both arms implemented
  (branch `inf10-gemv-fusion` @ `ea8ca0609`, build 10126, env-gated default OFF), correctness PASSED
  (PPL 5.5410 ± 0.53 identical 4/4 arms, 96-token greedy parity identical), but tg128 clean window
  (region-locked q0-q3, canonical env, 5×4 rotated): gateup **−2.11%**, qkv **+0.25%**, both **−0.57%**
  (verified window both −1.33%). **Magnitude annotation 2026-09-08 (MEAS-1/HARNESS-1)**: every one of
  those four numbers is **UNRESOLVED (below the 3.21% cold-harness A/A p95 floor)** — read −2.11% as
  "no measurable change", never as a 2% regression. The *refutation* is unaffected and stands: the
  arms were sized to detect the predicted +10–15%, and nothing of that size is present. Mechanism note: removing ~50 of ~590 barriers/token does not move
  wall-clock at tg128 (per-op barrier ≈1–2% of op time at Q8_0 op sizes; strided-view outputs offset
  the savings); the +2.6% precedent was the DeltaNet native-fused wqkv cluster, not these arms.
  Evidence: `epyc-inference-research/data/gemv-fusion-2026-08-25/` (summary + SHA256SUMS +
  correctness/README_correctness.md + raw llama-bench logs).
- [x] **Fuse the attention QKV cluster (frontdoor Q8_0)** to cut barrier count. Same measurement
  shape and the same window as the gate+up fusion; run them as one paired arm rather than two.
  ✅ 2026-08-27 — measured as the paired arm above; **neutral (+0.25% tg128 clean) — no gain**.
  Full-attention layers' separate wq/wk/wv were synthesized into a single wqkv projection
  (10 tensors, bit-identical by construction); Gated-DeltaNet layers already run native fused wqkv
  via `resolve_fused_ops`. No further barrier-fusion work is justified on this target; re-rank
  levers (e.g. `GGML_PERF=1` graph profile at tg128) with the receipts.

> **Certification coupling — read before closing anything.** The GEMV certification is
> high-severity and belongs to the **CPU-lane owner**, and it requires this re-anchor to land
> *before* the audit's 26 stale rows may close. **Do not close the 26 first**: closing them ahead of
> the re-anchor destroys the evidence that distinguishes the shelved plan from the live lever.
> Tracked as A17 in [`stale-open-audit-2026-07-18.md`](stale-open-audit-2026-07-18.md).

## Completed Scope

| Scope | Where it lives now |
|---|---|
| Live lever (gate+up and QKV fusion), both measured and refuted 2026-08-27 | this file, *★ THE LIVE LEVER* above |
| Sessions 15-18 (2026-04-24 → 04-27): AVX-512BW 8x8 Q8_0 kernel, NUMA mbind fix, 4.4 t/s ceiling analysis, Q6_K SIMD + prefetch | [archived history](../archived/cpu-shape-specialized-gemv-decode-history-through-2026-09-17.md) |
| Deprioritized SIMD ukernel plan (⛔ closed appendix, Phases 0-4, benchmark plan, risks) and its guarded Pickup Checklist | [archived history](../archived/cpu-shape-specialized-gemv-decode-history-through-2026-09-17.md) — reopen from its Phase 0 only if decode is shown BW-bound |

**What remains here:** no dispatchable task. This file is the receipts holder for the CPU GEMV axis;
live lever re-ranking is INF-70 (`cpu-decode-roofline-program.md`). The CPU18 and CPU26 candidates
below carry their own re-open triggers, and the 2026-05-08 intake block carries re-surface triggers.

## Phase 4 candidate (CPU18, added 2026-04-26 from research-intake batch)

**MegaBlocks blocked-CSR-COO + transpose-indices port for CPU MoE expert dispatch**

- Source: MegaBlocks paper (intake-467, arXiv:2211.15841, Stanford/MosaicML, MLSys 2023). Verdict: adopt_patterns.
- Transferable artifact: the **indexing scheme** (blocked-CSR-COO sparse encoding + transpose indices for sparse matmul in either orientation), NOT the GPU kernel itself.
- Why this matters on CPU: existing CPU2 8×8 Q8_0 kernel handles dense GEMV well, but MoE expert dispatch on CPU still relies on per-expert padding-or-drop logic inherited from upstream `mul_mat_id` path. MegaBlocks' "block-diagonal matrix with variable-sized blocks" formulation eliminates the capacity-factor padding/dropping tax at the dispatch layer.
- Compounds with: just-shipped CPU2 +31.8% (1t) / +1-3% (12-96t) Q8_0 8×8 wins, AND with CPU15 inter-process EP (intake-467 cross-references hipBLASLt grouped GEMM intake-305 and CUTLASS intake-465 / intake-424 as the GPU-side analogues we already track).
- Does NOT require BIOS reboot or env var. Pure software change inside `ggml/src/ggml-cpu/`.
- Open questions before starting: (1) does the indexing scheme map cleanly onto our existing 8×8 repack layout, or does it require a parallel repack format? (2) what's the per-token sync overhead of the indexing recompute on a 48-layer MoE? (3) does it interact with CPU15 drone+shard's expert-set partitioning?
- Suggested first step: read `ggml/src/ggml-cpu/repack.cpp` to find the `mul_mat_id` path, then prototype a blocked-CSR-COO routing index in `llama.cpp-experimental` on a fresh branch off `cpu-optimization/q8-8x8-avx512bw`. Validate on Qwen3.6-35B-A3B Q8_0 (already CPU15-EP-friendly) and gemma-26B-A4B (already CPU15-EP-friendly).
- Cross-reference: [`inference-research-index.md`](inference-research-index.md) (the merged CPU/GPU inference index).

### CPU18 design notes — added 2026-04-26 evening (post-CPU24 perf-record)

Code path located: `ggml/src/ggml-cpu/ggml-cpu.c:1774` `ggml_compute_forward_mul_mat_id`. The expert dispatch loop is in `ggml_compute_forward_mul_mat_id_one_chunk` at `:1703`. The current implementation processes per-(expert, token) pairs via a routing pass that builds `n_kept` per-expert token lists, then runs per-expert GEMV on each list.

**What MegaBlocks indexing replaces**: the per-expert padded GEMV calls. Currently each expert is processed as if it always has `capacity_factor × n_tokens / n_experts` rows; tokens beyond capacity are dropped or padded. MegaBlocks' blocked-CSR-COO encoding allows variable-sized expert blocks in a single "block-diagonal matrix with variable-sized blocks" formulation, avoiding both padding waste and drop loss.

**On the CPU side specifically**: capacity-factor padding/dropping is largely a non-issue for our regime because:
1. Single-user inference: typically 1 token/iteration, not large batches where capacity factor bites
2. CPU MoE workloads use top-K (K=8 typically) with `n_kept` = K × n_tokens, no capacity cap by default
3. Padding overhead only matters at large batch sizes which CPU rarely handles

**Realistic CPU18 ROI on our workload**:
- For single-token decode (the dominant path): each expert sees at most 1 token. Padding/drop logic isn't engaged. **Indexing change is a no-op.**
- For prefill (multi-token batches): indexing change could reduce wasted compute on padded slots. Estimated +2-5% on long prefills, but prefill is already 200-500 t/s which is rarely the bottleneck.

**Updated assessment (post-CPU24 perf-record)**: CPU24 attribution finding (compute kernels = 80% of cycles, sync = 15%) does NOT promote CPU18. The compute kernels are the GEMV inner loops, not expert-dispatch logic. CPU18 affects how many/which expert GEMVs run per token but doesn't make individual GEMV calls faster.

**Recommendation**: **DEPRIORITIZE CPU18 — for the current single-user-decode regime only**. This is an analysis-based deprioritization, NOT an empirical closure: no prototype was built, no microbenchmark of the indexing scheme was run on our codepath. The expected gain (≤5% on prefill only, ≤0% on decode) doesn't justify ~50-70 hours of engineering effort under current workload assumptions. Better leverage the same effort budget on:
- CPU2 Q6_K + Q5_K SIMD kernels (compounds CPU2 SIMD wins, addresses the actual 80% compute-cycle target)
- Per-thread BW-contention mitigations (the actual bottleneck per CPU24 perf-record)

**Re-open trigger** (workload-shift, not "exhausted"): if we shift to a workload pattern with large batched MoE inference (e.g., agent batch processing, eval pipelines, multi-tenant API, prefill-heavy pipelines), the capacity-factor padding/dropping cost becomes material and CPU18's blocked-CSR-COO + transpose indices become a real lever. For batched MoE/prefill/eval workloads the technique remains a live option that has not been tested or refuted on CPU. Track stays "deprioritized" not "closed".

## Phase 5 candidate (CPU26, added 2026-04-29 from PR #21149 audit)

**AVX-512BW Lightning Indexer kernel for `GGML_OP_LIGHTNING_INDEXER` on Zen 5**

- Source: [llama.cpp PR #21149](https://github.com/ggml-org/llama.cpp/pull/21149) by fairydreaming — DeepSeek V3.2 + DSA support. PR adds `GGML_OP_LIGHTNING_INDEXER` (FP8 head-weighted scoring with block-64 quantized key cache; per-query top-k=2048 token selection over MLA's compressed KV cache). Author commit (2026-04-28): "ggml : optimized GGML_OP_LIGHTNING_INDEXER (added WMMA kernel >= Ampere)" — CUDA path got Ampere WMMA optimization. CPU path is presumably scalar.
- Transferable artifact: the **AVX-512BW SIMD kernel** for the indexer's dot-product + top-k selection inner loop. Template from existing `gemv_q8_0_8x8_q8_0_avx512bw` in `arch/x86/repack.cpp` (Session 15 work).
- Why this matters on CPU: PR #21149's author explicitly flagged "long-context performance not yet improved" as the open issue; one of two suspects is the indexer overhead on non-CUDA backends. Our Zen 5 SIMD expertise (per `project_zen5_vnni_vs_maddubs` and `project_q8_8x8_avx512bw_outcome` memories — VPMADDUBSW 2/cycle beats VPDPBUSD 1/cycle on Zen 5) directly applies. **2-models-for-1 leverage**: any DSA infrastructure improvement helps GLM-5.1-555B-A14B on the same kernel path.
- Compounds with: just-shipped CPU2 +31.8% (1t) / +1-3% (12-96t) Q8_0 8x8 wins (same ZMM-level approach), AND with the auto-mbind(MPOL_INTERLEAVE) NUMA fix from Session 15 (Lightning Indexer's separate `llama_ik_cache` allocation will likely need the same NUMA-interleaving treatment per `feedback_repack_buffer_numa_mbind`).
- Does NOT require BIOS reboot or env var. Pure software change inside `ggml/src/ggml-cpu/arch/x86/`.
- Open questions before starting: (1) is `GGML_OP_LIGHTNING_INDEXER` compute-bound or BW-bound on CPU? Per `feedback_cpu_decode_bw_bound`, BW-bound work doesn't benefit from SIMD. **Profile-first gate is mandatory.** (2) does the indexer's per-block FP8 quantization map cleanly to AVX-512BW i8-pair multiplication (similar to Q8_0 8x8 kernel structure)? (3) does the existing token-generation sparse path benefit, or is the optimization only impactful in the (deferred) prompt-processing sparse path?
- Suggested first step: pull PR #21149 into `llama.cpp-experimental` as a feature branch (D1.2 in `llama-cpp-dsa-contribution.md`); profile current CPU `GGML_OP_LIGHTNING_INDEXER` with `perf record` on V3.2-Exp Q4_K_M (or any DSA-architecture model) to confirm whether SIMD optimization will move the needle. If compute-bound → write kernel; if BW-bound → redirect effort to D2 (prompt-processing sparse path follow-on).
- Strategic context: [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) D3 sub-track — full work-item list with explicit `[GATED on user inference approval]` markers per `feedback_no_concurrent_inference.md`.
- Cross-reference: [`inference-research-index.md`](inference-research-index.md) (the merged CPU/GPU inference index).

### Recommended ordering

CPU26 should go AFTER D1 (pull/build/smoke test) — we need to confirm V3.2 quality holds on CPU before optimizing the indexer kernel. Otherwise we're optimizing a broken path.

```
PR #21149 D1 (smoke test, ~1 day)
  ↓
CPU26.D3.1 (perf record profile, ~few hours)
  ↓ compute-bound?
  ├─ YES → CPU26.D3.2-D3.7 (SIMD kernel work, ~1 week)
  └─ NO  → redirect to D2 (prompt-processing sparse path, ~1-2 weeks upstream contribution)
```

## References

### Required reading before picking this up

1. [Justine Tunney, "LLaMA Now Goes Faster on CPUs" (justine.lol/matmul)](https://justine.lol/matmul/) — the primary-source reference for the Zen 4 result that motivates this.
2. [Gope et al., "Highly Optimized Kernels and Fine-Grained Codebooks for LLM Inference on Arm CPUs" (arXiv:2501.00032)](https://arxiv.org/abs/2501.00032) — the ARM KleidiAI paper; the most directly relevant technique.
3. Our own `research/deep-dives/dflash-dart-diffusion-speculation.md` — for context on what we've ruled out on the speculative-decoding side.

### Related handoffs

- [`llama-cpp-kernel-push-rebase.md`](../completed/llama-cpp-kernel-push-rebase.md) — historical v4 kernel-push record (archived 2026-06-12).
- [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) — orthogonal lever; composes with ukernel speedup.
- [`../completed/kv-cache-quantization.md`](../completed/kv-cache-quantization.md) — TurboQuant vs Hadamard result that shows fusion isn't automatically a win.
- [`gpu-acceleration-path.md`](gpu-acceleration-path.md) — TensileLite reference; cross-reference for shape-specialization context.

### Upstream code to inspect

- `llama.cpp/ggml/src/ggml-cpu/amx/mmq.cpp` — current VNNI templated GEMM, especially lines 2436–2463.
- `llama.cpp/ggml/src/ggml-cpu/ggml-cpu.c` — matmul dispatch.
- `llama.cpp/ggml/src/ggml-quants.c` — Q4_K_M and Q8_0 dequant reference.

### External libraries worth reading

- [llamafile tinyBLAS source](https://github.com/Mozilla-Ocho/llamafile) — specifically `llamafile/sgemm.cpp`.
- [KleidiAI source](https://github.com/ARM-software/kleidiai) — for the register-blocking patterns.
- [Intel oneDNN ukernel interface](https://github.com/oneapi-src/oneDNN/blob/master/src/cpu/gemm/gemm.hpp) — design reference.
- [Microsoft MLAS](https://github.com/microsoft/onnxruntime/tree/main/onnxruntime/core/mlas) — dispatch-table pattern reference.

### Hardware references

- [AMD EPYC 9655 specs / AVX-512 on Zen 5](https://www.amd.com/en/blogs/2025/unlocking-optimal-llm-performance-on-amd-epyc--cpus-with-vllm.html)
- [Phoronix EPYC Turin AVX-512 review](https://www.phoronix.com/review/amd-epyc-turin-avx512) — for the 512-bit datapath measurement.


## Research Intake Update — 2026-05-08

### New Related Research — Sakana "Sparser, Faster, Lighter" trio

Three URLs ingested as a single batch (paper + blog + repo, same research):

- **[intake-529] "Sparser, Faster, Lighter Transformer Language Models"** (arxiv:2603.23198, Sakana AI: Cetin / Peluchetti / Castillo / Naruse / Murakami / Llion Jones, March 2026)
  - Paper. Verdict `worth_investigating`, novelty medium, **relevance LOW** for our CPU path.
  - Key technique: training-time L1 regularization on FFN hidden activations → >95% activation sparsity at iso-quality, paired with a TwELL (Tile-wise ELLPACK) sparse storage format and custom H100 CUDA kernels avoiding dense hidden materialization.
  - Reported results: up to 30% inference speedup + 24% training speedup on H100, >24% peak GPU memory reduction, ~3% lower power draw. Models evaluated 0.5B / 1.5B / 2B.
  - Delta from current approach: Sakana's path is *training-induced static sparsity* (re-train with L1 → bake the sparsity pattern into weights), not runtime activation prediction (Deja Vu / PowerInfer / TEAL family flagged in intake-528). All shipped kernels are CUDA-only and Tensor Core / TMA aware — there is no AVX-512 / EPYC port.

- **[intake-530] "Sparser, Faster, Lighter LLMs" (Sakana AI publication blog)** (`pub.sakana.ai/sparser-faster-llms/`, 2026-Q2)
  - Blog. Verdict `worth_investigating`, novelty medium, **relevance MEDIUM**.
  - Contributes the transferable framing the paper omits: scaling 0.5B → 2B yielded 38% fewer non-zero activations at matched perplexity, supporting a "sparsity capacity grows with model size" hypothesis. This is direct counter-evidence to the NimbleEdge claim recorded in intake-528 that *modern* dense / small-MoE LLMs lose the activation-magnitude sparsity that OPT-class models enjoyed — but the counter-evidence is from a single training setup, single lab, and remains unreplicated.
  - Why it touches this handoff: re-opens the "sparse-FFN execution path on EPYC" question. If the scaling hypothesis holds, a future port of TwELL's tile-wise ELLPACK encoding to a CPU-side AVX-512BW masked-GEMV kernel becomes a coherent extension of CPU2 — but only after the GPU stack lands and the sparse-trained checkpoints prove out at scales that match a production draft or target.

- **[intake-531] github.com/SakanaAI/sparser-faster-llms** (MIT license, repo)
  - Repo. Verdict `worth_investigating`, novelty high, **relevance MEDIUM**, credibility 4.
  - Ships the implementation: TwELL packing + `twell-flex` (non-uniform sparsity variant), four pretrained sparse checkpoints (SparseLM-0.5B / 1B / 1.5B / 2B) on HuggingFace Hub, Hydra-driven training configs, a `benchmark_inference.py` harness comparing TwELL vs HF dense reference. CUDA 12.8+ and H100-tuned kernels; no CPU path, no llama.cpp / vLLM integration. README ships no benchmark numbers — the empirical anchor is the companion paper.
  - The novel piece for *our* stack is the static-sparse pretrained checkpoint format. If we ever entertain a SparseLM-2B port as a drafter (intake-530's scaling hypothesis is more credible at the smallest scales), we'd need: (a) HF → GGUF conversion for sparse weights, (b) a custom CPU sparse-FFN kernel in our llama.cpp fork, (c) a re-quant pass since SparseLM ships in BF16/FP16, not Q4_K_M.

### Why this is `worth_investigating`, not `new_opportunity`

- The production CPU2 / TQ3 / CPU18 / wdata-aware-MUL_MAT path already delivers measured wins on dense quantized GEMV. Unstructured-weight sparsity has historically lost to dense quantized GEMV on AVX-512 (per intake-528's verdict and CPU decode being DRAM-BW-bound, not weight-count-bound).
- Static training-induced sparsity requires *retraining*. None of the EPYC stack's models (Qwen3 30B-A3B, Coder-30B, Next-80B, REAP-246B) qualify, and we are not a pre-training shop.
- Per `feedback_closure_inflation`: this is a single-lab data point in a partially-explored design space, not a paradigm shift. Tracking, not action.

### Re-surface triggers (machine-readable)

1. Sakana releases an open-weight sparse-trained checkpoint that maps to a draft or target role.
2. llama.cpp lands a sparse-FFN execution path for any reason → TwELL becomes a candidate format for the repack/dispatcher layer.
3. dynamic-activation-sparsity (Deja Vu / PowerInfer / TEAL family) re-enters scope per intake-528's trigger #3 → re-evaluate the Sakana paper's iso-quality scaling claim against modern weights.
4. GPU hardware lands (`gpu-acceleration-path.md` activates) → SparseLM kernels become a candidate alongside vLLM + DDTree + Dflash.
5. We begin a from-scratch pre-training campaign where L1-sparsity regularization could be added at trivial cost.

### Cross-references in the handoff cluster

- [`moe-dynamic-expert-selection.md`](../completed/moe-dynamic-expert-selection.md), [`cpu-dynamic-moe-load-balancing.md`](../completed/cpu-dynamic-moe-load-balancing.md), [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) — adjacent (FFN-level sparsity vs expert-level routing; complementary not competing).
- [`gpu-acceleration-path.md`](gpu-acceleration-path.md) — primary parking lot if/when GPU hardware activates.
- [`llama-cpp-kernel-push-rebase.md`](../completed/llama-cpp-kernel-push-rebase.md) (archived 2026-06-12) — the v4 push pattern would be the template for integrating any CPU port of the TwELL format.
- intake-528 (Kolinko Effort Engine deep-dive, 2026-05-08) — same dynamic-sparsity neighborhood; the deep-dive's re-surface trigger (c) is the explicit mechanism for re-opening this entire family.

### Deep-Dive Addendum — 2026-05-08 (post-intake source-level audit)

A follow-up deep-dive (`research/deep-dives/sakana-sparser-faster-llms-deep-dive.md`) audited the actual paper, the TwELL CUDA source, and the SparseLM HF checkpoint configs. Six factual corrections and three new structural blockers surfaced — the initial intake was directionally right but glossed over major caveats. Highlights:

**Factual corrections to initial intake**:
1. **4 model scales, not 3**: 0.5B / 1B / 1.5B / 2B (added 1B). All dense gated-MLP, NOT MoE. Trained from scratch at Chinchilla-optimal token budgets (10B / 20B / 30B / 40B). 2 048-context only.
2. **Sparsity is DYNAMIC per-token, not static**: weights remain dense BF16; D2T repacks the post-ReLU hidden vector every forward pass. There is no static pruned weight matrix. This rules out one-time conversion of Qwen/Llama weights.
3. **Activation function is actual `nn.ReLU`** in `sparse_models.py`; the `hidden_act:"silu"` in `config.json` is a leftover overridden by `model_type: "llama_sparse_relu"`.
4. **Hopper-only (SM 90A)**, not just "CUDA" — kernels emit WGMMA m64n256k16, TMA cp.async.bulk.tensor.2d, thread-block cluster, mbarrier. A100 (sm_80), RTX 4090 (sm_89), MI300 — all out.
5. **Speedups are vs DENSE BF16**, never against Q4_K_M / Q8_0 / FP8. Headline +20.5% may not survive an apples-to-apples vs quantized dense.
6. **2B model shows +22.3% peak memory REGRESSION** in Table 1 (anomaly) — directly contradicts the blog's "memory reduction scales with size" framing.

**New structural blockers (compounding)**:
1. **MoE vs dense FFN**: production stack is MoE (Qwen3 30B-A3B, Coder, Next, REAP-246B); Sakana models are dense gated-MLP. TwELL skips post-ReLU zeros within a single FFN; MoE skips entire experts. The two compute-saving regimes do not orthogonal-stack on the same model — the paper does not demonstrate it.
2. **SwiGLU vs ReGLU**: production drafters/targets use SiLU/SwiGLU. Adopting forces retraining FFN as ReGLU (cost: full pretrain) or using SparseLM 2 048-context toy checkpoints. Draft-target compatibility is broken (SparseLM cannot be a drafter for any Qwen target — guaranteed logit drift).
3. **No quantized baseline**: Q4_K_M loads ~0.5 bytes/weight; sparse-BF16 at 99% sparsity is ~0.32 effective bytes/weight (with header+index overhead). Close — but Q4_K_M has the structured-load advantage (256-element super-blocks, contiguous reads), and indirect-addressed sparse loads break super-block alignment. Either duplicate the super-block scale per non-zero index (memory blow-up) or read full super-blocks anyway (no BW saving).

**Repo reality check**:
- 4 commits, all by single author Cetin (`Aladoro`); 1 open PR by Castillo (`emcastillo`) sitting unreviewed 7+ days at intake. Default branch is `master`, not `main`. No tests, no CI, no `setup.py`, no precompiled wheels. Empty HF model cards. Publication-drop, not maintained library.
- Repo MIT / HF weights Apache-2.0 — license mix. `OUT_DIM=2048` hardcoded in `matmul_t2d.cu` — kernel specialized to SparseLM hidden size.

**Revised assessment**:
- intake-529 (paper): novelty medium / **relevance LOW (confirmed)** / credibility 3 / verdict worth_investigating (narrowed to "design-reference-only").
- intake-530 (blog): novelty medium / relevance medium (caveats sharpened) / credibility 3 / verdict worth_investigating.
- intake-531 (repo): novelty high / relevance medium (caveats sharpened) / **credibility 3 (lowered from 4)** / verdict worth_investigating.

**Refined re-surface triggers** (replaces the simpler list above):
1. Finetune-from-existing-weights variant of the L1 recipe (paper's own future work).
2. **Combined sparse + INT4 / Q4_K kernel result vs Q4_K_M dense baseline** — the apples-to-apples for our stack.
3. **MoE variant of TwELL** — activation sparsity on top of expert sparsity could compound on Qwen3 30B-A3B.
4. Qwen-family or DeepSeek-family checkpoint released using this recipe (not Sakana's 0.5B-2B from-scratch toys).
5. CPU port by anyone (even slow reference impl) demonstrating BW savings under indirect-addressed gather on EPYC-class chip.
6. Internal pretraining-from-scratch campaign in our project (L1 regularization addition is trivial).
7. Sorted-bucket repack format lands in ggml for unrelated reason → trailing-skip / TwELL packing become reusable design references (shared with intake-528 trigger #1).

**Action**: no port handoff today. Track via this addendum + the deep-dive document. The TwELL bit-layout (16-bit idx + 16-bit BF16 + per-row NNZ header, 256-tile width) is filed as a CPU-port-design reference for any future ReLU-FFN training experiment.
