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
| Model | closed Seed-1.6 / DeepSeek-V3 / QwQ-32B | our coder/architect role or a frontier coding API | this handoff |

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
When the MI210 racks: **(1)** stand up **GEAK-eval on gfx90a** and reproduce the MI250X numbers on our MI210 (sanity gate); **(2)** run the **GEAK agent** (or Apex's pipeline) driven by our **local coder/architect role** as the agent backend (opensource_only — both are pluggable); **(3)** harden the loose GEAK/Apex correctness oracle with **robust-kbench (668)** (C6) before trusting any speedup; **(4)** keep EvoEngineer / KernelFoundry / K-Search as alternative controllers to A/B against GEAK once the backend is live. RL training and LoRA distillation stay deferred.

### Correction logged (intake-676 TritonForge)
Xe-Forge grouped TritonForge as AMD/ROCm-targeted; the deep-dive found its AMD support is **gfx942/MI300X (CDNA3) only — not our gfx90a/MI210** — and its AMD RL path crashes. It is **AMD-secondary, subordinate to GEAK**; useful only for its open SFT/data-curation recipe (offline local-model branch, pairs with ConCuR 665) and as corroboration that Triton's ROCm backend is a real on-ramp.

### Follow-up candidates (updated; GEAK family is now the priority)
- **GEAK-v2** — GEAK-OptimAgentv2 (evolutionary, +9.76% / avg 3.32×) + GEAK-OpenEvolve (QD, avg 3.42×, up to 11.23× per kernel); evaluated on MI300X/MI325X, **not yet gfx90a**. Blog-stage; watch for an arXiv ID.
- **GEAK-HIP** — extends GEAK from Triton to **HIP-level** kernels (our llama.cpp fork ultimately wants hand-HIP, so this is directly on-path). Blog-stage.
- (Superseded as top pointer: GEAK itself, now ingested as intake-674.) NPUEval (2507.14403) only if AMD AIE/XDNA ever enters scope.
