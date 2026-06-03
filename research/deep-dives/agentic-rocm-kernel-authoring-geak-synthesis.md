# Agentic ROCm Kernel Authoring on MI210 — GEAK-Family Synthesis (deep dive)

**Created:** 2026-06-03 · **Status:** durable synthesis (the verbose reasoning home for the two operational handoffs)
**Operational handoffs:** [`../../handoffs/active/agentic-rocm-kernel-authoring.md`](../../handoffs/active/agentic-rocm-kernel-authoring.md) (umbrella) · [`../../handoffs/active/rocm-verify-profile-backend.md`](../../handoffs/active/rocm-verify-profile-backend.md) (backend)
**Intake evidence:** intake-660 … intake-679 (see `research/intake_index.yaml` for per-paper key_claims, reported_results, `amd_rocm_transferability`, `mi210_gfx90a_applicability`, `contradicting_evidence`).

> This note is the *durable* reasoning record. The two handoffs are kept lean/operational and link here. When fresh evidence lands (a GEAK-v2 arXiv, gfx90a numbers, a new AMD-native tool), update the **Freshness Appendix** (§7) and the handoffs' decision snapshots; let this note grow.

---

## 1. Executive summary
We are a CPU-inference shop (EPYC 9655, custom llama.cpp fork) receiving our first datacenter GPU — an **AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB), ~July 2026** — and want to **author custom HIP/Triton kernels** for the EPYC stack using an **agentic, train-free, verify+profile loop** rather than hand-porting. Over 2026-06-03 we ingested the entire LLM-GPU-kernel-generation literature (20 entries, intake-660–679) and pivoted it onto this AMD path. The decisive discovery: **AMD has already built and open-sourced most of what we need — GEAK (the agent), Apex (the deploy harness), AgentKernelArena (the agent-comparison arena) — and GEAK is demonstrated on gfx90a, the MI210's exact ISA family.** So the program collapses from "build a ROCm kernel-authoring stack from scratch" to **"adopt AMD-native MIT/Apache-2.0 code, reproduce it on our gfx90a, and add the two pieces AMD left thin: anti-reward-hacking hardening (C6) and a gfx90a profiler-metric layer (C4)."** The single hard caveat threaded through everything: **every AMD number is vendor-reported and most are gfx942/CDNA3-only — they predict compile compatibility on our gfx90a, not performance equivalence.** GEAK-v1 is the only gfx90a-proven reference; reproducing it on the MI210 is the gating first step.

## 2. Provenance timeline (how the program came to be)
- **Seed.** A routine `/research-intake` of **CUDA Agent** (ByteDance, arXiv 2602.24286 → intake-660) — agentic-RL CUDA kernel authoring, NVIDIA-only.
- **The steer that created the program.** Mid-intake the operator interjected: *we are building custom kernels for the AMD stack, and an MI210 lands next month.* That reframed the cluster from "NVIDIA methodology" to a **near-term, hardware-gated engineering program**, scored through the MI210/gfx90a lens thereafter.
- **Core cluster (661–666).** CUDA-L1, CudaForge, Kevin, KernelBench, ConCuR, EvoEngineer — the kernel-gen literature; all NVIDIA, value = methodology + the design of a from-scratch ROCm backend.
- **De-risk batch (667–669).** MultiKernelBench, robust-kbench, KernelFoundry — the planned backend (fork MultiKernelBench + lift robust-kbench) + the QD hardware-awareness layer.
- **Next-tier (670–673).** KernelCraft (NOT our path — AIE-ML NPU/Peano), FastKernels (production-vs-sandbox critique), Xe-Forge (linear-CoVeR archetype; **surfaced the GEAK pointer**), K-Search (world-model tree, MoE-strong).
- **Keystone (674–676).** **GEAK** (AMD's own Triton agent, gfx90a-proven, MIT) + **Apex** (AMD's deploy harness, MIT, gfx90a-listed) + TritonForge (AMD-secondary, gfx942-only). This **reversed** the backend plan.
- **GEAK follow-up (677–678).** GEAK-v2 (OptimAgentv2 + OpenEvolve) and GEAK-HIP — blog/repo-stage, **gfx942-only (a gfx90a coverage regression)**, patterns not components.
- **Audit follow-up (679).** **AgentKernelArena** (AMD-AGI, Apache-2.0, arXiv 2605.16819) — the agent-comparison **arena** that is essentially the controller-A/B harness we planned to build; surfaced by the operator's post-review freshness sweep.

