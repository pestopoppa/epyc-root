# ROCm Verify/Profile/Benchmark Backend for MI210 Kernel Authoring

**Status**: ACTIVE HARDENING — phase-explicit rocprof landed; real decode and C3/C5 capture remain
**Created**: 2026-06-03 · **Updated**: 2026-08-12 (phase-explicit attribution repair)

> **NEXT ACTION (2026-08-12): after terminal-noncomplete INF-03 r17 cleanup, run the governed real-model
> decode attribution in RVP-C4-4a, then capture the real EPYC C3/C5 workload evidence.** OP-11 was
> resolved as Option B (decline for now), so C2-7/C2-8/C2-9 remain deliberately open unless the
> operator explicitly reopens the experimental producer. The research reducers/runners remain
> durable; the old oracle-integrity smoke remains non-evidence.
>
> **Evidence-authority boundary (2026-08-12):** RVP-T0-1 and its v9 replication are durable
> hardware-saturation diagnostics, and AK-BH-1/2/3 plus AK-LN-2/AK-X-5a are durable bounded
> diagnostic receipts. Their retained hashes and commands support those local findings, but the set
> does not uniformly bind a committed clean source checkout and complete build manifest. Do not use
> it as current AutoKernel calibration authority. Establish clean hardened-instrument provenance
> first, then run frozen-v9 controls, the full-host CPU IQK campaign, and the matched archive/evaluation.
>
> **Correction carried with it (operator, 2026-08-10):** the phrase *"All runs operator-approved
> (P-GPU-1)"* below is **wrong as a blanket statement**. P-GPU-1 governs the **class of claim** a GPU
> result may carry, not permission to run; the human boundary is **freeze / cutover / promotion**.
> What remains true and unchanged: profiling or benching a **live server** is owned by whoever owns
> that inference, and co-residency is theirs to schedule.

- [x] **RVP-AUD-1 — Audit diagnostic receipt durability versus source/build provenance.** RVP-T0-1,
  AK-BH-1/2/3, and AK-LN-2/AK-X-5a retain their bounded findings; missing clean source/build identity
  is now explicit and blocks their use as AutoKernel campaign authority. ✅ 2026-08-12
- [x] **RVP-AUD-2 — Reconcile implemented C3/C6 rows against current research main.** ✅ 2026-08-12 —
  clean detached research `26ca88dc` revalidated `microbench.py`, `physical_bounds.py`,
  `reward_hack_scan.py`, `devices.py`, `oracle_integrity.py`, and the generated import footprint at
  **408 tests + 15 subtests PASS**. This confirms RVP-C6-2/3/4 and RVP-C3-4/5. That audit correctly
  reopened RVP-C6-6/10 because their static detector corpus and ranked-unit machinery did not satisfy
  the empirical acceptance text; the later executable gfx90a r3 receipt below closes both rows.
  RVP-C2-8/9 also remain open: their reducers and claim-aware runners are complete, but OP-11 declined
  the committed seeded producer needed for fresh matched evidence. No implementation-only test
  upgraded empirical authority.
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
- [x] **MI210 base bring-up and one-task AgentKernelArena compatibility.** ✅ 2026-08-11 — ROCm,
  torch-ROCm, Triton and physical `gfx90a` were identity-checked; the live add task compiled, passed
  correctness 3/3 and timing 5/5, and released the claim. The preflight honestly records
  `external_type_dispatch_present=false`, so this does not claim the full vendor launcher ran.
- [ ] **Reproduce GEAK-eval's published MI250X task/result on the MI210.** Run the paper-era task and
  candidate through the pinned vendor launcher, expecting lower absolute speedup at roughly half the
  aggregate bandwidth; distinguish source compatibility from result reproduction. **External gate
  re-audited 2026-08-11:** paper pin `a85e657f` and current upstream `453b0218` have no project-level
  license; GitHub reports `license: null`, the license endpoint is 404, and PyPI 0.1.5 declares no
  license expression. Licensed GEAK-v1 and AgentKernelArena do not contain the paper-era MI250X
  harness/task. Per the pinned source-prep policy, no reproduction may run until AMD-AGI publishes a
  covering project license or explicit grant. No cached checkout or GPU claim was used in this audit.
- [ ] **Harden the remaining producer-dependent C2 oracle surfaces.** C2-7/C2-8/C2-9 reducers and
  runners are durable, but their sensitivity/hostile/checker-isolation evidence waits on OP-11's
  experimental producer identity.
  - [x] **Bind the three reducer outputs into verdict-bearing source-candidate T0 authority.** ✅
    2026-08-12 — research `d8013a6c` requires measured, hash-bound sensitivity,
    hostile-distribution, and checker-isolation evidence tied to the exact candidate source,
    evaluator bundle, suite version, producer, and evidence object. Missing or dry-run evidence and
    source/evaluator drift yield `COULD_NOT_CHECK`; parameter candidates cannot smuggle these source
    prerequisites. This completes the consumer authority, not OP-11's producer identity or replay.
- [x] **Build C6 reward integrity.** ✅ 2026-08-11 — immutable external scoring, exploit detectors,
  unseen/hostile shapes, stream/thread escape checks, planted red-team corpus, prompt disclosure,
  output-invariance, and ranked anti-short-circuit cases are implemented and tested.
