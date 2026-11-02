# Agentic ROCm Kernel Authoring — MI210 Verify+Profile Harness

> **Fold destination** (BRF-T1-F23, BRF-T1-1, route 1a, 2026-11-02): absorbs 1 handoff(s) as `## Track:` sections at the end of this file (`mi210-q8-dequant-gemv-roofline.md`). The body above the first track is the former `agentic-rocm-kernel-authoring.md`.

**Scratch**: `/mnt/raid0/llm/tmp/isa-audit-runner-bind/` · worktrees: `/mnt/raid0/llm/worktrees/isa-audit-runner-*` (new runner-binding work; historical evidence paths remain unchanged)

**Status**: active investigation — hardware present; P-GPU-1 ratified. **Corrected 2026-08-10 (operator): P-GPU-1 governs the CLASS OF CLAIM a result may carry, not permission to run — the human boundary is freeze / cutover / promotion.** Benching or profiling a *live server* is still owned by whoever owns that inference. Every "operator-approved GPU runs" phrase below predates this correction; read it as claim-class, not permission.
**Next action (2026-08-22)**: preserve immutable r19, and keep the relayed C5-3..16/Hawkeye rows as
the authoring-loop backlog while INF-48 repairs the C6 launch boundary. Do not revive a gfx90a
taxonomy column, import NVIDIA strategies, use TCC hit rate as an objective, or make profiling a
prerequisite: the zero-profiler arm remains mandatory. Never resume r4-r18 or aggregate a partial
attempt into the panel.
**Created**: 2026-06-03 (via /research-intake deep-dive of the LLM-kernel-generation cluster) · **Updated**: 2026-08-12 (r19 live after copy-time staged-input binding)
**Categories**: hardware_optimization, agent_architecture, autonomous_research, tool_implementation, training_distillation
**Hardware gate — SATISFIED 2026-07-02**: AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB) is racked and the llama.cpp HIP build is verified on gfx90a (`progress/2026-07/2026-07-02-mi210.md`; memory `project_mi210_gpu_inference`). This program is now **ACTIVE**, priority **MEDIUM** — it is an *optimization*, **not a production blocker**: llama.cpp-HIP already serves ~910 tok/s @32-way as-is (2026-07-02 obs). First step = reproduce **GEAK-eval** (intake-674, arXiv 2507.23194) on gfx90a — compile+correctness+timing round-trip — as the sanity gate. **Scoping caveat (adversarially verified 2026-07-03; AMENDED 2026-08-03, see §"GEAK scoping — amended")**: GEAK **v4** retains first-class gfx90a knowledge, though all published *evaluation* is gfx942; **AgentKernelArena (679) / robust-kbench (668) are gfx942/CDNA3-listed** and must be treated as ports, not drop-in reproductions. All GPU runs remain operator-approved measurements per MEASUREMENT.md (write P-GPU-1 first). [was: "expected ~July 2026; nothing executes until the card racks" — stale after 2026-07-02 install] [was: "close the measured quantized-MMQ-dequant roofline gap: ~33% Q4_K / ~47% Q8 at batch-1" — **re-targeted 2026-08-03**, that is half the prize; see §"Program re-target"]
**Priority**: MEDIUM (activates on MI210; prep proceeds now)
**Workstream**: Inference Acceleration / GPU · **Parent index**: [`inference-research-index.md`](inference-research-index.md)
**Full reasoning + evidence**: [`research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md`](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md) ← the durable narrative; this handoff is the operational summary.
**Related**:
- [`rocm-verify-profile-backend.md`](rocm-verify-profile-backend.md) — **child**: the ROCm verify/profile/benchmark backend this loop drives
- [`exl3-cpu-mi210-implementation.md`](quantization-and-low-bit.md) — `INF-80` consumer of the
  gfx90a verify/profile substrate; EXL3 implementation and acceptance remain owned there
- [`gpu-drafter-mi200-investigation.md`](../archived/gpu-drafter-mi200-investigation.md) — MI210-gated; consumes the kernels this loop produces
- [`gpu-acceleration-path.md`](mi210-serving-program.md#track-gpu-acceleration-path) — the ROCm kernel-library hand-port path this automates
- [`llama-cpp-dsa-contribution.md`](gemma-challenge-kernel-techniques-v7.md#track-llama-cpp-dsa-contribution) / [`cpu-shape-specialized-gemv-decode.md`](../completed/cpu-shape-specialized-gemv-decode.md) — the hand-HIP endgame + the CPU ukernel loop this rhymes with

---

## Objective
Stand up an **agentic, train-free kernel-authoring loop for the installed MI210** — drive a strong coding agent through generate → compile → verify → profile → refine to produce and tune **HIP/Triton kernels** for the EPYC stack, replacing the manual hipify-and-hand-tune path. **We cannot retrain a kernel model on one MI210, but we can run a train-free verify+profile loop** — and AMD has already open-sourced most of the substrate (GEAK/Apex/AgentKernelArena), demonstrated on gfx90a.

## Current Decision Snapshot (2026-06-03)
The path *today* (supersedes any earlier "EvoEngineer/CudaForge-first" framing):
1. **Backend = adopt AMD-native code.** **GEAK-eval (674, MIT)** is the primary benchmark/oracle/timing substrate (C1/C2/C3/C5), reproduced on our gfx90a; **Apex (675, MIT)** supplies the E2E deploy harness + Magpie scorer; **AgentKernelArena (679, Apache-2.0)** supplies a second substrate + the controller-A/B shell. Net-new to us: **C4 + C6** (see child handoff).
2. **Controller-A/B = register adapters, don't build a harness.** AgentKernelArena (679) already ships Claude Code / Codex / Cursor / GEAK adapters with a `@register_agent` pattern — **register our controllers (Claude+Codex actor-critic, EvoEngineer, KernelFoundry, K-Search, Xe-Forge, GEAK) as adapters and A/B them on gfx90a.** It compares whole agents at task level, complementing each controller's inner loop.
3. **Agent backend = Claude+Codex actor-critic** (reuse the autopilot planner's infra); local coder role is the self-hosted fallback. `opensource_only` governs deployed services, not build-time tooling — the authored kernel is the artifact, not the LLM. Empirically favored: CudaForge's best result was a cross-model coder/judge split; AgentKernelArena's best results are Claude Code / Cursor / Codex.
4. **Triton first (on-ramp), HIP second (endgame).** GEAK-eval (Triton, gfx90a-proven) → then the HIP arm via GEAK-HIP patterns (678) + AgentKernelArena's Torch2HIP suite (679) + our own HIP oracle. Pairs with `llama-cpp-dsa-contribution.md`.
5. **Differentiators we own: C6 (anti-reward-hacking) + C4 (gfx90a profiler-metric).** Both now have an AutoKernel implementation. Paired `rocprofv2` is the op-level Q4_K/Q8_0 path; direct timestamp-only `rocprof` v1 is the governed whole-model fallback and completed K28 attribution. IQ2_XXS still requires the seeded Omniperf fallback after OP-11 gives its producer a durable identity.

**Why this is the decision (one paragraph):** the entire cluster was NVIDIA-bound at the toolchain, so a from-scratch ROCm backend looked like the long pole — until GEAK/Apex/AgentKernelArena turned out to be AMD-native, permissively licensed, and (for GEAK-v1) demonstrated on **gfx90a, the MI210's exact ISA family**. That predicts *compile compatibility* on our card (not performance — single-GCD bandwidth, ROCm version, autotune space, and harness details still need reproduction), which shrinks the program to "adopt + reproduce + add C4/C6." Full reasoning, alternatives, and the rejected paths: see the [deep dive](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md).

## Evidence — grouped by role (intake-660…679; details in the deep dive + `intake_index.yaml`)
| Role | Entries | Use |
|------|---------|-----|
| **AMD-native substrate (adopt)** | GEAK 674 (gfx90a-proven, MIT), Apex 675 (MIT), AgentKernelArena 679 (Apache-2.0) | C1/C2/C3/C5 backend + Magpie scorer + controller-A/B arena. **674 carries the only gfx90a *evaluation*; 675/679 are gfx942-listed/eval'd. But GEAK v4 carries first-class gfx90a *knowledge* — see §"GEAK scoping — amended".** |
| **AMD-native, patterns-only (gfx942-only)** | GEAK-v2 677, GEAK-HIP 678 | 677 → C4 Profiler-Analyzer (try first) + QD upgrades; 678 → HIP-arm loop (out-optimized a human engineer) |
| **Controller candidates** | EvoEngineer 666 (lead), KernelFoundry 669 (hw-awareness layer), Xe-Forge 672 (linear archetype), K-Search 673 (world-model tree, MoE-strong), GEAK 674 (first to stand up) | register as AgentKernelArena adapters; A/B on gfx90a |
| **C4 (profiler-metric) sources** | GEAK-v2 677 (raw rocprof→LLM, try first), Xe-Forge 672 (static KB), CudaForge 662 (formal selection) | the standing research risk |
| **C6 (anti-hacking) sources** | robust-kbench 668 (exploit classes, Apache-2.0), AgentKernelArena 679 (unseen-shape generalization) | the two complementary halves; our differentiator |
| **Eval philosophy** | KernelBench 664 (`fast_p`), FastKernels 671 (vendor baseline + whole-model gate) | weight end-to-end over isolated-op |
| **RL lessons (no training)** | CUDA Agent 660, CUDA-L1 661, Kevin 663 | reward design + anti-hack gates + multi-turn |
| **Optional offline later** | ConCuR 665, TritonForge 676 | SFT data-curation for a local HIP-specialized small model |
| **Not our path** | KernelCraft 670 (AIE-ML NPU/Peano, not ROCm) | harvested only: tool vocabulary + thinking-budget + ICL findings |

## gfx90a caveat (applies to every AMD number above)
Same `gfx90a` ISA **predicts compile compatibility, not performance equivalence.** GEAK-v1's MI250X results should *build and run* on the MI210 (wavefront=64/MFMA/LDS identical), but single-GCD bandwidth, ROCm version, autotune space, and harness details require reproduction. GEAK-v2 / GEAK-HIP / AgentKernelArena publish **gfx942/CDNA3 numbers only**, so their *numbers* carry even less. **All AMD numbers are vendor-reported until reproduced on our own gfx90a.** [was: "a coverage regression vs v1" — **retired 2026-08-03**: for GEAK proper this is unpublished coverage, not removed coverage; see below.]

## GEAK scoping — amended 2026-08-03 (research-intake Stage-2b; this IS the mandated freshness sweep)

_The prior caveat **understated** the dependency. The README's narrowing is a deployment/evaluation
statement, not a capability removal._

- README (verbatim, confirmed): *"GEAK targets AMD Instinct MI GPUs (CDNA, e.g. gfx942 / gfx950; the
  on-box card is auto-detected)"*. **All published evaluation is gfx942 — there are no gfx90a numbers.**
- **But the tree says otherwise.** `perf_knowledge/hardware/cdna2_mi200/` ships **four files**
  (`arch.md`, `matrix_core.md`, `memory.md`, `occupancy.md`), all `gens: [gfx90a]`, all
  `updated: 2026-06-08`, titled *"CDNA2 / MI250X / MI210 (gfx90a)"* — **our exact card, named**.
  `perf_knowledge/index/capability_index.yaml` carries **40 `gens:` entries including gfx90a**
  (vs 214 gfx942 / 225 gfx950 / 20 gfx908). `perf_knowledge/README.md` scopes CDNA1 → CDNA4.
- **No arch gating found** — the card is auto-detected; there is no allowlist rejecting gfx90a.
- **Correct formulation to carry forward:** *GEAK v4 carries first-class gfx90a hardware knowledge and 40
  gfx90a-applicable capability entries, but publishes zero gfx90a numbers.* **Pin `v1.0.0 @ 4ffba15a`**
  (Apache-2.0, still pinnable) for the paper's MI250X evidence. v1→v4 spans eight tags, 2025-08-01 →
  2026-07-22; repo active (pushed 2026-08-03).
- Caveat on the v1 evidence itself: **v1's release notes name only MI300X** — the gfx90a claim traces to
  the v1 **paper** (arXiv 2507.23194), not the release.
- This cuts *with* the grain of GEAK's own consumption contract, which states the KB is
  *"reference material… not decisions"* and that consumers must *"decide by on-box measurement"* —
  i.e. AMD is telling us to measure on our own card, which is exactly the standing unchecked sanity gate.
- **The KB is not error-free** — its `memory.md` ridge-point figure is off by 2× (per-GCD vs per-OAM); see
  [`mi210-mfma-compute-bound-paths.md`](../completed/mi210-mfma-compute-bound-paths.md).
- **Bonus, unexploited:** GEAK ships `languages/` docs on **hipkittens · tilelang · mojo · cutlass ·
  flydsl** and a `landscape/` section on multi-backend libs, DSLs, AI kernel agents, autotuning and
  "AMD SOTA 2026" — a **vendor-maintained survey of the exact taxonomy our Stage-2 dive built by hand**,
  available as an external check.

## Program re-target — aim at the fp16 rung, not the Q8 rung (2026-08-03)

The old objective closed *"~33% Q4_K / ~47% Q8"*. **That is half the prize.** The fp16 rung — **62.6%
attainment — is demonstrated on our own device**, and vLLM-ROCm reaches **69.2%** on the same silicon;
DGX Spark GB10 reaches **77–80% at Q4_K_M dense across five models** on the same engine. The full ladder
and its calibration caveat live in
[`mi210-q8-dequant-gemv-roofline.md`](agentic-rocm-kernel-authoring.md#track-mi210-q8-dequant-gemv-roofline).

**Banded ceiling, for sizing campaigns** (bands, not point estimates; confidence stated):

| Lever | Band | Confidence |
|---|---|---|
| **K1 Q4_K → Q8 rung** | **+38–43%** | HIGH |
| **K5 batched elementwise/norm fusion** | **0 — CLOSED_NO_GO** | CERTAIN for frozen-v9 target selection: strict B=64/128 norm + activation + elementwise share is 1.837% / 1.490%, far below the predeclared 20% floor; the old 43% bucket conflated gather/recurrent/copy work |
| K2 Q4_K → fp16 rung | +60–80% | MEDIUM |
| K3 MoE expert-gather | ~2.0× | MEDIUM |
| K4 architect IQ2 | +2–3× | MED-LOW — attach the gfx906 kill-criterion first |
| K6 fp16 batch-1 | +11% | HIGH |
| K7 HIP graphs | +5.9% | banked already |
| K8 LDS prefetch | ~0 remaining | CDNA2 ceiling |
| **K9 MFMA decode kernels** | **0 — DO NOT BUILD** | CERTAIN (arithmetic, not counters) |
| K10 prefill | +20–30% | MEDIUM |
| **K11 closing the vLLM gap** | **not a kernel program** | see AK-D36 in `autokernel-research-loop.md` §17 |
| **K12 matching Blackwell prefill** | **unreachable** | 5.6× int8 silicon deficit |

**Prefill is mid-pack, not an AMD software problem.** MI210 converts 19–29% of matrix peak; A100 22.8%,
RTX PRO 6000 22–44%, H100 15.3%, MI300X 12.3%. **Prefill kernel *quality* is not the gap; prefill
*silicon* is.**

## New index-backed leads — 2026-08-03 (research-intake Stage-2b)

- **ARGUS (arXiv `2604.18616`) — register as a controller candidate.** Agentic GPU kernel optimisation
  reaching **99–104% of hand-optimised assembly on AMD MI300X** for GEMM / FlashAttention / MoE;
  2–1543× over prior agentic systems; 100% KernelBench L1, 90% L2. **Absent from all six MI210/autokernel
  handoffs.** Directly on-point for the controller A/B — and, being MI300X, it is CDNA3 evidence that
  still tells us what an agentic loop achieves against *AMD's own* hand-tuned assembly.
- **HipKittens fragment-layout identity — a free compositional result.** HK's `rt_base` is **bit-identical**
  to `ggml/src/ggml-cuda/mma.cuh`'s `tile<16,16>` in our frozen v8 (`:127,144` — `get_i = tid%16`,
  `get_j = 4*(tid/16)+l`, `ne=4`). Every HK technique composes onto our existing fragments with **zero
  layout re-derivation**. The arch-independent lessons are filed in
  [`mi210-mfma-compute-bound-paths.md`](../completed/mi210-mfma-compute-bound-paths.md); do **not** vendor the framework.
- **A live gfx90a build arm already exists** on HK's `cdna3` branch (`GPU_TARGET=CDNA2` →
  `-DKITTENS_CDNA2 --offload-arch=gfx90a`, `tests/unit/Makefile:39-40`). Across all 67 headers the library
  uses exactly **six** `__builtin_amdgcn_*` intrinsics and **exactly one is unavailable on gfx90a**
  (`mfma_f32_16x16x32_fp8_fp8`, `mma.cuh:47` — non-template static inline, so it needs an `#if` guard).
  That arm carries a **~3000-test correctness harness** that would run on our silicon. This is what makes
  the *decline to port* a decision about economics rather than capability.
- **A runnable LDS bank/phase solver** — `analysis/paper_experiments/phases/*/{bank_solver.py,
  phase_solver.py, kernel.cpp}`, a 45-line kernel over rocprofv3 PMC counters, ~40 min GPU on gfx90a.
  **Do not assume the CDNA3 answer (64 banks / 2 phases of 32 lanes) transfers** — whether gfx90a is 32 or
  64 banks decides whether HK's `>>7 <<3` swizzle constants transfer at all. Blocked on profiler tooling
  (below). ~~Still blocked as of 2026-08-12 (mainB)~~ — **RESOLVED, and this line is the mis-stamp.**
  The solver **ran on 2026-08-11** via a rocprofv2-compatible counter path (receipt SHA-256
  `ae1d833c…`, 372 bank / 6,048 phase dispatches, 32 banks + 8 phase cliques). `rocprofv3` really is
  absent — that half of the 2026-08-12 check stands — but it was never required: **this line names an
  instrument the run did not use.** Nothing was blocked. Corrected 2026-08-12 (mainB).

- **`rocm-flash-attn` as an enabling path**, re-assessed: an adaptation layer with no kernel code of its
  own, but genuine tested code with honest defect annotations. Judged on whether it improves performance,
  not on whether it contains kernels.
- **Two operational levers from AMD's own ROCm llama.cpp blog:** hipBLASLt grouped-GEMM plus tuning
  (**+29%**) and ~10× fewer `hipMemcpyAsync` calls.
- **llama.cpp issue #19984 — an LLVM loop-unroll regression in ROCm 7+ costing 3.7–5× on prefill**,
  workaround `-mllvm --amdgpu-unroll-threshold-local=600`. We are on ROCm 6.2 so this does not bite today;
  it belongs on the build-flag checklist **before any ROCm upgrade**.
  **Corrected 2026-09-15 (intake-969/1414/1424):** root cause is llvm #147700 (unroll cost model, not a
  threshold change), scoped to ROCm 7.2.0 + early TheRock 7.x nightlies and reverted; decode unaffected;
  do not cite 3.7–5×. Updated guard lives in `docs/runbooks/rocm-upgrade-checklist.md`.

**Profiler tooling — RESOLVED FOR THE CURRENT C4 AND LDS SURFACES.** `rocprofv2`, `rocprof` and
`rocm-bandwidth-test` are available, version-matched to ROCm 6.2.0-66, side-loaded by extraction
rather than installed so nothing in the shared `/opt/rocm` bind mount changed:
`source /mnt/raid0/llm/tools/rocm-profilers-6.2/env.sh`. **The gfx90a counter taxonomy is proven** —
465 counters across 12 blocks, enumerated on our own card, including every counter this program
already cites. Details, per-block collection limits, and the two path quirks:
[`rocm-verify-profile-backend.md`](rocm-verify-profile-backend.md). This unblocks C4's existing
`rocprofv2` path. The LDS solver was also successfully adapted to rocprofv2; its r4 receipt binds the
exact commands, tool and binary hashes, 372 bank dispatches and 6,048 phase dispatches. `rocprofv3`
remains absent but is not a blocker for that completed surface. The governed IQ2 Omniperf fallback
remains separately gated by the OP-11 producer identity.

- [x] Resolve the side-loaded ROCm 6.2 profiler-tool availability for C4. ✅ 2026-08-12 — live
  version checks confirm `rocprof`/`rocprofv2` at ROCProfiler 2.0 and a runnable argument parser for
  `rocm-bandwidth-test`. These tools are intentionally absent from the default PATH and `/opt/rocm`.
- [x] **Establish whether the LDS bank/phase counters are reachable through `rocprofv2`.** ✅
  2026-08-12 — reconciled against the already-terminal r4 empirical receipt: rocprofv2 captured 372
  bank and 6,048 phase dispatches and the solver derived 32 banks plus eight phase cliques. Receipt
  SHA-256 `ae1d833c704bdae9a78767d0fc0b927298d6d1dfdb31a0ea11c34058dc525987`.

## Open questions (decided ones live in the deep dive §5)
- Which controller wins on gfx90a? Unknown until the AgentKernelArena A/B runs on the MI210 with EPYC ops.
- Does GEAK-eval's published MI250X speedup reproduce on the single-GCD MI210? The substrate-level
  compile/correctness/timing round-trip now passes on physical gfx90a; the published task suite and
  matched controller-performance comparison remain separate empirical questions.
- Does C4's cheapest path give a usable signal on CDNA2? **Answered 2026-08-11: yes at op level,
  not as a whole-model `rocprofv2` capture on this host.** The deterministic report resolves the
  Q4_K/Q8_0 fill → requantize → matvec sequence and emits 1%-floor wall shares. Whole-model Qwen
  prefill and IQ2_XXS op captures reproducibly exit 139 inside the profiler; these are tool-scope
  limits, not zero-work readings. AutoKernel consumes only the deterministic report, never raw
  profiler text.
- Will AMD publish gfx90a numbers / arXiv papers for GEAK-v2 / GEAK-HIP / AgentKernelArena? → Freshness Appendix in the deep dive.

## Reporting / maintenance instructions
- After any work: update the **Current Decision Snapshot** here + the deep dive; log progress in `progress/YYYY-MM/`.
- **At every audit of this handoff, run the GEAK-family freshness sweep** in the deep dive §9 (GEAK repo pin/tag drift; missing gfx90a evidence for 677/678/679; AgentKernelArena leaderboard + GEAK-vs-general A/B; new AMD-native siblings on `AMD-AIG-AIMA`/`AMD-AGI`).
- **Done this session:** GEAK repo state recorded (HEAD `c8bfc19`, tags →`v4.8.3.3`, branches GEAK-v2/GEAK-HIP); AgentKernelArena ingested (intake-679). **Next intake candidates** if they appear: a GEAK-v2 arXiv, a GEAK-HIP open benchmark, the AgentKernelArena leaderboard.

## Research Intake Update — 2026-07-08: KernelBench (rec-007)

