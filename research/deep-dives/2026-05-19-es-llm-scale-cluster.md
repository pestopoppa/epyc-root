# Evolution Strategies at LLM Scale Cluster — 2026-05-19

**Cluster**: Deep-dive #5 of 8 (research-intake Phase 6)
**Intakes in scope**: intake-532 (EGGROLL), intake-563 (ES-at-Scale), intake-564 (ESSA), intake-565 (Hoy 2026)
**Grandfathered prior**: intake-474 (Trinity, sep-CMA-ES on 10K-param routing head)
**Active handoffs touched**: `routing-and-optimization-index.md`, `learned-routing-controller.md`, `decision-aware-routing.md`, `outer-coordinator-learned-head.md`, `meta-harness-optimization.md`, `tri-role-coordinator-architecture.md`, `routing-intelligence.md`

---

## Executive Summary

The 2025-2026 ES-LLM literature has bifurcated along **two orthogonal compression axes**: EGGROLL compresses the **perturbation rank** (`ε = ε₂ε₁ᵀ`) to recover GPU batch-inference arithmetic intensity, while ESSA compresses both the **search space** (LoRA-SVD top-p% singular values) and the **evaluation precision** (INT4/INT8 forward passes via BitsAndBytes). ES-at-Scale stakes out a third axis: extreme **population-size minimization** (N=30) for billion-param NES with no structural compression. Hoy 2026 is the qualifying study — ES and GRPO match on train-task accuracy but produce ~90° orthogonal updates with 87–107× larger L2 norm, inducing measurable off-task KL drift (0.23 nats Math→BoolQ vs 0.01 for GRPO).

For EPYC (no GPU, 1.1 TB DDR5, 96C/192T, AVX-512BW Q8_0 kernel landed): **ESSA is the only paper in this cluster that is mechanically feasible on our current hardware today.** Its INT4/INT8 forward-pass-as-fitness loop maps directly onto the existing llama.cpp + Q4_K_M / Q8_0 GGUF stack. EGGROLL's int8 EGG architecture is interesting as a future RWKV-7 / nonlinear-recurrent training reference but its 1.05M-population JAX/H100 design is not portable. ES-at-Scale's pop=30 result is the relevant population-size lower bound for our budget. Trinity stays grandfathered because its frozen-backbone scope sidesteps Hoy 2026's off-task-drift mechanism entirely.

---

## Algorithmic Spectrum

| Method | Perturbation | Param space | Population | Optimizee precision | Compute target | Antithetic? |
|--------|-------------|-------------|-----------|---------------------|----------------|-------------|
| **EGGROLL** | rank-r structured: `ε = ε₂ε₁ᵀ`, ε₁,ε₂~N(0,Iₐ) | full network (fused update, NOT LoRA) | **2²⁰ = 1,048,576** | int8 weights + int32 accum (EGG); fp for RWKV-7 | H100, 91% of pure batch inference throughput, 10 Mtok/s on 1×H100 | not specified |
| **ES-at-Scale** | standard OpenAI-ES, ε~N(0,I), fixed σ | full network | **N=30** | fp16/bf16 | distributed GPU, "P parallel processes" within/across GPUs | **explicitly NOT used** |
| **ESSA** | **CMA-ES** (covariance-adapted), not plain NES | LoRA-SVD top-p% singular values (p=40% common) | **96 / 192 / 400 / 608**; sweet spot N=192 | **INT4 + INT8** via BitsAndBytes (fitness only) | 8–128 GPU sweep reported | not detailed |
| **Hoy 2026** | z-scored NES, ε~N(0,I), σ=0.0015, α=0.00075 | full network, Qwen3-4B-Instruct | **N=30** | fp (greedy decoding fitness) | small-scale comparative | implicit via z-scoring |