- [ ] **Honest baseline + E2E scoring (C3 + FastKernels gate).** Gate reward on a vendor baseline; add a whole-model exit gate via Apex's hot-patch + re-bench with captured EPYC-workload tensors.
  - [x] **Compile the exact EPYC C3/C5 evaluation contract and controller/backend seam.** ✅ 2026-08-11
    — the offline research compiler binds HyRA `k228` attention and `k175` MoE to Apex's pinned
    Python/Triton overlay at `e06b5d1`, and binds EPYC-native Q4_K dequant to an immutable
    experimental llama.cpp binary because Apex cannot hot-patch system C++ or monolithic binaries.
    Every case requires an exact captured-tensor surface, honest vendor floor,
    correctness/integrity-first `fast_p`, and a matched whole-model exit; absent evidence is
    `COULD_NOT_CHECK`, never a synthetic score. Plan SHA-256
    `390bd1befe1a3d1eeb1433e579f3fc42d3c1d97ae8e7ccb1b90f059b9a5600ad`; research
    `4320d83a` (research main `5dfd14ad`). The parent remains open for EPYC workload capture, matched
    MI210 timing, candidate integration receipt, and whole-model re-bench.
  - [x] **Separate diagnostic ROCm-provider evidence from bankable llama.cpp integration.** ✅
    2026-08-12 — research `77689f76` gives baseline providers exact versioned manifests and makes
    Apex/standalone-provider bindings diagnostic-only at the whole-model exit. Only a clean,
    production-descended experimental `llama_gpu` commit with bound patch, binary, linkage,
    toolchain, and isolated-prefix identity can satisfy `IntegratedLlamaGpuBinding`. This closes an
    authority-laundering path; it does not perform the still-open EPYC capture or matched re-bench.
  - [x] **Provision the exact Apex/ROCm runtime without contaminating the host stack.** ✅ 2026-08-11
    — Apex is detached at `e06b5d1cd58996a82c5e2897164f760c3b3f87ac`; its time-matched Magpie
    dependency is detached at `2a9263833f71755df2a93b466cdd3a9f803fc625`; and the isolated Python
    3.12 environment carries Torch `2.5.1+rocm6.2`, HIP `6.2.41133`, and Triton `3.1.0`. A physical
    device preflight sees one `gfx90a:sramecc+:xnack-` MI210 with 64 GiB HBM. Apex's blanket registry
    validator currently requires every unrelated AITER/vLLM/SGLang source file before resolving one
    selected entry; the EPYC adapter must validate only its exact selected entry without weakening
    that entry's source pin.
  - [x] **Implement the fail-closed selected-entry Apex adapter.** ✅ 2026-08-11 — research
    `934b2a8d` (main `7e2bcb64`) validates only the separately reviewed selected row while still
    hash-binding the full
    pinned registry, exact Apex/Magpie/source revisions, source/config/model files, Torch/HIP/Triton,
    physical gfx90a identity, and the exact `e06b5d1` runner interface. It preserves `Path`-typed
    runtime fields, refuses a foreign Python/runner origin, binds the three capture outputs, and
    requires explicit inference authorization. The current path intentionally returns typed
    `MissingCaseMapping`: C5 records name `kernel.py::run` solution artifacts, not Apex registry
    entries. `k175` is additionally composite and cannot be laundered through one `kernel_id`; it
    requires a reviewed component-graph/multi-trace extension or an audited whole-composite entry.
    This closes the runtime adapter, not the missing semantic mapping or real capture evidence.
  - [x] **Audit the exact HyRA-to-Apex/AITER semantic mappings.** ✅ 2026-08-11 — the hash-bound
    static audit closes both current C5 rows as typed `StructuralMappingMismatch`, not executable
    maps. `k228` is mathematically adjacent to `aiter.hip.mla_prefill_asm_fwd`, but pinned AITER has
    HSA images only for gfx942/gfx950, no gfx90a object, and lacks reviewed base-2-LSE and split-ABI
    proof. `k175` is an ordered branch-aware router → top8/count/rank → scatter/gather → routed and
    shared experts → weighted undispatch graph; the registry lacks the router, exact biased-top8,
    inverse-map dispatch, shared-expert, weighted-undispatch, and multi-trace contracts. Research
    `a9779163` (main `4fd985c2`); audit SHA-256
    `40edaf2af2cf5b8624b9b0a05e7da137f1034dc25f8b6c2f44faae42faf4652e`. This closes mapping review,
    not EPYC workload capture or the matched whole-model gate.
- [x] **C4 profiler feedback (MED empirical risk).** ✅ 2026-08-11 — the deterministic paired
  `rocprofv2` report produces useful op-level mapping/formal signal, while the governed timestamp-only
  `rocprof` v1 fallback produced whole-model Qwen3.6 GDN attribution at 2K/8K/32K. Model-facing
  similarity/catalogue output remains diagnostic-only. IQ2_XXS's seeded Omniperf replay is tracked
  separately by INF-37/OP-11 and does not reopen the C4 implementation.
- [x] **EPYC-op suite integration.** ✅ 2026-08-12 — research `d8013a6c` binds the exact selected
  `k228` attention and `k175` MoE cases to their hash-pinned C5 references and Torch-ROCm-compile
  floor, and the EPYC-native Q4_K dequant case to the exact operator-ratified frozen-v9 branch,
  commit, reported version, binary/linkage digests, and attestation. Eager or candidate-relative
  baselines, incomplete case sets, and identity drift fail closed. The matched controller A/B and
  real EPYC capture remain owned only by INF-03; this checkbox makes no empirical completion claim.
