# Stage-3 plan: kernels, speculative decoding and eval rigor (intake-kspec-1125), DRAFT for operator approval

<!-- In-house line citations are pinned at lane head f19b902 (handoffs, scripts) unless marked; C21 llama.cpp at 98ff8a4; epyc-orchestrator template_provenance.py at faa783c7; epyc-inference-research census_extract.py at 4ca0d0d9a. -->

**Status:** awaiting operator approval. Nothing below has been written to any handoff or index. Stage 4 applies exactly this plan after approval.

## Run summary

- **Sources:** 15 operator-submitted (llama.cpp PRs #32921 and #32867, 13 arXiv papers) as intake-2956 to intake-2970.
- **Stage 1:** 7 literature expansions (cap 10): intake-2971 Stream-K, intake-2972 Dating the Model, intake-2973 Speculative Decoding Speed-of-Light, intake-2974 UBTree, intake-2975 TreeSpark, intake-2976 ForeSpark, intake-2977 Merged Not Measured. All 22 are relevance medium or high, so all were recommended for a dive and, under the operator's pre-approval, dived.
- **Stage 2 wave 1:** 9 dives (K1, K2, S1 on opus; K3, K4, S2, S3, M1, M2 on sonnet). intake-2961 (MXFP4 PTQ) has no arXiv HTML rendering, so it stays stage1-unverified with a hand-checked PDF read; no number from it is used below.
- **Stage 2b wave 2:** 4 dive-surfaced sources ingested and dived (2 sonnet dives): intake-2978 Overflow-Aware Scaling for MXFP4, intake-2979 agent performance-PR validation study, intake-2980 certified sparse attention, intake-2981 top-k attention via total variation. Every source the wave-2 dives surfaced was recommended decline, so the close-out gate closed after **2 of the 4 permitted sweeps**.
- **Second reader (haiku):** 160 quotes; 87 support their claim, 67 partly, 6 do not. The 6 were dropped (intake-2960 x3, intake-2962 x2, intake-2965 x1).
- **Subagents:** 3 opus (medium), 8 sonnet (medium), 7 haiku (low). Fetching, anchoring, integration and main review by the integrator (Opus).
- **Main-review corrections to dive output:** two dives returned verdict strings outside the enum (S2, S3); normalised to the enum. W2A returned placeholder IDs; renamed to intake-2978/2979. Steering item 9's "SPEC-DISTS-TRUNC" is the draft-length cap fix, not vocabulary truncation (dive S2, recorded in the K2 note).

## Per-source verdicts

| Intake | Source | Verdict | Read | One-line finding |
|---|---|---|---|---|
| intake-2956 | PR #32921 stream-k column-outer walk | worth_investigating | FULL | No-op on served gfx90a shapes; GB10 numbers confirmed |
| intake-2957 | Shifter Quantization | worth_investigating | FULL | Exact full-K integer dot; SHI2's 3.77x pairs a 4-bit-activation speed with an 8-bit-activation KL |
| intake-2958 | Below the Stopwatch | adopt_patterns | FULL | Claimed-mechanism witness with A/A; preliminary (82 PRs, one machine) |
| intake-2959 | TACPU | worth_investigating | FULL | 2.01x only at 128K on the AMX Xeon; llama.cpp never a baseline |
| intake-2960 | Roofline AI estimation | worth_investigating | FULL | Numbers confirmed; traffic is the weak half; no help to our census |
| intake-2961 | MXFP4 PTQ composability | worth_investigating | PARTIAL (PDF) | stage1-unverified; Midmax is a small weight rule |
| intake-2962 | PR #32867 HIP DPP scan | worth_investigating | FULL | No served consumer; "neutral below 1024" holds only on RDNA4 |
| intake-2963 | Pando | worth_investigating | FULL | Speedups modelled; noise coupling lossless only with a target-sample walk |
| intake-2964 | Draft calibration | already_integrated | FULL | Lossless; our SPEC-DRAFT-SHARPEN replay already closed it |
| intake-2965 | LEGOSpec / DFlux | worth_investigating | FULL | Gains confounded by training scale; no checkpoint released |
| intake-2966 | GramDelta | worth_investigating | FULL | Gain needs mid-request grammar growth; static cost equal across engines |
| intake-2967 | System-prompt date | adopt_patterns | FULL | 6.6% median churn confirmed; 36.5 points is an out-of-window searched date |
| intake-2968 | RECAP | worth_investigating | FULL | Gain about 1.2 sigma; the distortion score works untrained |
| intake-2969 | Effort training OPD vs RL | worth_investigating | PARTIAL | Every result needs training; operator's 58%/43% are not printed (paper prints 60.8%/46.3% vs the reference) |
| intake-2970 | Limits of Top-K | worth_investigating | FULL | Numbers exact; about singleton-KL ranking, not learned indexers |
| intake-2971 | Stream-K | already_integrated | FULL | Tile-visit order is the paper's own future work |
| intake-2972 | Dating the Model | adopt_patterns | FULL | Independent corroboration; "exceeds batch size" holds narrowly |
| intake-2973 | Speed-of-Light bound | worth_investigating | FULL | Bound holds for stochastic targets only; no concurrency analysis |
| intake-2974 | UBTree | worth_investigating | FULL | 27B datapoint 4.78x vs DFlash 2 4.24x (TP4, batch 1); load-adaptive trees win at concurrency |
| intake-2975 | TreeSpark | worth_investigating | PARTIAL | Calibration is for tree stopping, not draft temperature |
| intake-2976 | ForeSpark | worth_investigating | PARTIAL | Gain is a high-load drafting-cost effect |
| intake-2977 | Merged, Not Measured | worth_investigating | PARTIAL | Re-execution pilot with agent-built workloads; no population rate |
| intake-2978 | Overflow-Aware Scaling (MXFP4) | adopt_patterns | FULL | Same round-up threshold as Midmax; W4A4 only |
| intake-2979 | Agent perf-PR validation study | adopt_patterns | PARTIAL | Artifact-only; does not corroborate mechanism checks |
| intake-2980 | Certified sparse attention | worth_investigating | PARTIAL | Certificate needs a 4-bit scan of every key |
| intake-2981 | Top-k attention via total variation | adopt_patterns | PARTIAL | Exact identity: KL of a kept set = -log(1 - discarded mass) |

## Principles checked against MI210 (gfx90a) and EPYC Zen 5

Verdicts: TRANSFERS / TRANSFERS-WITH-CHANGES / DOES-NOT-TRANSFER / ALREADY-PRESENT / UNKNOWN-NEEDS-PROBE.

| Steering item | Principle | MI210 | EPYC | Mechanism (from the dive's code read) |
|---|---|---|---|---|
| 1 PR #32921 | Column-tile-outermost walk for x-band L2 reuse | DOES-NOT-TRANSFER on served shapes (TRANSFERS-WITH-CHANGES if MMQ ever serves more than 64 columns) | ALREADY-PRESENT | np4 verify M=36 picks J=48, one column tile; Q8_0 above 128 columns goes to rocBLAS; iqk keeps x stationary |
| 1 | Compile-time order template vs runtime branch | UNKNOWN-NEEDS-PROBE (moot today) | DOES-NOT-TRANSFER | iqk fixes its split once per thread |
| 1 | Tiles > CUs on 104 CUs | ALREADY-PRESENT (always stream-k at 104 blocks) | n/a | Only 17408-row tensors exceed 104 tiles at M=36, and they have one column tile |
| 2 Shifter Quantization | Shared-bit packing instead of per-group float scales | TRANSFERS-WITH-CHANGES (MFMA-bound paths only; needs per-token activation scales) | ALREADY-PRESENT (Q2_K x Q8_K) | Per-32 scale epilogue at mmq-vec-dot.cuh L197; CPU sums int32 per 256-value super-block |
| 2 | Mapping to v_mfma i8 / VNNI | TRANSFERS, no rate gain (int8 16x16x16 has f16's K); SHI DOES-NOT-TRANSFER (no INT4 MFMA) | TRANSFERS (vpdpbusd), no decode gain (bandwidth-bound) | mma.cuh L1311-L1315 |
| 2 | Coalescing of packed rows | ALREADY-PRESENT (Q8-W8 design 5) | ALREADY-PRESENT | Design 4 lost on scattered loads; design 5's packed layout passed at op level |
| 3 Below the Stopwatch | Claimed mechanism must move its counter, with A/A | TRANSFERS-WITH-CHANGES (rocprof counters) | TRANSFERS-WITH-CHANGES (memory-traffic counters) | ak_row_lint checks only knob effect |
| 3 | Instruction count is a weak signal; prefer transaction counters | TRANSFERS | TRANSFERS-WITH-CHANGES | Mirrors Q8-W8 design 4 |
| 4 TACPU | L1/L2/L3 tile sizing | DOES-NOT-TRANSFER | TRANSFERS-WITH-CHANGES (1 MB L2, 32 MB L3 per CCD, not one shared L3) | Our CPU FA has no L2/L3 blocking |
| 4 | Dispatcher vs static split under NPS4 | n/a | UNKNOWN-NEEDS-PROBE (paper tested SNC-2 only); longest-first order TRANSFERS-WITH-CHANGES | Our chunking is dynamic but cheapest-first |
| 4 | AMX GEMM with AVX-512 softmax overlap | DOES-NOT-TRANSFER | DOES-NOT-TRANSFER | No AMX on Zen 5 |
| 5 Roofline AI estimation | ISA/compiler-artifact prompting | DOES-NOT-TRANSFER for the census | n/a | The census measures counters and ranks by time share |
| 5 | Cache-dependent traffic as main error source | UNKNOWN-NEEDS-PROBE | UNKNOWN-NEEDS-PROBE | Motivates a deterministic bytes plausibility check |
| 6 MXFP4 PTQ | Midmax / Overflow-Aware scale rule | TRANSFERS (quantizer only) | TRANSFERS (quantizer only) | Our rule is plain floor (ggml-quants.c L368); only served MXFP4 model is a lossless repack |
| 6 | Hadamard rotation granularity | UNKNOWN-NEEDS-PROBE | UNKNOWN-NEEDS-PROBE | Needs online activation rotation |
| 6 | INT8/FP16 emulation of FP4 | ALREADY-PRESENT (dequant path) | ALREADY-PRESENT | Neither device has FP4 |
| 7 PR #32867 | DPP row_shr/row_bcast wave64 scan | TRANSFERS-WITH-CHANGES, no served consumer (gfx90a takes the row_bcast branch) | DOES-NOT-TRANSFER | One caller (cumsum.cu); fused GDN skips CUMSUM |
| 7 | DPP warp_reduce_sum | ALREADY-PRESENT in default-off GDN variants | DOES-NOT-TRANSFER | Stock GDN still uses shfl_xor |
| 8 Pando | Parallel-drafter tree vs chain | ALREADY-PRESENT | DOES-NOT-TRANSFER (MoE CPU lineup breaks the shared-weight-stream assumption) | Our DTREE path exists; C21 row 1.030x at T1.0 |
| 8 | Noise coupling | DOES-NOT-TRANSFER | DOES-NOT-TRANSFER | Not lossless with recursive-rejection verify; DICE V3 NULL |
| 8 | Node budget vs ridge point | DOES-NOT-TRANSFER as a predictor | TRANSFERS-WITH-CHANGES | Measured per-row verify cost (a step at 12 rows) dominates on MI210 |
| 9 Draft calibration | Draft temperature scaling | DOES-NOT-TRANSFER (measured about zero) | no-op at greedy | SPEC-DRAFT-SHARPEN CLOSE |
| 10 LEGOSpec | DFlux SWA-hybrid backbone, Residual Corrector | UNKNOWN-NEEDS-PROBE / TRANSFERS-WITH-CHANGES (needs weights) | DOES-NOT-TRANSFER (no CPU DFlash2 drafter) | No released checkpoint |
| 11 GramDelta | Delta-Earley mask updates | DOES-NOT-TRANSFER to current traffic | same | Grammars are built once per request |
| 12 Date | Pin and log the system-prompt date | TRANSFERS | TRANSFERS | llama-server injects the wall-clock date_string |
| 13 RECAP | Summary-vs-full next-action KL grader | TRANSFERS | TRANSFERS | Needs logprobs of one model on both contexts |
| 14 Effort training | Effort tiers by OPD or KL-anchored RL | needs training | needs training | No prompt-only arm in the paper |
| 15 Top-K limits | Joint support quality; dense-reference KL | TRANSFERS-WITH-CHANGES (diagnostic) | TRANSFERS-WITH-CHANGES | Our indexer is learned and exact; eviction screen pending |
| 15 (wave 2) | Tail-mass KL identity as a gate | TRANSFERS-WITH-CHANGES (offline gate) | TRANSFERS-WITH-CHANGES | Cannot certify a future query |

## Work packets

| Packet | Project decision | Boxes | Owner | Depends on |
|---|---|---|---|---|
| P1 | Are the stream-k census and the verify-kernel roofline census trustworthy and complete before kernel work is ranked from them? | AK-MMQ-SK2-CENSUS, VKRC-BYTES-PLAUSIBLE | `autokernel-loop.md`, `rocm-kernel-authoring.md` (AutoKernel) | none |
| P2 | Does a keep in an AutoKernel row require that the claimed mechanism was seen in a counter? | AK-MECH-WITNESS-1 | `autokernel-loop.md` (AutoKernel; root-repo lint code) | none |
| P3 | Is there enough tree headroom on 27B DFlash2 to keep investing in draft trees, and is a Pando-style tree shape worth a GPU row? | DTREE-HEADROOM-REPLAY | `speculative-decoding.md` (INF-50 owner) | none |
| P4 | Is the system-prompt date a recorded, pinnable eval input, so no template brings back a wall-clock variable unnoticed? | EV-DATE-PIN-1 | `eval-tower-program.md` (eval tower; orchestrator code) | none |

| Packet | Disposition | Covers |
|---|---|---|
| K1 | knowledge-only | kernel and quantization principles that do not transfer or are already present (notes in `autokernel-loop.md` and `quantization-and-low-bit.md`) |
| K2 | knowledge-only | speculative-decoding findings already answered in-house (note in `speculative-decoding.md`) |
| K3 | knowledge-only | methodology context kept on the intake entries only (no handoff note) |
| M1 | monitor | kernel, quantization and CPU-prefill triggers (prose in `rocm-kernel-authoring.md`, `quantization-and-low-bit.md`, `cpu-decode-roofline-program.md`) |
| M2 | monitor | speculative-decoding and grammar triggers (prose in `speculative-decoding.md`) |
| M3 | monitor | eval, compaction and attention-selection triggers (prose in `autokernel-loop.md`, `context-and-token-economy.md`, `autokernel-akx-program.md`, `long-context-program.md`) |

**Why four packets:** after compression the ledger has four independent units that can change a decision now: census correctness (P1), the keep gate's mechanism witness (P2), the 27B tree headroom decision (P3) and date provenance in evals (P4). Every other row is a no-op on our hardware, already measured in-house, or waits for a precondition that does not hold today (K and M rows below). The compaction-distortion grader and the eviction KL metric were considered for immediate boxes and moved to M3: their host measurements (TOC-CMP-4, EA-POOL-SCREEN) have not produced a result to validate against, so a box now would build an unvalidated metric.

**Concurrency:** all four packets are independent and can run in parallel. P1's two boxes touch different repos and owners. Only P3 uses compute (one CPU quarter, no GPU, no server).

### Minimum rigor

- **P3 DTREE-HEADROOM-REPLAY (empirical replay, all six controls):**
  - Frozen input: capture `cap-L01.jsonl` SHA-256 82d46a61a6d8f8b8088faece7935c5b8c10fd71c43bf3afa6db7941820d3a845 and its manifest; replay code at a pinned research commit; predeclaration sealed by hash before the replay.
  - Current baseline: served chain V0 (must reproduce realized acceptance within 2%, as SPEC-DRAFT-SHARPEN's V0 did) and the current tree builder.
  - Per-item raw outputs: per round tokens-per-pass for each arm, retained in RESULT.json.
  - Holdout: fit prompts 0-31, holdout 32-63 (the SPEC-DRAFT-SHARPEN split); thresholds chosen before any replay.
  - Complete denominator: all 7,499 captured rounds, capped rounds included and reported separately.
  - Predeclared rule: CLOSE_TREE_SHAPE / FILE_GPU_ROW / INCONCLUSIVE thresholds as in the done-when.
  - Measurement sufficiency: question = is there tree headroom worth a GPU row on 27B? Expected effect: the C21 tree row measured 1.030x at T1.0 and NULL at T0.3, so a useful new shape must clear 1.03 on holdout. Error: prompt-clustered bootstrap CI; stop-on-answer at half-width <= 1%. Stop-on-futility: V0 check fails. Evidence reused first: the existing capture; no new capture.
- **P1, P2, P4 (deterministic code and a reading task):** no holdout or baseline applies, because nothing is fitted or compared. Replacement checks:
  - AK-MMQ-SK2-CENSUS: every shape row cites the C21 code line its tile count rests on (provenance); complete denominator = every shape family named in AK-MMQ-SK2 step 2.
  - VKRC-BYTES-PLAUSIBLE: unit test with an over-peak row, an off-footprint row and a plausible row on the retained `verify_roofline.RESULT.json` fixture; flags are fields, rows are never dropped (complete denominator).
  - AK-MECH-WITNESS-1: three-case lint test (missing witness, missing counter, compliant); warn-only, so no keep decision changes.
  - EV-DATE-PIN-1: two-case provenance test (date-reading, date-free) plus the full served-role plan rows (complete denominator).

### Consumer discovery

Search terms: stream-k, MMQ, census_extract, FETCH_SIZE, NO-WITNESS, mechanism_prediction, KEEP_CANDIDATE, dice_replay, dice.v1, tree, date_string, strftime_now, chat_template_kwargs, template_provenance, compaction, distortion, EA-POOL, INDEXER-TOPK. Surfaces: `handoffs/active/*.md` (lane f19b902), root `scripts/coordination/rowflow/`, epyc-orchestrator `scripts/validate/`, `src/graph/`, epyc-inference-research `scripts/kernel_rnd/`, C21 llama.cpp tree.

| Primitive | Direct consumers | Evidence consumers | Policy / prospective consumers |
|---|---|---|---|
| Bytes plausibility check (P1) | census_extract.py extract_verify_roofline | VERIFY-KERNEL-ROOFLINE-CENSUS-1 r2 report | AutoKernel census planner (prospective) |
| Mechanism witness lint (P2) | ak_row_lint.py, AK row specs | RESULT.json counter fields | keep-gate enforcement (prospective, M3 trigger) |
| Tree headroom replay (P3) | dice_replay tooling | speculative-decoding.md tree decision | a GPU tree row (prospective, only on FILE_GPU_ROW) |
| template_reads_date (P4) | template_provenance.py, apply_registry_integrity_pins.py | registry plan rows | eval and judge request kwargs (prospective, when a flagged template is served) |

## Proposed handoff edits (Stage 4 only, after approval)

Five new boxes, each written with `handoff_box.py add ... --brief --brief-author intake`, landing at the bottom of its track's `### Backlog` (EV-DATE-PIN-1's track has none, so the tool creates it). The text below is the exact dry-run output of `handoff_box.py add --dry-run`. No existing box is edited, refined or ticked. No new handoff, so no index row.

#### AK-MMQ-SK2-CENSUS (P1) -> `handoffs/active/autokernel-loop.md`, track `autokernel-research-loop`

```text
- [ ] **AK-MMQ-SK2-CENSUS** [non-inference] Finish the AK-MMQ-SK2 step-2 served-shape census, the one item that keeps that box open: take the dense Qwen3.8-27B Q8_0 tile table already worked out in research/deep-dives/intake-kspec-1125/dive-K1-streamk-order.md (np4 verify M=36 picks J=48 so one column tile per tensor; Q8_0 above 128 columns is routed to rocBLAS by mmq.cu L346-L362 @ 98ff8a4), add the A3B Q8_0 MUL_MAT_ID shapes above the MMVQ cap and the Q4_K/Q6_K 5-128-row shapes from the C21 code, and record per shape the tile count against the 104 stream-k blocks, where force-tiling fires and where the grid cap changes the grid; zero compute (intake-2956, intake-2971)
      · done when: a census table covering the dense 27B, A3B MUL_MAT_ID and Q4_K/Q6_K shape families, with the C21 code lines it rests on, is filed under AK-MMQ-SK2 in handoffs/active/autokernel-loop.md
      · gate: none        · inputs: `handoffs/active/autokernel-loop.md` `research/deep-dives/intake-kspec-1125/dive-K1-streamk-order.md`
```

Brief: where `epyc-root:handoffs/active/autokernel-loop.md`, `epyc-root:research/deep-dives/intake-kspec-1125/dive-K1-streamk-order.md`. Approach: Read-only. Reuse the dive's dense-27B arithmetic as is. For the other two families read the C21 tree (/mnt/raid0/llm/llama-worktrees/c21-20261124 @ 98ff8a4): mmq.cu routing (MMVQ cap, rocBLAS cutover), mmq.cuh stream-k launcher (104 blocks, tile counts) and the CDNA mmq config tables, and count tiles from the tensor shapes named in AK-MMQ-SK2 step 2. File one table under the box; tick nothing (the owner ticks AK-MMQ-SK2). Acceptance: the done-when (accepted: auto). Non-goal: No GPU run and no new port; the row verdict is already CLOSE..

#### VKRC-BYTES-PLAUSIBLE (P1) -> `handoffs/active/rocm-kernel-authoring.md`, track `rocm-verify-profile-backend`

```text
- [ ] **VKRC-BYTES-PLAUSIBLE** [non-inference] Add a deterministic bytes plausibility check to the verify-kernel roofline census extraction (epyc-inference-research scripts/kernel_rnd/autokernel/loop/census_extract.py extract_verify_roofline @ 4ca0d0d9a) before VERIFY-KERNEL-ROOFLINE-CENSUS-1 r2 is read: flag every kernel row whose FETCH_SIZE+WRITE_SIZE-derived GB/s exceeds the HBM peak the census uses, or whose bytes per call differ from the analytic footprint (weight or tensor bytes x launches) by more than 2x, and print the flagged rows beside the ranking; no LLM estimate (intake-2960: LLM device-memory traffic estimates are the weak half, within 1.20x in 36-40% of cases)
      · done when: a pytest under epyc-inference-research scripts/kernel_rnd/autokernel/loop/ passes on origin/main and covers an over-peak row (flagged), a row with bytes 3x the analytic footprint (flagged) and a plausible row (not flagged), using the existing testdata/census/verify_roofline.RESULT.json fixture
      · gate: none        · inputs: `handoffs/active/rocm-kernel-authoring.md`
```

Brief: where `epyc-inference-research:scripts/kernel_rnd/autokernel/loop/census_extract.py::extract_verify_roofline`, `epyc-inference-research:scripts/kernel_rnd/autokernel/loop/testdata/census/verify_roofline.RESULT.json`. Approach: Add a pure function plausibility(rows, peak_gbps, footprint) that returns flags; call it from extract_verify_roofline after bytes are pooled. Analytic footprint: for GEMV/GEMM kernels, weight bytes from the model's tensor shapes x calls per step; other kernels get only the peak check. Flags are report fields, never a filter: every row stays in the table. Acceptance: pytest scripts/kernel_rnd/autokernel/loop -k plausib. Non-goal: No LLM or ISA-based estimator; no change to the census ranking rule..

#### AK-MECH-WITNESS-1 (P2) -> `handoffs/active/autokernel-loop.md`, track `autokernel-research-loop`

```text
- [ ] **AK-MECH-WITNESS-1** [non-inference] Add a warn-first claimed-mechanism witness to AutoKernel rows: a row spec whose decision rule can return a keep or pass on a speed claim declares mechanism_witness {counter, direction, aa_band} (the per-row form of mechanism_prediction.expected_counter_changes, autokernel-loop.md L1605-L1608), and ak_row_lint.py warns MECH-UNWITNESSED when the field is missing or the row's RESULT does not record that counter for both arms; today NO-WITNESS (ak_row_lint.py L39, L680-L682) checks only that a named knob took effect, and Q8-W8 design 4 cut static instructions per byte 3x yet ran 2-3x slower, a cause found only after the fact (intake-2958, intake-2977, intake-2979)
      · done when: pytest scripts/coordination/tests/test_ak_row_lint_mech_witness.py passes on origin/main and covers a speed-claim row with no witness (WARN), a row whose RESULT lacks the declared counter (WARN) and a compliant row (no WARN)
      · gate: none        · inputs: `scripts/coordination/rowflow/ak_row_lint.py` `handoffs/active/autokernel-loop.md`
```

Brief: where `epyc-root:scripts/coordination/rowflow/ak_row_lint.py`, `epyc-root:handoffs/active/autokernel-loop.md`. Approach: Mirror the NO-WITNESS rule: detect a speed claim from decision_rule keywords (KEEP_CANDIDATE, GATE_PASS, speedup, x >=) and require spec.mechanism_witness with counter, direction (up/down) and aa_band. Check the row code or RESULT schema for the counter key. WARN only; enforcement (downgrading a keep to INCONCLUSIVE) is a later decision once the would-fail count over new rows is known. Acceptance: pytest scripts/coordination/tests/test_ak_row_lint_mech_witness.py. Non-goal: No change to keep decisions or verdict strings in this box.. New test: `scripts/coordination/tests/test_ak_row_lint_mech_witness.py`.

#### DTREE-HEADROOM-REPLAY (P3) -> `handoffs/active/speculative-decoding.md`, track `dflash2-block-drafter-experimental-build`

```text
- [ ] **DTREE-HEADROOM-REPLAY** [inference] Measure how much tree headroom is left on 27B DFlash2 by offline CPU replay of the retained dice.v1 capture ak-dice-capture-27b-dflash2-gpu-20261123-r2 (cap-L01.jsonl SHA-256 82d46a61a6d8f8b8088faece7935c5b8c10fd71c43bf3afa6db7941820d3a845): (a) the speed-of-light ceiling on tokens per verify pass from the captured target distributions at verifier budgets 8, 12 and 16 (intake-2973 bound; stochastic targets only, so T0.3 and T1.0), and (b) a Pando-style best-first tree (k children per level, pruned to N nodes by cumulative draft probability, intake-2963) under the V1 recursive-rejection tree verify, against served chain V0 and the current builder, same fit 0-31 / holdout 32-63 split as SPEC-DRAFT-SHARPEN. Model: Qwen3.8-27B Q8_0 + DFlash2 capture (no model load); tool: research scripts/kernel_rnd/dice_replay/ (V0 check must reproduce realized acceptance within 2%); region: one CPU quarter; est 3600 s (provisional); metric: holdout tokens per pass ratio to V0 with prompt-clustered 95% CI. Stop-on-answer at CI half-width <= 1%; stop-on-futility if the V0 check fails.
      · done when: a RESULT.json filed under this box gives the ceiling and the Pando-tree and current-builder holdout ratios to V0 per T and N with CIs, and the verdict: CLOSE_TREE_SHAPE (ceiling over V0 < 1.10 at N=16 at both T, or Pando-tree ratio CI-upper < 1.02 at both T), FILE_GPU_ROW (Pando-tree ratio >= 1.03 with CI-lower > 1.0 at some T), or INCONCLUSIVE
      · gate: none        · inputs: `handoffs/active/speculative-decoding.md`
```

Brief: where `epyc-root:handoffs/active/speculative-decoding.md`, `epyc-inference-research:scripts/kernel_rnd/dice_replay/dice_replay_27b.py`. Approach: Reuse dice_replay_27b.py (and draft_sharpen_replay.py for the fit/holdout harness) and its V0/V1 verifiers unchanged; add two arms: a ceiling arm computing the branching-random-walk bound from each round's captured target top-k distribution, and a Pando tree builder over the captured draft lattice. Seal the predeclaration (thresholds above) before replay, as SPEC-DRAFT-SHARPEN did. CPU only, no GPU and no server. Acceptance: the done-when (accepted: auto). Non-goal: No noise coupling (lossless only with a target-sample walk, not our rejection verifier); no GPU row in this box..

#### EV-DATE-PIN-1 (P4) -> `handoffs/active/eval-tower-program.md`, track `prompt-construction-determinism`

```text
- [ ] **EV-DATE-PIN-1** [non-inference] Make the system-prompt date a recorded, pinnable eval input: template_provenance.py (epyc-orchestrator scripts/validate/template_provenance.py @ faa783c7) records template_reads_date true when the effective template references strftime_now, date_string or a datetime value, and registry validation warns on any served or eval role whose template reads the date without a pinned date_string in its request kwargs; llama-server fills date_string from the wall clock (common/chat.cpp L2573-L2581 @ 98ff8a4) and a request can override it through chat_template_kwargs (L2747-L2750), and two plausible dates flip a median 6.6% of items with none of 11 eval stacks pinning it (intake-2967, intake-2972)
      · done when: pytest tests/unit/test_template_provenance_bytes.py in epyc-orchestrator passes on its main and covers a date-reading template (template_reads_date true) and a date-free template (false), and the template plan rows for every served role in the registry carry template_reads_date
      · gate: none        · inputs: `handoffs/active/eval-tower-program.md`
```

Brief: where `epyc-orchestrator:scripts/validate/template_provenance.py`, `epyc-orchestrator:tests/unit/test_template_provenance_bytes.py`. Approach: Scan the effective template bytes that build_row already hashes for the three tokens; emit the boolean in the plan row so apply_registry_integrity_pins.py carries it. The warning lives in the registry validator. Today's served templates read no date (dive M1 checked the pinned 27B/A3B, Q38FN, deepseek-v41 and Gemma templates), so the expected first result is all false; the guard stops a future template from reintroducing a wall-clock variable silently. Acceptance: pytest tests/unit/test_template_provenance_bytes.py. Non-goal: No eval rerun; no change to served templates..

### Knowledge notes and trigger prose (dated, no checkbox)

- **`handoffs/active/autokernel-loop.md`**, after the AK-MMQ-SK2 *Knowledge (intake-ak-1123 K2, no checkbox)* line:

```text
  - *Knowledge (intake-kspec-1125 K1, no checkbox):* PR #32921's column-tile-outermost stream-k walk (intake-2956) is a no-op on served gfx90a shapes: np4 verify M=36 picks J=48, so each tensor has one column tile and the new order equals the old; Q8_0 above 128 columns goes to rocBLAS (mmq.cu L346-L362 @ 98ff8a4); its J == 128 gate cannot fire on CDNA. G17's WGM remap moved the other way (more weight bands live at once), so its negative does not predict this lever. On EPYC, iqk already sweeps all activation columns per 64-row weight step. The HIP DPP scan of PR #32867 (intake-2962#00) has no served consumer: its one caller is CUMSUM, which the fused GDN ops do not emit.
```

- **`handoffs/active/quantization-and-low-bit.md`**, after the QUANT-ROT-1 box block:

```text
  - *Knowledge (intake-kspec-1125 K1, no checkbox):* Shifter Quantization (intake-2957) gives an exact full-K integer dot with no per-group float scale, but on gfx90a int8 MFMA has the same K per instruction as f16, so it brings no rate gain there; SHI needs INT4 MFMA, which CDNA2 lacks; CPU Q2_K x Q8_K dots already use SHI-style integer correction products. Overflow-Aware Scaling (intake-2978) rounds the E8M0 scale up when the floor-scaled block max exceeds 7, the same threshold the PDF-only intake-2961 calls Midmax (unverified there), so cite one rule, not two confirmations; intake-2978's gains are W4A4 and are not weight-only evidence.
```

- **`handoffs/active/speculative-decoding.md`**, after the SPEC-DRAFT-SHARPEN box block:

```text
  - *Knowledge (intake-kspec-1125 K2, no checkbox):* (1) Draft temperature scaling (intake-2964) is lossless under rejection verify and a no-op at greedy; this box's CLOSE is the in-house answer, so the paper's gain is not carried to our stack. (2) SPEC-DISTS-TRUNC resizes the draft distributions to the capped draft length (common/speculative.cpp L3155-L3163 @ 98ff8a4); vocabulary truncation is this box's trunc arm. (3) Noise-coupled tree pruning (intake-2963) is lossless only with a target-sample walk, not with our recursive-rejection tree verify, and SPEC-DTREE-DICE V3 already measured draw-informed selection as NULL. (4) At more than one stream, keep tree budgets load-adaptive so they shrink to the chain (intake-2974, intake-2975). (5) DFlux (intake-2965) gains are confounded by training scale; its recipe options are inputs to DF2-FT-1, not a plan. (6) GramDelta (intake-2966) helps only mid-request grammar growth, which no served role does; it does not bear on SPEC-GRAM-JSON-1 or the llguidance default flip.
```

- **M1, `handoffs/active/rocm-kernel-authoring.md`**, after the VERIFY-KERNEL-ROOFLINE-CENSUS-1 result note:

```text
  - *Trigger (intake-kspec-1125 M1, no checkbox):* (a) if Q8_0 dense prefill is ever routed to MMQ on gfx90a, port PR #32921's column-outer order behind a CDNA J=64 gate as the first lever, judged on wall clock, not on L2 hit rate (intake-2956); (b) when a counter row next profiles MMQ Q8_0 at 9-128 columns on CDNA2, record the VALU share of the per-32 scale epilogue (mmq-vec-dot.cuh L197 @ 98ff8a4) against MFMA busy (intake-2957); (c) if this census shows the stock GDN recurrent kernel's reductions at 3% of the step or more, screen PR #32867's DPP warp_reduce_sum there, and if backend sampling is turned on for a GPU role, time CUMSUM over the vocabulary on gfx90a first (intake-2962#00).
```

- **M1, `handoffs/active/quantization-and-low-bit.md`**, after the K1 note under QUANT-ROT-1:

```text
  - *Trigger (intake-kspec-1125 M1, no checkbox):* (a) when QUANT-ROT-1 is booked, add an arm comparing per-output-channel INT8 after a signed H512 rotation (the SQ8 recipe, intake-2957) with Q8_0's per-32 scales on real 27B rows; the byte saving is at most 8.0 against 8.5 bits per weight. (b) When a BF16-to-MXFP4 requant is queued, try the round-up E8M0 rule against our floor rule (ggml-quants.c L368 @ 98ff8a4), judged by KLD (intake-2961, intake-2978).
```

- **M1, `handoffs/active/cpu-decode-roofline-program.md`**, after the XFER-4b box block:

```text
  - *Trigger (intake-kspec-1125 M1, no checkbox):* if a CPU-served role takes prompts of 32K tokens or more, first measure the flash-attention share of prefill there; if it is material, run the flash-attention chunks longest-first (our chunking is dynamic but cheapest-first) and then consider TACPU's L2 query-group inversion sized for Zen 5's 1 MB L2 and 32 MB per-CCD L3 (intake-2959). Its AMX GEMM and AVX-512 softmax overlap has no Zen 5 counterpart.
```

- **M2, `handoffs/active/speculative-decoding.md`**, after the K2 note under SPEC-DRAFT-SHARPEN:

```text
  - *Trigger (intake-kspec-1125 M2, no checkbox):* (a) if a UBTree Qwen3.8-27B selector (intake-2974) or a DFlux checkpoint for a served target (intake-2965) is released, run one paired acceptance probe against DFlash2 at served T; (b) when DTREE-GDN-BATCH makes a 16-node tree beat the chain, attach TreeSpark's two-scalar edge calibration and load-adaptive shrink to its reopen criteria (intake-2975); (c) if a role starts growing its grammar inside one request (progressive tool or schema discovery), price per-update llguidance matcher rebuilds against our turn count (intake-2966).
```

- **M3, `handoffs/active/autokernel-loop.md`**, directly under the new AK-MECH-WITNESS-1 box:

```text
  - *Trigger (intake-kspec-1125 M3, no checkbox):* once AK-MECH-WITNESS-1 lands, scan the stored keep and drop rows for a stated mechanism and the counter that would have tested it, before any decision to enforce the witness (intake-2958).
```

- **M3, `handoffs/active/context-and-token-economy.md`**, after the TOC-CMP-4 box block:

```text
  - *Trigger (intake-kspec-1125 M3, no checkbox):* when TOC-CMP-4 or the CF-3c A/B files its first complete paired result, add RECAP's behavior-distortion score (intake-2968: sampled-token KL of the next actions under the summary versus the full context, same model, no training) as a secondary metric and check whether it ranks the arms in the same order; adopt it as a cheaper instrument only if it does.
```

- **M3, `handoffs/active/context-and-token-economy.md`**, after the E-2 box block:

```text
  - *Trigger (intake-kspec-1125 M3, no checkbox):* when E-2 is booked, add the three effort instruction texts printed in intake-2969 and Qwen3.8's native low/medium/xhigh as rungs, and include agentic items, where the paper's trained tiers collapsed; the paper has no prompt-only arm, so expect little.
```

- **M3, `handoffs/active/autokernel-akx-program.md`**, after the Q38FN-INDEXER-TOPK-EXACT box block:

```text
    - *Trigger (intake-kspec-1125 M3, no checkbox):* if an approximate indexer top-k is proposed again, gate it on teacher-forced KL against the exact set and the discarded main-attention mass of the dropped blocks (intake-2981: the KL of a kept set is -log(1 - discarded mass)) beside greedy identity; joint support, not per-key rank, decides the loss (intake-2970).
```

- **M3, `handoffs/active/long-context-program.md`**, after the EA-POOL-SCREEN box block:

```text
  - *Trigger (intake-kspec-1125 M3, no checkbox):* if EA-POOL-SCREEN leaves two or more arms within 3 items of FULL, rank them by teacher-forced KL against FULL over the reference answers (intake-2970) and log the discarded attention mass per kept set (intake-2981) before choosing.
```

## Monitors and knowledge-only (durable prose, no checkbox)

- **K1** (knowledge-only): kernel and quantization principles that are no-ops or already present on gfx90a and Zen 5. Covered by the two K1 notes above.
- **K2** (knowledge-only): speculative-decoding findings already answered in-house. Covered by the K2 note above.
- **K3** (knowledge-only): methodology context recorded on the intake entries only (intake-2977 re-execution, intake-2972 corroboration, intake-2979 reporting statistics, SwapCert's cost, the value-mean-gap screen).
- **M1, M2, M3** (monitor): every trigger is owned prose under the box whose next event fires it, with no checkbox and no index next action.

## Operator decisions

- None open. Two later choices are named but not yet due: whether to enforce the mechanism witness (after the M3 backfill scan gives a would-fail count), and whether to book a GPU tree row (only if DTREE-HEADROOM-REPLAY returns FILE_GPU_ROW). No operator-decision box or index row is filed now.

## Index rows

None. No new handoff is created, and `index_state.py` regenerates the thin rows from the new boxes.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| KS-K1-1 | intake-2956 dive K1 (tiles vs 104 blocks and ntx decide stream-k regime) | File the dense 27B tile census (tiles and ntx per tensor at M=36 and hypothetical ub256/512, plus routing) under AK-MMQ-SK2 step 2 to close its remaining gap | P1 / AK-MMQ-SK2-CENSUS |
| KS-K1-2 | intake-2956 dive K1 (column-outer reuse needs >=2 column tiles per row band) | Record that PR #32921 is a no-op on served gfx90a MMQ (ntx=1 at M=36, Q8_0 n>128 on rocBLAS, J==128 absent on CDNA) | K1 knowledge-only: the PR's order is a no-op on served gfx90a shapes (one column tile at M=36, wide Q8_0 on rocBLAS, J=128 absent on CDNA) |
| KS-K1-3 | intake-2956 dive K1 (tile-walk order for L2 reuse of x row bands) | If Q8_0 dense prefill ever routes to MMQ on gfx90a, port the column-outer order with a CDNA J=64 gate as the first cheap lever, wall-clock vetoed | M1 monitor: port the order only if Q8_0 dense prefill is ever routed to MMQ on gfx90a |
| KS-K1-4 | intake-2971 dive K1 (tile-walk order for x row reuse) | Note that iqk prefill on EPYC is already x-stationary (per-thread row band, 64-row steps over all Ny); the npt<=16 Ny-split branch reads small-tensor x bands from two possibly cross-NUMA threads | K1 knowledge-only: iqk on EPYC already sweeps all activation columns per 64-row weight step |
| KS-K2-1 | intake-2957 dive K2 (shared-bit/per-channel packing vs per-group float scales) | we should add an offline arm to QUANT-ROT-1 comparing per-output-channel INT8 after signed H512 (SQ8 recipe) against Q8_0 per-32 FP16 scales on real 27B rows (weight/output error, dKLD if cheap), no kernel | M1 monitor: add the per-channel INT8 plus H512 arm when the activation-rotation probe is booked |
| KS-K2-2 | intake-2957 dive K2 (mapping to v_mfma i8; per-block scale inside K loop) | we could record the VALU epilogue share (C.x*dA*dB, mmq-vec-dot.cuh:L197) vs MFMA busy when a counter row next profiles MMQ Q8_0 at ne11 9-128 on CDNA2 | M1 monitor: record the scale-epilogue VALU share when a counter row next profiles MMQ at 9-128 columns |
| KS-K2-3 | intake-2957 dive K2 (mapping to v_mfma i8 and VNNI) | record that on gfx90a int8 MFMA (16x16x16i8) has the same per-instruction K as f16 MFMA, so an SQ8-style prefill gain is limited to removing the dequant-to-f16 pass and halving operand bytes | K1 knowledge-only: gfx90a int8 MFMA has the same K per instruction as f16, so no rate gain |
| KS-K2-4 | intake-2957 dive K2 (INT4 products; bandwidth-bound decode) | record that SHI does not transfer to MI210 (no INT4 MFMA), CPU K-quant dots already use SHI-style integer correction products, and SQ2/SQ4 matter only if EXL3-X0b reopens | K1 knowledge-only: SHI needs INT4 MFMA (absent on CDNA2); CPU K-quant dots already use integer correction products |
| KS-K3-1 | intake-2962 dive K3 (DPP row_shr + row_bcast wave64 scan) | Record that warp_prefix_inclusive_sum has one caller and CUMSUM is absent from served fused-GDN graphs; do not port the scan | K1 knowledge-only: the DPP scan's one caller is CUMSUM, which the served fused GDN graphs do not emit |
| KS-K3-2 | intake-2962 dive K3 (DPP-based warp_reduce_sum) | Op-level screen of the PR DPP warp_reduce_sum (incl. lane0-only tail) in the stock GDN recurrent kernel at GDN-VERIFY-BASE shapes; stop-on-futility if reduction share under 3 percent or gain under A/A p95 | M1 monitor: screen the DPP warp reduction only if the census shows GDN reductions at 3 percent or more of the step |
| KS-K3-5 | intake-2962 dive K3 (DPP row_shr + row_bcast wave64 scan) | Check whether backend sampling is enabled on any served GPU role; if so run one CUMSUM [vocab,1] op on gfx90a before judging the PR | M1 monitor: time CUMSUM over the vocabulary on gfx90a only if backend sampling is turned on for a GPU role |
| KS-K3-3 | intake-2960 dive K3 (Cache-dependent traffic is the dominant estimate error) | Add a deterministic plausibility check to census post-processing: flag kernel rows whose FETCH_SIZE+WRITE_SIZE-derived GB/s exceeds the measured 1.498 TB/s peak or whose bytes differ from the analytic footprint (tensor bytes x launches) by more than 2x; no LLM | P1 / VKRC-BYTES-PLAUSIBLE |
| KS-K3-4 | intake-2960 dive K3 (ISA + instruction-mix prompting for static AI estimates) | Do not build an LLM/ISA roofline pre-ranker for the census; if the AutoKernel planner wants a prior, use analytic bytes and measured time shares and gate any LLM prior on five-run agreement | decline: the census ranks by measured time share and fraction of peak; an LLM traffic estimate is weakest exactly on the cache-dependent kernels the census targets |
| KS-K4-2 | intake-2959 dive K4 (L3/L2 blocking) | measure prefill attention share at 32K-128K on C21 before any port | M1 monitor: measure the flash-attention share of CPU prefill only once a CPU-served role takes prompts of 32K tokens or more |
| KS-K4-3 | intake-2959 dive K4 (LPT dispatcher, L2 q-group) | reverse FA chunk order (expensive late rows first), then consider q-group loop inversion with 1 MB L2 sizing | M1 monitor: reverse the flash-attention chunk order, then consider query-group inversion, gated on that measurement |
| KS-K4-1 | intake-2961 dive K4 (Midmax scale rule) | prototype Midmax in an experimental quantize_row_mxfp4_ref and KLD A/B vs floor when an MXFP4 requant is queued | M1 monitor: try the round-up E8M0 rule against floor, judged by KLD, when a BF16-to-MXFP4 requant is queued |
| KS-S1-1 | intake-2963 dive S1 (parallel-drafter tree vs chain) | We could replay a Pando-style full best-first tree (k-expansion per level, prune to N by cumulative lattice prob) against the current sibling-of-main builder on the existing 27B DFlash2 capture at T 0.3/1.0 and W 8/12/16 with V1 RRS verify | P3 / DTREE-HEADROOM-REPLAY |
| KS-S1-3 | intake-2963 dive S1 (noise coupling) | We should record that noise-coupled or draw-informed tree shapes are lossless only with the target-sample walk; with RRS the tree must be blind to the verifier randomness | K2 knowledge-only: noise-coupled tree shapes are lossless only with a target-sample walk, not with our rejection tree verify |
| KS-S1-4 | intake-2963 dive S1 (noise coupling) | We should not build noise coupling on DFlash2 or MTP trees | decline: noise coupling is not lossless under our recursive-rejection verifier, and the draw-informed selection replay already returned NULL on both lineup models |
| KS-S1-2 | intake-2973 dive S1 (node budget vs ridge point) | We could compute the x03 bound (mu, mu2 -> E[X] at P 8/12/16) per served T from the DICE capture target top-64 logits and compare it with measured tau | P3 / DTREE-HEADROOM-REPLAY |
| KS-S1-5 | intake-2974 dive S1 (tree verify cost on hybrid GDN models) | We could check whether the UBTree Qwen3.8-27B selector or checkpoint is released and whether it drops into our DFlash2 lattice path (same low-rank bigram form, precomputed codebooks) | M2 monitor: probe a UBTree 27B selector only if one is released |
| KS-S1-6 | intake-2974 dive S1 (parallel-drafter tree vs chain) | At np>1 we should keep load-adaptive tree budgets that shrink to the chain, never a fixed large tree | K2 knowledge-only: at more than one stream keep tree budgets load-adaptive, shrinking to the chain |
| KS-S2-1 | intake-2964 dive S2 (draft T_d != T_t is lossless but its gain depends on the target sampler regime) | cite SPEC-DRAFT-SHARPEN as the in-house answer for intake-2964; do not re-run a 27B DFlash2 draft-temperature sweep | K2 knowledge-only: our own offline draft-sharpening replay already closed draft temperature on 27B DFlash2 |
| KS-S2-2 | intake-2964 dive S2 (a lever with an offline replay path is measured before it is built) | run an offline CPU replay of A3B MTP draft softening/sharpening from the mtp_top top-10 logits in the A3B dice.v1 capture; stop on futility if best-T_d gain CI-upper < 1.02; only on a keep build a served MTP q in C21 | decline: MTP verifies by sample-and-compare and its captured top-1 probability is about 0.997 or higher per depth, so softening has almost nothing to gain and would need a new served MTP distribution |
| KS-S2-3 | intake-2964 dive S2 (name the lever by its mechanism) | record that SPEC-DISTS-TRUNC means dists capped to draft length, and the vocabulary truncation lever is the trunc arm of SPEC-DRAFT-SHARPEN | K2 knowledge-only: record that the dists-truncation fix resizes draft distributions to the capped length; vocabulary truncation is the sharpening replay's trunc arm |
| KS-S2-4 | intake-2975 dive S2 (stop growing the tree when marginal survival falls below the verify price) | attach the edge-acceptance calibration and price-ladder idea to the DTREE-GDN-BATCH reopen criteria | M2 monitor: attach TreeSpark's edge calibration and load-adaptive shrink to the batched-tree reopen criteria when a 16-node tree beats the chain |
| KS-S2-5 | intake-2976 dive S2 (spend drafting compute only where verification will use it) | no action at np<=2; revisit only if we serve DFlash2 at np>=8 or a drafter share above 25% of the round | decline: ForeSpark's gain needs drafting to be a large share of the step at high load; ours is a small share at one or two streams |
| KS-S3-1 | intake-2965 dive S3 (consume-upstream-checkpoints) | Monitor for a released DFlux/LEGOSpec checkpoint matching a served target (Qwen3.8-27B or Qwen3.8-Flash-Next); if one appears, add a DFlash2-vs-DFlux paired acceptance probe at served T on the MI210 under the DF2-CARD-CONFORMANCE-1 recipe. | M2 monitor: run a paired acceptance probe only if a DFlux checkpoint for a served target is released |
| KS-S3-2 | intake-2965 dive S3 (recipe-over-architecture) | Fold the training-recipe findings (hybrid SWA(512)x4+GQA backbone for long context; hierarchical KL(0.2)+D-PAL loss; 1.4M T=1 self-generated samples, Muon) into the DF2-FT-1 design notes as options, not as a plan. | K2 knowledge-only: DFlux recipe options are inputs to the deferred drafter fine-tune, not a plan |
| KS-S3-3 | intake-2965 dive S3 (estimate-port-cost) | Port-cost note for a future DFlux drafter in llama.cpp: C21 already has dflash conv kernel and selector rank/top_k keys (src/models/dflash.cpp:L141-L144 @ 98ff8a4) and per-layer SWA (src/models/dflash-dspark41.cpp:L164-L332 @ 98ff8a4); missing pieces are per-layer window=512 hybrid layout and the R-Corrector (E-/E+ codebooks, top-16 x top-16 table) as a selector variant. | K2 knowledge-only: port-cost note; the C21 tree already has the DFlash conv, selector keys and per-layer SWA |
| KS-S3-4 | intake-2966 dive S3 (static-vs-dynamic-grammar-separation) | No change to SPEC-GRAM-JSON-1 or the INF-83 D2 flip; add a one-line note that GramDelta (intake-2966) addresses mid-request grammar growth only, which no served role does, and its static K=0 table shows no llguidance-vs-XGrammar steady-state difference. | K2 knowledge-only: GramDelta does not bear on the grammar-share measurement or the llguidance default flip |
| KS-S3-5 | intake-2966 dive S3 (trigger-gated-monitor) | Re-open only if a role starts discovering tools or schemas progressively inside one request (BFCL-like growing tool list); then price per-update llguidance matcher rebuild (about 50 ms on their GPU harness) against our turn count. | M2 monitor: price per-update matcher rebuilds only if a role starts growing its grammar inside one request |
| KS-M1-1 | intake-2958 dive M1 (claimed mechanism must move a named counter; instruction count does not discriminate) | we should add a claimed-mechanism witness (counter name, direction, A/A band) to AK row specs and ak_row_lint, downgrading KEEP_CANDIDATE to INCONCLUSIVE when it does not move | P2 / AK-MECH-WITNESS-1 |
| KS-M1-2 | intake-2958 dive M1 (retrospective discrimination check) | we could scan the stored keep and drop rows for stated mechanism versus a counter that would have tested it (zero compute) | M3 monitor: scan stored keep and drop rows for stated mechanism versus counter once the witness lint lands |
| KS-M1-5 | intake-2977 dive M1 (re-execute claims; check behaviour on untested inputs) | no change; our identity and re-measure gates already cover this lesson | K3 knowledge-only: our identity and re-measure gates already cover the merged-not-measured lesson |
| KS-M1-3 | intake-2967 dive M1 (pin and log the date alongside seed and decoding) | we should fail the template review gate and registry validation when a served template reads strftime_now, date_string or datetime without a pinned date_string, and record template_date_dependent in eval provenance | P4 / EV-DATE-PIN-1 |
| KS-M1-4 | intake-2967 dive M1 (check provider-side injection) | we should run a zero-compute probe asking the Claude judge path for today date with an empty system prompt | decline: asking the judge model for today's date cannot show whether a provider injects one; the guard on templates plus recorded request kwargs is the evidence that can |
| KS-M1-6 | intake-2972 dive M1 (pin and log the date) | no extra action beyond KS-M1-perfclaims-date-3 and -4 | K3 knowledge-only: the second date paper corroborates the first and adds no action |
| KS-M2-1 | intake-2968 dive M2 (behavior preservation as compaction grader) | build an offline distortion-score grader (summary-vs-full-context sampled-token KL on the same local Qwen) and validate it against TOC-CMP-4 blocked actions with a no-summary arm | M3 monitor: add the behavior-distortion score as a secondary compaction metric when the compaction A/B files its first complete paired result |
| KS-M2-2 | intake-2969 dive M2 (prompt effort tiers must be certified per model and per format) | add the three printed effort instruction texts and Qwen3.8 native low/medium/xhigh as E-2 rungs and measure tier ordering on REPL/agentic tasks as well as GPQA | M3 monitor: add the effort instruction rungs when the effort curve is booked |
| KS-M2-3 | intake-2970 dive M2 (label-free dense-reference KL as quality metric) | gate any future approximate indexer top-k on teacher-forced KL-vs-exact plus the m^2/2 top-1 certificate beside greedy identity | M3 monitor: gate any future approximate indexer top-k on KL against the exact set plus discarded mass |
| KS-M2-4 | intake-2970 dive M2 (KL beside accuracy) | add dense-reference KL as a second metric in EA-POOL-SCREEN arms | M3 monitor: rank near-tied eviction arms by KL against the full-cache arm if the screen leaves two or more within 3 items |
| KS-M2-5 | intake-2970 dive M2 (one-swap audit) | use SwapCert as a KV-eviction quality gate | K3 knowledge-only: SwapCert needs one partial forward per candidate swap per head, so it is a sampled diagnostic, not a gate |
| KS-W2A-1 | intake-2978 dive W2A (overflow-aware scale choice) | add OAS/Midmax or an MSE choice of {e,e+1} to the experimental MXFP4 quantizer and judge by KLD, when a BF16 to MXFP4 requant is scheduled | M1 monitor: same trigger as the round-up E8M0 rule (one rule under two names) |
| KS-W2A-2 | intake-2978 dive W2A (overflow-aware scale choice) | cite OAS and Midmax as one rule; never carry +2.8 as weight-only | K1 knowledge-only: cite Overflow-Aware Scaling and the PDF-only entry's rule as one rule; the verified gains are W4A4, not weight-only |
| KS-W2A-3 | intake-2978 dive W2A (macro block scaling) | do not pursue MBS or block-16 MXFP4 types now | decline: macro-block scaling and block-16 types would be new GGUF types for no served model |
| KS-W2A-4 | intake-2979 dive W2A (required evidence fields) | consider an ak_row_lint check that a row claiming a mechanism records a counter or A/A key, and an evidence-type enum with an M0 (unnamed gain) catch | P2 / AK-MECH-WITNESS-1 |
| KS-W2A-5 | intake-2979 dive W2A (claim vs evidence) | cite intake-2979 for reporting statistics only | K3 knowledge-only: cite the PR study for reporting statistics only; it never executes the code |
| KS-W2B-3 | intake-2980 dive W2B (perturbed-retrieval certification as a kernel change) | Do not build the certified-sampling kernel now; revisit only if a per-call error guarantee is required | decline: the certified-sampling kernel needs a 4-bit scan of every key and certifies a sampler, not a kept set; no near-term consumer |
| KS-W2B-1 | intake-2981 dive W2B (TV/KL tail-mass identity as a gate) | Add an offline attention-mass-captured (tau) and tau*\|\|mu_tail-mu_head\|\| diagnostic to the evidence for any future approximate or lower-precision Q38FN indexer; exact-set greedy identity stays the pass criterion | M3 monitor: same trigger as the approximate-indexer gate |
| KS-W2B-2 | intake-2981 dive W2B (TV bound as offline gate for eviction) | Log tau on held-out queries beside the EA-POOL-SCREEN task scores to separate scorer resolution from eviction mechanics | M3 monitor: same trigger as the near-tied eviction arms |
| KS-W2B-4 | intake-2981 dive W2B (output-error identity vs joint support) | Use the head/tail value-mean gap from one dense pass as a first-order screen before paying K(M-K) partial forwards for SwapCert-style joint-support audits | K3 knowledge-only: the value-mean gap is a cheap first screen before any one-swap audit |

**Stage-1 preliminary actionables:** Stage 1 ran under pre-approval and listed each entry's dive question as its preliminary actionable (`recommended_actions`); each was discharged by that entry's dive, and every dive-ledger row above has a terminal mapping.

## Dive-surfaced sources

| Source | Bears on | Disposition |
|---|---|---|
| arXiv 2603.08713 (Overflow-Aware Scaling for MXFP4) | intake-2961 | ingested and dived as intake-2978 (wave 2) |
| arXiv 2610.03969 (agent performance-PR validation) | intake-2958 | ingested and dived as intake-2979 (wave 2) |
| arXiv 2610.24991 (certified sparse attention) | intake-2970 | ingested and dived as intake-2980 (wave 2) |
| arXiv 2512.07647 (top-k attention via total variation) | intake-2970 | ingested and dived as intake-2981 (wave 2) |
| arXiv 2605.31464 (GPU Forecasters) | intake-2960 | declined: already in the index as intake-1240 |
| tetherto#586, arXiv 2511.08083 HipKittens | intake-2956 | declined: original fork change; HipKittens already indexed |
| NInfer a754fcf3, QServe | intake-2957 | declined: published baseline rates, W4A8 background |
| arXiv 2512.04355 | intake-2960 | declined: FLOP-only prediction |
| PR #32215 | intake-2962 | declined: merge prerequisite, read only if the DPP reduce screen opens |
| arXiv 2608.02123 PCTree, arXiv 2611.12356 DForkTree | intake-2963, intake-2975 | declined: greedy-only baseline; search-result title only |
| SJTU-DAI-Sys/LEGOSpec, incoai/Qwen3.6-35B-A3B-DFlash2 | intake-2965 | declined: no release evidenced; A3B is served with MTP |
| arXiv 2607.18357, XGrammar-2 | intake-2966 | declined: no served role grows its grammar mid-request |
| arXiv 2408.04667 | intake-2967 | declined: general background |
| arXiv 2610.02163 AutoCompact | intake-2968 | declined: training-based, no training lane |
| arXiv 2509.23202, arXiv 2512.02010 | intake-2978 | declined: related entry intake-2479 exists; title not captured verbatim |
| arXiv 2606.07205, arXiv 2502.07861 | intake-2980 | declined: streaming-attention theory, last wave |

Each decline is recorded in its bearing entry's `dive_corrections`.

## Second-reader results (for operator awareness; none auto-overturned)

160 quote-to-claim checks: 87 yes, 67 partial, 6 no. The 6 "no" anchors were dropped. Most partials are claims that bundle a supported core with a second number or scope the quote does not show; the dive markdown carries the other locators. Partials worth knowing before citing:

- intake-2965 claim 1: the 19.7% Alpaca figure and the "not 13.7%" correction rest on the dive's table read, not on the anchor quote.
- intake-2969 claim 3: the anchor shows about 80 steps, not the 123 in the claim text; cite the claim's step count only from the dive markdown.
- intake-2973 claim 3: the anchor shows only the stochastic-target scope; the T=0 and concurrency exclusions come from the dive's full read.
- intake-2976 claim 2: the anchor shows interactivity ratios (one is 0.96), not throughput.

## Steering ledger

17 operator steering rows (the header, the 15 numbered items and the dive pre-approval line) are recorded verbatim. 15 are `planned` against P1-P4, K1-K2 or M1-M3; the header and the pre-approval line are `context-only`. The full reconciliation is in the payload.

## Stage-3 filing payload

```json
{
 "format_version": 2,
 "entry_updates": [
  {
   "id": "intake-2956",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md",
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: P1 AK-MMQ-SK2-CENSUS; K1 note (no-op on served gfx90a); M1 trigger (MMQ wide prefill)"
   ]
  },
  {
   "id": "intake-2957",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "quantization-and-low-bit.md",
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: M1 trigger: per-channel INT8 arm when QUANT-ROT-1 is booked; K1 note (no int8 rate gain on gfx90a)"
   ]
  },
  {
   "id": "intake-2958",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: P2 AK-MECH-WITNESS-1; M3 backfill trigger"
   ]
  },
  {
   "id": "intake-2959",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "cpu-decode-roofline-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: M1 trigger: CPU-served prompts of 32K or more"
   ]
  },
  {
   "id": "intake-2960",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: P1 VKRC-BYTES-PLAUSIBLE (deterministic check; LLM pre-ranker declined)"
   ]
  },
  {
   "id": "intake-2961",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "quantization-and-low-bit.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: M1 trigger: BF16-to-MXFP4 requant queued; PDF-only, kept stage1-unverified"
   ]
  },
  {
   "id": "intake-2962",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "autokernel-loop.md",
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: K1 note (no served consumer); M1 trigger (GDN reduction share, backend sampling)"
   ]
  },
  {
   "id": "intake-2963",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: P3 DTREE-HEADROOM-REPLAY (Pando tree shape); K2 note (noise coupling)"
   ]
  },
  {
   "id": "intake-2964",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: K2 note: SPEC-DRAFT-SHARPEN CLOSE is the in-house answer"
   ]
  },
  {
   "id": "intake-2965",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: M2 trigger: DFlux checkpoint for a served target"
   ]
  },
  {
   "id": "intake-2966",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: K2 note: no served role grows its grammar mid-request"
   ]
  },
  {
   "id": "intake-2967",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "eval-tower-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: P4 EV-DATE-PIN-1"
   ]
  },
  {
   "id": "intake-2968",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "context-and-token-economy.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: M3 trigger: first complete compaction A/B result"
   ]
  },
  {
   "id": "intake-2969",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "context-and-token-economy.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: M3 trigger: E-2 booked"
   ]
  },
  {
   "id": "intake-2970",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "autokernel-akx-program.md",
    "long-context-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: M3 triggers: approximate indexer top-k; near-tied eviction arms"
   ]
  },
  {
   "id": "intake-2971",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: K1: reference design behind PR #32921; tile-visit order is listed there as future work"
   ]
  },
  {
   "id": "intake-2972",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "eval-tower-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: P4 EV-DATE-PIN-1 (corroboration)"
   ]
  },
  {
   "id": "intake-2973",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: P3 DTREE-HEADROOM-REPLAY (speed-of-light ceiling)"
   ]
  },
  {
   "id": "intake-2974",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: M2 trigger: UBTree 27B selector release; K2 note (load-adaptive budgets)"
   ]
  },
  {
   "id": "intake-2975",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: M2 trigger: DTREE-GDN-BATCH tree win"
   ]
  },
  {
   "id": "intake-2976",
   "integration_disposition": "declined",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: decline: gain needs a large drafting share at high load; ours is small at one or two streams"
   ]
  },
  {
   "id": "intake-2977",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: P2 AK-MECH-WITNESS-1 (cited)"
   ]
  },
  {
   "id": "intake-2978",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "quantization-and-low-bit.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: M1 trigger: BF16-to-MXFP4 requant queued; K1 note (same rule as Midmax)"
   ]
  },
  {
   "id": "intake-2979",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: P2 AK-MECH-WITNESS-1 (cited, reporting statistics only)"
   ]
  },
  {
   "id": "intake-2980",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: K3: certified-sampling kernel declined; exact tail-mass view retained"
   ]
  },
  {
   "id": "intake-2981",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "autokernel-akx-program.md",
    "long-context-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-kspec-1125 Stage 3 plan: M3 triggers: approximate indexer top-k; near-tied eviction arms"
   ]
  }
 ],
 "opportunity_reviews": {
  "P1": {
   "project_objective": "Rank GPU kernel work for the 27B verify step from complete, trustworthy census data (INF-48, INF-06).",
   "implementation_ref": "autokernel-loop.md AK-MMQ-SK2 result note (box left open: step-2 census not filed) @ f19b902; epyc-inference-research census_extract.py extract_verify_roofline @ 4ca0d0d9a (bytes taken from rocprof FETCH_SIZE+WRITE_SIZE with no plausibility check); rocm-kernel-authoring.md VERIFY-KERNEL-ROOFLINE-CENSUS-1 r1 FUTILITY_ATTRIBUTION, r2 in build",
   "gap": "AK-MMQ-SK2 stays open for a census nobody filed; the census extraction accepts any counter bytes, and intake-2960 shows device-memory traffic is exactly where estimates and counters disagree most.",
   "operational_change": "File the full served-shape census under AK-MMQ-SK2; flag implausible census rows before the ranking is read.",
   "benefit_direction": "Closes an open box and prevents a mis-attributed kernel from being ranked first; no change to measured numbers.",
   "owner": "handoffs/active/rocm-kernel-authoring.md",
   "execution_conditions": "Both are zero-compute code or reading tasks; no GPU, no row, no claim.",
   "closure_basis": "Immediate outcome retained; wider stream-k porting stays under the M1 trigger."
  },
  "P2": {
   "project_objective": "Keep only kernel changes whose speedup comes from the mechanism they claim (INF-06 keep gate).",
   "implementation_ref": "scripts/coordination/rowflow/ak_row_lint.py L39, L680-L682 @ f19b902 (NO-WITNESS checks only that a named knob took effect); autokernel-loop.md L1605-L1608 (mechanism_prediction specified in design, not enforced per row); rocm-kernel-authoring.md L1159 (Q8-W8 design 4)",
   "gap": "Rows record A/A and knob-honoured witnesses but not a counter for the claimed mechanism, so a keep can rest on an unverified story.",
   "operational_change": "Add mechanism_witness to row specs and a warn-only MECH-UNWITNESSED lint with tests.",
   "benefit_direction": "Fewer keeps whose cause is wrong; warn-only, so no keep is changed by this box.",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "Code in the root repo with unit tests; enforcement is a later decision once would-fail counts exist.",
   "closure_basis": "Immediate outcome retained; enforcement and the backfill scan stay under M3."
  },
  "P3": {
   "project_objective": "Decide whether draft trees on 27B DFlash2 still have headroom worth a GPU row (INF-50).",
   "implementation_ref": "speculative-decoding.md SPEC-DTREE-DICE capture ak-dice-capture-27b-dflash2-gpu-20261123-r2 (SHA-256 82d46a61...) and SPEC-DRAFT-SHARPEN replay protocol @ f19b902; epyc-inference-research scripts/kernel_rnd/dice_replay/dice_replay_27b.py",
   "gap": "No measured ceiling on tokens per pass exists for our captured target distributions, and the best-first tree shape of intake-2963 has never been replayed against our builder.",
   "operational_change": "One CPU replay row on the retained capture: speed-of-light ceiling plus a Pando-style tree under the V1 rejection-tree verify.",
   "benefit_direction": "Either closes tree-shape work on 27B with a measured ceiling or names a tree shape worth one GPU row; output law is unchanged (lossless verify).",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "CPU quarter only, no model load, no server; predeclaration sealed before the replay.",
   "closure_basis": "Immediate outcome retained; a GPU row follows only on FILE_GPU_ROW."
  },
  "P4": {
   "project_objective": "Make eval and judge results reproducible across dates (EVL-14 prompt-construction determinism).",
   "implementation_ref": "epyc-orchestrator scripts/validate/template_provenance.py @ faa783c7 (records template hashes, not date use); C21 common/chat.cpp L2573-L2581 @ 98ff8a4 (date_string from the wall clock), L2747-L2750 (override via chat_template_kwargs)",
   "gap": "Nothing records whether a served template reads the date, and nothing pins it; served templates read no date today only by accident.",
   "operational_change": "template_reads_date in the provenance plan rows and a registry warning for an unpinned date-reading template.",
   "benefit_direction": "A future template cannot silently add a date-dependent prompt; no change to current scores.",
   "owner": "handoffs/active/eval-tower-program.md",
   "execution_conditions": "Orchestrator code with unit tests; no eval rerun.",
   "closure_basis": "Immediate outcome retained; passing a pinned date in requests is needed only when a flagged template is served."
  },
  "K1": {
   "project_objective": "Avoid re-deriving kernel and quantization levers that do not transfer to gfx90a or Zen 5.",
   "implementation_ref": "dives K1, K2, K3, W2A (research/deep-dives/intake-kspec-1125/) against C21 98ff8a4 code",
   "gap": "None operational: each finding is a no-op, absent or already-present verdict.",
   "operational_change": "Dated knowledge notes in autokernel-loop.md and quantization-and-low-bit.md; no checkbox.",
   "benefit_direction": "Saves future sessions from porting no-op levers.",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "Note text only.",
   "closure_basis": "The immediate step considered (ports of PR #32921, PR #32867, SQ/SHI kernels) has no served consumer or no rate gain on gfx90a, per the dives' code reads; nothing remains to run."
  },
  "K2": {
   "project_objective": "Record speculative-decoding results the project already measured, so the papers' gains are not carried to our stack.",
   "implementation_ref": "speculative-decoding.md SPEC-DRAFT-SHARPEN (CLOSE), SPEC-DTREE-DICE (V3 NULL), DF2-FT-1 (deferred) @ f19b902",
   "gap": "None operational.",
   "operational_change": "One dated knowledge note beside SPEC-DRAFT-SHARPEN; no checkbox.",
   "benefit_direction": "Prevents re-running closed replays.",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "Note text only.",
   "closure_basis": "Draft temperature and noise coupling were already replayed in-house with null results; LEGOSpec and GramDelta have no served consumer."
  },
  "K3": {
   "project_objective": "Keep methodology context on the intake entries for later citation.",
   "implementation_ref": "dives M1, M2, W2A, W2B",
   "gap": "None operational.",
   "operational_change": "Intake-entry dispositions only; no handoff note (owner listed as the AutoKernel handoff, where two of the five items apply).",
   "benefit_direction": "Correct citations later.",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "No handoff change.",
   "closure_basis": "Each item is corroboration or a diagnostic with no current gate to attach to."
  },
  "M1": {
   "project_objective": "Act on kernel, quantization and CPU-prefill levers when their precondition appears.",
   "implementation_ref": "mmq.cu L346-L362, mmq-vec-dot.cuh L197, ggml-quants.c L368, ops.cpp flash-attention chunking @ 98ff8a4; quantization-and-low-bit.md QUANT-ROT-1 @ f19b902",
   "gap": "Each lever lacks its precondition today (no MMQ wide prefill, no queued MXFP4 requant, no 32K CPU prompts, no counter row on MMQ 9-128).",
   "operational_change": "Owned trigger prose under the relevant boxes; no checkbox.",
   "benefit_direction": "The lever is tried when it can pay.",
   "owner": "handoffs/active/rocm-kernel-authoring.md",
   "execution_conditions": "Each trigger is observable in its handoff.",
   "closure_basis": "No immediate step: each considered probe has no consumer until its trigger fires (for example the round-up E8M0 rule cannot change our only MXFP4 model, a lossless repack)."
  },
  "M2": {
   "project_objective": "Act on drafter and tree ideas when a checkpoint or a cheaper verify appears.",
   "implementation_ref": "speculative-decoding.md DTREE-GDN-BATCH reopen criteria, DF2-CARD-CONFORMANCE-1 @ f19b902",
   "gap": "No released UBTree selector or DFlux checkpoint for a served target; the 16-node tree does not yet beat the chain.",
   "operational_change": "Owned trigger prose in speculative-decoding.md; no checkbox.",
   "benefit_direction": "A probe runs when there is something to probe.",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "Observable release or measured tree win.",
   "closure_basis": "No immediate step: there is no checkpoint to load and no tree win to calibrate."
  },
  "M3": {
   "project_objective": "Add better quality metrics to compaction, effort and attention-selection measurements when those measurements run.",
   "implementation_ref": "context-and-token-economy.md TOC-CMP-4 (r3 pilot incomplete) and E-2; long-context-program.md EA-POOL-SCREEN; autokernel-akx-program.md Q38FN-INDEXER-TOPK-CPU/-EXACT @ f19b902",
   "gap": "The host measurements have not produced a result to validate a new metric against, or have no approximate candidate to gate.",
   "operational_change": "Owned trigger prose under each host box; no checkbox.",
   "benefit_direction": "Finer quality evidence once there is something to compare.",
   "owner": "handoffs/active/context-and-token-economy.md",
   "execution_conditions": "Each trigger is the host box's own next event.",
   "closure_basis": "No immediate step: building a distortion grader or a KL metric before its host run yields a result leaves it unvalidated, and the exact indexer top-k already passes greedy identity."
  }
 },
 "opportunity_scan": [
  {
   "scan_id": "S1",
   "source_ref": "intake-2956 PR #32921 body and diff (head 5bc67fe5d273)",
   "implementation_ref": "C21 mmq.cuh stream-k launcher and mmq.cu L346-L362 @ 98ff8a4",
   "mechanism": "column-tile-outermost stream-k walk",
   "consumer": "gfx90a MMQ (27B verify, prefill)",
   "application": "port the order to HIP",
   "disposition": "context-only",
   "ledger_ids": [
    "KS-K1-2",
    "KS-K1-3"
   ],
   "basis": "one column tile at M=36 and wide Q8_0 on rocBLAS make it a no-op today"
  },
  {
   "scan_id": "S2",
   "source_ref": "intake-2956 dive K1 shape arithmetic; autokernel-loop.md AK-MMQ-SK2 step 2 @ f19b902",
   "implementation_ref": "AK-MMQ-SK2 result note: census not filed",
   "mechanism": "served-shape tile census",
   "consumer": "AK-MMQ-SK2 owner",
   "application": "file the census to close the box",
   "disposition": "actionable",
   "ledger_ids": [
    "KS-K1-1"
   ],
   "basis": "the dive did the dense-27B half; the box names the rest"
  },
  {
   "scan_id": "S3",
   "source_ref": "intake-2971 Stream-K §5.2 and future work",
   "implementation_ref": "iqk_mul_mat.cpp row split (EPYC)",
   "mechanism": "tile-visit order as untested future work; x-stationary CPU split",
   "consumer": "EPYC iqk prefill",
   "application": "none",
   "disposition": "context-only",
   "ledger_ids": [
    "KS-K1-4"
   ],
   "basis": "iqk already keeps x stationary"
  },
  {
   "scan_id": "S4",
   "source_ref": "intake-2957 §3 SQ operand rebuild and Table 2",
   "implementation_ref": "C21 mmq-vec-dot.cuh L197 (per-32 scale epilogue), mma.cuh L1311-L1315 (CDNA2 int8 K) @ 98ff8a4",
   "mechanism": "full-K integer dot without per-group float scale",
   "consumer": "gfx90a MMQ, QUANT-ROT-1",
   "application": "per-channel INT8 arm; epilogue share measurement",
   "disposition": "actionable",
   "ledger_ids": [
    "KS-K2-1",
    "KS-K2-2",
    "KS-K2-3",
    "KS-K2-4"
   ],
   "basis": "no int8 rate gain on CDNA2; value limited to bytes and the scale epilogue, so both are trigger-gated"
  },
  {
   "scan_id": "S5",
   "source_ref": "intake-2958 Table II and claimed-vs-unclaimed ratios",
   "implementation_ref": "ak_row_lint.py L39, L680-L682 @ f19b902",
   "mechanism": "claimed-mechanism witness with A/A",
   "consumer": "AutoKernel row lint and keep gate",
   "application": "mechanism_witness field and warn-only lint",
   "disposition": "actionable",
   "ledger_ids": [
    "KS-M1-1",
    "KS-M1-2",
    "KS-W2A-4"
   ],
   "basis": "lint checks only knob effect; design already names expected counter changes"
  },
  {
   "scan_id": "S6",
   "source_ref": "intake-2977 re-execution protocol; intake-2979 validation taxonomy",
   "implementation_ref": "autokernel-loop.md A/A keep path L4423-L4426 @ f19b902",
   "mechanism": "re-execution of claimed speedups; evidence-form taxonomy",
   "consumer": "AutoKernel keep gate",
   "application": "none beyond S5",
   "disposition": "covered",
   "ledger_ids": [
    "KS-M1-5",
    "KS-W2A-5"
   ],
   "basis": "re-measure and A/A gates already exist"
  },
  {
   "scan_id": "S7",
   "source_ref": "intake-2959 Tables 1, 2, 6 and dispatcher description",
   "implementation_ref": "C21 ops.cpp flash-attention tiled path and chunk counter @ 98ff8a4",
   "mechanism": "L2/L3 blocking and longest-first task queue for causal prefill attention",
   "consumer": "CPU prefill",
   "application": "chunk-order reversal and blocking",
   "disposition": "actionable",
   "ledger_ids": [
    "KS-K4-2",
    "KS-K4-3"
   ],
   "basis": "no CPU-served long-prompt role today, so trigger-gated"
  },
  {
   "scan_id": "S8",
   "source_ref": "intake-2960 Tables 1 and A.8, traffic accuracy",
   "implementation_ref": "census_extract.py extract_verify_roofline @ 4ca0d0d9a",
   "mechanism": "device-memory traffic is the weak estimate",
   "consumer": "verify-kernel census",
   "application": "deterministic bytes plausibility check",
   "disposition": "actionable",
   "ledger_ids": [
    "KS-K3-3",
    "KS-K3-4"
   ],
   "basis": "census reads counters directly; plausibility check catches bad counter reads; LLM pre-ranking declined"
  },
  {
   "scan_id": "S9",
   "source_ref": "intake-2961 Midmax rule (PDF, hand-checked); intake-2978 OAS §3",
   "implementation_ref": "ggml-quants.c quantize_row_mxfp4_ref L368 @ 98ff8a4",
   "mechanism": "round-up E8M0 scale selection",
   "consumer": "MXFP4 requant",
   "application": "quantizer change judged by KLD",
   "disposition": "actionable",
   "ledger_ids": [
    "KS-K4-1",
    "KS-W2A-1",
    "KS-W2A-2",
    "KS-W2A-3"
   ],
   "basis": "only served MXFP4 model is a lossless repack, so trigger-gated"
  },
  {
   "scan_id": "S10",
   "source_ref": "intake-2962 PR #32867 diff (head 46f9316db490)",
   "implementation_ref": "C21 cumsum.cu L146, L157; llama-context.cpp L315-L316 fused GDN defaults @ 98ff8a4",
   "mechanism": "DPP wave64 inclusive scan and DPP reduce",
   "consumer": "GDN and sampler paths on gfx90a",
   "application": "port scan; screen reduce",
   "disposition": "context-only",
   "ledger_ids": [
    "KS-K3-1",
    "KS-K3-2",
    "KS-K3-5"
   ],
   "basis": "no served CUMSUM consumer"
  },
  {
   "scan_id": "S11",
   "source_ref": "intake-2963 §4 noise coupling, §7 results; intake-2973 bound; intake-2974 27B datapoint",
   "implementation_ref": "speculative-decoding.md SPEC-DTREE-DICE capture and replay @ f19b902",
   "mechanism": "best-first parallel-drafter tree; tokens-per-pass ceiling",
   "consumer": "27B DFlash2 tree decision",
   "application": "offline ceiling plus tree-shape replay",
   "disposition": "actionable",
   "ledger_ids": [
    "KS-S1-1",
    "KS-S1-2",
    "KS-S1-3",
    "KS-S1-4",
    "KS-S1-5",
    "KS-S1-6"
   ],
   "basis": "capture and replay tooling exist; no ceiling or best-first shape replayed yet"
  },
  {
   "scan_id": "S12",
   "source_ref": "intake-2964 Tables 1-2; intake-2975 calibration; intake-2976 estimator",
   "implementation_ref": "speculative.cpp L1812-L1830, server-context.cpp L4736-L4739 @ 98ff8a4; SPEC-DRAFT-SHARPEN CLOSE",
   "mechanism": "draft temperature and calibration",
   "consumer": "27B DFlash2, A3B MTP",
   "application": "none",
   "disposition": "covered",
   "ledger_ids": [
    "KS-S2-1",
    "KS-S2-2",
    "KS-S2-3",
    "KS-S2-4",
    "KS-S2-5"
   ],
   "basis": "already replayed in-house with a CLOSE verdict"
  },
  {
   "scan_id": "S13",
   "source_ref": "intake-2965 Tables III-VIII",
   "implementation_ref": "speculative-decoding.md DFlash2 drafter rows and DF2-FT-1 @ f19b902; C21 dflash.cpp",
   "mechanism": "DFlux drafter design and training",
   "consumer": "DFlash2 lineup",
   "application": "paired probe on release",
   "disposition": "context-only",
   "ledger_ids": [
    "KS-S3-1",
    "KS-S3-2",
    "KS-S3-3"
   ],
   "basis": "no released checkpoint; we do not train drafters"
  },
  {
   "scan_id": "S14",
   "source_ref": "intake-2966 Tables 1, 5, 6",
   "implementation_ref": "orchestrator src/graph/helpers.py L1694-L1716 (grammar built once per request)",
   "mechanism": "incremental grammar deltas",
   "consumer": "grammar-constrained roles",
   "application": "none",
   "disposition": "context-only",
   "ledger_ids": [
    "KS-S3-4",
    "KS-S3-5"
   ],
   "basis": "no role grows its grammar mid-request"
  },
  {
   "scan_id": "S15",
   "source_ref": "intake-2967 audit and churn results; intake-2972 date sweep",
   "implementation_ref": "template_provenance.py @ faa783c7; C21 chat.cpp L2573-L2581, L2747-L2750",
   "mechanism": "system-prompt date as a hidden variable",
   "consumer": "eval tower and judge provenance",
   "application": "template_reads_date plus registry warning",
   "disposition": "actionable",
   "ledger_ids": [
    "KS-M1-3",
    "KS-M1-4",
    "KS-M1-6"
   ],
   "basis": "llama-server injects the wall-clock date; nothing records it"
  },
  {
   "scan_id": "S16",
   "source_ref": "intake-2968 §3 distortion objective",
   "implementation_ref": "context-and-token-economy.md TOC-CMP-4 @ f19b902",
   "mechanism": "behavior-distortion score as untrained grader",
   "consumer": "compaction A/B",
   "application": "secondary metric",
   "disposition": "actionable",
   "ledger_ids": [
    "KS-M2-1"
   ],
   "basis": "host A/B has no complete result to validate against yet, so trigger-gated"
  },
  {
   "scan_id": "S17",
   "source_ref": "intake-2969 tier results and recipes",
   "implementation_ref": "context-and-token-economy.md E-2 @ f19b902",
   "mechanism": "effort instruction texts",
   "consumer": "effort-level curve",
   "application": "extra rungs",
   "disposition": "actionable",
   "ledger_ids": [
    "KS-M2-2"
   ],
   "basis": "all paper results need training; cheap only as rungs of an already-planned curve"
  },
  {
   "scan_id": "S18",
   "source_ref": "intake-2970 audits and K=128/256 results; intake-2981 tail-mass identity; intake-2980 certificates",
   "implementation_ref": "autokernel-akx-program.md Q38FN-INDEXER-TOPK-CPU/-EXACT; long-context-program.md EA-POOL-SCREEN @ f19b902",
   "mechanism": "joint-support quality and discarded-mass bound",
   "consumer": "indexer top-k and KV eviction screens",
   "application": "KL and tail-mass gates",
   "disposition": "actionable",
   "ledger_ids": [
    "KS-M2-3",
    "KS-M2-4",
    "KS-M2-5",
    "KS-W2B-1",
    "KS-W2B-2",
    "KS-W2B-3",
    "KS-W2B-4"
   ],
   "basis": "exact top-k already used; eviction screen not yet run, so trigger-gated"
  }
 ],
 "actionable_additions": [],
 "steering_reconciliation": [
  {
   "seq": 1,
   "stage": 1,
   "verbatim": "Operator steering (context for Stage 1 ranking and Stage 3 grounding, not authorization to write handoffs):",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Frames the 15 steering items as context for ranking and grounding, not filing authority; applied as such."
  },
  {
   "seq": 2,
   "stage": 1,
   "verbatim": "1. llama.cpp PR #32921 (open): MMQ stream-k makes column tile jt the slowest index so blocks sharing x rows co-run and share L2; NVIDIA-only, dense, J==128, more tiles than blocks; AMD keeps old order. GB10 Qwen3.8 27B Q8_0 pp2048 1.162x @ub256, 1.257x @ub512; single q8_0 8192x512 MUL_MAT 1.96x; mean KLD 0.00070 vs master. Not on gfx90a as-is.\n   Value: gfx90a MMQ prefill/verify for 27B Q8_0; compare with the stream-k notes filed for #32837 in the KB.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   Principles: tile-walk order for L2 reuse of x row bands; compile-time order template vs runtime branch (8% loss reported); when tiles > CUs on 104-CU gfx90a.",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "P1",
   "reason": "Principles checked against C21 code in dive K1: no-op on served gfx90a shapes (one column tile at M=36), so only the census box and an M1 trigger are filed."
  },
  {
   "seq": 3,
   "stage": 1,
   "verbatim": "2. Shifter Quantization (arXiv 2611.33080): appends/shifts shared bits to rebuild native-width integer operands so INT8/INT4 MMA spans the whole dot product. SQ2/SHI2 2.71-3.77x llama.cpp Q2_K 4096-token prefill, 6.6-7.8% lower WikiText-2 KL; SQ4 1.43-2.47x NInfer groupwise prefill, 24-40% lower KL; SQ8 +27.4% batch-one prefill, 72.7% lower KL vs vLLM online FP8. RTX 5090, Qwen3.8-27B shapes. Not gfx90a/EPYC-tested.\n   Value: INF-80 quantization-and-low-bit; Q8-W8-GEMV-1 int8-MFMA lane; KLD gates.\n   Extract/Check: as above.\n   Principles: shared-bit packing vs per-group scales; mapping to v_mfma i8 and AVX-512 VNNI; coalescing of packed rows (see the design-4 diagnosis).",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "M1",
   "reason": "Dive K2: exact integer dot, but no int8 rate gain on gfx90a and SHI needs INT4 MFMA; coalescing lesson already present (Q8-W8 design 5); arm and epilogue measurement trigger-gated."
  },
  {
   "seq": 4,
   "stage": 1,
   "verbatim": "3. Below the Stopwatch (arXiv 2611.31460): checks claimed perf mechanisms of 1,343 agent PRs with counters and LTTng traces; of 82 analyzed, 32 faster, 28 no clear change, 22 slower; claimed signal in 34; 42 changed output; kernel signals 1.7x more often for the claimed mechanism, instruction count 1.15x. Hardware-agnostic method.\n   Value: AutoKernel keep gate / akloop failclass (mechanism-witness rows); mirrors the Q8-W8 \"coalescing, not instruction count\" lesson.",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "P2",
   "reason": "Dive M1 confirmed the keep-gate gap (no claimed-mechanism counter); filed as warn-only lint AK-MECH-WITNESS-1."
  },
  {
   "seq": 5,
   "stage": 1,
   "verbatim": "4. TACPU (arXiv 2610.38809 v3): tiered cache blocking + in-kernel task dispatch for causal prefill attention on CPU; up to 2.01x over PyTorch SDPA, FlexAttention, SGLang; SGLang TTFT up to 1.74x on Llama-3.1-8B. Intel Xeon 6767P (AMX + AVX-512) plus a client platform; not EPYC-tested.\n   Value: INF-70 cpu decode roofline / XFER-4b prefill A/B; NUMA placement (INF-45).\n   Extract/Check: as above.\n   Principles: L1/L2/L3 tile sizing; dispatcher vs static split under NPS4; AMX-GEMM/AVX-512-softmax overlap has no Zen 5 equivalent.",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "M1",
   "reason": "Dive K4: our CPU FA has no L2/L3 blocking and runs cheapest-first; no CPU-served long-prompt role, so trigger-gated; AMX overlap has no Zen 5 counterpart."
  },
  {
   "seq": 6,
   "stage": 1,
   "verbatim": "5. LLM roofline arithmetic-intensity estimation (arXiv 2611.32975): three LLMs, 179 combinations, four NVIDIA/AMD GPUs incl. MI300X; compiler artifacts raise within-1.20x AI estimates from 8-14% to 26-32%; bound class correct 78-92%; FLOPs within tolerance 59-88% vs device-memory traffic 36-40%; agentic analysis +6.5 pp for one model at 3.6x cost. Not gfx90a.\n   Value: VERIFY-KERNEL-ROOFLINE-CENSUS-1 and AutoKernel census planner (pre-ranking surfaces before rocprofv3 rows).\n   Extract/Check: as above.\n   Principles: ISA/compiler-artifact prompting; cache-dependent traffic as main error source.",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "P1",
   "reason": "Dive K3: an LLM pre-ranker would not help the census; a deterministic bytes plausibility check (VKRC-BYTES-PLAUSIBLE) is filed instead."
  },
  {
   "seq": 7,
   "stage": 1,
   "verbatim": "6. MXFP4 PTQ composability (arXiv 2611.32873): six LLMs, MXFP6/MXFP4/NVFP4; recipes are format-dependent; MXFP4 gains from rotation + error-correcting PTQ; Midmax calibration-free scale selection reduces power-of-two scale clipping; MXFP6 act + MXFP4 weights matches/exceeds in-house BF16 on Llama-3.1-8B. Built for Blackwell/CDNA4 FP4; no FP4 on gfx90a.\n   Value: offline requant choice for E8M0-scaled GGUF types, judged by KLD gates; INF-80.\n   Extract/Check: as above.\n   Principles: Midmax scale rule; Hadamard rotation granularity; INT8/FP16 emulation cost.",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "M1",
   "reason": "Dives K4 and W2A: Midmax equals Overflow-Aware Scaling; our only MXFP4 model is a lossless repack, so the rule waits for a queued requant."
  },
  {
   "seq": 8,
   "stage": 1,
   "verbatim": "7. llama.cpp PR #32867 (open): HIP DPP path for warp_prefix_inclusive_sum; CUMSUM f32 ~15-19% faster on MI50 (gfx906) at large ne, up to ~24% on RDNA4 (gfx1200). Not measured on gfx90a.\n   Value: GDN/cumsum paths (gdn-state-fwd, AK-BW-GDN-GATE-FOLD); cheap port candidate.\n   Extract/Check: as above.\n   Principles: DPP row_shr/row_bcast scan vs shuffle; wave64 cross-row steps.",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "K1",
   "reason": "Dive K3: the scan has no served consumer (fused GDN ops skip CUMSUM); recorded as knowledge with an M1 trigger for the DPP reduce."
  },
  {
   "seq": 9,
   "stage": 1,
   "verbatim": "8. Pando (arXiv 2611.32269): dynamic draft trees on parallel (DFlash/DSpark) drafters with noise-coupled pruning (target noise drawn before drafting; lossless, no retraining); acceptance length up to +8.4% on Qwen3-8B; 16-node tree 5.3x speedup, 4.2x energy reduction vs AR on an edge device, 25% faster than DSpark's chain, 27% faster than an EAGLE-3 tree; ridge-point roofline normalization. Algorithmic; applies to MI210 and EPYC.\n   Value: INF-50 DFlash2 + DTREE device-side acceptance; DF2 lineup acceptance floor.",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "P3",
   "reason": "Dive S1: Pando's speedups are modelled and noise coupling is not lossless under our verifier; the tree-shape and ceiling replay (DTREE-HEADROOM-REPLAY) is filed."
  },
  {
   "seq": 10,
   "stage": 1,
   "verbatim": "9. Draft calibration (arXiv 2611.33111): open drafters are underconfident vs target; draft temperature scaling gives up to ~10% acceptance length at almost no cost; Dirichlet scaling generally does not beat it. Hardware-agnostic.\n   Value: SPEC-DISTS-TRUNC; Q38FN drafter acceptance (0.795 -> 0.751 under ROWEXACT).",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "K2",
   "reason": "Dive S2: already measured in-house as about zero (SPEC-DRAFT-SHARPEN CLOSE); the Q38FN acceptance drop is a greedy batch-invariance effect calibration cannot touch."
  },
  {
   "seq": 11,
   "stage": 1,
   "verbatim": "10. LEGOSpec / DFlux (arXiv 2611.33004): composable draft design; DFlux (conv SWA-GQA hybrid backbone, Residual Corrector, hierarchical supervision) up to +13.7% acceptance length, +34.7% long context across Qwen/Gemma; training throughput up to +79%. Hardware-agnostic.\n   Value: DFlash2 drafter training recipe (INF-50).",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "M2",
   "reason": "Dive S3: gains confounded by training scale, no checkpoint released; probe on release only."
  },
  {
   "seq": 12,
   "stage": 1,
   "verbatim": "11. GramDelta (arXiv 2611.32807): incremental constrained decoding under runtime grammar updates; median first-seen update latency 10.7-11.5x lower; added TPOT over unconstrained cut 53.1-81.9% vs reconstruction. CPU-side mask logic.\n   Value: SPEC-GRAM-JSON-1; llguidance default flip (INF-83 D2).",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "K2",
   "reason": "Dive S3: no served role grows its grammar mid-request; no bearing on SPEC-GRAM-JSON-1 or the llguidance flip."
  },
  {
   "seq": 13,
   "stage": 1,
   "verbatim": "12. System-prompt date as hidden variable (arXiv 2611.31254): two plausible dates flip a median 6.6% of items across six models/four benchmarks; one-day rerun flips about as many as a batch-size change; GCG-searched dates cost Llama-3.x up to 36.5 points; judge verdicts shift; 15-32% of reproduced jailbreaks undone. None of 11 eval stacks pin the date.\n   Value: eval tower / OFFICIAL-SAMPLING recipes / LLM-as-judge rigor (pin + log date).",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "P4",
   "reason": "Dive M1: llama-server injects the wall-clock date; EV-DATE-PIN-1 records and guards it."
  },
  {
   "seq": 14,
   "stage": 1,
   "verbatim": "13. RECAP (arXiv 2611.31258): RL for agent context compaction via behavior-distortion objective (summary reward + post-compaction self-distillation); Qwen3.5-4B +4.6% BrowseComp-plus, +4.3% SWE-bench Verified over task-reward-only RL.\n   Value: orchestrator context compaction; local Qwen post-training.",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "M3",
   "reason": "Dive M2: the distortion score works without training but the compaction A/B has no complete result yet; trigger-gated."
  },
  {
   "seq": 15,
   "stage": 1,
   "verbatim": "14. Reasoning-effort training, OPD vs RL (arXiv 2611.32131): length-penalized RL cuts AIME25 thinking 70% with no accuracy loss but collapses tiers jointly; multi-teacher OPD: low/medium use 58%/43% fewer thinking tokens than high, high +3.1 points over reference across 33 benchmarks; one token-level KL anchor on the high tier separates tiers within a single RL stage.\n   Value: thinking budgets / routing-escalation tiers for local Qwen.",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "M3",
   "reason": "Dive M2: every effort result needs training and no prompt-only arm exists; rungs added only when E-2 is booked."
  },
  {
   "seq": 16,
   "stage": 1,
   "verbatim": "15. Limits of Top-K attention (arXiv 2611.32324): independent ranking can be unboundedly worse than joint support (133.2x KL in a 4-position construction); exact-singleton Top-4 leaves >=10% improvement in 55/60, 49/60, 60/60 cases (SmolLM2, Gemma, Qwen); SwapCert one-swap audit catches 157/164.\n   Value: INDEXER-TOPK-CPU (INF-82), KV compaction/eviction gates.",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "planned",
   "plan_ref": "M3",
   "reason": "Dives M2 and W2B: the result concerns singleton-KL ranking, not our learned indexer; KL and tail-mass gates attach to the next approximate top-k or near-tied eviction arms."
  },
  {
   "seq": 17,
   "stage": 1,
   "verbatim": "Automatically accept every recommended deep dive and literature expansion for up to four Stage 2 sweeps.",
   "ts": "2026-11-25T00:00:00Z",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied as the dive set: all 22 Stage-1 entries dived, one Stage-2b wave of 4; every wave-2 surfaced source recommended decline, so two of four permitted sweeps were used. Not filing authority."
  }
 ],
 "outcome_reviews": {
  "KS-K1-1": {
   "required_outcome": "File the dense 27B tile census (tiles and ntx per tensor at M=36 and hypothetical ub256/512, plus routing) under AK-MMQ-SK2 step 2 to close its remaining gap",
   "review_status": "preserved",
   "review_basis": "Main review: AK-MMQ-SK2-CENSUS carries this outcome (AK-MMQ-SK2 stays open for a census nobody filed; the census extraction accepts any counter bytes, and intake-2960 shows device-memory traffic is exactly where estimates and counters disagree most.)",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-MMQ-SK2-CENSUS",
     "task_text": "- [ ] **AK-MMQ-SK2-CENSUS** [non-inference] Finish the AK-MMQ-SK2 step-2 served-shape census, the one item that keeps that box open: take the dense Qwen3.8-27B Q8_0 tile table already worked out in research/deep-dives/intake-kspec-1125/dive-K1-streamk-order.md (np4 verify M=36 picks J=48 so one column tile per tensor; Q8_0 above 128 columns is routed to rocBLAS by mmq.cu L346-L362 @ 98ff8a4), add the A3B Q8_0 MUL_MAT_ID shapes above the MMVQ cap and the Q4_K/Q6_K 5-128-row shapes from the C21 code, and record per shape the tile count against the 104 stream-k blocks, where force-tiling fires and where the grid cap changes the grid; zero compute (intake-2956, intake-2971)",
     "acceptance": "Census table for all three shape families filed under AK-MMQ-SK2, letting its owner judge its done-when."
    }
   ]
  },
  "KS-K1-2": {
   "required_outcome": "Record that PR #32921 is a no-op on served gfx90a MMQ (ntx=1 at M=36, Q8_0 n>128 on rocBLAS, J==128 absent on CDNA)",
   "review_status": "closed-with-basis",
   "review_basis": "the PR's order is a no-op on served gfx90a shapes (one column tile at M=36, wide Q8_0 on rocBLAS, J=128 absent on CDNA)",
   "task_refs": []
  },
  "KS-K1-3": {
   "required_outcome": "If Q8_0 dense prefill ever routes to MMQ on gfx90a, port the column-outer order with a CDNA J=64 gate as the first cheap lever, wall-clock vetoed",
   "review_status": "closed-with-basis",
   "review_basis": "port the order only if Q8_0 dense prefill is ever routed to MMQ on gfx90a",
   "task_refs": []
  },
  "KS-K1-4": {
   "required_outcome": "Note that iqk prefill on EPYC is already x-stationary (per-thread row band, 64-row steps over all Ny); the npt<=16 Ny-split branch reads small-tensor x bands from two possibly cross-NUMA threads",
   "review_status": "closed-with-basis",
   "review_basis": "iqk on EPYC already sweeps all activation columns per 64-row weight step",
   "task_refs": []
  },
  "KS-K2-1": {
   "required_outcome": "we should add an offline arm to QUANT-ROT-1 comparing per-output-channel INT8 after signed H512 (SQ8 recipe) against Q8_0 per-32 FP16 scales on real 27B rows (weight/output error, dKLD if cheap), no kernel",
   "review_status": "closed-with-basis",
   "review_basis": "add the per-channel INT8 plus H512 arm when the activation-rotation probe is booked",
   "task_refs": []
  },
  "KS-K2-2": {
   "required_outcome": "we could record the VALU epilogue share (C.x*dA*dB, mmq-vec-dot.cuh:L197) vs MFMA busy when a counter row next profiles MMQ Q8_0 at ne11 9-128 on CDNA2",
   "review_status": "closed-with-basis",
   "review_basis": "record the scale-epilogue VALU share when a counter row next profiles MMQ at 9-128 columns",
   "task_refs": []
  },
  "KS-K2-3": {
   "required_outcome": "record that on gfx90a int8 MFMA (16x16x16i8) has the same per-instruction K as f16 MFMA, so an SQ8-style prefill gain is limited to removing the dequant-to-f16 pass and halving operand bytes",
   "review_status": "closed-with-basis",
   "review_basis": "gfx90a int8 MFMA has the same K per instruction as f16, so no rate gain",
   "task_refs": []
  },
  "KS-K2-4": {
   "required_outcome": "record that SHI does not transfer to MI210 (no INT4 MFMA), CPU K-quant dots already use SHI-style integer correction products, and SQ2/SQ4 matter only if EXL3-X0b reopens",
   "review_status": "closed-with-basis",
   "review_basis": "SHI needs INT4 MFMA (absent on CDNA2); CPU K-quant dots already use integer correction products",
   "task_refs": []
  },
  "KS-K3-1": {
   "required_outcome": "Record that warp_prefix_inclusive_sum has one caller and CUMSUM is absent from served fused-GDN graphs; do not port the scan",
   "review_status": "closed-with-basis",
   "review_basis": "the DPP scan's one caller is CUMSUM, which the served fused GDN graphs do not emit",
   "task_refs": []
  },
  "KS-K3-2": {
   "required_outcome": "Op-level screen of the PR DPP warp_reduce_sum (incl. lane0-only tail) in the stock GDN recurrent kernel at GDN-VERIFY-BASE shapes; stop-on-futility if reduction share under 3 percent or gain under A/A p95",
   "review_status": "closed-with-basis",
   "review_basis": "screen the DPP warp reduction only if the census shows GDN reductions at 3 percent or more of the step",
   "task_refs": []
  },
  "KS-K3-5": {
   "required_outcome": "Check whether backend sampling is enabled on any served GPU role; if so run one CUMSUM [vocab,1] op on gfx90a before judging the PR",
   "review_status": "closed-with-basis",
   "review_basis": "time CUMSUM over the vocabulary on gfx90a only if backend sampling is turned on for a GPU role",
   "task_refs": []
  },
  "KS-K3-3": {
   "required_outcome": "Add a deterministic plausibility check to census post-processing: flag kernel rows whose FETCH_SIZE+WRITE_SIZE-derived GB/s exceeds the measured 1.498 TB/s peak or whose bytes differ from the analytic footprint (tensor bytes x launches) by more than 2x; no LLM",
   "review_status": "preserved",
   "review_basis": "Main review: VKRC-BYTES-PLAUSIBLE carries this outcome (AK-MMQ-SK2 stays open for a census nobody filed; the census extraction accepts any counter bytes, and intake-2960 shows device-memory traffic is exactly where estimates and counters disagree most.)",
   "task_refs": [
    {
     "owner": "handoffs/active/rocm-kernel-authoring.md",
     "task_id": "VKRC-BYTES-PLAUSIBLE",
     "task_text": "- [ ] **VKRC-BYTES-PLAUSIBLE** [non-inference] Add a deterministic bytes plausibility check to the verify-kernel roofline census extraction (epyc-inference-research scripts/kernel_rnd/autokernel/loop/census_extract.py extract_verify_roofline @ 4ca0d0d9a) before VERIFY-KERNEL-ROOFLINE-CENSUS-1 r2 is read: flag every kernel row whose FETCH_SIZE+WRITE_SIZE-derived GB/s exceeds the HBM peak the census uses, or whose bytes per call differ from the analytic footprint (weight or tensor bytes x launches) by more than 2x, and print the flagged rows beside the ranking; no LLM estimate (intake-2960: LLM device-memory traffic estimates are the weak half, within 1.20x in 36-40% of cases)",
     "acceptance": "Unit test on the existing census fixture flags over-peak and off-footprint rows and leaves plausible rows unflagged."
    }
   ]
  },
  "KS-K3-4": {
   "required_outcome": "Do not build an LLM/ISA roofline pre-ranker for the census; if the AutoKernel planner wants a prior, use analytic bytes and measured time shares and gate any LLM prior on five-run agreement",
   "review_status": "closed-with-basis",
   "review_basis": "the census ranks by measured time share and fraction of peak; an LLM traffic estimate is weakest exactly on the cache-dependent kernels the census targets",
   "task_refs": []
  },
  "KS-K4-2": {
   "required_outcome": "measure prefill attention share at 32K-128K on C21 before any port",
   "review_status": "closed-with-basis",
   "review_basis": "measure the flash-attention share of CPU prefill only once a CPU-served role takes prompts of 32K tokens or more",
   "task_refs": []
  },
  "KS-K4-3": {
   "required_outcome": "reverse FA chunk order (expensive late rows first), then consider q-group loop inversion with 1 MB L2 sizing",
   "review_status": "closed-with-basis",
   "review_basis": "reverse the flash-attention chunk order, then consider query-group inversion, gated on that measurement",
   "task_refs": []
  },
  "KS-K4-1": {
   "required_outcome": "prototype Midmax in an experimental quantize_row_mxfp4_ref and KLD A/B vs floor when an MXFP4 requant is queued",
   "review_status": "closed-with-basis",
   "review_basis": "try the round-up E8M0 rule against floor, judged by KLD, when a BF16-to-MXFP4 requant is queued",
   "task_refs": []
  },
  "KS-S1-1": {
   "required_outcome": "We could replay a Pando-style full best-first tree (k-expansion per level, prune to N by cumulative lattice prob) against the current sibling-of-main builder on the existing 27B DFlash2 capture at T 0.3/1.0 and W 8/12/16 with V1 RRS verify",
   "review_status": "preserved",
   "review_basis": "Main review: DTREE-HEADROOM-REPLAY carries this outcome (No measured ceiling on tokens per pass exists for our captured target distributions, and the best-first tree shape of intake-2963 has never been replayed against our builder.)",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "DTREE-HEADROOM-REPLAY",
     "task_text": "- [ ] **DTREE-HEADROOM-REPLAY** [inference] Measure how much tree headroom is left on 27B DFlash2 by offline CPU replay of the retained dice.v1 capture ak-dice-capture-27b-dflash2-gpu-20261123-r2 (cap-L01.jsonl SHA-256 82d46a61a6d8f8b8088faece7935c5b8c10fd71c43bf3afa6db7941820d3a845): (a) the speed-of-light ceiling on tokens per verify pass from the captured target distributions at verifier budgets 8, 12 and 16 (intake-2973 bound; stochastic targets only, so T0.3 and T1.0), and (b) a Pando-style best-first tree (k children per level, pruned to N nodes by cumulative draft probability, intake-2963) under the V1 recursive-rejection tree verify, against served chain V0 and the current builder, same fit 0-31 / holdout 32-63 split as SPEC-DRAFT-SHARPEN. Model: Qwen3.8-27B Q8_0 + DFlash2 capture (no model load); tool: research scripts/kernel_rnd/dice_replay/ (V0 check must reproduce realized acceptance within 2%); region: one CPU quarter; est 3600 s (provisional); metric: holdout tokens per pass ratio to V0 with prompt-clustered 95% CI. Stop-on-answer at CI half-width <= 1%; stop-on-futility if the V0 check fails.",
     "acceptance": "RESULT.json with ceiling and tree ratios and a predeclared verdict; the decision is the verdict, not the run."
    }
   ]
  },
  "KS-S1-3": {
   "required_outcome": "We should record that noise-coupled or draw-informed tree shapes are lossless only with the target-sample walk; with RRS the tree must be blind to the verifier randomness",
   "review_status": "closed-with-basis",
   "review_basis": "noise-coupled tree shapes are lossless only with a target-sample walk, not with our rejection tree verify",
   "task_refs": []
  },
  "KS-S1-4": {
   "required_outcome": "We should not build noise coupling on DFlash2 or MTP trees",
   "review_status": "closed-with-basis",
   "review_basis": "noise coupling is not lossless under our recursive-rejection verifier, and the draw-informed selection replay already returned NULL on both lineup models",
   "task_refs": []
  },
  "KS-S1-2": {
   "required_outcome": "We could compute the x03 bound (mu, mu2 -> E[X] at P 8/12/16) per served T from the DICE capture target top-64 logits and compare it with measured tau",
   "review_status": "preserved",
   "review_basis": "Main review: DTREE-HEADROOM-REPLAY carries this outcome (No measured ceiling on tokens per pass exists for our captured target distributions, and the best-first tree shape of intake-2963 has never been replayed against our builder.)",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "DTREE-HEADROOM-REPLAY",
     "task_text": "- [ ] **DTREE-HEADROOM-REPLAY** [inference] Measure how much tree headroom is left on 27B DFlash2 by offline CPU replay of the retained dice.v1 capture ak-dice-capture-27b-dflash2-gpu-20261123-r2 (cap-L01.jsonl SHA-256 82d46a61a6d8f8b8088faece7935c5b8c10fd71c43bf3afa6db7941820d3a845): (a) the speed-of-light ceiling on tokens per verify pass from the captured target distributions at verifier budgets 8, 12 and 16 (intake-2973 bound; stochastic targets only, so T0.3 and T1.0), and (b) a Pando-style best-first tree (k children per level, pruned to N nodes by cumulative draft probability, intake-2963) under the V1 recursive-rejection tree verify, against served chain V0 and the current builder, same fit 0-31 / holdout 32-63 split as SPEC-DRAFT-SHARPEN. Model: Qwen3.8-27B Q8_0 + DFlash2 capture (no model load); tool: research scripts/kernel_rnd/dice_replay/ (V0 check must reproduce realized acceptance within 2%); region: one CPU quarter; est 3600 s (provisional); metric: holdout tokens per pass ratio to V0 with prompt-clustered 95% CI. Stop-on-answer at CI half-width <= 1%; stop-on-futility if the V0 check fails.",
     "acceptance": "RESULT.json with ceiling and tree ratios and a predeclared verdict; the decision is the verdict, not the run."
    }
   ]
  },
  "KS-S1-5": {
   "required_outcome": "We could check whether the UBTree Qwen3.8-27B selector or checkpoint is released and whether it drops into our DFlash2 lattice path (same low-rank bigram form, precomputed codebooks)",
   "review_status": "closed-with-basis",
   "review_basis": "probe a UBTree 27B selector only if one is released",
   "task_refs": []
  },
  "KS-S1-6": {
   "required_outcome": "At np>1 we should keep load-adaptive tree budgets that shrink to the chain, never a fixed large tree",
   "review_status": "closed-with-basis",
   "review_basis": "at more than one stream keep tree budgets load-adaptive, shrinking to the chain",
   "task_refs": []
  },
  "KS-S2-1": {
   "required_outcome": "cite SPEC-DRAFT-SHARPEN as the in-house answer for intake-2964; do not re-run a 27B DFlash2 draft-temperature sweep",
   "review_status": "closed-with-basis",
   "review_basis": "our own offline draft-sharpening replay already closed draft temperature on 27B DFlash2",
   "task_refs": []
  },
  "KS-S2-2": {
   "required_outcome": "run an offline CPU replay of A3B MTP draft softening/sharpening from the mtp_top top-10 logits in the A3B dice.v1 capture; stop on futility if best-T_d gain CI-upper < 1.02; only on a keep build a served MTP q in C21",
   "review_status": "closed-with-basis",
   "review_basis": "MTP verifies by sample-and-compare and its captured top-1 probability is about 0.997 or higher per depth, so softening has almost nothing to gain and would need a new served MTP distribution",
   "task_refs": []
  },
  "KS-S2-3": {
   "required_outcome": "record that SPEC-DISTS-TRUNC means dists capped to draft length, and the vocabulary truncation lever is the trunc arm of SPEC-DRAFT-SHARPEN",
   "review_status": "closed-with-basis",
   "review_basis": "record that the dists-truncation fix resizes draft distributions to the capped length; vocabulary truncation is the sharpening replay's trunc arm",
   "task_refs": []
  },
  "KS-S2-4": {
   "required_outcome": "attach the edge-acceptance calibration and price-ladder idea to the DTREE-GDN-BATCH reopen criteria",
   "review_status": "closed-with-basis",
   "review_basis": "attach TreeSpark's edge calibration and load-adaptive shrink to the batched-tree reopen criteria when a 16-node tree beats the chain",
   "task_refs": []
  },
  "KS-S2-5": {
   "required_outcome": "no action at np<=2; revisit only if we serve DFlash2 at np>=8 or a drafter share above 25% of the round",
   "review_status": "closed-with-basis",
   "review_basis": "ForeSpark's gain needs drafting to be a large share of the step at high load; ours is a small share at one or two streams",
   "task_refs": []
  },
  "KS-S3-1": {
   "required_outcome": "Monitor for a released DFlux/LEGOSpec checkpoint matching a served target (Qwen3.8-27B or Qwen3.8-Flash-Next); if one appears, add a DFlash2-vs-DFlux paired acceptance probe at served T on the MI210 under the DF2-CARD-CONFORMANCE-1 recipe.",
   "review_status": "closed-with-basis",
   "review_basis": "run a paired acceptance probe only if a DFlux checkpoint for a served target is released",
   "task_refs": []
  },
  "KS-S3-2": {
   "required_outcome": "Fold the training-recipe findings (hybrid SWA(512)x4+GQA backbone for long context; hierarchical KL(0.2)+D-PAL loss; 1.4M T=1 self-generated samples, Muon) into the DF2-FT-1 design notes as options, not as a plan.",
   "review_status": "closed-with-basis",
   "review_basis": "DFlux recipe options are inputs to the deferred drafter fine-tune, not a plan",
   "task_refs": []
  },
  "KS-S3-3": {
   "required_outcome": "Port-cost note for a future DFlux drafter in llama.cpp: C21 already has dflash conv kernel and selector rank/top_k keys (src/models/dflash.cpp:L141-L144 @ 98ff8a4) and per-layer SWA (src/models/dflash-dspark41.cpp:L164-L332 @ 98ff8a4); missing pieces are per-layer window=512 hybrid layout and the R-",
   "review_status": "closed-with-basis",
   "review_basis": "port-cost note; the C21 tree already has the DFlash conv, selector keys and per-layer SWA",
   "task_refs": []
  },
  "KS-S3-4": {
   "required_outcome": "No change to SPEC-GRAM-JSON-1 or the INF-83 D2 flip; add a one-line note that GramDelta (intake-2966) addresses mid-request grammar growth only, which no served role does, and its static K=0 table shows no llguidance-vs-XGrammar steady-state difference.",
   "review_status": "closed-with-basis",
   "review_basis": "GramDelta does not bear on the grammar-share measurement or the llguidance default flip",
   "task_refs": []
  },
  "KS-S3-5": {
   "required_outcome": "Re-open only if a role starts discovering tools or schemas progressively inside one request (BFCL-like growing tool list); then price per-update llguidance matcher rebuild (about 50 ms on their GPU harness) against our turn count.",
   "review_status": "closed-with-basis",
   "review_basis": "price per-update matcher rebuilds only if a role starts growing its grammar inside one request",
   "task_refs": []
  },
  "KS-M1-1": {
   "required_outcome": "we should add a claimed-mechanism witness (counter name, direction, A/A band) to AK row specs and ak_row_lint, downgrading KEEP_CANDIDATE to INCONCLUSIVE when it does not move",
   "review_status": "preserved",
   "review_basis": "Main review: AK-MECH-WITNESS-1 carries this outcome (Rows record A/A and knob-honoured witnesses but not a counter for the claimed mechanism, so a keep can rest on an unverified story.)",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-MECH-WITNESS-1",
     "task_text": "- [ ] **AK-MECH-WITNESS-1** [non-inference] Add a warn-first claimed-mechanism witness to AutoKernel rows: a row spec whose decision rule can return a keep or pass on a speed claim declares mechanism_witness {counter, direction, aa_band} (the per-row form of mechanism_prediction.expected_counter_changes, autokernel-loop.md L1605-L1608), and ak_row_lint.py warns MECH-UNWITNESSED when the field is missing or the row's RESULT does not record that counter for both arms; today NO-WITNESS (ak_row_lint.py L39, L680-L682) checks only that a named knob took effect, and Q8-W8 design 4 cut static instructions per byte 3x yet ran 2-3x slower, a cause found only after the fact (intake-2958, intake-2977, intake-2979)",
     "acceptance": "Lint test covers missing witness, missing counter and compliant rows; warn-only."
    }
   ]
  },
  "KS-M1-2": {
   "required_outcome": "we could scan the stored keep and drop rows for stated mechanism versus a counter that would have tested it (zero compute)",
   "review_status": "closed-with-basis",
   "review_basis": "scan stored keep and drop rows for stated mechanism versus counter once the witness lint lands",
   "task_refs": []
  },
  "KS-M1-5": {
   "required_outcome": "no change; our identity and re-measure gates already cover this lesson",
   "review_status": "closed-with-basis",
   "review_basis": "our identity and re-measure gates already cover the merged-not-measured lesson",
   "task_refs": []
  },
  "KS-M1-3": {
   "required_outcome": "we should fail the template review gate and registry validation when a served template reads strftime_now, date_string or datetime without a pinned date_string, and record template_date_dependent in eval provenance",
   "review_status": "preserved",
   "review_basis": "Main review: EV-DATE-PIN-1 carries this outcome (Nothing records whether a served template reads the date, and nothing pins it; served templates read no date today only by accident.)",
   "task_refs": [
    {
     "owner": "handoffs/active/eval-tower-program.md",
     "task_id": "EV-DATE-PIN-1",
     "task_text": "- [ ] **EV-DATE-PIN-1** [non-inference] Make the system-prompt date a recorded, pinnable eval input: template_provenance.py (epyc-orchestrator scripts/validate/template_provenance.py @ faa783c7) records template_reads_date true when the effective template references strftime_now, date_string or a datetime value, and registry validation warns on any served or eval role whose template reads the date without a pinned date_string in its request kwargs; llama-server fills date_string from the wall clock (common/chat.cpp L2573-L2581 @ 98ff8a4) and a request can override it through chat_template_kwargs (L2747-L2750), and two plausible dates flip a median 6.6% of items with none of 11 eval stacks pinning it (intake-2967, intake-2972)",
     "acceptance": "Provenance test covers date-reading and date-free templates and every served role's plan row carries the flag."
    }
   ]
  },
  "KS-M1-4": {
   "required_outcome": "we should run a zero-compute probe asking the Claude judge path for today date with an empty system prompt",
   "review_status": "closed-with-basis",
   "review_basis": "asking the judge model for today's date cannot show whether a provider injects one; the guard on templates plus recorded request kwargs is the evidence that can",
   "task_refs": []
  },
  "KS-M1-6": {
   "required_outcome": "no extra action beyond KS-M1-perfclaims-date-3 and -4",
   "review_status": "closed-with-basis",
   "review_basis": "the second date paper corroborates the first and adds no action",
   "task_refs": []
  },
  "KS-M2-1": {
   "required_outcome": "build an offline distortion-score grader (summary-vs-full-context sampled-token KL on the same local Qwen) and validate it against TOC-CMP-4 blocked actions with a no-summary arm",
   "review_status": "closed-with-basis",
   "review_basis": "add the behavior-distortion score as a secondary compaction metric when the compaction A/B files its first complete paired result",
   "task_refs": []
  },
  "KS-M2-2": {
   "required_outcome": "add the three printed effort instruction texts and Qwen3.8 native low/medium/xhigh as E-2 rungs and measure tier ordering on REPL/agentic tasks as well as GPQA",
   "review_status": "closed-with-basis",
   "review_basis": "add the effort instruction rungs when the effort curve is booked",
   "task_refs": []
  },
  "KS-M2-3": {
   "required_outcome": "gate any future approximate indexer top-k on teacher-forced KL-vs-exact plus the m^2/2 top-1 certificate beside greedy identity",
   "review_status": "closed-with-basis",
   "review_basis": "gate any future approximate indexer top-k on KL against the exact set plus discarded mass",
   "task_refs": []
  },
  "KS-M2-4": {
   "required_outcome": "add dense-reference KL as a second metric in EA-POOL-SCREEN arms",
   "review_status": "closed-with-basis",
   "review_basis": "rank near-tied eviction arms by KL against the full-cache arm if the screen leaves two or more within 3 items",
   "task_refs": []
  },
  "KS-M2-5": {
   "required_outcome": "use SwapCert as a KV-eviction quality gate",
   "review_status": "closed-with-basis",
   "review_basis": "SwapCert needs one partial forward per candidate swap per head, so it is a sampled diagnostic, not a gate",
   "task_refs": []
  },
  "KS-W2A-1": {
   "required_outcome": "add OAS/Midmax or an MSE choice of {e,e+1} to the experimental MXFP4 quantizer and judge by KLD, when a BF16 to MXFP4 requant is scheduled",
   "review_status": "closed-with-basis",
   "review_basis": "same trigger as the round-up E8M0 rule (one rule under two names)",
   "task_refs": []
  },
  "KS-W2A-2": {
   "required_outcome": "cite OAS and Midmax as one rule; never carry +2.8 as weight-only",
   "review_status": "closed-with-basis",
   "review_basis": "cite Overflow-Aware Scaling and the PDF-only entry's rule as one rule; the verified gains are W4A4, not weight-only",
   "task_refs": []
  },
  "KS-W2A-3": {
   "required_outcome": "do not pursue MBS or block-16 MXFP4 types now",
   "review_status": "closed-with-basis",
   "review_basis": "macro-block scaling and block-16 types would be new GGUF types for no served model",
   "task_refs": []
  },
  "KS-W2A-4": {
   "required_outcome": "consider an ak_row_lint check that a row claiming a mechanism records a counter or A/A key, and an evidence-type enum with an M0 (unnamed gain) catch",
   "review_status": "preserved",
   "review_basis": "Main review: AK-MECH-WITNESS-1 carries this outcome (Rows record A/A and knob-honoured witnesses but not a counter for the claimed mechanism, so a keep can rest on an unverified story.)",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-MECH-WITNESS-1",
     "task_text": "- [ ] **AK-MECH-WITNESS-1** [non-inference] Add a warn-first claimed-mechanism witness to AutoKernel rows: a row spec whose decision rule can return a keep or pass on a speed claim declares mechanism_witness {counter, direction, aa_band} (the per-row form of mechanism_prediction.expected_counter_changes, autokernel-loop.md L1605-L1608), and ak_row_lint.py warns MECH-UNWITNESSED when the field is missing or the row's RESULT does not record that counter for both arms; today NO-WITNESS (ak_row_lint.py L39, L680-L682) checks only that a named knob took effect, and Q8-W8 design 4 cut static instructions per byte 3x yet ran 2-3x slower, a cause found only after the fact (intake-2958, intake-2977, intake-2979)",
     "acceptance": "Lint test covers missing witness, missing counter and compliant rows; warn-only."
    }
   ]
  },
  "KS-W2A-5": {
   "required_outcome": "cite intake-2979 for reporting statistics only",
   "review_status": "closed-with-basis",
   "review_basis": "cite the PR study for reporting statistics only; it never executes the code",
   "task_refs": []
  },
  "KS-W2B-3": {
   "required_outcome": "Do not build the certified-sampling kernel now; revisit only if a per-call error guarantee is required",
   "review_status": "closed-with-basis",
   "review_basis": "the certified-sampling kernel needs a 4-bit scan of every key and certifies a sampler, not a kept set; no near-term consumer",
   "task_refs": []
  },
  "KS-W2B-1": {
   "required_outcome": "Add an offline attention-mass-captured (tau) and tau*||mu_tail-mu_head|| diagnostic to the evidence for any future approximate or lower-precision Q38FN indexer; exact-set greedy identity stays the pass criterion",
   "review_status": "closed-with-basis",
   "review_basis": "same trigger as the approximate-indexer gate",
   "task_refs": []
  },
  "KS-W2B-2": {
   "required_outcome": "Log tau on held-out queries beside the EA-POOL-SCREEN task scores to separate scorer resolution from eviction mechanics",
   "review_status": "closed-with-basis",
   "review_basis": "same trigger as the near-tied eviction arms",
   "task_refs": []
  },
  "KS-W2B-4": {
   "required_outcome": "Use the head/tail value-mean gap from one dense pass as a first-order screen before paying K(M-K) partial forwards for SwapCert-style joint-support audits",
   "review_status": "closed-with-basis",
   "review_basis": "the value-mean gap is a cheap first screen before any one-swap audit",
   "task_refs": []
  }
 },
 "proposed_tasks": [
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **AK-MMQ-SK2-CENSUS** [non-inference] Finish the AK-MMQ-SK2 step-2 served-shape census, the one item that keeps that box open: take the dense Qwen3.8-27B Q8_0 tile table already worked out in research/deep-dives/intake-kspec-1125/dive-K1-streamk-order.md (np4 verify M=36 picks J=48 so one column tile per tensor; Q8_0 above 128 columns is routed to rocBLAS by mmq.cu L346-L362 @ 98ff8a4), add the A3B Q8_0 MUL_MAT_ID shapes above the MMVQ cap and the Q4_K/Q6_K 5-128-row shapes from the C21 code, and record per shape the tile count against the 104 stream-k blocks, where force-tiling fires and where the grid cap changes the grid; zero compute (intake-2956, intake-2971)"
  },
  {
   "owner": "handoffs/active/rocm-kernel-authoring.md",
   "task_text": "- [ ] **VKRC-BYTES-PLAUSIBLE** [non-inference] Add a deterministic bytes plausibility check to the verify-kernel roofline census extraction (epyc-inference-research scripts/kernel_rnd/autokernel/loop/census_extract.py extract_verify_roofline @ 4ca0d0d9a) before VERIFY-KERNEL-ROOFLINE-CENSUS-1 r2 is read: flag every kernel row whose FETCH_SIZE+WRITE_SIZE-derived GB/s exceeds the HBM peak the census uses, or whose bytes per call differ from the analytic footprint (weight or tensor bytes x launches) by more than 2x, and print the flagged rows beside the ranking; no LLM estimate (intake-2960: LLM device-memory traffic estimates are the weak half, within 1.20x in 36-40% of cases)"
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **AK-MECH-WITNESS-1** [non-inference] Add a warn-first claimed-mechanism witness to AutoKernel rows: a row spec whose decision rule can return a keep or pass on a speed claim declares mechanism_witness {counter, direction, aa_band} (the per-row form of mechanism_prediction.expected_counter_changes, autokernel-loop.md L1605-L1608), and ak_row_lint.py warns MECH-UNWITNESSED when the field is missing or the row's RESULT does not record that counter for both arms; today NO-WITNESS (ak_row_lint.py L39, L680-L682) checks only that a named knob took effect, and Q8-W8 design 4 cut static instructions per byte 3x yet ran 2-3x slower, a cause found only after the fact (intake-2958, intake-2977, intake-2979)"
  },
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **DTREE-HEADROOM-REPLAY** [inference] Measure how much tree headroom is left on 27B DFlash2 by offline CPU replay of the retained dice.v1 capture ak-dice-capture-27b-dflash2-gpu-20261123-r2 (cap-L01.jsonl SHA-256 82d46a61a6d8f8b8088faece7935c5b8c10fd71c43bf3afa6db7941820d3a845): (a) the speed-of-light ceiling on tokens per verify pass from the captured target distributions at verifier budgets 8, 12 and 16 (intake-2973 bound; stochastic targets only, so T0.3 and T1.0), and (b) a Pando-style best-first tree (k children per level, pruned to N nodes by cumulative draft probability, intake-2963) under the V1 recursive-rejection tree verify, against served chain V0 and the current builder, same fit 0-31 / holdout 32-63 split as SPEC-DRAFT-SHARPEN. Model: Qwen3.8-27B Q8_0 + DFlash2 capture (no model load); tool: research scripts/kernel_rnd/dice_replay/ (V0 check must reproduce realized acceptance within 2%); region: one CPU quarter; est 3600 s (provisional); metric: holdout tokens per pass ratio to V0 with prompt-clustered 95% CI. Stop-on-answer at CI half-width <= 1%; stop-on-futility if the V0 check fails."
  },
  {
   "owner": "handoffs/active/eval-tower-program.md",
   "task_text": "- [ ] **EV-DATE-PIN-1** [non-inference] Make the system-prompt date a recorded, pinnable eval input: template_provenance.py (epyc-orchestrator scripts/validate/template_provenance.py @ faa783c7) records template_reads_date true when the effective template references strftime_now, date_string or a datetime value, and registry validation warns on any served or eval role whose template reads the date without a pinned date_string in its request kwargs; llama-server fills date_string from the wall clock (common/chat.cpp L2573-L2581 @ 98ff8a4) and a request can override it through chat_template_kwargs (L2747-L2750), and two plausible dates flip a median 6.6% of items with none of 11 eval stacks pinning it (intake-2967, intake-2972)"
  }
 ]
}
```

Correction 2026-11-25 (status audit): the "monitor until DTREE-GDN-BATCH reopens" routing for TreeSpark (intake-2975, KS-S2-draft-calibration-4 / KS-S2-4, M2 trigger b) rested on the premise that trees are parked. That was wrong at write time: the C21 sampled tree (V2 RRS) was already KEEP at official T1 (row ak-c21-tree-official-gpu-20261124: T10 1.0303 [1.0223,1.0433], T16 1.0352 [1.0189,1.0614]; progress/2026-11/2026-11-24-handoff-df2.md:45). The DTREE-GDN-BATCH box is open pending the C20 fold decision (its GDN row is KEEP, 3.619 ms), not parked. New disposition: fold TreeSpark's edge-acceptance Platt calibration and load-adaptive shrink-to-chain in as arms of DTREE-HEADROOM-REPLAY (handoffs/active/speculative-decoding.md) instead of a monitor. History above is kept unchanged.

Correction 2026-11-25 (status audit): scope note for VKRC-BYTES-PLAUSIBLE (KS-K3-3): the plausibility check must also be applied retroactively to the already-filed census r2 table (ak-27b-verify-kernel-roofline-census-gpu-20261124-r2), which Q8-MULTICOL-GEMV-1 rests on. The retro-check is being run by workspace-f2.