**Key non-uniformities to internalize**:
1. ESSA is **CMA-ES**, not OpenAI-ES — full covariance adaptation in the (small) LoRA-SVD subspace. Different convergence behaviour vs the fixed-σ NES in the other three papers.
2. EGGROLL's "rank-r" is **perturbation rank**, not **parameter rank** (no LoRA restriction). Each `ε₂ε₁ᵀ` is rank-r, but the sum is high-rank, so the effective search space is the full network.
3. ES-at-Scale explicitly **forgoes antithetic sampling** despite mentioning it as a common enhancement. This is unusual — antithetic pairs halve variance for free. Worth re-introducing in any port.
4. Hoy 2026's hyperparameters (σ=0.0015, α=0.00075) are tiny — consistent with the very large displacement they report (87–107× GRPO's L2 norm even at small step size).

---

## ESSA — The CPU-Native Spike Path

ESSA is the **only** paper in the cluster where the optimizee runs in **INT4 / INT8 during fitness evaluation**. This is the exact precision band our hand-written AVX-512BW Q8_0 kernel was built for (`project_q8_8x8_avx512bw_outcome`: +31.8% at 1t, +1–3% at 12–96t, BW-saturated). The paper's headline finding ("INT4 and INT8 slightly outperform BF16 in convergence speed and final precision") removes the precision-loss concern that would normally gate quantized training.

### Concrete EPYC translation

