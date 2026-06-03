# ROCm Verify/Profile/Benchmark Backend for MI210 Kernel Authoring

**Status**: SKELETON — design scaffold, expect significant refinement before implementation
**Created**: 2026-06-03 (via /research-intake deep-dive; spun out as the long-pole item 3)
**Categories**: hardware_optimization, benchmark_methodology, tool_implementation, inference_serving
**Hardware gate**: AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB), expected ~July 2026. Phase 0 can be scoped on paper now; nothing executes until the card is racked + ROCm/torch-ROCm stood up.
**Priority**: MEDIUM (this is the prerequisite long pole for [`agentic-rocm-kernel-authoring.md`](agentic-rocm-kernel-authoring.md))
**Workstream**: Inference Acceleration / GPU
**Parent**: [`agentic-rocm-kernel-authoring.md`](agentic-rocm-kernel-authoring.md)
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)

> **This is a skeleton.** It captures the component decomposition, a phased plan, and an interface contract so we have something concrete to build on. Numbers, tool versions, metric subsets, and the exact benchmark fork strategy WILL be revised once the MI210 + ROCm stack are live and we can measure. Do not treat any value here as load-bearing yet.

---

## Objective

Provide the **hardware-agnostic-on-the-outside, ROCm-specific-on-the-inside** evaluation backend that the agentic kernel-authoring loop calls: given a candidate HIP kernel + a PyTorch reference, return `(compiles?, correct?, speedup, profiler_metrics)`. This is the reward/feedback substrate. It is deliberately factored out from the controller (model + search strategy) so the controller can be swapped (EvoEngineer-style evolutionary vs CudaForge-style Coder/Judge) without touching the backend.

Why this *was* framed as the long pole: the original cluster (intake-660–673) is NVIDIA-bound exactly here — nvcc, Nsight Compute, CUDA-only KernelBench — so the ROCm backend looked like net-new engineering. **The GEAK keystone batch (2026-06-03) overturned that:** AMD's own **GEAK-eval** (intake-674, MIT) and **Apex** (intake-675, MIT) already implement C1/C2/C3/C5 **on ROCm and demonstrate them on gfx90a (MI250X — the MI210's ISA family)**. The backend is now mostly an *adoption + integration* task, not a from-scratch build. What stays genuinely net-new for us: **C6** (anti-reward-hacking — GEAK/Apex have only loose oracles) and **C4** (gfx90a profiler-metric subset). See the GEAK keystone update at the foot of this doc; the component table below is annotated but the canonical revised substrate is GEAK-eval + Apex.

## Component Decomposition

| # | Component | CUDA-world reference | ROCm/MI210 target | Risk |
|---|-----------|----------------------|-------------------|------|
| C1 | **Build** | nvcc, torch `cpp_extension.load_inline` | hipcc + `hipify`; torch-ROCm `load_inline` (HIP transparently aliases the `cuda` namespace) | LOW — torch-ROCm cpp_extension is known-good |
| C2 | **Correctness oracle** | `torch.allclose` vs torch-CUDA reference on 5 random inputs | same vs torch-ROCm reference; **harden by lifting robust-kbench's oracle (intake-668, Apache-2.0 code)**: forward+backward passes, multiple init states, multiple/unseen shapes, output-magnitude & variation thresholds — all pure-torch, port as-is | MED — 5-input gate is the documented reward-hack surface (intake-661/663/664/666); robust-kbench code is directly adaptable |
| C3 | **Timing / speedup reward** | `torch.cuda.Event`, 3 warmup + 100 trials, CoV < 3% | `torch.cuda.Event` under ROCm (works) and/or `rocprof` wall-clock; baseline = torch-ROCm eager AND/OR a tuned lib (rocBLAS/MIOpen) | MED — define baseline carefully; eager is a weak bar (intake-663 caveat) |
| C4 | **Profiler-metric feed** | Nsight Compute (NCU), offline-selected 24-metric subset (CudaForge intake-662) | `rocprofv3` / `rocprof-compute` (Omniperf); **re-run the offline metric-selection on gfx90a** — the NVIDIA subset will NOT transfer (MFMA/LDS/CU semantics ≠ tensor-core/shared-mem) | HIGH — novel work; CDNA2 counter taxonomy + selection is unproven for us |
| C5 | **Benchmark / task suite** | KernelBench (250 tasks, L1/L2/L3, CUDA-only) | **fork MultiKernelBench (intake-667, arXiv:2507.17773)** + register a gfx90a/HIP `@register_backend('hip')` subclass (~5 methods: get_device/get_hardware_name/compile/correctness_execution/time_execution). **CONFIRMED fork target** (abstraction already runs CUDA/AscendC/Pallas + Triton/TileLang/SYCL in-repo; PyTorch reference layer → torch-ROCm carries it) | MED — single bounded backend file |
| C6 | **Reward-integrity / anti-hacking** | stream-sync before timing, adversarial LLM checker, robust discrete reward (intake-661) | **lift robust-kbench (intake-668, Apache-2.0): `run_filter.py` task-filtering + 3-verifier soft pre-filter + the exploit→defense catalogue** (7 classes, all hardware-agnostic — see below); only the profiler-detection feed needs the C4 rocprof swap | MED — design in from day one, not bolt-on |

