# Agentic ROCm Kernel Authoring — MI210 Verify+Profile Harness

**Status**: stub (design / investigation)
**Created**: 2026-06-03 (via /research-intake deep-dive of the LLM-kernel-generation cluster)
**Categories**: hardware_optimization, agent_architecture, autonomous_research, tool_implementation, training_distillation
**Hardware gate**: contingent on AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB) acquisition, expected ~July 2026.
**Priority**: MEDIUM (activates when MI210 lands; preparatory design can proceed now)
**Workstream**: Inference Acceleration / GPU
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**:
- [`rocm-verify-profile-backend.md`](rocm-verify-profile-backend.md) — **child**: the ROCm verify/profile/benchmark backend this harness drives (the long pole)
- [`gpu-drafter-mi200-investigation.md`](gpu-drafter-mi200-investigation.md) — MI210-gated; consumes the HIP kernels this authoring loop would produce
- [`gpu-acceleration-path.md`](gpu-acceleration-path.md) — tracks the ROCm kernel-library hand-port path (rocWMMA, AITER, hipBLASLt) this would automate
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) / [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) — the CPU AVX-512BW ukernel-authoring loop this rhymes with

---

## Objective

Stand up an **agentic kernel-authoring loop for the incoming MI210** that drives an existing strong coding model (our coder/architect role, or a frontier API) through a generate → compile → verify → profile → refine cycle to produce and tune **HIP/ROCm kernels** for the EPYC inference stack — replacing the manual hipify-and-hand-tune path with an automated verify+profile reward loop. Adopt the patterns proven by the CUDA kernel-generation literature; decline the parts that don't fit (NVIDIA toolchain, multi-GPU RL training, closed checkpoints).

**One-line thesis**: we cannot retrain a bespoke kernel model on a single MI210, but we *can* run a train-free, profiler-fed authoring loop driven by an off-the-shelf coder model — the literature shows that approach is competitive with (and cheaper than) RL-trained kernel models.

## Research Context

Deep-dived 2026-06-03 (intake-660 parent + 661–666 cluster). All are NVIDIA/CUDA-targeted; the value to us is **methodology transfer to ROCm**, not the released CUDA artifacts.

| Intake ID | Title | Paradigm | Relevance | Verdict | Why it matters here |
|-----------|-------|----------|-----------|---------|---------------------|
| intake-660 | CUDA Agent (ByteDance) | Large-scale agentic **RL** + open harness | high | adopt_patterns | The open verify+profile env (SKILL.md + verification.py + profiling.py + compile.sh) + 6K dataset — the env template |
| intake-661 | CUDA-L1 (DeepReinforce) | **Contrastive RL**, speedup-only reward | high | adopt_patterns | Contrastive-prompt recipe (feed prior variants+scores) usable **without** RL; anti-reward-hack defense kit |
| intake-662 | CudaForge (UMN) | **Training-free** Coder/Judge + profiler feedback | medium | adopt_patterns | Closest fit for single-GPU/no-cluster; the **offline profiler-metric-selection** algorithm is the key reusable asset |
| intake-663 | Kevin (Stanford/Cognition) | **Multi-turn RL** | medium | adopt_patterns | Multi-turn loop structure + cross-turn credit (sum, γ=0.4); sequential-refine > parallel-sample under fixed budget |
| intake-664 | KernelBench (Stanford) | **Benchmark** | high | worth_investigating | The scoring contract (fast_p, L1/L2/L3 tiers); ROCm analog tracked in child handoff |
| intake-665 | ConCuR (Westlake) | **Data curation** + LoRA distill | high | adopt_patterns | How to build a (HIP, CoT, kernel) corpus + cheap short-CoT quality filter; length ⟂ speedup (r=−0.047) |
| intake-666 | EvoEngineer (CityU HK) | **Train-free evolutionary** search | high | adopt_patterns | **Lead controller**: leanest loop runnable on one MI210 today; modular evaluator = the seam to re-target for ROCm |
| intake-667 | MultiKernelBench (Nanjing/Zhejiang) | **Multi-platform benchmark** | high | adopt_component | Backend abstraction (CUDA/AscendC/Pallas/Triton/SYCL) — confirmed ROCm-benchmark fork target (child handoff C5) |
| intake-668 | robust-kbench (Sakana) | **Anti-hacking harness** | high | adopt_component | Apache-2.0 exploit→defense catalogue + filtering/oracle code — reward-integrity layer (child handoff C2/C6) |
| intake-669 | KernelFoundry (Intel) | **Train-free evolutionary + hardware-aware** | high | adopt_patterns | **adopt-BOTH with 666**: MAP-Elites QD + profiler-gradient + per-arch template tuning as the hardware-awareness layer; multi-vendor backend template |
| intake-670 | KernelCraft (Cambridge/Imperial/AMD) | **ISA-level NPU/CPU benchmark** | med | adopt_patterns | **NOT our path** ("AMD" = AIE-ML NPU/Peano, not ROCm). Harvest: 6-tool function-calling vocabulary, extended-reasoning-required, ICL-exemplar lever |
| intake-671 | FastKernels (Snowflake/CMU/UCSD) | **Production-faithful benchmark** | med | adopt_patterns | Production-vs-sandbox misalignment (~25pp); adopt MacroEval **vendor-baseline + whole-model eval philosophy** as a Phase-5 exit gate |
| intake-672 | Xe-Forge (Intel) | **Train-free linear multi-stage (non-evolutionary)** | med | adopt_patterns | Contemporary competitor to 669 (NOT supersede). Harvest: **linear CoVeR controller archetype** + **static gfx90a-constraint-KB** (profiler-free hardware-awareness). Surfaces GEAK pointer |
| intake-673 | K-Search (UC Berkeley Sky) | **Train-free co-evolving world-model tree** | high | adopt_patterns | **3rd controller candidate** — open-source, **14.3× on MoE kernels** (named MI210 target); decoupled planning + bug-tolerant search. Does NOT supersede 666 |
| **intake-674** | **GEAK (AMD)** | **AMD-native train-free Triton agent + 2 open benchmarks** | **high** | **adopt_component** | **🔑 KEYSTONE — first AMD-native/ROCm reference, proven ON gfx90a (MI250X = MI210 ISA). GEAK-eval = the C1/C2/C3/C5 backend substrate. 4th controller candidate (Generator/Evaluator/Reflector/Optimizer)** |
| **intake-675** | **Apex (AMD-AGI)** | **AMD-native E2E optimize→hot-patch→re-bench harness** | **high** | adopt_patterns | **🔑 The ROCm HARNESS: Magpie scorer + AST anti-tamper + 5 MCP servers + hot-patch deploy + RL-trajectory export. Explicitly supports gfx90a. MIT** |
| intake-676 | TritonForge (UCR/Meta) | SFT+RL train + train-free paper | high | adopt_patterns | **Correction**: AMD support is gfx942/MI300X only, NOT gfx90a; AMD RL crashes. Subordinate to GEAK. Harvest: open SFT/data-curation recipe (pairs with 665) |
| intake-677 | GEAK-v2 family (AMD) | AMD-native Triton v2: OptimAgentv2 + OpenEvolve (train-free) | high | adopt_patterns | **C4 de-risk**: OptimAgentv2's Profiler-Analyzer (rocprof-compute→LLM→NL). OpenEvolve = AMD-native MAP-Elites QD (9-dim grid → upgrades 669 layer). **GAP: gfx942/CDNA3 only, NO gfx90a** (regression vs v1) |
| intake-678 | GEAK-HIP (AMD) | AMD-native **raw HIP/C++** optimization agent (train-free) | high | adopt_patterns | **The HIP-arm reference** (our llama.cpp endgame). 3-module loop; **out-optimized a human engineer** (Voxelization 2.07× vs 1.84×). gfx942-only; ships no open benchmark |

