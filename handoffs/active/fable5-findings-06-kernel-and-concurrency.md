# Fable 5 findings 06 — The kernel program & concurrent serving: what is exhausted, what was avoided

**Date**: 2026-06-12 (refinement pass; operator questions: *"none of your findings discuss the epyc-inference-research kernel work — was everything found exhausted, or is there another angle?"* and *"review the infrastructure used to execute inference concurrently — have I been unnecessarily avoiding obvious performance improvement pipelines?"*)
**Evidence**: dedicated kernel-program sweep (roofline findings.md read in full; fork source verified; all handoff gates re-read) + the earlier serving sweep; citations inline.

---

## 1. Verdict on the kernel program: batch=1 decode is genuinely exhausted — and it was closed *properly*. The program as a whole is not exhausted; it has five live angles, and the biggest one is a measurement you never ran.

First, credit where due: the closure discipline is excellent. The 2026-04-26 canonical re-measurement that collapsed apparent wins to noise, the CPU25 NUMA-mirror falsification, the roofline audit's three-times-corrected mechanism story, and the closure-inflation remediation are *better* metrology than most industrial perf teams practice. Nothing in this review found a batch=1 GEMV/sync/NUMA lever that was wrongly closed.

The decisive physics (roofline `findings.md:33-76,140-141`): decode achieves **0.03–0.35% of theoretical FLOPS** while the per-token bandwidth cross-check agrees with measured throughput to 93% — the machine is *simultaneously compute-idle and per-thread-BW-saturated*, and the gap to the 460 GB/s aggregate is structural per-thread channel share (the "2–4× BW headroom" framing was falsified three times; not recoverable by code). Conclusion: no kernel that streams the same bytes faster can win. **Three lever families survive that physics**, plus one shipped-but-stranded win, plus one untested regime:

### 1.1 Convert idle compute into fewer weight passes (the roofline audit's own promotion)
**Variant B — TiDAR-pattern one-pass draft+verify** (single forward with unified causal+bidirectional mask → drafts and verifies in one weight scan, ~halving per-cycle weight traffic; `nemotron-labs-diffusion-tri-mode.md:469-509`): 99.7% idle FLOPS is exactly the budget this spends; estimated 1.3–2× algorithmic; 5–10 days of ggml-op work (FlexAttention-equivalent mask); the open gate is a Q4-quantizable TiDAR-class checkpoint for quality validation. This is the highest-ceiling, highest-variance kernel work remaining, and it is *your own audit's* stated next step — it should be in the priority queue, not buried in a deep-dive's §10.6.

### 1.2 Reduce bytes per weight (the only lever that rescales the t/s equation)
**Low-bpw/ternary track** (STQ1_0 1.25-bit; Sherry QAT): strategically correct in a BW-bound regime — your own precedent is Q4_K_M +52% over Q8_0 with zero code change — but shallowly developed and **externally gated**: llama.cpp PR #22836 unmerged, no STQ1 symbols in the fork (verified by grep), Sherry is QAT so no stack-relevant base >1.8B has weights. Posture: **watch, don't build** — with one cheap in-control action: canonical-bench the on-disk 1.8B STQ1_0 artifact when #22836 merges to validate the ~1.5× decode claim on this host. Also keep CPU10-style per-model IQ3/IQ2 quality-floor sweeps in the toolbox — same lever, available today, model-by-model.

