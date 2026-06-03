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
