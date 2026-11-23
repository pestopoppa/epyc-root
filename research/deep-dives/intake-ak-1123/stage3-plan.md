# Stage-3 plan — HIP ISA/MMQ PRs, AITER v0.1.30, BPE, spec-decoding, context and harness papers (intake-ak-1123) — REVISION 1, APPROVED 2026-11-23 (OD-5 = C)

## Revision 1 (operator review 2026-11-23)

- New box SPEC-DTREE-DICE (P7): step 1 logs and measures the sampled (T > 0) share of served traffic; step 2 replays DICE node selection offline. The existing DTREE dumps are greedy with no target probabilities, so step 2a captures first (A3B MTP on a CPU quarter; 27B DFlash2 is an MI210 capture-only row, OD-5). The falsifier compares Gumbel-max coupling with pre-sampled randomness (V2, V3) against our rejection sampling (V0) and recursive rejection on the same tree (V1), with a futility rule; a GPU build row only on replay gains.
- K1 rewritten: the 1 - TV result (intake-2845) is a single-draft, per-position bound. It does not cover tree or multi-candidate verification, where k-candidate verifiers beat the standard one at T > 0 (intake-2846#02, intake-2715#00). Production serves at T > 0 (role defaults 0.1-0.3; :8083 direct agent traffic at 1.0), so T = 0 parity closes nothing. AKI-51/52 now map to SPEC-DTREE-DICE; M6 keeps only the calibration refit (AKI-68); multi-draft verifiers moved out of the AKI-54 decline into SPEC-DTREE-DICE (AKI-69); Stage 4 appends a scope line to intake-2845.
- SPEC-COUPLE-MTP-1 corrected: MTP at T > 0 is sample-and-compare against an argmax draft (common/sampling.cpp:693-711 @ a6a32c1), not rejection sampling, so the box stays open; it now tests routing MTP through the rejection path with a softmax top-10 draft, at every served T including 1.0, on the shared capture.
- AITER v0.1.30 reverse-engineered for gfx90a (source @ 77ba72b7061a, diffed against the 2026-11-05 clone): new P10 with AK-BW-GDN-GATE-FOLD (GDN beta/alpha projection and gate fold, about 1.5-2.5 ms of a 40.07 ms 27B verify in the C18 trace) and AK-ASM-I8GEMM-PERCHANNEL-GEMV (unmeasured verify half of the per-channel int8 lever, low confidence); AKI-23 upgraded from knowledge to AK-BW-GDN-GATE-FOLD; K4 replaced; other families declined (AKI-72).
- Operator answers OD-1 A, OD-2 B, OD-3 A, OD-4 A recorded (session file, e64c3bc13); new decision OD-5.

Entries intake-2824..intake-2862 (39): 13 submitted, 23 in Stage-2b wave 1, 3 in wave 2 (wave 2 surfaced nothing further, so the close-out gate is closed). 37 dive-verified; intake-2830 (Vega-Fafnir) and intake-2848 (ReTrace) are PDF-only and stay stage1-unverified, so no number or mechanism from them is used below. Subagents: 3 opus (MMQ dive, spec-decoding dive, determinism wave), 8 sonnet (dives and waves), 3 haiku/low (second readers over 409 anchors: 147 yes, 244 partial, 18 no; partials are mostly multi-part claims with one anchor per part). No compute was used; every [inference] box is a separately booked row.

## Per-source verdicts

| Entry | Source | Verdict | Relevance | Note |
|---|---|---|---|---|
| intake-2824 | PR #32837 CDNA MMQ without stream-k | worth_investigating | medium | Predicate is GCN or any CDNA, so gfx90a takes it (steering said gfx908 only); MI100 numbers only |
| intake-2825 | PR #32839 readlane | worth_investigating | low | Only one served uniform-lane site (mmid.cu:92); topk/GDN hunks absent in our tree |
| intake-2826 | PR #32840 ballot reduce (draft) | worth_investigating | low | Needs wrappers we lack; only prefill mask kernel is reachable |
| intake-2827 | PR #32841 mbcnt rank | worth_investigating | low | Code owner pushback; no site in our tree |
| intake-2828 | AITER v0.1.30 | adopt_patterns | medium | gfx942/gfx950 wheels; zero-timing and provider-record patterns adopted; source reverse-engineered: GDN gate fold and per-channel verify GEMV filed (P10) |
| intake-2829 | PR #32859 BPE | worth_investigating | low | Hardware not stated; under 0.1% of cold prefill |
| intake-2830 | Vega-Fafnir | adopt_patterns | high | PDF-only, stage1-unverified; cited only as #record |
| intake-2831 | DICE | worth_investigating | medium | H200; gain grows with T and is zero at T=0; lossless needs Gumbel-max target sampling; open for trees under SPEC-DTREE-DICE |
| intake-2832 | CoPyro | worth_investigating | medium | Needs drafter retraining; no training-free result |
| intake-2833 | Contexture | adopt_patterns | high | Supersession rule and cold-commit cost model; headline numbers narrowed |
| intake-2834 | CreditFilter | worth_investigating | low | Qwen3-8B-Base only; needs an RL lane we do not have |
| intake-2835 | ADAPT | adopt_patterns | medium | Priced asks; headline baselines narrowed |
| intake-2836 | HookEvo | adopt_patterns | medium | In-sample retention; margins within noise vs Life-Harness |
| intake-2837 | PR #30022 | adopt_patterns | medium | Force-tiling origin; GCN-gated; no CDNA gain per its author |
| intake-2838 | PR #30553 | adopt_patterns | low | Cap is a no-op on our dense served shapes |
| intake-2839 | AITER RFC #7240 + #7654/#8081 | adopt_patterns | medium | Decision record; all-or-none latency report |
| intake-2840 | AITER #7700 | adopt_patterns | medium | Planner and one-partition skip are dtype-agnostic |
| intake-2841 | AMD-AGI/AKLR | adopt_patterns | medium | All kernels gfx950; qualification and provenance patterns |
| intake-2842 | VERGE | worth_investigating | medium | Abstract only; anchorable divergence rate |
| intake-2843 | LLM-42 | adopt_patterns | medium | No-atomics premise fails on MI210 paths |
| intake-2844 | Batch spec forensics | adopt_patterns | medium | 95% at batch 8 overturned for v4; cache-drift signature |
| intake-2845 | Daliri coupling | adopt_patterns | low | Coupling cannot beat 1-TV per position for a single draft; trees not covered |
| intake-2846 | Kobus ERSD | already_integrated | low | Standard verifier optimal for single drafts; race verifier wins for k >= 3 (tree arm V4) |
| intake-2847 | SAM-Decoding | worth_investigating | low | ngram-mod is not an equivalent index |
| intake-2848 | ReTrace | worth_investigating | medium | PDF-only, stage1-unverified |
| intake-2849 | Leyline | adopt_patterns | medium | MLA-only; hybrids cannot use it |
| intake-2850 | SmoothAgent | adopt_patterns | medium | Hides re-prefill in slack; slack is short for supersession |
| intake-2851 | TokenPilot | adopt_patterns | medium | Savings mostly from prefix stabilisation |
| intake-2852 | Pichay | adopt_patterns | medium | 93% overturned (thrashing artefact) |
| intake-2853 | AgentDiet | adopt_patterns | high | Unconfounded cost 21-27%; trajectories released |
| intake-2854 | CreditFilter repo | worth_investigating | low | NVIDIA-only as shipped |
| intake-2855 | R2V | adopt_patterns | medium | No code; entropy never escalates on TextWorld |
| intake-2856 | AgentRL | worth_investigating | low | ADAPT's RL-only collapse is a tuning artefact |
| intake-2857 | HookEvo repo | adopt_patterns | medium | Configs do not reproduce headline runs |
| intake-2858 | Life-Harness | adopt_patterns | medium | Same-batch strict improvement; fresh incumbent |
| intake-2859 | PluginRSI | adopt_patterns | medium | Admission vs cached parent biases toward admit |
| intake-2860 | THUDM/AgentBench | adopt_component | medium | ALFWorld needs no Redis; driver must speak tool_calls |
| intake-2861 | Life-Harness repo | adopt_patterns | medium | Improver hardwired; loopback proxy route |
| intake-2862 | PluginRSI repo | adopt_patterns | medium | Manifest and status split read from code |

## Work packets

| Packet | Action | Owner | Boxes |
|---|---|---|---|
| P1 | Width-aware identity gates: ragged-rollback test, protocol and A/A noise floor | handoffs/active/speculative-decoding.md | SPEC-ID-RAGGED-1, SPEC-ID-GATE-1, SPEC-ID-NOISE-1, GGML-DET-POSINV-TEST |
| P2 | Port the stream-k cap and force-tiling rule to CDNA behind a default-off knob and screen it on gfx90a | handoffs/active/autokernel-loop.md | AK-MMQ-SK2 |
| P3 | AutoKernel timing and receipt hygiene plus a dispatch decision-record spec | handoffs/active/autokernel-loop.md | AK-TIMING-ZERO-1, AK-RECEIPT-ARMS-1, RKA-DECISION-RECORD-1 |
| P4 | Measure supersession share offline and build an evict-cost probe before any eviction arm | handoffs/active/context-and-token-economy.md | TOC-SUPERSEDE-1, KV-EVICT-COST-1 |
| P5 | Calibrate ask/escalation from logs: counts, residual-risk probe, budget-priced penalty | handoffs/active/routing-program.md | RTG-ASK-1 |
| P6 | Harden harness-evolution acceptance (disjoint tasks, fresh parent, sealed test, decision records) | handoffs/active/autopilot-program.md | AP-BSV2-ACCEPT-RIGOR, HIL-EVO-CASES-1 |
| P7 | Offline screens before copy-proposal, coupled-draw and sampled-tree (DICE) drafter work | handoffs/active/speculative-decoding.md | SPEC-COPY-COV-1, SPEC-COUPLE-MTP-1, SPEC-DTREE-DICE |
| P10 | AITER v0.1.30 reverse-engineering for gfx90a: GDN gate fold and per-channel int8 verify GEMV | handoffs/active/autokernel-loop.md | AK-BW-GDN-GATE-FOLD, AK-ASM-I8GEMM-PERCHANNEL-GEMV |
| P9 | Fix the stale DGX premise | handoffs/active/eval-tower-program.md | EVT-DGX-PREMISE-FIX |
| P8 | Small kernel/host follow-ups: readlane arm, trace shares, tokenizer timing | handoffs/active/kernel-champion-and-promotion.md | MMID-HELPER-READLANE, RKA-TRACE-SHARES-1, TOK-BPE-TIME-1 |

Ten packets: nine independent units (different owners, no shared code) plus P9, a one-line text fix; none was split to reach a target and none could be merged without mixing owners. Safe concurrency: P3, P4, P5, P6, P7 (SPEC-COPY-COV-1, SPEC-DTREE-DICE step 1), P10 step 1 and P8 (RKA-TRACE-SHARES-1, TOK-BPE-TIME-1) are independent code/doc work. Ordered: SPEC-ID-RAGGED-1 before the C18 bisect row; SPEC-ID-GATE-1 before SPEC-ID-NOISE-1 is judged; AK-MMQ-SK2 step 1 before step 3; MMID-HELPER-READLANE before the MMID-HELPER-N10-GATE row runs.

Minimum rigor: the measurement boxes (SPEC-ID-NOISE-1, AK-MMQ-SK2 step 3, TOC-SUPERSEDE-1, RTG-ASK-1, SPEC-COUPLE-MTP-1) state the six controls (frozen input with digest, incumbent baseline, per-item outputs, holdout, complete denominator, predeclared rule) and stop-on-answer / stop-on-futility rules; formal-gate cells are futility-only. KV-EVICT-COST-1's smoke is a deterministic conformance check (19/20 exact token counts), so holdout is replaced by synthetic cuts not used to fit a + b x cells. Code boxes (SPEC-ID-RAGGED-1, GGML-DET-POSINV-TEST, AK-TIMING-ZERO-1, AK-RECEIPT-ARMS-1) replace the empirical controls with red/green tests and mutation cases (0, -1, NaN, inf; missing arm; partial block). Doc boxes (SPEC-ID-GATE-1, RKA-DECISION-RECORD-1, HIL-EVO-CASES-1) have no empirical step.

Consumer discovery (searched: lane handoffs, epyc-inference-research loop/, llama.cpp C19 a6a32c1, orchestrator src/ and orchestration/): AK-RECEIPT-ARMS-1 consumers are run.py and bench.py (direct), surface_fold.py (evidence) and kernel-champion-and-promotion.md fold gates (policy); SPEC-ID-GATE-1 consumers are CAFE-1/CAFE-3, DF2-12.1, C18-REPLAY-Q4X-CONC-BISECT (policy); KV-EVICT-COST-1 consumers are TOC-CMP-4 (prospective via M2) and KPF-62 (prospective via M3). No consumer gets a duplicate task.

## Operator decisions (each blocks only its own item)

- **OD-1** (ANSWERED 2026-11-23: A) — Open a post-training lane on the MI210? Context: CreditFilter (intake-2834) and AgentRL (intake-2856) both need a pinned gfx90a training env; the only MI210 training box (model-evaluation-queue.md:1259) is marked declined by the ws58 content-review as 'training, out of scope' and countermanded until E5 Stage-B releases the host. Options: (A, recommended) reopen the smoke as a pinned-env build after E5 Stage-B, 0.6B then 1.7B, CreditFilter off/on, 3 steps, no quality claim; (B) keep training out of scope and mark intake-2834/2854 knowledge-only; (C) reopen now on CPU unit tests only (no GPU).
- **OD-2** (ANSWERED 2026-11-23: B) — Extend the 2026-10-22 HIL-6 pilot-only loop allowance to one Life-Harness evolve-from-scratch run (6 rounds, ALFWorld, local improver behind a loopback proxy, about 710 solver episodes) and the ALFWorld-only AgentBench smoke? Options: (A) yes, as two booked rows; (B, recommended until P6 lands) no, revisit after AP-BSV2-ACCEPT-RIGOR so the run uses the hardened accept rule.
- **OD-3** (ANSWERED 2026-11-23: A) — Approve the lineage_capture producer at keep_the_diff behind a default-off flag (module comment requires operator approval)? Options: (A, recommended) approve default-off; (B) keep unwired.
- **OD-5** (ANSWERED 2026-11-23: C) — SPEC-DTREE-DICE step 2a: the existing DTREE dumps are greedy with no target probabilities, so the offline replay needs a capture first. The A3B MTP capture runs on a CPU quarter; the 27B DFlash2 capture needs one MI210 capture-only row (no timing claim) before any replay gain exists, which departs from 'GPU row only on replay gains'. Options: (A, recommended) allow the 27B capture-only MI210 row only after the A3B CPU replay is not futile; (B) A3B only, no 27B capture until a further decision; (C) allow both captures now.
- **OD-4** (ANSWERED 2026-11-23: A) — Second-reader disagreements: 18 of 409 anchors were judged 'no' (quote does not support its claim): intake-2825#4, 2826#2, 2834#4, 2835#4, 2836#3, 2837#2, 2840#1, 2841#3, 2844#0, 2846#2, 2850#3, 2852#4, 2854#4, 2855#4, 2857#2, 2857#3, 2857#5, 2859#1. Several are in-house-state claims an external quote cannot carry. Options: (A, recommended) at Stage 4, drop those 18 anchors from claim_anchors (claims stay, unanchored at that index) and cite only anchored claims; (B) leave as is.

## Monitors and knowledge-only (durable prose, no checkbox)

| Packet | Owner | Trigger / basis |
|---|---|---|
| M1 | handoffs/active/autokernel-loop.md | AK-MMQ-SK2 KEEP_CANDIDATE fires an end-to-end 27B np4 aggregate and A3B pp512 (ub 64 and 512) row in speculative-decoding.md; if arm B's only ISA failures are AGPR classes, timing B needs the same operator waiver AK-MMQ-H5 needed. |
| M2 | handoffs/active/context-and-token-economy.md | TOC-SUPERSEDE-1 share >= 15% fires: add a supersession arm and an exploratory step_reduce arm (AgentDiet a=2, b=1) to the full TOC-CMP-4 pre-registration; the frozen pilot96 matrix is untouched. |
| M3 | handoffs/active/kv-cache-program.md | When KPF-62.6 runs its G3 harness, add a removed-span case (Leyline forget versus amortize) for dense-attention roles only; a default-off kv_splice request field follows only if that case passes. Rotate-only splice for GDN hybrids is declined. |
| M4 | handoffs/active/routing-program.md | RTG-ASK-1 probe beating entropy-only by >= 0.05 AUROC on holdout fires J17 ask-calibration readouts (entropy-only, heuristic, oracle-timing ceiling) in eval-tower-program.md and a design note for a trained ask policy costed from consultant_device_seconds. |
| M5 | handoffs/active/speculative-decoding.md | SPEC-COPY-COV-1 above threshold fires: an exact longest-match index as the proposal source for a default-off training-free copy-proposal probe on the DFlash2 weights (one GPU row), and a CoPyro arm in DF2-FT-1. |
| M6 | handoffs/active/speculative-decoding.md | DTREE-GDN-BATCH making T16 beat linear fires: a first-order DTREE acceptance-calibration refit on the dump (intake-2846). The DICE sampled-tree question is no longer gated here; it is SPEC-DTREE-DICE. |
| M7 | handoffs/active/speculative-decoding.md | intake-2848#record (ReTrace) and intake-2830#record (Vega-Fafnir) are PDF-only and stage1-unverified; when an HTML render appears or an operator hand-check passes, re-dive and reconsider a rejected-trajectory arm in DF2-FT-1 and the cache-rebuild findings. |
| M8 | handoffs/active/kernel-champion-and-promotion.md | At MMID-HELPER-N10-GATE close, if the helper is still >= 3% of Q38FN pp2048 after the fold, port the mbcnt-based ballot rank (#32841 shape) to any ballot site that remains. |
| M9 | handoffs/active/model-evaluation-queue.md | MI210 post-training smoke (gfx90a venv, CreditFilter and AgentRL as consumers) waits on OD-1 and on E5 Stage-B releasing the host (the box at model-evaluation-queue.md:1259 is countermanded until then). |
| M10 | handoffs/active/eval-tower-program.md | Operator approval of OD-2 fires the ALFWorld-only AgentBench smoke (AgentRL controller plus one worker, no Redis, local role via llama-server tool calls, 5 episodes) and the Life-Harness local-improver run. |
| M13 | handoffs/active/autokernel-loop.md | Operator approval of OD-3 fires: wire lineage_capture at keep_the_diff behind a default-off flag. |
| M11 | handoffs/active/context-and-token-economy.md | When RTE-LOG-1 (harness-program.md:519) lands prompt-structure logs: prefix-stability audit over all block kinds and a counterfactual batching B in {1,3,5} for the clearing pass. |
| M12 | handoffs/active/memory-program.md | When the M-23 SkillBank A/B is next booked: add an executable-guard arm beside the text-skill arm (HookEvo scope C finding). |
| K1 | handoffs/active/speculative-decoding.md | The 1 - TV ceiling (intake-2845#record) is a single-draft, per-position bound. It closes coupled-draw verification only on single-path chains, where the served DFlash2 rejection path at T > 0 already reaches it (common/sampling.cpp:1020-1128 @ a6a32c1). It does not close tree or multi-candidate verification, where k-candidate verifiers beat the standard one at T > 0 (intake-2846#02, intake-2715#00), so DICE on DFlash2/MTP trees at served T is open under SPEC-DTREE-DICE. Production serves at T > 0 (role defaults 0.1-0.3; :8083 direct agent traffic at 1.0), so 'no gain at T = 0' closes nothing. SPEC-RNG.1 DO-NOT-CARRY still records the keyed-RNG drafter-invariance variant. |
| K2 | handoffs/active/autokernel-loop.md | #30022's own author found no CDNA gain and #30553's cap is a no-op on our dense served shapes (nwork 160-2720 versus 104 blocks); both are inputs to AK-MMQ-SK2, not separate ports. |
| K3 | handoffs/active/context-and-token-economy.md | Contexture's +20-73% headline and energy figure are H100/H200 vLLM numbers and do not transfer; only the supersession rule and the cold-commit cost model are used. |
| K4 | handoffs/active/autokernel-loop.md | AITER v0.1.30's wheels and new kernels target gfx942/gfx950/gfx1250, and every CDNA2-portable family was already retargeted and timed on the MI210 (AK-ASM-H1..H15, AK-ASM-PORT-*, AK-MMID-MF, C8-6); its split-K reduce widening was tried as GGML_HIP_FA_TAIL_SPLIT (FUTILITY). The new served-path ideas are its GDN input fold and per-channel int8 weights, filed as AK-BW-GDN-GATE-FOLD and AK-ASM-I8GEMM-PERCHANNEL-GEMV; FP8/MX/NVFP4, MLA, gfx950 MTP4 tiles and kernarg preload do not map to gfx90a. |
| K6 | handoffs/active/vidya-belief-substrate-program.md | Second-reader disagreements: 18 of 409 anchors judged no (listed in OD-4); never auto-overturned. |
| K5 | handoffs/active/model-evaluation-queue.md | CreditFilter's gains are single-turn math, full-parameter RL on Qwen3-8B-Base, three data-order seeds, MATH500 margin carried by one collapsed DAPO run (intake-2834). |

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| AKI-01 | intake-2844 dive (B1) + intake-2830 A4 | Write test-multiseq-ragged-rollback before booking the C18 bisect | P1 / SPEC-ID-RAGGED-1 |
| AKI-02 | intake-2830 A2/A3 + intake-2842 V1/V2 + intake-2844 B2/B3 | Width-aware identity protocol; re-judge CAFE-1; recommend on CAFE-3 done-when | P1 / SPEC-ID-GATE-1 |
| AKI-03 | intake-2830 A1 + intake-2842 V3 | Measure width-1 versus width-W noise to set tau, with zero-margin share | P1 / SPEC-ID-NOISE-1 |
| AKI-04 | intake-2830 A4 + intake-2843 L3 | GPU redecode versus serial arm, pre-registered to fail | P1 / SPEC-ID-NOISE-1 |
| AKI-05 | intake-2843 L1 | Position-invariance unit test for GGML_DETERMINISTIC | P1 / GGML-DET-POSINV-TEST |
| AKI-06 | intake-2843 L2 | Report first-divergence hazard per token-at-risk as a rate ratio in the C18 bisect | P1 / SPEC-ID-GATE-1 |
| AKI-07 | intake-2830 decline | Serve a rebuild gate or fixed-shape verify for exactness | decline: production samples at T > 0, and the cheaper opt-in GGML_ROWEXACT_N already exists for CPU exactness |
| AKI-08 | intake-2843 decline | Build decode-verify-rollback or a per-request determinism flag | decline: gates already run one request per fresh server and the batch-invariance premise fails on the MI210 atomics paths |
| AKI-09 | intake-2844 decline | EqSpec/EXSpec realignment or batch-invariant mode as an np4 fix | decline: llama.cpp's cell-indexed KV has no rectangular batch to realign |
| AKI-10 | intake-2824 row 1 + intake-2837 row 1 + intake-2838 rows 1-2 | Port #30553 cap and #30022 force-tiling widened to CDNA, add #32837 table arm, census and screen on gfx90a | P2 / AK-MMQ-SK2 |
| AKI-11 | intake-2838 row 3 | State that bit-identity versus C19 is not expected after a grid change | P2 / AK-MMQ-SK2 |
| AKI-12 | intake-2824 row 2 | End-to-end 27B np4 and A3B pp512 row after a kernel keep | M1 |
| AKI-13 | intake-2824 decline | End-to-end probe at the served 27B np1 point | decline: MMQ is about 0.9% of 27B np1 kernel time, so no speedup can clear a 1% floor |
| AKI-14 | intake-2824 decline | Port the stream-k rule to Zen 5 | decline: ggml-cpu has no split-K/fixup stage or LDS-occupancy knob |
| AKI-15 | intake-2837 + intake-2838 doc rows | Record the dense-shape prior near zero and the cap no-op | K2 |
| AKI-16 | intake-2837 decline | Port the GCN table, grid and fixup pieces | decline: gated on GCN, which the MI210 is not |
| AKI-17 | intake-2828 row 1 | FAIL-on-zero/NaN timing ingestion with tests | P3 / AK-TIMING-ZERO-1 |
| AKI-18 | intake-2828 row 3 + intake-2839 row 1 + intake-2841 row 3 | Shared both-arms receipt validator, all-or-none comparison, perf fields by the measuring step only | P3 / AK-RECEIPT-ARMS-1 |
| AKI-19 | intake-2839 row 3 | Bind an authorising-act reference to each candidate | P3 / AK-RECEIPT-ARMS-1 |
| AKI-20 | intake-2828 row 2 + intake-2839 rows 2,4 | Spec a uniform fast-path decision record and a no-fallback-after-launch audit | P3 / RKA-DECISION-RECORD-1 |
| AKI-21 | intake-2839 row 5 | HIP-graph first-call note | P3 / RKA-DECISION-RECORD-1 |
| AKI-22 | intake-2828 row 4 | Check test-backend-ops id-compare exactness | P2 / AK-MMQ-SK2 |
| AKI-23 | intake-2828 row 5 + rev-1 AITER source read | Folded split-K ba partials summed inside the GDN kernel (concrete AITER design, fused_gdn_decode_qkvz.py:61) | P10 / AK-BW-GDN-GATE-FOLD |
| AKI-24 | intake-2828/2839 decline | Provider registry with enable-order priority or measured selection among providers | decline: one champion is the single source of dispatch truth |
| AKI-25 | intake-2841 rows 1-2 | CU-mask concurrent stress arm; actor-context ablation | decline: no current AK candidate has inter-workgroup waits; the ablation is a loop launch under the operator hold |
| AKI-26 | intake-2841 row 4 | Wire lineage_capture at keep_the_diff behind a flag | M13 |
| AKI-27 | intake-2833 C1 + intake-2853 AD-3 + intake-2851 TP-3 + intake-2852 PI-1 | Offline supersession classifier replay with dedup and regret counts | P4 / TOC-SUPERSEDE-1 |
| AKI-28 | intake-2833 C2 + intake-2853 AD-1 | Supersession and step_reduce arms in TOC-CMP-4 | M2 |
| AKI-29 | intake-2833 C3/C4 + intake-2850 SA-1/SA-2 + intake-2849 LL-4 + intake-2853 AD-2 | Evict-cost probe, checkpoint-alignment classes and device break-even table | P4 / KV-EVICT-COST-1 |
| AKI-30 | intake-2833 C5 + intake-2851 TP-1/TP-2 | Prefix-stability audit and batching counterfactual from prompt-layout logs | M11 |
| AKI-31 | intake-2849 LL-1/LL-2 | Removed-span case in KPF-62 G3 and a default-off kv_splice field | M3 |
| AKI-32 | intake-2850 SA-3 | Fork-based pre-warm prototype | decline: re-prefill slack for supersession is only the tool's execution time, and no measured idle-gap distribution exists yet |
| AKI-33 | intake-2833 C6/C7 + intake-2849 LL-3 + intake-2850 SA-4 + intake-2851 TP-4 + intake-2852 PI-3 + intake-2853 AD-4 | CPU pressure gate, energy metric, GDN rotate splice, offloading, LLM estimator, phantom tools, default in-place rewrite | decline: each rests on a premise our hosts or models do not meet |
| AKI-34 | intake-2833 headline | Use the paper's throughput and energy numbers for planning | K3 |
| AKI-35 | intake-2835 A1/A2 + intake-2855 R1 + intake-2856 G1 | Per-role ask counts, residual-risk probe versus entropy-only, budget-priced penalty replay | P5 / RTG-ASK-1 |
| AKI-36 | intake-2835 A3 + intake-2855 R2 | J17 ask-calibration readouts with an oracle-timing ceiling | M4 |
| AKI-37 | intake-2835 A4/A5 + intake-2855 R3 | Design note on a trained ask policy and escalate-versus-consult primitives | P5 / RTG-ASK-1 |
| AKI-38 | intake-2855 R4/R5 + intake-2856 G4 | Reproduce R2V or AgentRL headline numbers; CVaR | decline: R2V has no code and AgentRL's recipe needs 16 H800 |
| AKI-39 | intake-2856 G2 + intake-2860 AB1/AB2 | ALFWorld-only AgentBench smoke driving a local role | M10 |
| AKI-40 | intake-2860 AB3 | KG and WebShop workers | decline: no ledger row consumes them |
| AKI-41 | intake-2836 H1 + intake-2857 HR2 + intake-2859 PR1/PR4 + intake-2862 PR4a + intake-2858 LH2 | Disjoint-task accept, fresh parent, sealed test, decision record with status split, matched budget | P6 / AP-BSV2-ACCEPT-RIGOR |
| AKI-42 | intake-2857 HR1/HR3 + intake-2858 LH1/LH3 + intake-2859 PR3 | HIL-2 checklist cases, taxonomy, validity gate, install envelope | P6 / HIL-EVO-CASES-1 |
| AKI-43 | intake-2836 H2 + intake-2859 PR2 + intake-2862 PR2a | Map hook events and a versioned plugin manifest onto AP-DGM-PROV | P6 / AP-BSV2-ACCEPT-RIGOR |
| AKI-44 | intake-2836 H3 | Executable-guard arm beside the text-skill arm in the SkillBank A/B | M12 |
| AKI-45 | intake-2858 LH4 + intake-2861 LH4a-c | Life-Harness evolve-from-scratch with a local improver | M10 |
| AKI-46 | intake-2857 HR4 | No-model HookEvo smoke | decline: it exercises a JavaScript runtime we do not use |
| AKI-47 | intake-2836 H4 + intake-2857 HR5/HR6 + intake-2858 LH5 + intake-2859 PR5 + intake-2861 LH4d + intake-2862 PR6 | Reproduce headline numbers, vendor packages, copy slot/quota-hold | decline: they measure other harnesses; rowflow already covers slots |
| AKI-48 | intake-2847 S1 + intake-2832 A1 gate | Exact longest-suffix coverage curve over COPYSPEC P1 outputs | P7 / SPEC-COPY-COV-1 |
| AKI-49 | intake-2832 A1/A2 + intake-2847 S2 | Training-free copy-proposal probe and CoPyro arm in DF2-FT-1 | M5 |
| AKI-50 | intake-2845 D2 + intake-2831 A1 + rev-1 code read | Bound the MTP gap (draft distribution via the rejection path, or coupling) at every served T including 1.0 | P7 / SPEC-COUPLE-MTP-1 |
| AKI-51 | intake-2845 D1/D3 + intake-2831 A2 + operator review 2026-11-23 | The 1-TV theorem closes coupled-draw CHAIN verification only; DICE and Gumbel-max target sampling on trees at served T are falsified offline | P7 / SPEC-DTREE-DICE |
| AKI-52 | intake-2831 A1 + operator review 2026-11-23 | Measure the sampled share of served traffic, then replay DICE node selection offline for acceptance gains; GPU row only on gains | P7 / SPEC-DTREE-DICE |
| AKI-68 | intake-2846 K1 | First-order DTREE acceptance-calibration refit | M6 |
| AKI-69 | intake-2846#02 + rev-1 theory read | Exponential-race verifier for k >= 3 siblings and multi-draft coupling on trees | P7 / SPEC-DTREE-DICE |
| AKI-70 | rev-1 AITER source read (fused_gdn_decode_qkvz.py, fused_gemm_a16w16_dual_splitk.py) | Fold GDN beta/alpha projections and gate math into the recurrence kernel | P10 / AK-BW-GDN-GATE-FOLD |
| AKI-71 | rev-1 AITER source read (per-channel int8 GEMMs) + AK-ASM-I8GEMM-PERCHANNEL | Per-channel int8 weights on the bandwidth-bound verify GEMV | P10 / AK-ASM-I8GEMM-PERCHANNEL-GEMV |
| AKI-72 | rev-1 AITER non-candidates | Port the remaining v0.1.30 families (FP8/MX/NVFP4, MLA, gfx950 MTP4 tile, kernarg preload, gfx1201 small-m fmoe, sort pad-id fix) | decline: FP8/MX hardware absent on gfx90a, gfx940+ ISA, or already retargeted, tried or absent from our path |
| AKI-73 | rev-1 theory read | Scope intake-2845's 'never beats rejection sampling' claim to per position, single draft | K1 |
| AKI-53 | intake-2848 R1/R2 | ReTrace rank-coverage probe and arm | M7 |
| AKI-54 | intake-2832/2847 declines | Revive n-gram composition or serve SAM-Decoding standalone | decline: composition measured a loss on the 27B MI210 and the registry bans it |
| AKI-55 | intake-2834 C5 | Entropy-rank bands of DFlash2 rejections | decline: hypothesis with no source support |
| AKI-56 | intake-2825 row 1 | Readlane arm at mmid.cu:92 in the MMID-HELPER-N10-GATE build | P8 / MMID-HELPER-READLANE |
| AKI-57 | intake-2825 rows 2-3 + intake-2826 row 2 + intake-2827 row 2 | Port the topk-moe, GDN-MMA, mm_ids_helper<16 or 32> hunks or a standalone mbcnt helper | decline: none of these sites exists on our served path |
| AKI-58 | intake-2827 row 1 | mbcnt rank port at MMID-HELPER-N10-GATE close | M8 |
| AKI-59 | intake-2826 row 1 + intake-2840 rows 1-2 | flash_attn_mask_to_KV_max prefill share; np4 live-chunk max/mean | P8 / RKA-TRACE-SHARES-1 |
| AKI-60 | intake-2840 declines | gv merge skip, FP8/MX/K32/kernarg pieces, n=1 planner | decline: FP8/MX-dependent, nearly moot in gv, or unserved n=1 |
| AKI-61 | intake-2829 P1-P3 | Time vocab-only tokenization of a 100k prompt; port #32859 only if >= 2% of cached-turn TTFT | P8 / TOK-BPE-TIME-1 |
| AKI-62 | intake-2829 P4 | Treat #32859 as a cold-prefill TTFT item | decline: tokenization is 3-4 orders of magnitude below cold 100k prefill |
| AKI-63 | intake-2834 C1/C4 + intake-2854 CR1-CR4 + intake-2856 G3 | MI210 gfx90a training-viability smoke with CreditFilter and AgentRL as consumers | M9 |
| AKI-64 | intake-2834 C2 | Fix the stale DGX premise in eval-tower-program.md:159-161 | P9 / EVT-DGX-PREMISE-FIX |
| AKI-65 | intake-2834 C3 | Record CreditFilter's tested scope | K5 |
| AKI-66 | intake-2830/2848 PDF-only | Hand-check PDF quotes so Vega-Fafnir and ReTrace can be cited | M7 |
| AKI-67 | second reader | 18 anchor rows where the second reader answered no | K6 |

## Proposed handoff edits (Stage 4 only, after approval)

handoffs/active/kernel-champion-and-promotion.md (after C18-REPLAY-Q4X-CONC-BISECT (line 55)):
  - [ ] **SPEC-ID-RAGGED-1** [non-inference] Add `test-multiseq-ragged-rollback` on a fresh llama.cpp-experimental branch from C19 a6a32c1 as the mechanism check for the Q4X replay divergences that C18-REPLAY-Q4X-CONC-BISECT left UNLOCATED (8 ON-only phase-C first divergences, not tie flips, not on one slot) (intake-2844#01, intake-2844#02): 3-4 sequences in one batch, a different accepted-draft count per sequence each round, `kv_unified` on and off, both snapshot rollback and RS replay, compared token-for-token and state-for-state with a single-sequence reference run. No test at a6a32c1 covers multi-sequence ragged rollback (`tests/test-recurrent-state-rollback.cpp:13` sets n_seq_max = 1). If it fails, the fix comes before any Q4X replay re-allow; if it passes, the divergences are classified with SPEC-ID-GATE-1.
      · done when: test committed on the branch with its SHA, PASS or FAIL per arm (kv_unified x rollback mode) recorded under this box, and the consequence for the Q4X re-allow stated
      · gate: none

handoffs/active/speculative-decoding.md (Track speculative-decoding-mtp-refresh, ### Backlog):
- [ ] **SPEC-ID-GATE-1** [non-inference] Write the width-aware identity-gate protocol for speculative-decoding gates and apply it to two existing verdicts (intake-2842#00, intake-2842#04, intake-2844#record, intake-2844#02; in-house INF-70 E2a: `LLAMA_SPEC_EXACT` modes at tools/server/server-context.cpp:42-112 @ a6a32c1, opt-in `GGML_ROWEXACT_N` at ggml/src/ggml-cpu/ggml-cpu.c:1505 @ a6a32c1). Protocol: (a) an identity check compares arms only inside one verify-width class, or under `LLAMA_SPEC_EXACT=serial` / `GGML_ROWEXACT_N`, because pinning one kernel backend does not remove verify-path divergence (intake-2842#04); (b) never import a literature exact-match rate as a threshold (intake-2844#record); (c) classify every first divergence as near-tie flip (top-2 margin inside the measured A/A floor), DEGEN_AFTER_TIE (repeat loop after a tie, a defect when the speculation-off np4 control shows none, intake-2844#02) or defect. Apply it: re-judge the CAFE-1 p-min decline (speculative-decoding.md:505, decided on 100% identity alone; a CPU row only if its logprobs were not retained), and write a recommendation to CAFE-3's owner on its identity-100% done-when (speculative-decoding.md:523) without editing that box.
      · done when: protocol section committed in speculative-decoding.md; CAFE-1 re-judgement verdict (stands or reopens) and the CAFE-3 recommendation recorded under this box
      · gate: none

handoffs/active/speculative-decoding.md (Track speculative-decoding-mtp-refresh, ### Backlog):
- [ ] **SPEC-ID-NOISE-1** [inference] Measure the width-1 versus width-W teacher-forced logit noise that SPEC-ID-GATE-1 needs as its A/A floor, on 27B Q8_0 + DFlash2 (MI210, C19 GPU store) and Q38FN UD-IQ4_XS + MTP (CPU quarter q0-q2, C19 CPU store). Frozen input: 64 prompts from the DF2-13 prompt set, digest recorded, split into calibration and holdout halves. Per position: max |delta logit| and top-2 margin between width 1 and each served verify width; first-divergence margin histogram; share of first divergences at exactly zero margin (intake-2842#03). Extra arm on HIP: `LLAMA_SPEC_EXACT=redecode` versus `serial`, pre-registered to fail because redecode reuses verify-written KV and GDN state (intake-2843#02). Question: what tolerance tau separates noise from defect per width class. Stop-on-answer when the holdout q99 of |delta logit| is within 10% of the calibration q99 on both devices; stop-on-futility on residency proof failure (verify_ggml_linkage.sh plus nonzero VRAM sampled during the run), store mismatch or STOP/deadline; gate-class futility-only. Complete denominator: every prompt reported, refusals counted.
      · done when: per-device tau with calibration and holdout q99, the zero-margin share and the redecode-vs-serial verdict filed under this box with the run path
      · gate: none

handoffs/active/autokernel-loop.md (next to GGML-DETERMINISTIC-REDUCE-SCRATCH (line 4956)):
  - [ ] **GGML-DET-POSINV-TEST** [non-inference] Add a position-invariance unit test to the branch that carries `GGML_DETERMINISTIC` (fork commit bef2e4c7d; absent from C19 a6a32c1): at fixed M in {2, 4, 8, 16}, permute the rows of src1 and require bitwise-identical output rows after un-permuting, for the MI210 Q8_MF V5 and q8_skinny paths with GGML_DETERMINISTIC=1, and assert that the split count depends only on (M, N, K) (intake-2843#03). This is the property GGML-DETERMINISTIC-REDUCE-SCRATCH must preserve.
      · done when: test committed with its SHA, green with GGML_DETERMINISTIC=1 on ROCm0 (and red or documented-nondeterministic with it off) recorded under this box
      · gate: none

handoffs/active/autokernel-loop.md (AK MMQ section, after AK-MMQ-H5 (line 4532)):
- [ ] **AK-MMQ-SK2** [inference] Stream-k at small column counts on gfx90a (intake-2824#record, intake-2824#01, intake-2824#02, intake-2837#01, intake-2838#00). Step 1 (code, region-lock claim for the build): on a fresh llama.cpp-experimental branch from C19 a6a32c1, hand-port upstream #30553 (stream-k grid capped at useful work) and #30022 (force-tiling rule) as two default-off commits with the predicate widened from GCN to CDNA behind env `GGML_HIP_MMQ_CDNA_FORCE_TILING=1`, plus a separate build arm with #32837's CDNA table cell (256 threads, occupancy 2, I=64) in mmq-config-cdna.cuh. Our launcher always runs 104 stream-k blocks (ggml/src/ggml-cuda/mmq.cuh:1318-1366 @ a6a32c1). Step 2 (zero compute): census served MMQ shapes (27B np4 verify M=36, A3B Q8_0 MUL_MAT_ID above the MMVQ cap, Q4_K/Q6_K at 5-128 rows) and record where force-tiling fires and where the cap changes the grid. Step 3 (one GPU row, cap 1 GPU-h): arms D default, A force-tiling env, B table build; cells Q4_K MUL_MAT n 5/8/16/32 on 17408x5120 and 5120x17408, Q8_0 n 17/36/64, A3B Q8_0 MUL_MAT_ID n 16/64, n=512 guards; order: knob-honoured witness, test-backend-ops MUL_MAT/MUL_MAT_ID correctness (bit-identity versus C19 is not expected: a grid change regroups FP32 sums), ISA audit for B, then 7 interleaved reps per cell with a same-row A/A. KEEP_CANDIDATE if any cell beats its A/A by >= 3% with no n=512 guard worse than -3%; else CLOSE. Futility: correctness fails, knob not honoured, B spills or loses occupancy, residency fails; gate-class futility-only.
      · done when: branch SHA with the two port commits, the shape census, and the row verdict (KEEP_CANDIDATE or CLOSE) with per-cell A/A-relative deltas filed under this box
      · gate: none

handoffs/active/autokernel-loop.md (AK loop infrastructure section):
  - [ ] **AK-TIMING-ZERO-1** [non-inference] Close the three timing-ingestion holes that let zero or nonfinite numbers through, in epyc-inference-research scripts/kernel_rnd/autokernel/loop (intake-2828#03): `bench.py:424` returns `avg_ts` checked only for finiteness, `bench.py:642-694` silently drops `value <= 0`, and `graph_profile_reader.py:45` accepts `>= 0`. Make each a recorded refusal (value must be finite and > 0) matching the existing strict gate in `execution/microbench.py:1887-1897`, and add unit tests that feed 0, -1, NaN and inf through each path and expect a refusal, not a sample.
      · done when: the three call sites refuse with a reason, unit tests green, commit SHA recorded under this box
      · gate: none

handoffs/active/autokernel-loop.md (AK loop infrastructure section):
  - [ ] **AK-RECEIPT-ARMS-1** [non-inference] Make keep receipts self-validating at consumption (intake-2839#02, intake-2839#03, intake-2841#02): `ExperimentalKeepReceipt` (loop/surface_fold.py:140-193) validates `comparison` only by digest (:174-178), while the both-arms check lives at run.py:2450-2459 and bench.py:232-256. Move that check into one shared validator called when a receipt is consumed; require the comparison block all-or-none (measured value, baseline value, baseline path, measured_under, measurement reference); allow perf fields to be written only by the measuring step; add an authorising-act reference field to `CandidateTarget` (candidate_manifest.py:201-250); re-validate every retained receipt and list any that fail.
      · done when: shared validator landed with tests (missing arm, partial comparison block, hand-written perf field all refused), retained-receipt re-validation report path recorded under this box
      · gate: none

handoffs/active/rocm-kernel-authoring.md (INF-48 backlog):
- [ ] **RKA-DECISION-RECORD-1** [non-inference] Specify one fast-path decision record for the fork's HIP dispatch (design only; intake-2839#00, intake-2839#04): route chosen, reason, kernel id, build digest and knob source, emitted once per process per op-shape class and readable without a profiler, plus an audit rule that no fast path may fall back after launch. Motivation is in-house: C16-TOPK-STAGE and C15-GV-BW closed with the witness absent, and today only per-row oracles exist (cpu_route_witness.py, the once-per-process witness at fattn-gqa-verify.cu:828-830 @ a6a32c1).
      · done when: design section committed in rocm-kernel-authoring.md naming the record fields, emit points and the two closed rows it would have unblocked
      · gate: none

handoffs/active/context-and-token-economy.md (next to DCP-9a (line 438)):
- [ ] **TOC-SUPERSEDE-1** [non-inference] Replay a tool-supersession classifier offline over recorded REPL and Claude Code transcripts and over AgentDiet's released trajectories (intake-2833#00, intake-2833#01, intake-2853#00, intake-2851#02, intake-2852#00). Rule: a later read or edit of the same file path, a re-run of the same normalized shell command, a later build whose targets overlap, or a passing re-run of the same test supersedes the earlier tool output; a round whose outputs are all superseded becomes a candidate; 2-round grace window; no model calls. Report the candidate token share of final histories, the hash-dedup repeat count, and an eviction-regret rate (superseded content later re-read, by content hash). Six controls: frozen transcript manifest with digest, baseline = no eviction and the current age-based `_clear_stale_tool_outputs` (orchestrator src/graph/helpers.py:558), per-transcript outputs retained, holdout = transcripts after a fixed date, every transcript counted, rule fixed before the run. Stop-on-answer: share < 15% closes the supersession arm; >= 15% fires the TOC-CMP-4 trigger below.
      · done when: share, dedup count and regret rate per transcript class with the manifest digest filed under this box, and the arm closed or the trigger fired
      · gate: none

handoffs/active/kv-cache-program.md (Track near KPF-26 / KPF-62):
  - [ ] **KV-EVICT-COST-1** [inference] Build a read-only evict-cost probe for llama-server and a device break-even table (intake-2833#02, intake-2850#02, intake-2849#03, intake-2853#04). Probe: for a proposed cut, predict re-prefilled tokens = T' - p*, with p* the nearest checkpoint at or before the cut (restore logic tools/server/server-context.cpp:5126-5170 @ a6a32c1; hybrid models cannot shift, `can_shift` false at src/llama-memory-recurrent.cpp:832), classify the cut as checkpoint-aligned or not, and predict seconds as a + b x cells fitted from existing prefill rows. Check it in one small CPU smoke on 20 synthetic cuts against measured `n_prompt_tokens_processed` (pass at 19/20 exact token counts). Then publish a doc table per device (MI210 and one CPU quarter) of break-even gain for a cut, with a residual column max(0, cost - inter-turn slack) and a row for an LLM reflection call; device-specific commit caps, never the paper's H100 cap.
      · done when: probe committed with tests, smoke result (k/20 exact) and the per-device break-even table recorded under this box
      · gate: none

handoffs/active/routing-program.md (routing track backlog):
- [ ] **RTG-ASK-1** [non-inference] Calibrate when our small roles ask for help, from logs only (intake-2835#00, intake-2835#01, intake-2855#00, intake-2855#02, intake-2856#00). (1) Tabulate escalations per task and role from existing taps and progress logs, counting `escalate()` hand-offs (src/repl_environment/routing.py:303-319) and consult advice separately. (2) Fit a residual-risk probe on logged non-escalated episodes labelled by their own episode outcome and compare it with the entropy-only baseline (generation_monitor.py). (3) Replay-evaluate replacing the fixed `escalation_penalty = len(escalations) * 0.15` (orchestration/repl_memory/q_reward.py:173) with a price solved against a consults-per-task budget. Six controls: frozen log manifest with digest, baseline = current rule policy (src/orchestration/escalation.py:227-350), per-episode outputs, holdout = later time window, all episodes counted, decision rule fixed first: adopt the probe only if its holdout AUROC beats entropy-only by >= 0.05; stop and report counts only if fewer than 200 escalation-eligible episodes exist.
      · done when: per-role counts, holdout AUROC of probe versus entropy-only, and the replayed budget-price result filed under this box
      · gate: none

handoffs/active/autopilot-program.md (next to BSV-2 (line 123)):
- [ ] **AP-BSV2-ACCEPT-RIGOR** [non-inference] Amend the BSV-2 accept design and check it by offline replay of existing AutoPilot journals (intake-2836#01, intake-2857#00, intake-2858#00, intake-2859#03, intake-2862#01, intake-2861#04): (a) accept only on tasks disjoint from the batch whose traces fed the proposal; (b) re-run the parent fresh on that batch, never compare against cached parent outcomes; (c) keep the test split sealed until the search ends and pick the headline checkpoint by a training-side rule, never best-on-test; (d) write a per-round decision record with tokens per accepted gain and row statuses completed / solver_limit / infra_error / candidate_error, with retry for infra errors only; (e) state budgets in rollouts or tokens, not iterations. AutoPilot stays stopped; this is design plus replay.
      · done when: amended BSV-2 design text committed and the replay result (how many past accepts survive (a)-(b)) recorded under this box, or a recorded stop if journals are too sparse
      · gate: none

handoffs/active/harness-program.md (harness-improvement-loop track, after HIL-9):
- [ ] **HIL-EVO-CASES-1** [non-inference] Append to the HIL-2 pre-first-suite-run checklist in docs/design/harness-improvement-loop-design-20261006.md (as HIL-9 did): the HookEvo shipped per-round adoption record as a worked case of in-sample retention (intake-2857#00, intake-2857#01); the Life-Harness four-layer harness taxonomy as the annotation schema and its trace-replay validity gate before any paid evaluation (intake-2858#00, intake-2858#02); the plugin install envelope (signature regex plus syntax check, abort on an infrastructure-defect string) as a BEP-5 input (intake-2857#05); and the matched-budget rule from AP-BSV2-ACCEPT-RIGOR (e). Zero inference.
      · done when: checklist items committed in the design doc with the commit SHA recorded under this box
      · gate: none

handoffs/active/speculative-decoding.md (Track speculative-decoding-mtp-refresh, ### Backlog, near COPYSPEC):
- [ ] **SPEC-COPY-COV-1** [non-inference] Offline copy-match coverage curve before any copy-proposal drafter work (intake-2847#00, intake-2847#01, intake-2832#00, intake-2832#01). Over the archived COPYSPEC P1 outputs (artifacts/copyspec-20261006/source-archive/results/P.jsonl, 85 requests), build an exact longest-suffix index (our ngram-mod at common/speculative.cpp:2651-2812 @ a6a32c1 is a fixed-n hashed window, not longest-suffix) and report, per position, the match length and whether the next 3 tokens agree, for code and prose, plus a leave-one-out variant. Stop-on-answer: if positions with match length >= 5 and >= 3 agreed tokens are under 5% on code and under 2% on prose, close the copy-proposal path; otherwise fire the trigger below.
      · done when: coverage table (code and prose, in-sample and leave-one-out) recorded under this box with the path closed or the trigger fired
      · gate: none

handoffs/active/speculative-decoding.md (Track speculative-decoding-mtp-refresh, ### Backlog):
- [ ] **SPEC-COUPLE-MTP-1** [inference] Bound what a draft distribution plus rejection sampling, or coupled draws, could add on the A3B MTP chain at served temperatures (intake-2845#00, intake-2845#record, intake-2831#01). MTP at T > 0 verifies by sample-and-compare against an argmax draft (common/sampling.cpp:693-711, common/speculative.cpp:2116-2119 @ a6a32c1), so per-position acceptance is p(argmax q), below the single-draft 1 - TV ceiling (a per-position, single-draft bound, intake-2845#record) that the DFlash2 rejection path already reaches. Using the SPEC-DTREE-DICE step-2a capture (MTP top-10 drafter logits plus target candidates at every verified row; frozen 64-prompt set with digest; baseline = current sample-and-compare; per-position outputs kept; holdout = second half of the prompts; every position counted), compute offline per served T from SPEC-DTREE-DICE step 1 (expect 0.1/0.2/0.3 and 1.0): the gap 1 - TV(q, p) - p(argmax q) for q = softmax(logit/T) over the MTP top-10, i.e. routing MTP through the existing rejection path. Stop if the holdout gap is under 1% at every served T; file a build box (MTP fills draft distributions, rejection path) if it is 2% or more at any served T with >= 20% token share; gate-class futility-only.
      · done when: per-temperature holdout gap and the decision (close or build box filed) recorded under this box
      · gate: none

handoffs/active/speculative-decoding.md (Track dflash2-block-drafter-experimental-build, AK-DTREE program plan (near DTREE-A, line 2375)):
- [ ] **SPEC-DTREE-DICE** [inference] Falsify or confirm that pre-sampled target randomness raises expected accepted length on SAMPLED trees at served temperatures (intake-2831#00, intake-2831#03, intake-2831#05), where the single-draft 1 - TV ceiling (intake-2845#record) does not apply and k-candidate verifiers beat the standard one at T > 0 (intake-2846#02, intake-2715#00, intake-2717#01). Today DTREE is greedy-only (spec_tree_nodes_for returns 0 at temp > 0, tools/server/server-context.cpp:5586-5590 @ a6a32c1) and the DTREE dumps are greedy with no target probabilities, so they cannot be replayed at T > 0. Step 1 (code only): log the resolved temperature/top_k/top_p/min_p per request in the inference-tap start event (orchestrator llama_server.py:1739-1747 payload site) and poll /slots on the speculative ports for direct clients; report the token-weighted temperature histogram per drafter (27B DFlash2, A3B MTP) over a declared window; close if the T > 0 share is under 5% on both, else the served T set is its modes. Step 2a (capture): a dump-knob-only fork from the current champion, at served T with keyed draws (seed, position, vocab id), logging per round the drafter lattice/candidates and the target post-sampler candidates plus top-64 logits at every verified row; for DFlash2 force a superset tree (prob-greedy W32 + DICE W16 + chain) into the verify batch while committing through the unchanged chain. A3B MTP first on a CPU quarter q0-q2; the 27B DFlash2 capture is an MI210 capture-only row on gpu-q3 (OD-5 = C, operator 2026-11-23: both captures allowed now). Step 2b (offline replay, CPU) at equal node budget W in {1,4,8,12,16}: V0 served path, V1 same tree with recursive rejection without replacement, V2 Gumbel-max walk with pre-sampled draws and draw-blind selection, V3 DICE draw-informed selection ((alpha, sigma) fitted on the calibration half only), optional V4 exponential-race verifier for k >= 3 siblings (intake-2846#02); metric expected tokens per target pass per served T. Controls: frozen capture and replay script with sha256, baseline V0, per-round per-arm results.jsonl, holdout = second prompt half, every verify round counted, PREDECLARATION.md sealed before replay. Falsifier H1: V3 raises expected accepted length over V0 and over V1 at equal W. Futility: close if holdout V3/V1 < 1.02 at every served T and W <= 16 and V3/V0 stays below the verify-cost break-even; stop-on-answer at a prompt-clustered 95% CI half-width <= 1% on V3/V1 at the highest-share T; gate-class futility-only. A GPU build row (keyed Gumbel-max target sampler, DICE node selection, Gumbel tree walk, T > 0 guard lifted; ABBA np1/np4; KEEP iff tok/s CI-lower > 1.0 and an emitted-token distribution check passes) is filed only if the replay clears break-even; if only V1 clears it, file the sampled recursive-rejection tree row (DTREE-A) instead.
      · done when: step-1 temperature-share table and decision filed; then the capture digest and a RESULT.json with holdout tokens per pass per arm x T x W and a verdict CLOSE_FUTILITY / FILE_GPU_ROW / FILE_RRS_ROW
      · gate: none

handoffs/active/autokernel-loop.md (next to AK-BW-27B-ACTQUANT-FUSE (line 4976)):
  - [ ] **AK-BW-GDN-GATE-FOLD** [inference] Fold the GDN beta/alpha projections and gate math into the recurrence kernel on 27B/A3B verify, after AITER v0.1.30 `aiter/ops/triton/gated_delta_net/fused_gdn_decode_qkvz.py` (read at 77ba72b7061a; gfx950 Triton as written, the gate math is scalar and portable): it computes sigmoid(b) and exp(-exp(A_log) * softplus(a + dt_bias)) inside the GDN kernel from the raw projection and sums ba as fp32 split-K partials in-kernel with no zero-init or atomics (`:61`), with the ba projection emitted by the qkvz GEMM launch (`fused_gemm_a16w16_dual_splitk.py:47-60`, tuned for N1=16384 N2=96 K=5120, our 27B shape) (intake-2828#record). In-house budget, C18 27B DFlash2 verify trace ak-c18-27b-df2-v5i-trace-gpu-20261122 (40.07 ms GPU per verify): 96 small q8sk_mul_mat launches for beta/alpha (0.63 ms) and four unfused gate ops x 48 layers (0.88 ms), plus norm/z gate (0.42 ms) and the state gather k_get_rows (0.53 ms); the existing softplus fusion (ggml-cuda.cu:4252 @ a6a32c1) does not engage there (cause unknown). Arms in order: (a) row-concat ssm_beta|ssm_alpha into one Q8_0 tensor at load and one launch writing [KS, T, 2*H_v] fp32 partials without atomics; (b) a fusion from that output to GATED_DELTA_NET passing raw b/a, ssm_dt and ssm_a to the C19 fused K=T and rows kernels, which sum the partials and apply the gate in their prologue; (c) and (d) (norm + silu(z) epilogue; state pool by slot) only after (a)+(b). Side effect: removes the unordered atomic split-K on ssm_ab. Step 1 (no GPU): from the 27B trace above and ak-c18-a3b-mtp-trace-gpu-20261122, list the launches each arm removes with their ms and confirm from C19 source how the GDN kernels read g/beta; stop-on-futility if (a)+(b) remove < 0.8 ms per 27B verify. Then one op/trace row: stop-on-answer when GDN-input ms per verify <= 0.4 ms with test-backend-ops GATED_DELTA_NET parity and 27B KLD vs C19 <= 0.003; then 27B DFlash2 np1 e2e, 8 ABBA pairs, KEEP iff CI lower > +1% and no cell < -1%; futility if the first variant saves < 0.6 ms per verify; gate-class futility-only. Build: experimental branch from C19 a6a32c1, knob default off, region-lock claim; coordinate with AK-BW-27B-ACTQUANT-FUSE and AK-BW-A3B-DENSE-STEP2 (b) (same concat).
      · done when: step-1 launch/ms table filed, then an op/trace verdict and a 27B e2e KEEP/DROP for arms (a)+(b); A3B runs only after a 27B KEEP
      · gate: none

handoffs/active/autokernel-loop.md (child of AK-ASM-I8GEMM-PERCHANNEL (line 4324)):
        - [ ] **AK-ASM-I8GEMM-PERCHANNEL-GEMV** [inference] Measure the verify-GEMV half of AK-ASM-I8GEMM-PERCHANNEL that no row has measured (the port row measured only prefill, dispatch at ne11 >= 129, 0.821x). On the 27B verify trace ak-c18-27b-df2-v5i-trace-gpu-20261122 q8mf6_mul_mat is 25.2 of 40.07 ms at 1071 GB/s (71% of the 1.498 TB/s measured peak); a dense per-row int8 layout (32 B per 32 weights plus one scale per row versus Q8_0's 34 B) reads 1/17 fewer weight bytes and drops the per-block scale load; the 27B weight half already passed (AK-ASM-I8GEMM-PERCHANNEL-KLD: KLD 0.001015, dPPL +0.082%). Layout source: AITER per-channel 8-bit weight GEMMs (intake-2828#record). Step 1 (no GPU): from C19 mmq-q8-mf.cu record how the MF_INPLACE layout streams per-block scales and the bytes per weight q8mf6 reads; ceiling = bytes saved / bytes streamed x q8mf6 share of verify; stop-on-futility if the ceiling is < 3% of verify GPU time. Step 2 (GPU, timing only): a speed-of-light knob in q8mf6 that skips the per-block weight scales (numerically wrong, timing only) at the 27B shapes, n 1/4/8/16; futility if it saves < 3% of q8mf6 ms at n=8; at >= 3%, the real layout behind a default-off knob gated by 27B KLD <= 0.003 and |dPPL| <= 0.5%, then 8 ABBA pairs, KEEP iff CI lower > +1%; gate-class futility-only. Confidence low: at 71% of peak the kernel is not purely byte-bound.
      · done when: step-1 ceiling filed, and either a futility close or a step-2 timing verdict (plus, at >= 3%, an e2e KEEP/DROP)
      · gate: none

handoffs/active/kernel-champion-and-promotion.md (next to MMID-HELPER-N10-GATE (line 1861)):
- [ ] **MMID-HELPER-READLANE** [non-inference] Add a readlane arm to the MMID-HELPER-N10-GATE build (no separate row; intake-2825#02, intake-2825#03): replace the one wave-uniform-lane `__shfl_sync` in the served mm_ids helper (ggml/src/ggml-cuda/mmid.cu:92 @ a6a32c1) with `__builtin_amdgcn_readlane`, record the ISA diff (instruction count and VGPRs) and hand the arm to the gate row. Stop if the ISA is unchanged; the gate row's helper us/call decides KEEP (>= 3% helper gain) or DROP.
      · done when: arm commit SHA with the ISA diff recorded under this box and the arm listed in the MMID-HELPER-N10-GATE row argv
      · gate: none

handoffs/active/rocm-kernel-authoring.md (INF-48 backlog, near the FA tail-split item (line 2620)):
- [ ] **RKA-TRACE-SHARES-1** [non-inference] Answer two upstream-port questions from existing traces and arithmetic only (intake-2826#04, intake-2840#00, intake-2840#01): (a) the share of `flash_attn_mask_to_KV_max` in prefill GPU time on the served 27B and Q38FN traces (it only launches when Q->ne[1] >= 1024 or ne[3] > 1, fattn-common.cuh:1493 @ a6a32c1); under 1% closes the ballot-reduce port; (b) for np4 KV-length mixes, max/mean live KV chunks per block in the gv GQA-verify kernel under uniform splits (fattn-gqa-verify.cu:769-781 @ a6a32c1) for padded and unified layouts; max/mean <= 1.15 closes the min-max planner idea, > 1.3 files one GPU row.
      · done when: both numbers with the trace paths recorded under this box and each idea closed or a row filed
      · gate: none

handoffs/active/cpu-decode-roofline-program.md (host-side items):
- [ ] **TOK-BPE-TIME-1** [non-inference] Time tokenization of one real 100k-token orchestrator prompt with the vocab only (no weights, one core, seconds) on the Qwen3.8-27B and Qwen3.6-35B-A3B vocabularies at C19 a6a32c1 (intake-2829#00, intake-2829#04, intake-2829#05). Compare with the cached-turn TTFT of the same roles from existing rows. If tokenization is under 2% of cached-turn TTFT, close the upstream #32859 port; if 2% or more, port it as one commit on an experimental branch after upstream human review, with test-tokenizer-0 for qwen2 and qwen35 and a token-id diff on 20 real prompts.
      · done when: per-vocab tokenize ms and share of cached-turn TTFT recorded under this box with the port closed or filed
      · gate: none

handoffs/active/eval-tower-program.md (the ThinkPRM / verification-model section (line 159)):
- [ ] **EVT-DGX-PREMISE-FIX** [non-inference] Replace the stale premise at eval-tower-program.md:159 ("Training requires GPU (GRPO needs 16 rollouts/step) — defer to DGX Spark.") with: training requires a GPU; the DGX Spark path is closed and the MI210 is present, so a post-training lane is an operator decision (intake-ak-1123 OD-1; intake-2834#record).
      · done when: sentence replaced and the 'when DGX Spark available' roadmap heading at :161 re-pointed to the OD-1 outcome
      · gate: none


Durable trigger prose (no checkbox), one line each under the owner's current track: M1 -> handoffs/active/autokernel-loop.md; M2 -> handoffs/active/context-and-token-economy.md; M3 -> handoffs/active/kv-cache-program.md; M4 -> handoffs/active/routing-program.md; M5 -> handoffs/active/speculative-decoding.md; M6 -> handoffs/active/speculative-decoding.md; M7 -> handoffs/active/speculative-decoding.md; M8 -> handoffs/active/kernel-champion-and-promotion.md; M9 -> handoffs/active/model-evaluation-queue.md; M10 -> handoffs/active/eval-tower-program.md; M13 -> handoffs/active/autokernel-loop.md; M11 -> handoffs/active/context-and-token-economy.md; M12 -> handoffs/active/memory-program.md; K1 -> handoffs/active/speculative-decoding.md; K2 -> handoffs/active/autokernel-loop.md; K3 -> handoffs/active/context-and-token-economy.md; K4 -> handoffs/active/autokernel-loop.md; K6 -> handoffs/active/vidya-belief-substrate-program.md; K5 -> handoffs/active/model-evaluation-queue.md.

Index rows: none. Every box lands in a handoff that already owns an index row; no new stubs. Stage 4 also: entry updates below, the steering reconciliation, compile_sources.py check, intake_dive_digests.py for intake-2824..2862, and index_state.py --check.

## Dive-surfaced sources
All recommended sources were ingested and dived in waves 1-2 under the operator pre-authorisation; every declined source is named in its bearing entry's dive_corrections (Stage-2 close-out lines).

## Steering ledger
21 operator rows: 17 planned (P1-P8, P10, M8, M9), 4 context-only (pre-authorisation, stop-at-Stage-3, session context, OD answers). Rows 17-21 are Stage-3 operator comments carried in this plan and persisted at Stage 4. Full verbatim rows are in the payload.

## Stage-3 filing payload

```json
{
 "format_version": 2,
 "entry_updates": [
  {
   "id": "intake-2824",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): AK-MMQ-SK2"
   ]
  },
  {
   "id": "intake-2825",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): MMID-HELPER-READLANE"
   ]
  },
  {
   "id": "intake-2826",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): RKA-TRACE-SHARES-1 (a)"
   ]
  },
  {
   "id": "intake-2827",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): M8"
   ]
  },
  {
   "id": "intake-2828",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md",
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): AK-TIMING-ZERO-1, AK-RECEIPT-ARMS-1, RKA-DECISION-RECORD-1, AK-BW-GDN-GATE-FOLD, AK-ASM-I8GEMM-PERCHANNEL-GEMV"
   ]
  },
  {
   "id": "intake-2829",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "cpu-decode-roofline-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): TOK-BPE-TIME-1"
   ]
  },
  {
   "id": "intake-2830",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md",
    "kernel-champion-and-promotion.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): P1 boxes cite in-house and intake-2842/2844 evidence; this entry stays #record (PDF-only)"
   ]
  },
  {
   "id": "intake-2831",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): SPEC-DTREE-DICE; K1 rewritten to single-draft scope"
   ]
  },
  {
   "id": "intake-2832",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): SPEC-COPY-COV-1; M5"
   ]
  },
  {
   "id": "intake-2833",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "context-and-token-economy.md",
    "kv-cache-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): TOC-SUPERSEDE-1, KV-EVICT-COST-1"
   ]
  },
  {
   "id": "intake-2834",
   "integration_disposition": "monitor",
   "handoffs_updated": [
    "eval-tower-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): OD-1/M9; E1 premise fix"
   ]
  },
  {
   "id": "intake-2835",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "routing-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): RTG-ASK-1"
   ]
  },
  {
   "id": "intake-2836",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autopilot-program.md",
    "harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): AP-BSV2-ACCEPT-RIGOR, HIL-EVO-CASES-1"
   ]
  },
  {
   "id": "intake-2837",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): AK-MMQ-SK2 port commit 2"
   ]
  },
  {
   "id": "intake-2838",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): AK-MMQ-SK2 port commit 1"
   ]
  },
  {
   "id": "intake-2839",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md",
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): AK-RECEIPT-ARMS-1, RKA-DECISION-RECORD-1"
   ]
  },
  {
   "id": "intake-2840",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): RKA-TRACE-SHARES-1 (b)"
   ]
  },
  {
   "id": "intake-2841",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): AK-RECEIPT-ARMS-1 (perf-field rule); OD-3"
   ]
  },
  {
   "id": "intake-2842",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): SPEC-ID-GATE-1, SPEC-ID-NOISE-1"
   ]
  },
  {
   "id": "intake-2843",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md",
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): GGML-DET-POSINV-TEST, SPEC-ID-NOISE-1"
   ]
  },
  {
   "id": "intake-2844",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md",
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): SPEC-ID-RAGGED-1, SPEC-ID-GATE-1"
   ]
  },
  {
   "id": "intake-2845",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): SPEC-COUPLE-MTP-1, SPEC-DTREE-DICE; K1; dive_corrections scope line: the 1-TV result is per position, single draft"
   ]
  },
  {
   "id": "intake-2846",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): SPEC-DTREE-DICE optional V4 arm; M6 calibration refit"
   ]
  },
  {
   "id": "intake-2847",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): SPEC-COPY-COV-1"
   ]
  },
  {
   "id": "intake-2848",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): M7 (PDF-only, stage1-unverified)"
   ]
  },
  {
   "id": "intake-2849",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): M3"
   ]
  },
  {
   "id": "intake-2850",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kv-cache-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): KV-EVICT-COST-1 residual column"
   ]
  },
  {
   "id": "intake-2851",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "context-and-token-economy.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): TOC-SUPERSEDE-1 dedup count; M11"
   ]
  },
  {
   "id": "intake-2852",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "context-and-token-economy.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): TOC-SUPERSEDE-1 regret rate"
   ]
  },
  {
   "id": "intake-2853",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "context-and-token-economy.md",
    "kv-cache-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): TOC-SUPERSEDE-1 trajectories; KV-EVICT-COST-1 reflection row; M2"
   ]
  },
  {
   "id": "intake-2854",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): OD-1/M9"
   ]
  },
  {
   "id": "intake-2855",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "routing-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): RTG-ASK-1 probe"
   ]
  },
  {
   "id": "intake-2856",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "routing-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): RTG-ASK-1 premise; M10"
   ]
  },
  {
   "id": "intake-2857",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autopilot-program.md",
    "harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): AP-BSV2-ACCEPT-RIGOR, HIL-EVO-CASES-1"
   ]
  },
  {
   "id": "intake-2858",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "harness-program.md",
    "autopilot-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): HIL-EVO-CASES-1, AP-BSV2-ACCEPT-RIGOR; OD-2"
   ]
  },
  {
   "id": "intake-2859",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autopilot-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): AP-BSV2-ACCEPT-RIGOR"
   ]
  },
  {
   "id": "intake-2860",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): M10 / OD-2"
   ]
  },
  {
   "id": "intake-2861",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): OD-2"
   ]
  },
  {
   "id": "intake-2862",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autopilot-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1123 Stage 4 (operator-approved plan): AP-BSV2-ACCEPT-RIGOR (d) manifest and status split"
   ]
  }
 ],
 "opportunity_reviews": {
  "P1": {
   "project_objective": "Identity gates (C18-REPLAY-Q4X-CONC-BISECT, CAFE-1/CAFE-3, DF2-12.1) give verdicts that separate verify-width noise from real defects",
   "implementation_ref": "tools/server/server-context.cpp:42-112 @ a6a32c1 (LLAMA_SPEC_EXACT); tests/test-recurrent-state-rollback.cpp:13 (n_seq_max=1); speculative-decoding.md:505,:523 @ d785b6d",
   "gap": "No multi-sequence ragged rollback test; identity gates use 100% identity across width classes with no measured A/A floor",
   "operational_change": "Width-aware identity gates: ragged-rollback test, protocol and A/A noise floor",
   "benefit_direction": "Fewer false identity failures and a direct test of the np4 cache-drift suspect; no change to served numerics",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "Code/doc boxes need no compute; SPEC-ID-NOISE-1 is one GPU row plus one CPU quarter row booked through rowflow; nothing is activated in production",
   "closure_basis": "Immediate; broader determinism work (DVR, batch-invariant kernels) declined"
  },
  "P2": {
   "project_objective": "Small-column MMQ on the MI210 (27B np4 verify, A3B MoE batches) runs the best stream-k/tiling choice",
   "implementation_ref": "ggml/src/ggml-cuda/mmq.cuh:1318-1366 @ a6a32c1; mmq-config-cdna.cuh 512/1/128 cells",
   "gap": "Our launcher always runs 104 stream-k blocks with no force-tiling or useful-work cap",
   "operational_change": "Port the stream-k cap and force-tiling rule to CDNA behind a default-off knob and screen it on gfx90a",
   "benefit_direction": "Higher MMQ throughput at 5-64 columns where the rule fires; MUL_MAT/MUL_MAT_ID correctness unchanged within test-backend-ops tolerance",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "Code on an experimental branch with a region-lock claim; one GPU row capped at 1 GPU-h; promotion is operator-only",
   "closure_basis": "Immediate; end-to-end 27B np4 / A3B pp512 row only on KEEP_CANDIDATE (trigger M1)"
  },
  "P3": {
   "project_objective": "AK keep decisions cannot be fed by zero/nonfinite timings or one-armed receipts, and fast-path routing is witnessable",
   "implementation_ref": "loop/bench.py:424, :642-694; loop/graph_profile_reader.py:45; loop/surface_fold.py:140-193; candidate_manifest.py:201-250",
   "gap": "Three ingestion paths accept or silently drop non-positive timings; receipts validated by digest only; no uniform decision record",
   "operational_change": "AutoKernel timing and receipt hygiene plus a dispatch decision-record spec",
   "benefit_direction": "Fewer invalid keeps and fewer rows closed for an absent witness; no kernel change",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "Code/doc only in epyc-inference-research and root handoffs; AK loop launch hold is unaffected (launch_only)",
   "closure_basis": "Immediate; provider registry declined"
  },
  "P4": {
   "project_objective": "Decide whether tool-supersession eviction is worth an arm in TOC-CMP-4, given what a mid-history cut costs on our devices",
   "implementation_ref": "orchestrator src/graph/helpers.py:558 (age-based clearing, default off); src/graph/context_arm_ab.py:16 arms; server-context.cpp:5126-5170 @ a6a32c1",
   "gap": "No supersession arm and no evict-cost model for llama-server; hybrid models re-prefill from the last checkpoint",
   "operational_change": "Measure supersession share offline and build an evict-cost probe before any eviction arm",
   "benefit_direction": "An eviction arm only if share and cost justify it; no serving change",
   "owner": "handoffs/active/context-and-token-economy.md",
   "execution_conditions": "Offline replay is code-only; one small CPU smoke for the probe; no production activation",
   "closure_basis": "Immediate; the TOC-CMP-4 arm and the Leyline splice are trigger-gated (M2, M3)"
  },
  "P5": {
   "project_objective": "Escalation from small to large Qwen roles happens when it pays, not by a fixed penalty",
   "implementation_ref": "orchestration/repl_memory/q_reward.py:173; src/orchestration/escalation.py:227-350; src/repl_environment/routing.py:303-319 (orchestrator @ 1a10541b as read by the dive; HEAD now 0a88d7bc)",
   "gap": "No learned or calibrated ask signal; fixed 0.15 penalty",
   "operational_change": "Calibrate ask/escalation from logs: counts, residual-risk probe, budget-priced penalty",
   "benefit_direction": "Better escalation timing at equal or fewer consults; no live routing change until a later box",
   "owner": "handoffs/active/routing-program.md",
   "execution_conditions": "Logs only; no training; DAR-LAT stays frozen",
   "closure_basis": "Immediate; J17 readouts and a trained ask policy are trigger-gated (M4)"
  },
  "P6": {
   "project_objective": "AutoPilot and HIL accept only mutations that generalise, with comparable budgets and auditable rounds",
   "implementation_ref": "autopilot-program.md:123 (BSV-2); docs/design/harness-improvement-loop-design-20261006.md HIL-2 checklist",
   "gap": "Accept is in-sample; no fresh-parent rule; no per-round status split",
   "operational_change": "Harden harness-evolution acceptance (disjoint tasks, fresh parent, sealed test, decision records)",
   "benefit_direction": "Fewer false accepts; AutoPilot stays stopped",
   "owner": "handoffs/active/autopilot-program.md",
   "execution_conditions": "Design plus offline replay of existing journals; zero inference",
   "closure_basis": "Immediate; local-improver Life-Harness run needs an operator choice (OD-2)"
  },
  "P7": {
   "project_objective": "Spend drafter work only where copy matches or coupling can still add acceptance",
   "implementation_ref": "common/speculative.cpp:2651-2812 @ a6a32c1 (ngram-mod); common/sampling.cpp:1020-1128 @ a6a32c1 (rejection sampling); artifacts/copyspec-20261006",
   "gap": "No exact longest-suffix coverage measurement; MTP T>0 acceptance gap unmeasured; no tree verification at T>0 and no served-temperature log",
   "operational_change": "Offline screens before copy-proposal, coupled-draw and sampled-tree (DICE) drafter work",
   "benefit_direction": "Close or open two drafter lanes on evidence; no serving change",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "SPEC-COPY-COV-1 offline; SPEC-DTREE-DICE step 1 is an orchestrator logging change, step 2a a CPU capture (A3B) then an MI210 capture-only row (27B, OD-5), step 2b offline; SPEC-COUPLE-MTP-1 reuses the step-2a capture; any GPU build row only on replay gains",
   "closure_basis": "Immediate; CoPyro arm, training-free copy probe, DTREE calibration refit and ReTrace arm are trigger-gated (M5-M7)"
  },
  "P10": {
   "project_objective": "Port the AITER v0.1.30 ideas that map to CDNA2 onto the served 27B/A3B verify path",
   "implementation_ref": "C18 27B DF2 verify trace ak-c18-27b-df2-v5i-trace-gpu-20261122 (40.07 ms/verify); ggml-cuda.cu:4252 @ a6a32c1; AITER @ 77ba72b7061a fused_gdn_decode_qkvz.py:61",
   "gap": "GDN beta/alpha projections and gate ops run as ~1.5 ms of small launches per 27B verify; per-channel int8 never measured on the verify GEMV",
   "operational_change": "AITER v0.1.30 reverse-engineering for gfx90a: GDN gate fold and per-channel int8 verify GEMV",
   "benefit_direction": "Lower 27B verify GPU time (trace budget 1.5-2.5 ms of 40 ms for the fold); KLD-gated numerics",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "Step 1 of each is trace arithmetic and source reads; GPU rows only past their step-1 futility gates; experimental branch, default-off knobs, promotion operator-only",
   "closure_basis": "Immediate; every other v0.1.30 family is FP8/MX/gfx950-only or already retargeted (K4)"
  },
  "P9": {
   "project_objective": "Handoff premises match hardware",
   "implementation_ref": "eval-tower-program.md:159-161 @ d785b6d",
   "gap": "says defer training to DGX Spark",
   "operational_change": "Fix the stale DGX premise",
   "benefit_direction": "no stale premise steers planning",
   "owner": "handoffs/active/eval-tower-program.md",
   "execution_conditions": "text-only box",
   "closure_basis": "Immediate"
  },
  "P8": {
   "project_objective": "Decide three upstream micro-ports on our own numbers",
   "implementation_ref": "mmid.cu:92, fattn-common.cuh:1493, fattn-gqa-verify.cu:769-781, src/llama-vocab.cpp:274 @ a6a32c1",
   "gap": "Upstream changes absent; their share of our time unmeasured",
   "operational_change": "Small kernel/host follow-ups: readlane arm, trace shares, tokenizer timing",
   "benefit_direction": "Port only what moves served time",
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "execution_conditions": "Readlane rides an existing gate row; the other two read existing traces or time the vocab only",
   "closure_basis": "Immediate; mbcnt port trigger-gated (M8)"
  },
  "M1": {
   "project_objective": "AK-MMQ-SK2 KEEP_CANDIDATE fires an end-to-end 27B np4 aggregate and A3B pp512 (ub 64 and 512) row in speculative-decoding.md; if arm B's only ISA failures are AGPR classes, timing B needs the same operator waiver AK-MMQ-H5 needed.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "AK-MMQ-SK2 KEEP_CANDIDATE fires an end-to-end 27B np4 aggregate and A3B pp512 (ub 64 and 512) row in speculative-decoding.md; if arm B's only ISA failures are AGPR classes, timing B needs the same operator waiver AK-MMQ-H5 needed.",
   "closure_basis": "AK-MMQ-SK2 KEEP_CANDIDATE fires an end-to-end 27B np4 aggregate and A3B pp512 (ub 64 and 512) row in speculative-decoding.md; if arm B's only ISA failures are AGPR classes, timing B needs the same operator waiver AK-MMQ-H5 needed."
  },
  "M2": {
   "project_objective": "TOC-SUPERSEDE-1 share >= 15% fires: add a supersession arm and an exploratory step_reduce arm (AgentDiet a=2, b=1) to the full TOC-CMP-4 pre-registration; the frozen pilot96 matrix is untouched.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/context-and-token-economy.md",
   "execution_conditions": "TOC-SUPERSEDE-1 share >= 15% fires: add a supersession arm and an exploratory step_reduce arm (AgentDiet a=2, b=1) to the full TOC-CMP-4 pre-registration; the frozen pilot96 matrix is untouched.",
   "closure_basis": "TOC-SUPERSEDE-1 share >= 15% fires: add a supersession arm and an exploratory step_reduce arm (AgentDiet a=2, b=1) to the full TOC-CMP-4 pre-registration; the frozen pilot96 matrix is untouched."
  },
  "M3": {
   "project_objective": "When KPF-62.6 runs its G3 harness, add a removed-span case (Leyline forget versus amortize) for dense-attention roles only; a default-off kv_splice request field follows only if that case passes. Rotate-only splice for GDN hybrids is declined.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/kv-cache-program.md",
   "execution_conditions": "When KPF-62.6 runs its G3 harness, add a removed-span case (Leyline forget versus amortize) for dense-attention roles only; a default-off kv_splice request field follows only if that case passes. Rotate-only splice for GDN hybrids is declined.",
   "closure_basis": "When KPF-62.6 runs its G3 harness, add a removed-span case (Leyline forget versus amortize) for dense-attention roles only; a default-off kv_splice request field follows only if that case passes. Rotate-only splice for GDN hybrids is declined."
  },
  "M4": {
   "project_objective": "RTG-ASK-1 probe beating entropy-only by >= 0.05 AUROC on holdout fires J17 ask-calibration readouts (entropy-only, heuristic, oracle-timing ceiling) in eval-tower-program.md and a design note for a trained ask policy costed from consultant_device_seconds.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/routing-program.md",
   "execution_conditions": "RTG-ASK-1 probe beating entropy-only by >= 0.05 AUROC on holdout fires J17 ask-calibration readouts (entropy-only, heuristic, oracle-timing ceiling) in eval-tower-program.md and a design note for a trained ask policy costed from consultant_device_seconds.",
   "closure_basis": "RTG-ASK-1 probe beating entropy-only by >= 0.05 AUROC on holdout fires J17 ask-calibration readouts (entropy-only, heuristic, oracle-timing ceiling) in eval-tower-program.md and a design note for a trained ask policy costed from consultant_device_seconds."
  },
  "M5": {
   "project_objective": "SPEC-COPY-COV-1 above threshold fires: an exact longest-match index as the proposal source for a default-off training-free copy-proposal probe on the DFlash2 weights (one GPU row), and a CoPyro arm in DF2-FT-1.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "SPEC-COPY-COV-1 above threshold fires: an exact longest-match index as the proposal source for a default-off training-free copy-proposal probe on the DFlash2 weights (one GPU row), and a CoPyro arm in DF2-FT-1.",
   "closure_basis": "SPEC-COPY-COV-1 above threshold fires: an exact longest-match index as the proposal source for a default-off training-free copy-proposal probe on the DFlash2 weights (one GPU row), and a CoPyro arm in DF2-FT-1."
  },
  "M6": {
   "project_objective": "DTREE-GDN-BATCH making T16 beat linear fires: a first-order DTREE acceptance-calibration refit on the dump (intake-2846). The DICE sampled-tree question is no longer gated here; it is SPEC-DTREE-DICE.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "DTREE-GDN-BATCH making T16 beat linear fires: a first-order DTREE acceptance-calibration refit on the dump (intake-2846). The DICE sampled-tree question is no longer gated here; it is SPEC-DTREE-DICE.",
   "closure_basis": "DTREE-GDN-BATCH making T16 beat linear fires: a first-order DTREE acceptance-calibration refit on the dump (intake-2846). The DICE sampled-tree question is no longer gated here; it is SPEC-DTREE-DICE."
  },
  "M7": {
   "project_objective": "intake-2848#record (ReTrace) and intake-2830#record (Vega-Fafnir) are PDF-only and stage1-unverified; when an HTML render appears or an operator hand-check passes, re-dive and reconsider a rejected-trajectory arm in DF2-FT-1 and the cache-rebuild findings.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "intake-2848#record (ReTrace) and intake-2830#record (Vega-Fafnir) are PDF-only and stage1-unverified; when an HTML render appears or an operator hand-check passes, re-dive and reconsider a rejected-trajectory arm in DF2-FT-1 and the cache-rebuild findings.",
   "closure_basis": "intake-2848#record (ReTrace) and intake-2830#record (Vega-Fafnir) are PDF-only and stage1-unverified; when an HTML render appears or an operator hand-check passes, re-dive and reconsider a rejected-trajectory arm in DF2-FT-1 and the cache-rebuild findings."
  },
  "M8": {
   "project_objective": "At MMID-HELPER-N10-GATE close, if the helper is still >= 3% of Q38FN pp2048 after the fold, port the mbcnt-based ballot rank (#32841 shape) to any ballot site that remains.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "execution_conditions": "At MMID-HELPER-N10-GATE close, if the helper is still >= 3% of Q38FN pp2048 after the fold, port the mbcnt-based ballot rank (#32841 shape) to any ballot site that remains.",
   "closure_basis": "At MMID-HELPER-N10-GATE close, if the helper is still >= 3% of Q38FN pp2048 after the fold, port the mbcnt-based ballot rank (#32841 shape) to any ballot site that remains."
  },
  "M9": {
   "project_objective": "MI210 post-training smoke (gfx90a venv, CreditFilter and AgentRL as consumers) waits on OD-1 and on E5 Stage-B releasing the host (the box at model-evaluation-queue.md:1259 is countermanded until then).",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/model-evaluation-queue.md",
   "execution_conditions": "MI210 post-training smoke (gfx90a venv, CreditFilter and AgentRL as consumers) waits on OD-1 and on E5 Stage-B releasing the host (the box at model-evaluation-queue.md:1259 is countermanded until then).",
   "closure_basis": "MI210 post-training smoke (gfx90a venv, CreditFilter and AgentRL as consumers) waits on OD-1 and on E5 Stage-B releasing the host (the box at model-evaluation-queue.md:1259 is countermanded until then)."
  },
  "M10": {
   "project_objective": "Operator approval of OD-2 fires the ALFWorld-only AgentBench smoke (AgentRL controller plus one worker, no Redis, local role via llama-server tool calls, 5 episodes) and the Life-Harness local-improver run.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/eval-tower-program.md",
   "execution_conditions": "Operator approval of OD-2 fires the ALFWorld-only AgentBench smoke (AgentRL controller plus one worker, no Redis, local role via llama-server tool calls, 5 episodes) and the Life-Harness local-improver run.",
   "closure_basis": "Operator approval of OD-2 fires the ALFWorld-only AgentBench smoke (AgentRL controller plus one worker, no Redis, local role via llama-server tool calls, 5 episodes) and the Life-Harness local-improver run."
  },
  "M13": {
   "project_objective": "Operator approval of OD-3 fires: wire lineage_capture at keep_the_diff behind a default-off flag.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "Operator approval of OD-3 fires: wire lineage_capture at keep_the_diff behind a default-off flag.",
   "closure_basis": "Operator approval of OD-3 fires: wire lineage_capture at keep_the_diff behind a default-off flag."
  },
  "M11": {
   "project_objective": "When RTE-LOG-1 (harness-program.md:519) lands prompt-structure logs: prefix-stability audit over all block kinds and a counterfactual batching B in {1,3,5} for the clearing pass.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/context-and-token-economy.md",
   "execution_conditions": "When RTE-LOG-1 (harness-program.md:519) lands prompt-structure logs: prefix-stability audit over all block kinds and a counterfactual batching B in {1,3,5} for the clearing pass.",
   "closure_basis": "When RTE-LOG-1 (harness-program.md:519) lands prompt-structure logs: prefix-stability audit over all block kinds and a counterfactual batching B in {1,3,5} for the clearing pass."
  },
  "M12": {
   "project_objective": "When the M-23 SkillBank A/B is next booked: add an executable-guard arm beside the text-skill arm (HookEvo scope C finding).",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "trigger not fired",
   "operational_change": "none now",
   "benefit_direction": "n/a until the trigger fires",
   "owner": "handoffs/active/memory-program.md",
   "execution_conditions": "When the M-23 SkillBank A/B is next booked: add an executable-guard arm beside the text-skill arm (HookEvo scope C finding).",
   "closure_basis": "When the M-23 SkillBank A/B is next booked: add an executable-guard arm beside the text-skill arm (HookEvo scope C finding)."
  },
  "K1": {
   "project_objective": "The 1 - TV ceiling (intake-2845#record) is a single-draft, per-position bound. It closes coupled-draw verification only on single-path chains, where the served DFlash2 rejection path at T > 0 already reaches it (common/sampling.cpp:1020-1128 @ a6a32c1). It does not close tree or multi-candidate verification, where k-candidate verifiers beat the standard one at T > 0 (intake-2846#02, intake-2715#00), so DICE on DFlash2/MTP trees at served T is open under SPEC-DTREE-DICE. Production serves at T > 0 (role defaults 0.1-0.3; :8083 direct agent traffic at 1.0), so 'no gain at T = 0' closes nothing. SPEC-RNG.1 DO-NOT-CARRY still records the keyed-RNG drafter-invariance variant.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "none: knowledge retained",
   "operational_change": "none now",
   "benefit_direction": "informs planning",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "The 1 - TV ceiling (intake-2845#record) is a single-draft, per-position bound. It closes coupled-draw verification only on single-path chains, where the served DFlash2 rejection path at T > 0 already reaches it (common/sampling.cpp:1020-1128 @ a6a32c1). It does not close tree or multi-candidate verification, where k-candidate verifiers beat the standard one at T > 0 (intake-2846#02, intake-2715#00), so DICE on DFlash2/MTP trees at served T is open under SPEC-DTREE-DICE. Production serves at T > 0 (role defaults 0.1-0.3; :8083 direct agent traffic at 1.0), so 'no gain at T = 0' closes nothing. SPEC-RNG.1 DO-NOT-CARRY still records the keyed-RNG drafter-invariance variant.",
   "closure_basis": "The 1 - TV ceiling (intake-2845#record) is a single-draft, per-position bound. It closes coupled-draw verification only on single-path chains, where the served DFlash2 rejection path at T > 0 already reaches it (common/sampling.cpp:1020-1128 @ a6a32c1). It does not close tree or multi-candidate verification, where k-candidate verifiers beat the standard one at T > 0 (intake-2846#02, intake-2715#00), so DICE on DFlash2/MTP trees at served T is open under SPEC-DTREE-DICE. Production serves at T > 0 (role defaults 0.1-0.3; :8083 direct agent traffic at 1.0), so 'no gain at T = 0' closes nothing. SPEC-RNG.1 DO-NOT-CARRY still records the keyed-RNG drafter-invariance variant."
  },
  "K2": {
   "project_objective": "#30022's own author found no CDNA gain and #30553's cap is a no-op on our dense served shapes (nwork 160-2720 versus 104 blocks); both are inputs to AK-MMQ-SK2, not separate ports.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "none: knowledge retained",
   "operational_change": "none now",
   "benefit_direction": "informs planning",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "#30022's own author found no CDNA gain and #30553's cap is a no-op on our dense served shapes (nwork 160-2720 versus 104 blocks); both are inputs to AK-MMQ-SK2, not separate ports.",
   "closure_basis": "#30022's own author found no CDNA gain and #30553's cap is a no-op on our dense served shapes (nwork 160-2720 versus 104 blocks); both are inputs to AK-MMQ-SK2, not separate ports."
  },
  "K3": {
   "project_objective": "Contexture's +20-73% headline and energy figure are H100/H200 vLLM numbers and do not transfer; only the supersession rule and the cold-commit cost model are used.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "none: knowledge retained",
   "operational_change": "none now",
   "benefit_direction": "informs planning",
   "owner": "handoffs/active/context-and-token-economy.md",
   "execution_conditions": "Contexture's +20-73% headline and energy figure are H100/H200 vLLM numbers and do not transfer; only the supersession rule and the cold-commit cost model are used.",
   "closure_basis": "Contexture's +20-73% headline and energy figure are H100/H200 vLLM numbers and do not transfer; only the supersession rule and the cold-commit cost model are used."
  },
  "K4": {
   "project_objective": "AITER v0.1.30's wheels and new kernels target gfx942/gfx950/gfx1250, and every CDNA2-portable family was already retargeted and timed on the MI210 (AK-ASM-H1..H15, AK-ASM-PORT-*, AK-MMID-MF, C8-6); its split-K reduce widening was tried as GGML_HIP_FA_TAIL_SPLIT (FUTILITY). The new served-path ideas are its GDN input fold and per-channel int8 weights, filed as AK-BW-GDN-GATE-FOLD and AK-ASM-I8GEMM-PERCHANNEL-GEMV; FP8/MX/NVFP4, MLA, gfx950 MTP4 tiles and kernarg preload do not map to gfx90a.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "none: knowledge retained",
   "operational_change": "none now",
   "benefit_direction": "informs planning",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "AITER v0.1.30's wheels and new kernels target gfx942/gfx950/gfx1250, and every CDNA2-portable family was already retargeted and timed on the MI210 (AK-ASM-H1..H15, AK-ASM-PORT-*, AK-MMID-MF, C8-6); its split-K reduce widening was tried as GGML_HIP_FA_TAIL_SPLIT (FUTILITY). The new served-path ideas are its GDN input fold and per-channel int8 weights, filed as AK-BW-GDN-GATE-FOLD and AK-ASM-I8GEMM-PERCHANNEL-GEMV; FP8/MX/NVFP4, MLA, gfx950 MTP4 tiles and kernarg preload do not map to gfx90a.",
   "closure_basis": "AITER v0.1.30's wheels and new kernels target gfx942/gfx950/gfx1250, and every CDNA2-portable family was already retargeted and timed on the MI210 (AK-ASM-H1..H15, AK-ASM-PORT-*, AK-MMID-MF, C8-6); its split-K reduce widening was tried as GGML_HIP_FA_TAIL_SPLIT (FUTILITY). The new served-path ideas are its GDN input fold and per-channel int8 weights, filed as AK-BW-GDN-GATE-FOLD and AK-ASM-I8GEMM-PERCHANNEL-GEMV; FP8/MX/NVFP4, MLA, gfx950 MTP4 tiles and kernarg preload do not map to gfx90a."
  },
  "K6": {
   "project_objective": "Second-reader disagreements: 18 of 409 anchors judged no (listed in OD-4); never auto-overturned.",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "none: knowledge retained",
   "operational_change": "none now",
   "benefit_direction": "informs planning",
   "owner": "handoffs/active/vidya-belief-substrate-program.md",
   "execution_conditions": "Second-reader disagreements: 18 of 409 anchors judged no (listed in OD-4); never auto-overturned.",
   "closure_basis": "Second-reader disagreements: 18 of 409 anchors judged no (listed in OD-4); never auto-overturned."
  },
  "K5": {
   "project_objective": "CreditFilter's gains are single-turn math, full-parameter RL on Qwen3-8B-Base, three data-order seeds, MATH500 margin carried by one collapsed DAPO run (intake-2834).",
   "implementation_ref": "see the recommendation basis and cited entries",
   "gap": "none: knowledge retained",
   "operational_change": "none now",
   "benefit_direction": "informs planning",
   "owner": "handoffs/active/model-evaluation-queue.md",
   "execution_conditions": "CreditFilter's gains are single-turn math, full-parameter RL on Qwen3-8B-Base, three data-order seeds, MATH500 margin carried by one collapsed DAPO run (intake-2834).",
   "closure_basis": "CreditFilter's gains are single-turn math, full-parameter RL on Qwen3-8B-Base, three data-order seeds, MATH500 margin carried by one collapsed DAPO run (intake-2834)."
  }
 },
 "actionable_additions": [
  {
   "ledger_id": "AKI-01",
   "source": "intake-2844 dive (B1) + intake-2830 A4",
   "action": "Write test-multiseq-ragged-rollback before booking the C18 bisect",
   "terminal_mapping": "P1 / SPEC-ID-RAGGED-1"
  },
  {
   "ledger_id": "AKI-02",
   "source": "intake-2830 A2/A3 + intake-2842 V1/V2 + intake-2844 B2/B3",
   "action": "Width-aware identity protocol; re-judge CAFE-1; recommend on CAFE-3 done-when",
   "terminal_mapping": "P1 / SPEC-ID-GATE-1"
  },
  {
   "ledger_id": "AKI-03",
   "source": "intake-2830 A1 + intake-2842 V3",
   "action": "Measure width-1 versus width-W noise to set tau, with zero-margin share",
   "terminal_mapping": "P1 / SPEC-ID-NOISE-1"
  },
  {
   "ledger_id": "AKI-04",
   "source": "intake-2830 A4 + intake-2843 L3",
   "action": "GPU redecode versus serial arm, pre-registered to fail",
   "terminal_mapping": "P1 / SPEC-ID-NOISE-1"
  },
  {
   "ledger_id": "AKI-05",
   "source": "intake-2843 L1",
   "action": "Position-invariance unit test for GGML_DETERMINISTIC",
   "terminal_mapping": "P1 / GGML-DET-POSINV-TEST"
  },
  {
   "ledger_id": "AKI-06",
   "source": "intake-2843 L2",
   "action": "Report first-divergence hazard per token-at-risk as a rate ratio in the C18 bisect",
   "terminal_mapping": "P1 / SPEC-ID-GATE-1"
  },
  {
   "ledger_id": "AKI-07",
   "source": "intake-2830 decline",
   "action": "Serve a rebuild gate or fixed-shape verify for exactness",
   "terminal_mapping": "decline: production samples at T > 0, and the cheaper opt-in GGML_ROWEXACT_N already exists for CPU exactness"
  },
  {
   "ledger_id": "AKI-08",
   "source": "intake-2843 decline",
   "action": "Build decode-verify-rollback or a per-request determinism flag",
   "terminal_mapping": "decline: gates already run one request per fresh server and the batch-invariance premise fails on the MI210 atomics paths"
  },
  {
   "ledger_id": "AKI-09",
   "source": "intake-2844 decline",
   "action": "EqSpec/EXSpec realignment or batch-invariant mode as an np4 fix",
   "terminal_mapping": "decline: llama.cpp's cell-indexed KV has no rectangular batch to realign"
  },
  {
   "ledger_id": "AKI-10",
   "source": "intake-2824 row 1 + intake-2837 row 1 + intake-2838 rows 1-2",
   "action": "Port #30553 cap and #30022 force-tiling widened to CDNA, add #32837 table arm, census and screen on gfx90a",
   "terminal_mapping": "P2 / AK-MMQ-SK2"
  },
  {
   "ledger_id": "AKI-11",
   "source": "intake-2838 row 3",
   "action": "State that bit-identity versus C19 is not expected after a grid change",
   "terminal_mapping": "P2 / AK-MMQ-SK2"
  },
  {
   "ledger_id": "AKI-12",
   "source": "intake-2824 row 2",
   "action": "End-to-end 27B np4 and A3B pp512 row after a kernel keep",
   "terminal_mapping": "M1"
  },
  {
   "ledger_id": "AKI-13",
   "source": "intake-2824 decline",
   "action": "End-to-end probe at the served 27B np1 point",
   "terminal_mapping": "decline: MMQ is about 0.9% of 27B np1 kernel time, so no speedup can clear a 1% floor"
  },
  {
   "ledger_id": "AKI-14",
   "source": "intake-2824 decline",
   "action": "Port the stream-k rule to Zen 5",
   "terminal_mapping": "decline: ggml-cpu has no split-K/fixup stage or LDS-occupancy knob"
  },
  {
   "ledger_id": "AKI-15",
   "source": "intake-2837 + intake-2838 doc rows",
   "action": "Record the dense-shape prior near zero and the cap no-op",
   "terminal_mapping": "K2"
  },
  {
   "ledger_id": "AKI-16",
   "source": "intake-2837 decline",
   "action": "Port the GCN table, grid and fixup pieces",
   "terminal_mapping": "decline: gated on GCN, which the MI210 is not"
  },
  {
   "ledger_id": "AKI-17",
   "source": "intake-2828 row 1",
   "action": "FAIL-on-zero/NaN timing ingestion with tests",
   "terminal_mapping": "P3 / AK-TIMING-ZERO-1"
  },
  {
   "ledger_id": "AKI-18",
   "source": "intake-2828 row 3 + intake-2839 row 1 + intake-2841 row 3",
   "action": "Shared both-arms receipt validator, all-or-none comparison, perf fields by the measuring step only",
   "terminal_mapping": "P3 / AK-RECEIPT-ARMS-1"
  },
  {
   "ledger_id": "AKI-19",
   "source": "intake-2839 row 3",
   "action": "Bind an authorising-act reference to each candidate",
   "terminal_mapping": "P3 / AK-RECEIPT-ARMS-1"
  },
  {
   "ledger_id": "AKI-20",
   "source": "intake-2828 row 2 + intake-2839 rows 2,4",
   "action": "Spec a uniform fast-path decision record and a no-fallback-after-launch audit",
   "terminal_mapping": "P3 / RKA-DECISION-RECORD-1"
  },
  {
   "ledger_id": "AKI-21",
   "source": "intake-2839 row 5",
   "action": "HIP-graph first-call note",
   "terminal_mapping": "P3 / RKA-DECISION-RECORD-1"
  },
  {
   "ledger_id": "AKI-22",
   "source": "intake-2828 row 4",
   "action": "Check test-backend-ops id-compare exactness",
   "terminal_mapping": "P2 / AK-MMQ-SK2"
  },
  {
   "ledger_id": "AKI-23",
   "source": "intake-2828 row 5 + rev-1 AITER source read",
   "action": "Folded split-K ba partials summed inside the GDN kernel (concrete AITER design, fused_gdn_decode_qkvz.py:61)",
   "terminal_mapping": "P10 / AK-BW-GDN-GATE-FOLD"
  },
  {
   "ledger_id": "AKI-24",
   "source": "intake-2828/2839 decline",
   "action": "Provider registry with enable-order priority or measured selection among providers",
   "terminal_mapping": "decline: one champion is the single source of dispatch truth"
  },
  {
   "ledger_id": "AKI-25",
   "source": "intake-2841 rows 1-2",
   "action": "CU-mask concurrent stress arm; actor-context ablation",
   "terminal_mapping": "decline: no current AK candidate has inter-workgroup waits; the ablation is a loop launch under the operator hold"
  },
  {
   "ledger_id": "AKI-26",
   "source": "intake-2841 row 4",
   "action": "Wire lineage_capture at keep_the_diff behind a flag",
   "terminal_mapping": "M13"
  },
  {
   "ledger_id": "AKI-27",
   "source": "intake-2833 C1 + intake-2853 AD-3 + intake-2851 TP-3 + intake-2852 PI-1",
   "action": "Offline supersession classifier replay with dedup and regret counts",
   "terminal_mapping": "P4 / TOC-SUPERSEDE-1"
  },
  {
   "ledger_id": "AKI-28",
   "source": "intake-2833 C2 + intake-2853 AD-1",
   "action": "Supersession and step_reduce arms in TOC-CMP-4",
   "terminal_mapping": "M2"
  },
  {
   "ledger_id": "AKI-29",
   "source": "intake-2833 C3/C4 + intake-2850 SA-1/SA-2 + intake-2849 LL-4 + intake-2853 AD-2",
   "action": "Evict-cost probe, checkpoint-alignment classes and device break-even table",
   "terminal_mapping": "P4 / KV-EVICT-COST-1"
  },
  {
   "ledger_id": "AKI-30",
   "source": "intake-2833 C5 + intake-2851 TP-1/TP-2",
   "action": "Prefix-stability audit and batching counterfactual from prompt-layout logs",
   "terminal_mapping": "M11"
  },
  {
   "ledger_id": "AKI-31",
   "source": "intake-2849 LL-1/LL-2",
   "action": "Removed-span case in KPF-62 G3 and a default-off kv_splice field",
   "terminal_mapping": "M3"
  },
  {
   "ledger_id": "AKI-32",
   "source": "intake-2850 SA-3",
   "action": "Fork-based pre-warm prototype",
   "terminal_mapping": "decline: re-prefill slack for supersession is only the tool's execution time, and no measured idle-gap distribution exists yet"
  },
  {
   "ledger_id": "AKI-33",
   "source": "intake-2833 C6/C7 + intake-2849 LL-3 + intake-2850 SA-4 + intake-2851 TP-4 + intake-2852 PI-3 + intake-2853 AD-4",
   "action": "CPU pressure gate, energy metric, GDN rotate splice, offloading, LLM estimator, phantom tools, default in-place rewrite",
   "terminal_mapping": "decline: each rests on a premise our hosts or models do not meet"
  },
  {
   "ledger_id": "AKI-34",
   "source": "intake-2833 headline",
   "action": "Use the paper's throughput and energy numbers for planning",
   "terminal_mapping": "K3"
  },
  {
   "ledger_id": "AKI-35",
   "source": "intake-2835 A1/A2 + intake-2855 R1 + intake-2856 G1",
   "action": "Per-role ask counts, residual-risk probe versus entropy-only, budget-priced penalty replay",
   "terminal_mapping": "P5 / RTG-ASK-1"
  },
  {
   "ledger_id": "AKI-36",
   "source": "intake-2835 A3 + intake-2855 R2",
   "action": "J17 ask-calibration readouts with an oracle-timing ceiling",
   "terminal_mapping": "M4"
  },
  {
   "ledger_id": "AKI-37",
   "source": "intake-2835 A4/A5 + intake-2855 R3",
   "action": "Design note on a trained ask policy and escalate-versus-consult primitives",
   "terminal_mapping": "P5 / RTG-ASK-1"
  },
  {
   "ledger_id": "AKI-38",
   "source": "intake-2855 R4/R5 + intake-2856 G4",
   "action": "Reproduce R2V or AgentRL headline numbers; CVaR",
   "terminal_mapping": "decline: R2V has no code and AgentRL's recipe needs 16 H800"
  },
  {
   "ledger_id": "AKI-39",
   "source": "intake-2856 G2 + intake-2860 AB1/AB2",
   "action": "ALFWorld-only AgentBench smoke driving a local role",
   "terminal_mapping": "M10"
  },
  {
   "ledger_id": "AKI-40",
   "source": "intake-2860 AB3",
   "action": "KG and WebShop workers",
   "terminal_mapping": "decline: no ledger row consumes them"
  },
  {
   "ledger_id": "AKI-41",
   "source": "intake-2836 H1 + intake-2857 HR2 + intake-2859 PR1/PR4 + intake-2862 PR4a + intake-2858 LH2",
   "action": "Disjoint-task accept, fresh parent, sealed test, decision record with status split, matched budget",
   "terminal_mapping": "P6 / AP-BSV2-ACCEPT-RIGOR"
  },
  {
   "ledger_id": "AKI-42",
   "source": "intake-2857 HR1/HR3 + intake-2858 LH1/LH3 + intake-2859 PR3",
   "action": "HIL-2 checklist cases, taxonomy, validity gate, install envelope",
   "terminal_mapping": "P6 / HIL-EVO-CASES-1"
  },
  {
   "ledger_id": "AKI-43",
   "source": "intake-2836 H2 + intake-2859 PR2 + intake-2862 PR2a",
   "action": "Map hook events and a versioned plugin manifest onto AP-DGM-PROV",
   "terminal_mapping": "P6 / AP-BSV2-ACCEPT-RIGOR"
  },
  {
   "ledger_id": "AKI-44",
   "source": "intake-2836 H3",
   "action": "Executable-guard arm beside the text-skill arm in the SkillBank A/B",
   "terminal_mapping": "M12"
  },
  {
   "ledger_id": "AKI-45",
   "source": "intake-2858 LH4 + intake-2861 LH4a-c",
   "action": "Life-Harness evolve-from-scratch with a local improver",
   "terminal_mapping": "M10"
  },
  {
   "ledger_id": "AKI-46",
   "source": "intake-2857 HR4",
   "action": "No-model HookEvo smoke",
   "terminal_mapping": "decline: it exercises a JavaScript runtime we do not use"
  },
  {
   "ledger_id": "AKI-47",
   "source": "intake-2836 H4 + intake-2857 HR5/HR6 + intake-2858 LH5 + intake-2859 PR5 + intake-2861 LH4d + intake-2862 PR6",
   "action": "Reproduce headline numbers, vendor packages, copy slot/quota-hold",
   "terminal_mapping": "decline: they measure other harnesses; rowflow already covers slots"
  },
  {
   "ledger_id": "AKI-48",
   "source": "intake-2847 S1 + intake-2832 A1 gate",
   "action": "Exact longest-suffix coverage curve over COPYSPEC P1 outputs",
   "terminal_mapping": "P7 / SPEC-COPY-COV-1"
  },
  {
   "ledger_id": "AKI-49",
   "source": "intake-2832 A1/A2 + intake-2847 S2",
   "action": "Training-free copy-proposal probe and CoPyro arm in DF2-FT-1",
   "terminal_mapping": "M5"
  },
  {
   "ledger_id": "AKI-50",
   "source": "intake-2845 D2 + intake-2831 A1 + rev-1 code read",
   "action": "Bound the MTP gap (draft distribution via the rejection path, or coupling) at every served T including 1.0",
   "terminal_mapping": "P7 / SPEC-COUPLE-MTP-1"
  },
  {
   "ledger_id": "AKI-51",
   "source": "intake-2845 D1/D3 + intake-2831 A2 + operator review 2026-11-23",
   "action": "The 1-TV theorem closes coupled-draw CHAIN verification only; DICE and Gumbel-max target sampling on trees at served T are falsified offline",
   "terminal_mapping": "P7 / SPEC-DTREE-DICE"
  },
  {
   "ledger_id": "AKI-52",
   "source": "intake-2831 A1 + operator review 2026-11-23",
   "action": "Measure the sampled share of served traffic, then replay DICE node selection offline for acceptance gains; GPU row only on gains",
   "terminal_mapping": "P7 / SPEC-DTREE-DICE"
  },
  {
   "ledger_id": "AKI-68",
   "source": "intake-2846 K1",
   "action": "First-order DTREE acceptance-calibration refit",
   "terminal_mapping": "M6"
  },
  {
   "ledger_id": "AKI-69",
   "source": "intake-2846#02 + rev-1 theory read",
   "action": "Exponential-race verifier for k >= 3 siblings and multi-draft coupling on trees",
   "terminal_mapping": "P7 / SPEC-DTREE-DICE"
  },
  {
   "ledger_id": "AKI-70",
   "source": "rev-1 AITER source read (fused_gdn_decode_qkvz.py, fused_gemm_a16w16_dual_splitk.py)",
   "action": "Fold GDN beta/alpha projections and gate math into the recurrence kernel",
   "terminal_mapping": "P10 / AK-BW-GDN-GATE-FOLD"
  },
  {
   "ledger_id": "AKI-71",
   "source": "rev-1 AITER source read (per-channel int8 GEMMs) + AK-ASM-I8GEMM-PERCHANNEL",
   "action": "Per-channel int8 weights on the bandwidth-bound verify GEMV",
   "terminal_mapping": "P10 / AK-ASM-I8GEMM-PERCHANNEL-GEMV"
  },
  {
   "ledger_id": "AKI-72",
   "source": "rev-1 AITER non-candidates",
   "action": "Port the remaining v0.1.30 families (FP8/MX/NVFP4, MLA, gfx950 MTP4 tile, kernarg preload, gfx1201 small-m fmoe, sort pad-id fix)",
   "terminal_mapping": "decline: FP8/MX hardware absent on gfx90a, gfx940+ ISA, or already retargeted, tried or absent from our path"
  },
  {
   "ledger_id": "AKI-73",
   "source": "rev-1 theory read",
   "action": "Scope intake-2845's 'never beats rejection sampling' claim to per position, single draft",
   "terminal_mapping": "K1"
  },
  {
   "ledger_id": "AKI-53",
   "source": "intake-2848 R1/R2",
   "action": "ReTrace rank-coverage probe and arm",
   "terminal_mapping": "M7"
  },
  {
   "ledger_id": "AKI-54",
   "source": "intake-2832/2847 declines",
   "action": "Revive n-gram composition or serve SAM-Decoding standalone",
   "terminal_mapping": "decline: composition measured a loss on the 27B MI210 and the registry bans it"
  },
  {
   "ledger_id": "AKI-55",
   "source": "intake-2834 C5",
   "action": "Entropy-rank bands of DFlash2 rejections",
   "terminal_mapping": "decline: hypothesis with no source support"
  },
  {
   "ledger_id": "AKI-56",
   "source": "intake-2825 row 1",
   "action": "Readlane arm at mmid.cu:92 in the MMID-HELPER-N10-GATE build",
   "terminal_mapping": "P8 / MMID-HELPER-READLANE"
  },
  {
   "ledger_id": "AKI-57",
   "source": "intake-2825 rows 2-3 + intake-2826 row 2 + intake-2827 row 2",
   "action": "Port the topk-moe, GDN-MMA, mm_ids_helper<16 or 32> hunks or a standalone mbcnt helper",
   "terminal_mapping": "decline: none of these sites exists on our served path"
  },
  {
   "ledger_id": "AKI-58",
   "source": "intake-2827 row 1",
   "action": "mbcnt rank port at MMID-HELPER-N10-GATE close",
   "terminal_mapping": "M8"
  },
  {
   "ledger_id": "AKI-59",
   "source": "intake-2826 row 1 + intake-2840 rows 1-2",
   "action": "flash_attn_mask_to_KV_max prefill share; np4 live-chunk max/mean",
   "terminal_mapping": "P8 / RKA-TRACE-SHARES-1"
  },
  {
   "ledger_id": "AKI-60",
   "source": "intake-2840 declines",
   "action": "gv merge skip, FP8/MX/K32/kernarg pieces, n=1 planner",
   "terminal_mapping": "decline: FP8/MX-dependent, nearly moot in gv, or unserved n=1"
  },
  {
   "ledger_id": "AKI-61",
   "source": "intake-2829 P1-P3",
   "action": "Time vocab-only tokenization of a 100k prompt; port #32859 only if >= 2% of cached-turn TTFT",
   "terminal_mapping": "P8 / TOK-BPE-TIME-1"
  },
  {
   "ledger_id": "AKI-62",
   "source": "intake-2829 P4",
   "action": "Treat #32859 as a cold-prefill TTFT item",
   "terminal_mapping": "decline: tokenization is 3-4 orders of magnitude below cold 100k prefill"
  },
  {
   "ledger_id": "AKI-63",
   "source": "intake-2834 C1/C4 + intake-2854 CR1-CR4 + intake-2856 G3",
   "action": "MI210 gfx90a training-viability smoke with CreditFilter and AgentRL as consumers",
   "terminal_mapping": "M9"
  },
  {
   "ledger_id": "AKI-64",
   "source": "intake-2834 C2",
   "action": "Fix the stale DGX premise in eval-tower-program.md:159-161",
   "terminal_mapping": "P9 / EVT-DGX-PREMISE-FIX"
  },
  {
   "ledger_id": "AKI-65",
   "source": "intake-2834 C3",
   "action": "Record CreditFilter's tested scope",
   "terminal_mapping": "K5"
  },
  {
   "ledger_id": "AKI-66",
   "source": "intake-2830/2848 PDF-only",
   "action": "Hand-check PDF quotes so Vega-Fafnir and ReTrace can be cited",
   "terminal_mapping": "M7"
  },
  {
   "ledger_id": "AKI-67",
   "source": "second reader",
   "action": "18 anchor rows where the second reader answered no",
   "terminal_mapping": "K6"
  }
 ],
 "steering_reconciliation": [
  {
   "seq": 1,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "The operator has pre-authorized: \"Automatically accept every recommended deep dive and literature expansion for up to four Stage 2 sweeps.\" So run Stage 2 sweeps without pausing, up to 4.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied as the dive set: all 13 sources dived, two Stage-2b waves (wave 2 surfaced nothing further); not a filing authority."
  },
  {
   "seq": 2,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "STOP at the end of Stage 3 and hand back the Stage 3 plan for operator review. Do NOT apply Stage 4 handoff changes, and do not write index rows or boxes, without the operator's approval.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied: this plan is handed back before any Stage-4 write."
  },
  {
   "seq": 3,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "llama.cpp PR #32837 (open): HIP CDNA1 MMQ uses stream-k only where beneficial (GCN path) plus table retune. MI100: gemma4 26B.A4B Q6_K pp512 ub64 800.18 -> 1152.33 t/s (1.44x); gpt-oss 20B MXFP4 ub64 1112.41 -> 1491.87 (1.34x); ub512 gains ~1.00-1.26x. Targets gfx908 (CDNA1); not gfx90a as written. Value: small-ubatch MMQ for DFlash2/MTP verify (INF-50) and the DF2-11 Q4_K -> MMQ path; AutoKernel knob candidate. Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4). (Specifically: the stream-k on/off dispatch rule by ubatch and the MMQ tile table entries for gfx90a.)",
   "disposition": "planned",
   "plan_ref": "P2",
   "reason": "Folded into P2; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 4,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "llama.cpp PR #32839 (open): HIP v_readlane_b32 instead of ds_bpermute_b32 for uniform-source shuffles. topk_moe up to -3.43% ns/dispatch, -1.17% global over 216 dispatches; rank kernel 37 -> 33 ISA instructions; 14 -> 11 per loop iteration. GPU not stated; generic AMDGCN wave64, applies to gfx90a. Value: MoE top-k and GDN reduction micro-opts for the fork; AutoKernel ISA-level candidate.",
   "disposition": "planned",
   "plan_ref": "P8",
   "reason": "Folded into P8; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 5,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "llama.cpp PR #32840 (open): ballot + lane shift replaces the shfl_xor ladder in warp_reduce_all/any for width 16/32. No numbers in the PR. AMDGCN, applies to gfx90a. Value: same lane as #32839; fold into AutoKernel reduction primitives.",
   "disposition": "planned",
   "plan_ref": "P8",
   "reason": "Folded into P8; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 6,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "llama.cpp PR #32841 (open): v_mbcnt_lo/hi for ballot rank instead of mask + popcount. VGPR 6 -> 4, ISA 29 -> 26, rank calc 5 -> 2 instructions. AMDGCN wave64, applies to gfx90a. Value: register pressure in top-k/MoE routing kernels.",
   "disposition": "planned",
   "plan_ref": "M8",
   "reason": "Folded into M8; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 7,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "ROCm AITER v0.1.30: weekly release; wheels GPU_ARCHS=gfx942;gfx950 (ROCm 7.2/7.14/10.0/10.1); changes mostly gfx950/gfx1250 (FlyDSL MoE, Conv3d), RFC #7240 kernel provider interface (configuration, priority, provenance, observability), tuner rejects zero timing measurements. Does not run on gfx90a. Previous v0.1.29 is already in the KB. Value: AutoKernel provider/lineage registry design and timing-gate hygiene. Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4). (Specifically: provider priority/provenance dispatch and the zero-timing rejection rule; MoE sorting changes only if not MX/FP8-dependent.)",
   "disposition": "planned",
   "plan_ref": "P3",
   "reason": "Folded into P3; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 8,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "llama.cpp PR #32859 (open): BPE tokenization with zero heap allocations per rank lookup. 145.8 KB text: gemma-4 71.6 -> 34.4 ms; qwen2 35.4 -> 18.2 ms; llama-bpe 21.0 -> 12.7 ms; identical token ids. Host-side CPU, applies to EPYC. Value: prompt-ingest latency for long-context requests in the orchestrator.",
   "disposition": "planned",
   "plan_ref": "P8",
   "reason": "Folded into P8; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 9,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "Vega-Fafnir (arXiv 2611.27554): Qwen3-0.6B bf16, 128 tokens: verify-4 changes 60% of 150 prompts, padding 68%; every first divergence has top-1/top-2 gap <= 0.375; margin gate 58/100 vs 61/100; one-token cache rebuild 0/100 at 7.2 passes/token; fixed-width decoding 0/100 at 0.75 passes/token. Single GPU, small models; method hardware-agnostic. Value: DF2-13-ATTRIB near-tie flips, C19 argmax-tie fix, KLD gates, lossless-spec determinism in INF-50.",
   "disposition": "planned",
   "plan_ref": "P1",
   "reason": "Folded into P1; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 10,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "DICE (arXiv 2611.27891): pre-samples and synchronizes verification randomness to steer draft-tree node selection and async prefetch; up to 24.6% throughput over strong baselines, no drafter retraining. Hardware not stated in the abstract; algorithmic, portable to llama.cpp. Value: DTREE device-side tree accept node budget (T12/T16), sampled-mode spec decoding.",
   "disposition": "planned",
   "plan_ref": "P7",
   "reason": "Folded into P7; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 11,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "CoPyro (arXiv 2611.27217): feeds n-gram copy proposals into parallel (DFlash-style) drafters in place of masks; Qwen3-4B acceptance length +2.19-5.08% (100K-sample training, 4 drafters), +1.08-2.00% with DFlash trained on 710K samples; +0.24 ms/round on Qwen3-8B in Transformers. Algorithmic, portable to the fork. Value: INF-50 DFlash2 drafter input; combines with existing n-gram/lookup drafting.",
   "disposition": "planned",
   "plan_ref": "P7",
   "reason": "Folded into P7; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 12,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "Contexture (arXiv 2611.26980): tool-supersession-based runtime context eviction; 64% of final-history tokens are removal candidates; throughput under SLO +20-73% vs best of no eviction/harness compaction/AgentDiet/Continuum, +7-63% vs observation masking in 5 of 8 configs, +23% vs LMCache on H100; up to 11% less GPU energy per session. Built for H100 HBM; the policy layer is host-side. Value: orchestrator prefix-cache layout flags, toc-cmp context compaction, KV pressure on EPYC RAM. Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules. Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4). (Specifically: the supersession rule plus the re-prefill-vs-evict cost decision under NPS4 memory placement.)",
   "disposition": "planned",
   "plan_ref": "P4",
   "reason": "Folded into P4; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 13,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "CreditFilter (arXiv 2611.27227): within-response entropy-rank token weighting for critic-free RLVR, no extra forward passes; 3-seed average +7.7 MATH500, +10.5 AIME24, +9.1 AIME25 over DAPO; code public. Training-side; usable for local Qwen GRPO/DAPO runs. Value: post-training lane for local Qwen models.",
   "disposition": "planned",
   "plan_ref": "M9",
   "reason": "Folded into M9; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 14,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "ADAPT (arXiv 2611.27443): advisor-aware post-training for SLM agents from own rollouts and outcome supervision; TextWorld 24.5 -> 77.3%, LiveCodeBench 21.8 -> 56.0%, GAIA 17.5 -> 49.3% with ~1.0-2.1 advisor calls per task; closes 70-85% of gap to the oracle on long-horizon tasks. Hardware-agnostic. Value: orchestrator routing/escalation policy (small -> large Qwen), MemRL reward shaping.",
   "disposition": "planned",
   "plan_ref": "P5",
   "reason": "Folded into P5; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 15,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "HookEvo (arXiv 2611.27294): evolves task-specific harness plugins via runtime lifecycle hooks with matched-task retention; frozen Qwen3-4B executor: ALFWorld 95.41%, DBBench 70.56%, WebShop 48.17%, OSBench 41.67%. Hardware-agnostic. Value: evolutionary harness and skill-bank optimization, AutoPilot harness search, eval rigor via matched-task acceptance.",
   "disposition": "planned",
   "plan_ref": "P6",
   "reason": "Folded into P6; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 16,
   "stage": 1,
   "ts": "2026-11-23T09:45:00Z",
   "verbatim": "Session context for Stage 3 grounding (verify every claim against the repo): C19 candidate on fork llama.cpp-experimental-c19-20261123 @ a6a32c135. It folds GDN fused+dispatch (default on), the CPU argmax tie fix, IQ3_XXS, AK-H15 off, MMVF=8 and others. Its gates are published. GPU tree device accept took T16 to parity with linear. DTREE-GDN-BATCH is the open lever. The Q4X replay re-allow failed identity under np4, and a bisect row is queued. DF2-11 found the BF16 drafter sits on hipBLAS at 144 GB/s, and the Q4_K drafter on generic MMQ. The MI210 measured peak is 1.498 TB/s; the CPU quarter-24t read ceiling is 112.9 GB/s (single quarter only). The AutoKernel journal lives in research scripts/kernel_rnd/autokernel/loop/program.md, plus seeds/ and negatives.json.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Grounding facts checked against the lane and C19 a6a32c1; used in P1, P2 and P7 implementation refs."
  },
  {
   "seq": 17,
   "stage": 3,
   "ts": "2026-11-23T12:40:00Z",
   "verbatim": "Operator answers (2026-11-23): OD-1 A, OD-2 B, OD-3 A, OD-4 A, all as recommended. Record them in the session file. Do NOT apply Stage 4 yet: the operator is reviewing the full plan and is questioning the DICE gating (M6/K1) for the tree-drafting track. Stand by for plan approval.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Recorded in .research-session.json operator_decisions (commit e64c3bc13): OD-1 A, OD-2 B, OD-3 A, OD-4 A; applied at Stage 4; the DICE question is answered by seq 18-19."
  },
  {
   "seq": 18,
   "stage": 3,
   "ts": "2026-11-23T13:00:00Z",
   "verbatim": "DICE: open a box now (SPEC-DTREE-DICE in speculative-decoding.md), offline first. Step 1: measure the sampled (T>0) share of served traffic. Step 2: replay DICE node selection offline on existing DTREE tree dumps for acceptance gains. A GPU row follows only if the replay shows gains. M6's calibration refit can stay trigger-gated.",
   "disposition": "planned",
   "plan_ref": "P7",
   "reason": "Folded into P7; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 19,
   "stage": 3,
   "ts": "2026-11-23T13:00:00Z",
   "verbatim": "Re-examine K1. The operator states production runs at NONZERO temperature; greedy is only for research reproducibility. So \"no gain at T=0\" is not a reason to close anything. Check whether the 1-TV optimality theorem (intake-2845) really covers TREE (multi-candidate) verification, or only single-path drafts. If it covers only single-path, K1 is overstated for DFlash2 trees and DTREE: rewrite it. Also, the operator asks: if implementing Gumbel-max target sampling (DICE's lossless condition) could yield a gain, we should explore or falsify it, not decline it. Add an explicit falsification step (offline: does Gumbel-max coupling plus pre-sampled randomness raise expected accepted length over our rejection sampling on the tree dumps at served temperatures?), with a futility rule.",
   "disposition": "planned",
   "plan_ref": "P7",
   "reason": "Folded into P7; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 20,
   "stage": 3,
   "ts": "2026-11-23T13:00:00Z",
   "verbatim": "AITER: the operator asks whether, as on previous AITER tracks, anything in v0.1.30 is worth REVERSE-ENGINEERING for the MI210 (gfx90a), beyond the binary wheels. Look at the kernel sources and algorithms (asm or CK kernels, MoE sorting and fused MoE, paged attention, quant GEMM, split-K or partition planners, the #7700 planner) for ideas portable to CDNA2: what maps, what needs MFMA/LDS differences, and what we already have. Check previous AITER intake entries and boxes first so nothing is repeated. Turn any real candidates into boxes (likely autokernel-loop.md or rocm-kernel-authoring.md), and replace K4 if it no longer holds.",
   "disposition": "planned",
   "plan_ref": "P10",
   "reason": "Folded into P10; claimed numbers checked by the dives (see dive_corrections)."
  },
  {
   "seq": 21,
   "stage": 3,
   "ts": "2026-11-23T14:00:00Z",
   "verbatim": "Operator (2026-11-23): Stage 3 revision 1 is APPROVED, so apply Stage 4 now. OD-5 = C: allow BOTH captures now (the A3B MTP capture on a CPU quarter and the 27B DFlash2 MI210 capture-only row). Record that in the session file and the SPEC-DTREE-DICE box.",
   "disposition": "planned",
   "plan_ref": "P7",
   "reason": "Folded into P7; claimed numbers checked by the dives (see dive_corrections)."
  }
 ],
 "opportunity_scan": [
  {
   "scan_id": "S01",
   "source_ref": "intake-2844#01 I2 invariant (page)",
   "implementation_ref": "tests/test-recurrent-state-rollback.cpp:13 @ a6a32c1",
   "mechanism": "position/KV correspondence after ragged rollback",
   "consumer": "C18 bisect / np4 identity",
   "application": "ragged rollback test",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-01"
   ],
   "basis": "no multi-seq rollback test exists"
  },
  {
   "scan_id": "S02",
   "source_ref": "intake-2842#04 pinning no reduction (abstract)",
   "implementation_ref": "server-context.cpp:42-112 @ a6a32c1",
   "mechanism": "backend pinning does not remove verify divergence",
   "consumer": "identity gates",
   "application": "width-aware protocol",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-02",
    "AKI-06"
   ],
   "basis": "gates use 100% identity across widths"
  },
  {
   "scan_id": "S03",
   "source_ref": "intake-2842#01 divergence rate (abstract)",
   "implementation_ref": "speculative-decoding.md:505 @ d785b6d",
   "mechanism": "most greedy spec outputs diverge from AR",
   "consumer": "CAFE-1 verdict",
   "application": "re-judge",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-02"
   ],
   "basis": "CAFE-1 decided on identity alone"
  },
  {
   "scan_id": "S04",
   "source_ref": "intake-2843#02 verify-rollback overwrite (page)",
   "implementation_ref": "INF-70 E2a CPU result",
   "mechanism": "redecode reuses verify-written state",
   "consumer": "HIP exactness modes",
   "application": "GPU arm",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-03",
    "AKI-04"
   ],
   "basis": "only measured on CPU"
  },
  {
   "scan_id": "S05",
   "source_ref": "intake-2843#03 position invariance (page)",
   "implementation_ref": "fork bef2e4c7d GGML_DETERMINISTIC",
   "mechanism": "split count must depend only on shape",
   "consumer": "deterministic reduce",
   "application": "unit test",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-05"
   ],
   "basis": "no test"
  },
  {
   "scan_id": "S06",
   "source_ref": "intake-2824#01 force-tiling rule (diff)",
   "implementation_ref": "mmq.cuh:1318-1366 @ a6a32c1",
   "mechanism": "stream-k off when tiles fill waves",
   "consumer": "gfx90a MMQ launcher",
   "application": "port + screen",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-10",
    "AKI-11",
    "AKI-22"
   ],
   "basis": "always 104 stream-k blocks"
  },
  {
   "scan_id": "S07",
   "source_ref": "intake-2824#04 27B np1 MMQ share (page)",
   "implementation_ref": "DF2-11 trace",
   "mechanism": "MMQ is tiny at np1",
   "consumer": "27B np1",
   "application": "e2e probe",
   "disposition": "declined",
   "ledger_ids": [
    "AKI-13"
   ],
   "basis": "0.9% ceiling"
  },
  {
   "scan_id": "S08",
   "source_ref": "intake-2828#03 zero-timing rule (diff #6941)",
   "implementation_ref": "loop/bench.py:424,:642-694; graph_profile_reader.py:45",
   "mechanism": "reject non-positive timings",
   "consumer": "AK ingestion",
   "application": "refuse + tests",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-17"
   ],
   "basis": "three holes"
  },
  {
   "scan_id": "S09",
   "source_ref": "intake-2839#02 all-or-none report (PR #8081)",
   "implementation_ref": "loop/surface_fold.py:140-193",
   "mechanism": "complete comparison or no competition",
   "consumer": "AK keep receipts",
   "application": "shared validator",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-18",
    "AKI-19"
   ],
   "basis": "digest-only validation"
  },
  {
   "scan_id": "S10",
   "source_ref": "intake-2839#00 frozen decision record (RFC)",
   "implementation_ref": "fattn-gqa-verify.cu:828-830",
   "mechanism": "one decision record read four ways",
   "consumer": "HIP dispatch witness",
   "application": "spec",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-20",
    "AKI-21"
   ],
   "basis": "rows closed witness absent"
  },
  {
   "scan_id": "S11",
   "source_ref": "intake-2833#00 supersession rule (page)",
   "implementation_ref": "orchestrator src/graph/helpers.py:558",
   "mechanism": "later same-target call supersedes output",
   "consumer": "context compaction",
   "application": "offline replay",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-27",
    "AKI-28"
   ],
   "basis": "age-based only"
  },
  {
   "scan_id": "S12",
   "source_ref": "intake-2833#02 cold-commit cost (page)",
   "implementation_ref": "server-context.cpp:5126-5170 @ a6a32c1",
   "mechanism": "commit when cut cost is zero or pressure high",
   "consumer": "llama-server prompt cache",
   "application": "evict-cost probe",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-29",
    "AKI-32"
   ],
   "basis": "no cost model"
  },
  {
   "scan_id": "S13",
   "source_ref": "intake-2849#03 MLA-only splice (page)",
   "implementation_ref": "llama-memory-recurrent.cpp:832",
   "mechanism": "approximate KV splice",
   "consumer": "KPF-62 chunk KV",
   "application": "G3 case",
   "disposition": "context-only",
   "ledger_ids": [
    "AKI-31",
    "AKI-33"
   ],
   "basis": "hybrids cannot shift"
  },
  {
   "scan_id": "S14",
   "source_ref": "intake-2835#01 priced asks (page)",
   "implementation_ref": "q_reward.py:173",
   "mechanism": "win - lambda x n_ask with budget-solved lambda",
   "consumer": "orchestrator escalation",
   "application": "log calibration",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-35",
    "AKI-37"
   ],
   "basis": "fixed 0.15"
  },
  {
   "scan_id": "S15",
   "source_ref": "intake-2855#02 entropy never escalates (page)",
   "implementation_ref": "generation_monitor.py",
   "mechanism": "entropy alone is not an ask signal",
   "consumer": "escalation probe",
   "application": "baseline",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-35",
    "AKI-36"
   ],
   "basis": "entropy-based monitor exists"
  },
  {
   "scan_id": "S16",
   "source_ref": "intake-2859#02 cached-parent admission (page)",
   "implementation_ref": "autopilot-program.md:123 @ d785b6d",
   "mechanism": "admission biased by cached parent outcomes",
   "consumer": "BSV-2",
   "application": "fresh-parent rule",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-41",
    "AKI-43"
   ],
   "basis": "BSV-2 silent on it"
  },
  {
   "scan_id": "S17",
   "source_ref": "intake-2857#00 in-sample retention (README)",
   "implementation_ref": "HIL-2 checklist",
   "mechanism": "accept on the proposal batch",
   "consumer": "HIL",
   "application": "checklist case",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-42",
    "AKI-44"
   ],
   "basis": "not in checklist"
  },
  {
   "scan_id": "S18",
   "source_ref": "intake-2847#01 longest-suffix switch (page)",
   "implementation_ref": "common/speculative.cpp:2651-2812 @ a6a32c1",
   "mechanism": "exact longest-suffix index",
   "consumer": "copy drafting",
   "application": "coverage curve",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-48",
    "AKI-49"
   ],
   "basis": "ngram-mod is hashed fixed-n"
  },
  {
   "scan_id": "S19",
   "source_ref": "intake-2845#01 1-TV bound (page)",
   "implementation_ref": "common/sampling.cpp:1020-1128 @ a6a32c1",
   "mechanism": "no coupling beats rejection sampling",
   "consumer": "DFlash2/MTP verify",
   "application": "bound on MTP",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-50",
    "AKI-51"
   ],
   "basis": "DFlash2 already at ceiling; MTP unknown"
  },
  {
   "scan_id": "S20",
   "source_ref": "intake-2846#01 standard verifier optimal (page)",
   "implementation_ref": "DTREE dump",
   "mechanism": "exponential races only help k>=3",
   "consumer": "DTREE",
   "application": "monitor",
   "disposition": "context-only",
   "ledger_ids": [
    "AKI-52",
    "AKI-54"
   ],
   "basis": "tree unserved"
  },
  {
   "scan_id": "S21",
   "source_ref": "intake-2825#02 readlane (diff)",
   "implementation_ref": "mmid.cu:92 @ a6a32c1",
   "mechanism": "uniform-lane shuffle as readlane",
   "consumer": "mm_ids helper",
   "application": "gate arm",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-56",
    "AKI-57",
    "AKI-58"
   ],
   "basis": "one served site"
  },
  {
   "scan_id": "S22",
   "source_ref": "intake-2840#00 min-max planner (diff)",
   "implementation_ref": "fattn-gqa-verify.cu:769-781 @ a6a32c1",
   "mechanism": "split count from live chunks",
   "consumer": "gv verify FA",
   "application": "arithmetic",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-59",
    "AKI-60"
   ],
   "basis": "uniform splits"
  },
  {
   "scan_id": "S23",
   "source_ref": "intake-2829#01 zero-alloc rank lookup (diff)",
   "implementation_ref": "src/llama-vocab.cpp:274 @ a6a32c1",
   "mechanism": "string_view rank keys",
   "consumer": "tokenizer",
   "application": "timing",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-61",
    "AKI-62"
   ],
   "basis": "absent"
  },
  {
   "scan_id": "S24",
   "source_ref": "intake-2834#00 entropy-rank weights (page)",
   "implementation_ref": "model-evaluation-queue.md:1259",
   "mechanism": "RL token weighting",
   "consumer": "post-training lane",
   "application": "operator decision",
   "disposition": "context-only",
   "ledger_ids": [
    "AKI-63",
    "AKI-64",
    "AKI-65",
    "AKI-55"
   ],
   "basis": "no lane; box declined/countermanded"
  },
  {
   "scan_id": "S25",
   "source_ref": "intake-2841#02 qualification by CI (README)",
   "implementation_ref": "loop/lineage_capture.py:1-14",
   "mechanism": "measuring system writes perf fields",
   "consumer": "AK lineage",
   "application": "operator decision",
   "disposition": "context-only",
   "ledger_ids": [
    "AKI-25",
    "AKI-26"
   ],
   "basis": "producer needs approval"
  },
  {
   "scan_id": "S26",
   "source_ref": "intake-2836#01 HookEvo matched-task retention (page)",
   "implementation_ref": "memory-program.md:669",
   "mechanism": "executable guard beats text skill",
   "consumer": "SkillBank",
   "application": "monitor",
   "disposition": "context-only",
   "ledger_ids": [
    "AKI-46",
    "AKI-47"
   ],
   "basis": "A/B not booked"
  },
  {
   "scan_id": "S27",
   "source_ref": "intake-2861#02 strict improvement with fresh incumbent (README)",
   "implementation_ref": "harness-program.md:1724 HIL-6",
   "mechanism": "local improver evolution",
   "consumer": "HIL-6",
   "application": "operator decision",
   "disposition": "context-only",
   "ledger_ids": [
    "AKI-45",
    "AKI-39",
    "AKI-40"
   ],
   "basis": "needs allowance"
  },
  {
   "scan_id": "S28",
   "source_ref": "intake-2843#01 batch-invariance cost (page)",
   "implementation_ref": "registry temperatures",
   "mechanism": "determinism costs throughput",
   "consumer": "serving",
   "application": "decline",
   "disposition": "declined",
   "ledger_ids": [
    "AKI-07",
    "AKI-08",
    "AKI-09"
   ],
   "basis": "production samples at T>0"
  },
  {
   "scan_id": "S29",
   "source_ref": "intake-2837#01 GCN-only gate (diff)",
   "implementation_ref": "common.cuh:92 IS_CDNA",
   "mechanism": "GCN table",
   "consumer": "gfx90a",
   "application": "decline",
   "disposition": "declined",
   "ledger_ids": [
    "AKI-12",
    "AKI-14",
    "AKI-15",
    "AKI-16"
   ],
   "basis": "MI210 is CDNA"
  },
  {
   "scan_id": "S30",
   "source_ref": "intake-2828#00 wheel arch list (page)",
   "implementation_ref": "rocm-kernel-authoring.md:2621 tail split",
   "mechanism": "AITER gfx942/gfx950 kernels",
   "consumer": "AK",
   "application": "knowledge",
   "disposition": "context-only",
   "ledger_ids": [
    "AKI-23",
    "AKI-24"
   ],
   "basis": "not gfx90a"
  },
  {
   "scan_id": "S31",
   "source_ref": "intake-2833#03 H100 headline (page)",
   "implementation_ref": "context_arm_ab.py:16",
   "mechanism": "throughput under SLO",
   "consumer": "planning",
   "application": "knowledge",
   "disposition": "context-only",
   "ledger_ids": [
    "AKI-30",
    "AKI-34"
   ],
   "basis": "not transferable"
  },
  {
   "scan_id": "S32",
   "source_ref": "intake-2856#00 RL-only collapse is tuning (page)",
   "implementation_ref": "routing-program.md",
   "mechanism": "premise correction",
   "consumer": "ADAPT design",
   "application": "doc",
   "disposition": "context-only",
   "ledger_ids": [
    "AKI-38"
   ],
   "basis": "no reproduction"
  },
  {
   "scan_id": "S33",
   "source_ref": "intake-2848 / intake-2830 PDF-only",
   "implementation_ref": "machine_anchor text-only",
   "mechanism": "unverifiable mechanisms",
   "consumer": "spec decoding",
   "application": "monitor",
   "disposition": "context-only",
   "ledger_ids": [
    "AKI-53",
    "AKI-66"
   ],
   "basis": "stage1-unverified"
  },
  {
   "scan_id": "S34",
   "source_ref": "second-reader outputs",
   "implementation_ref": "second_reader_*.out.json",
   "mechanism": "anchor-claim agreement",
   "consumer": "intake index",
   "application": "operator decision",
   "disposition": "context-only",
   "ledger_ids": [
    "AKI-67"
   ],
   "basis": "18 no rows"
  },
  {
   "scan_id": "S35",
   "source_ref": "intake-2846#02 k>=3 race verifier (page) + intake-2715#00",
   "implementation_ref": "tools/server/server-context.cpp:5586-5590 @ a6a32c1",
   "mechanism": "multi-candidate verification beats single-draft at T>0",
   "consumer": "DTREE / DFlash2 trees",
   "application": "offline replay",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-51",
    "AKI-52",
    "AKI-69",
    "AKI-73"
   ],
   "basis": "DTREE greedy-only; dumps lack target probs"
  },
  {
   "scan_id": "S36",
   "source_ref": "intake-2831#05 draw-informed selection (page)",
   "implementation_ref": "orchestrator llama_server.py:1739-1747 (0a88d7bc)",
   "mechanism": "tree covers the sampled continuation more often",
   "consumer": "served temperature mix",
   "application": "log T then replay",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-52"
   ],
   "basis": "per-request temperature not logged"
  },
  {
   "scan_id": "S37",
   "source_ref": "intake-2828#record AITER fused_gdn_decode_qkvz.py:61 @ 77ba72b",
   "implementation_ref": "ggml-cuda.cu:4252 @ a6a32c1; C18 27B trace",
   "mechanism": "GDN gate math and split-K ba partials in-kernel",
   "consumer": "27B/A3B verify",
   "application": "fold",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-23",
    "AKI-70"
   ],
   "basis": "~1.5 ms of small launches"
  },
  {
   "scan_id": "S38",
   "source_ref": "intake-2828#record AITER per-channel int8 GEMMs",
   "implementation_ref": "mmq-q8-mf.cu @ a6a32c1; AK-ASM-I8GEMM-PERCHANNEL-ROW",
   "mechanism": "per-row int8 layout",
   "consumer": "27B verify GEMV",
   "application": "ceiling then timing knob",
   "disposition": "actionable",
   "ledger_ids": [
    "AKI-71"
   ],
   "basis": "only prefill measured"
  },
  {
   "scan_id": "S39",
   "source_ref": "rev-1 AITER non-candidates",
   "implementation_ref": "aiter-gfx90a-ops-20261105.md op map",
   "mechanism": "FP8/MX/gfx950 kernels",
   "consumer": "AK",
   "application": "decline",
   "disposition": "declined",
   "ledger_ids": [
    "AKI-72",
    "AKI-68"
   ],
   "basis": "already retargeted or no hardware"
  }
 ],
 "outcome_reviews": {
  "AKI-01": {
   "required_outcome": "Ragged multi-sequence rollback is tested before the bisect spends a row",
   "review_status": "preserved",
   "review_basis": "SPEC-ID-RAGGED-1 test and prior",
   "task_refs": [
    {
     "owner": "handoffs/active/kernel-champion-and-promotion.md",
     "task_id": "SPEC-ID-RAGGED-1",
     "task_text": "  - [ ] **SPEC-ID-RAGGED-1** [non-inference] Add `test-multiseq-ragged-rollback` on a fresh llama.cpp-experimental branch from C19 a6a32c1 as the mechanism check for the Q4X replay divergences that C18-REPLAY-Q4X-CONC-BISECT left UNLOCATED (8 ON-only phase-C first divergences, not tie flips, not on one slot) (intake-2844#01, intake-2844#02): 3-4 sequences in one batch, a different accepted-draft count per sequence each round, `kv_unified` on and off, both snapshot rollback and RS replay, compared token-for-token and state-for-state with a single-sequence reference run. No test at a6a32c1 covers multi-sequence ragged rollback (`tests/test-recurrent-state-rollback.cpp:13` sets n_seq_max = 1). If it fails, the fix comes before any Q4X replay re-allow; if it passes, the divergences are classified with SPEC-ID-GATE-1.",
     "acceptance": "test committed on the branch with its SHA, PASS or FAIL per arm (kv_unified x rollback mode) recorded under this box, and the consequence for the Q4X re-allow stated"
    }
   ]
  },
  "AKI-02": {
   "required_outcome": "Identity gates classify near-tie flips versus defects within one width class",
   "review_status": "preserved",
   "review_basis": "SPEC-ID-GATE-1 protocol and the two applications",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-ID-GATE-1",
     "task_text": "- [ ] **SPEC-ID-GATE-1** [non-inference] Write the width-aware identity-gate protocol for speculative-decoding gates and apply it to two existing verdicts (intake-2842#00, intake-2842#04, intake-2844#record, intake-2844#02; in-house INF-70 E2a: `LLAMA_SPEC_EXACT` modes at tools/server/server-context.cpp:42-112 @ a6a32c1, opt-in `GGML_ROWEXACT_N` at ggml/src/ggml-cpu/ggml-cpu.c:1505 @ a6a32c1). Protocol: (a) an identity check compares arms only inside one verify-width class, or under `LLAMA_SPEC_EXACT=serial` / `GGML_ROWEXACT_N`, because pinning one kernel backend does not remove verify-path divergence (intake-2842#04); (b) never import a literature exact-match rate as a threshold (intake-2844#record); (c) classify every first divergence as near-tie flip (top-2 margin inside the measured A/A floor), DEGEN_AFTER_TIE (repeat loop after a tie, a defect when the speculation-off np4 control shows none, intake-2844#02) or defect. Apply it: re-judge the CAFE-1 p-min decline (speculative-decoding.md:505, decided on 100% identity alone; a CPU row only if its logprobs were not retained), and write a recommendation to CAFE-3's owner on its identity-100% done-when (speculative-decoding.md:523) without editing that box.",
     "acceptance": "protocol section committed in speculative-decoding.md; CAFE-1 re-judgement verdict (stands or reopens) and the CAFE-3 recommendation recorded under this box"
    }
   ]
  },
  "AKI-03": {
   "required_outcome": "A measured A/A floor per width class on both devices",
   "review_status": "preserved",
   "review_basis": "SPEC-ID-NOISE-1",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-ID-NOISE-1",
     "task_text": "- [ ] **SPEC-ID-NOISE-1** [inference] Measure the width-1 versus width-W teacher-forced logit noise that SPEC-ID-GATE-1 needs as its A/A floor, on 27B Q8_0 + DFlash2 (MI210, C19 GPU store) and Q38FN UD-IQ4_XS + MTP (CPU quarter q0-q2, C19 CPU store). Frozen input: 64 prompts from the DF2-13 prompt set, digest recorded, split into calibration and holdout halves. Per position: max |delta logit| and top-2 margin between width 1 and each served verify width; first-divergence margin histogram; share of first divergences at exactly zero margin (intake-2842#03). Extra arm on HIP: `LLAMA_SPEC_EXACT=redecode` versus `serial`, pre-registered to fail because redecode reuses verify-written KV and GDN state (intake-2843#02). Question: what tolerance tau separates noise from defect per width class. Stop-on-answer when the holdout q99 of |delta logit| is within 10% of the calibration q99 on both devices; stop-on-futility on residency proof failure (verify_ggml_linkage.sh plus nonzero VRAM sampled during the run), store mismatch or STOP/deadline; gate-class futility-only. Complete denominator: every prompt reported, refusals counted.",
     "acceptance": "per-device tau with calibration and holdout q99, the zero-margin share and the redecode-vs-serial verdict filed under this box with the run path"
    }
   ]
  },
  "AKI-04": {
   "required_outcome": "INF-70 E2a repeated on HIP",
   "review_status": "preserved",
   "review_basis": "SPEC-ID-NOISE-1 extra arm",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-ID-NOISE-1",
     "task_text": "- [ ] **SPEC-ID-NOISE-1** [inference] Measure the width-1 versus width-W teacher-forced logit noise that SPEC-ID-GATE-1 needs as its A/A floor, on 27B Q8_0 + DFlash2 (MI210, C19 GPU store) and Q38FN UD-IQ4_XS + MTP (CPU quarter q0-q2, C19 CPU store). Frozen input: 64 prompts from the DF2-13 prompt set, digest recorded, split into calibration and holdout halves. Per position: max |delta logit| and top-2 margin between width 1 and each served verify width; first-divergence margin histogram; share of first divergences at exactly zero margin (intake-2842#03). Extra arm on HIP: `LLAMA_SPEC_EXACT=redecode` versus `serial`, pre-registered to fail because redecode reuses verify-written KV and GDN state (intake-2843#02). Question: what tolerance tau separates noise from defect per width class. Stop-on-answer when the holdout q99 of |delta logit| is within 10% of the calibration q99 on both devices; stop-on-futility on residency proof failure (verify_ggml_linkage.sh plus nonzero VRAM sampled during the run), store mismatch or STOP/deadline; gate-class futility-only. Complete denominator: every prompt reported, refusals counted.",
     "acceptance": "per-device tau with calibration and holdout q99, the zero-margin share and the redecode-vs-serial verdict filed under this box with the run path"
    }
   ]
  },
  "AKI-05": {
   "required_outcome": "Deterministic reduction is position invariant on the MI210 paths",
   "review_status": "preserved",
   "review_basis": "GGML-DET-POSINV-TEST",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "GGML-DET-POSINV-TEST",
     "task_text": "  - [ ] **GGML-DET-POSINV-TEST** [non-inference] Add a position-invariance unit test to the branch that carries `GGML_DETERMINISTIC` (fork commit bef2e4c7d; absent from C19 a6a32c1): at fixed M in {2, 4, 8, 16}, permute the rows of src1 and require bitwise-identical output rows after un-permuting, for the MI210 Q8_MF V5 and q8_skinny paths with GGML_DETERMINISTIC=1, and assert that the split count depends only on (M, N, K) (intake-2843#03). This is the property GGML-DETERMINISTIC-REDUCE-SCRATCH must preserve.",
     "acceptance": "test committed with its SHA, green with GGML_DETERMINISTIC=1 on ROCm0 (and red or documented-nondeterministic with it off) recorded under this box"
    }
   ]
  },
  "AKI-06": {
   "required_outcome": "Bisect excess judged as a rate, not saturated counts",
   "review_status": "preserved",
   "review_basis": "SPEC-ID-GATE-1 classification feeds the bisect via SPEC-ID-RAGGED-1's prior",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-ID-GATE-1",
     "task_text": "- [ ] **SPEC-ID-GATE-1** [non-inference] Write the width-aware identity-gate protocol for speculative-decoding gates and apply it to two existing verdicts (intake-2842#00, intake-2842#04, intake-2844#record, intake-2844#02; in-house INF-70 E2a: `LLAMA_SPEC_EXACT` modes at tools/server/server-context.cpp:42-112 @ a6a32c1, opt-in `GGML_ROWEXACT_N` at ggml/src/ggml-cpu/ggml-cpu.c:1505 @ a6a32c1). Protocol: (a) an identity check compares arms only inside one verify-width class, or under `LLAMA_SPEC_EXACT=serial` / `GGML_ROWEXACT_N`, because pinning one kernel backend does not remove verify-path divergence (intake-2842#04); (b) never import a literature exact-match rate as a threshold (intake-2844#record); (c) classify every first divergence as near-tie flip (top-2 margin inside the measured A/A floor), DEGEN_AFTER_TIE (repeat loop after a tie, a defect when the speculation-off np4 control shows none, intake-2844#02) or defect. Apply it: re-judge the CAFE-1 p-min decline (speculative-decoding.md:505, decided on 100% identity alone; a CPU row only if its logprobs were not retained), and write a recommendation to CAFE-3's owner on its identity-100% done-when (speculative-decoding.md:523) without editing that box.",
     "acceptance": "protocol section committed in speculative-decoding.md; CAFE-1 re-judgement verdict (stands or reopens) and the CAFE-3 recommendation recorded under this box"
    }
   ]
  },
  "AKI-07": {
   "required_outcome": "Exact greedy speculation in production",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: production is speculative at T > 0 (registry temperatures 0.1-0.3), and opt-in GGML_ROWEXACT_N / LLAMA_SPEC_EXACT=serial already provide width-1 equality where a gate needs it",
   "task_refs": []
  },
  "AKI-08": {
   "required_outcome": "Deterministic serving",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: gates run one request per fresh server; LLM-42's no-atomics premise fails for our Q8_MF V5 / q8_skinny paths until GGML_DETERMINISTIC is on (intake-2843#03)",
   "task_refs": []
  },
  "AKI-09": {
   "required_outcome": "np4 parity",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: invariant I1 does not apply to cell-indexed KV (intake-2844#01); SPEC-ID-RAGGED-1 tests the applicable invariant",
   "task_refs": []
  },
  "AKI-10": {
   "required_outcome": "A measured stream-k/tiling choice for small-column MMQ on gfx90a",
   "review_status": "preserved",
   "review_basis": "AK-MMQ-SK2 steps 1-3",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-MMQ-SK2",
     "task_text": "- [ ] **AK-MMQ-SK2** [inference] Stream-k at small column counts on gfx90a (intake-2824#record, intake-2824#01, intake-2824#02, intake-2837#01, intake-2838#00). Step 1 (code, region-lock claim for the build): on a fresh llama.cpp-experimental branch from C19 a6a32c1, hand-port upstream #30553 (stream-k grid capped at useful work) and #30022 (force-tiling rule) as two default-off commits with the predicate widened from GCN to CDNA behind env `GGML_HIP_MMQ_CDNA_FORCE_TILING=1`, plus a separate build arm with #32837's CDNA table cell (256 threads, occupancy 2, I=64) in mmq-config-cdna.cuh. Our launcher always runs 104 stream-k blocks (ggml/src/ggml-cuda/mmq.cuh:1318-1366 @ a6a32c1). Step 2 (zero compute): census served MMQ shapes (27B np4 verify M=36, A3B Q8_0 MUL_MAT_ID above the MMVQ cap, Q4_K/Q6_K at 5-128 rows) and record where force-tiling fires and where the cap changes the grid. Step 3 (one GPU row, cap 1 GPU-h): arms D default, A force-tiling env, B table build; cells Q4_K MUL_MAT n 5/8/16/32 on 17408x5120 and 5120x17408, Q8_0 n 17/36/64, A3B Q8_0 MUL_MAT_ID n 16/64, n=512 guards; order: knob-honoured witness, test-backend-ops MUL_MAT/MUL_MAT_ID correctness (bit-identity versus C19 is not expected: a grid change regroups FP32 sums), ISA audit for B, then 7 interleaved reps per cell with a same-row A/A. KEEP_CANDIDATE if any cell beats its A/A by >= 3% with no n=512 guard worse than -3%; else CLOSE. Futility: correctness fails, knob not honoured, B spills or loses occupancy, residency fails; gate-class futility-only.",
     "acceptance": "branch SHA with the two port commits, the shape census, and the row verdict (KEEP_CANDIDATE or CLOSE) with per-cell A/A-relative deltas filed under this box"
    }
   ]
  },
  "AKI-11": {
   "required_outcome": "Correctness judged by test-backend-ops, not identity",
   "review_status": "preserved",
   "review_basis": "AK-MMQ-SK2 step 3 ordering",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-MMQ-SK2",
     "task_text": "- [ ] **AK-MMQ-SK2** [inference] Stream-k at small column counts on gfx90a (intake-2824#record, intake-2824#01, intake-2824#02, intake-2837#01, intake-2838#00). Step 1 (code, region-lock claim for the build): on a fresh llama.cpp-experimental branch from C19 a6a32c1, hand-port upstream #30553 (stream-k grid capped at useful work) and #30022 (force-tiling rule) as two default-off commits with the predicate widened from GCN to CDNA behind env `GGML_HIP_MMQ_CDNA_FORCE_TILING=1`, plus a separate build arm with #32837's CDNA table cell (256 threads, occupancy 2, I=64) in mmq-config-cdna.cuh. Our launcher always runs 104 stream-k blocks (ggml/src/ggml-cuda/mmq.cuh:1318-1366 @ a6a32c1). Step 2 (zero compute): census served MMQ shapes (27B np4 verify M=36, A3B Q8_0 MUL_MAT_ID above the MMVQ cap, Q4_K/Q6_K at 5-128 rows) and record where force-tiling fires and where the cap changes the grid. Step 3 (one GPU row, cap 1 GPU-h): arms D default, A force-tiling env, B table build; cells Q4_K MUL_MAT n 5/8/16/32 on 17408x5120 and 5120x17408, Q8_0 n 17/36/64, A3B Q8_0 MUL_MAT_ID n 16/64, n=512 guards; order: knob-honoured witness, test-backend-ops MUL_MAT/MUL_MAT_ID correctness (bit-identity versus C19 is not expected: a grid change regroups FP32 sums), ISA audit for B, then 7 interleaved reps per cell with a same-row A/A. KEEP_CANDIDATE if any cell beats its A/A by >= 3% with no n=512 guard worse than -3%; else CLOSE. Futility: correctness fails, knob not honoured, B spills or loses occupancy, residency fails; gate-class futility-only.",
     "acceptance": "branch SHA with the two port commits, the shape census, and the row verdict (KEEP_CANDIDATE or CLOSE) with per-cell A/A-relative deltas filed under this box"
    }
   ]
  },
  "AKI-12": {
   "required_outcome": "End-to-end effect known only if the kernel screen keeps",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M1: fires on AK-MMQ-SK2 KEEP_CANDIDATE",
   "task_refs": []
  },
  "AKI-13": {
   "required_outcome": "27B np1 speed",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: DF2-11 trace puts MMQ at 0.093 of 10.259 kernel-ms per token at 27B np1 (intake-2824#04)",
   "task_refs": []
  },
  "AKI-14": {
   "required_outcome": "CPU matmul",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: the mechanism has no CPU counterpart in ggml-cpu",
   "task_refs": []
  },
  "AKI-15": {
   "required_outcome": "Prior recorded",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only K2",
   "task_refs": []
  },
  "AKI-16": {
   "required_outcome": "GCN tuning",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: IS_GCN covers gfx803-gfx90c only (intake-2837#01)",
   "task_refs": []
  },
  "AKI-17": {
   "required_outcome": "No zero or nonfinite timing reaches a keep decision",
   "review_status": "preserved",
   "review_basis": "AK-TIMING-ZERO-1",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-TIMING-ZERO-1",
     "task_text": "  - [ ] **AK-TIMING-ZERO-1** [non-inference] Close the three timing-ingestion holes that let zero or nonfinite numbers through, in epyc-inference-research scripts/kernel_rnd/autokernel/loop (intake-2828#03): `bench.py:424` returns `avg_ts` checked only for finiteness, `bench.py:642-694` silently drops `value <= 0`, and `graph_profile_reader.py:45` accepts `>= 0`. Make each a recorded refusal (value must be finite and > 0) matching the existing strict gate in `execution/microbench.py:1887-1897`, and add unit tests that feed 0, -1, NaN and inf through each path and expect a refusal, not a sample.",
     "acceptance": "the three call sites refuse with a reason, unit tests green, commit SHA recorded under this box"
    }
   ]
  },
  "AKI-18": {
   "required_outcome": "Receipts are self-validating at consumption",
   "review_status": "preserved",
   "review_basis": "AK-RECEIPT-ARMS-1",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-RECEIPT-ARMS-1",
     "task_text": "  - [ ] **AK-RECEIPT-ARMS-1** [non-inference] Make keep receipts self-validating at consumption (intake-2839#02, intake-2839#03, intake-2841#02): `ExperimentalKeepReceipt` (loop/surface_fold.py:140-193) validates `comparison` only by digest (:174-178), while the both-arms check lives at run.py:2450-2459 and bench.py:232-256. Move that check into one shared validator called when a receipt is consumed; require the comparison block all-or-none (measured value, baseline value, baseline path, measured_under, measurement reference); allow perf fields to be written only by the measuring step; add an authorising-act reference field to `CandidateTarget` (candidate_manifest.py:201-250); re-validate every retained receipt and list any that fail.",
     "acceptance": "shared validator landed with tests (missing arm, partial comparison block, hand-written perf field all refused), retained-receipt re-validation report path recorded under this box"
    }
   ]
  },
  "AKI-19": {
   "required_outcome": "Every default-on knob traces to an authorising act",
   "review_status": "preserved",
   "review_basis": "AK-RECEIPT-ARMS-1 CandidateTarget field",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-RECEIPT-ARMS-1",
     "task_text": "  - [ ] **AK-RECEIPT-ARMS-1** [non-inference] Make keep receipts self-validating at consumption (intake-2839#02, intake-2839#03, intake-2841#02): `ExperimentalKeepReceipt` (loop/surface_fold.py:140-193) validates `comparison` only by digest (:174-178), while the both-arms check lives at run.py:2450-2459 and bench.py:232-256. Move that check into one shared validator called when a receipt is consumed; require the comparison block all-or-none (measured value, baseline value, baseline path, measured_under, measurement reference); allow perf fields to be written only by the measuring step; add an authorising-act reference field to `CandidateTarget` (candidate_manifest.py:201-250); re-validate every retained receipt and list any that fail.",
     "acceptance": "shared validator landed with tests (missing arm, partial comparison block, hand-written perf field all refused), retained-receipt re-validation report path recorded under this box"
    }
   ]
  },
  "AKI-20": {
   "required_outcome": "Fast-path routing is witnessable without a profiler",
   "review_status": "preserved",
   "review_basis": "RKA-DECISION-RECORD-1",
   "task_refs": [
    {
     "owner": "handoffs/active/rocm-kernel-authoring.md",
     "task_id": "RKA-DECISION-RECORD-1",
     "task_text": "- [ ] **RKA-DECISION-RECORD-1** [non-inference] Specify one fast-path decision record for the fork's HIP dispatch (design only; intake-2839#00, intake-2839#04): route chosen, reason, kernel id, build digest and knob source, emitted once per process per op-shape class and readable without a profiler, plus an audit rule that no fast path may fall back after launch. Motivation is in-house: C16-TOPK-STAGE and C15-GV-BW closed with the witness absent, and today only per-row oracles exist (cpu_route_witness.py, the once-per-process witness at fattn-gqa-verify.cu:828-830 @ a6a32c1).",
     "acceptance": "design section committed in rocm-kernel-authoring.md naming the record fields, emit points and the two closed rows it would have unblocked"
    }
   ]
  },
  "AKI-21": {
   "required_outcome": "First-call routing under graph capture is covered by the record spec",
   "review_status": "preserved",
   "review_basis": "RKA-DECISION-RECORD-1 emit points include graph capture",
   "task_refs": [
    {
     "owner": "handoffs/active/rocm-kernel-authoring.md",
     "task_id": "RKA-DECISION-RECORD-1",
     "task_text": "- [ ] **RKA-DECISION-RECORD-1** [non-inference] Specify one fast-path decision record for the fork's HIP dispatch (design only; intake-2839#00, intake-2839#04): route chosen, reason, kernel id, build digest and knob source, emitted once per process per op-shape class and readable without a profiler, plus an audit rule that no fast path may fall back after launch. Motivation is in-house: C16-TOPK-STAGE and C15-GV-BW closed with the witness absent, and today only per-row oracles exist (cpu_route_witness.py, the once-per-process witness at fattn-gqa-verify.cu:828-830 @ a6a32c1).",
     "acceptance": "design section committed in rocm-kernel-authoring.md naming the record fields, emit points and the two closed rows it would have unblocked"
    }
   ]
  },
  "AKI-22": {
   "required_outcome": "MUL_MAT_ID correctness check is exact where it must be",
   "review_status": "preserved",
   "review_basis": "AK-MMQ-SK2 step 3 runs MUL_MAT_ID correctness first",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-MMQ-SK2",
     "task_text": "- [ ] **AK-MMQ-SK2** [inference] Stream-k at small column counts on gfx90a (intake-2824#record, intake-2824#01, intake-2824#02, intake-2837#01, intake-2838#00). Step 1 (code, region-lock claim for the build): on a fresh llama.cpp-experimental branch from C19 a6a32c1, hand-port upstream #30553 (stream-k grid capped at useful work) and #30022 (force-tiling rule) as two default-off commits with the predicate widened from GCN to CDNA behind env `GGML_HIP_MMQ_CDNA_FORCE_TILING=1`, plus a separate build arm with #32837's CDNA table cell (256 threads, occupancy 2, I=64) in mmq-config-cdna.cuh. Our launcher always runs 104 stream-k blocks (ggml/src/ggml-cuda/mmq.cuh:1318-1366 @ a6a32c1). Step 2 (zero compute): census served MMQ shapes (27B np4 verify M=36, A3B Q8_0 MUL_MAT_ID above the MMVQ cap, Q4_K/Q6_K at 5-128 rows) and record where force-tiling fires and where the cap changes the grid. Step 3 (one GPU row, cap 1 GPU-h): arms D default, A force-tiling env, B table build; cells Q4_K MUL_MAT n 5/8/16/32 on 17408x5120 and 5120x17408, Q8_0 n 17/36/64, A3B Q8_0 MUL_MAT_ID n 16/64, n=512 guards; order: knob-honoured witness, test-backend-ops MUL_MAT/MUL_MAT_ID correctness (bit-identity versus C19 is not expected: a grid change regroups FP32 sums), ISA audit for B, then 7 interleaved reps per cell with a same-row A/A. KEEP_CANDIDATE if any cell beats its A/A by >= 3% with no n=512 guard worse than -3%; else CLOSE. Futility: correctness fails, knob not honoured, B spills or loses occupancy, residency fails; gate-class futility-only.",
     "acceptance": "branch SHA with the two port commits, the shape census, and the row verdict (KEEP_CANDIDATE or CLOSE) with per-cell A/A-relative deltas filed under this box"
    }
   ]
  },
  "AKI-23": {
   "required_outcome": "The GDN input fold is screened on the 27B verify trace",
   "review_status": "preserved",
   "review_basis": "AK-BW-GDN-GATE-FOLD arm (b)",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-BW-GDN-GATE-FOLD",
     "task_text": "  - [ ] **AK-BW-GDN-GATE-FOLD** [inference] Fold the GDN beta/alpha projections and gate math into the recurrence kernel on 27B/A3B verify, after AITER v0.1.30 `aiter/ops/triton/gated_delta_net/fused_gdn_decode_qkvz.py` (read at 77ba72b7061a; gfx950 Triton as written, the gate math is scalar and portable): it computes sigmoid(b) and exp(-exp(A_log) * softplus(a + dt_bias)) inside the GDN kernel from the raw projection and sums ba as fp32 split-K partials in-kernel with no zero-init or atomics (`:61`), with the ba projection emitted by the qkvz GEMM launch (`fused_gemm_a16w16_dual_splitk.py:47-60`, tuned for N1=16384 N2=96 K=5120, our 27B shape) (intake-2828#record). In-house budget, C18 27B DFlash2 verify trace ak-c18-27b-df2-v5i-trace-gpu-20261122 (40.07 ms GPU per verify): 96 small q8sk_mul_mat launches for beta/alpha (0.63 ms) and four unfused gate ops x 48 layers (0.88 ms), plus norm/z gate (0.42 ms) and the state gather k_get_rows (0.53 ms); the existing softplus fusion (ggml-cuda.cu:4252 @ a6a32c1) does not engage there (cause unknown). Arms in order: (a) row-concat ssm_beta|ssm_alpha into one Q8_0 tensor at load and one launch writing [KS, T, 2*H_v] fp32 partials without atomics; (b) a fusion from that output to GATED_DELTA_NET passing raw b/a, ssm_dt and ssm_a to the C19 fused K=T and rows kernels, which sum the partials and apply the gate in their prologue; (c) and (d) (norm + silu(z) epilogue; state pool by slot) only after (a)+(b). Side effect: removes the unordered atomic split-K on ssm_ab. Step 1 (no GPU): from the 27B trace above and ak-c18-a3b-mtp-trace-gpu-20261122, list the launches each arm removes with their ms and confirm from C19 source how the GDN kernels read g/beta; stop-on-futility if (a)+(b) remove < 0.8 ms per 27B verify. Then one op/trace row: stop-on-answer when GDN-input ms per verify <= 0.4 ms with test-backend-ops GATED_DELTA_NET parity and 27B KLD vs C19 <= 0.003; then 27B DFlash2 np1 e2e, 8 ABBA pairs, KEEP iff CI lower > +1% and no cell < -1%; futility if the first variant saves < 0.6 ms per verify; gate-class futility-only. Build: experimental branch from C19 a6a32c1, knob default off, region-lock claim; coordinate with AK-BW-27B-ACTQUANT-FUSE and AK-BW-A3B-DENSE-STEP2 (b) (same concat).",
     "acceptance": "step-1 launch/ms table filed, then an op/trace verdict and a 27B e2e KEEP/DROP for arms (a)+(b); A3B runs only after a 27B KEEP"
    }
   ]
  },
  "AKI-24": {
   "required_outcome": "Dispatch selection",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: a provider registry would be a second dispatch truth beside the champion",
   "task_refs": []
  },
  "AKI-25": {
   "required_outcome": "AK candidate robustness",
   "review_status": "closed-with-basis",
   "review_basis": "Declined now: reopen only if a candidate with spin waits or a grid barrier appears; the actor ablation needs a loop launch, which the akagg hold gates",
   "task_refs": []
  },
  "AKI-26": {
   "required_outcome": "Lineage recorded for every keep",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M13: fires on operator approval OD-3 (the module states its producer needs operator approval)",
   "task_refs": []
  },
  "AKI-27": {
   "required_outcome": "Measured supersession share on our transcripts",
   "review_status": "preserved",
   "review_basis": "TOC-SUPERSEDE-1",
   "task_refs": [
    {
     "owner": "handoffs/active/context-and-token-economy.md",
     "task_id": "TOC-SUPERSEDE-1",
     "task_text": "- [ ] **TOC-SUPERSEDE-1** [non-inference] Replay a tool-supersession classifier offline over recorded REPL and Claude Code transcripts and over AgentDiet's released trajectories (intake-2833#00, intake-2833#01, intake-2853#00, intake-2851#02, intake-2852#00). Rule: a later read or edit of the same file path, a re-run of the same normalized shell command, a later build whose targets overlap, or a passing re-run of the same test supersedes the earlier tool output; a round whose outputs are all superseded becomes a candidate; 2-round grace window; no model calls. Report the candidate token share of final histories, the hash-dedup repeat count, and an eviction-regret rate (superseded content later re-read, by content hash). Six controls: frozen transcript manifest with digest, baseline = no eviction and the current age-based `_clear_stale_tool_outputs` (orchestrator src/graph/helpers.py:558), per-transcript outputs retained, holdout = transcripts after a fixed date, every transcript counted, rule fixed before the run. Stop-on-answer: share < 15% closes the supersession arm; >= 15% fires the TOC-CMP-4 trigger below.",
     "acceptance": "share, dedup count and regret rate per transcript class with the manifest digest filed under this box, and the arm closed or the trigger fired"
    }
   ]
  },
  "AKI-28": {
   "required_outcome": "Arms admitted only on a measured share",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M2 on TOC-SUPERSEDE-1 >= 15%",
   "task_refs": []
  },
  "AKI-29": {
   "required_outcome": "Cut cost predicted per device before any eviction",
   "review_status": "preserved",
   "review_basis": "KV-EVICT-COST-1",
   "task_refs": [
    {
     "owner": "handoffs/active/kv-cache-program.md",
     "task_id": "KV-EVICT-COST-1",
     "task_text": "  - [ ] **KV-EVICT-COST-1** [inference] Build a read-only evict-cost probe for llama-server and a device break-even table (intake-2833#02, intake-2850#02, intake-2849#03, intake-2853#04). Probe: for a proposed cut, predict re-prefilled tokens = T' - p*, with p* the nearest checkpoint at or before the cut (restore logic tools/server/server-context.cpp:5126-5170 @ a6a32c1; hybrid models cannot shift, `can_shift` false at src/llama-memory-recurrent.cpp:832), classify the cut as checkpoint-aligned or not, and predict seconds as a + b x cells fitted from existing prefill rows. Check it in one small CPU smoke on 20 synthetic cuts against measured `n_prompt_tokens_processed` (pass at 19/20 exact token counts). Then publish a doc table per device (MI210 and one CPU quarter) of break-even gain for a cut, with a residual column max(0, cost - inter-turn slack) and a row for an LLM reflection call; device-specific commit caps, never the paper's H100 cap.",
     "acceptance": "probe committed with tests, smoke result (k/20 exact) and the per-device break-even table recorded under this box"
    }
   ]
  },
  "AKI-30": {
   "required_outcome": "Whether our clearing breaks the prefix is measured",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M11: needs RTE-LOG-1 prompt-structure logs (harness-program.md:519, open)",
   "task_refs": []
  },
  "AKI-31": {
   "required_outcome": "Splice judged on the frozen G3 corpus",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M3 at KPF-62.6",
   "task_refs": []
  },
  "AKI-32": {
   "required_outcome": "Hidden re-prefill",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: reopen only if KV-EVICT-COST-1's residual column shows idle gaps >= cost at p25 for >= 30% of cuts",
   "task_refs": []
  },
  "AKI-33": {
   "required_outcome": "Eviction policy variants",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: 1.1 TB host never reaches 80% pool pressure; energy tracks throughput; GDN state cannot be shifted; the rest add model calls or tools with no measured need",
   "task_refs": []
  },
  "AKI-34": {
   "required_outcome": "Numbers not transferred",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only K3",
   "task_refs": []
  },
  "AKI-35": {
   "required_outcome": "Escalation calibrated from logs",
   "review_status": "preserved",
   "review_basis": "RTG-ASK-1",
   "task_refs": [
    {
     "owner": "handoffs/active/routing-program.md",
     "task_id": "RTG-ASK-1",
     "task_text": "- [ ] **RTG-ASK-1** [non-inference] Calibrate when our small roles ask for help, from logs only (intake-2835#00, intake-2835#01, intake-2855#00, intake-2855#02, intake-2856#00). (1) Tabulate escalations per task and role from existing taps and progress logs, counting `escalate()` hand-offs (src/repl_environment/routing.py:303-319) and consult advice separately. (2) Fit a residual-risk probe on logged non-escalated episodes labelled by their own episode outcome and compare it with the entropy-only baseline (generation_monitor.py). (3) Replay-evaluate replacing the fixed `escalation_penalty = len(escalations) * 0.15` (orchestration/repl_memory/q_reward.py:173) with a price solved against a consults-per-task budget. Six controls: frozen log manifest with digest, baseline = current rule policy (src/orchestration/escalation.py:227-350), per-episode outputs, holdout = later time window, all episodes counted, decision rule fixed first: adopt the probe only if its holdout AUROC beats entropy-only by >= 0.05; stop and report counts only if fewer than 200 escalation-eligible episodes exist.",
     "acceptance": "per-role counts, holdout AUROC of probe versus entropy-only, and the replayed budget-price result filed under this box"
    }
   ]
  },
  "AKI-36": {
   "required_outcome": "Readouts only after the probe earns them",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M4",
   "task_refs": []
  },
  "AKI-37": {
   "required_outcome": "Primitives counted separately; design deferred to M4",
   "review_status": "preserved",
   "review_basis": "RTG-ASK-1 step 1 counts the two primitives separately; the design note is part of M4",
   "task_refs": [
    {
     "owner": "handoffs/active/routing-program.md",
     "task_id": "RTG-ASK-1",
     "task_text": "- [ ] **RTG-ASK-1** [non-inference] Calibrate when our small roles ask for help, from logs only (intake-2835#00, intake-2835#01, intake-2855#00, intake-2855#02, intake-2856#00). (1) Tabulate escalations per task and role from existing taps and progress logs, counting `escalate()` hand-offs (src/repl_environment/routing.py:303-319) and consult advice separately. (2) Fit a residual-risk probe on logged non-escalated episodes labelled by their own episode outcome and compare it with the entropy-only baseline (generation_monitor.py). (3) Replay-evaluate replacing the fixed `escalation_penalty = len(escalations) * 0.15` (orchestration/repl_memory/q_reward.py:173) with a price solved against a consults-per-task budget. Six controls: frozen log manifest with digest, baseline = current rule policy (src/orchestration/escalation.py:227-350), per-episode outputs, holdout = later time window, all episodes counted, decision rule fixed first: adopt the probe only if its holdout AUROC beats entropy-only by >= 0.05; stop and report counts only if fewer than 200 escalation-eligible episodes exist.",
     "acceptance": "per-role counts, holdout AUROC of probe versus entropy-only, and the replayed budget-price result filed under this box"
    }
   ]
  },
  "AKI-38": {
   "required_outcome": "Reproduction",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: R2V repo is a placeholder (intake-2855#04); AgentRL training ran on >= 16 H800",
   "task_refs": []
  },
  "AKI-39": {
   "required_outcome": "Agentic env available to local roles",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M10 on OD-2",
   "task_refs": []
  },
  "AKI-40": {
   "required_outcome": "Env coverage",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: no consumer",
   "task_refs": []
  },
  "AKI-41": {
   "required_outcome": "Harness accepts generalise and are auditable",
   "review_status": "preserved",
   "review_basis": "AP-BSV2-ACCEPT-RIGOR",
   "task_refs": [
    {
     "owner": "handoffs/active/autopilot-program.md",
     "task_id": "AP-BSV2-ACCEPT-RIGOR",
     "task_text": "- [ ] **AP-BSV2-ACCEPT-RIGOR** [non-inference] Amend the BSV-2 accept design and check it by offline replay of existing AutoPilot journals (intake-2836#01, intake-2857#00, intake-2858#00, intake-2859#03, intake-2862#01, intake-2861#04): (a) accept only on tasks disjoint from the batch whose traces fed the proposal; (b) re-run the parent fresh on that batch, never compare against cached parent outcomes; (c) keep the test split sealed until the search ends and pick the headline checkpoint by a training-side rule, never best-on-test; (d) write a per-round decision record with tokens per accepted gain and row statuses completed / solver_limit / infra_error / candidate_error, with retry for infra errors only; (e) state budgets in rollouts or tokens, not iterations. AutoPilot stays stopped; this is design plus replay.",
     "acceptance": "amended BSV-2 design text committed and the replay result (how many past accepts survive (a)-(b)) recorded under this box, or a recorded stop if journals are too sparse"
    }
   ]
  },
  "AKI-42": {
   "required_outcome": "HIL pre-run checklist carries the evolution lessons",
   "review_status": "preserved",
   "review_basis": "HIL-EVO-CASES-1",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "HIL-EVO-CASES-1",
     "task_text": "- [ ] **HIL-EVO-CASES-1** [non-inference] Append to the HIL-2 pre-first-suite-run checklist in docs/design/harness-improvement-loop-design-20261006.md (as HIL-9 did): the HookEvo shipped per-round adoption record as a worked case of in-sample retention (intake-2857#00, intake-2857#01); the Life-Harness four-layer harness taxonomy as the annotation schema and its trace-replay validity gate before any paid evaluation (intake-2858#00, intake-2858#02); the plugin install envelope (signature regex plus syntax check, abort on an infrastructure-defect string) as a BEP-5 input (intake-2857#05); and the matched-budget rule from AP-BSV2-ACCEPT-RIGOR (e). Zero inference.",
     "acceptance": "checklist items committed in the design doc with the commit SHA recorded under this box"
    }
   ]
  },
  "AKI-43": {
   "required_outcome": "Mutation records carry a versioned manifest with digest",
   "review_status": "preserved",
   "review_basis": "AP-BSV2-ACCEPT-RIGOR (d) decision record includes the manifest fields and a content digest",
   "task_refs": [
    {
     "owner": "handoffs/active/autopilot-program.md",
     "task_id": "AP-BSV2-ACCEPT-RIGOR",
     "task_text": "- [ ] **AP-BSV2-ACCEPT-RIGOR** [non-inference] Amend the BSV-2 accept design and check it by offline replay of existing AutoPilot journals (intake-2836#01, intake-2857#00, intake-2858#00, intake-2859#03, intake-2862#01, intake-2861#04): (a) accept only on tasks disjoint from the batch whose traces fed the proposal; (b) re-run the parent fresh on that batch, never compare against cached parent outcomes; (c) keep the test split sealed until the search ends and pick the headline checkpoint by a training-side rule, never best-on-test; (d) write a per-round decision record with tokens per accepted gain and row statuses completed / solver_limit / infra_error / candidate_error, with retry for infra errors only; (e) state budgets in rollouts or tokens, not iterations. AutoPilot stays stopped; this is design plus replay.",
     "acceptance": "amended BSV-2 design text committed and the replay result (how many past accepts survive (a)-(b)) recorded under this box, or a recorded stop if journals are too sparse"
    }
   ]
  },
  "AKI-44": {
   "required_outcome": "Guard arm tested when the A/B runs",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M12: when the M-23 SkillBank A/B is next booked (memory-program.md:669)",
   "task_refs": []
  },
  "AKI-45": {
   "required_outcome": "Local improver run, if approved",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M10: fires on operator approval OD-2 (extends the HIL-6 pilot-only loop allowance)",
   "task_refs": []
  },
  "AKI-46": {
   "required_outcome": "HookEvo runtime",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: our hooks are Claude Code / opencode; the envelope lesson is captured in HIL-EVO-CASES-1",
   "task_refs": []
  },
  "AKI-47": {
   "required_outcome": "Reproduction",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: no EPYC decision depends on these numbers",
   "task_refs": []
  },
  "AKI-48": {
   "required_outcome": "Copy-proposal lane opened or closed on coverage",
   "review_status": "preserved",
   "review_basis": "SPEC-COPY-COV-1",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-COPY-COV-1",
     "task_text": "- [ ] **SPEC-COPY-COV-1** [non-inference] Offline copy-match coverage curve before any copy-proposal drafter work (intake-2847#00, intake-2847#01, intake-2832#00, intake-2832#01). Over the archived COPYSPEC P1 outputs (artifacts/copyspec-20261006/source-archive/results/P.jsonl, 85 requests), build an exact longest-suffix index (our ngram-mod at common/speculative.cpp:2651-2812 @ a6a32c1 is a fixed-n hashed window, not longest-suffix) and report, per position, the match length and whether the next 3 tokens agree, for code and prose, plus a leave-one-out variant. Stop-on-answer: if positions with match length >= 5 and >= 3 agreed tokens are under 5% on code and under 2% on prose, close the copy-proposal path; otherwise fire the trigger below.",
     "acceptance": "coverage table (code and prose, in-sample and leave-one-out) recorded under this box with the path closed or the trigger fired"
    }
   ]
  },
  "AKI-49": {
   "required_outcome": "Drafter work only above the coverage threshold",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M5",
   "task_refs": []
  },
  "AKI-50": {
   "required_outcome": "MTP T>0 lane opened or closed on a measured gap",
   "review_status": "preserved",
   "review_basis": "SPEC-COUPLE-MTP-1 (MTP is sample-and-compare at T>0, not rejection)",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-COUPLE-MTP-1",
     "task_text": "- [ ] **SPEC-COUPLE-MTP-1** [inference] Bound what a draft distribution plus rejection sampling, or coupled draws, could add on the A3B MTP chain at served temperatures (intake-2845#00, intake-2845#record, intake-2831#01). MTP at T > 0 verifies by sample-and-compare against an argmax draft (common/sampling.cpp:693-711, common/speculative.cpp:2116-2119 @ a6a32c1), so per-position acceptance is p(argmax q), below the single-draft 1 - TV ceiling (a per-position, single-draft bound, intake-2845#record) that the DFlash2 rejection path already reaches. Using the SPEC-DTREE-DICE step-2a capture (MTP top-10 drafter logits plus target candidates at every verified row; frozen 64-prompt set with digest; baseline = current sample-and-compare; per-position outputs kept; holdout = second half of the prompts; every position counted), compute offline per served T from SPEC-DTREE-DICE step 1 (expect 0.1/0.2/0.3 and 1.0): the gap 1 - TV(q, p) - p(argmax q) for q = softmax(logit/T) over the MTP top-10, i.e. routing MTP through the existing rejection path. Stop if the holdout gap is under 1% at every served T; file a build box (MTP fills draft distributions, rejection path) if it is 2% or more at any served T with >= 20% token share; gate-class futility-only.",
     "acceptance": "per-temperature holdout gap and the decision (close or build box filed) recorded under this box"
    }
   ]
  },
  "AKI-51": {
   "required_outcome": "Gumbel-max coupling with pre-sampled randomness on trees at served T is confirmed or falsified, never declined",
   "review_status": "preserved",
   "review_basis": "SPEC-DTREE-DICE falsifier H1 (V2/V3 versus V0/V1); K1 rewritten to the single-draft scope",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-DTREE-DICE",
     "task_text": "- [ ] **SPEC-DTREE-DICE** [inference] Falsify or confirm that pre-sampled target randomness raises expected accepted length on SAMPLED trees at served temperatures (intake-2831#00, intake-2831#03, intake-2831#05), where the single-draft 1 - TV ceiling (intake-2845#record) does not apply and k-candidate verifiers beat the standard one at T > 0 (intake-2846#02, intake-2715#00, intake-2717#01). Today DTREE is greedy-only (spec_tree_nodes_for returns 0 at temp > 0, tools/server/server-context.cpp:5586-5590 @ a6a32c1) and the DTREE dumps are greedy with no target probabilities, so they cannot be replayed at T > 0. Step 1 (code only): log the resolved temperature/top_k/top_p/min_p per request in the inference-tap start event (orchestrator llama_server.py:1739-1747 payload site) and poll /slots on the speculative ports for direct clients; report the token-weighted temperature histogram per drafter (27B DFlash2, A3B MTP) over a declared window; close if the T > 0 share is under 5% on both, else the served T set is its modes. Step 2a (capture): a dump-knob-only fork from the current champion, at served T with keyed draws (seed, position, vocab id), logging per round the drafter lattice/candidates and the target post-sampler candidates plus top-64 logits at every verified row; for DFlash2 force a superset tree (prob-greedy W32 + DICE W16 + chain) into the verify batch while committing through the unchanged chain. A3B MTP first on a CPU quarter q0-q2; the 27B DFlash2 capture is an MI210 capture-only row on gpu-q3 (OD-5 = C, operator 2026-11-23: both captures allowed now). Step 2b (offline replay, CPU) at equal node budget W in {1,4,8,12,16}: V0 served path, V1 same tree with recursive rejection without replacement, V2 Gumbel-max walk with pre-sampled draws and draw-blind selection, V3 DICE draw-informed selection ((alpha, sigma) fitted on the calibration half only), optional V4 exponential-race verifier for k >= 3 siblings (intake-2846#02); metric expected tokens per target pass per served T. Controls: frozen capture and replay script with sha256, baseline V0, per-round per-arm results.jsonl, holdout = second prompt half, every verify round counted, PREDECLARATION.md sealed before replay. Falsifier H1: V3 raises expected accepted length over V0 and over V1 at equal W. Futility: close if holdout V3/V1 < 1.02 at every served T and W <= 16 and V3/V0 stays below the verify-cost break-even; stop-on-answer at a prompt-clustered 95% CI half-width <= 1% on V3/V1 at the highest-share T; gate-class futility-only. A GPU build row (keyed Gumbel-max target sampler, DICE node selection, Gumbel tree walk, T > 0 guard lifted; ABBA np1/np4; KEEP iff tok/s CI-lower > 1.0 and an emitted-token distribution check passes) is filed only if the replay clears break-even; if only V1 clears it, file the sampled recursive-rejection tree row (DTREE-A) instead.",
     "acceptance": "step-1 temperature-share table and decision filed; then the capture digest and a RESULT.json with holdout tokens per pass per arm x T x W and a verdict CLOSE_FUTILITY / FILE_GPU_ROW / FILE_RRS_ROW"
    }
   ]
  },
  "AKI-52": {
   "required_outcome": "DICE on sampled trees decided on served-temperature evidence",
   "review_status": "preserved",
   "review_basis": "SPEC-DTREE-DICE steps 1, 2a, 2b and the GPU gate",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-DTREE-DICE",
     "task_text": "- [ ] **SPEC-DTREE-DICE** [inference] Falsify or confirm that pre-sampled target randomness raises expected accepted length on SAMPLED trees at served temperatures (intake-2831#00, intake-2831#03, intake-2831#05), where the single-draft 1 - TV ceiling (intake-2845#record) does not apply and k-candidate verifiers beat the standard one at T > 0 (intake-2846#02, intake-2715#00, intake-2717#01). Today DTREE is greedy-only (spec_tree_nodes_for returns 0 at temp > 0, tools/server/server-context.cpp:5586-5590 @ a6a32c1) and the DTREE dumps are greedy with no target probabilities, so they cannot be replayed at T > 0. Step 1 (code only): log the resolved temperature/top_k/top_p/min_p per request in the inference-tap start event (orchestrator llama_server.py:1739-1747 payload site) and poll /slots on the speculative ports for direct clients; report the token-weighted temperature histogram per drafter (27B DFlash2, A3B MTP) over a declared window; close if the T > 0 share is under 5% on both, else the served T set is its modes. Step 2a (capture): a dump-knob-only fork from the current champion, at served T with keyed draws (seed, position, vocab id), logging per round the drafter lattice/candidates and the target post-sampler candidates plus top-64 logits at every verified row; for DFlash2 force a superset tree (prob-greedy W32 + DICE W16 + chain) into the verify batch while committing through the unchanged chain. A3B MTP first on a CPU quarter q0-q2; the 27B DFlash2 capture is an MI210 capture-only row on gpu-q3 (OD-5 = C, operator 2026-11-23: both captures allowed now). Step 2b (offline replay, CPU) at equal node budget W in {1,4,8,12,16}: V0 served path, V1 same tree with recursive rejection without replacement, V2 Gumbel-max walk with pre-sampled draws and draw-blind selection, V3 DICE draw-informed selection ((alpha, sigma) fitted on the calibration half only), optional V4 exponential-race verifier for k >= 3 siblings (intake-2846#02); metric expected tokens per target pass per served T. Controls: frozen capture and replay script with sha256, baseline V0, per-round per-arm results.jsonl, holdout = second prompt half, every verify round counted, PREDECLARATION.md sealed before replay. Falsifier H1: V3 raises expected accepted length over V0 and over V1 at equal W. Futility: close if holdout V3/V1 < 1.02 at every served T and W <= 16 and V3/V0 stays below the verify-cost break-even; stop-on-answer at a prompt-clustered 95% CI half-width <= 1% on V3/V1 at the highest-share T; gate-class futility-only. A GPU build row (keyed Gumbel-max target sampler, DICE node selection, Gumbel tree walk, T > 0 guard lifted; ABBA np1/np4; KEEP iff tok/s CI-lower > 1.0 and an emitted-token distribution check passes) is filed only if the replay clears break-even; if only V1 clears it, file the sampled recursive-rejection tree row (DTREE-A) instead.",
     "acceptance": "step-1 temperature-share table and decision filed; then the capture digest and a RESULT.json with holdout tokens per pass per arm x T x W and a verdict CLOSE_FUTILITY / FILE_GPU_ROW / FILE_RRS_ROW"
    }
   ]
  },
  "AKI-68": {
   "required_outcome": "Refit when a tree is served",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M6 on DTREE-GDN-BATCH (operator: the calibration refit may stay trigger-gated)",
   "task_refs": []
  },
  "AKI-69": {
   "required_outcome": "k-candidate verifiers tested as replay arms, not declined",
   "review_status": "preserved",
   "review_basis": "SPEC-DTREE-DICE optional V4 arm",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-DTREE-DICE",
     "task_text": "- [ ] **SPEC-DTREE-DICE** [inference] Falsify or confirm that pre-sampled target randomness raises expected accepted length on SAMPLED trees at served temperatures (intake-2831#00, intake-2831#03, intake-2831#05), where the single-draft 1 - TV ceiling (intake-2845#record) does not apply and k-candidate verifiers beat the standard one at T > 0 (intake-2846#02, intake-2715#00, intake-2717#01). Today DTREE is greedy-only (spec_tree_nodes_for returns 0 at temp > 0, tools/server/server-context.cpp:5586-5590 @ a6a32c1) and the DTREE dumps are greedy with no target probabilities, so they cannot be replayed at T > 0. Step 1 (code only): log the resolved temperature/top_k/top_p/min_p per request in the inference-tap start event (orchestrator llama_server.py:1739-1747 payload site) and poll /slots on the speculative ports for direct clients; report the token-weighted temperature histogram per drafter (27B DFlash2, A3B MTP) over a declared window; close if the T > 0 share is under 5% on both, else the served T set is its modes. Step 2a (capture): a dump-knob-only fork from the current champion, at served T with keyed draws (seed, position, vocab id), logging per round the drafter lattice/candidates and the target post-sampler candidates plus top-64 logits at every verified row; for DFlash2 force a superset tree (prob-greedy W32 + DICE W16 + chain) into the verify batch while committing through the unchanged chain. A3B MTP first on a CPU quarter q0-q2; the 27B DFlash2 capture is an MI210 capture-only row on gpu-q3 (OD-5 = C, operator 2026-11-23: both captures allowed now). Step 2b (offline replay, CPU) at equal node budget W in {1,4,8,12,16}: V0 served path, V1 same tree with recursive rejection without replacement, V2 Gumbel-max walk with pre-sampled draws and draw-blind selection, V3 DICE draw-informed selection ((alpha, sigma) fitted on the calibration half only), optional V4 exponential-race verifier for k >= 3 siblings (intake-2846#02); metric expected tokens per target pass per served T. Controls: frozen capture and replay script with sha256, baseline V0, per-round per-arm results.jsonl, holdout = second prompt half, every verify round counted, PREDECLARATION.md sealed before replay. Falsifier H1: V3 raises expected accepted length over V0 and over V1 at equal W. Futility: close if holdout V3/V1 < 1.02 at every served T and W <= 16 and V3/V0 stays below the verify-cost break-even; stop-on-answer at a prompt-clustered 95% CI half-width <= 1% on V3/V1 at the highest-share T; gate-class futility-only. A GPU build row (keyed Gumbel-max target sampler, DICE node selection, Gumbel tree walk, T > 0 guard lifted; ABBA np1/np4; KEEP iff tok/s CI-lower > 1.0 and an emitted-token distribution check passes) is filed only if the replay clears break-even; if only V1 clears it, file the sampled recursive-rejection tree row (DTREE-A) instead.",
     "acceptance": "step-1 temperature-share table and decision filed; then the capture digest and a RESULT.json with holdout tokens per pass per arm x T x W and a verdict CLOSE_FUTILITY / FILE_GPU_ROW / FILE_RRS_ROW"
    }
   ]
  },
  "AKI-70": {
   "required_outcome": "27B verify drops the small GDN-input launches if the trace budget holds",
   "review_status": "preserved",
   "review_basis": "AK-BW-GDN-GATE-FOLD",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-BW-GDN-GATE-FOLD",
     "task_text": "  - [ ] **AK-BW-GDN-GATE-FOLD** [inference] Fold the GDN beta/alpha projections and gate math into the recurrence kernel on 27B/A3B verify, after AITER v0.1.30 `aiter/ops/triton/gated_delta_net/fused_gdn_decode_qkvz.py` (read at 77ba72b7061a; gfx950 Triton as written, the gate math is scalar and portable): it computes sigmoid(b) and exp(-exp(A_log) * softplus(a + dt_bias)) inside the GDN kernel from the raw projection and sums ba as fp32 split-K partials in-kernel with no zero-init or atomics (`:61`), with the ba projection emitted by the qkvz GEMM launch (`fused_gemm_a16w16_dual_splitk.py:47-60`, tuned for N1=16384 N2=96 K=5120, our 27B shape) (intake-2828#record). In-house budget, C18 27B DFlash2 verify trace ak-c18-27b-df2-v5i-trace-gpu-20261122 (40.07 ms GPU per verify): 96 small q8sk_mul_mat launches for beta/alpha (0.63 ms) and four unfused gate ops x 48 layers (0.88 ms), plus norm/z gate (0.42 ms) and the state gather k_get_rows (0.53 ms); the existing softplus fusion (ggml-cuda.cu:4252 @ a6a32c1) does not engage there (cause unknown). Arms in order: (a) row-concat ssm_beta|ssm_alpha into one Q8_0 tensor at load and one launch writing [KS, T, 2*H_v] fp32 partials without atomics; (b) a fusion from that output to GATED_DELTA_NET passing raw b/a, ssm_dt and ssm_a to the C19 fused K=T and rows kernels, which sum the partials and apply the gate in their prologue; (c) and (d) (norm + silu(z) epilogue; state pool by slot) only after (a)+(b). Side effect: removes the unordered atomic split-K on ssm_ab. Step 1 (no GPU): from the 27B trace above and ak-c18-a3b-mtp-trace-gpu-20261122, list the launches each arm removes with their ms and confirm from C19 source how the GDN kernels read g/beta; stop-on-futility if (a)+(b) remove < 0.8 ms per 27B verify. Then one op/trace row: stop-on-answer when GDN-input ms per verify <= 0.4 ms with test-backend-ops GATED_DELTA_NET parity and 27B KLD vs C19 <= 0.003; then 27B DFlash2 np1 e2e, 8 ABBA pairs, KEEP iff CI lower > +1% and no cell < -1%; futility if the first variant saves < 0.6 ms per verify; gate-class futility-only. Build: experimental branch from C19 a6a32c1, knob default off, region-lock claim; coordinate with AK-BW-27B-ACTQUANT-FUSE and AK-BW-A3B-DENSE-STEP2 (b) (same concat).",
     "acceptance": "step-1 launch/ms table filed, then an op/trace verdict and a 27B e2e KEEP/DROP for arms (a)+(b); A3B runs only after a 27B KEEP"
    }
   ]
  },
  "AKI-71": {
   "required_outcome": "The unmeasured verify half of the per-channel lever is decided",
   "review_status": "preserved",
   "review_basis": "AK-ASM-I8GEMM-PERCHANNEL-GEMV",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-ASM-I8GEMM-PERCHANNEL-GEMV",
     "task_text": "        - [ ] **AK-ASM-I8GEMM-PERCHANNEL-GEMV** [inference] Measure the verify-GEMV half of AK-ASM-I8GEMM-PERCHANNEL that no row has measured (the port row measured only prefill, dispatch at ne11 >= 129, 0.821x). On the 27B verify trace ak-c18-27b-df2-v5i-trace-gpu-20261122 q8mf6_mul_mat is 25.2 of 40.07 ms at 1071 GB/s (71% of the 1.498 TB/s measured peak); a dense per-row int8 layout (32 B per 32 weights plus one scale per row versus Q8_0's 34 B) reads 1/17 fewer weight bytes and drops the per-block scale load; the 27B weight half already passed (AK-ASM-I8GEMM-PERCHANNEL-KLD: KLD 0.001015, dPPL +0.082%). Layout source: AITER per-channel 8-bit weight GEMMs (intake-2828#record). Step 1 (no GPU): from C19 mmq-q8-mf.cu record how the MF_INPLACE layout streams per-block scales and the bytes per weight q8mf6 reads; ceiling = bytes saved / bytes streamed x q8mf6 share of verify; stop-on-futility if the ceiling is < 3% of verify GPU time. Step 2 (GPU, timing only): a speed-of-light knob in q8mf6 that skips the per-block weight scales (numerically wrong, timing only) at the 27B shapes, n 1/4/8/16; futility if it saves < 3% of q8mf6 ms at n=8; at >= 3%, the real layout behind a default-off knob gated by 27B KLD <= 0.003 and |dPPL| <= 0.5%, then 8 ABBA pairs, KEEP iff CI lower > +1%; gate-class futility-only. Confidence low: at 71% of peak the kernel is not purely byte-bound.",
     "acceptance": "step-1 ceiling filed, and either a futility close or a step-2 timing verdict (plus, at >= 3%, an e2e KEEP/DROP)"
    }
   ]
  },
  "AKI-72": {
   "required_outcome": "No repeat of prior AITER work",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: per-family reasons in /mnt/raid0/llm/tmp/dive-ak-1123/rev1/aiter_re.md section 5 (AK-MMID-MF FUTILITY_OP, H8/H8b DROP, GGML_HIP_FA_TAIL_SPLIT FUTILITY)",
   "task_refs": []
  },
  "AKI-73": {
   "required_outcome": "The entry no longer over-reads the theorem",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only K1; Stage 4 appends a scope line to intake-2845 dive_corrections",
   "task_refs": []
  },
  "AKI-53": {
   "required_outcome": "Revisit when the source is verifiable",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M7: intake-2848 is stage1-unverified (PDF only), so its mechanism cannot justify work yet",
   "task_refs": []
  },
  "AKI-54": {
   "required_outcome": "Drafting variants",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: COPYSPEC-27B 46.95 vs 59.32 tok/s on the MI210; the exact-index question is SPEC-COPY-COV-1. (Multi-draft verifiers moved to SPEC-DTREE-DICE; the single-draft optimality result does not cover trees.)",
   "task_refs": []
  },
  "AKI-55": {
   "required_outcome": "Rejection analysis",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: the dive marked it its own hypothesis; CreditFilter weights act only on training gradients",
   "task_refs": []
  },
  "AKI-56": {
   "required_outcome": "One served uniform-lane shuffle tested as readlane",
   "review_status": "preserved",
   "review_basis": "MMID-HELPER-READLANE",
   "task_refs": [
    {
     "owner": "handoffs/active/kernel-champion-and-promotion.md",
     "task_id": "MMID-HELPER-READLANE",
     "task_text": "- [ ] **MMID-HELPER-READLANE** [non-inference] Add a readlane arm to the MMID-HELPER-N10-GATE build (no separate row; intake-2825#02, intake-2825#03): replace the one wave-uniform-lane `__shfl_sync` in the served mm_ids helper (ggml/src/ggml-cuda/mmid.cu:92 @ a6a32c1) with `__builtin_amdgcn_readlane`, record the ISA diff (instruction count and VGPRs) and hand the arm to the gate row. Stop if the ISA is unchanged; the gate row's helper us/call decides KEEP (>= 3% helper gain) or DROP.",
     "acceptance": "arm commit SHA with the ISA diff recorded under this box and the arm listed in the MMID-HELPER-N10-GATE row argv"
    }
   ]
  },
  "AKI-57": {
   "required_outcome": "HIP micro-ops",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: group_mask_warp_inplace and gated-delta-net-mma are absent; no served model has n_used 16 or 32; zero ballot/popc rank sites at a6a32c1",
   "task_refs": []
  },
  "AKI-58": {
   "required_outcome": "Port only if the helper stays >= 3%",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M8",
   "task_refs": []
  },
  "AKI-59": {
   "required_outcome": "Two port ideas decided on our traces",
   "review_status": "preserved",
   "review_basis": "RKA-TRACE-SHARES-1",
   "task_refs": [
    {
     "owner": "handoffs/active/rocm-kernel-authoring.md",
     "task_id": "RKA-TRACE-SHARES-1",
     "task_text": "- [ ] **RKA-TRACE-SHARES-1** [non-inference] Answer two upstream-port questions from existing traces and arithmetic only (intake-2826#04, intake-2840#00, intake-2840#01): (a) the share of `flash_attn_mask_to_KV_max` in prefill GPU time on the served 27B and Q38FN traces (it only launches when Q->ne[1] >= 1024 or ne[3] > 1, fattn-common.cuh:1493 @ a6a32c1); under 1% closes the ballot-reduce port; (b) for np4 KV-length mixes, max/mean live KV chunks per block in the gv GQA-verify kernel under uniform splits (fattn-gqa-verify.cu:769-781 @ a6a32c1) for padded and unified layouts; max/mean <= 1.15 closes the min-max planner idea, > 1.3 files one GPU row.",
     "acceptance": "both numbers with the trace paths recorded under this box and each idea closed or a row filed"
    }
   ]
  },
  "AKI-60": {
   "required_outcome": "Verify attention",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: gfx90a has no FP8; gv n_splits==1 only below n_kv 512; plain n=1 decode is not served",
   "task_refs": []
  },
  "AKI-61": {
   "required_outcome": "Port decided on our TTFT share",
   "review_status": "preserved",
   "review_basis": "TOK-BPE-TIME-1",
   "task_refs": [
    {
     "owner": "handoffs/active/cpu-decode-roofline-program.md",
     "task_id": "TOK-BPE-TIME-1",
     "task_text": "- [ ] **TOK-BPE-TIME-1** [non-inference] Time tokenization of one real 100k-token orchestrator prompt with the vocab only (no weights, one core, seconds) on the Qwen3.8-27B and Qwen3.6-35B-A3B vocabularies at C19 a6a32c1 (intake-2829#00, intake-2829#04, intake-2829#05). Compare with the cached-turn TTFT of the same roles from existing rows. If tokenization is under 2% of cached-turn TTFT, close the upstream #32859 port; if 2% or more, port it as one commit on an experimental branch after upstream human review, with test-tokenizer-0 for qwen2 and qwen35 and a token-id diff on 20 real prompts.",
     "acceptance": "per-vocab tokenize ms and share of cached-turn TTFT recorded under this box with the port closed or filed"
    }
   ]
  },
  "AKI-62": {
   "required_outcome": "Cold TTFT",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: derived share under 0.1% of a cold 100k prefill (intake-2829#05)",
   "task_refs": []
  },
  "AKI-63": {
   "required_outcome": "A post-training lane decision",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M9: operator decision OD-1, then E5 Stage-B releasing the host",
   "task_refs": []
  },
  "AKI-64": {
   "required_outcome": "Handoff text matches hardware reality",
   "review_status": "preserved",
   "review_basis": "EVT-DGX-PREMISE-FIX",
   "task_refs": [
    {
     "owner": "handoffs/active/eval-tower-program.md",
     "task_id": "EVT-DGX-PREMISE-FIX",
     "task_text": "- [ ] **EVT-DGX-PREMISE-FIX** [non-inference] Replace the stale premise at eval-tower-program.md:159 (\"Training requires GPU (GRPO needs 16 rollouts/step) — defer to DGX Spark.\") with: training requires a GPU; the DGX Spark path is closed and the MI210 is present, so a post-training lane is an operator decision (intake-ak-1123 OD-1; intake-2834#record).",
     "acceptance": "sentence replaced and the 'when DGX Spark available' roadmap heading at :161 re-pointed to the OD-1 outcome"
    }
   ]
  },
  "AKI-65": {
   "required_outcome": "Scope recorded",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only K5: single-turn math, full-parameter, Qwen3-8B-Base, data-order seeds (intake-2834)",
   "task_refs": []
  },
  "AKI-66": {
   "required_outcome": "Citable when verifiable",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger M7",
   "task_refs": []
  },
  "AKI-67": {
   "required_outcome": "Operator sees reader disagreements",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only K6 with operator decision OD-4 on whether to drop the 18 anchors (never auto-overturned)",
   "task_refs": []
  }
 },
 "proposed_tasks": [
  {
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "task_text": "  - [ ] **SPEC-ID-RAGGED-1** [non-inference] Add `test-multiseq-ragged-rollback` on a fresh llama.cpp-experimental branch from C19 a6a32c1 as the mechanism check for the Q4X replay divergences that C18-REPLAY-Q4X-CONC-BISECT left UNLOCATED (8 ON-only phase-C first divergences, not tie flips, not on one slot) (intake-2844#01, intake-2844#02): 3-4 sequences in one batch, a different accepted-draft count per sequence each round, `kv_unified` on and off, both snapshot rollback and RS replay, compared token-for-token and state-for-state with a single-sequence reference run. No test at a6a32c1 covers multi-sequence ragged rollback (`tests/test-recurrent-state-rollback.cpp:13` sets n_seq_max = 1). If it fails, the fix comes before any Q4X replay re-allow; if it passes, the divergences are classified with SPEC-ID-GATE-1."
  },
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **SPEC-ID-GATE-1** [non-inference] Write the width-aware identity-gate protocol for speculative-decoding gates and apply it to two existing verdicts (intake-2842#00, intake-2842#04, intake-2844#record, intake-2844#02; in-house INF-70 E2a: `LLAMA_SPEC_EXACT` modes at tools/server/server-context.cpp:42-112 @ a6a32c1, opt-in `GGML_ROWEXACT_N` at ggml/src/ggml-cpu/ggml-cpu.c:1505 @ a6a32c1). Protocol: (a) an identity check compares arms only inside one verify-width class, or under `LLAMA_SPEC_EXACT=serial` / `GGML_ROWEXACT_N`, because pinning one kernel backend does not remove verify-path divergence (intake-2842#04); (b) never import a literature exact-match rate as a threshold (intake-2844#record); (c) classify every first divergence as near-tie flip (top-2 margin inside the measured A/A floor), DEGEN_AFTER_TIE (repeat loop after a tie, a defect when the speculation-off np4 control shows none, intake-2844#02) or defect. Apply it: re-judge the CAFE-1 p-min decline (speculative-decoding.md:505, decided on 100% identity alone; a CPU row only if its logprobs were not retained), and write a recommendation to CAFE-3's owner on its identity-100% done-when (speculative-decoding.md:523) without editing that box."
  },
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **SPEC-ID-NOISE-1** [inference] Measure the width-1 versus width-W teacher-forced logit noise that SPEC-ID-GATE-1 needs as its A/A floor, on 27B Q8_0 + DFlash2 (MI210, C19 GPU store) and Q38FN UD-IQ4_XS + MTP (CPU quarter q0-q2, C19 CPU store). Frozen input: 64 prompts from the DF2-13 prompt set, digest recorded, split into calibration and holdout halves. Per position: max |delta logit| and top-2 margin between width 1 and each served verify width; first-divergence margin histogram; share of first divergences at exactly zero margin (intake-2842#03). Extra arm on HIP: `LLAMA_SPEC_EXACT=redecode` versus `serial`, pre-registered to fail because redecode reuses verify-written KV and GDN state (intake-2843#02). Question: what tolerance tau separates noise from defect per width class. Stop-on-answer when the holdout q99 of |delta logit| is within 10% of the calibration q99 on both devices; stop-on-futility on residency proof failure (verify_ggml_linkage.sh plus nonzero VRAM sampled during the run), store mismatch or STOP/deadline; gate-class futility-only. Complete denominator: every prompt reported, refusals counted."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "  - [ ] **GGML-DET-POSINV-TEST** [non-inference] Add a position-invariance unit test to the branch that carries `GGML_DETERMINISTIC` (fork commit bef2e4c7d; absent from C19 a6a32c1): at fixed M in {2, 4, 8, 16}, permute the rows of src1 and require bitwise-identical output rows after un-permuting, for the MI210 Q8_MF V5 and q8_skinny paths with GGML_DETERMINISTIC=1, and assert that the split count depends only on (M, N, K) (intake-2843#03). This is the property GGML-DETERMINISTIC-REDUCE-SCRATCH must preserve."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **AK-MMQ-SK2** [inference] Stream-k at small column counts on gfx90a (intake-2824#record, intake-2824#01, intake-2824#02, intake-2837#01, intake-2838#00). Step 1 (code, region-lock claim for the build): on a fresh llama.cpp-experimental branch from C19 a6a32c1, hand-port upstream #30553 (stream-k grid capped at useful work) and #30022 (force-tiling rule) as two default-off commits with the predicate widened from GCN to CDNA behind env `GGML_HIP_MMQ_CDNA_FORCE_TILING=1`, plus a separate build arm with #32837's CDNA table cell (256 threads, occupancy 2, I=64) in mmq-config-cdna.cuh. Our launcher always runs 104 stream-k blocks (ggml/src/ggml-cuda/mmq.cuh:1318-1366 @ a6a32c1). Step 2 (zero compute): census served MMQ shapes (27B np4 verify M=36, A3B Q8_0 MUL_MAT_ID above the MMVQ cap, Q4_K/Q6_K at 5-128 rows) and record where force-tiling fires and where the cap changes the grid. Step 3 (one GPU row, cap 1 GPU-h): arms D default, A force-tiling env, B table build; cells Q4_K MUL_MAT n 5/8/16/32 on 17408x5120 and 5120x17408, Q8_0 n 17/36/64, A3B Q8_0 MUL_MAT_ID n 16/64, n=512 guards; order: knob-honoured witness, test-backend-ops MUL_MAT/MUL_MAT_ID correctness (bit-identity versus C19 is not expected: a grid change regroups FP32 sums), ISA audit for B, then 7 interleaved reps per cell with a same-row A/A. KEEP_CANDIDATE if any cell beats its A/A by >= 3% with no n=512 guard worse than -3%; else CLOSE. Futility: correctness fails, knob not honoured, B spills or loses occupancy, residency fails; gate-class futility-only."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "  - [ ] **AK-TIMING-ZERO-1** [non-inference] Close the three timing-ingestion holes that let zero or nonfinite numbers through, in epyc-inference-research scripts/kernel_rnd/autokernel/loop (intake-2828#03): `bench.py:424` returns `avg_ts` checked only for finiteness, `bench.py:642-694` silently drops `value <= 0`, and `graph_profile_reader.py:45` accepts `>= 0`. Make each a recorded refusal (value must be finite and > 0) matching the existing strict gate in `execution/microbench.py:1887-1897`, and add unit tests that feed 0, -1, NaN and inf through each path and expect a refusal, not a sample."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "  - [ ] **AK-RECEIPT-ARMS-1** [non-inference] Make keep receipts self-validating at consumption (intake-2839#02, intake-2839#03, intake-2841#02): `ExperimentalKeepReceipt` (loop/surface_fold.py:140-193) validates `comparison` only by digest (:174-178), while the both-arms check lives at run.py:2450-2459 and bench.py:232-256. Move that check into one shared validator called when a receipt is consumed; require the comparison block all-or-none (measured value, baseline value, baseline path, measured_under, measurement reference); allow perf fields to be written only by the measuring step; add an authorising-act reference field to `CandidateTarget` (candidate_manifest.py:201-250); re-validate every retained receipt and list any that fail."
  },
  {
   "owner": "handoffs/active/rocm-kernel-authoring.md",
   "task_text": "- [ ] **RKA-DECISION-RECORD-1** [non-inference] Specify one fast-path decision record for the fork's HIP dispatch (design only; intake-2839#00, intake-2839#04): route chosen, reason, kernel id, build digest and knob source, emitted once per process per op-shape class and readable without a profiler, plus an audit rule that no fast path may fall back after launch. Motivation is in-house: C16-TOPK-STAGE and C15-GV-BW closed with the witness absent, and today only per-row oracles exist (cpu_route_witness.py, the once-per-process witness at fattn-gqa-verify.cu:828-830 @ a6a32c1)."
  },
  {
   "owner": "handoffs/active/context-and-token-economy.md",
   "task_text": "- [ ] **TOC-SUPERSEDE-1** [non-inference] Replay a tool-supersession classifier offline over recorded REPL and Claude Code transcripts and over AgentDiet's released trajectories (intake-2833#00, intake-2833#01, intake-2853#00, intake-2851#02, intake-2852#00). Rule: a later read or edit of the same file path, a re-run of the same normalized shell command, a later build whose targets overlap, or a passing re-run of the same test supersedes the earlier tool output; a round whose outputs are all superseded becomes a candidate; 2-round grace window; no model calls. Report the candidate token share of final histories, the hash-dedup repeat count, and an eviction-regret rate (superseded content later re-read, by content hash). Six controls: frozen transcript manifest with digest, baseline = no eviction and the current age-based `_clear_stale_tool_outputs` (orchestrator src/graph/helpers.py:558), per-transcript outputs retained, holdout = transcripts after a fixed date, every transcript counted, rule fixed before the run. Stop-on-answer: share < 15% closes the supersession arm; >= 15% fires the TOC-CMP-4 trigger below."
  },
  {
   "owner": "handoffs/active/kv-cache-program.md",
   "task_text": "  - [ ] **KV-EVICT-COST-1** [inference] Build a read-only evict-cost probe for llama-server and a device break-even table (intake-2833#02, intake-2850#02, intake-2849#03, intake-2853#04). Probe: for a proposed cut, predict re-prefilled tokens = T' - p*, with p* the nearest checkpoint at or before the cut (restore logic tools/server/server-context.cpp:5126-5170 @ a6a32c1; hybrid models cannot shift, `can_shift` false at src/llama-memory-recurrent.cpp:832), classify the cut as checkpoint-aligned or not, and predict seconds as a + b x cells fitted from existing prefill rows. Check it in one small CPU smoke on 20 synthetic cuts against measured `n_prompt_tokens_processed` (pass at 19/20 exact token counts). Then publish a doc table per device (MI210 and one CPU quarter) of break-even gain for a cut, with a residual column max(0, cost - inter-turn slack) and a row for an LLM reflection call; device-specific commit caps, never the paper's H100 cap."
  },
  {
   "owner": "handoffs/active/routing-program.md",
   "task_text": "- [ ] **RTG-ASK-1** [non-inference] Calibrate when our small roles ask for help, from logs only (intake-2835#00, intake-2835#01, intake-2855#00, intake-2855#02, intake-2856#00). (1) Tabulate escalations per task and role from existing taps and progress logs, counting `escalate()` hand-offs (src/repl_environment/routing.py:303-319) and consult advice separately. (2) Fit a residual-risk probe on logged non-escalated episodes labelled by their own episode outcome and compare it with the entropy-only baseline (generation_monitor.py). (3) Replay-evaluate replacing the fixed `escalation_penalty = len(escalations) * 0.15` (orchestration/repl_memory/q_reward.py:173) with a price solved against a consults-per-task budget. Six controls: frozen log manifest with digest, baseline = current rule policy (src/orchestration/escalation.py:227-350), per-episode outputs, holdout = later time window, all episodes counted, decision rule fixed first: adopt the probe only if its holdout AUROC beats entropy-only by >= 0.05; stop and report counts only if fewer than 200 escalation-eligible episodes exist."
  },
  {
   "owner": "handoffs/active/autopilot-program.md",
   "task_text": "- [ ] **AP-BSV2-ACCEPT-RIGOR** [non-inference] Amend the BSV-2 accept design and check it by offline replay of existing AutoPilot journals (intake-2836#01, intake-2857#00, intake-2858#00, intake-2859#03, intake-2862#01, intake-2861#04): (a) accept only on tasks disjoint from the batch whose traces fed the proposal; (b) re-run the parent fresh on that batch, never compare against cached parent outcomes; (c) keep the test split sealed until the search ends and pick the headline checkpoint by a training-side rule, never best-on-test; (d) write a per-round decision record with tokens per accepted gain and row statuses completed / solver_limit / infra_error / candidate_error, with retry for infra errors only; (e) state budgets in rollouts or tokens, not iterations. AutoPilot stays stopped; this is design plus replay."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **HIL-EVO-CASES-1** [non-inference] Append to the HIL-2 pre-first-suite-run checklist in docs/design/harness-improvement-loop-design-20261006.md (as HIL-9 did): the HookEvo shipped per-round adoption record as a worked case of in-sample retention (intake-2857#00, intake-2857#01); the Life-Harness four-layer harness taxonomy as the annotation schema and its trace-replay validity gate before any paid evaluation (intake-2858#00, intake-2858#02); the plugin install envelope (signature regex plus syntax check, abort on an infrastructure-defect string) as a BEP-5 input (intake-2857#05); and the matched-budget rule from AP-BSV2-ACCEPT-RIGOR (e). Zero inference."
  },
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **SPEC-COPY-COV-1** [non-inference] Offline copy-match coverage curve before any copy-proposal drafter work (intake-2847#00, intake-2847#01, intake-2832#00, intake-2832#01). Over the archived COPYSPEC P1 outputs (artifacts/copyspec-20261006/source-archive/results/P.jsonl, 85 requests), build an exact longest-suffix index (our ngram-mod at common/speculative.cpp:2651-2812 @ a6a32c1 is a fixed-n hashed window, not longest-suffix) and report, per position, the match length and whether the next 3 tokens agree, for code and prose, plus a leave-one-out variant. Stop-on-answer: if positions with match length >= 5 and >= 3 agreed tokens are under 5% on code and under 2% on prose, close the copy-proposal path; otherwise fire the trigger below."
  },
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **SPEC-COUPLE-MTP-1** [inference] Bound what a draft distribution plus rejection sampling, or coupled draws, could add on the A3B MTP chain at served temperatures (intake-2845#00, intake-2845#record, intake-2831#01). MTP at T > 0 verifies by sample-and-compare against an argmax draft (common/sampling.cpp:693-711, common/speculative.cpp:2116-2119 @ a6a32c1), so per-position acceptance is p(argmax q), below the single-draft 1 - TV ceiling (a per-position, single-draft bound, intake-2845#record) that the DFlash2 rejection path already reaches. Using the SPEC-DTREE-DICE step-2a capture (MTP top-10 drafter logits plus target candidates at every verified row; frozen 64-prompt set with digest; baseline = current sample-and-compare; per-position outputs kept; holdout = second half of the prompts; every position counted), compute offline per served T from SPEC-DTREE-DICE step 1 (expect 0.1/0.2/0.3 and 1.0): the gap 1 - TV(q, p) - p(argmax q) for q = softmax(logit/T) over the MTP top-10, i.e. routing MTP through the existing rejection path. Stop if the holdout gap is under 1% at every served T; file a build box (MTP fills draft distributions, rejection path) if it is 2% or more at any served T with >= 20% token share; gate-class futility-only."
  },
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **SPEC-DTREE-DICE** [inference] Falsify or confirm that pre-sampled target randomness raises expected accepted length on SAMPLED trees at served temperatures (intake-2831#00, intake-2831#03, intake-2831#05), where the single-draft 1 - TV ceiling (intake-2845#record) does not apply and k-candidate verifiers beat the standard one at T > 0 (intake-2846#02, intake-2715#00, intake-2717#01). Today DTREE is greedy-only (spec_tree_nodes_for returns 0 at temp > 0, tools/server/server-context.cpp:5586-5590 @ a6a32c1) and the DTREE dumps are greedy with no target probabilities, so they cannot be replayed at T > 0. Step 1 (code only): log the resolved temperature/top_k/top_p/min_p per request in the inference-tap start event (orchestrator llama_server.py:1739-1747 payload site) and poll /slots on the speculative ports for direct clients; report the token-weighted temperature histogram per drafter (27B DFlash2, A3B MTP) over a declared window; close if the T > 0 share is under 5% on both, else the served T set is its modes. Step 2a (capture): a dump-knob-only fork from the current champion, at served T with keyed draws (seed, position, vocab id), logging per round the drafter lattice/candidates and the target post-sampler candidates plus top-64 logits at every verified row; for DFlash2 force a superset tree (prob-greedy W32 + DICE W16 + chain) into the verify batch while committing through the unchanged chain. A3B MTP first on a CPU quarter q0-q2; the 27B DFlash2 capture is an MI210 capture-only row on gpu-q3 (OD-5 = C, operator 2026-11-23: both captures allowed now). Step 2b (offline replay, CPU) at equal node budget W in {1,4,8,12,16}: V0 served path, V1 same tree with recursive rejection without replacement, V2 Gumbel-max walk with pre-sampled draws and draw-blind selection, V3 DICE draw-informed selection ((alpha, sigma) fitted on the calibration half only), optional V4 exponential-race verifier for k >= 3 siblings (intake-2846#02); metric expected tokens per target pass per served T. Controls: frozen capture and replay script with sha256, baseline V0, per-round per-arm results.jsonl, holdout = second prompt half, every verify round counted, PREDECLARATION.md sealed before replay. Falsifier H1: V3 raises expected accepted length over V0 and over V1 at equal W. Futility: close if holdout V3/V1 < 1.02 at every served T and W <= 16 and V3/V0 stays below the verify-cost break-even; stop-on-answer at a prompt-clustered 95% CI half-width <= 1% on V3/V1 at the highest-share T; gate-class futility-only. A GPU build row (keyed Gumbel-max target sampler, DICE node selection, Gumbel tree walk, T > 0 guard lifted; ABBA np1/np4; KEEP iff tok/s CI-lower > 1.0 and an emitted-token distribution check passes) is filed only if the replay clears break-even; if only V1 clears it, file the sampled recursive-rejection tree row (DTREE-A) instead."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "  - [ ] **AK-BW-GDN-GATE-FOLD** [inference] Fold the GDN beta/alpha projections and gate math into the recurrence kernel on 27B/A3B verify, after AITER v0.1.30 `aiter/ops/triton/gated_delta_net/fused_gdn_decode_qkvz.py` (read at 77ba72b7061a; gfx950 Triton as written, the gate math is scalar and portable): it computes sigmoid(b) and exp(-exp(A_log) * softplus(a + dt_bias)) inside the GDN kernel from the raw projection and sums ba as fp32 split-K partials in-kernel with no zero-init or atomics (`:61`), with the ba projection emitted by the qkvz GEMM launch (`fused_gemm_a16w16_dual_splitk.py:47-60`, tuned for N1=16384 N2=96 K=5120, our 27B shape) (intake-2828#record). In-house budget, C18 27B DFlash2 verify trace ak-c18-27b-df2-v5i-trace-gpu-20261122 (40.07 ms GPU per verify): 96 small q8sk_mul_mat launches for beta/alpha (0.63 ms) and four unfused gate ops x 48 layers (0.88 ms), plus norm/z gate (0.42 ms) and the state gather k_get_rows (0.53 ms); the existing softplus fusion (ggml-cuda.cu:4252 @ a6a32c1) does not engage there (cause unknown). Arms in order: (a) row-concat ssm_beta|ssm_alpha into one Q8_0 tensor at load and one launch writing [KS, T, 2*H_v] fp32 partials without atomics; (b) a fusion from that output to GATED_DELTA_NET passing raw b/a, ssm_dt and ssm_a to the C19 fused K=T and rows kernels, which sum the partials and apply the gate in their prologue; (c) and (d) (norm + silu(z) epilogue; state pool by slot) only after (a)+(b). Side effect: removes the unordered atomic split-K on ssm_ab. Step 1 (no GPU): from the 27B trace above and ak-c18-a3b-mtp-trace-gpu-20261122, list the launches each arm removes with their ms and confirm from C19 source how the GDN kernels read g/beta; stop-on-futility if (a)+(b) remove < 0.8 ms per 27B verify. Then one op/trace row: stop-on-answer when GDN-input ms per verify <= 0.4 ms with test-backend-ops GATED_DELTA_NET parity and 27B KLD vs C19 <= 0.003; then 27B DFlash2 np1 e2e, 8 ABBA pairs, KEEP iff CI lower > +1% and no cell < -1%; futility if the first variant saves < 0.6 ms per verify; gate-class futility-only. Build: experimental branch from C19 a6a32c1, knob default off, region-lock claim; coordinate with AK-BW-27B-ACTQUANT-FUSE and AK-BW-A3B-DENSE-STEP2 (b) (same concat)."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "        - [ ] **AK-ASM-I8GEMM-PERCHANNEL-GEMV** [inference] Measure the verify-GEMV half of AK-ASM-I8GEMM-PERCHANNEL that no row has measured (the port row measured only prefill, dispatch at ne11 >= 129, 0.821x). On the 27B verify trace ak-c18-27b-df2-v5i-trace-gpu-20261122 q8mf6_mul_mat is 25.2 of 40.07 ms at 1071 GB/s (71% of the 1.498 TB/s measured peak); a dense per-row int8 layout (32 B per 32 weights plus one scale per row versus Q8_0's 34 B) reads 1/17 fewer weight bytes and drops the per-block scale load; the 27B weight half already passed (AK-ASM-I8GEMM-PERCHANNEL-KLD: KLD 0.001015, dPPL +0.082%). Layout source: AITER per-channel 8-bit weight GEMMs (intake-2828#record). Step 1 (no GPU): from C19 mmq-q8-mf.cu record how the MF_INPLACE layout streams per-block scales and the bytes per weight q8mf6 reads; ceiling = bytes saved / bytes streamed x q8mf6 share of verify; stop-on-futility if the ceiling is < 3% of verify GPU time. Step 2 (GPU, timing only): a speed-of-light knob in q8mf6 that skips the per-block weight scales (numerically wrong, timing only) at the 27B shapes, n 1/4/8/16; futility if it saves < 3% of q8mf6 ms at n=8; at >= 3%, the real layout behind a default-off knob gated by 27B KLD <= 0.003 and |dPPL| <= 0.5%, then 8 ABBA pairs, KEEP iff CI lower > +1%; gate-class futility-only. Confidence low: at 71% of peak the kernel is not purely byte-bound."
  },
  {
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "task_text": "- [ ] **MMID-HELPER-READLANE** [non-inference] Add a readlane arm to the MMID-HELPER-N10-GATE build (no separate row; intake-2825#02, intake-2825#03): replace the one wave-uniform-lane `__shfl_sync` in the served mm_ids helper (ggml/src/ggml-cuda/mmid.cu:92 @ a6a32c1) with `__builtin_amdgcn_readlane`, record the ISA diff (instruction count and VGPRs) and hand the arm to the gate row. Stop if the ISA is unchanged; the gate row's helper us/call decides KEEP (>= 3% helper gain) or DROP."
  },
  {
   "owner": "handoffs/active/rocm-kernel-authoring.md",
   "task_text": "- [ ] **RKA-TRACE-SHARES-1** [non-inference] Answer two upstream-port questions from existing traces and arithmetic only (intake-2826#04, intake-2840#00, intake-2840#01): (a) the share of `flash_attn_mask_to_KV_max` in prefill GPU time on the served 27B and Q38FN traces (it only launches when Q->ne[1] >= 1024 or ne[3] > 1, fattn-common.cuh:1493 @ a6a32c1); under 1% closes the ballot-reduce port; (b) for np4 KV-length mixes, max/mean live KV chunks per block in the gv GQA-verify kernel under uniform splits (fattn-gqa-verify.cu:769-781 @ a6a32c1) for padded and unified layouts; max/mean <= 1.15 closes the min-max planner idea, > 1.3 files one GPU row."
  },
  {
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "task_text": "- [ ] **TOK-BPE-TIME-1** [non-inference] Time tokenization of one real 100k-token orchestrator prompt with the vocab only (no weights, one core, seconds) on the Qwen3.8-27B and Qwen3.6-35B-A3B vocabularies at C19 a6a32c1 (intake-2829#00, intake-2829#04, intake-2829#05). Compare with the cached-turn TTFT of the same roles from existing rows. If tokenization is under 2% of cached-turn TTFT, close the upstream #32859 port; if 2% or more, port it as one commit on an experimental branch after upstream human review, with test-tokenizer-0 for qwen2 and qwen35 and a token-id diff on 20 real prompts."
  },
  {
   "owner": "handoffs/active/eval-tower-program.md",
   "task_text": "- [ ] **EVT-DGX-PREMISE-FIX** [non-inference] Replace the stale premise at eval-tower-program.md:159 (\"Training requires GPU (GRPO needs 16 rollouts/step) — defer to DGX Spark.\") with: training requires a GPU; the DGX Spark path is closed and the MI210 is present, so a post-training lane is an operator decision (intake-ak-1123 OD-1; intake-2834#record)."
  }
 ]
}
```
