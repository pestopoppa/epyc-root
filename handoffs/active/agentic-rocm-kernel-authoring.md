# Agentic ROCm Kernel Authoring — MI210 Verify+Profile Harness

**Status**: active investigation — hardware present; P-GPU-1 ratified. **Corrected 2026-08-10 (operator): P-GPU-1 governs the CLASS OF CLAIM a result may carry, not permission to run — the human boundary is freeze / cutover / promotion.** Benching or profiling a *live server* is still owned by whoever owns that inference. Every "operator-approved GPU runs" phrase below predates this correction; read it as claim-class, not permission.
**Next action (2026-08-12)**: run the governed, availability-conditioned 6/6 AgentKernelArena panel
at matched 2h/8h/32h checkpoints; the full 8/8 panel continues to refuse on the unavailable exact
EvoEngineer and ARGUS source releases.
**Created**: 2026-06-03 (via /research-intake deep-dive of the LLM-kernel-generation cluster) · **Updated**: 2026-08-12 (current-source six-arm readiness re-audit)
**Categories**: hardware_optimization, agent_architecture, autonomous_research, tool_implementation, training_distillation
**Hardware gate — SATISFIED 2026-07-02**: AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB) is racked and the llama.cpp HIP build is verified on gfx90a (`progress/2026-07/2026-07-02-mi210.md`; memory `project_mi210_gpu_inference`). This program is now **ACTIVE**, priority **MEDIUM** — it is an *optimization*, **not a production blocker**: llama.cpp-HIP already serves ~910 tok/s @32-way as-is (2026-07-02 obs). First step = reproduce **GEAK-eval** (intake-674, arXiv 2507.23194) on gfx90a — compile+correctness+timing round-trip — as the sanity gate. **Scoping caveat (adversarially verified 2026-07-03; AMENDED 2026-08-03, see §"GEAK scoping — amended")**: GEAK **v4** retains first-class gfx90a knowledge, though all published *evaluation* is gfx942; **AgentKernelArena (679) / robust-kbench (668) are gfx942/CDNA3-listed** and must be treated as ports, not drop-in reproductions. All GPU runs remain operator-approved measurements per MEASUREMENT.md (write P-GPU-1 first). [was: "expected ~July 2026; nothing executes until the card racks" — stale after 2026-07-02 install] [was: "close the measured quantized-MMQ-dequant roofline gap: ~33% Q4_K / ~47% Q8 at batch-1" — **re-targeted 2026-08-03**, that is half the prize; see §"Program re-target"]
**Priority**: MEDIUM (activates on MI210; prep proceeds now)
**Workstream**: Inference Acceleration / GPU · **Parent index**: [`inference-research-index.md`](inference-research-index.md)
**Full reasoning + evidence**: [`research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md`](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md) ← the durable narrative; this handoff is the operational summary.
**Related**:
- [`rocm-verify-profile-backend.md`](rocm-verify-profile-backend.md) — **child**: the ROCm verify/profile/benchmark backend this loop drives
- [`gpu-drafter-mi200-investigation.md`](gpu-drafter-mi200-investigation.md) — MI210-gated; consumes the kernels this loop produces
- [`gpu-acceleration-path.md`](gpu-acceleration-path.md) — the ROCm kernel-library hand-port path this automates
- [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) / [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) — the hand-HIP endgame + the CPU ukernel loop this rhymes with

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
[`mi210-q8-dequant-gemv-roofline.md`](mi210-q8-dequant-gemv-roofline.md).

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
  (below).
- **`rocm-flash-attn` as an enabling path**, re-assessed: an adaptation layer with no kernel code of its
  own, but genuine tested code with honest defect annotations. Judged on whether it improves performance,
  not on whether it contains kernels.
- **Two operational levers from AMD's own ROCm llama.cpp blog:** hipBLASLt grouped-GEMM plus tuning
  (**+29%**) and ~10× fewer `hipMemcpyAsync` calls.
- **llama.cpp issue #19984 — an LLVM loop-unroll regression in ROCm 7+ costing 3.7–5× on prefill**,
  workaround `-mllvm --amdgpu-unroll-threshold-local=600`. We are on ROCm 6.2 so this does not bite today;
  it belongs on the build-flag checklist **before any ROCm upgrade**.

**Profiler tooling — RESOLVED 2026-08-03 (was a blocker).** `rocprofv2`, `rocprof` and `rocm-bandwidth-test` are now available, version-matched to ROCm 6.2.0-66, side-loaded by extraction rather than installed so nothing in the shared `/opt/rocm` bind mount changed: `source /mnt/raid0/llm/tools/rocm-profilers-6.2/env.sh`. **The gfx90a counter taxonomy is proven** — 465 counters across 12 blocks, enumerated on our own card, including every counter this program already cites. Details, per-block collection limits, and the two path quirks: [`rocm-verify-profile-backend.md`](rocm-verify-profile-backend.md). The LDS bank/phase solver and the C4 analyzer are unblocked on tooling. `omniperf` 2.0.1 now runs through a sealed Python environment; its governed IQ2 fallback is implemented but waits on the OP-11 seeded producer identity.

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

**Source**: KernelBench (**intake-664**, arXiv:2502.10517)

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
  - [ ] Run the governed available-source 6/6 campaign at the fixed 2h/8h/32h checkpoints when
    inference is authorized; interpret it only as an availability-conditioned diagnostic.
  - [ ] Obtain exact licensed source releases for EvoEngineer and ARGUS, then port their real
    controller policies through the same governed adapter contract; namesake substitutes are not
    admissible.
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
- [x] Resolve the profiler-tooling blocker on the host (rocprofv2/rocprof/omniperf/rocm-bandwidth-test) — C4 and the LDS bank/phase solver are both gated on it ✅ 2026-08-11 — version-matched ROCm 6.2 tools are side-loaded; `rocprofv2` is the working op-level path, with its whole-model/IQ2 crash boundary now measured and receipted. Omniperf is runnable and has a fail-closed governed fallback; seeded evidence waits on OP-11.
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
  - **Why this is not already covered.** [`reasoning-effort-levels.md`](reasoning-effort-levels.md) is
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
    [`architect-model-selection-bench.md`](architect-model-selection-bench.md) already selects a model
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