## Phased Plan (skeleton — refine on contact with hardware)

- [ ] **Phase 0 — Environment standup** (gated on MI210). Install ROCm + torch-ROCm; confirm `gfx90a` device visible; smoke-test `cpp_extension.load_inline` compiles+runs a trivial HIP kernel; confirm `torch.cuda.Event` timing works under ROCm. *Exit: a hand-written HIP kernel round-trips through compile→run→time.*
- [ ] **Phase 1 — C1+C2 (build + correctness)**. Wrap hipcc/hipify build; implement the hardened correctness oracle (C2). *Exit: given (HIP source, torch reference), returns reliable compiles?/correct?.*
- [ ] **Phase 2 — C3 (timing/reward)**. Implement warmup+trials timing, pick baseline(s), emit a speedup scalar with a stability/CoV guard. *Exit: stable speedup number, CoV-gated, on a known kernel.*
- [ ] **Phase 3 — C4 (profiler-metric selection)**. Wire rocprof/Omniperf; **re-derive** the gfx90a decision-relevant metric subset via the CudaForge offline algorithm (per-task sampling → correlation-filter → consolidate). *Exit: a compact CDNA2 metric vector a Judge can consume.* ← highest-risk phase.
- [ ] **Phase 4 — C5 (ROCm-KernelBench analog)**. Fork MultiKernelBench, register the HIP backend, port the `fast_p` + L1/L2/L3 tiering; seed with EPYC-relevant ops first (attention, MoE dispatch, dequant) not generic KernelBench ops. *Exit: a runnable ROCm task suite producing fast_p scores.*
- [ ] **Phase 5 — C6 (reward-integrity)**. Add stream-sync/no-op/library-passthrough exploit detectors + robust-kbench hardening; red-team the backend with deliberately-cheating kernels. *Exit: known exploit classes are caught.*

## Interface Contract (the seam the controller depends on)

The controller (`agentic-rocm-kernel-authoring.md`) should depend ONLY on this signature, so the backend internals can change freely:

```
evaluate(candidate_hip_source, torch_reference_module, inputs) -> {
    compiled: bool,
    correct:  bool,              # hardened C2 oracle verdict
    speedup:  float,             # vs declared baseline; clamp <1.0 handling per EvoEngineer
    metrics:  dict[str, float],  # C4 gfx90a profiler subset (for a profiler-fed Judge)
    diagnostics: str,            # compiler/runtime errors for Correction-mode feedback
    integrity_flags: list[str],  # C6 exploit detectors tripped (empty = clean)
}
```

This mirrors the open CUDA Agent harness layout (intake-660: `verification.py` + `profiling.py` + `compile.sh`) and EvoEngineer's modular evaluator (intake-666) — both validate this factoring.

## Open Questions (to resolve before/at implementation)

- ~~**Benchmark strategy**: fork MultiKernelBench vs port KernelBench directly.~~ **RESOLVED 2026-06-03 (intake-667), then SUPERSEDED same day (intake-674 GEAK):** the primary task suite + oracle + timing is now **GEAK-eval** (AMD-native, MIT, gfx90a-proven: TritonBench-revised + a real ROCm Triton benchmark). MultiKernelBench is demoted to *secondary* — kept only for its multi-vendor `@register_backend` abstraction if non-AMD backends are ever wanted. Still port our own `fast_p` tiering on top (GEAK-eval uses Call/Execution-Accuracy + Speedup, not `fast_p`).
- **Baseline definition** for C3: torch-ROCm eager (easy, weak bar) vs rocBLAS/MIOpen tuned (harder, honest bar). Probably report both, gate reward on the honest one.
- **C4 is the research risk**: does a small, decision-relevant gfx90a metric subset even exist the way it does for NCU? Needs an empirical selection pass; budget for it.
- **Timing fidelity**: `torch.cuda.Event` under ROCm vs native `rocprof` timing — which is lower-noise on gfx90a? Affects reward stability.
- **Host contention**: profiling/timing on the MI210 shares the box with EPYC CPU benches — per `feedback_no_concurrent_inference`, these runs need explicit per-run approval and zombie-checks.

