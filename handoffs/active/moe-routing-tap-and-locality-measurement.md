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

- [x] **RT-1 — The port, not a build.** COMPUTE-GATED — FILE ONLY. Port `llama-moe-trace`
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

  ✅ 2026-10-23 — port landed and captured. `llama-moe-trace` on `experimental/rt1-moe-trace-20261023` @ `42a0514db` (cut from `production-consolidated-v10`
  `ffc1bac82`, binary `b10303-ffc1bac82`, v10 store libs proven by linkage), Qwen3.8-Flash-Next UD-IQ4_XS (`qwen4exp`, 48 layers, 512 experts, top-10, int16
  ids), CPU, `-b 512`, finished 19:26Z. 3 workloads (prose wikitext-2 test, code v10-tree src + gguf-py, reasoning Fable-5 cot) x 512 windows of 512 tokens
  (windows 0-23 carry a greedy decode leg; windows 24-511 prefill only): 794,623 token rows in 27 shards, 27 verified, 0 quarantined, SELFTEST ok, RT-3
  stride-hazard guard 0 sub-chance checks, sha256 re-verified, 512/512 windows per domain, IR_t recomputed independently from the stored ids agrees with the tool
  to 5e-7. IR_t (prefill, mean over layers) 0.359 / 0.389 / 0.329 for code / prose / reasoning = 18.4x / 19.9x / 16.8x the 1.95 % chance, so this is not a
  stride-hazard artefact. Caveat: decode legs stop at EOS (7-128 decode rows per window; 2,975 / 2,373 / 2,843 decode rows per domain), so decode statistics
  rest on ~2.4-3k tokens. SELFTEST/schema/guard evidence also covers RT-2 (EOR rider, SCH rows) and RT-3 (hazard guard); those boxes are left to their owners.
  Evidence: research `data/moe-routing-rt1-q38fn-20261023/` (scripts `scripts/benchmark/moe_routing/`, commit d3db98e28); traces `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/results/`.

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
- [x] **RT-5 — AK-G rider: expert-skew report for Qwen3.6-35B-A3B on the CPU frontdoor.** From the RT-1 tap (or a diagnostic counter in MUL_MAT_ID), report per-layer share of selections in the top 10% and 25% of experts on >= 2 workloads against the 3.13% chance baseline. It gates CAFE-7 (MoE expert-cache HIP port): trigger is top-10% share >= 60% on >= 2 workloads. COMPUTE-GATED — FILE ONLY. (intake-1925 claim 1: the fork publishes no skew statistic) — Owner: workspace-ec (2026-10-06).
  - *(2026-10-23, 3c4ca599, RT-9.)* ✅ Target-model result, Qwen3.6-35B-A3B frontdoor: top-10 % share 0.503 / 0.419 / 0.463 prefill and 0.470 / 0.410 / 0.461 decode (code / prose / reasoning; uniform 0.104; top 25 % 0.73 / 0.68 / 0.74 prefill, null 0.25), 0 of 40 layers at >= 0.60 on every workload and leg. Decision rule as written (>= 0.60 on >= 2 workloads): NOT met on the frontdoor, so RT-5 does not trigger CAFE-7. Flash-Next RT-1 proxy for comparison: 0.576 / 0.464 / 0.477 prefill, 0.604 / 0.475 / 0.481 decode, 18 of 48 layers >= 0.60 on code prefill, gate also not met (decode code only). Two-model summary, as measured: the static-hot-set premise is weak on both production MoE models (top-10 % share 0.41-0.50 on q36, 0.46-0.60 on Q38FN, versus the 0.60 gate); this box is closed for its own scope (q36), DS41 is not covered by it. Not a final decision on CAFE-7, which also waits on RT-7 and DS41. Evidence: `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/analysis-q36/` (`comparison/comparison.md`, `rt5_skew/`, `rt6_placement/`, `rt7_residency/`, `locality/`); traces `.../results-q36/` (job inf72-rt1-q36 done 21:06Z; analysis job inf72-rt9-analysis done 21:18Z, q3 grant); same code as the Q38FN run (research d3db98e28).
    - 2026-10-28: RT-5 top-10% share 0.503/0.419/0.463 prefill, 0.470/0.410/0.461 decode (code/prose/reasoning) vs predeclared rule >= 0.60 on >= 2 workloads (higher = more skew) → reject (CAFE-7 trigger not met on the frontdoor; 0 of 40 layers >= 0.60 on any workload/leg). Verdict was filed 2026-10-23 above; filler inf72-rt9-analysis rc0, analysis COMPLETE. Evidence: /mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/analysis-q36/comparison/comparison.json. [belief: cc]

  - *(2026-10-23, 3c4ca599.)* Tooling done (`skew_report.py`), target-model run open (RT-9): the only trace is Qwen3.8-Flash-Next, not Qwen3.6-35B-A3B. Proxy result, share of selections on the top 10 % of experts (52 of 512; uniform 0.104; held-out ranking in brackets): prefill 0.576 [0.576] / 0.464 [0.463] / 0.477 [0.477] and decode 0.604 [0.593] / 0.475 [0.432] / 0.481 [0.463] for code / prose / reasoning; top 25 % 0.82 / 0.73 / 0.75 prefill (uniform 0.25). Gate (>= 0.60 on >= 2 workloads): NOT met on the proxy (prefill 0 of 3; decode 1 of 3, code only, on 2,975 tokens). Per-layer spread is wide (code prefill 0.33-0.71, 18 of 48 layers >= 0.60), normalised entropy 0.83 / 0.87 / 0.86. Evidence: research `data/moe-routing-rt1-q38fn-20261023/` (scripts `scripts/benchmark/moe_routing/`, commit d3db98e28); traces `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/results/`.

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

  - *(2026-10-23, 3c4ca599.)* Tooling done (`placement_replay.py`: contiguous, null-random, uniform-multinomial null, EPLB-global, DeepInfer window policy re-implemented from intake-2134's description because `policy.py` is not on this host, UltraEP-shape per-step oracle, MoonEP floor, exact Hall LP floor; DeepInfer/EPLB each at 0 and 32 (= E/16, +6.25 % expert bytes) redundant copies per layer, with idealized least-loaded and realizable random-replica dispatch), target-model run open (RT-9, RT-10). Proxy = Q38FN, 10 selections per token, 48 layers, replay on the 24 decode legs (T = 1 and 3) and 128 held-out 512-token prefill chunks, calibration on disjoint windows. Rule value 1.65 / (best realizable static arm), same-domain calibration: 4 NUMA bins T=1 1.04-1.08 (idealized dispatch 1.14-1.21), T=3 1.17-1.22, prefill 1.53-1.56; 12 CCD bins T=1 0.59-0.63, T=3 0.73-0.79, prefill 1.32-1.40. Cross-domain calibration: 4 bins T=1 1.00-1.01, T=3 1.11-1.15. The per-step oracle and MoonEP sit at the integrality floor (T=1: 1.20 at 4 and 12 bins, T=3: 1.067 / 1.20, prefill 1.00), which passes the rule trivially, so the bound never closes the item; the finding is that at T=1 contiguous placement equals the multinomial null (4 bins: 1.675 vs 1.678) and the best realizable static arm improves on it by only 6-9 % (1.53-1.59), so only T=3 at 4 NUMA bins (and prefill) clears 1.10 realizably. Static replication of 32 experts buys little at decode without exact-state dispatch. Evidence: research `data/moe-routing-rt1-q38fn-20261023/` (scripts `scripts/benchmark/moe_routing/`, commit d3db98e28); traces `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/results/`.
  - *(2026-10-23, 3c4ca599, RT-9.)* Frontdoor (Qwen3.6-35B-A3B) arm done; box stays open (DS41 arm = RT-10). Rule value 1.65 / (best realizable static arm), code / prose / reasoning, same-domain calibration: 4 NUMA bins T=1 1.01 / 0.99 / 1.02, T=3 1.18 / 1.13 / 1.16, prefill 1.54 / 1.50 / 1.54; 12 CCD bins T=1 0.56 / 0.54 / 0.57, T=3 0.73 / 0.67 / 0.72, prefill 1.32 / 1.22 / 1.34. Cross-domain calibration: 4 bins T=1 0.97 / 0.96 / 0.98, T=3 1.11 / 1.08 / 1.10, prefill 1.32 / 1.27 / 1.35; 12 bins T=1 0.52, T=3 0.62-0.66, prefill 0.85-0.99. The per-step oracle and MoonEP sit at 1.000 (bound only, passes trivially). Same picture as Q38FN (4 bins T=1 1.04-1.08, T=3 1.17-1.22, prefill 1.53-1.56): at T=1 the best realizable static arm does not beat the null (contiguous 1.768 vs uniform multinomial 1.772), only T=3 at 4 NUMA bins and prefill clear 1.10 realizably, and a placement calibrated on another workload gains little or nothing. DI-081 reading, as measured: realizable static arms meet 1.10 on 3 of 3 workloads only at 4 bins T=3 (same-domain; 2 of 3 cross-domain) and on none at T=1 or at 12 bins; so the static-placement gain is workload-specific and small at decode on both models. Evidence: `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/analysis-q36/` (`comparison/comparison.md`, `rt5_skew/`, `rt6_placement/`, `rt7_residency/`, `locality/`); traces `.../results-q36/` (job inf72-rt1-q36 done 21:06Z; analysis job inf72-rt9-analysis done 21:18Z, q3 grant); same code as the Q38FN run (research d3db98e28).
- [x] **RT-2.1 — Trace-shape rider for the replays (intake-2134#record).** The tap keeps token order and sample boundaries, tags each token prefill vs decode (and the speculative block size), and covers deepseek41 including the 128-expert DSpark layers (int16 ids), so RT-6/RT-7 can derive [steps, layers, experts] counts; an aggregate-only dump is insufficient. COMPUTE-GATED - FILE ONLY. ✅ 2026-10-24
  - *(2026-10-20, workspace-f8.)* schema + validator + 16 tests + C++ change spec on epyc-inference-research feat/rt21-20261020 @ ce1a1f4e5 (merged to research main today); the tap itself is still RT-1; evidence /mnt/raid0/llm/epyc-inference-research feat/rt21-20261020 @ ce1a1f4e5. Box left open for main review: schema, validator and C++ change spec delivered (FILE ONLY done criterion arguably met); tick once main confirms the tap itself stays under RT-1.
  - *(2026-10-24, f8 sweep.)* Ticked: FILE ONLY criterion met and confirmed. Schema, validator, 16 tests and the C++ change spec are on research main (`ce1a1f4e5` is an ancestor of origin/main). The tap itself shipped under RT-1 (ticked) and its traces carry the shape RT-6/RT-7/RT-8 consumed (prefill vs decode legs, T = 1 and 3, `validate_traces.py`). The DS41 part (hash layers, 128-expert DSpark/MTP layers, int16 ids) is owned by RT-10, which keeps RT-6 and RT-7 open.
- [ ] **RT-7 — Residency hit-rate curve h(k) and stationarity for DS41 hot experts on the MI210 (intake-2116#record, intake-2139#record).** Offline from RT-1 traces: for k in {39, 53, 63} experts/layer with greedy cross-layer allocation, the share of top-6 selections covered by a static ranking learned on domain A and scored on domain B, plus top-set overlap between consecutive 1k-step windows. Rule: open the HIP MXFP4 expert-cache work (CAFE-7) only if h(53) >= 0.30 on >= 2 workloads and the HIP resident MXFP4 MoE kernel check passes; h < 0.23 closes it. Per-step dynamic prefetch is excluded (fetch costs ~5.7 CPU reads).

  - *(2026-10-23, 3c4ca599.)* Tooling done, target-model run open: `residency_curve.py` run on the Q38FN trace (512 experts, top-10, so a PROXY, not DS41 6-of-384). k rescaled to the same pool fraction as 53/384 is 71/512. Same-domain held-out static ranking: h(53) = 0.583 / 0.469 / 0.485 (code / prose / reasoning prefill; chance 0.104), h(71) = 0.667 / 0.548 / 0.568; same-domain prefill-learned ranking scored on decode h(53) = 0.568 / 0.395 / 0.428. Cross-domain (learned on A, scored on B) h(53) = 0.049-0.163 on every pair, i.e. < 0.23 on all three workloads and barely above chance, so a ranking learned on one workload does NOT carry to another: the hot set is workload-specific (top-10 % expert-set Jaccard between workloads 0.02-0.08 vs 0.054 random). Stationarity (top-53 set, consecutive 1024-row blocks): Jaccard 0.52-0.66 vs 0.055 random and 0.73-0.83 ceiling; next-block coverage 0.49-0.68. Literal gate on the proxy: same-domain >= 0.30 on 3/3, cross-domain on 0/3; which one is the right reading depends on whether the serving ranking is learned on the workload it serves, to be stated before the DS41 run. Evidence: research `data/moe-routing-rt1-q38fn-20261023/` (scripts `scripts/benchmark/moe_routing/`, commit d3db98e28); traces `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/results/`.
  - *(2026-10-23, 3c4ca599, RT-9.)* Qwen3.6-35B-A3B proxy (256 experts, top-8; k rescaled to the DS41 pool fraction, 53/384 is 36/256), box stays open (DS41 and the HIP kernel check are the gate). Same-domain held-out static ranking, code / prose / reasoning: prefill h(36) = 0.583 / 0.508 / 0.558, h(53) = 0.679 / 0.624 / 0.679 (chance 0.141 / 0.207); same-domain prefill-learned scored on decode h(36) = 0.508 / 0.394 / 0.513, h(53) = 0.605 / 0.491 / 0.629. Cross-domain (learned on A, scored on B) h(36) = 0.086-0.249 and h(53) = 0.136-0.335 across the six pairs (decode h(53) 0.139-0.325): below 0.30 on 4 of 6 pairs at h(53), near chance for code<->prose, with only reasoning scored from code/prose and code from reasoning reaching 0.29-0.34. Stationarity (top-53 set, consecutive 1024-row blocks): Jaccard 0.64 / 0.64 / 0.64 prefill (random 0.115, ceiling 0.79-0.82); next-block coverage 0.67-0.73. Versus Q38FN (h(53) same-domain 0.583 / 0.469 / 0.485, cross-domain 0.049-0.163): a hot set learned on one workload is predictive of that workload and weakly of others on both models; q36 cross-domain transfer is better (reasoning shares with code) but the hot sets are still workload-specific (top-10 % Jaccard 0.03-0.13 vs 0.054 random). The gate reading (same-domain vs cross-domain) still has to be stated before the DS41 run. Evidence: `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/analysis-q36/` (`comparison/comparison.md`, `rt5_skew/`, `rt6_placement/`, `rt7_residency/`, `locality/`); traces `.../results-q36/` (job inf72-rt1-q36 done 21:06Z; analysis job inf72-rt9-analysis done 21:18Z, q3 grant); same code as the Q38FN run (research d3db98e28).

- [x] **RT-8 — Locality analysis suite on the Q38FN trace (reuse, reuse distance, co-activation, entropy, cross-workload overlap).** ✅ 2026-10-23 `locality_report.py`, `skew_report.py`, `validate_traces.py`. Adjacent-token IR_t 16.8-19.9x chance (above). Within-window LRU hit rate per layer (cache of k experts, first use = compulsory miss ~5-6 %): k = 32 0.47-0.52, k = 64 0.62-0.68, k = 128 0.80-0.88, k = 256 0.92-0.97; median stack distance 28-38 experts. Co-activation: excess over rescaled independence 0.47-0.51 of pair mass (Poisson noise floor 0.02-0.03), max pair lift 112-121, 12-14 % of pairs at lift >= 2. Cross-workload top-10 % expert-set Jaccard 0.02-0.08 (random 0.054, within-domain even/odd ceiling 0.95), Spearman of per-expert counts -0.12 to 0.31. Evidence: research `data/moe-routing-rt1-q38fn-20261023/` (scripts `scripts/benchmark/moe_routing/`, commit d3db98e28); traces `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/results/`.
- [x] **RT-9 — Qwen3.6-35B-A3B frontdoor trace, then rerun the suite (closes RT-5 and the RT-6 frontdoor arm).** Same `trace_job.sh` with `RT1_MODEL=/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf RT1_RAM_GIB=45 RT1_OUT=.../results-q36` (qwen35moe, 256 experts, top-8, chance 3.13 %). FILLERS row draft + preflight `precond_q36.sh` (rc 0) in `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/NEXT_ROWS.md`; est. ~2 h on 24 cores. Then `validate_traces.py`, `skew_report.py`, `locality_report.py`, `placement_replay.py` on `results-q36`, tick RT-5 and record the RT-6 frontdoor numbers. ✅ 2026-10-23 — trace and suite rerun on Qwen3.6-35B-A3B (40 layers, 256 experts, top-8). Skew (top-10 % share, 25.6 experts of 256; uniform 0.104; in-sample): prefill 0.503 / 0.419 / 0.463 and decode 0.470 / 0.410 / 0.461 for code / prose / reasoning (held-out 0.503/0.418/0.463 and 0.459/0.390/0.436); layers meeting the 0.60 gate 0 of 40 on every workload and leg (per-layer max 0.58-0.59). Cross-workload top-10 % Jaccard prefill 0.028 / 0.129 / 0.084 and decode 0.046 / 0.134 / 0.053 (code|prose, code|reasoning, prose|reasoning) vs random 0.0535; within-domain even/odd ceiling 0.946 prefill, 0.629 decode. LRU within-window hit rate (k = 32/64/128/256): 0.55-0.67 / 0.75-0.81 / 0.92-0.94 / 0.96-0.99. h(k) vs Q38FN below under RT-7, placement under RT-6. Evidence: `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/analysis-q36/` (`comparison/comparison.md`, `rt5_skew/`, `rt6_placement/`, `rt7_residency/`, `locality/`); traces `.../results-q36/` (job inf72-rt1-q36 done 21:06Z; analysis job inf72-rt9-analysis done 21:18Z, q3 grant); same code as the Q38FN run (research d3db98e28).
- [ ] **RT-10 — DS41 tap hook and DS41 trace, then RT-6/RT-7 on DS41.** The Q38FN tap records `ffn_moe_topk`; in `src/models/deepseek4.cpp` the first `dsv4_hash_layer_count` layers take `selected_experts = ggml_get_rows(ffn_gate_tid2eid, tokens)` (~line 1332) with no such callback, and the 128-expert DSpark/MTP layers need a decision (RT-2.1 spec). Build task on the experimental branch (not a decline reason), then a DS41 MXFP4 trace via the same job (draft row `inf72-rt1-ds41`, BACKLOG blocker=build in `NEXT_ROWS.md`), then `placement_replay.py` / `residency_curve.py` with `--ref-experts` as shipped. RT-6 and RT-7 stay open until this lands.
  - [x] Prepare RT-10 DS41 trace and RT-6/RT-7 analysis, including model-free verification ✅ 2026-10-27 [no-belief: preparation/fixture only]. Frozen C5 tool build `c72ec82f5417bb2937310326120f149b665e8400` completed 19:29:56Z; two native CTests and selftest passed. Private packet `/mnt/raid0/llm/tmp/refactor-01a16fc3/rt10-ds41-tap-ready/` seals trace manifest `91416a25024b180b56929b1e7acc5a7d7a856760723c7faf074e40665ea5e245` / PF `ef8451aed20891288d40c26af477f748a93fdd08b1de7c32` and analysis manifest `eca3cf8142692343af7bfd8c8317669bafae09121ecb7a1e236d3b9b34110dd3` / PF `ac5c7a6602831009323ca05342929ca8247aade5b56461cf`; normal admit and validator 0/0. Synthetic trace → native verification → original same-attempt binding → existing RT6/RT7 belief writer and partial/corpus/hash/missing/gap refusals passed. Capture binds raw and effective prompt hashes, including C5 `-f` removal of one trailing LF. Actual trace remains HELD pending DS41-1017 HOLD lift and a whole-host grant (739 GiB plus 64 GiB margin); analysis additionally requires a real COMPLETE trace and grant. No model, GPU or inference was used; trunk-only capture makes no DSpark/MTP or throughput claim. Prospective integration and canary remain open under VB-MOE-RT10-CAPTURE-LINK.
- [x] **RT-6.2 — Replay fidelity items.** Diff the DeepInfer re-implementation against `policy.py` (deepseek-ai/DeepInfer @ 774ce24) once fetched, and add a calibration-lag sweep (history window vs step staleness) since the proxy shows static and cross-domain placements losing most of their gain. <!-- evidence-integrity: Research `d5e400c9010a671a0ab4ca912e4e6f9abc1ac1d3`; main `3bbeac0a1d916b6ee703abebdb48297cd77c1e2f`; artifact: artifacts/compute/refactor-rt62-source-20261031/EVIDENCE.json; ✅ 2026-10-31; [no-belief: new diagnostic writer/adapter not enrolled; no captured claim tuple] -->

  <!-- task-evidence-integrity:start RT-6.2 -->
  - Evidence metadata: Research `d5e400c9010a671a0ab4ca912e4e6f9abc1ac1d3` (main `3bbeac0a1d916b6ee703abebdb48297cd77c1e2f`); [source/test/audit custody](../../artifacts/compute/refactor-rt62-source-20261031/EVIDENCE.json). The exact pinned upstream774ce244 CPU control demonstrates surrogate replication differences. New NumPy diagnostic keeps the original policy and DI-081 unchanged; full48-layer×3domain T=1/B=4 H{1,4,16}×lag{0,1,8} sweep uses eight paired targets/cell. Nine NumPy controls, eleven separate upstream controls and Ruff pass. No exact fidelity, causal workload effect, runtime/model/grade claim or RT-6/RT-10 completion. Prospective existing-family write/projection gap is filed under VB-RT62-LAG-PROJECTION. [no-belief: new diagnostic writer/adapter not enrolled; no captured claim tuple]
  <!-- task-evidence-integrity:end RT-6.2 -->

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

- [x] **RT-5.1 — Expert-load statistics rider for RT-5/RT-6.** COMPUTE-GATED — FILE ONLY. Add per-layer MaxVio, MinVio and inactive-expert ratio (intake-2195#record definitions) to the RT-5/RT-6 offline analysis of RT-1 traces (numpy, no inference), reported against the same chance baselines.

  ✅ 2026-10-23 — `skew_report.py` (MaxVio = (max-mean)/mean, MinVio = (mean-min)/mean, inactive ratio; each beside a uniform-router null with the same row count). Q38FN prefill, mean over layers, whole-stream: MaxVio 19.2 / 15.9 / 12.9 (code / prose / reasoning; null 0.04; worst layer 22-44), inactive 0.2-0.7 % (null 0), per 512-token chunk inactive 41-48 % (null 0). MinVio is ~1.0 everywhere because some expert is idle in every stream, so it carries no signal at this expert count; the paper's 0.5 scale is a different aggregation. Qwen3.6 frontdoor rerun is RT-9. Evidence: research `data/moe-routing-rt1-q38fn-20261023/` (scripts `scripts/benchmark/moe_routing/`, commit d3db98e28); traces `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/results/`.

- Trigger (no checkbox): a first-party report names the load-balancing method used to train Qwen3.8-Flash-Next or DeepSeek-V4.1-Flash. Then interpret the RT-5 skew statistics against that training objective (intake-2195#05).