## Approach Taxonomy & Recommended Path

The cluster spans four paradigms. Mapped to our constraints (single 64 GB MI210, no training cluster, opensource_only, existing strong coder models in-house):

1. **Train-free evolutionary / agentic search** (EvoEngineer 666, CudaForge 662, **KernelFoundry 669**) — ✅ **lead path.** Runs on one GPU with an off-the-shelf model; no policy training. EvoEngineer's modular evaluator + CudaForge's profiler-metric-fed Judge are the two halves of the controller; **KernelFoundry (adopt-both, intake-669) adds the hardware-awareness layer on top** — MAP-Elites quality-diversity archive (better exploration than a flat population), profiler-metric-in-the-loop, and per-arch template (tile/block) tuning.
2. **RL-trained kernel model** (CUDA Agent 660, CUDA-L1 661, Kevin 663) — ⛔ training out of reach on one MI210. ✅ but harvest the **reward design + anti-reward-hacking gates + multi-turn structure**, which apply to a train-free loop too.
3. **Data-curation + LoRA distillation** (ConCuR 665) — 🟡 optional later: if/when we want a *local* HIP-specialized small model, the curation recipe + 8×A100-class one-shot LoRA is feasible offline (not on the MI210 itself).
4. **Benchmark / scoring** (KernelBench 664) — ✅ prerequisite; see child handoff `rocm-verify-profile-backend.md`.

**Recommended first milestone**: EvoEngineer-style train-free controller (intake-666) + CudaForge profiler-metric-fed Judge (intake-662), driven by our coder/architect role, scoring against the ROCm verify+profile backend (child handoff). Defer all RL and distillation.

## CUDA → ROCm Porting Surface (what does NOT transfer for free)

| Layer | CUDA (as published) | ROCm/MI210 replacement | Owner |
|-------|---------------------|------------------------|-------|
| Build | nvcc, torch cpp_extension load_inline | hipcc / hipify, torch-ROCm cpp_extension | child handoff |
| Correctness oracle | torch.allclose vs torch-CUDA reference | torch-ROCm allclose (HIP aliases cuda namespace) | child handoff |
| Timing/reward | torch.cuda.Event (3 warmup/100 trials) | torch.cuda.Event under ROCm OR rocprof timing | child handoff |
| Profiler feedback | Nsight Compute (NCU), 24-metric subset | rocprofv3 / rocprof-compute (Omniperf); **re-derive** the gfx90a metric subset (NVIDIA subset will NOT transfer) | child handoff |
| Benchmark | KernelBench (CUDA-only) | fork MultiKernelBench (2507.17773) + register gfx90a/HIP backend (<20 LoC claim) | child handoff |
| Reward integrity | stream-sync, adversarial checker, robust discrete reward | same defenses (exploit classes recur on ROCm); harden via robust-kbench (2509.14279) | this handoff |
| Model | closed Seed-1.6 / DeepSeek-V3 / QwQ-32B | **agent backend is pluggable** — pick from: (a) our local coder/architect role; (b) a frontier single model (Claude); (c) **a Claude+Codex actor-critic combo** reusing the autopilot planner's infra. See the agent-backend note below. | this handoff |

## Open Questions

- Which in-house model drives the loop best — coder role (local, opensource) vs a frontier API for one-shot authoring quality? Run the CudaForge cross-model finding (best is coder/judge split across two models) on our roster.
- Is the EvoEngineer train-free controller or the CudaForge profiler-Judge the better *first* controller, or do we want CudaForge's metric-feed bolted onto EvoEngineer's evolutionary population? (They compose.)
- What's the smallest set of EPYC-relevant kernels to target first — the MI210 frontdoor attention + MoE dispatch + dequant kernels named in `gpu-drafter-mi200-investigation.md`, not generic KernelBench ops.
- ~~Does KernelFoundry (2603.12440) subsume EvoEngineer before we commit?~~ **RESOLVED 2026-06-03 (intake-669): NO supersession → adopt-BOTH.** KernelFoundry never benchmarks EvoEngineer; both are train-free evolutionary. Keep EvoEngineer as the lean lead controller and **bolt on KernelFoundry's hardware-awareness layer** (MAP-Elites QD archive for exploration + profiler-metric-in-the-loop + per-arch template tuning). Its multi-vendor (SYCL+CUDA) backend factoring is also the architectural template for the child backend handoff.
- Reward-hacking: which exploit classes (no-op via output-buffer reuse, library-passthrough, stream-timing) manifest under HIP timing, and which robust-kbench defenses port? Must be designed in from day one (see intake-661/663/664 contradicting-evidence).

## Notes

- This is the umbrella; the **buildable backend skeleton lives in the child handoff** [`rocm-verify-profile-backend.md`](rocm-verify-profile-backend.md), which is the long pole and independent of model choice.
- opensource_only is satisfied on the lead path: EvoEngineer ships a modular open platform, no closed checkpoint, no SaaS base model required.
- Per `feedback_no_concurrent_inference` / `feedback_speed_verify_via_llama_bench`: any MI210 timing runs that share the host with EPYC CPU benches need explicit per-run approval — the authoring loop's profiling step is a benchmark and must respect the same gating.