- [x] **HIP arm minimum loop closure (after the Triton loop works).** ✅ 2026-08-12 — research
  `2c214d48` `controller/hip_authoring_arm.py` admits only a true Torch2HIP task from clean Apache-2.0
  AgentKernelArena `2dbbf1d3`, hashes the task/candidate/toolchain, compiles GPU-blind for gfx90a,
  and uses separate released MI210 claim/sampler windows for the vendor baseline and centralized
  final evaluation. The r4 SiLU receipt compiled and passed 11/11 public correctness and 11/11
  timing-validity cases; root independently re-derives its two producer-authored belief rows. The
  Torch-eager ratio is observation-only and non-rankable; no production or experimental llama tree
  was touched.
- [x] **HIP arm decision-grade hardening.** ✅ 2026-08-12 — research `b8d8c409` adds the sealed
  `hip_decision_grade.py` parent plus a C6-contained worker: candidate source is sealed before the
  24-case hostile suite seed/shapes exist, expected values remain in an independent host-double
  oracle, and two differently poisoned outputs must be fully overwritten and bitwise repeatable.
  The honest C3 provider is the exact one-graph/no-break Torch-Inductor ROCm SiLU expression on the
  same tensor/device. The terminal r6 receipt passed 24/24 cases, all 40 candidate/provider arm
  windows individually cleared RVP-C3-5's 250,090,903 ns gfx90a floor (minimum 276,039,581 ns), and
  measured a 1.076935x median paired speedup over 20 randomized blocks; all block signs were positive
  and the anytime-valid e-process crossed threshold 20 at block 9. Receipt internal SHA-256
  `0ba60558951d47b596abce52ebe41401ae50a1326375595c49dfaf737f902ccb`, file SHA-256
  `c2b7f7ce983ef31ea92d6977450e993c2ae0f4fdf07db595de26caf5341174ab`. This is task-local rankable
  evidence only: it has no release/promotion authority, and an experimental llama integration plus
  whole-model gates remain mandatory before any production proposal. r4 is superseded sub-floor
  instrument evidence; it must not be cited as decision-grade.

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

## Historical C4 tooling block — resolved 2026-08-03 (research-intake Stage-2b)

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
  CDNA2 taxonomy, deterministic parsing and the report contract are closed. The empirical question
  is also answered at op level: hash-bound Q4_K and Q8_0 single-process captures produce complete
  mapping/formal reports, and the report now crosses a diagnostic-only AutoKernel/GEAK/Arena seam.
  Residual MED risk is explicitly scoped: `rocprofv2` exits 139 for whole-model Qwen prefill and
  IQ2_XXS op capture on this host, so those workloads require another profiler or a narrower probe.
- [x] **RVP-C4-1 — Add and exercise a governed whole-model `rocprof` v1 attribution fallback.**
  ✅ 2026-08-11 — `run_autokernel_rocprofv1_attribution.py` binds clean source/binary/model/profiler
  and linkage identities, holds the MI210 claim, samples the device at 250 ms, and captures
  p2048/p8192/p32768 with graphs disabled. GDN summed-kernel shares were **15.397%, 14.649%, and
  12.180%**; optimistic 4x-op full-model ceilings were **11.548%, 10.987%, and 9.135%**. This
  reproduces the earlier ceiling instead of raising it. Receipt:
  `/mnt/raid0/llm/autokernel/probes/k28-rocprofv1-attribution-20260811-r3/receipt.json`, SHA-256
  `981306080a674f89f5ac7f9c7631feef1d31071dacd46329aa983db72e74c5a0`; research integration
  commit `48350b24`.
- [x] **RVP-C4-2 — Add a governed batched-decode target selector for AutoKernel G15.** ✅ 2026-08-11 —
  `run_autokernel_g15_profile.py` binds clean source/binary/model/profiler/linkage identities, exact
  B=64/128 cells, the runner hash, a device claim, and a 250 ms trace. Its deterministic taxonomy
  keeps gather/scatter, recurrent, quantization, layout, position, and runtime copies out of the
  verdict-bearing norm + activation + elementwise share; exact kernel and adjacent-cluster tables
  remain available diagnostically. The admitted r4 receipt passes with 1,035 samples and a maximum
  0.250060 s gap, and falsifies G15 at **1.837% / 1.490%** against its 20% floor. Receipt SHA-256:
  `d7a0c8c257c2a59435b95c39b988485a8283d709d83ef7397b3c67ee7ec8cca9`. Research `0674df51`
  preserves the exact receipt-bound runner SHA; follow-up `4b738fb5` corrects only the per-cell
  hypothesis question label so B=64 no longer says B=128.
