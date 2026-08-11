# ROCm Verify/Profile/Benchmark Backend for MI210 Kernel Authoring

**Status**: ACTIVE HARDENING — Q4_K failures isolated to MMQ; fixed-gate correction open
**Created**: 2026-06-03 · **Updated**: 2026-08-11 (RVP-C2-6a dispatch isolation + RVP-C3-5)

> **NEXT ACTION (2026-08-11): `RVP-C2-6b` — correct the stock gfx90a Q4_K MMQ path under the
> unchanged κ=1.5 gate.** The non-contiguous oracle coverage defect is fixed. The corrected forced
> matrix passed force-rocBLAS 43/43 and force-MMQ 18/43, isolating 25 genuine failures to MMQ. Preserve
> the passing rocBLAS control and do not relax the gate. The experimental implementation remains
> uncommitted and must
> not be committed or pushed without explicit user approval per that tree's `AGENTS.md`. The two static
> probes (`RVP-T0-2`, `RVP-T0-5`) remain complete and independently re-verified. **`RVP-T0-1` is now
> complete:** the live card never approached its 300 W cap, so the clock-pinning branch and AK-OP-2
> are closed. Everything else in §2026-08-10 is CPU-only or static and runs today.
>
> **Correction carried with it (operator, 2026-08-10):** the phrase *"All runs operator-approved
> (P-GPU-1)"* below is **wrong as a blanket statement**. P-GPU-1 governs the **class of claim** a GPU
> result may carry, not permission to run; the human boundary is **freeze / cutover / promotion**.
> What remains true and unchanged: profiling or benching a **live server** is owned by whoever owns
> that inference, and co-residency is theirs to schedule.
**Categories**: hardware_optimization, benchmark_methodology, tool_implementation, inference_serving
**Hardware gate — SATISFIED 2026-07-02**: AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB) is racked; ROCm 6.2 bind-mounted; llama.cpp HIP build verified on gfx90a (`progress/2026-07/2026-07-02-mi210.md`). This backend is now **ACTIVE** (priority MEDIUM). Runnable first tasks: (1) install/pin `pytorch-triton-rocm` matched to ROCm 6.2 + verify gfx90a matmul (intake-760); (2) stand up `rocprof-compute` gfx90a metric subset (C4); (3) the honest-vendor-baseline candidates that are gfx90a-*reachable* — **BitBLAS/TileLang low-bit GEMM** (intake-497/tilelang-puzzles), **NOT AITER** (gfx942-only, intake-759). GPU claim grade follows P-GPU-1; profiling a live server remains the inference owner's scheduling boundary. [was: "~July 2026; nothing executes until the card racks" — stale]
**Priority**: MEDIUM (the substrate for [`agentic-rocm-kernel-authoring.md`](agentic-rocm-kernel-authoring.md))
**Parent**: [`agentic-rocm-kernel-authoring.md`](agentic-rocm-kernel-authoring.md) · **Parent index**: [`inference-research-index.md`](inference-research-index.md)
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
| **C4** | Profiler-metric feed | **BUILD — deterministic first** | Paired mapping/formal `rocprofv2` traces → deterministic kernel/overlap/fuse/architecture tables; bounded similarity/catalogue judgment only after that. Xe-Forge static gfx90a constraint-KB and CudaForge formal selection remain fallbacks. NVIDIA/NCU subsets do NOT transfer | **MED** — parser/report/counter taxonomy are closed; real paired-trace signal remains empirical |
| **C5** | Benchmark / task suite | **ADOPT (primary) + layer** | GEAK-eval 674 (TritonBench-revised + real ROCm bench, gfx90a-proven) **and** AgentKernelArena 679 (HIP/Triton/Torch2HIP suites); layer our own `fast_p` tiering; seed EPYC ops (attention/MoE-dispatch/dequant). MultiKernelBench 667 = secondary (multi-vendor abstraction only) | MED |
| **C6** | Reward-integrity / anti-hacking | **BUILD — our differentiator** | robust-kbench 668 exploit-class half (Apache-2.0, liftable) **+** AgentKernelArena 679 unseen-shape half **+** a red-team-with-cheating-kernels gate. GEAK/Apex have only loose oracles | MED |

