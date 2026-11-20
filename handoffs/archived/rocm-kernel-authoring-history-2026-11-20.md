# rocm-kernel-authoring — compacted ticked boxes (2026-11-20, handoff_compact.py)

- [x] **RVP-AUD-2 — Reconcile implemented C3/C6 rows against current research main.** ✅ 2026-08-12 —
  clean detached research `26ca88dc` revalidated `microbench.py`, `physical_bounds.py`,
  `reward_hack_scan.py`, `devices.py`, `oracle_integrity.py`, and the generated import footprint at
  **408 tests + 15 subtests PASS**. This confirms RVP-C6-2/3/4 and RVP-C3-4/5. That audit correctly
  reopened RVP-C6-6/10 because their static detector corpus and ranked-unit machinery did not satisfy
  the empirical acceptance text; the later executable gfx90a r3 receipt below closes both rows.
  RVP-C2-8/9 also remain open: their reducers and claim-aware runners are complete, but OP-11 declined
  the committed seeded producer needed for fresh matched evidence. No implementation-only test
  upgraded empirical authority.
- [x] **Pre-hardware prep (now).** Pin GEAK / GEAK-eval / Apex / AgentKernelArena repos to paper-matching commits, inspect licenses, and draft a split ROCm + torch-ROCm environment recipe ✅ 2026-07-29. Source pins and the no-execution activation order are recorded in [deep-dive §10](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md#10-pre-hardware-source-pins-and-deferred-environment-recipe-2026-07-29): GEAK v1 `v1.0.0` is Apache-2.0 (not the old MIT label); Apex is MIT; AgentKernelArena is Apache-2.0; GEAK-eval has no project-level license at its paper-era snapshot, so its code is **no-reuse pending resolution**. GEAK v1 (`triton==3.1.0`) and GEAK-eval (`triton==3.3.0`) require isolated environments. No install, server, benchmark, GPU/ROCm workload, or production-kernel action is authorized by this closure.
- [x] **MI210 base bring-up and one-task AgentKernelArena compatibility.** ✅ 2026-08-11 — ROCm,
  torch-ROCm, Triton and physical `gfx90a` were identity-checked; the live add task compiled, passed
  correctness 3/3 and timing 5/5, and released the claim. The preflight honestly records
  `external_type_dispatch_present=false`, so this does not claim the full vendor launcher ran.
- [x] **Build C6 reward integrity.** ✅ 2026-08-11 — immutable external scoring, exploit detectors,
  unseen/hostile shapes, stream/thread escape checks, planted red-team corpus, prompt disclosure,
  output-invariance, and ranked anti-short-circuit cases are implemented and tested.
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:104)* **Honest baseline + E2E scoring (C3 + FastKernels gate).**
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
- [x] **Re-score the C4 risk row from HIGH.** ✅ 2026-08-11 — C4 is now MED: tool availability,
  CDNA2 taxonomy, deterministic parsing and the report contract are closed. The empirical question
  is also answered at op level: hash-bound Q4_K and Q8_0 single-process captures produce complete
  mapping/formal reports, and the report now crosses a diagnostic-only AutoKernel/GEAK/Arena seam.
  Residual MED risk is explicitly scoped: `rocprofv2` exits 139 for whole-model Qwen prefill and
  IQ2_XXS op capture on this host, so those workloads require another profiler or a narrower probe.
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
- [x] **Give the monitor the WHOLE SEARCH TREE, not the selected candidate.** ✅ 2026-08-11 —
  `controller/reward_monitor.py` binds the complete evaluated variant set and exactly one selected row. Best-path-only transcripts
  advantage the AIDE sandbagger by hiding potentially higher-scoring paths (intake-979#01). Hand the monitor every evaluated variant **including discarded higher-scoring ones** as a local journal requirement; the paper did not ablate the detection benefit of whole-tree visibility.
- [x] **Name the threat model in the monitor prompt.** ✅ 2026-08-11 — the declaration requires the
  versioned threat-specific id and the compiled prompt renders it. In the sandbagging experiment using claude-3.7 as monitor, the sandbagging-specific prompt outperformed the general prompt (intake-979#02); this does not rank it as the largest intervention across the study
- [x] **Aggregate.** ✅ 2026-08-11 — the reducer requires a complete model×sample panel and computes
  mean-of-mean@k. Aggregation improved detection in the reported code-sabotage setting; mean@k over repeated samples improved AUC with diminishing returns (intake-979#04). The prior legend-only 0.993/0.970 numbers were not read in this audit and are omitted, not refuted; local monitoring cost remains unmeasured here
- [x] **Assume monitor-awareness.** ✅ 2026-08-11 — `assume_monitor_aware` is mandatory true. Every tested monitor scored higher AUROC on unaware than aware **AIDE code-sabotage** runs in Figure 6 (intake-979#03); this is not a universal result across scaffolds or sandbagging monitors. Any
  agent that can read the loop's config knows it is monitored — design for the aware case
- [x] **Preserve CoT visibility.** ✅ 2026-08-11 — every trace requires non-empty reasoning and
  `include_reasoning_trace` is mandatory true. Hidden reasoning tokens are described as a "large advantage to the
  agent". The local reasoning-visibility control is a design transfer, not a source-measured kernel detection gain
- [x] **Declare an explicit FPR budget rather than claiming safety.** ✅ 2026-08-11 — the declaration
  requires a numeric FPR budget and the reducer emits sensitivity, specificity, observed FPR and
  `budget_met` — *"gaining strict safety guarantees
  may require prohibitively high false positive rates."* A C6 layer with no stated FPR is not a gate
- [x] Build C6 (reward-integrity) from OpenHyra's proven design: a trusted evaluator OUTSIDE the sandbox recomputes score on an immutable snapshot (self-reported numbers ignored); anti-TOCTOU snapshot (O_NOFOLLOW, reject symlink/FIFO/multiply-linked, size cap, chmod 0444, SIGKILL the candidate process-group BEFORE snapshot; OpenHyra `sandbox.py:80-134,255`); correctness-gate evaluated BEFORE latency (HyRA SOL-ExecBench `is_correct` precondition). This is the anti-cheating-kernel gate this handoff notes GEAK/Apex leave loose ✅ 2026-07-22
- [x] Adopt the SOL-ExecBench task/scoring schema {entry_point kernel.py::run, target_hardware, dependencies, hard is_correct gate, sol_score, latency_ms} as the C5 task contract, and OpenHyra run-manifest provenance (sha256 sources+task+evaluator + resume-drift rejection; `provenance.py:72-157`) as the attestation format binding each kernel measurement to MEASUREMENT.md ✅ 2026-07-22
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
  clock-pinning branch closes for free** and OP-2 in [`autokernel-research-loop.md`](autokernel-loop.md#track-autokernel-research-loop)
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
- [x] **RVP-C4-4 — Make the rocprof-v1 attribution workload phase explicit.** ✅ 2026-08-12 —
  research `c38bf49a` (promoted to `main` as `1527ea49`) adds `--gen-tokens`, preserves the historical
  prefill-only default, threads the requested generation count to `llama-bench -n`, rejects negative
  values, and records both `gen_tokens` and `phase: prefill|prefill+decode` in every receipt. K28's
  historical prefill result needs no relabelling. The focused producer suite passes 12/12 and the
  AutoKernel README suite passes 17/17.
  - [x] **RVP-C4-4a — Capture governed real-model decode attribution.** ✅ 2026-08-12 — the
    source-bound p0/tg128 decode run on the real Qwen3.5-122B-A10B UD-IQ2_M model passed at
    **37.057131 tok/s**. Summed device time was MMV **59.9524%**, quantize **8.0084%**, RMSNorm
    **4.3655%**, FlashAttention **3.1458%**, copy **2.3187%**, and GDN **1.8620%**. The GDN target is
    therefore low priority on this exact decode surface; type-specialized MMVQ is primary. Receipt
    `/mnt/raid0/llm/autokernel/probes/rvp-c4-4a-122b-decode-20260812T192651Z/receipt.json`, file
    SHA-256 `c7f3f5a243310021e022715b403fe0668b47145440bda00ee43ac6d84e14bed3`; CSV SHA-256
    `e7fd3481d8c978463831391ef19c9c640907a774e34fd393c95edcc5c53e01fa`. Exact MI210 and CPU-q3
    claims released; 58 device samples covered the measurement window.
  - [x] **Route the RVP-C4-4a rocprof-v1 trace through the source-bound prior-art gate.** ✅ 2026-08-12
    — research `5c8e57dc`/main `6103bde8` adds rocprof-v1 schema ingestion and frozen-v9 ggml-type
    decoding. Replay classified 11 admitted families / **69.3283%** of captured time as existing-path
    work, two / **2.3187%** as forward-port candidates, and eight / **25.3907%** as unmatched. The
    deterministic recommendation is `expand_catalogue_before_novel_generator`; this is routing,
    not a performance verdict.
  - [x] **RVP-C4-4b — Capture and route the governed 35B Q8 decode control.** ✅ 2026-08-12 — the
    source-bound p0/tg128 run on Qwen3.6-35B-A3B-MTP-Q8_0 passed at **81.582817 tok/s**. Summed device
    time was MMV **42.3760%**, quantize **12.9820%**, RMSNorm **6.2201%**, FlashAttention **5.5143%**,
    copy **2.7359%**, and GDN **1.7678%**. Receipt
    `/mnt/raid0/llm/autokernel/probes/rvp-c4-4a-35b-q8-decode-20260812T194500Z/receipt.json`, file
    SHA-256 `0ca812e34c8c7c939c9b9d5eac90941dcad603236a7fbed85ade3c839316d2ce`; CSV SHA-256
    `670819fbd7b33094bba4a8904667196d6eccade78296c8d0a632aa3fd29d18dd`. Sixty-one device samples
    covered the measurement window and both claims released cleanly. Its deterministic replay routes
    four families / **62.4344%** of captured time to existing paths, two / **2.7359%** to forward-port
    candidates, and ten / **33.0644%** to unmatched work, yielding `retain_novel_generator_scope`.
    Paired outputs are `rvp-c4-4a-iq2-decode-20260812-prior-art.json` (SHA-256
    `8037bf5eec8b7be71d29f2714ee1469dc83dc7e7ab6d2063b379b874e22025ec`) and
    `rvp-c4-4a-q8-decode-20260812-prior-art.json` (SHA-256
    `c5a6190f0c6d6c6ff6c606f3b3a9640e08c0688381e6fe178f188f20c62163fd`). This sibling control
    corroborates low GDN priority, but model size, active parameters, and quant differ, so it is not a
    causal model/quant comparison and the two workload-specific router decisions must not be pooled.
  - [x] **RVP-C4-4c — Exercise the Q4_K_M decode surface with fail-safe preflight and source-bound
    routing.** ✅ 2026-08-12 — the attempted 122B three-shard Q4_K_M surface failed safely during
    `llama-bench` preflight before any captured profile; both exact claims released and teardown had
    zero errors. Its failure receipt is
    `/mnt/raid0/llm/autokernel/probes/rvp-c4-4a-122b-q4km-decode-20260812T200800Z/receipt.json`
    (file SHA-256 `9140e29c1e182e4c3ad503a2935b9edd061784b36a92b22c13afbf68fa9461db`).
    The governed 35B Q4_K_M p0/tg128 fallback then passed at **70.19648 tok/s** with **217,358**
    dispatches and 44 device samples spanning 10.892 seconds. Summed device time was MMV
    **46.0984%**, quantize **10.6058%**, RMSNorm **5.7346%**, FlashAttention **5.2539%**, copy
    **2.8384%**, and GDN **1.6451%**. Receipt
    `/mnt/raid0/llm/autokernel/probes/rvp-c4-4a-35b-q4km-decode-20260812T201000Z/receipt.json`
    has file SHA-256 `459e7bfd3eb0aa3357544569ffec92f082d55a89e525eaf16cff5e37dc9a82f6`;
    CSV SHA-256 is `6a3571de4bb4d2a1d3267369c99e8b7141618a70cadcae50d980a660af9234f4`.
    Both claims released cleanly. Source-bound routing admitted six existing families / **59.9639%**
    of captured duration, two forward-port families / **2.8384%**, and eleven unmatched families /
    **36.4956%**, yielding workload-local `retain_novel_generator_scope`. Output
    `rvp-c4-4a-q4km-decode-20260812-prior-art.json` has SHA-256
    `c234b4b168cd4b95adb8668aa77d3c0e989807f354ae29bb9e5c51892c7243d3`.
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:724)* **RVP-C2-8 — Hostile distribution at identical shapes.**
  - [x] **RVP-C2-8a — Build the hostile-distribution reducer and claim-aware runner.** ✅ 2026-08-11 —
    four named same-shape populations require distinct materialized inputs and complete successfully.
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:735)* **RVP-C2-9 — Checker precision pinning.**
  - [x] **RVP-C2-9a — Build the checker-isolation reducer and claim-aware runner.** ✅ 2026-08-11 —
    missing receipts or accelerated checker paths fail closed.
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
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:907)* **RVP-C5-2 — Screen the C5 seed corpus for input-INSENSITIVE ops**
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:912)* **RVP-C3-2 — Expert-reference ceiling alongside the honest-baseline floor.**
  - [x] **RVP-C3-2a — Build and validate expert-ceiling scoring for held-out historical tasks.** ✅ 2026-08-11 —
    the scorer emits both deltas when a candidate exists and returns `COULD_NOT_CHECK` when it does not.
- [x] **RVP-C3-4 — 250 ms in-run device-state sampler** across the measurement window. ✅ 2026-08-11 —
  the AK-BH-1, AK-BH-2, and corrected Q4_K receipts carry numeric in-window samples with maximum gaps
  of 0.250006, 0.250032, and 0.250023 seconds respectively, plus released device claims.
- [x] **RVP-C2-10 — Add a non-power-of-2 extent to the standing shape set.** ✅ 2026-08-11 — frozen v9's
  executed `MUL_MAT` case set already carries extents 83, 77 and 127 (plus other irregular shapes),
  and the AutoKernel T0 op filter runs that standing set rather than a power-of-two subset. Adding
  4095 would increase cost without adding the requested non-power-of-two property. Near-zero
  cost. Keep shape-variation-as-correctness-probe distinct from shape-variation-as-hack-detector —
  different instruments, and merging them weakens both.
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:946)* **RVP-C2-11 — Seed-invariance degeneracy screen**
- [x] **RVP-C2-12 — A hard error on non-contiguous input must be a FAIL, never a skip.** ✅ 2026-08-13 producer `f744cc220e722d1bda93783959471d44f8e118b0`; Research `1403462340acb89c5652a157a9aacb1ebbb5dd6c`; [fixture tests](../../artifacts/compute/codex3-rvp-c2-12-20261031/TEST.log). [no-belief: source and regression verification] The reference
  - 2026-10-31 prior-work hygiene only, **excluded from today’s code quota**. The work predates today; evidence filing or verification is not a new implementation. See [operator tick audit](../../artifacts/compute/codex3-tick-audit-20261031/tick-audit-20261031.md). [no-belief: quota-accounting correction]
  suite converts these to skips in half its files; a kernel that cannot accept a strided ggml view is
  not correct for llama.cpp, and a skip records that as neither pass nor fail. **2026-08-11 static
  implementation:** under the separate `--autokernel-layouts` flag, the experimental tool marks an
  unsupported selected layout as a hard failure; both console and CSV parsers preserve FAIL instead
  of `not_supported`. Research commit `14034623` covers the consumer. This row remains open until the
  producer is committed.
  - 2026-10-31: producer `f744cc220e722d1bda93783959471d44f8e118b0` is committed and an ancestor of frozen `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`; selected unsupported layouts set `hard_failure` and return FAIL. Existing console and CSV parser fixtures pass on Research `93c217ec5d743da8f81b430630a03ad3638d106a`. [Source and test evidence](../../artifacts/compute/codex3-rvp-c2-12-20261031/README.md). No new native backend run or production edit/build. [no-belief: source and regression verification]
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
- [x] **RVP-C6-13 — Close side-stream timing integrity.** ✅ 2026-08-16 — C3 surfaces now require
      either full-device synchronization or the exact tracked fence-after-start/join-before-stop
      contract; event-only timing is refused. The discovery oracle uses `hip_full_device`. The source
      mechanism is ~200 lines, Apache-2.0, arch-independent: track every stream
      constructed after install, fence from current after the start event, join into current before the
      end event, so the reported time is correct regardless of what the source does. Note the detail
      that makes it worth copying rather than re-deriving — a join-only first version still read 1.41×
      fast, which is why the fence exists, and a *real* submitted kernel had hit a mild unintentional
      form at 1.42×. Single-stream submissions take no new code path.