Arc: *one NVIDIA paper → an operator steer → an exhaustive sweep → the realization the vendor had already solved most of the backend on our exact silicon, and even shipped the A/B harness.*

## 3. Hard constraints (these drive every decision)
- **One MI210 (CDNA2/gfx90a, 64 GB HBM2e, single-GCD).** Binding constraint behind "train-free" and every "does it run on gfx90a?" question.
- **No training cluster.** No multi-GPU RL or large on-device SFT. (Offline LoRA distillation on a separate box is a *possible later* branch.)
- **`opensource_only` governs DEPLOYED services, not build-time tooling.** The authored kernel is the deployed artifact and is open; the LLM that authors it is a build tool (like Claude Code writing this repo). So Claude/Codex are fine as the agent backend — see §5.4.
- **Reusable assets:** strong in-house coder/architect roles; an **autopilot planner already running a Claude+Codex actor-critic** (reusable infra).
- **Endgame artifact:** raw **hand-written HIP/C++** kernels (attention, MoE dispatch, dequant — the `gpu-drafter-mi200-investigation.md` ops). Triton is the on-ramp; HIP the destination.

## 4. The CDNA-generation / gfx90a analysis (the single most load-bearing technical fact)
| AMD part | Arch | ISA (gfx) | Relation to our MI210 |
|----------|------|-----------|------------------------|
| **MI210** (ours) | CDNA2 | **gfx90a** | — (single-GCD, 64 GB) |
| **MI250 / MI250X** | CDNA2 | **gfx90a** | **SAME ISA family**; MI250X dual-GCD (MI210 ≈ one GCD) |
| MI300X / MI325X / MI308X | CDNA3 | gfx942 | newer; adds MFMA/FP8 paths gfx90a lacks |
| MI355X | CDNA4 | gfx950 | newer still |

**Softened claim (per audit finding #3).** Same `gfx90a` target **strongly predicts compile compatibility** — identical wavefront=64, MFMA availability, LDS semantics — so GEAK-v1's MI250X kernels and its eval/oracle/timing harness should **compile and run** on the MI210 with no porting. It does **not predict performance equivalence**: the MI210 is single-GCD with roughly half MI250X's aggregate bandwidth, and ROCm version, autotune search space, and benchmark-harness details all still require reproduction. So "MI250X = MI210 ISA" means *"expect it to build and run; re-measure everything before trusting a number."* Work demonstrated *only on gfx942* (GEAK-v2, GEAK-HIP, AgentKernelArena) carries even less: gfx942 kernels may use CDNA3-only instructions/tile-shapes absent or suboptimal on CDNA2. **This table is why GEAK-v1 (674, has an MI250X line) is the keystone while 677/678/679 are a coverage regression despite being newer.**

## 5. Current decisions
### 5.1 Train-free, not RL-trained
The strongest headline results are RL-trained (CUDA Agent 660, CUDA-L1 661, Kevin 663), but training any needs a GPU cluster — and TritonForge (676) shows AMD RL *crashes within 2 steps on MI300X*. We have one MI210. **RL training is out.** Counter-evidence that this is fine: the train-free loops (CudaForge 662, EvoEngineer 666, K-Search 673, GEAK 674) are competitive by spending *inference-time* compute (sequential refinement + parallel best-of-K + evolutionary/QD search); GEAK's ablations take correctness <15% → 54–63% with no training. **We still harvest from the RL papers** (without training): reward *design* (CUDA-L1 discrete/robust reward; Kevin's `0.3·correct + speedup`, γ=0.4 cross-turn credit), the **anti-reward-hacking gates**, and the multi-turn finding that sequential refinement beats parallel sampling under a fixed budget.

### 5.2 Backend substrate — the reversal
**Original plan:** build a ROCm backend from scratch (fork MultiKernelBench 667 + lift robust-kbench 668). **Reversal:** **GEAK-eval** (674, MIT) ships two AMD-validated benchmarks (TritonBench-revised + a real ROCm Triton benchmark) with a ROCm build + torch-ROCm oracle + AMD timing that already run on gfx90a (MI250X); **Apex** (675, MIT) ships the E2E harness (profile→optimize→hot-patch→re-bench) + the **Magpie scorer** + AST anti-tampering + 5 MCP servers, gfx90a-listed; **AgentKernelArena** (679, Apache-2.0) adds a third AMD-native substrate plus three task suites and the unseen-shape generalization protocol. So **C1/C2/C3/C5 are largely adopt**, MultiKernelBench is demoted to "secondary, multi-vendor abstraction only," and the two pieces we own are **C4 + C6**.