- [x] **RVP-C4-3 — Replace the Q4_K Omniperf multi-pass merge with a governed single-pass PMC
  transport.** ✅ 2026-08-11 — Omniperf/rocprof-v1 permuted rows across passes and blocks, so its
  apparent block-1 comparisons were withdrawn. The replacement validates the installed gfx90a
  counter catalogue, collects `SQ_WAVES`, `SQ_INSTS_VALU`, and `SQ_INSTS_VALU_INT32` in one
  rocprofv2 file-plugin pass, requires exact within/across-block invariance, and emits no normalized
  comparison on missing/zero/drifting counters. A predeclared two-attempt ceiling retries only
  transport exit/missing-artifact failures and preserves every attempt. The four-block
  representative-shape r7 matrix passed 12/12 cells and found Q4_K minus same-bit Q4_0 at
  **+112.5 VALU and +35 INT32 instructions/wave** with equal waves. Receipt SHA-256
  `1e34339c1c986413c4eeb1b56ba3202c8763d08df45aba1c0580917c888f5e47`; research
  `70374c43` / main `ac88d75a`. The result is differential-mechanism evidence only; fused unpack
  wall share remains structurally unidentifiable.
  The retained exit-139 attempts are localized to target-process finalization after complete
  correctness rows and CSV flush: an intermittent legacy ROCProfilerV2 preload-stack teardown crash
  in the side-loaded ROCm 6.2 profiler on the unsupported Ubuntu 25.10 / kernel 6.14 host mix. It is
  not a kernel-execution or counter-collection failure. Keep the fail-closed bounded retry; do not
  mask rc139 or accept its otherwise-complete CSV. If this becomes recurring infrastructure, first
  reproduce with core capture in a ROCm-6.2-supported 22.04/24.04 environment, then validate a
  rocprofiler-SDK/rocprofv3 migration on an isolated current stack.
  A later Q4_K candidate diagnostic narrowed one tempting false explanation: two runs with 32/34-byte
  workload identifiers both exhausted their two attempts, but a 13-byte identifier still produced one
  exit 139 followed by a passing retry. Identifier length is therefore not established as causal.
  The existing bounded fail-closed retry remains the correct integration contract; never accept a
  complete-looking CSV from a nonzero profiler exit. Diagnostic receipt SHA-256
  `de4241bd26b77f5dac7df746d165034b67e6f8105133daf0359142a97dd35d5d`.
- `omniperf` 2.0.1 is now runnable through a sealed Python environment and `rocprof` v1. A manual
  IQ2_XXS smoke produced 260 dispatch rows, proving fallback reachability, but is non-evidence. The
  governed fallback runner fails closed because frozen v9 lacks its seeded/repeated producer flags;
  the passing evidence replay waits on OP-11. The deterministic paired-`rocprofv2` report remains C4's
  primary path; Omniperf is the measured IQ2 crash-boundary fallback.
- **Standing caveat, now narrowed**: direct `rocprof` v1 whole-model SQ/TA captures read zero and it
  aborts at init on graph-enabled builds. The Omniperf op smoke had nonzero `SQ_WAIT_ANY` and TCC
  request/miss totals but zero VALU/VMEM/hit fields, so treat it as a partial diagnostic until the
  seeded runner passes; use `rocprofv2` for the established C4 surfaces.
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
- [x] Verify a fail-closed C6 sandbox on the live host and remove the unsandboxed route from real
  kernel-authoring execution. ✅ 2026-08-11 — the campaign path now uses
  `autokernel/execution/sandbox.py`, not the 2026-07-22 `c6_reward_integrity.py` prototype (which has
  no AutoKernel caller outside its regression tests). A scoped `/sys/fs/cgroup/autokernel`
  delegation plus Landlock ABI 6 and seccomp was exercised as uid 1000: an in-tree write succeeded;
  an outside write and evaluator-receipt forgery failed; host signalling and socket creation returned
  `EPERM`; and teardown killed an escaped descendant, proved empty membership, and removed its leaf.
  `execution/provision_cgroup.sh` makes the host prerequisite reproducible after boot. The live path
  has no `allow_unsandboxed`/environment bypass: missing delegation refuses before spawn.

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
  [`k28-fused-chunked-gdn-kernel-research.md`](../completed/k28-fused-chunked-gdn-kernel-research.md)); block
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

**Strict-contract repair and replay (2026-08-11).** Research commit `d7260844` closes four admission
gaps found after the first live captures: the 1% floor now applies to overlap/fuse rows as well as the
kernel table; mapping/formal traces must bind the same workload/source/stage while using distinct
corpus IDs and paths; stage labels are derived from workload semantics; and a host catalogue can no
longer alias the kernel-catalogue hash. Reviewed family-alias sets preserve architecture-shape
matching across declared renames without adding fuzzy matching. The full AutoKernel suite passed
3,972 tests with one declared expected failure.