- [x] **RVP-C6-20 — Falsify "L1+L2 is enough" with three hand-authored adversarial gfx90a kernels.** ✅ 2026-08-21 A
      LayerNorm computing mean/variance/normalize but **SKIPPING scale and bias**; a matmul-then-transpose
      **omitting the transpose**; a softmax **omitting the max-subtraction**. All three are invoked and
      contain no blacklisted symbol. Confirm the CURRENT gate accepts them, then confirm the new semantic
      tier rejects them. This is the mutation test our verification doctrine requires — and the mutation must
      be both **visible AND counted**.
      **CHECKPOINT 2026-08-21 — harness BUILT and the static arm RUN** (research repo
      `scripts/kernel_rnd/c6_mutants/` @ `ef7fec18`): three genuine Triton mutants authored with honest
      positive controls, PyTorch references, and standard + adversarial input arms. **The L1 scanner was
      mutation-tested BEFORE its verdict counted** — 8 planted-dirty samples it must flag, the references
      as a scope negative-control (they must FAIL), an empty-scope refusal; 6/6 static tests pass.
      **L1 result: all six candidates PASS with zero findings** — the first half of the falsification
      holds. One refinement to the row's claim, recorded before any GPU run: the matmul-transpose mutant
      is PREDICTED value-visible to a sound oracle at random inputs — the corpus is built to measure where
      the omission class SPLITS into input-conditional identities (LayerNorm-under-default-init, softmax)
      versus value-visible members, which is sharper than "all three pass". GPU arms (L2 ghost replay via
      `JITFunction.run` no-op swap; value oracle with NaN/Inf rejection + max-observed-error per
      `intake-1245#04`) are written and REFUSE to run without an acknowledged negotiated idle window on the
      shared MI210 (operator instruction 2026-08-21); window requested from the peer session holding the
      GPU (llama-server pid 3499606, Qwen3.8-27B). Row stays OPEN pending the GPU arms and, later, the
      C6-19 judge arm.
      **RESULT 2026-08-21 16:03Z — FALSIFIED, on the MI210 (gfx90a:sramecc+:xnack-), inside an
      owner-granted co-resident window (~14 s GPU; CT-5c owner notified for latency-row hygiene).**
      Full JSONL at research `scripts/kernel_rnd/c6_mutants/results_20260821.jsonl`. All honest positive
      controls PASS every tier; all three mutants PASS L2 ghost replay (genuinely load-bearing kernels).
      Value oracle at STANDARD inputs (rtol=atol=1e-3, NaN/Inf rejected, max-observed-error recorded):
      **layernorm_no_affine PASSES with max error 4.768e-07 — BIT-IDENTICAL to the honest kernel's error**,
      i.e. under default module init the omission is an exact identity and NO tolerance, however tight,
      can catch it; **softmax_no_maxsub PASSES at 5.588e-09**; **matmul_transpose_no_t is CAUGHT
      (9.458e+01)** — the pre-registered value-visibility prediction confirmed — and PASSES on the
      symmetric-input arm (1.068e-04), proving the oracle's verdict is input-structure-dependent.
      Adversarial arms catch what they were designed to: non-default affine fails the LayerNorm mutant
      (4.471e+00); large-magnitude inputs fail the softmax mutant via the non-finite rejection.
      **CONCLUSION: L1 + L2 + a SOUND value oracle at standard inputs accepted 2 of 3 omission mutants.
      The sharper finding: the omission class SPLITS into input-conditional identities (uncatchable by
      any tolerance at standard inputs) and value-visible members (a sound oracle catches). The
      semantic-judge tier (C6-19) is therefore load-bearing for the first sub-class, and adversarial
      input curricula (non-default parameters, overflow-scale magnitudes) are the cheap complementary
      defence for both.** The judge-rejects-all-three arm is owned by C6-19's ratified hard-prerequisite
      clause; this corpus is its validation set.
  - *(folded into INF48-LIVE-1; full text at b3bd883d3:1310)* **RVP-C6-21 — Run the DIFFERENTIAL ORACLE AUDIT on our own C6 corpus.**
- [x] **RVP-C6-25 ✅ 2026-08-21 (compiled into wiki/benchmark-methodology.md, evening update) — Record the KernelFalcon test-harness admission as a SIXTH Shape-C instance in
      `wiki/benchmark-methodology.md`.** It is the cleanest one in the set: the authors name the weakness of
      their own gate in the same post as the 100%-correctness headline — _"we trust the LLM-generated test
      harness itself—we don't statically analyze it for cheating"_ — and the follow-up post then wins only
      **65 of 100** L1 tasks against plain `torch.compile`. Pair it with the existing index datapoint showing
      the same system at **0.777x** geomean against PRODUCTION baselines: same system, different denominator,
      win becomes slowdown.
  - *(folded into INF48-LIVE-1; full text at b3bd883d3:1351)* **RVP-C6-26 — close the within-pair content-memo hole in the hardened bench (rider on RVP-C6-8).**
- [x] **RVP-C4-10 ✅ 2026-08-21 — Settle GPA's input availability on the MI210 with one bounded probe (~30 min).** Run
      `rocprofv3 --pc-sampling-beta-enabled` against one trivial HIP kernel and dump the per-sample record
      schema. Two decision-grade outcomes: the flag errors/does not exist on 6.2 → the C4-template question
      closes NEGATIVE until a ROCm upgrade is on the table; or it emits records → inspect whether any
      stall-reason field is populated under host-trap (docs say it will be absent). **Record what the
      hardware actually emits rather than concluding absence from documentation.**
      **RESULT 2026-08-21 (measured, not doc-inferred): PC SAMPLING ON ROCm 6.2 IS A STUB.** The CLI
      flag does not exist (`rocprofv3: error: unrecognized arguments: --pc-sampling-beta-enabled`,
      SDK 0.4.0-66). The LIBRARY exports the API (`rocprofiler_query_pc_sampling_agent_configurations`,
      `rocprofiler_configure_pc_sampling_service` both present in `librocprofiler-sdk.so`) — but calling
      it against the live agent (enumerates cleanly as `gfx90a / AMD Instinct MI210`) returns **status 16
      "API function is defined but not implemented"**, with the SDK's own log printing `pc_sampling.cpp:53]
      PC sampling unavailable`. So the answer is stronger than "needs 6.4": at 6.2 there is NOTHING to
      configure — no host-trap, no stochastic, no record schema to inspect. **The GPA C4-template question
      closes NEGATIVE at this ROCm version by direct measurement.** The one caveat that stays doc-based:
      whether a 6.4+ upgrade would yield stall reasons on gfx90a (docs say host-trap only, stall reasons
      stochastic-exclusive = CDNA3+) remains untested because untestable here. Probe source:
      `tmp/intake-20260821/pcs_probe/probe.c` (session scratch; ~40 lines, gcc against the side-loaded SDK).
  - *(folded into INF48-LIVE-3; full text at b3bd883d3:1393)* ** GPA publishes estimated beside achieved for all 26 optimization rows, **
- [x] **RVP-PWR-2 ✅ 2026-08-21 (first pass; see caveat in the result block) — Run the aliasing probe on gfx90a under LOAD, which is where any divergence appears.**
      `intake-1238#record` (SC24, >70 GPUs, external-meter validated) shows the vendor power field is a
      firmware boxcar average over a window SHORTER than its own update period — 25% of runtime sampled on
      A100/H100. The probe is vendor-neutral: a periodic square-wave workload of controlled duty cycle swept
      across periods, looking for aliasing. Compare the **cumulative energy counter** against
      **integrated average power** over the same window; divergence bounds how wrong the averaged field is
      here. **DIRECTIONAL WARNING, the most important line in this section:** the error is NOT a constant
      offset and cannot be calibrated out with a fudge factor — its sign and magnitude depend on the phase
      relationship between workload periodicity and sampling window. For llama.cpp decode, which is HIGHLY
      PERIODIC at the token cadence, this is close to a worst case: a token period near a harmonic of the
      sampling window can **PHASE-LOCK and produce a stable, repeatable, and completely wrong power number.**
      A number that reproduces across runs is not thereby correct.
      **CONCRETE PROTOCOL, LIFTED FROM `intake-1251#record` Figure 10 — this replaces "sweep some periods"
      with a runnable design.** Their two bracketing cases on MI250X are **10 Hz / 100 ms period (clean)**
      and **250 Hz / 4 ms period (aliased)**; run both plus a sweep between them. **THE DETECTION TEST IS AN
      FFT, NOT AN EYEBALL, AND IT NEEDS NO EXTERNAL INSTRUMENT** — because the ground truth is the period
      *you commanded*. Clean case: _"clear harmonics at expected frequencies"_. Aliased case: _"a peak shift
      from the ground-truth period, and an increased floor of noise across all other frequencies"_. Those two
      signatures are the pass/fail criterion. Sample the **cumulative energy counter** (`energy_count`,
      microjoules) via the **rsmi C API**, not the CLI: per their Figure 1 the sensor, the driver publication
      and the application read are three *asynchronous* stages, so **a read is not a measurement** and our
      ~200 ms CLI spawn cost is a third stage on top of the 1 ms sensor cadence rather than a sampling rate.
      Run it against `power_average` in parallel — Appendix Table III names that field _"GPU power moving
      average"_ in microwatts, so the vendor's own metric table confirms the filtering our probe is trying to
      bound. Report the knee **as a median with an interval**, matching their Figure 6 treatment across
      512 GPUs; on one MI210 the interval is across repeats, not devices, and must be labelled as such.
      **RESULT 2026-08-21** (same probe suite @ `df40658a`): sampler sustained **107 µs/sample** via ctypes
      on librocm_smi64 (1700x the CLI); the energy counter's **1 ms refresh CONFIRMED on-die** (236 distinct
      values in 236 ms). FFT of derived power against commanded periods: 10 Hz → 9.9 Hz peak at 34.3 dB;
      **250 Hz — the paper's aliased case — resolves CLEAN at 249.94 Hz, 32.2 dB (n=1, the one cell still
      wanting repeats)**. Forcing analysis past Nyquist (500 Hz command at a 2 ms bin) produces the textbook
      signature — peak shifted to 187.7 Hz, prominence collapsed to 2.8 dB — **validating the detection test
      itself**. FINDING: the paper's ~4 ms knee is an INSTRUMENTATION-LAYER cost (consistent with its own
      wording), not a sensor limit; with our sampler the floor is the counter's Nyquist (500 Hz). **API TRAP
      recorded for every future consumer: `rsmi_dev_energy_count_get` returns the RAW COUNTER — energy_uJ =
      counter x 15.3 (counter_resolution). The CLI pre-multiplies; the API does not; a naive dE/dt
      under-reads by exactly 15.3x and looks plausible.** Load-generator lesson: sync every op, or the async
      backlog stretches the realized period (measured: exactly halved frequency). Remaining, deliberately
      not claimed: the token-cadence phase-lock measurement on a REAL decode workload — that needs a served
      model and belongs at the next serving boundary. **DONE 2026-08-21 (late), operator-directed, and the
      answer is a BOUNDED NEGATIVE** (research `power_sensor_probe/` @ `bf8fdd93`): two llama-bench tg-only
      decode runs at **122.4 tok/s** (gemma-4-e2b Q8) and **30.5 tok/s** (Qwen3.8-27B Q8) — averaged field
      vs energy-counter ground truth in the settled steady window: **−0.86% and −0.84%**. The discrepancy is
      **invariant across a 4x cadence change, which is the decisive test — a phase effect must move with
      cadence** — and the token cadence is essentially invisible in the dE/dt spectrum (0.4 dB / −1.1 dB):
      steady decode is back-to-back compute, near-DC at the token scale, so the modulation that could
      phase-lock barely exists. **SCOPE OF THE ALL-CLEAR: steady, settled decode only.** The measured
      hazards stand exactly where the square waves put them — transitions (~190 ms delay, ~4 s rise) and
      duty-cycled/bursty loads (request gaps, prefill/decode alternation, speculative bursts), where dE/dt
      remains the only instrument. The `intake-1238` directional warning is thereby BOUNDED, not refuted.
      Ops lesson for anyone generating decode load: the b10125 llama-cli is a chat REPL that ignores
      `-no-cnv` and floods stdout (one hung orphan produced 0.9 GB of redraw; killed + death verified);
      **llama-bench is the decode-load generator.**
- [x] **RVP-PWR-5 ✅ 2026-08-21 — Re-measure the three CONFIDENCE-WINDOW parameters on the MI210, because the paper
      does not publish them.** `intake-1251#record` defines `W_conf = [t_s + t_d + t_r, t_e - t_d - t_f]`
      (delay, 10-90% rise, 90-10% fall) and states that outside it _"measurements are dominated by sensor
      transition effects"_ — but **no consolidated numeric values for t_d, t_r or t_f appear anywhere**, so
      **its own central equation cannot be applied as published.** They are characterised only visually in
      Figure 5. Fold this into RVP-PWR-2's square-wave sweep, which produces exactly these three quantities
      as a by-product. Until we have them, we cannot legitimately gate any phase-level power attribution.
      **MEASURED 2026-08-21, TWO-RUN PERSISTENCE** (research `scripts/benchmark/power_sensor_probe/` @
      `df40658a`): averaged field **t_d = 192.7 / 184.1 ms**, **t_r(10-90) = 4418 / 3913 ms**,
      **t_f(90-10) = 3566 / 3479 ms** (idle 59.8/60.8 W, plateau 224.1/224.5 W). CONSEQUENCE: a phase must
      exceed **~8 s** before the averaged field has ANY attributable interior — below that, dE/dt from the
      energy counter is the only instrument (its own response: t_d ≤12 ms, t_r ≤2 ms). W_conf is now
      computable on this part.
- [x] **RVP-C6-26-C-POINTER-SOURCE — close only the C-style uintptr_t pointer-key lexical gap.** MAIN reviews exact two-file Researchb2b44 lexical repair descending from9f415, preserving existing C++ detectors/source IDs and pointer-only comment/string exclusion. Original37617279801 FALSE8/9 exposed a real quoted-string false positive and remains unaccepted. Bind all9 actual whole-module controls, all6 Research source/metadata inputs, explicit separate APP70096 locked pytest environment5packages/all5wheels and unchanged native CI carrier before hosted capture. This named lexical source correction does not establish arbitrary memoization absence, GPU timing/ranking, executable content-hash-memo corpus completeness, a kernel/protocol/grade change or parent RVP-C6-26 completion. Native companion: VB-RVP-C6-26-C-POINTER-CONFORMANCE. ✅ 2026-10-07 — [MAIN exact source/original9 acceptance](../../artifacts/ni08/c-pointer-literal-source-acceptance-20261007/README.md); Researchaefa, original TRUE9/9 and prior FALSE retained. Publication lease deviation recorded; parent/GPU/kernel gates unchanged.
- [x] Resolve the side-loaded ROCm 6.2 profiler-tool availability for C4. ✅ 2026-08-12 — live
  version checks confirm `rocprof`/`rocprofv2` at ROCProfiler 2.0 and a runnable argument parser for
  `rocm-bandwidth-test`. These tools are intentionally absent from the default PATH and `/opt/rocm`.
- [x] **AK-KB-1** — audit KernelBench for the GEAK-eval **C2** correctness surface ✅ 2026-08-11 —
      declined the incompatible task artifacts (current first-party HIP is gfx942/gfx950 and ROCm 7.1+),
      while retaining the already-native correctness and anti-hacking design rules above. The live
      gfx90a GEAK/AgentKernelArena round-trip is the compatible C2/C5 substrate.
