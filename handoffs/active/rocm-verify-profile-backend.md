# ROCm Verify/Profile/Benchmark Backend for MI210 Kernel Authoring

**Status**: SKELETON — design scaffold; substrate is now mostly *adopt AMD-native*, not build-from-scratch
**Created**: 2026-06-03 · **Updated**: 2026-06-03 (GEAK keystone reversal + AgentKernelArena)
**Categories**: hardware_optimization, benchmark_methodology, tool_implementation, inference_serving
**Hardware gate — SATISFIED 2026-07-02**: AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB) is racked; ROCm 6.2 bind-mounted; llama.cpp HIP build verified on gfx90a (`progress/2026-07/2026-07-02-mi210.md`). This backend is now **ACTIVE** (priority MEDIUM). Runnable first tasks: (1) install/pin `pytorch-triton-rocm` matched to ROCm 6.2 + verify gfx90a matmul (intake-760); (2) stand up `rocprof-compute` gfx90a metric subset (C4); (3) the honest-vendor-baseline candidates that are gfx90a-*reachable* — **BitBLAS/TileLang low-bit GEMM** (intake-497/tilelang-puzzles), **NOT AITER** (gfx942-only, intake-759). All runs operator-approved (P-GPU-1). [was: "~July 2026; nothing executes until the card racks" — stale]
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
- [x] **Pre-hardware prep (now).** Pin GEAK / GEAK-eval / Apex / AgentKernelArena repos to paper-matching commits, inspect licenses, and draft a split ROCm + torch-ROCm environment recipe ✅ 2026-07-29. Source pins and the no-execution activation order are recorded in [deep-dive §10](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md#10-pre-hardware-source-pins-and-deferred-environment-recipe-2026-07-29): GEAK v1 `v1.0.0` is Apache-2.0 (not the old MIT label); Apex is MIT; AgentKernelArena is Apache-2.0; GEAK-eval has no project-level license at its paper-era snapshot, so its code is **no-reuse pending resolution**. GEAK v1 (`triton==3.1.0`) and GEAK-eval (`triton==3.3.0`) require isolated environments. No install, server, benchmark, GPU/ROCm workload, or production-kernel action is authorized by this closure.
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
Same `gfx90a` predicts **compile compatibility, not performance equivalence** — reproduce every AMD number on the MI210 before trusting it (GEAK-v1 carries the only gfx90a *evaluation*; GEAK-v2/HIP/AgentKernelArena publish gfx942 numbers only — but GEAK **v4** retains first-class gfx90a *knowledge*, amended 2026-08-03 in [`agentic-rocm-kernel-authoring.md`](agentic-rocm-kernel-authoring.md)). **Run the GEAK-family freshness sweep (deep dive §9) at each audit.** All intake-674–679 AMD numbers are vendor-reported until reproduced on our own gfx90a (`feedback_classify_eval_failures_by_reason`, observe-before-diagnosing).

## C4 is blocked on TOOL AVAILABILITY, not only on metric selection — 2026-08-03 (research-intake Stage-2b)

The C4 row above is scored HIGH risk for "CDNA2 counter taxonomy unproven". That is only half of it:
**the profilers themselves are absent.** `rocprofv2`, `rocprof` and `omniperf` were all missing as of
2026-07-20 ([`mi210-big-model-and-acceleration-roadmap.md:205`](mi210-big-model-and-acceleration-roadmap.md));
`rocprof` v1's SQ/TA counters read zero on this box and it aborts at init on graph-enabled builds;
`rocm-bandwidth-test` is not installed; and QuixiCore's timing recipe — otherwise worth copying — assumes
`rocprofv3`, also absent.

**This is a regression, not a contradiction.** Two other files record successful `rocprofv2` runs on
2026-07-04, sixteen days earlier, so something changed on the host between those dates. Recording it as a
chronology rather than as an inconsistency is the point: the earlier runs are still valid evidence, and
the fix is a host action (reinstall/re-pin), not a re-litigation of which file is right.

### CLOSED 2026-08-03 — tooling side-loaded, and the CDNA2 counter taxonomy is PROVEN

- [x] **`rocprofv2`, `rocprof` (v1) and `rocm-bandwidth-test` are available** ✅ 2026-08-03. Version-matched
  to ROCm **6.2.0-66** exactly — a mismatched profiler against a 6.2 runtime is a defect generator, so the
  match is load-bearing, not incidental. Activate with:
  `source /mnt/raid0/llm/tools/rocm-profilers-6.2/env.sh`
- [x] **`SQ/TA/TCC` counter taxonomy for gfx90a is no longer unproven** ✅ 2026-08-03: **465 distinct
  counters across 12 blocks**, enumerated on our own card. All seven counters our MI210 work already cites
  are present — `SQ_INSTS_VALU`, `SQ_BUSY_CYCLES`, `SQ_VALU_MFMA_BUSY_CYCLES`, `GRBM_GUI_ACTIVE`,
  `TCC_HIT_sum`, `TCC_MISS_sum`, `TCC_EA_RDREQ_sum`. Full listing:
  `/mnt/raid0/llm/tools/rocm-profilers-6.2/evidence/gfx90a-counters-20260803.txt`
- [x] **Per-block simultaneous-collection limits captured** ✅ 2026-08-03 — the constraint a C4 pass must
  schedule around, and the reason a naive collect-everything run silently drops counters:
  `SQ 8 · SPI 6 · TCA 4 · TCC 4 · TCP 4 · CPC 2 · CPF 2 · GRBM 2 · TA 2 · TD 2`

**Installed by EXTRACTION, not by `apt install`, and the distinction is deliberate.** `/opt/rocm` is a
bind mount of the host's `/opt/rocm-6.2.0`, shared by four live GPU servers and three FROZEN kernel trees
running three different ggml generations. An apt install would write into that shared tree and could pull
dependency upgrades of ROCm runtime libraries underneath a production server — the exact silent-breakage
mode the `LD_LIBRARY_PATH` discipline exists to prevent. The packages were `dpkg -x`-extracted to
`/mnt/raid0/llm/tools/rocm-profilers-6.2` (19 MB); **nothing outside that directory was modified** and
reversal is `rm -rf`.

Two incidental findings worth keeping: `libpciaccess.so.0` was **absent from this container entirely**
(our own handoff had recorded "add `/usr/lib/x86_64-linux-gnu` to `LD_LIBRARY_PATH`" as the fix — but the
library was not there to find), and `rocprofv2` derives its ROCm root from its own `argv[0]` rather than
from `$ROCM_PATH`, so the prefix needs a mirrored `.info/version`. Both are handled in `env.sh`.

- [ ] **Re-score the C4 risk row from HIGH.** "No usable gfx90a signal" and "no profiler installed" were
  aliasing; the second is now resolved and the first is newly testable. The taxonomy exists and is rich —
  what remains unproven is whether an LLM can read it usefully, which is the actual C4 question
- [ ] `omniperf` extracted but **not runnable** — needs a Python venv (`astunparse`, `colorlover`, …).
  Deferred deliberately: our chosen C4 path is GEAK-v2's LLM-reads-raw-`rocprof`, so omniperf is a
  fallback, not the critical path. Reopen if the raw-counter path fails
- [ ] **Standing caveat unchanged by any of this**: `rocprof` v1's SQ/TA counters read ZERO on this box and
  it aborts at init on graph-enabled builds. Use `rocprofv2`
- [ ] Having the tool does **not** authorize profiling a live server. GPU runs remain operator-approved and
  co-residency is owned by whoever owns the inference

## C6 monitor design — five rules from a sabotage/sandbagging red-team (intake-979; 2026-08-03)

_Via `/research-intake` Stage-2b. C6 is our named differentiator and it had no design for the case where
the agent **underperforms deliberately** rather than cheats. All five are prompt- or plumbing-level and
cost essentially nothing._

**Why this reaches kernel work at all** — the observed sandbagging strategies map straight onto our
domain. Verbatim from the source: *"agents might train their models on a needlessly small subset to
avoid supposed memory issues, or use small and few layers for their CNNs."* Kernel analogues:
conservative tile/block sizes justified by "LDS pressure", disabled fast paths justified by "numerical
safety", low unroll factors justified by "register spills". **Each is individually defensible — which is
exactly why they evaded the general monitor.**

- [ ] **Give the monitor the WHOLE SEARCH TREE, not the selected candidate.** Best-path-only transcripts
  structurally advantage a saboteur (the authors say so). Hand the monitor every evaluated variant
  **including discarded higher-scoring ones** — otherwise a candidate that quietly discards its own best
  result is invisible. This is a plumbing requirement on the journal, not a prompt change
- [ ] **Name the threat model in the monitor prompt.** Largest measured effect in the study: a generic
  "is this suspicious?" monitor **rarely fires** on sandbagging; the threat-specific one "performs well"
- [ ] **Aggregate.** Mean over monitor models ≈ the best single monitor (0.993 vs 0.970); mean@k over
  repeated samples of one model also improves AUC with fast diminishing returns. Cheap on our stack
- [ ] **Assume monitor-awareness.** Every monitor scored higher AUC on unaware runs, universally. Any
  agent that can read the loop's config knows it is monitored — design for the aware case
- [ ] **Preserve CoT visibility.** Hidden reasoning tokens are described as a "large advantage to the
  agent"; a monitor reading only final outputs is the weak configuration
- [ ] **Declare an explicit FPR budget rather than claiming safety** — *"gaining strict safety guarantees
  may require prohibitively high false positive rates."* A C6 layer with no stated FPR is not a gate
- Secondary signal available free: attempting sabotage **reduced main-task performance** for both
  scaffolds in the study — a measurable tax usable as corroboration
- **Cite the qualitative sandbagging finding, never a number**: the AUCs live only in a plot legend that
  is not text-extractable from either the PDF or the HTML render (NOT-FOUND-IN-SOURCE)


## Auto-kernel revival — research-intake integration 2026-07-22 (C6 + task-contract from OpenHyra/HyRA)
_Via /research-intake Stage-2 (intake-884 HyRA, intake-885 OpenHyra). OpenHyra effectively implements the C6 anti-reward-hacking differentiator this backend owns but never built._
- [x] Build C6 (reward-integrity) from OpenHyra's proven design: a trusted evaluator OUTSIDE the sandbox recomputes score on an immutable snapshot (self-reported numbers ignored); anti-TOCTOU snapshot (O_NOFOLLOW, reject symlink/FIFO/multiply-linked, size cap, chmod 0444, SIGKILL the candidate process-group BEFORE snapshot; OpenHyra `sandbox.py:80-134,255`); correctness-gate evaluated BEFORE latency (HyRA SOL-ExecBench `is_correct` precondition). This is the anti-cheating-kernel gate this handoff notes GEAK/Apex leave loose ✅ 2026-07-22
- [x] Adopt the SOL-ExecBench task/scoring schema {entry_point kernel.py::run, target_hardware, dependencies, hard is_correct gate, sol_score, latency_ms} as the C5 task contract, and OpenHyra run-manifest provenance (sha256 sources+task+evaluator + resume-drift rejection; `provenance.py:72-157`) as the attestation format binding each kernel measurement to MEASUREMENT.md ✅ 2026-07-22

### Follow-up discovered during C6 implementation — 2026-07-22
- [ ] The C6 harness (`scripts/kernel_rnd/c6_reward_integrity.py`) Linux sandbox (bwrap/unshare+RLIMIT) **fails closed** and is bypassed via `allow_unsandboxed` only because the devcontainer lacks bwrap/user-namespaces (it is itself the isolation boundary). Before real MI210 kernel-authoring runs, verify a working sandbox backend on the host and remove the unsandboxed override there.