The first post-repair Q4_K mapping attempt retained a fail-closed `rocprofv2` exit-139 receipt. One
identity-matched retry succeeded with **195 mapping + 195 formal dispatches**, **80** device samples,
and a released MI210 claim. The report declares `kernel_only`, independently records the host gap,
applies the 1% floor, and finds `mul_mat_vec_q` **42.107%**, `quantize_q8_1` **30.457%**, and runtime
fill **27.436%** at the bounded `m=16,n=1,k=256` decode cell. Receipt:
`/mnt/raid0/llm/autokernel/probes/c4-q4k-strict-contract-v9-20260811-r2/receipt.json` (SHA-256
`23f14e71015d21d021b4f6ee6128cd34a52b73f3e756b39e0a47243dd9bb9bfb`). This validates the repaired
contract on gfx90a; it does not claim the tiny cell provides Item B's requested inside-kernel unpack
attribution.

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
  An independently launched same-protocol replication later on 2026-08-11 corroborated the closure:
  **41.879670 TFLOP/s**, **242** samples, **0.250022 s** maximum gap, and **202 W** peak. After the
  initial idle-transition sample, all **241/241** samples held **1700 MHz**; steady-state median/p95
  power was **198/201 W**. Receipt:
  `/mnt/raid0/llm/autokernel/probes/rvp-t0-1-v9-20260811-r1/receipt.json` (SHA-256
  `33b0514a4f2f3ad475c891ca34d46c2faeea241825f5558d68f394401afce17e`). The claim has a recorded
  release timestamp and the post-run device check found no KFD process or VRAM allocation.
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
  A fresh 2026-08-12 corroborating replication under a held MI210 claim produced
  **41.854545 TFLOP/s** over 60.000284 s while the 250 ms sampler captured **242** samples with a
  **0.250023 s** maximum gap. Nominal **1700 MHz** held for **99.5868%** of samples and peak power
  was only **196 W / 300 W**; `approached_power_cap=false`. Receipt:
  `/mnt/raid0/llm/autokernel/campaigns/rvp-t0-1-20260812T0444Z/receipt.json`, SHA-256
  `3ca5f261814bcc27114c15db4480a52496041b3c4c524b3271e5c9f6703da9e1`; the receipt binds the
  workload binary hash and records claim release time. This corroborates the already-closed row and
  does not create a second completion. The clock-pinning branch remains closed.
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
  ([`k28-fused-chunked-gdn-kernel-research.md`](../completed/k28-fused-chunked-gdn-kernel-research.md)).
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
  - [x] **RVP-C2-6b — Correct the stock gfx90a Q4_K MMQ path without changing κ=1.5.** ✅ 2026-08-11 — Preserve the
    force-rocBLAS 43/43 control, retain all 25 force-MMQ failures as regression cases, and do not rank
    this surface until the corrected MMQ arm passes the same matrix. **2026-08-11 diagnostic:** a
    separately compiled force-MMQ DP4A arm reproduced the same 25/43 failures (maximum ratio 3.0178),
    so the defect is not the gfx90a MFMA implementation. It is common to MMQ's Q8 activation staging;
    do not spend the repair on an MFMA-only patch. Receipt:
    `/mnt/raid0/llm/autokernel/probes/rvp-c2-6b-q4k-dp4a-20260811T1300Z/receipt.json`, SHA-256
    `c955f5df4cd584586b0e59746b8dc1e2542fbde57a558de0257ba616dee78021`.
    A second Q4_K-only least-squares refinement of the existing per-32 Q8 activation scale also
    failed 25/43 (maximum ratio 2.8834) while the rocBLAS control remained clean; it was reverted, so
    no source delta survives. Receipt:
    `/mnt/raid0/llm/autokernel/probes/rvp-c2-6b-q4k-ls-scale-20260811T1430Z/receipt.json`, SHA-256
    `476e6fb3fc004b30067ea9de4826a094a90db529c610670673c159e803342d89`.
    Root cause was instead the affine Q4_K reconstruction mixing two activation populations: the
    quantized dot used dequantized Q8 values (`q*d`), while the min-correction used the original
    pre-quantization float sum. The local `quantize.cu` fix derives the min-correction sum from the
    same quantized/dequantized Q8 values for Q4_K DS4, in both ordinary and scatter paths. The final
    default, force-rocBLAS, force-MMQ MFMA, and force-MMQ DP4A matrix passed **172/172** cases with
    zero failures and maximum error ratio 1.2283 under unchanged κ=1.5. Receipt:
    `/mnt/raid0/llm/autokernel/probes/rvp-c2-6b-q4k-qsum-final-20260811/receipt.json`, SHA-256
    `355bdcf169cb8682d2f56e1754b321f770a0fe3c0bbc5f6e1dc58eaffb443fb2`. The source fix remains
    uncommitted and approval-gated; this row closes the diagnosis and live correction, not promotion.
- [ ] **RVP-C2-7 — Degenerate and insensitive-case screening.** Reference-only, 3 seeds × 4
  transforms, run once per suite version, plus an input-*insensitivity* screen (does the output move
  at all when the input does?) and a seed-invariance screen. **Audit our own `(0.9, 1.1)`-style ranges
  first** (RVP-T0-5) — a case whose inputs cannot distinguish a correct kernel from a constant is a
  case that grades nothing. **2026-08-11 implementation checkpoint:** the research-side two-axis
  reducer and claim-aware runner are complete and durable in research commit `000a2686` (promoted to
  research `main` via `f3c6b24a`). They require reference-only materialized
  inputs, at least three seeds, all four identity/×3/×0.01/negate transforms, and measurable input
  and reference-output movement on both the seed and transform axes. The 14 focused reducer tests
  pass. This parent row remains open because the `AK_SENS_V1` producer is still an uncommitted change
  in `llama.cpp-experimental`; OP-11 declined that commit for now. Reopen only with explicit operator
  approval, followed by a fresh matched run whose suite identity includes the durable producer commit.

  - [x] **RVP-C2-7a — Build the two-axis research reducer and claim-aware runner.** ✅ 2026-08-11 —
    research commit `000a2686`, promoted to `main` via `f3c6b24a`; the focused reducer passes 14/14.

  **OP-11 RESOLVED 2026-08-12 — operator selected Option B (decline for now).** No experimental
  commit or push occurred. The implementation remains a local diagnostic, the smoke remains
  non-evidence, and producer-dependent closure remains unavailable unless the operator reopens it.