- [x] Write P-GPU-1 measurement protocol before any GPU runs ✅ 2026-07-29 — human amendment ratified the canonical MI210 GPU protocol in [`MEASUREMENT.md`](../../MEASUREMENT.md#p-gpu-1--mi210-gpu-canonical-throughput-ratified-2026-07-19) on 2026-07-19; this closes protocol authoring only, not any GPU run or decision claim.
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
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:2399)* **Provide the exact k228 model-tensor capture hook manifest and run the governed capture.**
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:2402)* **Provide the exact k175 ordered multi-trace capture hook manifest and run the governed capture.**
- [x] Re-target the program objective from the Q8 rung to the fp16 rung, with a banded per-lever ceiling (K1–K12) ✅ 2026-08-03
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
- [x] Add FP8 as an authoring datatype target: gfx90a has no native FP8 MFMA, but an FP8-weight -> bf16-MFMA upcast GEMV is buildable and potentially bandwidth-valuable for memory-bound decode (half the weight bytes of bf16; compute upcast to bf16) — an experimental-kernel investigation, NOT a hard wall. NVFP4 microscaling (per HyRA k185) is the harder end; scope after the FP8-upcast path ✅ 2026-08-11 — `datatype_targets.py` exposes a non-numeric FP8-weight/software-upcast contract to Arena tasks, requires an independent decoder, exact-shape baseline, upcast-cost attribution and whole-model gate, forbids batch-one MFMA assumptions, and mechanically defers NVFP4 until the FP8 path has a terminal result.
- [x] **Add the governed execution bridge for the AK-LE-1/2 planner panel.** ✅ 2026-08-12 —
  research `98f642cd` compiles exact `ExperimentContract` model/quant/effort cells, resolves and
  hashes the Claude/Codex CLI, executes each cell in a captured read-only process group, and seals
  the exact prompt, argv, stdout, stderr, last message, timing, and strict parsed observation. It
  has observe-only authority and cannot mutate a campaign, rank, select a champion, or release.
  Focused runner tests passed **16/16**, the controller slice passed **487/487**, and the integrated
  canonical AutoKernel suite exited zero.
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
- [x] Recompute the full quant ladder on one consistent basis (fp16 62.6 / Q8_0 50.2 / Q4_K 35.1 / MoE-Q8 21.3 / MoE-IQ2 10.3) ✅ 2026-08-03 — via /research-intake Stage-2b; reproduces the fable5 series to within 1 pp
- [x] Correct the IQ2_XXS access characterization: four INDEPENDENT gathers (single 8-byte memcpy, ILP≈4) plus FOUR sign-table gathers, not a dependent pointer chase with one sign read ✅ 2026-08-03
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
  - **[superseded: inf48-triage 2026-11-09: Item C decoder no longer serves (stated in the box) and the 122B is retired; full text at b3bd883d3:3258]** **(no title)**
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
- [x] **Settle the gfx90a low-precision datapath at ISA level.** ✅ 2026-08-15 — gfx90a FP16 and
  INT8 MFMA have identical shape sets and peak rate; there is no FP8 or INT4 matrix path. Batch-one
  decode sits 31–113× below the measured ridge, so native-MFMA decode hypotheses have zero value on
  this die. Composable Kernel FP8 on gfx90a is fp32 emulation, not a datapath benchmark. Durable
  citations and assembly/toolchain checks are compiled in `wiki/hardware-optimization.md`.
  - *(folded into INF48-LIVE-7; full text at b3bd883d3:3365)* **TRIPWIRE — re-open low-quant VALU/occupancy work when an IQ-format role becomes GPU-resident.**
  - [x] **INF37-IQ-1 — Bind the latent-residency blocker into planner memory.** ✅ 2026-08-16 —
    research `5ae54e0ae4a80ab02450f703617b6a769599caf2` assigns zero current live-stack payoff,
    preserves the IQ mechanism as ineligible memory, and requires reprice on an IQ residency change.
    Automatic machine-trigger enforcement is owned by AutoKernel AK-ADM-1.
  - **[declined: ws58 2026-11-03 content-review: merged into the tripwire ("activate on the same trigger")]** **INF37-IQ-2 — On IQ residency, reprice with the levers now on file.** Activate on the same
    trigger. (1) AK-QL-7 unroll(disable) falsifier. (2) If the resident is an IQ2/IQ3 **MoE**: confirm the
    CDNA MUL_MAT_ID cutoff (IQ2_XXS `ne2<=5`, mmvq.cu:185-194 — unmeasured on gfx90a, intake-1410) at the
    recipe's verify widths, since `ne2>=6` also disables HIP graphs. (3) Optional: backport llama.cpp
- [x] **K1 — `onegraph` precondition check**: verify the Q-only / KV-shared / no-cross-position preconditions hold for our gemma-4-26B-A4B assistant-head drafter ✅ 2026-07-11 — all 3 satisfied
- [x] **K2 — HIP graph smoke-test + benchmark on MI210 ✅ 2026-07-11**: verified on the existing `build-hip` (`46f876c12`, `GGML_HIP_GRAPHS=ON`, ROCm 6.2 — **no rebuild needed**). HIP graph capture engages on MI210 gfx90a; gemma-4-26B-A4B MoE + gemma-4-31B dense both run correctly on HIP under MTP (~83–88% draft accept, output byte-identical graphs on/off). Graph A/B (`GGML_CUDA_DISABLE_GRAPHS`): **Q8 A4B decode +4.3% / spec-dec +25%**; dense-31B Q8 +6.1% / +3.4%; A4B **Q4 spec-dec −5% (graphs hurt — re-capture thrash)**. See "K2 Empirical Results" below. Per-decode capture only — the onegraph single-graph fold is still unimplemented.
- [x] **K3 — CPU warm-up-redundancy test ✅ 2026-07-11 (answered by the K1 audit — no action available)**: the onegraph insight is "the multi-position drafter warm-up is redundant." Our audit (Warm-up vs Draft Loop Equivalence, above) found that for the gemma4 `is_mem_shared` drafter the warm-up is **already zero-drafter-compute** (the catch-up decode block at `speculative.cpp:~1465` is entirely elided; only hidden-state copies remain). So there is **no redundant drafter warm-up to remove** on the CPU worker — it is already optimal. No CPU win available from this lever.
- [x] **K4 — drafter-α baseline ✅ 2026-07-16**: measured current acceptance α on the real task corpus before any fine-tuned-drafter investment; acceleration index records `summary.json` as decision-grade. Fine-tuning/control redesign remains gated by `feedback_measure_alpha_before_specdec_investment`.
- [x] **K5 — quality-gate wiring ✅ 2026-07-16**: implemented `MMLUProAdapter` (TIGER-Lab/MMLU-Pro, 12K questions, 10-choice A-J) + `v7_quality_gate_runner.py` (eval runner) + `v7_quality_gate_compare.py` (regression comparator). The fixed chat-endpoint harness under `epyc-inference-research` reran the gate successfully; the earlier raw `/v1/completions` attempt in `/mnt/raid0/llm/tmp/v7-quality-20260716/` was aborted as a Content-only protocol error and is not evidence. Valid artifacts: `/mnt/raid0/llm/tmp/v7-quality-20260716-chat/v6-production-worker-general.json`, `/mnt/raid0/llm/tmp/v7-quality-20260716-chat/v7-candidate-worker-general.json`, and `/mnt/raid0/llm/tmp/v7-quality-20260716-chat/v7_quality_gate_report.md`. Result: endpoint=`chat`, errors=`0`; v6 MMLU-Pro `73/200=36.5%`, GPQA `50/195=25.6%`; v7 candidate `8e5c555ab` MMLU-Pro `73/200=36.5%`, GPQA `50/195=25.6%`; comparator `PASS`, deltas `+0.0%` on both suites versus the `-5pp` threshold.
- [x] **K6 — `GGML_CUDA_GRAPH_OPT=1` lever ✅ 2026-07-11**: benchmarked on MI210 → **REJECTED** (net-negative: Q8 base −16%, spec −11%). Leave off (default).
- [x] **K9 — non-gemma4 graph generalization ✅ 2026-07-11**: Qwen3.6-27B (dense hybrid) + Qwen3.6-35B-A3B (MoE), native MTP. Base decode **+7–14%** (generalizes); native-MTP spec-dec only **+1.8–2.5%** (the +25% is gemma4-external-head-specific); Qwen native-MTP deterministic under load. See "Non-gemma4 generalization".
- [x] **K11 — gemma4 external-head MTP short-smoke determinism ✅ 2026-07-17; broad free-form gate reopened 2026-07-18**: the old short JSON closure remains valid but too narrow. **2026-07-16 preliminary evidence:** the new research runner (`scripts/benchmark/k11_gemma4_determinism_runner.py`) passed a GLM-download-contended 3-run fresh-server smoke on experimental v7: one output hash, `18/18` drafts accepted each run, artifact `data/k11_gemma4_determinism/k11_gemma4_determinism_20260716T194501Z/summary.json`. **2026-07-17 quiet-host repeat:** after GLM completed, the same runner passed 3 fresh sequential MI210 servers with one output hash (`5ebb69a089cc...`), `18/18` draft tokens accepted in every run, prompt `273.85-281.61 t/s`, and decode `148.58-149.59 t/s`; artifact `data/k11_gemma4_determinism/k11_gemma4_determinism_20260717Tquiet_glm_done/summary.json`. **2026-07-18 long exact-stop extension:** runner controls now cover `--spec-type none`, `--slots`, and exact repeated-word scoring. Report `data/k11_gemma4_determinism/k11_long_stop_condition_20260718Tcodex/k11_long_stop_condition_report.md` shows single-slot MTP passed `3/3` at `~158 t/s`, but multi-slot MTP failed an `n=10` long gate (`8/10` task pass, 3 output hashes), and no-spec GPU controls failed repeatedly. **Explicit-greedy attribution:** no-spec with `samplers=["temperature"]`, `top_k=0`, and `backend_sampling=false` still failed n=10 (`4/10` task pass, 3 hashes), so the ROCm `TOP_K` warning is unlikely to explain target-generation semantics. **Stop-string diagnostic:** adding a `stop=["END"]` payload made the no-spec explicit-greedy lane deterministic over 10 fresh servers, but the model emitted 512 repeated words and never emitted `END`, so this did not close task compliance. **Schema diagnostic:** request-level JSON schema closed the structured-output path: no-spec and external-head MTP each passed `10/10` fresh-server `word-array-200` runs with one hash; MTP decoded at mean `122.128 t/s` and accepted `97.3568-98.2301%` drafts. Treat external-head MTP as stable and fast for schema-constrained structured output, while free-form stop/termination remains open for a broad GPU-worker lane.
  - [x] **K11.1a — explicit-greedy no-spec attribution ✅ 2026-07-18**: `data/k11_gemma4_determinism/k11_long_nospec_explicit_greedy_np4_n10_20260718Tcodex/k11_explicit_greedy_report.md` shows CPU-side greedy request shape did not fix stop/count divergence; failures are 512-word cap hits or 289-word stops using only the requested word.
  - [x] **K11.1b — stop-string diagnostic instrument + negative result ✅ 2026-07-18**: runner now supports repeatable `--stop`; no-spec explicit-greedy with `stop=["END"]` produced one hash over `10/10` runs but still task-failed by never emitting `END` and hitting 512 repeated words.
  - [x] **K11.1c — JSON-schema structurally bounded diagnostic ✅ 2026-07-18**: runner now supports request-level `json_schema` via `--schema-task word-array-200`. No-spec explicit-greedy passed `10/10` with one hash and mean decode `76.577 t/s`; external-head MTP passed `10/10` with one hash, mean decode `122.128 t/s`, and `97.3568-98.2301%` draft acceptance. Reports: `data/k11_gemma4_determinism/k11_schema_word_array_nospec_np4_n10_20260718Tcodex/k11_schema_word_array_nospec_report.md` and `data/k11_gemma4_determinism/k11_schema_word_array_mtp_np4_n10_20260718Tcodex/k11_schema_word_array_mtp_report.md`.
  - [x] **K11.1d — current-build free-form GPU serving n=10 isolation ✅ 2026-07-18**: experimental v7 `d1e5a20eb` reran the exact 200-word free-form task with `--slots 4`. Backend-sampling-off MTP artifact `data/k11_gemma4_determinism/k11_gemma4_long_mtp_np4_n6_draft_backend_off_20260718T141719Z/summary.json` passed `6/6` with one output hash, exact `200` observed words in every run, median decode `159.18 t/s`, and stable `133/134` draft acceptance (`99.2537%`). Paired default-backend MTP n=6 artifact `data/k11_gemma4_determinism/k11_gemma4_long_mtp_np4_n6_default_backend_20260718T142021Z/summary.json` also passed `6/6` with the same output hash, median decode `159.05 t/s`, and the same acceptance. Current-build default-backend MTP n=10 confirmation `data/k11_gemma4_determinism/k11_gemma4_long_mtp_np4_n10_default_backend_current_20260718T142203Z/summary.json` reproduced the broad-lane defect: `9/10` task pass, `2` output hashes, one run overgenerated to `512` observed words with `340/341` accepted drafts while all other runs stayed exact at `200` words and `133/134` drafts. Current-build backend-off MTP n=10 confirmation `data/k11_gemma4_determinism/k11_gemma4_long_mtp_np4_n10_backend_off_current_20260718T142614Z/summary.json` also failed: `9/10` task pass, one run emitted `201` words with `135/136` accepted drafts. Current-build no-spec n=10 control `data/k11_gemma4_determinism/k11_gemma4_long_nospec_np4_n10_current_20260718T143112Z/summary.json` failed too: `7/10` task pass, `3` output hashes, two `289`-word outputs and one `512`-word runaway. This moves K11.1 root cause upstream of external-head MTP: the primary defect is a longer-run/intermittent Gemma4 free-form serving stop/count failure visible in GPU no-spec; MTP inherits it and changes the failure envelope.
  - [x] **K11.1e — CPU no-spec free-form control ✅ 2026-07-18**: direct fresh-server CPU control forced `--device none -ngl 0 --spec-type none` because, at the time of this run, the K11 runner exposed only the MI210 device shape. Artifact `data/k11_gemma4_determinism/k11_gemma4_long_nospec_cpu_device_none_np4_n10_20260718T143903Z/summary.json` ran the same `--slots 4`, 200-word free-form prompt for `10` fresh servers. Result: task pass `0/10`, `1` output hash, every run emitted only the requested `benchmark` token but hit `512` observed words with `finish_reason=length`, median decode `19.54 t/s`, and all server PIDs cleaned up. This proves the exact-count natural-language failure is not GPU-specific; GPU adds intermittent shorter stop modes (`289`/`512`), while CPU deterministically runs to the cap.
  - [x] **K11.1f — CPU/no-device control promoted into the runner ✅ 2026-07-18**: inference-research `scripts/benchmark/k11_gemma4_determinism_runner.py` now exposes `--target-device` and `--draft-device` while keeping the default MI210 lane unchanged. Dry-run artifact `data/k11_gemma4_determinism/k11_cpu_device_surface_dryrun_20260718Tcodex/` proves the first-class CPU/no-spec shape emits `--device none -ngl 0 --spec-type none` with no draft device. Focused tests passed: `python3 -m unittest scripts/benchmark/test_k11_gemma4_determinism_runner.py` (`15` tests). Future K11 CPU controls should use the runner, not hand-written one-off harnesses.