## Dependencies

- **Upstream**: MI210 acquisition; ROCm + torch-ROCm install; (optional) MultiKernelBench fork access.
- **Downstream consumer**: [`agentic-rocm-kernel-authoring.md`](agentic-rocm-kernel-authoring.md) (the controller) and ultimately [`gpu-drafter-mi200-investigation.md`](gpu-drafter-mi200-investigation.md) (the kernels' deployment target).
- **Intake provenance**: intake-664 (KernelBench scoring contract), intake-662 (profiler-metric-selection algorithm), intake-661/663/666 (anti-reward-hacking + evaluator factoring), plus MultiKernelBench 2507.17773 and robust-kbench 2509.14279 (flagged for a follow-up intake batch).

## Reporting Instructions

Tick the phase checkboxes above as phases complete; record measurements (ROCm/tool versions, metric subset chosen, baseline decision, CoV achieved) inline and in `progress/YYYY-MM/`. When Phase 3's metric subset is derived, capture it as a reference artifact (it's a reusable finding). Surface any blocking ROCm/torch-ROCm gaps back to the parent handoff.

## Research Intake Update — 2026-06-03 (follow-up batch: intake-667/668/669)

Three de-risking references ingested specifically for this backend. Net: the C5 fork strategy is **confirmed**, the C2/C6 anti-hacking layer now has **liftable Apache-2.0 code**, and we have a better vendor-portable architectural template.

