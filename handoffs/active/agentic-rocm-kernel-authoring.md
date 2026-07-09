# Agentic ROCm Kernel Authoring — MI210 Verify+Profile Harness

**Status**: stub (design / investigation) — hardware-gated
**Created**: 2026-06-03 (via /research-intake deep-dive of the LLM-kernel-generation cluster) · **Updated**: 2026-06-03 (GEAK keystone + AgentKernelArena)
**Categories**: hardware_optimization, agent_architecture, autonomous_research, tool_implementation, training_distillation
**Hardware gate — SATISFIED 2026-07-02**: AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB) is racked and the llama.cpp HIP build is verified on gfx90a (`progress/2026-07/2026-07-02-mi210.md`; memory `project_mi210_gpu_inference`). This program is now **ACTIVE**, priority **MEDIUM** — it is an *optimization* (close the measured quantized-MMQ-dequant roofline gap: ~33% Q4_K / ~47% Q8 at batch-1), **not a production blocker**: llama.cpp-HIP already serves ~910 tok/s @32-way as-is (2026-07-02 obs). First step = reproduce **GEAK-eval** (intake-674, arXiv 2507.23194) on gfx90a — compile+correctness+timing round-trip — as the sanity gate. **Scoping caveat (adversarially verified 2026-07-03)**: GEAK-v1 is the *only* gfx90a-proven substrate (MI250X = same CDNA2 ISA family); **AgentKernelArena (679) / robust-kbench (668) are gfx942/CDNA3-listed** and must be treated as ports, not drop-in reproductions. All GPU runs remain operator-approved measurements per MEASUREMENT.md (write P-GPU-1 first). [was: "expected ~July 2026; nothing executes until the card racks" — stale after 2026-07-02 install]
**Priority**: MEDIUM (activates on MI210; prep proceeds now)
**Workstream**: Inference Acceleration / GPU · **Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Full reasoning + evidence**: [`research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md`](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md) ← the durable narrative; this handoff is the operational summary.
**Related**:
- [`rocm-verify-profile-backend.md`](rocm-verify-profile-backend.md) — **child**: the ROCm verify/profile/benchmark backend this loop drives
- [`gpu-drafter-mi200-investigation.md`](gpu-drafter-mi200-investigation.md) — MI210-gated; consumes the kernels this loop produces
- [`gpu-acceleration-path.md`](gpu-acceleration-path.md) — the ROCm kernel-library hand-port path this automates
- [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) / [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) — the hand-HIP endgame + the CPU ukernel loop this rhymes with

---

## Objective
Stand up an **agentic, train-free kernel-authoring loop for the incoming MI210** — drive a strong coding agent through generate → compile → verify → profile → refine to produce and tune **HIP/Triton kernels** for the EPYC stack, replacing the manual hipify-and-hand-tune path. **We cannot retrain a kernel model on one MI210, but we can run a train-free verify+profile loop** — and AMD has already open-sourced most of the substrate (GEAK/Apex/AgentKernelArena), demonstrated on gfx90a.