- [x] **K11.1g — UD-IQ4_XS source-head schema n=10 confirmation ✅ 2026-07-19**: corrected `1024`-token run `data/k11_gemma4_determinism/k11_schema_word_array_ud_iq4xs_mtp_np4_n10_currentv7_20260719Tmain_1024/summary.json` passed `10/10` fresh servers with one output hash, exact `word-array-200`, and `94.86-95.31%` draft acceptance. The first `512`-token attempt `data/k11_gemma4_determinism/k11_schema_word_array_ud_iq4xs_mtp_np4_n10_currentv7_20260719Tmain/summary.json` was deterministic but cap-truncated, so use the `_1024` artifact for the closure.
- [x] **K11.1h — UD-IQ4_XS external-MTP no-stop free-form n=3 confirmation ✅ 2026-07-19**: `data/gpu-mi210/gemma4_ud_iq4xs_mtp_freeform_termination_20260719T035436Z/summary.json` ran three fresh-server no-stop 200-word `benchmark` completions with the assistant-head drafter. It passed `3/3`, produced exactly 200 words every run with one output hash and no reasoning content, decoded at mean `126.33 t/s`, and accepted `133/134` drafts (`99.25%`) in every run. This is positive for no-stop bounded free-form UD serving, but it is not a substitute for the open n=10 broad/free-form and stop-string root-cause gate.
- [x] **K11.1i — UD-IQ4_XS external-MTP no-stop free-form n=10 post-candidate confirmation ✅ 2026-07-20**: post-candidate experimental build `12a292f0c21d` reran the actual no-schema exact-count free-form shape at `data/k11_gemma4_determinism/k11_freeform_ud_iq4xs_mtp_n10_post_candidate_20260720T063000Z/summary.json`. It passed `10/10` fresh servers, produced exactly 200 `benchmark` words with one output hash, decoded at mean `126.44 t/s` (`124.06-127.51`), and accepted `1330/1340` drafts (`99.25%`). This narrows K11.1: no-stop exact-count free-form is now stable on the post-candidate build, but stop-string/termination semantics and ORIG-vs-UD quality retention remain open. The row is not frozen-v7 promotion evidence.
- [x] **K11.1j — stop-string n=10 positive repeat + ORIG comparison ✅ 2026-07-20**: concurrent-with-PC-4o MI210 stop-string runs used `stop=["END"]`, four slots, assistant-head MTP, and the same exact 200-word prompt. UD-IQ4_XS artifact `data/k11_gemma4_determinism/k11_stop_end_ud_iq4xs_mtp_n10_concurrent_pc4o_20260720T084818Z/summary.json` passed `10/10` with one output hash, exact 200 words, mean decode `113.738 t/s`, and `1333/1340` accepted drafts (`99.48%`). ORIG-Q4 artifact `data/k11_gemma4_determinism/k11_stop_end_orig_q4_mtp_n10_concurrent_pc4o_20260720T085122Z/summary.json` also passed `10/10` with one output hash, mean decode `141.788 t/s`, and `1330/1340` accepted drafts (`99.25%`). This narrows the stop-string defect, but the evidence is observation-grade because the CPU PC-4o bench overlapped, and ORIG-Q4 is materially faster than UD-IQ4_XS on this slice.
- [x] **K11.1k — natural free-form ORIG-vs-UD clean comparison ✅ 2026-07-20**: isolated MI210 fresh-server natural-prose prompt used `stop=["END"]`, four slots, assistant-head MTP, and no concurrent CPU/GPU bench. Aggregate summary: `data/k11_gemma4_determinism/k11_natural_freeform_compare_20260720T0937Z.summary.json`. ORIG-Q4 artifact `data/k11_gemma4_determinism/k11_natural_freeform_orig_q4_mtp_n10_clean_20260720T093339Z/summary.json` completed `10/10` runs but failed determinism with `9` output hashes, mean decode `108.702 t/s`, mean acceptance `0.5279` (`906/1720`), and `0/10` exact 160-word runs (`152-159` words observed). UD-IQ4_XS artifact `data/k11_gemma4_determinism/k11_natural_freeform_ud_iq4xs_mtp_n10_clean_20260720T093527Z/summary.json` completed `10/10` but failed determinism with `10` output hashes, mean decode `89.548 t/s`, mean acceptance `0.5608` (`953/1702`), and `1/10` exact 160-word runs (`152-160` words observed). Cleanup proof after both arms showed no KFD PIDs and no live llama processes. Verdict: broad natural free-form serving is still policy-blocked; ORIG is faster than UD on this realistic slice, and UD is not a worker replacement.
- [x] **K11.1l — natural free-form explicit-greedy repeat CLOSED NEGATIVE ✅ 2026-07-20**: isolated MI210 fresh-server repeat added request-level explicit-greedy plus `--no-spec-draft-backend-sampling` to the same natural 160-word prompt. Comparison artifact: `data/k11_gemma4_determinism/k11_natural_freeform_explicit_greedy_compare_20260720T1059Z/summary.json`. ORIG-Q4 still failed with `10` output hashes, `0/10` exact 160-word runs, mean decode `91.154 t/s`, and `879/1750` accepted drafts (`50.23%`). UD-IQ4_XS also failed with `10` hashes, `0/10` exact 160-word runs, mean decode `77.966 t/s`, and `950/1734` accepted drafts (`54.79%`). Explicit-greedy/backend-off does not repair natural prose; future K11 work needs a sampler/control fix or stricter task templating, not more same-shape reruns.
- [x] **K11.1m — token-divergence instrumentation landed ✅ 2026-07-20**: inference-research `scripts/benchmark/k11_gemma4_determinism_runner.py` now exposes opt-in `--trace-token-divergence`, `--trace-n-probs`, `--trace-post-sampling-probs/--no-trace-post-sampling-probs`, and repeatable `--trace-response-field`. Trace mode requests server token/probability metadata without changing the default payload, writes compact `token_traces/run_XX.tokens.json`, records finish reasons and content/reasoning word counts, and reports common-prefix / first-divergent-token metadata in `summary.json` when the server returns token identities. Focused tests passed: `python3 -m unittest scripts/benchmark/test_k11_gemma4_determinism_runner.py` (`21` tests), `py_compile`, and `git diff --check`. This is an instrumentation checkpoint only; no inference result or lane admission claim.
- [x] **K11.1n — traced no-spec isolation CLOSED NEGATIVE ✅ 2026-07-20**: trace triad artifact `data/k11_gemma4_determinism/k11_natural_freeform_trace_compare_20260720T1139Z/summary.json` reran the ORIG-Q4 natural 160-word prompt with explicit-greedy/token tracing. MTP+np4 failed with `10` hashes, mean decode `89.81 t/s`, first all-run divergence after 7 tokens (`deterministic cleanup is a critical component of`; `maintaining` 9x vs `a` 1x). No-spec+np4 also failed with `9` hashes, mean decode `69.75 t/s`, and the same 7-token branch. No-spec+np1 failed with `10` hashes, mean decode `69.86 t/s`, first all-run divergence after 16 tokens (`... efficient inference service. when`; `serving` 5x vs `a` 5x). All runs returned `finish_reason=stop`, produced token traces from `__verbose.tokens`, and cleaned up with no KFD PIDs. Verdict: external-head MTP and multi-slot scheduling are not required to reproduce natural-prose nondeterminism; next work should inspect GPU no-spec sampler/backend deterministic tie-breaking or run a CPU no-spec traced control if GPU backend remains suspect.
- [x] **K11.1o — CPU no-spec traced control CLOSED ✅ 2026-07-20**: CPU-only ORIG-Q4 control artifact `data/k11_gemma4_determinism/k11_natural_freeform_orig_q4_cpu_nospec_np1_explicit_greedy_trace_20260720T114120Z/summary.json` reran the same natural 160-word prompt with `--spec-type none`, `--slots 1`, `--device none`, `-ngl 0`, explicit-greedy request controls, and token tracing. It completed `10/10` runs with one output hash (`f0eded78...`), deterministic token sequences (`all_token_sequences_identical=true`, common prefix length `182`, no first divergence), `finish_reason=stop` for all runs, fixed `156`-word outputs, and mean decode `21.12 t/s`. Paired compare artifact `data/k11_gemma4_determinism/k11_natural_freeform_trace_compare_20260720T1139Z/summary.json` now shows GPU MTP/no-spec/np1 diverges while CPU no-spec np1 is byte-identical. Verdict: the broad natural-prose defect is GPU/backend-path dependent, not external-head MTP or multi-slot scheduling alone; next work should inspect GPU backend deterministic reductions/logit handoff/tie-breaking.
- [x] **K11.1p — GPU backend-path A/B narrowed CLOSED NEGATIVE ✅ 2026-07-20**: compare artifact `data/k11_gemma4_determinism/k11_gpu_backend_path_ab_20260720T1204Z/summary.json` used pre-sampling `top_logprobs` on the same ORIG-Q4 no-spec single-slot natural prompt. Corrected graphs-on/FA-on GPU trace failed with `10` hashes, mean decode `72.52 t/s`, first divergence at token index `16` (` a` x4 vs ` serving` x6), with top-1/top-2 logprob gaps `0.0587-0.5555`; the first default-prompt attempt was invalid and moved to `/tmp/k11_invalid_default_prompt_20260720T115054Z`. Graphs-off (`GGML_CUDA_DISABLE_GRAPHS=1`) still failed with `10` hashes, mean decode `66.48 t/s`, first divergence at index `7` (` a` x2 vs ` maintaining` x8). FA-off still failed with `9` hashes, mean decode `79.61 t/s`, first divergence at index `16` (` a` x5 vs ` serving` x5). Verdict: graph replay and flash-attention are not sufficient explanations; remaining root cause is broader GPU backend numerical nondeterminism or logits copy/handoff. Harness support landed in inference-research commits `480b6243` (`--server-env`) and `12239ec3` (`--flash-attn`).
- [x] **K11.1q — default-off TopK-MoE fusion kill switch source prep ✅ 2026-07-20**: experimental-v7 post-candidate source now exposes `GGML_CUDA_DISABLE_TOPK_MOE_FUSION=1` in `ggml/src/ggml-cuda/ggml-cuda.cu`, skipping only the CUDA/HIP TopK-MoE fusion block inside `ggml_cuda_try_fuse` while leaving all behavior unchanged when unset. This is a compile-validated diagnostic switch, not a runtime verdict: `git diff --check -- ggml/src/ggml-cuda/ggml-cuda.cu` passed, `cmake --build build-hip --target llama-server -j 8` passed, and `strings build-hip/bin/libggml-hip.so` confirms the env key is present. GitNexus re-index failed with a native `Napi::Error` abort, so impact analysis is degraded and recorded as unavailable rather than claimed. Next GPU K11 trace should run the same ORIG-Q4 no-spec single-slot natural prompt with only this env set, then compare hash count, first divergent token, and pre-sampling top-logprob gap against K11.1p.
- [x] **K11.1r — TopK-MoE fusion-off runtime trace CLOSED NEGATIVE ✅ 2026-07-20**: reran the same ORIG-Q4 no-spec single-slot natural 160-word prompt with only `GGML_CUDA_DISABLE_TOPK_MOE_FUSION=1` set. Artifact: `data/k11_gemma4_determinism/k11_natural_freeform_orig_q4_gpu_nospec_np1_topk_moe_fusion_off_20260720T130746Z/summary.json`. Result: `task_passed=false`, `deterministic=false`, `10` output hashes, content word counts `149,158,154,158,158,156,154,159,155,158`, all `finish_reason=stop`, mean decode `69.704 t/s`, and first divergence at token index `7` (`maintaining` x9 vs `a` x1). TopK-MoE fusion is therefore not sufficient to explain or repair the GPU natural-prose nondeterminism.
- [x] **K12 — `GGML_CUDA_Q8_PREFETCH` 0/1/2 benchmark ✅ 2026-07-11**: net-negative on all 4 Q8 models → keep OFF (default). Dense hurt most (Qwen-27B −12/−18%, gemma4-31B −6/−7.5%); MoE marginal/noisy (gemma4-A4B −3.5/−0.3%, Qwen-35B-A3B +4.2/+3.1%). qwen-27b server relaunched graphs-ON + prefetch-off + MTP (draft-mtp n-max 3, ~91% accept). See "Kernel-Optimization Levers → Q8_PREFETCH".
- [x] **K14 — v7 HIP backend-ops failure triage ✅ 2026-07-16**: resolved the MI210 `test-backend-ops` abort in `experimental-v7-candidate` with scoped flash-attn selector/device-guard fixes in `fattn.cu`, `fattn-tile.cuh`, and `fattn-mma-f16.cuh`. Focused validation passed for the 192/128, 256/256 short-KV, 320/256, and BF16 hsk64 families; full HIP validation passed with candidate `LD_LIBRARY_PATH`: `ctest --test-dir build-hip/tests -R '^test-backend-ops$' --output-on-failure` → `100% tests passed, 0 tests failed out of 1`, `722.34 sec`. A transient `SOLVE_TRI` tolerance miss was isolated to HIP `hipblasStrsmBatched` randomness; the exact case passed 20/20 repeats and the full rerun passed, with no `SOLVE_TRI` code/test tolerance change.
- [x] **K15 — ngram-mod retest on MI210 ✅ 2026-07-16**: quiet-card retest on `4e9287eb3` shows workload-dependent speed upside. Qwen2.5-Coder-0.5B repetitive JSON edit: `292.5 -> 347.7 t/s` (+18.9%). Gemma-4-26B-A4B Q4 with default reasoning: `85.4 -> 85.8 t/s` (flat, because output was reasoning text). Gemma-4-26B-A4B Q4 with `--reasoning off`: `85.7 -> 129.1 t/s` (+50.6%). **Caveat:** outputs were not token-identical and both Gemma arms had JSON/key errors, so this is speed evidence only; do not enable by default without task-level quality/acceptance checks.
- [x] **K16 — orchestrator worker combined ngram→MTP launch ✅ 2026-07-16**: deployed the conservative single-server policy instead of redundant lanes. `worker_general` / `worker_math` / `toolrunner` now launch one combined speculative stack, `--spec-type ngram-mod,draft-mtp`, on ports `8072`, `8082`, `8182`, `8282`, and `8382`; live cmdlines verified at PIDs `1053926`, `1054354`, `1054723`, `1055049`, and `1055416`. Source of truth is the research master registry plus regenerated lean registry, descriptors, stack priors, and operator summary. AutoPilot remains stopped. This is not a planner tunable yet; task-level quality/acceptance monitoring decides whether the combined default stays.
- [x] **K13 refresh checkpoint ✅ 2026-07-16**: upstream freshness was restored by `experimental-v7-refresh-20260716` (`8e5c555ab`) merged with `origin/master` `a8dc0e326`; `Q2_0` is now present again on the refreshed v7 candidate, with the K14 backend-ops fix retained at `99f3fffd6` and validation passing on the candidate `build-hip`. The Bonsai smoke-test remains open below.
- [x] **K13 — Bonsai/Ternary smoke and first quality gate ✅ 2026-07-17**: Bonsai-27B Q1_0 loads on stock experimental v7 CPU and MI210, but the corrected quiet-host prompting gate passed only 6/8 strict probes, so Q1_0 is loadable/partially coherent but not role-ready. Ternary Q2_g64 also loads on CPU and MI210 and passed 6/8, with a speed-only `ngram-mod` signal; it is not role-ready. Ternary Q2_0 is not an ordinary pending smoke: the loader rejects a structured tensor offset mismatch before prompt execution, so it is blocked on producer-layout or compatibility-loader investigation.
- [x] **K13a — Ternary Bonsai Q2_0 offset-mismatch audit ✅ 2026-07-17**: read-only follow-up classified the Q2_0 load failure as an artifact/layout incompatibility, not a bad command or ordinary incomplete download. The v7 loader rejects `output_norm.weight` at offset `337715200` vs expected `357580800` before prompt execution; the local file size matches HF metadata and offsets are structured, so evidence favors noncanonical Q2_0 packing under standard `GGML_TYPE_Q2_0` rather than corruption. Do not rerun Q2_0 smokes until the producer layout is verified or an experimental compatibility loader is scoped. Q2_g64 remains the usable Ternary runtime path, but its quality gate is still not role-clean.
- [x] **K17 — v7 perf/server A/B + launcher guard ✅ 2026-07-16**: production-shaped measurements on the refreshed v7 candidate `8e5c555ab` are recorded in `/mnt/raid0/llm/tmp/v7-perf-20260716/v7_perf_ab_20260716.md` and the server JSON artifacts under `/mnt/raid0/llm/tmp/v7-perf-20260716/`. Direct base-decode results: worker Gemma CPU prod `12.5634 t/s` vs v7 `12.2010` (`-2.88%`); frontdoor Qwen3.6 CPU prod `8.8559` vs v7 `8.2757` (`-6.55%`); v7 worker GPU standalone `86.7806 t/s`. Fresh-server `worker_general` ngram+MTP A/Bs: production default-temp `65.6846` / `69.5352 t/s`; v7 hidden-ROCm/default `67.9978` / `68.2169 t/s`; identical output hashes and draft counters (`500` accepted / `1172` generated on measured reps). HIP-visible v7 default on CPU role regressed to roughly `34-39 t/s` and touched ROCm despite `-ngl 0`; device-hidden/default restored parity. The earlier resident production `~127 t/s` was not reproduced on a fresh production server and is treated as a resident-state outlier, not the baseline. Launcher validation in `epyc-orchestrator/scripts/server/orchestrator_stack.py` passed with `107` tests and `3` warnings.
- [x] **K18 — K5 quality + readiness checkpoint ✅ 2026-07-16**: fixed-chat K5 rerun passed with comparator `PASS` and zero errors; the invalid raw-completions attempt is discarded. Promotion-gate no-inference checks also passed after refreshing generated stack artifacts (`summary: ok`, promotion gate `181` passed, acceptance no-inference checks passed). The corrected MI210 sidecar showed the earlier no-device result was a wrong-library false negative: with `LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin`, v7 `llama-bench` sees `ROCm0`, reports `backends="ROCm"` / `gpu_info="AMD Instinct MI210"`, and measured Gemma3 1B Q8 generation at `197.773 tok/s` with sampled GPU use `99%`. CPU-only temp servers and sidecar bench processes were stopped after the run; `pgrep` for `18072`, `18073`, `v7_quality_gate`, `llama-bench`, and `llama-cli` found no live process beyond the shell, and `rocm-smi` showed `0%` / no KFD PIDs. This closes the checkpoint readiness evidence for v7; no additional long inference remains queued from this checkpoint.
- [x] **K19 — v7 all-family server-smoke checkpoint ✅ 2026-07-16**: recorded the completed smoke run from `/mnt/raid0/llm/tmp/v7-server-smoke-20260716T153522Z/summary.json`. Rebuilt v7 HIP binary reports `version: 10075 (8e5c555ab)`; `LD_LIBRARY_PATH` was pinned to `build-hip/bin` so shared libraries resolved from `/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin` instead of production. All six production families passed: frontdoor `Qwen3.6`, worker_general `Gemma4+assistant draft` with `ngram-mod,draft-mtp`, architect `Qwen3.5-122B`, ingest_long_context `Qwen3-Next`, worker_vision `Qwen2.5-VL+mmproj`, and vision_escalation `Qwen3-VL+mmproj`. Structured-output schema passed for all six. Vision image smoke passed for both vision roles. Frontdoor and architect required production-style `chat_template_kwargs` `enable_thinking=false` reruns so output landed in `message.content`; direct raw chat without kwargs emitted `reasoning_content` only. All temp server PIDs were verified dead after stop.
- [x] **K20 — v7 production-path speed A/B clarification ✅ 2026-07-16**: separated base-decode guards from production server/speculative path evidence. Baseline `llama-bench` guard artifacts live in `/mnt/raid0/llm/tmp/v7-perf-20260716-postsmoke/`: architect base decode prod `5.848182 t/s` vs v7 `5.307566` (`-9.24%`), ingest base decode prod `13.886879` vs v7 `14.016139` (`+0.93%`). These are non-spec guard cells, not MTP/NEXTN coverage. Production server-path artifacts live in `/mnt/raid0/llm/tmp/v7-spec-server-ab-20260716T155208Z/summary.json` and `/mnt/raid0/llm/tmp/v7-ingest-server-ab-20260716T155557Z/summary.json`: frontdoor `draft-mtp` prod `34.599352 t/s` vs v7 `33.866551` (`-2.12%`) with matched measured draft acceptance (`219/319`); architect `draft-mtp` prod `19.343445` vs v7 `19.295712` (`-0.25%`) with matched measured draft acceptance (`194-195/240`); ingest_long_context production Qwen3-Next server path prod `23.521174` vs v7 `23.272615` (`-1.06%`) with the stack launch's `qwen3next.expert_used_count=int:4` override. All sidecar server PIDs were verified dead after stop. Interpretation: v7's production server/speculative paths are near parity, while architect's non-spec base-decode regression remains a guardrail risk to track rather than the production-path result.
- [x] **K21 — v7 performance-feature inventory and measured-runtime-scope audit ✅ 2026-07-16**: v7 does carry performance-oriented codepaths, but this is not promotion approval and the evidence is narrower than "v7 is faster everywhere." Present/retained features: per-decode HIP graph capture on MI210 (`GGML_HIP_GRAPHS=ON`), refreshed upstream speculative/MTP/NEXTN machinery with combined `ngram-mod,draft-mtp`, restored upstream freshness including `Q2_0`, and the K14 flash-attn backend-op fix that lets the HIP backend validation complete. Rejected or not landed as wins: `GGML_CUDA_GRAPH_OPT=1`, Q8 prefetch, the shape-aware graph key, and the onegraph single-graph fold. Quality coverage now includes the production CPU worker's combined `ngram-mod,draft-mtp` path: the K5 chat gate passed v6 and v7 with identical MMLU-Pro/GPQA scores and zero errors. Performance evidence says CPU-pinned production server/speculative paths are near parity, not a broad speedup; MI210 exact production-vs-v7 A/B is not available under the frozen production-kernel rule because the current production comparator is CPU-only, but v7 MI210 functionality and standalone speed sanity were captured under K18. Gemma4 external-head MTP on GPU remains a future GPU-worker-lane gate, not a blocker for the currently measured CPU-pinned runtime scope.
- [x] **K22 (P0, correctness) — grammar-sampler crash fix ✅ 2026-07-16**: fixed on experimental v7 commit `96986f5e9` (`Fix grammar prefill for plain JSON schema`). Root cause: plain CLI `--json-schema` output-format grammars constrain generated JSON only, but the v7 prefill path tried to accept the chat generation prompt into that grammar; server `response_format` passed because its chat-template/tool-call grammar includes that prefix. The fix makes `common_grammar_needs_prefill()` return true only for chat-template/tool-call grammars, adds a sampler-policy regression test, and updates the sampling comments. Validation: rebuilt `build-hip` targets `test-sampling`, `test-json-schema-to-grammar`, and `test-chat`; `test-sampling` passed, `test-json-schema-to-grammar` passed with Python subtests skipped because `python` is unavailable, and `test-chat` passed when `LD_LIBRARY_PATH` was pinned to the experimental `build-hip/bin`. Subagent also verified CPU Qwen3-0.6B and MI210 Qwable IQ4_XS bounded schema smokes no longer hit sampler init crash. Production v6 untouched.
- [x] **K23 (P0, correctness) — GLM-5.2 glm-dsa load/runtime reconciliation + coherence smoke ✅ 2026-07-17**: `LLM_ARCH_GLM_DSA` ("glm-dsa") exists in-tree and GLM-5.2 UD-IQ2_M reports `general.architecture=glm-dsa`. Pre-fix source only constructed `llama_kv_cache_dsa` for `LLM_ARCH_DEEPSEEK32`, not `LLM_ARCH_GLM_DSA`; experimental-v7 commit `3dee86a5a` closes that gap by wiring GLM to `llama_kv_cache_dsa`, aliasing `llama_model_deepseek32::graph`, requiring live GLM indexer tensors, and force-building GLM indexer Hadamard rotation tensors. Validation: `test-llama-archs --arch glm-dsa`, `test-llama-archs --arch deepseek32`, ASAN `glm-dsa`, rebuilt HIP server/CLI, and current-source exact `READY` GLM smoke at `/mnt/raid0/llm/tmp/glm52-current-source-ready-smoke-20260717T092344/` passed with main + indexer DSA caches and `Lightning Indexer enabled`. **2026-07-16/17 stale-binary evidence:** artifact integrity closed, short CPU smoke passed (`READY`), 4K/8K traces and a true >64K run recorded `glm-dsa`, `indexer.top_k` metadata/override, expected NextN-tail skipping, and `Lightning Indexer enabled`; true >64K processed `65969` prompt tokens at `6.76 t/s` prompt eval and `1.20 t/s` decode (`/mnt/raid0/llm/tmp/glm52-dsa-true64k-probe-20260717T0125/`). Those artifacts were generated by a `build-hip` binary self-reporting `9d70bae4b`, so they close stale-binary runnability/scaling only. **2026-07-17 static audit:** generic DSA final MLA attention builds a full-length `kq_mask_top_k` and calls `build_attn_mha()` over full cached K/V; no sparse gather was found. Follow-on remains open in the GLM/DSA handoffs for sparse-attention implementation/profiling plus current-source long-context quality/needle.
  - [x] **K23.1 / B6 — GLM-DSA native-MTP scaffold + serving repair ✅ 2026-07-19**: experimental-v7 commit `d6706a612` exposes `t_h_nextn` from the shared DeepSeek32/GLM-DSA target graph when NextN layers exist, loads the physical GLM-5.2 `blk.78` NextN tail tensors, and adds a real GLM-5.2 single-NextN `glm-dsa` `LLM_GRAPH_TYPE_DECODER_MTP` graph that combines Qwen-style NextN projection/norm flow with the GLM-DSA/MLA/MoE tail block. The first real generated-token A/B found a zero-chunk `draft-mtp` failure; the 2026-07-19 DeepSeek32/GLM-DSA unmasked-NEXTN row-selection repair superseded it on the matched retry: `512` completion tokens, `5.33 t/s` decode vs no-spec `2.49 t/s`, draft alpha `0.933` (`376/403` accepted). The promotion-source hardening assertion also landed in `test-llama-archs`, proving GLM-DSA unmasked NEXTN retains all target rows through `h_nextn` before output-row selection; focused `glm-dsa` and `deepseek32` tests passed. This closes B6 serving/throughput/source hardening, not reviewer quality/admission.