### 5.3 Controller — candidates + the AgentKernelArena pivot
We keep **multiple controller candidates** to A/B (no head-to-head exists on our hardware; each occupies a distinct, defensible point): **EvoEngineer (666)** flat-population evolutionary (lean lead) · **KernelFoundry (669)** MAP-Elites QD + profiler-gradient + per-arch template tuning (adopt-both as the hardware-awareness layer) · **Xe-Forge (672)** linear multi-stage CoVeR (cheaper/interpretable alternative archetype; same lab as 669, different team, does NOT supersede it) · **K-Search (673)** world-model tree, bug-tolerant, beats OpenEvolve 2.1×/14.3× MoE · **GEAK (674)** AMD-native 4-module best-of-K, gfx90a-proven (the default *first* controller to stand up, simply because it already runs on our ISA). **Consistency guard:** GEAK-v2's OpenEvolve (677) is an OpenEvolve derivative and K-Search beats OpenEvolve, so we did **not** auto-promote the newer AMD QD over K-Search — we harvest OpenEvolve's 9-dim grid + cascade filtering + hybrid selection as *upgrades to the 669 layer*. **The AgentKernelArena pivot (679):** the agent-comparison harness we planned to *build* largely **exists** (Apache-2.0, Claude Code/Codex/Cursor/GEAK adapters, registry `@register_agent` pattern, ~4-step custom adapter). **Decision: register our controllers (Claude+Codex actor-critic, EvoEngineer, K-Search, Xe-Forge) as AgentKernelArena adapters and A/B them on gfx90a, rather than hand-rolling a harness.** Caveat: it compares whole *agents* at task level, not the fine-grained inner generate→profile→refine loop, so it complements (not replaces) each controller's internal loop; and its headline run *excluded* GEAK/AutoTriton, so a GEAK-vs-general A/B on gfx90a is itself net-new data for us.

### 5.4 Agent backend — pluggable; Claude+Codex actor-critic favored
`opensource_only` governs deployed services, not build-time tooling (§3). Both harnesses have pluggable backends (GEAK→LiteLLM; Apex→Claude Code/Codex/Cursor; AgentKernelArena→same adapters). Options: (a) local coder/architect role (self-hosted, weakest), (b) frontier single model (Claude), (c) ⭐ **Claude+Codex actor-critic** reusing the autopilot planner's infra. Evidence (c) is *better*, not merely allowed: **CudaForge (662) got its best result from a cross-model O3-coder/GPT-5-judge split** (actor-critic by another name), GEAK's Generator↔Evaluator and Apex's Coder↔Magpie-judge are actor-critic-shaped, and **AgentKernelArena's best results come from Claude Code (Opus 4.6, HIP-to-HIP 6.69×) and Cursor/Codex agents** — empirical corroboration on AMD kernel-gen, with Claude Code already a wired adapter. **Plan: prototype with the Claude+Codex actor-critic; local role is the self-hosted fallback.**

### 5.5 C4 (profiler-metric feed) — the standing research risk, three paths
A profiler-fed judge needs a compact, decision-relevant gfx90a counter set. CudaForge's (662) 24-metric NCU subset **does not transfer** (CDNA2 ≠ tensor-core semantics), and whether a small useful gfx90a subset even exists is unproven. **Try cheapest-first:** (1) ⭐ **GEAK-v2 OptimAgentv2 Profiler-Analyzer (677)** — feed *raw* `rocprof-compute` counters → LLM → NL performance intelligence (no curated subset to start; v2 ablation shows this loop is the dominant lever 1.38×→3.32×); caveat: v2 counters captured on gfx942, semantics port but values don't. (2) **Xe-Forge static constraint-KB (672)** — a hand-authored gfx90a rules YAML (wavefront=64, LDS sizing, MFMA tile constraints, VGPR/AGPR limits); profiler-*free*, cheap, brittle, good first-pass/fallback. (3) **CudaForge formal offline selection (662)** — rigorous, expensive, the fallback. **Note:** neither GEAK/Apex nor AgentKernelArena is profiler-counter-fed, so C4 stays genuinely ours.