## Current Decision Snapshot (2026-06-03)
The path *today* (supersedes any earlier "EvoEngineer/CudaForge-first" framing):
1. **Backend = adopt AMD-native code.** **GEAK-eval (674, MIT)** is the primary benchmark/oracle/timing substrate (C1/C2/C3/C5), reproduced on our gfx90a; **Apex (675, MIT)** supplies the E2E deploy harness + Magpie scorer; **AgentKernelArena (679, Apache-2.0)** supplies a second substrate + the controller-A/B shell. Net-new to us: **C4 + C6** (see child handoff).
2. **Controller-A/B = register adapters, don't build a harness.** AgentKernelArena (679) already ships Claude Code / Codex / Cursor / GEAK adapters with a `@register_agent` pattern — **register our controllers (Claude+Codex actor-critic, EvoEngineer, KernelFoundry, K-Search, Xe-Forge, GEAK) as adapters and A/B them on gfx90a.** It compares whole agents at task level, complementing each controller's inner loop.
3. **Agent backend = Claude+Codex actor-critic** (reuse the autopilot planner's infra); local coder role is the self-hosted fallback. `opensource_only` governs deployed services, not build-time tooling — the authored kernel is the artifact, not the LLM. Empirically favored: CudaForge's best result was a cross-model coder/judge split; AgentKernelArena's best results are Claude Code / Cursor / Codex.
4. **Triton first (on-ramp), HIP second (endgame).** GEAK-eval (Triton, gfx90a-proven) → then the HIP arm via GEAK-HIP patterns (678) + AgentKernelArena's Torch2HIP suite (679) + our own HIP oracle. Pairs with `llama-cpp-dsa-contribution.md`.
5. **Differentiators we own: C6 (anti-reward-hacking) + C4 (gfx90a profiler-metric).** Exactly the two pieces AMD left thin.

**Why this is the decision (one paragraph):** the entire cluster was NVIDIA-bound at the toolchain, so a from-scratch ROCm backend looked like the long pole — until GEAK/Apex/AgentKernelArena turned out to be AMD-native, permissively licensed, and (for GEAK-v1) demonstrated on **gfx90a, the MI210's exact ISA family**. That predicts *compile compatibility* on our card (not performance — single-GCD bandwidth, ROCm version, autotune space, and harness details still need reproduction), which shrinks the program to "adopt + reproduce + add C4/C6." Full reasoning, alternatives, and the rejected paths: see the [deep dive](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md).

## Evidence — grouped by role (intake-660…679; details in the deep dive + `intake_index.yaml`)
| Role | Entries | Use |
|------|---------|-----|
| **AMD-native substrate (adopt)** | GEAK 674 (gfx90a-proven, MIT), Apex 675 (MIT), AgentKernelArena 679 (Apache-2.0) | C1/C2/C3/C5 backend + Magpie scorer + controller-A/B arena. **674 is the only gfx90a-proven one; 675/679 are gfx942-listed/eval'd.** |
| **AMD-native, patterns-only (gfx942-only)** | GEAK-v2 677, GEAK-HIP 678 | 677 → C4 Profiler-Analyzer (try first) + QD upgrades; 678 → HIP-arm loop (out-optimized a human engineer) |
| **Controller candidates** | EvoEngineer 666 (lead), KernelFoundry 669 (hw-awareness layer), Xe-Forge 672 (linear archetype), K-Search 673 (world-model tree, MoE-strong), GEAK 674 (first to stand up) | register as AgentKernelArena adapters; A/B on gfx90a |
| **C4 (profiler-metric) sources** | GEAK-v2 677 (raw rocprof→LLM, try first), Xe-Forge 672 (static KB), CudaForge 662 (formal selection) | the standing research risk |
| **C6 (anti-hacking) sources** | robust-kbench 668 (exploit classes, Apache-2.0), AgentKernelArena 679 (unseen-shape generalization) | the two complementary halves; our differentiator |
| **Eval philosophy** | KernelBench 664 (`fast_p`), FastKernels 671 (vendor baseline + whole-model gate) | weight end-to-end over isolated-op |
| **RL lessons (no training)** | CUDA Agent 660, CUDA-L1 661, Kevin 663 | reward design + anti-hack gates + multi-turn |
| **Optional offline later** | ConCuR 665, TritonForge 676 | SFT data-curation for a local HIP-specialized small model |
| **Not our path** | KernelCraft 670 (AIE-ML NPU/Peano, not ROCm) | harvested only: tool vocabulary + thinking-budget + ICL findings |

## gfx90a caveat (applies to every AMD number above)
Same `gfx90a` ISA **predicts compile compatibility, not performance equivalence.** GEAK-v1's MI250X results should *build and run* on the MI210 (wavefront=64/MFMA/LDS identical), but single-GCD bandwidth, ROCm version, autotune space, and harness details require reproduction. GEAK-v2 / GEAK-HIP / AgentKernelArena are **gfx942/CDNA3-only** — a coverage regression vs v1 — so their numbers carry even less. **All AMD numbers are vendor-reported until reproduced on our own gfx90a.**

## Open questions (decided ones live in the deep dive §5)
- Which controller wins on gfx90a? Unknown until the AgentKernelArena A/B runs on the MI210 with EPYC ops.
- Does GEAK-eval's MI250X result reproduce on the single-GCD MI210 (expected yes, lower absolute speedup)? **First thing to verify when the card racks.**
- Does C4's cheapest path (GEAK-v2 LLM-reads-raw-rocprof) give a usable signal on CDNA2?
- Will AMD publish gfx90a numbers / arXiv papers for GEAK-v2 / GEAK-HIP / AgentKernelArena? → Freshness Appendix in the deep dive.

## Reporting / maintenance instructions
- After any work: update the **Current Decision Snapshot** here + the deep dive; log progress in `progress/YYYY-MM/`.
- **At every audit of this handoff, run the GEAK-family freshness sweep** in the deep dive §9 (GEAK repo pin/tag drift; missing gfx90a evidence for 677/678/679; AgentKernelArena leaderboard + GEAK-vs-general A/B; new AMD-native siblings on `AMD-AIG-AIMA`/`AMD-AGI`).
- **Done this session:** GEAK repo state recorded (HEAD `c8bfc19`, tags →`v4.8.3.3`, branches GEAK-v2/GEAK-HIP); AgentKernelArena ingested (intake-679). **Next intake candidates** if they appear: a GEAK-v2 arXiv, a GEAK-HIP open benchmark, the AgentKernelArena leaderboard.

## Research Intake Update — 2026-07-08: KernelBench (rec-007)

**Source**: KernelBench (intake-797, arxiv 2606.20128)

**Key finding**: Seeded fuzzing for kernel correctness catches 9/9 buggy kernels, passes 15/15 controls. Provides fine-grained kernel-level benchmarking substrate.

**Applicability to EPYC**: Directly applicable to the agentic kernel-authoring loop — serves as the C3 correctness verification substrate in the generate→compile→verify→profile→refine loop. KernelBench's seeded fuzzing methodology can catch correctness regressions in agent-generated kernels before they enter the profiling stage.

**Integration with existing C1-C6**: KernelBench maps to C3 (correctness) in our verification layer, complementing C4 (profiler-metric) and C6 (anti-reward-hacking). The seeded fuzzing approach is complementary to our GEAK-eval substrate.

- [ ] **AK-KB-1** — integrate KernelBench into GEAK-eval verification loop as C3 correctness substrate
- [ ] **AK-KB-2** — establish KernelBench baseline over current llama.cpp-HIP kernels

## Progress checklist

- [ ] Reproduce GEAK-eval (intake-674) on gfx90a MI210 - compile+correctness+timing round-trip (first sanity gate)
- [ ] Write P-GPU-1 measurement protocol before any GPU runs
- [ ] Register controllers (Claude+Codex, EvoEngineer, KernelFoundry, K-Search, Xe-Forge, GEAK) as AgentKernelArena adapters and A/B on gfx90a
- [ ] Build C4 gfx90a profiler-metric analyzer (GEAK-v2 raw-rocprof path first)
- [ ] Build C6 anti-reward-hacking layer (robust-kbench + AgentKernelArena unseen-shape)
- [ ] Run GEAK-family freshness sweep (deep-dive s9) at each audit