- [x] **K24 (P0-adjacent, promotion guardrail) — root-cause v7 non-spec base-decode regression ✅ 2026-07-17**: the large K17/K20 non-spec guardrail deltas were measurement/host-state artifacts, not a validated v7 source regression. Original cross-run concern: architect `-9.24%`, frontdoor `-6.55%`, worker `-2.88%` vs v6, while server/spec paths were already near parity (K20: frontdoor draft-mtp `-2.12%`, architect `-0.25%`). **2026-07-17 read-only audit:** highest-confidence source suspects were experimental commit `3c2696b88` (`gfx90a: bf16 GDN recurrent-state`) and secondary `90e0f5cfc` fused-op resolution, but HIP-enabled v7 build vs CPU-only production was a validation confound. **K24.1:** fresh CPU-only experimental-v7 artifact (`build-k24-cpu`, `9d70bae4b`) separated the HIP-build confound. **K24.4:** paired quiet production-vs-current-v7 CPU rerun at `/mnt/raid0/llm/tmp/k24-paired-quiet-20260717T074502Z/` measured frontdoor `8.5756 -> 8.3491 t/s` (`-2.64%`), architect `3.6477 -> 3.5364 t/s` (`-3.05%`), and ingest `9.7992 -> 9.8971 t/s` (`+1.00%`). The same run showed current production itself is far below the old 07-16 production guard cells (architect old `5.8482`, ingest old `13.8869`), so the big regression is a host/runtime repeatability issue. Source bisect against `3c2696b88`/`90e0f5cfc` is retired unless a future same-host paired run exceeds the promotion threshold.
  - [x] K24.1 Build/run a CPU-only experimental-v7 artifact for the same non-spec CPU guard cells to separate source regression from HIP-enabled binary configuration. ✅ 2026-07-17
  - [x] K24.2 Source-bisect gate against parent of `3c2696b88` retired: same-host paired K24.4 falsified the large v7-source regression premise. ✅ 2026-07-17
  - [x] K24.3 Fused-op source-bisect gate against parent of `90e0f5cfc` retired under the same paired-run result. ✅ 2026-07-17
  - [x] K24.4 Repeat the architect/frontdoor/ingest CPU guard cells in one quiet, paired production-vs-current-v7 run before source bisection; do not treat 07-16 vs 07-17 cross-host-state deltas as kernel evidence. ✅ 2026-07-17
- [x] **K25 (P1, GPU) — mmvq draft-tree verify-width routing validation ✅ 2026-07-17**: source audit found the implementation side is already present on experimental v7: `ggml/src/ggml-cuda/mmvq.cu:281` `ggml_cuda_should_use_mmvq()` returns `ne11 <= 1` for CDNA2 `GGML_TYPE_Q8_0`, so Q8_0 verify widths `ne11 >= 2` already route away from MMVQ to MMQ. Low-level and accepted end-to-end route proofs now confirm `ne11=1` goes to MMVQ and accepted draft-tree verify widths `ne11=2..9` plus `33` go to MMQ. Economics still fail because MI210 external draft-tree is slower than the no-spec resident frontdoor path.
  - [x] **K25.1 low-level route/correctness proof ✅ 2026-07-17**: sidecar artifact `/mnt/raid0/llm/tmp/k25-mmvq-verify-width-20260717-a/` used experimental `LD_LIBRARY_PATH` and ROCm0 `test-backend-ops` + `rocprofv2` on Q8_0 `MUL_MAT` for `n=1..8`. Correctness CSV passed all selected cases (`test_mul_mat` CPU reference, local max NMSE threshold `5e-4`). Kernel-name summary proves `n=1` uses `mul_mat_vec_q` while `n=2..8` use `mul_mat_q`; dispatch means for `n=2..8` were ~`10.16-11.20 us`. Cleanup verified no `llama-server`, profiler, benchmark process, or KFD PID.
  - [x] **K25.2 end-to-end draft-tree route proof ✅ 2026-07-17**: existing Stage-1 artifact shows accepted draft-tree behavior (`508/508`, mean len `2.00`, throughput fail `0.915x`) but does not log per-verify `ne11` or kernel route. Prove widths `3..8` either by instrumenting/logging `src1->ne[1]`, `src0->type`, GPU arch, and selected MMVQ/MMQ route at `ggml_cuda_should_use_mmvq()`, or by profiling a server request forced to wider `--spec-draft-n-max` and correlating request-time kernel names.
    - [x] **K25.2a forced draft-tree e2e attempt falsified ✅ 2026-07-17**: sidecar artifact `/mnt/raid0/llm/tmp/k25-mmvq-drafttree-e2e-20260717T101243Z/` launched widths `3..8` against Qwen3.6-27B Q8 + MTP Q8, but every step logged `returning 0 greedy tokens`; `spec_draft` stayed empty, so `server-context.cpp` used the non-speculative batch path and no target verify batches at widths `3..8` occurred. HIP runtime traces saw both `mul_mat_q` and `mul_mat_vec_q` in the process, but not correlated to verify batches. Treat as negative evidence for that forced config, not a route proof.
    - [x] **K25.2b env-gated Q8_0 route logging landed ✅ 2026-07-17**: experimental-v7 commit `9882c2c69` adds `GGML_CUDA_LOG_MMVQ_ROUTE=1` diagnostics in `ggml/src/ggml-cuda/mmvq.cu` and `ggml/src/ggml-cuda/ggml-cuda.cu`. Default behavior is silent. Pinned `test-backend-ops` smoke at `/mnt/raid0/llm/tmp/k25-route-log-smoke-20260717T102617Z/` proves `n=1` logs `use_mmvq=1` + `route=MMVQ`, and `n=4` logs `use_mmvq=0` + `route=MMQ`; all rows supported. Next e2e attempt should use this env flag and a prompt/config that actually yields draft tokens.
    - [x] **K25.2c accepted draft-tree route proof ✅ 2026-07-17**: manual external-draft server artifact `/mnt/raid0/llm/tmp/k25-mmvq-route-external-only-20260717T211050Z/` pinned experimental `LD_LIBRARY_PATH`, enabled `GGML_CUDA_LOG_MMVQ_ROUTE=1`, and generated accepted draft-tree traffic (`draft_n=120`, `draft_n_accepted=96`, decode `40.55 t/s`). Route logs show Q8_0 `ne11=1` dispatching to MMVQ and Q8_0 verify widths `ne11=2..9` plus `33` dispatching to MMQ. This closes the route-proof question; the separate Stage-2 economics gate still fails because MI210 external draft-tree is slower than the no-spec resident frontdoor path.
- [x] **K26 (P1, GPU, config-only) — f16-vs-bf16 KV-cache bench ✅ 2026-07-17**: measured four KV dtype arms on MI210 with Qwen3.6-35B-A3B-MTP-Q8_0 (`9d70bae4b`, artifact root `/mnt/raid0/llm/tmp/k26-kv-cache-bench-20260717-codex/`). `llama-bench` decode: `f16/f16 100.013 t/s`, `bf16/f16 12.936`, `f16/bf16 12.885`, `bf16/bf16 80.896`. Server decode median across three short prompts: `f16/f16 104.375 t/s`, `bf16/f16 91.100`, `f16/bf16 88.213`, `bf16/bf16 100.224`. Prompt-processing bench: `f16/f16 2256.079 t/s`, `bf16/f16 1110.047`, `f16/bf16 531.281`, `bf16/bf16 2253.098`. Verdict: do not switch defaults to BF16 KV; `bf16/bf16` is close but not faster, and mixed K/V BF16 is a large regression. Output quality was not gated here; prompts showed normal reasoning preambles, so treat this as config-performance evidence only.
- [x] **K27.1 — Q8_0 8x8 generic probe gated off by default ✅ 2026-07-17**: added Q8_0 8x8 repack/gemv/gemm plumbing on experimental v7 (`ggml/src/ggml-cpu/repack.cpp`, `repack.h`) behind explicit opt-in `GGML_REPACK_Q8_0_8X8=1`. Clean same-host Qwen3-4B Q8_0 CPU-only smoke with experimental `LD_LIBRARY_PATH` pinned: default-off stays plain CPU (`CPU model buffer 4076.43 MiB`, prompt `209.66 t/s`, decode `8.10 t/s`); opt-in selects `CPU_REPACK` and logs `repack tensor ... with q8_0_8x8`, but regresses prompt to `17.34 t/s` and decode to `7.65 t/s`. Verdict: generic scalar x86 Q8_0 8x8 is a correctness-feasible experiment but **not promotable/default-safe**.
- [x] **K27.3 — default Q8_0 iqk routing to native, old path kept opt-in ✅ 2026-07-17**: experimental-v7 commit `aebb556b1` changes `GGML_IQK=1` so `GGML_TYPE_Q8_0` falls through to native CPU kernels unless `GGML_IQK_Q8_0=1` is explicitly set; all other iqk-supported quant families remain under the existing `GGML_IQK` gate. Final pinned CPU artifact `/mnt/raid0/llm/tmp/k27-q8-policy-final-20260717T105344Z/`: frontdoor Qwen3.6-35B Q8 default/native `21.38 t/s`, old iqk Q8 opt-in `20.98 t/s`, stock no-iqk `21.05 t/s`; Qwen3-4B Q8 still favors old iqk opt-in (`9.14` vs `8.90 t/s`). Verdict: this is a stack/frontdoor-safe routing policy, not a universal optimized x86 Q8 kernel. Keep K27 parent open for a real AVX2/AVX512/VNNI implementation; use `GGML_IQK_Q8_0=1` only on lanes with model-specific evidence.
  - [x] **K27.4 — x86 Q8 microkernel scoping audit ✅ 2026-07-18**: read-only sidecar confirmed K27 is not a bounded low-risk hookup. Stock x86 Q8_0 is still the single-output vec-dot path (`ggml/src/ggml-cpu/arch/x86/quants.c:1308` wired from `ggml-cpu.c:271`), CPU_REPACK has scalar Q8_0 bodies and no x86 selector branch (`repack.cpp:1275`, `:2281`, `:4723`), and the real fast path is the existing iqk Q8 route gated by `GGML_IQK=1 GGML_IQK_Q8_0=1` (`iqk_dispatch.cpp:70`, `:136`; `iqk_mul_mat.cpp:280`; `iqk_gemm_legacy_quants.cpp:1580`). Future work should be filed as an AVX2/AVX512/VNNI microkernel project with `test-backend-ops` correctness plus perf/canonical bench validation, not as a resurrection of the generic scalar repack probe.
