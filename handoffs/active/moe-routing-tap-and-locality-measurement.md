# MoE per-token routing tap and locality measurement (INF-72)

**Status**: stub
**Created**: 2026-09-07 (research intake, operator-approved plan)
**Categories**: moe, gpu_acceleration, benchmark_methodology
**Related**: [mi210-big-model-and-acceleration-roadmap.md](mi210-big-model-and-acceleration-roadmap.md) (INF-34) · [cpu-decode-roofline-program.md](cpu-decode-roofline-program.md) (INF-70) · [vidya-belief-substrate-program.md](vidya-belief-substrate-program.md) (SC66)

## Objective

Stand up a per-token MoE routing tap on our own fleet and measure expert-selection locality directly —
SRP (per-expert rank/mask) and SCH (top-k schedule) plus an EOR/IR_t reuse rider — so that any
offload, expert-cache or residency argument on this box rests on a measured local number instead of a
foreign paper's. The instrument is the deliverable; no throughput claim is licensed by it.

## Research Context

| Intake | Status | What it contributes |
|---|---|---|
| `intake-1328` | dive-verified | The from-scratch tap build, **superseded** by the port in 1336; the shared-expert census that makes the Qwen fleet an open question rather than a favourable one |
| `intake-1336` | dive-verified | `llama-moe-trace` as a portable instrument, the four required adjustments, and the strided-read hazard |
| `intake-1338` | dive-verified | What the tap must emit, the SCH oracle's real size, and the chance baselines that make a locality number interpretable |

## Tasks

- [ ] **RT-1 — The port, not a build.** COMPUTE-GATED — FILE ONLY. Port `llama-moe-trace`
  (MIT, `github.com/Shriniwas410/cacheable-by-design` @ `03366ef1`, files
  `llama-moe-trace/moe-trace.cpp` + `routing-lab/06_convert_gguf_trace.py`) onto an
  `llama.cpp-experimental` branch off **current production**. Four verified adjustments:
  1. **int16, not int8** — our 256/512-expert fleet overflows int8.
  2. `-b 512` with the existing per-chunk `llama_memory_clear` yields the `[samples, 512, top_k]`
     geometry by reshape.
  3. **SRP additionally needs `ffn_moe_argsort`** (cb-named at `src/llama-graph.cpp:1985`); SCH needs
     only what the tap emits.
  4. v9 covers `qwen35moe` and `qwen3next` but **not** `qwen4exp` / `glm5next`.

  "Zero-surgery" means zero-surgery-to-the-model; an experimental branch is still required.
  `intake-1336#00`, superseding the from-scratch build in `intake-1328#record`.