**Source**: KernelBench (**intake-664#record**, arXiv:2502.10517)

> **⚠ CORRECTION 2026-08-10 — this attribution is wrong, and was already corrected elsewhere.**
> The identical line in [`mi210-speed-campaign-summary.md`](../completed/mi210-speed-campaign-summary.md)
> carries a verified 2026-07-22 correction that never propagated here: this is a **three-way
> conflation**. The real **KernelBench** is Stanford ScalingIntelligence **arXiv:2502.10517**
> (kernel *generation*, metric `fast_p`), confirmed via intake-660/661. `arXiv:2606.20128` is a
> separate seeded-fuzzing paper, and `intake-797` was never either of them — it was
> "Externalization in LLM Agents" (now merged into intake-418). The 9/9 seeded-fuzzing finding
> below belongs to the 2606.20128 paper. Surfaced while auditing references to merged intake ids.

**Corrected disposition**: the seeded-fuzzing result belongs to a separate paper and maps to **C2
(correctness)**, not C3 (timing/reward). Its useful design rules—stateful-op coverage, adversarial and
non-power-of-two extents, absolute-duration gates, speed-of-light rejection, and anti-reward-hacking
checks—are already implemented natively in AutoKernel's C2/C6 surfaces. KernelBench itself is an
isolated PyTorch operator suite, not a baseline corpus for current llama.cpp HIP kernels.

- [x] **AK-RB-1** — adopt RE-Bench's SCORING PROTOCOL for gfx90a kernel-agent evaluation, not the
      benchmark itself (intake-1072, filed 2026-08-10). Transferable: log-time scoring of
      behaviour-preserving optimization, 0 = starting state / 1 = a strong reference solution, and
      time-budget curves (2h/8h/32h) rather than pass-fail. NOT worth standing up as-is — only 1 of 7
      environments is a kernel task, it is Triton on H100, and porting to gfx90a invalidates the
      published human and model anchors that are the reason to use it. ✅ 2026-08-11 — implemented
      reference-normalized, deliberately unclipped log-time scores; behavior failures withhold reward;
      matched best-so-far curves emit at 2h/8h/32h in
      `scripts/kernel_rnd/autokernel/evaluator/rebench_scoring.py`.
- [x] **AK-KB-1** — audit KernelBench for the GEAK-eval **C2** correctness surface ✅ 2026-08-11 —
      declined the incompatible task artifacts (current first-party HIP is gfx942/gfx950 and ROCm 7.1+),
      while retaining the already-native correctness and anti-hacking design rules above. The live
      gfx90a GEAK/AgentKernelArena round-trip is the compatible C2/C5 substrate.
- [x] **AK-KB-2** — establish the correct baseline disposition for current llama.cpp HIP kernels
      ✅ 2026-08-11 — retired the category error: exact-surface llama.cpp baselines and historical C5
      replay are authoritative; translating them into isolated PyTorch KernelBench tasks would change
      the unit under test and cannot establish a production-kernel baseline.

## Progress checklist

- [x] Reproduce the GEAK/AgentKernelArena compile+correctness+timing round-trip on gfx90a MI210
  (first sanity gate) ✅ 2026-08-11 — the exact-pinned adapter refused gfx90a spoofing, compiled the
  live add-kernel arm under Torch 2.5.1+ROCm 6.2 / Triton 3.1.0, passed correctness 3/3 and timing
  harness 5/5 on the physical MI210, and released its device claim. Receipts:
  `/mnt/raid0/llm/autokernel/probes/inf03-geak-arena-gfx90a-preflight-20260811/receipt.json`
  (SHA-256 `256a4c60a416828a1299a35d8399609c3c5ad2541272ab41de40dd00f2f297a4`) and
  `/mnt/raid0/llm/autokernel/probes/inf03-geak-arena-add-roundtrip-20260811/receipt.json`
  (SHA-256 `aee866ee3ebd2fe88b37185f4226c3c20a5b439c60a40fac57ef1bb42898be8c`). This closes compatibility,
  not the published-suite speedup reproduction.
- [x] Write P-GPU-1 measurement protocol before any GPU runs ✅ 2026-07-29 — human amendment ratified the canonical MI210 GPU protocol in [`MEASUREMENT.md`](../../MEASUREMENT.md#p-gpu-1--mi210-gpu-canonical-throughput-ratified-2026-07-19) on 2026-07-19; this closes protocol authoring only, not any GPU run or decision claim.
- [ ] Run the matched controller-authoring A/B on gfx90a across the registered Claude+Codex,
  EvoEngineer, KernelFoundry, K-Search, Xe-Forge, GEAK, ARGUS, and baseline arms. Registration,
  C4 prompt-hygiene binding, and the three-argument `@register_agent` bridge are complete in
  research commit `48350b24`; the full-panel implementation now refuses honestly at 6/8, and the
  matched eight-arm comparison waits only on the two unavailable licensed source releases.
  - [x] **Build the governed eight-arm campaign driver and audit executable coverage.** ✅ 2026-08-11
    — baseline plus Claude/Codex actor-critic, EvoEngineer, KernelFoundry, K-Search, Xe-Forge,
    GEAK-v1, and ARGUS are serialized on one MI210 at exact 2h/8h/32h checkpoints with source,
    entrypoint, executable, model, configuration, and driver hashes. The physical audit correctly
    refused before launch because only **1/8** arms was executable at the initial audit; baseline is
    explicitly a zero-hour non-authoring control. Audit receipt:
    `/mnt/raid0/llm/autokernel/probes/inf03-controller-ab-audit-20260811/receipt.json`, SHA-256
    `3152e2fa97b52d9f0b91fb43449375adec66128189fddf253b0772fadfcf59c4`; research
    `429b59a1` (promoted via `ee54c144`).
  - [x] **Provision the internal Claude-planner/Codex-actor arm.** ✅ 2026-08-11 — the exact
    three-argument Arena callable and stdin executable pin Claude Opus 5/high as planner+critic and
    GPT-5.6-Codex/high as actor, enforce exact 2h/8h/32h checkpoints plus captured process-group
    termination, confine all writes to one candidate inside the Arena workspace, and hash-bind the
    CLIs, prompts, transcripts, candidate, artifacts, and final receipt. The clean physical audit now
    admits exactly **2/8** arms (baseline plus this controller); the other six refusal rows remain
    verbatim. Implementation `dcdc2311`, binding `084b8be1`, research main `9947f805`; 409
    controller tests and 17 AutoKernel README tests pass. Neither CLI was invoked during
    implementation or audit.
  - [x] **Build the governed Arena cell runner.** ✅ 2026-08-11 — research `36ed94a8` and
    `cffd3b02` provide direct belief receipts, process-group teardown, workspace confinement, and
    a no-inference test surface for upstream controllers; the original validation passed 129 tests
    plus eight subtests.
  - [x] **Port and bind K-Search without replacing its search policy.** ✅ 2026-08-11 — research
    `866855a3`, `832f6833`, and `2ceb2878` retain the exact upstream source pin
    `53c8fab9a5e8fab2c86610d24fbec5067f90e115` and put the governed adapter on the fixed campaign path.
  - [x] **Port and bind GEAK-v1 without replacing its evolutionary loop.** ✅ 2026-08-11 —
    research `38b8e07e` and `60cae5bf` retain exact upstream source pin
    `4ffba15a55f250816598b4e27eb56ca40a699cea`, safe cleanup, and direction-preserving receipts on
    the fixed campaign path.
  - [x] **Port, bind, and repair Xe-Forge.** ✅ 2026-08-11 — research `d76fe4b9`, `af5d026a`,
    `1bd5ec75`, and wrap repair `e31cc8c8` retain exact source pin
    `4dcb5080b0f56d0b655ec8c8c9509b8e3ba0382c`; the real-upstream regression proves AMD-only
    prompts, refuses fabricated shapes, and closes the executor cleanly.
  - [x] **Port KernelFoundry and preserve its governed MAP-Elites/QD behavior.** ✅ 2026-08-11 —
    research `7654383c` plus wrap repair `e31cc8c8` retain exact upstream source pin
    `1c053e02383d12937f144923bcc1faa82fa7788f`, activate 159 missing Triton regexes, and prove a real
    inherited 2x2 fixture with two occupied cells, four programs, two QD transitions, and one
    direction without model, GPU, or inference.
    The selected AutoKernel suite passes 538 tests plus 202 subtests at the repaired tip.
  - [x] **Bind KernelFoundry and produce the final no-execution full-panel audit.** ✅ 2026-08-11 —
    research `58c4e332` through `26ad6178` binds all six available arms and emits a clean physical
    gfx90a refusal at **6/8** before any controller or GPU command. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-final-audits-20260811-Kpg5wU/full-eight-arm-refusal.json`
    carries receipt SHA-256 `3f67b750c99dccbbe45f5c0043c8aa11973c3e014ab3610bb117786f60a79f7f`
    and file SHA-256 `b432fcb802797136444b510618966489529147aac60d73209b0c1ee946231b1d`.
  - [x] **Add and audit the separately governed available-source panel.** ✅ 2026-08-11 — the same
    pinned task, evaluator, identities, and 2h/8h/32h budgets are ready at **6/6**. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-final-audits-20260811-Kpg5wU/available-source-six-arm.json`
    carries receipt SHA-256 `d812b69ce380613bd854dd0d15206c09981899abac11b10234a8f98bb02482b8`
    and file SHA-256 `88101db4f28f909f220acb3bf906f488fe8b4f8e7c307821d325a5542fd4627d`.
    Its authority is availability-conditioned and diagnostic only: it cannot imply an eight-arm
    result, rank partial full-panel evidence, or authorize promotion. No inference ran in the audit.
  - [x] **Run a real KernelFoundry diagnostic smoke and repair the launch boundary it exercised.**
    ✅ 2026-08-11 — v1 found that copied task workspaces lacked the immutable repository import root;
    v2 passed import and two real GPT-5.6 Sol/high calls, then found concurrent branches racing in
    the shared Arena evaluator. Research `f8569112` and `8afd016c` repair both boundaries. V3 passed
    compilation, correctness, and all 4/4 baseline plus 4/4 optimized timing cases under a cleanly
    released MI210 claim. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-kernelfoundry-real-smoke-v3-20260811-Mg6Fl9/smoke-receipt.json`
    carries receipt SHA-256 `cd61675e83040b196a92aa85f2c0bd951f34912bef10a37e1b07f41864f52276`
    and file SHA-256 `9b47fefcb2744392923745385053aa6ee9a8a959102a17acb7eaea079a1be5b1`.
    Its `0.9986680991832163` average speedup is diagnostic and non-rankable, not a campaign result.
  - [x] **Run one-iteration diagnostic smokes for K-Search, Xe-Forge, and GEAK-v1.**
    ✅ 2026-08-11 — all three terminal runs passed centralized compilation and correctness plus
    4/4 baseline and 4/4 optimized timing cases, then released their MI210 claims. K-Search receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-k-search-real-smoke-20260811-tQf7zZ/smoke-receipt.json`
    has receipt/file SHA-256 `6eea9028399635083a6aed7a4d0101aa106cc4393e4225dd768c6f27c23e7704` /
    `74f49b472dcb6b2eed1cef66e706e9471ea67f71c94de7a8ba046e3bcd7520b7`; Xe-Forge receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-xe-forge-real-smoke-20260811-NIffwN/smoke-receipt.json`
    has `a53ef172b42d3fbb6008902a865eac9c884d181a6cc0fc0cc981f9e8aad1ccae` /
    `e82917d9f1f751520317700520f33b7bf62dd372749ef18ce3d822ba5b2806ea`; GEAK-v1 receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-geak-v1-real-smoke-v3-20260811-RJ4UYN/smoke-receipt.json`
    has `0deef125d026625055e77a63270c444101fd96ce5f6f9b2fce433e47b509a229` /
    `a4c30029a38011cfc7ca0b59be1eb826463cc336322db57e7d6b2cdea19d7487`.
    Their near-1.0 speedups are non-rankable smoke telemetry, not comparative evidence.
  - [x] **Complete the Claude/Codex actor-critic diagnostic smoke through its confined actor path.**
    ✅ 2026-08-11 — v1–v4 exposed fenced-JSON parsing, contained absolute-path handling, nested
    sandbox, and Docker-stdin defects. Research `84e2f948`, `dd0daedd`, `da677443`, and `22e60940`
    repair them while keeping the actor in a digest-pinned, read-only-root container with one
    writable workspace bind, dropped capabilities, no-new-privileges, exact teardown, and ephemeral
    auth. V5 completed planner, actor, and critic and reached centralized evaluation, but the worker
    inherited `/usr/bin/python3` without pytest. Its apparent correctness failure and zero timing
    cases are therefore an evaluator-runtime defect, not candidate evidence. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-actor-critic-real-smoke-v5-20260811-2Oo2cJ/smoke-receipt.json`
    has receipt/file SHA-256 `dcb2da77bf691c670b705149bfaec0bf6e8062594cd4297ac3247037da5937fb` /
    `e890240fa4e3e5134c2975f77930bf5a611e3db285dea2f01a9560d5b699d0d3`.
    The cleanly released 457.02 s MI210 claim retained 1,829 samples. Research `a57feba0` then pinned
    the ROCm evaluator Python/package identity and made mismatch a refusal. V6 passed compilation,
    correctness, and 4/4 baseline plus 4/4 optimized timing cases, reporting diagnostic speedup
    `0.9936027407797491`. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-actor-critic-real-smoke-v6-20260811-3hAJir/smoke-receipt.json`
    has receipt/file SHA-256 `5961eef441e487e787310d3bea9d4e57693a8f7a621dff1cc39190d48d952ef9` /
    `816ecc2d60ee48e8b0be3c6fb05ff1d562d7283697f1def9499ce6d0a98a916c`.
    The nested controller receipt has SHA-256
    `fa11ee8162fb6da877358a0c26c67d58d84c75b6c284fe9ee53540bb3673e315`.
    Its cleanly released 158.72 s claim retained 635 samples; the result remains non-rankable.
  - [x] **Refresh the campaign pins to the validated controller trees and repeat both static audits.**
    ✅ 2026-08-11 — clean detached research `6233cd42` binds the actor pin
    `a57feba0`/`e223a9cd26184aff5df7e24ceafebd53dab7cb1ab712a92c4bf82ca7712d9213` and GEAK pin
    `743f59df`/`7418493b4322f1be0df76be21686a6e0d48f43f27e0198a0db55b915f27516a7`.
    The full-panel receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-final-audits-v2-20260811-v6/full-eight-arm-refusal.json`
    has receipt/file SHA-256 `4a13f7d0ba91c2610efae4e51bcf7e0be8661d07657f74fecf9a5ee0a4dab3af` /
    `199e4e129daf561f42d59750a1c2e157da340f433c0fec3abf19cf7c1bd91195` and refuses
    at 6/8 only for external EvoEngineer and ARGUS. The available-source receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-final-audits-v2-20260811-v6/available-source-six-arm.json`
    has `cf8b03df355a8124a1dd668293c1d7d6e839c9f176aebdcd082f073f92ba0581` /
    `625280fb92b678b8a2a24f15f9a87484a2409c0dcb94e32a777e613639f327ed` and is
    ready at 6/6. Neither audit ran a controller or GPU command.
  - [x] **Bind a representative four-task EPYC Arena campaign instead of an add-only proxy.** ✅
    2026-08-12 — research `99fe3014` hash-pins the existing add control plus real
    `attention_llama`, `moe_gemm`, and `dequantize_matmul` task files under the same MI210/gfx90a,
    elapsed-wall-time, 2h/8h/32h, and one-GPU-cell contract. The available six controller arms keep
    their exact implementation/source/license hashes; EvoEngineer and ARGUS remain explicitly
    unavailable rather than receiving namesake substitutes. This is static campaign authority only;
    no controller, model, or GPU command ran.
  - [x] **Re-audit the available-source panel against the current integrated research source.** ✅
    2026-08-12 — the static audit at research `5c8714a1` reports `status=ready`, **6/6** executable
    arms, all four representative tasks ready, a physical `gfx90a` MI210 identity, and the fixed
    elapsed-wall-time 2h/8h/32h budget. It preserves the separate 8-arm refusal for unavailable
    EvoEngineer and ARGUS sources and grants no ranking or promotion authority. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-available-source-reaudit-20260812-r1/receipt.json` carries
    self-hash `7c670931628b17a1491d7f25642681f2ee17d996848c0b09032518ad58e08d5a` and file SHA-256
    `e86fbe4a4fb3f45d28d0a9ca7a62be97e021bdf710b5e2f4d7b2287644f0a623`. No controller,
    inference, build, or GPU command ran.
  - [x] **Make the available-source campaign restart-safe before spending the 2h/8h/32h
    budgets.** ✅ 2026-08-12 — research `971e3a00` verifies immutable audit/config/source identity,
    atomically records completed cells and checkpoints, resumes only exact hash-matched terminal
    work, and rejects partial, tampered, in-flight, or claim-leaking state. Focused campaign tests
    passed **139/139**. Resume does not make partial results rankable; the terminal aggregate remains
    the only campaign result.
  - [x] **Repair Arena workspace containment and guaranteed device-claim release before restarting
    INF-03.** ✅ 2026-08-12 — Research `b84c809f` uses collision-bound dot-free cell components,
    rejects dot-bearing ancestor paths, compares exact post-worker cell/sibling manifests on success
    and failure, and defers TERM/INT across claim acquisition so teardown journals the release. The
    focused runner/claim suite passed 68/68 after promotion. The invalid r1 attempt had exposed a
    dotted-path escape: the task's
    `__file__.replace('.', '_')` wrote `test_add_kernel_py.pt` into an adjacent sibling cell tree.
    Reject writes outside the exact workspace after every evaluator/controller step, normalize cell
    paths safely, and release/journal the device claim from a SIGTERM-safe `finally` path. Add
    regression tests for dotted task ids, external writes, and exact-signal cleanup before r2. The
    r2 baseline then completed in the dot-free hash-bound cell without creating an escaped sibling;
    its first controller checkpoint started only after that live containment regression passed.
  - [x] **Enforce the exact planner/critic response schemas at the provider boundary before spending
    another INF-03 checkpoint.** ✅ 2026-08-12 — r2 is immutable and invalid: its baseline completed
    safely, but the first Claude planner returned structurally valid JSON with extra fields that the
    strict four-field parser correctly refused. Research `298bab0c`, pin advances `98f7658f` and
    `6f599ed0`, plus the fresh r3 audit now bind provider-enforced planner and critic schemas without
    weakening the parser. Focused actor/critic tests passed **21/21** and the controller slice passed
    **540/540**. The r3 audit is ready at **6/6** over four tasks with authority still limited to an
    availability-conditioned diagnostic; self-hash
    `b8d966ee7581f2a2fe4ee7e8c2eb7e314514bc4f888f22635dfa23d9ec4ce6dc`.
  - [x] **Stop INF-03 r4 and preserve it only as invalid diagnostic history after auditing its
    intermediate feedback path.** ✅ 2026-08-12 — the captured campaign processes were terminated
    by exact PID and confirmed dead; no MI210 claim remained. The immutable partial root is
    `/mnt/raid0/llm/autokernel/campaigns/inf03-available-source-six-arm-20260812-r4`, bound to manifest
    self-hash `941fece21400362f41772682ec2cf8e3162b08488183a767dce276209ec61eaf`. It retains **5/64
    checkpoints**, **2/24 cells**, **10/10 released** vendor/final windows, 215 samples, and 52.588
    claimed GPU-seconds, but it is not resumable, rankable, aggregatable, or valid controller-comparison
    evidence. KernelFoundry's receipt records 64 intermediate centralized evaluations; the evaluator
    log records 64/64 correctness failures. Those calls ran from the deliberately GPU-blind controller
    environment outside the only two durable claim windows, so the controller received invalid search
    feedback even though its final checkpoint receipt was structurally complete.
  - [x] **Broker every intermediate controller evaluation through the parent worker's exact-PID
    boundary.** ✅ 2026-08-12 — integrated research `70a0d254` + `de7214ee` make the parent own an
    authenticated AF_UNIX broker and every intermediate/final evaluation. The broker verifies the exact
    registered peer PID/start ticks, accepts bounded candidate bytes, and the parent evaluates each
    request in a fresh GPU-capable deny-network subprocess under its own serialized MI210 claim. Neither
    controller nor candidate receives a claim credential. Request/result/baseline, sampler, claim,
    subprocess, activation, and teardown receipts are rehashed during durable restore.
  - [x] **Enforce controller/candidate OS isolation before a decision-bearing INF-03 pilot.** ✅
    2026-08-12 — research `9480a1b3`, `9a17e638`, and `de7214ee` wire every non-baseline Arena cell
    through an exact-read/exec controller sandbox with one inherited peer-bound broker socket, no ROCm
    device access, no campaign-sibling access, cgroup-owned descendants, and durable activation/teardown
    evidence. Candidate evaluation runs separately in a fresh deny-network evaluator sandbox; the parent
    alone owns the claim, sampler, and subprocess. The integrated focused warning-strict suite passed
    **95/95**, the pinned EvoEngineer suite **11/11**, and the pinned controller suite **572/572**.
  - [x] **Exercise the governed one-task/K-Search pilot through its first real Codex request and retain
    every fail-closed attempt.** ✅ 2026-08-12 — research branch
    `integrate/inf03-isolation-merge-20260812` at `569a8c42` added the explicit
    `epyc.autokernel.arena_diagnostic_pilot.v1` authority, a pilot-only one-round K-Search override,
    exact task-source discovery, narrow controller import/runtime/ELF/Git/null-device grants, and a
    workspace-local ephemeral Codex home that is scrubbed during teardown. The immutable probe ladder is:

    | Attempt | First fail-closed boundary | Disposition |
    |---|---|---|
    | r1 | task contract omitted `source_file_path` | fixed by deterministic instruction-task source discovery |
    | r2-r3 | sandbox could not import the controller module at the declared package root | fixed by the exact `scripts/` import root and below-root module identity |
    | r4-r5 | Python extension closure was incomplete (`libffi.so.8`) | fixed by exact extension/ELF dependency admission |
    | r6-r7 | the selected Python environment could not import `yaml` / the pinned Arena evaluator | fixed by binding the governed K-Search Python and exact venv package root |
    | r8 | exact source verification could not start `git` | fixed by admitting the exact executable and ELF closure |
    | r9 | Git could not open `/dev/null` | fixed by admitting only the null device; KFD/render remained denied |
    | r10 | ambient system/global Git configuration paths were denied | fixed by `GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL=/dev/null` |
    | r11 | Codex could not initialize under the read-only host `CODEX_HOME` | fixed with an ephemeral, workspace-local auth/config projection that is scrubbed on exit |
    | r12 | the real Codex client started, attempted the response request, retried five times for about 60 seconds, then failed with `Operation not permitted` while sending to the responses endpoint | fixed by binding the exact sandboxed Codex launcher |
    | r13 | the terminal controller path passed, but a stale controller null-device validator rejected its governed `/dev/null` grant | immutable invalid validator attempt; fixed in research `fe33954e` |
    | r14 | the controller path passed again, but a stale evaluator validator rejected the deny-network evaluator's exact device set | immutable invalid validator attempt; fixed in research `aa2020ab` |
    | r15 | one task / one K-Search round completed through six `gpt-5.6-sol:high` calls, one brokered intermediate evaluation, and the final evaluator | terminal compatibility-only receipt; no campaign/ranking/belief/promotion/release authority |

    R1-r14 remain immutable, non-rankable engineering history. R15 is a terminal compatibility pilot,
    not a campaign result: its final ratio `1.0019039030` and brokered intermediate ratio
    `1.0033912745` are diagnostic telemetry only. The terminal receipt is
    `/mnt/raid0/llm/autokernel/probes/inf03-mi210-isolated-k-search-pilot-20260812-r15/diagnostic-pilot-receipt.json`
    (self-hash `3425cf579a9d6fb06f5ed76b480ae652eaed3b3685eec9116299d253528a8771`,
    file SHA-256 `eb53de389450ba6ef800528a0da6f54c8508eabc39b4357f0cd9beff64aacefa`).
  - [x] **Resolve the r12 sandboxed Codex transport denial with least additional authority, then rerun
    the identical one-task/K-Search diagnostic pilot.** ✅ 2026-08-12 — research main `15c61ed5`
    binds the exact sandboxed Codex launcher (`45b82bbc`) and carries the r13/r14 validator repairs
    (`fe33954e`, `aa2020ab`). R15 completed six model calls, non-null brokered feedback, exact
    controller/evaluator activation, three matched claim/release and sampler windows (11/21/21
    samples), scrubbed ephemeral CLI state, empty/removed cgroups, and a terminal receipt. Controller
    access remained `/dev/null` only; both evaluators used deny-network sandboxes with exact GPU
    devices. Full merged validation passed 578 tests plus 202 subtests; footprint/readme checks passed
    106 plus 6 tests.
  - [x] **Project the diagnostic-pilot v1 contract and pre-receipt failure posture into the Kernel-R&D
    dashboard.** ✅ 2026-08-12 — the hub now reads the newest terminal pilot receipt, verifies its
    self-hash and explicit no-authority constraints, and renders PASS, broker/model/evaluation/window/
    teardown facts under a loud no-campaign-authority boundary.
  - [x] **Retract the reported all-tree discovery parser collision after reproducing its exact test
    context.** ✅ 2026-08-12 — `test_live_controls.py` intentionally invokes mutually exclusive
    `--evaluate-existing` and `--execute` arguments inside `assertRaises(SystemExit)`; the argparse
    stderr is the expected assertion surface, not an import-time collection abort. Discovery with both
    strings in `sys.argv` collected **3,927** tests, and an AST sweep found zero module-scope
    `parse_args` calls in AutoKernel. No parser repair is warranted.
  - [x] **Trace and repair one reproducible Claude/Landlock startup failure outside the campaign.**
    ✅ 2026-08-12 — local, unpushed research commit `916cdc92` adds ten fixed volatile read paths,
    stages only Claude credentials/config with identity hashes, scrubs the
    staged config, keeps `/dev/urandom` read-only, and excludes volatile reads from stable identities.
    The bounded standalone Claude probe returned structured `{"ok": true}`, left an empty/removed
    cgroup, and retained activation/result/teardown evidence under
    `/mnt/raid0/llm/autokernel/probes/inf03-claude-sandbox-runtime-20260812-r1`. Focused validation passed
    **59/59**, footprint/README validation passed **106/106**, and the pinned full AutoKernel suite ran
    **5,653** tests with one expected failure and no unexpected failure. Those counts were observed in
    the live session but lack a retained transcript; the probe receipts are the durable runtime evidence.
    This proves the bounded probe, not full actor-critic campaign compatibility.
  - [x] **Preserve r5 and r6 as immutable non-rankable engineering attempts after the exact campaign
    cell falsified the standalone compatibility inference.** ✅ 2026-08-12 — both attempts completed
    only the starting-state baseline, then the first Claude/Codex 2h planner exited `-11` with empty
    stdout/stderr. R6 included all ten new runtime paths and used source `916cdc92`, yet reproduced r5;
    its controller cgroup was verified empty and removed. Neither attempt has an aggregate, controller
    ranking, belief update, proposal-bank entry, champion, or release authority.
  - [x] **Trace r6's exact campaign-versus-standalone differential and repair the process-bound model
    sandbox boundary.** ✅ 2026-08-12 — `/proc/self/*` Landlock rules were bound to the controller PID,
    so its forked Claude child still received `EACCES`. Research `43ba6263` leaves the controller in a
    deny-network broker-only sandbox, launches each read-only model client in its own outbound sandbox
    so `/proc/self/*` binds to the actual CLI PID, preserves the digest-pinned single-writable-bind
    Docker boundary for the Codex actor, and journals model/evaluation receipts through the parent.
    Targeted validation passed **77/77**; the pinned full AutoKernel suite passed **5,655** tests with
    one expected failure.
  - [x] **Refresh the actor pin and preserve r7's pre-execution refusal.** ✅ 2026-08-12 — research
    `a3fcea3c` pins the repaired actor entrypoint. R7 correctly refused the stale prior pin before any
    controller or GPU command; its audit file SHA-256 is
    `45c4ae3dbb563dfebd20715238407b304cdbdd98f96dfc841cae310d2dd017b0` and its receipt self-hash is
    `0f0b9000b4a2647e68db493c751769f4f845db4bce6d089a0aa15d3e10b7cfab`.
  - [x] **Preserve r8 as an immutable partial, non-rankable implementation diagnostic.** ✅ 2026-08-12
    — the 7/7 audit passed and the starting-state baseline completed, but the first actor cell exited
    before Claude inference because the broker-backed controller unnecessarily constructed
    `ArenaWorkspaceEvaluator`, importing unavailable `yaml` and the pinned vendor evaluator inside the
    broker-only Python environment. The controller cgroup teardown is hash-bound, verified empty, and
    removed. R8 has no aggregate, ranking, belief, proposal-bank, champion, promotion, or release
    authority.
  - [x] **Remove the broker-backed controller's unnecessary Arena evaluator import, prove the exact
    Claude cell under the campaign sandbox, then launch a fresh governed 7/7 attempt.** ✅ 2026-08-12
    — research `6270ebc1` keeps vendor evaluation in the parent and `cd1303b9` refreshes the actor
    pin. R9 then exposed a separate broker transport defect: `socket.sendall()` selected denied
    `sendto`, so it stopped before Claude with a verified-empty, removed controller cgroup. Research
    `eb00c411` writes framed requests directly on the inherited descriptor. R10 consequently banked
    the starting-state evaluation and completed the first real Claude planner request, then correctly
    stopped before actor execution when its mutation guard counted the controller's staged session and
    config as task source. The ephemeral state was scrubbed. Research `2525f2f7` separates semantic
    task files from model state and `7b20b5d6` refreshes the manifest pin. R11 completed the first full
    real planner → digest-pinned Docker Codex actor → centralized GPU evaluation → Claude critic
    loop, but was stopped as an immutable non-rankable partial after repeated mechanisms exposed the
    missing feedback seam.
  - [x] **Close r11 without interpreting it and prove measured critic feedback alters the next live
    proposal.** ✅ 2026-08-12 — r12 iteration one compiled and passed 4/4 correctness at
    `average_speedup=0.9967805648538064`; its critic selected `revise`. Iteration two's planner cited
    that exact measurement, forbade the rejected unmasked-fastpath mechanism, corrected the infeasible
    autotune suggestion from the fixed launcher contract, and proposed a distinct shared-offset/
    vectorized-streaming mechanism. It also compiled and passed 4/4 correctness at
    `average_speedup=1.0059084616458236`; the critic selected `accept` while acknowledging that the
    ratio remained inside noise. This proves feedback propagation, not a kernel speedup.
  - [x] **Move host actor-runtime attestation out of the confined controller and pin the repair.** ✅
    2026-08-12 — after all six model calls and three brokered evaluations, r12 finalization failed by
    reopening `/usr/bin/docker` inside Landlock. Research `4b516e9f` makes the parent model-receipt
    chain authoritative for host runtime identity and validates the actual flat model-receipt layout;
    `f316bf31` pins the source. The full AutoKernel suite passed 5,660 tests with one expected failure.
  - [x] **Close INF-03 seven-arm r13 as an immutable partial and identify its confined-runtime failure.**
    ✅ 2026-08-12 — the baseline completed and planner model receipt ordinal `0001` persisted, then
    Claude failed exactly `EACCES: permission denied, mkdir '/mnt/raid0/llm/tmp/claude-1000'` before a
    completed planner response. All captured PIDs are dead and every controller/model cgroup was verified
    empty and removed. R13 has no controller cell receipt or aggregate and is permanently non-rankable.
  - [x] **Repair the confined Claude runtime temp path.** ✅ 2026-08-12 — research `268115ad` refuses
    inherited host scratch for direct model clients, creates a fresh call-scoped directory under the
    governed workspace, binds the relative path plus `ambient_host_temp_inherited=false` into the model
    sandbox receipt, and verifies deletion after every call. The campaign manifest still pins its parent.
  - [x] **Pin `268115ad` and launch a fresh seven-arm attempt.** ✅ 2026-08-12 — research
    `446a1c31` isolates each brokered model call and `152ed0d9` pins that runtime into the campaign.
    Seven-arm r14 audited `ready` at 7/7 on observed clean source `152ed0d9`. A timestamped live
    checkpoint found seven successful, non-timeout model receipts (five Claude and two Codex) and three
    complete parent-owned evaluator windows. Every Claude receipt recorded
    `ambient_host_temp_inherited=false` plus a call-scoped relative temp path, and its captured cgroup was
    verified empty and removed. This proves the r13 capability repair across repeated real calls; it does
    not make the live campaign terminal or rankable.
  - [x] **Close seven-arm r14 as an invalid source-identity attempt.** ✅ 2026-08-12 — after nine
    successful model calls and four correct evaluator windows, the outer checkpoint guard raised
    `task or controller source identity changed during checkpoint execution`. Its audit had bound clean
    source `152ed0d9`, but implementation work advanced that same worktree to `03f9ae69` while the cell
    ran. The actor cell therefore emitted no admitted cell receipt or panel aggregate. All eight device
    claims have released receipts; 14 captured PIDs are absent; and all 12 recorded controller/model/
    evaluator cgroups are verified empty and removed. R14 is permanently invalid and non-rankable.
  - [x] **Close seven-arm r15 as a transient structured-output failure with complete teardown.** ✅
    2026-08-12 — r15 completed the baseline plus four compilation/correctness-4/4 controller-feedback
    windows, then Claude call ordinal `0010` returned non-timeout exit `1` with exact subtype
    `error_max_structured_output_retries` and terminal reason `structured_output_retry_exhausted` after
    five provider-internal attempts. No actor-cell receipt or aggregate was admitted, so r15 is
    permanently non-rankable. All **7/7** device claims released, all **13** captured PIDs were absent,
    every recorded cgroup was empty and removed, and the immutable source worktree remained clean at
    `03f9ae69`.
  - [x] **Add one bounded, receipt-visible retry for exact structured-output exhaustion and refresh the
    campaign pin.** ✅ 2026-08-12 — research `537163d5` retries exactly once only for the recognized
    non-timeout Claude wrapper failure, journals the first and retry attempts separately, and leaves
    arbitrary non-zero exits and timeouts fail-closed. Research `eb1de388` refreshes the actor-critic
    campaign identity to those bytes. The admitted Python 3.12 environment passed the full AutoKernel
    suite: **5,682 tests with one expected failure**. Both commits are pushed and on research `main`.
  - [x] **Preserve seven-arm r16 as a pre-claim source-identity refusal.** ✅ 2026-08-12 — its static
    audit observed the new actor entrypoint but the campaign still expected the pre-repair digest, so it
    refused before controller inference, GPU execution, or device-claim acquisition. The corrected pin
    is `eb1de388`; r16 carries no empirical or comparison authority.
  - [ ] **Drive retry-hardened seven-arm comparison to a terminal aggregate and validate the complete
    receipt chain.** R18 is terminal-noncomplete and non-rankable after the parent rejected mutable
    host Claude-config drift following the staged copy. No actor-cell receipt or aggregate was admitted.
    Fresh r19 is live from clean immutable research `0b1fdbe9`; its ready 7/7 audit, completed baseline,
    and active first actor cell grant no comparison authority. Preserve diagnostic checkpoints, but never
    aggregate, rank, bank, promote, release, or resume r4-r18.
    - [x] **Patch the EvoEngineer evaluator-constructor call and launch a fresh immutable successor.**
      ✅ 2026-08-12 — research `381bc55e` wires governed `source_paths` through EvoEngineer, GEAK,
      K-Search, KernelFoundry, and Xe-Forge; `11bccd41` refreshes affected entrypoint pins. Research
      `b0d6f79f` adds prospective intermediate evaluator belief rows and strict feedback-only reading.
      Fresh r18 was sealed at `17b9208d`; its later terminal disposition is recorded below.
    - [x] **Close seven-arm r18 as a staged-host-input identity failure without upgrading its measured
      partial.** ✅ 2026-08-12 — r18 completed the baseline and full Claude/Codex 2h loop, including
      four compile/correctness-4/4 candidate evaluations, but the outer parent re-hashed mutable host
      `~/.claude/.claude.json` after its bytes had already been copied into the scrubbed workspace.
      That host file changed during the multi-minute cell, so admission failed after controller exit.
      No actor-cell receipt or aggregate was admitted; r18 remains permanently non-rankable and is
      recorded in the dashboard disposition overlay under exact attempt id `21754d23…`.
    - [x] **Bind staged controller inputs at copy time and launch a clean immutable successor.** ✅
      2026-08-12 — research `0b1fdbe9` verifies the source hash immediately before copying, verifies
      the staged bytes, emits `epyc.autokernel.controller_staged_inputs.v1`, and validates the receipt
      instead of reopening a later-mutated host credential/config file. The controller suite passed
      **596 tests**. R19 is live from clean exact source `0b1fdbe966f338a8ac840c9961eb718528af1a0f`
      at `/mnt/raid0/llm/autokernel/campaigns/inf03-available-source-seven-arm-r19-20260812`; its audit
      is ready 7/7, baseline is complete, and the first actor cell is active.
    - [x] **Specify the safe controller-overlap architecture before enabling it.** ✅ 2026-08-12 —
      research `dfe265a1` defines immutable schedule order, isolated deterministic lanes, serial
      per-lane checkpoints, exact MI210 claims around evaluator windows, bounded claim waits, an
      inherited attempt lease, PID/start-tick cancellation, manifest-v3 validation, truthful observed
      overlap, and a required overlap A/A noise gate. This is a design/verification contract only:
      overlap remains disabled, and r19 intentionally retains the proven sequential runner.
    - [ ] **Implement and validate deterministic controller overlap for a post-r19 successor.** Close
      every `dfe265a1` gate: manifest-v3 lane/claim bindings, inherited attempt lease, PID/start-tick
      cancellation, lane confinement, contention/restart regressions, truthful observed concurrency,
      disjoint CPU placement, and a governed overlap A/A inside its predeclared noise bound. Do not
      change r19 execution semantics or make concurrent results rankable before that matrix passes.
  - [x] **Narrow INF-03 MI210 claims to the centralized evaluator's actual GPU windows.** ✅
    2026-08-12 — research `e6c7aab6` and the r4 manifest bind
    `controller_deliberation_holds_no_gpu_claim=true`, a GPU-blind controller environment, claims
    only around vendor/final measurement windows, exact complete-checkpoint resume, and signal-safe
    release. The audit observed no KFD PID or active device claim while KernelFoundry deliberated;
    other governed GPU work may use those intervals.
  - [x] **Obtain and execute the exact licensed EvoEngineer source through the governed adapter.** ✅
    2026-08-12 — research `f42b3540`, `7e915831`, and `a81c2692` pin MIT source commit
    `1649715a975b9022c84b5279c88aaef0b73b28dc`, preserve the historical EvoEngineer-Full loop and its
    four ordered fallback semantics, and exercise the exact upstream `EvoEngineer.run()` for 10
    generations / 40 samples with fixture model/evaluator bridges only. The fresh physical static audit
    at `/mnt/raid0/llm/autokernel/probes/inf03-isolation-available-source-reaudit-20260812-r3/receipt.json`
    is ready at **7/7** over four tasks with zero controller/GPU commands (self-hash `5fa93695…`, file
    SHA-256 `082d977f…`).
  - [ ] Obtain the exact licensed ARGUS source release, then port its real controller policy through the
    same governed adapter contract; a namesake substitute is not admissible. Until then the separate
    full 8/8 panel must refuse, while the 7/7 available-source panel remains diagnostic-only.
- [x] Build C4 gfx90a profiler-metric analyzer (GEAK-v2 raw-rocprof path first) ✅ 2026-08-11 —
  `profile_report.py` implements the deterministic paired mapping/formal report; the live single-process
  Q4_K/Q8_0 captures prove it on gfx90a. `profile_context.py` binds the report hash into a priced
  AutoKernel discovery block and a framework-neutral `c4_evaluator_observation.v1` seam for GEAK /
  AgentKernelArena adapters. The seam is diagnostic-only and cannot write a verdict or rank.
- [x] Build C6 anti-reward-hacking layer (robust-kbench + AgentKernelArena unseen-shape) ✅ 2026-08-11
  — the immutable external scorer, search-tree monitor, unseen/hostile-shape cases, stream/thread
  escape checks, planted red-team corpus, prompt disclosure guard, and ranked-set short-circuit cases
  are implemented and covered by the AutoKernel suite. Live candidate sensitivity remains governed by
  the producer-dependent RVP-C2 rows, not by reopening the C6 implementation task.
- [x] **Compile the initial EPYC C3/C5 exact-suite seam.** ✅ 2026-08-11 — research `4320d83a`
  (main `5dfd14ad`)
  emits a hash-bound three-case plan/receipt contract for attention `k228`, MoE `k175`, and native
  Q4_K dequant, with honest vendor floors, correctness/integrity precedence, and captured-workload
  whole-model exit. Apex owns only the Python/Triton overlay cases; dequant correctly uses the
  experimental-binary adapter. This closes the offline integration seam, not the real MI210/Apex
  evidence campaign.
- [x] **Add selected-entry-only Apex runtime validation without guessing C5 mappings.** ✅ 2026-08-11
  — research `934b2a8d` bypasses Apex's unrelated-repository global validation bug only for an exact,
  reviewed registry row; all source/toolchain/model/capture identities remain fail-closed. The
  subsequent hash-bound mapping audit (`a9779163`, main `4fd985c2`) classifies both seeds honestly: `k228` is adjacent
  to AITER MLA prefill but has no pinned gfx90a HSA image or proved LSE/ABI contract, while composite
  `k175` requires missing component-graph/multi-trace support. Both now return typed structural
  mismatches rather than a similar-looking single kernel.
- [x] **Harden the governed C3/C5 real-capture seam and bind its observation window.** ✅ 2026-08-12
  — research `7b3cc6f4`, `a865bd7c`, and `300647bd` bind live-produced gfx90a inventory, KFD
  producer ancestry, exact sampler-window overlap, immutable acquire/release claim slices, frozen
  source paths, and selected-entry-only Apex admission. Focused validation passed 27 tests and the
  evaluator regression passed 1,579 tests. This closes the capture mechanism, not the model-specific
  tensor evidence.
- [ ] **Provide the exact k228 model-tensor capture hook manifest and run the governed capture.** The
  hook must execute the real model surface and emit the source/model/process/window identities the
  C3/C5 provider validates; a HyRA reference tensor or synthetic fixture cannot substitute.
- [ ] **Provide the exact k175 ordered multi-trace capture hook manifest and run the governed capture.**
  The hook must preserve the router → top8/count/rank → dispatch → routed/shared experts →
  weighted-undispatch graph; a single similar-looking kernel cannot satisfy the composite case.
- [x] **GEAK-family freshness sweep completed ✅ 2026-08-03** (research-intake Stage-2b): GEAK v4 retains a current gfx90a KB (`perf_knowledge/hardware/cdna2_mi200/`, `updated: 2026-06-08`) and 40 gfx90a capability entries; all published evaluation remains gfx942. Scoping caveat amended above; "677/678/679 are a coverage regression" **retired** — for GEAK proper it is unpublished coverage. `v1.0.0 @ 4ffba15a` pinned.
- [x] Re-target the program objective from the Q8 rung to the fp16 rung, with a banded per-lever ceiling (K1–K12) ✅ 2026-08-03
- [x] Register **ARGUS** (arXiv 2604.18616) as a controller candidate alongside EvoEngineer /
  KernelFoundry / K-Search / Xe-Forge / GEAK ✅ 2026-08-11 — `arena_adapter.py` registers the
  `argus` controller id under the same exact three-argument bridge and prompt-hygiene contract as
  the other arms. This records registration only; the cited MI300X result remains vendor evidence.
- [x] Read GEAK's `landscape/` + `languages/` sections as an external check on our seven-school
  taxonomy ✅ 2026-08-11 — current GEAK `5107c7e4` showed that “seven schools” was never a durable,
  enumerated fact. The corrected comparison is seven *abstraction families*, recorded in the
  [deep-dive sweep](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md#sweep-2026-08-11--landscape--languages-taxonomy-check-closed).
  The live gfx90a ladder is Triton → TileLang → HIP/C++ → MFMA/ISA when measurement justifies each
  descent, with CK/CK-Tile/rocWMMA as baselines. FlyDSL is a valuable new vocabulary source but GEAK
  scopes it to gfx942/gfx950, so it is not a current MI210 execution arm.
- [x] Resolve the profiler-tooling blocker on the host (rocprofv2/rocprof/omniperf/rocm-bandwidth-test) — C4 and the LDS bank/phase solver are both gated on it ✅ 2026-08-12 (mainB)
  — **re-verified live, not inherited from the 2026-08-03 note.** Through
  `source /mnt/raid0/llm/tools/rocm-profilers-6.2/env.sh`: `rocprof` and `rocprofv2` both report
  `ROCm 6.2.0-66 / ROCProfiler 2.0`, `rocm-bandwidth-test` responds to argument parsing, and
  `omniperf` resolves on PATH but **does not run** — it exits on missing Python deps
  (`astunparse==1.6.2`, `colorlover`, `dash>=1.12.0`), exactly as line ~138 predicted, so its
  deliberate deferral stands and is accurate. **Note for anyone re-checking this**: none of these
  are on the default `PATH` and none are under `/opt/rocm` — that is by design (extraction, so the
  shared bind mount is untouched). Probing `PATH` or `/opt/rocm` returns a confident *absent* for
  all five. Source the env or you are measuring the wrong universe.
- [x] Run HipKittens' LDS bank/phase solver method on gfx90a ✅ 2026-08-11 — 372 bank and 6,048 phase
  dispatches across three repetitions measured **32 LDS banks and eight phase cliques of eight lanes**.
  HipKittens' CDNA3 64-bank/two-phase swizzle topology therefore does not transfer to gfx90a;
  `swizzle_transfer_class=retune_required`. Receipt:
  `/mnt/raid0/llm/autokernel/probes/inf03-lds-gfx90a-20260811-r4/receipt.json`, SHA-256
  `ae1d833c704bdae9a78767d0fc0b927298d6d1dfdb31a0ea11c34058dc525987`.
- [x] Add `-mllvm --amdgpu-unroll-threshold-local=600` to the build-flag checklist as a
  **precondition of any ROCm 7+ upgrade** ✅ 2026-08-11 — the new
  [ROCm upgrade checklist](../../docs/runbooks/rocm-upgrade-checklist.md) requires Linux builds to pass
  the option through `CMAKE_HIP_FLAGS`, proves it reached HIP compile commands, and retains it unless
  an exact-toolchain matched A/B shows it unnecessary. This does not alter frozen v9 or ROCm 6.2.


> **MERGE NOTE 2026-08-12 (coordinator).** The two sides of this section disagreed on FACT,
> not formatting, and I preserved both rather than picking. The 2026-08-11 side records the
> LDS bank/phase solver as RUN with a receipt (32 banks, 8 phase cliques, SHA-256
> `ae1d833c704bdae9a78767d0fc0b927298d6d1dfdb31a0ea11c34058dc525987`); the 2026-08-12 side
> records `rocprofv3` as ABSENT and questions whether the solver's counters are reachable
> at all. If the receipt is real the question is answered; if the receipt came from a
> different path than the solver row describes, the row is mis-stamped. **OWNERS: verify
> and correct — I did not adjudicate this.** The profiler row below is the NEWER
> 2026-08-12 re-verified-live text, deliberately preferred over the 2026-08-11 inherited note.
- [x] **`rocprofv3` absence vs the LDS solver — settled, the row was mis-stamped** ✅ 2026-08-12 (mainB).
  Both halves were true and they were never in conflict. `rocprofv3` IS absent (the side-load is a ROCm
  6.2 extraction topping out at ROCProfiler 2.0) — but the solver did **not** need it: it ran
  2026-08-11 over a **rocprofv2-compatible counter path**, receipt SHA-256 `ae1d833c…`, 372 bank and
  6,048 phase dispatches, deriving 32 banks and eight phase cliques. So the ~40 min GPU window is
  already spent and its result is banked; what was wrong is the *description* at line ~126, which
  names `rocprofv3` as the instrument. **The run is real; the row named the wrong tool.**
  Recorded because the failure mode generalises: a row that names its instrument can go stale against
  a run that used a different one, and then a correct check of the instrument returns a false BLOCKED.
- [x] **GEAK-family freshness sweep completed ✅ 2026-07-29**: refreshed the deep-dive appendix from AMD's current AgentKernelArena/GEAKv3 reports. AKA now publishes 214 tasks and a 44-task MI300X comparison; this is vendor/CDNA3 evidence only and does not close the MI210/gfx90a reproduction gap. [Freshness appendix](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md#9-freshness-appendix-sweep-at-each-handoff-audit--when-the-mi210-racks).


## Auto-kernel revival — research-intake integration 2026-07-22 (C5 seed corpus + FP8 authoring target)
_Via /research-intake Stage-2 (intake-884 HyRA MI210 re-check). The loop AUTHORS gfx90a kernels — these are task specs, not port-or-decline artifacts._
- [x] Seed C5 with the HyRA sol_execbench kernels as reference specs the loop authors gfx90a kernels FROM (maps onto this handoff's "seed EPYC ops: attention / MoE-dispatch / dequant"): 5 bf16/fp16 Triton kernels directly (k138 mamba, k145 hyena, k154 chunk-gated-delta linear-attn, k175 MoE dispatch, k228 MLA paged-prefill); CUDA-lib-bound winners (k215 GEMM/flashinfer, k225/k227 GQA/MLA) as reference targets to re-author. All Hopper-autotuned + NVIDIA-only-attested -> loop re-authors + re-attests on gfx90a (wavefront-64/MFMA/LDS) ✅ 2026-08-11 — `c5_seed_corpus.{json,py}` pins all eight artifacts to Hyra-results commit `26ebfbe7`, separates the direct and CUDA-bound sets, excludes Hopper scores/latencies from authoring context, and lets Arena tasks select exact rows through `c5_seed_ids`.
- [x] Add FP8 as an authoring datatype target: gfx90a has no native FP8 MFMA, but an FP8-weight -> bf16-MFMA upcast GEMV is buildable and potentially bandwidth-valuable for memory-bound decode (half the weight bytes of bf16; compute upcast to bf16) — an experimental-kernel investigation, NOT a hard wall. NVFP4 microscaling (per HyRA k185) is the harder end; scope after the FP8-upcast path ✅ 2026-08-11 — `datatype_targets.py` exposes a non-numeric FP8-weight/software-upcast contract to Arena tasks, requires an independent decoder, exact-shape baseline, upcast-cost attribution and whole-model gate, forbids batch-one MFMA assumptions, and mechanically defers NVFP4 until the FP8 path has a terminal result.

---

## Loop engineering — controller experiments and prompt hygiene (research-intake Stage-3, 2026-08-10)

_Via `/research-intake`. Source: an operator-supplied field note on running a coding-agent research
loop against a batched linear-algebra kernel to competitive results._

**Provenance, stated once and carried by every item below.** The note's loop-engineering claims —
that raising the planner's reasoning-effort knob lengthens search rather than deepening any single
answer, and that a proximate numeric target changes what the agent proposes — have **zero primary
backing**: the accompanying repository does not contain the loop, the transcripts, or any ablation.
They are `[unverified]` **hypotheses** and no number from them may be quoted as evidence anywhere.

**Operator steering, verbatim (2026-08-10):** *"zero primary backing doesn't mean we can't reason
about the potential usefulness of this information from first principles."* That is the governing
instruction for this section. The unverified contract governs **citation**, not **consideration** —
so each hypothesis below is evaluated on our own stack and paired with the cheapest experiment that
would settle it here. Nothing is blocked: frontier Anthropic/GPT models are available to our
planners (operator, 2026-08-10 — we are not restricted to local models), and every experiment in this
section costs **zero GPU and zero local inference**.

- [x] **AK-PL-1 — Prompt-leak guard on the assembled authoring prompt.** Grep the fully-rendered
  planner/actor prompt for `test-backend-ops`, `max_nmse_err` and `init_tensor_uniform`. An agent that
  can read the tolerance it must clear is being graded by a rubric it holds.
  **Test the guard against the COMPLIANT path too** — a guard that also rejects the legitimate prompt
  is a guard that will be disabled the first time it fires
  (`feedback_guard_must_not_forbid_its_own_idiom`). Pairs with RVP-C6-7 in
  [`rocm-verify-profile-backend.md`](rocm-verify-profile-backend.md), which filters the *diagnostics*
  half of the same channel. ✅ 2026-08-11 — `controller/authoring_contract.py` scans the fully rendered
  prompt for all three named internals plus the exact `ERR = value > tolerance` disclosure shape;
  tests plant every leak and prove an ordinary compliant authoring prompt remains admissible.
- [x] **AK-PT-1 — Per-turn productivity accounting (this handoff owns it; emitted at
  `autokernel-research-loop.md` §8.8).** Record `(turn, task, correct?, speedup)` per refine turn, and
  split **rescued** (a turn that fixed a previously-failing candidate) from **persistent** (a turn
  that improved an already-correct one). We currently measure **neither**. The reason the split is
  load-bearing: mean speedup falls across turns as a **composition** effect — later turns admit
  candidates that earlier turns could not fix, which are systematically worse — so a declining mean is
  not evidence that refinement stopped working, and reading it that way would truncate the loop
  exactly where it is still paying. ✅ 2026-08-11 — AutoKernel `turn_productivity.py` implements an
  immutable append-order archive with state-continuity checks; rescued/persistent/failed/regressed is
  mechanically derived from the correctness transition, incorrect turns cannot carry a speed rank,
  and every observation retains its evidence reference and content hash. AK-X-6 is its first consumer.
- [x] **AK-LE-0 — Implement the static experiment contracts and selected-task-safe scaffold for
  AK-LE-1/2/3.** ✅ 2026-08-12 — research main `51742ebd` integrates the effort/persistence,
  proximate-target, direct-implement, split-implement, and split-exploit arm contracts. Every scaffold
  consumes the same independently SHA-256-bound selected-task artifact; planner-only `PROPOSE … do
  not implement it yet` text is excluded. The accepted full AutoKernel suite passed **5,464 tests
  with one expected failure**. This closes static wiring only; AK-LE-1/2/3 remain open until their
  budget-matched model runs produce empirical results.
- [x] **Add the governed execution bridge for the AK-LE-1/2 planner panel.** ✅ 2026-08-12 —
  research `98f642cd` compiles exact `ExperimentContract` model/quant/effort cells, resolves and
  hashes the Claude/Codex CLI, executes each cell in a captured read-only process group, and seals
  the exact prompt, argv, stdout, stderr, last message, timing, and strict parsed observation. It
  has observe-only authority and cannot mutate a campaign, rank, select a champion, or release.
  Focused runner tests passed **16/16**, the controller slice passed **487/487**, and the integrated
  canonical AutoKernel suite exited zero.
- [x] **AK-LE-1 — Reasoning-effort × search-persistence experiment.** Hold champion, retrieval context
  and PROPOSE prompt fixed; sweep only the planner's effort knob. Measure **search** outcomes, not
  answer quality: count of novel non-duplicate hypotheses, count of explicit "this is already
  optimized" terminations, and how many proposals survive the pre-filter.
  - **Why this is not already covered.** [`reasoning-effort-levels.md`](context-and-token-economy.md#track-reasoning-effort-levels) is
    a **stub**, and its entire measured evidence (the A4 / GPQA-Diamond ladder, +32.0 pp at 4.0×
    tokens) is about *answer accuracy on a fixed question*. Nothing in it measures whether more effort
    makes an agent keep looking. That is a different dependent variable.
  - **Pre-register the direction before running.** Our own observed planner failure is the *opposite*
    one — halting after a single critic "revise" — so the sign must be predicted in advance rather
    than read off the result. Its per-model invariant applies here too: effort is a property of a
    (model, quant) pair and is never inherited. ✅ 2026-08-12 — the corrected r3 panel completed all
    **8/8** predeclared Claude Opus 5 / GPT-5.6 Sol × high/xhigh × control/target cells, then the
    source-pinned structural reducer emitted one planner receipt and **32** prospective belief rows.
    Higher effort did not increase novel/surviving counts in either control arm (Claude `6→6`, Codex
    `3→3`) and all four xhigh cells took longer. This is a bounded null result for the predeclared
    control contrast, not a model-wide effort claim: there is one observation per cell and no
    scaffold or campaign-ranking authority. Evidence:
    `/mnt/raid0/llm/autokernel/campaigns/ak-le-planner-20260812-r3/planner-reduction.json`, file
    SHA-256 `c24122893acdd7cf10f042a447d7daa41aeb7d77161dcda8b5b5bf5344b57791`.
- [x] **AK-LE-2 — `proximate_target` arm, run as one extra arm on AK-LE-1.** Tests the effort × target
  interaction jointly rather than as a second study. **Specify it as a rendered planner-context line
  only — never a manifest field a gate can read** — regenerated each round and scoped **per cell**.
  AK-D3 demoted a percentage figure from trigger to readiness signal for sound statistical reasons
  (threshold peeking, winner's-curse inflation); a target that any gate can read re-introduces exactly
  that, one layer up. The rendered-context form gives the planner the steer without giving the
  evaluator the number. ✅ 2026-08-12 — r3 rendered the decode target only as planner context and
  reduced the complete matched panel. Claude produced `6` surviving hypotheses in every arm; Codex
  target arms produced fewer than their matched controls (`3→1` at high, `3→2` at xhigh). No cell
  emitted an already-optimized termination. The honest result is null for Claude and mixed/adverse
  for Codex on this single panel; it does not establish a transferable proximate-target benefit.
- [x] **AK-LE-3 — Split *implement* from *exploit* as two prompt roles on the SAME model first,
  budget-matched in wall-hours, before any multi-model A/B.** The note's four-role split
  (explore / critique / implement / exploit) is a runnable design, but the delta from our current
  two-role planner may be small, and a multi-model comparison would confound scaffold with model.
  **Vary scaffold and model independently** — published evidence has identical models inverting rank
  under different scaffolds.
  - **What is already reusable (inventory, operator steering: "what could be repurposed of our current
    design").** AutoPilot already runs a two-role draft + critique planner with a **binding** critic —
    that is `explore` + `critique` in place, and it is the half that usually costs most to build.
    [`architect-model-selection-bench.md`](model-evaluation-queue.md) already selects a model
    per role, but on **quality**, never on throughput — the per-role choice machinery exists and its
    objective is the missing piece. AgentKernelArena's `@register_agent` adapter pattern (Decision
    Snapshot item 2) is the substrate for registering the arms. So the increment is roles 3 and 4 plus
    a throughput-aware selection objective, not a new controller.
  - [x] **Implement a governed same-model direct-implement versus implement-then-exploit
    authoring/evaluation seam before running this panel.** ✅ 2026-08-12 — research `c4434810` and
    `230721b6` compile the exact two-model × two-scaffold panel, use the same writable Codex actor and
    trusted Arena evaluator in every cell, isolate disposable baseline/candidate worktrees, bind
    runtime/image/import identities, serialize MI210 claims, and clean up exact owned worktrees on
    every exit. The focused integrated slice passed **29/29** and the controller suite passed
    **512/512**. The following terminal campaign closes the parent experiment.
  - [x] **Run and reduce the governed same-model scaffold panel.** ✅ 2026-08-12 — all **4/4**
    gpt-5.6-sol/terra × direct/split cells compiled, passed all four correctness cases, retained four
    valid baseline and four optimized timing cases, and released their MI210 claims. Average speedup
    was Sol direct `0.9957477195`, Sol split `1.3930213301`, Terra direct `1.0021830618`, and Terra
    split `0.9935661224`. The split benefit is therefore task- and model-specific, not a cross-model
    scaffold default. The panel has diagnostic observation authority only: it cannot rank a campaign,
    choose a champion, or authorize a release. Receipt:
    `/mnt/raid0/llm/autokernel/campaigns/ak-le-3-scaffold-20260812-r1/panel/panel.json`, self-hash
    `6e764cca1df8cf347d43c48bca70654f1cec4dddbe967e7e80a3705c3d71ff32`, file SHA-256
    `5af0307ffd823e093d06d26497a536e414090d72e3dee73bf3c33f4ea853e666`.
- [x] **AK-LE-4 — Context discipline: a priced context budget and a reversible compaction protocol.**
  (a) A per-round context-budget table with an explicit **never-bulk-read** rule, so the loop cannot
  spend its window on a file it will not use. (b) A research-log compaction step that writes a
  **what-was-kept / what-was-dropped header** — and, critically, **a git recovery recipe**. The source
  note describes the compaction and omits the recovery half; compaction is only safe *because* it is
  reversible, and a protocol that drops the reversibility keeps the risk and discards the mitigation.
  ✅ 2026-08-11 — the authoring contract prices every context item and round, enforces per-item and
  total caps, rejects duplicate/bulk reads, prints the budget table and literal never-bulk-read rule,
  and emits kept/dropped compaction headers with an exact `git -C <repo> show <commit>:<path>` recovery.
- [x] **AK-LE-5 — Anti-fabrication clause for externally-sourced numbers.** Our invariants
  (`autokernel-research-loop.md` §4) bind the loop's own measurements to a protocol, an anchor and a
  receipt. **Nothing currently covers a number the loop claims came from outside itself** — a vendor
  figure, a paper result, a leaderboard score quoted into a proposal. Require an external number to
  carry a source, a retrieval date or commit, and a normalisation to roofline utilisation (§8.3.1)
  before it may appear in a proposal at all; otherwise it is not admissible even as `design_prior`.
  The source campaign logged this exact failure three times in its own write-up, which is the only
  part of that document that is self-evidencing. ✅ 2026-08-11 — proposal-v3 now requires a validated
  `external_numbers` vector (empty is explicit). Every entry binds source, retrieval date or commit,
  exact quant, denominator basis and normalized roofline utilization; the validator independently
  re-derives utilization and refuses mixed unit/quant/basis denominators.

**Declined here (recorded so it is not re-derived):** adopting the note's evaluation cadence. It rests
on elastic external accelerator capacity and a free third-party adversarial verifier; we have one
MI210 and a verifier we own. **The orchestration is reproducible almost fully; the cadence is not** —
and per AK-LN-1/AK-LN-4 in [`autokernel-research-loop.md`](autokernel-research-loop.md) §21, our
answer to cadence is concurrent screening lanes, not more devices.

## Research Intake Update — 2026-08-15 (SOL-ExecBench as a gfx90a correctness oracle; intake-1102)

The Stage-2 dive settled the C5 provider question, and the answer is more useful than the headline
suggests. **State it in two parts or it misleads.** The ROCm port carries *no measured constants* for
gfx90a — it is gfx950-only (MI350X/MI355X), pinned to ROCm 7.2 against our 6.2. **That is not the same
as unusable here.** Its compile path is genuinely architecture-agnostic (the gencode helper falls back
to reading `gcnArchName` from torch and would emit `--offload-arch=gfx90a`, and a `LOCAL` hardware
target exists for exactly this case), so **compilation and correctness checking run on our MI210
today**. Only SOL *scoring* needs a port, because T_SOL, T_b and tolerances are per-part measured
quantities.

All eight C5 seeds resolve to real definition/workload/reference/tolerance/bound records — 193
workloads, all scoreable and zero deferred. The port's actual k145 oracle workload/tolerance surface
is fp32, while HyRA candidate metadata names fp16; k227 is bf16-only. The provider deliberately keeps
oracle-workload and candidate-metadata identities separate rather than repeating the earlier
"all bf16/fp16" conflation.

- [ ] **C5-3 — Use the port as a gfx90a CORRECTNESS ORACLE now, ahead of any bound port.** Target
      `LOCAL` hardware, compile through the existing arch-agnostic path, and run the 10 fresh-input
      correctness rounds against the live-executed references. This is the C3/C5 provider validation
      the handoff already says a HyRA reference tensor or synthetic fixture cannot substitute for — and
      it needs no measured constants, so it is available immediately. AutoKernel is explicitly in scope
      to author and screen gfx90a kernels against it.
  - [x] **C5-3a — Implement the sealed gfx90a correctness-only provider.** ✅ 2026-08-16 — research
        `5f1b645c0c5034137e298c1dc9732beee9742547` adds LOCAL/gfx90a planning, exact source/runtime/
        workload identities, ten fresh live-reference rounds, and `scoring.enabled=false`; later
        hardening binds source staging and complete raw-result reduction. No live 193-workload run
        occurred, so the parent C5-3 empirical task remains open.
- [x] **C5-4 — Classify the eight seeds by bound quality, and stop quoting `S` where it is meaningless.** ✅ 2026-08-16 —
      research `777ac7845ad378cb660c30bf9a4a14f4a23851b3` persists the quality classes, blocks gfx90a SOL
      scoring without measured constants, and keeps numeric SOL fields out of author prompts.
      Median headroom (T_b/T_SOL) per seed: **k215 6.8× (ok)**; k145 16.8×, k175 17.0×, k138 33.4×
      (loose); **k154 506×, k227 3,690×, k225 5,710×, k228 36,837× (vacuous)**. Above ~100× the score
      collapses toward T_b/(T_b+T_k) and carries no roofline content — it degenerates into plain
      speedup-over-PyTorch, the exact framing the benchmark exists to replace, and the repo says so
      itself. **Treat the four vacuous seeds as correctness-only oracles plus a PyTorch-relative speed
      number; never quote their `S` as a speed-of-light figure.** k228 is named in the source as a
      problem where a correct kernel beat the bound, and k227's correction took its bound to 8 cycles —
      "correct, and vacuous". Note k175 additionally sits on the still-defective `declared_traffic` tier.
- [x] **C5-5 — Persist the kNNN ↔ problem-slug mapping into `c5_seed_corpus.json`.** All eight resolve
      uniquely with matching ordinals (k138→`L2__044_mamba…`, k145→`L2__051_…hyena…`,
      k154→`L2__060_chunk_gated_delta_rule…`, k175→`L2__081_moe_sparse_expert_dispatch`,
      k215→`FlashInfer-Bench__006_gemm_n2048_k4096`, k225→`FlashInfer-Bench__016_gqa_ragged_prefill…`,
      k227→`FlashInfer-Bench__018_mla_paged_decode…`, k228→`FlashInfer-Bench__019_mla_paged_prefill…`),
      with workload counts reproducing exactly (16/16/16/16/29/15/47/38 = 193). **The kNNN ids appear
      nowhere in either repository** — they are HyRA's — so this join is ours to maintain and should
      stop being re-derived. Add it as a `sol_execbench_problem_id` field. **2026-08-16 checkpoint:**
      `c5_seed_corpus.json` is now tracked, but exact problem IDs still live separately in
      `c5_rocm_oracle.json`; the requested joined field remained open at that checkpoint.
      ✅2026-10-06 — [MAIN source/native acceptance](../../artifacts/ni08/c5-seed-provider-join-20261006/README.md): exact persisted eight-way join, unchanged193 workloads/dtypes, original27/27 controls and byte-identical Research publication. Exact historical policy bytes are recovered; versioned default-verifier path restoration remains separate source work.

### OPERATOR DECISION — port the SOL bound constants to gfx90a?

This is the one item that needs MI210 GPU time and therefore a region claim, so it is presented rather
than filed. The port is **bounded and signposted** — the source's two refusals name their own remedy,
and its own MI355X runbook is effectively the checklist: add an MI210 `Part` entry (spec-sheet peak
clock + power cap), measure `F_LOCK` on gfx90a (they ship the task for it), add a measured `gfx90a`
`LLC_BYTES` (do NOT fall back to torch's reported L2 — it reports the per-XCD L2 and would undersize the
cache flush ~64×, making every memory-bound kernel look faster than it is), regenerate the SOLAR arch
YAML with the parametric generator, then re-measure T_b and tolerances.

**Scope it by bound quality, not by seed count.** Because four of eight seeds are vacuous, the honest
target is **k215 alone at 29 workloads** for a bound worth optimizing against, or ~77 workloads if
k138/k145/k175 are included at loose quality. Not 193, and certainly not the full 3,717.

| Option | Buys | Costs |
|---|---|---|
| **A. No bound port** | Correctness oracle (C5-3) + PyTorch-relative speed. Zero GPU time. | No speed-of-light measure on any seed. |
| **B. Port k215 only** | One genuine SOL-scored seed at 6.8× headroom. | F_LOCK + LLC measurement + T_b/tolerance re-measure over 29 workloads. |
| **C. Port k215 + the three loose seeds** | Four scored seeds, three of them loose. | ~77 workloads; the loose three yield weak roofline content. |
| **D. Full eight-seed port** | — | 193 workloads, four of which produce vacuous scores by construction. Not recommended. |

**Recommendation: B**, after C5-3 has shown the correctness oracle works end-to-end on gfx90a. A is a
legitimate stopping point if GPU time is scarce — the correctness half is where the C3/C5 provider gap
actually was.

## Research Intake Update — 2026-08-21 (Hawkeye / agentic-kernel cohort; intake-1218..1236)

_Via `/research-intake` Stage-4, operator-approved plan. Nine dives, 18 dive-verified entries. Two
corrections to earlier framing carried in deliberately, because both were repeated in briefs during this
session before primary source overturned them: **C4 is CLOSED** (✅ 2026-08-11, taxonomy closed, risk MED)
and nothing here reopens it; and **"GPU Kernel Scientist is gfx90a prior art" is FALSE** — it targets
MI300/CDNA3 and never mentions MI210, MI250, CDNA2 or gfx90a. The related "one of only two systems
targeting HIP for AMD" framing is an index-internal assertion, NOT-FOUND-IN-SOURCE, and should be struck
wherever it appears._

- [ ] **C5-6 — Add a ZERO-PROFILER null arm to the controller-authoring A/B on gfx90a.** The cheapest arm
      in the matrix: it needs a compiler, a correctness oracle and a wall-clock timer, all of which we have,
      and it has **no C4 dependency**, so it unblocks immediately. The point is to MEASURE what our profiler
      feed is worth instead of assuming it. Two independent sources now say the feed is a **MULTIPLIER, NOT
      A PREREQUISITE**: `intake-1226#record` ran an AMD HIP authoring loop with NO profiler of any kind —
      "the lack of any tools for profiling the kernels (apart from end-to-end running time...)" — and still
      cleared the PyTorch fp16 library baseline by ~1.9x (~450us vs ~850us), losing to the human winner at
      105us; and `intake-1222#record` found a raw ~50-counter dump measured WORSE than no profiling at all
      (its honest null comparison is +19% at p=0.0078, not the +125% headline, which is measured against
      that degraded arm). A third line agrees by construction: all five QiMeng papers (intake-1232..1236)
      are profiler-free and none cites profiling-guided-optimization literature at all.
- [ ] **C5-7 — Adopt COUNTER-GATED acceptance for agentic gfx90a kernels.** Pair every cell or kernel with
      a bottleneck counter and an expected DIRECTION, and refuse a speedup claim whose counter did not fire.
      From `intake-1218#record`, where this is load-bearing rather than decorative: a unit test passes only
      at **>=99% of the expert's counter value**, and the harness always reports the counter alongside TFLOPS
      "so a runtime improvement is verified to have come from exercising the targeted feature". This is the
      strongest structural defence against the faster-because-it-did-less-work hack anywhere in the
      intake-660..680 cluster. Pair it with a correctness gate STRICTER than that source's own
      99%-of-elements at atol=rtol=0.01 single-shape check.
- [ ] **C5-8 — Register two new controller archetypes on the adapter roster.** (a) **Hawkeye**
      (`intake-1218#record`) as the CURATED-STATIC-SUPERVISION archetype — no population, no archive, no RL,
      no meta-prompt evolution; a single-candidate edit/compile/profile/refine loop at a 100-productive-turn
      budget, notable for spending 24-50k tokens per TFLOPS of result versus 120k-2216k for its own
      baselines. (b) **SwizzlePerf's controller shape** (`intake-1221#record`) — a persistent history buffer
      appending (code diff + bottleneck report) per iteration, with a structured output signature of
      chain-of-thought -> JSON critique of prior iterations -> rationale -> final code. Both are
      architecture-neutral; (b) maps onto the existing planner-memory registry.
- [ ] **C5-9 — Trial MANUAL-CORPUS hardware-factor extraction as a third, profiler-free supervision
      source.** Point an LLM extractor at the public AMD CDNA2 ISA reference and MI200/MI210 tuning guides
      to populate a four-slot factor schema (memory hierarchy / instructions / vector+scalar registers /
      CU-SIMD-LDS-matrix-core), then A/B the resulting hint block against our existing static constraint KB
      on the hash-pinned k228 attention and k175 MoE cases. From `intake-1234#record`, and it is the ONLY
      hardware-grounding step in that entire five-paper line whose ACQUISITION IS AUTOMATED rather than
      hand-authored — pointing it at AMD manuals is the same operation the paper performs on the XuanTie
      manual. Complements, does not replace: CudaForge (intake-662) still owns the counter-SELECTION method,
      IntelliPerf (intake-1223) hands us the counter LIST. Bonus axis: the same mechanism would transfer to
      our EPYC 9655 CPU-kernel work via Zen5 optimization manuals, which no other cluster entry offers.
      **Clean-room only** — that framework is unreleased AND unlicensed.
  - [ ] **C5-9a — Falsify the load-bearing unknown behind C5-9 BEFORE investing in it.** Is cross-ISA
        transfer carried by the EXTRACTED FACTORS, or by the LLM's PRETRAINING FAMILIARITY with the target
        ISA? Every ISA that source tested (RVV, NEON, CuTe/PTX) is well represented in pretraining corpora;
        **gfx90a GCN assembly is not**, and the paper runs no ablation isolating the two. Run the hint block
        with and without the extracted factors on the same pinned cases, and compare the delta on gfx90a
        against the same delta on a pretraining-rich ISA. Cheap, and it gates C5-9.
- [ ] **C5-10 — Trial the LLM-TL sketch scaffold on the HIP arm.** From `intake-1235#record`: a two-stage
      sketch-then-parameterize scaffold whose Stage-1 DSL (Copy / Compute / Allocate / Reshape / for over a
      global->shared->register hierarchy) is **vendor-neutral and maps directly onto gfx90a** with LDS as
      shared and VGPRs as register — and whose prompts are published VERBATIM in that paper's appendix, so
      this half is liftable at zero cost. The paper's evidence for the split is that "none of the existing
      LLMs is capable of generating entirely correct TL code in a single stage", with two named reproduced
      failure modes. Measure against free-form HIP generation on **compile rate and correctness, not speed**.
      Stage 2 does NOT transfer — it emits CuTe, whose atom taxonomy is a 1:1 encapsulation of PTX.
- [ ] **C5-11 — Fix the ablation protocol before running any controller A/B.** Paired one-sided Wilcoxon
      signed-rank on a FIXED, ENUMERATED gfx90a task subset; three arms (no-feedback / raw-rocprof-dump /
      semanticized C4 report); report effective n after tie exclusion. Two disciplines imported from
      `intake-1222#record` and `intake-1227#record`: **(a) the honest control is NO-FEEDBACK, not a degraded
      feedback arm** — that paper's +125% is measured against a ~50-counter dump it separately proves is
      worse than nothing, while the no-feedback comparison is +19% at p=0.0078; and **(b) DO NOT report
      best-of-N-seeds as a headline** — it inflates every arm. Add the matched-subset rule: never compare
      mean speedup across arms with different pass sets, because weak configurations post higher means by
      failing the hard tasks and never paying their penalty.
- [ ] **C5-12 — Adopt two token-cost levers, and one falsifiable prediction to test cheaply.** (a) TWO-TIER
      MODEL SPLIT — a cheap model for parent selection and experiment design, a strong model only for kernel
      writing (`intake-1226#record`), mapped onto our registered Claude+Codex roster; `intake-1227#record`
      prices why it matters, at 5.11M tokens per SUCCESSFUL operator for kernel-specialised agents versus
      1.45-3.30M for vanilla frameworks. (b) A **FINDINGS DOCUMENT** — a one-time LLM-authored gfx90a quirks
      digest distilled from rocWMMA docs, the HIP reference and the AMD Matrix Instruction Calculator,
      carried in every prompt; this is the gfx90a analogue of the static constraint-KB already named as a C4
      fallback. Also import the 3-of-5 experiment-selection rule (most-innovative + highest-max-perf +
      highest-min-perf, without replacement) as a zero-cost diversity mechanism. PREDICTION TO TEST: a
      traceback-only reflection arm will UNDERPERFORM independent resampling at equal token budget —
      `intake-1227#record` measured 88% cross-turn code similarity for reflection versus 36% for independent
      sampling, and reflection lost outright on its vLLM subset.
- [x] **C5-13 — Record the DECLINE of a gfx90a taxonomy column, with its cost census as the ✅ 2026-10-29 (audit: handoffs/active/agentic-rocm-kernel-authoring.md:1030-1043 the decline is recorded in the box body with the a226e955 cost census (108 files, ~17,012 lines) and revisit condition; box is a record-only task) [no-belief: audit-reconciliation]
      justification.** A dive proposed authoring one; a later, better-evidenced dive of the same project's
      source measured what it actually costs and the decline wins. Census at `a226e955`: the cdna4 column is
      40 unit-test files (4,241 lines) PLUS a 68-file / 12,771-line abstractions library = **108 files,
      ~17,012 lines**, and the AMD column is the LARGEST of the four architectures — porting to a new VENDOR
      costs MORE, not less. Worse, the repo's own EASIEST cross-arch move (ampere->hopper: same vendor,
      adjacent generation, features added not removed) retained only **6.9% of abstraction lines and 11.4% of
      unit-test lines**, and is the port that silently corrupted agent context (its `AUDIT_FINDINGS.md` A-1,
      HIGH: Blackwell-only ISA left in A100/H100 guides). gfx950->gfx90a REMOVES features, so 7-11% is an
      OPTIMISTIC upper bound. One cell (`02_quantized_precision`) has no gfx90a meaning at all — gfx90a has
      no FP8 — and would need re-specification, which is a taxonomy decision rather than a coding task.
      **The STRUCTURE ports for free; the CONTENT does not.** Revisit only if a gfx90a kernel-authoring
      campaign is separately funded.

## Research Intake Update — 2026-08-21 (Stage-2b second wave: controllers, and what documentation scarcity costs)

_From `intake-1246#record` (AutoKernel), `intake-1244#record` (CodegenBench), `intake-1249#record`
(KLineage), `intake-1250#record` (Kernel-Smith), `intake-1240#record` (GPU Forecasters)._

- [x] ✅ 2026-11-01 [belief: cc] Evidence: epyc-inference-research `a23bd9c65203c9e8a9cbf7cabd76b716a9303d49`; artifact `scripts/kernel_rnd/autokernel/controller/ARENA_INTEGRATION.md`; docs-only `git diff --check` passed. **C5-14 — Add AutoKernel to the controller roster as the ONLY surveyed kernel controller that needs
      no vendor profiler.** `intake-1246#record` (MIT, `github.com/RightNow-AI/autokernel` @ `78435821`,
      1,531 stars): Phase A uses **`torch.profiler` with shape recording only** — zero `ncu`/`nsys` in paper
      or code. Our environment has rocprof v1/v2/v3 and omniperf and specifically **NO ncu/nsys**, which has
      been the standing blocker for importing every NVIDIA-native agent, so **Phase A would run on the MI210
      unmodified**. It is also **train-free and model-agnostic** (BYO coding agent reading `program.md`), so
      it composes with our existing roster. **HARVEST:** the Amdahl-ranked target selector with explicit
      move-on criteria (plateau / peak utilisation / time budget / speedup threshold), the
      fixed-evaluation/mutable-single-file invariant, and the five-stage gate ORDER (smoke → shape sweep →
      stability → determinism → edge cases), which is cheap-first and arch-independent. **DO NOT HARVEST:**
      the hardware spec DB (see AK-PM-15 — it fabricates a gfx90a roofline), playbook tier 3 TF32
      accumulation (no TF32 on gfx90a), tier 5 (TMA/cp.async do not exist on CDNA2), or the CUDA C++ backend.
      Use FlashInfer-Bench's tolerance policy (RVP-C6-23), **not** AutoKernel's 1e-2/2e-2 blanket, which is
      loose enough to admit an accumulator downgrade on the fp16/bf16 arms — the more so because its own
      playbook tier 3 sanctions changing accumulator precision as an optimization.
- [ ] **C5-15 — Adopt the KLineage BACKWARD-LINEAGE induction mechanism as a design candidate, and test it
      on one gfx90a expert kernel.** `intake-1249#record` inverts the family's direction: instead of
      generate-measure-keep-what-was-fast, it walks an EXPERT kernel BACKWARD through validation-gated
      de-optimizations, then RE-DERIVES each accepted backward step as a forward transition and re-validates
      it — supervision from expert artifacts rather than agent exploration. It is **train-free** and its
      profile gate is `triton.testing.do_bench` wall-clock with **`ncu`/`nsight`/`nvprof`/`nvcc` appearing
      nowhere**, so the machinery has no NVIDIA-profiler dependency. **The decisive open question for us is
      MODEL DOWNGRADE**: only Claude Opus 4.6 is ever evaluated, and the backward rewriter is the hardest
      reasoning in the pipeline. Run the loop on ONE gfx90a expert kernel from our own tree (an iqk MMQ path
      or a Composable Kernel GEMM) with a **locally-served** model; that single question gates the method for
      us and is answerable with one kernel. Nothing is released, so adoption means reimplementing the
      induction pipeline AND re-inducing from AMD expert kernels — do not plan around reusing their library.
      Also lift the nine-field **SkillCard** schema (intent, anchor, carrier, pre, effect, evidence, risk,
      scope, ver) as a STARTING POINT, noting explicitly that we ADD what they lack: a commit binding and a
      re-verification predicate (AK-PM-10).
- [ ] **C5-16 — Supply architecture documentation IN CONTEXT rather than relying on model priors, and cite
      the first external measurement of what scarcity costs.** `intake-1244#record` (CodegenBench) holds the
      architecture constant-across-tasks and varies only the chip: `Pass@1` falls from **0.74** on the
      well-documented architecture to **0.48** on the thinly-documented one, and to **0.00** for one model.
      **gfx90a/CDNA2 is our Sunway** — our corpus already carries three independent confirmations of CDNA2
      ecosystem abandonment (AITER dropped CDNA2, HipKittens never supported it, the sol-execbench fork ships
      zero cdna2 code). This is the citable prior for building a curated in-context CDNA2 reference (ISA
      excerpts, MI200 tuning-guide facts, wavefront-64 and LDS-bank specifics, MFMA shapes) into the
      authoring prompt. Note the effect is **NOT monotone across architectures** — the same model scored
      HIGHER on ARM-Kunpeng than on x86 — so do not cite "non-x86 is uniformly worse" as this paper's finding.
- [ ] **C5-17 — Adopt ordinal binning and calibration-as-a-gate for any performance predictor we ever
      build, and decline the trained artifact.** GPU Forecasters v1 (`intake-1240#02`, `intake-1240#03`, `intake-1240#04`; `dive-1240/source.txt:L86,L131,L148`) says fine-grained numerical inference is difficult without execution; it does not establish that numeric prediction is impossible or that ordinal output is the only tractable method in general. Keep forecast accuracy separate from calibration: the tested RL rewards reduce ECE while increasing numerical forecast error, and the six-task search records three surrogate wins, one tie, and two surrogate losses to the baseline (about 5% and 7%). Preserve the existing ordinal reward shape, ECE or Brier as an ACCEPTANCE gate, and explicit DEFERRAL to real gfx90a measurement. Decline the trained forecaster: it is A100-conditioned, and the reviewed paper supplies no cross-GPU transfer test despite its dataset spanning three GPU types; no gfx90a transfer is established. Any future comparison needs the equal-budget baseline arm alongside, never a single-arm demo. Preserve **Note-the-method-do-not-build-yet** while the loop is not trustworthy and RVP-C2-8/C2-9 are open.
      **Clause (2026-10-21): decision-level rank agreement on the deployment distribution.** A surrogate acceptance report also states rank agreement (Kendall tau or top-1) between surrogate-chosen and measured-chosen candidates on held-out recorded rounds, because prediction accuracy alone did not certify play quality; the held-out rounds for that check include candidates the planner chooses under the surrogate (the deployment distribution), not only uniform samples (`intake-2233#record`, `intake-2263#record`; the game domain is a mechanism, not evidence about kernels). Document edit only; no surrogate is built.

### Recorded so it is not re-derived — a pattern, no longer an incident

**"SUPPORTS PLATFORM X" IN THIS LITERATURE IS A CAPABILITY STATEMENT WITH NO EVIDENTIARY CONTENT.** Two
independent papers now ASSERT cross-platform capability and never MEASURE cross-platform transfer:
`intake-1087#record` (KForge) names cross-platform translation as an optional strategy and never ablates it;
`intake-1250#record` (Kernel-Smith) runs a MetaX MACA arm in which a **separate model was trained, the task
formulation changed and the benchmark changed** — so nothing measures what knowledge crossed the vendor
boundary. Treat such claims as unevidenced until an ablation is shown.

**METHOD TRANSFERS, TRAINED ARTIFACT NEVER DOES** — now well enough evidenced to state once rather than
re-derive per intake. `intake-1222` (KernelPro), `intake-662` (CudaForge) and `intake-1240` (GPU Forecasters)
all evaluate on one NVIDIA family and ship artifacts that cannot cross to gfx90a. Every number we would ever
produce from an NVIDIA-measured corpus on gfx90a is a **RE-MEASUREMENT, never a transfer** — the KLineage and
daVinci authors are themselves explicit that they do not claim cross-vendor skill transfer, and we must not
claim it on their behalf.

**LICENSING BLOCKERS to clear BEFORE any download** (open-source-self-hosted-only sourcing policy):
`github.com/GAIR-NLP/daVinci-kernel` has **no LICENSE file** (blocks reuse of its 960-skill corpus);
`github.com/parallelcodefoundry/ParEval-Repo` has **no root LICENSE** (GitHub reports `license: null`);
KLineage and Kernel-Smith release **nothing at all**. Public-and-unlicensed is not permissive.

## Research Intake Update — 2026-09-07 — FreeToken on gfx90a: DECLINE with reasons (intake-1318, 1343, 1345)

- *Classification*: it is a **port, not a rewrite** — Triton slot pool in flashlib (Apache-2.0), generic torch graph API, AVX-512-BF16 CPU branch, 22-line CUDA surface, working RDNA4 precedent. **But port-not-rewrite survives only as a classification, not as a cost estimate**: the community realisation of that "22-line surface" is ~750 lines across two unmerged PRs (#132, #378). `intake-1318#record`.
- *Gate 1 (dependency pins)* — upstream pins `torch>=2.11,<2.12` and `triton==3.6.0`; all three ROCm reporters run torch 2.11–2.15 on ROCm 7.14/10.1 nightlies; **we are on ROCm 6.2 deliberately** (see the ROCm-6.2 build-flag checklist note at :144 — issue #19984's unroll regression is gated behind the same version boundary). A port needs a host-level ROCm major upgrade under a FROZEN production kernel set — an operator decision, not a research task. This **supersedes** "untuned kernels on a different ISA family" as the stated reason. `intake-1343#record`.
- *Gate 2 (HIP-graph API floor) — THE STRONGEST, and it cannot be packaged around*: HIP stream memory operations are **not graph-recordable before HIP 7.14** (`hipGraphAddBatchMemOpNode` / `hipStreamBatchMemOpParams` absent from ROCm 6.2's HIP documentation; confirmed by PR #378's own `#if` guard and source comment), so on ROCm 6.2 even the fixed engine runs cpu/hybrid MoE with graph capture **disabled**. `intake-1345#00`, `intake-1345#01`.
- *Gate 3 (it does not build)*: `setup.py` requires `CUDA_HOME` and links `cudart`; `cpu_moe` includes `cuda_runtime_api.h`; the only ROCm support is three unmerged PRs whose own compatibility header enumerates **RDNA3/RDNA4 exclusively — no CDNA entry**. `intake-1345#record`.
- *Gate 4 (payoff)*: 0.73–0.86× vs fully-resident llama.cpp in **every** AMD configuration ever run; the one favourable ratio is set by a 6-core baseline we already beat by 3.2×; local ceiling on the mechanism is +27%. `intake-1343#00`.
- *Reusable facts banked here for a future ROCm porting session*: flashlib is Apache-2.0 Triton; both `pinned.py` defects are **fork-introduced regressions**, not upstream (upstream raises `ImportError`, the port replaced it with `return None`); PR #378 exists and is the community fix.
- *Declines recorded, with scope*: **port/adopt/trial FreeToken in any form** (1318#8, 1343#5, 1345#4); **build a q*-style bandwidth-adaptive miss splitter** (1318#9 — refuted on its own arithmetic before any implementation cost; our measured DRAM sub-linearity, 152.6 of 460.8 GB/s, is exactly the condition that makes the split net-negative); **chase Vulkan-vs-ROCm** (1343#6 — structurally unavailable: no Vulkan ICD targets CDNA2 compute-only parts, RADV enumerates zero devices on gfx90a per `design-backlog-triage-2026-07-23.md:229`; independent Linux data also shrinks the gap to +1.6%/+8.8%); **ingest the three further ROCm forks** (1343#7 — surfaced, not read; recording the decline scopes the negative rather than letting the sweep look exhaustive); **file the two architecture-independent findings** — `qsa_block_topk` tie behaviour (misattributed at the pinned commit, harmless by the reporter's own measurement) and `FREETOKEN_CACHE_DIR` (a doc defect in a project we do not run) — **beyond the notes in the entry** (1345#5); **chase the across-process topk tie variability** (30/39/46/62/82 of 2048 on identical seeded input, stable within a process) (1345#6 — the most interesting unexplained observation, needs Triton-level work on hardware we do not have; recorded so a reader knows what was left on the table).

## Research Intake Update — 2026-09-15 (search-strategy confound)

- [ ] **S3-INF03-01 — record that the eight-arm panel ranks WHOLE AGENTS, not search strategies.** Each arm brings its own editor/actor and there is no trivial search-policy arm (arm 1 is the no-authoring start state). Write this into the campaign contract, and add OR explicitly decline a greedy hill-climber arm that uses an existing actor as editor. intake-1375#00.
**S3-INF03-AIDE-1 trigger record — fixed-actor search-policy control.** Activate only after the shared selector replay finds a material held-out policy difference, or an already-running AutoKernel campaign can reuse its frozen actors, proposals, evaluator, and budgets without new generation infrastructure. Then compare greedy incumbent selection with an AIDE85-style five-arm UCB/fork policy while fixing model, prompts, context policy, task subset, seeds, and token/evaluator/wall budgets. Keep the final evaluator inaccessible and retain every proposal, branch, failure, score, and receipt. Sources: intake-1630#record and intake-1375#record.

## Research Intake Update — 2026-09-17 (SimpleTES code: RPUCG + ROCm eval path, intake-1454)

- [ ] **AR-RPUCG — A/B SimpleTES's RPUCG DAG parent-selection as a controller candidate in the MI210 verify+profile loop.** Selection-only over evaluated candidates (no re-execution; code @ `47d3413d`); compare against the current selection heuristic on one nonpromotable task; no NVIDIA-strategy import. Source: intake-1454.
- [x] **AR-ROCm-eval — register SimpleTES's ROCm eval path (AMD_REQUIREMENTS rocm6.2.4; `profile_program_roc`) and issue #6 MI300 config as gfx90a port input.** Study-only; no external-benchmark re-measure (AK-RB-1). Source: intake-1454. Pinned profiler/runtime/artifact seam, host-version mismatch and issue #6 caveat are registered below; no executable port or benchmark claim was made.

### AR-RPUCG/AR-ROCm-eval implementation intake — 2026-09-17

**AR-RPUCG data admission.** At SimpleTES `47d3413d`,
`simpletes/policies/rpucg.py` selects *already evaluated* nodes from a
parent→child DAG. Its selection uses each node's raw score, creation order,
chain membership, per-chain visit counts/total expansions, and one-hop
parent/child exclusions; the default policy parameters are `c=1`, `gamma=0.8`.
The current MI210 r19 archive is not such a dataset: the admitted first
actor cell's checkpoint records four broker evaluations and a final score,
while its individual `controller-evaluation-windows/*-result.json` receipts
carry source hashes and scores but no candidate/parent IDs, chain or visit
state. An exact JSON search of r19's cell receipts found no `parent_ids`,
`parent_candidate_id`, `chain_idx`, or `visit_counts`. Do not invent a DAG by
ordering these revisions, and do not describe a fixture comparison as the
requested A/B. The r19 archive remains diagnostic/nonpromotable under its
own campaign rules.

The minimum prospective, nonpromotable capture for **one named MI210 task** is
an immutable pre-selection snapshot: task and evaluator/recipe identities;
candidate ID, source hash, parent IDs, creation order, chain ID, valid
correctness and direction-normalized reward for *every eligible evaluated*
node; the exact incumbent eligibility set, choice and tie rule; and RPUCG
visit/expansion state before choice. Compare both selectors on precisely
that frozen pool, with equal inspiration count and no evaluator call from the
selector. Record chosen IDs, overlap, score/lineage of each choice and
selector cost. This is a **selection disagreement** result only; one logged
history cannot establish counterfactual downstream kernel quality. That
requires separately governed paired continuations with equal budget and
the standard correctness/timing claims. No live selector switch follows an
offline disagreement.

**AR-ROCm-eval port register (study-only).** Source pin: SimpleTES
`47d3413da1d85dc24341219d47452d2601e56a57`, AGPL-3.0-or-later,
`datasets/gpukernel/server/tasks/libkernelbot/run_eval.py`:
`profile_program_roc` wraps the supplied call in `rocprofv3`, requests
HIP/kernel/RCCL/marker/memory-copy/scratch traces in pftrace and CSV, and
packages traces/code objects. `run_eval.py` dispatches to it when the
detected runtime is `ROCm`. This is a profiler/artifact seam, **not** a
replacement for our parent-owned evaluator, sealed reference, claims or
promotion gate. The source's `server_info.yaml` points at private hosts and
must not be imported as a runnable service configuration. The source's AMD
environment note names ROCm 6.2.4, while this host's `hipcc` reports ROCm
6.2.0; our own `rocm-verify-profile-backend.md` records a side-loaded,
version-matched `rocprofv3`. A future port must pin the actual executable,
runtime and trace schema and validate gfx90a compatibility rather than infer
it from MI300. [SimpleTES issue #6](https://github.com/wq-will/SimpleTES/issues/6)
reports a released TriMul artifact near 1.390 ms but an independently run
MI300 search near 1.841 ms; its search-budget/variance/configuration question
is a warning against importing a headline or default budget as an MI210
expectation. No external benchmark was re-measured here.

## Research Intake Update — 2026-09-17 (cross-ISA port evidence; intake-1491)

**Cross-ISA port evidence (2026-09-17)**: a HIP-native SageAttention port exists but targets RDNA2/RDNA3 (gfx103x/gfx110x, WMMA/V_DOT — absent on CDNA2/MFMA); cite only as existence proof for cross-ISA porting, never as gfx90a evidence (intake-1491). CuTeDSL remains NVIDIA/CUTLASS-only and must not be imported (standing rule).

## Research Intake Update — 2026-09-25 (adversarial program evolution)

**Digital Red Queen activation trigger.** Materialize the following work only when EPYC has a real opponent-defined kernel workload and observes or must decide around cycling, forgetting, or nontransitivity. Ordinary candidate ranking and static correctness/performance panels do not fire this trigger.

- **S3-INF03-DRQ-1:** add external and historical cross-play over contemporaries, a stratified archive, and frozen unseen shapes/operators/edge cases; emit the pairwise matrix, dominance graph, forgetting, regret/exploitability, cycles, internal champion, population mean, and external-panel result with repeated-seed/opponent intervals. Sources: intake-1600#record, intake-1612#record, intake-1613#record.
- **S3-INF03-DRQ-2:** run matched random, neutral-mutation, non-LLM-mutation, static-opponent, score-only/no-archive, no-history, and archive-depth controls under equal evaluator, model-call, token, and wall budgets; retain every effective config and terminal summary in native receipts. Sources: intake-1600#record, intake-1611#record, intake-1616#record, intake-1617#record.

## Research Intake Update — 2026-09-26 (GEMM ladders and MFMA form on gfx90a; intake-1822..1826)

- [ ] **INF03-REGAUDIT-RUNNER — PROPOSED: bind the MMQ timing runner to the exact passing static ISA audit.** Refine existing INF03-REGAUDIT-2 coverage for the H10a/H10b rerun consumer: before timing in the next/reused runner, require incumbent/candidate audit records whose binary SHA-256 values match the selected libraries, nonempty relevant MMQ coverage, and the existing passing ISA diff or explicitly named accepted failures. Reuse the current audit/comparator/source; preserve historical experiment evidence rather than rewriting its receipts. Fixture acceptance: matching passing audits proceed; missing records, changed hashes, empty MMQ coverage and unaccepted FAILs stop before any timing process starts; deliberate removed J-cap instances remain permitted by existing policy. No new grading rule, performance campaign, parked-experiment reopening or production change. The historical J-cap run has a passing audit; this is a future enforcement gap, not a claim that it bypassed the gate. [Review](../../docs/reviews/research-intake-practical-applications-20261004.md); record discussion: intake-1826#record.

Dived: intake-1822 (HipKittens Helios GEMM ladder + code), intake-1823 (Gluon GEMM tutorial + repo, and a read-only
extraction of our production libggml-hip.so), intake-1825 (arXiv 2609.15627, DS-V4-Flash on MI250/gfx90a),
intake-1826 (LLVM #159493/#148079, MFMA VGPR/AGPR form). What transfers to gfx90a is lever ORDER and a short list of
ROCm 6.2 builtins (sched_group_barrier, iglp_opt, s_setprio, dword raw.buffer.load.lds); TDM, split barriers, clusters,
async b128 loads and WMMA do not exist here. MMQ at J=64 already spills at the 256-VGPR cap, so every register-affecting
candidate must pass a static audit first. The AGPR copy tax on <=256-thread MFMA kernels is a ROCm 6.2 compiler default
(intake-1826#record).

- [x] **INF03-REGAUDIT-1 — Standing zero-GPU static register/ISA audit for gfx90a HIP kernels.** ✅ 2026-09-27 — landed as research `scripts/kernel_rnd/gfx90a_isa_audit.py` (e603216f; `diff` exits 1 on new/larger spills, more hot-loop reloads or accvgpr copies, AGPRs appearing, lower occupancy). First audit `data/gfx90a-isa-audit-20260926/` (v10 f26a166b + v9). Confirms Q8_0 J=64 at 256 VGPR/37 spills, spill-free at J≤48; corrects the dive: MMQ has two hot k-loops (Q8_0 10/12 reloads; need_check=1 up to 34), Q2_K spills at J=48, FA-MMA reloads ~2x undercounted (DKQ=256 656–756/iter). v9→v10 regressed several MMQ types (Q5_0 15→46, Q1_0 21→61, Q4_0 nc=1 0→32, Q8_0 32→37 spills). Promote the
  intake-1823 dive scripts (`/mnt/raid0/llm/tmp/dive-intake-1823/ourbuild/`: split_fatbin.py, analyze_kernels.py,
  loop_analysis.py, agpr_rule_check.py) into the research repo with a README. Per kernel, emit: symbol, workgroup
  size, agpr_count / accum_offset, total and arch VGPR, vgpr_spill_count, private bytes, in-hot-loop spill reloads,
  in-loop v_accvgpr_read/write, s_waitcnt drains per iteration, and MFMA placement relative to s_barrier. Scope: MMQ,
  MMA-FA, rocWMMA FA, mul_mat_f. It is the accept gate for any MMQ/FA register-affecting candidate: no timing
  before it passes. Reads existing binaries only. Belief-kernel write side: SC84 amendment (P6).
- [x] **INF03-REGAUDIT-2 — make the ISA gate a hard step before timing.** Add `gfx90a_isa_audit.py diff <incumbent>
  <candidate> --families mmq,fattn_mma,fattn_wmma,mmf` to the kernel-promotion runbook/skill and the INF03-AGPR-1 arm
  protocol: must exit 0, or each FAIL is accepted by name in the package. Store both audit JSONs with
  `--category`/`--source-commit` so they feed SC84. ✅ 2026-09-27 — `.claude/skills/kernel-promotion/SKILL.md` step 3c
  plus the required `gpu_isa_audit` gate in `promotion_gates.yaml` (root lane `lane/park-20260927` `222a2f93`); the
  INF03-AGPR-1 accept clause below now names the same diff.
- [ ] **INF03-REGAUDIT-3 — investigate the v9→v10 MMQ spill regressions** (Q5_0 J=64 15→46, Q1_0 21→61, Q4_0
  need_check=1 0→32, Q8_0 32→37; Q2_K improved 346→35). Bisect which v10 change raised register pressure; feeds the
  J-cap (AK-MMQ-H10) and any MMQ forward-port.
  - PARKED 2026-09-27 (operator): not started. The regressions exist only as rows in the v9-vs-v10 audit (research `data/gfx90a-isa-audit-20260926/`), and no bisect build has been made. AK-MMQ-H10 came back NEGATIVE, so this is now the main MMQ register-pressure lead; resume by building gfx90a `libggml-hip.so` at bisect points between v9 `0db32c06e` and v10 `ffc1bac82` in an experimental worktree and running `gfx90a_isa_audit.py audit --families mmq` on each against the v9 audit (zero GPU).
- [ ] **INF03-AGPR-1 — NH-1 MFMA-form arm on ROCm 6.2** (gate lifted 2026-09-27: v10 FREEZE is the consolidated champion; audit supports excluding MMA-FA DKQ≥192, already at 512 VGPR with hundreds of reloads/iteration). On an experimental
  branch from the v10 tip, change the <=256-thread `__launch_bounds__(N,1)` of mul_mat_f (mmf.cuh) and rocWMMA FA
  (fattn-wmma-f16.cu) to `(N,2)`, with a separate `amdgpu_num_vgpr(128)` arm (waves_per_eu also raises the scheduler's
  occupancy target). Compile for gfx90a with ROCm 6.2. Accept only if `gfx90a_isa_audit.py diff <v10 audit> <arm
  audit> --families mmq,fattn_mma,fattn_wmma,mmf` exits 0 (the INF03-REGAUDIT-2 gate; audit each arm with
  `--category CANDIDATE --source-commit <sha>`) AND the arm's audit shows agpr=0, zero in-loop
  v_accvgpr copies and no new spills; no timing before that. Then run a matched same-window ABA with correctness. Exclude MMA-FA DKQ>=192:
  a 256 cap there would trade copies for scratch spills. Evidence: intake-1826#record, intake-1823#record.
  - PARKED 2026-09-27 (operator): not started. The gate was lifted 2026-09-27, but no experimental branch, build or audit exists; resume by branching from the v10 tip `ffc1bac82`, changing the <=256-thread `__launch_bounds__(N,1)` in mmf.cuh and fattn-wmma-f16.cu to `(N,2)` (plus the separate `amdgpu_num_vgpr(128)` arm), compiling for gfx90a with ROCm 6.2, and passing the `gfx90a_isa_audit.py diff` gate above before the matched ABA.
- [x] **INF03-GLUON-X — record, not work: Gluon and the tutorial's tools do not transfer to gfx90a.** Upstream Triton
  rejects BufferLoadToLocal on CDNA2, and local Triton 3.1.0 predates Gluon. amdgcnas hard-codes gfx950 registers,
  misses gfx90a `buffer_*` spills, and deletes in-loop s_nop wholesale. llirSched's cycle table is gfx950-only (gfx90a
  16x16 MFMAs are 8-pass). Do not port. (intake-1823#record) ✅ 2026-09-26
- Register-pressure datapoint (cross-reference only): intake-1825 Table 5 reports a 32x32 INT8 MFMA gate at 165 VGPR plus
  32 KiB LDS collapsing occupancy on gfx90a. That is independent support for INF03-REGAUDIT-1.


## Recovered C5 historical policy carrier — 2026-10-06

- [x] **C5-POLICY-PATH — restore default verification of the exact already-pinned historical policy bytes through a versioned Research evidence carrier.** MAIN independently verified90723-byte Git blob `f17f295b884889ba837709f1822e1045fad4a5cb`, original ROOT commit `97674cbce44146bd40778d50d1232fc62af8918d` and authenticated GitHub source identity. Keep SHA `c8cec57941b5c0954cd65b44719b984612d9c25094fce3e2ef4bcd42e8ec4f70`, evidence ID and all claims unchanged; add explicit repo-relative no-follow identity checks and actual default-loader/refusal controls. Existing absolute external authorities retain their verifier. No policy replacement, ratification, SOL/GPU run, production kernel edit or retrospective warrant. C5-5 persisted join is already complete; this is newly unlocked source work.
- [x] **AK-C517-1 — Surrogate acceptance: decision-level rank agreement on the deployment distribution (clause on C5-17).** Append to C5-17: a surrogate acceptance report also states rank agreement (Kendall tau or top-1) between surrogate-chosen and measured-chosen candidates on held-out recorded rounds, because prediction accuracy alone did not certify play quality; the held-out rounds for that check include candidates the planner chooses under the surrogate (the deployment distribution), not only uniform samples (intake-2233#record, intake-2263#record; the game domain is a mechanism, not evidence about kernels). Document edit only; no surrogate is built. Acceptance: the clause is on C5-17. Estimate: 0.1 day. ✅ 2026-10-21

2026-10-06 MAIN acceptance: C5-POLICY-PATH completed after exact source publication and independently reviewed original28/28; [bounded acceptance](../../artifacts/ni08/c5-policy-path-source-20261006/README.md). Historical policy bytes and existing grader unchanged; no SOL/GPU/runtime warrant.

### 2026-10-31 C5-7 conditional source seam

Research implementation `39b63b061238d52d0669d2d9eb3e4d3f29affd11` adds the explicitly declared counter gate at the actual hip_decision_grade terminal decision: wrong/missing/ambiguous counter evidence suppresses the opted-in speedup belief and rankability, while absent declarations preserve legacy behavior. The bounded raw-CSV reader hashes and parses one stable buffer and binds exact counter/kernel/dispatch, source, campaign, workload, units and normalization; zero remains valid.19 focused tests, compilation and diff checks passed. Evidence: Research `scripts/kernel_rnd/autokernel/controller/test_hip_decision_grade.py`; ROOT `progress/2026-10/2026-10-31-c5-7-counter-gate.md`. This replays externally supplied profiler receipts only: no end-to-end PMC capture, broader native caller or live activation is established. C5-7 remains open, with no completed-code-quota claim. [no-belief: conditional source and synthetic replay controls]

### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

Operator-approved 2026-10-31 (plan revision 2, `research/intake-stage3-plan-2026-10-31-ws58.md`, sha256 `043e502133cae214175ea3f2a395f575e6ca13b9f3ee058525ed020264ab5012`; relayed by the ws58 coordinator; budget approved: about 13 MI210-hours for the drafter pilot, 6-9 engineer-weeks for the race checker, the 95.5 GB ThinkingCap download; D1 confirmed: in-weights calculator declined, GPU reason recorded on intake-2550/2574; D2 approved: scratch upstream builds are measurement instruments only). Trigger records below are prose with no checkbox until a reviewed session confirms their condition.

- [ ] **C5-ISA-1 — Archive the AMDGCN ISA of every AK GPU candidate and check the claimed instructions executed (intake-2555#record, intake-2588#record).** Store the hipcc --save-temps .s (or llvm-objdump of the code object) of each touched kernel in the candidate record next to its source diff. When a candidate claims a mechanism (MFMA, LDS staging, buffer loads), confirm in the ISA, and with a rocprof instruction counter where one exists, that the instruction executes on the measured path; a candidate whose claimed instruction is absent is refused.
- [ ] **C5-ISA-2 — GCN-Gym: LLM-edited AMDGCN for a compute-bound gfx90a kernel whose limiter is register allocation (intake-2555#record, intake-2556#record).** Not trigger-gated, because the HIP-source levers on the target are measured out: AK-MMQ-H10 (J-cap) NEGATIVE, the ak-27b-gpu-verify stream-k MMQ hypotheses were all refused or retired, and the ROCm 6.2 AGPR copy tax and MMQ spills are compiler-side (INF03-REGAUDIT-1: Q8_0 J=64 at 256 VGPR with 37 spills; MMA-FA DKQ>=192 at 512 VGPR with hundreds of reloads per iteration). Build a standalone harness (1-2 weeks). Extract the gfx90a .s of one kernel from an experimental v10-tip build via gfx90a_isa_audit.py; let the agent edit it with unified-diff patch tools; reassemble with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a; load with hipModuleLoad; replay the served-shape launches (the RVP-RACE-2 capture shim); diff-test against the hipcc kernel with the AK oracle (host-double for Q8_0); require gfx90a_isa_audit.py diff to exit 0, and the RVP-RACE-2 verdict once M2 lands. Target 1: MMQ Q8_0 J=64 prefill tile. Target 2: MMA-FA DKQ>=192. Run 3 runs per target at a fixed declared token budget on a frozen shape manifest; time on the GPU window with ABBA (>=2 pairs) against the hipcc incumbent, keeping per-run raw candidate .s, oracle outputs and timings. Decision rule: if >=1 of 3 runs on a target reaches >=1.05x kernel time at the served prefill shape, passes the oracle, and its ABBA intervals do not overlap the incumbent, open an experimental-tree code-object override path for that kernel as an ISA-rung AK arm; otherwise record the null with traces and stop the ISA rung for that kernel class.
- *Intake knowledge note, K5, row KERN-9 (intake-2556#record):* Keep the AK-PL-1 prompt-leak guard. If diagnostic failure feedback (failing indices/values) is ever adopted from TAIC, generate it on a feedback seed disjoint from the acceptance seed population.

## Track: mi210-q8-dequant-gemv-roofline
<!-- gate: INF-48, EVL-47 -->

> Folded from `handoffs/active/mi210-q8-dequant-gemv-roofline.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F23, route 1a, operator D1/D5; retired row INF-37 → INF-03). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Handoff: MI210 single-stream roofline — Q8 dequant-GEMV kernel + batch-1 latency levers

**Scratch**: `/mnt/raid0/llm/tmp/mi210-moe-q8-fusion/` · worktrees: `/mnt/raid0/llm/worktrees/mi210-moe-q8-fusion-*` (new follow-up only; historical evidence is not relocated).

**Status**: OPEN — Q4_K inside-kernel attribution and IQ2 governed replay remain live. **Created**: 2026-07-04 (Fable5 window-2 MI210 campaign follow-on).
**Owner tree**: `/mnt/raid0/llm/llama.cpp-experimental`; all new work starts from current frozen production (v10 as of 2026-10-04) in an isolated experimental branch. The old `upstream-mtp-verify`, production-v6/v9, and `build-hip/` instructions below are historical only.
**Substrate**: MI210 gfx90a/CDNA2, 64 GB HBM2e, ROCm 6.2. Current runs follow P-GPU-1, exclusive device claims, numeric in-window sampling, and the governed INF-48 profiler runners; pre-P-GPU-1 observations below retain their historical authority only.
**Context doc**: `handoffs/completed/fable5-window2-findings-05b-mi210-inference-architecture.md` §1/§9.

#### UPDATE 2026-07-04 — measured results REFRAME this handoff (Tier-1 premise is WRONG; async-prefetch is the lever)

Kernel-thread `a8afd338` executed the levers below. Corrections, most important first:

1. **Tier-1 lever 2 (fused dequant-in-GEMV) is a NON-TASK.** The Q8_0 GEMV is ALREADY int8-native — `vec_dot_q8_0_q8_1` (`vecdotq.cuh:797`) uses `ggml_cuda_dp4a` integer MAC + one fp scale per 32-block, i.e. the CPU iqk "dequant-under-load" pattern is already implemented on GPU. There is **no per-element fp dequant to hide.** The **47→62% gap is achieved-bandwidth / occupancy, NOT dequant-compute.** Do not port iqk to "hide dequant" — there is nothing to hide.
2. **The real lever is Tier-2 lever 3 (async weight-prefetch / memory-level-parallelism).** Down-payment already LANDED: **nwarps 2→4 for batch-1 Q8_0 on CDNA2 = +4.6% (28.99→30.32 t/s)**, `test-backend-ops MUL_MAT` 1103/1103, committed **`5dc116130`** (fork `upstream-mtp-verify`). Async prefetch (`raw.buffer.load.lds` LDS double-buffer) is now in build+measure — exact gfx90a intrinsic design in [mi210-batch1-latency-wall-greenfield.md](../completed/mi210-batch1-latency-wall-greenfield.md).
3. **Tier-1 lever 1 (`quantize_q8_1` requant) = DEFER.** Measured **3.37%** of decode (this build; 5.68% on the older mi210-hip build). Every GEMV re-quantizes its own activation (call-count == `mul_mat_vec_q` count); localized prologue-fusion is *counterproductive* (would requant the activation `gridDim.x`≈thousands of times). Only fix is graph-level (q/k/v activation caching, or fuse into the preceding RMSNorm), ceiling ~1.5–3% with correctness risk on the 82%-of-decode hot path → not worth it now.
4. **Tier-3 lever 6 (n-gram / prompt-lookup GPU spec) = MEASURED NEGATIVE.** All variants regress on the 27B: plain 28.4 → ngram-simple 27.7 (best) → ngram-cache 26.1 (worst); context-only acceptance **~15%**, below break-even. A zero-cost n-gram does NOT beat plain single-stream here — a real trained drafter (draft-mtp/eagle3) remains the path. (Corpus-static ngram, CPL-4b, is separate but must clear a HIGH acceptance bar to beat this negative.)
5. **rocprof note**: v1 aborts at init on this build (PDL/graph kernels) — use **rocprofv2** with the `pmc:` prefix, and add `/usr/lib/x86_64-linux-gnu` to `LD_LIBRARY_PATH` (`libpciaccess.so.0`).

Net: the Tier-1 dequant framing is superseded. The live single-stream track is **nwarps (done +4.6%) → async-prefetch → SoA-repack**, toward the fp16 62% ceiling. Levers below are kept for the record; read them through this update.

#### L3-MoE / L15 quantized-MMQ bet — scope said GO, **BUILD FALSIFIED IT: L3-MoE occupancy rewrite = NO-GO** (2026-07-04)

**Phase-1 result (measure/build-first worked as intended):** the compact-LDS rewrite was BUILT + gated + correct — LDS halved 49→25 KB, LDS-limited residency 1→2 WG/CU, accumulator untouched; `MUL_MAT 1103/1103`, `MUL_MAT_ID 789/789`, PPL indistinguishable — but occupancy stayed **FLAT (3.07→3.07)** and aggregate moved **+1.6% B=32 / −12% B=64**. **The Phase-0 LDS-limit premise is FALSIFIED with data:** at B=32 Q8-MMQ is **grid-limited** (grid = 53248/512 = exactly 104 WGs = 1 WG/CU → no second workgroup to place in the freed LDS), NOT LDS-limited. bf16's aggregate win is its **native-MFMA / zero-dequant compute**, not an occupancy edge Q8 could match by freeing LDS. Raising Q8-MMQ aggregate needs MORE workgroups → **stream-K K-splitting** (a bigger separate bet w/ fixup-kernel overhead; the gated compact-LDS kernel is the ready substrate, saved `campaign/mmq-compact-lds-NEGATIVE.patch`) — or smaller `mmq_y` (forbidden: halves the accumulator; campaign already measured mmid-forcing negative). **Settled: bf16-for-aggregate (B≥16–24), Q8 only for HBM-capacity.** **L15 (sub-4-bit capacity unlock) is INDEPENDENT of this occupancy result and still viable.** The optimistic scope below is kept for the record — read it through this result.

The aggregate-MoE #1 kernel lever, scoped + de-risked into a fundable GO with a concrete mechanism + a measured target.
- **Mechanism (de-risked):** Q8 `mul_mat_q`'s occupancy limiter is the **dequant-staging LDS (45–49 KB > half of 64 KB) + Arch-VGPR (128)**, which caps residency at exactly **1 WG/CU** (grid = 104 WGs) → ~2.5 waves resident → memory unit under-driven at **32%** vs bf16's 48% (the 1.5× maps onto the measured +32% gap). **NOT the MFMA accumulator tile** — bf16 wins with the SAME ~128 Acc-VGPR, just smaller LDS (12.8–25.6 KB) + tiny Arch-VGPR (16). So the "shrink the MFMA tile / lose efficiency" risk is OFF the table; the lever is halving the **staging** footprint only.
- **Target** = bf16's own measured profile: LDS 49→~24 KB, Arch-VGPR 128→~64 → **2 WG/CU** → MemUnitBusy 32→~48% → occ 2.55→~3.2. **Payoff: Q8 aggregate B=32 from 563 t/s toward bf16's 744 — Q8 aggregate-competitive at HALF the HBM.** Residual: at B=128 bf16 also wins on native-MFMA FLOPs, so occupancy alone won't fully erase the top-end; "competitive at half HBM" is the residency-bet goal + achievable. Risk = more dequant recompute / less N-reuse if staging cut too far.
- **L15 sub-4-bit — path ALREADY EXISTS + numerically correct on CDNA2** (not MMVQ-only): IQ2_XXS/XS/S, IQ3, IQ1, Q2_K, Q3_K all MMQ-supported (`mmq.cu:267`) with MFMA tile mappings; CDNA2 gate routes them to MMQ when `n_experts>64 OR ne11≤128`. Live-confirmed (HEAD 7c28056b7): `MUL_MAT 1103/1103` + **`MUL_MAT_ID 789/789, 0 FAIL`** across q8_0/q2_K/iq2/iq3/iq1/iq4. **Missing = a quantized GGUF + the SAME occupancy rewrite** (IQ codebook dequant is MORE LDS-hungry → needs it more than Q8). **Capacity: Qwen3.5-122B-A10B @ IQ2 ≈ 38 GB FITS → fully GPU-resident (the big residency-bet unlock); GLM-5.2 ~238 GB does NOT fit** even at IQ2. **STATUS 2026-07-04: Qwen3.5-122B-A10B UD-IQ2_M (40.4 GB, unsloth) is DOWNLOADING** (in flight ~11%+; obviates the "quantize an IQ2 proxy" step in the build sequence) → on completion, measure PPL + aggregate vs the existing UD-Q4_K_M benchmarks. L15 measurement PENDING.
- **Shared kernel family (one investment, two payoffs):** `mul_mat_q_case<TYPE>` → single `mul_mat_q` device kernel; the LDS-staging/accumulator/occupancy body is SHARED, only `load_tiles` (per-type dequant) differs. **L3-MoE (the shared-body rewrite) is the prerequisite for L15 being fast.**
- **Build sequence:** Phase 0 (sub-4-bit MMQ correctness ✅; remaining = quantize an IQ2 proxy + operator-gated IQ2-vs-Q8 bench) → **Phase 1 (shared LDS-staging/occupancy rewrite, IN PROGRESS)** → Phase 2 (apply to IQ2/IQ3 + retune codebook dequant + quantize 122B→IQ2).
- **Key files:** `ggml/src/ggml-cuda/mmq.cu` (267–340), `mmq.cuh` (MMA tile map 239–264, LDS `MMQ_MMA_TILE_X_K_*` 219–225). Prior CSVs: `campaign/moe-agg/prof/pmc_{q8,bf16}/`.

#### UPDATE 2026-08-03 — the gap is ONE handoff but TWO mechanisms; splitting them (research-intake Stage-2b)

_Via `/research-intake` Stage-2b dive 2b-C. This **refines** the 2026-07-04 update above, it does not
contradict it — the recomputed ladder reproduces the existing fable5 series to within 1 pp._

**The full quant ladder, recomputed on one consistent GiB basis** (spec-BW denominator; see the calibration
caveat below), with `mul_mat_vec_q` measured at **77.8% of decode time**:

| Rung | Bandwidth attainment |
|---|---|
| fp16 (llama.cpp) | **62.6%** |
| fp16 (vLLM-ROCm, same device) | **69.2%** |
| Q8_0 | 50.2% |
| Q4_K | 35.1% |
| MoE-bf16 | 34.4% |
| MoE-Q8 (frontdoor) | 21.3% |
| **MoE-IQ2 (architect, `Qwen3.5-122B-A10B UD-IQ2_M`)** | **10.3%** |
| Qwen3-Next-80B i1-IQ2 | 3.3% |

**The reading that matters: 62–69% is already reached on this device, so the memory system is not the
limiter.** The collapse is entirely down the quant ladder. For reference, DGX Spark GB10 reaches **77–80%
at Q4_K_M dense across five models** on the same engine — NVIDIA's quant sag is 5–10 pp; ours is 27 pp.

**Why this handoff now carries two items instead of one.** The 2026-07-04 update's finding —
*"the 47→62% gap is achieved-bandwidth / occupancy, NOT dequant-compute. Do not port iqk to hide dequant"* —
is **correct, and it is correct for Q8_0**, whose GEMV is already int8-native. But **Q4_K 35→50 is a
different mechanism** (k-quant superblock unpack, not occupancy), and treating the two as one gap has
already produced one wrong verdict. They are filed separately in the checklist below.

**Corrected IQ2_XXS characterization** (verified read-only against our tree, supersedes the
"four *dependent* random reads plus *a* sign-table read" framing): per 32 quantized weights there are
**four INDEPENDENT data-dependent gathers** into a 256-entry / 2 KiB grid — all four indices arrive in a
**single 8-byte `memcpy`** (`ggml-quants.c:2500`), so no address depends on another lookup's result, ILP ≈ 4,
**not a pointer chase** — plus **FOUR** sign-table gathers (`ksigns_iq2xs[…]` is inside the `l` loop), each
grid entry expanding to 8 values. The 4+4 ratio holds across every SIMD path including our production iqk
(`iqk_gemm_iquants.cpp:176-181`, signs `:86-90`), AVX2, and CUDA.

**Calibration — MEASURED 2026-08-03, and the correction is smaller than estimated.**
`epyc-inference-research` `328b768d`, receipt
`data/mi210-achievable-bandwidth/20260803T124401Z/receipt.json`
(SHA-256 `0aab9c7e135929e72fd3a5c2498eb807dc16d0f80b773f063e1df3524df7b4d3`).

**Achievable = 1433.3 GB/s, i.e. 87.5% of the 1638 GB/s datasheet peak** — high for HBM2e. Triad 1371.1;
per-kernel medians copy 1412.5 / mul 1413.9 / add 1362.3 / triad 1362.1, p20–p80 within ~1.2%; 10 warmup,
50 timed, correctness PASS (max abs err 0.0). **Correction factor 1.143×, not the 1.17–1.26× estimated
here before the run — the prior ~1.3–1.4 TB/s guess was low.**

| Rung | % of spec (1638) | % of **achievable** (1433.3) |
|---|---|---|
| fp16 | 62.6 | **71.5** |
| fp16, vLLM-ROCm | 69.2 | **79.1** |
| Q8_0 | 50.2 | 57.4 |
| Q4_K | 35.1 | 40.1 |
| MoE-bf16 | 34.4 | 39.3 |
| MoE-Q8 (frontdoor) | 21.3 | 24.3 |
| **MoE-IQ2 (architect)** | **10.3** | **11.8** |
| Qwen3-Next-80B i1-IQ2 | 3.3 | 3.8 |

**⚠ THE BASIS WARNING, and it is the most important line on this page.** Converting *our* numbers to an
achievable basis while leaving *someone else's* on a spec basis makes the gap look smaller without it
being smaller. **The AMD-vs-NVIDIA comparison must stay spec-to-spec** — our fp16 62.6 against DGX Spark
GB10's 77–80, both against datasheet — **until somebody measures GB10's achievable bandwidth.** Our
71.5%-of-achievable set beside their 77–80%-of-spec is a mixed-basis comparison and is not a reading.
This measurement makes our own numbers physically meaningful; **it does not narrow the NVIDIA gap at all.**
That is precisely the error found this session in AMD's own KB, where a per-OAM TFLOPS figure was divided
by a per-GCD bandwidth to give a ridge point off by 2×.

Use the **achievable** column for headroom and campaign sizing (it is the real roof); use the **spec**
column for any cross-vendor comparison, and say which one you used — a utilisation quoted without its
denominator is not a number.

**The E8M0 divergence is instrumented, and its first classification was WRONG** ✅ 2026-08-03.
`CONFORMANCE-VECTORS-1` ships at `epyc-inference-research/conformance/` (research `33f7076b`): three
contracts, harnesses that **execute the real CPU and HIP decoders** (27 values, gfx90a, all matching),
and 15 tests. Three backend rows are now **VERIFIED** rather than asserted — including the HIP row,
where which branch of `#if CUDART_VERSION >= 12080` is taken was previously *inferred* from source and
is now *observed* on the card.

**RETRACTED: "documented-divergent, not a defect."** That rested on `validate_e_e8m0` rejecting
`0xFF` at load — but that gate runs only under `check_tensors`, which **defaults to false** and is
passed by none of our launchers. And it is not dead code: **both paths are live.** CPU MXFP4 uses
fused `_half`; GPU MXFP4 uses `full(e) * 0.5f`. They agree everywhere except `0xFF`, where
`+Inf × 0.5` is still `+Inf` while the fused half gives a finite 2^127.

**What actually bounds it is weaker: we serve no MXFP4 model** — a property of the fleet, not the
code. So the claim is now *checked*: a sentinel fails the moment an MXFP4 model enters the registry
or lands on disk, carrying the remediation options. Recommendation is to rely on the sentinel now and
pass `--check-tensors` the moment an MXFP4 model is proposed.

**Free incidental finding in our own CPU tree, filed here because it is the same IQ2 sign path:**
`iqk_gemm_iquants.cpp` contains an AVX512-VPOPCNTDQ routine deriving IQ2 signs arithmetically with **zero
table reads**, but its dispatch at `:184` is guarded by `#if defined z_HAVE_FANCY_SIMD && …`. **The `z_`
prefix makes the macro undefinable, so the branch is permanently dead** (same at `:109`, `:571`) and the
table lookup always runs — **including on our Zen 5 host, which has VPOPCNTDQ.** Inherited verbatim from
ik_llama.cpp via `fec061dea`; not introduced by us. Experimental branch only — production is frozen.

#### Objective

**Historical framing below is superseded:** the Q8_0 GEMV is int8-native, and the Q8 gap is an achieved-bandwidth/occupancy question, not per-element floating-point dequant. Use the updates and checklist above and below for current decisions.

Raise **single-stream** GPU decode throughput for the qwen35/Q8 family toward the bandwidth roofline. Measured today: Q8 decode ~47% roofline (766 GB/s), fp16 ~62%, and rocprof attributes single-stream decode ~78% to `mul_mat_vec_q` (the Q8 weight GEMV) + 5.68% to `quantize_q8_1` (activation requant). Two gaps: **47→62% = Q8 dequant cost** (kernel-addressable); **62→100% = batch-1 latency wall** (memory-level-parallelism, harder). This handoff attacks both.

#### Why this matters / transfer

- The already-landed MMVQ→MMQ dispatch fix (`de447119f`, `mmvq.cu:323` CDNA2 `case GGML_TYPE_Q8_0: return ne11<=1;`) gave +17% (27B) / +31.7% (gemma-31B) on the **MTP-verify** batch. This handoff is the **plain single-token** decode, the dominant path.
- Transfers to every GPU-resident Q8 role (the deferred residency bet): frontdoor, and any dense-Q8 model.
- The dequant kernel also unlocks **sub-4-bit** viability (bytes/token axis, below).

#### Levers, ranked (each ships with its decisive experiment)

The following original ranking and experiment sequence are historical; the updates and current checklist supersede their Q8 premise and prioritization.

##### Tier 1 — the dequant gap (47→62%, kernel-addressable, highest confidence)
1. **Kill the `quantize_q8_1` activation-requant overhead** (measured 5.68% of decode). The GEMV requants activations to Q8_1 every step; investigate fusing it into the GEMV prologue or caching. *Experiment*: rocprof before/after; acceptance = quantize_q8_1 share → ~0, decode +5%.
2. **Fused dequant-in-GEMV / int8-native MMQ path for batch-1.** Current `mul_mat_vec_q` dequantizes Q8 blocks then does fp accumulate. Port the CPU **iqk** approach (weight-block-outer, dequant-under-load; ref `ggml/src/ggml-cpu/iqk/iqk_gemm_legacy_quants.cpp:302-330`) to HIP, or hide dequant under the HBM weight load. *Experiment*: single-stream `llama-bench -n 128` Q8 vs the fp16 62% ceiling; acceptance = Q8 decode → ~55-62% roofline (~34-38 t/s on 27B, +15-30%), PPL/output unchanged.

##### Tier 2 — the batch-1 latency wall (62→~80%, harder, MLP-bound)
3. **Async weight prefetch / double-buffering** in the GEMV — software-pipeline the next weight tile's `buffer_load` under current compute (Little's law: more requests in flight → higher achieved BW). *Experiment*: rocprof MemUnitStalled + achieved-BW before/after; acceptance = achieved BW 62%→~70%.
4. **Persistent/megakernel decode** (CUDA-proven, NO ROCm version — greenfield, high-effort). Fuse decode into one launch, weights streamed with pipelining; the Hazy/Mirage ~78% single-dispatch result. *Scope first, don't build blind* — estimate launch-overhead fraction via rocprof gap-analysis before committing.
5. **Weight swizzle/layout for gfx90a** — verify MMVQ HBM access is coalesced to the 64-wide wavefront + 128B cache line. *Experiment*: rocprof L2/MemUnit efficiency; a layout change is only worth it if coalescing is measurably poor.

##### Tier 3 — sidestep / bytes-per-token (orthogonal, can exceed BW-% gains)
6. **n-gram / prompt-lookup speculation on GPU** (`--spec-type ngram-simple|ngram-cache|ngram-map-k`, already in v6, UNTESTED on GPU). Zero-cost draft → converts batch-1 into batch-N verify → more MLP + amortized weight read, at high acceptance for code/JSON/repetitive output. *Experiment (cheap, no kernel)*: run `--spec-type ngram-*` on the 27B over a code/structured prompt set, measure decode t/s + acceptance vs plain. **Do this FIRST — it's the cheapest single-stream win and needs no kernel.**
7. **Sub-4-bit weights (IQ2/TQ1/TQ2) + efficient CDNA2 dequant** — fewer bytes/token → higher absolute t/s even at same roofline-%. Gated on Tier-1 dequant kernel + an eval-parity/PPL quality check. *Experiment*: IQ2/TQ quant of the 27B, decode t/s + PPL vs Q8.
8. **KV-quant for single-stream LONG context** (q8-KV, `-fa 1`) — distinct from the aggregate case (where it was dead): at batch-1 long context the KV read adds to bytes/token. *Experiment*: 27B decode at 64k ctx, q8-KV vs f16-KV.

#### Start-here sequence for the executor
1. **Lever 6 (ngram-spec) FIRST** — cheapest, no kernel, may bank a single-stream win in an hour.
2. **Lever 1 (quantize_q8_1)** — small, high-confidence kernel win.
3. **Lever 2 (fused dequant-GEMV)** — the main event; port the iqk pattern to HIP.
4. Then Tier-2 (prefetch/megakernel) only if Tier-1 leaves the 62% gap and it's worth the effort.

#### Correctness / measurement discipline
- Every kernel change: `test-backend-ops` parity + PPL/greedy-output unchanged (the MMVQ fix was numerically-valid-not-bit-exact; document the same for any new kernel).
- Pair every speed number with a correctness check. Label OBSERVATION until a P-GPU-1 protocol exists.
- Do NOT commit to production-consolidated-v6; experimental only, operator-gated for promotion.

#### Key files
`ggml/src/ggml-cuda/mmvq.cu` (dispatch + `mul_mat_vec_q`), `ggml/src/ggml-cuda/quantize.cu` (`quantize_q8_1`), `ggml/src/ggml-cuda/ggml-cuda.cu:2554-2617` (mul_mat dispatch), CPU reference for fused approach: `ggml/src/ggml-cpu/iqk/iqk_gemm_legacy_quants.cpp:302-330`. Profiling artifacts: `/mnt/raid0/llm/tmp/mi210-build/campaign/{prof,finish}/`.

#### Progress checklist

- [x] nwarps 2->4 (+4.6%, committed 5dc116130) ✅
- [x] async weight-prefetch raw.buffer.load.lds (historical +3.3%, committed 7c28056b7; subsequent governed replay +0.936%, below the 2% floor, **NOT_REPRODUCED**; see Item A) ✅
- [x] L3-MoE compact-LDS occupancy rewrite (BUILT + FALSIFIED, NO-GO) ✅
- [x] L15 sub-4-bit: quantize 122B->IQ2 proxy + operator-gated IQ2-vs-Q8 bench ✅ **2026-07-29 — the "PENDING" predates the run.**
  Both halves landed 2026-07-05: 122B UD-IQ2_M GPU-resident at 43.7 t/s single / 148.7 agg @B32, PPL 5.02
  (`progress/2026-07/2026-07-05-mi210-capability-kernel-rnd.md:23-24`), and the IQ2-vs-Q4 paired eval returned Δ0.0pp,
  McNemar p=1.000 (`progress/2026-07/2026-07-05-mi210-residency-and-cot-reframe.md:12`). Certified by read-certification (`auditor`).
- [ ] SoA-repack lever (only if coalescing measured poor - currently deemed healthy)
  - **2026-11-02 source check:** the historical healthy disposition is recorded in
    `progress/2026-07/2026-07-03-mi210-qwen36-27b-speed-campaign.md:124`; a numeric coalescing
    counter receipt was not located in checked-in documentation. The October S7 planar-layout seed
    is source-only, not new evidence of poor coalescing. The repack condition is not established;
    keep it conditional and do not treat the historical assessment as a newly verified counter result.
- [x] Generic stream-K K-splitting for Q8-MMQ aggregate is already present and therefore not a new
  lever ✅ 2026-08-11 — the current CDNA MMQ path is persistent stream-K, and the governed WGM
  experiment exercised that exact launch. Retain only a distinctly justified higher-persistent-grid
  residual (for example `2*nsm`) behind fresh grid/occupancy evidence; do not reopen “add stream-K.”
- [x] Recompute the full quant ladder on one consistent basis (fp16 62.6 / Q8_0 50.2 / Q4_K 35.1 / MoE-Q8 21.3 / MoE-IQ2 10.3) ✅ 2026-08-03 — via /research-intake Stage-2b; reproduces the fable5 series to within 1 pp
- [x] Correct the IQ2_XXS access characterization: four INDEPENDENT gathers (single 8-byte memcpy, ILP≈4) plus FOUR sign-table gathers, not a dependent pointer chase with one sign read ✅ 2026-08-03
- [ ] **Item A — Q8_0 50→62 rung (achieved-bandwidth / occupancy).** There is no per-element fp dequant to hide; do NOT reopen an iqk port for this rung. The governed frozen-v9 replay now supersedes async-prefetch as a presumed win: its 20-block median was only **+0.936%**, below the 2% floor, with one negative block (`NOT_REPRODUCED`; receipt SHA-256 `7b173cafcccb8a99319bf93a80fd13a2e94a400afab2bf03355363f9521ab17f`). Reopen only from fresh cache-line/MLP profiling evidence, not the 2026-07-04 patch prior.
- [x] **Item B — attribute the Q4_K superblock-unpack mechanism before authoring.** ✅ 2026-08-11 —
  the representative-shape mechanism-counter route below passed. It supports a materially larger
  instruction burden than the same-bit Q4_0 control, but not the former +38–43% single-lever premise.
  - **2026-08-11 bounded op probe:** the hash-bound single-process C4 reports at
    `/mnt/raid0/llm/autokernel/probes/c4-{q4k,q8}-op-singleproc-20260811T12{10,15}Z/report.json`
    hold `m=16,n=1,k=256` and the dispatch sequence fixed. Q4_K versus Q8_0 `mul_mat_vec_q`
    share is 41.95% versus 40.92%, and per-dispatch duration is ~5.72 versus ~5.50 µs. That small
    synthetic surface does **not** explain the 35→50 roofline rung and cannot see unpack work inside
    the fused kernel. Item B therefore remains open for a representative-shape counter/source-timer
    probe; the current result prevents mistaking a complete kernel-family table for the requested
    inside-kernel attribution.
  - [x] **Run the representative-shape single-pass PMC differential and resolve what is identifiable.**
    ✅ 2026-08-11 — clean frozen-v9 `test-backend-ops` ran four balanced blocks × five exact
    dispatches at model-derived `m=17408,n=1,k=5120`. A single rocprofv2 pass collected
    `SQ_WAVES`, `SQ_INSTS_VALU`, and `SQ_INSTS_VALU_INT32`; every counter was exactly invariant
    within and across blocks. Q4_K and the same-bit Q4_0 control both launched 34,816 waves, but
    Q4_K carried **+112.5 VALU instructions/wave**, **+35 INT32 instructions/wave**, and a
    **+11.751%** median dispatch duration (77,600 vs 69,440 ns). Q8_0 launched twice the waves, so
    it remains the quant-ladder control rather than the closest unpack control. The fused dispatch
    makes an exact inside-kernel wall share unidentifiable; the admissible result is differential
    mechanism evidence, not a fabricated share. Receipt:
    `/mnt/raid0/llm/autokernel/probes/inf37-q4k-unpack-v9-20260811-r7/receipt.json`, SHA-256
    `1e34339c1c986413c4eeb1b56ba3202c8763d08df45aba1c0580917c888f5e47`; research
    `70374c43` (promoted via `ac88d75a`). Four rocprofv2 exit-139 attempts were retained and only
    transport-retried under the predeclared two-attempt ceiling; no parsed counter failure was
    retried. **The former +38–43% single-lever expectation is not supported by this matched
    diagnostic.** Before authoring, use the exact instruction delta to define a surgical unpack
    change and test whether it can recover part of the observed ~10.5% Q4_K-to-Q4_0 headroom.
  - [x] **Author and test one surgical Q4_K unpack hypothesis.** ✅ 2026-08-11 — the candidate removed
    the two lane-local Q8 partial-sum `dp4a` operations per `QR4_K` iteration and consumed the
    already-stored `block_q8_1.ds.y` sum. It failed **5/5** representative Q4_K correctness cases
    (relative errors 0.729–0.977 versus the 0.0005 limit), while frozen v9 passed 5/5 under a separate
    released MI210 claim. The reason is structural: `ds.y` covers all 32 block elements, whereas each
    MMVQ lane needs a distinct 8-element slice selected by `iqs`. Receipt SHA-256
    `c8c055ff43f022ae4c61e3142b0278c15a807476db03aa29d16a50b6dbb25eea`; the one-file diagnostic
    remains uncommitted and has no performance or promotion authority.
  - [x] **Split the remaining +35 INT32/wave burden before a second Q4_K source candidate.** ✅
    2026-08-11 — exact gfx90a disassembly of the measured
    `mul_mat_vec_q<Q4_K,1,false,false>` specialization contains four extra
    `v_dot4c_i32_i8` sites for lane-local Q8 sums. At `k=5120`, Q4_K has 20 superblocks and each
    lane executes the vecdot five times, attributing **20/35 INT32 instructions/wave (57.1%)** to
    the required subgroup sums. The residual **15/35 (42.9%)** covers six-bit scale/min unpack plus
    Q4_K-specific packed-nibble address/control; it is not honestly pure unpack yet. Static receipt:
    `/mnt/raid0/llm/autokernel/probes/inf37-q4k-isa-attribution-20260811/receipt.json`, SHA-256
    `01458d64fcd9d2fab0bdb883a619f0904ab3aa3c28d23f3ef8a3fc881517860c`.
  - [x] **Test a correctness-preserving branchless six-bit scale/min decoder.** ✅ 2026-08-11 — the
    one-file experimental candidate leaves both lane-local Q8 subgroup sums untouched and replaces
    only the divergent `j < 2` scale/min extraction. The rebuilt gfx90a backend passed all five exact
    representative `m=17408,n=1,k=5120` Q4_K correctness repetitions. Static ISA size remained 1,452
    bytes while the specialization lost three `s_cbranch_execz` and two `s_branch` sites. A balanced
    two-control/two-candidate diagnostic then found **69,840 vs 78,080.5 ns median (-10.554%)**, despite
    the candidate executing **236.5 vs 216.5 VALU/wave (+9.238%)** and **87 vs 78 INT32/wave
    (+11.538%)**. This is directional evidence for reduced exec-mask/control-flow cost, not an
    instruction-count win. The source is uncommitted, so the result is explicitly diagnostic-only:
    `/mnt/raid0/llm/autokernel/probes/inf37-q4k-branchless-scales-20260811/diagnostic-paired-r3/receipt.json`,
    SHA-256 `de4241bd26b77f5dac7df746d165034b67e6f8105133daf0359142a97dd35d5d`.
  - [ ] **Commit only after explicit experimental-tree approval, then clean-replay the branchless
    decoder through the governed paired runner.** The clean candidate must reproduce correctness and
    timing before any promotion or model-level claim; the dirty diagnostic cannot satisfy this gate.
- *(Retarget 2026-10-28 (operator): Qwen3.5-122B deprecated. It no longer serves, so Item C is not a production-serving
  rung. The IQ2_XXS kernel work is format-level. Re-measure it on a current IQ-format target: the
  DS41 or Q38FN low-bit lanes, or the TRIPWIRE's GPU-resident IQ role. Do not use the 122B.)*
- [ ] **Item C — architect MoE-IQ2 at 10.3%**, our worst rung by 2× and a production-serving model. Attach the kill-criterion first (below) — this is a probe, not yet a funded kernel
- [ ] Kill-criterion probe for item C: on gfx906 an optimised community fork **and** vLLM independently converge on ~10% bandwidth for MoE batch-1 — the same rung as ours. Two stacks hitting one wall means this may be an **architectural floor**; establish cheaply whether it is before funding a kernel
  - **2026-08-11 tool-boundary result:** the exact main tensor type in the 122B UD-IQ2_M file is
    IQ2_XXS (94 tensors; alongside IQ3_XXS/Q5_K/Q6_K). Ten unprofiled seeded warm-up repetitions pass,
    but `rocprofv2` exits 139 during the IQ2_XXS active trace even after moving all repetitions into
    one backend process. Durable failure receipt:
    `/mnt/raid0/llm/autokernel/probes/c4-iq2xxs-op-singleproc-20260811T1220Z/receipt.json`,
    SHA-256 `fdf355ebc933f3cf20def077cdcc7b998c0072295c00c97b977ad32358c284e2`.
    This is not evidence of an architectural floor. Keep the kill-criterion open and switch the next
    probe to a non-`rocprofv2` device timer/counter path rather than retrying the same crash.
  - [x] **IQ2 tool-boundary follow-up:** capture the same seeded IQ2_XXS shape through a
    non-`rocprofv2` device-timer/counter path and retain the failed receipt as the negative control.
    ✅ 2026-08-12 — done by a different route than the row assumed, so read the caveats. The
    non-`rocprofv2` path is `rocprof` v1 device timestamps, which needs **no seed flags**, so OP-11
    was never on this critical path (OP-11 subsequently DECLINED, Option B). Governed run on the real
    122B UD-IQ2_M passed: `/mnt/raid0/llm/autokernel/probes/iq2xxs-rocprofv1-attribution-20260812T1302Z`,
    residency proven during (VRAM 57→58%, GPU 99–100%). Full analysis:
    [`artifacts/gpu-aux-baselines/a10_iq2_decode_attribution_20260812.md`](../../artifacts/gpu-aux-baselines/a10_iq2_decode_attribution_20260812.md).
    **Three caveats that matter more than the capture:** (1) the governed runner hardcodes `-n 0`, so
    that run is **prefill-only** — the decode GEMV numbers come from a **non-governed** companion run
    (`iq2xxs-decode-nongoverned-20260812T1306Z`); fix filed as RVP-C2-11 with a verified patch.
    (2) IQ2_XXS decode is **16.42%** of decode kernel time, median 85.60 µs across 6,063 dispatches.
    (3) The earlier "not occupancy-limited" reading was from the **synthetic** smoke's
    `<…,false,false>` variant at `Arch_VGPR=64`; production MoE decode runs `<…,true,false>` at
    `Arch_VGPR=80` → **6 waves/SIMD, 75% of max**. Scratch 0 in both, so no spill.
  - [x] **IQ2 VGPR-pressure lever — ISA read done, zero GPU time** ✅ 2026-08-12. Read statically from
    the shipped `libggml-hip.so.0.16.0` (clean frozen-v9 `0db32c06e`). Full table:
    [`artifacts/gpu-aux-baselines/a10_iq2_vgpr_lever_20260812.md`](../../artifacts/gpu-aux-baselines/a10_iq2_vgpr_lever_20260812.md).
    True counts are **63** (`<…,false,false>`, 8 waves) and **78** (`<…,true,false>`, 6 waves) — `rocprof`
    had reported 64/80, which is the allocation-granularity rounding, not the true count. **The mm_ids
    wrapper is NOT the cost:** Q8_0 runs the identical wrapper in **25** VGPRs, so the 78 is IQ2_XXS's own
    dequant state. **But "codebook ⇒ expensive" is also wrong** — IQ4_NL is 38 and IQ1_S 42, while block
    quant Q3_K is the table's worst at 88; pressure tracks per-block state-machine complexity, not the
    lookup. **IQ4_XS sits at exactly 64 on this same wrapper**, so the 8-wave target is proven reachable
    and IQ2_XXS is 14 registers over. Constraint: spill is 0 everywhere, so there is no slack — any
    reduction attempt must report `vgpr_spill_count` beside occupancy or it is not evidence.
  - [x] **Disassembly diff `<IQ2_XXS,1,true,false>` vs `<IQ4_XS,1,true,false>`** ✅ 2026-08-12, zero GPU.
    1002 instructions vs 565; `v_*` 758 vs 334 while scalar (210/203) and LDS (16/16) are near-identical
    and IQ2_XXS issues **fewer** global loads (3 vs 5) — **the codebook gather is not the cost, for the
    third independent time**. The excess is sign unpacking: `unpack_ksigns`/`__vcmpne4`/`__vsub4` lowers
    to ~272 sub-word ops (`v_or_b32_sdwa` 96, `v_lshlrev_b16` 96, `v_sub_i16` 64, `v_bfe_i32` 46), while
    IQ4_XS does its byte manipulation with **48 `v_perm_b32`** that IQ2_XXS never uses.
  - [ ] **Re-express the IQ2_XXS sign expansion using `v_perm_b32`** (byte permute) instead of 16-bit
    shift/or/sub chains, in `vecdotq.cuh`. IQ4_XS is a working in-tree example of the idiom on the
    identical wrapper landing at exactly 64 VGPR = 8 waves. **EXPERIMENTAL BRANCH ONLY** — production
    `production-consolidated-v9` is frozen. Report `vgpr_spill_count` beside occupancy, and note that
    decode is bandwidth-bound so this is necessary-not-sufficient for throughput.
    **2026-09-15:** a compiler-side route reaches the same threshold without the rewrite
    (`#pragma clang loop unroll(disable)` → 44 VGPR static; autokernel-research-loop AK-QL-2b). Attempt
    v_perm_b32 only if AK-QL-7 shows the retained 4-trip loop costs more than the regained waves.
  - [ ] **Re-run the decode attribution under governance** once RVP-C2-11's `--gen-tokens` patch
    lands, so the 16.42% decode figure carries a durable receipt instead of a non-governed probe.
    **Prerequisite correction 2026-11-02:** the generation flag landed under RVP-C4-4, not
    RVP-C2-11: research `c38bf49a` / main `1527ea49`. RVP-C4-4a also captured a governed
    122B decode trace (receipt SHA-256 `c7f3f5a243310021e022715b403fe0668b47145440bda00ee43ac6d84e14bed3`),
    but the aggregate MMV figure is not this task's IQ2_XXS-specialized 16.42% attribution.
    The 122B is now retired and must not be rerun; select an eligible current IQ target under
    the 2026-10-28 retarget. Separately, the Omniperf seeded-op fallback requires a binary
    containing `--suite-seed` and `--repeat-suite`: frozen v10 source contains both, introduced
    by `f744cc220e722d1bda93783959471d44f8e118b0` after v9, but the old in-tree HIP test binary
    lacks them. OP-11 declined the distinct `AK_SENS_V1` experimental producer, not these generic
    CLI flags. Build an identity-bound test binary from a fresh experimental v10-based tree, then
    check the fallback's own preflight and the applicable measurement authorization before a run.
    Do not assert this task complete from aggregate data.
    The Omniperf 2.0.1 / `rocprof` v1 fallback is now durable in research, but its first governed run
    correctly failed compatibility before profiling: clean frozen-v9 `test-backend-ops` at
    `0db32c06` does not implement `--suite-seed` or `--repeat-suite`. The failed receipt retains the
    exact command, clean source/binary/profiler identities, one device sample, and claim
    acquisition/release:
    `/mnt/raid0/llm/autokernel/probes/inf37-iq2xxs-omniperf-v1-20260811/receipt.json`, SHA-256
    `2054a31b5f9104bcd3437b250833de6086a7dded8533e3cc9182bc9a79222510`. A prior manual smoke at
    `/mnt/raid0/llm/autokernel/probes/omniperf-iq2xxs-v1-smoke-20260811T1238Z` produced 260 dispatch
    rows and proves rocprof-v1 reachability, but it has no governed receipt and is non-evidence.
    Keep this parent open until OP-11 permits a durable seeded producer and the runner records a
    passing matched capture.
  - [x] **Build a fail-closed Omniperf-v1 fallback runner for the IQ2 profiler boundary.** ✅ 2026-08-11 —
    it binds clean exact source/tool/Python identities, requires seeded repeated correctness before
    SQ/TCC collection, holds the MI210 claim, samples device state, and writes failure receipts.
- [x] Investigate the permanently-dead `z_HAVE_FANCY_SIMD` AVX512-VPOPCNTDQ IQ2 sign path on an EXPERIMENTAL branch only (production kernel is frozen; this is a CPU-side finding filed here for mechanism adjacency) ✅ 2026-08-11
  - Globally reviving the historical branch was correctly rejected: a governed ten-block A/B at the
    exact IQ2_XXS `m=4096,k=14336` shapes improved `n=1` by **+5.753%** median but regressed `n=512`
    by **-9.511%** median. The kill switch therefore encoded a real prompt-processing tradeoff, not a
    typo. Global-candidate receipt:
    `/mnt/raid0/llm/autokernel/probes/inf37-iq2-fancy-simd-ab-v9-20260811-r4/receipt.json`, SHA-256
    `242cb61b122b39324316d020d1a2a4bc4be4c17ec3008a66f5ecaf7a2a7c2a91`.
  - A one-row-only template dispatch preserves the arithmetic VPOPCNT sign decoder exclusively for
    `kernels[0]` while every multi-row kernel keeps the table decoder. Native correctness passed
    **44/44** supported IQ2_XXS matmul cases plus the full quantization-function suite; the AVX2-only
    fallback compiled. In the fresh governed replay, `n=1` improved **+5.733%** median across all ten
    blocks (range **+5.325% to +6.027%**) while `n=512` returned to parity at **+0.020%** median
    (range **-0.117% to +0.219%**). Receipt:
    `/mnt/raid0/llm/autokernel/probes/inf37-iq2-fancy-simd-ab-v9-20260811-r5/receipt.json`, SHA-256
    `12dc4d95a8b208f97ce8c82ab7917f4e6aa28872a90c5fc85f15b72f07fa73ea`; candidate diff SHA-256
    `c24892485af0bddedc641b4ae764302a3c7dc070ed2d765c8e820c01f680b470` against frozen v9
    `0db32c06e3e550065b78311a6031ef3dd2c4f27c`.
- [ ] With OP-12 approval, commit the one-file IQ2_XXS one-row dispatch and run matched model-level TG/PP confirmation before any promotion claim.
- [x] **Settle the gfx90a low-precision datapath at ISA level.** ✅ 2026-08-15 — gfx90a FP16 and
  INT8 MFMA have identical shape sets and peak rate; there is no FP8 or INT4 matrix path. Batch-one
  decode sits 31–113× below the measured ridge, so native-MFMA decode hypotheses have zero value on
  this die. Composable Kernel FP8 on gfx90a is fp32 emulation, not a datapath benchmark. Durable
  citations and assembly/toolchain checks are compiled in `wiki/hardware-optimization.md`.
- [ ] **TRIPWIRE — re-open low-quant VALU/occupancy work when an IQ-format role becomes GPU-resident.**
  Current production has no IQ1/IQ2/IQ3/IQ4 serving role on ROCm0, so the 6-vs-8-wave loss is a
  latent exposure rather than current payoff. Reprice immediately on a registry transition making an
  IQ-format GGUF resident; do not close the mechanism as “not a problem.”
  - [x] **INF37-IQ-1 — Bind the latent-residency blocker into planner memory.** ✅ 2026-08-16 —
    research `5ae54e0ae4a80ab02450f703617b6a769599caf2` assigns zero current live-stack payoff,
    preserves the IQ mechanism as ineligible memory, and requires reprice on an IQ residency change.
    Automatic machine-trigger enforcement is owned by AutoKernel AK-ADM-1.
  - [ ] **INF37-IQ-2 — On IQ residency, reprice with the levers now on file.** Activate on the same
    trigger. (1) AK-QL-7 unroll(disable) falsifier. (2) If the resident is an IQ2/IQ3 **MoE**: confirm the
    CDNA MUL_MAT_ID cutoff (IQ2_XXS `ne2<=5`, mmvq.cu:185-194 — unmeasured on gfx90a, intake-1410) at the
    recipe's verify widths, since `ne2>=6` also disables HIP graphs. (3) Optional: backport llama.cpp
    #27621 (multi-token MoE GLU/top-k fusion) — only if the GGUF has separate `ffn_gate_exps`/`ffn_up_exps`
    and after locating the fix for AMD-HIP garbage-output issue #28113; correctness (fusion on vs
    `GGML_CUDA_DISABLE_FUSION=1`) before speed (intake-1420).
    - **Lever (4), factual note 2026-10-20 (from the INF37-IQ-4 note; no benefit claimed):** Magnitude's planar IQ2_XS/IQ2_XXS/IQ3_XXS layout differs from ggml's block layout (scale and factor placement, packet byte widths): layout-only, needs a repack. Sign-decode ALU order, per-packet factor reload and fp32 versus dp4a accumulation differ in kernel arithmetic: kernel-only. Details and locators in the INF37-IQ-4 note.
  - [x] **INF37-IQ-3 — Correct the imported AGPR compiler-tax note.** ✅ 2026-09-15 — the MI200 CDNA2
    ISA (intake-1409) lets MFMA A/B come from Acc VGPRs, so "HIPCC will not feed AGPRs to matrix-core
    instructions" (`completed/mi210-mfma-compute-bound-paths.md:94-96`) is at most a compiler
    observation, not an ISA limit. Acc VGPRs are MFMA-only (ordinary v_* needs `V_ACCVGPR_READ`), so they
    are no MMVQ decode lever. The 64-VGPR→8-wave rule is in neither the ISA nor the MI250 docs
    (intake-1418); treat it as empirical.
- [x] **INF37-IQ-4 — Record Magnitude's IQ2/IQ3 planar-decode GEMV layout as a lever on file for the IQ-residency reprice (documentation-only, zero compute).** ✅ 2026-10-20 — factual note below: layout-only and kernel-only differences classed; lever (4) on file under INF37-IQ-2; the 16-byte-load claim is corrected in the note. Read `inference/seismic/lang/native-library/vulkan/packets.glsl` (IQ2_XS, IQ2_XXS and IQ3_XXS kinds; the rows16 planar layout with code, scale and super-factor planes and one 16-byte packet load per 32 elements; factored scale*dot+bias*sum(x); the grid sign-parity trick) from `/mnt/raid0/llm/tmp/dive-1979/repo` @ `940e51b` and compare it with ggml-cuda's IQ2/IQ3 `mul_mat_vec_q` decode on gfx90a. Add to the INF37-IQ-2 lever list which differences exist (memory layout, loads per element, sign decode) and which are layout-only (would need a repack) versus kernel-only. No MI210 run and no IQ role is made resident; the entry is read at the tripwire's reprice and claims no benefit.
  - **Factual note 2026-10-20 (INF37-IQ-4; read-only source comparison, no build, bench or GPU; checkbox left open for main review).** Sources: Magnitude `inference/seismic/lang/native-library/vulkan/packets.glsl` @ `940e51b`; production llama.cpp tree HEAD `ffc1bac82` (read with cat/sed only; tracked files clean; last changes `ggml/src/ggml-cuda/vecdotq.cuh` @ `aba5a8155`, `ggml/src/ggml-cuda/mmvq.cu` @ `bff30cebe`). Scope: IQ2_XS, IQ2_XXS, IQ3_XXS grid kinds.
  - Class **layout-only (needs a repack)**: (1) Planar storage. Magnitude keeps per 256-value group an entries plane, a scale plane and an f32 factor plane (`packets.glsl:90-107`, `PACKETS_ROWS16_GRID`; loads `:302-316`). ggml stores array-of-struct blocks: `block_iq2_xxs {f16 d; u16 qs[32]}` (`ggml/src/ggml-common.h:397-399`), `block_iq2_xs` with `scales[8]` (`:403-407`), `block_iq3_xxs {f16 d; u8 qs[96]}` (`:423-425`). (2) Bytes per 32-value packet. Magnitude loads 8 B for IQ2_XS and IQ2_XXS (`packets.glsl:303,306`, `packet.low.xy`) and 12 B for IQ3_XXS (`:310`); ggml reads two u32 per 8 values (`vecdotq.cuh:1038-1040`, `:1073-1075`, `:1162-1164`). The checkbox text's "one 16-byte packet load per 32 elements" does not hold for these grid kinds: the 16-byte load is the q4k/q8 code plane (`packets.glsl:249`). (3) Scale placement. Magnitude's odd scale `2s+1` is a nibble of the scale plane (`packets.glsl:304,307,311,314-316`); ggml's is a nibble in the qs word (`vecdotq.cuh:1061`, IQ2_XXS), the `scales[]` byte (`:1077-1078`, IQ2_XS) and `aux32 >> 28` (`:1188`, IQ3_XXS). Same code, different placement. (4) Super-factor placement. Magnitude keeps one f32 per 256 group (`packets.glsl:313`); ggml one f16 `d` per block (`vecdotq.cuh:1063`, `:1104`, `:1190`).
  - Class **kernel-only**: (5) Factor reload. Magnitude re-reads the group factor for every packet (`packets.glsl:313`); ggml reads `d` once per block (`vecdotq.cuh:1063`). (6) Sign decode. Both use seven sign bits plus an even-parity eighth bit: Magnitude `packets.glsl:217-224` (`bitCount` parity, XOR of float sign bits) versus ggml `vecdotq.cuh:97-104` (`__popc` parity) with byte negation via `__vcmpne4`/`__vsub4` (`:1050-1053`). The parity trick is the same; the ALU sequence is not. (7) Accumulation. Magnitude's `packets_grid_codes` emits fp32 vec4 codes (`packets.glsl:217-224`); ggml accumulates int8 with `ggml_cuda_dp4a` against q8_1 activations (`vecdotq.cuh:1048-1056`, `:1094-1096`). The consumer of Magnitude's fp32 codes lies outside `packets.glsl` and was not read, so the Vulkan accumulation type is not established by this note.
  - No difference: grid tables and index widths (`packets.glsl:198-211` vs `vecdotq.cuh:1047`, `:1084`, `:1171`); no bias term for grid kinds (`packets.glsl:70-72`, `packets_biased` is false; ggml computes `d * sumi`, `vecdotq.cuh:1063`).
  - Dispatch context (not a decode difference): on CDNA2 the IQ types fall to the default batch cap (`mmvq.cu:757-758`); the explicit IQ caps at `mmvq.cu:710-735` sit in the CDNA1 branch. The INF37-IQ-2 item (2) cutoff at `mmvq.cu:185-194` was not re-verified here.
  - This note claims no benefit. No MI210 run, no IQ role made resident. Lever entry (4) added under INF37-IQ-2.

#### Proposed non-IQ follow-through — 2026-10-04 earlier-intake retrospective

- [ ] **INF37-MOE-Q8-FUSION — Qualify and implement a correctness-gated multi-token MoE GLU fusion slice for the existing Qwen3.6-35B Q8 MTP recipe.** PROPOSED, not build/run/deployment approval. This is independent of INF37-IQ-2's IQ-residency trigger. Main's read-only qualification found the model has separate Q8 gate/up expert tensors (41 of each), the canonical recipe uses MTP width four, and frozen v10's source still rejects multi-token MUL_MAT_ID fusion; this does not prove the running binary's route or benefit. Start an isolated experimental candidate from current production, never modify/build the frozen tree. Review upstream #27621 and AMD garbage-output report #28113; locate the exact fixing patch or implement and fixture-test a minimal gfx90a correction—closed issue status is not fix provenance. Keep scope to GLU: preserve v10's CPU-only top-k guard and do not bundle the unrelated top-k optimization. Bind source, patch, model/tensor metadata, rendered canonical recipe, compiler, actual binary/library digests and runtime fusion eligibility; inspect actual launch/verification widths rather than infer them from draft-n-max. Compare candidate fusion-on versus candidate fusion-off and fresh production on identical held-out inputs: operator differential tests including expert selection, verify widths and nonfinite/repeated-garbage cases, logits/decoded-output correctness against the measured local floor, then a bounded paired MTP end-to-end latency/throughput and acceptance screen. Charge failures and retain all outputs. Stop on any correctness failure, ineligible runtime path or no improvement beyond local paired uncertainty; report negative/inconclusive rather than widening into a kernel campaign. Render the existing `qwen3.6-35b-a3b-q8-gpu-mtp.json` recipe, do not hand-retype it. Prospective write-side capture under VB-RI-OPS-WIRE precedes any measured run, with existing ClaimTuple grading; normal campaign/resource and separate production-promotion gates remain intact. [Qualification, counter-coverage and limits](../../docs/reviews/research-intake-earlier-applications-20261004.md); record discussion: intake-1420#record.
  - **2026-11-02 provenance review, no build or run:** [issue #28113](https://github.com/ggml-org/llama.cpp/issues/28113) initially attributed repeated punctuation on gfx1151/ROCm 7.14 to the multi-token fusion guard, but its reporter subsequently reported that isolated #27621 worked, could no longer reproduce the issue after a ROCm update, and suspected local tuning interactions. The issue identifies no confirmed upstream fix or gfx90a result; referenced fork commits are not proof of either. The exact correction/fixture gate remains open. Upstream `41ef91f7c8046087cdfbb276b79bff311ecf1c6d` changes GLU, MMVQ, top-k and tests, so a GLU-only slice requires selective review, not wholesale application. VB-RI-OPS-WIRE remains open, so no decision-bearing run is ready to publish.
  - **Capture preparation:** `scripts/vidya/adapters/speech_ggml_optest.py` is a possible existing measurement projection scaffold, not an INF37 producer: its current profile lacks actual verify widths, three-arm MTP pairing and correctness-floor/raw-output bindings. The eventual experiment finalizer must write those fields and failed/ineligible attempts before a strict projection through the existing grader; a reader-only extension cannot satisfy the write-side gate. Select the native runner and its owner before implementing the finalizer; no runner or capture is claimed ready here.
  - **GLU slice source map, 2026-11-02 (read-only):** v10 already matches MoE GLU graphs but rejects multi-token quantized fusion in `ggml_cuda_should_fuse_mul_mat_vec_q`; its `mmvq.cu` multi-token `has_ids` branch calls a dedicated MoE kernel without fusion arguments. The upstream GLU slice requires a bounded shape gate plus passing fusion through that launcher and implementing gate accumulation/reduction and the GLU epilogue in that kernel. Preserve v10's top-k guard and exclude the upstream top-k files and logits-alias changes. Frozen v10's matcher admits SWIGLU/GEGLU/SWIGLU_OAI, not upstream's clamp variant; do not assume clamp support. This is a source map, not a tested patch or proof of gfx90a correctness.

##### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **INF37-LB1 — Static ISA audit of HIP mul_mat_vec_q at ncols 1 vs 2..8 for Q8_0, Q4_K and IQ4_XS on gfx90a: count weight VMEM loads and dequant VALU per block per column with gfx90a_isa_audit.py; if loads repeat per column, seed a weight-hoisted multi-row MMVQ (Q4_K MMVQ at 8 rows measured 9.4% of roof vs 46.5% at 1 row in the lb1 profile) (intake-2386, intake-2393).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / locals-c.)* AUDITED, no build, no GPU: `scripts/kernel_rnd/mmvq_hoist_audit.py` over the v10 kernel store `libggml-hip.so.0.16.0` (sha256 `f26a166b…`, built 2026-09-21 from `ffc1bac82`), research `0eea263b4` on the research branch `f8/locals-c-research-20261022` (worktree `/mnt/raid0/llm/worktrees/f8-locals-c-research`, unmerged, unpushed); table and json in `artifacts/mmvq_hoist_audit_20261022/`. Weight VMEM loads per ROW per block (flat in ncols = hoisted): **Q8_0 3 at every ncols 1..8** (per block per column 3.0 → 0.375), **IQ4_XS 3 at every ncols 1..8**, so the weight-hoist hypothesis is falsified for both. **Q4_K 6 at ncols 1 → 27 at ncols 8**: the 3 dword `qs` loads per row are hoisted but the 3 ushort d/dmin/scale loads per row are re-issued per column (9, 12, -, 18, 21, 24, 27 at ncols 2, 3, 5..8) and nibble-unpack VALU per row grows with ncols (21 → ~106); ncols 4 is hoisted by the existing `load_q4_K_b4_weight` path. Dequant VALU per block per column: Q8_0 18 → 8.1, Q4_K 63 → 44.2, IQ4_XS 89 → 24.3. Verdict: no seed for Q8_0/IQ4_XS; a Q4_K-only seed (generalise the b4 path to ncols 2, 3, 5..8) is filed in the 27B inbox as 50.4 and is moot for the Q8_0 27B campaign (relevant to the K-quant follow-on). Q4_K ncols 4 loop duplicates load arms (Y loads flagged `load_overcount`), so its counts are an upper bound.