- [x] **RVP-C4-4 — Make the rocprof-v1 attribution workload phase explicit.** ✅ 2026-08-12 —
  research `c38bf49a` (promoted to `main` as `1527ea49`) adds `--gen-tokens`, preserves the historical
  prefill-only default, threads the requested generation count to `llama-bench -n`, rejects negative
  values, and records both `gen_tokens` and `phase: prefill|prefill+decode` in every receipt. K28's
  historical prefill result needs no relabelling. The focused producer suite passes 12/12 and the
  AutoKernel README suite passes 17/17.
  - [ ] **RVP-C4-4a — Capture governed real-model decode attribution.** After INF-03 r15 releases
    the MI210, run the repaired producer with `--gen-tokens 128` against the real 122B MoE model and
    retain the claim, device, source, binary, linkage, profiler, model, phase, and receipt identities.
    The earlier `iq2xxs-decode-nongoverned-20260812T1306Z` capture remains non-authoritative.
- [ ] **RVP-C2-8 — Hostile distribution at identical shapes.** Hold the shape fixed and change only
  the value distribution. This is the anti-shape-detection device, and it targets something we
  actually ship: our shape-gated default-off levers are exactly the kind of dispatch a candidate can
  learn to satisfy without being correct. The durable research reducer/runner is in `1a4d7dca`
  (research `main` merge `c5fe6b51`). A non-evidence smoke selected two ROCm0 `SOFT_MAX` cases;
  hostile mode returned 0 and passed 2/2 rows, with the device claim acquired/released and four
  sampler observations. Keep this evidence item open until the uncommitted producer gains a durable
  identity and the claim-aware runner retains a campaign receipt.

  - [x] **RVP-C2-8a — Build the hostile-distribution reducer and claim-aware runner.** ✅ 2026-08-11 —
    four named same-shape populations require distinct materialized inputs and complete successfully.
- [ ] **RVP-C2-9 — Checker precision pinning.** The property and reference paths must not run through
  `-fa`, MFMA-f16 accumulation, or `FORCE_MMQ`. A checker validated by the same fast path it is
  checking corrupts **claims**, not merely screens — this is the "verify THE consumer, not A consumer"
  discipline applied to the oracle itself. Research commit `1a4d7dca` requires host-double plus CPU
  sibling/reference checkers and refuses device-code, forced-MMQ, CUDA-FA, or rocWMMA checker paths.
  The same non-evidence smoke returned 0 and passed 2/2 selected `SOFT_MAX` rows; claim and four-sample
  telemetry were observed but no durable receipt was retained. Keep this evidence item open until the
  producer identity is committed and replayed by the claim-aware runner.

  - [x] **RVP-C2-9a — Build the checker-isolation reducer and claim-aware runner.** ✅ 2026-08-11 —
    missing receipts or accelerated checker paths fail closed.

### C6 — reward integrity: close the instrument gap first

- [x] **RVP-C6-1 — Hash-pin the measurement translation units.** `tests/test-backend-ops.cpp`,
  `tests/test-quantize-perf.cpp` and `tools/llama-bench/llama-bench.cpp` are hashed against the
  production anchor before every measured round; **any diff is a hard fail, not a warning.**
  **This is the highest-value single item in the batch.** C6 as designed pins the *evaluator*; but the
  *instrument* is compiled from the very tree the candidate is allowed to edit. No timer redesign
  fixes that — only pinning the sources does. The gate must also refuse to be satisfied by deleting
  the file it inspects (`feedback_verify_integrity_not_presence_of_own_edit`). ✅ 2026-08-11 — the
  reviewed measurement anchor is hardened commit `a4cb04ca8`, whose direct parent is frozen production
  v9 `0db32c06`; the one-commit overlay changes only `llama-bench` and its README. T0, T1 open and every
  T1 invocation hash the complete three-file manifest against that named anchor and hard-refuse a
  missing, unreadable, deleted or changed file. Pinning to the reviewed overlay rather than pretending
  its intentional instrument change is byte-identical to production preserves both authorities.
- [x] **RVP-C6-1a — Finalize the clean one-parent measurement-instrument lineage.** ✅ 2026-08-12 —
  `a4cb04ca8f92fa4d665684490f609b380f9b5e96` is clean, pushed, has frozen v9 `0db32c06` as its
  sole parent, and is the instrument pinned by the live-control path. Its real CPU smoke emitted all
  six required receipt families and released the exact q0–q3 claim; the all-PASS v9 preflight binds
  source, copied binary, capability, model, topology, storage, production, and package power.
- [x] **RVP-C6-2 — Stream-escape defence.** ✅ 2026-08-11 — the hardened lineage culminating in
  `a4cb04ca8`
  implements the ordinary/full-device-synchronized hybrid twin and the research reducer at
  `eda8de1a` requires `hip_full_device`, retains both timing vectors, and refuses an excessive twin
  gap. Live AK-BH-2 evidence (`/mnt/raid0/llm/autokernel/probes/ak-bh-2-factorial-20260811T0952Z/receipt.json`,
  SHA-256 `2a53cee2d8513737eca894e0f34152549932b75f3e04ef541cdee1848472cfdf`) exercised all eight
  ROCWMMA × MFMA × flash-attention arms with `autokernel_hybrid_ab_complete=true`,
  `autokernel_escape_checks_complete=true`, and `autokernel_device_sync_mode=hip_full_device`.
  Verified: T0 timing brackets
  `ggml_backend_graph_compute` with host wall clock (`tests/test-backend-ops.cpp:1621-1627`), and
  `ggml_backend_cuda_synchronize` (`ggml/src/ggml-cuda/ggml-cuda.cu:2512-2518`) calls
  `cudaStreamSynchronize(cuda_ctx->stream())` — **one stream**. Work issued on a second stream is not
  waited on and falls outside the timed region. Add (a) a hybrid A/B that repeats the measurement
  behind a full device synchronize and (b) a stream-creation audit in the source-integrity gate.
  **A candidate need not look malicious to do this** — multi-stream is an ordinary in-tree idiom.