- [ ] **RT-2 — What it emits, plus the EOR rider and the chance baselines.** COMPUTE-GATED — FILE ONLY.
  Per MoE layer: top-k expert-index tensor `[samples, tokens, top_k]` (SCH) plus per-expert rank/mask
  (SRP); m ∈ {4, 16, 64, 256}; 512-token samples × 2,048 per domain sufficed. SRP needs no simulator;
  SCH needs the incremental oracle (**201 lines**, `41_sch_calc.py:12-212` — *not* the "20-line"
  figure, already corrected in-index). **Rider**: emit **EOR/IR_t** alongside —
  `|E_t ∩ E_{t-1}| / K` over the same top-k tensor SRP already consumes, free once the tap exists.
  Chance baselines, mandatory so a number is interpretable: **8/256 = 3.13%** (qwen35moe),
  **10/512 = 1.95%** (qwen4exp), against DeepSeek-V2-Lite's 9.38% where ReMoE's baseline was already
  2.91× chance. `intake-1338#01`.
  *Rider 2026-09-23 (intake-1524#03; compute-gated, file only):* cross-artifact route-set agreement — run the ported tap on a
  reference GGUF (Q8_0/BF16 experts) and a Q4_K candidate of the SAME model over the IDENTICAL token stream; emit per-layer
  top-k Jaccard, the share of token-layers with at least one replaced expert, a repeat floor and a chance baseline, labelled
  occurrence-only (not damage). v10 `llama-quant.cpp:304-307` never quantizes `ffn_gate_inp`, so flips come from upstream
  perturbation.

- [ ] **RT-3 — The stride hazard: BLOCKING, read before writing any tap code.** COMPUTE-GATED —
  FILE ONLY. Tell-tale signature: *every expert appearing exactly k times, sub-chance reuse*. Cause:
  a flat read of a strided router tensor. Fix: row-by-row `ggml_backend_tensor_get` at offset
  `i * t->nb[1]`. Anchored in our own tree at `ggml/src/ggml.c:5373` and `src/llama-graph.cpp:1987`.
  This is a measurement-integrity item — the broken read manufactures a **plausible-looking negative**,
  exactly the failure "vacuous verification" and "rule out the test method first" exist to catch.
  `intake-1336#00`.

- [x] **RT-4 — Scope-out, written down so the numbers are never re-cited.** COMPUTE-GATED — FILE ONLY.
  Source boundary: Suram, [*Cacheable by Design?*, arXiv:2608.18261v1](https://arxiv.org/html/2608.18261v1) §§2–5 and Limitations (v)
  (`intake-1336#record`, `intake-1336#05`). Its serving measurements and PMS ceiling use one RTX 3070
  with 8 GB VRAM, 32 GB system RAM, a 134 GB Q4_K_M model, and a DRAM-less PCIe-3 NVMe SSD measured at
  about 2.4 GB/s. The paper's PMS result (about 0.9 tok/s; 2–7× over its baseline) is a projection
  from measured IO/cache rates, not an end-to-end PMS deployment. These machine-specific measurements
  and projections do not transfer to EPYC, and a local routing/SCH result alone licenses no throughput
  claim. This scope-out is documentary; it calls for no local capture or performance measurement.

  ✅ 2026-10-07 — MAIN independently checked the primary source and accepted this documentary scope-out; no local inference or throughput claim.
- [ ] **RT-5 — AK-G rider: expert-skew report for Qwen3.6-35B-A3B on the CPU frontdoor.** From the RT-1 tap (or a diagnostic counter in MUL_MAT_ID), report per-layer share of selections in the top 10% and 25% of experts on >= 2 workloads against the 3.13% chance baseline. It gates CAFE-7 (MoE expert-cache HIP port): trigger is top-10% share >= 60% on >= 2 workloads. COMPUTE-GATED — FILE ONLY. (intake-1925 claim 1: the fork publishes no skew statistic) — Owner: workspace-ec (2026-10-06).

## Open Questions

- Does `qwen4exp` / `glm5next` coverage need its own graph-side work, or does the v9 gap close on its
  own once the port lands on a newer experimental base? (RT-1 adjustment 4.)
- Which domains and how many 512-token samples are needed on *our* fleet before an SRP/SCH number is
  stable — the 2,048-per-domain figure is the source's, not ours.
- Does EOR/IR_t clear its chance baseline on either fleet? A result at or below 3.13% / 1.95% is a
  negative and must be reported as one.

## Notes

- **Compute-gated — FILE ONLY. Never run.** Nothing in this stub authorises a build, a benchmark, or a
  model load; the tasks are recorded so the instrument can be built when compute is granted.
- Production kernels are FROZEN: all work happens on an `llama.cpp-experimental` branch cut from the
  current production tip, never on the production tree.
- The mi210 roadmap (INF-34) carries a cross-link line to this file, not a second index row — one
  handoff, one owner.
- Wire the tap's output into the belief kernel on the **write** side when RT-2 is built (SC66); a
  claim tuple invented on read cannot recover warrant the run never captured.

## Research intake 2026-10-20 — DeepInfer (research intake entries 2116–2142, see research/intake_index.yaml)

Operator-approved 2026-10-20 via research intake (plan sha256 recorded in the session's stage3_filing).

- [ ] **RT-6 — Offline expert-placement replay on RT-1 traces, DS41 + frontdoor (intake-2116#record, intake-2134#record, intake-2138#record, intake-2141#record, intake-2142#record).** Numpy, no inference (capture is RT-1). Bins = 4 NUMA nodes and 12 CCDs; T in {1, 3} decode plus one prefill-chunk row. Arms: DeepInfer windowed per-step-peak policy (policy.py port), EPLB-global (eplb.py @ d52c72d), a zero-lag exact-load oracle (UltraEP planner logic), MoonEP rank-level greedy, and the LPLB fractional LP floor as a bound only; score every arm by per-step max/mean with the null model beside it and replication priced in copied bytes. Rule: if even the oracle/LP bound fails 1.65 / (best max/mean) >= 1.10 on >= 2 workloads, close as a negative recorded in large-moe-expert-parallelism.md.
- [ ] **RT-2.1 — Trace-shape rider for the replays (intake-2134#record).** The tap keeps token order and sample boundaries, tags each token prefill vs decode (and the speculative block size), and covers deepseek41 including the 128-expert DSpark layers (int16 ids), so RT-6/RT-7 can derive [steps, layers, experts] counts; an aggregate-only dump is insufficient. COMPUTE-GATED - FILE ONLY.
  - *(2026-10-20, workspace-f8.)* schema + validator + 16 tests + C++ change spec on epyc-inference-research feat/rt21-20261020 @ ce1a1f4e5 (merged to research main today); the tap itself is still RT-1; evidence /mnt/raid0/llm/epyc-inference-research feat/rt21-20261020 @ ce1a1f4e5.
- [ ] **RT-7 — Residency hit-rate curve h(k) and stationarity for DS41 hot experts on the MI210 (intake-2116#record, intake-2139#record).** Offline from RT-1 traces: for k in {39, 53, 63} experts/layer with greedy cross-layer allocation, the share of top-6 selections covered by a static ranking learned on domain A and scored on domain B, plus top-set overlap between consecutive 1k-step windows. Rule: open the HIP MXFP4 expert-cache work (CAFE-7) only if h(53) >= 0.30 on >= 2 workloads and the HIP resident MXFP4 MoE kernel check passes; h < 0.23 closes it. Per-step dynamic prefetch is excluded (fetch costs ~5.7 CPU reads).

**Dormant triggers (no checkbox, no index next action; materialize a task only when the trigger is observed). 'An' in a row means that intake entry's own dive-ledger row n:**

- DI-037 (intake-2123): monitor: a MoE role with experts resident on the MI210 enters the lineup and MMQ_MMID shows as a top kernel in the HIP route log (GGML_CUDA_LOG_MMVQ_ROUTE); then compare MMQ_MMID against a masked-layout kernel
- DI-081 (intake-2116#record): monitor: RT-6 replay result - trigger: 1.65 / (best max/mean) >= 1.10 on >= 2 workloads at T in {1,3}; then open CPU15-REVAL with the EPLB planner as the dispatch policy (CPU20 canonical matrix, 3 reps, PPL gate)
- DI-118 (intake-2134): monitor: a model with n_group > 1 and topk_group routing is added to the lineup (check config.json for n_group/topk_group)
- DI-138 (intake-2139): monitor: trigger = DS41-T7 delivers t_cpu and t_gpu per token-expert AND RT-7 shows h(53) >= 0.30 on >= 2 workloads (then open the CAFE-7 design with MoonEP's slot-pool layout as the reference)
- DI-148 (intake-2142): knowledge-only: retain LPLB as the min-max replica-edge LP formulation reference and as the (non-quantified) 'LPLB loses to EPLB under extreme global imbalance, one replica per expert' limitation; monitor trigger: RT-6/RT-6 shows an LP-floor pass of the decision rule at T=1..3 that integral power-of-two-choices does not reach.

**Retained knowledge (no task):**

- DI-036 (intake-2123): knowledge-only: layout recipe retained as the design input for A1 if the fused node is positive; do not task before A1 measures (CPU decode is bandwidth-bound, the layout changes locality not bytes)
- DI-114 (intake-2133): knowledge-only: confirms scale-pack granularity/order is an implementation choice tuned to each vendor's cache/DMA width, not a constraint on ggml's own MXFP4 format; no action needed
- DI-117 (intake-2134): knowledge-only: EPLB is the right reference for NUMA-bin balancing (RT-6) and the wrong shape for CPU-vs-MI210 residency (RT-7), which is a top-k coverage curve
- DI-122 (intake-2135): knowledge-only: no EP reopen without a new bottleneck proof (large-moe-expert-parallelism.md reopen rule); retain the no-CPU-sync decode idea for that day
- DI-123 (intake-2135): knowledge-only: confirms D4-A9's shape; no new task
- DI-135 (intake-2138): knowledge-only: records why UltraEP-style per-step planning is not a decode candidate (excluded by its authors; quota floor and byte-neutral replication at T=1-4); revisit only if RT-6's oracle arm shows >=1.10 headroom at T in {1,3}
- DI-136 (intake-2138): knowledge-only: retained use = break-even formula for any MoE prefill GPU-assist design (cite UltraEP quota floor as the same idea); no task until DS41-T7 produces t_cpu and t_gpu per token-expert
- DI-137 (intake-2139): knowledge-only: records the 5.7x fetch-vs-read break-even that rules out per-step MoonEP-style prefetch at decode on this host; RT-7 (already proposed) remains the decision instrument
- DI-145 (intake-2141): knowledge-only: UltraEP is retained as the reference for exact-load planning and for the finding that history windows go stale in prefill/training; its runtime is NVLink-domain EP infrastructure with no EPYC consumer. Re-open only if RT-6 shows an oracle-vs-history gap at T>=512 that the CPU prefill path (cpu-prefill-compute-large-models.md) could exploit.
- DI-146 (intake-2141): knowledge-only: main session carries the narrowing into intake-2138 claim 6 (see claim_corrections).

## Research intake 2026-10-21 — open-model backdoors, control-vector projection, Qwen3.8 post-train (research intake entries 2191–2213, see research/intake_index.yaml)

- [ ] **RT-5.1 — Expert-load statistics rider for RT-5/RT-6.** COMPUTE-GATED — FILE ONLY. Add per-layer MaxVio, MinVio and inactive-expert ratio (intake-2195#record definitions) to the RT-5/RT-6 offline analysis of RT-1 traces (numpy, no inference), reported against the same chance baselines.

- Trigger (no checkbox): a first-party report names the load-balancing method used to train Qwen3.8-Flash-Next or DeepSeek-V4.1-Flash. Then interpret the RT-5 skew statistics against that training objective (intake-2195#05).
