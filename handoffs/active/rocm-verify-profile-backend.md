# ROCm Verify/Profile/Benchmark Backend for MI210 Kernel Authoring

**Status**: SKELETON — design scaffold; substrate is now mostly *adopt AMD-native*, not build-from-scratch
**Created**: 2026-06-03 · **Updated**: 2026-06-03 (GEAK keystone reversal + AgentKernelArena)
**Categories**: hardware_optimization, benchmark_methodology, tool_implementation, inference_serving
**Hardware gate**: AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB), ~July 2026. Prep on paper now; nothing executes until the card racks + ROCm/torch-ROCm stand up.
**Priority**: MEDIUM (the substrate for [`agentic-rocm-kernel-authoring.md`](agentic-rocm-kernel-authoring.md))
**Parent**: [`agentic-rocm-kernel-authoring.md`](agentic-rocm-kernel-authoring.md) · **Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Full reasoning + evidence**: [`research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md`](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md) (§5.2/§5.5/§5.6 cover this backend).

---

## Objective
Provide the **evaluation backend** the agentic kernel-authoring loop calls: given a candidate HIP/Triton kernel + a PyTorch reference, return `(compiles?, correct?, speedup, profiler_metrics, integrity_flags)`. It is factored out from the controller (model + search) so controllers can be A/B'd without touching it. **The substrate is now mostly AMD-native MIT/Apache-2.0 code (GEAK-eval + Apex + AgentKernelArena) demonstrated on gfx90a — so this is an adopt/reproduce/harden task, not a from-scratch build.** The two genuinely net-new pieces are **C4** (gfx90a profiler-metric) and **C6** (anti-reward-hacking).

## Component table — adopt / build / harden (post-GEAK truth)
| # | Component | Plan | Source | Risk |
|---|-----------|------|--------|------|
| **C1** | Build (hipcc/hipify/torch-ROCm) | **ADOPT** | GEAK-eval 674 / Apex 675 (already build on ROCm/gfx90a); torch-ROCm `load_inline` known-good | LOW |
| **C2** | Correctness oracle | **ADOPT then HARDEN** | adopt GEAK-eval's torch-ROCm oracle; **harden** with robust-kbench 668 (forward+backward, multi/unseen shapes, magnitude/variation, output-buffer poisoning) **+ AgentKernelArena 679 unseen-shape generator** | MED |
| **C3** | Timing / speedup reward | **ADOPT then FIX BASELINE** | adopt GEAK-eval timing + Apex/AgentKernelArena Magpie score; **gate reward on an honest vendor baseline** (rocBLAS/hipBLASLt/AITER/torch-ROCm-compile), not eager (FastKernels 671) | MED |
| **C4** | Profiler-metric feed | **BUILD — try cheapest first** | (1) GEAK-v2 677 Profiler-Analyzer: raw `rocprof-compute` → LLM → NL; (2) Xe-Forge 672 static gfx90a constraint-KB (profiler-free); (3) CudaForge 662 formal offline selection. NVIDIA/NCU subset does NOT transfer | **HIGH** — the standing research risk; CDNA2 counter taxonomy unproven |
| **C5** | Benchmark / task suite | **ADOPT (primary) + layer** | GEAK-eval 674 (TritonBench-revised + real ROCm bench, gfx90a-proven) **and** AgentKernelArena 679 (HIP/Triton/Torch2HIP suites); layer our own `fast_p` tiering; seed EPYC ops (attention/MoE-dispatch/dequant). MultiKernelBench 667 = secondary (multi-vendor abstraction only) | MED |
| **C6** | Reward-integrity / anti-hacking | **BUILD — our differentiator** | robust-kbench 668 exploit-class half (Apache-2.0, liftable) **+** AgentKernelArena 679 unseen-shape half **+** a red-team-with-cheating-kernels gate. GEAK/Apex have only loose oracles | MED |

## Current sequence (replaces the old phase plan)
- [ ] **Pre-hardware prep (now).** Pin GEAK / GEAK-eval / Apex / AgentKernelArena repos to paper-matching commits (repo HEADs are past the papers — see deep-dive §9); inspect licenses (GEAK/Apex MIT, AgentKernelArena Apache-2.0); draft the ROCm + torch-ROCm env recipe.
- [ ] **MI210 bring-up (gated on card).** Install ROCm + torch-ROCm; confirm `gfx90a` visible; **reproduce GEAK-eval's MI250X numbers on the MI210** (sanity gate — expect lower absolute speedups at ~half the aggregate bandwidth, verify correctness/compile). Also reproduce AgentKernelArena on gfx90a (`target_gpu_model`).
- [ ] **Harden oracle + integrity (C2 + C6).** Lift robust-kbench's exploit-class defenses + AgentKernelArena's unseen-shape generator into the GEAK/Apex oracle; red-team with deliberately-cheating kernels.
- [ ] **Honest baseline + E2E scoring (C3 + FastKernels gate).** Gate reward on a vendor baseline; add a whole-model exit gate via Apex's hot-patch + re-bench with captured EPYC-workload tensors.
- [ ] **C4 profiler feedback (HIGH risk).** Try GEAK-v2 LLM-reads-raw-rocprof first; Xe-Forge static-KB second; CudaForge formal selection fallback. Derive whether a usable gfx90a signal exists.
- [ ] **EPYC-op seeding + controller A/B.** Seed the suites with EPYC ops; A/B controllers as AgentKernelArena adapters (see parent handoff).
- [ ] **HIP arm (after the Triton loop works).** GEAK-HIP patterns (678) + AgentKernelArena Torch2HIP suite (679) + our own HIP oracle, toward hand-HIP for the llama.cpp fork.

## Interface contract (the seam controllers depend on)
```
evaluate(candidate_source, torch_reference_module, inputs) -> {
    compiled: bool,
    correct:  bool,              # hardened C2 verdict (incl. unseen-shape check)
    speedup:  float,             # C3 reward vs the HONEST vendor baseline
    metrics:  dict[str, float],  # C4 gfx90a profiler signal (for a profiler-fed judge)
    diagnostics: str,            # compiler/runtime errors -> Correction-mode feedback
    integrity_flags: list[str],  # C6 exploit detections (empty = clean)
}
```
Mirrors GEAK-eval's evaluator, Apex's Magpie scorer, and CUDA Agent's `verification.py`/`profiling.py`/`compile.sh` (intake-660) — all validate this factoring. Resist widening the seam; a new controller's needs should be derivable from these fields.

## gfx90a caveat + audit
Same `gfx90a` predicts **compile compatibility, not performance equivalence** — reproduce every AMD number on the MI210 before trusting it (GEAK-v1 is the only gfx90a-proven reference; GEAK-v2/HIP/AgentKernelArena are gfx942-only). **Run the GEAK-family freshness sweep (deep dive §9) at each audit.** All intake-674–679 AMD numbers are vendor-reported until reproduced on our own gfx90a (`feedback_classify_eval_failures_by_reason`, observe-before-diagnosing).