- [x] **RVP-C6-3 — Thread / async-escape check across the timed region.** ✅ 2026-08-11 — the same
  eight live AK-BH-2 arms record `autokernel_thread_set_stable=true` and hash the process thread set
  before/after both ordinary and synchronized brackets. Static added-line detectors retain separate
  thread/async findings and missing detector ids remain `COULD_NOT_CHECK`; the focused reducer,
  live-control, and reward-hack suites pass 14/14. The CPU-side analogue of RVP-C6-2 is therefore
  exercised rather than merely present.
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
- [x] **RVP-C6-6 — Red-team corpus with a stated sensitivity.** ✅ 2026-08-12 — The required unit is 10 planted-bug
  and ~15 clean **executable HIP kernels**; report sensitivity and specificity, not an assertion of
  coverage. `execution/reward_hack_corpus.py` now materializes, compiles with ROCm 6.2 for gfx90a,
  and executes the 10 planted plus 15 clean programs. Every program's normal-128 and
  anti-short-circuit-127 units run under one MI210 claim and are checked against an independent host
  oracle. Final r3 observed **10/10** true positives, **15/15** true negatives, sensitivity **1.0**,
  specificity **1.0**, FPR **0.0**, and **25/25** expected runtime behaviors on both units. This is
  named-taxonomy instrument validation, never arbitrary-program coverage or a candidate speed claim.
  Receipt: `/mnt/raid0/llm/autokernel/campaigns/rvp-c6-executable-r3-20260812T0905Z/receipt.json`,
  embedded self-hash `b4e39c65f23323bd648b84e2b8088850201a2be16b4d46002b8e869a7b1620ee`, full-file SHA-256
  `91bcef0b21220f4947ce1b37bbdfe9df42b645b100f48ec1e71011da2779df9f`. The receipt binds failed
  22/25 r1 and passing r2 attempts by embedded and file hashes. Mine the published
  exploit **taxonomy** (harness frame-hacking, pointer-keyed memoization, structured-input
  short-circuit) — **do not vendor the 4.66 GB corpus**; it is NVIDIA-targeted Python with zero
  executable value on gfx90a. This is what lets the §"C6 monitor design" FPR-budget row above be
  stated as a number instead of a promise.
  - [x] **RVP-C6-6a — Validate the named static source-pattern detector corpus.** ✅ 2026-08-11 — the
    two versioned detectors pass 10/10 planted and 15/15 clean diff strings, reporting 100%
    sensitivity/specificity and 0/15 FPR for that narrow taxonomy only.
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
  memoization keyed on the pointer rather than on the contents. ✅ 2026-08-11 — the hardened lineage
  culminating in `a4cb04ca8` adds trusted `--autokernel-harden <seed>`: unique content per timed repetition, two
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

- [x] **RVP-C5-R — Mine a real-workload task class from our own repo history.** ✅ 2026-08-11 — Keyword-filter merged
  llama.cpp performance PRs (`optim`, `speed`, `latency`, `memory`) → classify → verify each is a
  genuine optimization and not a refactor → extract the PR's own benchmark command and claimed numbers
  → replay a candidate at the pre-optimization commit → **score against the human patch**. Row **C5**
  lists only synthetic and ported suites today; this is the only identified path to **non-synthetic
  tasks on our own stack**, at zero hardware-porting cost. **Two hard constraints**: (a) construct and
  run on historical commits or `llama.cpp-experimental` — **never** against the frozen v8 tree; (b) our
  PRs are public and in training data, so temporal filtering or held-out selection is mandatory, or the
  suite measures memorization. **2026-08-11 evidence audit:** the exact 2026-07-04 argv and raw
  parent/human-patch evidence are no longer available; the surviving summaries cannot reconstruct a
  matched claim. The replacement descriptor therefore states `historical_command_recovered=false`
  rather than laundering a reconstructed argv into an original-command claim. It seals GDN bf16
  state at parent `7c28056b` versus human expert `496e2f09`, pins the full replacement benchmark
  surface and model SHA, and withholds the expert until terminal candidate state. The fresh five-block
  matched replay retained all 15 exact argv/raw runs, build and descriptor hashes, a 1,995-sample
  250 ms device trace, and claim acquisition/held/release receipts. Parent mean was 155.4233734
  `speed_tg`; expert-on mean was 188.4099002, a **21.223659%** expert gain; same-binary expert-off was
  -0.105875% versus parent. With no terminal AutoKernel candidate, candidate-vs-expert correctly
  remains `COULD_NOT_CHECK`. Receipt:
  `/mnt/raid0/llm/autokernel/probes/rvp-c5-r-gdn-bf16-20260811-r2/receipt.json`, SHA-256
  `279b7c3d6272eb6f881ca55b9599e7f341777338942490f36aadc17766aa1abb`. Research implementation:
  `1a4d7dca`, promoted via `c5fe6b51`.
- [ ] **RVP-C5-2 — Screen the C5 seed corpus for input-INSENSITIVE ops** (the `mean(softmax(x))` /
  `relu(x-2)`-under-uniform-sampling class). Twin of the degenerate-output screen on a different axis:
  constant output vs insensitivity to the input. The durable research reducer now implements this
  distinction, but this row remains open until the experimental producer is committed with operator
  approval and the C5 corpus is screened by a fresh matched run.