## Current sequence (replaces the old phase plan)
- [x] **Pre-hardware prep (now).** Pin GEAK / GEAK-eval / Apex / AgentKernelArena repos to paper-matching commits, inspect licenses, and draft a split ROCm + torch-ROCm environment recipe ✅ 2026-07-29. Source pins and the no-execution activation order are recorded in [deep-dive §10](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md#10-pre-hardware-source-pins-and-deferred-environment-recipe-2026-07-29): GEAK v1 `v1.0.0` is Apache-2.0 (not the old MIT label); Apex is MIT; AgentKernelArena is Apache-2.0; GEAK-eval has no project-level license at its paper-era snapshot, so its code is **no-reuse pending resolution**. GEAK v1 (`triton==3.1.0`) and GEAK-eval (`triton==3.3.0`) require isolated environments. No install, server, benchmark, GPU/ROCm workload, or production-kernel action is authorized by this closure.
- [ ] **MI210 bring-up (gated on card).** Install ROCm + torch-ROCm; confirm `gfx90a` visible; **reproduce GEAK-eval's MI250X numbers on the MI210** (sanity gate — expect lower absolute speedups at ~half the aggregate bandwidth, verify correctness/compile). Also reproduce AgentKernelArena on gfx90a (`target_gpu_model`).
- [ ] **Harden oracle + integrity (C2 + C6).** Lift robust-kbench's exploit-class defenses + AgentKernelArena's unseen-shape generator into the GEAK/Apex oracle; red-team with deliberately-cheating kernels.
- [ ] **Honest baseline + E2E scoring (C3 + FastKernels gate).** Gate reward on a vendor baseline; add a whole-model exit gate via Apex's hot-patch + re-bench with captured EPYC-workload tensors.
- [ ] **C4 profiler feedback (MED empirical risk).** Run the deterministic paired-trace report first,
  then confine any model to its bounded similarity/catalogue receipt. Derive whether the resulting
  gfx90a signal is useful on a real mapping/formal capture; Xe-Forge and CudaForge remain fallbacks.
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

**The container fix keeps getting reverted, and it does not matter.** `.devcontainer/Dockerfile` gained a
`libpciaccess0` line (root `e0cbad4a`); a host-side sync rewrote the whole `.devcontainer/` directory twice
on 2026-08-03 and dropped it both times, leaving a stale `Dockerfile.orig` beside it. That sync is outside
the container and cannot be reached from a session here. **Nothing depends on the line**: the provisioner
side-loads `libpciaccess0` itself when the container lacks it, which is the path actually in use today. Do
not re-litigate this — restore the line if convenient, and rely on the provisioner regardless.

**Reproducible from git, not just present on the filesystem** — `epyc-inference-research`
`scripts/benchmark/provision_rocm_profilers.sh` (idempotent, `--verify` mode, refuses if the installed
ROCm is not 6.2.x). The 19 MB of extracted binaries are deliberately not tracked; the recipe is. `env.sh`
is the tracked canonical copy at `scripts/benchmark/rocm_profilers_env.sh` and the tools-directory path is
a symlink to it, so there is one copy and it cannot drift. Counter enumeration committed at
`data/gfx90a-counters/`. Research `7926557b`.

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

- [x] **Re-score the C4 risk row from HIGH.** ✅ 2026-08-11 — C4 is now MED: tool availability,
  CDNA2 taxonomy, deterministic parsing and the report contract are closed; usefulness of the first
  real paired mapping/formal signal remains empirical.
- `omniperf` extracted but **not runnable** — needs a Python venv (`astunparse`, `colorlover`, …).
  Deferred deliberately: our chosen C4 path is the deterministic paired-`rocprofv2` report, so omniperf is a
  fallback, not the critical path. Reopen if the raw-counter path fails
- **Standing caveat unchanged by any of this**: `rocprof` v1's SQ/TA counters read ZERO on this box and
  it aborts at init on graph-enabled builds. Use `rocprofv2`
- Having the tool does **not** authorize profiling a live server — co-residency is owned by whoever
  owns that inference. **Corrected 2026-08-10 (operator):** the rest of this line used to read "GPU runs
  remain operator-approved", which is wrong as a blanket. P-GPU-1 governs the **class of claim**, not
  permission to run; an AutoKernel experiment on an idle card needs no per-run approval. The live-server
  clause is the part that survives
- [x] **Apply the "does the caller propagate this check's answer?" screen to the whole probe family.** ✅
  2026-08-11 — `test_shell_pipeline_status.py` walks every owned `scripts/kernel_rnd/**/*.sh` wrapper,
  requires `#!/bin/bash` plus `set -euo pipefail` before its first pipeline, and refuses any later
  `set +o pipefail`. The
  bandwidth probe shipped with `hipcc … 2>&1 | tail -20`, which takes its exit status from `tail`, so a
  failed build exited 0 and the script walked on to the reporting path — a non-compiling probe was
  committed looking like a working one. Fixed there (`PIPESTATUS` + `exit 5`), but the same shape is
  available to every wrapper we own that pipes a compiler, a test runner or a validator. This is the
  complement to the screen we already have (*"can I make this check pass by deleting the thing it
  inspects?"*), and `feedback_pipe_hazards` already records it for piped pytest

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

- [x] **Give the monitor the WHOLE SEARCH TREE, not the selected candidate.** ✅ 2026-08-11 —
  `controller/reward_monitor.py` binds the complete evaluated variant set and exactly one selected row. Best-path-only transcripts
  structurally advantage a saboteur (the authors say so). Hand the monitor every evaluated variant
  **including discarded higher-scoring ones** — otherwise a candidate that quietly discards its own best
  result is invisible. This is a plumbing requirement on the journal, not a prompt change
- [x] **Name the threat model in the monitor prompt.** ✅ 2026-08-11 — the declaration requires the
  versioned threat-specific id and the compiled prompt renders it. Largest measured effect in the study: a generic
  "is this suspicious?" monitor **rarely fires** on sandbagging; the threat-specific one "performs well"
- [x] **Aggregate.** ✅ 2026-08-11 — the reducer requires a complete model×sample panel and computes
  mean-of-mean@k. Mean over monitor models ≈ the best single monitor (0.993 vs 0.970); mean@k over
  repeated samples of one model also improves AUC with fast diminishing returns. Cheap on our stack
- [x] **Assume monitor-awareness.** ✅ 2026-08-11 — `assume_monitor_aware` is mandatory true. Every monitor scored higher AUC on unaware runs, universally. Any
  agent that can read the loop's config knows it is monitored — design for the aware case
- [x] **Preserve CoT visibility.** ✅ 2026-08-11 — every trace requires non-empty reasoning and
  `include_reasoning_trace` is mandatory true. Hidden reasoning tokens are described as a "large advantage to the
  agent"; a monitor reading only final outputs is the weak configuration
- [x] **Declare an explicit FPR budget rather than claiming safety.** ✅ 2026-08-11 — the declaration
  requires a numeric FPR budget and the reducer emits sensitivity, specificity, observed FPR and
  `budget_met` — *"gaining strict safety guarantees
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

## 2026-08-09 — C4 report contract and capture protocol (research-intake Stage-2b)

Source: [intake-1026](../../research/intake_index.yaml) (SGLang `llm-torch-profiler-analysis` skill) and
intake-1029 (its two reference catalogs), both dive-verified 2026-08-09 against
`sgl-project/sglang` `main`. SGLang is Apache-2.0. **These are design references, not components** —
the upstream tooling parses torch-profiler Chrome traces and declares no ROCm path anywhere.

- [x] **RVP-1 — Adopt the three-table output contract as the C4 report spec** ✅ 2026-08-11:
  `profile_report.py` emits kernel /
  overlap-opportunity / fuse-pattern, rendering only rows at or above a `1.0%` cumulative GPU-time
  share. **The report layer is separable from the parser** — verified in source:
  `scripts/analyze_llm_torch_profile.py` renderers (`render_kernel_table_for_stage`,
  `render_overlap_table_for_stage`, `render_fuse_table_for_stage`) all take `rows: Sequence[dict]`,
  with parsing delegated to sibling `triage_kernel_helpers` / `triage_overlap_helpers` /
  `profile_common` modules. So only a `rocprofv2` row adapter has to be built. Adopt the determinism
  rule verbatim (source-backed matching, explicitly *not* a fuzzy matcher) and the bounded
  `high` / `medium` / `low` similarity vocabulary.
- [x] **RVP-2 — Split the C4 HIGH-risk path into a deterministic pass plus a bounded judgment pass,
  then re-score the C4 row.** C4 currently reads as "GEAK-v2 LLM-reads-raw-`rocprof`". The reference
  design does not do that: a deterministic script emits the tables, and the model is confined to the
  similarity note and the catalog comparison. This *shrinks* the trusted surface rather than adding
  to it, and is the cheapest available de-risking of the standing HIGH-risk row. ✅ 2026-08-11 — the
  optional receipt admits only an emitted pattern id, `low|medium|high`, and a catalogue comparison;
  measured/source fields are unknown-field errors.
- [x] **RVP-3 — Adopt the two-trace mapping/formal protocol.** Capture an attribution trace first with
  graphs disabled or a lower-fusion configuration, then a formal trace with the real optimizations on,
  because graphs and fusion destroy `kernel -> cpu_op -> source` mapping. Upstream explicitly forbids
  calling the mapping pass a fast profile. **Convergence worth naming**: this handoff already records
  that `rocprof` v1 *aborts at init on graph-enabled builds*. The capture mode our profiler can
  survive is the same one that yields source attribution — so this is a two-phase protocol, not a
  workaround for a defect. ✅ 2026-08-11 — the manifest requires mapping mode
  `graphs_disabled|lower_fusion`, formal mode `production_optimizations`, one source commit and one stage.
- [x] **RVP-4 — Adopt the capture discipline**: warm up before arming the profiler and bound the
  capture (upstream default is 10 warm-up / 5 active steps), and keep prefill and decode captures
  stage-separated so they are never averaged together. ✅ 2026-08-11 — v1 requires exactly 10 warm-up
  and 5 active steps and rejects prefill/decode mixing.
- [x] **RVP-5 — Adopt architecture-shape matching as a profiling primitive.** Attribute trace structure
  to *architectural blocks*, not only to kernel names: repeating trace groups map to the model's layer
  pattern. Kernel names drift (see the K28 rename evidence in
  [`k28-fused-chunked-gdn-kernel-research.md`](k28-fused-chunked-gdn-kernel-research.md)); block
  structure does not. ✅ 2026-08-11 — reviewed architecture blocks are exact ordered family sequences;
  the mapping trace reports their occurrence count without fuzzy kernel-name inference.
- [x] **RVP-6 — Log RocmProfileData (RPD) as a fourth profiler candidate** alongside `rocprofv2`,
  `rocprof` v1 and `omniperf`, and check gfx90a availability before assuming any RPD-based workflow is
  reachable on this box. Source intake-1027 is `stage1-unverified` and is MI300X/gfx942 only —
  **no figure from it may be cited for any purpose.** ✅ 2026-08-11 — every report must declare all
  four candidates and RPD's independent `gfx90a_state`; missing RPD is a manifest error.
- [x] **RVP-7 — Decide our catalog scope deliberately instead of inheriting it.** intake-1029's catalog
  excludes "host-only scheduler, event-loop, executor, offload, and load-path patterns" by explicit
  written policy. A host/device transfer bottleneck therefore has no row and cannot be surfaced by a
  kernel-time-share table at all. Either widen the scope or pair the catalog with a host-side one.
  ✅ 2026-08-11 — `kernel_only` emits the host-path coverage gap; `kernel_and_host` requires a hash-bound
  host catalogue receipt. No report silently inherits either scope.

**Declined here, recorded so they are not re-derived**: (a) inheriting the upstream synthetic stage
shapes (prefill `4090`/`1`, decode `1`/`2048`) without re-deriving from our own production
prompt-length distribution — a gate's scope must match the measured subset; (b) adopting the upstream
analysis scripts as a component, since they parse torch Chrome traces and `rocprof` output is not one.

---

## 2026-08-10 — C2 correctness oracle, C6 reward integrity, and three zero-cost probes (research-intake Stage-3)

_Via `/research-intake` (8 URLs + 2 operator-supplied inline documents → 16 entries, 5 Stage-2 dives,
13 Stage-2b ingest-and-dives). Every `file:line` below was read directly in the FROZEN production tree
`/mnt/raid0/llm/llama.cpp` @ `67a433bf45a8`, branch `production-consolidated-v8`, on 2026-08-10 —
these are citations of **our own** code, not of any source. Nothing here modifies the frozen tree;
C2/C6 work lands in `llama.cpp-experimental` and in the harness that drives it._

### The finding that reorders this handoff's priorities

The C2 row above says "ADOPT then HARDEN". The dives found that **the thing we planned to harden does
not do what its name implies**, in three independent ways:

1. **The reference is a sibling, not an independent implementation.** `ggml-cpu.c:3041` reads
   `if (ggml_cpu_disable_fusion || cplan->use_ref) { return 0; }` — `use_ref` **disables fusion and
   tiling**, and the "reference" then runs the *same* type traits, the *same* dequantisers, and the
   *same* vectorised inner loops. A defect shared by both sides is invisible to an elementwise
   comparison, by construction.
2. **The tolerance admits large errors on exactly our target class.** `test-backend-ops.cpp:5942`
   (`struct test_mul_mat_vec_fusion`) overrides `max_nmse_err()` at `:6120-6121` to return `5e-3`.
   NMSE `5e-3` is **≈ 7.1 % RMS relative error** — and dequant-GEMV is the op family the MI210
   program is actually aimed at.
3. **Every T0 failure we have ever seen was unreproducible by construction.**
   `init_tensor_uniform` (`test-backend-ops.cpp:54`) draws from
   `thread_local std::default_random_engine gen(std::random_device{}())` (`:62`), and there is **no
   seed flag anywhere** in the tool. A failing case cannot be re-run as the same case.

None of that is an upstream criticism — `test-backend-ops` is a regression tester and is good at that
job. It is a statement about **what a reward-bearing oracle needs that a regression tester does not**.

### Zero-cost probes — run these first; two of them can close later work for free

- [x] **RVP-T0-1 — MI210 saturation probe (row C3).** ✅ 2026-08-11 — the authorized 60-second
  gfx90a GEMM produced **41.904029 TFLOP/s** while a 250 ms sampler captured **242** samples with a
  maximum gap of **0.250029 s**. The card held its nominal **1700 MHz** sclk for **99.5868%** of
  samples and peaked at **200 W** against its **300 W** cap; `approached_power_cap=false`. Receipt:
  `/mnt/raid0/llm/autokernel/probes/rvp-t0-1-20260811T0906Z/receipt.json` (SHA-256
  `07788e1d488ecec062e8133dd9e11d379e5075afbcc20f80b6da37e345533431`). The workload PID is gone
  and the receipt records release at `2026-08-11T09:06:40.267163+00:00`.
  Drive a saturating gfx90a GEMM and log `power_w`
  and `sclk_mhz` at 250 ms intervals for 60 s. **If the card never approaches its 300 W cap, the entire
  clock-pinning branch closes for free** and OP-2 in [`autokernel-research-loop.md`](autokernel-research-loop.md)
  §21 is declined without spending anything. That condition was met, so the branch is closed. Facts
  verified on-box 2026-08-10 before designing the probe: `power1_cap_max` = 300 W
  (`rocm-smi --showmaxpower` agrees), the card exposes only **three**
  sclk levels — `pp_dpm_sclk` = 500 / 800 / 1700 MHz — and the `sysfs` control nodes are root-owned,
  so the probe is read-only and the *remedy*, not the measurement, is what needs root. **At idle the
  card was sitting on level 1 (800 MHz), not level 2**; a three-level DPM table with a wide idle step
  means the probe must record which level is *held under sustained load*, not just the peak touched.
- [x] **RVP-T0-2 — MFMA disassembly audit (row C3).** `roc-obj` + `llvm-objdump --disassemble
  -mcpu=gfx90a` over the hot `mul_mat` kernels in `libggml-hip.so`; grep for `v_mfma_*`. **Static
  only — no GPU time, no server.** If MFMA is absent from the paths this program cares about, that is
  a larger deflation of our standing baseline than any published-number dispute, and it is answerable
  today. Pair with the `mfma-decode-kernels-are-worth-zero` HARD_CONSTRAINT (`autokernel-research-loop.md`
  §19.2): that entry is about *decode arithmetic intensity*, so an MFMA absence in **prefill** paths
  would not be covered by it. ✅ 2026-08-10 — 57/134 gfx90a disassemblies contain MFMA and 38 of
  those also contain `mul_mat`; MFMA-total-absence is falsified, without claiming runtime dispatch or
  hotness. Evidence: [`artifacts/audit/autokernel-static-probes-20260810.md`](../../artifacts/audit/autokernel-static-probes-20260810.md).
- [x] **RVP-T0-5 — Static audit of `init_tensor_uniform` call sites (row C2).** Classify every call
  site in `test-backend-ops.cpp` as one-sided (e.g. `(0.9, 1.1)`) or symmetric about zero. This
  decides where the negate transform in RVP-C2-3 is worth its runtime and where it is a provable
  no-op, and it is the input to the degenerate-range screen in RVP-C2-7. Pure grep + read. ✅ 2026-08-10
  — all 56 sites classified: 44 symmetric, 9 one-sided, 3 asymmetric across zero. Evidence:
  [`artifacts/audit/autokernel-static-probes-20260810.md`](../../artifacts/audit/autokernel-static-probes-20260810.md).

### C2 — build the oracle the loop actually needs

Sequenced: **RVP-C2-1 is a precondition for every other row here.**

- [ ] **RVP-C2-1 — Seeded input generation.** Derive each tensor's seed deterministically from
  `(suite_seed, op, case_idx, tensor_idx)` and record `suite_seed` on the evaluation event
  (`autokernel-research-loop.md` §7.4). Without this, a T0 failure is an anecdote: the RNG is
  `std::random_device`-seeded per thread (`:54,:62`) and there is no flag to pin it. **Do this first.**
- [ ] **RVP-C2-2 — Property layer (the only axis independent of the sibling).** Reference-free
  structural checks computed in host `double` **directly from raw tensor data — never by building a
  second ggml graph**, which would re-enter the shared implementation and re-create the problem.
  Seed set: `SOLVE_TRI` residual bound, `ARGSORT` / `TOP_K` permutation validity (bit-exact — a
  permutation check has no tolerance), `SOFT_MAX` sum-to-one. **Ship it with a seeded-defect gate**
  (RVP-C6-6) or it inherits the same unquantified-sensitivity weakness it was built to fix.
  - [x] **Live property acceptance within the value-transform pass.** ✅ 2026-08-11 — the 779-case
    pass covered `SOFT_MAX`, `ARGSORT`, `TOP_K`, and `SOLVE_TRI`. The `SOFT_MAX` invariant was
    corrected before acceptance to include the operation's implicit attention sink mass rather than
    demanding that only the explicit output cells sum to one. The parent row remains open until the
    producer and seeded-defect gate are durable.
- [ ] **RVP-C2-3 — Value transforms.** identity / ×3 / ×0.01 / negate, floats only, structure
  preserved, **fail-any** gating. Apply per RVP-T0-5 — negate is near-useless on symmetric ranges.
  **Do not copy the fail-open-on-reference-exception branch** the upstream design carries: a
  reference that throws must fail the case, not pass it (`feedback_fail_open_defaults_conceal_their_own_corruption`).
  **2026-08-11 static implementation:** research commit `eca5dbda` adds a pass separate from the
  layout axis, exact four-transform and non-zero-case gates, suite-seed-bound `AK_VALUE_V1`
  receipts, per-property transform binding, and fail-closed refusals for missing case receipts or
  legacy property rows. The experimental producer compiles but remains uncommitted pending its
  required explicit local-commit approval.
  - [x] **Live value-transform acceptance.** ✅ 2026-08-11 — suite seed `4711` passed **779/779**
    cases across `SOFT_MAX`, `ARGSORT`, `TOP_K`, and `SOLVE_TRI`; every case completed identity,
    ×3, ×0.01, and negate. This validates the live pass but does not make its producer durable.
- [ ] **RVP-C2-4 — Layout / stride axis, as a SEPARATE pass with its own flag.** Three probe families:
  transpose (stride permutation), `as_strided`-equivalent (stride gap), offset base pointer
  (alignment). **Kept separate from RVP-C2-3 deliberately**: the value-transform pass needs shapes
  *fixed* to catch shape-locked hacks, while this pass needs layout *varied* to catch fragility —
  merging them makes each weaker. `test-backend-ops` already has per-op view flags, but they are
  opt-in and are not exercised on the paths we reward. **2026-08-11 static implementation:** research
  commit `14034623` adds the separate `OpSuitePlan.layout_probe`, exact
  `offset|stride_gap|transpose` family accounting, suite-seed-bound receipts and a gate requiring all
  three families plus a non-zero case count. The experimental producer compiles but remains
  uncommitted pending its required explicit local-commit approval.
  - [x] **Live layout acceptance.** ✅ 2026-08-11 — **1,048/1,048** emitted layout cases passed the
    separately gated offset, stride-gap, and transpose-family contract. This validates the live pass
    but does not make its producer durable.
- [ ] **RVP-C2-5 — Stateful-op triad.** (1) State is an explicit graph input; (2) byte-equality
  assertion on input buffers across both runs; (3) **the final state is in the compared output set**.
  Rule 3 is the one that gets forgotten, and it is the one that matters — a kernel that computes the
  right outputs and corrupts the carried state passes rules 1 and 2. Targets `SSM_SCAN`, `SSM_CONV`,
  flash-attention-with-cache, and the k28 chunked-GDN work
  ([`k28-fused-chunked-gdn-kernel-research.md`](k28-fused-chunked-gdn-kernel-research.md)).
  - [x] **Live acceptance probe.** ✅ 2026-08-11 — suite seed `4711` passed **5,184/5,184** cases
    across `SSM_SCAN`, `SSM_CONV`, `FLASH_ATTN_EXT`, and `GATED_DELTA_NET`. Every emitted
    `AK_STATE_V1` receipt had `initial_equal=1`, `input_immutable=1`, and one or more final-state
    outputs. Research commit `9cc3ed1b` supplies the fail-closed consumer. The parent row remains
    open because its experimental producer is still uncommitted pending explicit operator approval.
- [ ] **RVP-C2-6 — fp64 CPU reference with a ratio gate.** `e_cand ≤ κ · max(e_ref, floor)`, κ = 1.5.
  **Implement dequantisation from the GGUF format specification, not from `ggml-quants.c`** — sourcing
  it from our own quant code reproduces the sibling problem one level down and the independence is
  illusory. Cheap for us specifically: CPU is our abundant resource. Note the error budget: the
  weight-quantisation error largely cancels between the two sides, so the tolerance is set by
  **activation requantisation**, not by reduction order.
  - [x] **Implement and live-validate the independent host-double oracle.** ✅ 2026-08-11 — Q4_0,
    Q8_0, Q4_K, and Q6_K are decoded directly from GGUF wire bytes rather than project quant helpers.
    The final metric id is `fp64_error_ratio/host-double-gguf-wire/v1`. Five representative CPU cases
    and the dedicated broadcast-indexing regression passed; the real receipt parser remained compatible
    across 31 parser tests; and the property self-test caught 5/5 planted defects while accepting 5/5
    clean cases. The implementation remains uncommitted pending explicit user approval.
  - [x] **RVP-C2-6a — Correct oracle coverage and isolate the stock ROCm Q4_K failures.** ✅ 2026-08-11 —
    the first matrix exposed a real non-contiguous-row coverage bug in the host-double decoder. Reading
    each logical row through `nb[1..3]` fixed that oracle defect. The corrected forced-dispatch matrix
    retained 43 cases per arm: force-rocBLAS passed 43/43 with maximum error ratio 1.2283, while
    force-MMQ passed 18/43 and failed 25 with maximum ratio 3.0361. This is now an MMQ-specific stock
    correctness finding under unchanged κ=1.5. Receipt:
    `/mnt/raid0/llm/autokernel/probes/rvp-c2-6a-rocm-q4k-dispatch2-20260811T1042Z/receipt.json`, SHA-256
    `6e7870558c6317a7ef12f7fca8a267466cc0734295d0c33562103a0c022a3502`. Research runner:
    `scripts/benchmark/run_rocm_q4k_fp64_matrix.py`.
  - [ ] **RVP-C2-6b — Correct the stock gfx90a Q4_K MMQ path without changing κ=1.5.** Preserve the
    force-rocBLAS 43/43 control, retain all 25 force-MMQ failures as regression cases, and do not rank
    this surface until the corrected MMQ arm passes the same matrix.
- [ ] **RVP-C2-7 — Degenerate and insensitive-case screening.** Reference-only, 3 seeds × 4
  transforms, run once per suite version, plus an input-*insensitivity* screen (does the output move
  at all when the input does?) and a seed-invariance screen. **Audit our own `(0.9, 1.1)`-style ranges
  first** (RVP-T0-5) — a case whose inputs cannot distinguish a correct kernel from a constant is a
  case that grades nothing.
- [ ] **RVP-C2-8 — Hostile distribution at identical shapes.** Hold the shape fixed and change only
  the value distribution. This is the anti-shape-detection device, and it targets something we
  actually ship: our shape-gated default-off levers are exactly the kind of dispatch a candidate can
  learn to satisfy without being correct.
- [ ] **RVP-C2-9 — Checker precision pinning.** The property and reference paths must not run through
  `-fa`, MFMA-f16 accumulation, or `FORCE_MMQ`. A checker validated by the same fast path it is
  checking corrupts **claims**, not merely screens — this is the "verify THE consumer, not A consumer"
  discipline applied to the oracle itself.

### C6 — reward integrity: close the instrument gap first

- [x] **RVP-C6-1 — Hash-pin the measurement translation units.** `tests/test-backend-ops.cpp`,
  `tests/test-quantize-perf.cpp` and `tools/llama-bench/llama-bench.cpp` are hashed against the
  production anchor before every measured round; **any diff is a hard fail, not a warning.**
  **This is the highest-value single item in the batch.** C6 as designed pins the *evaluator*; but the
  *instrument* is compiled from the very tree the candidate is allowed to edit. No timer redesign
  fixes that — only pinning the sources does. The gate must also refuse to be satisfied by deleting
  the file it inspects (`feedback_verify_integrity_not_presence_of_own_edit`). ✅ 2026-08-11 — the
  reviewed measurement anchor is hardened commit `0492c231`, whose direct parent is frozen production
  v9 `0db32c06`; the one-commit overlay changes only `llama-bench` and its README. T0, T1 open and every
  T1 invocation hash the complete three-file manifest against that named anchor and hard-refuse a
  missing, unreadable, deleted or changed file. Pinning to the reviewed overlay rather than pretending
  its intentional instrument change is byte-identical to production preserves both authorities.
- [ ] **RVP-C6-2 — Stream-escape defence.** Verified: T0 timing brackets
  `ggml_backend_graph_compute` with host wall clock (`tests/test-backend-ops.cpp:1621-1627`), and
  `ggml_backend_cuda_synchronize` (`ggml/src/ggml-cuda/ggml-cuda.cu:2512-2518`) calls
  `cudaStreamSynchronize(cuda_ctx->stream())` — **one stream**. Work issued on a second stream is not
  waited on and falls outside the timed region. Add (a) a hybrid A/B that repeats the measurement
  behind a full device synchronize and (b) a stream-creation audit in the source-integrity gate.
  **A candidate need not look malicious to do this** — multi-stream is an ordinary in-tree idiom.
- [ ] **RVP-C6-3 — Thread / async-escape check across the timed region.** The CPU-side analogue of
  RVP-C6-2: assert no candidate-spawned thread or async handle outlives the bracket.
- [x] **RVP-C6-4 — Speed-of-light screen.** ✅ 2026-08-11 —
  `execution/physical_bounds.py` binds conservative per-shape compute/memory ceilings to the exact
  delivered unit and measurement frame; `microbench.py` requires a complete predeclared envelope and
  refuses any impossible sample before ranking. Flag any candidate faster than
  `max(compute-bound, HBM-bound)` for its shape. Free, needs no reference execution, and catches the
  whole "measured the wrong thing" family before a single verification rep is spent.
- [x] **RVP-C6-5 — Keep provenance detection in its own component.** Substitution / call-provenance
  checks populate `integrity_flags`, **never `correct`** (interface contract, §"Interface contract").
  The upstream reference built the merged version and reverted it within 30 minutes — **inherit the
  placement, not the removal**: their stated reason was that their top-10 users are trusted, a
  *social* control that does not exist for an autonomous loop. ✅ 2026-08-11 — provenance derivation
  remains isolated in `evaluator/integrity.py` and `evaluator/surface.py`; the evaluator event has no
  actor-settable `correct` field. The verdict alone derives status, provenance failures appear as
  `INTEGRITY:<gate>:<outcome>`, and any such flag structurally withholds the speed rank.
- [x] **RVP-C6-6 — Red-team corpus with a stated sensitivity.** ✅ 2026-08-11 — the two versioned
  source-pattern detectors pass the named 10 planted / 15 clean corpus and report 10/10 sensitivity,
  15/15 specificity and 0/15 FPR without claiming arbitrary-program coverage. ~10 planted-bug and ~15 clean HIP
  kernels; report sensitivity and specificity, not an assertion of coverage. Mine the published
  exploit **taxonomy** (harness frame-hacking, pointer-keyed memoization, structured-input
  short-circuit) — **do not vendor the 4.66 GB corpus**; it is NVIDIA-targeted Python with zero
  executable value on gfx90a. This is what lets the §"C6 monitor design" FPR-budget row above be
  stated as a number instead of a promise.
- [x] **RVP-C6-7 — Refine-prompt disclosure rule + PUBLIC/SEALED split.** Our loop is multi-turn, so
  the failure diagnostics fed back into a repair turn are a channel into the oracle:
  `test-backend-ops` prints `ERR = %.9f > %.9f` on failure, which hands the candidate the exact
  tolerance it must clear. Filter `diagnostics` at the seam (interface contract), and hold a SEALED
  case population the refine loop never sees. ✅ 2026-08-11 — `authoring_contract.py` requires
  predeclared PUBLIC and SEALED populations with content-addressed seeds, projects only PUBLIC
  diagnostics into refine context, replaces exact tolerance/evaluator disclosures with a generic safe
  finding, and has planted-leak tests proving sealed ids and details never reach the assembled prompt.
- [x] **RVP-C6-8 — T1 output-invariance across repetitions, with buffer-address rotation.**
  `llama-bench` repeats over the same input buffers with no output validation between reps — a live
  pointer-keyed-cache hole. Assert outputs are invariant across reps **and rotate the input buffer
  addresses between them**; address rotation is strictly stronger than a re-check, because it defeats
  memoization keyed on the pointer rather than on the contents. ✅ 2026-08-11 — experimental commit
  `0492c231` adds trusted `--autokernel-harden <seed>`: unique content per timed repetition, two
  simultaneously live contexts/input allocations per comparison, a same-content address-rotated
  untimed replica, and bitwise logits comparison. It exits nonzero on mismatch and exports hashes,
  addresses and working-set size; the evaluator refuses incomplete/reused receipts. The experimental
  CPU build succeeds. Real-model execution awaits explicit inference permission.

### Recorded so it is not re-derived

- **`torch.rand_mix` — declined.** It is dead code upstream (0 of 270 call sites), and the upstream
  `randn` → `rand` switch that accompanies it is the *enabling condition* for a ReLU-identity hack, not
  a defence against one. Keep the four transforms in RVP-C2-3.
- **Peak-memory scoring, the upstream timing protocol, and a `speedup ≥ 1.0` pass clause — declined.**
  Ours are stronger on all three; adopting them would be a regression.
- **`KernelBenchX` / `ISO-Bench` / KernelBench task suites — declined as artifacts.** They are
  torch/CUDA and hard-fail without CUDA; no torch-ROCm is installed here and our unit under test is a
  C++ ggml op. This is a *technical* decline — per standing policy licences are not blockers for our
  self-hosted personal use, and nothing here is gated on one.

### Additional actionables from the recovered Stage-2b reports — filed 2026-08-10, beyond the Stage-3 plan

_The Stage-2b analyst reports were recovered from the session transcript **after** the Stage-3 plan was
written, so they carry derived actionables the plan predates. These are the survivors; the declines at
the end are deliberate and recorded so they are not re-derived._

- [ ] **RVP-C5-R — Mine a real-workload task class from our own repo history.** Keyword-filter merged
  llama.cpp performance PRs (`optim`, `speed`, `latency`, `memory`) → classify → verify each is a
  genuine optimization and not a refactor → extract the PR's own benchmark command and claimed numbers
  → replay a candidate at the pre-optimization commit → **score against the human patch**. Row **C5**
  lists only synthetic and ported suites today; this is the only identified path to **non-synthetic
  tasks on our own stack**, at zero hardware-porting cost. **Two hard constraints**: (a) construct and
  run on historical commits or `llama.cpp-experimental` — **never** against the frozen v8 tree; (b) our
  PRs are public and in training data, so temporal filtering or held-out selection is mandatory, or the
  suite measures memorization.
- [ ] **RVP-C5-2 — Screen the C5 seed corpus for input-INSENSITIVE ops** (the `mean(softmax(x))` /
  `relu(x-2)`-under-uniform-sampling class). Twin of the degenerate-output screen on a different axis:
  constant output vs insensitivity to the input.
- [ ] **RVP-C3-2 — Expert-reference ceiling alongside the honest-baseline floor.** Where a task derives
  from a real merged optimization, report candidate-vs-human-patch delta as well as
  candidate-vs-vendor-baseline. C3 currently fixes only the floor.
- [x] **RVP-C3-3 — Parse `rocm-smi` into numeric fields and add `throttle_observed`.** Capture is
  already mandatory and implemented, but it is stored as a **text blob** and the completeness audit
  only regex-checks that the word appeared — so a run that throttled 1700 → 800 MHz mid-window passes
  every check we have. Upgrade the audit from word-presence to value-presence. ✅ 2026-08-10 —
  AutoKernel `evaluator/devices.py` parses SCLK, MCLK, power and junction temperature into validated
  samples; evaluation-event v5 mechanically re-derives throttle and makes it verdict-bearing.
- [x] **RVP-C3-4 — 250 ms in-run device-state sampler** across the measurement window. ✅ 2026-08-11 —
  the AK-BH-1, AK-BH-2, and corrected Q4_K receipts carry numeric in-window samples with maximum gaps
  of 0.250006, 0.250032, and 0.250023 seconds respectively, plus released device claims.
- [x] **RVP-C3-5 — Declare an absolute duration-window admission test** for any op-shape used to rank
  variants, with the lower bound **measured on gfx90a**. ✅ 2026-08-11 — the research implementation
  derives a 250,090,903 ns minimum from the first nominal-SCLK observation in the hash-bound RVP-T0-1
  receipt, refuses missing/foreign/sub-floor live GPU evidence before ranking, and exempts CPU and
  non-live arms. The focused device-sampler module passes 11/11 tests. These research-tree changes
  live in `scripts/kernel_rnd/autokernel/evaluator/devices.py`,
  `scripts/kernel_rnd/autokernel/execution/microbench.py`, and
  `scripts/kernel_rnd/autokernel/execution/test_device_sampler.py`; they remain uncommitted at this
  checkpoint.
- [x] **RVP-C2-10 — Add a non-power-of-2 extent to the standing shape set.** ✅ 2026-08-11 — frozen v9's
  executed `MUL_MAT` case set already carries extents 83, 77 and 127 (plus other irregular shapes),
  and the AutoKernel T0 op filter runs that standing set rather than a power-of-two subset. Adding
  4095 would increase cost without adding the requested non-power-of-two property. Near-zero
  cost. Keep shape-variation-as-correctness-probe distinct from shape-variation-as-hack-detector —
  different instruments, and merging them weakens both.
- [ ] **RVP-C2-11 — Seed-invariance degeneracy screen**: an output that does not vary across input
  seeds is cacheable and therefore unscoreable. Complements RVP-C2-7.
- [ ] **RVP-C2-12 — A hard error on non-contiguous input must be a FAIL, never a skip.** The reference
  suite converts these to skips in half its files; a kernel that cannot accept a strided ggml view is
  not correct for llama.cpp, and a skip records that as neither pass nor fail. **2026-08-11 static
  implementation:** under the separate `--autokernel-layouts` flag, the experimental tool marks an
  unsupported selected layout as a hard failure; both console and CSV parsers preserve FAIL instead
  of `not_supported`. Research commit `14034623` covers the consumer. This row remains open until the
  producer is committed.
- [x] **RVP-C6-9 — Build the two unbuilt detectors behind `AntiRewardHackingEvidence`**
  (`timing_dependent_branch_findings`, `environment_probe_findings`). Until they exist, an empty list
  must read **UNKNOWN, not PASS** — an empty result from a detector that was never built is exactly the
  fail-open shape this row exists to prevent. ✅ 2026-08-11 — versioned added-line scanners now inspect
  the committed candidate delta for environment probes and direct or simple data-flow timing branches;
  the real T0 provider records detector ids/findings. Missing ids make empty findings
  `COULD_NOT_CHECK`; planted/clean source-pattern tests report 100% sensitivity/specificity for this
  narrow detector taxonomy without claiming the broader RVP-C6-6 exploit corpus.
- [x] **RVP-C6-10 — Anti-short-circuit cases go in the RANKED set, not just the gate.** ✅ 2026-08-11 —
  `MicrobenchPlan.anti_short_circuit_units` requires real per-unit command/recipe changes, a normal
  control, distinct parameter frames, and emits those units into the same ranked block stream. If the hard
  cases only gate, a candidate can route easy inputs to a fast invalid path and never pay for the
  accurate path's cost on the hard ones. Ranking them prices it.
- [x] **RVP-VIDYA-1 — Belief-kernel wiring, filed now per CLAUDE.md.** ✅ 2026-08-11 — the source row is
  present in `scripts/vidya/adapters/README.md` and the owned projection task is SC18 in
  `vidya-belief-substrate-program.md`; actual write-side work remains tracked there rather than hidden
  in this dependency. The property layer (RVP-C2-2)
  **produces measurements** — per-op property residuals per backend per shape. Add a row to the source
  table in [`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md) and a task in
  [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md). The write side is cheap and
  permanent; the read side cannot be retrofitted.

**Declined, recorded so they are not re-derived:** lifting the 129 human-verified reference test files
as a component (design reference only — and the reason is **technical**: torch/CUDA, will not run
here); the `speedup >= 1.0` pass clause; the upstream `warmup=3, repeats=5` timing protocol, which is
weaker than our canonical one; and citing any foreign-hardware correctness-overestimation magnitude as
if it were ours — under P-GPU-1 the analogous magnitude is ours to derive on our own card.