### intake-667 MultiKernelBench (2507.17773) — C5 fork target CONFIRMED, with two corrections
- The modular `@register_backend` abstraction is **real and already runs 3–6 platforms** (CUDA/AscendC/Pallas + Triton/TileLang/SYCL in the live repo `wzzll123/MultiKernelBench`). PyTorch is the reference layer → torch-ROCm carries correctness+timing onto gfx90a. **Fork it.**
- **Correction 1 (scoring):** MultiKernelBench does **NOT** ship KernelBench's `fast_p` or L1/L2/L3 tiers — it uses Compilation@k / Pass@k / SpeedUp_α@k + 14 functional categories. We must **port `fast_p` in ourselves from intake-664**, not inherit it from the fork. (C5 + the interface contract's `speedup` field stand; the scoring contract is ours to add.)
- **Correction 2 (effort):** the "<20 LoC to add a platform" figure is measured on **Triton** (PyTorch-adjacent). A HIP backend shelling to hipcc/hipify + managing the build dir is realistically **low-hundreds of LoC** — still a single bounded file, LOW–MED effort, but budget accordingly.
- Caveat (platform-skew): expect **near-zero one-shot LLM pass rates** on a fresh HIP backend (mirrors AscendC's collapse) — the agentic refine loop + **category-aware exemplar prompting** is load-bearing. That prompting lever belongs in the controller (parent handoff), informed here.

### intake-668 robust-kbench (2509.14279, Sakana, Apache-2.0) — C2 + C6 implementation reference
This is Sakana's **post-scandal remediation** of the AI CUDA Engineer (claimed up-to-150× → independently found ~3× *slowdown* via an output-buffer-theft exploit). Its headline lesson: re-scoring prior work, **3.13× avg → 1.49× after excluding 40 gameable tasks** — ~half the "gain" was benchmark artifact. The harness logic (`run_filter.py`, forward+backward multi-shape oracle, 3-verifier orchestration) is **pure-torch and lift-able onto torch-ROCm**; only the NCU profiler feed needs the C4 rocprof swap.

**Exploit → defense catalogue (all PORT to HIP unless noted) — bake into Phase 1 (C2) + Phase 5 (C6):**
1. **Output-buffer aliasing** (kernel steals the reference result buffer, skips compute, passes allclose — the original scandal) → zero/poison output buffers before each call, fresh non-aliased tensors, re-seed inputs per trial.
2. **Hardcoded/eliminable op** (softmax-over-1D=1.0 → 123.6× false) → filter input-independent/constant outputs; require variation >0.01 across seeds; **add backward-pass correctness** (a no-op fwd usually breaks bwd).
3. **Low-magnitude output** (|out|<0.01 → FP noise passes) → filter on output std/magnitude; enforce a minimum-magnitude threshold.
4. **Single-input-config overfit** → test multiple + **unseen** shapes post-optimization; report generalization regression.
5. **Uniform-output trivial task** → filter overly-uniform output tensors.
6. **Inefficient-baseline inflation** (51.1× vs a naive ref) → audit reference efficiency + feature parity. *(This is the C3 "eager vs rocBLAS/MIOpen honest baseline" question — it matters more on ROCm.)*
7. **Invalid-kernel flooding** → 3 LLM soft-verifiers (compile/memory/numerics) as a cheap pre-hardware gate (~45%→15–20% invalid); retarget the memory-verifier vocabulary to HIP/rocm errors.
- Plus **stream-timing** (extra stream hides work → fake ~18×, cf. intake-661) → `torch.cuda.synchronize`/`hipDeviceSynchronize` under ROCm before reading events.
- **Meta-defense (authors' own caveat):** anti-hacking is an arms race — Phase 5's "red-team with deliberately-cheating kernels" exit criterion is mandatory, and **human-verify any strong speedup**. The defenses are a hardened floor, not a guarantee.

### intake-669 KernelFoundry (2603.12440, Intel) — better vendor-portable backend template
Intel/SYCL-first, **train-free**, multi-vendor (SYCL + CUDA) — its **distributed, backend-swappable compile/execute worker architecture is the cleanest cross-vendor template in the cluster** for this backend (it proves the abstraction across two vendors rather than disclaiming it, as EvoEngineer does). Borrow that worker-layer factoring. Caveat: its hardware-awareness is bound to Intel unitrace / Nsight Compute counters — **does not transfer to rocprof/Omniperf**, reinforcing that **C4 (gfx90a metric re-derivation) is the standing research risk**. (Controller-side implications — adopt-both with EvoEngineer — are in the parent handoff.)

## Research Intake Update — 2026-06-03 (next-tier batch: intake-670/671/672/673)

Three backend-relevant refinements from the next-tier batch (the 4th, K-Search 673, is controller-side — see parent handoff).

### C4 de-risk — a profiler-FREE first pass (intake-672 Xe-Forge)
The highest-risk component (C4, re-deriving the gfx90a profiler-metric subset) now has a cheaper complement: Xe-Forge drives hardware-awareness from a **static constraint knowledge base** (84 YAML entries of hard constraints + before/after patterns, prompt-injected) + a runtime device-property query — **no profiler counters**. **Action:** before (or instead of) the full rocprof/Omniperf metric-selection, author a **gfx90a rules/patterns YAML** (wavefront=64, LDS/shared-mem sizing, MFMA tile constraints, VGPR/AGPR limits, boundary-check typing). This gives a working hardware-awareness layer at Phase 0–1 cost and demotes C4 from a blocker to an enhancement.

### C3 baseline + a new production-grade exit gate (intake-671 FastKernels)
FastKernels quantifies that operator-level / torch-eager scoring **overstates real gains ~25pp** (1.16× sandbox → 0.93× vs vendor-optimized). Two implications:
- **C3 baseline (reinforced):** gate the speedup reward on an **honest vendor baseline** (rocBLAS / hipBLASLt / AITER / torch-ROCm-compile), not torch-ROCm eager. This resolves the C3 open question toward the honest bar.
- **New Phase-5+ exit gate (MacroEval-style):** beyond isolated-op `fast_p`, add a **whole-model end-to-end check** — inject the authored HIP kernel into a full torch-ROCm / llama.cpp forward pass with **captured real EPYC-workload tensors** + a downstream-quality check. A kernel that wins isolated-op `fast_p` but regresses end-to-end fails. (FastKernels itself is NVIDIA-only with no backend abstraction — adopt the *philosophy*, do not fork it; MultiKernelBench 667 stays the C5 fork target.)

### C2 caution (intake-670 KernelCraft)
KernelCraft's tolerance-based correctness oracle (abs_tol up to 0.012, single-shape) is exactly the **loose gate** the reward-hacking literature warns about — a reminder that the C2 oracle must use the robust-kbench (668) hardening (multi-shape, forward+backward, magnitude/variation thresholds), not a single loose tolerance.

### Follow-up pointer
**GEAK (arXiv:2507.23194)** — AMD's own Triton/HIP kernel agent for Instinct + a **ROCm Triton benchmark** — is the highest-value next intake for this backend (a real AMD-native correctness/timing reference for gfx90a). Flagged in the parent handoff for a dedicated intake.

## Research Intake Update — 2026-06-03 (GEAK KEYSTONE: intake-674/675/676) — backend substrate found

**This is the most consequential update to this handoff.** The first AMD-native, ROCm-targeted references in the program — and crucially, **demonstrated on gfx90a, the MI210's exact ISA family** — collapse most of the "long pole."

### intake-674 GEAK (AMD, arXiv:2507.23194, MIT) — adopt_component → the C1/C2/C3/C5 substrate
AMD's own train-free Triton kernel agent **+ two open benchmarks (GEAK-eval)**: TritonBench-revised (184 kernels) and a real **ROCm Triton benchmark** (30 kernels from ROCm/triton, aiter, aotriton, vllm, pytorch, xformers). It already ships, on ROCm:
- **C1 build** (Triton→ROCm), **C2 correctness oracle** (tolerance-based torch.allclose on torch-ROCm, seeded, up to 32K inputs, halt-on-mismatch), **C3 timing/speedup** (median-latency vs reference), **C5 task suite** (two AMD-validated benchmarks).
- **Demonstrated ON gfx90a**: GEAK reports a dedicated **MI250X (gfx90a)** line — 52.72% exec / 2.42× on TritonBench-revised — *not just MI300X*. MI250X is CDNA2/gfx90a, the **same ISA as our MI210** (MI210 ≈ one MI250 GCD). So the harness + generated kernels run on the MI210 with **autotune-level re-tuning only, no porting**.

**Revised plan:** adopt **GEAK-eval as the primary C1/C2/C3/C5 substrate**, *displacing the from-scratch MultiKernelBench-fork as primary* (intake-667 is retained only for its multi-vendor `@register_backend` abstraction if non-AMD backends are ever wanted, and for the `fast_p` tiering we layer on top). Phases 0–2 and 4 shrink from "build" to "stand up GEAK-eval on the MI210 + confirm the gfx90a numbers."

### intake-675 Apex (AMD-AGI, MIT repo) — adopt_patterns → the deploy harness + scorer
The AMD-native end-to-end **harness**: profile a real vLLM/SGLang/aiter serving workload → rank bottleneck kernels by GPU time → optimize → **hot-patch into site-packages** → re-benchmark E2E. **Explicitly lists gfx90a support.** Directly droppable pieces:
- **Magpie scorer** (`compiled*20 + correct*100 + piecewise-speedup`, regression penalty) — a ROCm-native realization of the C3 reward + part of C6.
- **AST anti-tampering** — a partial C6 layer (catches fabricated results; does NOT catch functional reward-hacks, so robust-kbench-668 hardening still required).
- **5 MCP servers** (source-find, kernel-RAG, GPU-info, fusion-detect, eval) — the controller's tool vocabulary (swap the SaaS agent backend for our local coder role → opensource_only).
- **Hot-patch + E2E re-benchmark** — operationalizes the FastKernels (671) production-faithful exit gate (Phase 5+): score kernels in a full serving pass, not isolated-op.

### intake-676 TritonForge — correction + a narrower role
Xe-Forge grouped it as "AMD/ROCm-targeted," but its AMD support is **gfx942/MI300X (CDNA3) only — NOT our gfx90a/MI210** — and its AMD multi-turn RL crashes. **AMD-secondary, not AMD-native; subordinate to GEAK.** Useful only for: its validated ROCm Docker/env recipe (as a gfx942→gfx90a starting template) and its open SFT data-curation recipe (controller-side, offline).

### Net revised component status
| Comp | Was | Now (post-GEAK) |
|------|-----|-----------------|
| C1 build | from-scratch hipcc/hipify wrap | **adopt GEAK-eval / Apex (ROCm, gfx90a-proven)** |
| C2 correctness | build hardened oracle | **adopt GEAK-eval oracle; HARDEN with robust-kbench-668 (still required — GEAK's is loose)** |
| C3 timing/reward | build timing + pick baseline | **adopt GEAK-eval timing + Apex Magpie reward; honest vendor baseline per 671** |
| C4 profiler-metric | re-derive gfx90a subset | **STILL net-new** (GEAK/Apex are optimizer-driven, not counter-fed); Xe-Forge-672 static-constraint-KB de-risk applies |
| C5 benchmark | fork MultiKernelBench | **adopt GEAK-eval's two benchmarks (incl. real ROCm bench); layer our fast_p tiering; seed EPYC ops** |
| C6 anti-hacking | lift robust-kbench | **STILL net-new + most valuable** — GEAK has no anti-hack; Apex AST catches only fabrication. robust-kbench-668 hardening is our differentiator |

**Bottom line:** our remaining real engineering is **C6 (anti-reward-hacking hardening) and C4 (gfx90a profiler-metric selection)** — exactly the two gaps GEAK and Apex leave. Everything else is adopt-and-integrate from MIT-licensed AMD-native code that already runs on the MI210's ISA.

### Follow-up (high priority)
**GEAK-v2** (GEAK-OptimAgentv2 + GEAK-OpenEvolve — evolutionary, avg 3.32–3.42×, but evaluated on MI300X/MI325X, not yet gfx90a) and **GEAK-HIP** (HIP-level, beyond Triton) — both blog-stage, repo HEAD already contains v2 code. Dedicated intake recommended once an arXiv lands. **Validate GEAK-eval's gfx90a numbers on the real MI210 first thing when it racks.**

## Research Intake Update — 2026-06-03 (GEAK-v2 + GEAK-HIP: intake-677/678)

Two AMD-native, blog/repo-stage GEAK follow-ups. Both regress gfx90a coverage (all numbers on gfx942/CDNA3 — MI300X/MI325X/MI308X — none on our gfx90a), so they are **patterns, not components** — but they materially de-risk **C4** and open the **HIP arm**.

### C4 (the highest-risk component) just got a cheaper path — intake-677 GEAK-OptimAgentv2
v2's **Profiler-Analyzer** feeds **rocprof-compute hardware counters → an LLM → structured natural-language performance intelligence → back into generation.** Its ablation shows this loop is the dominant lever (avg 1.38× → +Profiler 1.98× → +Profiler+LLM 3.32×). **Implication for C4:** instead of (or before) the expensive manual offline metric-*selection* (the CudaForge-662 algorithm we scoped as HIGH-risk), we can have the **LLM consume raw rocprof-compute output directly as NL** — no curated 24-metric subset required to get started. Add this as the **primary C4 approach to try first**; keep the formal metric-selection as the fallback if the LLM-reads-raw-profiler signal is too noisy. (Caveat: v2's counter vocabulary was captured on gfx942/CDNA3 — the *semantics* port to gfx90a/CDNA2, the specific tuned values do not; this still needs a gfx90a pass.) OpenEvolve's 9-dim QD feature grid + Cascade Filtering also belong to the controller (KernelFoundry-669 layer), not this backend.

### HIP arm — intake-678 GEAK-HIP (the C1/C2/C3 pattern at the raw-HIP level)
GEAK v1/v2 + Apex prove the loop at **Triton** level (the lower-risk on-ramp). **GEAK-HIP** proves the same 3-module Generator/Evaluator/Reflector loop at the **raw HIP/C++** level via a **hipcc compile/exec/profile harness with error-trace feedback** — exactly the C1/C2/C3 contract one layer down, where our llama.cpp fork ultimately hand-writes kernels. Notable: it **out-optimized a human engineer** on production kernels (Voxelization 2.07× vs 1.84×). It ships **no open HIP benchmark/oracle** (only research-use example kernels), so for the HIP arm we still **build our own HIP benchmark + oracle** and apply robust-kbench (668) hardening — at the HIP level UB/silent-miscompare risk is *higher* than Triton, so C6 matters more here. Sequencing: **Triton arm first (GEAK-eval substrate), HIP arm second (GEAK-HIP patterns + our own oracle).** Pairs with `llama-cpp-dsa-contribution.md`.

### 🔁 AUDIT REMINDER — re-check for fresh GEAK-family content at next review
Same list as the parent handoff (`agentic-rocm-kernel-authoring.md`): at the next audit / when the MI210 racks, sweep for a **GEAK-v2 arXiv paper**, a **GEAK-HIP arXiv / open benchmark**, **any gfx90a/MI250 numbers** for v2 or GEAK-HIP (closes the coverage gap), GEAK-agent **repo HEAD drift** (re-pin commit), and **new AMD-native siblings** on rocm.blogs.amd.com / the AMD-AIG-AIMA & AMD-AGI GitHub orgs. Treat all intake-674–678 AMD numbers as **vendor-reported until independently reproduced on our own gfx90a hardware** (per `feedback_classify_eval_failures_by_reason` / observe-before-diagnosing).

---

# Component Design Rationale (VERBOSE REVIEW DRAFT — 2026-06-03)

> Intentionally verbose, for human review before cleanup/tightening. Companion to the §"Full Reasoning Narrative" in the parent handoff `agentic-rocm-kernel-authoring.md` — read that first for the program-level reasoning; this doc reasons through the **backend** specifically, component by component. Every claim traces to an intake entry (intake-660…678).

## Why this backend exists as a separate doc at all
The single most important architectural decision is the **controller/backend split**: the controller (model + search strategy — EvoEngineer/KernelFoundry/K-Search/GEAK/Xe-Forge) must be swappable *without touching the evaluation substrate*. Every mature reference validates this factoring — CUDA Agent's `verification.py`/`profiling.py`/`compile.sh` (660), EvoEngineer's modular evaluator (666), GEAK's cascaded Evaluator (674), Apex's Magpie scorer (675). So we define one stable seam — `evaluate(hip_source, torch_reference, inputs) → {compiled, correct, speedup, metrics, diagnostics, integrity_flags}` — and everything behind it is this handoff's concern. If we get the seam right, we can A/B five controllers against the same backend cheaply; if we entangle them, every controller experiment re-touches ROCm plumbing.

## The reversal this doc has already undergone (read before the component table)
This handoff was first written assuming a **from-scratch ROCm backend** (fork MultiKernelBench + lift robust-kbench), with the framing "this is the long pole, the controllers port easily." The **GEAK keystone batch (674/675)** overturned that mid-life: AMD's GEAK-eval + Apex are MIT, AMD-native, and **demonstrated on gfx90a (MI250X = the MI210's ISA)**, and they already implement C1/C2/C3/C5. So the canonical substrate is now **GEAK-eval + Apex**, and the from-scratch component table below is *retained as the conceptual decomposition and risk map* but is superseded on "who builds it" by the GEAK keystone section. The net is that the genuinely net-new work narrowed to **C4 + C6**. The component-by-component reasoning below reflects the *post-reversal* view.

## C1 — Build (hipcc / hipify / torch-ROCm). Risk: LOW.
**Reasoning:** Triton-on-ROCm and `torch.utils.cpp_extension.load_inline` under torch-ROCm are known-good; HIP transparently aliases the CUDA namespace, so the PyTorch-reference machinery that the whole cluster relies on carries onto gfx90a. GEAK-eval and Apex both already do this build step on ROCm. **Net-new: ~none** — adopt. The only real task is environment standup (Phase 0): confirm a hand-written HIP kernel round-trips compile→run→time on the actual MI210.

## C2 — Correctness oracle. Risk: MED. **This is half of our differentiator.**
**Reasoning:** Every AMD-native reference (GEAK 674, Apex 675, GEAK-HIP 678) uses a *loose* tolerance-based `torch.allclose` oracle — exactly the gate the reward-hacking literature shows is gameable (KernelBench's no-op-via-stale-output-memory, low-magnitude FP-noise passes, single-shape overfit). A loose oracle makes every downstream speedup untrustworthy (robust-kbench re-scored 3.13×→1.49× after removing gameable tasks). **Decision:** adopt GEAK-eval's oracle as the starting point but **harden it by lifting robust-kbench's (668, Apache-2.0) oracle logic**: forward+backward passes, multiple init states, multiple/unseen shapes, output-magnitude + variation thresholds, output-buffer poisoning. All of that is pure-torch and ports to torch-ROCm unchanged. **Net-new: integration + the hardening port.**

## C3 — Timing / speedup reward. Risk: MED.
**Reasoning:** `torch.cuda.Event` works under ROCm; GEAK-eval already times on AMD. The *real* decision is the **baseline**, and FastKernels (671) settles it: torch-ROCm **eager is a weak bar** that overstates real gains ~25pp; gate the reward on an **honest vendor baseline** (rocBLAS / hipBLASLt / AITER / torch-ROCm-compile). Report both eager and vendor numbers, but the reward that the controller optimizes must be vs the honest bar — otherwise the controller learns to beat a strawman. Apex's Magpie piecewise reward (`compiled·20 + correct·100 + speedup`, regression penalty for <1.0) is a good ROCm-native scoring shape to adopt. **Net-new: baseline selection + Magpie adoption.**

## C4 — Profiler-metric feed. Risk: HIGH. **The standing research risk.**
**Reasoning:** A profiler-fed judge needs a compact, decision-relevant counter set. CudaForge (662) derived a 24-metric NCU subset on NVIDIA; that subset's semantics (MFMA/LDS/CU) **do not exist or differ on CDNA2**, and whether a small useful gfx90a subset even exists is unproven for us. This is the one thing no NVIDIA paper hands us. **Three paths, try cheapest first** (see parent §8): (1) ⭐ **GEAK-v2 OptimAgentv2 Profiler-Analyzer (677)** — feed *raw* `rocprof-compute` counters → LLM → NL performance intelligence; no curated subset to begin, the LLM interprets; v2's ablation shows this loop is the dominant lever; caveat: v2 counters were captured on gfx942, semantics port but values don't, needs a gfx90a pass. (2) **Xe-Forge static constraint-KB (672)** — a hand-authored gfx90a rules YAML; profiler-*free*, cheap, brittle, good first-pass/fallback. (3) **CudaForge formal offline selection (662)** — rigorous, expensive, re-run on gfx90a as the fallback. **Net-new: substantial — this is where to budget research time.**

## C5 — Benchmark / task suite. Risk: MED → now mostly adopt.
**Reasoning (post-reversal):** **GEAK-eval (674)** provides two AMD-validated benchmarks (TritonBench-revised + a real ROCm Triton benchmark) that *already run on gfx90a* — this is the primary C5 substrate. MultiKernelBench (667) is secondary: kept only for its `@register_backend` multi-vendor abstraction if non-AMD backends are ever wanted. Either way we **port our own `fast_p` + tier scoring on top** (GEAK-eval reports Call/Execution-Accuracy + Speedup, not `fast_p`; MultiKernelBench uses Compilation@k/Pass@k/SpeedUp_α@k + 14 categories — neither inherits `fast_p`). **Seed with EPYC-relevant ops first** (attention, MoE dispatch, dequant — the `gpu-drafter-mi200-investigation.md` targets), not generic KernelBench ops. **Net-new: fast_p layer + EPYC-op seeding.**

## C6 — Reward-integrity / anti-hacking. Risk: MED. **The other half of our differentiator.**
**Reasoning:** see parent §9 for the full evidence (CUDA-L1's 32.8% stream-timing exploit, the AI CUDA Engineer 150×→3×-slowdown scandal, KernelBench's gameable gates, the OpenReview 73.8% finding). The AMD-native refs are the *least* protected (GEAK loose oracle; Apex AST anti-tamper catches only fabrication). **Decision:** lift robust-kbench's (668) Apache-2.0 exploit→defense catalogue (7 classes, almost all hardware-agnostic) + a `run_filter.py`-style task-filter + the 3-verifier soft pre-filter, and add a **red-team-with-cheating-kernels** Phase-5 exit gate. At the **raw-HIP** level (the GEAK-HIP arm) UB/silent-miscompare risk is *higher* than Triton, so C6 matters even more there. **Net-new: the hardening port + red-team harness — this is the value we add on top of AMD's work.**

## Phased plan — the reasoning behind the ordering
- **Phase 0 (env standup)** is gated on the physical card because nothing here can be trusted from CUDA analogy — the whole point is to verify torch-ROCm/hipcc/`torch.cuda.Event` actually behave on *our* gfx90a. **First real action when the MI210 racks: reproduce GEAK-eval's MI250X numbers on the MI210** (sanity gate; expect lower absolute speedups at half the aggregate BW, same correctness).
- **Phases 1–2 (C1+C2, C3)** come before C4 because a trustworthy correctness + timing reward is the prerequisite for *any* controller A/B; the profiler feed (C4) is an *enhancement* to the reward, not a prerequisite — a controller can run on correctness+speedup alone.
- **Phase 3 (C4)** is explicitly the high-risk phase and is sequenced after a working reward so we can measure whether the profiler signal actually improves controller convergence on gfx90a, rather than assuming it.
- **Phase 4 (C5)** layers `fast_p`/tiering + EPYC-op seeding onto the adopted GEAK-eval suite.
- **Phase 5 (C6)** is "design in from day one" in spirit (the oracle hardening in C2 starts in Phase 1) but the red-team gate is a distinct final check.

## Interface contract — why exactly these fields
`{compiled, correct, speedup, metrics, diagnostics, integrity_flags}` is the minimal set that lets *every* candidate controller operate without backend changes: `compiled`+`diagnostics` feed a Correction-mode agent (Apex/Xe-Forge/GEAK all have one); `correct` is the hardened C2 verdict; `speedup` is the C3 reward vs the honest baseline; `metrics` is the C4 profiler vector for a profiler-fed judge (KernelFoundry/CudaForge/GEAK-v2 style); `integrity_flags` surfaces C6 exploit detections so the controller (and our logs) can see when a "win" was a hack. If a future controller needs more, it should be derivable from these — resist widening the seam.

## The standing caveat that governs all of the above
Every AMD number in intake-674–678 is **vendor-reported** (AMD authors the agent, the benchmark, *and* the hardware) with **no independent replication** found in Tier-2b search. Per `feedback_classify_eval_failures_by_reason` and observe-before-diagnosing: treat all of it as provisional until reproduced on *our own* gfx90a, and do not let a vendor blog number drive an irreversible design choice. The AUDIT REMINDER block above is the mechanism for revisiting this as fresh (ideally peer-reviewed, ideally gfx90a) evidence appears.