- [ ] **RVP-C3-2 — Expert-reference ceiling alongside the honest-baseline floor.** Where a task derives
  from a real merged optimization, report candidate-vs-human-patch delta as well as
  candidate-vs-vendor-baseline. C3 currently fixes only the floor. The sealed scorer and replay
  receipt now establish the 21.223659% human ceiling, but this parent remains open until a terminal
  AutoKernel candidate supplies the candidate-to-parent and candidate-to-human terms.

  - [x] **RVP-C3-2a — Build and validate expert-ceiling scoring for held-out historical tasks.** ✅ 2026-08-11 —
    the scorer emits both deltas when a candidate exists and returns `COULD_NOT_CHECK` when it does not.
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
  landed in research commit `5fbd471b5e7929d04113f7d5d95008837cd2107a`, an ancestor of
  research `origin/main` at `1448d93e3b3f42ef7b16484fe6cb3e770660c1e2`, in
  `scripts/kernel_rnd/autokernel/evaluator/devices.py`,
  `scripts/kernel_rnd/autokernel/execution/microbench.py`, and
  `scripts/kernel_rnd/autokernel/execution/test_device_sampler.py`. A clean detached worktree at that
  main commit revalidated the focused module at 11/11 on 2026-08-12.
- [x] **RVP-C2-10 — Add a non-power-of-2 extent to the standing shape set.** ✅ 2026-08-11 — frozen v9's
  executed `MUL_MAT` case set already carries extents 83, 77 and 127 (plus other irregular shapes),
  and the AutoKernel T0 op filter runs that standing set rather than a power-of-two subset. Adding
  4095 would increase cost without adding the requested non-power-of-two property. Near-zero
  cost. Keep shape-variation-as-correctness-probe distinct from shape-variation-as-hack-detector —
  different instruments, and merging them weakens both.
- [ ] **RVP-C2-11 — Seed-invariance degeneracy screen**: an output that does not vary across input
  seeds is cacheable and therefore unscoreable. Complements RVP-C2-7. The durable research reducer
  now emits this axis separately from transform variation; closure still requires an operator-approved
  experimental producer commit and a fresh durable-identity replay.
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
- [x] **RVP-C6-10 — Anti-short-circuit cases go in the RANKED set, not just the gate.** ✅ 2026-08-12 — The durable
  mechanism now has a live ranked hard-case receipt. If the hard
  cases only gate, a candidate can route easy inputs to a fast invalid path and never pay for the
  accurate path's cost on the hard ones. Final r3 places `normal-128` and
  `anti-short-circuit-127` beside each other for every program and records real gfx90a elapsed time
  for both. Claim `akd-006b9b9b049b4249` covered only the 10.283-second execution window, released at
  `2026-08-12T09:05:14.248081+00:00`, and carried 42 numeric samples at 250 ms cadence (maximum gap
  0.250032 s). Pointer-alignment, one-shape-only, and nondeterministic-timing mutations are explicit
  fail-closed controls: a defect that manifests in only one ranked unit is refused. This closes the
  instrument contract and asserts no candidate optimization or speedup.
  - [x] **RVP-C6-10a — Implement strict ranked hard-case campaign units.** ✅ 2026-08-11 —
    `MicrobenchPlan.anti_short_circuit_units` requires real per-unit command/recipe changes, a normal
    control, distinct parameter frames, physical envelopes, and emits those units into the same
    ranked block stream. Focused campaign/microbench tests pass; no durable live ranked-set receipt
    exists yet.
- [x] **RVP-VIDYA-1 — Belief-kernel wiring, filed now per CLAUDE.md.** ✅ 2026-08-11 — the source row is
  present in `scripts/vidya/adapters/README.md` and the owned projection task is SC18 in
  `vidya-belief-substrate-program.md`; actual write-side work remains tracked there rather than hidden
  in this dependency. The property layer (RVP-C2-2)
  **produces measurements** — per-op property residuals per backend per shape. Add a row to the source
  table in [`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md) and a task in
  [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md). The write side is cheap and
  permanent; the read side cannot be retrofitted.
- [x] **RVP-VIDYA-2 — Bind the stranded G15, C4, and standalone-WGM profiler receipts into the
  AutoKernel/Vidya measurement seam.** ✅ 2026-08-11 — research `07b303cc` adds an isolated
  finalizer rather than modifying the CRITICAL shared C4 capture helper. It verifies immutable source
  receipts, released device claims, C4 report hashes, exact scored repetitions, physical ranges, and
  the WGM proxy's non-transfer-to-real-MMQ boundary before emitting a separate self-hashed
  `epyc.autokernel.profile_beliefs.v1` receipt. Root's existing auxiliary adapter now admits that
  schema through the one measurement ladder. Four current artifacts produced **16 rows**: G15 B=64/128
  throughput plus target-share signals, three formal family-duration rows each for Q4_K and Q8_0,
  and six standalone WGM proxy factors. The original profiler receipts remain unchanged.

**Declined, recorded so they are not re-derived:** lifting the 129 human-verified reference test files
as a component (design reference only — and the reason is **technical**: torch/CUDA, will not run
here); the `speedup >= 1.0` pass clause; the upstream `warmup=3, repeats=5` timing protocol, which is
weaker than our canonical one; and citing any foreign-hardware correctness-overestimation magnitude as
if it were ours — under P-GPU-1 the analogous magnitude is ours to derive on our own card.