**Setup**:
- Optimizee: Qwen2.5-Math-7B Q4_K_M GGUF (matches paper's primary model; already in our stack)
- Adapter: LoRA rank 32 applied to attention QKV + MLP-down, SVD-decomposed, optimize top p=40% singular values → ~few×10⁵ trainable scalars
- Population: N=96 (paper's smallest tested value; sweet spot N=192 is too large for our forward-pass budget)
- CMA-ES (use `cma` Python package, not custom NES) over the singular-value vector
- Fitness oracle: GSM8K-test 200-sample subset (matches Hoy 2026 sample size), binary correct/incorrect via greedy decoding
- Iteration budget: capped at 200 generations (Hoy 2026 gate)

**EPYC compute path**:
- 96 evaluations / generation × greedy GSM8K answer (~200 output tokens / question × 1 question or batched 4)
- NUMA-concurrent split (`project_concurrent_split_throughput`: 32×6t aggregate +44–58%): run 16 concurrent llama-cli evaluations × 12 threads each. Per-process Q4_K_M Qwen-7B decode ~30–50 t/s at 12t (need verification — sweep is required).
- 200 output tokens × 200 questions / 50 t/s = 800 s per evaluation × ceil(96 / 16) = 6 parallel batches = 80 minutes / generation × 200 generations = **~11 days wall-clock on a single EPYC node**, in line with ESSA's 8-GPU 290-min figure scaled down.

**Verdict on feasibility**: tight but plausible **within one autopilot week**, IF we can amortize the per-generation cost by:
1. Caching LoRA-SVD weight reconstruction (avoid full GGUF rewrite per individual)
2. Using llama-server keep-alive instead of fresh llama-cli launches (saves model-load time per evaluation; currently 30-60 s per Qwen-7B load on cold cache)
3. Pre-tokenizing the 200-question GSM8K fixture once

**Per `feedback_no_concurrent_inference` and `feedback_speed_verify_via_llama_bench`**: every benchmark run including the per-generation forward passes requires user approval. The autopilot framing of this spike must therefore be **explicit per-generation gating** OR a **dedicated long-running session lock** that the user grants once. Surface this to the user before any spike begins.

**Success gate (matches intake-564 verdict_justification)**: GSM8K Δ > +2pp over Q4_K_M baseline with same LoRA adapter SFT-initialized, achieved in < 1 nightshift (12 hours) of dedicated compute.

### LoRA-SVD parameter-count estimation

For Qwen2.5-7B with LoRA rank 32 applied to standard target modules (q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj) across 28 layers:
- Per module per layer: 2 × hidden_dim × rank = 2 × 3584 × 32 = 229,376 scalars
- 7 modules × 28 layers × 229,376 = ~44.9M LoRA scalars total
- SVD-restrict to top p=40% singular values: each LoRA matrix A∈ℝ³⁵⁸⁴ˣ³² and B∈ℝ³²ˣ³⁵⁸⁴ has at most 32 singular values; top-40% = 12 SVs per (A or B) per module per layer = 12 × 2 × 7 × 28 = **~4,700 trainable singular values total**

This is the ESSA recipe applied to our optimizee: **CMA-ES over ~5K parameters**. CMA-ES covariance is O(d²) = ~25M entries — manageable in ~100 MB host RAM. Population 96 fits easily.

This sits **between** Trinity (10K params, sep-CMA-ES, frozen backbone, no off-task concern) and full ES-at-Scale (billions of params, OpenAI-NES, full off-task concern). At 5K params with **frozen backbone**, the off-task-drift mechanism Hoy 2026 identifies should be partially suppressed but not eliminated — measurement is required.

---

## The Trinity Question

Trinity (intake-474, Sakana sep-CMA-ES on a separate 10K-param routing head) is grandfathered active work. The new cluster reframes its position:

| Axis | Trinity | ESSA-on-router-head | ES-at-Scale style |
|------|---------|---------------------|-------------------|
| Backbone | frozen | frozen | trained |
| Trainable params | ~10K | ~5K (LoRA-SVD subset) | full billion-scale |
| ES variant | sep-CMA-ES | CMA-ES | NES (z-scored) |
| Hoy 2026 off-task gate applies? | **NO** (no backbone change) | partially (frozen backbone but additive adapter) | **YES, strictly** |
| Compute on EPYC | feasible today | feasible today (this cluster's spike) | infeasible without GPU |

**Trinity is NOT replaced** by EGGROLL/ES-at-Scale/ESSA. It occupies a distinct point: the smallest, simplest, most off-task-safe corner. The cluster **complements** Trinity by:
- (a) providing a documented escalation path if Trinity routing-head capacity proves insufficient (jump to ESSA-style LoRA-SVD on the router itself, then to LoRA-SVD on the drafter)
- (b) supplying the Hoy 2026 evaluation protocol that **retroactively validates** Trinity's update geometry (worth doing as a cheap audit even though the frozen-backbone setup likely passes trivially)
- (c) giving us a numerical reference point (ESSA N=192 sweet spot) for sizing the Trinity population if we ever increase its routing-head dimensionality

**Recommendation**: keep Trinity active under `project_learned_routing_controller`; do **not** absorb it into a unified ES handoff. Trinity's grandfathered status holds.

---

## Hoy 2026 as Mandatory Protocol

Hoy 2026 (Harvard Kempner / Miami) is the qualifying study. Its core empirical finding — ES updates are **near-orthogonal** to GRPO updates despite matching train-task accuracy, with **87–107× larger L2 norm** and **20× larger off-task KL drift** — translates into an evaluation protocol that every ES-LLM experiment in our stack must clear before deployment.

### The 4-gate protocol (now binding for `routing-and-optimization-index.md`)

1. **Train-task accuracy gate**: Δ accuracy on the ES training task ≥ +2pp over the SFT-initialized baseline. (Standard gate; necessary not sufficient.)

2. **Off-task KL gate**: KL(π_ES || π_baseline) measured on ≥1 held-out task distribution, must be ≤ 3× the equivalent GRPO measurement OR ≤ a calibrated absolute threshold (Hoy 2026 reports 0.23 nats for ES on Math→BoolQ — use 0.10 nats as our action threshold). Off-task probes for our stack: HumanEval (for coder spikes), IFEval (for general instruction following), MMLU subsection (for world knowledge). Probe must be ≥200 samples per distribution.

3. **Linear-mode-connectivity probe**: if a gradient-trained baseline (LoRA SFT or DPO) is available, interpolate θ_t = (1-t)·θ_SFT + t·θ_ES for t ∈ {0, 0.25, 0.5, 0.75, 1.0} and confirm no loss barrier. Hoy 2026 found ES and GRPO solutions linearly connected despite orthogonal trajectories — failure of LMC indicates pathological optimization, not just geometry difference.

4. **Iteration-budget control gate**: in any sequential / continual-learning setting (e.g., router being refined across multiple deployment phases), iteration budget per phase must be **fixed in advance** and an early-stop criterion (validation off-task accuracy plateau) must trigger before budget exhaustion. Hoy 2026 shows MMLU degradation of 3.7% under uncapped sequential ES vs +0.8% improvement for GRPO.

### Cheap retroactive audit

Trinity Phase 1 outputs (sep-CMA-ES on 10K-param routing head) can be gated retroactively under this protocol at near-zero cost — the trained head and frozen backbone produce deterministic π for the off-task KL measurement. **Spike proposal #1 below is exactly this audit.** It is the lowest-cost ES-cluster action available and validates whether the Trinity setup actually evades Hoy 2026's mechanism (expected: yes, because frozen backbone means π_ES − π_baseline lives entirely in the routing logits, not the policy distribution over generations).

### What the protocol catches

- An ESSA-style spike that ostensibly improves GSM8K but silently degrades HumanEval by 5pp: **gate 2 catches**
- A drafter-LoRA-SVD ES result that drifts into a different basin (different verifier-acceptance pattern) than the SFT-initialized starting point: **gate 3 catches**
- A multi-phase continual ES schedule that ratchets forward on each new domain but cumulatively forgets the original task: **gate 4 catches**

The protocol is **proportionate** — it costs roughly 1× the training compute for the off-task probes if reused across phases. Updates to `routing-and-optimization-index.md` should already reflect this; this deep-dive confirms the four gates are correctly specified and adds the explicit thresholds (0.10 nats action threshold, ≥200-sample probes, ≤3× GRPO ratio as alternative gate).

---

## EGGROLL and ES-at-Scale — Research References

### EGGROLL (intake-532)

**Position**: Cluster headline paper but NOT directly portable to EPYC. The rank-r perturbation trick `ε = ε₂ε₁ᵀ` recovers near-batch-inference arithmetic intensity on H100 (91% of pure batch throughput, 10 Mtok/s on 1×H100). On CPU, arithmetic intensity is **not** the bottleneck — memory bandwidth is (`feedback_cpu_decode_bw_bound`). The rank-r trick collapses to "compute many forward passes whose perturbations share factors", which on EPYC saves a fraction of the perturbation-application cost but does nothing for the dominant DRAM-fetch cost of weight loading.

**What is portable**:
- **The int8 EGG architecture** (D256-L6 character-level, all weights int8, int8×int8→int32 GEMM as the nonlinearity) is an interesting reference for any future CPU-native nonlinear-recurrent backbone. Our AVX-512BW Q8_0 kernel could likely host EGG inference at competitive speed. Not relevant to current routing/coordinator work; flag for `wiki/architectures/` once we have a fork to mention.
- **The 1.05M-population result** is a reference point on the upper end of what ES-LLM can absorb in sample count without diluting signal. Our pop=96 spike sits at the opposite extreme; ES-at-Scale's pop=30 anchors the lower extreme.

**Code**: HyperscaleES (JAX) at https://github.com/ESHyperscale/HyperscaleES; nano-egg (single-file int8) at https://github.com/ESHyperscale/nano-egg. License not stated in landing page; need to inspect repo. CC BY 4.0 on the paper itself.

**Action**: log as research reference in `wiki/research-references/es-at-scale.md` (create if absent). Do not adopt code; do not allocate spike budget. Re-evaluate if/when DGX Spark lands and JAX/H100 workflows become viable.

### ES-at-Scale (intake-563)

**Position**: Sample-side companion to EGGROLL — both achieve LLM-scale ES, but via opposite axes (population minimization vs perturbation compression). The **pop=30 result is the load-bearing reference for our budget**: it confirms that the ESSA spike's N=96 is comfortably above the empirical lower bound for billion-param ES on reasoning tasks. The fact that ES-at-Scale **does not use antithetic sampling** is a deliberate methodological choice and we should respect it in any port (introducing antithetic pairs would change the variance regime in ways the paper does not characterize).

**Code**: https://github.com/VsodicV/es-fine-tuning-paper. License not stated — inspect on first use.

**Action**: log as research reference. If/when we acquire any GPU, this is the canonical billion-param NES recipe to port first (simpler than EGGROLL, smaller-population than ESSA, no LoRA-SVD machinery). Add to `routing-and-optimization-index.md` under "deferred — GPU-required path".

### Why not run ES-at-Scale on EPYC

- 30 evaluations × full Qwen2.5-7B fp forward pass × Countdown task (~50 output tokens / problem × ~100 problems for stable fitness) = 30 × ~10 s per problem × 100 = 30,000 s per generation = 8.3 hours per generation × 200 generations = **70 days** wall-clock single-node. That is a non-starter even with NUMA-concurrent (best case ~2× speedup, still 35 days).
- The CPU-feasibility win in ESSA is **the INT4/INT8 forward pass**, not ES per se. Plain fp ES on EPYC at billion-param scale is infeasible regardless of population size.

---

## learned-routing-controller as the Primary Customer

The MLP routing classifier hit **92% val acc in Phase 1** (per `project_learned_routing_controller`). Phases 1.5–3 are pending. The natural failure mode that justifies an ES escalation:

- Phase 2+ adds harder routing decisions (multi-role disagreement cases, novel input distributions)
- Cross-entropy supervised training on labelled routing decisions plateaus at <95% accuracy
- Adding more labelled data fails to move the plateau (label noise floor or representation capacity hit)
- At that point, two routes are open:
  1. Increase MLP capacity (more layers, larger hidden dim) — increases backprop cost linearly, still bound by label quality
  2. **Switch to gradient-free ES on a LoRA-SVD-restricted adapter over the existing MLP** — uses end-to-end downstream reward (actual routing outcome quality measured by orchestrator success metric) as fitness, **bypasses the label-quality bottleneck entirely**

### Integration sketch

- Take the trained Phase 1 MLP (92% val acc) as θ_0
- Add a LoRA adapter (rank 8 — MLP is much smaller than an LLM) to the MLP's hidden-to-output projection
- SVD-restrict to top 8 singular values per adapter = ~10² trainable scalars total
- CMA-ES with N=48, σ adapted, fitness = orchestrator's existing routing-decision success rate on a held-out task batch
- 100-generation budget (much smaller than ESSA because parameter space is much smaller)
- **4-gate Hoy 2026 protocol mandatory**:
  - Gate 1: routing accuracy on training distribution ≥ +2pp over MLP baseline
  - Gate 2: routing accuracy on held-out task distribution within 1pp of baseline (off-task drift gate)
  - Gate 3: LMC interpolation between θ_0 and θ_ES, no accuracy barrier
  - Gate 4: iteration budget fixed at 100 generations, validation early-stop on plateau

**This is Spike #2 below.** It is the natural bridge between the Trinity-style small-head ES (which we already accept) and the ESSA-style drafter ES (which is the eventual goal but carries full Hoy 2026 risk).

### Why this works on EPYC

- 48 evaluations / generation × small-batch MLP forward + downstream routing call (no large-LLM forward needed if the routed-to LLMs are already warm in orchestrator)
- Per-evaluation cost dominated by the orchestrator's normal routing roundtrip (already measured in current production)
- No new infrastructure: reuses `learned-routing-controller` Phase 1 evaluation harness with the MLP θ swapped per evaluation

---

## Concrete Spike Proposals

Ordered cheapest → most expensive. Each spike must clear the prior spike's gates before the next is approved.

### Spike #1 — Pure Hoy 2026 protocol audit of existing Trinity output

- **Goal**: validate the 4-gate protocol works as specified on a known-good ES output (Trinity Phase 1)
- **Dev cost**: ~150 LOC (probe harness for routing-head off-task KL + LMC interpolation script)
- **Compute cost**: <30 minutes CPU-only (Trinity head is 10K params; no LLM retraining)
- **Success criterion**: all 4 gates execute without error and Trinity output passes gates 1+3 trivially, with measurable but small gate-2 drift (expected because frozen backbone)
- **Failure mode**: if Trinity FAILS gate 2 unexpectedly, the entire ES escalation pathway needs re-architecture before any further spike
- **User approval**: minimal — no large compute, no benchmark runs needed (uses cached Trinity outputs)
- **Owner**: assigned by `routing-and-optimization-index.md`

### Spike #2 — ESSA-style spike on the MLP router head

- **Prerequisite**: Spike #1 passes
- **Goal**: gradient-free ES training of the Phase 1 MLP routing classifier via LoRA-SVD; validate 4-gate protocol on a real (small-LLM-free) ES experiment
- **Dev cost**: ~500 LOC (CMA-ES driver using `cma` package, LoRA-SVD reconstruction, fitness harness wrapping orchestrator routing-success metric)
- **Compute cost**: ~50–100 CPU-hours (48 evaluations × 100 generations × per-eval routing roundtrip; per-eval cost dominated by existing orchestrator stack which is small but real)
- **Success criterion**: routing accuracy +2pp on hard cases that MLP-only training plateaued on, with all 4 Hoy gates green
- **Failure mode**: if gate 2 fails (off-task routing drift), we have learned that the LoRA-SVD-on-MLP recipe inherits the off-task mechanism — must reduce capacity or add explicit regularization
- **User approval**: per `feedback_no_concurrent_inference`, the per-evaluation orchestrator calls need user approval ONCE for the spike session; not per-evaluation
- **Estimated wall-clock**: 2–4 nightshifts

### Spike #3 — Full ESSA spike on a 1B drafter (q_scorer or candidate drafter)

- **Prerequisite**: Spike #2 passes
- **Goal**: validate that ESSA recipe transfers from MLP-scale to small-LLM-scale on EPYC with our INT8 / INT4 kernel
- **Dev cost**: ~1500 LOC (full ESSA implementation: BitsAndBytes-equivalent on llama.cpp side, LoRA-SVD-to-GGUF reconstruction, llama-server keep-alive fitness loop, NUMA-concurrent population split, Hoy 4-gate probe suite)
- **Compute cost**: ~7–14 nightshifts (96 evaluations × 200 generations × per-eval GSM8K decode on Q4_K_M Qwen-7B; see ESSA section above for arithmetic)
- **Success criterion**: target-model task accuracy +2pp under all 4 Hoy gates
- **Failure mode**: if convergence fails to materialize in 200 generations OR any Hoy gate fails, escalate to ES-at-Scale style full-NES (deferred until GPU available)
- **User approval**: dedicated multi-week session lock, explicit user opt-in per ESSA spike batch
- **Note**: this is the spike that fulfills intake-564's verdict_justification ("take a Qwen2.5-7B Q4_K_M GGUF, instantiate ~512-singular-value LoRA-SVD parameter space, run 200-iteration ES loop"). Our parameter count estimate above (~4,700 SVs) is slightly larger than intake-564's "~512" — the larger number is what falls out of standard LoRA targeting; we can shrink to 512 by restricting to attention-only modules.

---

## Open Questions

Per `feedback_no_concurrent_inference`, these are surfaced for explicit user decision before any spike is launched:

1. **Trinity retroactive audit (Spike #1)**: are we OK gating Trinity Phase 1 output retroactively under the Hoy 2026 4-gate protocol, given Trinity was originally accepted without these gates? Likelihood of failure is low (frozen backbone), but a failure would force re-architecture across all 7 active routing handoffs.

2. **NUMA-concurrent CPU split for ES population evaluation**: are we OK using the `project_concurrent_split_throughput` 16×12t configuration for Spike #3's population evaluation, given each population member triggers a llama-server warm-up phase (~few seconds) on first hit? Specifically, do we use llama-server keep-alive with batched population requests, or do we accept per-evaluation startup overhead?

3. **LoRA-SVD-to-GGUF reconstruction tooling**: ESSA assumes PyTorch + BitsAndBytes; our stack is llama.cpp + GGUF. Is it acceptable to write a custom LoRA-SVD-to-Q4_K_M reconstruction path in epyc-llama, or do we keep the spike CPU-fp16 (paying the bandwidth penalty) until GGUF tooling exists?

4. **Hoy 2026 off-task probe selection for routing context**: for `learned-routing-controller` Spike #2, what counts as the "off-task" distribution? Routing decisions are inherently task-specific, so the off-task gate may need redefinition in terms of "novel input modality" or "novel role mix" rather than literal held-out tasks. Want user direction on the probe design before spike begins.

5. **Spike ordering with concurrent active handoffs**: spikes #2 and #3 would run in time slots that overlap with autopilot, frontdoor decode optimization, and other ongoing work. Per `feedback_no_concurrent_inference` the ES spike's per-generation evaluation poisons concurrent benchmarks. Acceptable to gate the entire EPYC node to ES-only for the spike duration?

---

## References

### Cluster papers

- **EGGROLL** — Sarkar et al. 2025, Oxford / FLAIR / WHIRL / Mila / NVIDIA / NormaCore. arxiv:2511.16652. Code: https://github.com/ESHyperscale/HyperscaleES (JAX), https://github.com/ESHyperscale/nano-egg (int8 single-file). Paper license CC BY 4.0; code license unverified. Landing: https://eshyperscale.github.io/
- **ES-at-Scale** — Qiu, Gan, Hayes, Liang, Xu, Dailey, Meyerson, Hodjat, Miikkulainen 2025, Cognizant AI Lab / UT Austin. arxiv:2509.24372. Code: https://github.com/VsodicV/es-fine-tuning-paper. License unverified. Pop=30 NES on Qwen2.5 (0.5B–7B) and LLaMA3 (1B–8B); Countdown + conciseness benchmarks. No wall-clock vs baseline reported.
- **ESSA** — Korotyshova, Shaposhnikov, Malakhov, Khokhulin, Surnachev, Ovcharenko, Bredis, Gorbatovski, Sinii, Gavrilov 2025, T-Tech (T-Bank) / Yandex. arxiv:2507.04453. No code repo URL in paper; corresponding author b.shaposhnikov@tbank.ru. CMA-ES + LoRA rank 8–64 + SVD top-p% + BitsAndBytes INT4/INT8. Qwen2.5-Math-7B, LLaMA3.1-8B, Qwen2.5-32B on GSM8K + PRM800K. 8–128 GPU sweep, 290 min on 8 GPU, <80 min on 128 GPU.
- **Hoy 2026** — Hoy, Wang, Pan 2026, Harvard Kempner Institute / University of Miami. arxiv:2604.01499. Code: https://github.com/Bhoy1/ESvsGRPO. License unverified. Qwen3-4B-Instruct-2507; Countdown, Math, SciKnowEval-Chemistry, BoolQ + MMLU/IFEval holdouts. N=30, σ=0.0015, α=0.00075 z-scored NES vs no-KL GRPO. 87–107× L2 norm difference, 0.23 vs 0.01 nats off-task KL drift.

### Grandfathered prior (not in this cluster but referenced)

- **Trinity** — intake-474, Sakana AI. sep-CMA-ES on 10K-param routing head with frozen backbone. Maintained under `project_learned_routing_controller`. Out of Hoy 2026 off-task scope by virtue of frozen backbone.

### EPYC infrastructure references (memory)

- `project_q8_8x8_avx512bw_outcome` — AVX-512BW Q8_0 kernel: +31.8% at 1t, +1–3% at 12–96t (BW-saturated)
- `project_concurrent_split_throughput` — 4×48t → 32×6t NUMA-concurrent split, +44–58% aggregate
- `project_learned_routing_controller` — MLP routing classifier, 92% val acc Phase 1; phases 1.5–3 pending; flag-gated
- `project_dgx_spark_target` — DGX Spark NOT acquired; GPU-only ES paths deferred
- `feedback_no_concurrent_inference` — per-bench user approval mandatory
- `feedback_speed_verify_via_llama_bench` — NEVER auto-run run_benchmark.py; user runs all benchmarks
- `feedback_cpu_decode_bw_bound` — CPU decode is BW-bound on EPYC 9655; arithmetic-intensity tricks (EGGROLL's primary contribution) do not transfer

### Active handoffs touched by this cluster

- `handoffs/active/routing-and-optimization-index.md` (already updated with ES protocol per intake-565 verdict)
- `handoffs/active/learned-routing-controller.md` (already updated, Phase 1 done)
- `handoffs/active/decision-aware-routing.md`
- `handoffs/active/outer-coordinator-learned-head.md`
- `handoffs/active/meta-harness-optimization.md`
- `handoffs/active/tri-role-coordinator-architecture.md`
- `handoffs/active/routing-intelligence.md`

### Sibling deep-dives in same Phase 6 batch

- Cluster #1–4, #6–8 deep-dives in `/workspace/research/deep-dives/` (to be cross-referenced once all 8 land)