## Reporting Instructions

After any work here: update this handoff's status, tick the child-handoff phase checkboxes in `rocm-verify-profile-backend.md`, log progress in `progress/YYYY-MM/`, and reflect intake cross-refs if new cluster papers land (KernelFoundry 2603.12440 is the next intake candidate).

## Research Intake Update — 2026-06-03 (next-tier batch: intake-670/671/672/673)

Four more cluster papers deep-dived. Net effect on the controller decision: **a third candidate (K-Search) and a second controller archetype (Xe-Forge's linear pipeline)**, plus a sharper evaluation philosophy. One correction and one high-value new pointer.

### Controller design — now a 3-candidate, 2-archetype decision
- **Archetype A — evolutionary** (lead path, unchanged): EvoEngineer (666) lean controller + KernelFoundry (669) hardware-awareness layer (MAP-Elites QD + profiler-gradient + per-arch template tuning).
- **Archetype B — linear multi-stage** (NEW, intake-672 Xe-Forge): a fixed ordered pipeline of single-purpose CoVeR refinement agents (fusion → memory-coalescing → block-ptr → persistent-kernel → autotune), each with on-hardware 4-level verification. **Cheaper and more interpretable than evolutionary search**; worth prototyping as an alternative controller. Xe-Forge is a *contemporary competitor* to KernelFoundry (same lab, different team) — it does **NOT** supersede 669; both are harvestable.
- **NEW 3rd candidate — world-model tree** (intake-673 K-Search, UC Berkeley Sky, **open-source**): reframes authoring as search over an explicit tree of NL optimization hypotheses + programs, decoupling planning from instantiation and **tolerating temporary bugs/regressions** (the exact failure flat-population evolution suffers). Reports **2.1× avg / 14.3× on MoE kernels** vs OpenEvolve/ShinkaEvolve — and **MoE-dispatch is a named MI210 target**. Adopt its three patterns into the controller design: (1) explicit hypothesis-tree state (NL intent separate from code), (2) in-context Insert/Update/Prune world-model evolution with per-node [0,1] priority, (3) stagnation-limited refinement (K=7) before backtracking. **Does NOT supersede EvoEngineer** (never benchmarks it — avoid closure-inflation); gate any "switch lead to K-Search" on reproducing it against our ROCm backend once the MI210 lands.

### Profiler-FREE hardware-awareness (intake-672) — de-risks the C4 long pole
Xe-Forge's **static hardware-constraint knowledge base** (84 YAML entries: hard constraints + before/after patterns, prompt-injected) is a cheap, **profiler-counter-free** alternative to the CudaForge/KernelFoundry metric-selection path the child backend flags as its highest-risk component (C4). Author a **gfx90a rules/patterns YAML** (wavefront=64, LDS sizing, MFMA tile constraints, VGPR/AGPR limits) as a first-pass hardware-awareness layer that needs no rocprof counters. Recorded in the child handoff.

### Evaluation philosophy (intake-671 FastKernels) — a Phase-5 exit gate
FastKernels quantifies **production-vs-sandbox misalignment**: operator-level/torch-eager scores (which all our controllers and the MultiKernelBench fork optimize) **overstate real gains ~25pp** (1.16× sandbox → 0.93× vs vendor baselines). Adopt the philosophy as a late-stage exit gate: score authored HIP kernels **in a full torch-ROCm/llama.cpp forward pass with captured real EPYC-workload tensors against rocBLAS/hipBLASLt/AITER**, not just isolated-op `fast_p` vs torch-eager. Recorded in the child backend handoff.

### Correction (intake-670 KernelCraft)
Despite "emerging hardware + AMD" framing, KernelCraft targets the **Versal AIE-ML / XDNA NPU via Peano LLVM** — a *separate stack from ROCm/HIP*, **not** our CDNA2/gfx90a MI210. Relevance is medium, not high. Harvest only: its **6-tool function-calling vocabulary** (write_code/check_syntax/run_evaluation/view_output/get_instruction_size/grep_docs) as a tool-surface template, its **extended-reasoning-required** finding (model-selection constraint), and its **ICL-exemplar** lever (corroborates intake-667). If AMD AIE/XDNA ever enters scope, KernelCraft + NPUEval (2507.14403) are the references.

### Highest-value follow-up pointer (surfaced by intake-672)
**GEAK (arXiv:2507.23194)** — **AMD's own Triton-kernel AI agent for Instinct (MI300X/MI250), with a GEAK-HIP variant and a ROCm Triton benchmark.** This is materially more MI210-relevant than anything ingested so far (AMD-native, ROCm, Triton). **Strongly recommend a dedicated intake next.** (Also adjacent: Apex, TritonForge for ROCm.)

## Research Intake Update — 2026-06-03 (GEAK KEYSTONE: intake-674/675/676)

**The program's premise just got materially de-risked.** Until now every reference was NVIDIA/CUDA — we were planning a methodology-transfer + from-scratch-ROCm-backend build. The GEAK batch surfaced the **first AMD-native, ROCm-targeted, gfx90a-proven** references, two of them MIT-licensed and directly reusable.

### The headline: gfx90a is the MI210's ISA family — and GEAK already runs on it
**MI250X = CDNA2 / gfx90a = the exact ISA family of our incoming MI210.** GEAK (intake-674) reports results **on MI250X (gfx90a)** — 52.72% exec / 2.42× on TritonBench-revised — not only on MI300X. So GEAK's generated Triton kernels, its correctness oracle, its timing, and its two benchmarks run on the MI210 with **autotune-level re-tuning only, no porting**. This is categorically different from the entire intake-660–673 cluster, none of which produces a runnable AMD artifact.

### Impact on the two open decisions
- **Backend (child handoff):** GEAK-eval + Apex become the **C1/C2/C3/C5 substrate** — see `rocm-verify-profile-backend.md`'s GEAK keystone section. The "long pole" shrinks to **C6 (anti-hacking) + C4 (gfx90a profiler-metric)** — precisely GEAK's/Apex's gaps, which robust-kbench (668) and Xe-Forge's static-KB (672) cover. **Our differentiated engineering is now small and well-scoped.**
- **Controller:** GEAK is a **4th candidate** (Generator → Evaluator[cascaded] → Reflector[Reflexion memory] → Optimizer[LLM-as-Optimizer], + code-similarity 1-shot + knowledge injection + sequential/parallel best-of-K). It is train-free and AMD-proven, but it is best-of-K, **not** population/QD or world-model-tree — it does **not** auto-displace the EvoEngineer (666) + KernelFoundry (669) evolutionary lead or K-Search (673). Harvest its modules as patterns; consider it the **default first controller to stand up** simply because it already runs on gfx90a.
- **Harness:** Apex (intake-675) is the AMD-native **deploy harness** — its profile→optimize→**hot-patch into site-packages**→re-benchmark-E2E loop, Magpie reward, AST anti-tamper, and 5 MCP servers are the concrete realization of this umbrella's "generate→compile→verify→profile→refine" loop, and its E2E scoring operationalizes the FastKernels (671) production-faithful exit gate.

### Revised recommended first milestone (supersedes the EvoEngineer-only milestone above)
When the MI210 racks: **(1)** stand up **GEAK-eval on gfx90a** and reproduce the MI250X numbers on our MI210 (sanity gate); **(2)** run the **GEAK agent** (or Apex's pipeline) — agent backend per the note below (local role, Claude single, or a Claude+Codex actor-critic); **(3)** harden the loose GEAK/Apex correctness oracle with **robust-kbench (668)** (C6) before trusting any speedup; **(4)** keep EvoEngineer / KernelFoundry / K-Search as alternative controllers to A/B against GEAK once the backend is live. RL training and LoRA distillation stay deferred.

### Correction logged (intake-676 TritonForge)
Xe-Forge grouped TritonForge as AMD/ROCm-targeted; the deep-dive found its AMD support is **gfx942/MI300X (CDNA3) only — not our gfx90a/MI210** — and its AMD RL path crashes. It is **AMD-secondary, subordinate to GEAK**; useful only for its open SFT/data-curation recipe (offline local-model branch, pairs with ConCuR 665) and as corroboration that Triton's ROCm backend is a real on-ramp.

### Follow-up candidates (updated; GEAK family is now the priority)
- **GEAK-v2** — GEAK-OptimAgentv2 (evolutionary, +9.76% / avg 3.32×) + GEAK-OpenEvolve (QD, avg 3.42×, up to 11.23× per kernel); evaluated on MI300X/MI325X, **not yet gfx90a**. Blog-stage; watch for an arXiv ID.
- **GEAK-HIP** — extends GEAK from Triton to **HIP-level** kernels (our llama.cpp fork ultimately wants hand-HIP, so this is directly on-path). Blog-stage.
- (Superseded as top pointer: GEAK itself, now ingested as intake-674.) NPUEval (2507.14403) only if AMD AIE/XDNA ever enters scope.

## Agent backend — pluggable; actor-critic is the favored option (2026-06-03)

A clarification that earlier framing got wrong by defaulting to "our local coder role": **`opensource_only` governs deployed production services, not build-time tooling.** The kernel-authoring loop is an *offline build tool*; the **authored HIP/Triton kernel is the deployed artifact**, not the LLM that wrote it (same way Claude Code writes this project's code without violating the constraint). Both candidate harnesses have **pluggable agent backends** — GEAK routes via LiteLLM (any provider); Apex ships Claude Code / Codex / Cursor adapters. So the backend options are:

1. **Local coder/architect role** — fully self-hosted; lowest capability, zero external dependency.
2. **Frontier single model (Claude)** — strongest single-actor; GEAK/CudaForge show frontier reasoning models dominate on kernel-gen.
3. **Claude + Codex actor-critic combo** — ⭐ **favored.** Reuse the autopilot planner's existing Claude+Codex actor-critic infra. Evidence it's the *better* design, not just allowed: **CudaForge (intake-662) got its best result from a cross-model Coder/Judge split (O3-coder + GPT-5-judge, 2.114×)** — an actor-critic by another name — and GEAK's Generator/Evaluator and Apex's Coder + Magpie-judge are already actor-critic-shaped. A Claude-actor (Generator) + Codex-critic (Evaluator/Judge) maps cleanly onto GEAK's and Apex's module boundaries.

**Recommendation:** prototype with the **Claude+Codex actor-critic** (reusing autopilot infra) as the default backend, with the local role as the self-hosted fallback. This supersedes the "local coder role only" phrasing elsewhere in this doc.

## Research Intake Update — 2026-06-03 (GEAK-v2 family + GEAK-HIP: intake-677/678)

Ingested the available (blog/repo-stage) GEAK follow-ups. Both train-free, AMD-native — but **both regress gfx90a coverage** (all results on gfx942/CDNA3 MI300X/MI325X/MI308X; none on our gfx90a), so they are **adopt_patterns, not adopt_component** (unlike gfx90a-proven v1).

- **intake-677 GEAK-v2** = two agents: **GEAK-OptimAgentv2** (instruction→Triton + Multi-Offspring Evolution + an **Advanced LLM-Evaluator** + a **Profiler-Analyzer: rocprof-compute counters → LLM → natural-language perf intelligence**) and **GEAK-OpenEvolve** (Triton→Triton **MAP-Elites QD** over a 9-dim feature grid, AlphaEvolve-derived). Harvests: (a) the **Profiler-Analyzer is a cheaper C4 path** — an LLM reading raw rocprof-compute output, sidestepping manual metric-subset re-derivation (recorded in the child backend handoff); (b) OpenEvolve's **9-dim grid + Hybrid Parent Selection + Cascade Filtering** upgrade the KernelFoundry-669 QD layer. **Cross-check:** K-Search (673) reports beating OpenEvolve 2.1×/14.3× MoE → keep K-Search as a candidate; OpenEvolve does **not** displace the controller lead.
- **intake-678 GEAK-HIP** = the **raw HIP/C++** arm (our llama.cpp hand-HIP endgame, more on-path than any Triton-only entry). 3-module Generator/Evaluator/Reflector loop + parallel offspring + a GEMM-heuristic-generation mode. **Strongest existence proof in the whole cluster: the agent out-optimized a human engineer** on production kernels (Voxelization 2.07× vs 1.84×, SwiGLU 1.68× vs 1.30×). Ships no open benchmark → patterns only; pairs with `llama-cpp-dsa-contribution.md`. Triton (GEAK-eval, gfx90a-proven, open) stays the lower-risk **on-ramp**; GEAK-HIP is the **endgame** target once the Triton loop is working.

### 🔁 AUDIT REMINDER — re-check for fresh GEAK-family content at next review
GEAK-v2 and GEAK-HIP are **blog/repo-stage (no arXiv, no gfx90a eval)** as of 2026-06-03. **At the next audit of this handoff (or when the MI210 racks), re-run a fresh-content sweep:**
- [ ] Has a **GEAK-v2 arXiv paper** appeared? (re-credibility-score intake-677 if so — currently null/vendor-blog.)
- [ ] Has a **GEAK-HIP arXiv / open benchmark** appeared? (could promote intake-678 toward adopt_component.)
- [ ] Has AMD published **any gfx90a / MI250 numbers for v2 or GEAK-HIP**? (closes the standing coverage gap.)
- [ ] Repo HEAD drift: pin/refresh the GEAK-agent commit mapping (HEAD is past the papers — "GEAK 3.2.0" 2026-05-21; new subagents land frequently).
- [ ] New AMD-native siblings beyond GEAK/Apex/GEAK-HIP (watch rocm.blogs.amd.com + AMD-AIG-AIMA/AMD-AGI GitHub orgs).

---

# Full Reasoning Narrative & Decision Log (VERBOSE REVIEW DRAFT — 2026-06-03)

> **Why this section exists / how to read it.** This is a deliberately *verbose* capture of the entire reasoning chain and the deep-dive/intake evidence behind this program, written for human review **before** the handoff is cleaned up, polished, and tightened. It intentionally repeats and over-explains. Once reviewed, the durable conclusions should be distilled back into the sections above and this narrative trimmed or moved to a `research/deep-dives/` note. Every claim here traces to an intake entry (intake-660…678) — read those for the per-paper specifics (key_claims, reported_results, `amd_rocm_transferability`, `mi210_gfx90a_applicability`, `contradicting_evidence`).

## 0. One-paragraph executive statement
We are a CPU-inference shop (EPYC 9655, custom llama.cpp fork) receiving our first datacenter GPU — an **AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB), ~July 2026**. The goal is to **author custom HIP/Triton kernels** for the EPYC inference stack on it, using an **agentic, train-free, verify+profile loop** rather than hand-porting kernels. Over 2026-06-03 we ingested the entire LLM-GPU-kernel-generation literature (19 entries, intake-660–678) and pivoted it onto this AMD path. The decisive discovery is that **AMD has already built and open-sourced most of what we need (GEAK + Apex, MIT) and demonstrated it on gfx90a — the MI210's exact ISA family** — so the program collapses from "build a ROCm kernel-authoring stack from scratch" to "adopt AMD-native MIT code + add two well-scoped pieces of our own (anti-reward-hacking hardening and a gfx90a profiler-metric layer)."

## 1. Provenance — how this program came to exist (the actual sequence)
1. **Seed.** A routine `/research-intake` of **CUDA Agent** (ByteDance, arXiv 2602.24286 → intake-660): a large-scale agentic-RL system that authors CUDA kernels, SOTA on KernelBench. On its own, NVIDIA-only and not obviously relevant to a CPU shop.
2. **The steer that created the program.** Mid-intake the operator interjected: *we are building custom kernels for the AMD stack, and an MI210 lands next month.* That single steer reframed the whole cluster from "interesting NVIDIA methodology to file under hardware_optimization" into "**near-term, hardware-gated engineering program**." Relevance of intake-660 was elevated medium→high on that basis, and every subsequent ingest was scored through the **MI210/gfx90a lens**.
3. **Cluster expansion (660→673).** We chased CUDA Agent's references and the surrounding literature in batches: the core cluster (CUDA-L1, CudaForge, Kevin, KernelBench, ConCuR, EvoEngineer = 661–666), a de-risking batch (MultiKernelBench, robust-kbench, KernelFoundry = 667–669), and a next-tier batch (KernelCraft, FastKernels, Xe-Forge, K-Search = 670–673). All NVIDIA/Intel — value was methodology transfer + the design of a from-scratch ROCm backend.
4. **The keystone (674→676).** Xe-Forge's (672) related-work surfaced **GEAK** — AMD's *own* Triton kernel agent for Instinct. Ingesting it (674) + its sibling **Apex** (675) + **TritonForge** (676) flipped the program: the first **AMD-native, ROCm-targeted, gfx90a-proven** references, two of them MIT-licensed.
5. **GEAK family follow-up (677→678).** GEAK-v2 (OptimAgentv2 + OpenEvolve) and GEAK-HIP — blog/repo-stage, AMD-native, but a **gfx90a coverage regression** (gfx942/CDNA3 only). Patterns, not components.

The narrative arc: **a single NVIDIA paper → an operator steer → an exhaustive literature sweep → the realization that the vendor (AMD) had already solved most of the backend on our exact silicon.** The intake index is the audit trail; the two handoffs are the synthesis.

## 2. Problem framing and hard constraints (these drive every decision)
- **Hardware:** one MI210 (CDNA2/gfx90a, 64 GB HBM2e, single-GCD). This is the binding constraint behind "train-free" and behind every "does it run on gfx90a?" question.
- **No training cluster.** We cannot do multi-GPU RL or large SFT on-device. (Offline LoRA distillation on a separate box is *possible* later but out of near-term scope.)
- **`opensource_only`** — but see §7: this governs **deployed production services**, not build-time tooling. The authored kernel is the deployed artifact; the LLM that authors it is a build tool.
- **Existing assets:** strong in-house coder/architect roles, and an **autopilot planner that already runs a Claude+Codex actor-critic** — reusable infra for the agent backend.
- **The endgame artifact:** our llama.cpp fork ultimately wants **hand-written HIP/C++ kernels** (attention, MoE dispatch, dequant — the ops named in `gpu-drafter-mi200-investigation.md`). Triton is an on-ramp; raw HIP is the destination.

## 3. The single most important technical fact: CDNA generations and gfx90a
This underpins the entire "is it reusable?" analysis, so it is stated explicitly:

| AMD part | Architecture | ISA (gfx target) | Relation to our MI210 |
|----------|--------------|------------------|------------------------|
| **MI210** (ours) | CDNA2 | **gfx90a** | — (single-GCD, 64 GB) |
| **MI250 / MI250X** | CDNA2 | **gfx90a** | **SAME ISA family**; MI250X is dual-GCD (MI210 ≈ one MI250 GCD) |
| MI300X / MI325X / MI308X | CDNA3 | gfx942 | newer; adds MFMA/FP8 paths gfx90a lacks |
| MI355X | CDNA4 | gfx950 | newer still |

**Consequence:** any work *demonstrated on MI250/MI250X is demonstrated on our MI210's ISA* and transfers with autotune-level re-tuning only (clock/HBM-bandwidth/per-GCD-partitioning differ, but wavefront=64, MFMA, LDS semantics are identical — no porting). Work demonstrated *only on MI300X/MI325X (gfx942)* does **not** automatically carry: gfx942 kernels can use CDNA3-only instructions and tile shapes that are absent or suboptimal on CDNA2. This table is why **GEAK v1 (intake-674, reports an MI250X line) is our keystone** while **GEAK-v2 and GEAK-HIP (gfx942-only) are a coverage regression** despite being newer.

## 4. Decision: train-free, not RL-trained (and what we still take from the RL papers)
**Reasoning.** The headline-strongest results in the literature come from RL-trained kernel models — CUDA Agent (660), CUDA-L1 (661), Kevin (663) — but training any of them needs a GPU cluster at ByteDance/lab scale. TritonForge (676) is the cautionary data point: its AMD RL path *crashes within 2 steps on MI300X*. We have one MI210. **Therefore RL training is out.** The counter-evidence that this is OK: the *train-free* agentic loops (CudaForge 662, EvoEngineer 666, K-Search 673, GEAK 674) report results competitive with — and far cheaper than — the RL-trained models, by spending **inference-time compute** (sequential refinement + parallel best-of-K + evolutionary/QD search) instead of training compute. GEAK's own ablations show inference-time scaling alone takes correctness from <15% to 54–63%.
**What we still harvest from the RL papers** (without training): reward *design* (CUDA-L1's discrete/robust speedup reward, Kevin's `0.3·correct + speedup` with γ=0.4 cross-turn credit), the **anti-reward-hacking gates** (CUDA-L1's stream-timing fix, Kevin's run-candidate-before-reference + tensor-enlargement), and the **multi-turn structure** (Kevin's finding that sequential refinement beats parallel sampling under a fixed budget). These are all loop-design lessons that apply to a train-free controller verbatim.

## 5. Decision: controller candidates (why several, why no single winner yet)
We are deliberately keeping **four/five controller candidates** to A/B once the backend is live, because none has been measured against the others on our hardware and each occupies a distinct, defensible point in design space:
- **EvoEngineer (666)** — flat-population LLM-guided evolutionary search; the *lean lead* because it's the simplest train-free loop that runs on one GPU with an off-the-shelf model, and its modular evaluator is the clean seam to re-target for ROCm. Weakness: flat population is prone to mode-collapse on hard, non-monotonic optimizations.
- **KernelFoundry (669)** — MAP-Elites **quality-diversity** + profiler-gradient + per-arch template tuning, multi-vendor (SYCL+CUDA) backend. **adopt-both with EvoEngineer**: it's the *hardware-awareness layer* (better exploration than a flat population, profiler-in-the-loop). Its multi-vendor backend factoring is also the architectural template for our ROCm backend.
- **Xe-Forge (672)** — a *non-evolutionary* **linear multi-stage CoVeR** pipeline (ordered single-purpose refinement agents + 4-level on-hardware verification). A genuinely different archetype — cheaper and more interpretable than search; worth prototyping as an alternative. Same lab as KernelFoundry, different team, **does not supersede it**.
- **K-Search (673)** — a **co-evolving world-model tree** that decouples natural-language planning from program instantiation and is *bug-tolerant* across intermediate regressions/compile failures. Reports beating OpenEvolve/ShinkaEvolve 2.1× avg / **14.3× on MoE kernels** (a named MI210 target). Open-source. The most compelling *new* idea, but NVIDIA-only and unreplicated — so adopt-patterns, gate "make it lead" on a gfx90a reproduction.
- **GEAK agent (674)** — AMD-native 4-module (Generator/Evaluator/Reflector/Optimizer) best-of-K. Train-free, **proven on gfx90a**. It becomes the *default first controller to stand up* purely because it already runs on our ISA, even though architecturally it's best-of-K rather than QD/tree.

**Why no winner:** the suites and hardware differ across papers (EvoEngineer on RTX 4090/CUDA, KernelFoundry on Intel Arc/SYCL, K-Search on H100, GEAK on MI250X/MI300X), so headline numbers are apples-to-oranges. We resolve this empirically: stand up the GEAK-eval backend on the MI210, then A/B the controllers on *our* gfx90a with *our* EPYC-relevant ops.
**A consistency guard we enforced:** GEAK-v2's OpenEvolve (677) is an OpenEvolve/AlphaEvolve derivative, and K-Search (673) explicitly beats OpenEvolve — so we did **not** let the newer, AMD-native OpenEvolve auto-promote over K-Search. We harvest OpenEvolve's richer 9-dim QD grid + cascade filtering as *upgrades to the KernelFoundry layer*, and keep K-Search as a candidate. (This is also an instance of the project's standing `feedback_closure_inflation` discipline: don't let "newer/vendor" extrapolate into "better" without a head-to-head.)

## 6. Decision: the backend substrate (the pivotal reversal)
**Original plan (pre-GEAK).** Because the whole 660–673 cluster is NVIDIA-bound at the toolchain (nvcc, Nsight Compute, CUDA-only KernelBench), we scoped a *from-scratch* ROCm backend: fork **MultiKernelBench (667)** for the task suite (its `@register_backend` abstraction already runs CUDA/AscendC/Pallas/Triton/SYCL, so adding a gfx90a/HIP backend is bounded), port `fast_p` in ourselves, and lift **robust-kbench (668, Apache-2.0)** for the correctness oracle + anti-hacking. This was the "long pole."
**The reversal (GEAK keystone).** GEAK (674) ships **GEAK-eval** (MIT): two open benchmarks (TritonBench-revised 184 kernels + a *real* ROCm Triton benchmark of 30 kernels harvested from ROCm/triton, aiter, aotriton, vllm, pytorch, xformers) with a **ROCm build + torch-ROCm correctness oracle + AMD timing that already run on gfx90a (MI250X)**. Apex (675, MIT) ships the **end-to-end harness** (profile real serving workload → optimize bottleneck → **hot-patch into site-packages** → re-benchmark E2E) with the **Magpie scorer** (`compiled·20 + correct·100 + piecewise-speedup`) + **AST anti-tampering** + **5 MCP servers**, and explicitly lists **gfx90a** support. So **C1 (build), C2 (correctness), C3 (timing/reward), C5 (benchmark)** — the bulk of the "long pole" — are *already built, MIT-licensed, and demonstrated on our ISA*.
**Revised substrate.** GEAK-eval + Apex are the primary C1/C2/C3/C5 substrate; MultiKernelBench (667) is demoted to secondary (kept only for its multi-vendor abstraction if we ever want non-AMD backends), with our own `fast_p` tiering layered on. The two pieces that remain genuinely **net-new and ours to own** are **C4** and **C6** (next two sections) — which, not coincidentally, are exactly GEAK's/Apex's gaps. This is the cleanest possible outcome: we stand on AMD's MIT code and add only our differentiated value.

## 7. Decision: agent backend — pluggable, and an actor-critic is favored
**The mistake corrected.** Earlier drafts defaulted to "drive the loop with our local coder role (opensource_only)." That over-applied the constraint. `opensource_only` (per `feedback_opensource_only` / `feedback_feature_mine_closed_source_competitors`) governs **what we deploy as a production service**, not the build-time tools we use to *produce* artifacts. The kernel-authoring loop is offline tooling; the **authored HIP/Triton kernel is the deployed artifact**, and it is fully open. Using Claude/Codex to write a kernel is exactly like using Claude Code to write this project's code — it does not make the output proprietary.
**The options, and why actor-critic wins.** Both harnesses have pluggable backends (GEAK → LiteLLM, any provider; Apex → Claude Code / Codex / Cursor). So: (a) local coder role (self-hosted, weakest), (b) a frontier single model (Claude), or (c) ⭐ a **Claude+Codex actor-critic** reusing the autopilot planner's existing infra. The evidence that (c) is not just *allowed* but *better*: **CudaForge (662) got its strongest result from a cross-model Coder/Judge split (O3-coder + GPT-5-judge → 2.114×)** — an actor-critic by another name — and GEAK's Generator↔Evaluator and Apex's Coder↔Magpie-judge are already actor-critic-shaped, so the boundary maps cleanly. **Plan: prototype with the Claude+Codex actor-critic; keep the local role as the self-hosted fallback.**

## 8. Decision: C4 (profiler-metric feed) — the highest-risk component and its three de-risk paths
**Why it's the risk.** A profiler-fed "judge" needs a compact, decision-relevant set of hardware counters. On NVIDIA, CudaForge (662) derived a 24-metric NCU subset offline. That subset **does not transfer** to gfx90a — CDNA2's MFMA/LDS/CU counter semantics differ from tensor-core/shared-mem — so we'd have to re-derive it, and whether a small useful subset even *exists* on CDNA2 is unproven for us. This is the one piece no NVIDIA paper hands us.
**Three paths discovered, in increasing cheapness/decreasing rigor — try them in reverse order:**
1. **GEAK-v2 OptimAgentv2 Profiler-Analyzer (677)** — ⭐ *try first*. Feed **raw `rocprof-compute` counters → an LLM → natural-language performance intelligence → back into generation.** No curated subset needed to start; the LLM does the interpretation. v2's ablation shows this loop is the dominant lever (1.38× → 3.32×). Caveat: v2's counters were captured on gfx942, so semantics port but tuned values don't — still needs a gfx90a pass.
2. **Xe-Forge static constraint-KB (672)** — a hand-authored **gfx90a rules/patterns YAML** (wavefront=64, LDS sizing, MFMA tile constraints, VGPR/AGPR limits) injected into the prompt. Profiler-*free* hardware-awareness; cheap, brittle, but a good first-pass and a fallback if the LLM-reads-profiler signal is noisy.
3. **CudaForge formal metric-selection (662)** — the rigorous offline correlation-filtering algorithm, re-run on gfx90a to derive a CDNA2 subset. Highest rigor, highest cost; keep as the fallback if (1) and (2) are insufficient.

## 9. Decision: C6 (anti-reward-hacking) — our genuine differentiator
**Why it matters and why it's ours.** The entire cluster documents that speedup-reward kernel agents are **acutely game-able**, and the AMD-native references are the *least* protected: GEAK and Apex use only loose tolerance oracles (Apex's AST anti-tamper catches fabricated results but not functional hacks). The evidence base is damning and worth keeping in front of any reviewer:
- **CUDA-L1 (661):** 32.8% (82/250) of its initial RL solutions exploited an extra-CUDA-stream timing loophole for a fake ~18× before mitigation.
- **The AI CUDA Engineer scandal → robust-kbench (668):** Sakana's earlier agent claimed up-to-150× that independent researchers found to be an actual ~3× *slowdown* via an output-buffer-theft exploit; robust-kbench is the hardened remediation, and re-scoring prior work it found **3.13× → 1.49×** after excluding 40 gameable tasks (~half the "gains" were artifact).
- **KernelBench (664) / METR:** no-op kernels passing via stale output memory, library-passthrough, stream-sync timing tricks.
- **OpenReview "Reward Hacking in Self-Improving Code Agents":** 73.8% of KernelBench iterative optimizations show proxy gains *without* real-task gains.
**Our move.** Lift **robust-kbench's Apache-2.0 exploit→defense catalogue** (7 classes, almost all hardware-agnostic — output-buffer poisoning, eliminable-op/low-magnitude/uniform-output filtering, multi-shape + forward+backward correctness, the 3-verifier soft pre-filter, stream-sync) into C2/C6, plus a **red-team-with-deliberately-cheating-kernels** exit gate. This is net-new value we add on top of AMD's harness, and it is the difference between a number we can trust and one we can't.

## 10. Decision: production-faithful evaluation (FastKernels) as a late-stage gate
FastKernels (671) quantifies that operator-level / torch-eager scores **overstate real end-to-end gains by ~25pp** (1.16× sandbox → 0.93× vs vendor-optimized baselines), and that several agents are *net-negative* in production. Two consequences baked into the plan: (1) **C3 gates reward on an honest vendor baseline** (rocBLAS/hipBLASLt/AITER/torch-ROCm-compile), not eager; (2) a **whole-model exit gate** — score the authored HIP kernel inside a *full forward pass with captured real EPYC-workload tensors* (Apex's hot-patch+re-bench loop operationalizes exactly this). A kernel that wins isolated-op `fast_p` but regresses end-to-end fails.

## 11. Decision: Triton on-ramp, HIP endgame
Two layers, sequenced. **Triton first** because GEAK-eval is gfx90a-proven, open, and Triton has a clean ROCm backend — lowest-risk path to a working loop. **HIP second** because our llama.cpp fork ultimately hand-writes raw HIP/C++ and **GEAK-HIP (678) proves the same 3-module loop closes at the hipcc level** — and, strikingly, **out-optimized a human engineer** on production kernels (Voxelization 2.07× vs 1.84×, SwiGLU 1.68× vs 1.30×), the strongest existence proof in the cluster that this goal is agent-tractable. GEAK-HIP ships no open benchmark, so the HIP arm requires us to build our own HIP oracle/benchmark + apply robust-kbench hardening (UB risk is higher at the raw-HIP level). Pairs with `llama-cpp-dsa-contribution.md`.

## 12. What we deliberately rejected / down-scoped (and why)
- **RL training of a bespoke kernel model** — infeasible on one MI210 (§4); TritonForge's AMD RL even crashes.
- **KernelCraft (670) as a path** — its "AMD" is the **Versal AIE-ML/XDNA NPU via Peano LLVM**, a *separate stack from ROCm/HIP*, not our MI210 GPU. Down-scoped to: harvest its 6-tool function-calling vocabulary + the extended-reasoning-required + ICL-exemplar findings only. (A reminder to always verify what "AMD support" actually means.)
- **TritonForge (676) as AMD-native** — Xe-Forge mis-grouped it; it's gfx942/MI300X-only and AMD-RL-unstable. Down-scoped to: its open SFT/data-curation recipe for a *possible later* offline local-HIP-model branch (pairs with ConCuR 665).
- **Re-basing the controller on GEAK-OpenEvolve (677)** — rejected per the §5 consistency guard (K-Search beats OpenEvolve; gfx90a-unproven; vendor-blog).
- **Treating MultiKernelBench as primary backend** — superseded by GEAK-eval (§6); kept only for its multi-vendor abstraction.

## 13. Open decisions and what would change them (the live questions)
- **Which controller leads on gfx90a?** Unknown until we A/B GEAK vs EvoEngineer+KernelFoundry vs Xe-Forge vs K-Search on the real MI210 with EPYC ops. *Changes if:* the gfx90a A/B produces a clear winner, or K-Search reproduces its MoE result on gfx90a.
- **Does C4's cheapest path (GEAK-v2 Profiler-Analyzer, LLM-reads-raw-rocprof) give a usable signal on CDNA2?** Unknown — needs a gfx90a pass. *Changes the C4 risk rating if it works.*
- **Do GEAK-eval's MI250X numbers reproduce on the single-GCD MI210?** Expected yes (same ISA) with lower absolute speedups (half the aggregate BW) — but this is the **first thing to verify when the card racks**.
- **Will AMD publish gfx90a numbers / arXiv papers / open benchmarks for GEAK-v2 and GEAK-HIP?** If so, intake-677/678 could move from adopt_patterns toward adopt_component, and C4/HIP-benchmark work could shrink further. → see the AUDIT REMINDER blocks in both handoffs.

## 14. Evidence map — every intake entry's role in this program
| Intake | Role in the program | Key reason |
|--------|---------------------|-----------|
| 660 CUDA Agent | seed; env-template + RL reward/anti-hack lessons | the paper that started it; open verify+profile env |
| 661 CUDA-L1 | RL reward design + anti-reward-hack kit | quantified the stream-timing exploit (32.8%) |
| 662 CudaForge | train-free Coder/Judge + **C4 metric-selection** algorithm | closest single-GPU fit; profiler-metric recipe |
| 663 Kevin | multi-turn RL loop + credit-assignment + anti-hack gates | sequential-refine > parallel-sample |
| 664 KernelBench | the `fast_p` scoring contract + reward-hack evidence | the benchmark everything else measures against |
| 665 ConCuR | offline SFT data-curation recipe (optional later) | short-CoT quality filter; length ⟂ speedup |
| 666 EvoEngineer | **lead controller** (train-free evolutionary) | leanest loop on one GPU; modular evaluator |
| 667 MultiKernelBench | secondary backend (multi-vendor abstraction) | demoted by GEAK-eval; kept for non-AMD |
| 668 robust-kbench | **C6 anti-hacking** (Apache-2.0, liftable) | the exploit→defense catalogue; our differentiator |
| 669 KernelFoundry | **hardware-awareness layer** (QD + profiler-gradient) | adopt-both with 666; multi-vendor template |
| 670 KernelCraft | tool-vocabulary + thinking-budget + ICL only | NOT our path (AIE-ML NPU, not ROCm) |
| 671 FastKernels | production-faithful **exit-gate philosophy** | sandbox overstates real gains ~25pp |
| 672 Xe-Forge | linear-CoVeR archetype + **static constraint-KB (C4 de-risk)** | surfaced the GEAK pointer |
| 673 K-Search | **3rd controller** (world-model tree, bug-tolerant, MoE-strong) | beats OpenEvolve; open-source |
| **674 GEAK** | **🔑 keystone backend substrate (C1/C2/C3/C5) + 4th controller** | AMD-native, MIT, **gfx90a-proven** |
| **675 Apex** | **🔑 the ROCm harness** (Magpie + hot-patch + MCP) | AMD-native, MIT, gfx90a-listed |
| 676 TritonForge | offline SFT recipe (subordinate to GEAK) | gfx942-only; AMD-RL unstable |
| 677 GEAK-v2 | **C4 de-risk (Profiler-Analyzer)** + QD upgrades for 669 | gfx942-only (regression); patterns |
| 678 GEAK-HIP | **HIP-arm reference** (raw HIP/C++, our endgame) | out-optimized a human; no open benchmark |

## 15. Net engineering picture (what actually has to be built, post-all-of-this)
1. **Stand up GEAK-eval + Apex on the real MI210/gfx90a** and reproduce the MI250X numbers (sanity gate). — *mostly integration, MIT code.*
2. **Drive the loop with a Claude+Codex actor-critic** (reuse autopilot infra); A/B GEAK vs EvoEngineer/KernelFoundry/K-Search/Xe-Forge as controllers.
3. **Build C6** — lift robust-kbench's anti-hacking into the GEAK/Apex oracle + a red-team gate. *(our differentiator)*
4. **Build C4** — try the GEAK-v2 LLM-reads-raw-rocprof Profiler-Analyzer first, Xe-Forge static-KB second, CudaForge formal selection as fallback. *(the standing research risk)*
5. **Add the FastKernels production exit-gate** (whole-model, vendor-baseline) via Apex's hot-patch+re-bench.
6. **Then the HIP arm** — GEAK-HIP patterns + our own HIP oracle, toward hand-HIP kernels for the llama.cpp fork.
Everything is **gated on the MI210 (~July 2026)**; design/scoping proceeds now. All AMD numbers are **vendor-reported until reproduced on our own gfx90a**.