### 5.6 C6 (anti-reward-hacking) — our differentiator, now with two complementary sources
Every AMD-native ref is *least* protected (GEAK/Apex/GEAK-HIP loose tolerance oracles; Apex's AST catches only fabrication). The evidence that this matters: CUDA-L1's 32.8% stream-timing exploit (661); the AI CUDA Engineer 150×→3×-*slowdown* scandal that birthed robust-kbench (668), which re-scored prior work **3.13×→1.49×** after removing 40 gameable tasks; KernelBench/METR gameable gates (664); the OpenReview 73.8%-proxy-gains-without-real-gains finding. **Two complementary defenses, both lift-able:** (i) **robust-kbench (668, Apache-2.0)** — the exploit-class half (output-buffer poisoning, eliminable-op/low-magnitude/uniform-output filtering, forward+backward correctness, 3-verifier pre-filter, stream-sync); (ii) **AgentKernelArena (679)** — the **unseen-shape half** (an LLM-driven generator of 8 held-out input configs × 6 categories that exposes shape-hardcoding — the dominant Torch2HIP failure, where correctness drops to 59.7%). Together they are the full C6. Plus a **red-team-with-cheating-kernels** exit gate.

### 5.7 Production-faithful evaluation (FastKernels 671) as a late gate
Operator-level/torch-eager scores overstate real gains ~25pp (1.16×→0.93× vs vendor baselines). So **C3 gates reward on an honest vendor baseline** (rocBLAS/hipBLASLt/AITER/torch-ROCm-compile), and a **whole-model exit gate** scores the kernel inside a full forward pass with captured real EPYC-workload tensors (Apex's hot-patch+re-bench operationalizes this). AgentKernelArena's unseen-config drop (§5.6) is a second instance of the same "isolated number overstates" lesson.

### 5.8 Triton on-ramp, HIP endgame
**Triton first** (GEAK-eval gfx90a-proven, open, clean ROCm backend — lowest-risk). **HIP second** — GEAK-HIP (678) proves the same loop closes at the hipcc level and **out-optimized a human engineer** (Voxelization 2.07× vs 1.84×); AgentKernelArena's **Torch2HIP** category (679) is the from-scratch torch→HIP path directly seeding the llama.cpp endgame. Neither ships an open HIP benchmark, so the HIP arm requires our own HIP oracle + robust-kbench hardening (UB risk is higher at raw-HIP). Pairs with `llama-cpp-dsa-contribution.md`.

## 6. Evidence matrix (grouped by ROLE, not chronology)
**AMD-native substrate (adopt):** GEAK 674 (C1/C2/C3/C5, gfx90a-proven, MIT) · Apex 675 (E2E harness + Magpie scorer + MCP, MIT, gfx90a-listed) · AgentKernelArena 679 (controller-A/B arena + 3 task suites + unseen-shape C6 half, Apache-2.0, **gfx942-only**) · GEAK-v2 677 (C4 Profiler-Analyzer + QD upgrades, **gfx942-only**) · GEAK-HIP 678 (HIP-arm patterns, **gfx942-only**).
**Controller candidates:** EvoEngineer 666 (lead) · KernelFoundry 669 (hardware-awareness layer) · Xe-Forge 672 (linear archetype) · K-Search 673 (world-model tree) · GEAK 674 (AMD-native, first to stand up).
**C4 sources:** GEAK-v2 Profiler-Analyzer 677 (try first) · Xe-Forge static-KB 672 · CudaForge formal selection 662.
**C6 sources:** robust-kbench 668 (exploit classes) · AgentKernelArena 679 (unseen shapes).
**Scoring/eval philosophy:** KernelBench 664 (`fast_p`) · FastKernels 671 (vendor baseline + whole-model) · Apex/AgentKernelArena Magpie shape.
**Optional later (offline):** ConCuR 665 + TritonForge 676 (SFT data-curation for a local HIP-specialized small model).
**RL lessons (no training):** CUDA Agent 660 · CUDA-L1 661 · Kevin 663.

## 7. Rejected / down-scoped paths (and why)
- **RL training of a bespoke kernel model** — infeasible on one MI210; TritonForge's AMD RL crashes.
- **KernelCraft (670) as a path** — its "AMD" is the Versal AIE-ML/XDNA **NPU via Peano LLVM**, a separate stack from ROCm/HIP, not our GPU. Harvested only: 6-tool vocabulary, extended-reasoning-required, ICL-exemplar findings.
- **TritonForge (676) as AMD-native** — gfx942-only, AMD-RL-unstable; down-scoped to its offline SFT recipe (pairs with ConCuR 665).
- **Re-basing the controller on GEAK-OpenEvolve (677)** — rejected per the §5.3 consistency guard (K-Search beats OpenEvolve; gfx90a-unproven; vendor-blog).
- **MultiKernelBench as primary backend** — superseded by GEAK-eval; kept only for multi-vendor abstraction.
- **Hand-rolling a controller-A/B harness** — superseded by adopting AgentKernelArena (679) as the comparison shell.

## 8. Net engineering picture (what actually has to be built)
1. **Reproduce GEAK-eval (+ AgentKernelArena) on the real MI210/gfx90a** — the sanity gate; expect lower absolute speedups at half the bandwidth, verify correctness/compat. *(integration of MIT/Apache-2.0 code.)*
2. **Register our controllers as AgentKernelArena adapters** and A/B them on gfx90a (Claude+Codex actor-critic, EvoEngineer, KernelFoundry, K-Search, Xe-Forge, GEAK).
3. **Build C6** — robust-kbench exploit classes (668) + AgentKernelArena unseen-shape generator (679) + a red-team gate. *(our differentiator.)*
4. **Build C4** — GEAK-v2 LLM-reads-raw-rocprof Profiler-Analyzer first (677), Xe-Forge static-KB second (672), CudaForge formal selection fallback (662). *(the standing research risk.)*
5. **Add the FastKernels production exit-gate** (671) via Apex's hot-patch+re-bench.
6. **Then the HIP arm** — GEAK-HIP patterns (678) + AgentKernelArena Torch2HIP suite (679) + our own HIP oracle, toward hand-HIP for the llama.cpp fork.
All gated on the MI210 (~July 2026); design/scoping proceeds now. **All AMD numbers are vendor-reported until reproduced on our own gfx90a.**

## 9. Freshness Appendix (sweep at each handoff audit / when the MI210 racks)
**Last swept: 2026-06-03 (operator).**
- **GEAK repo pins (drift is real):** `AMD-AGI/GEAK` HEAD `c8bfc19`, tags through `v4.8.3.3`, branches `GEAK-v2` and `GEAK-HIP`. The repo HEAD is *past* the published papers — **pin a paper-matching commit/tag before treating repo code as a paper's artifact.** (GEAK-eval and Apex live in the same org.)
- **Missing gfx90a evidence (the standing gap):** as of 2026-06-03 there is **no GEAK-v2 or GEAK-HIP arXiv paper** (both AMD-blog/repo-stage) and **no gfx90a numbers** for GEAK-v2, GEAK-HIP, or AgentKernelArena — all are MI300-class (gfx942). GEAK-v1 (arXiv 2507.23194) remains the only gfx90a-proven AMD reference. **Watch for:** a GEAK-v2 arXiv (re-credibility-score intake-677), a GEAK-HIP arXiv/open benchmark (could promote intake-678 toward adopt_component), and **any gfx90a/MI250 numbers** for v2/HIP/Arena (closes the gap).
- **AgentKernelArena (intake-679):** arXiv 2605.16819, Apache-2.0, repo `AMD-AGI/AgentKernelArena`. Public **leaderboard not yet released** (placeholder table); Torch2HIP/CUDA2HIP task sets expanding to 100+. Headline run **excluded GEAK/AutoTriton** — watch for a GEAK-vs-general A/B and the leaderboard launch.
- **New-sibling watch:** `rocm.blogs.amd.com` + the `AMD-AIG-AIMA` and `AMD-AGI` GitHub orgs (where GEAK/GEAK-eval/Apex/GEAK-HIP/AgentKernelArena all live) for further AMD-native kernel-agent tooling.
- **Standing caveat:** triple commercial bias on all AMD entries (AMD authors agent + benchmark + hardware); no independent third-party reproduction found in Tier-2b for any of intake-674–679. Treat as provisional until reproduced on our own gfx90a (`feedback_classify_eval_failures_by_reason`, observe-before-diagnosing).