- [x] **K28 (P2, GPU) — GDN long-prefill optimized kernel CLOSED NO-GO ✅ 2026-08-11**: the governed direct `rocprof` v1 gate measured GDN summed-kernel shares of 15.397%, 14.649%, and 12.180% at p2048/p8192/p32768. Even an optimistic 4x op speedup yields only 11.548%, 10.987%, and 9.135% full-model ceilings, declining with context and not materially beating the higher-EV alternatives. No fused prototype is warranted. Detailed closeout: [k28-fused-chunked-gdn-kernel-research.md](../completed/k28-fused-chunked-gdn-kernel-research.md); receipt SHA-256 `981306080a674f89f5ac7f9c7631feef1d31071dacd46329aa983db72e74c5a0`.
  - [x] **K28.1 stale-title/source audit ✅ 2026-07-17**: confirmed upstream `d28961d81` already enabled the functional chunked fused GDN path; no bounded safe patch is available for the remaining performance goal this session.
  - [x] **K28.2 long-prefill K-overflow boundary regression test ✅ 2026-07-18**: experimental-v7 commit `231db22c7` adds a `GATED_DELTA_NET(type=f32, head_count=4, head_size=16, n_seq_tokens=65, K=4)` test case so the future optimized kernel must preserve multi-token snapshot overflow semantics across the 64-token chunk boundary. Validation: `test-backend-ops test -o GATED_DELTA_NET -b CPU -j 8` and `-b ROCm0 -j 8` both passed `37/37`.
  - [x] **K28.3 KDA overflow + fused-cache bridge guard ✅ 2026-07-18**: experimental-v7 commit `41ae83402` adds the KDA 65-token / `K=4` overflow case and makes the CUDA fused-cache bridge explicitly skip `K<=1`, preserving the snapshot-copy path when no multi-slot recurrence exists. Validation: `cmake --build build-hip --target test-backend-ops -j16`; `LD_LIBRARY_PATH=build-hip/bin ./build-hip/bin/test-backend-ops test -o GATED_DELTA_NET -b CPU -j 8` passed `38/38` on CPU. ROCm validation remains future/operator-safe because this is source-prep, not the optimized recurrence kernel.
  - [x] **K28.4 Phase 0 ceiling gate ✅ 2026-07-20**: detailed K28 handoff consumed; no direct ROCm profiler was available (`rocprofv2`/`rocprof`/`omniperf` absent), so Phase 0 used a fresh `GATED_DELTA_NET` MI210 op rerun plus the existing Qwen3.6-35B-A3B Q8 full-model prefill rows. Op efficiency still falls with length (`51.20 GB/s` at 64 tokens → `26.84 GB/s` at 1024), confirming serial-dependency headroom, but the modeled full-model ceiling is bounded: GDN prefill share about `15.31%` at p2048 and `14.54%` at p8192; an optimistic 4x op kernel maps to only `11.48%` / `10.91%` full-model prompt gain. Evidence: `epyc-inference-research/data/k28_gdn_perf/k28-phase0-ceiling-20260720T102644Z/summary.json`. Verdict: do not delay frozen-v7 promotion for K28 Phase 1; keep the fused chunked recurrence kernel as default-off post-promotion research unless a profiler rerun or throwaway prototype proves materially higher ceiling.
  - [x] **K28.5a default-off scaffold gate ✅ 2026-07-20**: isolated worktree `/mnt/raid0/llm/llama.cpp-k28-prototype-20260720` on branch `k28/prototype-20260720` adds `GGML_CUDA_GDN_CHUNKED_PROTOTYPE`, a future launch hook in `ggml/src/ggml-cuda/gated_delta_net.cu`, and `docs/development/k28-fused-chunked-gdn-prototype.md`. Eligibility is deliberately narrow (GDA-only, F32, `K==1`, no fused-cache bridge, `S_v==128`, `n_seqs==1`, `n_tokens>=64`), and every path still falls back to the existing serial GDN kernel. Validation passed `git diff --check`, HIP CMake configure, and `cmake --build build-k28-prototype-hip --target test-backend-ops -j 8`; GitNexus impact remained unavailable because indexing crashed after parser timeout retries. This is scaffold/readiness only, not speed evidence.
    - **Uncommitted-work note 2026-09-16 (sub-closure-fix; annotation only):** in `/mnt/raid0/llm/llama.cpp-k28-prototype-20260720` (branch `k28/prototype-20260720`), `docs/development/k28-fused-chunked-gdn-prototype.md` is **staged but never committed**, and the CUDA hook `ggml/src/ggml-cuda/gated_delta_net.cu` is a modified, uncommitted working-tree change. No ref carries the scaffold. The owner should commit it on that experimental branch. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #10).
    - [x] **K28.5a-COMMIT — commit the K28.5a scaffold on `k28/prototype-20260720`** (the prototype worktree, not ✅ 2026-10-07
          production). A `git diff HEAD` patch (85+/3-) and the doc are backed up in
          `/mnt/raid0/llm/backups/preserve-20260916/`. Filed 2026-09-17.
          MAIN accepts isolated historical scaffold custody at project-owned [b76d2549e4](https://github.com/pestopoppa/llama.cpp/commit/b76d2549e4f99bf5f7764c326d955308076452e4), exact two-file85+/3- patch based on owner8bb53c5205. Owner dirty tree/staging unchanged; no build, production/main merge or reopening of the recorded performance NO-GO.
  - [x] **K28.5 default-off fused recurrence prototype gate CLOSED NO-GO ✅ 2026-08-11**: direct ROCm attribution completed the accepted cheap proof step and reproduced, rather than raised, the old ceiling. The measured shares/ceilings above fail the handoff's “materially above alternatives” admission bar, so the correct gate result is to stop before kernel authoring.
- [x] **K29 (P2) — draft hot-path malloc removal ✅ 2026-07-17**: experimental-v7 `6b93ca027` removes the `malloc`/`free` token sidecars in `common/speculative.cpp` EAGLE3 and MTP draft implementations. `llama_batch_init()` still owns/frees the embedding and metadata buffers; the extra token buffer is now owned by `std::vector<llama_token>` in the speculative implementation, and destructors null `batch.token` before `llama_batch_free()` so the batch free path only frees owned allocations. Validation: `git diff --check`; no remaining `TODO: fix, how to call without malloc` / manual `malloc` / `free(batch.token)` matches; `cmake --build build-k24-cpu --target llama-server -j16`; `cmake --build build-hip --target llama-server -j16`; pinned `llama-server --version` smoke for both builds reported `10082 (3dee86a5a)`.
- [x] **K32 (P0, correctness) — external draft model path honored in common server init ✅ 2026-07-17**: Stage-1 MI210 drafter execute exposed that `common/speculative.cpp` recorded `params.speculative.draft.mparams.path` but called `llama_model_load_from_file(params.model.path.c_str(), mparams)`, silently reloading the target model as the draft in common/server paths. Experimental v7 now loads the actual draft path and applies draft-specific devices, `n_gpu_layers`, and tensor-buffer overrides, matching the standalone speculative examples. Validation: `cmake --build build-hip --target llama-server -j16`; rebuilt server reports `version: 10079 (96986f5e9)`; invalid `-md /mnt/raid0/llm/tmp/definitely-missing-stage1-draft.gguf` startup smoke fails on the missing draft path instead of loading the target.
- [x] **K33 (P0-adjacent, robustness) — draft-tree long-output HTTP 500 at 256-token context slice ✅ 2026-07-17**: Stage-1 repaired-path 256-token requests failed near `n_tokens=257` because draft-tree raised `n_seq_max` to `32` but left draft `n_ctx` unchanged; llama.cpp divided `8192 / 32`, leaving only a 256-token per-sequence draft context. Experimental v7 now forces unified KV for draft-tree draft contexts, preserving the full per-sequence context while still allowing scratch branch seq IDs. Validation: `cmake --build build-hip --target llama-server -j16`; final Stage-1 256-token artifact `data/specdec_frontdoor_alpha/stage1_mi210_gpu_drafter_20260717T0518Z_drafttreeunifiedkv/summary.json` completed all `1024` completion tokens with `508/508` accepted draft tokens. The Stage-1 economics gate still failed (`0.915x` decode, `0.911x` wall), so this fixes robustness only.
- [x] **K34 (P1, operations/perf reproducibility) — CPU host throughput drift root-cause ✅ 2026-07-20**: K24.4 proved current production CPU guard cells were much slower than the 07-16 production cells on architect and ingest even after `megasync` and Firefox were killed (`architect 5.8482 -> 3.6477 t/s`, ingest `13.8869 -> 9.7992 t/s`). This is not a v7 promotion blocker by itself, but it can poison AutoPilot speed telemetry and future kernel A/Bs. Root-cause finding: the large regression was transient host/runtime state, not source/compiler; current default placement recovered to far above K24.4 and v7 is parity-or-better under the same host state. Clean-run policy is now defined: future decision-grade CPU A/Bs must run the K34 preflight and retry host state before source blame if the sentinel falls below the recovered band.
  - [x] **K34.1 paired default-vs-`--numa distribute` guard ✅ 2026-07-17**: artifact `/mnt/raid0/llm/tmp/k34-numa-distribute-20260717T094451Z/` reran the K24 frontdoor/architect/ingest CPU decode cells (`-p 0 -n 256 -r 3 -t 96 -ngl 0 -dev none`) on production `91745611f` and v7 CPU build `2e79e10cc`, with libraries pinned. Current default placement recovered versus K24.4 by `+141.6%` prod frontdoor, `+141.6%` prod architect, `+101.1%` prod ingest, `+146.4%` v7 frontdoor, `+158.7%` v7 architect, and `+100.4%` v7 ingest. Current default v7-vs-prod deltas: frontdoor `-0.73%`, architect `+3.84%`, ingest `+0.68%`. `--numa distribute` was mixed/noisy and hurt ingest (`prod -8.05%`, v7 `-4.68%`), so do not hard-code it as a universal fix.
  - [x] **K34.2 clean-run preflight ✅ 2026-07-17**: inference-research commit `3b55aeb` adds `scripts/benchmark/cpu_bench_clean_preflight.py` plus unit tests. The preflight records process blockers (AutoPilot, llama-server/bench/CLI, profilers), `numactl --hardware`, `free -h`, `lscpu`, governor/EPP/boost/THP/NUMA-balancing/perf state, pinned `LD_LIBRARY_PATH`, source commit/worktree status, and an optional K34-shaped frontdoor sentinel (`Qwen3.6-35B-A3B-MTP-Q8_0`, `-p 0 -n 256 -r 3 -t 96 -ngl 0 -dev none`) with `GGML_IQK=1`. Sentinel policy records recovered reference `20.57 t/s`, retry threshold `18.0 t/s`, and explicit "retry before source blame" guidance. Validation: focused unittest passed (`5` tests), `diff --check` clean, record-only and `--strict` preflights wrote `ok` reports with zero blockers/host warnings at `/mnt/raid0/llm/tmp/cpu-bench-clean-preflight-20260717T100919Z-record/preflight.json` and `/mnt/raid0/llm/tmp/cpu-bench-clean-preflight-20260717T100932Z-strict/preflight.json`.
  - [x] **K34.3 pre-promotion clean-host checkpoint ✅ 2026-07-20**: record-only preflight wrote `status=ok`, zero blockers, zero host warnings, and pinned experimental source head `93d945885f9183ab8cf1f1bcd0a1c208d9379433` at `epyc-inference-research/data/k34_cpu_host_throughput_drift/k34-clean-preflight-record-20260720T104546Z/preflight.json`. The CPU-only sentinel then passed with `status=ok`, `avg_ts=19.322867 t/s` on `Qwen3.6-35B-A3B-MTP-Q8_0`, build commit `12a292f0c`, `-p 0 -n 256 -r 3 -t 96 -ngl 0 -dev none`, above the `18.0 t/s` retry threshold at `data/k34_cpu_host_throughput_drift/k34-clean-preflight-sentinel-20260720T104608Z/preflight.json`. Post-run process and ROCm checks showed no inference processes or KFD PIDs. Verdict: K34 is closed as a pre-v7 research/reproducibility blocker; keep the preflight as mandatory hygiene for future CPU A/B evidence.
- [x] **K35 (P0 release artifact) — optimized stack throughput-vs-context matrix before v7 finalization ✅ 2026-07-18**: operator-facing throughput/context evidence is now consolidated for every production stack role/model with optimized serving shapes, memory rows, quality/acceptance side data, command/provenance, and cleanup proof. The release artifact is closed for A1/v7 readiness; remaining K35 child tasks are non-blocking candidate/parser/service follow-ups, not missing release-matrix rows. The final promotion handoff still separately requires a cutover coherence/garbage smoke after the last candidate source state is fixed.
  - [x] **K35.1 worker_general CPU full/quarter smoke ✅ 2026-07-17**: current v7 HIP binary `d1e5a20eb` was smoke-tested with production-shaped `worker_general` CPU-only server flags, composed `--spec-type ngram-mod,draft-mtp`, `--device none --device-draft none`, `q8_0/q8_0` KV, reasoning off, and pinned experimental `LD_LIBRARY_PATH`. Full-instance high-port smoke at `/mnt/raid0/llm/tmp/v7-worker-general-server-cpu-20260717T111809Z/` proved composed spec active (`draft_n=58`, `draft_n_accepted=34`) but stopped early after `63` tokens (`16.64 t/s` decode), so it is not a long-decode throughput point. Short-context full-instance recheck at `/mnt/raid0/llm/tmp/v7-worker-general-shortctx-recheck-20260717T112435Z/` reproduced the historical healthy band: two 520-token requests with 8-token prompts decoded at `76.02 t/s` (`454/631` accepted) and `116.96 t/s` (`487/776` accepted). Four quarter-shaped high-port servers at `/mnt/raid0/llm/tmp/v7-worker-general-quarters-cpu-20260717T111949Z/` completed concurrent forced-256-token requests on masks q0-q3 with per-quarter decode `9.74`, `9.33`, `7.99`, and `7.95 t/s` (aggregate `~35.0 t/s`) at `3235` prompt tokens, prompt `120-136 t/s`, and accepted draft counts `157-168/173-195`. Cleanup proof: all temporary `llama-server` PIDs were gone and ROCm reported no KFD PIDs after the runs. Verdict: worker full short-context speed is healthy; the slow quarter numbers are context-depth/launch-shape evidence, not "optimizations disabled." K35 remains open for role-complete throughput-vs-context tables.
  - [x] **K35.2 dry-run-first matrix runner + frontdoor/worker partial matrix ✅ 2026-07-17**: inference-research adds `scripts/benchmark/k35_stack_context_matrix_runner.py` plus unit tests. The runner writes `plan.json`, `commands.sh`, `guard_state.json`, per-run `server_argv.json`/`response.json`/`result.json`, summary, and cleanup proof for one optimized stack-role scenario at a time. Initial scenarios are deliberately limited to fastest-safe prior evidence: `frontdoor_gpu_resident_no_spec` (MI210-resident Qwen3.6-35B no-spec, Stage-2 fastest arm) and `worker_general_cpu_composed_spec` (Gemma4 CPU composed `ngram-mod,draft-mtp`, draft_max=2, q8 KV, reasoning off). Frontdoor rows passed at prompt/decode: `1861 tok -> 98.04 t/s` (`/mnt/raid0/llm/tmp/k35-frontdoor-gpu-smoke-20260717T1207Z/`), `8005 -> 93.56 t/s` (`/mnt/raid0/llm/tmp/k35-frontdoor-worker-8k-20260717T1212Z/`), `14534 -> 88.84 t/s`, and `28534 -> 79.63 t/s` (`/mnt/raid0/llm/tmp/k35-frontdoor-deep-20260717T1218Z/`). Canonical runner artifact `/mnt/raid0/llm/tmp/k35-frontdoor-canonical-20260717T132933Z/summary.json` now covers the default 2K/8K/32K frontdoor release cells with MI210-resident no-spec decode `99.44`, `95.07`, and `78.17 t/s` respectively; cleanup blockers were empty and ROCm reported no KFD PIDs after release. Worker rows passed at prompt/decode: `1862 -> 93.18 t/s` with `240/414` draft tokens accepted (`/mnt/raid0/llm/tmp/k35-worker-general-cpu-smoke-20260717T1208Z/`), `8006 -> 106.71 t/s` with `492/666` accepted (`/mnt/raid0/llm/tmp/k35-frontdoor-worker-8k-20260717T1212Z/`), and `12535 -> 97.80 t/s` with `492/666` accepted (`/mnt/raid0/llm/tmp/k35-worker-general-deep-20260717T1220Z/`). Canonical worker artifact `/mnt/raid0/llm/tmp/k35-worker-canonical-20260717T133244Z/summary.json` covers default 2K/8K/14K worker release cells with Gemma4 CPU composed-spec decode `126.18`, `96.67`, and `82.94 t/s`; each row completed `512` tokens and accepted `492/666` draft tokens. Cleanup blockers were empty for all cells. K35 remains open for a consolidated operator-facing report, vision throughput/quality rows beyond smoke, and any operator-requested production-stack concurrency rows.
  - [x] **K35.3 architect/ingest optimized matrix rows ✅ 2026-07-17**: architect and corrected ingest rows are now covered. Harness fix: `-np > 1` now sizes `-c` as total server context and skips contexts above per-slot capacity; the first architect 8K attempt correctly failed as a harness accounting bug (`/mnt/raid0/llm/tmp/k35-arch-ingest-8k-20260717T121645Z/`), then passed after the fix. Architect Qwen3.5-122B rows use CPU native `draft-mtp`, same-file NEXTN, `-np 2`, `q4_0/f16` KV, `--mlock`, `--jinja`, request `chat_template_kwargs.enable_thinking=false`, and no `-md`; rows passed at prompt/decode: `837 tok -> 23.53 t/s`, `203/205` draft accepted (`/mnt/raid0/llm/tmp/k35-arch-ingest-2k-20260717T121543Z/`) and `6725 tok -> 20.72 t/s`, `408/409` accepted (`/mnt/raid0/llm/tmp/k35-architect-8k-fixed-20260717T121856Z/`). Deeper architect contexts are not covered under the production `-np 2 -c 16384` launch shape. **Invalidated ingest rows:** `/mnt/raid0/llm/tmp/k35-arch-ingest-2k-20260717T121543Z/`, `/mnt/raid0/llm/tmp/k35-arch-ingest-8k-20260717T121645Z/`, and `/mnt/raid0/llm/tmp/k35-ingest-deep-20260717T122029Z/` used stale `qwen3next.expert_used_count=int:4` MoE expert-count reduction and must not be used as the K35 default ingest matrix. Corrected ingest rows use Qwen3-Next default experts, spec disabled, `q4_0/q4_0` KV, `--mlock`, `--jinja`, and no `--override-kv`; rows passed at prompt/decode: `575 tok -> 19.82 t/s` and `6719 tok -> 15.94 t/s` (`/mnt/raid0/llm/tmp/k35-ingest-default-2k8k-20260717T123107Z/`), plus `14528 tok -> 13.00 t/s` and `28528 tok -> 10.13 t/s` (`/mnt/raid0/llm/tmp/k35-ingest-default-deep-20260717T123308Z/`). Cleanup blockers were empty for all successful cells.
  - [x] **K35.3a registry drift follow-up ✅ 2026-07-17**: removed the abandoned Qwen3-Next MoE4 expert-count reduction from the live `ingest_long_context` registry path. Research `server_mode.ingest_long_context` and `roles.ingest_long_context` now use `acceleration.type: none`, the stale server-mode model name was corrected to `Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf`, and the orchestrator lean registry/model descriptors/stack priors/operator summary were regenerated from the master registry. Validation evidence: research registry validator reports `0 error(s)` with only pre-existing off-disk catalogue warnings; `stack_change_pipeline.py check --allow-known-gaps --allow-production-blocker-waivers` passes; the focused no-inference promotion suite passes (`181 passed`); and no `qwen3next.expert_used_count` remains in orchestrator live registry/descriptors/stack-priors/summary. Production v6 was not touched.
  - [x] **K35.4 production vision release-smoke scope ✅ 2026-07-17**: current production vision roles passed a bounded v7 release smoke at `/mnt/raid0/llm/tmp/k35-vision-release-smoke-20260717T125719Z/summary.json`. The smoke used the regenerated stack-prior launch contracts with the experimental v7 HIP `llama-server` on high ports, `--device none`, and a single real image request per role. `worker_vision` (Qwen2.5-VL-7B + `mmproj-model-f16.gguf`, `-np 2 -c 8192 -t 24`) answered the OCR image as `7500` (`10.93 t/s` decode). `vision_escalation` (Qwen3-VL-30B + mmproj, `-np 1 -c 16384 -t 96`, `qwen3vlmoe.expert_used_count=int:4`) also answered `7500` (`27.18 t/s` decode). Both health checks passed, both server PIDs were verified dead after stop, and post-run ROCm reported no KFD PIDs. Replacement/admission candidates remain deliberately deferred: Qwen3-VL-8B A/B, MiniCPM-o modality mapping, PaddleOCR-VL, SuperGemma4 multimodal, Bonsai/Ternary projectors, and matched text-only tax A/B before any multimodal checkpoint is used as a text-role replacement.
  - [x] **K35.5 consolidated operator-facing report ✅ 2026-07-17; A1 artifact reconciled ✅ 2026-07-18**: root report `research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md` consolidates the frontdoor, worker, architect, corrected ingest, and vision evidence into one operator-facing table with artifact paths, model paths/sizes, optimized launch shapes, throughput rows, acceptance/quality side data, invalidated MoE4/harness rows, and remaining gaps. The later K35.8/K35.13c evidence supplies the true vision throughput/quality/memory rows and broader MiniCPM-o/frontdoor service matrix, and K35.13f supplies the controlled live MiniCPM-o smoke. A1 is no longer blocked on missing rows or live-smoke evidence; remaining parser/stress follow-ups are optional.
  - [x] **K35.6 resident-memory sampler scaffold ✅ 2026-07-17**: inference-research `scripts/benchmark/k35_stack_context_matrix_runner.py` now records `memory_samples` for each executed cell after health, after request, and before cleanup. Samples include `/proc/<pid>/status`, `/proc/<pid>/smaps_rollup` parsed KiB fields, `ps` RSS/VSZ/CPU, and a ROCm PID/memory/utilization snapshot when `rocm-smi` is available. Validation: `python3 -m unittest scripts/benchmark/test_k35_stack_context_matrix_runner.py` (`10` tests), `python3 -m py_compile ...`, and `git diff --check`. This closes the runner-instrumentation gap, not the historical matrix memory rows; those require rerunning selected K35 cells.
  - [x] **K35.7 non-vision resident-memory backfill ✅ 2026-07-17**: sequential quiet-host memory-backfill artifact `/mnt/raid0/llm/tmp/k35-memory-backfill-20260717T1400Z/summary.json` reran the optimized non-vision K35 cells with the new sampler and completed `status: ok`, empty `cleanup_process_blockers`, all temporary server PIDs dead, and post-run ROCm showing no KFD PIDs. After-request resident memory: frontdoor 2K/8K/32K `1.37/1.38/1.40 GiB` host RSS plus `55/55/56%` MI210 VRAM; worker 2K/8K `17.48/17.74 GiB`; architect 2K/8K `75.56/76.46 GiB`; ingest 2K/8K/32K `45.84/46.11/46.35 GiB`. Decode remained in-family: frontdoor `99.77/95.56/78.48 t/s`, worker `122.75/97.80`, architect `22.76/19.37`, ingest `19.83/15.86/9.59`.
  - [x] **K35.8 production vision matrix + escalation defect ✅ 2026-07-17**: inference-research adds `scripts/benchmark/k35_vision_matrix_runner.py` plus unit tests. Default rows are production `worker_vision` and `vision_escalation`; diagnostic/candidate rows require explicit opt-in. Live artifact `/mnt/raid0/llm/tmp/k35-vision-matrix-20260717T1500Z/summary.json` used experimental v7 server `10088 (d1e5a20eb)`, four fixed local OCR/chart fixtures, guard state, per-request scoring/timing, memory samples, and cleanup proof. `worker_vision` passed `4/4` (`7500`, `43.36`, `Tanzania`, `CS00012465`) with decode `16.91-21.32 t/s` and `6.05 GiB` RSS before cleanup. Current production `vision_escalation` passed `3/4` with faster short decode `35.87-50.17 t/s` and `19.69 GiB` RSS, but failed the chart fixture (`Moldova` instead of `Tanzania`). Diagnostic probes did not recover it: `--image-min/max-tokens 1024` still failed (`Suriname`), and default experts without `qwen3vlmoe.expert_used_count=int:4` also failed (`Suriname`). Validation: `python3 -m unittest scripts/benchmark/test_k35_vision_matrix_runner.py scripts/benchmark/test_k35_stack_context_matrix_runner.py` (`18` tests), `py_compile`, and `git diff --check`. K35 remains open for a vision-escalation replacement/specialization A/B and optional service-concurrency rows.
  - [x] **K35.9 temporary safe vision-escalation alias ✅ 2026-07-17**: because K35.8 shows the Qwen3-VL-30B escalation lane is faster but not quality-safe, the live registries now bind `vision_escalation` on port `8087` to the same Qwen2.5-VL model/projector as `worker_vision` until a replacement A/B wins. Research `roles.vision_escalation` is marked as a temporary C-tier safety alias with the K35 evidence path; orchestrator `stack_manifest.py`, `stack_numa.py`, `orchestrator_stack.py`, lean registry, descriptors, stack priors, and generated stack summary were regenerated. The stack-priors compiler no longer injects `qwen3vlmoe.expert_used_count=int:4` merely because `vision_type == escalation`; explicit MoE override configs still pass through. Validation: GitNexus impact for `_launch_runtime_record` flagged HIGH because it feeds stack-prior generation and launch guards; edit was limited to the override source. Research registry validation reports `0 error(s)` with only pre-existing off-disk catalogue warnings; `stack_change_pipeline.py update --allow-known-gaps --allow-production-blocker-waivers --allow-descriptor-model-removal` passed; no-inference promotion plus compiler tests passed (`197 passed`). Active port `8087` is now safe/call-site-stable but not a true higher-quality escalation lane.
  - [x] **K35.10 Qwen3-VL-8B escalation replacement A/B ✅ 2026-07-17**: local Qwen3-VL-8B Q4_K_M + F16 projector was added as explicit opt-in K35 vision candidate rows in inference-research. Artifact `/mnt/raid0/llm/tmp/k35-qwen3vl8-candidate-20260717T185330Z/summary.json` shows the CPU candidate passed the four fixed OCR/chart fixtures (`4/4`) but was slower than the temporary Qwen2.5-VL alias at `10.81-13.39 t/s` decode and verbose on the chart answer. The MI210 candidate in the same artifact was fast (`110.02-125.72 t/s`) but failed the chart fixture as `Moldova` (`3/4`). Artifact `/mnt/raid0/llm/tmp/k35-qwen3vl8-mi210-default-image-20260717T185459Z/summary.json` repeated the MI210 chart failure with default image-token shape (`3/4`, `109.61-120.32 t/s`). Verdict: Qwen3-VL-8B is runtime/coherence-clean and CPU-quality-clean on this small slice, but it is not the active `vision_escalation` replacement. This closes the Qwen3-VL-8B candidate A/B; extra vision-candidate A/Bs are paused unless a specific fixture/role-gap fix is identified, and any reopened probe must append to the scoreboard.
    - [x] **K35.10a latest-tip default-image repeat ✅ 2026-07-19**: `data/gpu-mi210/k35_qwen3vl8_mi210_default_image_currentv7_20260719T042531Z/summary.json` reran the MI210 default-image-token lane on experimental-v7 `6a8dd5ea6` and again passed only `3/4`, failing `chart_tanzania` as `Moldova`; decode was `111.21-120.93 t/s`, VRAM was about `11-12%`, and cleanup was clean. This confirms the image-token override was not the chart-failure cause on the current promotion tip.
  - [x] **K35.11 MiniCPM-o escalation replacement A/B ✅ 2026-07-17**: local MiniCPM-o-4_5 Q4_K_M + vision F16 projector was added as explicit opt-in K35 vision candidate rows. Default reasoning mode loaded and read the images but routed correct answers into `reasoning_content`, so `message.content` scoring failed (`0/4`) in `/mnt/raid0/llm/tmp/k35-minicpm-o45-candidate-20260717T1909Z/summary.json`. The realistic `--reasoning off` lane passed the four fixed OCR/chart fixtures on CPU (`4/4`, `11.98-14.13 t/s`) and MI210 (`4/4`, `110.81-122.18 t/s`, about `11%` VRAM) in `/mnt/raid0/llm/tmp/k35-minicpm-o45-reasoning-off-20260717T1911Z/summary.json`. Verdict: MiniCPM-o is the first fast quality-clean higher-speed escalation candidate, but activating it changes `vision_escalation` from a CPU safety alias to an MI210 service. K35 remains open for the GPU service/concurrency/text-tax decision; additional candidate A/Bs are paused unless a concrete fixture or role gap not covered by MiniCPM-o / worker_vision appears.
  - [x] **K35.12 MiniCPM-o service policy gate ✅ 2026-07-17**: frontdoor+MiniCPM-o MI210 co-residency smoke passed at `/mnt/raid0/llm/tmp/k35-minicpm-frontdoor-coresidency-20260717T191849Z/`. The smoke launched the fastest validated frontdoor lane (`Qwen3.6-35B-A3B-MTP-Q8_0`, MI210 resident, q8 KV, reasoning off, no spec, `-c 4096`) beside the realistic MiniCPM-o lane (`MiniCPM-o-4_5-Q4_K_M` + vision F16 projector, MI210, `--reasoning off`, `-c 8192`). Both servers were healthy together at `66%` MI210 VRAM, both handled concurrent requests, frontdoor decoded `512` tokens at `99.97 t/s`, and MiniCPM-o answered the chart fixture as `Tanzania` (`score_pass=true`, `108.68 t/s` on a 4-token answer). Cleanup proof: both PIDs terminated cleanly, `post_cleanup_verification.txt` shows no `llama-server` or AutoPilot process and ROCm reports `0%` VRAM / no KFD PIDs. This closes the basic co-residency smoke, not a broad service-level concurrency matrix or automatic live routing flip.
  - [x] **K35.13 vision-escalation activation decision / capacity policy ✅ 2026-07-18**: decision recorded to activate MiniCPM-o Q4_K_M + vision F16 projector as the next MI210 `vision_escalation` lane with `--reasoning off`, resident-loaded/on-demand scheduling, and a one-active-vision-request capacity cap while the MI210 frontdoor is resident. The minimum coexistence smoke passed in K35.12, K35.13a bounds a synthetic active-collision tax, and K35.13c covers the broader 2K/8K fixture service matrix. The current live stack remains on the Qwen2.5-VL CPU safety alias until a controlled stack-registry patch/reload is executed; Qwen2.5-VL stays the rollback alias if MiniCPM-o shows real-traffic contention or content-channel regressions.
  - [x] **K35.13d controlled live-stack MiniCPM-o source/config flip ✅ 2026-07-18**:
    orchestrator `4ab4e0ee` changes the `vision_escalation` launch contract on port `8087`
    from the Qwen2.5-VL CPU safety alias to MiniCPM-o-4_5 Q4_K_M + vision F16 projector,
    carries `--reasoning off` and `--device ROCm0` through generated stack priors, and
    preserves the one-active-slot cap. The no-inference stack-change pipeline passed with
    generated descriptors/priors/operator summary fresh; focused tests passed (`143 passed`,
    plus promotion gate `182 passed`). Dry launch inspection emits
    `/mnt/raid0/llm/llama.cpp/build/bin/llama-server ... -np 1 -c 8192 -t 24 --flash-attn on --reasoning off --device ROCm0`.
    No AutoPilot restart, live stack reload, or live traffic smoke was run in this checkpoint.
  - [x] **K35.13f controlled live reload + MiniCPM-o smoke/rollback gate ✅ 2026-07-18**:
    launched only `vision_escalation` through the stack launcher after teaching the runtime
    contract to use the experimental v7 HIP binary plus matching `LD_LIBRARY_PATH` for this
    role. The launch gate passed fresh stack-change checks and promotion tests; live command
    was `/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin/llama-server ... -np 1 -c 8192
    -t 24 --flash-attn on --reasoning off --device ROCm0`. Live fixture artifact
    `/mnt/raid0/llm/tmp/k35-vision-escalation-live-smoke-20260718T1225Z/summary.json`
    passed `4/4` fixed OCR/chart fixtures (`7500`, `43.36`, `Tanzania`, `CS00012465`),
    with short-answer decode `115.22-127.35 t/s` and prompt eval `731.92-884.41 t/s`.
    Stopped PID `2813245` after the smoke; post-stop `rocm-smi` showed `0%` VRAM and no
    KFD PIDs. AutoPilot and the orchestrator API were not restarted.
  - [x] **K35.13a MiniCPM-o/frontdoor service-tax probe ✅ 2026-07-17**: artifact `/mnt/raid0/llm/tmp/k35-minicpm-frontdoor-service-tax-20260717T192427Z/` ran two 1024-token frontdoor requests in each condition using the same MI210-resident Qwen3.6 frontdoor lane and MiniCPM-o `--reasoning off`. Frontdoor alone decoded `101.68` and `101.84 t/s`; frontdoor with MiniCPM-o resident but idle decoded `101.89` and `101.86 t/s`; concurrent active MiniCPM-o vision decode dropped frontdoor to `80.16` and `80.34 t/s` while MiniCPM-o decoded `90.49` and `90.23 t/s`. Cleanup proof: both PIDs terminated cleanly, refreshed `post_cleanup_verification.txt` shows no `llama-server`/AutoPilot process and ROCm reports `0%` VRAM / no KFD PIDs. Interpretation: residency is cheap; active overlap costs about `21%` frontdoor decode on this synthetic pair.
  - [x] **K35.13b frontdoor 1024-token operational replay ✅ 2026-07-17**: artifact `/mnt/raid0/llm/tmp/k35-frontdoor-operational-1024-20260717T201842Z/summary.json` reran the fastest validated frontdoor serving lane (`Qwen3.6-35B-A3B-MTP-Q8_0`, MI210 resident, q8 KV, reasoning off, no spec) with a 1024-token generation cap. Decode held `100.55 t/s` at 2K, `95.56 t/s` at 8K, and `77.67 t/s` at 32K; all rows passed the 512-token completion floor, cleanup blockers were empty, and post-run ROCm showed no KFD PIDs. This is an optimized operational row, not a baseline/control row.
  - [x] **K35.13e frontdoor Gate-R candidate row ✅ 2026-07-18**: inference-research extended `scripts/benchmark/k35_stack_context_matrix_runner.py` with first-class `--reps`, a same-window `frontdoor_cpu_no_spec` re-anchor, and a `frontdoor_gpu_native_mtp` arm. Quiet-host artifact `data/k35_stack_context_matrix/frontdoor_pgpu1_candidate_20260718Tquiet/` ran Qwen3.6-35B Q8 on experimental v7 `d1e5a20eb` at nominal 8K / 1024-token output with `n=5` fresh-server reps per arm. Results: CPU no-spec median `17.10 t/s` (MAD `0.06`), MI210 no-spec `95.39 t/s` (`5.58x`, MAD `0.24`), MI210 native MTP `119.69 t/s` (`7.00x`, MAD `0.35`) with `3835/3835` accepted draft tokens. All `15/15` cells completed and cleaned up; post-run ROCm showed `0%` VRAM/no KFD PIDs. This is strong Gate-R evidence but observation-grade because ratified `P-GPU-1` requires a production-named kernel; decision-grade Gate-R reruns after promotion on `production-consolidated-v7`.
  - [x] **K35.13c MiniCPM-o/frontdoor broader service matrix ✅ 2026-07-17**: inference-research adds `scripts/benchmark/k35_minicpm_service_matrix_runner.py` plus unit tests. Live artifact `/mnt/raid0/llm/tmp/k35-minicpm-service-matrix-20260717T2045Z/summary.json` used the same fastest validated MI210 frontdoor lane and MiniCPM-o `--reasoning off` lane across 2K/8K contexts and all four K35 vision fixtures. Frontdoor alone averaged `96.33 t/s`; frontdoor with MiniCPM-o resident but idle averaged `96.48 t/s`; active overlap averaged `94.77 t/s` frontdoor and `85.22 t/s` MiniCPM-o; all `8/8` active fixture/context pairs passed; cleanup blockers were empty. This replaces the single synthetic pair as the more realistic activation-policy datum while leaving the live flip decision open.
  - [x] **K35.14 SuperGemma4 multimodal escalation replacement A/B ✅ 2026-07-17**: inference-research added opt-in `vision_candidate_{cpu,mi210}_supergemma4_mm_q8` rows and tests. Artifact `/mnt/raid0/llm/tmp/k35-supergemma4-candidate-20260717T193120Z/summary.json` shows SuperGemma4-26B multimodal Q8_0 + F16 projector passed the four fixed OCR/chart fixtures on CPU (`4/4`, decode `25.58-31.76 t/s`, about `26.4 GiB` PSS) and MI210 (`4/4`, decode `80.35-83.87 t/s`, about `42%` VRAM). Cleanup proof: both PIDs terminated cleanly and `post_cleanup_verification.txt` shows no `llama-server`/AutoPilot process plus `0%` VRAM / no KFD PIDs. Verdict: quality-clean on this small K35 slice, but not the preferred active `vision_escalation` replacement because MiniCPM-o is faster on MI210 (`110.81-122.18 t/s`), much smaller, and already has frontdoor co-residency/service-tax evidence.
  - [x] **K35.15 PaddleOCR-VL document-specialist smoke ✅ 2026-07-17**: PaddleOCR-VL-1.6 GGUF + mmproj was downloaded from `PaddlePaddle/PaddleOCR-VL-1.6-GGUF` revision `511b09642bb324401f15f97cc23bc67e8f0a291d`, SHA-verified, and loaded through experimental-v7 MI210 `llama-server` with `-ngl 99 --reasoning off`. Artifact `/mnt/raid0/llm/tmp/paddleocr-vl-first-smoke-20260717T194332Z/summary.json` passed digit OCR (`7500`, `484.36 t/s`) and invoice markdown extraction (`489.82 t/s`); the narrow receipt QA prompt failed because it emitted broad OCR text under a 96-token cap. Follow-up `/mnt/raid0/llm/tmp/paddleocr-vl-receipt-extract-20260717T194415Z/summary.json` used a realistic 768-token full-extraction prompt and included `CS00012465` at `487.55 t/s`. Cleanup proof showed no `llama-server`/AutoPilot process and `0%` VRAM. Verdict: fast document/OCR extraction specialist, not a general `vision_escalation` QA replacement.
  - [x] **K35.16 PaddleOCR-VL Wave-3 document benchmark producer ✅ 2026-07-17**: inference-research now has a guarded `odl_bench run-model --engine paddleocr_vl_1_6` path that requires `--allow-inference`, launches only experimental-v7 `llama-server`, consumes OmniDocBench GT page images, writes `<stem>.md` predictions, records per-page response JSON, and scores through the existing structural/table/reading-order config. First operational demo `/mnt/raid0/llm/tmp/odl-paddleocr-vl-demo-20260717T200212Z/model_gated_row_set.json` wrote/scored `18/18` pages, captured one `peg-native` model error as an empty prediction, and reported median decode `485.30 t/s`, median page latency `2918.78 ms`, text-block edit distance `0.343019`, reading-order edit distance `0.337318`, and table TEDS `0.0`. Cleanup proof showed no `llama-server`/AutoPilot process and `0%` VRAM/no KFD PIDs. Verdict: producer/runtime path is closed; remaining document work is prompt/table-format tuning plus matched LightOnOCR/ODL comparison.
  - [x] **K35.17 PaddleOCR-VL HTML-table prompt profile + negative prompt-only table result ✅ 2026-07-17**: inference-research added a configurable `--prompt-profile html_tables` / `--prompt-file` path for the guarded PaddleOCR-VL producer. Live artifact `/mnt/raid0/llm/tmp/odl-paddleocr-vl-htmltables-20260717T201106Z/model_gated_row_set.json` completed `18/18` pages with no model errors and improved reading-order edit distance to `0.285753`, but emitted zero HTML `<table>` tags, kept table TEDS at `0.0`, worsened text-block edit distance to `0.429062`, and slowed median page latency to `3245.60 ms`. Cleanup proof showed no `llama-server`/AutoPilot process and `0%` VRAM/no KFD PIDs. Verdict: prompt-only HTML-table recovery is negative; next document-table lever should be post-processing / HTML conversion or a different parser arm.
  - **[declined: ws58 2026-11-03 content-review: duplicate — knowledge-pipelines owns the parser-quality comparison]** **K35.18 post-release document-parser follow-up — table post-processing or stronger parser comparison**: because both default and `html_tables` PaddleOCR prompt profiles scored `table.TEDS=0.0`, the remaining work is parser/post-processing quality, not another generic model speed run. LightOnOCR-2 already has a bounded comparison smoke and is not table/QA clean in the current prompt shape; rerun it only with a concrete parser-quality hypothesis or a bench-compatible HTML/table extraction path. This does not block the K35/A1 release matrix.
    - [x] **K35.18a scorer-compatible pipe-table post-processing hook ✅ 2026-07-17**: inference-research `scripts/benchmark/odl_bench/paddleocr_vl.py` now converts aligned pipe-delimited table row runs into escaped HTML `<table>` blocks before writing model-gated predictions, with deterministic tests. Existing default PaddleOCR predictions were copied and rescored without inference at `/mnt/raid0/llm/tmp/odl-paddleocr-vl-postprocess-rescore-20260717T211432Z/postprocess_rescore_summary.json`: only `2/18` files changed; table TEDS improved `0.0 -> 0.058333` and structure-only TEDS `0.0 -> 0.066667`, while text-block edit distance moved `0.343019 -> 0.343540` and reading-order edit distance `0.337318 -> 0.350138`. Keep the hook as a scorer-compatibility fix, but do not treat PaddleOCR-VL as table-quality-clean; K35.18 remains open for stronger table extraction and matched parser comparison.
    - [x] **K35.18b no-inference existing-artifact ODL comparison ✅ 2026-07-18**: inference-research adds `odl_bench compare-existing`, which materializes JSON/Markdown comparisons from already-scored row sets, raw OmniDocBench metric results, postprocess summaries, or inferred prediction-dir results without launching inference or scoring. Artifact `data/odl_existing_comparison/paddleocr_vl_existing_20260718T035107Z/existing_comparison.md` compares PaddleOCR default, PaddleOCR `html_tables`, PaddleOCR postprocessed, and existing ODL end-to-end metrics. ODL end-to-end is much stronger on tables and reading order (`table.TEDS=0.783813`, reading-order edit distance `0.216996`) than PaddleOCR default (`0.0`, `0.337318`), HTML-table prompt (`0.0`, `0.285753`), or postprocessed (`0.058333`, `0.350138`). This closes the current ODL comparison prep and confirms PaddleOCR remains a fast OCR/document specialist rather than a table-quality parser.
    - [x] **K35.18c LightOnOCR-2 MI210 parser-comparison smoke ✅ 2026-07-19**: bounded v7 `llama-server` run on `LightOnOCR-2-1B-bbox-Q4_K_M` + F16 mmproj at `/mnt/raid0/llm/epyc-inference-research/data/gpu-mi210/lightonocr2-1b-bbox-v7-odl-probe-20260719T0154Z/summary.json` decoded a 512-token document extraction at `224.45 t/s` and median `226.62 t/s` across three probes, using about `4%` VRAM after requests. Cleanup verified no KFD/llama processes and `0%` VRAM. Quality was not table-clean or QA-clean in this server prompt shape: the table-page probe missed expected table markers and the OCRBench digit QA emitted a bbox string instead of `7500`. This supplies the first LightOnOCR comparison smoke but does not close K35.18; next step remains bench-compatible HTML/table extraction or a stronger parser arm on structural/table/reading-order metrics.
    - [x] **K35.18d zero-inference checklist sync ✅ 2026-07-19**: confirmed the A1/K35 release matrix remains closed and should not be reopened for parser quality work. The K35.18 parent remains open because PaddleOCR postprocessing and LightOnOCR-2 smoke do not yet provide bench-compatible, table-clean structural extraction.
- [x] **K36 (P1, upstream freshness) — low-risk official upstream carry-forward ✅ 2026-07-17**: keep v7 current on promotion-relevant upstream fixes without importing unrelated backend churn. DeepSeekV4 fused hyper-connection work remains explicitly outside this v7 promotion scope; backend-only Vulkan/OpenCL/SYCL/Hexagon/Kleidiai updates stay out unless those backends enter scope.
  - [x] **K36.1 DFlash/Eagle3 HF sidecar discovery ✅ 2026-07-17**: experimental-v7 commit `0af063a88` ports upstream `635cdd5f` runtime behavior for auto-discovering `dflash-` and `eagle3-` HF sidecars. The patch adds sidecar plan fields, excludes DFlash/Eagle3 sidecars from primary model selection/cache listings, and wires fallback `speculative.draft.mparams.path` assignment when `--spec-type draft-dflash` or `draft-eagle3` is selected without an explicit draft. Validation: `git diff --check`; `cmake --build build-k24-cpu --target llama-cli llama-server -j16` (C++ targets linked; UI npm cache warning fell back to HF archive as usual); pinned `llama-cli`/`llama-server --help` and `--spec-type draft-{dflash,eagle3} --version` parser smokes. README updates were limited to the two stale `--spec-type` rows, not a full generated-doc import.
  - [x] **K36.2 recurrent rollback test activation ✅ 2026-07-17**: experimental-v7 commit `d1e5a20eb` carries upstream `32e789fdf` so `test-recurrent-state-rollback` runs against generated local recurrent-state models rather than depending on the downloaded model fixture. Validation: `cmake --build build-k24-cpu --target test-llama-archs test-recurrent-state-rollback -j16`; pinned `ctest --test-dir build-k24-cpu -R 'test-generate-models|test-recurrent-state-rollback' --output-on-failure`; pinned ASAN repeat with `ctest --test-dir build-asan -R 'test-generate-models|test-recurrent-state-rollback' --output-on-failure`.
- [x] **K11-REPEAT-SUMMARY-SOURCE — prevent partial or empty repeat sets from reporting task success.** The actual runner previously summarized only available task evaluations, allowing a passed repeat to hide another requested error/missing evaluation; --runs0 also yielded empty-set determinism success. MAIN reviewed exact two-file Researchf770-based source: reject nonpositive repeats before server launch, require every requested repeat to have status ok and boolean task pass, preserve absent oracle NULL. Bind full original test module including actual run_execute fake-server/persisted-summary regressions and existing captured-process cleanup control through VB-K11-REPEAT-SUMMARY-CONFORMANCE before publication. No model, live sampler/stop fix, historical result rewrite or K11.1 natural-prose acceptance. ✅ 2026-10-07 — [MAIN exact source and original30/30](../../artifacts/ni08/k11-repeat-summary-success-acceptance-20261007/README.md). Live K11 determinism remains independently gated.
- [x] **D4 — root-cause the HIP bf16 LIGHTNING_INDEXER numerical failure** ✅ 2026-08-13 — reproduced on
  frozen `production-consolidated-v9` (`0db32c06e`, build-hip `10125`); **NOT flaky** — deterministic and
  bf16-specific. `test-backend-ops -o LIGHTNING_INDEXER -p type_K=bf16` fails exactly the 6 `nb=1` configs
  (ERR≈1.0); `type_K=f16` passes 12/12 including all `nb=1`. The prior "flaky 5/5 vs 0/5" was a misread: the
  isolated run re-tested the *passing* `nb=512` shape. **Root cause narrowed to the bf16 load path of
  `lightning_indexer_kernel_vec`** (`lightning-indexer.cu`, reached via `get_dequantize_V<GGML_TYPE_BF16,…>`
  → `dequantize_V_bf16` in `fattn-common.cuh`): the WMMA kernel is `#if !defined(GGML_USE_HIP)` and never runs
  on gfx90a, so the handoff's "WMMA-era reduction" suspicion is wrong. Ruled out by inspection: tensor
  indexing (all 4 tensors cross-checked vs the CPU reference), the warp reduction (shared with f16, which
  passes), `nv_bfloat16`/`nv_bfloat162` sizes (2B/4B confirmed), and the HIP `ggml_cuda_cast<float2>` low/high
  bf16 extraction. A standalone ggml dump (`/tmp/opencode/dump_*.cpp`) confirms the bf16 output is a constant
  garbage value in the direct (non-graph) path for *all* batch sizes, while f16 is exact — i.e. the bf16 K
  load itself is defective, not the batch geometry. Latent correctness bug only (no production role uses a
  bf16 indexer K-cache). **Remaining for upstream filing**: pin the exact line via a `hipPrintf`/patched-build
  debug of `dequantize_V_bf16` vs the known-good `vec_dot_fattn_vec_KQ_bf16` (fattn-common.cuh:117) bf16 path,
  then file against upstream `ggml-cuda` (`#25545` is the introducing commit).
- [x] D1 pull/build/smoke PR #21149 — SUPERSEDED: DSA landed in v6 via generic-DSA #23346 (`deepseek32` + `glm-dsa` archs present); no draft-PR pull needed; smoke-test moved to the model-eval handoffs. ✅ 2026-07-16
- [x] Weekly monitoring of PR #21149 to merge-readiness — MOOT: DSA landed via #23346; stopped tracking #21149. ✅ 2026-07-16
- [x] Re-anchor D2/D3 to the LANDED #23346 code, not the fairydreaming draft. ✅ 2026-07-16
- [x] Run the static D2 landed-code audit: top-k selection is shared across prompt/decode, but final attention appears dense/mask-based. ✅ 2026-07-16
- [x] Close D2 with runtime evidence: current-source GLM-5.2 fixed-`indexer_top_k=32` KV-length scaling classified final attention as `DSA-DENSE-MASK` ✅ 2026-07-17
- [x] Re-run D3.1 "is the CPU indexer compute-bound?" profiling check on landed code before any contribution work — CLOSED NO-GO; `ggml_compute_forward_lightning_indexer` was only `1.08%` of cycle samples in the OP-2/B4 GLM-5.2 profile. ✅ 2026-07-19