### 1.3 Skip bytes entirely (sparsity)
**DSA / Lightning Indexer (D1/D2/D3)**: fully specified, profile-gated, flagged "LOWEST-HANGING FRUIT" at the top of your own CPU index — and **zero work items executed** (every row PENDING on inference approval; no CPU datapoint of PR #21149 exists anywhere). ~1 day to the first smoke datapoint; D2 (prompt-processing sparse path) is also the only matching lever for the measured O(N²) long-context prefill cliff (Coder −70% at 32K), for which **no prefill roofline has ever been measured**. **MoE-Spec expert budgeting** is the same family's shipped cousin — see 1.4.

### 1.4 The shipped-but-stranded win — and the reconciliation the handoffs need
MoE-Spec B=40 measured **+13.5–15.2% verification / +3% e2e** with its pre-production gate RELEASED 2026-04-29 — but the model it was proven on (REAP-246B) has since left the stack, and Coder B=64 failed robustness. So "ship MoE-Spec" is **not** an action today; the honest state is: *a proven mechanism with no live consumer, because its consumer is speculative-decoding verification batches and the only spec-dec in production runs on a different binary (gemma4/ik) while frontdoor runs none.* This chains directly to findings-03 G1: **enable frontdoor spec-dec → measure α → B-sweep MoE-Spec on the frontdoor A3B's verification batches**. Three findings docs converge on the same first domino.

### 1.5 The untested regime — batched decode (this is also the answer to your concurrency question)

## 2. Concurrent-inference infrastructure: what you built is good; what you never measured is the gap

**What exists and works** (verified live): NUMA quarter-splits (6–7× aggregate ≤65GB), the placement state machine + per-region locks + cross-role disjoint placement + reverse migration (all env-ON), the measured contention matrix with admission gating, session→quarter affinity with transactional KV migration, same-GGUF process consolidation. As *multi-instance* concurrency, this is mature — and it is the right safety layer.

**What was avoided — three specific affirmatives to your question:**

1. **Single-instance batched decode has never been measured.** CPU14 (the `-np N` slot-decode bench suite) was **never run** ("Reopen when Tier 2 un-defers", index:374). CPU23 explicitly deferred multi-stream decode interference ("not measured… Deferred unless multi-tenant production becomes relevant"). Meanwhile heavy roles run `-np 1/2` under an exclusive cross-process lock, and the fork's continuous batching (`cont_batching=true` default) is structurally unexploited. The closures were *conditional on a single-user workload* — and per findings-02/03, your dominant workload is now the eval/optimization harness: **4.6 h/day of T1 evals + 1.3 h/day T0**, 43 independent questions per trial, currently fanned out at concurrency 3 *across instances*. Your own closure notes name the reopen trigger: CPU18's reads "agent batch processing, **eval pipelines**, multi-tenant API" — the trigger has been satisfied for weeks by your own autopilot; nobody connected the dots.
2. **The batched kernel literally does not exist.** The shipped 8x8 AVX-512BW work covers only GEMV (M=1); `ggml_gemm_q8_0_8x8_q8_0` — the batch>1 path — **falls back to generic scalar** (`arch/x86/repack.cpp:1563-1566`, verified this session). The +31.8%@1t / +1–3%@96t result is the mechanism proof that the kernel wins wherever per-thread DRAM isn't saturated; batch>1 raises compute-per-byte exactly the way 1t did (MoE-Spec's own pp32 batches: **321–402 t/s vs ~47 t/s single-stream** on Coder-30B = ~7–8× arithmetic-intensity rise). So "would AVX-512 pay at batch>1" is not merely unmeasured — the SIMD body was never written, because batch=1 was the only regime that counted.
3. **Frontdoor speculative decoding was never enabled** (findings-03 §1.1) — the single largest unharvested config item, and the unlock for 1.4.

**Cautions against over-claiming**: A3B-MoE batching is weaker than dense batching (distinct tokens hit distinct experts → expert weight traffic grows with batch; the gemma4 MTP "MoE batch=1 cancellation" is the same physics from the other side). The 9.6× rep-1 TTFT amplification under concurrent prefill on sync-bound MoE (CPU23) is real and is what CPU17/Sarathi chunked-prefill exists to fix. So the expected value is genuinely *unknown* — which is the point: this is an evidence vacuum sitting under your highest-volume workload.

**The decisive experiment (cheap, bench-only, operator-approved per `feedback_no_concurrent_inference`):**
- **E1 — CPU14 at last**: one instance, `-np {1,2,4,8,16}`, fixed question batch, measure aggregate solved-tasks/hour (the findings-05 objective) + per-stream latency, on (a) frontdoor Qwen3.6-A3B and (b) a dense control. Half a day.
- **E2 — eval-driver A/B**: run one T1 eval (43 questions) against a single full instance with `-np 8` continuous batching vs the current 3-concurrent-across-quarters path. Directly prices "batch serving class for the autopilot" in wall-minutes per eval — which, per findings-01, is *statistical power per day*.
- **E3 — if E1 shows intermediate-batch decode leaves per-thread-BW saturation**: write the 8x8 GEMM SIMD body (the dispatcher slot already exists) and re-run E1 — the first genuinely new kernel work justified since the wall was declared.
- Then, conditionally: CPU17 chunked-prefill re-promotion (its 9.6× TTFT pathology is the eval class's pathology) and CPU18 MegaBlocks (explicit "eval pipelines" trigger).

**Priority-inversion note**: the contention gate currently classes autopilot traffic as background (always queues on unknown/bad pairs). Under the workload model (findings-04 §D) where eval-batch is a first-class traffic class with its own serving instances, that conservatism can be kept for interactive protection while the batch class gets dedicated capacity — the placement machinery you already built supports exactly this split.

## 3. Ranked answer to "what remains" (one table)

| Rank | Angle | Cost | Gate | Expected value |
|---|---|---|---|---|
| 1 | Frontdoor spec-dec ON + α (G1) | hours | operator window | unlocks 1.4 + findings-03 fork; possibly 1.3–2× hottest path |
| 2 | E1/E2 batched-decode measurement (CPU14 + eval A/B) | ~1 day bench | operator window | prices the batch serving class; gates E3/CPU17/CPU18 |
| 3 | DSA D1 smoke → D3.1 profile | ~1 day | inference approval | first CPU datapoint; unlocks V3.2/GLM-5.1 on 1.1TB; D2 = the long-context prefill lever |
| 4 | Variant B TiDAR one-pass ggml work | 5–10 days | Q4-able checkpoint exists | 1.3–2× ceiling from idle FLOPS; highest variance |
| 5 | 8x8 GEMM SIMD body | ~days | E1 shows unsaturated intermediate batch | second life for the proven +31.8% mechanism |
| 6 | Low-bpw/ternary | bench-only now | PR #22836 merge + weights ecosystem | watch; largest long-run t/s rescale |
| — | Batch=1 GEMV/sync/NUMA micro-opt | — | **closed, correctly; do not reopen** | — |
