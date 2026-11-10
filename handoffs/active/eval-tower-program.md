# Eval Tower Verification Framework

> **Fold destination** (BRF-T1-F2, BRF-T1-1, route 1a, 2026-11-02): renamed from `eval-tower-verification.md`; absorbs 9 handoff(s) as `## Track:` sections at the end of this file (`bulk-inference-campaign.md`, `eval-benchmark-cost-reduction.md`, `eval-tower-architecture-audit-2026-07-20.md`, `eval-tower-loop-robustness-audit-2026-07-20.md`, `fable5-window2-findings-01-optimizer-integrity.md`, `inference-batch-loop.md`, `prompt-construction-determinism.md`, `re4-protocol-redesign.md`, `scoring-infra-standardization.md`). The body above the first track is the former `eval-tower-verification.md`.

**Scratch**: `/mnt/raid0/llm/tmp/eval-tower-verification/` · worktrees: `/mnt/raid0/llm/worktrees/eval-tower-verification-*`

**Status**: IN PROGRESS — EV-1/2/3/6 code complete; EV-11 scorer flip, EV-11a boxed-Latex companion fix, and EV-11b closed-bin ECE implementation landed. EV-4 is the current quiet-window runnable island in `inference-batch-loop.md`; EV-11c math rebaseline becomes runnable after EV-CONF makes confidence real and the remaining scorer-era prerequisites are settled. EV-5/7/8 remain model-download/build-gated. AA-Omniscience hallucination suite integrated (2026-04-15).

**⚠ Robustness audit 2026-07-20:** [eval-tower-loop-robustness-audit-2026-07-20.md](eval-tower-program.md#track-eval-tower-loop-robustness-audit-2026-07-20) — the EV-11 confidence proxy is a stub (`float(correct)`) wired into live rlvr scoring → ECE constant 0.0 (1182/1182); EV-11b binning is now implemented as the closed-top-bin `stat_tests` definition, but real calibration remains tracked as **EV-CONF** below (gated after the parallel agent's `eval_tower.py` loop fixes; [agent] plumbing + interim, [operator] only the final scoring decision). Plus runner (dirty-stack-on-kill, degenerate→decision_grade), preflight (health-check false-positive, matrix-freshness only checked on reload), and ledger (`INFRA_BLOCKED` wedge) robustness gaps.
**⚠ Architecture audit 2026-07-20 (tower-internal, complements the loop audit):** [eval-tower-architecture-audit-2026-07-20.md](eval-tower-program.md#track-eval-tower-architecture-audit-2026-07-20) — 3 CRITICAL / 16 HIGH / ~55 MED+LOW across scorer identity, question identity, gate soundness, persistence, and test architecture. Headliners: **math_verify silently degrades to exact_match on every threaded eval** (EV-11 no-op resurrected, concurrency-dependent — invalidates EV-11c until fixed); **the live question pool was built by the stale orchestrator adapter registry** — 15 of 33 adapter suites; `omniscience`/`scoring_verifiers` (EV-3!) marked "integrated" here but never actually sampled; **promotion recency exclusion is a qid-namespace no-op**; torn-journal-line startup wedge; no reliability gate; per-suite 1-flip float-boundary regression. Phased owner-tagged fix plan (A–E) in the audit doc; EV-4/EV-11c should not run decision-grade until its Phase A lands.
**Created**: 2026-04-14 (from deep-dive research, 5 papers + 2 subsystem threads)
**Updated**: 2026-07-20
**Priority**: HIGH — [research-evaluation-index.md](research-evaluation-index.md) and `inference-batch-loop.md` route the next operator-gate-free inference batch to EV-4; EV-11c follows once EV-CONF/logprob passthrough and the scorer-era prerequisites are settled.
**Categories**: evaluation, verification, reinforcement_learning
**Tracked in**: [research-evaluation-index.md](research-evaluation-index.md) P8

## Problem / Context

Current `EvalResult` (`safety_gate.py` L44-100) measures 4 metrics: quality, speed, cost, reliability. These are outcome-level accuracy metrics. **They are insufficient for RLVR formalization (AP-27).**

SWE-RM (intake-368) proved this empirically: two verifiers with **identical accuracy** produced completely different RL training outcomes. The difference:
- Verifier A: AUC 0.805, smooth RL training
- Verifier B: AUC 0.710, RL training collapse
- Despite nearly identical test-time-scaling performance (+4.7% vs +4.5%)

**Root cause**: Accuracy (TTS) provides only top-1 ranking ability but hides calibration and discrimination properties that directly affect reward signal quality. The eval tower must track **ECE** (Expected Calibration Error) and **AUC** (Area Under ROC Curve) alongside accuracy before it can serve as an RLVR environment.

## Research Context

| Intake | Title | Key Finding for Eval Tower |
|--------|-------|---------------------------|
| intake-363#00 | LLM-as-a-Verifier | Logprob-based multi-criteria verification: R(t,τ) = (1/CK) Σ p_θ(v_g\|t,c,τ)·φ(v_g). llama.cpp has full vocab access (no k=20 truncation). Cross-family verification critical. |
| intake-367 | Scoring Verifiers (COLM 2025) | 4-metric eval protocol (Top-1, Bottom-1, Spearman ρ, MAE). Reasoning models dominate by 5-9pp for verification. Don't show solution to test generator (10-15pp self-evaluation bias). |
| intake-368 | SWE-RM | TTS ≠ RL effectiveness. Must track ECE + AUC. 2:1 positive-to-negative ratio optimal. MoE 30B/3B active. Hybrid rewards (deterministic + model-based) beat either alone. |
| intake-370 | Aletheia RLVR | Scale-dependent training recipes: 1.5B needs on-policy GRPO, skip thinking traces. 14B needs thinking traces + negative samples. Training is GPU-only. |
| intake-371 | ThinkPRM | Generative PRM via verification CoT. 1% of PRM800K labels achieves parity. +8% OOD on GPQA-Diamond. P("yes")/(P("yes")+P("no")) scoring from logprobs. |

## Per-Tier Verification Design

### T0 (10 sentinel questions, ~30s)

**Current**: `score_answer_deterministic()` — binary exact-match scoring.
**Add**: Logprob logging from inference response. No new model needed.

Store `logprob_confidence` per question — the model's own confidence in its answer, extracted from llama.cpp `/completion` response `completion_probabilities`. This costs nothing at inference time and builds a calibration dataset over time.

### T1 (100 stratified questions, ~5min)

**Current**: Same deterministic scoring as T0, more questions.
**Add**: ECE + AUC computation from accumulated logprob_confidence values.

- **ECE** (Expected Calibration Error): Bin predictions by confidence, compute accuracy per bin, weight by bin size. ~20 lines. Formula: `ECE = Σ_m (|B_m|/n) * |acc(B_m) - conf(B_m)|` with M=10 bins.
- **AUC** (Area Under ROC Curve): Overall discriminative power — can the eval distinguish good from bad configs? ~10 lines.
- **Calibration violations**: Count questions where |confidence - correctness| > 0.5. Flags most miscalibrated predictions.

### T2 (500+ questions, ~30min)

**Current**: Same deterministic scoring.
**Add**: ECE/AUC (from T1) + ThinkPRM-1.5B process verification on **subset of uncertain questions**.

- Deploy ThinkPRM-1.5B (Q4_K_M, ~2GB RAM, 20-40 tok/s on EPYC CPU)
- For N most uncertain questions (identified by T1 calibration data): generate step-level verification CoT
- This gives PromptForge actionable feedback: not just "wrong answer" but "step 3 introduced the error"
- **Cross-family verification mandatory**: verifier model must be different family than generator

## LLM-as-a-Verifier Local Adaptation

### Logprob Truncation: Non-Issue

- [x] ✅ 2026-08-19 — **Re-verified against the frozen v9 tree AND empirically, correcting two defects in
      what this section previously asserted.** [intake-363#00]

**Corrections to the prior text.** (1) It cited `get_token_probabilities()` at
`tools/server/server-common.cpp` **L1755**; the actual location in `production-consolidated-v9`
(`0db32c06e3e5`) is **`server-common.cpp:1256`**. (2) It claimed unconditional full-vocabulary softmax.
In v9 that function reads `llama_get_sampled_candidates_ith()` / `llama_get_sampled_logits_count_ith()`,
so full-vocab holds only when `sampled_ids == nullptr`; with backend sampling active the logits array
is already a subset. **True by default, but now conditional** — do not re-cite it as unconditional.

**What was verified by running it** (llama-server on v9, CPU-only, server started and confirmed
terminated by the verifying session):

| Property | Result |
|---|---|
| `top_logprobs` ceiling | **None.** Requests for 20, 40 and 64 each returned exactly that many. `server-common.cpp:1141` maps `top_logprobs → n_probs` with default 20 and no clamp. |
| Response shape on `/v1/chat/completions` | `{id, token, bytes, logprob, top_logprobs[]}` — the exact OpenAI shape (`server-task.cpp:312-331`) |
| Head is pre-sampler? | **Yes** — temp 0.0 and temp 1.0 return byte-identical logprobs, so the expectation is not silently distorted **provided `post_sampling_probs` stays false** (its default) |
| Score-token coverage | 19 of 20 A–T letters present in the top-20 head, score-token mass ≈ 1.0000 |

**Two silent failure modes** found while verifying, both of which return a well-formed logprob array
containing nothing scoreable — neither raises an error:

1. **A thinking model puts its reasoning token at position 0**, so the head contains *zero* score
   letters and the expectation is undefined. Requires `enable_thinking:false` or a forced prefix to the
   scoring position.
2. **A generation-oriented chat template costs roughly half the signal** — TOPReward's own ablation
   measures ~50% VOC loss on one backbone and ~20% on another. [intake-1170]

Note also that the `TODO: The response format of this option is not yet OAI-compatible` comment at
`server-common.cpp:1140` is **stale relative to the code beneath it**.

| Aspect | Gemini API (k=20) | llama.cpp v9 (uncapped) |
|--------|--------------------|-----------------------|
| Score token coverage | Capped at 20 top logprobs | Uncapped; 20/40/64 all honored |
| Probability mass | ~0.88–0.90 retained at K=99 [intake-1162] | No API truncation; renormalize over the K score tokens |
| Determinism | Non-deterministic (GPU routing) | Deterministic at temp=0 |
| Cost | API pricing | Local compute only |

### Confirmation Bias Mitigation

**The biggest risk**: Repeated verification can AMPLIFY bias. From arxiv:2603.18740, adversarial success increased from 52% (first attempt) to 87% after 4 iterative review rounds.

**Mitigations** (in order of effectiveness):
1. **Cross-family verification**: Different model family for verifier vs generator. Gemini verifying GPT: +4.6pp. Same-family: +1.7pp. ~~This is the strongest defense.~~ **⚠ CONTESTED 2026-08-19 — see the "split the cross-family claim" operator-review candidate below.** It is falsified as an anti-*reward-hacking* defence (intake-875 Proposition 2 excludes every monotone aggregation rule; a three-family min-vote still accepts ~65% of hacked wrong answers) but survives as an anti-*collusion* / self-favouring-bias control, and only while nothing is optimising against the verifier. Do not cite this line unscoped.
2. **Criteria decomposition**: Forces attention to specific aspects (error signals, output matching) rather than holistic judgment.
3. **Pairwise comparison**: A vs B framing is more resistant than absolute scoring.
4. **"Do NOT trust agent self-assessment"**: Explicit debiasing instruction in verification prompts.

**Design rule**: If evaluating Qwen-family generator output, verifier must be non-Qwen (e.g., Llama, DeepSeek, or Ouro-2.6B from P7).

## Scoring Verifiers Benchmark Protocol

### 4-Metric Evaluation Standard

From Scoring Verifiers (intake-367, COLM 2025, NVIDIA Research):

| Metric | What It Measures | Use For |
|--------|------------------|---------|
| **Top-1 Accuracy** | Can verifier identify the best solution? | Primary selection quality |
| **Bottom-1 Accuracy** | Can verifier identify the worst solution? | Rejection/filtering quality |
| **Spearman ρ** | Rank correlation (predicted vs ground truth) | Full ordering quality |
| **MAE** | Score accuracy (predicted vs actual pass rate) | Calibration accuracy |

### Key Findings

- **Reasoning models dominate**: o3-mini 88.2% Top-1 vs Qwen2.5-Coder-32B 79.1% (+9.1pp). Full reasoning required — distilled reasoning (78.2%) gives almost no benefit.
- **Test case scaling**: Standard models plateau at 15-20 test cases. Reasoning models keep improving past 25. Sweet spot: 15 tests with reasoning verifier.
- **Self-evaluation bias**: Never show candidate solution to test generator — 10-15pp Top-1 degradation.
- **Quantile selection**: Generate 5 quality-stratified solutions per problem (0%, 25%, 50%, 75%, 100% pass rates) for verifier evaluation.

### Benchmark Datasets

Available at HuggingFace `nvidia/Scoring-Verifiers`:
- HE-R (164 problems, ~9.6 tests/problem) and HE-R+ (164, ~764 tests/problem)
- MBPP-R (978 problems, ~3.0 tests/problem) and MBPP-R+ (378, ~108.5 tests/problem)

## Aletheia Training Recipes (Scale-Dependent)

From Aletheia (intake-370, TU Darmstadt):

| Scale | On-policy GRPO | Thinking Traces | Negative Samples | DPO Viable? |
|-------|----------------|-----------------|-------------------|-------------|
| **1.5B** | Essential | Skippable | Required (+10-20% without) | No (-23.4%) |
| **7B** | Preferred | Helpful | Required | Yes (with good data) |
| **14B** | Preferred | **Mandatory** | **Critical** (stability) | Yes (Easy→Hard) |

**For our CPU-only environment**: The 1.5B scale is the sweet spot for verification model inference. Training requires GPU (GRPO needs 16 rollouts/step) — defer to DGX Spark. Pre-trained ThinkPRM-1.5B or Aletheia-1.5B models can be downloaded and quantized today.

**Training roadmap** (when DGX Spark available):
- Binary outcome rewards, 16 rollouts/step, temperature 1.0, constant LR 1e-6
- 2:1 positive-to-negative ratio (SWE-RM finding)
- No thinking traces at 1.5B scale (Aletheia finding)
- On-policy GRPO (not DPO, not RAFT)

## Implementation Phases

### EV-1: Add confidence to QuestionResult — ✅ 2026-04-15

- [x] Add `confidence: float = 0.0` to `QuestionResult` at `eval_tower.py` L52
- [x] In `_eval_question()`, set `confidence = float(correct)` as initial proxy. For `code_execution`, use pass_rate from `scoring_config` when available.
- [x] **Note**: Orchestrator ChatResponse does NOT include logprobs. Logprob passthrough from llama-server is a separate infrastructure task. The `confidence` field is ready to accept real logprob values once that lands.

**Files modified (EV-1 historical)**: `eval_tower.py` (QuestionResult dataclass + _eval_question)

### EV-CONF: Logprob passthrough — make `confidence` real (the real fix under EV-11b; surfaced by the 2026-07-20 audit)
**Why.** The EV-1 `confidence = float(correct)` stub is tautological → ECE is a constant **0.0** (1182/1182 journaled) → `rlvr_tiers._calibration_component = 1.0 − ece` is pinned to a phantom **1.0**, silently worth **10–15% of every RLVR tier score** (`rlvr_tiers.py:130,151`; required_metric tiers 2–3). **EV-11b (ECE binning) is moot until confidence is real** — flipping the binning alone ships a still-degenerate metric.
**Why not done yet (GATED, not "operator-only-forever").** The plumbing lives in `eval_tower.py` and the RLVR scoring trust boundary. The loop-owned denominator/EV-11b edits are now landed locally; schedule EV-CONF as the next scoring-plumbing step before EV-11c math rebaseline.
- [x] **[agent, interim — do FIRST, low-risk] Neutralize the phantom now.** ✅ 2026-07-21 — implemented as the pre-approved `confidence_is_real` gate (orchestrator, takeover session): `rlvr_tiers.rlvr_reward_from_result` zeroes BOTH `_calibration_component` and `_discrimination_component` + appends blocker `confidence_not_real` unless `details['confidence_is_real']` is True (stub/mixed-provenance/legacy rows all fail closed). Operator ratified consumption posture same day (op-bundle ESC-7): keep n_probs default-on accruing, decide real-ECE re-entry with EV-4's calibration data. Known follow-up: `export_rlvr_environment`'s SimpleNamespace doesn't thread the flag → exported rows are all `confidence_not_real` until ESC-7's final decision (correct fail-closed interim).
- [x] **[agent] Plumbing.** Thread `completion_probabilities` from llama-server (`/completion` `n_probs`) → orchestrator `ChatResponse` → `eval_tower` `confidence`, replacing the `float(correct)` default when probability rows are present while keeping `code_execution`/`rubric` overrides. ✅ 2026-07-21 — additive opt-in path: `ChatRequest.n_probs` → model-server `InferenceRequest.n_probs` → llama.cpp `/completion` `n_probs` → `InferenceResult.completion_probabilities` → direct-mode `ChatResponse.completion_probabilities` → EvalTower `confidence_source=completion_probabilities_geomean`; `confidence_source_counts`/`confidence_is_real` are stamped in aggregate details. Verify: `uv run pytest tests/unit/test_llama_server.py tests/unit/test_seeding_orchestrator.py tests/unit/test_inference_mixin.py tests/unit/test_chat_pipeline_stages.py tests/unit/test_eval_tower_concurrency_metrics.py -q` (198 passed).
- [x] **[operator + loop] Scoring decision (EV-11b).** ✅ 2026-07-20 — operator selected the closed-top-bin `stat_tests.expected_calibration_error` definition; `_aggregate` now emits `details["ece_binning"]="closed_top_bin_stat_tests"` and `details["ece_instrument_era"]="ev11b_closed_bin_2026_07_20"`. The separate real-confidence / re-entry-to-gating decision remains under EV-CONF.

### EV-2: ECE + AUC in _aggregate() — ✅ 2026-04-15

- [x] Add `ece: float = 0.0`, `auroc: float = 0.0`, `calibration_violations: int = 0` to `EvalResult` at `safety_gate.py`
- [x] In `_aggregate()` at `eval_tower.py`: 10-bin ECE computation, sklearn AUC with fallback for degenerate confidence, calibration violation count
- [x] Updated `to_grep_lines()` to include ECE/AUC/calibration_violations for log parsing
- [x] **Note**: With binary confidence proxy (float(correct)), ECE is trivially 0. Becomes meaningful once logprob passthrough or code_execution pass rates provide continuous confidence.

**Files modified**: `safety_gate.py` (EvalResult dataclass + to_grep_lines), `eval_tower.py` (_aggregate)

### EV-3: Download Scoring Verifiers benchmarks — ✅ 2026-06-19

- [x] Download from HuggingFace `nvidia/Scoring-Verifiers` (HE-R, HE-R+, MBPP-R, MBPP-R+) to `/mnt/raid0/llm/data/eval/scoring_verifiers`
- [x] Create adapter class in `scripts/benchmark/scoring_verifiers_adapter.py`
- [x] Register in `dataset_adapters.py` / `suites.py` as suite `scoring_verifiers`
- [x] Validate: load datasets, verify schema, count candidate solutions

**Files**: `scripts/benchmark/scoring_verifiers_adapter.py`, `dataset_adapters.py`, `suites.py`, data storage at `/mnt/raid0/llm/data/eval/scoring_verifiers/`

**2026-06-19 correction**: the downloaded JSONL schema stores one problem row
with `all_solutions[]` candidate solutions and `average_test_score` oracle
scores. Research `7c11920` expands each candidate into a labeled verifier item
instead of treating the problem row as one unlabeled example. Validation:
`39` adapter tests passed, `py_compile` passed, and the real local snapshot
loads `6,701` candidate-level items across HE-R/HE-R+/MBPP-R/MBPP-R+ with
`3,395` expected `correct` and `3,306` expected `incorrect` labels.

### EV-4: Calibration baseline (needs inference)

**2026-11-01 reconciliation:** EV-4c subsequently superseded the original EV-4b
calibration attempt, but the [2026-09-16 ledger caveat](../../coordination/inference-batch/ledger.jsonl)
suspends its ECE/AUROC as decision-grade evidence because speculative decoding
contaminated token probabilities. The contamination size is unmeasured; accuracy
remains usable. EV-11c is already terminal, so waiting for it to finish is stale.
A replacement calibration run needs a verified uncontaminated confidence source,
current serving and topology attestation, and a fresh eligible run contract; do
not reuse the old manifest's v9 topology without revalidation. EV-PROTO's alternate
execution modes are not required for that replacement. [belief: cc]

- **[declined: ws58 2026-11-03 content-review: merged into EV-4b — the accuracy leg is done and the calibration axes are EV-4b's rerun; the "v7 contention-matrix" gate is era-stale]** **EV-4** — Complete the decision-grade HE-R+ calibration baseline through the inference-batch loop after v7 contention-matrix recertification. *(accuracy leg DONE; calibration axes pending the EV-4b rerun below)*
- [x] Run current eval tower on Scoring Verifiers HE-R+ benchmark ✅ 2026-07-21 — two-phase run on the E7 instrument (frontdoor @ certified concurrency 3, worker_general `--allow-serial`): **accuracy BANKED** frontdoor 0.7085 (820/820), worker_general 0.6572 (814/820; unscored rows excluded per REL-1); dataset_sha256 `87eaabbd…` identical across arms; ledger `DONE_MARGINAL_OBS` per the entry's own authored marginal fork.
- [x] Diagnose the calibration-axes outcome ✅ 2026-07-21 — ECE 0.0/AUROC None/Spearman 1.0 = degenerate BY DESIGN: EV-CONF suppressed `n_probs` for `code_execution`-scored questions and all scoring_verifiers items are code-execution-scored; also means the ranking metrics (Top-1/Bottom-1/ρ/MAE) were structurally unmeasurable with binary confidence. Operator decided **ESC-7-EXT Option A** same day: code_execution now captures generation-logprob geomean confidence (test verdict stays the label; landed in orchestrator).
- **[declined: ws58 2026-11-03 content-review: superseded by the operator correction of 2026-07-23 (cross-fleet arm-parallelism box): overlapping fleets serialize under CROSS_ROLE_DISJOINT_PLACEMENT, so option (a) is not viable and option (b) was already declined as a different instrument]** **EV-PROTO — rebaseline wall-clock protocol options** (from the 2026-07-21 EV-11c 26h-serial run): (a) **arm-parallelism** — different-role arms run on separate servers, so concurrent arms are compute-identical to serial (contention shifts timing only, not logits); adopt for future multi-role rebaselines with a protocol note relaxing sole-occupancy when no speed axis gates (≈2× wall saved). (b) **pinned slot-batching** — in-server continuous batching jitters logits (FP reduction order) and hence sampled tokens + completion_probabilities at temp>0; NOT poison but a DIFFERENT instrument — only with the batch level declared in the protocol id (precedent: MEASUREMENT.md pins T1 eval concurrency 3 as instrument identity). Prereq: teach the tower's concurrency ladder to distinguish live-instance count from per-instance slots. Do NOT mix batching levels within one comparison. (c) **direct-port sharded mode** — the harness assigns question i → quarter instance i mod N, bypassing the dispatcher: disjointness true by construction when N idle same-shape quarters exist, and the deterministic question→instance mapping is BETTER for reproducibility than dispatcher placement. Cost: new harness mode (runner speaks the orchestrator API today) + exits the journal/provenance path, so requires its own protocol id + provenance stamping. Contrast with the dispatcher path, which is gated on the Step-2 SHAPE_AWARE_CONTENTION arming chain (ROUTE-A1 → WP-8) — the admission gate refuses same-role co-placement it cannot prove disjoint, despite J5 certifying quarter co-run free (safety interlock currently dumber than the data we hold; 2026-07-21 diagnosis).
- [x] ✅ 2026-07-23 (`4e684678` — eval-scoped connection-level backoff, 60s budget, REL-1-honest) **EV-RUNNER-BACKOFF — eval client reconnect backoff** (from the 2026-07-21 burned arm): `call_orchestrator_forced`/the window runner churned ~680 questions as instant connect-errors during a ~1min API reload window (no backoff, no retry-on-connect-refused). Add bounded exponential backoff on connection-level failures (NOT on inference errors — those stay honest REL-1 errors) so an API restart pauses the run instead of burning the question budget. Pairs with the SIGSTOP deploy procedure (progress 2026-07-21).
- [ ] **EV-4b — rerun the calibration axes on the Option-A scorer** (chained to execute when EV-11c frees the window): real code-domain ECE/AUROC/Top-1/Bottom-1/ρ/MAE on HE-R+; supersedes the marginal run's calibration axes via ledger append. Absorbs EV-4 and the calibration-violation question: with the Option-A scorer on HE-R+ (ECE/AUROC/Top-1/Bottom-1/rho/MAE), report which question types are miscalibrated; this run is the comparison point for later verification changes. Era: current v10 stack, not v7.
- **[declined: ws58 2026-11-03 content-review: merged into EV-4b (needs its data; same run)]** Identify calibration violations — which question types produce miscalibrated confidence? *(needs EV-4b + EV-11c data)*
- **[declined: ws58 2026-11-03 content-review: a statement, not a task; now carried inside EV-4b]** This baseline is the comparison point for all subsequent verification improvements

**Dependencies**: Inference stack must be running. Can be folded into a Package B/C run.

### EV-5: Deploy ThinkPRM-1.5B for T2 process verification (~100 lines)

- [x] Download ThinkPRM-1.5B from HuggingFace, quantize to Q4_K_M GGUF (~2GB) ✅ 2026-10-30 — [no-belief: operational model acquisition and format/load validation; no decision-grade inference claim]. Pinned `launch/ThinkPRM-1.5B` revision `fcf2c6f6ca28ac2b901206609d8714845290f72e`; produced `ThinkPRM-1.5B-Q4_K_M.gguf` (1,117,320,992 bytes; SHA-256 `ffabf3ea931fd710d8197704e6afd6331bf3b7c3c1af0b175e3f0f9dbf5cfc49`). A 16-token capped native control using CPU llama-cli loaded the model and generated output (6.081 s; peak RSS 1,875,025,920 bytes). Elapsed time and RSS validate bounded execution only; verification quality and comparative performance were not evaluated.
- *Moved to [`model-evaluation-queue.md`](model-evaluation-queue.md) § Track: meq-carve-eval-tower-verification on 2026-11-03 (BRF-T1-MEQ, operator D2): "Add server config for ThinkPRM in orchestrator_stack.py too-big: shared-runtime …".*
- [x] Implement verification pass in `eval_tower.py` `eval_t2()`: ✅ 2026-10-30 — orchestrator `de6c56e34f5f23c2155d2b7dc839554ae692f771`; opt-in postpass selects actual scored/core finite-confidence rows with deterministic uncertainty ties, sends problem/answer to native ThinkPRM CoT verification, extracts explicit per-step verdicts and the conditional score from both observed Yes/No logprobs (missing support is unknown), and stores feedback in per-question details plus fsynced attribution JSONL and aggregate coverage. [no-belief: structural software implementation; no quality or calibration claim]
  - After standard scoring, identify N most uncertain questions (lowest |confidence - 0.5|)
  - For each uncertain question: send to ThinkPRM with verification CoT prompt
  - Extract step-level verdicts and P("yes")/(P("yes")+P("no")) score
  - Store per-step attribution in `QuestionResult.details`
- [x] Cross-family verification: enforce that ThinkPRM model family differs from evaluated models ✅ 2026-10-30 — orchestrator `de6c56e34f5f23c2155d2b7dc839554ae692f771` classifies ThinkPRM as Qwen and rejects Qwen or unknown generators before verifier loading. [no-belief: fail-closed software guard] Evidence: APP `de6c56e34f5f23c2155d2b7dc839554ae692f771`; `tests/unit/test_eval_verifier_mode.py` and `tests/unit/test_process_verification.py`. [historical hygiene: implemented 2026-10-30; zero new quota]

**Source qualification (2026-10-30):** The merged 11-file implementation passed 392 deduplicated tests (96 focused, 236 compatibility, 102 RTE with 42 overlaps), schema, scoped Ruff and normal hooks. Receipt: `/mnt/raid0/llm/tmp/codex-ni-app-source-lane-20261030/t2/T2-PUBLISHED.json`. Private native N1 qualification took 33.51 s; postwork returned 75 and resume/completed reentry returned 0 without a completed-output rewrite. This operational Gemma control uses confidence 0.5 and is not representative quality evidence or an independent resume N2. Its private source binding is preserved; merged-source tests do not retroactively rebind the native run. The server-config leaf stays open: private generation-drained ownership does not implement automatic shared-main-model unloading. No full 500-question T2, adoption or calibration gain is claimed. Prospective belief write/read/canary wiring remains `VB-EV5-PROCESS-ATTRIBUTION-WIRE`.

**EV-5 owned T2 lifecycle source integration (2026-10-30):** epyc-orchestrator main `fb9ada636c6b74d3afc98576fdaf68aa9076037c` (from `0c8f70d6`) adds the ThinkPRM config and opt-in owner-bound T2 lifecycle, default OFF. The lifecycle drains the captured generator child by PIDFD before ThinkPRM and has a whole-evaluation finalizer covering pool/admission and artifact/error paths. Seventy-one focused tests passed. The actual `eval_t2` code path ran with an isolated CONTROL fixture and real native ThinkPRM; a separate post-work rc75/partial cutoff control drained both generator and verifier. The native metadata is `control_only=true` and `quality_evaluated=false`, so this is not an original 500-row cohort result or shared-production main-model-unload acceptance. The authoritative `FINAL-GATE-REPORT.json` at `/mnt/raid0/llm/tmp/codex-ni-next-cpu-prep-20261030/` records full `make gates` rc0 on the clean APP lane using pinned private tools and source/tool hashes. In the shared `/workspace` APP clone, `make gates` fails only at `shfmt-check` on the ignored pre-existing untracked `scripts/server/_step1_obs_sampler.sh`; `make lint` passes there. Leave that file untouched. Keep the server-config leaf unchecked while shared-runtime acceptance remains open. [belief: cc]

**Files**: `eval_tower.py` L324-355 (eval_t2), `orchestrator_stack.py`, new verification module

### EV-6: Cross-family verification constraint — ✅ 2026-04-15

- [x] Added `VERIFICATION_FAMILIES` dict and `check_cross_family()` function to `eval_tower.py`
- [x] Supports Qwen, Llama, DeepSeek, Ouro, Mistral, Gemma families
- [x] Returns True (safe) if families differ or either is unknown (permissive default)
- [x] Runtime guard for EV-5 (ThinkPRM) and EV-7 (AP-27 RLVR)

**Files modified**: `eval_tower.py` (module-level VERIFICATION_FAMILIES + check_cross_family)

### EV-7: AP-27 RLVR integration (depends on EV-1–4 + Ouro P7)

> **2026-11-10 deprecation:** Ouro P7 is deprecated (operator decision 2026-11-10: all tasks for the Ouro-1.4B and Nanbeige4.2 models are deprecated; their GGUFs are not on disk and will not be downloaded); no Ouro sentinel or verifier will be integrated, and every "Ouro P7" dependency below is withdrawn. [no-belief: deprecated by operator]

- [x] Formalize T0/T1/T2 as RLVR verification functions with deterministic reward signals. ✅ 2026-07-11 — `epyc-orchestrator` commit `7ee919d8` adds the pure `src/autopilot_core/rlvr_tiers.py` contract and shared exports.
- [x] Design reward signal per tier: T0 = binary, T1 = calibrated continuous, T2 = process-attributed. ✅ 2026-07-11 — no promotion authority changed; the contract returns observe-only rewards and blockers.
- *Moved to [`model-evaluation-queue.md`](model-evaluation-queue.md) § Track: meq-carve-eval-tower-verification on 2026-11-03 (BRF-T1-MEQ, operator D2): "Integrate Ouro-2.6B as T0 sentinel verification candidate …".*
- [x] Export eval environments for actual RL model training when DGX Spark available. ✅ 2026-07-11 — `epyc-orchestrator` adds `scripts/autopilot/export_rlvr_environment.py`, an offline prompt-free exporter from EvalResult/journal artifacts to `ap27_rlvr_environment_row.v1` JSONL with tier reward metadata, blockers, suite counts, safe per-question outcomes, and optional fail-on-blockers behavior. No inference run or live gate wiring required.
- [x] Track three metrics (quality + ECE + AUC) as the minimal signal for RLVR reward design. ✅ 2026-07-11 — existing `EvalResult` quality/ECE/AUROC fields are now consumed by the RLVR reward contract; degenerate/missing ECE/AUROC remain explicit blockers.
- [x] Surface the RLVR reward view in report-only `METRIC rlvr_*` lines. ✅ 2026-07-11 — `epyc-orchestrator` wires `rlvr_reward_from_result()` into `EvalResult.to_grep_lines()` only; objectives, SafetyGate verdicts, Pareto archive state, and journal schema remain unchanged.
- [x] Wire the RLVR reward view into `eval_details`/journal payloads after reviewing the HIGH GitNexus blast radius for `EvalTower._aggregate`; do not fold the reward into Pareto/safety authority without operator sign-off. ✅ 2026-07-11 — `epyc-orchestrator` commit `69445d43` avoids the high-risk aggregate path and instead adds the observe-only `eval_details["rlvr_reward"]` payload at the main-loop journal assembly point (`_run_loop_inner`, GitNexus LOW risk: 2 upstream dependants, 0 affected processes). Objectives, SafetyGate verdicts, Pareto archive state, and planner scoring remain unchanged.

**2026-07-14 quiet-window export evidence**: the offline exporter was run
against `epyc-orchestrator/orchestration/autopilot_journal_1.jsonl` and wrote
`epyc-orchestrator/orchestration/reports/ap27_rlvr_environment_20260714T172226Z_quietwindow.jsonl`
plus summary `...summary.json`. Result: `351` rows exported, `102` marked
`ready_for_training`, `249` blocked, `11` skipped as non-eval rows; blocker
counts are dominated by `auroc_missing_or_degenerate=249` with one
`question_results_missing`. Tier mix: `T0=102`, `T1=239`, `T2=6`, `T3=4`. This
is useful live-environment evidence for AP-27's offline bridge, but it does not
change the remaining gates: EV-4 still needs a real calibration baseline, and
Ouro P7 integration is still required before AP-27 can use a verifier model.

**Dependencies**: EV-1–4 provide the calibration infrastructure. Ouro P7 provides the sentinel model.

### EV-8: Diversity metrics (NEW 2026-04-22, DD4 / intake-441)

**Source**: `/workspace/research/deep-dives/diversity-collapse-posttraining.md` (402 lines + Tier 2b sweep 2026-04-22).

**⚠️ Load-bearing claim contested (Tier 2b, 2026-04-22)**: Verbalized Sampling (arXiv 2510.01171, Zhang et al. 2025) is a **training-free inference-time prompt** that recovers **66.8%** of the base-model diversity gap and delivers 1.6-2.1× diversity boost. This directly refutes intake-441's load-bearing claim ("inference-time interventions cannot recover training-time diversity loss"). Additional findings: self-BLEU ignores quality (ACL W19-2311); distinct-N/self-BLEU are surface-level and gameable (arXiv 2506.00514); OLMo-3 results not replicated on Qwen/Llama/MoE families.

**EV-8 AMENDED to two-tier warn/reject with recovery probe**:

**Target**: NIB2-42 in `non-inference-backlog.md`.

Tasks:
- [x] Add 4 fields to `EvalResult` at `safety_gate.py` (L44-100): `diversity_entropy`, `diversity_distinct2`, `diversity_self_bleu`, `diversity_ttr`. **DONE 2026-04-22 (NIB2-42)**: EvalResult landed in new `src/safety_gate.py`.
- [x] Add supplemental field `diversity_semantic_embedding_agreement` — pairwise cosine agreement across N completions on a sentence-embedder (anti-gaming against surface-level distinct-2). **DONE 2026-04-22**: accepts injected embedder; NaN fallback when absent.
- [x] Implement `diversity_metrics.py` scoring functions. **DONE 2026-04-22**: `src/tools/diversity/metrics.py` — entropy, distinct_n, self_bleu (cumulative BLEU-4 with brevity penalty), type_token_ratio, semantic_embedding_agreement, compute_all bundle.
- [x] Wire through `to_grep_lines()` for log parsing. ✅ 2026-07-11 — verified current `epyc-orchestrator` `EvalResult.to_grep_lines()` emits NaN-gated `METRIC diversity_*` lines for entropy, distinct-2, self-BLEU, TTR, and semantic embedding agreement when populated; `tests/unit/test_diversity_metrics.py` covers omission of NaN fields and emission of populated fields.
- [ ] One-day baseline pass: 4 production roles × 20 open-ended prompts × 4 completions (temperature 0.7 baseline + T=1.0 ladder point for recovery probe). **Inference-gated; baseline yaml schema ready (`orchestration/autopilot_baseline.yaml` diversity_baseline: + diversity_baseline_meta: blocks).** [check: what decision does the diversity baseline feed — a per-role temperature change, an RL-data filter, or nothing? Name the consumer and its threshold or retire]
- [x] **Amended SafetyGate policy** (originally "reject if distinct-2 drops >20% AND quality not up"): **DONE 2026-04-22 (NIB2-42)**: `SafetyGate` in `src/safety_gate.py`. Tier 1 WARN / Tier 2 REJECT (all 4 signals). Warn-only default via `SAFETY_GATE_WARN_ONLY` env var (default ON).
  - **Tier 1 WARN**: distinct-2 drops >20% AND quality not up → log warning, investigate.
  - **Tier 2 REJECT**: only when ALL of: (a) distinct-2 drops >20%, (b) semantic-embedding-agreement drops >10%, (c) quality not up, (d) **Verbalized Sampling probe fails to recover >50% of the gap**. Multi-signal reject prevents rejecting models that merely lack a calibrated sampling prompt.
  - Warn-only mode mandatory until Verbalized Sampling replication on Qwen3-30B-A3B produces baseline recovery data.
- [x] **Verbalized Sampling recovery probe**: implement distributional-prompt variant ("generate 5 diverse responses with probabilities...") as part of the diversity baseline. A model that recovers >50% via VS is NOT a candidate for rejection. **DONE 2026-04-22**: `src/tools/diversity/verbalized_sampling.py` with `VS_DISTRIBUTIONAL_PROMPT` template, `recovery_ratio()`, `format_vs_prompt()`, `parse_vs_completions()`. Never calls inference directly; caller injects completions.
- **[declined: ws58 2026-11-03 content-review: deferred with no trigger; the baseline pass (if kept) already includes the T=1.0 ladder point]** Deferred: temperature-ladder experiment (T=0.7/1.0/1.3); CoT-suppression ablation.

**Test coverage (2026-04-22)**: `tests/unit/test_safety_gate_diversity.py` — 14 tests all passing. Metric math, embedder mock, 3 verdict paths, Tier 2 REJECT all-four-signals requirement, VS recovery > 0.50 suppresses REJECT, warn-only converts REJECT → WARN, NaN-baseline falls through to PASS, VS parser tolerance.

Exit criterion: baseline file populated; warn-only rule live for 10 trials AND VS recovery probe integrated AND Qwen/Llama replication of OLMo-3 finding attempted; then flip warn → multi-signal reject.

**Reason for amended gate**: Verbalized Sampling evidence shows the "weights-only, inference-irrecoverable" framing was overstated. The amended multi-signal gate avoids false-negatives (rejecting checkpoints that just need better sampling prompts).

**EV-8 candidate inherited from qwen-scope-sae-toolkit closure (2026-06-12)**: the Qwen-Scope SAE **Section-4 eval-suite-redundancy probe** (feature-coverage AUC + inter-benchmark overlap as an evaluation-free redundancy proxy; Spearman 0.85 vs performance redundancy across 17 benchmarks) is an EV-8 candidate — prune known-redundant benchmarks before any further harness-suite expansion. Application recipe, storage map (~3.34 GB single-layer pull), and caveats are in the Research Intake Update § Qwen-Scope below and in the deep-dive `research/deep-dives/qwen-scope-sae-suite.md`; the source handoff is archived at [`../completed/qwen-scope-sae-toolkit.md`](../completed/qwen-scope-sae-toolkit.md).

### EV-9: Multi-dimensional rubric (NEW 2026-04-22, DD7 / intake-438)

**Source**: `/workspace/research/deep-dives/minddr-multi-agent-rl-specialization.md` (442 lines). Required dependency for `minddr-deep-research-mode.md` MD-7.

**Target**: Supports NIB2-45 MindDR Phase 1.

Tasks:
- [x] Extend `EvalResult` with rubric fields: `rubric_reasoning_trajectory`, `rubric_tool_calls`, `rubric_outline`, `rubric_content_stage`. **DONE 2026-06-27**: `src.safety_gate.EvalResult` already carried the MindDR rubric stubs; orchestrator `9db36fcb` adds the same NaN-safe fields to the live AutoPilot `scripts/autopilot/safety_gate.py::EvalResult`.
- [x] LLM-as-judge scoring functions per rubric dimension (deterministic fallback via regex+structure for T1 low-cost runs). **DONE 2026-06-27** in orchestrator `9db36fcb`, `ce6cdf75`, `07720457`, and `697ad506`: added pure `scripts/autopilot/rubric_scoring.py` with positive/negative criterion aggregation, MindDR process dimensions, DRACO content dimensions, saturation screening, multi-judge Bradley-Terry stability diagnostics, a JSON-only judge-prompt builder, and deterministic T1 fallback scores from expected-hint coverage, outline structure, citation/source markers, tool events, reasoning markers, plus EvalTower consumption for `deep_research_*` expected-hint items. EvalTower now treats those items as rubric-scoreable, persists per-question rubric scores, rolls up process-dimension means into `EvalResult`, and emits the existing `METRIC rubric_<dim>` lines. The local judge runner/parser is gated by `AUTOPILOT_RUBRIC_JUDGE_ROLES`, calls local cross-family judge roles through the existing background-priority EvalTower path, parses JSON/fenced JSON `scores`, and falls back deterministically if judges are unset or fail. Live judge-role selection and MD-9 A/B remain downstream evidence gates, not implementation blockers for EV-9 task 2.
- [x] Create `deep_research_sentinel` suite: 20-40 research-like queries with multi-dimensional ground truth. 10 BrowseComp-style + 10 WideSearch-style + 10 mixed. **DONE before 2026-06-27**: `orchestration/deep_research_sentinel.yaml` has 20 entries (`browsecomp=7`, `widesearch=7`, `mixed=6`) and the existing sentinel tests parse and classify them as research-like.
- [x] Wire rubric scoring into existing `to_grep_lines()` — one `METRIC rubric_<dim>: <score>` line per dimension. **DONE 2026-06-27** in orchestrator `9db36fcb`: populated rubric dimensions emit `METRIC rubric_<dim>: ...`; NaN/unavailable dimensions are omitted like EV-8 diversity metrics.

Exit criterion: `minddr-deep-research-mode.md` MD-9 A/B test can produce multi-dimensional scores.

## Dependency Graph

```
EV-1 (logprob_confidence field)       ──independent of inference──
EV-2 (ECE + AUC computation)          ──independent of inference (depends on EV-1 for data)──
EV-3 (Scoring Verifiers benchmarks)   ──independent (download + adapter)──
EV-6 (cross-family constraint)        ──independent (code only)──

EV-4 (calibration baseline)           ──needs inference stack + EV-1/2/3──
EV-5 (ThinkPRM-1.5B deployment)       ──needs model download + inference stack──

EV-7 (AP-27 RLVR integration)         ──depends on ALL above + Ouro P7──
```

## Cross-Cutting Concerns

### 1. AP-27 ↔ Eval Tower Verification
AP-27 in [autopilot-continuous-optimization.md](autopilot-program.md) is the parent work item. This handoff provides the implementation plan that AP-27 lacks. AP-27 becomes a pointer: "see eval-tower-verification.md EV-1–EV-7."

### 2. Ouro P7 ↔ T0 Sentinel
Ouro-2.6B-Thinking (research-eval P7) is a candidate T0 sentinel verifier. Its looped architecture achieves 90.85% MATH-500 at only 2.6B params. If Ouro's MATH-500 performance validates on our CPU, it becomes the cross-family verification model for T0 (it's ByteDance architecture, distinct from our Qwen/Llama stack).

### 3. Decision-Aware Routing ↔ Reward Signal
The [decision-aware-routing.md](routing-program.md) changes the Q-scorer reward signal. The eval tower verification framework must be able to assess whether the new reward signal is calibrated (ECE) and discriminative (AUC). DAR-2/3/4 changes should be validated through EV-4 calibration baselines.

### 4. Sequential Model Loading
ThinkPRM-1.5B at T2 requires loading a separate model. Per memory note (feedback_sequential_model_loading), models MUST load sequentially. T2 eval should: complete standard scoring → unload generation models → load ThinkPRM → run verification → unload ThinkPRM.

## Key Files

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `epyc-orchestrator/scripts/autopilot/safety_gate.py` | EvalResult + QuestionResult dataclasses | L38-52 (QuestionResult), L44-100 (EvalResult) |
| `epyc-orchestrator/scripts/autopilot/eval_tower.py` | Tiered eval T0→T1→T2, aggregation | L100-165 (_eval_question), L169-251 (_aggregate), L324-355 (eval_t2) |
| `epyc-orchestrator/scripts/autopilot/dataset_adapters.py` | Benchmark dataset loading | Adapter pattern for new suites |
| `epyc-orchestrator/scripts/autopilot/suites.py` | Suite registration | Suite definitions |
| `llama.cpp/tools/server/server-common.cpp` | Logprob extraction | L1755 (get_token_probabilities) |
| `epyc-orchestrator/scripts/server/orchestrator_stack.py` | Server management | DOCKER_SERVICES, model loading |

## Known Issues

- ThinkPRM-1.5B may not have a GGUF quantization available — may need to convert from HuggingFace weights via `llama.cpp/convert_hf_to_gguf.py`
- ECE computation requires well-distributed confidence scores. If the model is systematically over- or under-confident, ECE will be high but uninformative about verification quality. Need reliability diagrams for visual inspection.
- The Scoring Verifiers benchmarks are code-specific (HumanEval, MBPP). For non-code evaluation tasks, we need to generate our own quality-stratified solutions using the quantile selection methodology.
- Cross-family verification adds model loading overhead. At T2 (30min budget) this is acceptable. At T1 (5min), loading a separate verification model may consume too much of the time budget.

## Research Intake Update — 2026-04-15

### New Related Research
- **[intake-377] "Math-Verify"** (github:huggingface/Math-Verify)
  - Relevance: Directly applicable to T0/T1 deterministic scoring. Current `score_answer_deterministic()` uses binary exact-match — Math-Verify provides robust mathematical expression comparison with LaTeX parsing, set theory support, symbolic simplification, and matrix equivalence. Addresses underestimation of model performance by up to 40 points through superior parsing.
  - Key technique: Three-step grading — answer extraction (regex by priority), ANTLR4-based parsing to SymPy, multi-strategy comparison (string, symbolic, numeric precision)
  - Reported results: Highest accuracy (0.1328) vs lm-eval-harness (0.0802) and Qwen evaluator (0.1288) on MATH dataset
  - Delta from current approach: Our binary exact-match misses equivalent expressions. Math-Verify is Apache-2.0 Python, integrates directly into eval_tower.py scoring pipeline. Dependency: ANTLR4 runtime.
  - **Integration caveats (from deep dive)**:
    - `verify(gold, pred)` is NOT symmetric — gold must be first argument
    - NOT thread-safe (uses `signal.alarm()`) — if `_eval_question()` uses threading, must use multiprocessing or set `timeout_seconds=None` with external timeout
    - Open interval `(1,2)` converts to `Tuple(1,2)` — could false-positive for coordinate pairs
    - Accuracy impact: 0.1328 vs 0.0802 means current exact-match underestimates model capability by ~66% on math questions — affects routing decisions
  - **Deep dive**: `research/deep-dives/math-verify-integration-analysis.md`

- **[intake-379] "Let's Verify Math Questions Step by Step" (MathQ-Verify)** (arxiv:2505.13903)
  - Relevance: Complementary to answer verification — addresses question quality. ValiMath benchmark (2,147 annotated questions) and MathQ-Verify pipeline parse questions into atomic assumptions/conclusions for consistency checks. +25pp F1 over direct verification baselines.
  - Key technique: Five-stage pipeline: InstValid → Clean → AtomValidAll → Consistent → Complete. Decision is AND of all stages.
  - Delta from current approach: We verify answers but not question validity. Flawed questions waste eval budget and produce misleading results. Could improve T1/T2 dataset curation.
  - **Ablation insight**: Stage 5 (completeness) actually hurts F1 by +0.57pp — introduces false positives. Deploy stages 1-4 only.
  - **Hidden gem**: Referenced paper arxiv:2504.06514 shows missing premises cause models to generate MORE reasoning tokens — filtering flawed questions also reduces inference cost.

## Research Intake Update — 2026-04-15 (Session 6)

### New Benchmark Suites Integrated

- **AA-Omniscience** (`omniscience` suite) — 600 factual questions across 6 domains (Finance, Health, Humanities, Law, Science/Engineering, Software Engineering). Tests knowledge reliability and hallucination detection. Wired into general/frontdoor/architect roles. F1 scoring with `<answer>` extraction. Abstention patterns stored for future ternary scorer. `AAOmniscienceAdapter` in `epyc-inference-research/scripts/benchmark/dataset_adapters.py`.

- **AA-LCR** (`aa_lcr` suite) — 100 long-context multi-document reasoning questions (~100K tokens each). Requires one-time `download_aa_lcr.py` to fetch 173 source PDFs via pdf_router OCR pipeline. Wired into architect/ingest/long_context roles. `AALCRAdapter` reads from cached JSONL at `/mnt/raid0/llm/data/eval/aa_lcr/aa_lcr.jsonl`.

- **Relevance to EV-4**: AA-Omniscience provides ground-truth calibration data for ECE/AUC measurements. Run omniscience suite through eval tower to measure hallucination-specific calibration alongside existing quality suites.

## Research Intake Update — 2026-04-30

### New Related Research

- **[intake-516] "HALO-Gemini-3-Flash-AppWorld — Gemini-3-Flash agent traces on AppWorld test-normal in HALO span schema"** (HF dataset `inference-net/HALO-Gemini-3-Flash-AppWorld`, MIT)
  - Relevance to eval tower: AppWorld is a deterministic long-horizon multi-app tool-use simulator with verifiable success metrics (SGC = Sub-Goal Completion). The dataset releases 168 traces / 3,438 spans of Gemini 3 Flash on test-normal split as a public commercial-teacher baseline. Relevant to EV-4/5/7 if the eval tower extends to agent benchmarks beyond AA-Omniscience.
  - Two concrete uses: (a) **commercial-baseline benchmark** — run our local stack (Hermes + Qwen3.6 worker + 30B-A3B coder) on the same AppWorld split for apples-to-apples SGC comparison against published Gemini 3 Flash numbers (37.5% test_normal SGC vanilla / 48.2% with HALO trace-loop optimization); (b) **eval-as-corpus** — span-tree format may be a useful logging target if we standardize agent trace observability across the orchestrator (cross-ref `../completed/meta-harness-optimization.md` 2026-04-30 update).
  - Constraint: the 168-trace dataset alone is small — value is access to AppWorld as the eval substrate, not the trace count. Pair with the AppWorld benchmark proper at appworld.dev before acting.
  - Verdict: `worth_investigating`. Action: when EV-4/5/7 advance and agent-eval scope is on the table, scope AppWorld setup cost on EPYC.

#### Deep-dive refinement (2026-04-30) — AppWorld DEFER, dev/test_normal split adopted

Deep-dive at [`/workspace/research/deep-dives/halo-rlm-trace-loop-integration.md`](../../research/deep-dives/halo-rlm-trace-loop-integration.md).

**AppWorld dataset**: defer (and skip the 168-trace dataset). Same rationale as `agent-world-env-synthesis.md` 2026-04-30 deep-dive refinement — feasible hardware, no current eval gap demanding 3–5 days integration. Revisit only when EV-4/5/7 explicitly demand a long-horizon multi-tool external benchmark.

**dev/test_normal split discipline (worth adopting in eval tower regardless)**: AppWorld's convention separates a held-out test_normal split from dev. The pattern is generic and transferable to our existing eval suites (AA-Omniscience, KO-Bench, MathBench): every harness or model candidate must show improvement on BOTH splits before promotion. This guards against the autopilot frontier accidentally selecting harnesses that overfit dev. Will be lifted into the `halo-trace-loop-spike.md` HALO-4 work; reference here so EV-4/5/7 can plan to honor the convention.

## Research Intake Update — 2026-05-04

### Qwen-Scope feature-coverage redundancy as evaluation-free pruning signal

- **[intake-521] "Qwen-Scope: Turning Sparse Features into Development Tools for LLMs"** (Qwen Team, 2026-04-30) — deep-dive at `research/deep-dives/qwen-scope-sae-suite.md`.
  - Direct relevance: Section 4 of the report defines an **evaluation-free benchmark redundancy / inter-benchmark similarity framework** built on SAE feature footprints. The paper reports Spearman 0.85 correlation between feature-redundancy R-hat(D) and performance-redundancy R(D) across 17 benchmarks (MMLU, MMLU-Redux, MMLU-Pro, GSM8K, MATH, GPQA-D, TheoremQA, MBPP, EvalPlus, MultiPL-E, KOR-Bench, ICLEval, C-Eval, CMMLU, SuperGPQA, MMMLU, INCLUDE) using 26 in-house Qwen pre-training checkpoints. After partialling out MMLU as a general-ability confound, inter-benchmark feature-overlap correlates with performance-rank similarity at Pearson 75.5%.
  - Concrete implication for EV-4/5/7: **the canonical EPYC eval suite (AA-Omniscience, KO-Bench, MathBench, harness candidates) can be analyzed for redundancy and inter-benchmark similarity using ONE SAE pull (~5 GB), without running any new model evaluations.** That gives a representation-level signal complementary to the dev/test_normal split discipline noted at the tail of this handoff: dev/test_normal guards against harness overfit; SAE feature-coverage guards against benchmark overlap (e.g., is GSM8K's contribution to the suite already subsumed by MATH? Section 4 example: 63% of GSM8K's features ARE covered by MATH, while only 10% the other way).
  - Reported asymmetric overlap signature (paper Section 4.3, Figure 6): code benchmarks (EvalPlus, MBPP, MultiPL-E) form a tight cluster; broad knowledge benchmarks (MMLU-Pro, SuperGPQA) subsume specialized ones like TheoremQA at 0.56-0.68 coverage. Useful template for what our EPYC suite should look like once analyzed.
  - **Application path** (recommended pull, lowest cost):
    1. Pull SAE-Res-Qwen3.5-27B-W80K-L0_50 single layer in the middle band (e.g., layer 30 of 64) — ~3.34 GB. Storage estimate detailed in the `../completed/qwen-scope-sae-toolkit.md` storage map (archived 2026-06-12).
    2. Encode the residual stream at that layer for every prompt in (a) AA-Omniscience, (b) KO-Bench, (c) MathBench, (d) any harness candidate in EV-4/5/7 evaluation campaigns.
    3. Compute per-benchmark feature-coverage curve c_n and feature-redundancy R-hat(D) per Section 4.2 equations 7-9.
    4. Compute pairwise asymmetric overlap (eq. 10) and min-normalized symmetric overlap (eq. 11) across benchmark pairs.
    5. Cross-validate redundancy ranking against actual model-ranking-preservation on a held-out 5-checkpoint panel (cheap — many Qwen quants on disk).
    6. Propose pruned eval suite that preserves discriminative power for iterative dev cycles.
  - **Caveats** (deep-dive 2026-05-04):
    - The "evaluation-free" claim is **in-distribution to Qwen pretraining**: the SAEs were trained on Qwen pretraining data (paper Section 2.2: "in-house pretraining data"; not disclosed further). MMLU/GSM8K/etc. are likely well-represented in that corpus, so feature-coverage saturation is being computed by SAEs that have effectively seen the benchmarks. This is fine for EPYC's purposes since we use Qwen models, but the framing must not be over-extended to non-Qwen evaluator panels.
    - License is `qwen` custom (NOT Apache 2.0). Section 4 post-hoc analysis is unambiguously permitted under the paper's Section 9.3; the storage cost is the only meaningful gate for EV-4/5/7 scope.
    - Wang et al. 2026 (ICLR 2026, OpenReview Q4ooLNOFeR) on Qwen-2.5-3B + Gemma-2 reports SAE interpretability ≠ steering utility, but Section 4 is **redundancy / similarity over feature footprints**, not steering — Wang 2026's finding does not directly apply. AxBench (Wu et al. ICML 2025) is also off-target since it benchmarks steering and concept detection, not benchmark redundancy.
  - **Cross-cutting concern**: this is potentially the strongest single application of Qwen-Scope for EPYC and is gated only on "decide to do it." Recommend slotting as an EV-8 candidate ahead of any further harness-suite expansion — pruning known-redundant benchmarks before adding new ones is the right ordering.
  - **Action**: do NOT block EV-3 / EV-4 on this. After EV-3 (Scoring Verifiers) lands, evaluate EV-8 against the SAE redundancy analysis as a parallel track; require a clear pruning recommendation backed by held-out checkpoint cross-validation before any benchmark is removed from the canonical suite.

## Research Intake Update — 2026-05-27 (skill-efficacy cluster: SkillsBench + CoEvoSkills)

Source: `/research-intake` of the text-space skill-optimizer cluster (intake-626 SkillOpt → cohort 627–631). Two of those entries land squarely on eval-tower territory: how to score whether a *skill / agent-file / prompt* actually helps, and how to gate edits when ground truth cannot be exposed.

### New Related Research
- **[intake-096] "SkillsBench"** (arxiv:2602.12670, Li et al.) — first standardized benchmark of whether agent skills help. 86 tasks (84 evaluated) / 11 domains, each paired with a curated Skill and a **deterministic verifier** (binary reward over 5 trials; agents never see the verifier — post-solution execution, leak-resistant). **Methodology already adopted 2026-03-03** ([completed/07-skillsbench-eval-suite.md](../completed/07-skillsbench-eval-suite.md)): our `skill_transfer.yaml` suite + `analyze_skill_transfer.py` (skill×domain matrix) + `skill_transfer_regression.py` (model-swap per-skill regression flagging). The v3 deep-dive (2026-05-27) adds the findings below.
  - **Two decision-relevant findings**: (1) **self-generated skills are net-NEGATIVE on average (−1.3pp vs no-skill)** — "models cannot reliably author the procedural knowledge they benefit from consuming"; (2) **curated skills can REGRESS** specific tasks (16/84 negative, e.g. −39.3pp) via conflicting guidance / unnecessary complexity, even though the average is +16.2pp.
  - **Caveat (bounds reuse)**: all 3 harnesses (Claude Code / Gemini CLI / Codex CLI) and all 7 models are proprietary commercial-API; **no open-weight support**. The *methodology and findings* transfer to our stack; the *suite* does not run as-is on our CPU-served llama.cpp harness. Also a stated context-length confound (gains may partly be "more context," not procedural structure).
- **[intake-628] "CoEvoSkills"** (arxiv:2604.01687, Philip S. Yu et al.) — **Surrogate Verifier** that, seeing only the task instruction + the agent's output files, generates its OWN deterministic assertion suite and returns proxy reward = fraction passing; the ground-truth oracle returns only an **opaque pass/fail bit** (no content) to stop the generator overfitting to held-out tests. **Ablation-proven load-bearing: −30pp without it** (71.1% → 41.1%). Author-acknowledged failure mode: the surrogate cannot match the oracle's exact precision (flagged a 0.00002-day discrepancy as failure when the agent was actually *more* accurate) and cannot separate its own error from the agent's — the oracle stays the authoritative arbiter (K=5 oracle interventions, M=15 surrogate retries).

### EV-10 (NEW 2026-05-27) — Skill/Prompt Efficacy Gate + leak-free surrogate scoring

Two complementary, mostly inference-free pieces. **Tracked in [research-evaluation-index.md](research-evaluation-index.md) P8.**

- [ ] **EV-10a — Paired skill-vs-no-skill efficacy check** (adopt SkillsBench methodology). For any candidate skill / agent-file / prompt mutation, eval-tower should report the *paired* delta (with-artifact minus without-artifact) on the relevant suite, **per-suite, with an explicit negative-delta guard**: a mutation that improves the aggregate but regresses a specific suite (the SkillsBench 16/84 pattern) must surface, not hide. **Do NOT rebuild the regressor** — `skill_transfer_regression.py` (from completed/07-skillsbench-eval-suite.md, 2026-03-03) already flags per-skill cells dropping >threshold across a before/after checkpoint pair; EV-10a is the *wiring* of that detector (and the paired no-artifact arm) into the autopilot mutation accept path (cross-ref `../completed/meta-harness-optimization.md` 2026-05-27 SkillOpt section), plus honoring the **dev/test_normal split discipline** (2026-04-30 AppWorld update) — require improvement on BOTH splits. Net-new work is the no-artifact baseline arm + accept-path hook, not the regression math. **DECISION LOGIC LANDED 2026-05-27** — `epyc-orchestrator/scripts/autopilot/skill_efficacy.py` `evaluate_skill_efficacy()` (per-suite delta + negative-delta guard + strict aggregate-gain) and `evaluate_skill_efficacy_split()` (dev/test both-arms discipline); 19 tests in `tests/unit/test_skill_efficacy.py` pass. **DEFAULT-OFF LIVE-BRANCH WIRING LANDED 2026-06-13** — `epyc-orchestrator` `924ca50` wires `AUTOPILOT_SKILL_EFFICACY_GATE` into prompt/GEPA/code mutation handlers: pre-mutation no-artifact eval arm, post-mutation per-suite compare, `eval_result.details["skill_efficacy"]`, and revert before epoch acceptance on reject. Remaining: deploy/restart and paired-mutation A/B validation; keep flag isolated from `AUTOPILOT_BSV2_ACCEPT_GATE`.

  **Granularity caveat (EV-10f):** `evaluate_skill_efficacy` compares suite aggregates. Its negative-delta guard flags suite regression, but cannot expose task regressions hidden by a rising suite mean. The interface has no per-task outcome comparison; WikiSkill does not close that gap.

- [ ] **EV-10b — Surrogate-verifier scoring for leak-constrained tasks** (adopt CoEvoSkills pattern). Where a task has no exposable ground truth, score via a self-authored assertion suite from an **independent, cross-family verifier session** (reuse EV-6 `check_cross_family()`), returning only an opaque correctness bit to the artifact-author path. This is the eval-side complement to EV-5 (ThinkPRM process verification) and EV-7 (RLVR reward). **Guard**: keep a ground-truth oracle as authoritative arbiter where one exists (per the CoEvoSkills precision failure mode); the surrogate is for dense feedback, not final scoring. **SCAFFOLD LANDED 2026-05-27** — `skill_efficacy.py` `surrogate_proxy_reward()` (fraction of self-authored assertions passing), `surrogate_feedback()` (dense vs **opaque-oracle-bit anti-overfit** decision), `require_cross_family()` (injected `check_cross_family` so the sidecar doesn't import the in-flight `eval_tower.py`). **READ-ONLY REPORT CONSUMER LANDED 2026-07-11** — `epyc-orchestrator` commit `fd709e4a` makes `eval_task_coverage_report.py` summarize journaled `eval_details.details.surrogate_feedback` / `eval_details.surrogate_feedback` rows (accepted, dense-feedback, opaque-only oracle conflicts, average proxy reward) and render them in Markdown without touching accept gates. Remaining: inference-gated verifier-session assertion authoring / producer wiring; caller still injects outcomes per the `verbalized_sampling.py` convention.
  - [x] EV-10b read-only report consumer for journaled surrogate feedback. ✅ 2026-07-11
- [x] **EV-10d — Diff outcome-grounded rerun reward against local admission semantics.** ✅ 2026-10-06 MAIN accepted [the source comparison](../../docs/reference/ni08-admission-and-skill-granularity.md#ev-10d-scalar-proposal-reward-versus-measured-result-admission): full-batch delta/zero-invalid candidate rewards versus separate keep/retry/revert and tier-local frontier decisions. Retry exceptions and cross-batch-memory scope are explicit; no universal bias-correction or efficacy claim. `intake-1323#record`.
- [x] **EV-10e — Report CPM (completions per million tokens) and quality-per-dollar beside quality** in whatever gate reports a scored task set (intake-1333#03, gate half; the doc half lands in `docs/chapters/08-cost-aware-rewards.md`). Reporting change, not a measurement campaign — two derived columns over numbers the gate already holds. Zero compute. ✅ 2026-10-31 — Research `51aef79c6529f6362db0df632754bf37e7a0a3b9`; `scripts/benchmark/test_task_economics_runner.py`, 46 actual-lane focused tests; [ev10e-task-economics-20261031 source controls](../../artifacts/compute/ev10e-task-economics-20261031/SOURCE-CONTROLS.json). [no-belief: source implementation and synthetic controls; no inference measurement]
  - Versioned `v7_quality_gate_economics_runner.py` persists native per-draw usage/cost and reports CPM plus quality-per-dollar beside official quality. Missing or zero denominators remain unknown; actual completions are separate from attempted draws, and failed/resumed spend stays aligned with the scored population. Frozen v7 bytes and scoring are unchanged. CLI output is exclusive/write-once after belief finalization; invalid resume preserves evidence and fails closed; status is append-only JSONL. Existing accuracy-hook success/refusal and attestation identity pass. Prospective economics projection is separately tracked by `VB-V7-TASK-ECONOMICS-WRITE`; no wired-loop or new grading claim.

- [x] **EV-10f — State the SUITE granularity of `evaluate_skill_efficacy` beside EV-10a.** ✅ 2026-10-06 MAIN verified the actual suite-keyed API and inserted its task-granularity limitation. [Source note](../../docs/reference/ni08-admission-and-skill-granularity.md#ev-10f-suite-aggregates-cannot-identify-hidden-task-regressions); WikiSkill supplies no task comparison. No inferred task-regression counts.
  - Pointer for the per-task-granularity gap: *"Third independent replication of the skills-regression prior (intake-096, intake-1142); see `intake-1321#record`. Unverified — cite intake-096/1142 for the effect, never this entry."*
- **Cross-ref (2026-09-07)**: the executor half of the asymmetric-access rule is `AP-54` in [`autopilot-continuous-optimization.md`](autopilot-program.md) — does the agent under evaluation read our compiled wiki during the same rollouts that feed the mutation proposer? Answered zero-compute first; only an ambiguous answer becomes a compute-gated A/B. `intake-1317#02`.
- **Cross-cutting**: EV-10a is the empirical instrument that makes the `../completed/meta-harness-optimization.md` SkillOpt recommendation auditable — without paired, per-suite, negative-delta-guarded efficacy measurement, the autopilot cannot distinguish a genuinely-helpful skill edit from a SkillsBench-style net-negative self-generation. **Priority MEDIUM**, mostly code (no new model for 10a; 10b reuses cross-family infra). Do NOT block EV-3/4/5 on this. **Inference-gated validation is tracked in [bulk-inference-campaign.md](eval-tower-program.md#track-bulk-inference-campaign) Package K as K-SKILL-1** (remaining stage: deploy/restart + paired-mutation A/B; post-AR-3/AR-4 class).


#### EV-10a corroboration — the regression prior is now REPLICATED (2026-08-15, intake-1142)

The SkillsBench "curated skills help on average while a sixth of tasks regress" finding that EV-10a's
negative-delta guard exists to catch has been **independently reproduced on a second benchmark
generation and a different model family**, using a third party's own raw data. A Stage-2b dive
downloaded all four MEGA release bundles (~557 MB), parsed 1,719 per-trial records and 1,604 agent
transcripts, and recomputed per-task deltas against the no-curation control:

| arm vs no-curation control (n=85 shared tasks) | mean lift | tasks regressing |
|---|---|---|
| SkillNet | +10.69pp | 13 (15.3%) |
| AgentSkillOS | +10.02pp | 17 (20.0%) |
| MEGA (Wisdom Graph) | +15.52pp | 12 (14.1%) |

On the clean 78-task subset (all four arms, no infrastructure failure anywhere): **MEGA +16.92pp with
12/78 = 15.4% regressing**, against our standing SkillsBench prior of +16.2pp with 16/84 = 19.0%.
Close to exact on lift, directionally identical on regression.

**Stronger than a replication**: the regressing set is partly **method-invariant** — five tasks
(`crystallographic-wyckoff-position-analysis`, `financial-modeling-qa`, `python-scala-translation`,
`travel-planning`, `video-tutorial-indexer`) regress under **all three** independent curation methods,
and three more under both baselines. That makes it a property of the TASKS, not of any one retriever.
Note the ceiling too: even the winning arm passes 46.5%, so curation moves about one task in six and
breaks about one in seven.

**Consequence for this handoff — evidence only, NO new task.** EV-10a's per-suite negative-delta guard
is confirmed load-bearing by a source with every incentive not to find it (the vendor never reports
this cut). This raises the priority of EV-10a's remaining validation stage, tracked as K-SKILL-1 in
[`bulk-inference-campaign.md`](eval-tower-program.md#track-bulk-inference-campaign) Package K. Cite `intake-1142#record`.

### EV-11/12/13 (NEW 2026-07-14) — backlog ROI audit waypoints

Formalized from the 2026-07-14 backlog ROI audit ([backlog-roi-audit-2026-07-14.md](backlog-roi-audit-2026-07-14.md) §A):

- [x] **EV-11 — math_verify scoring flip** ✅ 2026-07-17 (Wave-2 B1): GSM8K+MATH-500 adapter → `scoring_method=math_verify` (GSM8K prompt `<answer>`→`\boxed{}` for extraction); eval_tower HARD-FAILS on missing math-verify (no silent exact_match fallback; the 0/1,819-question no-op is fixed). math-verify 0.9.0 installed. 113 eval_tower tests green.
  - [x] **EV-11a — companion fix** ✅ 2026-07-20: `debug_scorer._score_math_verify` no longer regex-extracts `\boxed{...}` before math-verify. It passes the raw answer to native `math_verify.parse()`, preventing non-greedy truncation of nested boxed LaTeX such as `\boxed{\frac{1}{2}}`. Validation: `tests/unit/test_eval_verifier_mode.py::test_score_math_rebaseline_handles_nested_boxed_latex` plus focused EV-11 scorer suites (`31 passed`).
  - [x] **EV-11b — ECE binning decision + implementation** ✅ 2026-07-20: eval_tower `_aggregate` now uses `stat_tests.expected_calibration_error` (closed top bin) instead of the old inline open-top-bin loop, with an era-labeled details stamp. Behavior CHANGE → operator-decided and era-labeled; bundle fresh historical comparison with EV-11c, never mix pre/post numbers.
    - **DECIDED + IMPLEMENTED 2026-07-20 (operator + loop agent)**: adopted the recommendation below; implementation landed in `_aggregate` with focused tests. Recorded in [eval-tower-architecture-audit-2026-07-20.md](eval-tower-program.md#track-eval-tower-architecture-audit-2026-07-20) decision log.
    - **Decision package prepared 2026-07-20**: recommend adopting the consolidated `src.llm_primitives.stat_tests.expected_calibration_error` definition for `_aggregate` when EV-11c runs, with an era-labeled metric shift. Rationale: exact `confidence==1.0` failures are currently dropped from all bins, so a 10-row math-like cohort with 7 correct / 3 wrong at confidence 1.0 reports old inline ECE `0.000000` vs canonical ECE `0.300000`; an all-wrong confidence-1.0 cohort reports `0.000000` vs `1.000000`. Values below 1.0 are unchanged (`0.95`/`0.90` top-bin controls match).
  - [ ] **EV-11c — fresh math re-baseline (INFERENCE → batch manifest)**: gated on EV-11a fix + EV-11b decision; production temp+seed42; record dataset_sha256+test_profile per arm; era-label supersede (never edit historical). Pre-decided forks in the Wave-3 manifest entry EV-11-math-rebaseline. Absorbs the screen_paired_arms residual: promoting its McNemar p from observation-grade to decision-gating rides on this re-baseline (codified recipe), never on a side edit of eval_tower.py. EV-11b closed-bin binning is implemented (Cluster E note), so the gate is only EV-11a.
- [x] **EV-12 — execution-free patch verifier as gating signal** ✅ 2026-07-17 (module landed `epyc-orchestrator/src/verification/patch_verifier.py`: `verify_patch(patch, base) -> VerdictResult`; git-apply-check/hunk-context/AST-compile/import-sanity/ruff — none execute patched code; `to_report()` validates live against verification_report.schema.json; `.to_check()` = the eval-tower hook signal for Wave-2 B1; 30 tests. Remaining: B1 wires the eval_tower hook + coder_escalation pre-gate A/B (inference).)
- [ ] **EV-13 — review-finding-F1 suite** (M; intake-658, audit RE-3, formalizes the EV-NEW prose below): local code-review benchmark per the Factory-methodology deep-dive (Augment v1 145-bug golden set, ~80-LOC scorer, local models via /v1/chat/completions, ≤2pp judge-swap as first concrete EV-6 cross-family instance); feeds coder-pool composition + Strand Phase C.
  - [x] **EV-13a — build leg** ✅ 2026-07-17: NEW `epyc-inference-research/scripts/benchmark/review_f1/` (clean-room micro-avg P/R/F1 scorer w/ low-severity-neither rule + Mean-F1/StdDev ≥3-run protocol; /v1 harness w/ per-PR atomic incremental persistence + resume, model/quant indexing, judge-swap plumbing, mock/--dry-run transports; assemble_golden_set.py + checksum) + 22 self-contained tests. No inference, no unlicensed vendoring; run-leg CLI documented in review_f1/README.md.
  - [ ] **EV-13b — run leg (INFERENCE → batch-manifest entry)**: source Augment-v1 145-bug set (github.com/ai-code-review-evaluations/golden_comments; raw items lack structured criterion/location → semantic-matcher rides the run leg) + 5 PR diffs; assemble golden_set.json; run the documented harness CLI over local models (≥3 runs) + EV-6 ≤2pp cross-family judge-swap; index by model/quant.
    - **Sourcing 2026-09-16 (sub-gpu-prep; run still open):** research `e70b6974` on `sub/gpu-prep-20260916`.
      **Upstream has NO licence** (`license: null`), so no data is committed: `scripts/benchmark/review_f1/fetch_augment_v1.py`
      fetches into git-ignored `data/external/review_f1/augment_v1/`, pinned by `data/review_f1/augment_v1_manifest.json`
      (upstream `3f2c8ab794b4`, 50 PR head/base SHAs + diff sha256). **Actual set = 137 bugs (97 scored) / 50 PRs,
      not 145 / 5.** Goldens carry no file/line; 114/137 name an identifier in their diff. Matcher spec (judge ≠ reader,
      swap leg, controls ≥95%): `data/review_f1/SEMANTIC_MATCHER_SPEC.md`; `harness.py` judge_config gains
      `judge_distinct_from_reader`/`cross_family_ok`. Qwen-on-Qwen is not cross-family: the EV-6 ≤2pp leg needs a
      non-Qwen judge (e.g. gemma4). Tests: `tests/test_augment_v1_manifest.py` 5/5, `test_harness.py` 13/13.
    - **OPERATOR RULING 2026-09-16:** internal use of the unlicensed Augment-v1 golden set is APPROVED. Data stays out of git (fetch script + manifest only, research `e70b6974`); do not redistribute. Run leg released to the GPU runner with a gemma4 cross-family judge (reader Qwen3.8-27B, judge gemma-4-26B-A4B).
    - **RUN 2026-09-16 14:30–15:38Z (sub-gpu-runner; box NOT ticked). The EV-6 swap gate FAILS: 2.94pp against a 2.0pp limit.**
      The evidence is research `aac025a4`, `data/ev13b-review-f1-20260916/`: summaries, calibration digests and
      run_record only. Per-case output stays local because it quotes the unlicensed diffs.
      - **Setup.** Reader Qwen3.8-27B-Q8_0, using the production architect_general argv with `-np 1 -c 131072`,
        over 50 PRs × 3 runs on frozen v9 build-hip. There were 370 findings.
      - **Judge calibration.** Both judges are VALID against the 95% bar.
        - gemma-4-26B-A4B Q4_K_M: positive controls 99.0% (n=97), negative controls 100% (n=50).
        - Qwen3.6-35B-A3B-MTP Q8_0: positive 100%, negative 96%.
      - **Semantic Mean-F1** (matcher spec sha `d5a6a9bb`; category CANDIDATE; no codified protocol, so these
        are observations capped at Judged/Located).
        - Judged by gemma (cross-family): **0.338 (sd 0.014)**, per run 0.335/0.357/0.322. Judge parse-fail
          rate 0.8%, no malfunction runs.
        - Judged by Qwen3.6: **0.367 (sd 0.021)**, per run 0.391/0.371/0.340.
        - Swap delta = **2.94pp > 2.0pp → gate FAIL**. The Qwen judge scored higher in all 3 runs (per-run
          deltas 5.6/1.5/1.8pp), which is consistent with a same-family leniency.
      - **Other readings.** Location validity was 1.0. The deterministic build-leg matcher scored TP=0, as the
        spec predicts.
      - **Residency.** Proven for all 3 servers: KFD count 1, VRAM peaks of 35.6/26.0/38.3 GiB, and 3131/476/422
        samples.
      - **Belief kernel.** 6 rows ingested (`ingest review-f1`).
      - **Still open.** The SPEC's leg B (the Qwen3.6 reader) was not run, so this is one reader and not
        "local models". The swap gate failure needs a decision: widen n, change the judge, or record EV-6 as
        failing for this pair.
    - [x] **EV-13b decision: PARKED (operator 2026-09-17)** ✅ 2026-09-17. The operator chose "park it" over the
      other two options (widen n plus run leg B on GPU, or change the judge). EV-13b stays open and is not
      dispatchable. No GPU time is spent on it, and the batch entry should not be scheduled. EV-6 is recorded as
      FAILING for the reader=Qwen3.8-27B, judge=gemma-4-26B-A4B vs Qwen3.6-35B-A3B pair at n=3 (2.94pp).
      **Resume trigger:** a consumer needs a judge-stable review-F1 ranking. The first expected consumer is the
      detect/repair split in `reviewer-escalation-and-human-gate-policy.md` HG-9, whose small-model detection
      leg is what this suite measures. On resume, choose widen-n or judge-swap before running anything.

## Research Intake Update — 2026-06-03

### New Related Research
- **[intake-658] "Which Model Reviews Code Best?" (Factory Research code-review benchmark)** (https://factory.ai/news/code-review-benchmark)
  - Relevance: a **turn-key, fully open-sourced** code-review eval methodology that validates two patterns eval-tower already scaffolds, and supplies a task family we have NOT built (find-bugs-in-a-diff against a human-curated golden set; our suites are answer-correctness / debug-fix / agentic-coding). Released materials: golden set (50 real PRs from Sentry/Grafana/Keycloak/Discourse/Cal.com + curated bug ground truth) under the `droid-code-review-evals` org, and scoring scripts as `review-droid-benchmark`.
  - Key technique → maps onto **EV-6 directly**: their **judge-swap self-favoring-bias ablation** (swap the judge model, observe ≤2pp impact) is exactly our cross-family verification check (`check_cross_family()`). Also liftable: **findings-F1 scoring** (precision = fraction of findings that are real bugs; recall = fraction of golden-set bugs found) with a *semantic* LLM judge (not string-match) — slots into ch07's F1 verifier + ch06's Claude-as-Judge; and a **≥3-run Mean-F1 + StdDev** stability protocol.
  - Reported results: GPT-5.2 60.5% F1 @ $1.25/PR (top); Opus 4.6 59.8% @ $3.11; Sonnet 4.6 57.4% @ $1.15; Kimi K2.5 51.9% @ $0.41; MiniMax M2.7 45.6% @ $0.15. **Cost explains only ~21% of quality variance.** Even the best model misses ~40% of golden-set bugs.
  - Delta from current approach: we'd point the judge at our **local** models (gemma4-26B-A4B worker_general, coder roles, any peer-verifier) and reuse existing Claude-as-Judge plumbing — a reviewer-model F1 suite naturally lands in [`multi-file-coding-completion-capability.md`](benchmark-suites.md#track-multi-file-coding-completion-capability). **Caveat**: vendor self-benchmark (models adjacent to their own product), 50 PRs / 5 repos only — treat rankings as indicative; the judge-swap check mitigates *judge* bias but not golden-set/PR-selection bias. Verdict: adopt_patterns.

#### Deep-dive: full methodology + reproduction plan (2026-06-03)
Deep-dive of `review-benchmark.md` + the released repos + `eval_common.py` source → full write-up in [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md) (Part 4). **Corrections**: (1) judge model is **`claude-opus-4-6` hardcoded** (Anthropic SDK), not Sonnet 4; (2) **"open source" is overstated** — harness repo is **unlicensed**, the v3 golden set (167) is **gitignored**, only Augment upstream **v1 (145)** is genuinely open; (3) provenance is **Greptile → Augment → Factory** (Factory added 31 bugs Droid itself surfaced → self-curation bias); (4) **low-severity golden comments are scored as neither TP/FP/FN** (load-bearing); (5) all 13 models at reasoning_effort=High, 3 runs (malfunction-excluded), **micro-averaged** P/R/F. **EV-NEW (review-finding-F1 suite — now tracked as the EV-13 checkbox above, 2026-07-14)** — reuse Augment v1 + the 5 PR sets, re-implement the ~80-LOC scorer (do **not** vendor the unlicensed file), drive **local** models via `/v1/chat/completions` over diff+context (document the divergence from their agentic whole-repo setup), judge with a **local cross-family verifier** and run the ≤2pp judge-swap as a concrete **EV-6** instance; index by model/quant not role; per-PR incremental persistence. Absolute F1 is **not** comparable to their leaderboard — internal-only.

## Research Intake Update — 2026-06-20

### DRACO rubric methodology (intake-713 → EV-9)

- **[intake-713] DRACO (Perplexity AI, arXiv 2602.11685)** — a deep-research benchmark contributing rubric-methodology refinements to EV-9 (Multi-dimensional rubric, L240). **Ownership note**: this handoff (`eval-tower-verification.md`) is the OWNING handoff for EV-9; `research-evaluation-index.md` holds only a collective EV-4/8/9/10 pointer, not the EV-9 detail. Methodology transfer only — see numbers caveat below.
- **[intake-713] DRACO scoring — separate positive/negative rubric weighting** — fold into EV-9's LLM-as-judge scoring functions (the per-dimension scorers at EV-9 task 2): weight positive (reward-bearing) and negative (penalty-bearing) rubric criteria independently rather than as a single symmetric score. CPU-portable; no new model required (refines the existing judge prompt + aggregation).
- **[intake-713] DRACO validation — multi-judge ranking-stability across ≥2 LOCAL judges** — validate rubric-score rankings for stability across at least two local judge models. **Reuse the existing `src/bradley_terry.py`** (from autopilot P17.BT-1) as the ranking-stability primitive rather than building a new ranker. CPU-portable; pairs naturally with EV-6 cross-family discipline (the ≥2 judges should be cross-family).
- **[intake-713] DRACO saturation testing — reject sentinels scoring >90%** — when constructing the `deep_research_sentinel` suite (EV-9 task 3), reject sentinel queries that any candidate scores >90% on (saturated → non-discriminative). This is also a **chapter-07 recommendation** — flagged as a recommendation only; we do NOT edit chapters here.
- **[intake-713] DRACO content axes — ADDITION, not a swap** — EV-9's existing four rubric dims (`rubric_reasoning_trajectory` / `rubric_tool_calls` / `rubric_outline` / `rubric_content_stage`) are **MindDR-process** dimensions. DRACO's four **CONTENT** axes — Factual Accuracy / Breadth-Depth / Presentation / Citation — are an ADDITION to consider alongside them, NOT a replacement. The `deep_research_sentinel` suite already exists (MD-8 done 2026-04-22); these ideas refine HOW it is constructed/scored, not WHETHER it exists.
- **[intake-713] DRACO production-query sampling — DESIRABLE-BUT-GATED** — DRACO's task-construction front-end samples real production queries. EPYC has no Perplexity-scale traffic, so this is gated: substitute = draw from [`frontier-f1-real-task-corpus.md`](../completed/frontier-f1-real-task-corpus.md) once its soak yields ≥100 real records. Do not block EV-9 construction on this; use synthetic/curated queries until the corpus matures.
- **[intake-713] DRACO reported numbers — external observations only** — Perplexity Deep Research 70.5% (and the rest of DRACO's leaderboard) are external/closed-system observations on Perplexity's stack; they are NOT runnable here and are NOT decision-gating for EPYC. Methodology transfer only — no number is lifted as a target or baseline.

## Research Intake Update — 2026-06-23

### EV-9 saturation: empirical instance — our production review suite cannot resolve top-of-stack models (operator-flagged)

The DRACO "reject sentinels scoring >90% / saturated → non-discriminative" methodology (L409) now has a **concrete, dated instance from our own production review suite**, surfaced during the 2026-06-22 MTP-refresh promotion analysis (see [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh) "Eval-resolution caveat"):

- **Symptom**: gemma-4-31B (31B **dense**) and gemma-4-26B-A4B (~3.8B-active **MoE**) both score ~90% on our `benchmarks/results/reviews/summary.csv` suites — i.e. a small MoE *appears tied* with a much larger dense model of the same family. Operator (correctly) flagged this as implausible.
- **Diagnosis = instrument saturation, NOT model parity and NOT quantization**: public dense-Q4 gemma-4-31B ≈ 92% (above our 90%) rules out a Q4 penalty; the dense 31B is genuinely ~1–3pp stronger on standard suites and ~8–10pp on frontier/agentic suites **we do not run**. Our suites sit in the saturated 90–94% band, so they cannot resolve the real gap — the exact failure mode EV-9 saturation-rejection exists to prevent, observed on a *deploy-gating* comparison rather than a sentinel-construction screen.
- **EV-9 implication (operator-review candidate, NOT actioned here — eval trust boundary is human-amendment-only)**: (1) the >90%-saturation reject rule (L409) should extend beyond `deep_research_sentinel` construction to a **standing audit of the production review suites** — any suite where the top-2 stack models are within noise at >90% is non-discriminative for promotion decisions and needs a harder tier; (2) this is direct motivation for the **frontier/harder eval tier** the eval tower lacks (pairs with EV-8 redundancy pruning, L238 — prune saturated suites, add discriminative ones). The Qwen-Scope feature-coverage-saturation proxy (EV-8) could *flag* such suites evaluation-free.
- **Cross-refs**: memory `feedback_eval_saturation_masks_model_gap`; sibling resolution-artifact precedent `feedback_per_suite_gate_resolution_artifact` (per-suite 1-question flips). The MTP-refresh Pareto-domination call (worker A4B over dense 31B) stays valid **for the worker role** (~90% bar + speed-dominated); it must NOT be generalized to "A4B = dense-31B in capability."

## Research Intake Update — 2026-07-16 (Reviewer control plane: EV-9/ECE/AUC reuse contract)

The Architect→Reviewer control-plane series ([`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)) REUSES this handoff's machinery rather than duplicating it: H4 ([`reviewer-calibration-accounting.md`](reviewer-control-plane.md#track-reviewer-calibration-accounting)) calls the EV-tier ECE/AUC implementations for reviewer Brier/ECE/AUC, and H3's grading turn builds on the EV-9 rubric-judge prompts/scoring (`rubric_scoring.py`). Boundary: reviewer-calibration metrics (FA/FR/CR) are a SEPARATE instrument gating reviewer-role promotion — they do not enter the T0-T3 model-quality axes; the plane invokes the tower, never the reverse. New intake relevant to EV work: intake-834 (Agentic Rubrics — weighted-axis rubric artifact, authoring/grading split, decision bands S≥0.85/≤0.5), intake-836 (judge overcorrection FR≫FA — motivates symmetric tolerance monitoring on any judge), intake-837/838 (judge-bias probe set + Consistency-Rate reporting — applicable to EV-9 rubric judges too).

## Research Intake Update — 2026-07-21 (Judge validity: anchoring, agreement metrics, rubric hacking)

Three new entries converge on one finding: **our judge-scored numbers currently have no validity check that would detect the dominant failure mode.** All three are operator-review candidates — the eval trust boundary is human-amendment-only, so nothing here is actioned by an agent.

- **[intake-875] "More Convincing, Not More Correct: Self-Play Reward Hacking of Reference-Free LLM Judges"** (arxiv:2607.05904)
  - Relevance: directly undercuts a rule this handoff already codifies. Cross-family verification is documented here as the strongest defense; this paper reports hacked errors **transferring across judge families** and a three-family min-vote ensemble still accepting ~55% of hacked wrong answers (FPR 0.438 → 0.552).
  - Key technique: **de-anchoring** — make the judge commit to its own answer *before/without* seeing the candidate. Reported FPR 0.906 → 0.012. A plain "verify/recompute" instruction is measured to be **worthless** (FPR 0.719), so the fix is independent commitment, not a stronger prompt.
  - Best-of-N result is the shape of our exposure: judge-selected gap 0.20 at k=1 widening to **0.588 at k=16** on LiveCodeBench while true unit-test pass moves only 0.27 → 0.29.
  - Delta from current approach: we report judge scores without a paired judge-independent anchor, so a widening judge-vs-truth gap is currently invisible.
- **[intake-874] "Reproducing, Analyzing, and Detecting Reward Hacking in Rubric-Based RL"** (arxiv:2606.04923; Tsinghua KEG) — credibility 4.
  - Relevance: kills the claim that rubric judges are *robust* to hacking (does NOT establish they are worse than verifiable rewards — see the entry's honest scope note; our own intake-660, intake-664#record show programmatic verifiers gamed 32.8% of the time, so neither class is a safe default).
  - Transferable now, no training needed: the **semantic-relevant vs semantic-irrelevant bias taxonomy** (lexical/format vs tone/self-praise) as an organizing axis for RM-5; the **exploitability ceiling** (a bias only bites if the generator can cheaply emit the pattern — format bias ~66% elicitation vs 95-100% for the others); and the finding that **in-domain capability drops while aggregate general benchmarks stay flat**, so an aggregate suite is an unreliable tripwire.
- **[intake-876] "Agreement Metrics for LLM-as-Judge Evaluation"** (arxiv:2606.00093; Rao & Callison-Burch) — see also the note appended to `reviewer-calibration-accounting.md`.
  - Relevance: a full-text search of the 865-entry index returned **zero** hits for kappa / Krippendorff / inter-annotator / inter-rater before this run. Neither MEASUREMENT.md nor MEASUREMENT_POLICY.md mentions agreement statistics at all.

- [ ] Operator-review candidate (EV, judge validity): adopt an **anchor rule** — any judge-scored metric used to gate a decision must be paired with a judge-independent verifier (exact-match, unit tests, code execution, or held-out anchor), with the judge-vs-anchor gap reported alongside the judge number; a gap that widens with N is the reward-hacking signature. [intake-875]
- **[declined: ws58 2026-11-03 content-review: merged into the offline A/B — the rule proposal follows the local evidence, and its capability threshold is measured there]** Operator-review candidate (EV, judge validity): adopt a **de-anchoring rule** for judges used in *selection* (commit-first or blind-solve rather than show-candidate-and-ask), **GATED on a measured verifier solve-accuracy threshold**. Record against it the caveat that cross-family ensembling is only a partial defense. [intake-875]
      - **Amended 2026-08-19 after the intake-875 dive.** The rule as originally drafted was unconditional and, adopted that way, could measurably make the reviewer plane *worse*. De-anchoring has a **capability threshold**: it helps judges that can solve the task and *hurts* those that cannot — the 1.7B judge in that paper goes 0.588 → **0.637** (worse) under commit-first, while the 8B goes 0.378 → 0.227 and it plateaus by 8B. Corollary 1 gives the gate: a judge's verdicts are certified anchored iff its independent solve-accuracy exceeds an FPR-implied threshold (0.583 for GLM-5.2, 0.458 for Qwen3.6-27B on the C-CRAB slice). **That number has never been measured for our pool — RM-11b measures it, and this rule should not be adopted before it lands.**
      - Second amendment: the FPR→0.012 collapse this rule leans on is a **math / exact-match** result. On **code** — our actual judging domain — de-anchored gap@16 floors at 0.225–0.227 even at 14B, never approaching zero. The rule is a large improvement, not a fix.
- **[declined: ws58 2026-11-03 content-review: merged into the offline A/B as a second arm (clean rubric vs bias-augmented rubric gap per judge config)]** Operator-review candidate (EV-6): run the **dual-judge offline audit** — score a held-out set with a clean rubric and with a deliberately bias-augmented rubric, report the gap per reviewer/judge config. Runnable on our stack today, no training required. [intake-874]
- **[declined: ws58 2026-11-03 content-review: curiosity — no gate consumes an exploitability axis; the judge-validity decision rides on the offline A/B]** Operator-review candidate (EV-9 / RM-5): extend the bias-robustness probe set with the four CHERRL bias families and add exploitability (can the *author* cheaply emit the pattern?) as a second reporting axis. [intake-874]
- [x] Operator-review candidate: quantify the judge-scored fraction of the autopilot quality objective — count distinct `scoring_method: llm_judge|rubric` questions per suite and their weight in the Pareto quality axis. **PRE-ESTABLISHED 2026-08-19, which is why this is now a bounded count rather than an open-ended audit**: autopilot's selection function contains **no LLM judge** (`pareto_archive.py:660-678` builds the Bradley-Terry matrix by axis-wise Borda over numeric objectives), and the rubric multi-judge path is **gated off in production** (`AUTOPILOT_RUBRIC_JUDGE_ROLES` appears only in tests and defaults empty, `eval_tower.py:3439-3446`). Occurrence counts across orchestrator suites put `llm_judge` at 49 and `rubric` at 20 against ~9,400 total, i.e. ~0.7%. Residual exposure is (i) that ~0.7% rolling into the quality axis and (ii) the reviewer decision plane, which is genuinely candidate-conditioned reference-free judging and is tracked separately at RD-2. [intake-875] ✅ 2026-10-31 — APP `fb127bf0206bd6f038ffd227e0499ed4d98ecedc`; `tests/unit/test_judge_exposure.py` 9 passed; [durable evidence](../../artifacts/non-inference/codex-ni-next-accepted-20261031/CAPSULE.md#judge-method-exposure), APP `orchestration/reports/judge_exposure_20261031/{pool_inventory,retained_t1_batch}.json`: 4.6164% declared-input inventory, 2.2222% retained historical core-batch denominator; neither current live judge invocation nor performance. [belief: cc]
- [ ] Operator-review candidate (EV-6, judge validity): **split the cross-family claim at the top of this file** — it is currently stated once, as one rule, and it is true of one failure mode and false of the other. Do NOT delete it; scope it. [intake-875] [intake-1168]
      - **FALSIFIED as an anti-reward-hacking defence.** Proposition 2 in intake-875 proves that *any* non-decreasing aggregation over reference-free verdicts is monotone in the shared plausibility signal and bounded below by the product of individual FPRs — which covers majority-k, min-vote and Bradley-Terry consensus alike. Measured: the three-family min-vote ensemble still accepts **~65%** of hacked wrong answers (three-seed mean; our records previously carried **55%**, which is seed 0, the most conservative). On code the same ensemble accepts 16.4% of wrong programs, 2.38× the independence prediction. Training against the ensemble makes it *worse* (Min FPR 41.2% → 73.3%). The axis that works is independence-from-the-candidate, **not** diversity-of-judge.
      - **SURVIVES as an anti-collusion / self-favouring-bias control** — its original EV-6 justification, and independently supported by intake-1168, which finds verifier *gain* highest cross-family and lowest in self-verification, with FPR rising under self- and intra-family verification.
      - **Scope boundary that must travel with the surviving half**: intake-1168 measures **unoptimised** solver distributions; intake-875 measures distributions **optimised against the judge**. The cross-family rule is valid only while nothing is optimising against the verifier — and a best-of-N selection loop is exactly such an optimiser.
      - Note the internal inconsistency this resolves: the claim near the top of this file and the intake-875 finding recorded further down have coexisted unreconciled.

### Audit catch 2026-07-21 — de-anchoring can be EVIDENCE-GATHERED before the rule decision

The anchor/de-anchoring rules above are human-amendment-only (trust boundary). But **measuring** de-anchoring on our own data is not a rule change — it is evidence gathering, and it makes the operator decision empirical rather than paper-cited:

- [ ] Offline A/B on an existing labeled set (e.g. the RM-3/RM-5 reviewer corpus, or any suite with gold labels): score the same candidates with (a) the current show-candidate-and-ask judge and (b) a commit-first judge (judge answers independently, then compares). Report FPR on known-wrong answers for both, with a chance-corrected agreement stat per intake-876. intake-875's claimed effect is FPR 0.906 → 0.012 — if ours reproduces at even a fraction of that, the rule proposal carries local evidence; if it does not, we saved a constitution amendment. Moderate judge-inference cost → candidate for the inference-batch loop rather than ad-hoc execution. Arms (absorbs the de-anchoring rule and the dual-judge audit): (a) show-candidate-and-ask judge, (b) commit-first judge, (c) clean rubric vs bias-augmented rubric for each judge config; report FPR on known-wrong answers and chance-corrected agreement (intake-876). Decision: if (b) cuts FPR by >= half of intake-875's 0.906 -> 0.012 effect on our corpus, propose the de-anchoring rule gated on the measured solve-accuracy threshold; otherwise record that no constitution amendment is warranted.
- [ ] Forward guard from intake-877 (was prose-only in progress): when the three absent-source suites are downloaded (operator ask), attach a **web-egress check** to any GAIA run — the suite is 165 verbatim public questions and is only safe on the direct-completion path; repl mode + `frontdoor` (the sole `web_access: true` role) is the one contaminating combination.

- [ ] **Cross-fleet arm-parallelism for rebaselines (operator-endorsed 2026-07-23; TRIGGER: implement
  WITH the next scheduled EV-4-class cross-fleet run so it lands with its consumer)**: CORRECTED DESIGN
  SPACE (operator 2026-07-23 — fleets overlap on cpusets/BW; naive 4∥4 overlap is NOT free):
  (i) overlapped 4∥4 — NOT VIABLE under live policy (operator correction #2, 2026-07-23):
  CROSS_ROLE_DISJOINT_PLACEMENT=1 + per-region locks SERIALIZE overlapping-region requests across
  roles — the arms would interleave, aggregate ≈ serial, no win. (The ~1.3-1.7x figures were
  contention-matrix MEASUREMENT experiments that produced this policy, not allowed placements.); (ii) **node-partitioned layouts
  (operator-proposed, likely the real ~2x): frontdoor half on node0 ∥ worker quarters-of-the-
  disjoint-half on node1, or two disjoint halves — true cpuset disjointness + per-node BW
  isolation**; each arm keeps a full node's local bandwidth. Quantify (ii) vs (i) via the E5
  NUMA×batch mapping (batched-decode-measurement.md) BEFORE implementing. Not applicable to
  tier/whole-stack draws (route across all roles; no disjoint layout exists). Protocol must declare the mode (solo vs overlapped
  load profile) for era comparability. Cross-ref: design-backlog-triage-2026-07-23.md Section 2 top-3.
- [x] ✅ 2026-07-23 T1+T2 DONE (T1 1.600 core_v2 rel 0.90 escalation-off-verified; T2 1.891 rel 0.92) + reseed APPLIED by operator; T3 leg now gated ONLY on the architect decision (judge prereq MET 76c34590) **core_v2 re-run batch composition (2026-07-23, REVISED per operator architect-swap caution)**:
  when core_v2 promotes, run **T1+T2 with think-harder/architect escalation explicitly pinned OFF**
  (declared protocol property, not gate accident; verify architect-independence per-row via
  think_harder_attempted in the sidecar) — baselines then measure the try-cheap-first serving plane
  and stay VALID across the pending architect model swap; reseed consumes these. **T3 HELD** until
  BOTH (a) the llm_judge response-shape fix (evidence: ev_baseline_e7_tier1 sidecar
  zeroscrolls/physreason rows) AND (b) the operator's architect-model decision land — T3's
  expert/hard population is the escalation-prone tier where the architect materially serves;
  measuring it days before a swap bakes in an immediately-stale anchor.
- [x] **Unify autopilot's second McNemar producer (filed 2026-07-23) ✅ 2026-07-29**:
  the observation-only sequential baseline payload now consumes `paired_stats.verdict_from_result`
  under `mcnemar_verdict` while preserving `used_for_gating: False`; verified by
  `uv run python -m pytest -q tests/unit/test_paired_stats.py tests/unit/test_autopilot_sequential_wiring.py` (72 passed).
- **Architect resource model — heterogeneous correction (operator, 2026-07-23)**: "escalation
  drains the machine (quarters idle before the 122B takes the full bank)" holds ONLY for the
  pure-CPU plane. With the MI210 in the design, the drain constraint dissolves into an OPEN
  OPTION SPACE (operator: do NOT settle this in prose — it is a strategic-triage row): (A)
  architect on GPU, CPU plane untouched; (B) CPU roles teleport to GPU, architect takes the CPU
  bank (bandwidth asymmetry cuts both ways — MI210 HBM ~3.5x socket BW, the decode-bound party
  wants it); (C) hybrid layer-split residency; (D) dynamic residency under the slot fabric —
  under which the static choice partially CONVERTS to autopilot-exposable surfaces (residency
  thresholds, teleport break-evens, per-device slot budgets). Decide with E5 + slot-fabric
  measurements, not assumption. Changes
  T3 economics post-architect-decision (escalation tier measurable without touching the CPU
  baseline plane). Generalizes under heterogeneous-slot-fabric-residency.md ("everything is a
  slot"); residual cost = CPU↔GPU stream-teleport break-even (~150-250 resident tokens). The
  pending architect bench includes GPU arms — the swap decision may itself select this topology.


## 2026-07-25 — intake Stage-2a dive: EV-9 frontier-tier candidate + EV-10c admission prefilter

_Via `/research-intake` Stage-2 2026-07-25; see [`intake-derived-work-2026-07-25.md`](../completed/frontier-lab-automation.md)._

- [ ] **EV-10c — single-artifact admission prefilter (CORE pattern, intake-888).** Before a candidate skill/insight/prompt fragment reaches the EV-10a paired per-suite gate, re-attempt ONLY the originating failure with ONLY that artifact in context; admit iff success rate beats the pre-artifact baseline. Rejects junk at ~1 rollout each instead of a full paired suite run, and gives the SkillsBench net-negative caution (intake-096) a mechanical filter. Keep EV-10a as the authoritative accept gate.
- [ ] **EV-9 frontier-tier candidate — FrontierCS (arXiv 2512.15699).** EV-9 records production suites saturating in the 90–94% band and unable to resolve the top-2 models; FrontierCS is maximally non-saturating (best model Score@1 **29.37** vs human expert **95.41**) and ships per-problem evaluators. **Start with a ~10-problem FLOOR PROBE on one production arm** before costing the exec-sandbox harness: all published baselines are proprietary API models, so our open-weight arms may land near zero — trading a saturation problem for an equally non-discriminative floor. Version note: paper v1 = **156** problems; the site reflects FrontierCS **1.0, 240 tasks / 172 algorithmic**. **No seeds, variance or significance testing anywhere** — do not build ranking-sensitive work on it, and define our own protocol-id rather than inheriting theirs.

## Research Intake Update — 2026-08-15 (measurement resolution: VeRO / HarnessOpt-Bench cluster)

Source cohort: intake-1128…1147 (MEGA + Phantom Guardrails, operator-submitted 2026-08-14; 14 entries
dive-verified). The convergent finding across four independent sources is that **we gate acceptance on
deltas we have never measured the resolution of.**

**The gap, precisely.** Three mechanisms touch resolution today; none blocks on the aggregate quality
axis:

| Mechanism | Measured? | Blocks acceptance? |
|---|---|---|
| MAD noise filter (`safety_gate.py:1419-1439`, rolling 10-sample window, z>2.0) | **Yes** | **No** — warnings/categories only, feeds `learning_exclusions.py`; also only ever sees deltas ≥ 0 |
| Per-suite 3/n single-flip quantum (`safety_gate.py:242-254`) | No — analytic quantization | Yes, but only on the per-suite *regression* side |
| `self_criticism.py:48-56` min-resolvable-delta, third state "within eval resolution" | No — derived 3/n | **No** — runs *after* the gate, emits prompt/journal text only |

The three constants that actually decide `passed` on quality are all **chosen, not measured**:
`QUALITY_FLOOR_T0=2.0`, `QUALITY_FLOOR_T1=1.0`, `REGRESSION_THRESHOLD=-0.05`.

**This is not a new idea here** — we already declare noise floors elsewhere (K-RAG-1's 2pp floor in
[`bulk-inference-campaign.md`](eval-tower-program.md#track-bulk-inference-campaign), where a 1.31pp gap was correctly called
below-floor; and calibrated floors throughout [`autokernel-research-loop.md`](autokernel-loop.md#track-autokernel-research-loop)).
The eval-tower *quality* lane is the one place the instrument is missing, and its absence is already
documented in this file's 2026-06-23 EV-9 section via `feedback_per_suite_gate_resolution_artifact`.

### EV-14 (NEW 2026-08-15) — measured resolution band, and promoting it to the gate

- [ ] **EV-14a — Measure a per-suite resolution band using the instrument we already have.** Run
      `scripts/autopilot/core_v2_calibrate.py --repeats` (fixed n and seed, standalone JSONL rows,
      spread fully retained, nothing averaged) against ONE **UNCHANGED** config per T1 suite; derive
      the band from the retained spread and publish it beside the suite. Report a difference smaller
      than its own suite's band as **UNRESOLVED** — never as "no change", never as a regression.
      **Do NOT build a new rescore harness.** External method: `intake-1140#02` (published and
      citable). External evidence of magnitude: `intake-1141` measured one *unchanged* harness at
      0.800 and 0.547 on the same suite.
      **ATTEMPTED 2026-08-28 (first real run, CPU-only) — run performed, band NOT emitted, root
      cause documented, HELD pending the GPU judge lane.** Staged protocol executed from the
      orchestrator repo (`core_v2_calibrate.py --n 300 --repeats 3 --seed 4242 --trial-id-base
      900000`, tier-1 baseline pinned before repeat 0, core `tier_stratified_equal_thirds_v1_
      seed_4242_n300_rot45000`, era E16-eval-history-scoped-quiescence-v10-quality) against the
      CPU serving fleet (orchestrator :8000 → frontdoor 35B / worker gemma / ingest 80B lanes).
      Repeat 1/3 completed clean on the protocol side (q=1.410, r=0.943, n=300, 4-wide
      concurrency, eval_wall 14,033s ≈ 3.9h) but carried **17 infra-failed questions**, and
      `build_band_artifact` is fail-closed on ANY degraded repeat — so no `.band.json` was
      emitted and the run was stopped before repeats 2-3. **Corrected failure attribution (13:50Z
      wrap):** 10× physreason `vision_unavailable` = MISSING IMAGES on disk, not a dead lane —
      the PhysReason-full.zip (68 MB) sat unextracted in the HF cache (`datasets--zhibei1204--
      PhysReason`); **extracted 2026-08-28 to `/mnt/raid0/llm/tmp/physreason/`, 0/2576 image
      rows now missing** (vl images were already present, which is why vl scored clean on the
      same worker_vision route). 5× architect_general `conn_refused`/`circuit_open` on
      agentic/coder/gpqa_diamond/mmlu_pro = **generation-lane escalations to the GPU-resident
      architect_general** (substring/multiple_choice scored, NOT judge calls — an
      `LLM_JUDGE_ROLE=architect_critic` override would NOT have fixed them); these wait on the
      GPU lane being realized again (operator: architect_general is GPU-hosted and occupied).
      2× transient (placement + request timeout). **Band estimate once the GPU lane is back:
      ~12h** (3 × ~3.9h measured + ~1h build/ingest/rows); the physreason data fix is already in
      place so a re-run should be clean on that front. Evidence:
      `/mnt/raid0/llm/epyc-inference-research/data/eval-tower-bands-2026-08-28/` (JSONL + driver
      + waiter + ingest scripts). Pending: re-pin + re-run when architect_general (and
      worker_vision for the image suites) are realized.
- [ ] **EV-14b — Decide whether the measured band should BLOCK.** The only measured instrument (MAD) Decide together with EV-14b' (absorbed): the candidate is measured live every trial while the baseline is a pinned prior scalar never re-measured, so only the candidate side can be zero-filled or unlucky; the third gate state must account for that asymmetry, not only for the band.
      never blocks and never sees negative deltas; the only blocking resolution bound (3/n) is
      analytic. `self_criticism.py` already computes the right third state and discards it. Proposal:
      give the gate that third state, so a sub-band delta records as `unresolved` rather than
      counting as an improvement.
- **[declined: ws58 2026-11-03 content-review: merged into EV-14b (its own text says decide alongside)]** **EV-14b′ — The candidate/baseline asymmetry is structural, not just a K mismatch.** The
      candidate is measured LIVE every trial; the baseline is a PINNED PRIOR SCALAR never re-measured,
      so only the candidate side can be zero-filled, infra-degraded or unlucky. There is no paired
      re-run of the incumbent, and the existing mitigations (`reliability_blocked`,
      `quality_rebaseline_hold`) are one-sided suppressions that skip the comparison rather than
      equalizing it. Decide alongside EV-14b. This is a stronger form of `intake-1141`'s √K argument
      (repo-only; that argument is NOT in the paper).
- [x] **EV-14c — Fix the baseline last-write-wins collapse (defect, not enhancement).** ✅
      2026-08-26 — `safety_gate.py` now keeps per-tier baseline REVISIONS bumped by every
      identity-changing `update_tier()` write (persisted through load/save/state), logs an explicit
      `BASELINE MOVED T<n> (prior -> new)` WARNING naming the measurement pins it invalidates, and
      `update_baseline()` REFUSES a promotion whose compare-to-write span saw the reference move
      (compare-to-ghost is now impossible). 11 new tests
      (`tests/unit/test_safety_gate_ev14c_reference_pin.py`) + 262 orchestrator suite tests pass.
      EV-14a can now measure a band against a pinned reference that cannot silently move.
- [x] **EV-14d — Assert expected case count before scoring.** ✅ 2026-09-14 — `epyc-orchestrator`
      `4555677e`. `_eval_batch` returns `[r for r in results if r is not None]` and can come back
      SHORT (abandoned lane, cancelled future, serial wall-budget `break`), so the four writers that
      defined `n_questions = len(results)` (`eval_tower.py:6637`/`6747`/`6872`/`6971` on origin/main
      — calibration, math_rebaseline, question_subset, resume_incomplete) renamed the shortfall as
      the denominator: 40 of 50 scored was indistinguishable from a complete draw of 40. All four now
      emit `n_questions` = the REQUESTED count plus `n_questions_completed` /
      `n_questions_missing` / `completeness_ratio` / `draw_complete`, each mode report carries a
      top-level `draw_complete` + `incomplete_roles` fold, and the window runner's
      `_arm_decision_blocker` / `_verifier_result_blocker` block on a recorded requested/completed
      gap. `draw_is_complete()` is fail-closed (no counts ≠ complete); `draw_shortfall()` is silent
      on pre-EV-14d artifacts so old reports are not retroactively failed. 14 tests
      (`tests/unit/test_ev14d_short_draw_completeness.py`), including the real
      `eval_question_subset` call site returning 7 of 10 and the gate consumer refusing it.
- [x] **EV-14e — Record the baseline pin INSIDE the trial record, beside the delta.** ✅ 2026-09-14 —
      `epyc-orchestrator` `4555677e`. `JournalEntry.baseline_pin` now records tier, reference
      quality, the EV-14c `tier_revision`, `eval_quality_era` / `autopilot_speed_era`, the per-suite
      reference map + its counts, the baseline path, and the `delta` / `relative_delta` the trial
      actually measured — so the comparison is self-contained instead of joined by hand.
      `baseline_pin_for()` prefers the structured field and falls back to `_BASELINE_QUALITY_RE`
      (`experiment_journal.py:99`) ONLY for pre-2026-09-14 rows, marking the read
      `source="legacy_failure_analysis_regex"` and logging it once per trial; a corrupt 0-3-scale
      prose baseline is reported suspect with `baseline_quality=None` rather than handed back.
      autopilot captures the pin via `Baseline.pin_tier(register=False)` BEFORE
      `gate.update_baseline()` can move the reference (the write-time read would have been the
      POST-promotion value), mirrors the rebaseline hold as `suppressed_by`, and cannot fail a trial.
      Schema is additive: the field defaults to `{}`, legacy shards load unchanged, no journal file
      was rewritten or back-filled. 14 tests (`tests/unit/test_ev14e_baseline_pin_record.py`).
      Zero edits to `safety_gate.py`.
- [ ] **EV-14f — Known-null corpus: run the optimizer against inputs with NO failures and assert it
      proposes nothing.** Our eval tower measures whether a change HELPS, never whether a proposed fix
      ANSWERS a real observed failure. Method: `intake-1129`'s Counterfactual Fabrication Lab, whose
      whole design is that the correct action is known to be "do nothing". This is the cheapest
      measurement of the exposure that `safetygate-rlvr-provenance-audit-2026-07-22.md` SG-W2 tracks,
      and it needs no gate change. Carry the source's limits: its effect was concentrated in one
      proposer of five, and the trigger was a board-game genre prior whose analogue in
      kernel/routing/benchmark harnesses is untested — a null result here is informative, not
      exculpatory.
- [x] ✅ 2026-10-31 **EV-14g — decide whether `EvalResult` carries a completed count beside `n_questions`.** Evidence: orch `e60e51887b3956d017af1ed74988e1d9fa795272`; `tests/unit/test_ev14g_completed_count.py`; `/mnt/raid0/llm/tmp/refactor-ev14g-integration-20261031/PROMOTION.json`. [no-belief: source contract and fixture validation, no inference claim]
      Added nullable requested/completed counts through EvalResult, journal and task-rate inputs; explicit zero stays zero and legacy unknown keeps the existing fallback. Prior gap: it had none
      today (set from `total_count` at `:5580` on origin/main), so EV-14d's requested/completed split stops at
      the four per-role mode reports; if the pair belongs on `EvalResult` it also lands in `eval_details`, the
      journal and `tier_specs._task_rate_inputs_from_row` (`scripts/autopilot/eval_tower.py`) (found
      2026-09-14, noninf sweep).

*Declined 2026-09-14: the `"vs baseline {q:.3f}"` prose still emitted at `scripts/autopilot/safety_gate.py:1949`
— not filed because it is a deliberate keep recorded in EV-14e's scope (it remains the human-facing line, and
deleting it would change `has_legacy_scale_failure_analysis` behaviour), i.e. a decision already taken, not an
open action.*

**Reuse, do not rebuild**: `core_v2_calibrate.py --repeats` (repeat scoring, spread retained);
`paired_stats.py` (McNemar — exact binomial, continuity-corrected normal, verdict surface,
discordant-pair sample-size guidance); `pareto_archive.hv_slope_noise_floor()` (an existing *measured*
floor, though it gates stagnation rather than acceptance).

**Do not miscite SEQ-B.** It lives at `src/autopilot_core/tier_specs.py:121-147` (not under
`scripts/`), and it root-caused a **measurement-pairing bug** — an unchanged config scored a rate
regression because candidate and incumbent used different denominators — *not* sampling noise. Cite it
for the "an unchanged config scores a regression" framing and for deriving a constant from 396
journaled trials. It is **not** precedent for a measured noise band.

---

## Research Intake Update — 2026-08-19 (LLM-as-a-Verifier re-ingest: the local read-out instrument)

Source round: intake-362#record / intake-363#record / intake-804#record re-encountered and dived; intake-875 reconciled; new entries
intake-1161…1171. The re-ingest overturned the rationale that kept this source unused since
2026-04-14 — see the corrected "Logprob Truncation" section above, and the `dive_corrections` on
intake-363#record.

**Why this is EV-15 and not EV-5.** EV-5 deploys ThinkPRM for **step-level process** verification
inside T2. EV-15 is a **trajectory-level selection** read-out — a scoring instrument, not a tier
verifier. They share the cross-family constraint and nothing else.

**Scope discipline, stated once.** EV-15 builds and validates an *instrument*. It does **not** deploy
a selector, does not touch T0/T1/T2 reward semantics (AP-27 specifies "state matching, not
LLM-as-judge" for verification functions and nothing here proposes otherwise), and does not by itself
justify best-of-N anywhere. Whether the instrument is worth using is decided by RM-11a/RM-11b in
`reviewer-model-ablations.md`, not here.

### EV-15 (NEW 2026-08-19) — local logprob-expectation read-out: build the instrument, then let the measurement decide

- [ ] **EV-15a — Clean-room port of the eight read-out formulas.** Implement mode, mean, rounded mean, Absorbs EV-15c: guard the two silent failure modes — a thinking model emitting its reasoning token at position 0, and a generation-oriented chat template — by asserting the score position before trusting a score and failing loudly (intake-1170).
      median, 1st percentile, risk-averse mean (lower semi-deviation), quantile integral and
      probability of superiority **from the CC BY 4.0 paper's Table 3**, not from the reference repo —
      that repo carries **no LICENSE** (verified four ways) and is all-rights-reserved. Validate against
      the golden vectors recorded on intake-1169, which include a K=5 case where risk-averse mean flips
      sign against the mean and a K=9 case where quantile and probability-of-superiority disagree in
      sign. Fix the four defects the dive reproduced by execution while porting (hardcoded `dim=1`
      breaking batched input, hardcoded `.float()` breaking float64, in-place mutation of the caller's
      tensor, no sum-to-one validation). [intake-1162] [intake-1169]
  - 2026-10-31 source partial (codex-ni): orchestrator `2de4e338247c2e7b4589f1b258044d9f3c3e5736` adds the eight paper-based NumPy readouts in `src/typed_decisions/distributional_readout.py`, with independent/comonotone coupling, shifted-support RAM normalization, float32/float64 batching, immutable inputs, bounded simplex validation, and explicit refusal of underspecified exact mode/rounding ties. Ten focused tests and `make gates` pass; Git proof is `artifacts/audit/ni-ev15-readouts-20261031/README.md`. New hand-computable K=5/K=9 fixtures are explicitly not the historical intake vectors. The referenced original numeric goldens were not found in the current ROOT tree, reachable intake publication history, or bounded artifact search, so original-golden conformance remains unverified and EV-15a stays open with no completion credit. No unlicensed reference-repository code, live judge integration, or model-quality result is claimed. [no-belief: clean-room mathematical source controls; original acceptance incomplete]
- [x] **EV-15b — Pin the read-out spec.** Force an assistant prefix, read completion **position 0**, ✅ 2026-10-31 ROOT `b60a0de57f426fd0c155f06c65245b58b28144c9`; [spec](../../docs/design/ev15b-readout-spec-20261031.md), [tests](../../tests/test_ev15b_readout_spec.py). [no-belief: design specification and deterministic math]
      restrict to the K score-token ids, `exp` then renormalize **over those K only**. Temperature
      **1.0 exactly**: softmaxing the K judgment logits at T=1 is mathematically identical to
      exponentiating the K score-token logprobs and renormalizing, because the full-vocab denominator
      cancels — and that equivalence holds at T=1 and nowhere else. Mass on non-score tokens is
      discarded, not redistributed. First implementation is **K=9, single-digit alphabet, no-CoT**:
      single-token in every tokenizer we run, and it sidesteps the token-bias artifact that appears at
      large K. [intake-1162] [intake-1169]
      - The 1–9 alphabet is the implementation choice, with per-tokenizer/context verification required before use; no actual tokenizer or model was tested. EV-15c/d guards, native scoring and deployment remain open. [no-belief: design specification and deterministic math]
- **[declined: ws58 2026-11-03 content-review: merged into EV-15a as its guard]** **EV-15c — Guard the two silent failure modes** [too-big: native capture provenance and template validation need handoff design], both of which return a well-formed logprob array
      containing nothing scoreable and neither of which raises: (i) a thinking model emitting its
      reasoning token at position 0, and (ii) a generation-oriented chat template, which costs ~50% of
      the signal on one backbone and ~20% on another. Assert the score position before trusting a
      score; fail loudly. [intake-1170]
- [x] **EV-15d — `retained_mass` as a first-class per-call field, with a refusal floor.** Assert all K <!-- ✅ 2026-10-31 [implementation: epyc-orchestrator 79230233c04b1e24b8736640d70e290825612880; tests: tests/unit/test_score_token_head.py, tests/unit/test_paired_distributional_readout.py; evidence: artifacts/audit/ni-ev15d-retained-mass-20261031/focused-tests.log (70 passed), artifacts/audit/ni-ev15d-retained-mass-20261031/R6-RECEIPT.json] [no-belief: offline scoring contract and deterministic regression controls; no native judgment claim] -->
      score tokens are present in the head; if any is absent treat its probability as 0 **and record
      the retained mass**, refusing the judgment below a stated floor. **Neither the paper nor its
      reference implementation specifies this fallback** — it is our gap to close, and the retained-mass
      field is what makes the hazard detectable instead of silent. [intake-1169]
- [x] **EV-15e — Pre-aggregation over both presentation orders is REQUIRED, not optional**, and must be ✅ 2026-10-31 [no-belief: offline software controls, no native judgment or measurement claim] [implementation: epyc-orchestrator e38774267ac25366ab05e56097bde0188b67a418; test: epyc-orchestrator/tests/unit/test_paired_distributional_readout.py]
      asserted in the implementation rather than requested in the prompt. It is the single largest
      effect in intake-1162 (56.7 → 73.1 on one arm) and it is one line. Pair it with an **order swap
      per comparison** — this is how we take the positional-bias-cancellation insight from the pivot
      tournament **without adopting the pivot tournament**, which is separately declined. [intake-1162]
      [intake-804]
  - The offline CLI generates both presentation requests for each pair and refuses incomplete, duplicated or identity-mismatched captures; it aligns candidate distributions, averages them, then applies the unchanged readout. Forty-three focused tests and `make gates` passed. This closes the order implementation; native capture and EV-15a/c/d validation remain open.
- [x] ✅ 2026-10-31 **EV-15f — Record the cheaper alternative before building the expensive one.** Evidence: orch `a844520f3cabefe2bbca6aff7231d9bc9eb2e5a0`; `scripts/autopilot/text_rating_readout.py`; `tests/unit/test_text_rating_readout.py` (24 pass). [no-belief: offline text-rating instrument; no judge deployment or comparative measurement claim]
      The standalone JSON-to-readout CLI implements text ratings, explicit preference/tie, confidence weighting and mandatory paired orders; missing/duplicate pairs refuse before aggregation. EV-15e's broader/logprob consumer and scientific comparison remain open. Original rationale: intake-1171 (V1)
      obtains the same graded, tie-free signal from **text ratings plus margin weighting**
      (`w = max(|r_i − r_j|/9, τ)`, `μ = Σwv/Σw`, τ=0.1) with **no logprob plumbing at all**, in ~20
      lines. Two independent papers, two mechanisms, one lever. Build the text route first and treat
      the logprob route as an upgrade that must earn itself against it. [intake-1171]

**Deliberately NOT in EV-15**, with reasons recorded so they are not re-proposed: the Probabilistic
Pivot Tournament (loses 0.29pp to full round-robin at 9,630 vs 13,111 comparisons, and its O(Nk) is not
an advance over V1's earlier O(N)-scale adaptive schedule; at N=3–5 round-robin is 3–10 comparisons);
V1's Swiss scheduler (provably inert at our pool sizes — its max budget is 3N while round-robin is
N(N−1)/2, so 3N ≥ C(N,2) for all N ≤ 7); granularity beyond G≈16–20 (SNR gains +0.002 from G=16→20,
and intake-1162 finds finer granularity flat-to-worse for the expectation specifically); and vendoring
the reference implementation (no licence).

## Research Intake Update — 2026-08-21 (intake-1217, Claw-Eval)

- [x] **ETV-T1** — Claw-Eval (intake-1217, arXiv:2604.06132v3) reports that **trajectory-opaque
      grading misses 44% of safety violations and 13% of robustness failures** that trajectory-aware
      grading detects, measured across 14 frontier models. Our harness grades outcomes. Assess the
      trajectory-aware direction: three independent evidence channels (execution traces, audit logs,
      environment snapshots) feeding fine-grained rubric items, scoring decomposed into
      Completion / Safety / Robustness, and **Pass^k over repeated trials** to separate genuine
      capability from a lucky run. Surfaced as a side effect of a chat-template intake, not sought. ✅ 2026-08-21 —
      **PILOT (narrow) + MONITOR**: the three-channel / Safety-Robustness direction has no denominator in
      our tower yet, but the `tool_use` trajectory/outcome divergence is instrumented and already costing
      us a gate carve-out → one zero-inference report-only task (ETV-T2).

### ETV-T1 assessment — trajectory-aware grading against OUR harness (2026-08-21)

Grounded in the eval-tower code, not in the paper. Every claim below names its source. `intake-1217#record`.

**(1) What our scoring observes today: the final answer string, and nothing else.**
The scorer's entire contract is `score_answer(answer, expected, scoring_method, scoring_config) -> bool`
(`epyc-orchestrator/scripts/benchmark/debug_scorer.py:86-91`) — no trace, no tool events, no environment
argument exists to pass one. It then *deletes* the only trajectory it is handed: `<think>…</think>` is
regex-stripped before grading (`debug_scorer.py:107-108`). Even the execution channel is collapsed —
`_score_code_execution` returns a bare `bool` (`debug_scorer.py:448`), so per-test pass/fail is computed and
thrown away (contrast the research copy `epyc-inference-research/scripts/benchmark/code_exec_scorer.py:160-161`,
which returns `{passed,total,pass_rate,detail[]}`). The tower's call sites pass only answer+expected
(`eval_tower.py:4297-4302` → `scripts/benchmark/seeding_scoring.py:77-116`).
**One exception exists and is unreachable**: the rubric path forwards `tool_events=resp["tools_called"]` into
grading (`eval_tower.py:4282-4288` → `rubric_scoring.py:315-317`), but `_is_rubric_scored_question`
(`eval_tower.py:705-711`) requires a `deep_research*` suite, and the live pool metadata in
`epyc-inference-research/benchmarks/prompts/question_pool.jsonl` (line 1) reports 41 suites / 79,479
questions with **zero** `deep_research` rows. We already built one trajectory-fed grader and never fed it.

**(2) Channel analogues — two of three already exist on the WRITE side; the grader is what's missing.**
- *Execution traces*: PARTIAL. `epyc-inference-research/scripts/benchmark/agentic_swe_harness.py` already
  writes a per-turn trajectory JSONL with `capture_status` / `evidence_complete` / `trajectory_sha256`
  (docstring L29-30; `_verify_entry` L724-740; `persist_turn` L798; summary L886-900) — Claw-Eval-grade
  capture. But it is **build-leg only**: no `trajectories/` directory exists under `/mnt/raid0/llm` or in
  `benchmarks/results/`, and its scoring is still outcome-only (predictions.json → SWE-bench `resolved`).
- *Audit logs*: EXISTS. Durable per-question sidecar `question_results.<arm>.jsonl`
  (`_EvalQuestionJsonlWriter`, `eval_tower.py:2636-2760`) persisting the full raw answer plus `tools_used`,
  `tools_called[:5]`, `disposition`, `infra_reason`, timing (`_compact_question_result`,
  `eval_tower.py:1301-1345`); plus `orchestration/autopilot_journal.jsonl` carrying `eval_details.rlvr_reward`.
- *Environment snapshots*: EXISTS. Per-question `host_covariates` (`eval_tower.py:86-95`, compacted at
  `1200-1215`: min/mean core MHz, `host_inflight`, `numa_balancing`, page-cache and mem-available), plus
  `dataset_sha256` + `test_profile` arm stamping (`eval_tower.py:3046-3078`) and `eval_concurrency`/`eval_wall_s`.
- **NEW BUILD** would be: (a) a grader that reads any of the above, and (b) the Completion/Safety/Robustness
  decomposition — we run no safety suite and no robustness suite, so two of its three axes have an empty
  denominator today.

**(3) Where opaqueness plausibly costs us TODAY — one instrumented case, and two look-alikes that are not.**
- **REAL — `tool_use` T0 sentinels** (live since the n=15 era, `orchestration/instrument_eras.yaml:29`). Our
  own gate documents the divergence verbatim: *"models invoke the tool correctly but don't reliably echo the
  returned secret"* (`scripts/autopilot/safety_gate.py:117-123`). Outcome-only grading turned a
  correct-trajectory/wrong-outcome row into a per-suite regression, and we paid for it with a permanent
  instrument concession — `TOOL_USE_CATASTROPHIC_REGRESSION` plus the advisory branch at
  `safety_gate.py:1865-1873`. We persist `tools_called` for exactly those rows and never compare it to the verdict.
- **NOT trajectory-opaqueness — EV-9 saturation** (L516-523, gemma-4-31B ≈ gemma-4-26B-A4B at ~90%). That is a
  *resolution* failure; a trajectory grader would not have separated them, a harder tier will.
- **NOT, but instructive — the 2026-08-03 dead-API-scores-0% incident.** It was fixed by promoting a
  non-outcome channel to first class (`disposition`/`infra_reason`, `eval_tower.py:2859-2882`). Precedent that
  non-outcome evidence pays — and that channel is already built. Likewise the cross-arm parse-fail gap
  (`feedback_parse_failure_rate_is_a_scoring_artifact`) is a *scorer* bug whose fix is offline re-scoring from
  the persisted answer, which the sidecar already supports.

**(4) Pass^k — we have no repeat policy at all, and an estimator already exists offline.**
`eval_tower.py` contains zero occurrences of repeat / resample / `pass@k` / majority-vote: each question is
generated exactly once per trial. What we vary across trials is the *question draw*, not the sample —
`rotated_core_seed` (`eval_tower.py:887-893`, rationale at `:852`) deliberately re-draws a different question
set each rotation so AutoPilot cannot overfit a fixed seed. That is the opposite budget allocation to Pass^k,
which holds the item fixed and varies the sample: rotation buys coverage, Pass^k buys per-item reliability.
Repeats exist only at run level, in two places: `review_f1/scorer.py:126-135` (Mean-F1 ± population StdDev over
≥3 runs, per-run seed at `review_f1/harness.py:171`) — that is aggregate variance, not Pass^k — and a genuine
Pass^k already implemented in `epyc-orchestrator/scripts/analysis/reviewer_calibration_report.py:329-380`
(`_consistency_and_passk`, `--k` default 2, consistency-gated correctness over per-candidate run groups),
which reads the reviewer ledger, not eval-tower rows.
**Cost to adopt in the tower**: k× inference on every graded item (T1 ~5 min → ~15 min at k=3; T2 ~30 min →
~90 min; the EV-11c 26h serial rebaseline → ~78h), **plus** an instrument-identity change — production
temp+seed42 makes k repeats byte-identical, so Pass^k requires deliberately varied seeds and therefore its own
protocol id (the rule that pins T1 concurrency 3 as identity; cf. EV-PROTO, L209).

**(5) Verdict — PILOT (one narrow task) / MONITOR (everything else).**
The 44% / 13% headline does not transfer as stated: those are violations *present in an agentic trajectory*,
whereas our pool is 79,479 single-turn rows with 44 `agentic` (0.06%), no safety suite, no robustness suite,
and `enable_thinking: false` stack-wide — on most rows there is no trajectory to grade. We already shipped one
trajectory-fed grading path that the pool cannot reach, and the outcome instrument itself is uncertified
(3 CRITICAL / 16 HIGH open, L6); adding a second grading surface on top is out of order.
**So: MONITOR the three-channel / Completion-Safety-Robustness direction until an agentic eval with a
persisted trajectory actually runs in the tower** — the agentic_swe_harness run leg, EV-13b, or EV-5 — at
which point revisit with the trajectory JSONL already in hand rather than designing against a paper.
**MONITOR Pass^k** on the same trigger; when a decision turns on per-item reliability, reuse
`_consistency_and_passk` rather than writing a second estimator.
The single exception is already instrumented, zero-inference, and report-only, so it earns one task:

- [x] **ETVT2-SRC — implement source-bound offline tool-use outcome reporting.** MAIN accepted2026-10-06: [native11/11 and exact APPmain integration](../../artifacts/ni08/tool-use-report-source-20261006/README.md). Known attempted/scoreable denominators, unknown/partial inputs and separate batch/label groups; metadata only, no causal attribution or actual cohort estimate. Parent ETV-T2 remains open.

- [ ] **ETV-T2 — report-only trajectory/outcome divergence counter for `tool_use` sentinels** (cheapest first
      step; ZERO inference, no gate authority). For rows where `suite == "tool_use"`, compare the persisted
      action trace (`tools_called` / `tools_used`, already in `question_results.<arm>.jsonl` per
      `_compact_question_result`, `eval_tower.py:1310,1327-1328`) against `correct`, and emit the count of
      **tool-invoked-but-scored-wrong** rows as a report-only line (EV-7 / EV-10b observe-only precedent — do
      NOT fold it into SafetyGate, Pareto, or per-suite regression authority). Exit criterion: a number that
      says how much of the `safety_gate.py:117-123` carve-out is trajectory/outcome divergence rather than
      genuine failure. If that number is small, this direction is closed for our harness on present evidence;
      if it is large, it is the first honest datapoint for re-opening the Claw-Eval direction. Runs offline
      against existing sidecars — no new inference, no new suite.

## Research Intake Update — 2026-09-15 (judge independence and judge validity)

- [x] **EV-6b (S3-EV-01) — check_cross_family is VACUOUS on its only production call site.** eval_tower passes
      ✅ 2026-09-23 — epyc-orchestrator `21cb7756`: roles resolve to served models via the lean registry; unknown family fails closed as `unverified`; +gpt-oss/glm/kimi/nemotron/minimax; rubric-judge path gates, llm_judge path LABELS each row (`judge_independence`, `judge_independence_counts`) rather than refusing — with the all-Qwen lineup every llm_judge row now reads `same_family`, which is the finding. 39 tests.
      a ROLE name (e.g. architect_general) as verifier_model, no VERIFICATION_FAMILIES pattern matches a role,
      the family resolves unknown, and the permissive default returns True for every generator. The llm_judge
      path has no family check at all. Fix: resolve role → served model via model_registry.yaml before the
      check; fail CLOSED on an unknown family, or record independence: unverified on the row so it can never
      read as a cross-family judgment; extend families (gpt-oss, glm, kimi, nemotron, minimax); apply the same
      check on the llm_judge path. Tests: a role name resolves; an unknown family blocks or labels; the judge
      path is covered. EV-6 ✅ 2026-04-15 shipped the permissive default as design; this supersedes it.
      (intake-1367#record; intake-1377#record; intake-875 already shows cross-family is a partial defense.)
- [ ] **EV-6c — give llm_judge a non-Qwen judge.** Since EV-6b every llm_judge row is labelled `same_family` (default judge `architect_general` = Qwen3.8-27B; every served generator is Qwen): 3,806 pool items (physreason, zeroscrolls, leval, physics) are judged in-family. Choose a non-Qwen judge role (operator model choice; inference to validate), then re-baseline those suites.
- [ ] **EV-16 (S3-EV-02) — judge-validity gate before AUTOPILOT_RUBRIC_JUDGE_ROLES is enabled for any run
      whose scores reach the quality axis.** Run a controlled-perturbation check on deep_research_* answers
      with the intended judge role: localized faithfulness / evidence-omission / fabrication edits, scored
      holistic vs per-chunk, REPORTING THE TIE RATE. Enable only a fine-grained (per-chunk) or
      swapped-pairwise protocol that clears a detection floor pre-registered before the sweep. Zero cost until
      someone proposes enabling the rubric judge. intake-1377#record.

## Minimum viable research execution contract

This section shapes research actions; it does not amend the evidence grades or trust boundary in [`MEASUREMENT.md`](../../MEASUREMENT.md). A stronger domain protocol always governs. Every immediate empirical screen or replay must record:

1. a frozen input manifest and digest;
2. the current production or policy baseline;
3. per-item raw outputs and their retained location;
4. a held-out split or later time window;
5. failures, invalids, and abstentions in the denominator; and
6. a predeclared stop, reject, shadow, or promotion rule.

Deterministic infrastructure uses conformance and provenance fixtures instead of inventing a held-out split, and must state that substitution. The evidence ladder is **screen** (the six controls, sufficient for an internal stop/continue decision), **governed comparison** (screen plus domain calibration, integrity, cost, authorization, or safety controls), then **claim-bearing reproduction** (the complete package needed before an external paper-level claim). A promising screen can advance to shadow; only the owning promotion policy can grant authority. An unfired condition is a non-checkbox trigger record, not blocked work or an index next action.

### Canonical consumer map

| Primitive family | Primary owner | Direct and evidence consumers |
|---|---|---|
| Prepared action and `decision_receipt.v1` | `harness-selection-and-integration.md` / HS-TD-4 | HS-TD-1/2/3; URE-2/2a/3; TD-23/24/25; CJ-15/16; Vidya typed-decision projection |
| Typed-decision shadow and calibration | `decision-aware-routing.md` plus `typed-decision-plane.md` | routing, judge cascade, verifier, tool-focus, context selection, and authorization surfaces |
| Evolutionary selector replay | `autopilot-continuous-optimization.md` | AP-DGM-SEL, SEQ-SHINKA-1, AutoKernel replay, and triggered ALE/AIDE follow-ons |
| Evaluator preflight | this handoff / EV-RI-EXEC-1 | benchmark packages, executable-search campaigns, formal artifacts, and autonomous-science evaluation |
| Native experiment receipts | `vidya-belief-substrate-program.md` | every immediate screen, replay, shadow, and promotion consumer; the shared grader remains authoritative |

Consumers receive separate checkboxes only for distinct integration, schema, or acceptance work. The primary owner implements the shared primitive once.

## Research Intake Update — 2026-09-25 (LensVLM, evolving evaluators, and program-search contracts)

- [x] **EV-RI-EXEC-1 — Executable-search evaluator preflight.** Build the reusable deterministic gate that rejects candidate-supplied objectives, non-finite values, wrong output shapes, malformed or invalid artifacts, and score mismatches after independent recomputation. Bind the protocol ID to task revision, geometry, normalization, arithmetic mode, tolerance, scorer hash, and witness hash; apply a separate rational post-check to finite-decimal geometry. Novelty earns archive credit only after compile/test validity, held-out behavioral scoring, and judge-independent checks, with every invalid candidate retained in the denominator. Acceptance is conformance coverage of every accept/refuse branch plus immutable provenance; a held-out split is inapplicable to this deterministic primitive. This work can proceed without EVL-13's inference-gated contention remeasurement and does not launch a search campaign. Sources: intake-1627#record, intake-1628#record. **Completed 2026-09-26:** research commit `82269e31` adds the host-owned protocol, fail-closed receipt and full-denominator ledger plus 12 conformance tests covering 50 accept/refuse cases; independent review reran all tests, bytecode compilation, and `git diff --check` successfully.

### Trigger records — materialize only when the named condition fires

- **EV-LENS-1/2 — LensVLM recovery and compression accounting.** Activate when visual-token processing is a measured latency or memory bottleneck or a named deployment needs LensVLM. Then recover and pin the exact evaluation artifacts rather than manufacturing an equivalent suite, and separately account for initial tokens, successful text/OCR/high-resolution expansions, reader input, and retriever preprocessing. Source: intake-1582#record.
- **EV-17 — Evaluator-evolution control matrix.** Activate when a live evolutionary campaign proposes changing an evaluator. Then run frozen, anchor-only, full-replacement, no-erasure, erase-only-with-the-same-evaluator, and cached-artifact old/new arms; preserve the immutable external promotion gate and raw per-seed evidence. Sources: intake-1641#record, intake-1662#record, intake-1687#record, intake-1688#record.
- **EV-RI-PACKAGE-1 — Claim-bearing long-horizon reproduction package.** Activate after a promising screen or before EPYC relies on an external reproduction claim. Pin code, task/data split, benchmark view, task IDs, scorer, container, effective config, model/provider, seeds, hardware, per-iteration and raw scorer outputs, tokens, cost, timeouts, wall time, and aggregation code; require clean-room table recomputation and conversion evidence for cross-view ranking. This third-tier package does not block internal screens. Sources: intake-1597#record, intake-1599#record, intake-1631#record, intake-1645#record.
- **EV-RI-RIVER-1 — Reward-transform replay.** Fold this comparison into an existing objective/control replay when a frozen candidate-by-instance matrix exists; otherwise leave it dormant. On activation compare raw, instance-normalized, uniform-rank, and winner-heavy rewards on identical saved evidence, including ties, distributions, ECE/Brier where applicable, and policy-independent ordering. Source: intake-1632#record.
- **EV-RI-HEURI-1 — HeuriGym audit.** Activate when a current campaign selects HeuriGym as a decision surface. Then pin paper-era code, data, tasks, evaluator, timeout policy, and metric formula; separate arithmetic QYI from geometric QCI; exclude `demo/`; create inaccessible final instances; and retain scorer-direction, A/A, repeat, cost, and prompt-exposure evidence. Sources: intake-1633#record, intake-1646#record, intake-1647#record.
- **EV-RI-SPEED-1 — Speedrunner scorer fixture.** Activate when a current campaign selects Speedrunner. Then cover the `3.28`/`3.29` boundary, out-of-range FSR, and records 19/20; keep runtime and analysis thresholds identical and bind all effective-config, run, task, model, provider, hardware, and scorer identities. Sources: intake-1648#record, intake-1670#record.
- **EV-RI-METRIC-1 — Additive-combinatorics metric registry.** Activate when one of these metric families becomes an EPYC decision surface. Register `GHR_theta`, `sum_difference_C`, `restricted_sum_dominance`, and `dilate_growth` separately; reject cross-metric leaderboards, correct family comparators, separate search from exact-verification cost, and keep the Gerbicz witness audit-only until licensing and portable-build metadata exist. Sources: intake-1667#record, intake-1668#record, intake-1669#record, intake-1689#record, intake-1691#record, intake-1692#record, intake-1693#record.

## Research Intake Update — 2026-10-04

Operator-approved [P3](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#p3--exercise-both-harnesses-and-improve-correctness-gated-evaluationtraining) at `3911ec91`. A valid grade and a complete durable archive are distinct outcomes; recovered requests must retain their actual reconnect overhead.

- [x] **EV-RI-CAPTURE-STATUS — Expose question-sidecar persistence status in existing batch details.** ✅ 2026-10-06 — [Contract](../../docs/reference/eval-question-sidecar-persistence-status.md), APP05a18b4e/ROOT490b7030; native37463260425 TRUE9/9 after MAIN3361Git+2context/all3371original custody review. Bounded per-batch status reaches aggregate/filter/role summaries, grades/dispositions unchanged. Prior diagnosticNULL and FALSE6/9 retained; fixture-only0..3 baseline correction, no live eval/model/host tests.
- [x] **EV-RI-RECONNECT-COST — carry outer reconnect cost through original question rows.** ✅ 2026-10-06 — [Contract](../../docs/reference/eval-outer-reconnect-cost.md), native37466167911 TRUE57/57 after MAIN3363Git+2contexts/all3373original-member review; APP726084a8/ROOTa5929784. Outer attempts/backoff/reason reach original question rows; inner retry counts and grading unchanged. No live eval/model/host tests.

**Acceptance.** Fault-inject writer creation, one append and completion-marker failure: grades unchanged, durable counts/status exact. Fake connection failures followed by success and exhausted budget: counts/wait exact, non-reconnectable errors unretried. Cover the direct and watcher paths. Deterministic fixtures replace empirical holdout; count all fixtures, including degraded cases. Consumers are batch details, question metadata and their existing summaries, not a new publication or training system.

**K6 / K9 / M3 qualification.** Evaluation, offline SFT and off-policy RL have distinct requirements. Correctness-before-efficiency is applied by TU-MH-1 in [tool-use-eval-contract.md](benchmark-suites.md#track-tool-use-eval-contract) and S2-CGE-1 in [memento-block-reasoning-compression.md](context-and-token-economy.md#track-memento-block-reasoning-compression); these consumer tasks are not duplicated here. These two repairs establish no training gain or token-perfect GRPO eligibility. Full multi-harness RL requires a named model/workload/objective and eligible original rollouts; exact-token export is implemented only for that actual consumer, under the [approved K/M qualifications](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#broader-follow-ons--distinct-from-the-immediate-integrations).

ETV-T2 source correction2026-10-06: persisted `tools_called` must be a valid native list; a scalar `tools_used` count alone does not establish a trace. No currently inspected sidecar has tool_use rows. Future owner-cohort reporting may quantify observed attempt/wrong co-occurrence; it cannot identify the causal fraction of a SafetyGate carve-out or prove genuine failure. The original parent goal requires additional outcome interpretation, independently supported by that cohort.

## Research Intake Update — 2026-10-20 (harness cluster)

- [x] **EV-18 — Report intention-to-treat beside per-protocol for every AutoPilot quality delta (zero inference).** Default scoring excludes unparseable answers (`EXCLUDE_UNPARSEABLE_ANSWERS = True`, `scripts/benchmark/debug_scorer.py:161 @5d4ad2c0`; a stale comment at `scripts/autopilot/eval_tower.py:5972` still says False), and `parse_failure_count` is journaled beside `quality` (`eval_tower.py:5995-6003`), so no ITT counterpart exists. Add the ITT quality (an unparseable answer counts as a failure) next to the exclusion-based quality in the eval report and correct the stale comment; flag any delta whose sign or significance differs between ITT and per-protocol; and require a stored-output re-score with a second independent scorer before a scorer-dependent delta is acted on (`intake-2171#04`, `intake-2171#06`). ✅ 2026-10-21
  - 2026-10-21 (noninf-gates) partial result. `EvalTower._aggregate` now adds `details.quality_itt`, `details.itt_denominator`, `details.itt_unparseable_counted_as_failure` beside the per-protocol `quality` (epyc-orchestrator `ea8c7338`); the ITT denominator is n_scored plus unparseable answers, capped by the excluded `scoring_failed` count. The stale comment at `eval_tower.py:5972` now states `EXCLUDE_UNPARSEABLE_ANSWERS` is True. `src/autopilot_core/itt_quality.itt_delta_flag` flags a delta whose sign or |z| >= 1.96 verdict differs between ITT and per-protocol and sets `requires_second_scorer_rescore`. Tests: `tests/unit/test_gate_replays_and_itt.py`; 95 related unit tests pass.
  - 2026-10-21 (noninf-gates) follow-up (epyc-orchestrator `3d8830ee`): `itt_delta_flag` is wired into the AutoPilot quality-delta report path, `self_criticism.generate_self_criticism` (its `keep_revert_reasoning` text is the journaled quality-delta report); it appends the ITT delta and a SCORER-DEPENDENT warning, never changes keep/revert. The reference is the previous same-species journaled trial's `details`, because the baseline object carries no counts. Write side: `details` is journaled verbatim, so every new row already carries `parse_failure_count` (written since the 2026-09-24 TD-21 work) plus the new `quality_itt` keys; a test pins the key set. The second-scorer rescore stays a process rule carried by the `requires_second_scorer_rescore` flag, not an implemented rescorer.
  - Not done: the delta flag is not yet wired into a live report, and no historical delta can be flagged, because 0 of 1372 journal rows carry `parse_failure_count` (the field postdates them). The second-scorer stored-output rescore is a process rule carried by the flag, not an implemented rescorer.
- [x] **EV-19 — Scorer self-check on gold answers, per suite (zero inference).** Before any scorer-dependent delta is acted on, run each eval suite scorer on its own reference answers and report the fraction scored wrong, per suite, beside EV-18 (read-only, CPU). Verifier validity bounds every pass rate (intake-2274#record). Acceptance: a per-suite table of gold-self-score failures, and each suite with a nonzero rate flagged in the eval report header. Estimate: 0.5 day. ✅ 2026-10-21
  - 2026-10-21 (dpf-gates) result (epyc-orchestrator `44d63a0b`). `src/autopilot_core/gold_self_check.py` + `scripts/autopilot/gold_self_check.py`: the real scorer is run on each suite's gold (bare, then inside 8 answer wrappers; stride sample of at most 300 per suite; llm_judge and code_execution rows are not checkable without a model or code run). Table: `data/autopilot/gold_self_check.json` (36 suites). Nonzero: mmlu_pro 54/300 (18.0%), livecodebench 300/300, tulving_episodic 119/300 (39.7%), real_suite_v1 3/38 (7.9%). Suites with zero checkable rows print `-`, not 0. The flag reaches the quality-delta report header via `self_criticism` only when a report exists and flags a suite the eval used. Tests: `tests/unit/test_ev19_gold_self_check.py` (6 pass).
  - EV-19.1 `- [x]` Corpus fix: mmlu_pro rows whose gold is a letter I or J but whose `scoring_config.choices` is empty (54 of 300 sampled) are refused by the scorer, so they are excluded from quality; repair the corpus join or drop the rows, then re-run `gold_self_check.py`.
    - 2026-10-21 (corpus-fix-ev19) EV-19.1 fixed at source: cause was `scoring_config={}` on all 12,032 live-pool mmlu_pro rows (2,053 with gold I/J, not only the 54 sampled); PRB-T4 adapter fix (research `52595b9ba`) now reaches a refreshed pool with `choices` + `choice_labels` A-J. Full-pool self-check 0/12,032 wrong. LIVE SWAP PENDING operator era decision (same pool as EV-19.3).
  - EV-19.2 `- [x]` Corpus fix: tulving_episodic rows with an empty gold list (`[]`, nb_gt 0) score false under f1_list even for a correct 'none' answer (119 of 300 sampled); give them a scorable none-answer rule or exclude them, then re-run.
    - 2026-10-21 (corpus-fix-ev19) EV-19.2 resolved: self-check artifact, not a corpus defect. The 182/456 empty-gold rows are genuine no-match controls; the correct answer `None` already scores true (the self-check scored the literal string `[]`). WORDING CORRECTION: the item text "score false even for a correct none answer" is wrong. Fixed in the self-check (`render_gold`, SELF_CHECK_VERSION 2): tulving 0/456 wrong. Separate open question for the operator: the f1_list extractor accepts only a bare `None`; `- None`, `None.`, `Answer: None` score false.
  - EV-19.3 `- [x]` Corpus fix: livecodebench (300 of 300 sampled) and real_suite_v1 (3 of 38) rows carry a substring oracle on code rows (needle `def`) that the scorer itself refuses (`rebuild the pool so the row carries an executable code_execution oracle`); rebuild those rows with executable oracles, then re-run.
    - 2026-10-21 (corpus-fix-ev19) EV-19.3 fixed at source: livecodebench rebuilt to 704 rows with executable oracles (1,656 without a validated oracle EXCLUDED, reason `no_validated_oracle`); real_suite_v1 YAML 1.0->1.1 (0007 executable oracle; 0006, 0034 marked not scorable). Re-run on the corpus-ev19-20261021 pool: 0 wrong. Orchestrator `c153f975`, research `795cf9626`. LIVE SWAP PENDING operator era decision: the live `question_pool.jsonl` still carries the defective rows; the fixed pool is `/mnt/raid0/llm/tmp/corpus-fix-ev19/question_pool.corpus-ev19-20261021.jsonl`, sha256 `f8b536632b0d95feee339333f46247125def384b6d36d65b39711155825d7f0a`.
  - 2026-10-21 (corpus-fix-ev19) HISTORICAL SCORES ARE NOT EVIDENCE: journaled livecodebench scores (912 trials, 2026-05-27..2026-08-09) are INFLATED (vacuous `def ` oracle, 764 of 912 at the 3.0 cap) and mmlu_pro scores (40 trials, 2026-07-26..2026-08-09) are DEFLATED (17.1% of rows, gold I/J, could never pass); real_suite_v1 (361 trials) carries a small upward bias (3/50 rows) and tulving_episodic (43 trials) is unaffected. No conclusion should rest on them. Not rescored. Full table: `epyc-orchestrator/data/autopilot/corpus_fix_ev19_history_impact.md`.
  - [x] **EV-19.4 - swap the live question pool to `corpus-ev19b-20261021`** (sha256 `73a2ed5aa87c38e554c818aff4b8c6dd865621c6134b4abacebfa9070a818f8b`; = `corpus-ev19-20261021` f8b53663 + 22 ARC rows) with a ratified instrument-era row.
    - 2026-10-21 (ev19-era) LIVE SWAP DONE: `epyc-inference-research/benchmarks/prompts/question_pool.jsonl` 64218c27 -> f8b53663 (15:19:42Z) -> 73a2ed5a (16:13:44Z), atomic `mv -T`, AutoPilot idle (paused, no in-flight trial, no process). Backups beside it: `question_pool.jsonl.pre-corpus-ev19-20261021` (64218c27) and `.pre-corpus-ev19b-20261021` (f8b53663), each with a `.sha256`. Extra defect found and fixed in-era: 22 `thinking` ARC rows with numeric labels were unscoreable; re-derived (research `2d3a7cbe8`). Full-pool self-check v2: 0 wrong, 0 scorer_error. ERA ROW PENDING OPERATOR RATIFY (human-only registry): `bash /mnt/raid0/llm/worktrees/ev19b-root/scripts/operator/ratify_ev19_corpus_era_20261021.sh --apply` (root `203132c06`, dry-run validated; era `E20-eval-corpus-ev19-quality`). The era is NOT recorded until that runs; AutoPilot `active_instrument_eras` still E16 until its next start.
    - era E20-eval-corpus-ev19-quality RATIFIED by operator, orchestrator 04685908 (2026-10-21)
  - [x] **EV-19.5 - tulving f1_list extractor: accept `- None`, `None.`, `Answer: None` on empty-gold controls.**
    - 2026-10-21 (ev19-era) DONE (operator "Accept variants"): `debug_scorer._score_f1_list` normalises the whole reply (leading bullet, `Answer:` prefix, trailing punctuation, case/whitespace) before the abstention fullmatch; `None` inside a longer answer or naming events still fails. Orchestrator `dd5bcf06`; `tests/unit/test_debug_scorer_ev19_none_variants.py` (21 accepted, 11 rejected) + neighbours 98 passed. Full-pool self-check v2 on the ev19b pool: tulving 0/456 wrong, all suites 0 wrong. Scorer identity = the era row (no version constant exists); the research repo adapter `score_f1_list` is unchanged.
- [x] **EV-20 — Per-task paired path for evaluate_skill_efficacy with a zero-growth readout.** Extend `evaluate_skill_efficacy` (scripts/autopilot/skill_efficacy.py) with an optional per-task paired-outcome input returning c, b, exact McNemar p and the rescued and regressed task lists, suite-level path and default-off wiring unchanged. Also return b_candidate and b_incumbent and the report-only field would_pass_zero_growth_budget (b_candidate not above b_incumbent and c_candidate above b_candidate), with no change to accept or reject. The incumbent arm needs at least the replicate count from the M-29 replicate floor and b_incumbent is reported as a mean with its replicate SD; errored or timed-out samples are excluded from both arms (pairwise drop) or counted in both, never one (intake-2236#record, intake-2266#record). Fixtures: the 18-cell table of intake-1321#record and the pass/fail matrix on the intake-1354#record page. Pure functions, zero inference. Acceptance: unit tests reproduce the fixture p-values and the pairwise-drop rule; default behaviour byte-identical. Estimate: 1-2 days. ✅ 2026-10-21
  - 2026-10-21 (dpf-gates) result (epyc-orchestrator `44d63a0b`). `paired_task_readout` and `mcnemar_exact_p` added to `scripts/autopilot/skill_efficacy.py`; `evaluate_skill_efficacy` takes optional `per_task_without/with/incumbent` and attaches a report-only `.paired` (excluded from repr and equality; accept/reject unchanged, default calls identical). Returns c, b, exact McNemar p, rescued and regressed lists, b_candidate, b_incumbent mean and replicate SD, and `would_pass_zero_growth_budget` (None when the incumbent has fewer replicates than the floor). Errored samples: pairwise drop across all arms, or counted as fail in all arms. The default floor is 2 replicates (the minimum that yields an SD); the M-29 replicate floor has no number filed, so the caller passes the M-29 floor as `min_incumbent_replicates`. Tests `tests/unit/test_ev20_paired_task_readout.py` (38 pass) reproduce the 18-cell Table 2 totals (122/81, 431/243) and the reported p-values (1.000, 0.572, 0.078, 0.039, 0.008) and the intake-1354 page p-values (3.6e-5, 0.42, 4.2e-7); 97 skill-efficacy tests pass.

## Research intake 2026-10-22 — SLQ / IST-DASLab / kaitchup Qwen3.8-27B SLQ (intake-2461..2493)

Source: research intake session intake-ist-slq-20261022, Stage-3 plan `/mnt/raid0/llm/tmp/intake-ist-slq-20261022/stage3/STAGE3_PLAN.md` (sha256 db108374cd1bd164e5baaac2586b9d3abf26daaba46aec4085192e4b0c0232ad); operator ruling 2026-10-22 approved a subset. Trigger prose and knowledge notes from that plan are still pending the operator and are not filed here.

- [x] **EV-DEGR1 — Seeded, zero-discordant-safe one-sided degradation tests as an additive paired_stats diagnostic (intake-2484, intake-2491).** (filed 2026-10-22 via research intake, operator-approved 2026-10-22) New module in epyc-orchestrator scripts/autopilot, re-implemented from the paper, not from the CC BY-NC repo: pooled exact one-sided binomial on the sum of b over the sum of b+c, Fisher over per-suite exact p, max-drop Monte Carlo with a fixed seed, and an any-of-three flag; consumes paired_stats QuestionOutcome pairs and emits beside mcnemar_verdict without a new P-PAIRED verdict string. Tests: a b = c = 0 suite contributes p = 1.0 (no exception, never 0.0), single-suite Fisher equals pooled, and the E7c regression b = 61, c = 58 gives one-sided 0.4273.

  *EV-DEGR1 done 2026-10-22 (workspace-58).* epyc-orchestrator `scripts/autopilot/degradation_stats.py` + `tests/unit/test_degradation_stats.py`, commit 0993affc on origin/main. Pooled exact one-sided binomial, Fisher over per-suite exact p, seeded max-drop Monte Carlo (seed 20261022, 20000 sims), any-of-three flag; `degradation_from_vectors` consumes paired_stats QuestionOutcome vectors. Additive: paired_stats.py untouched (no gitnexus impact needed - no existing symbol modified), no new P-PAIRED verdict string; test_paired_stats.py still passes. Tests (9): b=c=0 suite -> p=1.0, empty/tiny-n, single-suite Fisher == pooled, E7c b=61,c=58 -> 0.4273, seed reproducibility, power arithmetic, CLI. Re-implemented from the paper (intake-2484#00, intake-2484#03), not from the CC BY-NC repo (intake-2491#record).


### EV-15d retained-mass contract — 2026-10-31

Orchestrator `79230233c04b1e24b8736640d70e290825612880` adds per-call retained-mass capture and a refusal floor to the existing paired distributional consumer. A versioned v2 plan binds the ordered K=9 score-token IDs and explicit floor; each call records missing IDs as zero mass and refuses a below-floor or zero-mass judgment before aggregation. Legacy v1 mathematical vectors preserve their original manifest, request IDs and output shape and carry no native mass warrant. Seventy focused tests, accepted/refused CLI cases, Ruff and diff checks pass; durable validation and admitted R6 resource evidence are committed under `artifacts/audit/ni-ev15d-retained-mass-20261031/`. This closes the software contract only. Native position/template checks, original numeric goldens and live judgment validation remain separate open asks. [no-belief: offline software controls; no native scoring or quality claim]

## Track: bulk-inference-campaign
<!-- gate: none -->

> Folded from `handoffs/active/bulk-inference-campaign.md` @ `c4b6d1388716` on 2026-11-02 (BRF-T1-F2, route 1a, operator D1/D5; retired row EVL-07 → EVL-14). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Bulk Inference Campaign — active backlog (Packages G–K)

**Status**: active - live backlog is Queue 2 consolidated quiesce-window measurements, Queue 3 restart-bundle evidence accrual, standalone model-batched windows, and Package I frozen after the DAR-1 replay failed its reopen gate. J7/DCP remains default-off after the first live A/B worsened latency; K-MEM-1 completed its first Tulving baseline and no longer blocks the next throughput-sensitive lane; frontdoor G11 run `20260620_035613`, worker G11 run `20260620_062750`, and architect G10 run `20260620_081041` are packaged as raw-response/throughput evidence and deterministic-F1 scored. G12 tier calibration is complete: deterministic AA-Omniscience 4-class scoring was accepted for role-tier recalibration only, and orchestrator `d0e082a7` updated production factual-risk tier multipliers to `0.727978/0.824178/1.0`; factual-risk mode/canary/enforce decisions remain separate telemetry gates. The v6 contention-matrix age blocker was cleared on 2026-06-27 by refreshing the full/primary pair layer in orchestrator `526ba3a2`; Queue 3 baseline mutation should now fail or pass on clean evidence, not stale topology metadata.
**Created**: 2026-04-06
**Updated**: 2026-07-14 - backlog ROI audit: added K-LCM-1 (LongCoT-Mini calibration, intake-386/RE-4) to the standalone clean-window queue and annotated the K-ROPE-1 `worker_general` gate as unverified-stale (2026-06-20 claim; re-attest against the Gemma4-MTP launch recipe before repeating). Prior update 2026-06-20 - K-MEM-1 run `20260619_141212` completed and was packaged in `epyc-inference-research` `b6edc64`; research `9e63af0` fixed Tulving ground-truth parsing and rescored it. The production/default-expert run scored 456/456 Tulving questions with avg F1 `0.4309`, Simple Recall **`0.5684`** (scorer v2, M-12e research `dcb769c1`: over the 366 `get=="all"` questions with event-count bins; the originally quoted `0.5530` was scorer v1, computed over all 456), Chronological Awareness `0.1593` (unchanged under v2; 37/45 tau questions now fail closed for partial coverage), and avg decode `17.27 t/s`; the runner log ended `448 completed, 8 skipped, 0 errors` because the first 8 rows were reused from the corrected resume. This is a mixed baseline with usable lexical entity/time/location recall, weak event/detail and chronology, and zero-answer hallucination failure; it is not a memory-routing promotion signal. Research `2eb94f8` adds a targeted 120-row follow-up manifest for zero-answer abstention, event-content/detail recall, and chronology-order repair. Frontdoor G5 short-m@k clean-window evidence is packaged in research `7e9f67f`. Frontdoor G11 clean-window run `20260620_035613` first exited after `24:57` with `26 completed`, `0 skipped`, and `1800 errors`; triage found the quality rows used the subprocess path without built `completion`/`lookup` binaries, while the successful `moe4_lookup`/`moe6_lookup`/`moe8_lookup` files were speed-only telemetry. Research `7d27597` makes generated AA/clean-window suite commands add `--server-mode --skip-speed-tests`; the corrected rerun completed and is packaged in research `587c6cd` with `600/600` non-blank rows for baseline, moe4, and moe6. Research `92a5602` adds deterministic-F1 AA labels and the factual-risk report view: baseline accuracy `0.1117`, hallucination rate `0.5610`, OI `0.2753`; moe4 accuracy `0.1117`, hallucination rate `0.5666`, OI `0.2725`; moe6 accuracy `0.1233`, hallucination rate `0.5608`, OI `0.2812`. Worker G11 run `20260620_062750` completed with canonical preflight `data/preflight/2026-06-20_062737.json` and is packaged/scored in research `32f2c27`: baseline accuracy `0.1433`, avg F1 `0.2280`, hallucination rate `0.6829`, OI `0.2302`, avg decode `52.63 t/s`, and label counts `86` correct / `351` incorrect / `110` partial / `53` not attempted. Architect G10 run `20260620_081041` completed against resident `architect_general :8083` and is packaged/scored in research `b91d16c`; the combined factual-risk report is `ready_for_tier_update`, and orchestrator `d0e082a7` applied the measured tier multipliers. Research `7d05d03` adds X-MAS constrained-policy A/B to the clean-window manifest after the earlier DS-E1 entry; research `7d2dade` adds Queue-2 E2 plan generation and E1 batched-decode sweep entries. Current generated manifest state is 27 entries, 21 ready, and 6 blocked under observed live ports/contexts. K-ROPE clean-window evidence has valid 4K/8K cells plus valid 16K frontdoor/ingest cells; exact-boundary rows and the current `worker_general` MTP serving path remain blocked. J7/DCP launch-code provenance is satisfied, but the first live A/B does not support enablement.
**Categories**: evaluation, inference, coordination
**Priority**: HIGH
**Depends on**: Package A results (complete)
**Related**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md), [`research-evaluation-index.md`](research-evaluation-index.md), [`pipeline-integration-index.md`](pipeline-integration-index.md), [`user-facing-harness-index.md`](user-facing-harness-index.md), [`inference-research-index.md`](inference-research-index.md), [`cross-role-nway-contention-matrix.md`](../completed/cross-role-nway-contention-matrix.md)

---

#### Problem

14 inference-dependent tasks are scattered across 5 domain indices. Running them independently requires 14 separate stack launches with 5-15 minutes of NUMA warmup each — over 3 hours of dead time before any evaluation begins. Many tasks share the same stack configuration and can collect cross-task telemetry simultaneously via feature flags.

**Consolidation**: 14 tasks → 4 optimized runs. Each run maximizes the number of tasks resolved per inference session by piggybacking telemetry collection, A/B comparisons, and eval passes on shared model instances.

---

> **⚡ 2026-07-17 — Execution source-of-truth while the consolidated inference-batch is active:** `/workspace/coordination/inference-batch/manifest.yaml` (52 entries incl. these queues + the reviewer-plane RCP window) is the single machine-executed manifest; the operator's `/loop` session is the SOLE writer of its `ledger.jsonl` + checkbox flips (see `coordination/inference-batch/LOOP_PROTOCOL.md`). The RCP-W1/W2/W3 rows staged in this handoff's 2026-07-17 section, DS-E1, K-ROPE, X-MAS-monitor, K-LCM-1 (LongCoT-Mini), and the Queue-2 items are SUBSUMED as manifest entries (each `also_flips` back to its owning checkbox here). Do NOT run a manifest entry from any other session — single-writer discipline.
>
> **⚡ 2026-07-17 update — audited + repaired, loop-ready:** an adversarial command-audit found the authoring agents had fabricated ~30 `execution.command` strings (nonexistent runners/flags). A 5-pass re-audit confirmed the damage was localized to leaf commands (provenance/preconditions/graph/committed-code all ground-truthed clean). Repair: 8 genuinely-missing non-inference runners built + tested (109 tests; orchestrator `d9f0d148`, research `0d80923`), ~15 entries re-pinned to real commands, ~15 marked as honest `BUILD-*` gates, `op-bundle.md` gate registry reconciled (A–F + 12-item build-backlog) with 4 pre-formed Escalation decision blocks. Manifest re-compiles 52/52 valid. Every entry now has a real command or an honest gate — no fabricated runnable commands remain.

#### Current State (2026-06-12) — Three-Queue Structure

The 2026-04 campaign (Packages A–F) is complete/overtaken and archived (see *Completed* below). The cross-role N-way matrix + within-role placement SM (J1/J4a-J4c/J4/J5) are CLOSED (see the compaction note in Package J). The remaining inference-gated backlog is organized into three queues plus standalone windows and a frozen block, per the Fable 5 portfolio pass. Per-task detail is preserved in the Package G/H/I/J/K sections below — this is the dispatch view.

##### Quiet-window batch queue (refreshed 2026-07-06)

Use this when AutoPilot is deliberately stopped. The items below are ordered to
maximize handoff progress without rediscovering command syntax. E2 activation /
rollback is closed and DS-E1 is already decision-ready, so the active batch
starts with the remaining E1 dense-control / P-BENCH-3 sweep. J12, A9,
real_suite_v1, and ODL can share an AutoPilot-off window if they do not compete
for the same stack reload; J12 and A9 are now closed for the current window,
N12 is the controlled stop/start placement check, and the ODL structural
manifest/probe evidence for 2026-07-06 is already recorded. The 2026-07-06
batched-decode checkpoint captured the full `qwen36_q8_0` NP ladder and
intentionally interrupted the 27B dense-control tail after a long-running
`np=1` probe so the stack could be restored cleanly. The 2026-07-06
real_suite_v1 clean-window run also completed in this window, packaged
successfully, and came back as a hard negative (`0/50`), so the row remains
open even though the decision-grade artifacts now exist.

| Order | Item | Owning handoff | Why quiet window | Can-run-together | Expected artifacts |
|---:|---|---|---|---|---|
| 1 | E1 dense-control / P-BENCH-3 batched-decode sweep | [batched-decode-measurement.md](numa-placement-and-contention.md#track-batched-decode-measurement), [inference-research-index.md](inference-research-index.md) | Needs AutoPilot stopped plus a clean host-health/reboot window. | Do not share with live-stack reloads or other throughput-sensitive measurements. | P-BENCH-3 `-np 1,2,4,8,16` sweep artifacts under `epyc-inference-research/data/batched_decode/<run_id>/` with `summary.csv`, recommendations, server logs, and stop events. 2026-07-06 checkpoint: `qwen36_q8_0` NP ladder complete; `qwen36_27b_q8` dense-control tail intentionally interrupted after `np=1`; stack restored to `STACK READY`. |
| 2 | real_suite_v1 EvalTower ledger collection | [frontier-f1-real-task-corpus.md](../completed/frontier-f1-real-task-corpus.md), [evidence-plane-ledger-and-sequential-verdicts.md](autopilot-program.md#track-evidence-plane-ledger-and-sequential-verdicts) | Clean AutoPilot-stopped window needed for decision-grade real-task ledger evidence. | Can share the same AutoPilot-off window as the PDF probe if the live stack is otherwise stable. | Raw JSONL under `/mnt/raid0/llm/tmp` plus packaged `orchestration/reports/real_suite_v1_eval_<UTC>/{question_ledger.jsonl,summary.json,summary.md}`; the bounded `--allow-partial --n 12` smoke is now packaged at `real_suite_v1_eval_20260706T145900Z_n12` (7/12 correct, 2 timed out), and the full `--apply --confirm-clean-window --n 50` run completed at `real_suite_v1_eval_20260706T192007Z` with `0/50` correct, `0.0` quality, and backend-unavailable/no-progress failures. W3 acceptance remains open, but the decision-grade ledger artifact now exists. |
| 3 | ODL structural/table-heavy PDF corpus probe | [opendataloader-pipeline-integration.md](knowledge-pipelines.md#track-opendataloader-pipeline-integration), [pipeline-integration-index.md](pipeline-integration-index.md) | Needs an idle window to load the structural corpus, exercise the hybrid sidecar path, and keep results attributable. | Can share with real_suite_v1 if the ODL sidecar/stack is isolated; do not pair with stack-down maintenance. | 2026-07-06 structural manifest and 27-PDF probe recorded; live hybrid sidecar now returns `27/27` success on the same corpus with median `1510.743 ms / 1.000`, so the remaining work is benchmark-backed comparison and routing policy, not sidecar viability. |
| 4 | N12 live `numa_maps` observability refresh | [numa-private-weights-quarter-roles.md](../completed/numa-private-weights-quarter-roles.md), [inference-research-index.md](inference-research-index.md) | Needs a controlled stop/start plus live `/proc/<pid>/numa_maps` verification on the current worker quarters. | Pair only with other stop/start maintenance on the same model stack; do not overlap with throughput-sensitive sweeps. | Strict locality JSON artifact with live placement fractions and `--require-memory-locality` pass/fail. |
| 5 | W8/Fable readiness refresh | [evidence-plane-ledger-and-sequential-verdicts.md](autopilot-program.md#track-evidence-plane-ledger-and-sequential-verdicts), [autopilot-continuous-optimization.md](autopilot-program.md) | AutoPilot stopped only; report-only. | Can run with the other report-only work after the live stack is quiesced. | `orchestration/reports/w8_promotion_trajectory_20260706Tcurrent.{json,md}` and `orchestration/reports/fable5_gate_report_20260706Tcurrent.{json,md}`; current blocker summary remains: phase heartbeat stale, W6 gaming alarm triggered, tool-use activation attention-level, with stale_accumulating replay pressure still present. |

##### Queue 1 — offline-now (≈0 llama-hours; run today alongside the live autopilot)
- ✅ **J7 DCP-6 offline replay + DCP-6a repair CLOSED/PREPARED; first live A/B does not support enablement** — launch-code provenance is satisfied and orchestrator `56a72f6` packages the first 3-off/3-on live run. Result: 6/6 HTTP 200, zero errors, all delegated, fewer generated tokens with DCP ON, but worse p50 latency (32.628s vs 20.219s). Orchestrator `7c84f102` closes the no-inference runner-prep tail: default `dcp_j7_ab.py` execution is now schema-only stub mode, live inference requires explicit `--real --host-quiet-confirmed`, and the current stub artifact is `benchmarks/results/runs/dcp_j7/stub-20260706T033205Z/`. Keep `dcp_pre_assembly` off; rerun only for a larger quality-scored falsification after operational attestation cleanup.
- ✅ **DAR-1 regret replay CLOSED 2026-06-12** — current-traffic replay over 2026-06-05..2026-06-12 analyzed 12,057 routing decisions, matched 11,249 outcomes, found 8,145 regret-identifiable decisions, and measured 0.00% identifiable mean regret versus the >=5% reopen gate. Package I and broader learned-routing expansion remain frozen. Report: `epyc-orchestrator/orchestration/reports/dar1_regret_replay_2026-06-12.md`; code/telemetry landed in `epyc-orchestrator` `1dfbc22`.
- ✅ **K-RAG-1 formal K7 sweep CLOSED 2026-06-13** — final 70-case pool over the fresh K7 index produced 420 rows with `ok=true` and no missing evidence files. Safety/default candidate is `recency_w0.3_s90` (recall@10 0.6167, 0 missed-all-evidence cases); aggregate winner `recency_w0.1_s90_rerank_w0.3` reached recall@10 0.6298 but missed 3 all-evidence cases, and the 1.31pp gap is below the declared 2pp noise floor. Temporal recency is validated; cross-encoder rerank stays opt-in for first-rank/recall@3-biased consumers.
- ✅ **J13 P17.BT-3 analysis CLOSED 2026-06-12; cleanup landed 2026-06-13** — 341 rich/stagnation-fired trials and 75 logged BT-disagreement events satisfy the sample-size gate, but the journal does not persist the BT top trial ID, the hypervolume-top trial ID, or whether the planner followed either seed. Available proxy outcomes do not justify P17.BT-4 (`current frontier`: 2/75 BT-disagreement events vs 9/266 no-disagreement rich events; cluster-start next-10 frontier: 1/7 vs 8/34 thinned no-disagreement). Verdict: do not queue peer-judged BT. The cosmetic `bt_tiebreak_hint` rich-prompt block was removed while AutoPilot was paused in orchestrator `b8c0611`; the offline/shared BT helper remains.
- ✅ **J9 HLE-4 analysis CLOSED 2026-06-12** — 580 metric-bearing trials from immutable snapshot `/mnt/raid0/llm/tmp/autopilot_journal_snapshot_1781290411.jsonl`. Verdict: no Pareto co-objective promotion from the current rule metrics. `execution_fidelity` and `planning_stability` separate keep/revert but mostly mirror existing quality/reliability/safety verdicts; keep them diagnostic/advisory. `feedback_interpretation`, `memory_coherence`, and `recovery_rate` stay dashboard-only because of low variance, constant score, or 99.3% missingness. Any future J9 promotion waits for N2 per-question ledgers/sequential verdicts and redesigned evidence.
- ✅ **J12 clean-window probe CLOSED 2026-07-06** — registry-driven auto-population of `chat_template_kwargs` exists and the production `LlamaServerBackend` `/v1/chat/completions` path honors the kwarg (`tests/unit/test_registry_chat_template_kwargs.py`, `tests/unit/test_llama_server.py::...chat_template_kwargs`, `tests/unit/test_chat_completions_roles.py` -> 6 passed). Clean-window J12 report `epyc-orchestrator/orchestration/reports/j12_think_loop_probe_20260706T143621Z/` found frontdoor `15/15`, architect `14/15`, and `0` empty outputs / errors / `<think>` leaks / known wait-reference loops / repetition loops. THINK-ABL-1 remains Queue 2.
- ✅ **G12 factual-risk tier calibration CLOSED 2026-06-20** — deterministic AA-Omniscience 4-class scoring was accepted for role-tier recalibration only; orchestrator `d0e082a7` updated `_DEFAULT_ROLE_TIERS`, default config, and live `classifier_config.yaml` to measured multipliers. Do not reopen G12 for LLM-judge scoring; mode/canary/enforce decisions remain separate telemetry gates.

##### Queue 2 — ONE consolidated quiesce window (t1000 or operator SIGTERM; ~28–31h; one attested reload serves all)
Ordered manifest (one reload, then everything rides it):
1. **Reload with declared production env** (fixes test-defaults; sets EVERY flag this window needs in launch env) **+ per-worker attestation** — orchestrator `4bbf1163` adds the concrete runbook and local `attest_orchestrator_workers.py` process-env proof, paired with `attest_flags.py`; live read-only default-poll checks saw all six API workers with no feature/env diffs. This is the only route around the 1-of-6 `POST /config` propagation bug. Rerun both attesters after the Queue-2 reload before trusting any flag.
2. **E1 dense-control / P-BENCH-3 batched-decode sweep FIRST** (findings-06 — E2 activation/rollback is closed; the remaining batched-decode item is the direct `-np 1,2,4,8,16` sweep under a clean host-health window).
3. **Shape-keyed flag-on bracket** (`CROSS_ROLE_DISJOINT_PLACEMENT=1` live → verify env → multi-role fan-out probe → `SHAPE_AWARE_CONTENTION=1` smoke → revert or `mark_epoch`).
4. **J2/J3** single-worker live migration probe (`--workers 1`).
5. **THINK-ABL-1** (best leverage/hour, +33pp class effect; real ablation needs a non-no-op suppressor at fixed non-truncating `max_tokens`, same tasks both arms). **J12 clean-window probe closed 2026-07-06**: with AutoPilot stopped, `scripts/benchmark/j12_think_loop_probe.py --roles frontdoor architect_general --confirm-clean-window` produced durable report `orchestration/reports/j12_think_loop_probe_20260706T143621Z/`; frontdoor `15/15`, architect `14/15`, and `0` empty outputs / errors / `<think>` leaks / known wait-reference loops / repetition loops. The architect jinja flip has no J12 revert trigger. The remaining ablation is THINK-ABL-1 for ingest with a non-no-op suppressor.
6. **J15** MD-9 deep_research sentinel A/B.
7. **J7** DCP-6 inference half follow-up. First live run is packaged in `epyc-orchestrator` `56a72f6` and does not justify enablement; keep `dcp_pre_assembly` off. Orchestrator `7c84f102` validates the no-inference stub/schema path and makes it the default; use `scripts/benchmark/dcp_j7_ab.py --real --host-quiet-confirmed` only for larger/quality-scored falsification or reruns after broad operational attestation cleanup.
8. **J10** URE shadow env-flag rides the reload free (passive).
9. **J16** RI-ITG-1 ingest-triviality A/B — **only if** N2 per-question ledger landed AND its leak premise re-verified against the live routing path.

##### Queue 3 — restart bundle (live code; collect clean vector history)
- **Per-question eval ledger + sequential verdicts** (findings-01c) — the keystone; everything below gates on it. Ledger W1/W2 are live in the current orchestrator lineage (`22a3874a`, `9f6fc8e`); W3 pure sequential-verdict math is live at `7e6ac9c`; W4 default-off safety-gate/update-baseline wiring and W7 game-layer hardening are landed. Authority remains disabled until readiness passes. The 2026-06-28 strict fold after the E5/v6 restart reports archive authority aligned, baseline fold ready, and sequential cutover ready, but W6 audit cutover is now era-fenced by `pareto_exclude_before_ts`: `100` pre-v6 audited rows are fenced out, current-era W6 has `9/30` trusted audited rows, and the current-era gaming alarm is still triggered. The first post-pool restart missed the W4/W6 env and was stopped at trial `1004`; continue current-era W6 collection under the corrected live `--max-trials 2000` AutoPilot run with `AUTOPILOT_SEQ_VERDICT=1` and W6 audit shadow flags; do not enable sequential verdict/baseline authority until strict readiness passes with `--require-seq-cutover --require-w6-audit`.
- **J11/BSV-2** behavior-signature accept gate — observe-only diagnostics are live (`fd84655e` + `d89b4a9`), same-qid paired reporting now accepts both journal rows and standalone EvalResult-like artifacts (`0943e7c0` + `5b29eead`), and final accept gate remains flag-isolated behind `AUTOPILOT_BSV2_ACCEPT_GATE`.
- **K-SKILL-1** skill-efficacy gate (flag `AUTOPILOT_SKILL_EFFICACY_GATE`) — default-off accept-path wiring landed on the live branch at `924ca50`; keep it flag-isolated from J11 for attribution until N2 W4 cutover.
- **Current runtime evidence**: operator-conservative quarantine covers pre-clean-epoch artifacts `#786-#797`; `#798` is killed-startup audit. Clean vector collection has advanced through the patched trial-888 denominator repair, but readiness is still sample-size blocked. Do not use raw paired-stats counts without filtering quarantined/killed rows. **2026-06-27 v6 matrix unblock:** trial 972 exposed baseline-update refusal on `matrix_status=stale`; topology hash still matched (`df373c79cc4af06f`), but the matrix age exceeded the 30-day certification window after the v6+iqk stack cutover. Orchestrator `526ba3a2` refreshed the measured full/primary pair layer against the live v6 stack, preserved curated same-role/N-way policy, removed the two stale unknown pairs, and passed `check_contention_matrix_fresh.py`. AutoPilot was paused, the long trial 973 worker was terminated during the refresh window, and the post-refresh restart recovered it as `AUTOPILOT_KILLED` before resuming at trial 974 with `--max-trials 2000`.
- Then **H5/EV-4** calibration baseline against the **redesigned** tower (K-EVAL-1 folded into H5 — single owner; see the Package K note).

##### Standalone model-batched windows (~27h; group by model so each GGUF loads once)
- ✅ **K-MEM-1 Tulving on `ingest_long_context` completed/scored 2026-06-20** — run `20260619_141212` used `--server-mode --skip-moe-reduction` so evidence reflects production/default GGUF expert settings. Raw artifacts were packaged in research `b6edc64`; corrected score artifacts and `tulving_failure_modes.md` landed in research `9e63af0` after fixing Tulving ground-truth parsing for NumPy-array/list-repr answers. Scorer result: `456/456` scored, missing ground truth `0`, avg F1 `0.4309`, Simple Recall **`0.5684`** (scorer v2, M-12e research `dcb769c1`: over the 366 `get=="all"` questions with event-count bins; the originally quoted `0.5530` was scorer v1, computed over all 456), Chronological Awareness `0.1593` (unchanged under v2; 37/45 tau questions now fail closed for partial coverage), avg decode `17.27 t/s`. The benchmark log ended `448 completed, 8 skipped, 0 errors`; the eight skipped rows are the reused corrected-resume rows. Research `2eb94f8` adds `data/package_k/tulving_followup_20260619_141212_manifest.jsonl` and `summary.md`: 120 ID-only rows split evenly across zero-answer abstention, event-content/detail recall, and chronology-order cases. Treat this as a mixed baseline and targeted repair slice, not a memory-routing promotion.
- **Current standalone lane** — K-MEM no longer blocks scheduling. Frontdoor G5 short-m@k clean-window evidence is now packaged in `epyc-inference-research` `7e9f67f` at `benchmarks/results/clean_window/short_mk_voting/frontdoor.json`: `status=complete`, `40` questions, `14/40` correct (`0.35` accuracy), GPQA `2/20`, MATH `12/20`, and no completion errors. Frontdoor G11 AA-Omniscience run `20260620_035613` was launched with canonical preflight pass records (`data/preflight/2026-06-20_035546.json`, `data/preflight/2026-06-20_035613.json`) and full-affinity caveat limited to absent old parallel replicas; target `frontdoor :8070` was healthy/idle before launch. It first exited after `24:57` with `26 completed`, `0 skipped`, and `1800 errors`; `/mnt/raid0/llm/tmp/g11_frontdoor_20260620T035601Z.log` shows a completed speed sweep but no claim-grade quality aggregate. Triage root cause: the generated G11 command omitted `--server-mode`, so baseline/moe4/moe6 quality rows fell through to missing subprocess binaries (`completion`, `lookup`) and failed `600` rows each; the successful lookup sweep artifacts are speed-only telemetry. Corrected repair completed under the same run id with `--server-mode --skip-speed-tests --force --baseline-run 20260620_035613`; preflight `data/preflight/2026-06-20_043836.json` passed all gates with an uptime warning. Research `587c6cd` packages `frontdoor_baseline.json`, `frontdoor_moe4.json`, `frontdoor_moe6.json`, lookup telemetry, three preflights, and `summary.md`: all three quality configs have `600/600` non-blank responses and avg TPS `24.8823`, `25.9453`, and `25.7758`. Research `92a5602` adds `data/package_g/omniscience/frontdoor_20260620_035613_aa_omniscience.jsonl` (`1,800` rows), deterministic-F1 summary, and factual-risk aggregation report. Worker G11 then completed as run `20260620_062750` after canonical preflight `data/preflight/2026-06-20_062737.json`; research `32f2c27` packages `worker_general_baseline.json`, the scored JSONL/summary, and factual-risk aggregation report. Worker baseline scored `600` rows with accuracy `0.1433`, avg F1 `0.2280`, hallucination rate `0.6829`, OI `0.2302`, and avg TPS `52.63`. Research `1d80fca` added the guarded resident-server runner path needed to avoid double-loading the 122B model; architect G10 then completed run `20260620_081041` against resident `architect_general :8083` after canonical preflight `data/preflight/2026-06-20_081041.json`, and research `b91d16c` packages/scored it: baseline accuracy `0.1317`, avg F1 `0.2103`, hallucination rate `0.4971`, OI `0.3173`, avg TPS `11.05`, label counts `79` correct / `259` incorrect / `101` partial / `161` not attempted. The combined factual-risk report is `ready_for_tier_update`, and orchestrator `d0e082a7` applied the measured G12 multipliers; do not reopen G12 for scoring-policy work.
- **Clean-window manifest state** — `docs/data/clean_window_measurement_manifest.json` and commands historically grouped G10/G11, K-MEM-1, K-ROPE-1, G5, Queue-2 E2/E1, DS-E1 dynamic-stack KV measurement, and the now-run X-MAS constrained-policy A/B by model/window. Current readiness is 21 ready / 6 blocked across 27 entries under observed live ports/contexts after research `7d2dade`, but the active next-run filter now excludes closed E2 activation/rollback work and decision-ready DS-E1. Generated `run_benchmark_suite` commands now include `--server-mode --skip-speed-tests` so clean-window quality runs use the server path and do not re-run speed-only MoE/spec/lookup sweeps. The remaining batched-decode item is E1 as the direct P-BENCH-3 `-np 1,2,4,8,16` sweep, which still requires a clean host-health/reboot window for decision-grade claims; X-MAS is no longer a missing-run blocker after the 2026-06-21 `hold` result.
- **K-ROPE progress** — valid 4K and 8K clean-window cells exist for `frontdoor`, `architect_general`, and `ingest_long_context`; valid 16K cells exist for `frontdoor` and `ingest_long_context`. Exact-boundary rows are now blocked, and `worker_general` is blocked by the Gemma4 MTP 8072 serving/slot-state issue until reloaded/re-attested. *(2026-07-14 audit note: this worker-gate claim dates from 2026-06-20 and is unverified-stale — a Gemma4-MTP launch recipe now exists and MTP-refresh work is active; re-attest `worker_general` serving against the launch recipe before repeating the gate.)*
- **[declined: ws58 2026-11-03 content-review: merged into RE-4.3 — the full reference run IS the K-LCM-1 calibration run; RE-4.5 flips it on DONE_PASS]** **K-LCM-1 — LongCoT-Mini calibration run** (intake-386, audit RE-4, filed 2026-07-14): ~500-easy deterministic long-horizon reasoning suite on local models, one clean-window package. Adds a non-saturated suite exactly where EV-9 found production suites saturated AND tests the reasoning-compression premise (unbounded reasoning harmful) on our stack. Cross-ref: reasoning-compression.md L~368 prose note; scoring must be deterministic (no LLM-judge) per MEASUREMENT.md. **BLOCKED_PRECONDITION (verified 2026-08-13, mainB):** full run gated on the RE-4.2 non-saturation probe (`re4-protocol-redesign.md` §4, index row EVL-35) — frontdoor-only, two-phase, R=4096, 30 stratified rows, gate = overall accuracy ∈ (10%, 90%) + ~100% marker presence. RE-4.2 has **never run** (no probe artifacts anywhere); its own prerequisites — operator quiet-window, current v8/v9 topology re-attested, autopilot stopped — are operator-gated and the redesign note explicitly authorizes **no inference** ("Status: ACTIVE/GATED … no inference is authorized by this design note"). The v1 protocol floor-saturated (frontdoor 0/402, worker_general 0/307, quarantined `protocol_blocked/floor_saturated`); the v2 runner (`9323213d`) and entry (`…v2`) landed 2026-07-21 but the probe gate was never executed. Backlog queue confirms the gate: L87 dep = "clean window + RE-4 protocol repair", L18 = "clean-window package; RE-4 protocol gates". Runner requires live llama-server on role ports (frontdoor/worker_general) — a model-server inference window, not a region-lock bench. **Next action: run RE-4.2 probe in an operator-granted quiet window with re-attested topology; do NOT attempt the full run or flip this row before RE-4.2 is in-band (per RE-4.5: flip K-LCM-1 only on DONE_PASS).**
- **K-EMB-1** embedder-only (standalone granite/BGE servers; informs the N9/retrain-routing re-embed choice).
- **H7** Ouro-2.6B transformers-CPU, serial (feeds H5). **[2026-11-10 deprecated by operator: Ouro models dropped, GGUFs not on disk and will not be downloaded]**

##### Frozen after DAR-1 replay (~24–28h avoided)
**Package I** (I1 SPO+ / I2 bilinear / I3 ThinkPRM EV-5) — frozen by findings-02's routing reframe and the 2026-06-12 current-traffic DAR-1 replay. The measured regret was 0.00% (<5% reopen gate), so do NOT spend the 24–28 inference-hours unless a future replay after enough new `action_topk` telemetry reaches the gate.

#### Staleness corrections (2026-06-12 audit; refreshed 2026-06-19)
- ✅ **J6 CLOSED/SUPERSEDED 2026-06-19** — the continuous autopilot run already satisfied the 24h soak, and orchestrator `2eb4437` closed the code half by making `_eval_concurrency()` matrix-aware: explicit `AUTOPILOT_EVAL_CONCURRENCY` still wins, otherwise the default is capped by topology safe-N and requires a certified-fresh same-role contention-matrix `ALLOW` verdict for background/eval traffic. Missing/stale/invalid matrix evidence fails closed to serial. Do not re-run J6 as a fresh inference task.
- ✅ **G9 respecified 2026-06-12** — the removed `architect_coding` target is gone. G9 now asks only whether MiniMax M2.7 can replace or complement the live `architect_general` role; code-generation replacement is out of scope unless a separate coder-eval owner claims it.
- ✅ **G10/G11 respecified 2026-06-12** — model targets now name the live stack: `architect_general` = Qwen3.5-122B-A10B, `frontdoor` = Qwen3.6-35B-A3B Q8, `worker_general` = gemma4-26B-A4B-it-Q4_K_M.
  - *(Retarget 2026-10-28 (operator): Qwen3.5-122B deprecated. Any unrun G9/G10 `architect_general` row now targets
    Qwen3.8-Flash-Next UD-IQ4_XS.)*
- ✅ **J12 wiring verification closed 2026-06-12** against production `LlamaServerBackend` `/v1/chat/completions` (NOT `src/backends/openai.py`). The quiesce-window empirical probe closed 2026-07-06; remaining J12 work is THINK-ABL-1.
- **ALL flag-flip A/Bs must set flags via launch env + per-worker attestation** — `POST /config` reaches only 1 of 6 workers, so any A/B that flips a flag at runtime is invalid. Flags go in the reload env; attest each worker before measuring.
- **The speed-metric policy paragraph below changes when the `task_rate` objective lands** (fable5-findings-05) — the current aggregate-batch-t/s convention is provisional until the objective layer is redesigned.

J6's 24h autopilot soak ran on certified topology `df373c79cc4af06f` (now superseded — see above). The cross-role **N-way contention matrix is closed + certified** (all-allow on certified affinity; defensive runtime policy in `src/scheduling/contention_gate.py` + `orchestration/contention_matrix.yaml`) — handoff archived to [`../completed/cross-role-nway-contention-matrix.md`](../completed/cross-role-nway-contention-matrix.md).

> Binding hard rules (baseline-mutation / live-affinity / concurrent-metric) are in **Remaining Execution Order** below; canonical sequencing is the three-queue structure above. Chronological history → `progress/2026-05/` and `progress/2026-06/`.

#### Completed — 2026-04 Campaign (Packages A–F)

Complete or overtaken by the Package J reprioritization. Full runbook detail (commands, expected outputs, results, telemetry plan) archived to **[`../completed/bulk-inference-2026-04-packages.md`](../completed/bulk-inference-2026-04-packages.md)**.

| Pkg | Outcome | Owning handoff |
|-----|---------|----------------|
| **A** | Routing thresholds recalibrated (635 decisions, 2026-04-06) | [`routing-and-optimization-index.md`](routing-and-optimization-index.md) |
| **B** | Instrumented seeding eval v2 — tool-compression +4pp, WS-3 fix validated (2026-04-10) | [`routing-intelligence.md`](routing-program.md#track-routing-intelligence) |
| **C** | Context-folding eval batch — 30B summarizer, L3 sweet spot, TALE deferred (2026-04-11) | [`context-folding-progressive.md`](context-and-token-economy.md) |
| **D** | AR-3 relaunch + RI-10 canary (ran autonomously; canary live since 2026-04-06) | [`routing-and-optimization-index.md`](routing-and-optimization-index.md) · [`autopilot-continuous-optimization.md`](autopilot-program.md) |
| **E** | Vision + Hermes multimodal validation — Hermes PASS, vision fixed 2026-04-08 | [`pipeline-integration-index.md`](pipeline-integration-index.md) · [`user-facing-harness-index.md`](user-facing-harness-index.md) |
| **F** | llama.cpp v3 smoke tests + production binary swap (coder +101%, REAP +50%, 2026-04-10) | [`inference-research-index.md`](inference-research-index.md) |

---
#### Remaining Execution Order

> **SUPERSEDED FOR SEQUENCING (2026-06-12)**: the canonical run order is now the three-queue structure at the top (Queue 1 offline-now → Queue 2 one consolidated quiesce window → Queue 3 restart bundle → standalone model-batched windows → frozen Package I). The flat J1→J11 table below is retained as detailed-ordering provenance; the closed placement/matrix gates (J1/J4a-J4c/J4/J5) are compacted in the Package J note. **The hard-rule paragraphs that follow the table (baseline-mutation / live-affinity / concurrent-run metric policy / frontdoor Half0/Half1 / autopilot dispatch defaults) remain binding for any concurrent or bench run.**

| Order | Work | Duration | Why this order / concurrency policy |
|-------|------|----------|--------------------------------------|
| 0 | **Parallel-dispatch integrity + live-affinity preflight** | ~30 min | Before any large run: confirm epyc-orchestrator main is `15350fe` or later plus the concurrency-metric patch if present, run the placement/migration unit subset, verify `AUTOPILOT_EVAL_CONCURRENCY` defaults to topology-safe `max_safe_concurrency(frontdoor)=3`, and confirm 4-way frontdoor traffic queues rather than placing on overlapping q0/q1. Also verify live llama-server process affinity against `NUMA_CONFIG` for every matrix role before trusting any matrix result. Abort the bulk train if this fails. |
| 1 | **J1** WP-2 placement state-machine gate | ~1h | First required inference gate. Proves safe fan-out (full + disjoint quarters + queued overlap) before any downstream task relies on parallel dispatch. |
| 2 | **J2** WP-3 forward-migration verification | ~2h | Verifies shipped session-handover migration semantics and sticky quarter affinity. This is not proactive mid-decode eviction; do not require an impossible in-flight full decode preemption. |
| 3 | **J3** WP-4 reverse-migration verification | ~30 min + analysis | Verifies solo-after-burst recovery before persistent parallel flags stay on. |
| 4 | **J4a/J4b** N-way contention-matrix closure | ~4-12h, runs alone | Required before using cross-role parallelism to accelerate the backlog. Enumerate every non-trivial all-lower-order-allowed active set up to the scheduler's maximum cross-role concurrency, bench it, write N-way verdicts, and fail closed until every candidate is either measured or explicitly pruned/excluded for this topology. |
| 5 | **J5** WP-6 within-role instance-pair matrix re-bench | overnight, runs alone | Completes the within-role side of the matrix. Must run alone because it launches controlled instance-pair benches. |
| 6 | **J10** URE-1 shadow logger | passive | Flip after the matrix gates are safe; it shapes no workload and can accumulate through all later traffic. |
| 7 | **J12** chat_template_kwargs wiring verification | CLOSED 2026-06-12; empirical probe CLOSED 2026-07-06 | Non-inference wiring verified, and the clean-window frontdoor/architect probe found no revert trigger. Remaining work is THINK-ABL-1 under declared production env. |
| 8 | **J4** WP-5 ratification observation + **J9/J11** observe-only/paired gates where wired | 6-12h | Uses the newly verified parallel-dispatch path and completed matrix. J9 is observe-only; J11 runs per accepted mutation. Keep paired-eval attribution sequential unless explicit concurrent approval exists. |
| 9 | **J6** WP-7 24h rollout | 24h passive | Requires J4a/J4b/J5. J7/J8/J9/J10/J11 can co-run only when their own flags are observe/advisory, the N-way matrix allows the specific active set, and run metadata records concurrency. |
| 10 | **J7** DCP inference gate + optional **J8** legacy BEP A/B | 3-4h each | J7's DCP-4 hook is already default-off/advisory, the offline replay is closed, `29b9ba3` adds the off/on A/B runner, and `56a72f6` packages the first live A/B. Initial result: zero errors/all delegated, fewer generated tokens with DCP ON, but worse p50 latency; no enablement. J8 is not a remediation gate; run it only if its answer would change whether the legacy `batch_edit_mode` path is kept, retired, or exposed as a narrow task-class knob. |
| 11 | **Package H/I/G residuals and D-tail** | variable | H7 before H5; I1 before I2; I3 independent. Standalone G benches can fill downtime, but do not co-run with J4a/J4b/J5 or any standalone throughput bench. |

**Completed historical ordering**: E/B/F/C and the completed G/AM/SEAL items remain documented below for provenance only. Do not use their April ordering as the current run order.

**Concurrent-run metric policy**: When `AUTOPILOT_EVAL_CONCURRENCY>1`, fan-out is allowed only inside a single trial's eval batch; do not run separate trials concurrently in one autopilot process. Individual request tokens/sec normally drops while aggregate batch throughput can improve. Every concurrent eval must record `speed_metric_mode`, `eval_concurrency`, median per-request t/s, aggregate batch t/s, and eval wall time. For concurrent eval batches, the SafetyGate/Pareto `speed` objective is aggregate batch t/s; the raw median request t/s is retained as audit metadata. This prevents the planner from treating safe same-trial fan-out as a regression while still exposing the per-instance slowdown for diagnostics. Cross-role bulk parallelism is stricter: pairwise-allowed is necessary but not sufficient; before J4b completion, unmeasured N-way active sets fail closed. After J4b completion for the current topology, there should be no unclassified N-way active set: each is measured `allow`, measured `block`, or explicitly pruned/excluded by a lower-order failure. This closed-world guarantee is scoped to the exact `topology_hash` / stack state measured by J4b; any future orchestration-stack, role, model, CPU binding, or server-launch topology change invalidates the matrix and requires re-derivation before using cross-role parallelism again.

**Baseline mutation hard rule**: Do not update production baselines, Pareto archives, regression thresholds, learned scheduling priors, routing speed priors, or trial-scheduling evidence from any run unless `speed_metric_mode`, `topology_hash`, and `matrix_status` are recorded and valid. Cross-role concurrent runs must also record the exact N-way active-set verdict or a same-trial within-role fan-out marker. Missing, stale, or inconsistent metadata means diagnostic-only quarantine.

**Live-affinity hard rule (2026-05-26 stack audit)**: `topology_hash` is necessary but not sufficient. It fingerprints the intended `NUMA_CONFIG`, not proof that the currently running llama-server processes were launched with the intended `taskset`/`numactl` prefix. Before J4/J5/J6 or any downstream concurrent run, compare each live port's `/proc/<pid>/task/*/status` `Cpus_allowed_list` union against the exact `NUMA_CONFIG[role].instances[idx]` CPU list. If any process has CPUs outside the expected set or misses expected CPUs, mark matrix status `diagnostic_only`, reload that role through `scripts/server/orchestrator_stack.py`, rerun the affinity check, and rerun all matrix rows involving the affected role/shape before baseline mutation or bulk parallelism.

**Frontdoor Half0/Half1 interpretation**: The dashboard's `Half0` cell for frontdoor is the current idx0 solo/full-speed anchor shape (`0-47,96-143`), not evidence that a validated second `Half1` frontdoor instance exists. Current certified frontdoor concurrency is via the existing q0-q3 quarter instances. Adding a dedicated frontdoor `Half1` replica is a new topology experiment, not a matrix-repair assumption: it requires a new server/port, explicit placement policy, fresh topology hash, isolated benchmarks comparing Half0+Half1 against the current Half0-plus-quarters policy, and a new matrix derivation before it can accelerate the bulk backlog.

**Autopilot dispatch-latency defaults (2026-05-26 hardening)**: before starting the long bulk train, run on an orchestrator containing `scripts/autopilot/phase_status.py`, the dashboard `autopilot_phase` panel, async auxiliary plot/digest scheduling, and contention-aware seed-role waves. Recommended environment:

```bash
AUTOPILOT_ASYNC_AUX=1
AUTOPILOT_ASYNC_WORKERS=2
AUTOPILOT_SEED_ROLE_CONCURRENCY=auto
AUTOPILOT_PAUSE_POLL_S=1
AUTOPILOT_HEALTH_BACKOFF_S=10
```

Use the dashboard phase panel to classify idle gaps before changing scheduling policy: stopped/down, paused, health backoff, planner prompt build, planner invoke, dispatch, journaling, checkpointing, or async artifact scheduling. Seeder fan-out is allowed only for background contention-matrix-safe role waves; missing/stale/unknown matrix evidence should collapse toward serial behavior. Request-level `trial_id`/`batch_id` propagation through benchmark HTTP callers is still deferred because those callers have high/critical GitNexus blast radius; the current phase heartbeat gives loop-level attribution without changing those contracts.

---

#### Package G: Deferred Inference-Dependent Research Tasks

**Duration**: Variable (opportunistic — run during Package D downtime or after D completes)
**Stack required**: Individual model servers (like Package C)
**Depends on**: Nothing — independent research evaluation
**Status**: NOT STARTED — indexed here 2026-04-11 during handoff audit

These tasks are scattered across active handoffs and require inference compute but are not time-critical. Consolidated here so they can be scheduled opportunistically.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| G1 | Memento S2 feasibility | [memento-block-reasoning-compression.md](context-and-token-economy.md#track-memento-block-reasoning-compression) | Benchmark KV masking overhead on llama.cpp. Test if KV states from masked blocks preserve accuracy. | Any 8B+ model | ~4h |
| G2 | Expected Attention S8 profile sweep | [triattention-kv-selection.md](long-context-program.md#track-triattention-kv-selection) | Sweep `keep_ratio` and `layer_weights` per production role; record Pareto profile with quality, speed, cost, and reliability axes. Historical S1 deployment evidence moved to completed ledger. | coder_escalation + one long-context role | ~4h |
| G3 | Expected Attention stacking/high-compression check | [triattention-kv-selection.md](long-context-program.md#track-triattention-kv-selection) | Reopen selection + quantization stacking only if S8 shows production need for higher compression; otherwise compare Attention Matching before adding kernel complexity. | coder_escalation | ~4h |
| G4 | FlowSteer activation steering | [reasoning-compression.md](context-and-token-economy.md#track-reasoning-compression) Tier 2 | Test nonlinear activation steering for concise reasoning on 30B-A3B worker. | worker_general | ~6h |
| G5 | short-m@k voting baseline | [reasoning-compression.md](context-and-token-economy.md#track-reasoning-compression) Tier 1 | Run k=3 parallel generations, majority vote. Measure accuracy vs single-shot on GPQA/math. | Any reasoning model | ~4h |
| G6 | v3 clean NUMA throughput | [llama-cpp-v3-upstream-rebuild.md](../completed/llama-cpp-v3-upstream-rebuild.md) | Isolated NUMA test (requires stopping production stack). Compare v3 vs v2 48t quarter throughput. | frontdoor or worker | ~1h |
| G7 | MiniMax M2.7 download + launch | Research intake (intake-328/329) | ✅ DOWNLOADING: Q8_0 (243GB) + UD-Q4_K_XL (141GB) from unsloth/MiniMax-M2.7-GGUF → `/mnt/raid0/llm/models/MiniMax-M2.7-GGUF/`. MoE 230B-A10B, 256 experts, 200K ctx. Launch with `--spec-type ngram-simple --draft-max 64`, `numactl --interleave=all`. No spec-dec (200K vocab, no compatible draft). Expected: Q4_K_XL ~12-16 tps w/ ngram, Q8_0 ~9-13 tps w/ ngram. | Standalone | ~2h |
| G7a | MiniMax M2.7 NUMA sweep | — | Sweep NUMA parallelization: 1×192t interleave vs 2×96t per-node vs 4×48t quarters. Model fits single node (~141-243GB vs ~560GB/node). 256-expert scatter pattern may favor interleave. | Standalone | ~3h |
| G8 | MiniMax M2.7 tool-calling | Research intake (intake-328/329) | Evaluate tool-calling reliability vs Qwen3 stack. Test orchestrator function-calling pipeline. | Standalone | ~4h |
| G9 | MiniMax M2.7 architect_general replacement eval | Research intake (intake-328/329) | **Goal: test whether MiniMax M2.7 can replace or complement the live `architect_general` role only.** The removed `architect_coding` role is no longer a target. Compare M2.7 against current `architect_general` (Qwen3.5-122B-A10B) on architecture/general-reasoning tasks plus any existing MiniMax G8 tool-calling evidence. Do not treat this as a coder replacement or RAM-consolidation decision unless a separate coder-eval owner reopens that scope. | Standalone | ~4-6h |

- [x] **G9-disk — MiniMax-M2.7 keep-vs-delete decision (operator; filed 2026-07-26).** ✅ 2026-08-09 —
  **RESOLVED: DELETE.** Operator decided during the 2026-08-09 model-root reclaim. 227 GB freed.
  Evidence supporting delete: the artifact was never exercised (zero run artifacts under
  `/mnt/raid0/llm/tmp`), only Q8_0 ever landed (the campaign expected Q8_0 *and* UD-Q4_K_XL), and
  G8/G9 have been "IN PROGRESS" since 2026-04-19 — superseded by the post-v8 architect-bench
  campaign. Ledgered in the **master** registry (`epyc-inference-research`): `minimax_m27_q8`
  marked `artifact_status.download: deleted` + a `deprecated_models` entry; lean registry
  recompiled (`deprecated_models` 22 → 37, the only section that changed). **Do not re-download
  without a fresh operator decision.** G7a/G8/G9 below are consequently dead — treat as killed,
  not pending.
  *Process note:* the 2026-07-26 entries (Qwable/longcat/f16-upcast) were appended to the **lean**
  registry only and were dropped by the 2026-07-29 recompile `f6691d79`, which correctly
  regenerates the derived artifact from master. They have been restored into master and now
  survive recompiles. **Ledger entries go in the master registry, never the compiled output.**
  <details><summary>Original decision text (filed 2026-07-26)</summary>

  The 227GB
  `models/MiniMax-M2.7-GGUF/` dir survived the 2026-07-26 disk cleanup ONLY because G7a-G9 are
  still-open rows. Decide when the post-v8 architect-bench campaign lands its verdicts: either
  G9 merges into the architect bench as an M2.7 arm (keep the download), or G7a-G9 are killed as
  superseded by that campaign (delete 227GB, record in both registries' deletion ledgers per the
  2026-07-26 pattern). Do not re-download if deleted without a fresh operator decision.

  </details>

##### Progress (updated 2026-04-13)

- **G1 (Memento S1)**: ✅ Feasibility CONFIRMED (2026-04-13). `llama_memory_seq_rm()` supports mid-sequence block eviction. Runtime validation passed (slot erase + continued generation). OpenMementos-228K downloading (`microsoft/OpenMementos`). S2 (LoRA) is next.
- **G2 (EA S1)**: ✅ Scaffold ready + proxy evaluation done (2026-04-13). KV compression at 50% removal: cosine=1.000 on NIAH tasks. Full KVPress integration needs compatible transformers version.
- **G3 (stacking)**: PENDING — depends on G2 full evaluation
- **AM P2**: ✅ Validated on Qwen2.5-7B (2026-04-13). 2x=1.000, 5x=0.906, 10x=0.807. Layer-adaptive strategy identified.
- **AM L1-L3b**: ✅ COMPLETE (2026-04-13). Beta bias kernel in llama.cpp-experimental, public `llama_memory_set_beta()` API, server `POST /slots/{id}?action=set-beta` endpoint, E2E test on Coder-32B f16. Full pipeline: Python compaction → HTTP beta injection → server decode. Next: quality comparison test.
- **SEAL cvector**: ✅ Pipeline validated (2026-04-13). Trained 28-layer concise reasoning vector on 7B. A/B: +1.8% tokens (minimal at 7B, real experiment targets 30B+). Fixed v3 GGML_OP_GLU build issue (stale libggml-cpu.so).

##### New tasks for AR-3 fold-in assessment

The following medium-term tasks could piggyback on AR-3 stack sessions:

| Task | Can fold into AR-3? | Notes |
|------|---------------------|-------|
| **PPL sweep** (v3 baseline) | YES — run during AR-3 warmup/cooldown | `llama-perplexity` on wikitext2 for coder, frontdoor, worker, REAP. Independent of stack. ~1h total. |
| **AM P3** (AM vs EA head-to-head) | PARTIAL — needs model loaded, not full stack | Compare AM HighestAttnKeys-fast vs Expected Attention at 5x/10x/20x on same model. Python-only, ~4h. Can run during Package D downtime. |
| **RI-10 canary** | YES — this IS Package D | Extended to 2026-04-27, n=16/50 high-risk samples. AR-3 generates these samples. |
| **SEAL on 30B** | NO — needs dedicated server with cvector | Train + eval concise reasoning vector on Qwen3-Coder-30B-A3B. Separate from orchestrator stack. |
| **AM P2 on 32B** | ✅ DONE — E2E beta injection tested on 32B f16 | L1-L3b complete. Beta injection via server endpoint works on Coder-32B. Full compaction quality test next. |
| **ColBERT reranker S1 data** | YES — passive (already instrumented) | S1 relevance logging in `_web_research_impl()` fires on every web_research call. AR-3's 50-question `web_research` sentinel suite generates the data. After AR-3, grep logs for `web_research relevance summary` to measure irrelevant page rate. If >20%, proceed to S3 (model download). See [colbert-reranker-web-research.md](knowledge-pipelines.md#track-colbert-reranker-web-research). |
| **SearXNG backend validation (SX-5/SX-6)** | YES — activate via feature flag | SX-1/2/3/4 implemented (Docker service, `_search_searxng()`, settings.yml, telemetry). Activate `ORCHESTRATOR_SEARXNG_DEFAULT=1` during AR-3 warmup trial. The web_research sentinel suite (50q) validates SearXNG search quality under real query patterns. Telemetry: `searxng unresponsive_engines` logs engine failures; S1 relevance instrumentation measures page quality. If no regression on first warmup trial, lock in SX-6 swap. If regression, disable flag and iterate on SX-3 engine tuning. Post-AR-3: analyze engine failure rates + result quality delta vs DDG baseline. See [`searxng-search-backend.md`](knowledge-pipelines.md#track-searxng-search-backend) P12. |

##### Prioritization (updated 2026-04-13)

- **G1 + G5 together**: Memento S1 DONE. G5 runner/manifest wiring is READY in research `cbf00e1`; run the clean-window G5 GPQA/math commands with the standalone model-batched window, not during active AutoPilot evidence collection.
- **G2 + G3 sequentially**: G2 proxy DONE (gate passed). Full KVPress evaluation + G3 stacking test pending. **AM compaction is now the primary path** — P2 results show structured attention compresses near-losslessly at 2-5x with layer-adaptive strategy.
- **G4**: Defer — FlowSteer library maturity unconfirmed.
- **G6**: Low priority — v3 smoke tests showed no regression.
- **G7**: ✅ COMPLETE (2026-04-17). All models downloaded and benchmarked. Q4_K_XL deleted (Q8 preferred for quality). M2.7 Q8 = 11.1 tps. Also swept: Qwen3.6 Q8 (27.4 tps), SG4-26b Q4 (42 tps), SG4-31b Q4 (9.0 tps), SG4-26b-MM Q8 (21.1 tps), Gemma4 E2B/E4B (deleted — no value).
- **G7a**: ✅ COMPLETE (2026-04-17). Full NUMA characterization with concurrent requests. Key findings: (1) --mlock + --membind required for multi-instance, (2) Q8 > Q4 for dense models < 40GB, Q4 > Q8 for large MoE, (3) concurrent benchmarks show ~40% less aggregate than serial sum. New deterministic `numa_sweep.py` with early stopping + scaling gates.
- **G8 + G9**: IN PROGRESS (2026-04-19). Quality benchmarks run with Claude-as-Judge scoring. Multiple iterations to fix model-specific serving issues (chat templates, reasoning mode, KV cache, repeat_penalty). Partial results: SG4-26b-MM 65.4%, SG4-31b 60.5%, M2.7 55.7%. Qwen3.6 still iterating (thinking model config). SG4-26b Q4KM deprecated (irrecoverable degeneration at Q4). Final run with `--reasoning off` in progress for all 4 remaining models.
- **G10 + G11 + G12**: AA-Omniscience hallucination calibration — can run per-model sequentially, ~6h total.

##### G10-G12: AA-Omniscience Factual-Risk Calibration (2026-04-15 research intake)

**Source**: intake-381/intake-383 ([arxiv:2511.13029](https://arxiv.org/abs/2511.13029)), [routing-intelligence.md](routing-program.md#track-routing-intelligence) Phase 4 calibration gap
**Dataset**: `ArtificialAnalysis/AA-Omniscience-Public` (600 Qs, Apache 2.0, already in HuggingFace cache)
**Goal**: Replace heuristic capability tiers in `factual_risk.py` (`_DEFAULT_ROLE_TIERS`: tier_1=0.6, tier_2=0.8, tier_3=1.0) with measured per-model hallucination rates. **Done 2026-06-20**: deterministic AA-Omniscience 4-class scoring was accepted for this role-tier recalibration, and orchestrator now uses measured tier_1 `0.727978`, tier_2 `0.824178`, tier_3 `1.0`.

Scoring methodology (from paper): Omniscience Index = 50% accuracy + 50% (1 - hallucination_rate), where hallucination_rate = incorrect / (incorrect + partial + not_attempted). Answers graded as CORRECT/INCORRECT/PARTIAL_ANSWER/NOT_ATTEMPTED. Models prompted to say "I don't know" rather than guess.

| # | Task | Description | Models Needed | Effort |
|---|------|-------------|--------------|--------|
| G10 | AA-Omniscience: architect_general | Run 600 Qs through the live `architect_general` target, Qwen3.5-122B-A10B. Record per-domain accuracy + hallucination rate. Expect above-zero Omniscience Index. | architect_general (solo) | ~2h |
| G11 | AA-Omniscience: frontdoor + worker | ✅ Raw-response + deterministic-F1 evidence packaged for live `frontdoor` (research `587c6cd` + `92a5602`) and live `worker_general` (research `32f2c27`). | frontdoor, worker_general (sequential) | complete |
| G12 | Calibrate capability tiers | ✅ Deterministic AA-Omniscience 4-class scoring accepted for role-tier recalibration; `_DEFAULT_ROLE_TIERS`, default config, and live `classifier_config.yaml` updated to measured multipliers. Future SimpleQA augmentation is optional evidence expansion, not a blocker for this tier update. | No inference — analysis only | complete |

**2026-06-19 G12 offline prep:** Orchestrator `7d729e3` repaired
`scripts/build_factual_risk_calibration_v2.py` so HuggingFace `datasets` is not shadowed by the local
`scripts/datasets` package when run by path, hardened JSONL writing to ASCII-escape Unicode line separators,
and regenerated the v2 calibration artifacts:
`orchestration/factual_risk_calibration_v2.jsonl` plus `_train`, `_val`, `_test`. Completed artifact has
2,600 rows (`v1_regex` 2,000 + `aa_omniscience` 600), risk features populated for all rows, and split counts
1,806 / 375 / 419. This is dataset prep only; G10/G11 live per-model AA-Omniscience runs and the downstream
`src/classifiers/factual_risk.py` tier update remain open and should stay on the main thread when touched.

**2026-06-19 measurement/report prep:** Research `cf3cd3a` added
`scripts/benchmark/aa_omniscience_manifest.py` plus generated
`docs/data/aa_omniscience_measurement_manifest.json` and
`docs/data/aa_omniscience_measurement_commands.sh`. The adapter preflight sees all 600 AA-Omniscience
questions, 56 candidate roles, 43 ready roles, and 13 blocked roles with missing local model paths. The
generated command file leaves canonical preflight enabled and comments blocked roles instead of executing
them. Research `7d27597` refreshed this generator after the failed frontdoor G11 run so every AA quality command
uses `--server-mode --skip-speed-tests`; do not resurrect the older subprocess/speed-sweep command shape for
G10/G11 evidence. Orchestrator `8546b3e` added `scripts/analysis/factual_risk_calibration_report.py`, which summarizes
the v2 corpus/splits and can aggregate future G10/G11 result JSONL by role/model/outcome. Orchestrator
`61e670d` extends that report with AA outcome rates and a fail-closed `tier_calibration_readiness`
block. After research `b91d16c`, the deterministic report observes all expected roles and reports
`ready_for_tier_update`: architect multiplier preview `0.727978`, frontdoor `0.824178`, and
worker_general `1.0` relative to the current worst observed hallucination rate. Orchestrator then accepted deterministic
AA-Omniscience 4-class scoring for this role-tier recalibration only and updated `src/classifiers/factual_risk.py`,
`src/classifiers/config_loader.py`, and `orchestration/classifier_config.yaml` to those measured values. Factual-risk
mode/canary/enforce decisions remain on their separate telemetry gates.

**Implementation notes**:
- Prompt template from paper: `"You are answering questions about {domain}, and in particular {topic}. You will be given a question, answer with JUST the answer (no explanation). If you do not know the answer, or you need more context or tools to answer the question, be clear about this - it is better that you say this than get the wrong answer."`
- Grading: LLM-as-judge with 4-class output, or regex for exact-match answers (many are short factual: dates, names, section numbers)
- Results persist to `data/package_g/omniscience/` per model — incremental (one row per question)
- Key output: `{model}_{domain}_hallucination_rate.json` → feeds tier recalibration
- SimpleQA augmentation: grep seeding logs for `simpleqa` suite with `passed=False`, extract prompt+answer pairs, cross-reference with AA-Omniscience domains for combined calibration

**Exit criteria**:
- [x] Per-model hallucination rate per domain computed
- [x] Empirical tier multipliers differ from heuristic by >5% (otherwise heuristic was adequate)
- [x] `factual_risk.py` `_DEFAULT_ROLE_TIERS` updated with measured values
- [x] routing-intelligence.md Phase 4 calibration gap closed for role-tier calibration

#### Package H: Research-Driven Inference Tasks (2026-04-12 research intake)

**Duration**: Variable (~12-16h total if sequential)
**Stack required**: Standard orchestrator stack (frontdoor + coder) for most; Ouro needs transformers separately
**Depends on**: Non-inference Tasks 10-11 (DSPy/GEPA install + dspy.RLM setup)
**Status**: NOT STARTED — indexed 2026-04-12 from research intake deep-dives

These tasks evaluate research-intake findings that require live inference. Ordered by dependency chain.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| ~~H1~~ | ~~GEPA frontdoor optimization (AP-19)~~ | ~~[autopilot-continuous-optimization.md](autopilot-program.md) P10~~ | → **Folded into Package D** (2026-04-12). GEPA integrated as PromptForge mutation type. AR-3 runs GEPA trials at 30% of PromptForge budget. | — | — |
| ~~H2~~ | ~~GEPA Full Program Adapter eval (AP-20)~~ | ~~[autopilot-continuous-optimization.md](autopilot-program.md) P10~~ | → **Folded into Package D**. Resolved by comparing GEPA vs LLM mutation acceptance rates in AR-3 journal. | — | — |
| ~~H3~~ | ~~PromptForge GEPA integration test (AP-21)~~ | ~~[autopilot-continuous-optimization.md](autopilot-program.md) P10~~ | → **Folded into Package D**. Decision from AR-3 data: if GEPA dominates Pareto frontier after 50+ trials → increase ratio to 100%. | — | — |
| H4 | dspy.RLM integration testing (AP-26) | [autopilot-continuous-optimization.md](autopilot-program.md) P11 | Test dspy.RLM for benchmark analysis via REPL exploration. Coder as main LM, frontdoor as sub_lm. **Post-AR-3** — controller change too risky mid-run. | coder + frontdoor | ~2h |
| H5 | RLVR eval tower validation (AP-27) + calibration baseline (EV-4) | [eval-tower-verification.md](eval-tower-program.md) EV-4 + [autopilot-continuous-optimization.md](autopilot-program.md) P11 | Run eval tower on Scoring Verifiers HE-R+ to establish ECE/AUC baseline (EV-4), then validate T0/T1/T2 as RLVR verification functions. **Depends on**: EV-1+EV-2+EV-3 (non-inference prep, now complete after research `7c11920` fixed candidate-level Scoring-Verifiers labels) + P7 Ouro results. **Post-AR-3** — modifies eval trust boundary. | full stack | ~4h |
| ~~H6~~ | ~~GEPA search algorithm eval (MH-4)~~ | ~~[meta-harness-optimization.md](../completed/meta-harness-optimization.md) Tier 2b~~ | → **Folded into Package D**. Pareto frontier contributions by mutation source analyzed from AR-3 journal. | — | — |
| H7 | Ouro-2.6B-Thinking benchmark (P7) | [research-evaluation-index.md](research-evaluation-index.md) P7 | Run MATH-500 + reasoning suite via transformers on CPU. NOT llama.cpp. Standalone. No stack conflict if needed, but not urgent — feeds H5 which is post-AR-3. | Ouro-2.6B (transformers, CPU-only) | ~4h | *(2026-11-10: DEPRECATED by operator, Ouro dropped.)*

##### Prioritization (updated 2026-04-12)

- ~~**H1/H2/H3/H6**~~: **Folded into Package D** (2026-04-12). GEPA integrated into PromptForge as mutation type. AR-3 generates comparison data organically. See `scripts/autopilot/species/gepa_optimizer.py`.
- **H4 post-AR-3**: dspy.RLM testing. Controller architecture change — defer to AR-4.
- **H5 post-AR-3**: RLVR formalization + EV-4 calibration baseline. Non-inference prep (EV-1/2/3/6) now complete — ready for inference run. Defer to AR-4. Depends on H7.
- **H7 post-AR-3**: Ouro benchmark. Standalone (transformers CPU, no stack conflict). Feeds H5. Not urgent.

---

#### Package I: Decision-Aware Routing Validation (post-AR-3)

**Duration**: ~2 days (DAR-3 exploration needs sustained traffic for counterfactual data)
**Stack required**: Full orchestrator stack
**Depends on**: Future DAR-1 replay reaching the >=5% regret reopen gate + N2 per-question eval vectors. The current-traffic replay on 2026-06-12 did **not** reach the gate (0.00% identifiable mean regret), so Package I remains frozen. Historical DAR-1 analysis also found uniform Q (April: 96%; current replay: 99.1%).
**Status**: NOT STARTED — indexed 2026-04-15 from research deep-dive

These tasks modify routing behavior and need isolated measurement. Running exploration routing during Package H's research eval would contaminate both.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| I1 | DAR-3 SPO+ exploration | [decision-aware-routing.md](routing-program.md) DAR-3 | 10% epsilon-greedy exploration routing for counterfactual data collection. Convex SPO+ loss replaces TD update. | full stack | ~3-4 sessions |
| I2 | DAR-4 bilinear scorer A/B | [decision-aware-routing.md](routing-program.md) DAR-4 | Model-feature-conditioned Q vs current per-action Q-tables. Zero cold-start for new models. | full stack | ~2 sessions |
| I3 | EV-5 ThinkPRM-1.5B T2 | [eval-tower-verification.md](eval-tower-program.md) EV-5 | Deploy ThinkPRM-1.5B-Q4KM for T2 process verification on uncertain questions. Cross-family constraint enforced. | ThinkPRM + eval stack | ~4h |

##### Prioritization

- **I1 (DAR-3)**: Highest priority — generates counterfactual data needed for decision-aware training. Must run with sustained traffic.
- **I2 (DAR-4)**: Can run after I1 data collection. A/B comparison: bilinear scorer vs current Q-scorer on same traffic.
- **I3 (EV-5)**: Independent of I1/I2. Deploy ThinkPRM-1.5B, run T2 verification pass. Validate cross-family constraint (EV-6, already in code).

##### DAR-1 Preliminary Results (2026-04-15)

Initial regret analysis on 7,211 routing decisions (Apr 10-14):
- 96% uniform Q-values — Q-scorer has barely learned preferences
- Selection score spread is non-trivial (median 0.107) — comes from cost/similarity, not Q-values
- 25% trivial spread (<0.01)
- Implication: DAR-2 contrastive training needs more routing memories. Consider seeding-driven memory accumulation before Package I.

---

#### Package J: Within-Role Placement + Audit-Batch Inference Gates (2026-05-26)

> **▶ STATUS UPDATE (2026-05-27) — supersedes the "Status" line below.** The 2026-05-26 status is stale. Current truth (reconciled against `orchestration/contention_matrix.yaml` + `data/bulk_inference_2026_05_26/execution_manifest.jsonl`):
> - **Contention matrix: CLOSED + certified, ALL-ALLOW.** The famous `{frontdoor,ingest,vision}=0.847` "block" was a **bad-affinity artifact** (launcher `_numa_prefix` bug mis-pinned quarters); re-benched on certified disjoint quarters (`live_affinity_verified=true`) it is **1.731 allow**, and every measured N-way set allows (`4363dae`). **No measured N-way block remains.** New hard gate: `live_affinity_verified` + `affinity_preflight.py` artifact (topology_hash alone is insufficient).
> - **J4b/J5: SUPERSEDED** by the certified re-bench (their verdicts were bad-affinity). **J4c: LIVE but now DEFENSIVE** (`nway_policy` wired; nothing currently queues). **J4: RATIFIED** (placement SM live; per-role policy decided). **J6: relaunched repeatedly** (soak runs on `df373c79`, production API; the live daemon pid changes on every relaunch — discover it at runtime via `pgrep -af "autopilot.py start"`, do not trust any pid written here).
> - **J1 core PASS; J2/J3 NOT live-closed** — migrations never naturally triggered in the ratification autopilot; a dedicated live migration probe is still pending.
> - **BEP-2 status changed after the 2026-05-27 edit-transaction work**: the read-loop is no longer the active remediation blocker. Qwen3.6 passed the direct one-shot ablation 5/5, and the default-off `force_mode="edit"` transaction path is built + hardened. **J8 is now optional for a narrower decision**: whether to keep, retire, or task-scope the legacy structured patchset/batch-edit path. **DCP-6 is no longer gated on BEP's read-loop**, and DCP-4 advisory attach is already wired/default-off; only its offline replay + eval remain.
> - **N-way runtime policy** is fail-OPEN for unmeasured foreground / closed-world for background-bulk (matches the code + cross-role-bw handoff); the older "closed-world serialize" wording is superseded.

**Duration**: ~1-3 days if sequenced; J5 (matrix re-bench) can run overnight
**Stack required**: Standard orchestrator stack; J1-J3 require `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1`; J3 additionally requires `ORCHESTRATOR_REVERSE_MIGRATION=1` set in the API env
**Depends on**: epyc-orchestrator main @ `15350fe` or later — both feature branches MERGED 2026-05-26 (`fe6805c` placement WP-0..WP-4 + WP-5 scaffold; `15350fe` intake-607 harness DCP/BEP/BSV/URE). 347 unit tests on main; all new code additive + flags default-OFF. No further branch merging needed before any J task.
**Status**: IN PROGRESS (claude 2026-05-26). Preflight PASS (67 tests). **J4a DONE** (`data/contention_matrix/bulk-2026-05-26-j4a/`). **J1 core PASS** — placement SM scales concurrent frontdoor 1.68×–1.91× across disjoint instances, no overlap; the `topology_overlap` queue is NOT observable via `/chat` (HTTP rate limiter 60rpm/10burst + a persistent dashboard client cap concurrent arrivals) → **J1 queue + J2/J3 migration verification re-vehicled to the autopilot eval-concurrency fan-out path** (the original WP-0 motivation). **J4b**: first full-instance pass exposed an operator-flagged methodology error → corrected to a **quarter-level disjoint-cpuset feasibility model** (`enumerate --feasibility`: 25 feasible / 32 `topology_infeasible`); quarter-level re-bench (`--safe-sampling`) IN PROGRESS (`data/contention_matrix/bulk-2026-05-26-j4b-feasible/`). **gemma4 worker_general full-instance crash FIXED** (uncaught PEG-parser throw → raw-content fallback; ik_llama.cpp `d84755dc`, rebuilt+redeployed+verified). Findings F1–F4 in [within-role-placement-state-machine.md](numa-placement-and-contention.md#track-within-role-placement-state-machine); correction detail in [cross-role-nway-contention-matrix.md](../completed/cross-role-nway-contention-matrix.md). Remaining: finalize quarter-level matrix → J4c policy wiring → J5/J4/J6 → J7–J12.

**2026-05-27 Codex audit checkpoint**: this runbook is structurally correct, but several execution-state surfaces
need a consistency sweep before launching another nonstop bulk agent. Later certified-affinity results supersede
older manifest/handoff rows that still cite the `{frontdoor,ingest,vision}` `0.847` block as live proof; current
matrix/progress says that row was a bad-affinity artifact and remeasured `allow`. Runtime safety also needs two
code-level hardening items before baseline-eligible cross-role bulk parallelism: `ContentionGate.matrix_health()`
should check the live topology hash, and `SafetyGate.update_baseline()` should enforce the documented
`speed_metric_mode`/`topology_hash`/`matrix_status` baseline mutation rule. J2/J3 live migration verification
remains open; do not call J1-J3 complete until the dedicated probe produces evidence. See the 2026-05-27 progress
entry "Codex bulk-campaign audit + wrap-up skill checkpoint" for the full findings list.

Inference-gated verifications and observability runs for the within-role-placement-state-machine handoff. Also bundles the two sibling inference gates from the 2026-05-25 audit batch (DCP-6, BEP-2) because they share the same "needs autopilot-style eval workload" profile and benefit from one operator sitting + one cleared stack window. Add other-agent inference-gated items under this Package (or a successor) for shared sequencing.

##### Priority-zero sequencing (RUN FIRST)

> **J1 → J2 → J3 → J4a/J4b/J5 must run BEFORE any downstream inference Package that relies on parallelism** (D-tail, G/H/I, J4/J6-J9, or other-agent items appended at the end). Reason: J1-J3 enable the within-role WP-2/3/4 parallelization flags, while J4a/J4b/J5 finish the cross-role and within-role matrix evidence needed to decide which concurrent active sets are actually throughput-positive. Once verified and left on, every subsequent autopilot/eval/bench task benefits from safe concurrency without corrupting throughput metrics or scheduling priors.
>
> Equivalent ordering rule for the global Execution Order table: insert **`J1, J2, J3, J4a, J4b, J5`** ahead of any not-yet-started inference Package that could use shared-stack concurrency. Don't backfill `Package E/B/F/C` ordering — those already completed.
>
> If the operator wants to mix flag-enablement validation with downstream work in the same sitting, the safe interleave is: J1 (~1h) → J2 (~2h) → J3 (~30-min profile) → J4a dry-run enumeration → J4b/J5 matrix benches in isolated slots → enable flags persistently → proceed with anything else.

##### Parallel-dispatch integrity preflight (abort-on-fail)

Before starting the bulk train, run this preflight on the orchestrator checkout:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python3 -m py_compile src/backends/concurrency_aware.py src/scheduling/placement.py scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py scripts/autopilot/autopilot.py
pytest -q tests/unit/test_eval_tower_concurrency_metrics.py \
  tests/unit/test_topology_concurrency.py \
  tests/unit/test_dispatch_placement_state_machine.py \
  tests/unit/test_per_region_locks_migration.py \
  tests/unit/test_load_transition_migration.py \
  tests/unit/test_reverse_migration.py \
  tests/unit/test_migration_transaction.py
```

Gate expectations:
- `AUTOPILOT_EVAL_CONCURRENCY` unset resolves to `max_safe_concurrency(frontdoor)=3`; any explicit override above 3 is a deliberate stress test, not a production default.
- Four concurrent frontdoor requests show exactly 3 active safe placements and one queued/denied for `topology_overlap`; no q0/q1 overlap with full is allowed.
- Concurrent eval results include `speed_metric_mode`, separate median request t/s, and aggregate batch t/s metadata. If a run predates that telemetry, compute the two metrics manually from logs and mark the trial analysis as concurrency-audited before using it for scheduling decisions.
- Live process affinity matches `NUMA_CONFIG` for all roles used by J4/J5/J6. Minimum check: enumerate live llama-server ports, map port->role/index from `NUMA_CONFIG`, union all thread `Cpus_allowed_list` values for each PID, and assert exact equality with the expected CPU set. Record the result in the execution manifest as `live_affinity_verified: true` plus `affinity_artifact`.
- Specific 2026-05-26 audit hazard: frontdoor and ingest affinities were observed correct, but `worker_general` and `vision_escalation` quarter ports were observed with wrong live affinity when their special launcher paths used `_numa_prefix(role)` instead of `_numa_prefix(role, numa_instance)`. After applying/reloading the launcher fix, rerun the affinity check and treat pre-fix worker/vision matrix rows as diagnostic until re-measured.
- If any of these fail, stop. Do not run D-tail/G/H/I/J4+ on top of a suspect dispatcher, stale live affinity, or unlabelled concurrent speed metric.

> **CLOSED placement + matrix gates (J1, J4a, J4b, J4c, J4, J5, J6) — runbook should migrate to `handoffs/completed/`.** Per the 2026-05-27 status update above plus the 2026-06-19 J6 closure: J1 core PASS; J4b/J5 SUPERSEDED by the certified disjoint-quarter re-bench (`4363dae`, all-allow, `live_affinity_verified=true`); J4c LIVE-but-defensive (`nway_policy` wired, nothing queues); J4 RATIFIED (placement SM live, per-role policy decided); J6's soak is superseded by the continuous run and its EvalTower default is now matrix-aware (`2eb4437`). Their detailed commands/gates/manifest are reference-only and should move to the completed placement runbook (`within-role-placement-state-machine.md` + `../completed/cross-role-nway-contention-matrix.md` own the canonical copies). The only OPEN item from the placement block is **J2/J3** (live migration probe — never naturally triggered), scheduled in Queue 2. The table below retains J2/J3 + J7-J9 rows; J6 is closed/superseded.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| J2 | WP-3 forward-migration verification | [within-role-placement-state-machine.md](numa-placement-and-contention.md#track-within-role-placement-state-machine) § Phase 3 | Forward migration is shipped on the existing session-handover trigger (transactional, policy-gated), not as proactive mid-decode eviction. Verify: under sustained 2+ concurrent traffic with session handover on full, MigrationTransaction completes (state_history shows planned→saving→restoring→verified→source_erased→committed within budget), old session's NEXT request lands on the assigned quarter (sticky affinity preserved), and aggregate t/s under continuous fan-out approaches the matrix's 4-quarters baseline once all requests are placed on disjoint cpusets. | frontdoor (Qwen3.6-35B-A3B Q8 ×5) | ~2h |
| J3 | WP-4 reverse-migration verification | [within-role-placement-state-machine.md](numa-placement-and-contention.md#track-within-role-placement-state-machine) § Phase 4 | Enable `ORCHESTRATOR_REVERSE_MIGRATION=1`, run a 30-min mixed traffic profile (alternating bursts of 4 concurrent and solo turns) on frontdoor. Verify reverse-migration log/stat evidence increments, per-session migration counts respect the cap (default 5), and solo-after-burst per-request latency regresses ≤+10% vs solo-only baseline. The Prometheus counter named in the original Phase 4 plan is not wired as of this audit; do not block on it unless a metrics patch lands first. | frontdoor (Qwen3.6-35B-A3B Q8 ×5) | ~30-min profile + analysis |
| J6 | WP-7 production rollout + 24h gate | [within-role-placement-state-machine.md](numa-placement-and-contention.md#track-within-role-placement-state-machine) § Phase 7 | **CLOSED/SUPERSEDED 2026-06-19.** Continuous AutoPilot satisfied the soak, and `_eval_concurrency()` now uses a matrix-aware default (`2eb4437`): topology safe-N is only used when the same-role contention matrix is certified fresh and allows background/eval fan-out; env override remains the documented operator escape hatch. | full production stack | closed |
| J7 | DCP-6 delegation context pre-assembly eval | [delegation-context-preassembly.md](context-and-token-economy.md#track-delegation-context-preassembly) DCP-6 | DCP-4 advisory attach is wired/default-off (`features().dcp_pre_assembly`) and validated by `tests/unit/test_dcp4_wiring.py`. 2026-06-12 offline replay passed scratch-root/file-selection/budget correctness over 5 historical BEP tasks, then DCP-6a branch `fix/dcp6a-context-depth-current` (`530128b7`) fixed shallow slices + missing hashes and replayed clean: 100% file coverage, 100% line coverage, 0 missing hashes at budgets 500/1000/2000. Code landed on the live branch at `2e2e0d3`; 2026-06-19 launch-code provenance check found current `server_launch_git_sha=eeb8cce` already contains `2e2e0d3` and `756c96b`. Orchestrator `29b9ba3` adds `scripts/benchmark/dcp_j7_ab.py`, which validates its artifact schema in `--stub`, refuses real inference without `--host-quiet-confirmed`, refuses while AutoPilot is running, and records per-prompt latency/token/delegation telemetry in off/on arms. Next is a clean running-state attestation after clearing deleted llama-server binary paths, flag intent diffs, and missing API-parent tool-sentinel env, then inference gate measuring prefill tokens, latency, top-ups, bundle-build latency, quality, hallucinated-file references, and context-contamination failures vs reactive-discovery baseline. Default-off flag stays off until results justify. | frontdoor + worker_coder (delegation-heavy roles) | ~3-4h after clean DCP-6a running-state attestation |
| J8 | BEP-2 batched edit CPU-latency A/B | [batched-edit-parallel-apply.md](autopilot-program.md#track-batched-edit-parallel-apply) BEP-2 | **Optional decision experiment for the legacy batch-edit path.** The production-relevant remediation is the shipped edit transaction, which bypasses both the interleaved Root LM loop and the old patchset proposal. Run J8 if the answer would change whether `ORCHESTRATOR_BATCH_EDIT_MODE` is kept, retired, or exposed as a narrow task-class knob, especially for large-repo patch economy or structured-patch provenance. Do not run it merely to validate the already-built edit-transaction remediation. | worker_coder + frontdoor | ~3h |
| J9 | HLE-4 harness metrics observe-only run | [autopilot-continuous-optimization.md](autopilot-program.md) HLE-4 + [meta-harness-optimization.md](../completed/meta-harness-optimization.md) HLE-1/2/3 | **CLOSED 2026-06-12** from existing trial journal snapshot. `EvalResult` + journal JSONL carry `harness_metrics`, `oracle_adequacy`, `metric_schema_version` and retain concurrency telemetry fields. `execution_fidelity` and `planning_stability` separate keep/revert but are not independent enough to promote; `feedback_interpretation`, `memory_coherence`, and `recovery_rate` fail signal/missingness gates. No Pareto co-objective promotion before N2 ledger/sequential verdict redesign. | full autopilot stack | closed |

##### Sequencing notes

- **Preflight → J1 → J2 → J3 → J4a/J4b/J5 → J4** is the new parallelization block. J1-J3 prove dispatcher safety; J4a/J4b close cross-role N-way contention; J5 closes within-role instance-pair contention; J4 observes policy choices on the now-characterized stack.
- **J4b and J5 matrix benches** must run ALONE on the host and honor `feedback_no_concurrent_inference`. They are the highest stack-conflict risk in this Package and are required before using cross-role concurrency to speed up the remaining inference backlog.
- **Affinity repair outranks matrix reuse**: if live affinity differs from `NUMA_CONFIG`, the matrix is stale even when `topology_hash` matches. Reload/fix the affected role first, then rerun all matrix evidence involving that role/shape before J4/J6 or downstream parallel bulk work.
- **Optional frontdoor Half1 exploration is out-of-band**: do not add or assume a second half frontdoor inside the repair path. If pursued, create a separate topology experiment after current matrix repair: add Half1 port/config, validate affinity, measure Half0+Half1 and Half0/Half1+quarters against current q0-q3 policy, update `topology_hash` and rederive the matrix before use.
- **J6 (production rollout)** is 24-hour passive once flipped; can start as soon as J4a/J4b/J5 are done and any J4c policy wiring needed for bulk scheduling is in place.
- **J7 and J9** are independent of the WP implementation work but should run after J1-J3 so they inherit safe fan-out. J7 is an autopilot-style eval against the production stack; its DCP-4 hook is already built, and DCP-6a code is landed but must be server-reloaded/attested at a clean deploy boundary before inference. J9 is closed diagnostic-only as of 2026-06-12. **J8 is optional** because edit-transaction mode solved the practical BEP-2 blocker; keep it out of the critical run order unless its result would change the legacy batch-edit path's keep/retire/task-scope decision.

##### Execution manifest template

Before launching the nonstop bulk train, create a run manifest with one row per task/gate. A JSONL file is preferred for machine checking; this table defines the required fields.

| Field | Required | Notes |
|-------|----------|-------|
| `run_id` | yes | Stable id shared by logs, artifacts, and progress notes. |
| `task_id` | yes | Package task id such as `J1`, `J4b`, `H7`, `I1`. |
| `allowed_concurrency_mode` | yes | `serial`, `same_trial_eval_fanout`, `cross_role_matrix_allow`, `observe_only`, or `isolated_bench`. |
| `required_topology_hash` | yes for concurrent/bench tasks | Must match runtime before launch. |
| `live_affinity_verified` | yes for concurrent/bench tasks | Boolean. True only after every live llama-server PID in scope has thread affinity exactly matching `NUMA_CONFIG` for its role/index. |
| `affinity_artifact` | yes for concurrent/bench tasks | Path to captured port->pid->expected-cpus->observed-cpus evidence. |
| `matrix_status` | yes | `not_required`, `preclosure`, `closed_world`, `stale`, or `diagnostic_only`. |
| `flags` | yes | Feature flags and env vars used for the task. |
| `command` | yes | Exact command or script invocation. |
| `output_path` | yes | Primary artifact directory/file. |
| `journal_quarantine_rule` | yes | When results must be kept out of baselines/Pareto/scheduling priors. |
| `pass_fail_gate` | yes | Concrete metric threshold or artifact condition. |
| `next_action` | yes | Continue, rerun, serialize downstream, stop, or open follow-up. |

Minimum manifest example:

```json
{"run_id":"bulk-2026-05-26-j4b","task_id":"J4b","allowed_concurrency_mode":"isolated_bench","required_topology_hash":"<hash>","live_affinity_verified":true,"affinity_artifact":"data/contention_matrix/<run_id>/live_affinity.json","matrix_status":"preclosure","flags":{"feedback_no_concurrent_inference":true},"command":"python scripts/server/contention_matrix.py ...","output_path":"data/contention_matrix/<run_id>/","journal_quarantine_rule":"diagnostic_only_until_closed_world","pass_fail_gate":"all candidate_sets measured or excluded; CV <= 0.05; live affinity exact-match","next_action":"J5 if pass; stop if topology drift, affinity drift, or unmeasured bucket remains"}
```

##### Baseline mutation rule

Baseline mutation is opt-in, never implicit. A run is baseline-eligible only if:

- `speed_metric_mode` is present and matches the evaluation shape.
- `topology_hash` matches the manifest and matrix artifact.
- `live_affinity_verified=true` for any run that depends on the contention matrix.
- `matrix_status` is `closed_world` for cross-role parallel runs, or `not_required` for serial/same-trial-only runs.
- Same-trial EvalTower fan-out records `eval_concurrency`, median per-request t/s, aggregate batch t/s, and eval wall time.
- Cross-role concurrent runs record the exact active-set verdict id and launch only `allow` sets.

Everything else is diagnostic-only. Diagnostic-only data can be summarized in progress reports, but it must not update production baselines, Pareto archives, regression thresholds, learned scheduling priors, routing speed priors, or future trial scheduling evidence.

##### Resume protocol

If the long-running session is interrupted:

1. Read the latest `progress/YYYY-MM/*.md` entry and the run manifest.
2. Verify the current orchestrator git sha, stack state, and topology hash before relaunching anything.
3. Inspect the last produced artifact, not just the final log line or process exit status.
4. Rerun only idempotent preflight steps automatically: py_compile, unit subset, health checks, topology hash capture, and J4a dry-run enumeration.
5. Continue from the first incomplete gate in the manifest.
6. Keep partially completed throughput benches quarantined unless every sample, CV, ratio, verdict, topology hash, and artifact path is present.
7. If topology hash, live affinity, or matrix status changed, stop cross-role parallelism and return to J4a/J4b before downstream bulk work.

##### Other agents' inference-gated work — add here

This Package is designed to absorb additional inference-gated items from parallel agents so one operator-sitting window clears multiple. Append rows below (or open a Package K for a separate window). Suggested format: same table columns; surface dependencies in this sequencing section if any.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| J10 | URE-1 routing-uncertainty calibration | [decision-aware-routing.md](routing-program.md) URE-1 | Enable `ORCHESTRATOR_URE_UNCERTAINTY_SHADOW_LOG=1`; passively collect shadow routing-uncertainty records over normal traffic; compute ECE/AUC for "would escalation help?", abstention precision/recall, per-suite calibration drift. Pre-enforcement gate: ECE ≤ eval-tower P8 target + abstention precision > baseline escalation precision + ≤10% latency regression. **Shadow-only** — needs no dedicated window. Prereq: URE-1 shadow logger wired (approval_record schema done in `src/trace/harness_schema.py`). | none extra (shadow on existing frontdoor/escalation traffic) | passive collection + ~1h analysis |
| J11 | BSV-2 behavior-signature differential testing | [autopilot-continuous-optimization.md](autopilot-program.md) BSV-2 | Before promoting a mutation, run new-vs-old paired on the same sentinels (sequential under identical model snapshot preferred; parallel only if explicitly approved per `feedback_no_concurrent_inference`); compare behavior_signature diff severity (benign/watch/blocking) + scalar score; gate accept on both. Catches silent Pareto-win regressions a scalar misses. Prereq: BSV-1 partial archive-member observe wiring is now on main (`9a175eac`, default-off, `trial:<id>` archive IDs + compact signature index), now prefers per-question `question_results` sentinel outcomes before falling back to per-suite proxies (`31e7e008`), has a read-only same-question BSV paired report scaffold (`0943e7c0`), and can feed standalone paired-run EvalResult-like JSON artifacts into the same report via `eval-result-pair` (`5b29eead`). Remaining prerequisite is the paired inference runner plus full-enough trace/answer/tool evidence before accept-loop enforcement. | autopilot eval stack | paired eval per candidate mutation |
| J12 | chat_template_kwargs empirical probe + THINK-ABL-1 | epyc-orchestrator `cac4148` (chat_template_kwargs passthrough merge), later registry/production-backend wiring tests, and [x-mas-text-routing.md](routing-program.md#track-x-mas-text-routing) | **Non-inference wiring is CLOSED 2026-06-12**: registry-driven `chat_template_kwargs` auto-populates per-role defaults, production `LlamaServerBackend` forwards them on `/v1/chat/completions`, and chat-completions role selection shares one source of truth. Focused verification: `uv run pytest tests/unit/test_registry_chat_template_kwargs.py tests/unit/test_llama_server.py::TestLlamaServerBackend::test_chat_completions_stream_forwards_registry_chat_template_kwargs tests/unit/test_chat_completions_roles.py -q` -> 6 passed. 2026-07-06 clean-window probe is CLOSED in `epyc-orchestrator/orchestration/reports/j12_think_loop_probe_20260706T143621Z/`: frontdoor `15/15`, architect `14/15`, and `0` empty outputs / errors / `<think>` leaks / known wait-reference loops / repetition loops. No architect flip revert trigger. Remaining empirical work: THINK-ABL-1 with a non-no-op suppressor for ingest (`/no_think` or empty-`<think></think>`) at fixed non-truncating `max_tokens`, same tasks both arms; ingest result decides only the THINK-ABL-1 policy. | ingest_long_context plus comparison roles as needed | ~1h ablation |
| J13 | P17.BT-3 axis-vote BT tiebreak falsification | [autopilot-continuous-optimization.md](autopilot-program.md) § P17 BT-3 (epyc-orchestrator commits `2e51c86` + `60ed552` + `45df95c` + `56ee9fc` range-normalization fix; prompt cleanup `b8c0611`) | **CLOSED 2026-06-12** from existing journal data; **cleanup landed 2026-06-13**. Sample size passed (341 rich/stagnation-fired trials, 75 logged disagreements), but the exact seed-outcome gate is not measurable because journal/log artifacts do not persist BT top ID, hypervolume-top ID, or planner-followed seed. Proxy outcomes do not clear the positive-signal threshold. Do not queue P17.BT-4; the cosmetic rich-prompt `bt_tiebreak_hint` has been removed. | autopilot eval stack (no new models) | closed |
| J14 | DAR-6.5 swarm-fanout adversarial-robustness A/B | [decision-aware-routing.md](routing-program.md) § DAR-6.5 | **Note 2026-09-16: `dispatch_swarm_fanout` / `src/swarm_fanout.py` no longer exist. They were deleted in orchestrator `771348c8` (2026-06-16), so the prereq ✅ marks below are historical and J14 must rebuild the dispatcher first.** 2-arm A/B on a chosen injection suite (Garak / HouYi / PromptInject — pick one with active maintenance + Apache/MIT licence). Arm A: existing single-model escalation. Arm B: N≥2 heterogeneous concurrent serves via `dispatch_swarm_fanout` in `src/swarm_fanout.py`, aggregated via the shared BT module (`src/bradley_terry.py`). Replicates intake-615's published 0.12% vs 6.20% prompt-injection-degradation claim on our own suite. Pre-enforcement gate: ≥3pp absolute reduction in injection-success rate AND ≤30% per-stream throughput regression at the swarm-fanout setting. **Prereq status (2026-05-28)**: (1) P26.1 BT module ✅ (`src/bradley_terry.py`); (2) DAR-6.1 feature flag ✅ (`features().swarm_fanout`, default-off), DAR-6.3 dispatch ✅ (`dispatch_swarm_fanout`), DAR-6.4 BT-aggregator ✅ (`bradley_terry_aggregate`) — all in epyc-orchestrator commit pending; (3) injection-risk classifier is now explicitly tracked as [routing-intelligence.md](routing-program.md#track-routing-intelligence) RI-13, but should **not** be built before the cheap-first unconditional J14 A/B clears its gate. | 2-3 heterogeneous concurrent serves (e.g., gemma4-26B-A4B + qwen3.6-35B + qwen3-coder, depending on injection-suite topic) + injection eval harness + a pairwise judge model OR the included `length_proxy_aggregator` baseline (the latter is documented as a deliberate weak baseline — see `src/swarm_fanout.py:length_proxy_aggregator`) | 1-2 days A/B harness assembly + one eval run (DAR-6.1/6.3/6.4 are no longer in this estimate — already ✅) |
| J15 | MD-9 deep_research_mode sentinel A/B | [minddr-deep-research-mode.md](minddr-deep-research-mode.md) MD-9 | Phase 1 MindDR readiness gate. Sentinel suite at `orchestration/deep_research_sentinel.yaml` (20 curated queries: 7 BrowseComp + 7 WideSearch + 6 mixed); each query is pre-tagged `is_research_like=True`. Run the suite with `ORCHESTRATOR_DEEP_RESEARCH_MODE=0` (control) then `=1` (treatment), score on the four NaN-safe rubric fields already wired into `EvalResult` (`rubric_reasoning_trajectory`, `rubric_tool_calls`, `rubric_outline`, `rubric_content_stage`). Promote to production default iff uplift ≥+5pp on the aggregate rubric AND no regression on the existing eval-tower sentinels. **All prereqs already landed 2026-04-22** (MD-1 flag, MD-2 classifier, MD-3/4/5 prompts, MD-6 pydantic_graph subpackage, MD-7 EvalResult rubric stubs, MD-8 sentinel suite). The LLM-as-judge scoring functions themselves are tracked separately as EV-9 in [`eval-tower-verification.md`](eval-tower-program.md) (also inference-gated; if EV-9 hasn't landed at J15 run-time, fall back to structural-only scoring against the `expected_contains` hints baked into the sentinel YAML). | frontdoor + worker_coder + web-research backend (per the three-agent pydantic_graph pipeline) | ~1 day inference + ~2h analysis |
| J16 | RI-ITG-1 ingest-triviality guard A/B | epyc-orchestrator `9203c00` (flag `INGEST_TRIVIALITY_GUARD`, default OFF, depends on `specialist_routing`) + [x-mas-text-routing.md](routing-program.md#track-x-mas-text-routing) § "Follow-up validation" | The learned MemRL router leaks ~8.5% of ingest_long_context traffic as trivial short prompts (153/1803 math in the 2026-05-30 tap analysis) — a ~19× latency tax (80B @ ~6.4 t/s) for work a cheap role answers identically. `apply_ingest_triviality_guard` demotes ingest→`worker_general` ONLY for positively-trivial requests (difficulty band ≠ medium/hard AND short AND no long-context). 2-arm enforce A/B vs flag-off baseline on the eval-concurrency fan-out; also enable `difficulty_signal` shadow/enforce so the easy-band path is live. **Gate**: ingest short-prompt leakage materially reduced AND **zero accuracy regression** vs baseline; long-context + short-but-hard reasoning routes unchanged. Then consider default-on. | frontdoor + ingest_long_context + worker_general (existing stack; no new models) | ~1-2h enforce A/B + ~1h analysis |
| J17 | Internal-interaction-lifecycle P2 consult A/B (`review_before_commit` at the edit-transaction seam) | [internal-interaction-lifecycle.md](routing-program.md#track-internal-interaction-lifecycle) P2 + P2-0 design note (2026-05-31) | 2-arm A/B at `epyc-orchestrator/src/edit_transaction.py:199` `run_edit_transaction()`, between the one-shot draft `llm_call()` at `:209` and `apply_edit_transaction()` at `:211` (chosen attach point per P2-0). Arm A = baseline (`features().consult_skills_enabled.review_before_commit=false`); Arm B = `=true` with `consult(consultant_role="architect_general", requester_role="coder_escalation", skill="review_before_commit", ...)` between draft and apply, integrating advisory with one re-run cap when `blocking_issues` non-empty AND `confidence ≥ 0.6`. ≥50 code-edit turns on a fixed eval slice. **Gate to P3**: tokens saved ≥30% on advisory leg; code-edit eval ≤1pp quality drop; `coder_escalation` decode p50 within ±5%; advice cache hit ≥10% on repeated identical-shape edits within 1h; all six handoff invariants (I1–I6) hold under P2 traffic. **Prereqs (HARD, SEQUENTIAL — do NOT trigger before both clear)**: (1) Cross-Role Contention + Placement TRACKING section's autopilot/contention bake clean (this handoff's tail); (2) P1 lifecycle refactor landed + regression gate passed (pytest suite green, `delegation_diagnostics` byte-equal on identical inputs, no wire change to `delegation_events`, no affinity drift, ≥48h autopilot bake). | `coder_escalation` (Qwen3.6-35B-A3B Q8 @ :8071, shared mmap with frontdoor) + `architect_general` (Qwen3.5-122B Q8) + code-edit eval slice harness | ~1d eval slice + ~2h A/B analysis |

**Sequencing of the appended items (intake-607 residual gates + 2026-05-27 P17/DAR-6 additions):**
- **J16 (RI-ITG-1)** is an **active routing change** (enforce-mode demotion), so it **cannot co-run with the passive J6 24h soak** (would contaminate the baseline) — run it as a dedicated cheap eval in a host-quiet window after the matrix gates, like J11/K-EVAL-1. *Partial-fold option*: a shadow/observe mode (log would-demote without demoting) would be observe/advisory and could ride J6 to passively quantify leakage; that mode is **not yet built**, and the accuracy A/B needs enforce mode regardless. THINK-ABL-1 (real thinking ablation for ingest) is **not** a J16 item — it folds into **J12** (same chat_template_kwargs subsystem); see the corrected J12 row above.
- **J10 (URE-1) is shadow-only** — flip the flag and let it accumulate during ANY of J1–J9 or Package I traffic; it shapes no workload and needs no dedicated slot. Analyze once enough decisions accrue.
- **J11 (BSV-2)** runs per-mutation inside the autopilot accept loop; co-runs naturally with J9's autopilot observation window.
- **J13 (P17.BT-3) is CLOSED 2026-06-12** — offline analysis reached a negative/non-certifying verdict; do not queue P17.BT-4. The rich-prompt hint removal landed at `b8c0611` on 2026-06-13 while AutoPilot was paused.
- **J14 (DAR-6.5)** had a real prereq backlog until 2026-05-27 when DAR-6.1/6.3/6.4 scaffolding landed. Remaining prereq is the conditional-routing trigger (DAR-6.2 injection-risk classifier in [`routing-intelligence.md`](routing-program.md#track-routing-intelligence)); cheap-first variant runs unconditional A/B without it, decoupling J14 from the classifier work.
- **J15 (MD-9)** has zero outstanding prereqs as of 2026-04-22 (all of MD-1..MD-8 done). Sentinel YAML + EvalResult rubric fields + pydantic_graph subpackage all present. Can run any time inference window opens; results compare to existing sentinel baselines.
- J10/J11 are gated on their wiring landing (URE-1 shadow logger; BSV-1 partial archive-member observe wiring now on main via `9a175eac`, per-question sentinel preference via `31e7e008`, read-only paired report scaffold via `0943e7c0`, and standalone EvalResult artifact input via `5b29eead`; BSV-2 paired inference runner / accept-loop flag integration still open). J13's P17.BT-2 hint wiring was removed from the live planner prompt after P17.BT-3 closed negative/non-certifying on 2026-06-12; the shared BT algorithm remains available. Schemas + pure algorithms on `15350fe` and orchestrator `2e51c86`+`60ed552`+`45df95c`; prompt cleanup at `b8c0611`. DCP-6/BEP-2/HLE-4 are already covered above as J7/J8/J9 — no duplication.
- **J17 (internal-interaction-lifecycle P2)** has TWO hard sequential prereqs and must NOT be triggered before both clear: (a) the Cross-Role Contention + Placement bake (tracked at the tail of this handoff) — autopilot/contention rollout has to complete so the bake measurement establishes a clean baseline that the P2 invariant checks (I1 region-lock visibility, I6 one-shot only) can compare against; (b) the P1 lifecycle refactor regression gate (zero-behavior-change refactor of `_architect_delegated_answer`, must show byte-equal `delegation_diagnostics` on identical inputs and ≥48h autopilot bake with no `delegation_cache_hits` miss-rate rise). Counter emission for that bake is now live via orchestrator `02a01617` (deployed `2026-07-03T15:40:30Z`): delegated completions persist cache lookup/hit/miss/rate counters and `ContentionDenied` 503s emit `kind="contention_denied"` progress events. Then-and-only-then is the J17 A/B safe to run after the ≥48h counter window is clean. Triggering owner: whichever inference-window operator next has a quiet code-edit eval slice after both prereqs clear — see the Internal Interaction Lifecycle TRACKING section at the tail of this handoff for the live status of (a) and (b).

##### Per-gate conditional workflows + mitigation policies (intake-607 gates J7–J11 — READ BEFORE RUNNING)

Each gate is a **decision point**, not just a measurement: run → branch on the result → apply the mitigation. Deep specs are in the owning handoffs (linked); this is the operator decision tree so the run can proceed in one sitting without round-trips.

**Pre-run wiring status** (none is in production until wired AND its gate passes; all flags default-OFF):
- **J10 / URE-1**: shadow logger **WIRED** (`ORCHESTRATOR_URE_UNCERTAINTY_SHADOW_LOG`) on main (merged 2026-05-26) — runnable now.
- **J7 / DCP-6**: **DCP-1 + DCP-2 discovery + DCP-3 ast-codemap DONE** on main (merged 2026-05-26) and **DCP-4 advisory attach DONE** in the live specialist delegation path (`chat_delegation._maybe_dcp_seed_context`, flag `dcp_pre_assembly`, default-off; validated by `tests/unit/test_dcp4_wiring.py`). 2026-06-12 offline replay closed task-root/file-selection/budget validation; DCP-6a branch `530128b7` then fixed content-depth/freshness and replayed clean on the current live lineage; equivalent code landed at `2e2e0d3`. 2026-06-19 launch-code provenance check is satisfied (`server_launch_git_sha=eeb8cce`, current API `git_sha=27e09a1`), but operational attestation remains caveated. `29b9ba3` adds the real A/B runner. Remaining work is clean running-state attestation, then inference A/B.
- **J8 / BEP-2**: optional legacy path. `_execute_turn` batch divergence + sandboxed patchset path are wired behind `ORCHESTRATOR_BATCH_EDIT_MODE`, but the active remediation path is already the `force_mode="edit"` transaction, not this batch-vs-interleaved A/B.
- **J9 / HLE-4**: `EvalResult`/journal extension is DONE (`931e43c`), rule-based HLE-1 metric computation + HLE-2 oracle-adequacy registration are DONE (`9222a19`), and the 2026-06-12 metric-validity analysis is DONE. Shared trace schema is done. Current verdict: dashboard/advisory only; no Pareto promotion from the current proxies.
- **J11 / BSV-2**: BSV-1 partial archive-member observe wiring is on main (`9a175eac`, default-off), now prefers per-question `question_results` sentinel outcomes before falling back to suite proxies (`31e7e008`), has a read-only paired behavior report over same-qid journal vectors (`0943e7c0`), and can compare standalone paired-run EvalResult-like JSON artifacts through `eval-result-pair` (`5b29eead`). It still needs the paired inference runner and full-enough trace/answer/tool evidence before it can gate accepts. Compute (`compute_behavior_signature`, `diff_signatures`) done.

**J8 — BEP-2 batched-edit A/B (optional decision experiment; NOT on the critical remediation path):**
- **What it decides**: whether the legacy structured patchset/batch-edit mode is worth keeping as a task-class knob, retiring, or preserving only for provenance/large-repo patch-economy cases.
- **What it does not decide**: whether Qwen3.6 can complete multi-file coding tasks, and whether the edit-transaction remediation works. Those were already answered by the direct one-shot ablation and the edit-mode unit/module/server validations.
- **Run J8 if** the answer would change `batch_edit_mode` ownership: keep/retire decision, large-repo/full-file-cost concern, need for structured-patch provenance, or evidence for BEP-3 task-class routing.
- **Defer J8 if** the immediate goal is routine coding completion reliability, because `force_mode="edit"` is the higher-leverage shipped path and J7/J11/J15 are more directly actionable in scarce inference windows. J9 and J13 analyses are already closed.
- ✅ batch cuts end-to-end latency ≥15% AND quality within −1pp AND parse-failure ≤5% AND apply-failure ≤2% (whole-repo verify) → keep the legacy batch flag available for narrow task-class experiments; do **not** displace edit-transaction mode without a separate rollout decision.
- ⚠️ latency win but quality −1..−3pp OR parse/apply failures 5–15% → do NOT promote; keep the legacy flag off and treat the result as parser/prompt hardening evidence only.
- ❌ no latency win OR quality < −3pp OR failures >15% → retire the legacy batch-vs-interleaved path; record NEGATIVE in the handoff + intake-605. This does **not** invalidate the shipped edit-transaction remediation.
- **Mitigation**: flag-off = instant rollback; **every apply is in a sandbox/worktree (BEP-5), never production files, until whole-repo verify passes AND accept**; stale-base rejection; parse=None/invalid → fall back to the normal REPL loop (zero behavior change).

**J7 — DCP-6 delegation pre-assembly eval (run advisory-first: bundle attached, reactive discovery still on):**
- Prereq before inference: clean running-state attestation with launch marker containing `2e2e0d3` or later; the isolated replay already showed full-small-file/padded ranges, per-file `content_sha256`, 100% line coverage, and 0 missing hashes. The 2026-06-19 attestation satisfied launch-code provenance but did not satisfy the clean-running-state gate.
- ✅ prefill+latency down AND quality ≥ baseline AND top-up rate ≤20% → keep advisory; consider seed-bundle-primary mode after a second confirm.
- ⚠️ quality flat but top-up rate >20% → packer under-selecting; tune discovery depth / ColGREP top-k / budget; re-run.
- ❌ quality drop OR no latency improvement → keep reactive discovery; shelve pre-assembly; flag off.
- **Mitigation**: flag-off; advisory mode never removes reactive discovery; top-ups always allowed (no hard firewall); bundle freshness (repo_sha/content_sha256) re-checked per delegation.

**J9 — HLE-4 harness-metrics observe-only (no Pareto promotion during the run):**
- **2026-06-12 result**: the observation window already happened. 580 metric-bearing trials showed `execution_fidelity` cleanly separates keep/revert (`r=0.52`, keep mean `0.851` vs revert `0.731`) but strongly mirrors quality/reliability (`r=0.83`/`0.89`). `planning_stability` separates keep/revert even more (`r=0.84`, keep mean `0.988` vs revert `0.623`) but is derived from the same safety verdicts, so it is useful as a sanity dashboard/advisory signal, not an independent objective. `feedback_interpretation` is low-confidence/low-variance; `memory_coherence` is constant; `recovery_rate` is missing on 99.3% of rows.
- Decision: keep all current HLE metrics diagnostic/advisory only. Do **not** promote any J9 metric to Pareto selection or hard guardrail until N2 per-question ledgers/sequential verdicts land and a redesigned metric demonstrates independent predictive signal.
- **Mitigation**: observe-only first; low-signal/low-confidence metrics never gate; oracle-adequacy flags shortcut-prone suites so they can't drive promotion.

**J10 — URE-1 calibration (shadow → enforce; J10 itself only collects + analyzes):**
- ✅ ECE ≤ eval-tower P8 target AND abstention precision > baseline escalation precision AND ≤10% shadow latency regression → enable uncertainty-routed escalation (separate enforce flag) + optionally URE-3 (uncertainty as a frozen-label routing feature).
- ❌ any gate fails → stay shadow-only; recalibrate (re-weight components / threshold) on a frozen shadow set; do NOT enforce.
- **Mitigation**: calibration-precedes-enforcement; shadow→enforce is a separate flag flip; frozen shadow-calibration set; re-run calibration after any DAR-3/DAR-4 change to avoid a feedback loop.

**J11 — BSV-2 differential testing (mutation accept gate; per candidate mutation):**
- `benign` → auto-accept; `watch` (route/tool changed, outcomes equal) → accept + log; `blocking` (prior-pass sentinel regressed, forbidden shortcut appeared, or cost guardrail crossed) → **REJECT, do not promote**; if it touches a shared subsystem → BSV-3 conflict-ledger review.
- **Mitigation**: gate accept on BOTH scalar regression AND signature severity; partial-confidence signatures cannot certify `benign`; git-committed revert remains the backstop.

**J13 — P17.BT-3 axis-vote BT tiebreak falsification (offline post-run analysis):**
- **2026-06-12 result**: sample requirement passed (341 rich/stagnation-fired trials, 75 logged disagreement events), but the exact BT-picked-seed vs hypervolume-top-seed comparison is not measurable from current artifacts. The journal stores only `"BT-tiebreak disagrees with hypervolume top"`; logs/planner archive do not retain the `BT picks trial #... (rank-by-hv would pick #...)` line or whether the planner followed either seed.
- Proxy outcomes are not enough to keep investing: current-trial frontier rate was 2/75 (2.7%) for BT-disagreement events vs 9/266 (3.4%) for rich no-disagreement events; cluster-start next-10 frontier rate was 1/7 (14.3%) vs 8/34 (23.5%) for thinned no-disagreement rich prompts. Overlapping raw windows showed 23/75 next-10 frontier hits, but those are dominated by long repeated disagreement clusters and cannot certify the seed-level gate.
- Decision: treat P17.BT-3 as negative/non-certifying. The `bt_tiebreak_hint` block was removed from the rich-prompt template at `b8c0611`; do **not** queue P17.BT-4 unless a future explicitly-instrumented run persists BT top ID, hypervolume-top ID, chosen seed/action lineage, and then shows positive signal.
- **Mitigation completed**: the live planner prompt no longer carries the cosmetic hint. Failure mode is closed for future restarts; the shared BT helper remains for offline diagnostics and non-AutoPilot consumers.

**J14 — DAR-6.5 swarm-fanout adversarial-robustness A/B (publishability falsification):**
- ✅ ≥3pp absolute reduction in injection-success rate AND ≤30% per-stream throughput regression at the chosen N=2 or N=3 swarm-fanout setting → enable the routing mode (separate enforce flag); also queue work on the conditional injection-risk classifier in [routing-intelligence.md](routing-program.md#track-routing-intelligence) so swarm-fanout is reserved for high-risk prompts rather than always-on.
- ⚠️ Reduction in injection-success rate present but <3pp OR throughput regression 30–50% → keep DAR-6 code path but stay shadow-only; revisit if (a) lighter peer models (8B specialists) emerge from swarm-dataset-distillation or (b) hardware changes.
- ❌ No measurable reduction OR throughput regression >50% → **kill DAR-6 swarm-fanout mode**; document the kill in DAR § DAR-6 with the exact A/B numbers; the BT module remains available for the autopilot P17 and distillation P3 consumers.
- **Mitigation**: cheap-first variant runs the A/B unconditionally on a fixed injection-prompt set BEFORE building the conditional-routing trigger; this isolates "does swarm-fanout reduce injection success at all?" from "is our routing classifier good enough to gate it?"

**J15 — MD-9 deep_research_mode sentinel A/B (Phase 1 promotion gate):**
- ✅ Aggregate rubric uplift ≥+5pp on `deep_research_sentinel.yaml` AND no regression on existing eval-tower sentinels → set `deep_research_mode` production-default ON for queries matching `is_research_like()`; queue MD-7 LLM-as-judge wiring (EV-9 in [`eval-tower-verification.md`](eval-tower-program.md)) if it wasn't already landed.
- ⚠️ Uplift 0–5pp OR regression on a sub-rubric (e.g., `tool_calls` worse but `outline` better) → keep `deep_research_mode` flag available but stay default-off; the rubric breakdown is the trigger for MD-3/4/5 prompt iteration before re-running.
- ❌ Uplift ≤0pp OR meaningful regression on existing sentinels → leave flag default-off; record the kill in [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md) with rubric-level numbers; Phase 2 (RL) becomes unmotivated.
- **Mitigation**: flag-off is the default state; routing classifier `is_research_like()` shadow-logs without altering routing today (per MD-2); the pydantic_graph subpackage at `src/graph/minddr/` is decoupled from production `src/graph/` so a kill is just "stop calling the new entry point" — no rollback of routing infra needed.

---

#### Package K: Audit-Batch Code-Ready Inference Gates (2026-05-27)

**Origin**: the 2026-05-27 `/research-intake` of agent-oss (intake-610–613) prompted an audit of `research-evaluation-index.md` + `pipeline-integration-index.md` for work that is *not* inference-gated. All code scaffolding was implemented that session (see `progress/2026-05/2026-05-27.md` + `research/deep-dives/2026-05-27-agent-memory-cluster.md`). The RUNS below are now unblocked — code has landed, models/datasets are downloaded or have a one-line fetch noted. **Independent of Package J** — pick up in any stack window; none block J.

**Stack required**: varies per row (most need only individual model servers, not the full orchestrator).

| Task | Code prereq (DONE this session) | Inference run / gate |
|------|----------------------------------|----------------------|
| **K-RAG-1** — KB-RAG hybrid-signal eval (K7 + K9/K10) | `kb_rag.query()` recency+rerank params (`src/retrieval/kb_rag.py`); `src/retrieval/cross_encoder.py`; cross-encoder ONNX on disk at `/mnt/raid0/llm/models/ms-marco-minilm-l6-v2-onnx`; 21 unit tests pass. 2026-06-12 diagnostic used `/mnt/raid0/llm/pace-env` because orchestrator `.venv` is missing `onnxruntime`; stale index had 137 files / 4,634 chunks, max mtime 2026-05-30. | Formal K7 is not yet runnable/decision-grade: add/locate the HotpotQA/LoCoMo-style query set + harness, restore `onnxruntime` in orchestrator `.venv` or bless `pace-env`, refresh the KB index, then sweep `KB_RAG_RECENCY_WEIGHT` / `KB_RAG_RECENCY_SIGMA_DAYS` / `KB_RAG_RERANK=1` / `KB_RAG_RERANK_WEIGHT`. Gate: any config beats the MaxSim-only baseline on doc-recall@{3,5,10} by >2pp (Flywheel ~1pp noise floor). Do not promote default weights from the tiny diagnostic. |
| ✅ **K-EMB-1** (P9) | A-fast fallback corpus + dry-run harness are verified (`100` docs, `30` queries, no missing refs); HF sources and conversion env are staged; warm/default-off embedder server recipes for Granite, multilingual-e5-base, and BGE-M3 landed in orchestrator `e2922d7`; GGUF conversion/quantization completed 2026-07-03; Phase B fallback-corpus bench passed 2026-07-20 — see `granite-97m-r2-bench-plan.md` | `BULK-K-EMB-1` DONE_PASS: Granite Q8_0 recall@10 `0.9333`, recall@50 `0.9889`, nDCG@10 `0.8382`, wall `1.213s` vs e5 `2.651s`, BGE-M3 `7.037s`, BGE-large `13.749s` under common 512-char policy. Remaining work is Phase C dense-retriever decision / optional 32K+rereanker extension, not another Phase B rerun. |
| ~~**K-EVAL-1**~~ → **FOLDED INTO H5 (2026-06-12)** | EV-3 `scoring_verifiers` adapter DONE (`scripts/benchmark/scoring_verifiers_adapter.py`, registered in `dataset_adapters.py`+`suites.py`); 2026-06-19 validation confirms the local snapshot loads 6,701 candidate-level verifier items with 3,395 correct / 3,306 incorrect labels after research `7c11920`. | **Single owner: H5 / [eval-tower-verification.md](eval-tower-program.md) EV-4.** This row was a duplicate of H5's ECE/AUC calibration baseline on Scoring-Verifiers — do NOT schedule it separately (struck to avoid double-scheduling). Runs in Queue 3 after the per-question ledger lands. |
| ✅ **K-MEM-1** (P3b) | `tulving_episodic` suite adapter + deterministic F1 scorer landed (`scripts/benchmark/tulving_episodic_adapter.py`); 77 unit tests. 2026-06-18 prep: Figshare data extracted at `/mnt/raid0/llm/data/eval/tulving_episodic/`, adapter selection hardened to the documented Claude 20ch/456-QA slice, benchmark extras now include parquet deps, `suites.load_suite("tulving_episodic")` bridges adapter suites into `run_benchmark.py`, and prompts are self-contained with the selected book narrative prepended. 2026-06-19 post-run scorer `scripts/benchmark/score_tulving_run.py` landed in research `8249be9` for Simple Recall / Chronological Awareness report generation from raw run JSON. | **Completed/scored 2026-06-20**: raw run packaged in research `b6edc64`; corrected score and failure report in research `9e63af0` after parser repair. Run `20260619_141212`, `ingest_long_context`, production/default experts via `--skip-moe-reduction`; `456/456` scored, avg F1 `0.4309`, Simple Recall **`0.5684`** (scorer v2, M-12e research `dcb769c1`: over the 366 `get=="all"` questions with event-count bins; the originally quoted `0.5530` was scorer v1, computed over all 456), Chronological Awareness `0.1593` (unchanged under v2; 37/45 tau questions now fail closed for partial coverage), avg decode `17.27 t/s`, preflight all passed. Result is mixed: usable lexical recall, weak event/detail and chronology, and zero-answer hallucination failure. Research `2eb94f8` adds the targeted 120-row follow-up manifest; next action is to run that repair slice in a clean window, not route/memory promotion. |
| **K-DIV-1** (EV-8) | `diversity_metrics` + 5 `EvalResult` fields wired (`scripts/autopilot/diversity_metrics.py` + `safety_gate.py`; `src/` side pre-existing); 50 tests | Baseline diversity pass on 4 production roles; populate the SafetyGate two-tier WARN/REJECT thresholds (semantic-embedding-agreement needs an embedder pass). |
| **K-ROPE-1** (P10.2) | `scripts/benchmark/rope_position_probe.py` (`--dry-run` verified) | 5 models × 4 context lengths (4K/8K/16K/32K), 100 samples/cell ≈ 100 min. LOW priority, **bulk-pickup eligible**. Record collapse-point per model into the RoPE deep-dive appendix. |
| **K-SKILL-1** (EV-10a/b) — skill-efficacy gate validation | **Default-off live-branch wiring landed 2026-06-13** in epyc-orchestrator `924ca50`: `scripts/autopilot/actions.py` runs the no-artifact pre-mutation eval arm when `AUTOPILOT_SKILL_EFFICACY_GATE` is enabled, compares post-mutation per-suite deltas through `evaluate_skill_efficacy`, attaches `eval_result.details["skill_efficacy"]`, and reverts prompt/GEPA/code mutations before epoch acceptance if the gate rejects. Decision logic remains in `scripts/autopilot/skill_efficacy.py` (`evaluate_skill_efficacy`/`_split` negative-delta guard + dev/test discipline; surrogate `proxy_reward`/`feedback`/`require_cross_family`). Validation: 43 focused tests passed; ruff check/diff-check passed on changed files. | Remaining **restart/validation** work: deploy/restart with the flag default-off unless deliberately measuring it, then run a paired A/B over PromptForge mutations with `AUTOPILOT_SKILL_EFFICACY_GATE` isolated from `AUTOPILOT_BSV2_ACCEPT_GATE`. **Gate**: the negative-delta guard flags ≥1 real per-suite regression that aggregate-only acceptance would have admitted (the SkillsBench 16/84 pattern), AND accepted edits show no held-out-split regression beyond threshold. EV-10b surrogate scoring still needs verifier-LLM assertion authoring (cross-family, inference). The N2/J11 restart bundle is rebased onto live W7 tip `9e5d861` at `c63816b`; keep that lineage for deployment. Source: [eval-tower-verification.md](eval-tower-program.md) EV-10 + [meta-harness-optimization.md](../completed/meta-harness-optimization.md) § 2026-05-27. |

**Run-command note**: each adapter is registered as a named suite, so existing seeding/eval harnesses pick them up by suite name (`scoring_verifiers`, `tulving_episodic`). K-RAG-1 + K-ROPE-1 are standalone scripts (env-var-swept / `--context-length` per cell). **K-SKILL-1 is the exception** — it is not a suite run; its default-off accept-path wiring exists, but validation is a flag-isolated paired-mutation A/B after the restart bundle, so it cannot be picked up turnkey like the others. Per `feedback_speed_verify_via_llama_bench` + `feedback_no_concurrent_inference`: the user/campaign runs these manually with per-run approval — code is prepared, not executed.

**K-RAG-1 seed sweep update (2026-06-19)**: the CPU-only K7 seed sweep ran during
the active AutoPilot window without touching llama servers:
`uv run python scripts/kb_rag/cli.py eval --output-dir
data/kb_rag/eval/k7_seed_20260619T0411Z` in `epyc-orchestrator`. The ignored
derived artifact contains 20 cases, 6 configs, no missing evidence files, index
stats 142 files / 4,958 chunks, and `onnxruntime 1.26.0` working in the
orchestrator venv. Best recall@10 was `0.300` for `rerank_w0.3`,
`rerank_w0.6`, and `recency_w0.1_s90_rerank_w0.3` vs MaxSim baseline `0.275`
(+2.5pp on the seed suite). Treat this as a seed-suite positive for rerank, not
a final default-weight promotion; the case file itself says it is not the final
50+20 certification pool.

---

#### Reporting

After each Package completes:
1. Update the task checkboxes in this file
2. Update the relevant domain index (routing, research, pipeline, hermes)
3. Update [`master-handoff-index.md`](master-handoff-index.md) priority queue
4. Add session to `progress/YYYY-MM/YYYY-MM-DD.md`

When all Packages complete:
- Move this handoff to `handoffs/completed/`
- Extract reusable findings to docs/research
- Update `CHANGELOG.md` with key results

---

#### Cross-Role Contention + Placement (shape-keyed-contention-gating) — TRACKING [added 2026-05-30]

Sibling to **Package J** (within-role placement). Where Package J makes *one role* fan out across disjoint quarters, this work (`handoffs/active/numa-placement-and-contention.md`) makes *different roles* co-reside on disjoint shapes — closing the seeder's non-work-conserving gap (heavy node-half runs while q2/q3 sit idle).

**State:** Part A + A-1 CODE-COMPLETE, and Step 1 is staged in `orchestrator_stack.py` to default `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` on the next API reload. Part B is now end-to-end code-complete/default-off: dispatch passes real `candidate_topology_idx` values to the authoritative shape-aware gate when both flags are armed, with 146 affected tests green. Live traffic is unchanged because `ORCHESTRATOR_SHAPE_AWARE_CONTENTION` is off and the API was not reloaded. C remains prep only (`select_backfill_candidate`); heavy veto/barrier/pressure-skip are untouched.

**⏳ ACTION ON J6 END (do immediately):** the live-observation gate must run *while the stack is quiesced*, in a flag-on bracket, then either revert or deliberately mark an epoch before resuming. Sequence: autopilot clears → reload orchestrator so the staged `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` default is live → verify `/proc/<api_pid>/environ` → run the multi-role fan-out helper from orchestrator `937e6446` (`.venv/bin/python scripts/benchmark/placement_fanout_probe.py --roles frontdoor,ingest_long_context --n 4 --mode concurrent --out /tmp/step2_cross_role_fanout.json`) → confirm region-lock dashboard shows heavy+light on disjoint shapes + queue-on-overlap → bracket `ORCHESTRATOR_SHAPE_AWARE_CONTENTION=1` smoke for Step 2 (disjoint quarters admit; true q-overlaps queue). Adopting flag-on for production traffic is a SEPARATE decision requiring a `mark_epoch`/archive reset, not a silent resume.

**Cross-ref:** Package J (`within-role-placement-state-machine.md`) J7 is the within-role analogue (`ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1` rollout); this is the cross-role layer above it.

---

#### Internal Interaction Lifecycle (consult sibling) — TRACKING

Sibling tracker for [`internal-interaction-lifecycle.md`](routing-program.md#track-internal-interaction-lifecycle); the inference-gated A/B it lands here is **J17** (above). J17 was double-hard-gated on (a) the Cross-Role Contention + Placement bake and (b) the P1 lifecycle refactor/regression bake. Those gates cleared by 2026-07-07, and the J17 live A/B then ran.
Attach point chosen (P2-0): `edit_transaction.py:199` `run_edit_transaction()` between draft parse `:210` and apply `:211`; requester `coder_escalation` / consultant `architect_general` / skill `review_before_commit`.
- [x] **J17 executed** ✅ 2026-07-07. Artifact `epyc-orchestrator/orchestration/reports/internal_interaction_j17_ab_20260707T011136Z/` shows the simple BEP slice tied baseline at `40/50`, while consult added latency, produced `0` rerun requests, and had `0.0` cache-hit rate. Follow-up targeted artifact `epyc-orchestrator/orchestration/reports/internal_interaction_j17_ab_20260707T121211Z/` shows the high-risk edit slice improved `35/50 -> 40/50` with `15` rerun requests, mainly rescuing parser/data-contract edge cases. Outcome: keep `review_before_commit_consult` default-off, but proceed toward a high-risk edit-shape gate rather than blanket HOLD.

#### Research Intake Update — 2026-07-17 (OP-6 reviewer-plane baseline window — staged for clean-window pickup)

**Operator gate**: runs ONLY after §A00 **OP-6 (a)+(b)** approval (master index). One quiesced window (~1.5–2h), AutoPilot stopped, **REFERENCE lineup only** — relaunch as-was (122B-Q4 architect / 35B frontdoor / gemma workers; reviewer aliased to architect_general; GLM-5.2 NOT resident), kernel per the OP-6(a) timing decision (v6-now recommended for this cheap tier; everything era-stamped). No lineup changes, no enforce-mode, all numbers observation-grade pre-P-REV-1. **Reporting/anti-double-run**: these three tasks are the EXECUTION of series checkboxes owned by the reviewer-control-plane leaves — on completion flip TM-8 (`reviewer-trace-materialization.md`), RD-12 (`reviewer-decision-plane.md`), RC-8 (`reviewer-calibration-accounting.md`), LB-1 (`reviewer-latency-and-sampling-budget.md`) there with the numbers, then ✅ these lines; no other session should run them independently.

- [ ] **RCP-W1 — Reference-lineup relaunch + preflight**: `orchestrator_stack.py` relaunch under three-gates discipline (pipeline-green ≠ starts ≠ live==config); `affinity_preflight.py` live-affinity check; flip `review_decision_shadow=ON` (runtime flags) and **verify propagation on ALL uvicorn workers** (known 1-of-6 propagation hazard — per-worker flag introspection BEFORE any replay; a partial flip silently corrupts TM-8 coverage).
- [ ] **RCP-W2 — RD-12 paired shadow replay** (feeds LB-1 + TM-8 + first `review_ledger` rows): the same 50-question eval-tower replay run shadow-OFF then shadow-ON (paired, same questions, seed42 production sampling). OFF leg re-anchors the post-`bc8d3303` throughput baseline; ON leg measures shadow-emission overhead; TM-8 gate = ~100% of review invocations produce trace rows (`src/trace/query.py decision-chain` + ledger counts). Artifacts: replay JSONLs under `/mnt/raid0/llm/tmp/`, ledger rows in `data/trace/events.sqlite`.
- [ ] **RCP-W3 — RC-8 smoke slice**: status-quo self-review (architect alias) in shadow over ~100–200 multi-oracle `nearmiss-v1` rows across domains incl. the natural-defect control slice (`/mnt/raid0/llm/datasets/nearmiss-corpus-v1/`); score via `scripts/analysis/reviewer_calibration_report.py` → first FA/FR/CR observations. **Broken-grader guardrail**: read transcripts before believing any surprising number (CORE-Bench 42→95% was grader repair). Instrument stamp: kernel era, combined ngram+MTP worker config (provisional), corpus id+hash, flag state.
- *(Optional rider at operator discretion: OP-2's still-pending v6-iqk canonical verification can share this quiesced window.)*


- [x] **BSV-INPUT-STRICT — reject malformed standalone EvalResult evidence before paired reporting.** ✅ 2026-10-06 — [Strict standalone contract](../../docs/reference/bsv-standalone-input-integrity-contract.md) published APPmain09e087b2; originalCI37454712581 TRUE38/38 independently accepted by MAIN. Existing disposition taxonomy, valid producer forms, stable/source IDs and all statistical/journal/threshold semantics retained. Initial FALSE31/38 fixture-only CLI error retained; no inference/acceptance deployment.

## Track: eval-benchmark-cost-reduction
<!-- gate: none -->

> Folded from `handoffs/active/eval-benchmark-cost-reduction.md` @ `c4b6d1388716` on 2026-11-02 (BRF-T1-F2, route 1a, operator D1/D5; retired row EVL-11 → EVL-14). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Eval Benchmark Cost Reduction — Mid-Range Difficulty Filter

**Status**: stub
**Created**: 2026-06-25 (via research intake)
**Categories**: benchmark_methodology, autonomous_research

#### Objective

Apply a mid-range difficulty filter (30–70% historical pass rate) to *external fixed-task evals* (Terminal-Bench Core) to reduce per-run evaluation cost by 44–70% while maintaining rank fidelity (Spearman ρ ≥ 0.87). **Not applicable to autopilot's rotating question pool** — see Constraints below.

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-727 | Efficient Benchmarking of AI Agents (arxiv:2603.23749) | high | new_opportunity |
| intake-726 | Terminal-Bench / Harbor Framework (GitHub) | high | adopt_component |
| intake-369 | Terminal-Bench paper (arxiv:2601.11868) | medium | worth_investigating |

#### Technique

**Mid-Range Difficulty Filter (MR)**: select tasks where historical pass rate ∈ [0.30, 0.70]. Tasks outside this range contribute minimal ranking signal and add pure cost. Motivated by Item Response Theory.

- Evaluated on Terminal-Bench 2.0 (89 fixed tasks, 101 agents, 23 scaffolds) + 7 HAL benchmarks
- Mean Spearman ρ = 0.94, worst-case = 0.87 under scaffold/temporal shift
- 44–70% task reduction (median 58%); $268.8–$870.6 savings per run (HAL benchmarks)

#### Constraints: Why This Does NOT Apply to Autopilot's Rotating Pool

Analyzed 2026-06-25 against the live autopilot journal (852 trials, 141 with question_results):

1. **Wrong evaluation objective**: The paper optimizes for *cross-agent rank ordering*. Autopilot performs *within-system regression detection* on an evolving config — opposite sensitivity requirement. Ceiling questions (>70% pass rate) are strong regression signals when they fail; floor questions (<30%) signal breakthroughs. The mid-range filter would discard both classes.

2. **Pool is rotating, not fixed**: 1382 unique qids from suites `general`, `math`, `coder`, `thinking`, `simpleqa`, `hotpotqa`, `gpqa`, `debugbench`, `livecodebench`, `cruxeval`, `bigcodebench`, `instruction_precision`, `vl`, `mode_advantage`, etc. Only 50 qids appear in ≥50 trials — the stable core. Of those 50, **only 3 fall in the 30–70% mid-range**. The filter would reduce the stable core from 50 to 3 questions.

3. **Pass rate polarization**: The 50-qid stable core is highly polarized — ~15 floor questions (<30%, dominated by `simpleqa` and `hotpotqa`) and ~32 ceiling questions (>70%, dominated by `coder`, `debugbench`, `math`, `thinking`). Only `cruxeval`×1, `instruction_precision`×1, `vl`×1 are mid-range.

**Correct use of pass-rate data for autopilot**: rotate out permanently saturated/floor questions and replace with fresh mid-range ones — a *question pool curation* problem, not a subset-selection problem. The differential signal from ceiling/floor qids is low between config mutations, suggesting those slots should be refreshed with harder/more-varied questions.

#### Where the MR Filter IS Applicable: TB Core External Evals

The filter is designed for the TB Core v0.1.1 scenario: **89 fixed tasks evaluated repeatedly against different agent configurations**. After establishing a TB Core baseline (see `agent-world-env-synthesis.md` and `autopilot-continuous-optimization.md`):

1. Run our stack against all 89 TB Core tasks to calibrate per-task difficulty
2. Identify the ~37–50 tasks in the 30–70% pass-rate band
3. Use that subset for routine re-evaluations (e.g., after major config changes) to reduce TB run cost by ~44–58%
4. Reserve full 89-task runs for quarterly calibration resets

Cold-start: The paper requires ~10 full-benchmark agent runs before the filter is reliable. Our one-time TB Core run provides 1 data point across a single configuration. To reach 10 points across diverse configs, either run our stack at multiple historical checkpoints or use the published TB2.0 paper dataset (101 agents, 23 scaffolds, temporal window Oct 2025–Jan 2026) as the difficulty calibration corpus — the pass rates are in the paper itself, not behind a submission wall.

#### Open Questions

- What is the Harbor adapter implementation cost for our `/v1/chat/completions` endpoint? (Prerequisite for TB Core run — estimate ~1 day: build a thin Terminus-compatible wrapper over our OpenAI-compatible endpoint.)
- After TB Core run: which of the 89 tasks fall in 30–70% for our stack? Does the mid-range band shift meaningfully between our orchestrator config variants?
- Can the TB2.0 paper's published per-task difficulty data (101 agents, 23 scaffolds) serve as a proxy calibration corpus to identify the mid-range subset without running our stack first?

#### Notes

- Solo-author preprint (March 2026), not peer-reviewed; credibility_score = 2 (medium). Pilot externally before any autopilot integration.
- The paper's scaffold-driven distribution shift guarantee (ρ ≥ 0.87 under LOSO) holds under temporal shift too — relevant for TB Core re-evaluations over time as our stack evolves.
- Do NOT apply to autopilot regression gates — per-suite resolution-awareness (3/n quantum gate, 2026-06-06) already addresses the small-sample problem differently.

#### Progress checklist

- **[declined: ws58 2026-11-03 content-review: unbounded — blocked on a Harbor adapter and a TB Core baseline that no handoff schedules; the MR-filter technique stays readable here]** BLOCKED: needs Harbor adapter + TB Core baseline (agent-world-env-synthesis) before MR/TB filter applies

#### Research Intake Update — 2026-07-11

##### New Related Research
- **[intake-802] "llm-inference-bench"** (GitHub `local-inference-lab/llm-inference-bench`; **UNLICENSED** — deep-dive corrected first-pass "MIT" (that refers to the GSM8K dataset); single-author, no CI/tests)
  - Relevance: a serving-benchmark harness whose **statistical-rigor methodology** is directly transferable to our eval framework, independent of its GPU-serving target.
  - Key techniques worth mining (adopt_patterns, NOT adopt_component — it's coupled to vLLM/SGLang GPU serving we don't run in prod, no llama.cpp/CPU path): (1) **McNemar paired-significance test** for A/B quant comparisons — a concrete upgrade for gating quant swaps beyond raw accuracy deltas; (2) **Wilson confidence intervals** on GSM8K/MMLU-Pro/GPQA-Diamond — pairs with our small-sample per-suite resolution-awareness; (3) concurrency×context-length throughput matrix + Prometheus server-side ground truth (reference for [[dynamic-stack-concurrency]] baselines).
  - Delta: our bench stack (bench_canonical.sh) uses Claude-as-judge + codified recipes and lacks explicit paired-significance testing; McNemar/Wilson are low-cost additions to chapters 06/07 methodology.
  - **Deep-dive (2026-07-11) verified the methodology is REAL, not README aspiration** — credibility bumped **2→3**: `wilson_interval` (`llm_decode_bench.py:11476`), `mcnemar_exact_p` (`:11487`, the rigorous **exact binomial** variant), and `build_paired_comparison` (`:11523`) are implemented, **stdlib-only** (math/statistics; no scipy), and cleanly separable from the vLLM/SGLang+Prometheus serving code. The tool is **AIPerf-0.7.0 parity-validated** (`docs/aiperf-parity-report-2026-04-26.md`, aggregate tok/s within −0.3…−3.6%) — first-pass "zero empirical numbers" was wrong. McNemar is the principled successor to our 3/n resolution gate. Full note: [`research/deep-dives/2026-07-11-paired-significance-eval-methodology.md`](../../research/deep-dives/2026-07-11-paired-significance-eval-methodology.md).
  - [x] A1 landed the reusable clean-room primitives ✅ 2026-07-17: `wilson_interval`/`expected_calibration_error`/`roc_auc` in `epyc-orchestrator/src/llm_primitives/stat_tests.py` (stdlib-only; 8 duplicate call-sites swapped w/ quantified equivalence — ROC Δ=0.0, ECE ≤3.2e-8) + the `dataset_sha256`+`test_profile` equality gate (`require_matched_comparison`) in `scripts/autopilot/paired_stats.py`; canonical exact McNemar stays `paired_stats.py::mcnemar_from_vectors`.
  - [x] A1 documented paired-McNemar as the formal successor to the 3/n resolution gate in chapter 06 (tracked: `epyc-inference-research/docs/chapters/06-benchmarking-framework.md` §Paired Significance Testing) ✅ 2026-07-17
  - [x] Pairing/discordant-flip screening wired into the eval-scoring/quant-A/B path ✅ 2026-07-17: `eval_tower.screen_paired_arms` (`scripts/autopilot/eval_tower.py:1124`) emits exact-McNemar p + per-arm Wilson CIs over the flip pairs, gated by `require_matched_comparison` on `dataset_sha256`+`test_profile`; called from the math-rebaseline A/B path at `eval_tower.py:3004` (`paired_significance` key). Commit `e93c6263`.
  - **[declined: ws58 2026-11-03 content-review: merged into EV-11c (its own text says promotion rides on that re-baseline)]** RESIDUAL (**owned by the inference-batch `/loop`, not this handoff**): `screen_paired_arms` output is currently **observation-grade** — it is reported in the result dict but is not reachable through a codified recipe, so per MEASUREMENT.md its McNemar p may not gate a keep/revert/promote decision. Promoting it to decision-gating rides on **EV-11 math re-baseline** (`coordination/inference-batch/entries/20-eval-tower.yaml` → `EV-11-math-rebaseline`), which is BLOCKED on the **EV-11b ECE-binning operator decision**. Do not edit `eval_tower.py` for this from a side session — see [`inference-batch-loop.md`](eval-tower-program.md#track-inference-batch-loop) (single-writer).
- [x] Operator-review candidate: port `wilson_interval` + `mcnemar_exact_p` + the pairing/discordant-flip core of `build_paired_comparison` (`llm_decode_bench.py:11476–11640`) into the eval-scoring / quant-A/B path (NOT `canonical_recipe.py`, speed-only); gate on `dataset_sha256`+profile match; document paired-McNemar as the formal successor to the 3/n resolution gate in chapter 06. ✅ 2026-07-17 — all three legs landed; see the A1 items above. Chapter 06 §"Paired Significance Testing (Quant A/B)" is live at `epyc-inference-research/docs/chapters/06-benchmarking-framework.md:347`. Chapter 07 was never owed a section (suite construction, not test methodology). Only the decision-gating residual above remains.

#### Research Intake Update — 2026-09-17 (external cost anchors + citation hygiene; intake-1475, intake-1492#record)

- [x] **ECR-TD-1 — Cost-order anchor + same-rubric local comparison.** Record the verified per-million-checks cost order (Jev ~$160; DeepSeek Flash $260; Gemini $1,600; Astra $18,700; Fable 5.1 $33,000 — estimates at list rates, intake-1475) as an external anchor, then run one same-rubric local cheap-judge arm before assuming a typed judge is the cheapest adequate reader. ✅ 2026-09-29 — folded into CJ-13 (`canonical-judge-suite-revamp.md`; operator-directed duplicate consolidation). The cost-order anchor and the same-rubric local comparison moved there.
- **[declined: ws58 2026-11-03 content-review: standing citation-hygiene rule, not a task; claim tuples already require a captured warrant (MEASUREMENT_POLICY)]** **ECR-TD-2 — External dashboard citations must be snapshot-captured** (payload hash or rendered snapshot) before entering a claim tuple; the 3–329 s baseline citation is not derivable from its cited live page (intake-1492#record).
- [x] **ECR-EB-1 — EdgeBench zero-compute slice selection for a short-budget CPU slice.** ✅ 2026-10-21 From the EdgeBench card per-task table at dataset sha `6cc5a7f1` and `tasks.jsonl`, produce a ranked list of at most 8 CPU-only tasks for a 2 h budget with the selection rule predeclared (non-saturated at 2 h, positive 2 h to 12 h headroom, internet false, Python or C++), as a CSV and a one-page note. Add the run-to-run SD columns for GLM-5.1 and DS-V4-Pro from the paper cells (HTML at sha `037e38aa`) and predeclare the exclusion (SD above 15 points on a 0-100 scale) before looking at the ranking; join on task name and drop unmatched rows (the paper covers all 134 tasks, definitions exist for the 51 public ones). The parser column for all 51 tasks is already produced (27 structured_json, 18 score_sum, 3 pytest_v, 3 game-server) and direction and rescale fields are partial: treat score_direction, selection and rescale as optional (intake-1361#record, intake-2234#record). Zero inference, no image pull. Acceptance: CSV with the columns and the exclusion applied, and the one-page note. Estimate: 0.5-1 day.
  - 2026-10-21 (dpf-sample-yarn-zc, lane `lane/dpf-sample-yarn-zc-epyc-root-20261021`): DONE. Rule committed before ranking (`ac0af86d0`, `artifacts/ecr-eb-1-20261021/SELECTION_RULE.md`); outputs commit `d89b1324f`: `edgebench_slice.csv` (8 tasks), `edgebench_all_joined_audit.csv`, `build_log.json`, `EDGEBENCH_SLICE_NOTE.md`. Join 51 of 51 on task name, 0 dropped; 254 paper 12 h cells checked against the card, 0 mismatches (the paper SD is a 12 h SD). Funnel 51, 40 (Python or C++), 39 (internet false), 39 (CPU-only), 39 (non-saturated at 2 h), 39 (positive headroom), 33 after the predeclared SD above 15 exclusion (6 excluded). Slice: tryst_text_adventure, borden_source_inversion, order_addition_permutation_optimization, anchorhead_text_adventure, juliet_vulnerability_analyzer, tree_block_partitioning, trinity_text_adventure, k12_math_recommendation. Caveats in the note (12 h SD only; 3 game-server tasks and 1 pytest-v need harness check; leaderboard-model headroom).

#### Research Intake Update — 2026-10-21 (harness cluster, DP-F amendment)

Operator-approved Stage-3 amendment (plan sha256 2edfb0662f61e1254e7dc5e2b21888ef4f19df800a283e82b25caebeb6644746). Durable records only: no checkbox, no index next action. Each monitor row carries its trigger and first step; each knowledge row states what to rely on. Ledger ids (DPF-...) key to the Stage-3 recommendation mapping preserved in `.research-session.json` (`stage3_filing`).

##### M24 — EdgeBench and SForge follow-ons

- DPF-1361-1361-03 (intake-1361): SForge as a like-for-like harness comparison bed: built-in OpenCode scaffold plus SFORGE_AGENT_API_BASE_URL lets the HS-4 shell run EdgeBench against the local orchestrator /v1 endpoint. — Trigger: 1361-02 produces a slice AND an inference-budget decision plus a granted compute window exist (12 h tasks at local decode speeds are weeks; 2 h slice only). No run, no image pull before then.
- DPF-1361-1361-09 (intake-1361): Independent replication or critique of the log-sigmoid law. — Trigger: any third-party reanalysis of the released 51-task per-task tables, or paper v2.
- DPF-W1-G6D-SFORGE-S4 (intake-2235): SForge as a like-for-like harness comparison bed through the built-in OpenCode scaffold and SFORGE_AGENT_API_BASE_URL. — Trigger unchanged: slice list from 1361-02 plus an inference-budget decision and a granted compute window. No run, no image pull before then.

## Track: eval-tower-architecture-audit-2026-07-20
<!-- gate: none -->

> Folded from `handoffs/active/eval-tower-architecture-audit-2026-07-20.md` @ `c4b6d1388716` on 2026-11-02 (BRF-T1-F2, route 1a, operator D1/D5; retired row EVL-12 → EVL-14). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Eval Tower Architecture & Robustness Audit (2026-07-20)

**Status**: AUDIT — findings + phased owner-tagged fix plan; **no code changed** (read-only; the parallel
loop agent has live uncommitted work in `eval_tower.py` and the runner — see §Constraints).
**Scope**: the tower ITSELF — `eval_tower.py` internals, scoring pipeline (`debug_scorer.py`,
`rubric_scoring.py`), `safety_gate.py` + `rlvr_tiers.py`, dataset/suite data plane, persistence/observability,
test architecture. Companion to [eval-tower-loop-robustness-audit-2026-07-20.md](eval-tower-program.md#track-eval-tower-loop-robustness-audit-2026-07-20)
(which covered the loop AROUND the tower: contention matrix, runner kill-safety, preflight, ledger, EV-CONF).
Findings from that audit are NOT re-reported here.
**Cross-links**: [eval-tower-verification.md](eval-tower-program.md) (EV-N program),
[inference-batch-loop.md](eval-tower-program.md#track-inference-batch-loop), `/workspace/MEASUREMENT.md`.
**Provenance**: 6 parallel read-only subagent audits (core internals, scoring, gate/RLVR, data plane,
persistence, tests/drift), 2026-07-20. All 3 CRITICALs + the per-suite float boundary + the pool-registry
gap independently re-verified by the audit author against source. Two findings were double-discovered by
independent agents (QID-1, REL-1) — treat as high-confidence.
**Severity totals (after dedup)**: **3 CRITICAL · 16 HIGH · ~30 MED · ~25 LOW.**

---

#### Headline — the seven architectural weaknesses behind "we keep running into bugs"

1. **Scorer/module identity is nondeterministic.** Same-named modules exist in two repos
   (`debug_scorer.py`, `dataset_adapters.py`, `question_pool.py`, plus `safety_gate.py` twice inside
   orchestrator) and `sys.path` is mutated at import AND lazily at runtime — **which code scores your eval
   depends on which eval ran first in the process** (SCORE-02, XREPO-1, DRIFT-1).
2. **Silent-fallback is the default error philosophy.** Scoring falls back scorer→scorer without
   provenance; loaders cache failures forever; empty suites produce legitimate-looking zero-quality
   results; broad `except Exception` converts subsystem breakage into silent serial/degraded modes.
   Infra failures systematically masquerade as model-quality signal (SCORE-01/08/13/25, CACHE-1,
   EMPTY-1, SCHEMA-1, REL-1).
3. **Identity & provenance are not machine-checked.** Journal qids and sampler qids live in disjoint
   namespaces; tier evals carry no dataset-content hash; the content sha that exists omits the scoring
   oracle; "same instrument" claims are unverifiable and already false in production (QID-1, VERS-1,
   SHA-1, the pool gap).
4. **Evidence durability is single-copy and fragile.** Per-question results exist only in memory until
   trial end (a killed 1,800-question run keeps nothing); the journal — the only durable evidence store —
   is appended non-atomically at up to 336 KB/line with zero-tolerance loaders; baseline YAML writes are
   truncate-in-place (JRN-1/2/4, SG-2).
5. **The gate is asymmetric.** Quality has floor+regression+per-suite guards; reliability has NO gate at
   all; NaN quality passes every check; missing same-tier baselines silently compare across incomparable
   tier scales; the sequential anti-ratchet goes soft exactly in low-evidence regimes (REL-1, SG-3/5,
   SEQ-2).
6. **Dead code and field explosion mask policy gaps.** The entire EV-8 diversity gate has zero production
   importers (well-tested dead code); EvalResult has 55 fields with three inconsistent emission surfaces
   (objectives / grep-lines / journal) that silently drop whole field families (DUP-1, FIELD-1).
7. **Tests mock at the wrong boundary and some enshrine bugs.** Every eval test mocks the inference
   client, so the entire error/timeout/retry surface is unexercised; the QID-1 masking test passes while
   production is broken; the forbidden ECE consolidation has no pinning test (TEST-1/2/3).

#### Confirmed-in-production evidence (measured, not hypothetical)

- **The live question pool was built by the stale orchestrator adapter registry.** `question_pool.jsonl`
  (53,231 questions) holds 15 adapter suites + 6 yaml-only; the research registry defines **33** adapter
  suites. Absent from all T1/T2/T3 sampling: `mmlu_pro`, `physics`, `physreason`, `aime`, `aime25`,
  `olympiadbench`, `gpqa_diamond`, `gpqa_diamond_cot`, `longbench`, `zeroscrolls`, `leval`, `ruler`,
  `needle_parameterized`, `omniscience`, `aa_lcr`, `scoring_verifiers`, `document_extraction`,
  `tulving_episodic`, `longcot_mini`. `mmlu_pro`/`physics`/`physreason` are in BOTH registries and still
  missing, and `gaia` shipped with **0 rows** — the build also silently dropped suites it intended to
  include. Per MEASUREMENT.md the current T1 instrument is the seed-42 draw from THIS pool → the live
  quality gate has never sampled these suites; EV-3 (`scoring_verifiers`) and AA-Omniscience are marked
  "integrated" in [eval-tower-verification.md](eval-tower-program.md) but never actually sampled.
- **634 bare `NaN` tokens** across 317 lines of the live `autopilot_journal_1.jsonl` (non-strict JSON).
- **190 rows with `NaN` ece/auroc in the shipped AP-27 RLVR export**, several `ready_for_training: true`.
- **186 (n,k) combinations for n∈[2,60]** where a single-question flip crosses the per-suite float
  boundary and fires a hard violation (SG-1) — the exact artifact class of
  `feedback_per_suite_gate_resolution_artifact`, reintroduced by strict `<` on unrounded floats.
- (Known, prior audit): 1182/1182 journaled ECE values exactly 0.0 → EV-CONF.

#### Prior-audit correction

The loop audit marked "safety_gate blocks all v7 baseline writes" **unverified** claiming
`_baseline_eligible` doesn't exist. **It exists** (`safety_gate.py:1253-1284`) and gates only
`update_baseline()` (never `check()`): eligible iff `speed_metric_mode ∈ {median_request_tps,
aggregate_batch_tps}` AND `matrix_status == OK` vs the live topology fingerprint, fail-closed, no env
override. A v7 kernel swap alone does NOT trip it (fingerprint hashes NUMA role placement, not the
binary). What DOES silently freeze all baseline ratcheting: matrix file **mtime > 30 days**, matrix
MISSING/INVALID, or any measured-role NUMA edit — surfaced only as a `log.warning`
(`safety_gate.py:1362`). Matrix is fresh today (2026-07-20), so writes currently work, but the 30-day
wall-clock re-freeze is a **built-in future wedge** (compounds loop-audit A5/A6). → SG-0 below.

---

#### Cluster F — Scorer identity & scoring correctness
`debug_scorer.py` = orchestrator `scripts/benchmark/debug_scorer.py` unless noted.

| # | Sev | Finding (file:line) | Failure scenario | Tested |
|---|---|---|---|---|
| **SCORE-01** | **CRITICAL ✓verified** | **math_verify silently degrades to exact_match on EVERY threaded eval.** math-verify's `signal.alarm` timeout raises ValueError in any non-main thread (`math_verify/parser.py:709-714`); `debug_scorer.py:713-719` catches bare `Exception` → `_score_exact_match` fallback; `_eval_batch` scores inside `ThreadPoolExecutor` workers (`eval_tower.py:1843-1847`); the EV-11 guard (`eval_tower.py:115-133`) checks importability only. | Any T1/T2/rebaseline with concurrency>1 scores all math via exact_match (orch copy has NO `\boxed{}` fallback, `:92-100`) while stamping `test_profile.scoring="math_verify"` — the EV-11 0/1,819 no-op resurrected, invisible, and **concurrency-dependent**: serial and concurrent arms of one comparison are scored by different scorers under identical provenance. | no — threaded tests monkeypatch `_eval_question` |
| **SCORE-02** | **HIGH** | **Two divergent `debug_scorer.py` copies race on lazy import.** `eval_tower.py:779` puts orch benchmark dir on `sys.path[0]`; `:1411`/`:2788-2792` later insert the research dir; `seeding_scoring.py:32` imports `debug_scorer` lazily at first scoring call → last-inserted-before-first-call wins, `sys.modules` caches it. Research copy has NO `math_verify` scorer and no digit-separator fix; orch copy dropped the boxed fallback. | Fresh process running `eval_math_rebaseline`: research copy binds → all 1,819 questions/arm ERROR (`Unknown scoring method`). Process that ran T0 first: orch copy binds → SCORE-01 behavior. Which bugs you get depends on eval order. | no |
| SCORE-03 | HIGH | exact_match colon/quote fallback scans the WHOLE answer including CoT (`debug_scorer.py:133-150`). | Expected "42", CoT line "Step 3: 42", final answer "43" → scored **correct**. | no |
| SCORE-04 | HIGH | code_execution `entry_point` oracle calls with no args and interpolates expected without `repr` (`:338-340`): string expecteds → NameError → always-False; dataset-controlled `expected`/`entry_point` = arbitrary code execution in the subprocess. `_has_code_execution_oracle` (`eval_tower.py:101-112`) still deems these scoreable. | Whole question class permanently scores wrong; injection surface from dataset files. | no |
| SCORE-05 | HIGH | "Sandboxed" subprocess isn't (full privileges/network/fs, `:342-356`); `_score_stdin_program` runs dataset `test_code` via `exec` **in-process with no timeout** (`:213-216`) — an infinite loop wedges a worker thread unkillably; hardcoded `dir="/mnt/raid0/llm/tmp"` missing → `OSError → False` scores the whole suite 0 as *wrong*, not *error* (`:226-229,344-347`). | Untrusted-ish dataset code runs unconfined; one bad row wedges the batch; a missing tmp dir reads as capability collapse. | no |
| SCORE-06 | MED | Substring scorer boundary-free (`:505-535`); live T0 sentinels use it with expecteds like `"63"`, `"\sqrt{130}"` (`sentinel_questions.yaml:146-163`). | "63" matches "630"/"2,630" anywhere incl. reasoning; LaTeX spacing variants false-negative. (Class already in memory `feedback_substring_scorer_comma_brittle`; here = live-sentinel exposure.) | no |
| SCORE-07 | MED | Rubric judge scores clamped not validated (`eval_tower.py:1315`): judge answering on 0–10 scale ("7") → 1.0 perfect on every dimension → `correct=True` at 0.60 threshold. | Scale-drifted judge saturates rubric quality. | clamp asserted as intended |
| SCORE-08 | MED | Silent judge→heuristic fallback, no provenance flag (`eval_tower.py:1569-1571,1598-1606`; heuristics `rubric_scoring.py:292-323`). | Judges die mid-run → half judge-scored, half markdown-structure-heuristic-scored, indistinguishable downstream; heuristics gameable. | partial |
| SCORE-09 | MED | `aggregate_rubric_score({})` returns perfect 1.0 (`rubric_scoring.py:109`); feeds confidence (`eval_tower.py:1704`). | Any caller with empty/all-missing scores gets "perfect". | no |
| SCORE-11 | MED | multiple_choice guard uses substring semantics: `expected_letter not in "ABCDEFGH"` (`:165-167`) — `""`/`"AB"` pass then always-False; `"(B)"` fails guard → always-False. | A dataset emitting parenthesized answers scores 0 silently. | no |
| SCORE-12 | MED | Phantom `pass_rate` confidence: `scoring_config.get("pass_rate", correct)` reads a static dataset field no scorer writes (`eval_tower.py:1701-1702`); None/non-dict config → AttributeError converts a scored question into an error result (`:1740-1756`). | `pass_rate: 0.9` in a dataset injects constant 0.9 confidence → corrupts ECE/AUROC inputs (interacts with EV-CONF). | no |
| SCORE-13 | MED | `_score_llm_judge` silently falls back to substring when judge unreachable (`debug_scorer.py:688-690`) + substring fast-path over full answer (`:653-654`). | Judge port dead → PhysReason-class suites quietly re-scored by substring — the silent-degrade class EV-11 banned. | no |
| SCORE-14 | MED | `_score_math_verify` ignores its own `extraction_mode` config (`:704-719`) and falls back to exact_match on ANY exception even main-thread (sympy errors, TimeoutException). (`verify(gold,pred)` order IS correct; `strict=True` default avoids the interval→Tuple false positive.) | Documented config silently no-ops; main-thread parse failures silently rescored. | happy path only |
| SCORE-15 | LOW | `_to_number("1,2")` == 12 (`:116-120`). | Coordinate answer "1,2" vs expected "12" → false positive. | no |
| SCORE-16 | LOW | Orch exact_match dropped the research copy's `\boxed{}` fallback (`:92-100` vs research `:106-109`) — amplifies SCORE-01. | Boxed answers false-negative under fallback. | no |
| SCORE-17 | LOW | `rubric_scoring._spearman` returns 1.0 for <2 shared items; formula invalid for partial-overlap lists (can leave [−1,1]) (`rubric_scoring.py:336-345`). | Disjoint judge rankings report "perfectly stable". | no |
| SCORE-20 | LOW | AUROC class-presence guard uses banker's-rounded labels (`eval_tower.py:1051`) vs `roc_auc`'s `>=0.5` rule (`stat_tests.py:169`); also denies 2-distinct-confidence vectors. | Computable AUROCs reported None. | partial |
| SCORE-21 | LOW | Vacuous oracles accepted: `test_code="assert True"` passes any compilable answer (`eval_tower.py:87-94`). | Junk rows count as scoreable coverage. | no |
| SCORE-22 | LOW | Cross-family judge gate compares model-vs-ROLE name (`eval_tower.py:1580`→`:913-928`): "reviewer" → unknown → permissive. | EV-6 discipline silently unenforced for judge roles. | no |
| SCORE-23 | LOW | Non-string `expected` → `.strip()` AttributeError → question errors at scoring time (`eval_tower.py:1618,1691`; contrast `str()` wrap at `:1250`). | Unquoted numeric expected errors every draw of that question. | no |
| SCORE-24 | LOW | F1 uses set (not multiset) overlap; multi-group regex extract crashes to error (`debug_scorer.py:589-595`). | Repetition-sensitive answers mis-scored; 2-group patterns kill questions. | partial |
| SCORE-25 | LOW | Unknown programmatic verifier name silently degrades to substring (`:497-500`); explicit `count: 0` treated as missing (`:413`). | Typo'd verifier name = silent substring scoring. | no |

#### Cluster G — Question identity & dataset integrity

| # | Sev | Finding (file:line) | Failure scenario | Tested |
|---|---|---|---|---|
| **QID-1** | **CRITICAL ✓verified ×2** | **Promotion "fresh draw" recency exclusion is a silent no-op: disjoint qid namespaces.** Journal rows carry sha1-hash qids (`_eval_question` computes `stable_qid`, `eval_tower.py:1621-1626`; `_compact_question_result` `:422-424`); `actions.py:1888-1938,2021` harvests those hashes into `exclude_qids`; but the sampler filters via `_question_qid` (`:295-299`) which returns the raw pool `id` (`gsm8k_00042`) — pool rows have `id`, never `qid`/`stable_qid`. Hash set ∩ id set = ∅. | Every W8 promotion eval can re-test recently-seen questions while journaling `recent_exclusion_qids: N` as if the 60-day freshness guarantee held — overfit leakage into promotion with false provenance. The test masks it: `test_eval_tower_instrument_repair.py:930` builds the exclusion set in the pool-id namespace. | masking test |
| **XREPO-1** | **HIGH ✓verified** | **Same-named diverged module copies across repos; first-import-wins; the stale copy demonstrably built production data.** Orch facade `dataset_adapters.py` (frozen 2026-05-22, 18 suites) + own `question_pool.py` shadow the research monolith (33 suites); `eval_tower.py:779` vs `:1410-1411,2791-2792` path races (same mechanism as SCORE-02). Realized: live pool built by the orch copy (header `yaml_only` key unique to it) → **see Confirmed-in-production above**. No invariant checks pool-suites ⊇ registry-suites. | Pool rebuilds silently drop whole suites; `_load_dataset_adapter("scoring_verifiers")` raises "no adapter registered" if orch copy binds first. | no |
| VERS-1 | HIGH | Tier evals (T1/T2/T3) carry NO dataset-content identity: `dataset_content_sha256` computed only in verifier modes (`eval_tower.py:2871,2937`), never compared to a pin anywhere; tier draws identified only as `legacy_pool_seed_42_n100` (`:2460`). | Two runs across a pool rebuild (or XREPO-1 registry swap) evaluate different question sets under identical core_id — baselines silently mix instruments. | sha determinism only |
| LOSS-2 | HIGH | Adapters drop rows and whole sub-datasets silently: `extract_all` bare-`continue` on row exceptions (research `dataset_adapters.py:265-272`); MATH-500 load failure → `[]`, zero logging (`:372-375`). `eval_math_rebaseline` documents 1,819/arm but nothing gates `n_math500>0` (`eval_tower.py:2911,2939`). | Re-baseline silently runs GSM8K-only and stamps itself decision-grade; live pool `gaia: 0` shows the pattern shipped. | no |
| LOSS-1 | MED | `load_pool` skips malformed JSONL rows uncounted and returns `{}` for missing file (research `question_pool.py:140-154`); nothing reconciles loaded counts vs the header's own per-suite stats. | Truncated pool quietly shrinks every suite. | no |
| SCHEMA-1 | MED | No load-time question schema validation: row missing `prompt` passes `_is_scoreable_question` (`eval_tower.py:145-153`) and is dispatched with `prompt=""` → scored **incorrect**; `_load_sentinels` is `yaml.safe_load or []` with zero validation (`:1352-1360`). | Corrupt data manifests as phantom model regression (T0 trip / suite drop) instead of a data error. | no |
| SPLIT-1 | MED | `_filter_questions_by_split` = loose substring matching with asymmetric normalization (`:2814-2820`): `HE-R+` can never match `he_r_plus` (loud footgun), `he_r` silently matches `he_r_plus` (over-inclusive). No hashed/persisted dev-test assignment exists anywhere in the plane (the AppWorld dev/test discipline has no enforcement point). | Wrong-superset splits selected silently; leakage prevention rests on id naming conventions. | no |
| SHA-1 | MED | `dataset_content_sha256` hashes only `(id, prompt, expected, scoring_method)` (`:1073-1078`) — omits `scoring_config` (test_code, patterns, thresholds = the oracle) and `suite`. | Arms differing only in oracle hash identical → `require_matched_comparison` passes on materially different instruments. | field coverage no |
| PAIR-1 | MED | `screen_paired_arms` bypasses the provenance gate when EITHER arm lacks a profile (`:1178`), contradicting `paired_stats.py:238-244` ("missing identity is itself a refusal"). | Half-identified pairs get a McNemar verdict instead of a refusal. | bypass untested |
| DISJ-1 | LOW | Non-promotion T2 has no disjointness from the T1 core: same seed 42, same pool, exclusions only when `promotion_eval` (`:2635-2641`). | T2 "independent confirmation" of a config tuned on T1 largely re-tests the T1 set. | no |
| QID-2 | LOW | Identity split between mutable content-hash (prompt edit → new identity, orphaned longitudinal joins) and mutable positional ids (`gsm8k_{idx:05d}` — HF revision renumbers silently); hash fn triplicated (`eval_tower.py:290`, `core_v2_select.py:62`, `eval_task_coverage_report.py:44`). | Any copy drifting silently unpairs qid spaces. | no equivalence test |
| QID-3 | LOW | Duplicate qids collapse last-write-wins in paired vectors (`:2994`, `:1107-1120`) and cross-suite bare-id lookup resolves to first suite iterated (`:1480`). | McNemar shared-set denominator silently shrinks; wrong question served for a designed-core id. | no |
| SV-1 | LOW | ScoringVerifiers label extraction falsy-`or` alias chain (`scoring_verifiers_adapter.py:250-256`): valid `label=0` falls through to stale truthy aliases → "correct"; unlabeled problem rows become junk `(empty solution)` items (`:171-175,268-272`). | Mislabeled verifier items poison EV-4 calibration baselines. | alias fall-through untested |
| PATH-1 | LOW | Research repo path hardcoded (`eval_tower.py:1410,2789`) without the `EPYC_RESEARCH_ROOT` override its sibling honors (orch `question_pool.py:30-32`); failure deferred to first call and swallowed into empty-pool. | Moved tree → silent empty pool (see CACHE-1). | no |

#### Cluster I — Partial-failure & error semantics

| # | Sev | Finding (file:line) | Failure scenario | Tested |
|---|---|---|---|---|
| **REL-1** | **HIGH ✓found ×2** | **Infra errors scored as wrong answers in decision-grade quality; NO reliability gate exists anywhere in `SafetyGate.check`.** `_aggregate`: `quality = correct/len(results)` with errored rows in the denominator (`eval_tower.py:1982-1983`); no-progress timeout mass-converts pending questions to errors (`:1867-1877`); `check()` violations = quality floor/regression/per-suite/routing/throughput only — `reliability` never compared (`safety_gate.py:966-1164`). Same file uses opposite semantics (drop errored rows) in `eval_calibration`/`eval_math_rebaseline` (`:2877-2886,2970-2979`). | 20 of 100 T1 questions 5xx → quality −0.6 → "Quality regression" violation → good config reverted; symmetrically a 70%-error trial passes if aggregate quality holds. Two partial-failure semantics in one module. | no |
| EMPTY-1 | MED | Infra absence encoded as legitimate zero-quality: empty pool → bare `EvalResult(quality=0)` with no error marker in T0/T1/T2 (`:2342-2345,2454-2457,2585-2588`); T3 + promotion path fail closed properly (`:2642-2661,2702-2721`). | Lost research mount mid-run journals quality=0 trials indistinguishable in-band from catastrophic regression. | partial |
| CACHE-1 | MED | Sticky failure caches: `_load_pool` caches `{}` and `_load_sentinels` caches `[]` on first exception for process lifetime (`:1405-1418`); successful loads also never refresh after on-disk rebuild. | One transient NFS blip → eval plane permanently dark (or permanently stale) until restart, no retry, no escalating signal. | no |
| ET-3 | MED | No-progress watchdog exists ONLY on the concurrent path (`:1851-1877`); serial mode — the fail-closed default the tower usually runs in — has no batch-level stall protection (`:1817-1841`); httpx read-timeout is per-read, not end-to-end. | A byte-trickling response stalls the entire eval unboundedly — the exact hazard the watchdog was built for, unguarded in the common mode. | serial absence untested |
| ET-4 | MED | After no-progress timeout, running futures aren't cancellable (`shutdown(wait=False)`, `:1915-1916`) and the shared `httpx.Client` closes on return (`:2360,2533,2668`) while llama-server keeps decoding orphaned requests. | Next eval batch runs concurrently with leaked inference on a host where concurrent decode corrupts speed/quality evidence. | no |
| ET-5 | MED | W6 shadow-audit decision re-aggregation divides subset tokens/counts by FULL-batch wall time (`:2539-2541,1994-2011`). | 50-core+10-audit batch → ~17% systematic speed/task_rate/goodput deflation; trials on/off audit cadence are Pareto-incomparable under one instrument id. | no |
| ET-6 | MED | `tool_sentinel` partition included in decision metrics (shadow filter excludes only `"audit"`, `:2539`); with secrets unminted these are guaranteed-INCORRECT by design (`:1390-1395`). | Enabling tool sentinels before secret minting drags decision quality + pins a `tool_use` suite at 0 vs baselines computed without it. | no |
| ET-8 | LOW | `AUTOPILOT_EVAL_NO_PROGRESS_TIMEOUT_S=0` → `or None` → watchdog disabled (wait forever) instead of fail-fast (`:83,1855`). | "Zero tolerance" config = infinite tolerance. | no |
| ET-9 | LOW | Unscoreable-item replacement taken in pool file order, not seed-driven (`:168-183`). | Head-of-file questions over-represented in every draw. | distribution untested |
| ET-13 | LOW | Routing distribution misclassifies non-worker/architect routes as "frontdoor" (`:2055-2064`). | Planner routing telemetry inflated. | no |
| ET-14 | LOW | `on_question` invoked from N worker threads with no thread-safety contract; wired autopilot callback does unlocked `write_text` (autopilot_tui.py:148-155). | Torn prompt-tap file at concurrency 3. | no |
| ET-15 | LOW | Promotion suite-health exclusion picks newest `item_analytics*.json` by mtime with no freshness bound; `stat()` inside `sorted` can raise out of `eval_t2` (`:494-545`). | Months-old analytics silently drives promotion suite exclusion; glob/stat race raises. | no |

#### Cluster J — Safety gate, baseline & sequential verdict

| # | Sev | Finding (file:line) | Failure scenario | Tested |
|---|---|---|---|---|
| SG-0 | HIGH | (From the correction above) `_baseline_eligible` silently freezes ALL baseline promotion when the contention matrix mtime exceeds 30 days — `log.warning` only (`safety_gate.py:1253-1284,1362`; `contention.py:42,336-338`). | Every ~30 days ratcheting silently stops until someone re-measures/touches the matrix; compounds loop-audit A5/A6 (mtime≠measured_at). | no |
| **SG-1** | **HIGH ✓verified** | **Single-question flip fires a hard per-suite violation at many n via float boundary**: `threshold = -max(quanta)` with `3.0/n` floats, strict `suite_delta < threshold`, no epsilon (`:78-90,1060`); 186 (n,k) combos in n∈[2,60] cross it (n=5,7,9,10…). Only `tool_use` has the advisory carve-out. | Baseline 1/5 → 0/5 on a 5-question suite = hard violation — the exact artifact `per_suite_regression_threshold` exists to prevent. | only n=2 tested |
| **SG-2** | **HIGH ✓verified** | Baseline persistence non-atomic + zero-tolerance load: `save()` truncate-in-place `write_text` (`:607`), second non-atomic text-surgery writer (`autopilot.py:8866-8889`), `load()` bare `yaml.safe_load` no try/except (`:487`), no schema version. | Crash mid-write → truncated YAML → `SafetyGate.__init__` crashes at startup (AttributeError/ParserError) — gate bricked until hand-edit. | no corrupt-file test |
| SG-3 | HIGH | Cross-tier baseline contamination: lenient `quality_for_tier` falls back to legacy `self.quality` (`:621-626`) which T1 promotions overwrite with T1-scale values (`:649-651`); used by regression gate (`:974`) and monotonic gate (`:1359`); tiers declared scale-incomparable (`tier_specs.py:4-7`). | T2/T3 eval with no same-tier baseline is gated against T1-scale 1.9 → automatic violation → spurious rollback at 3 consecutive; good first T2 promotion refused as non-monotonic. | fallback path untested |
| DUP-1 | HIGH | The NIB2-42 diversity gate (`src/safety_gate.py`) has ZERO production importers (only 2 test files); EV-8's Tier-1 WARN / Tier-2 REJECT policy is unenforced dead code; live loop's only diversity handling is a different mechanism (`meta.observe_diversity`, autopilot.py:8098). | `SAFETY_GATE_WARN_ONLY=0` changes nothing; diversity-collapsed candidates admissible to the frontier. 12 passing tests mask the wiring gap. | gate tested, wiring not |
| SG-4 | MED | `apply_state()` lacks the archive-max guard `load()` applies to YAML (`:609-619` vs `:500-534`). | Corrupt `autopilot_state.json` in-scale-but-above-frontier value enters the live baseline — the exact 2026-05-31 gate-lock class. | no |
| SG-5 | MED | NaN quality passes every `check()` gate (NaN comparisons False, `:966,976`); only `update_baseline` rejects NaN (`:1389`). | Degenerate eval → passing verdict → NaN objectives poison Pareto frontier math (all comparisons False). | no |
| SG-7 | MED | MAD=0 history → ANY nonzero delta "significant" (z=NaN escapes the `mad_noise` tag, `:763,1001`). | At suite saturation a 1-question flip up is a "real improvement" into archive/learning surfaces. | asserted as intended |
| SG-8 | MED | `load()` validates quality/reliability but not speed/cost/frontdoor_speed (`:551-561`): `null` → TypeError in every check (gate down); negative → throughput floor can never fire (fail-open); string quality → load crash. | Type-corrupt baseline either bricks or silently disarms the gate. | no |
| SG-9 | MED | Throughput floor fails open whenever host "looks throttled" (remediated or not, `:1143-1161`); `_hh_remediate()` runs drop_caches mid-gate under blanket except-pass (`:1135-1136`). | Genuine throughput regression passes on any throttle false-positive; gate has side effects. (Cross-ref memory: bare drop_caches → NUMA pinning.) | no |
| SEQ-1 | MED | Sequential e-process null = mixture of recent trials of ANY candidate (autopilot.py:2696-2712), not the incumbent; once-seen degenerate qids give full ±1.0 evidence (`sequential_verdict.py:165-185`). | Depressed profile after bad candidates → mediocre candidate accrues wealth to confirm_e=20 anti-conservatively. | idealized profiles only |
| SEQ-2 | MED | With `AUTOPILOT_SEQ_VERDICT` on, `seq_confirmed=None` (fresh journal, missing question_results) skips the anti-ratchet entirely (`safety_gate.py:1374`; autopilot.py:7813-7817). | The hard "no promotion without sequential confirmation" is soft exactly in low-evidence regimes. | None-with-flag-on untested |
| SEQ-3 | LOW | Bridge mode ignores rate REFUTATION (not just confirmation) (`:847`); corrupt journal z<−2 raises inside unwrapped main-loop `gate.check` (autopilot.py:7639). | Rate-refuted candidate confirms on quality alone; hand-edited journal crashes the loop. | no |
| FIELD-1 | MED | EvalResult = 55 fields, 3 inconsistent surfaces: `to_grep_lines` omits the whole tool-telemetry block + suppresses `auroc==0` but not `ece` (`safety_gate.py:365-452`); journal `eval_details` silently drops diversity_*/rubric_*/reviewer_* — the AP-4 axes documented as feeding H-LB are never persisted (autopilot.py:8109-8151); `actions.py:688` bypasses the `tier_specs.objectives_from` chokepoint its own comment forbids. | Field families exist in memory only; downstream consumers reason over silently-partial views. | no round-trip parity test |
| MISC-1 | LOW | `update_tier` unconditionally clobbers top-level speed/cost/reliability on non-frontier-tier promotions (`:654-656`). | T2 promotion corrupts legacy state reporting. | no |
| MISC-2 | LOW | `update_baseline` rebuilds the full journal-derived Pareto archive up to 3×/call; `Baseline.load` per-tier (`:124-145,1408-1448,521-525`). | O(journal) work per promotion attempt, grows forever (see JRN-9). | n/a |

#### Cluster K — RLVR reward contract (`src/autopilot_core/rlvr_tiers.py`)

| # | Sev | Finding | Failure scenario | Tested |
|---|---|---|---|---|
| RLVR-1 | MED | `required_metrics` "quality"/"reliability" never enforced — `_metric_blockers` checks only ece/auroc/question_results (`:172-186`); missing quality → 0.0 via `_as_float` (`:99,215-220`). | Garbage EvalResult-like object → reward from accuracy=0.0, zero blockers, `ready_for_training=True`. | ece/auroc blockers only |
| RLVR-2 | MED | T0 binary reward requires accuracy==1.0 (quality exactly 3.0, `:115`) but T0 saturates ~2.4 (`tier_specs.py:4`). | T0 reward ≈ constant 0 — no training gradient (outcome-side sibling of the EV-CONF phantom). | test enshrines it |
| RLVR-3 | LOW | `ece_missing` blocker dead for the primary caller (ece defaults finite 0.0); AUROC∈(0,0.5) (anti-discriminative) gets positive credit via `clamp01` (`:180-183,211-212`). | Inverted-labels confidence adds positive reward. | no |

#### Cluster L — Persistence, journal & observability

| # | Sev | Finding (file:line) | Failure scenario | Tested |
|---|---|---|---|---|
| **JRN-1** | **CRITICAL ✓verified** | **A torn journal line wedges autopilot startup.** Appends buffered, no fsync/flock, avg 35.9 KB max 336 KB/line (measured — far beyond atomic-append size); loader `_load_existing` bare `json.loads` no try/except (`experiment_journal.py:327-340,411-412`); crashes `_run_loop_inner` (autopilot.py:6140) AND the safety-gate baseline path (safety_gate.py:133). State corruption has an exit-70 recovery path (`state_store.py:99-105`); journal corruption has none. | Host crash mid-append → crash-loop until an operator hand-edits the shard. The eval tower's ONLY durable evidence store has zero corruption tolerance. | no |
| JRN-2 | HIGH | Concurrent appenders unguarded: `append_ledger_event` + `journal_snapshot_create --append` (large multi-syscall snapshot lines) write to the live shard with no lock and no live-autopilot guard (contrast `scrub_journal.py:132-140` which refuses) (`experiment_journal.py:426-427,497-506`; `journal_snapshot_create.py:224,238`). | Operator CLI append during a 300 KB trial commit → interleaved chunks → two corrupt lines → JRN-1 fires. | no |
| JRN-3 | HIGH | Journal is not strict JSON: `json.dumps(default=str)` with `allow_nan=True` + `eval_details["tool_helpfulness"]=float("nan")` default → **634 bare `NaN` tokens live** (`experiment_journal.py:412`; autopilot.py:8147). | jq / JS / Go / starlette-JSONResponse consumers reject rows; masked only because all current readers are Python. | no |
| **JRN-4** | **HIGH** | **No incremental per-question persistence anywhere** — QuestionResults live in memory until trial-end `journal.record()`; progress hooks persist counts only; crash placeholder says "no eval evidence available" (eval_tower.py:1843-1924; autopilot.py:8109-8112,5327-5352). Violates the project-memory requirement (`feedback_incremental_persistence`). | 1,800-question EV-11 rebaseline killed at question 1,750 → zero rows retained, full compute re-spent. (The EV-13a harness got this right — per-PR atomic incremental persistence; the tower itself never did.) | absent — nothing to test |
| JRN-5 | MED | `_load_existing` stops at first missing batch file starting at 0 (`:327-330`). | Archiving the frozen base shard makes the journal load empty despite 449 live trials in `_1`. | no |
| JRN-6 | MED | Shard-blind readers analyze frozen data: base-shard-only defaults in `gen_system_card.py:86`, `item_analytics.py:24,535`, `task_rate_goodput_replay.py:32`, `extract_journal_soft_labels.py:43`, `mine_repl_patterns.py:38`; `optimization_brief.py:41-44` hardcodes base+`_1` (breaks at `_2`). (Correct shard handling exists in 11 other consumers — the pattern is known, adoption partial.) | Item analytics / soft labels "succeed" on 6-week-old data; conclusions look current. | partial |
| JRN-7 | LOW | Lexicographic shard sort orders `_10` before `_2` (`economics/ledger.py:312`, `token_audit.py:27`, `paired_stats.py:54`, `audit_block_report.py:25`). | Order-sensitive last-N windows mis-order past trial 10000. | no |
| JRN-8 | LOW | TSV + JSONL appends are two unsynced writes (`experiment_journal.py:404-412`). | Crash between them → divergent human vs machine views. | no |
| JRN-9 | MED | Unbounded journal growth + full-history eager load at every `ExperimentJournal()` construction (15+ call sites incl. every CLI). | Linear-forever construction cost/memory; each CLI invocation pays it. | no |
| EXP-1 | HIGH | RLVR exporter writes bare NaN into training-input JSONL and `ready_for_training` doesn't flag it — **190 NaN rows in the shipped export**, blockers protect the reward scalar but not `metrics` (`rlvr_tiers.py:102-110`; `export_rlvr_environment.py:103`). | Non-Python RL training loader rejects the file; summary says clean. | no NaN tests |
| EXP-2 | MED | All-or-nothing export: one malformed row aborts the entire run (`:121-134`), no skip/partial mode. | One torn line (JRN-1's producer defect) → total evidence loss for a 1000-trial export, rc=2. | no |
| EXP-3 | MED | Non-atomic truncate-then-write outputs, no tmp+replace (`:101-103,292-296`). | Kill mid-export leaves truncated artifacts at canonical paths, parse as corrupt. | no |
| EXP-4 | MED | No journal-rotation awareness — explicit paths only (`:274-276`). | Pointing at the base shard silently exports only frozen trials ≤999 as "the whole history". | no |
| MET-1 | MED | METRIC line contract has no machine parser, no schema-version anchor; ~14 keys conditionally emitted (zero/NaN-suppressed) — absence vs zero ambiguous; documented consumer is manual awk (`safety_gate.py:365-452`; only non-test consumer = dashboard colorizer regex). | awk/agent consumers silently drop zero-valued trials; renamed keys return empty not error. | emission only |
| MET-2 | LOW | `METRIC ece: nan` emitted unconditionally on NaN (`:400`); suite/species interpolated unsanitized → `": "` in a name breaks field splitting (`:372,387-388`). | Numeric tooling ingests literal `nan` / mis-split fields. | no |
| RPT-1 | MED | Two incompatible schemas share `eval_batch_serving_evaltower_*/summary.json` with no `schema_version` key (A/B-window `:434-441` vs 22-key verifier `:912-916` in `eval_batch_serving_evaltower_window.py`; both live on disk today). | Latest-summary consumers must key-sniff; producer drift breaks silently. | schema stability no |
| RPT-2 | LOW | `summary.json` bare `write_text` while `progress.current.json` in the SAME file uses atomic tmp+replace (`:203-206,246` vs `:431,438,916`). | Truncated-but-present summary — worse than absent (parses as corrupt). | no |
| SEA-1 | LOW | seagym views: unknown partition/tier lands silently in `"validation"` with no unknown-bucket counter (`eval_tower_seagym_views.py:117,130,156-157`); module otherwise sound. | New partition name skews view accounting invisibly. | yes (module) |

#### Cluster M — Module topology & structure

| # | Sev | Finding | Failure scenario | Tested |
|---|---|---|---|---|
| **DRIFT-1** | **HIGH** | Two incompatible `EvalResult`/`SafetyGate` classes reachable under the same bare module name; `structural_lab.py:397,560` inserts `src/` AHEAD of `scripts/autopilot/` on sys.path. Bare-name importers: eval_tower, actions, autopilot, self_criticism, core_v2_calibrate + 13 test files. Both names exist in both files → no ImportError ever. | Any process touching structural_lab before its first bare `from safety_gate import …` silently binds the diversity classes — verdicts evaluate NaN deltas / missing `.tier`. Only import order + sys.modules caching prevents it today. | no |
| DUP-2 | MED | Concrete divergence between the two gate definitions: 15 vs 55 fields; `vs_recovery_ratio` first-class in src but scraped from `details` under 3 alternate key names in prod (autopilot.py:8079-8097); different env vars (`SAFETY_GATE_WARN_ONLY` default ON vs `AUTOPILOT_SEQ_VERDICT` default OFF); `test_minddr` asserts against the dead definitions. | Evolving either side changes nothing/breaks silently on the other. | no parity test |
| ARCH-1 | MED (advisory) | God-module: 3,433 lines fusing ≥9 responsibilities with conflicting change-control regimes — import-time sys.path mutation + registry I/O freezing `DEFAULT_TIMEOUT` at import (`:559-565,776-782`); hardcoded cross-repo dependency; dual-consumer `confidence` field (safety-gate ECE series vs EV-4 calibration — one field, two amendment regimes; the EV-CONF upgrade will silently rewrite the gate-era ECE series); concurrency-policy ladder absorbing scheduling API changes via blanket `except → serial forever` (`:670-671,762-763`); stateless trace-IR/trace-bank/rubric-parsing subsystems riding the same blast radius; two ECE implementations + two partial-failure semantics in one file. | Every unrelated change to the file risks the CRITICAL-blast-radius serialized metrics; refactors silently degrade rather than break. | n/a |
| DRIFT-4 | LOW | `src/autopilot_core/__init__` eagerly imports `rlvr_tiers` and re-exports symbols no runtime consumer uses (all import the module path directly). | rlvr_tiers breakage takes down every unrelated `src.autopilot_core.*` importer at package-import time. | no |
| WT-1 | LOW/MED | Stale registered worktree `epyc-orchestrator.wt-local-frontdoor` (11 commits behind on eval_tower/safety_gate, 0 unique commits, nothing references it); two more registered worktrees carry `src/safety_gate.py` copies (`/mnt/raid0/llm/tmp/model-descriptor-rebase-check`, `/tmp/tmp.D68rlco8oz/promote`). | An agent resolving "the eval tower" into a stale tree runs/edits an 11-commit-old copy. `git worktree remove` is safe (no unique work) — operator call. | n/a |
| DEBT-1 | LOW | Zero TODO/FIXME markers in the audited modules — debt lives in prose comments only (ECE deferral `:2075-2087`, EV-1 placeholder `:1697-1699`, warn-only note in src gate). | Marker-based debt scans report this area clean when it isn't. | n/a |

#### Cluster N — Test architecture

| # | Sev | Finding | Consequence |
|---|---|---|---|
| TEST-1 | MED | Every EvalTower test mocks at `call_orchestrator_forced` or replaces `_eval_question`/`_eval_batch` wholesale; no fake-transport test exists. The ENTIRE inference-failure surface — `_eval_question` except-branch (`:1740-56`), `resp["error"]` path, worker-exception path (`:1884-89`), `eval_cancelled_after_no_progress_timeout` residual — appears in zero tests. | A refactor changing the client error contract (raise vs `{"error":…}`) passes the whole suite while breaking reliability accounting in production. |
| TEST-2 | MED | Three `SafetyGate.check` branches have zero tests: `routing_diversity` (`safety_gate.py:1094-1101`), throughput floor + throttle remediation (`:1103-1169`), `_proxy_check` (`:1217+`). The throttle branch swallows all exceptions — a broken import silently disables throttle detection, unnoticed. | Untested policy branches drift/die silently. |
| TEST-3 | MED | The deliberately divergent inline ECE (`eval_tower.py:2075-2097`, "do NOT 'helpfully' swap") has NO pinning test — the forbidden consolidation would pass CI on a CRITICAL-blast-radius serialized metric. | The one change the code most loudly forbids is the one CI can't catch. |
| TEST-4 | MED | Several tests enshrine defects as intended: QID-1's masking test (wrong namespace), SCORE-07's clamp assertion, SG-7's MAD-zero assertion, RLVR-2's exact-1.0 assertion. | Green tests certify broken behavior; fixing the defects requires fixing the tests. |

Coverage map (full table in the tests-agent transcript): well-tested = `_aggregate` math, MAD/sequential/per-suite core paths, Baseline round-trip, designed-core validation, concurrent no-progress timeout, stat_tests/paired_stats primitives. Untested = everything in TEST-1/2 + serial stall, orphaned threads, subset wall-time bias, sticky caches, apply_state, empty-pool zero-result semantics.

#### What is solid (don't break it while fixing)

`stat_tests.py` (ECE/roc_auc/wilson — correct, sklearn-parity-tested) · `paired_stats.py` McNemar + provenance refusal · `sequential_verdict.py` math core (capped-Kelly, Ville bound empirically tested — weaknesses are all wiring) · `state_store.py` atomic save + flock (the pattern the journal/baseline should copy) · `_load_designed_core` (the model citizen: everything raises) · `_load_audit_block` + promotion min-N fail-closed · trace banks (bounded, deduped, atomic via state) · EV-11 `_require_math_verify` + tool-sentinel "never spuriously passes" design intent · EV-13a harness (per-PR atomic incremental persistence — the pattern JRN-4 needs).

---

#### Fix plan (phased, owner-tagged)

> **Ownership** (per the 2026-07-20 operator ruling in the loop audit): **[loop]** = the parallel
> inference-batch-loop agent (owns `eval_tower.py`, the runner, coordination files — sequence these AFTER
> its current fixes land; do not touch its files from other sessions). **[agent]** = non-loop mechanisms
> (safety_gate.py, experiment_journal.py, debug_scorer.py, exporters, adapters, tests). **[op]** =
> operator decision / MEASUREMENT trust-boundary sign-off. Scoring/threshold semantics are
> human-amendment-only; mechanical robustness (atomicity, locking, validation, provenance) is agent-safe.
> Flip a box only when the fix lands AND its Verify passes.
>
> **Operator decisions (2026-07-20, in-session sign-off):** **B1** approved per recommendation —
> reliability floor + suppress quality gating on unreliable evals (gate-leg [agent], this wave) AND
> exclude errored rows from the `_aggregate` quality denominator (denominator-leg → [loop] queue).
> **B2** approved — quantum-inclusive per-suite threshold. **B5** T0 success threshold 0.8 approved
> (observe-only). **B6** approved as RENAME (`src/safety_gate.py` → `src/diversity_gate.py`) — kills
> the DRIFT-1 collision while preserving the tested EV-8 gate for future wiring. **E4** approved +
> executed. **A3** era-label pre-authorized; execution still gated on the A2 remainder. **EV-11b**
> decided per the prepared decision package (adopt `stat_tests` closed-bin ECE); the [loop] agent
> implemented the closed-bin `_aggregate` path with an era label on 2026-07-20, while EV-11c remains
> the separate fresh math re-baseline. **EV-CONF final scoring decision** remains gated — cannot
> be taken until logprob passthrough lands and confidence is real.
>
> **Traceability (2026-07-20 coverage pass)**: every CRITICAL/HIGH/MED finding above maps to exactly one
> checklist item; LOWs are swept in E5 (or ride a parent item). Mapping — F: SCORE-01/13/14/25→A1,
> 02→A2, 03–12/15/16/21/23/24→B7, 20/22→E5 · G: QID-1→A4, XREPO-1/PATH-1→A2, VERS-1/SHA-1→C1,
> LOSS-1/2→C2(+A3 invariant), SCHEMA-1→C3, SPLIT-1/DISJ-1→C6, PAIR-1/SV-1→C7, QID-2/3→E5 · I: REL-1→B1,
> EMPTY-1/CACHE-1→C4, ET-3/4→C8, ET-5/6→C5, ET-8/9/13/14/15→E5 · J: SG-0→B8, SG-1→B2, SG-2/8→A6,
> SG-3/4/5/MISC-1→B3, SG-7/SG-9/SEQ-3→B9, SEQ-1/2→B4, DUP-1/2+DRIFT-1→B6, FIELD-1→D6, MISC-2→D3 ·
> K: RLVR-1/2/3→B5 · L: JRN-1/2+EXP-2→A5, JRN-3+EXP-1→D2, JRN-4→D1, JRN-5/6/7/8/9+EXP-4→D3, MET-1/2→D4,
> RPT-1/2+EXP-3→D5, SEA-1→E5 · M: ARCH-1→E1, WT-1→E4, DRIFT-4→E5, DEBT-1 advisory · N: TEST-1→E2,
> TEST-2/3/4→E3. If a future edit adds a finding, add its fix item and extend this map.

##### Phase A — stop producing wrong evidence (P0)
> **2026-07-20 execution note:** operator gave the Phase A [agent] go-ahead (= the A1 one-line sign-off).
> Landed in epyc-orchestrator on `spec-dec-mtp-refresh-2026-06-22`: A1+A2-leg `2a41c0bc` (+test fix),
> A5 `935efa64`, A6 `e8bd4ac9`. Implementation by Opus subagents on disjoint file sets; reviewed,
> verified in an isolated worktree, and committed by the orchestrating session. During review, an
> **in-flight uncommitted `_score_multiple_choice` textual-label rewrite by the loop agent** was found
> co-resident in `debug_scorer.py` (its EV-4 "scorerfix"); it was excluded from these commits via
> hunk-filtered staging. Review of that rewrite found a **confirmed containment-bias bug**: with
> choices `["cat","black cat"]`, answer `black cat` scores False vs expected `black cat` and True vs
> expected `cat` (`max(matches)` ranked by match START; a contained shorter choice always starts later),
> and the `"(B)"`-style expected format remained always-False. The loop agent landed the repair in
> orchestrator `8f24679a` by ranking text matches by match END then choice length and adding
> overlapping-choice/`(B)` tests; `0ddce51d` adds the named `None`/`None of the above` containment
> regression. The textual-label support is still a scoring-semantics change and remains part of the
> **B7** sign-off package before EV-4 can be decision-grade.
- [x] **A1 [agent·op] SCORE-01/13/14/25 — kill ALL silent scorer-to-scorer fallbacks.** ✅ 2026-07-20 (`2a41c0bc`; verify: 8-test hard-fail suite incl. in-thread real-math_verify scoring + thread-degrade regression; math_verify's verify() ALSO needed `timeout_seconds=None` off-main-thread — found and fixed during implementation) In `debug_scorer`: (a) `_score_math_verify` calls `parse(..., parsing_timeout=None)` (thread-safe per math-verify's own guidance) with an external timeout, and the bare `except Exception → exact_match` becomes score-as-ERROR (completing the EV-11 mandate at the layer that actually scores); (b) `_score_llm_judge` judge-unreachable → ERROR, not substring (SCORE-13); (c) unknown programmatic verifier name → ERROR, not substring (SCORE-25). One-line operator sign-off (scoring path; consistent with the approved EV-11 hard-fail direction). *Verify:* a threaded batch scores math via math_verify (spot-check a nested `\boxed{\frac{1}{2}}`); induced parse failure / dead judge port / typo'd verifier each yield error, never a silently different scorer.
- [x] **A2 [agent] SCORE-02/XREPO-1/PATH-1 — make module identity deterministic.** *(PARTIAL ✅ 2026-07-20: the debug_scorer leg landed in `2a41c0bc` — `seeding_scoring.score_answer_deterministic` pins the orchestrator copy via explicit same-directory import under `sys.modules['epyc_orch_debug_scorer']`, with a binding test. EvalTower and normal seeding-sampler paths now load research `dataset_adapters`/`question_pool` by file path with `EPYC_RESEARCH_ROOT` honored. Loop-owned research scripts are landed/cleared in research `51868f72`; REMAINING: the CRITICAL `question_pool.build_pool`/CLI/`load_questions_by_ids` shadow surfaces, then operator-era-labeled A3 pool rebuild.)* Single explicit import bootstrap for the benchmark modules (research repo canonical, `EPYC_RESEARCH_ROOT` honored); delete or hard-alias the orch shadow copies (`debug_scorer`, `dataset_adapters` facade, `question_pool`); add a test asserting which copy binds. *Verify:* `sys.modules['debug_scorer'].__file__` is deterministic regardless of eval order.
  - **CLOSED 2026-08-12 (`mainC`), all three legs verified against today's tree rather than against this row's anchors — which have rotted.** This row cites `eval_tower.py:1410,2789` for PATH-1; neither line is the site any more.
    - **SCORE-02** — done. `seeding_scoring.py:29-42` loads THIS repo's `debug_scorer.py` by path under the private `sys.modules` key `epyc_orch_debug_scorer`, so the lazy-import race cannot bind whichever copy won `sys.path` (`2a41c0bc`).
    - **XREPO-1** — the fix was already in place and **had no test**, which is how it would have regressed silently. `_load_research_benchmark_module` (`eval_tower.py:513`) loads by path under a private content-keyed name, cached on `(module, path, mtime_ns)`. Now pinned by `tests/unit/test_research_module_identity.py` (orchestrator `2416fabe`, 5 tests): a same-named module already in `sys.modules` does not capture the load, the bare name is left untouched, an edited research module reloads rather than serving stale (DRIFT-1 sibling), and a missing module fails closed. **Mutation-checked**: swapping the loader for bare `__import__` makes the decoy win and the key test fail, so the test is load-bearing rather than passing for free.
    - **PATH-1** — done. `_research_root()` (`eval_tower.py:509`) honours `EPYC_RESEARCH_ROOT` exactly as its sibling `question_pool.py:29-31` does, and both call sites go through it. Pinned by the same new test file.
    - The remaining `sys.path.insert` calls at `eval_tower.py:2640-2644` are **orch-local** (`_orch_root`), not cross-repo, so they do not reintroduce XREPO-1's hazard. Additive throughout: test-only, no behaviour change.
  - [x] **A2 seeding-sampler canonical research-module binding** — normal seeding sampling now loads research `dataset_adapters`/`question_pool` by file path under private module names instead of relying on bare import order; tests leave stale bare modules in `sys.modules` to prove they cannot win the fast path. ✅ 2026-07-20 (`8d729ca1`; seeding/pool slice 91 passed; loader/module-identity slice 15 passed)
  - [x] **A2 residue — bare `question_pool` imports in the seeding CLI** ✅ 2026-09-16 — FIXED on orchestrator branch `sub/cleanup2-20260916` @ `d111d432` (worktree `/mnt/raid0/llm/worktrees/sub-cleanup2-orch`), integrated by orchestrator merge `dec73e25` (pushed in `753343f5`, 2026-09-16). The residue was flagged unowned in `progress/2026-09/2026-09-16-sub-cleanup.md`. `seed_specialist_routing.py:998` (`--rebuild-pool`), `:1163` (`--question-ids`) and `seed_specialist_routing_v2.py:920` bound whichever `question_pool` came first on `sys.path` (the orchestrator copy), while the sampler reads the research copy. All three now go through `seeding_sampling._load_research_benchmark_module`, following the pattern of `8d729ca1`/`2416fabe`: `build_question_pool()` and `load_questions_by_ids()`, the latter over research `load_pool`, because the research module has no such function. Both fail closed and never fall back to a bare import. Tests: stale-decoy `main()` tests plus three helper tests. **352 passed** across every test file that references `question_pool`/`seeding_sampling`/`seed_specialist_routing`, and ruff shows no new findings. Mutation check: restoring the bare imports fails 4 tests. The orch shadow copy `scripts/benchmark/question_pool.py` itself is not deleted; it is still imported by `deprecated/seed_specialist_routing_v1.py`.
    - **2026-10-24 candidate follow-through:** `refactor/scripts-cleanup-reviewed-01a16fc3` retires the remaining orchestrator `question_pool.py` shadow together with its deprecated v1 importer after current consumer checks. Research remains canonical. The September statement that the shadow still exists describes that historical checkpoint; owner publication of the candidate remains separate.
  - [x] **Integrate `sub/cleanup2-20260916` (`d111d432`) into orchestrator `main`** (owning session; review, then merge). ✅ 2026-09-16 — merged as `dec73e25` (orchestrator `753343f5`).
- [x] **A3 [op + agent] Rebuild the question pool against the full research registry** (after A2), with a build invariant: pool suites ⊇ `ADAPTER_SUITES` AND every suite nonzero (gaia:0 must fail the build; LOSS-1/2 accounting below). **Instrument change → era-label the new pool; never quietly swap** (MEASUREMENT.md). *Verify:* pool header lists all 33 adapter suites with nonzero counts; era registry row appended. ✅ 2026-07-21 — EXECUTED: staged build (offline, research-canonical 34-suite registry asserted via module __file__), all invariants PASS (79,479 rows / 38 nonzero suites; shared suites byte-identical, zero loss; gaia/aa_lcr/document_extraction = 0 with loud source_absent accounting — operator downloads pending); live pool swapped with backup retained; era row **E7-eval-instrument** appended to instrument_eras.yaml under the 2026-07-20 pre-authorization. Staging + REPORT.md: research repo `benchmarks/prompts/pool_rebuild_a3_20260721/`.
- [x] **A4 [loop] QID-1 — unify qid namespaces.** ✅ 2026-07-20 — `ef0f3f21` makes promotion fresh-draw exclusion compare against the union of pool IDs, question IDs, explicit/stable qids, and the stable prompt hash; `_recent_eval_qids` harvests legacy `id` rows too; the masking test now excludes a pool row via its stable hash. *Verify:* `test_eval_t2_promotion_eval_uses_trial_seed_and_excludes_recent_qids`, full `test_eval_tower_instrument_repair.py`, and full `test_autopilot_actions.py` passed.
- [x] **A5 [agent] JRN-1/2 + EXP-2 — journal durability.** ✅ 2026-07-20 (`935efa64`; verify: torn-tail load-tolerance + sidecar quarantine-on-append + mid-file hard-fail + snapshot live-PID guard + exporter --skip-bad-rows; 29 new/updated + 89 existing journal-suite tests green) Append under the existing `state_lock` flock pattern + flush/fsync; `_load_existing` quarantines a torn TRAILING line (rename to `.corrupt`, log loudly, continue) and hard-fails on mid-file corruption; `journal_snapshot_create --append` gets the scrub_journal live-PID guard; exporter gets `--skip-bad-rows` with accounting. *Verify:* truncate the last line of a copy → loader recovers; concurrent append test.
- [x] **A6 [agent] SG-2/SG-8 — baseline durability.** ✅ 2026-07-20 (`e8bd4ac9`; verify: atomic tmp+fsync+replace on BOTH writers, BaselineCorruptError on empty/malformed, typed speed/cost/frontdoor_speed validation incl. non-finite, schema_version:1 round-trips; 86 gate-suite tests green) `Baseline.save()` → tmp+`os.replace`+fsync (copy `state_store.py`); `load()` catches parse errors → explicit corruption path (exit-70 style, not AttributeError); validate speed/cost/frontdoor_speed types/signs; add `schema_version`. Consolidate the second writer (autopilot.py text surgery) onto the one code path. *Verify:* corrupt-file tests for empty/truncated/type-wrong baselines.

##### Phase B — gate & scorer correctness (operator-adjacent semantics)
> **2026-07-20 wave-3 execution note:** D4/D6-emit/B9/B4-gate → `ade26db3`; D6-journal/B4-plumbing/
> SEQ-1/SEQ-3 → `7fb77e68`; ECE pin test committed separately. 390 tests green at the committed state
> in an isolated worktree. Cross-agent: the loop agent independently landed `8f24679a` (incl. the
> EV-11b closed-bin implementation, era-labeled — the pin now locks it) and `b22d99d0` (C2's MATH-500
> coverage gate on the rebaseline). METRIC consumers note: grep-line contract is now v2
> (schema_version line, unconditional null-gated emission, parse via scripts/autopilot/metric_lines.py).
> Remaining open: B7 bundle (operator sign-off + debug_scorer freeze window), C2-verify/PAIR-1/E2/A4
> (loop agent), A2-remainder → A3 (blocked on loop agent's research-repo landing), EV-CONF plumbing.
> **2026-07-20 wave-2 execution note:** B1(gate-leg)/B2/B3/B8 → `1b3da6ea`; B5/B6 → `4e9efe32`;
> D2/D3 → `969e0620`; SV-1 → research `d8bb2d0e`; E4 executed. Full wave verified green (163 tests)
> in an isolated worktree at the committed state. The loop agent independently landed `8f24679a`
> (denominator hardening, eval-batch wall budget, question_id journaling, and the multiple-choice
> rewrite WITH the relayed containment-bias fix — verified: ranks by match end+length, probe cases
> correct). Still open in this phase: B4 (SEQ), B7 (bundled scorer-semantics package — now includes
> reviewing the loop agent's committed mc rewrite), B9 (SG-7/SG-9/SEQ-3), D4/D6, E2/E3, C2 loader
> accounting, PAIR-1, and the A2-remainder→A3 chain. Loop-owned research adapter/runner dirt is now
> landed/cleared in research `51868f72`; do not rebuild the pool until A2 completes and A3 is era-labeled.
- [x] **B1 [op·agent] REL-1 — decide + implement reliability conditioning.** Options: (a) reliability floor violation in `check()`; (b) exclude errored rows from the quality denominator (aligning tier path with the calibration paths) + n_scored minimum; (c) both. Interacts with loop-audit B3 (`decision_grade`). Gate semantics → operator decision, agent implements. **Denominator leg ✅ 2026-07-20 ([loop])**: `_aggregate` now computes quality/per-suite/partition quality over non-error rows, records `n_scored`/`quality_denominator`, and runner decision-grade blockers require full non-error scoring; reliability-floor gate leg remains in the audit wave's `safety_gate.py` scope. *Verify:* 20%-error trial → blocked as unreliable, NOT failed as quality regression. ✅ 2026-07-20 gate-leg `1b3da6ea` (floor 0.8, quality-gating suppressed on unreliable evals, no rollback-counter increment); denominator-leg landed by the loop agent in `8f24679a` (its session owns that verify/flip)
  - [x] **B1 denominator leg verification** — loop-owned `_aggregate` denominator hardening is verified and tracked. ✅ 2026-07-20 (`8f24679a`; `test_aggregate_quality_denominator_excludes_error_rows`; focused scorer/denominator/EV-11 stats slice 14 passed; broader eval-tower slice 132 passed)
- [x] **B2 [op] SG-1 — restore documented threshold intent**: quantum-inclusive comparison (`suite_delta < threshold - EPS` or round-to-quantum) so a single flip never hard-fires. One-line instrument amendment. *Verify:* the 186-combo sweep produces zero single-flip violations; multi-flip still fires. ✅ 2026-07-20 (`1b3da6ea`; single flip = at-resolution noise per MEASUREMENT MDE; property sweep n=2..60)
- [x] **B3 [agent] SG-3/SG-5/SG-4/MISC-1 — baseline integrity.** Strict same-tier baselines for regression/monotonic gates (no legacy fallback; missing baseline → seed-don't-gate); NaN quality → explicit blocker verdict; `apply_state` gets the archive-max guard; `update_tier` stops clobbering non-frontier scalars. *Verify:* T2-no-baseline seeds instead of violating; NaN quality → blocked. ✅ 2026-07-20 (`1b3da6ea`; strict scalar tier baselines — per-suite accessor stays lenient by scope)
- [x] **B4 [op·agent] SEQ-2/SEQ-1 — harden the anti-ratchet.** Flag-on + `seq_confirmed=None` must NOT silently fall through (block, or explicit advisory verdict with journal marker — operator choice); document/repair the baseline-profile provenance (incumbent-only or provenance-filtered). *Verify:* fresh-journal promotion attempt with flag on → blocked/marked, not silently legacy-pathed. ✅ 2026-07-20 (gate-leg `ade26db3`: seq-inputs-unavailable → refuse with seq_refused_reason; plumbing `7fb77e68`: incumbent-representative null profile (frontier/keep, min 3) else inputs-unavailable)
- [x] **B5 [agent] RLVR-1/2/3** — enforce quality/reliability in `_metric_blockers`; T0 success threshold vs actual saturation (op sign-off on the number); block/zero sub-chance AUROC credit. *Verify:* quality-missing payload → blocker; auroc=0.3 → no positive discrimination credit. ✅ 2026-07-20 (`4e9efe32`; T0 thresholds 0.8/0.9 operator-decided, observe-only)
- [x] **B6 [op] DUP-1/DUP-2/DRIFT-1 — decide the diversity gate's fate**: wire `src/safety_gate.py` into the live accept path (EV-8 exit criterion) OR delete it and fold the fields into the real gate. Either way: exactly one `safety_gate` module name importable (rename to `diversity_gate.py` if kept); fix `structural_lab` sys.path insertion. *Verify:* `python -c "import safety_gate"` resolves identically from every entry point; grep shows one definition of EvalResult. ✅ 2026-07-20 (`4e9efe32`; executed as RENAME src/safety_gate.py→src/diversity_gate.py + structural_lab sys.path fix + module-identity lock test)
- [x] **B7 [op·agent] SCORE-03..12,15,16,21,23,24 — scorer extraction & oracle correctness package.** Bundle the scoring-semantics repairs into ONE operator-reviewed package (one sign-off, one era note — not a dozen drip amendments): anchor colon/quote fallback extraction to the final-answer region only (03; deterministic scorer leg landed `07a20a7c`); `repr()`-interpolate expecteds + real args or drop the `entry_point` oracle form, and treat oracle-infra failures (missing tmp dir) as ERROR not wrong (04/05 scoring side; deterministic scorer leg landed `07a20a7c`); boundary-anchored substring matching (06, live T0 sentinels; deterministic scorer leg landed `07a20a7c`); rubric judge score RANGE VALIDATION not clamping + judge-vs-heuristic provenance flag + empty-rubric ≠ 1.0 (07/08/09); multiple_choice letter guard exact-match + normalization for `(B)`/`B.` plus configured textual labels/overlapping choices (11; implementation landed `8f24679a`, exact overlap coverage expanded `0ddce51d`, still not signed off); remove the phantom `pass_rate` confidence read or source it from an actual scorer output (12 — coordinate with EV-CONF); `\boxed{}` fallback restored to whichever exact_match copy survives A2 (16; deterministic scorer leg landed `07a20a7c`); comma/number normalization (15); reject vacuous `assert True` oracles at scoreability time (21; deterministic scorer leg landed `07a20a7c`); `str()`-wrap non-string expecteds (23; deterministic scorer leg landed `07a20a7c`); multiset F1 + multi-group pattern guard (24; deterministic scorer leg landed `07a20a7c`). **Sequence BEFORE A3/EV-11c and before EV-4 can be decision-grade** so the pool rebuild + rebaseline era-label captures a single scorer change. *Verify:* golden-file scorer regression suite (inputs → expected verdicts) covering every repaired case, run against BOTH pre- and post-package scorers to document the delta. ✅ 2026-07-21 — RATIFIED (op-bundle ESC-6 option B) + golden-delta doc landed (`orchestration/reports/b7_scorer_golden_delta_20260721/`: 146 rows, 50 finding-traced changes, 21/39 sentinels package-sensitive, corpus pin test). Package live since `07a20a7c`+`8f24679a`; era boundary = E7-eval-instrument.
- [x] **B7b [agent·op] SCORE-07/08/09/12 — scorer-semantics remainder**: rubric judge range-VALIDATION not clamping (07), judge-vs-heuristic provenance flag + empty-rubric ≠ 1.0 (08/09), remove/replace the phantom `pass_rate` confidence read (12 — coordinate with EV-CONF's real-confidence path). Same one-sign-off discipline; extend the golden corpus + pin in the same commit. ✅ 2026-07-21 — RATIFIED (operator: 'all four as one package') and committed with golden-corpus extension (+13 rows, 159/58 totals pinned; B7 sub-counts unchanged) and 242-test verification incl. ECE-pin + paired-significance drift guards.
  - [x] **B7 deterministic scorer sub-leg dashboard anchor** — final-region exact-match, boundary substring/llm-judge, multiple-choice overlap, boxed extraction, F1, and code-execution hardening landed; parent stays open for remaining scorer package + operator sign-off. ✅ 2026-07-20 (`07a20a7c`, `8f24679a`, `0ddce51d`; text-label choices rank by match end then length, including `cat`/`black cat` and `None`/`None of the above`; 93 scorer tests + 14 focused scorer/denominator/EV-11 tests)
- [x] **B8 [agent] SG-0 — make the baseline-ratchet freeze loud and predictable.** `_baseline_eligible` ineligibility becomes a first-class journaled event + verdict marker (not a `log.warning`): journal row + operator-outbox entry stating WHY (matrix stale/missing, speed-metric mode) and since when; pre-expiry alert ≥7 days before the 30-day wall; key staleness off the YAML `measured_at`, not file mtime (same repair as loop-audit A6, applied to this consumer; cross-ref H1 hard-gating). *Verify:* backdating the matrix `measured_at` → next `update_baseline` emits the journaled freeze event + outbox row; a `touch` of the file no longer resets the clock. ✅ 2026-07-20 (`1b3da6ea`; ineligible_reason on BaselineUpdateResult, log.error + 7-day pre-expiry countdown)
- [x] **B9 [agent·op] SG-7/SG-9/SEQ-3 — significance & throttle hygiene.** MAD=0 windows: require ≥2-quantum delta (or explicit saturated-suite handling) before "significant", and tag NaN-z outcomes (SG-7 — semantics change → op sign-off); throttle branch: remove the in-gate `_hh_remediate` side effect, use `flush_cache_with_pause` if remediation stays (memory: bare drop_caches pins NUMA), and make throttle-demotion a journaled advisory rather than an invisible pass (SG-9); bridge mode: rate REFUTATION still blocks even when confirmation is advisory + guard `rebuild_candidate_view` against out-of-range journal z (SEQ-3). *Verify:* unit tests for each branch (they currently have zero). ✅ 2026-07-20 (`ade26db3` + `7fb77e68`: MAD-zero 2-quantum rule, no in-gate drop_caches, explicit throttle demotion, bridge rate-refutation blocks, floor-only z guard w/ skip+count preserving the Ville bound, main-loop check wrapped)

##### Phase C — data-plane integrity
- [x] **C1 [loop] VERS-1/SHA-1 — instrument identity on every result.** Stamp `dataset_content_sha256` (extended with `suite` + canonicalized `scoring_config`) into every tier EvalResult + journal row; warn on cross-trial drift under the same core_id. *Verify:* pool rebuild mid-era → next trial logs an instrument-drift warning. ✅ 2026-07-20 (`9f9128bc`; every T0/T1/T2/T3 EvalResult now carries `dataset_content_sha256`, `dataset_sha256`, `test_profile`, and `test_profile_json`; same-core drift emits `instrument_drift_warning`; 43 focused tests green) *(2026-07-21 verification caveat: drift check is process-local in-memory; a durable cross-restart pin is a small follow-up)*
- [x] **C2 [agent] LOSS-1/2 — loader accounting.** Adapters count+log dropped rows; sub-dataset failures raise or record `degraded_sources`; pool loader reconciles loaded counts vs header stats; `eval_math_rebaseline` gates on `n_math500>0`. *Verify:* deleting MATH-500 cache → rebaseline refuses decision-grade. *(✅ 2026-09-16: adapter loss accounting, EV-11 math rebaseline gate and EvalTower canonical research-module binding had landed; the A3-era pool build invariant, the last open leg, is now integrated (sub-box below).)*
  - [x] **C2 research-side adapter loss accounting** — `dataset_adapters.py`/`question_pool.py` count dropped rows and preserve adapter loss/degraded-source accounting. ✅ 2026-07-20 (`7d138bf5`; dataset/pool adapter slice 147 passed)
  - [x] **C2 EV-11 math rebaseline non-empty MATH-500 gate** — refuses `n_math500=0` before inference. ✅ 2026-07-20 (`b22d99d0`; `tests/unit/test_eval_verifier_mode.py tests/unit/test_eval_tower_ev11_stats.py -q` 33 passed)
  - [x] **C2/A2 EvalTower canonical research-module binding** — `_load_pool()` and `_load_dataset_adapter()` load research benchmark modules by file path under private names, so stale bare `question_pool`/`dataset_adapters` entries cannot win through `sys.modules` order; `EPYC_RESEARCH_ROOT` is honored for both paths. ✅ 2026-07-20 (`a4fd1c41`; loader/verifier/instrument slice 73 passed; seeding/pool slice 91 passed; module-identity/scorer-binding slice 4 passed)
  - [x] **C2 A3-era pool build invariant codified in `build_pool`** — ✅ 2026-09-16 (`sub-sweep`): research
    `88b1160d` (branch `sub/nextaction-sweep-20260916`), integrated as cherry-pick `04124a54` with merge `9777a3d5` on
    research `main`. A3's invariant was only checked by the untracked staging validator; `build_pool` wrote a
    failed or empty suite as `0` over the live pool. It now raises `PoolBuildInvariantError` before writing when a
    registered adapter suite is missing, or when a suite has zero rows and no recorded reason. Accounted zeros
    (an extraction error, or adapter `degraded_sources` such as gated GAIA) pass and are listed in the new header
    key `empty_suites`. The write uses tmp + fsync + `os.replace`. Tests: `test_question_pool.py` +
    `test_dataset_adapters.py`, 8 passed. The live pool was not rebuilt; this is a build-time guard.
- [x] **C3 [loop] SCHEMA-1 — load-time question validation** (require prompt/expected/suite; reject rows, never mis-score); sentinel YAML schema check. *Verify:* promptless row → excised+counted, not scored-wrong. ✅ 2026-07-20 (`15ae635e`; sentinels/tool-sentinels/pool rows validate required fields + scoreability, dropped rows counted)
- [x] **C4 [loop] EMPTY-1/CACHE-1 — fail-closed + retryable loaders.** Empty pool/sentinels → details-error result (copy the T3 pattern) in T0/T1/T2; don't cache failures; refresh caches on file mtime change. *Verify:* transient pool failure recovers on next eval without restart. ✅ 2026-07-20 (`15ae635e`; T0/T1/T2 return stamped `loader_error` details with `decision_grade=false`; missing/failed/invalid loads are retryable without restart)
- [x] **C5 [loop] ET-6/ET-5 — decision-metric hygiene.** Exclude `tool_sentinel` partition from decision aggregates until secrets minted (or gate on minted-secret detection); compute decision-subset speed over subset wall time (or flag subset-speed as non-comparable). *Verify:* audit-on vs audit-off trials produce comparable speed under one instrument id. ✅ 2026-07-20 (`9204d6b7`; audit/tool-sentinel partitions excluded from decision aggregates, full-batch telemetry preserved, partition-filtered speed uses comparable median request TPS, decision dataset SHA stays stable across shadow rows) **DEFECT (2026-07-21 verification) FIXED same day: `_baseline_eligible` now strips the `_partition_filtered` provenance suffix; regression tests added.**
- [x] **C6 [loop] SPLIT-1/DISJ-1** — strict split matching (exact after shared normalization, error on zero matches — keep the loud ValueError); T2 non-promotion draws exclude the T1 core qids. ✅ 2026-07-20 (`4808ef33`; split filtering now exact after shared normalization, `HE-R` no longer matches `HE-R+`; non-promotion T2 unions caller exclusions with T1-core identities and fails closed when the non-core pool is empty)
- [x] **C7 [agent] SV-1/PAIR-1** — `is not None`-based label alias chain; unlabeled rows dropped+counted; `screen_paired_arms` refuses one-sided provenance. ✅ 2026-07-20 (SV-1 landed in research `d8bb2d0e`; PAIR-1 landed in orchestrator `1c655076`) **RESIDUAL (2026-07-21 verification) FIXED same day: both-arms-None now refuses with `provenance_missing_both`.**
  - [x] **C7 PAIR-1 provenance refusal** — `screen_paired_arms` refuses one-sided provenance instead of allowing a half-identified McNemar verdict. ✅ 2026-07-20 (`1c655076`; `tests/unit/test_eval_tower_paired_significance.py` 8 passed)
- [x] **C8 [loop] ET-3/ET-4 — stall protection + orphan drain in `_eval_batch`.** Serial path gets the same no-progress watchdog the concurrent path has (plus an end-to-end per-question deadline — httpx read-timeout is per-read); after a watchdog fire, drain/join workers with a bounded timeout BEFORE the shared client closes, and mark the trial's follow-on measurements contaminated if requests were abandoned server-side (llama-server keeps decoding them). *Verify:* a byte-trickling fake transport in serial mode fails closed within budget; post-timeout, no in-flight request outlives the batch unaccounted. ✅ 2026-07-20 (`151638c7`; serial path now uses per-question no-progress futures, concurrent+serial watchdogs run bounded orphan drain via `AUTOPILOT_EVAL_ORPHAN_DRAIN_TIMEOUT_S`, abandoned requests set `eval_orphan_contamination`, aggregate details expose `eval_contaminated_by_abandoned_requests`, and learning exclusion journals them as `eval_abandoned_requests`; broad eval-tower slice 132 passed)

##### Phase D — durability & observability
- [x] **D1 [loop] JRN-4 — incremental per-question persistence** (the project-memory requirement): append compact QuestionResult rows to a per-trial JSONL during `_eval_batch` (atomic per-line, EV-13a pattern); crash-recovery ingests partials. *Verify:* kill at question k → k rows on disk, recovery reports partial evidence. ✅ 2026-07-20 (`7931c478`; durable O_APPEND JSONL rows with fsync, strict JSON, env/trial/default artifact roots, no prompt/expected/raw-answer leakage, batch-start/question-result/batch-complete recovery rows; 103 focused eval-tower/eval-batch tests green)
- [x] **D2 [agent] JRN-3/EXP-1 — strict JSON at every serialization boundary**: `allow_nan=False` + None-instead-of-NaN convention (emit `null`, document absence semantics) in experiment_journal, export_rlvr_environment, state_store; exporter flags NaN-metrics rows instead of `ready_for_training:true`. *Verify:* `jq . ` over a fresh journal shard + export succeeds. ✅ 2026-07-20 (`969e0620`; NaN→null + allow_nan=False in journal/state/exporter, metrics_nonfinite row flags; legacy NaN shards still load)
- [x] **D3 [agent] JRN-5/6/7/8/9 + EXP-4 — one canonical shard iterator** (`journal_shards()`: numeric sort, gap-tolerant, all-shards default) adopted by the base-only readers listed in JRN-6; TSV made derived-view-only or written after JSONL commit (JRN-8); add a streaming/tail-N read path so CLI tools and `Baseline.load` stop paying full-history eager load (JRN-9, also relieves MISC-2's 3× archive rebuilds). *Verify:* archived base shard no longer empties the journal; `_10` sorts after `_9`. ✅ 2026-07-20 (`969e0620`; journal_shards module adopted by _load_existing + 12 readers)
- [x] **D4 [agent] MET-1/2 — METRIC contract**: `METRIC schema_version` line, unconditional emission with explicit `null`, sanitize interpolated names, ship the one blessed parser module and point consumers at it. ✅ 2026-07-20 (`ade26db3`: schema_version 2, unconditional null-gated emission, sanitized names, metric_lines.py blessed parser + round-trip contract test)
- [x] **D5 [loop] RPT-1/2 + EXP-3 — artifact atomicity + versioning**: `schema_version` key in both summary.json schemas; atomic tmp+replace for summary/export writes (the code already has `_atomic_write_json` — use it). ✅ 2026-07-20 (`536529eb`; tier + verifier report summaries already carry schema versions, `_atomic_write_json`/`_atomic_write_text` now fsync temp files and parent directory around `os.replace`; 14 focused report-window tests green)
- [x] **D6 [agent] FIELD-1 — emission-surface parity for EvalResult.** Journal `eval_details` carries the documented field families (diversity_*, rubric_*, reviewer_* — the AP-4/H-LB axes currently never persisted), `to_grep_lines` emits the tool-telemetry block its own comment promises, ece/auroc suppression made symmetric; route `actions.py:688` through the `tier_specs.objectives_from` chokepoint it currently bypasses. Add a three-surface round-trip parity test (fields ↔ grep-lines ↔ eval_details) that fails when a new field is added to only one surface. *Verify:* parity test green; a journaled trial with rubric suites shows rubric_* in eval_details. ✅ 2026-07-20 (emitter `ade26db3`: tool-telemetry block emits; journal `7fb77e68`: diversity/rubric/reviewer families persist + completeness-guard parity test; actions.py objectives via tier_specs chokepoint)

##### Phase E — structure & test architecture
- [ ] **E1 [loop·coord, after its queue] ARCH-1 — split the god-module** *(PARTIAL 2026-07-21 verified: trace-IR/trace-bank → `eval_tower_trace_feedback.py` (`0d6f0a41`/`d11baf66`), calibration metrics → `stat_tests` (`5603bcf0`), behavior-preserving, ECE pin green; concurrency ladder + import bootstrap + rubric-parsing seams still open)* (mechanical extraction, no behavior change): stats (calibration/rank/paired) → the existing `stat_tests`/`paired_stats` homes; concurrency-policy ladder → scheduling-owned module with a LOUD degraded-reason contract (kills the blanket except→serial); trace-IR/trace-bank/rubric-parsing → sidecar modules; one import bootstrap, no runtime sys.path mutation; `DEFAULT_TIMEOUT` read lazily.
- [x] **E2 [agent] TEST-1 — fake-transport error-path suite** (httpx MockTransport): timeout, 5xx, `{"error":…}`, worker exception, watchdog residual branch; asserts REL-1's chosen semantics end-to-end. ✅ 2026-07-20 (`ae9854bd`; `_eval_question`/`_eval_batch` fake-transport error-path coverage; `tests/unit/test_eval_tower_paired_significance.py tests/unit/test_eval_tower_concurrency_metrics.py -q` 50 passed)
- [x] **E3 [agent] TEST-3/TEST-2/TEST-4 — pin the landmines, fix the bug-enshrining tests** *(MOSTLY ✅ 2026-07-20: ECE pin committed (locks ev11b_closed_bin era, guards revert + un-relabeled change); three gate branches tested in `ade26db3`; import-identity in `4e9efe32`; qid round-trip + QID-1 fixture repair landed with A4; REMAINING: SCORE-07 clamp repair rides B7)*: EV-11b closed-bin ECE pin test landed locally ✅ 2026-07-20 (`test_aggregate_ece_uses_ev11b_closed_top_bin_stat_tests`); remaining pins/repairs: SCORE-07 clamp repair and any B7-era scorer package pins that still assert a defect as intended. ✅ 2026-10-31 reconciliation — SCORE-07 `b5da2080824e56fbdccc3dd38aac2ad6a31f04bc`, TEST-2/SG-7 `ade26db3a9bda9b95500bc0f070ab929300fcffb`, RLVR-2/import `4e9efe3285dca6c44ef57f642971616d7b3ad9ef`, QID-1 `ef0f3f21df39559acd36516e0c2d780f61a5651d`; [194 targeted tests and provenance](../../artifacts/non-inference/codex-ni-next-accepted-20261031/CAPSULE.md#e3-existing-test-task-reconciliation) passed, including 159/58 golden pin. Existing code completion verified; no new engineering output. [belief: cc]
  - [x] **E3/A4 qid round-trip + QID-1 masking fixture** — verified complete with A4's union-based recency exclusion and repaired masking test. ✅ 2026-07-20 (`ef0f3f21`; `_recent_eval_qids` harvests qid/stable_qid/question_id/id, promotion eval excludes by stable prompt hash against pool rows, `test_eval_t2_promotion_eval_uses_trial_seed_and_excludes_recent_qids`, `test_recent_eval_qids_excludes_only_rows_inside_recency_window`)
- [x] **E4 [op] WT-1 — worktree hygiene** ✅ 2026-07-20 (operator-approved; all three removed: frontdoor re-verified 0-unique-commits + clean, `model-descriptor-rebase-check` clean with HEAD reachable from main, `/tmp/.../promote` clean; only the canonical tree remains registered).
- [ ] **E5 [agent] remaining LOWs sweep** — ET-8 watchdog=0 fail-fast; ET-15 suite-health freshness bound + stat-race guard; ET-14 `on_question` thread-contract note + locked tap write; DRIFT-4 lazy rlvr facade; SCORE-20 AUROC label guard; SCORE-22 cross-family gate gets the resolved MODEL name, not the role; QID-2 single shared `_stable_question_qid` (kill the two copies) + document id-mutability; QID-3 duplicate-qid accounting in paired vectors/core lookup; ET-9 seed-driven replacement draw; ET-13 honest routing buckets; SEA-1 unknown-partition counter; ET-12 fix or delete `progressive_eval`'s stale contract.
  - 2026-11-01 partial E5: orchestrator `b2b8e7bcc28956d6237a097708655435d03d5348` (published merge `3182846824ad50ec6201fde523f25aa1c5ecab51`) guards disappearing suite-health reports and serializes prompt tap writes. Negative control fails original source as intended; 29 native tests pass under R4 78–79, drained. HIGH GitNexus impact stopped ET-8 and EvalTower contract note; no canonical freshness bound found, so ET-15 freshness and E5 remain open. Evidence: APP `artifacts/validation/eval-tower-e5-20261101/README.md`. [no-belief: source conformance controls]

#### Interactions with existing workstreams
- **EV-CONF** (logprob passthrough): SCORE-12's phantom `pass_rate` confidence and ARCH-1's dual-consumer `confidence` field are the same plumbing — land EV-CONF's neutralize-then-plumb sequence with A1/C-cluster awareness; note the gate-era ECE series rewrite risk (ARCH-1).
- **EV-11b/EV-11c**: EV-11b closed-bin ECE is implemented and era-labeled in `_aggregate`; EV-11c remains the inference rebaseline and MUST wait for A1 (else it re-runs on a thread-degraded scorer) and benefits from A3's rebuilt pool + C1 stamping.
- **EV-4**: SV-1 label integrity + A1 are preconditions for a trustworthy calibration baseline.
- **Loop audit Phase 0–3**: A4/C3/C4/C5/C6/D1/D5 touch `eval_tower.py`/runner → sequence into the loop agent's queue after its current fixes; everything tagged [agent] is disjoint from its files.
- **EV-8**: B6 is the decision point the EV-8 exit criterion has been implicitly waiting on since 2026-04-22.

#### Constraints
- **Read-only audit**: nothing was edited; `eval_tower.py`, the runner, and coordination files carry the parallel loop agent's live uncommitted work — its ownership per the 2026-07-20 operator ruling stands.
- **MEASUREMENT trust boundary**: scoring semantics, thresholds, eval concurrency (fixed at 3 as part of the instrument), and era handling are human-amendment-only. Items tagged [op] change instrument semantics; [agent·op] are bug-fixes on the scoring path that still take a one-line sign-off (EV-CONF precedent). Pool rebuild (A3) is an instrument change → era label, never edit-in-place.
- The former `eval_tower.py:2068` inline-ECE tripwire is retired by EV-11b; new outputs carry `details["ece_binning"]="closed_top_bin_stat_tests"` and `details["ece_instrument_era"]="ev11b_closed_bin_2026_07_20"`.

#### DEFERRED — non-inference eval-tower hardening (operator decision, 2026-07-22)
The non-inference eval-tower hardening cluster is **DEFERRED to a genuine quiet window** per operator. It was scoped + ready but held: `scripts/autopilot/eval_tower.py` is **single-writer** to the live inference-batch / eval-batch loop, and a sustained `eval_batch_serving_evaltower_window.py --mode calibration` campaign was running (repeatedly spawning windows), so editing that surface from a side session would violate the "do not edit from a side session" rule.
Pick up when **no** eval-batch/calibration run is live — gate check: `pgrep -f evaltower_window` returns nothing (and `:8000` idle). Deferred tasks (all still `- [ ]` in their owning handoffs):
- **A2** single-import bootstrap + delete/hard-alias orch shadow copies (this handoff) — fixes the CRITICAL nondeterministic module binding.
- **C2** loader accounting / silent-drop guard (this handoff).
- **E5** ~12 mechanical `[agent]` LOW fixes (this handoff).
- **EV-RUNNER-BACKOFF** bounded backoff on connection-refused — [eval-tower-verification.md](eval-tower-program.md) (stops burning eval budget during API reloads).
- **safetygate provenance fields** `started_at`/`ended_at` + `--resume-incomplete-from` — [completed SafetyGate/RLVR provenance audit](../completed/safetygate-rlvr-provenance-audit-2026-07-22.md).

#### NI08 diagnostic routing source follow-up — 2026-10-07

- [x] **ET13-ROUTING-SOURCE — preserve honest diagnostic route buckets and validate the actual whole-module source controls.** Attribute exact frontdoor, worker and architect routes with architect precedence; retain unknown/empty/model-ID routes in an explicit unknown bucket and preserve original route bytes. MAIN reviewed the two-file candidate from APP ce48; bind all four whole selected modules/140 expanded cases and complete eager source/config/locked environment before hosted native capture. Existing CI carrier/projector/shared grade only; no result denominator, gate/default/objective, runtime/inference or release change. This bounded source task does not close the mixed E5 sweep. Native conformance is tracked by VB-ET13-ROUTING-CONFORMANCE. ✅ 2026-10-07 — [MAIN exact source and original140/140](../../artifacts/ni08/et13-honest-routing-source-acceptance-20261007/README.md); native TRUE/shared Judged/Located, original setup/NULL/FALSE retained; live/runtime and mixed E5 remain open.

## Track: eval-tower-loop-robustness-audit-2026-07-20
<!-- gate: none -->

> Folded from `handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md` @ `c4b6d1388716` on 2026-11-02 (BRF-T1-F2, route 1a, operator D1/D5; retired row EVL-13 → EVL-14). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Eval-Tower / Inference-Batch-Loop Robustness Audit (2026-07-20)

**Status: IMPLEMENTATION CHECKPOINT — original read-only audit plus executed Phase 0-3 unblock checklist.**
The original read-only review was triggered by the EV-4 `INFRA_BLOCKED` failure while working the P2
eval-tower entries of `inference-batch-loop.md`; five audits (4 subagent + 1 scoring, all
evidence-backed and independently spot-verified) produced the findings below. The 2026-07-20
follow-up implemented the checked Phase 0-3 agent-fixable items; EV-4 itself remains open.

**Sidecar checkpoint (2026-07-20T19:17Z, EV-4 still open):** the Phase-0 EV-4
unblock reached a real preflight checkpoint. `preflight_gate` now emits a separate
16-char contention topology hash and full registry hash. Fresh attestation
`coordination/inference-batch/attestations/20260720T191355.json` passed for EV-4
CPU roles `frontdoor+worker_general` with
`topology_hash=expected_topology_hash=8c8cfcbb13d2611d`. The prepare-only
`run_batch_entry.py --batch-entry /tmp/ev4-batch-entry.json` preflight reported
`blocking_reasons=[]`, `stack_contract.ok=true`, and `topology.verified=true`
with `live_hash=required_hash=8c8cfcbb13d2611d`. Root coordination verification:
`/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -m pytest scripts/coordination/tests/test_batch_ledger.py scripts/coordination/tests/test_batch_status_report.py -q`
=> 31 passed. This is not an EV-4 completion signal and does not flip EV-4.

**Cross-links:** [eval-tower-verification.md](eval-tower-program.md), [inference-batch-loop.md](eval-tower-program.md#track-inference-batch-loop), [within-role-placement-state-machine.md](numa-placement-and-contention.md#track-within-role-placement-state-machine), [v7-promotion.md](../completed/v7-promotion.md).

#### Headline (corrected root cause)
The EV-4 failure is **three independent defects stacked**, and the premise that the *kernel* promotion
caused it is **wrong**:
1. **The stale contention matrix is the root** — and it went stale because of the **2026-07-17
   `vision_escalation` NUMA rebind (commit `139ba643`, 5 instances → 1)**, NOT the v7 kernel cutover.
   `topology_fingerprint` hashes only `(cpu_list, port, threads)` (`src/scheduling/contention.py:806-826`),
   so a pure kernel swap cannot move it; a *measured-role NUMA change* did. Reproduced: old shape →
   `df373c79cc4af06f`, live shape → `8c8cfcbb13d2611d`.
2. **The runner silently degraded** (fanout → concurrency=1) and then a **partial serial run was killed**
   leaving a **dirty stack + a decision-grade-looking empty result**.
3. **The batch entry itself is mis-pinned + the loop can't resume** it after an infra-block.

**Confirmed production-scope finding:** the same stale matrix has, since 2026-07-17, been silently
degrading **production cross-role concurrency** — `contention_gate` fail-closes background decode to
`QUEUE` and foreground to `DEGRADED_ALLOW` whenever `matrix_health() != OK`, and the shape-aware /
per-region-lock flags are live prod defaults (`orchestrator_stack.py:1648,1659`). (A related claim that
`safety_gate` blocks all v7 baseline writes **did NOT reproduce** — no `_baseline_eligible` symbol
exists; treat as unverified.)

#### Constraints (read before touching anything)
- **Scoring semantics = human-amendment-only** (MEASUREMENT.md trust boundary names eval tower + scoring).
  Cluster E is now sequenced through EV-CONF: agent work may prepare the logprob plumbing and an
  operator-signed interim neutralization of the degenerate ECE input. EV-11b closed-bin ECE was
  operator-decided and implemented on 2026-07-20; the remaining operator amendment is the EV-CONF
  real-confidence / scoring-weight decision.
- **Shared tree / live parallel work:** at audit time, `scripts/autopilot/eval_tower.py` and
  `orchestration/contention_matrix.yaml` had parallel-session edits. The checked Phase 0-3 items
  below have since landed in the owning repos; remaining open items still need normal file ownership
  checks before editing.
- **Location note:** the runner + `eval_tower.py` live in **epyc-orchestrator** (not research). A stale
  duplicate exists at `epyc-orchestrator.wt-local-frontdoor/` — reconcile so edits don't diverge.

---

#### Cluster A — Contention-matrix staleness (the systemic root) · agent-fixable (recert needs a bench)
| # | Sev | Finding (file:line) | Fix |
|---|---|---|---|
| A1 | ROOT | Matrix stale because the **vision rebind** moved the topology hash (`contention.py:806-826`; commit `139ba643`) — not the kernel. | Frame prevention around *measured-NUMA-role changes* (§H), not kernel promotion. |
| **A2** | **HIGH ✓prod** | Stale matrix **silently degrades live cross-role concurrency** — `contention_gate.matrix_health()` → `matrix_status()`; fail-closed `QUEUE`/`DEGRADED_ALLOW` (`contention_gate.py:131-139,244-252`); flags live. Every bg cross-role decode serialized since 2026-07-17, visible only in a counter. | Treat matrix recert as a **go-live blocker**; surface degraded state loudly, not just a metric. |
| A3 | HIGH | Vision matrix **data is semantically invalid**, not just hash-stale — pairs/n_way/instance_pairs (`contention_matrix.yaml:75-83,165-200,270-298`) describe the old 5-instance shape. A hash-only "bump to 8c8c" would certify **wrong geometry**. | **Re-MEASURE** vision (operator/quiet-window bench), never rehash. Forbid hash-only refresh. |
| A4 | HIGH | **No CI/pre-commit guard** binds the committed matrix hash to live `NUMA_CONFIG`; `test_real_matrix_against_live_numa_config` (`tests/unit/test_scheduling_contention.py:422-429`) **deliberately skips** the hash match; `scripts/validate/check_contention_matrix_fresh.py` is wired into nothing. | Un-skip the test to assert `matrix.topology_hash == topology_fingerprint_for_matrix(NUMA_CONFIG)`; wire the checker into pre-commit + stack-start (§H). |
| A5 | HIGH | The v7 EvalTower unblock certs are **uncommitted** (`M contention_matrix.yaml`), **role-narrow** (frontdoor+worker only), and **expire ~2026-08-19** (`eval_tower.py:630`) → a `git checkout` drops back to concurrency=1; a deferred re-break is built in. | Commit the certs (after A3 re-measure); lint that live topology is covered by a fresh hash or fresh cert; alert before expiry. |
| A6 | MED | Age-staleness keys on **file mtime** not the YAML `measured_at` (`contention.py:333-338`) → a cert append or `touch`/checkout resets the 30-day clock, masking an old measurement. | Compute age from `measured_at`. |
| A7 | MED | The **seeder** reads the matrix **unguarded** (`seeding_eval.py:141-147`) for background wave-pack admission, placement-blind → stale "allow" over-admits. | Gate wave-pack on `matrix_status==OK`/fresh cert; fail closed for bg when stale. |

#### Cluster B — Runner robustness (`eval_batch_serving_evaltower_window.py` / `eval_tower.py`) · agent-fixable
| # | Sev | Finding (file:line) | Fix |
|---|---|---|---|
| B1 | HIGH | **Killed run leaves the stack dirty** — no `try/finally`, no signal handler, `run_eval_arm` catches `Exception` not `BaseException` (`:217`); rollback (`:393`) is skipped on SIGINT/kill → API stuck `eval_batch_serving=1` + warm `:18070`, no `summary.json`, poisons the next `--apply`. | Wrap activation→arms→rollback in `try/finally`; SIGINT/SIGTERM handlers → same rollback; write partial `summary.json{status:interrupted}`. |
| B2 | HIGH | `--min-eval-concurrency` guard is **opt-in (argparse default 1)** (`:803-808`) → default `/loop` invocation silently serializes; `_eval_concurrency` (`eval_tower.py:747-763`) fails closed to `1` on stale/exception/fleet-down with **no distinguishing reason**. | Require explicit `--min-eval-concurrency` OR `--allow-serial` for any `--apply`; have `_eval_concurrency` return a **structured reason**. |
| B3 | HIGH | **Degenerate/empty eval → `decision_grade=True, rc=0`** — `eval_t1` *returns* an `n_questions=0` result (`eval_tower.py:2454-2457`); `decision_grade` (`:402-412`) never checks `n_questions>0`. Feeds the rlvr scoring (Cluster E). | Gate `decision_grade` on `n_questions>=expected` AND `n_scored>0`/`reliability>0`; degenerate → blocker `rc=75` (pair speed with a garbage check). |
| B5 | MED | Fanout certified against **wrong role** — `AUTOPILOT_EVAL_BOTTLENECK_ROLE=frontdoor` (`:754`) but calibration forces traffic onto `worker_general` (safe-N=1) → over-subscription. | Resolve concurrency against the **forced role(s)** actually receiving traffic; take min across roles. |
| B4/B6/B7/B8/B9 | MED | B4 TOCTOU guard-time vs eval-time concurrency, no reconcile (`eval_tower.py:1805`). B6 tier path skips the live-stack contract check (verifier-only, `:581`). B7 **unbounded wall time** — serial branch has no no-progress timeout (`:1817-1841`) → *why it had to be killed*. B8 `e2_eval_driver_ab.py:504-527` **always exits 0** even on `blocked`/`incomplete`. B9 no idempotency preflight for a dirty frontdoor; `:18070` shared with E2 (`e2…:473`). | Reconcile actual vs min concurrency; run the contract gate in `build_report`; add an overall wall budget + serial no-progress timeout; non-zero exit on blocked/incomplete; detect/reclaim a stale frontdoor. |
| B10-12 | LOW | Misleading blocker text (always blames the matrix); guard is floor-only (env override beats the live-safe cap → over-subscribe); test gaps (no interrupt/rollback, no default-1, tests lock in B3). | Surface real reason; validate against live-safe cap; add the missing tests. |

#### Cluster C — Preflight / gating · agent-fixable
| # | Sev | Finding (file:line) | Fix |
|---|---|---|---|
| C1 | HIGH | **The real killer is caught by no gate** — matrix freshness is only checked by `preflight_gate.check_contention_matrix_fresh` **and only on reload** (`LOOP_PROTOCOL.md:16`); EV-4 ran on the resident stack (no reload) → skipped; the entry even declares `contention_matrix: not_required` while being a fanout entry (`manifest.yaml:1435`). | Make matrix-freshness + topology-cert a **first-class precondition for every `*_eval_fanout` entry regardless of reload**; forbid `contention_matrix: not_required` on fanout entries at compile time. |
| C2 | HIGH | **health_check.sh false-positive** — 500 G session-init threshold (`:53`) mis-applied to a batch run needing a few MB, + a `/tmp/claude` mountpoint check (`:66`), both collapse to `exit 1` (`:168`) → `preflight_gate` `health_ok=False` → **every attestation fails** → override-fatigue. (Correctly checks `/mnt/raid0`, not a wrong mount. Doc-drift: `LOOP_PROTOCOL.md:17` wrongly blames a "security-audit step".) | Split batch vs session-init thresholds (`--profile`); make `/tmp/claude` advisory in batch context. |
| C3/C4/C5 | MED | C3 no advisory-vs-blocking **exit-code separation** → mask-everything overrides. C4 `host_health.py --remediate` uses **unsafe bare `drop_caches`** (`:415`), not `flush_cache_with_pause` (`:602`) → single-NUMA-node page pinning, depressed baseline (LOOP_PROTOCOL:14 prescribes the unsafe one). C5 `autopilot_precondition_gate.py` + the "mandatory dry-run" `run_batch_entry.py` are **built-but-unwired / nonexistent**. | Exit codes 0/1/2; point `--remediate` at the safe flush; wire the C2 gate into pick-next or delete the dead reference. |
| C6-C9 | LOW | C6 quiet-window **TOCTOU** (no lease). C7 throttle gate keyed on the efficiency *floor* → boost-clock loss invisible. C8 live-affinity **asserted not verified** on no-reload. C9 (**unconfirmed**) preflight hashes `sha256(registry yaml)` 64-char vs the runner's 16-char live-topology hash — two schemes, so a "matching" pin gives false assurance. | Short batch-loop lease; document/relax; verify affinity on no-reload; reconcile the two hash schemes (ties to D4). |

#### Cluster D — Entries + ledger integration · agent-fixable
| # | Sev | Finding (entry / file:line) | Fix |
|---|---|---|---|
| D1 | **CRITICAL** | **`INFRA_BLOCKED` is a permanent wedge** — `pending()` only re-picks `READY` (`batch_ledger.py:77,291`); no `INFRA_BLOCKED→READY` transition exists; `retry_policy` is declarative-only; and 3 modules disagree (`batch_status_report.py:63` lists it "eligible" while `pending()` never returns it). Same for stale `RUNNING` after a crash. | Make `pending()` re-eligible `INFRA_BLOCKED`/stale-`RUNNING` under `retry_policy`, or add an explicit requeue that appends a `READY` row; unify the 3 eligibility sets. |
| D2 | HIGH | **EV-11 `also_flips` targets the wrong item** — `#RE-3` (review-finding suite, `backlog-roi-audit…:17`) instead of `#RE-1` (the math rebaseline, `:15`). A clean pass **falsely completes RE-3** and leaves RE-1 open. | `#RE-3` → `#RE-1`. |
| D3 | HIGH | **EV-4 has no checkbox anchor** — the handoff has only prose; `flip_checkbox` will raise, but the compiler's **loose substring resolver** (`compile_inference_batch.py:213`) matched `"EV-4"` in `**Status**` prose and recorded `resolved:True` (false assurance). Same defect resolves EV-11c to prose L411 not the real L412. | Add a real `- [ ] **EV-4` checkbox (or repoint `provenance.checkbox`); make the compiler validate with the **strict flip anchor**, not a substring. |
| D4 | HIGH | **EV-4 topology pin is wrong format AND value** — `4320d9b2…` (64-char) vs live `8c8cfcbb13d2611d` (16-char); every other entry uses the 16-char v6 `df373c79…`; schema types it as a bare string with no pattern (`inference_batch.schema.json:173`). Propagated from the `COORD-v7-promotion` row. | Repin to the certified v7 **16-char** hash; add a schema `pattern` so format drift fails compile. |
| D5 | HIGH | **v7 reconciliation incomplete** — only EV-4 was updated; **EV-5/7/8/10a/11/RE-4/H5-RM3 still declare v6 kernel + v6 topology** → they will `INFRA_BLOCK` identically; EV-5/EV-7 `depends_on EV-4`(v7) while declaring v6 (inconsistent across the edge). | Sweep all still-runnable EV entries to v7 era + v7 hash and recompile (the same reconciliation the P4 note demanded, which missed P2). |
| D6-D10 | MED/LOW | D6 `entry_verdict.decide()` can't distinguish a degenerate run from a pass — the gate `rule` text (metric-count / ECE-nondegeneracy) is unenforced (`entry_verdict.py:375-377`). D7 silent `entry_hash` drift after the post-run `--min-eval-concurrency` edit. D8 EV-11b gate is a soft `operator_gate`, not a structural `depends_on` (`pending()` ignores op-gates). D9 the EV-4 infra-block was **never written to `op-bundle.md`** — the recert ask is stranded in the ledger. D10 ledger append has no `flock`; large lines risk non-atomic writes. | Bind the concrete gate rule to a verifier signal before `pass`; warn on entry_hash drift; append the op-bundle row on infra-block; add advisory locking. |

#### Cluster E — Scoring semantics · **EV-CONF sequenced; final scoring decision operator-only**
Credit: the EV-11 confidence-proxy insight came from the parallel research agent; verified + extended here.
- **E1 — the confidence proxy is a stub wired into live scoring.** `eval_tower.py` sets `confidence = float(correct)`, overridden only for `code_execution`/`rubric`; math suites are therefore **tautological** → ECE is **0.0 by construction**. Empirically confirmed: **1182/1182 journaled ECE values are exactly 0.0** (both `autopilot_journal*.jsonl` shards). The designed source — **logprob passthrough from `completion_probabilities`** — is stubbed (`:1697` comment; eval-tower-verification.md:38).
- **E2 — it is NOT an inert null instrument (corrects the "blast radius overstated" framing).** `safety_gate.py` has no `ece`, but `rlvr_tiers.py` uses it as a **`required_metric` for tiers 2–3** (`:66,72`) *and* a **score component**: `_calibration_component = clamp01(1.0 − ece)` (`:207`) feeds `0.65·acc + 0.20·rel + 0.10·calibration + 0.05·disc` (`:130`) and `… + 0.15·calibration` (`:151`). With ECE pinned to 0.0, **calibration is a constant 1.0 — a phantom max-signal worth 10–15 % of every RLVR tier score** that gates autopilot promotion.
- **E3 — the recommendation.** The EV-11b "open vs closed top bin" question is **downstream of and moot until** confidence is real. Flipping the binning alone ships a still-degenerate metric and burns an era-label. **Correctly-posed order:** (1) under EV-CONF, land logprob passthrough (`completion_probabilities → confidence`) and, with operator sign-off if scoring weights are touched, neutralize the degenerate ECE/AUC input as observation-only until confidence is real; (2) *then* the operator settles the binning against the `:2068` tripwire's measured 0.15–0.40 claim (which itself only bites where confidence decouples from correctness — code_execution/rubric — none of which appear in the 1182 math records).

#### §H — Change-hardening (the operator's ask, retargeted)
The prevention is **not** kernel-promotion-specific — it's **any change to a measured NUMA role's shape**:
- **H1 — bind the matrix to the live topology, loudly.** (a) Un-skip `test_real_matrix_against_live_numa_config` so `matrix.topology_hash == topology_fingerprint_for_matrix(NUMA_CONFIG)` is asserted in CI; (b) wire `check_contention_matrix_fresh.py` into pre-commit **and** into stack-start `preflight_gate.attest` as a **hard** gate (not `observation_only`); (c) recert = **re-measure** changed roles, never a hash bump (A3).
- **H2 — promotion/change-routine step.** In `v7-promotion.md` (and any future `-vN`) add a **"recertify topology-dependent artifacts"** gate before promotion is declared done: enumerate + refresh (i) the contention matrix, (ii) placement caps, (iii) every batch entry's `required_topology_hash` pin. A kernel promotion is one *caller* of H1; the 2026-07-17 vision rebind is proof the trigger class is broader than kernels.

#### Executable fix checklist (priority order)
> **Ownership (operator, 2026-07-20):** the **inference-batch-loop session (parallel codex agent) owns all loop/inference/runner files** — `coordination/inference-batch/*`, the loop tooling (`batch_ledger.py`, `compile_inference_batch.py`, `entry_verdict.py`), `eval_tower.py`, the runner, and `contention_matrix.yaml` — and executes **Phases 0–3 + the A3/A5 bench**. The **audit author owns only the non-loop epyc-root mechanisms**: the health_check `--profile` (✅ landed) and the CI matrix-hash guard (H1). Tags below — **[loop]** parallel agent · **[loop·op]** parallel agent + operator (bench / MEASUREMENT) · **[mech]** non-loop mechanism (audit author). Flip a box only when the fix lands *and* its Verify passes.

##### Phase 0 — Unblock the loop
- [x] **[operator] A3/A5 — re-measure `vision_escalation` + regenerate the v7 matrix, then commit it.** ✅ 2026-07-20 — `scripts/server/contention_matrix.py run` re-measured 15 live v7 production-role pairs on topology `8c8cfcbb13d2611d`; canonical `contention_matrix.yaml` now validates fresh with 15 pairs / 6 same-role entries / 0 unknown pairs. The live recert artifact is `epyc-orchestrator/data/contention_matrix/v7-live-recert-20260720T180916Z/`.
- [x] **[agent] D1 — break the `INFRA_BLOCKED` wedge.** ✅ 2026-07-20 — `batch_ledger.pending()` and `batch_status_report.py` now share retry-policy pickability for `INFRA_BLOCKED` / stale `RUNNING`; post-recert verification shows latest EV-4 row remains `INFRA_BLOCKED` but EV-4 is eligible again via policy, not via a fake checkpoint.
- [x] **[agent] D4 — repin EV-4 `required_topology_hash`** to the certified v7 **16-char** hash + add a `pattern` to `inference_batch.schema.json:173`. ✅ 2026-07-20 — EV-4 pins `8c8cfcbb13d2611d`; schema rejects non-16-char hashes; manifest compile passes.
- [x] **[agent] D5 — sweep EV-5/7/8/10a/11/RE-4/H5-RM3 to v7 era + v7 pin** (`entries/20-eval-tower.yaml`); recompile. ✅ 2026-07-20 — the named EV/P2 rows are era-consistent on `production-consolidated-v7` + `8c8cfcbb13d2611d`; fanout rows require the v7 recert matrix.

##### Phase 1 — Entry / ledger correctness [agent]
- [x] **D2 — `also_flips` `#RE-3` → `#RE-1`** on EV-11 (`20-eval-tower.yaml:619-620`). ✅ 2026-07-20 — `sources.lock.json` resolves EV-11's `also_flips` to `backlog-roi-audit-2026-07-14.md#RE-1`.
- [x] **D3 — add a real `- [ ] **EV-4` checkbox** to `eval-tower-verification.md` (or repoint `provenance.checkbox`) AND make `resolve_checkbox_refs()` (`compile_inference_batch.py:213`) use the **strict flip anchor**, not substring. ✅ 2026-07-20 — EV-4 and EV-11c each resolve to exactly one unchecked checkbox anchor in `sources.lock.json`.
- [x] **D9 — append the op-bundle row** for the EV-4 matrix-recert ask (`op-bundle.md`) per `LOOP_PROTOCOL.md:33`. ✅ 2026-07-20 — `EV-4-v7-contention-matrix-recert` is present in the operator bundle.
- [x] **D6/D7/D8 (med)** — bind the concrete gate `rule` (metric-count / ECE-nondegeneracy) to a verifier signal before `entry_verdict.decide()` emits `pass`; warn on `entry_hash` drift at pick-next; document EV-11b as a soft (non-structural) op-gate. ✅ 2026-07-20 — `entry_verdict.decide()` now refuses EV-4-style PASS unless metric completeness and non-degenerate confidence/ECE signals are supplied, downgrading binary `float(correct)` proxy evidence to the marginal branch when present; `batch_status_report.py` emits `entry_hash_drift` warnings for structurally eligible entries whose latest ledger row was recorded against a different manifest hash; `op-bundle.md` marks the exact `EV-11b-ece-binning-decision-recorded` gate satisfied while noting it remains a soft operator gate, not a structural dependency. Verify: `scripts/coordination/tests/test_entry_verdict.py`, `test_batch_status_report.py`, `test_batch_ledger.py` (55 passed); full coordination suite 117 passed; manifest validate 52/52.
- [x] **D6a — the D6 confidence gate was unsatisfiable by our own stack.** ✅ 2026-08-19 — `_confidence_nondegeneracy` matched `confidence_source` by **equality** against `{logprob, logprobs, probabilities, completion_probabilities}`, but the eval tower's only real value is `completion_probabilities_geomean` ([`eval-tower-verification.md`](eval-tower-program.md) L149). It matched neither that set nor the degenerate markers, so the sole genuinely non-degenerate confidence source in the stack fell through to `None, "no signal supplied"` — the gate written to accept real logprob confidence could only ever reject it, while correctly catching the `float(correct)` phantom. Now substring-matched over `logprob`/`logit`/`probabilit*`, with degenerate markers (`proxy`/`float(correct)`/`binary`) checked **first** so `binary_probabilities` still fails closed, and `confidence_is_real` — already stamped by EvalTower `_aggregate` — accepted as an explicit non-degeneracy signal. Verify: 4 new tests in `scripts/coordination/tests/test_entry_verdict.py`, each mutation-tested (revert the fix → 3 fail; swap the two branches → the ordering test fails); `scripts/coordination/tests/` + `tests/vidya/` 709 passed, 38 skipped. **Ownership note:** `entry_verdict.py` is the inference-batch-loop session's file per the 2026-07-20 ownership ruling below; this fix was operator-directed, landed in `07073fe8`, and is flagged here rather than claimed.

##### Phase 2 — Preflight / gating [agent]
- [x] **C1 — make matrix-freshness + topology-cert a precondition for every `*_eval_fanout` entry regardless of reload;** forbid `contention_matrix: not_required` on fanout entries at compile time. ✅ 2026-07-20 — compile lint rejects `eval_fanout` + `contention_matrix: not_required`; `run_batch_entry.py` blocks stale fanout matrices in preflight.
- [x] **[mech] C2/C3 — health_check.sh `--profile batch`** — ✅ landed `940522a8` (2026-07-20): batch profile relaxes the raid floor 500 G→20 G + demotes `/tmp/claude` to advisory; session-init unchanged; bad profile → exit 64; empty-df guarded. Verified batch→exit 0, session-init→exit 1. ✅ 2026-07-20 follow-up: `preflight_gate` now calls the root batch profile, keeps contention-matrix freshness hard-gated, and resolves v7 quarter live role ports from `NUMA_CONFIG`; role-scoped EV-4 preflight passes for live frontdoor/worker quarters.
- [x] **C4 — point `host_health.py --remediate` at `flush_cache_with_pause()`** (`:602`), not bare `drop_caches`; fix `LOOP_PROTOCOL.md:14`. ✅ 2026-07-20 — the CLI remediation path now uses pause + `drop_caches` + NUMA-interleave rewarm; `LOOP_PROTOCOL.md` names `health_check.sh --profile batch` and the safe remediation sequence. Verify: `tests/unit/test_host_health_pause_around_flush.py` (15 passed).
- [x] **C5 — wire `autopilot_precondition_gate` into pick-next** (or delete the dead `run_batch_entry.py` reference). ✅ 2026-07-20 — the mandatory batch-entry bridge (`epyc-inference-research/scripts/benchmark/run_batch_entry.py`) now imports the root-owned pure gate and blocks when live `autopilot.running` disagrees with `preconditions.autopilot`; entries with `autopilot:any` avoid live probing. Verify: `scripts/benchmark/tests/test_run_batch_entry.py` (32 passed) + root `test_autopilot_precondition_gate.py`.

##### Phase 3 — Runner robustness [agent·coord — touches `eval_tower.py`]
- [x] **B1 — try/finally + SIGINT/SIGTERM rollback** so a killed run always rolls back `eval_batch_serving=1` + `:18070` and writes `summary.json{status:interrupted}`. ✅ 2026-07-20 — runner activation is wrapped in rollback-on-interrupt, and regression coverage verifies interrupted runs write non-decision-grade summaries after rollback.
- [x] **B3 — gate `decision_grade` on `n_questions>=expected` + `n_scored>=expected`/`reliability>0`;** degenerate → blocker `rc=75`. ✅ 2026-07-20 — empty/all-error and partially scored verifier/current-arm paths return `decision_grade=False` with degenerate status.
- [x] **B2 — require explicit `--min-eval-concurrency` OR `--allow-serial` for any `--apply`;** `_eval_concurrency` returns a structured reason. ✅ 2026-07-20 — default `--apply` now refuses without an explicit concurrency guard; EV-4 command includes `--min-eval-concurrency 3`.
- [x] **B5/B7 (med)** — resolve concurrency against the forced role(s) actually receiving traffic; add an overall wall budget + serial no-progress timeout. ✅ 2026-07-20 — EvalTower now computes fanout from the actual per-question `force_role` set and takes the minimum safe live cap across those roles; verifier-mode preflight passes its `--roles` set into the same resolver, so `--min-eval-concurrency` validates the roles EV-4 will actually hit. Serial fallback now has a finite batch wall budget and fails remaining questions closed with `eval_wall_budget_timeout`. Verify: `tests/unit/test_eval_tower_concurrency_metrics.py`, `test_eval_batch_serving_evaltower_window.py`, and `test_eval_verifier_mode.py` (81 combined passed with host-health coverage).
- [x] **B13 — EV-4 textual multiple-choice scorer blocker.** ✅ 2026-07-20 — `debug_scorer.py` now accepts configured textual multiple-choice labels such as `expected="incorrect"` with `choices=["correct","incorrect"]`, ranks overlapping textual matches by match end then choice length, and accepts parenthesized expected letters like `(B)` while preserving the legacy A-H letter contract for entries without choices. **Important:** this is a scoring-semantics change, so EV-4 is now ledgered `BLOCKED_PRECONDITION` until the B7 operator-reviewed scorer package signs it off; the interrupted `20260720T191550Z` run is diagnostic-only. Verify: `tests/unit/test_debug_scorer_multiple_choice.py` + `test_debug_scorer_code_execution.py` pass.
- [x] **B14 — `run_batch_entry.py` interrupt result preservation.** ✅ 2026-07-20 — the batch bridge now runs children in their own process group, terminates that group on timeout/SIGINT, and converts `KeyboardInterrupt` during execute into a structured `exit_code=130` result instead of losing the result JSONL path. Verify: `epyc-inference-research/scripts/benchmark/tests/test_run_batch_entry.py` stdlib runner (33 passed).
- [x] **B15 — B1 denominator leg + EV-11b closed-bin ECE.** ✅ 2026-07-20 — EvalTower `_aggregate` excludes errored rows from the quality denominator while preserving total/error observability in `details`, runner arms require full `n_scored` before decision-grade, and `_aggregate` now uses closed-top-bin `stat_tests.expected_calibration_error` with `ece_instrument_era=ev11b_closed_bin_2026_07_20`. Verify: `test_eval_tower_concurrency_metrics.py`, `test_eval_tower_ev11_stats.py`, `test_eval_batch_serving_evaltower_window.py`, and `test_eval_verifier_mode.py` (80 passed).

##### Phase 4 — Prevention [agent]
- [x] **H1 — bind the matrix to live topology in CI + stack-start.** ✅ 2026-07-20 — `test_real_matrix_against_live_numa_config` now asserts the committed matrix hash equals `topology_fingerprint_for_matrix(NUMA_CONFIG)`; `preflight_gate.attest` keeps `check_contention_matrix_fresh.py` as a hard gate; the local pre-commit hook also runs the freshness check. Verify: `tests/unit/test_scheduling_contention.py` and live `check_contention_matrix_fresh.py` pass.
- [x] **H2 — add a "recertify topology-dependent artifacts" step to `v7-promotion.md`** (+ future `-vN`): matrix + placement caps + entry topology pins refreshed before promotion is declared done. ✅ 2026-07-20 — `v7-promotion.md` now records the recertification hardening as a checked promotion-routine item.
- [ ] **H2.v8 — remeasure the contention matrix under frozen v8 after E8 quality collection** — live dashboard topology and region-lock payloads already include `architect_general`; the stored/live measured-role topology hash is the same `8c8cfcbb13d2611d`, so existing batch pins require no rewrite. The 2026-07-27 six-role affinity preflight passed for all 18 live instances and wrote `epyc-orchestrator/data/contention_matrix/affinity_preflight_1785131940.json`. The canonical matrix still carries v7-era measurements from 2026-07-23; run the operator-authorized six-role `contention_matrix.py run`, then both validators, after the E8 quality baseline is sealed so the recertification traffic cannot contaminate it. Era correction: production is v10 (frozen 2026-09-22); run the six-role contention_matrix.py under the v10 lineup, not v8, and supersede the v7-era rows by era label.

##### Scoring Trust Boundary
- [ ] **Cluster E — scoring → tracked as EV-CONF in [eval-tower-verification.md](eval-tower-program.md).** EV-11b closed-bin binning is implemented; **[agent]** logprob-passthrough plumbing (`completion_probabilities → confidence`) landed ✅ 2026-07-21 with source stamping; **[agent·op]** interim neutralization (hold ECE/AUC observation-only so the constant-0.0 stops inflating the rlvr tier score, with operator sign-off before merge if scoring weights are touched) remains open; **[operator]** owns the final real-confidence / gating decision.

#### Provenance
5 audits, 2026-07-20: runner + contention-matrix + preflight + entries/ledger (4 read-only subagents) +
scoring (parallel research agent, verified here). Load-bearing claims spot-verified against source;
F2a (safety_gate baseline block) and C9 (hash-namespace) flagged **unconfirmed**. Later checked items in the executable checklist record the implemented follow-up.

#### Research Intake Update — 2026-08-15 (failed-trial convention; intake-1141)

The convention worth adopting, from a Stage-2b dive of the `scaleapi/vero` repository: an
**agent/seed-caused** failure scores 0 *and the baseline pays the same tax*; a **platform-caused**
failure is **dropped** (a retry cannot score a trial that never ran, and zero-filling infra bakes
outage luck into the pin); an **unclassified exception type is a hard error**, not a default bucket.

**Cite this as design guidance, never as validated practice.** The source that documents the rule does
not implement it: `runs/recompute.py`, named as the rule's home, has **never existed** in that
repository's history; the script that produced their published pins drops unrewarded trials rather
than zero-filling them; and their shipped error taxonomy has zero `raise` statements. Their *live
engine* does implement the first two halves. Both facts must travel together — this is a worked
external example of "the convention is documented" and "the numbers obey the convention" being two
different claims.

**Verified against our own code**, where the gap is narrower and more specific than the source implies.
`src/autopilot_core/measurement_guards.py` does have **zero `raise` statements**, but it is not naively
fail-open — it exists *because* of the documented 2026-08-03 incident (a T1 calibration reported 0%
correct purely because the orchestrator API was down), explicitly naming
`feedback_fail_open_defaults_conceal_their_own_corruption`. Three specific holes remain:

- [x] **ETR-1 — We DROP BOTH failure classes; decide whether agent-caused should score 0.**
      ✅ 2026-09-23 — operator RULED: agent-caused (`task_failed`) rows score 0 inside the denominator; infra/scoring failures stay excluded. Code: epyc-orchestrator `44d0d4a0` + `927380a5` (aggregate carries `quality_denominator_policy`, `task_failed_count`; EV-11 per-role accuracy uses the same helper). Era row E17 + MEASUREMENT.md §5 clause ship in `scripts/operator/ratify_trust_boundary_and_etr1_20260923.sh` (operator runs it).
      `eval_tower.py:5129` filters the quality denominator with `not r.error`, so an agent/config-caused
      failure and a platform-caused failure are treated **identically** — both leave the denominator.
      The distinction survives only into telemetry and `reliability`. The consequence: **a config that
      crashes more gets a smaller denominator and is not penalized for it.** The external convention
      says the agent-caused half should score 0 (with the baseline paying the same tax) while only the
      platform-caused half is dropped. Decide deliberately; do not inherit current behaviour by default.
- [x] **ETR-2 — `quality_measured` is computed and never read (latent defect).** ✅ 2026-09-14 — the flag is now READ, and the producers made truthful. `SafetyGate.check()` fails closed on `quality_measured=False` with its own `quality_not_measured` category (a placeholder is no longer charged as a `quality_floor`/`regression` violation, and does not arm the auto-rollback), `update_baseline()` refuses the write with `ineligible_reason="quality_not_measured"`, the eleven `EvalResult(quality=0)` placeholders in `eval_tower.py` plus the consult-gate probe in `actions.py` now declare `quality_measured=False` with a named reason, and `_eval_details_from_result()` carries the distinction onto every journal row. A MEASURED 0.0 is still gated as a measurement. `epyc-orchestrator` `250a5d13`; 16 tests in `tests/unit/test_safety_gate_quality_measured.py` + `tests/unit/test_quality_measured_producers.py` (incl. an AST guard so a new placeholder cannot reintroduce the defect).
- [x] **ETR-3 — Close the narrow silent-scoring hole.** ✅ 2026-09-14 — closed with the structural fact already on the wire: a non-blank answer whose response reports ZERO generated tokens did not come out of a decode, so `infra_failure_reason` now returns the new reason `answer_without_generation` (the `empty_response` sibling whose blank-answer requirement let this shape through). Opt-in via `require_generation_evidence`, set on the MEASUREMENT paths only (`eval_tower`, `seeding_scoring._classify_error`, `seeding_eval`) and deliberately OFF for the live-serving reward path, so a genuine wrong answer keeps earning its negative reward; mock-mode replies and legacy rows with no token counter are unchanged. The residue is named: a non-blank answer WITH a real token count is a real generation, so garbage there stays scored WRONG. `epyc-orchestrator` `250a5d13`; 10 tests in `tests/unit/test_answer_without_generation.py`.
- [x] **ETR-4 — guard the unguarded `r.rubric_threshold_source` read** ✅ 2026-09-17 — the `getattr` guard had already landed in `epyc-orchestrator` `4055dba0` (NIB2-69, 2026-09-15) without a test; `1097a392` adds `tests/unit/test_etr4_rubric_threshold_source_guard.py` (4 cases: a duck-typed row without the attribute compacts and omits the key, a row with it still serializes it, empty/None is omitted, and an AST check that refuses any bare `r.rubric_threshold_source` read — it flags the two in the pre-fix source). Original text: in `_compact_question_result`, which
      breaks the documented duck-typed-row contract and is a real defect for any legacy or foreign row;
      one-line `getattr` (`scripts/autopilot/eval_tower.py:1413`) (found 2026-09-14, noninf sweep).
- [x] **ETR-5 — expose ETR-2's state as the first-class `SafetyVerdict.reliability_blocked` field** ✅ 2026-09-17 — `epyc-orchestrator` `0399c3fe`. This was implemented as a SIBLING field, not by overloading `reliability_blocked`. `SafetyVerdict.quality_unmeasured: bool` carries ETR-2's state. A `retry_not_revert` property folds it with REL-1's `reliability_blocked` for consumers that only need "retry, not revert", and the consecutive-failure guard now reads that property. The two causes stay distinguishable, because the ETR-2 test deliberately pins "NOT the REL-1 path". No `src/`/`scripts/` consumer read `reliability_blocked`, so nothing else changes. Asserts were added to `tests/unit/test_safety_gate_quality_measured.py`. Original text: instead of
      only as the `quality_not_measured` category string, so a downstream consumer can branch on it
      (`scripts/autopilot/safety_gate.py`) (found 2026-09-14, noninf sweep).
- [x] **ETR-6 — make the two "no decode" cases serialize identically** ✅ 2026-09-17 — `epyc-orchestrator` `0399c3fe`. `_execute_mock` now sets `tokens_generated=0` explicitly. Because of the model default, both shapes already dumped as 0 in a plain `model_dump()`; they differed only under `exclude_unset` or a field-presence check (ETR-3's `"tokens_generated" in resp`). `tests/unit/test_etr6_no_decode_wire_shape.py` has 2 cases, and both fail on the old code. Original text: mock-mode `ChatResponse` omits
      `tokens_generated` entirely while `vision_stage.py:194` sets it to `0`, an inconsistent wire contract for
      any future structural check (`src/api/routes/chat_pipeline/stages.py:115`) (found 2026-09-14, noninf
      sweep).
- [x] **ETR-7 — delete the unused `INBAND_ERROR_PREFIX` imports** ✅ 2026-09-17 — `epyc-orchestrator` `0399c3fe`. Deleted in both files. No caller, test or `__all__` entry referenced the private `_INBAND_ERROR_PREFIX` alias, and `ruff --select F401` is now clean on both. Original text: delete the unused `INBAND_ERROR_PREFIX` imports (pre-existing `ruff F401`), or state the
      re-export intent, one line in each of `scripts/autopilot/eval_tower.py:1142` and
      `scripts/benchmark/seeding_scoring.py:133` (found 2026-09-14, noninf sweep).

## Track: fable5-window2-findings-01-optimizer-integrity
<!-- gate: none -->

> Folded from `handoffs/active/fable5-window2-findings-01-optimizer-integrity.md` @ `c4b6d1388716` on 2026-11-02 (BRF-T1-F2, route 1a, operator D1/D5; retired row EVL-19 → EVL-14). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Window-2 findings 01 — Self-optimizer integrity: the guarantee, not the mechanism (§4A)

**Verdict in one line**: the evidence plane is a *hybrid* — promotion integrity is guaranteed by construction; learning-surface integrity is detection-plus-hygiene with three named, cheaply closable gaps; and the W5 no-go is a stale-era measurement whose protocol is now structurally obsolete. All facts below independently re-verified by adversarial agents against `epyc-orchestrator @ a2e5f3e` (CONFIRMED unless marked PARTIAL).

#### 1. What is actually guaranteed by construction today

The unifying model you built (and its theorem, restated from window-1 findings-01:32): *append-only facts + supersession events + all derived state recomputable from the journal + planner reads only through policy-applying views ⇒ any contamination dies with one appended event plus recompute.* Where this holds, it holds well:

- **Baseline promotion** — fail-closed conjunction: seq verdict `confirmed` on both axes (`safety_gate.py:1245-1251`), combined E = min(E_q, E_rate) ≥ 100 (`autopilot.py:190-192, 748-757`), a **forced fresh T2 deep-eval** (`autopilot.py:848-915`; W8 fresh draws exclude qids seen ≤60 days), a one-sided Hoeffding delta-CI excluding regression (`autopilot.py:785-797`), ≥3-reproduction cluster median clearing one quantum (`safety_gate.py:1318-1338`), and ledger authority behind a root-chowned operator consent file the autopilot can only read (`src/autopilot_core/authority_consent.py:1-26`). The t775-ratchet class is impossible by construction. A refuted candidate can *never* move the baseline, and refutation persists across restarts because e-state rebuilds from journal seq rows per fingerprint (`autopilot.py:1057-1073`).
- **Contaminated-evidence exclusion** — read-time, recomputed per call: strategy retrieval drops any strategy whose `evidence_trial_ids` intersect journal-derived excluded trials (`strategy_store.py:146-167, 1190-1192, 1247-1267`); planner-hint retrieval hard-fails on stores lacking this path (`actions.py:207-230, 460-469`). AP-22 STM is a pure journal projection regenerated every trial (`autopilot.py:4607-4612`) — **the operator-memory "rewind must purge STM" hole is closed**; a journal rewind now propagates automatically.
- **Eval conditions** — W7's real structural item: `EvalTower.evaluate()` ignores caller n/seed (pins n=100/500, seed=42, commit 7492cf5); eval concurrency is topology-derived, not planner-choosable (`eval_tower.py:451-468`). The optimizer cannot vary its own measurement conditions.
- **E-process math** — verified valid test-martingale: predictable capped-Kelly λ from past observations only, factor nonnegativity enforced, z bounded (`sequential_verdict.py:96-147`). Confirmation is anytime-valid under planner optional stopping (Ville). Conservative asymmetry: no rate evidence ⇒ can never confirm.

#### 2. Where the guarantee does NOT hold — the three gaps

**G1 — The refutation loop is open (the §2 question, answered: NO, refuted narratives can re-inject).**
No code consumed `seq_refuted` as a learning exclusion — grep found it only in a comment (`learning_exclusions.py:69`; BENIGN set at `:7-9` lacked it; verifier confirmed a passing trial of a refuted candidate fell through to "include normally" at `:89` and `archive.update` ran at `autopilot.py:4271`). Path: refuted candidate → gate-*passing* trial → clean journal row → `_is_distillable_entry` accepts it (`evolution_manager.py:80-95`, no seq check) → strategy store → planner hints. Push-back was *advisory only* (planner evidence renders `seq=refuted E=…`, `planner_evidence.py:296-304`; the W7 critic is told to reject below-MDE claims). **R1 status 2026-07-03**: CLOSED in orchestrator `aa20d029`. `seq_refuted` is now a non-benign learning quarantine when the broader safety verdict otherwise passed, while failed-regression verdicts keep their primary deficiency. Validation: focused sequential/classifier tests (`34 passed`), downstream AutoPilot/StrategyStore/journal tests (`77 passed`), and Ruff.

**G2 — Strategy-store writes were honor-system.** CLOSED 2026-07-04 in orchestrator `796119ec`. `StrategyStore.store()` now stamps `provenance_status`, rejects evidence IDs absent from a supplied folded journal or valid trial-id set, fails closed if journal validation is requested but unavailable, and treats explicitly empty evidence as provenance-less instead of silently falling back to `source_trial_id`. Journal-aware retrieval/distillation/compression paths filter non-operator `provenance_status=none` rows, while operator-seeded handoff hypotheses remain visible as explicit `operator_seeded` rows rather than pretending to be trial evidence.

**G3 — No multiplicity control across candidate fingerprints.** Each new fingerprint starts wealth=1.0 with its own per-axis α=0.05 (`autopilot.py:1016-1089`). The optimizer mints candidates freely; expected false *learning-surface* confirms grow linearly in fingerprints tried (baseline damage is capped separately by the E≥100 + fresh-eval promotion chain — this is why the plane is a hybrid, not broken). **R4 status 2026-07-04**: CLOSED in orchestrator `62b24aa8`. Sequential readiness now reports `fingerprints_tested`, `alpha_spent`, `expected_false_confirms`, and budget exhaustion. Live replay on the current journal reported `52` fingerprints, `alpha_spent=2.6`, `expected_false_confirms=2.6`, `budget=1.0`, and `new_fingerprint_confirmations_allowed=false`. AutoPilot now blocks first-time candidate fresh-eval confirmation when the shared alpha budget is exhausted; already-started/existing candidate continuation and the E≥100 promotion path remain separately guarded.

**G5 (accepted, document it) — Episodic memory + routing-model training sit outside the quarantine chain** (`q_scorer.py:1237`; `structural_lab.py:188`). Consistent with the era ruling (demote-to-prior wholesale). This is fine *while routing expansion stays frozen* — but it means the DAR-1 unfreeze path (R16) must add read-time exclusion to training-data assembly before any learned-routing retrain consumes post-authority rows.

#### 3. W5 `core_v2`: neither mis-specified objective nor mis-built instrument

What 33/40 actually is (verified by independent recomputation from the raw JSONLs): 300 qids × 5 same-seed repeats; 187 always-correct, 80 always-wrong, **33 flip items** (k=4 in 19 of them — one flip in five); the selector admits p̂∈[0.2,0.8], target 40, shortfall 7 (`core_v2_select.py:157-161,307-310`). The no-go was an operator decision, not a code gate (progress 2026-06-15:1044-1055).

Why the 33 is not a fact about item difficulty:
1. **Infra flips**: 88 error events across the 5 repeats (16/15/20/24/13 of 300; worker-path 504s in every repeat), errors score as incorrect (`eval_tower.py:1002-1004`), and every error necessarily lands in a non-always-correct item. ~13 of the 33 band items have failure sides that are timeout-shaped (three failures within 150 ms of 90.6 s on one item; 180 s and 151 s triples) or fast-fail (<5 s). The band was partly manufactured by infrastructure.
2. **Era invalidation**: the calibration ran under nondeterministic production sampling; the determinism fix (declared temps + fixed sampling seed, f4a8a3ca) landed 2026-06-26 — **eleven days after** calibration. The measured per-item p's are properties of a decommissioned regime. Per the MEASUREMENT.md era rule, the 2026-06-15 lineage should be **demoted to prior**.
3. **Estimator resolution below its own gate**: eligible items went 21→33 as repeats went 3→5; at 5 reps p̂ quantizes to k/5 and a true-p≈0.9 item enters the band ~41% of the time by chance. A sharp 40-count gate cannot be certified by this estimator at this budget.
4. **The artifact cannot adjudicate**: the compact rows persist no `error`/`error_detail`/`route`/answer fields (0 of 1500 rows); that persistence landed 2026-06-20 (c13e5ae) — after calibration.

**The reframing (the real finding)**: post-f4a8a3ca, with a fixed sampling seed, same-prompt repeats are deterministic up to concurrency/batching and infra — so the repeat-flip protocol no longer measures difficulty *even in principle*. "Difficulty" for a designed core must be defined as **P(correct | production config distribution over time/configs)** — and that is exactly what the now-live per-question ledger accrues for free (200+ trusted vectors and growing). **R2**: rebuild core_v2 item statistics from the ledger (zero inference), select the 40-item core from per-item pass rates across trusted trials, and retire the calibration-batch protocol. **R3** (the single cheapest discriminating experiment, for closure): re-run only the 33 flip items on the current stack, once at eval-concurrency 1 and once at 3, with `error_detail`+`route` persisted (~99–165 requests, 1–2 h): (i) errors reproduce → infra-manufactured band; (ii) flips vanish at conc=1 but reappear at conc=3 → the instrument constant conc=3 is the flake source (a genuine instrument-design fact worth knowing); (iii) error-free flips persist → real residual nondeterminism, widen the draw instead of repeating.

**The cost of leaving W5 parked** is not abstract: live authority runs on the legacy seed-42 core with effective discriminating n≈10–14 (findings-01-impl-plan:52). Every day of authority-on with the old core is decision-making at ~4.7pp MDE.

#### 4. W6/W7: "clear" means re-based first, then re-earned within a narrowed frame

- W6 semantics (verified): rotating shadow-only audit block (sha256-seeded per trial, core qids excluded, never in optimizer reward, `eval_tower.py:1680,1806-1828,862-892`); gaming event = core rises >1 step AND audit falls >1 step between consecutive trusted audited trials; alarm window = trailing 30 (`audit_block_report.py:336-340,:14`). "40/30" = 40 trusted *current-era* audited trials vs the 30 minimum.
- **The re-base**: on 2026-06-21 the un-fenced fold reported `gaming_alarm=true` with 12 cumulative divergences; the era fence (2026-06-28, `pareto_exclude_before_ts`=E5 cutover 2026-06-26T22:07:11Z) removed 100 of 132 audited rows, and both the windowed *and* "cumulative" diagnostics are computed only over era-eligible rows (`audit_block_report.py:151-169,181,300,315`) — the 12 divergences are structurally invisible to the current fold and were never root-caused. Within the new era the clear then accrued honestly (9→40 rows, zero divergences, live monitoring). Both statements are true; only the second is usually reported.
- **Trigger blindness**: CLOSED 2026-07-04 in orchestrator `ef70f859`. W6 now emits a separate core-inflation warning when core quality rises by a configurable number of core-question steps while audit quality remains resolution-flat; this warning is surfaced through restart readiness and the Fable5 gate.
- **Governance hole**: no production code writes `pareto_exclude_before_ts` (reads + tests only) — the fence is an operator-plane knob with no in-code governance; it demonstrably converted an active alarm into "clear" once already.
- **R5 status 2026-07-04**: CLOSED in orchestrator `ef70f859`. The audit report now preserves `era_excluded_gaming_events`, restart readiness validates the matching `instrument_eras.yaml` row/disposition contract (`adjudicated | demoted | superseded`) whenever fenced-out gaming events exist, and the aggregate Fable5 gate exposes `w6_core_inflation_warning` plus `w6_fence_governance_status`. Current journal replay shows `190` audited rows, `gaming_alarm=false`, `core_inflation_warning=false`, and `era_excluded_gaming_event_count=0`.

**Is W7 the right design or a patch to re-derive?** The *architecture* (append-only + read-time policy views + clamped eval conditions) is right and has now survived contact with production; W7's items are correct patches on that architecture. Nothing needs re-derivation. R1 refutation-as-exclusion, R4 alpha budgeting, R5 W6 fence governance, and R6 StrategyStore write-side provenance validation are now closed. The honest claim is now: *promotion and learning surfaces are both policy-gated views over an append-only journal; gaming is limited to instrument overfit, which is detected by W6 and bounded by W8 fresh draws with governed fence moves*.

#### 5. Build seeds (acceptance criteria + cheapest decisive experiment)

- **R1 refutation loop** — Accept: a synthetic refuted-fingerprint trial passes the gate, and its rows are absent from distillation input, strategy retrieval, and STM; a pre-existing refuted-derived strategy stops being retrievable with no purge. Decisive experiment: unit fixture replaying a refuted→passing sequence through `classify_learning_exclusion` + `retrieve_for_journal` (zero inference).
- **R2 ledger-derived core_v2** — Accept: a `core_v2_select --source ledger` mode emits ≥40 items with p∈[0.2,0.8] computed over ≥N trusted trials each, era-fenced; selection reproducible from the journal alone. **Status 2026-07-03**: CODE/CANDIDATE CLOSED in orchestrator `080c4fa1`. The live read-only selector emitted non-promoted `core_v2_ledger_20260703_min5` with selected `40/40`, eligible `79`, observed `923`, source rows `77`, `min_attempts=5`, unresolved `0`, `25` untrusted current-era rows excluded, and `849` pre-era rows fenced by `pareto_exclude_before_ts=1782511631.0`. Remaining decision: promote/era-handle the candidate, and optionally compare against the 2026-06-15 33 flip set.
- **Current-era rebuild 2026-07-29 (I2, zero inference):** the same selector, reading the folded ledger under the current state-era fence (`pareto_exclude_before_ts=1785004723.0`), produced only **2/40** selected/eligible items from 16 trusted rows (50 observed question outcomes; shortfall 38). The two current items (`leval/7b69f2f6f04fada0`, `needle_parameterized/bf267ac944ba8a79`) have **zero overlap** with the July-3 40-item candidate. The old candidate is therefore a historical prior, not an E8-promotable core; its former E4-era promotion block cannot be resolved by re-labelling it.
- [ ] **R2-current — accrue a current-era, trusted per-question ledger sufficient for a reproducible ≥40-item core selection.** Do not promote the July-3 candidate or use its item set as a substitute. A later selection must retain the current state-era fence, report trusted/untrusted/era-excluded row counts, and bind the selected core to an operator-owned era decision before activation.
- **R4 α-budget** — CLOSED 2026-07-04 in orchestrator `62b24aa8`. Readiness reports show `fingerprints_tested`, `alpha_spent`, `expected_false_confirms`, and `new_fingerprint_confirmations_allowed`; the live journal replay shows the channel is live (`52 × 0.05 = 2.6` expected false confirms). Budget-exhausted state now blocks *new-fingerprint* confirmations, not already-started candidate continuation or promotions, which remain E≥100 + fresh-eval guarded.

#### 6. Depth reallocation note

Per the brief's instruction ("if largely solved, say so and reallocate to 4B"): the mechanism is ~80% solved and the remaining 20% is enumerated above with small fixes — no rescue needed. Depth was accordingly reallocated to §4B (findings-02), which is where the new hardware makes architectural guidance time-critical.

#### Progress checklist

- [x] Findings deliverable produced (build-seeds R1/R2/R4/R5/R6 CLOSED) ✅

## Track: inference-batch-loop
<!-- gate: none -->

> Folded from `handoffs/active/inference-batch-loop.md` @ `c4b6d1388716` on 2026-11-02 (BRF-T1-F2, route 1a, operator D1/D5; retired row INF-24 → EVL-14). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Inference-Batch Loop — Campaign Insertion Point

**PARKED-ISLAND DECISION MENU (2026-07-23, prepared for the operator per standing directive — one-word approvals suffice):**
- **ROUTE-A1 (shape-keyed step-2 smoke; build-gated on the `_drive_admit_overlap_probes` stub)** — (a) build the smoke bridge now (CPU-session code work; validates step-2 admit on the CURRENT gate, but E5's R4 capability rows + the fabric capability-records inversion may reshape shape-keyed gating → rework risk); (b) **RECOMMENDED: park until post-E5** — build against the E5-informed design once R4 lands (the smoke then validates the design that will actually ship).
- **ROUTE-A2 (edit-transaction A/B; data-gated on a nonexistent multifile_edit corpus)** — (a) build a bespoke corpus now (medium effort, single consumer); (b) **RECOMMENDED: fold into architect-bench Phase-2 SWE-bench corpus work** (OD-1/OD-2 needs the same multifile-edit task family — one corpus effort, two consumers), sequenced post-E5; (c) drop the entry.
- **RE-4 (LongCoT-Mini calibration; protocol-gated — answer-only grammar floor-saturated 0/402 + 0/307)** — (a) **RECOMMENDED: suffix-extraction redesign** — free generation with a bounded reasoning budget, then a required terminal `solution = X` line (stop-sequence + the new `structural_exact_match` scorer `7e767df7`; no grammar during reasoning, deterministic extraction preserved; cheapest fix, CPU-session owns it, sequenced after E5 W0/W1); (b) LLM-judge extraction (judge path fixed `76c34590`, but adds judge variance to a calibration instrument — disfavored); (c) drop RE-4 and accept the runner-confidence-parity gap.

**Status (2026-07-21 ~09:30Z, takeover session):** the prior loop session ran out of tokens ~07:00Z after a clean overnight burn-down — **5 entries terminal** (K-EMB, TM-7 parity, hermes-smokes, kbrag-K11, ROUTE-A3; banners below), no stale RUNNING rows. The takeover session then **exhausted the live island** (banner below): ROUTE-A1 parked build-gated (smoke bridge is a stub), ROUTE-A2 parked data-gated (no multifile_edit corpus exists), RE-4 parked protocol-gated (floor-saturated answer-only design). **Every remaining entry is operator/build/model-download gated.** Next runnable: **EV-4** once the B7 golden-delta doc lands (ESC-6 option B GRANTED 2026-07-21; delta harness in flight) — on the rebuilt E7-era pool (scoring_verifiers now actually sampled), ratified scorer, and real-confidence plumbing. Production is `production-consolidated-v7` (`6ad45fa3ff`, binary `10098`).

**kbrag-K11 terminal execution (2026-07-21T06:05Z, `DONE_MARGINAL_OBS`):** K11 lexical-weight sweep 0.1–0.3 matched the ColBERT-only baseline exactly (recall@10 `0.5048`) — keep `lexical_weight=0`; two trailing ledger rows are intentional terminalization of an orphaned run (latest-wins correct). Sweep checkbox flipped in `internal-kb-rag.md`.

**Live island EXHAUSTED (2026-07-21 ~09:30Z):** under the operator's window grant, the takeover
session attempted both remaining preflight-clean entries and discovered both were **mislabeled
runnable** (the bridge sidecar validated command *resolution* only): **ROUTE-A1** parked
`BLOCKED_PRECONDITION` (`build_gate=step2-smoke-bridge` — `_drive_admit_overlap_probes` is a
`NotImplementedError` stub at `shapekeyed_step2_smoke.py:718`; entry command double-gate bug found
+ fixed on the way; build task filed in `shape-keyed-contention-gating.md`); **ROUTE-A2** parked
`BLOCKED_PRECONDITION` (`data_gate=multifile-edit-corpus` — harness correctly refuses suite-only
execution and no multifile_edit corpus manifest exists on disk; env-gate command bug also fixed).
Both first-attempt invalid-passes were caught by the `b216fe0f` artifact-validation hardening.
**Every remaining entry is now operator/build/model-download gated.** Next runnable: **EV-4** the
moment the B7 golden-delta doc lands (ESC-6 option B granted 2026-07-21; delta harness in flight).

**ROUTE-A3 terminal execution (2026-07-21T06:55Z, `DONE_PASS`):** J2 forward=6 / J3 reverse=4 live KV-migration probes, `n_aborted=0`, matrix_status fresh; API restored to `--workers 6`. WP-3/WP-4 flipped in `within-role-placement-state-machine.md`. This was the prior session's final ledger write.

**K-EMB terminal execution (2026-07-20T23:33Z):** `BULK-K-EMB-1` retried under the corrected exact-model and 512-character input policy and reached `DONE_PASS`. Preflight and execute both exited `0`, ports `8096`/`8097`/`8098` were closed after cleanup, and the Phase B artifact is `data/embedder_bench/granite_97m_r2_phaseB.json` in `epyc-inference-research`. Metrics on the 100-doc / 30-query fallback corpus: Granite Q8_0 recall@10 `0.9333`, recall@50 `0.9889`, nDCG@10 `0.8382`, wall `1.213s`; e5-base Q8_0 `0.8444` / `0.9611` / `0.7928`, wall `2.651s`; BGE-M3 Q8_0 `0.9000` / `0.9889` / `0.8380`, wall `7.037s`; BGE-large reference `0.8889` / `0.9500` / `0.8093`, wall `13.749s`. This flips the Granite Phase B/smoke checkboxes only; the broad P3 campaign remains open.

**RE-4 terminal blocker (2026-07-21T03:25Z; no RE-4 flip):** the optimized v7
quarter-stack RE-4 rerun with `prompt_mode=concise_solution` and
`force_solution_grammar=true` fixed marker compliance but destroyed the benchmark
signal. Frontdoor emitted `solution =` for 402/402 rows and scored 0/402;
worker_general emitted markers for 307/307 partial rows and scored 0/307. The
run was stopped after 6223s because the answer-only grammar suppresses the
reasoning/computation LongCoT-Mini is meant to measure. Latest ledger status is
`INFRA_BLOCKED`, not `DONE`; score artifacts live under
`coordination/inference-batch/bundles/RE-4/partial_*_score_20260721T013833Z.*`.

**TM-7 bridge no-op blocker fixed (2026-07-21T03:36Z; no TM-7/TM-8 flip):**
the first `BULK-langgraph-tm7-parity` execute attempt returned success in
0.038s without running live real-node parity. Root cause was two-part: the
manifest command omitted `run_task_lg_parity.py --execute`, and the research
bridge ignored `artifacts.outputs`, so it predicted `artifacts=[]` and never
failed on the missing `data/trace/tm7_realnode_parity.json`. The bad attempt is
terminal `INFRA_BLOCKED`; the source entry/compiled manifest now include
`--execute` and the bridge now maps `artifacts.outputs` into expected artifacts
with relative validation under `execution.cwd`. A follow-up semantic guard split
the completed durable-resume code checkbox from the remaining live parity
residual, removed the incorrect automatic TM-8 flip, and requires non-empty
decision chains for both arms. Retry TM-7 only from the regenerated entry hash
`sha256:720b210fd1ee2ba7a4e33fdaa647347c94faca0414bb8c7ca26c73f6473d6b3e`.

**TM-7 invalid-pass retry blocker (2026-07-21T03:49Z; no TM-7/TM-8 flip):**
the corrected bridge did execute the TM-7 command and wrote
`data/trace/tm7_realnode_parity.json`, but the report's `overall=PASS` is invalid
evidence. All four per-task verdicts had `len_a=0`, `len_b=0`, empty extracted
coverage, and both arms returned
`[FAILED: Terminal role architect_general: No LLM primitives or REPL configured]`.
The harness bug was that the pre-`9dfbe572` guard counted raw
`decision_chain()` metadata dict keys instead of extracted chain rows; orchestrator
`9dfbe572` fixes that fail-closed guard and adds a regression test. Latest ledger
status for retry `BULK-langgraph-tm7-parity-20260721T034655Z` is terminal
`INFRA_BLOCKED`. Evidence is packaged in
`coordination/inference-batch/bundles/BULK-langgraph-tm7-parity/tm7_realnode_parity_invalid_pass_summary_20260721T034655Z.json`.
Do not retry TM-7 until the parity runner wires the same live graph/LLM
dependencies used by production instead of bare `TaskDeps()`.

**TM-7 live graph parity closed (2026-07-21T04:09Z; TM-8 still open):**
after orchestrator `36bfe9b4` wired live graph dependencies and explicit
`result_role_history` parity-chain fallback, official retry
`BULK-langgraph-tm7-parity-20260721T040534Z` passed. The stale parity JSON was
backed up and removed before execution, `run_batch_entry.py --execute` exited
0, and the fresh report shows `overall=PASS`, `n_pass=4/4`, `n_fail=0`,
`arm_success_ok=true`, exact output equivalence, and
`n_parity_chain_coverage_fail=0`. Keep TM-8 separate: trace DB decision-chain
coverage is still missing (`n_trace_coverage_fail=4`, trace chain lengths
`0/0`), so trace materialization remains open before trace-coverage-dependent
gates.

**No-execute bridge preflight sidecar (2026-07-20T22:31Z; no entry completion):** durable evidence is now stored at `coordination/inference-batch/attestations/eligible-preflight-20260720T2231Z.jsonl`. It contains exactly 8 `phase=preflight` rows for `RE-4-longcot-mini-calibration`, `BULK-langgraph-tm7-parity`, `BULK-K-EMB-1`, `BULK-hermes-smokes`, `BULK-kbrag-autowiki-k11`, `ROUTE-A1-shapekeyed-step2`, `ROUTE-A2-edit-transaction-ab`, and `ROUTE-A3-j2j3-single-worker`. Every row has `dry_run_ok=true`, `blocking_reasons=[]`, topology verified against attestation `coordination/inference-batch/attestations/20260720T191355.json` with live hash `8c8cfcbb13d2611d`, `stack_contract.ok=true`, and `autopilot_precondition.ok=true`. The bridge passed no `--execute`; it created no batch ledger row or execution artifact package, and no execution checkbox was flipped.

**Topology repin checkpoint (2026-07-20; no entry completion):** root commit
`2c5a4125` repinned the P3 bulk-campaign and P4 routing source entries to
`production-consolidated-v7` with certified topology
`8c8cfcbb13d2611d`; the manifest and source lock were regenerated. A
preflight-only bridge verified the 9 currently runnable entries (`RE-4`,
`BULK-langgraph`, `BULK-K-EMB-1`, `BULK-XMAS`, `BULK-hermes`, `BULK-kbrag`,
`ROUTE-A1/A2/A3`) with `dry_run_ok=True`, `topology.verified=True`, and no
blocking reasons. Execution remains quiet-window gated; none is
`serial_noninference`.

**RCP/reviewer topology repin checkpoint (2026-07-20; no entry completion):** root
commit `c9bc73eb` repinned `00-rcp-prologue.yaml` and `10-reviewer-plane.yaml`
to `production-consolidated-v7` / topology `8c8cfcbb13d2611d`; the manifest and
source lock were regenerated. A targeted preflight-only bridge verified 11
RCP/reviewer operator-gated entries clean. Consolidated batch status is
`entries_total=52`, `valid=52`, `eligible_now=9`, `operator_gate_blocked=15`,
and `blocked=1` (`EV-4 BLOCKED_PRECONDITION`). The quiet window is false due to
active inference on port `18072` / MI210, so no entries were executed and no
checkboxes were flipped.

**Queue-hygiene checkpoint after v7-era repins (2026-07-20; no entry completion):**
root commits `94538e47` and `905519f2` tightened the runnable-row bridge. Passive
`BULK-XMAS` telemetry now requires the concrete
`XMAS-enforce-window-ab-root-present` gate, removing the literal
`<enforce-window AB root>` placeholder from pickable work; consolidated status is
now `eligible_now=8` and `operator_gate_blocked=16`. `BULK-K-EMB-1` now points at
`/mnt/raid0/llm/epyc-root/data/benchmarks/eval-corpus-v0.jsonl`, uses the real
`embedder_recall_bench.py --models/--k` operands, and sets
`EMBEDDER_RECALL_EXECUTE=1` for execution. Its preconditions name the e5-base,
bge-m3, and bge-large references. The current bridge preflight reports all 8
eligible rows `dry_run_ok=True`, verified topology, no literal `<...>`
placeholders, no blockers, and the K-EMB dry-run plan reports 100 documents,
30 queries, 0 missing references, and five result keys. The quiet window remains
false because port `18072` / MI210 is active: no entry was executed and no
checkboxes were flipped. EV-4 remains `BLOCKED_PRECONDITION` on B7 scorer sign-off.

**K-EMB warm-embedder lifecycle checkpoint (2026-07-20; no entry completion):** root
commit `ff2eaf0d` (`Guard K-EMB warm embedder lifecycle`) updated
`coordination/inference-batch/entries/30-bulk-campaign.yaml`, the compiled
`coordination/inference-batch/manifest.yaml`, and
`coordination/inference-batch/sources.lock.json`. `BULK-K-EMB-1` now probes ports
`8096`/`8097`/`8098`, starts only missing warm embedder roles, preserves roles that
were already live, and cleans up only the roles it started; baseline BGE on `8090`
is outside that cleanup set. This was a metadata/command-definition change only:
the batch entry was not executed and no execution checkbox was flipped.

**▶ To run (2026-07-20):** launch this as a **`/goal`** session (codex's equivalent of the `/loop` this handoff's protocol references) — the loop is **single-writer**, so no other session may write the ledger. **Do not re-run EV-4 yet:** the latest ledger row is `BLOCKED_PRECONDITION` on B7 scorer-semantics sign-off after the 2026-07-20T19:15Z partial run confirmed the textual multiple-choice rewrite was still changing scorer semantics. `OP-quiet-window` is granted only when `inference_load_check.py --json` reports `quiet: true` immediately before execution. EV-11a and EV-11b are now fixed; EV-11c still waits on the EV-CONF/logprob and scorer-era prerequisites before the math rebaseline entry can execute. P0 still needs its front gates (`OP-6a/6b` + stack-restart). (Terminology: this doc says `/loop` throughout; read it as `/goal` under codex.)

**⚠ 2026-07-20 — EV-4 did NOT pass; robustness audit filed, then Phase 0-4 blockers landed.** EV-4 hit `INFRA_BLOCKED` (stale contention matrix → silent fanout→concurrency=1 → killed partial run → no decision-grade metrics), and a later partial rerun exposed a textual multiple-choice scorer blocker. Root cause of the original fanout failure was NOT the kernel — it was the **2026-07-17 vision NUMA rebind** shipping without a matrix recert. The loop wedge, v7 topology pins, live v7 matrix recert, safe host remediation, mandatory autopilot preflight, forced-role concurrency, serial wall-budget hardening, scorer textual-label fix, and promotion/preflight prevention guards are now landed and checked in [eval-tower-loop-robustness-audit-2026-07-20.md](eval-tower-program.md#track-eval-tower-loop-robustness-audit-2026-07-20). EV-4's latest ledger state is now `BLOCKED_PRECONDITION` on B7 scorer-semantics sign-off, so it is intentionally not retry-pickable; do not append a fake checkpoint row or flip EV-4 until a fresh run produces decision-grade metrics.

**Checkpoint (2026-07-20T19:17Z; no EV-4 flip):** EV-4 is preflight-ready again
after the Phase-0 unblock. The fresh attestation
`coordination/inference-batch/attestations/20260720T191355.json` passed for
`frontdoor+worker_general` with `topology_hash=expected_topology_hash=8c8cfcbb13d2611d`;
`preflight_gate` now separates the 16-char contention topology hash from the
registry hash. A prepare-only `run_batch_entry.py --batch-entry /tmp/ev4-batch-entry.json`
reported `blocking_reasons=[]`, `stack_contract.ok=true`, and topology
`live_hash=required_hash=8c8cfcbb13d2611d`; root coordination verification
`test_batch_ledger.py test_batch_status_report.py -q` passed 31/31.

**Checkpoint (2026-07-20T19:22Z; no EV-4 flip):** the preflight-ready EV-4 run was
started and resolved fanout concurrency `4`, but was intentionally interrupted at
partial `cal-worker_general` progress after the overlapping textual-choice scorer
bug was confirmed. The latest ledger row is `BLOCKED_PRECONDITION` (run
`EV-4-20260720T191550Z-B7`), not retry-pickable by EV-4's `INFRA_BLOCKED` retry
policy. Complete the B7 operator-reviewed scorer-semantics package before appending
a `READY` row or re-running EV-4; partial progress artifacts under
`orchestration/reports/eval_batch_serving_evaltower_20260720T191550Z/` are
diagnostic-only and contain no `summary.json`.

**Checkpoint (2026-07-20Tpost-B7; no EV-4 flip):** `batch_status_report.py` now
distinguishes structural eligibility from runnable-now eligibility after
`op-bundle.md` operator gates. The current manifest has 24 structurally eligible
entries, but only 9 runnable entries once missing/ungranted operator gates are
filtered; 15 are surfaced separately as "structurally eligible but operator-gated."
Use `--ignore-operator-gates` only for structural audits, not for pick-next.

**Safety sidecar (2026-07-20; no EV-4 flip):** root `566eaacf` makes
`batch_status_report.py --ledger <missing>` fail closed with `rc=2` and
`ledger not found`; the real ledger reports EV-4 `BLOCKED_PRECONDITION`,
`ledger_rows=14`, and `eligible_now=9`. Root `bf112b90` makes
`compile_inference_batch.py` reject duplicate YAML mapping keys through its
strict safe loader, with clean CLI failure for validate/compile/simulate. The
full coordination suite passed `120 passed`, and validation reported `52 valid`.
RE-4 source/manifest content was already clean; this records duplicate-key
prevention only, not a manifest-content change. EV-4 remains blocked and its
checkbox is intentionally unchanged.

**START HERE (execution source-of-truth — machine-readable, do not re-narrate):**
- `coordination/inference-batch/LOOP_PROTOCOL.md` — the operator `/loop` runbook (single-writer rule, session-init, pick-next, per-entry cycle, autonomy policy)
- `coordination/inference-batch/manifest.yaml` — the 52 compiled entries (source of truth for WHAT runs; recompile from `entries/*.yaml` via `scripts/coordination/compile_inference_batch.py compile`)
- `coordination/inference-batch/op-bundle.md` — the canonical operator-gate registry (A–F) + 4 pre-formed Escalation decisions
- `coordination/inference-batch/ledger.jsonl` — append-only execution ledger (the loop is its SOLE writer)

The `/loop` is the SOLE writer of the ledger + batch checkbox flips. Do NOT run a manifest entry from any other session. NO nightshift; quiet-window-gated (never compete with the parallel inference session).

#### Prioritized task list

##### Infrastructure — COMPLETE (this makes the loop runnable; 2026-07-17)
- [x] Consolidated inference-batch manifest built — 52 entries, compiler + ledger lib ✅ 2026-07-17
- [x] Command-fabrication 5-audit (commands/provenance/preconditions/graph/committed-code) — fabrication localized to leaf commands ✅ 2026-07-17
- [x] Command repair — ~15 entries re-pinned to real commands; ~15 honest `BUILD-*` gates ✅ 2026-07-17
- [x] 8 backlog runners built + fixture-tested (tm8_coverage, lb1_attribution, reviewer_policy_arm_ab, field-order arm, glm_capability_probe, embedder_recall_bench, shapekeyed_step2_smoke, migration_probe) ✅ 2026-07-17
- [x] eval-tower verifier/calibration mode (EV-4/EV-11 runnable; EV-5/7/8 download-gated) ✅ 2026-07-17
- [x] Mechanism-B ledger bridge + Mechanism-A events→ledger materializer (RCP-W2/W3/RC-8 runnable) ✅ 2026-07-17
- [x] Escalations ESC-1..4 resolved (relaunch command, eval-suite routing, bench `-m` form, Mechanism-A validated on 32 real events) ✅ 2026-07-17
- [x] op-bundle gate registry reconciled (21 gates A–F + 12-item build-backlog, 9 flipped SATISFIED) ✅ 2026-07-17
- [x] Autopilot wiring: digest FA/FR consumer (B1), materializer refresh (B2), AP-6 seam (B4), supervisor liveness (C1), precondition gate (C2) ✅ 2026-07-17
- [x] Dashboard incoherence root-cause (H4 lost-updates / H2 no-shared-epoch / H5 age-not-value) + `state_lock` primitive ✅ 2026-07-17
- [x] Dashboard incoherence root-cause + fix — H4 single-writer lock + daemon control-merge, H2 shared snapshot epoch, H5 value-consistency axis ✅ 2026-07-17
- [x] TM-7 bridge no-op prevention — command-driver entries now treat `artifacts.outputs` as expected artifacts, validate relative outputs under `execution.cwd`, and `BULK-langgraph-tm7-parity` now invokes the live parity leg with `--execute` ✅ 2026-07-21

##### Inference runs — PENDING the operator /loop (quiet-window gated)
- [x] **P-CRIT (Phase 0 unblock — do FIRST; runs in any detected quiet window, self-gated via `inference_load_check` like every other entry — no separate approval)** — **re-measure `vision_escalation` + regenerate the v7 contention matrix, then commit it.** ✅ 2026-07-20 — live v7 recert completed on topology `8c8cfcbb13d2611d` (15 measured cross-role pairs, 6 same-role entries, 0 unknown pairs), committed in `epyc-orchestrator`; D1/D4/D5 also landed in `epyc-root`. Full analysis + owner-tagged fix checklist: [eval-tower-loop-robustness-audit-2026-07-20.md](eval-tower-program.md#track-eval-tower-loop-robustness-audit-2026-07-20).
- **[declined: ws58 2026-11-03 content-review: duplicate — RCP-W1/W2/W3 are the boxes; this is a campaign index line]** **P0** RCP prologue — RCP-W1 (reference relaunch + preflight), RCP-W2 (ledger materialize), RCP-W3 (calibration smoke) — gated OP-6a/6b + OP-stack-restart-approval
- **[declined: ws58 2026-11-03 content-review: duplicate — RC-8, RM-6, LB-1, LB-4, RD-12, TM-8 are owned by reviewer-control-plane.md; a campaign index line]** **P1** reviewer-plane riders — RC-8, RM-6, LB-1, LB-4, RD-12, TM-8 (TM-8 self-attested until emit-path markers land)
- **[declined: ws58 2026-11-03 content-review: duplicate of EV-4b above; the B7 scorer-semantics sign-off is recorded there]** **P2** eval-tower — EV-4 is the first live v7 entry, but it is currently `BLOCKED_PRECONDITION` on B7 scorer-semantics sign-off. The EV-4 command requires `--min-eval-concurrency 3`; verifier-mode preflight now checks fanout against the actual forced roles (`worker_general,frontdoor`), serial fallback has a wall-budget fail-closed path, runner arms require full `n_scored` before decision-grade, and the textual multiple-choice implementation now covers configured labels, overlapping labels, and `(B)` expected letters. Because that changes scoring semantics, rerun EV-4 only after B7 operator sign-off, then append an explicit `READY` row or intentional retry-policy change. EV-11b closed-bin ECE is implemented; EV-11c remains after EV-CONF/scorer-era prerequisites; EV-5/7/8 (MODEL-DOWNLOAD-gated); EV-10a; RE-4; H5-RM3
  - **[declined: ws58 2026-11-03 content-review: merged into RE-4.2 — the redesign is done (re4-protocol-redesign track); the non-saturation probe is the next step]** **RE-4 protocol repair** — redesign LongCoT-Mini execution so models may do bounded reasoning while deterministic final-answer extraction still works. Do not rerun the `concise_solution` + answer-only grammar protocol; latest evidence is floor-saturated (frontdoor 0/402, worker_general 0/307) and quarantined as `protocol_blocked/floor_saturated`.
- [ ] **P3** bulk-campaign — DS-E1, A7, XMAS, hermes, kbrag, langgraph, ODLB-W3-01/02; K-ROPE (harness build-gate); ODLB-W3-03 (paddleocr-VL build-gate). `K-EMB-1` is DONE_PASS 2026-07-20, but this campaign row stays open until the remaining P3 entries close. **ODLB-W3-01 status (verified 2026-08-13, mainB): BLOCKED_PRECONDITION — do not dispatch as a bare run.** Three verified blockers: (1) no `lightonocr` engine exists in `odl_bench` (only pdftotext/opendataloader/liteparse deterministic + paddleocr_vl/unlimited_ocr model-gated; the manifest entry is a Wave-3 stub in `manifest_stubs.py` with no backing implementation); (2) the only real LightOnOCR path is orchestrator `PDFRouter._extract_with_lightonocr` — an HTTP OCR server (`{url}/ocr/pdf`) — contradicting the "no llama-server / use llama-cli one-shot" constraint; (3) prior evidence (K35.18c, 2026-07-19) already showed LightOnOCR-2-1B quality "not table-clean or QA-clean", and K35.18 says rerun **only with a concrete parser-quality hypothesis or a bench-compatible HTML/table extraction path** — none supplied. Manifest preconditions also unmet (needs source PDFs mapped to GT pages + quiet window). **Unblock path: build the lightonocr odl_bench engine or a llama-cli one-shot producer with a named hypothesis, then run in a quiet window.** [check: which of DS-E1, A7, XMAS, hermes, kbrag, langgraph, ODLB-W3-01/02/03, K-ROPE still exist as runnable entries under coordination/inference-batch/entries/? List the runnable ones here with their blockers or retire the row]
  - [x] **TM-7 live-deps runner repair** ✅ 2026-07-21 — orchestrator `36bfe9b4` wires `scripts/trace/run_task_lg_parity.py` to live graph/LLM dependency construction and distinguishes role-history parity from trace DB coverage. Official retry `BULK-langgraph-tm7-parity-20260721T040534Z` passed with `n_pass=4/4`, `n_parity_chain_coverage_fail=0`, and `n_trace_coverage_fail=4`; TM-7 is closed, TM-8 remains open.
  - [x] **BULK-hermes-smokes standalone smoke close** ✅ 2026-07-21 — official run `BULK-hermes-smokes-20260721T042834Z` passed the corrected standalone Hermes smoke bundle with `13/13` checks, including `live:reference-client`, `live:multiturn`, and `live:subagent` (`2/2` parallel subagents on one `8099` slot). Harness fixes landed in root (`run_hermes_wave3_batch.sh`, `run_hermes_smokes.sh`, `reference_openai_client.py`, `launch_hermes_backend.sh`). Important scope boundary: this did **not** perform the upstream Hermes checkout/pin bump and did **not** complete the full orchestrator `8000` override-semantics validation; those remain open in `user-facing-harness-index.md`.
- [x] ~~**P4** kernel/OP-2 — OP-2/v6+iqk and final v7 readiness closed outside this loop on 2026-07-19; do not schedule unchanged KOP2-frontdoor/KOP2-v6iqk reruns. Remaining kernel/routing entries require the manifest owner to reconcile the ledger against [v7-promotion.md](../completed/v7-promotion.md) and current post-candidate work before execution.~~ (closed 2026-10-29 audit: SUPERSEDED → box text: OP-2/v6+iqk and v7 readiness closed outside this loop 2026-07-19 (handoffs/completed/v7-promotion.md); do not schedule unchanged reruns)
- [x] ~~**P5** GLM window — legacy GC1/GC2/GC3 admission chain is superseded. GLM failed decision-grade P-REV-1 and reviewer/control-plane is decoupled from v7; only run a GLM entry with a named repair hypothesis or non-reviewer capability gate.~~ (closed 2026-10-29 audit: OBSOLETE → box text: legacy GC1-GC3 chain superseded; GLM failed decision-grade P-REV-1; GLM-5.2/5.3 models are in deprecated_models graveyard)
- **[declined: ws58 2026-11-03 content-review: duplicate — RC8/LB7/RM4/RM8/RELABEL/RM2-A3 are owned by reviewer-control-plane.md; a campaign index line]** **P6** decision-grade confirmations — RC8/LB7/RM4/RM8/RELABEL/RM2-A3 (gated OP-5a P-REV-1; RM2-A3 also COORD-axa-teleport)

##### Genuinely blocked build-backlog — OWNED BY THIS reviewer-plane/ODL workstream (NOT the loop, NOT the parallel session)
These are BUILD tasks for this workstream's own code. The parallel session / operator only CLEARS the trigger; the build itself is a future session like the one that built the other 8 runners (see progress 2026-07-17). **When the trigger fires: build the runner (fixture-tested; non-serving-path where possible), then pin it into its manifest entry + flip its op-bundle §F gate — exactly the pattern used for the 8 built runners.** A parallel/loop session picking up this handoff should NOT attempt these — it should only signal when the trigger fires.
- [ ] `BUILD-semantics-serving-integration` — wire CP1/CP2/CP3 (reducer/authority/escalation — already landed as modules, orchestrator `43a77eaf`) into the live serving path. **TRIGGER: the stack-freeze lifts** (parallel session's feature tests complete). This IS a serving-path change, so it genuinely cannot be built until then. Owner: reviewer-plane workstream. Unblocks: `semantics-shadow-rollout`, `semantics-advisory-rollout`. [check: is the CP1/CP2/CP3 serving-path wiring tracked in reviewer-control-plane.md? If yes, retire here as a duplicate; if not, its trigger ("stack-freeze lifts") was satisfied months ago and it needs a stack-change package]
- [ ] `BUILD-paddleocr-vl-adapter` — `_extract_with_paddleocr` VL backend in `src/services/pdf_router.py`. **TRIGGER: the PaddleOCR-VL model lands on disk** (operator download, gated `OP-VL-INFERENCE-APPROVAL`). Owner: ODL workstream. Unblocks: `ODLB-W3-03`.
- [ ] **CP3 in-content-injection quarantine (§13.2 control 1)** — the reviewer-prompt control/data DELIMITER. The assembly-layer half (path-allowlist + secret redaction + buried-critical `truncation_manifest`) LANDED 2026-07-17 (`src/proactive_delegation/candidate_sanitizer.py` `7a3fcb55`); this residual needs a delimiter in `review_service._render_outputs`, which is serving-path. **TRIGGER: stack-freeze lifts** (same freeze as `BUILD-semantics-serving-integration`). Owner: reviewer-plane. Anchor: `tests/test_candidate_security.py::TestInContentInjectionGap` + injection-probe `01`/`09` (xfail, annotated freeze-blocked). [check: same question as BUILD-semantics-serving-integration: tracked in reviewer-control-plane.md? If yes retire here; the July freeze is long lifted]
- [ ] **Patch pre-gate live-dispatch wiring (EV-12)** — wire the built `src/verification/patch_pre_gate.py` (`902fd303`) into the coder_escalation dispatch as a real pre-gate (skip escalation inference on a provably-broken patch). The SIGNAL is built + tested; only the live-dispatch call is deferred. **TRIGGER: stack-freeze lifts** (touches the dispatch/serving path). Owner: routing/reviewer-plane. Consumer handoff: `research-evaluation-index.md` RE-2/EV-12. Trigger satisfied: the July 2026 stack-freeze lifted. Ship as a flagged orchestrator change; done when one logged coder_escalation dispatch skips inference on a provably-broken patch and the flag is default-off until that log exists.

#### Dependency graph (phase gating)
`P0 (RCP-W1 -> W2/W3)` -> `P1 riders (depend on RCP-W1)` -> `P2 eval-tower (independent)` -> `P3 bulk` -> `P4 kernel/routing (requires 2026-07-19 readiness reconciliation before pick)` -> `P5 GLM (only named repair/non-reviewer gates)` -> `P6 decision-grade (OP-5a)`. COORDINATION rows (phase 90) are never picked — the operator/parallel-session flips them to DONE_PASS to unblock dependents. Full DAG in `manifest.yaml`; `compile_inference_batch.py simulate` prints pick-next ordering, but stale kernel/GLM rows must be reconciled before execution.

#### Cross-cutting concerns
- **Stack-freeze**: no serving-path/lineup change until the parallel session's feature tests complete. The RCP relaunch brings up the *existing* reference lineup (not a config change).
- **Instrument discipline**: all pre-P-REV-1 reviewer numbers are OBSERVATIONS (never gate keep/revert/promote). Era-stamp every result.
- **Quiet-window rider**: `throughput_sensitive`/`eval_fanout` entries run only in a detected quiet window (`inference_load_check.py`); `serial_noninference` may run anytime.

#### Reporting instructions (for the /loop)
After each entry: write the ledger terminal row; on `pass`, flip the entry checkbox + `also_flips` via `flip_checkbox.py`; on `marginal`, record an observation (no flip); on `ambiguous`/`op_gate`, append a decision block to `op-bundle.md` and continue. Regenerate `batch_status_report.py` + update this handoff's status line at each phase boundary. Full wrap-up at phase boundaries.

#### Key file locations
- Entries: `coordination/inference-batch/entries/{00-rcp-prologue,10-reviewer-plane,20-eval-tower,30-bulk-campaign,40-routing,50-kernel-op2,60-glm-decision,90-coordination-rows}.yaml`
- Loop tooling (epyc-root): `scripts/coordination/{compile_inference_batch,batch_ledger,entry_verdict,flip_checkbox,inference_load_check,batch_status_report,autopilot_precondition_gate}.py`
- Runners (epyc-orchestrator): `scripts/analysis/{run_paired_ab,reviewer_corpus_ledger_run,reviewer_events_to_ledger,reviewer_policy_arm_ab,tm8_coverage,lb1_shadow_overhead_attribution}.py`, `scripts/autopilot/{skill_efficacy_paired_ab,glm_reviewer_capability_probe,shapekeyed_step2_smoke,migration_probe,state_lock}.py`, `scripts/trace/run_task_lg_parity.py`
- Runners (epyc-inference-research): `scripts/benchmark/{longcot_mini_adapter,score_longcot_run,embedder_recall_bench}.py`, `scripts/kb_rag/autowiki_writer.py`

#### Completed Scope
Historical detail: `progress/2026-07/2026-07-17.md` ("Inference-batch manifest — command-fabrication audit + repair"). This handoff subsumes the RCP/DS-E1/K-ROPE/K-LCM-1/Queue-2 execution rows previously staged in `bulk-inference-campaign.md` (see its 2026-07-17 subsume banner).

#### Candidate entries proposed 2026-07-21 (from the research-intake deep-dive session)

Proposed as **prose only** — deliberately not written into `coordination/inference-batch/entries/*.yaml`, because the loop was actively consuming those files and the ledger at the time. Whoever owns the loop should decide whether to promote these into entries.

**Triage of the three items that session produced, by whether they actually need inference:**

| item | needs inference? | disposition |
|---|---|---|
| iqk IQ-quant enablement (B1-B5) | **YES** — build + per-model coherence + `llama-bench` | **operator-assigned** to a dedicated kernel session; see [iqk-iquant-enablement.md](quantization-and-low-bit.md#track-iqk-iquant-enablement). Do not duplicate — but if the loop reaches a quiet window first, coordinate rather than race. |
| ContextRot rot-signature probe | **YES** — moderate, see below | genuine candidate entry, **optional** |
| rot↔NA compaction telemetry | **NO** | orchestrator-side plumbing only (`pipeline_monitor/anomaly.py` detectors already exist; the inverted detector is already fixed in `3d452476`). **Does not belong in this loop.** |

##### Candidate entry: ContextRot behavioural-signature probe (optional, moderate cost)

**What**: run the `GAIR-NLP/ContextRot` local-search arm against our own stack to see whether the paper's **rot ↔ no-answer substitution** reproduces on models we serve. Source: intake-869 / arXiv 2606.29718.

**Why it is scoped to the signature, not the accuracy delta**: the paper's accuracy differences between context-management policies are ~1pp on the self-hostable arm (BrowseComp-Plus), with ±2.5-3.8 SD over 5 repeats on a 100-question split — we cannot resolve that at any n we can afford. The **behavioural** signature is a ~50pp move (rot 53.4%→16.2%; no-answer 4.2→17.6 when summarization is added) and is resolvable at far smaller n. Anything targeting the accuracy delta should be refused.

**Cost estimate (honest, and the reason this is optional)**: the full three-arm 200-question replication is ~25-50h/arm NUMA-concurrent at 1 rep — 3-6 days wall clock, and still underpowered for accuracy. A signature-only probe (2 arms — ReAct vs keep-latest+summary — at n≈30-50, capped turns, shorter contexts) is materially cheaper but is **still real inference time**, not a smoke test. Do not schedule it ahead of anything with a decision attached.

**Preconditions** (all verified 2026-07-21, none blocking):
- Corpus `Tevatron/browsecomp-plus-corpus` — 100,195 docs, 1.76 GB download / 3.26 GB on disk. **Not present locally** → this is a `data_gate`.
- Embeddings `miaolu3/browsecomp-plus` `corpus_embeddings.pkl` — 821 MB, **Qwen3-Embedding-8B-specific** (4096-dim bf16). Our BGE servers are **not** a drop-in substitute; substituting them would require re-embedding all 100,195 docs and would break comparability with every published number.
- Judge is hardcoded `gpt-4o-mini` / `gpt-4.1` at `localsearch/src/envs/local_search.py:208,250` — **two string literals** must be repointed at a local endpoint before it can run at all (open-source-only constraint).
- `search_server.py` hardcodes `torch.device("cuda:0")`; under ROCm this maps to HIP and would occupy our only MI210. **Patch it to CPU** so the GPU stays free — retrieval is one 8B query forward plus an 820 MB matmul per turn, sub-second on EPYC.
- The BrowseComp (web) arm requires a paid `SERPER_API_KEY` and is **out of scope** — local arm only.
- Repo ships **no LICENSE file**.

**Gate**: report rot-rate and no-answer-rate, never accuracy. A give-up-rate improvement that is accompanied by a rise in unfinished trajectories is **not** an improvement — that substitution is the whole finding.

- **[declined: ws58 2026-11-03 content-review: the ContextRot harness fails the open-source-only constraint (paid SERPER_API_KEY, missing license) per the CF-3c deep-dive correction; nothing to promote]** Operator/loop-owner decision: promote the ContextRot signature probe to an entry, or decline it as too costly for its decision value.

## Track: prompt-construction-determinism
<!-- gate: none -->

> Folded from `handoffs/active/prompt-construction-determinism.md` @ `c4b6d1388716` on 2026-11-02 (BRF-T1-F2, route 1a, operator D1/D5; retired row RTG-27 → EVL-14). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Prompt-Construction & Sampling Determinism

**Created**: 2026-06-26
**Owner domain**: [routing-and-optimization-index.md](routing-and-optimization-index.md) · master row **N14**
**Status (2026-07-06)**: **DEPLOYED LIVE, attestation-green, COMMITTED through the June sampler path; OpenAI-compatible sampling propagation landed in orchestrator `fe390e5a` and was deployed by scoped API reload (PID `3577452`).** D2 clean-window probe is closed with no think-loop/revert trigger; D3/D4 remain.

#### Current State

A determinism audit of the live orchestrator prompt/sampling path established: **prompt *construction* is deterministic; generation *sampling* was not.** The sampling gaps were deployed-fixed on 2026-06-26 (immediately after the v6+iqk cutover, N13). Stack reloaded (`architect_general` pid→3811260 with `--jinja`; `orchestrator` pid→3812248); `stack_change_pipeline check` → **all gates green, `runtime_attestation: ok`, acceptance: no-inference checks passed.**

**Verified deterministic (no action):** routing artifact `derived/stack_priors.yaml` fresh (7/7 source hashes), no `ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES` override, no degraded fallback, template-family selection correct per role, static system prompts, no timestamp/random in builder path, RAG abandoned, `--jinja` inert on `/completion` (no double-templating).

#### What landed (deployed + committed)

| # | Change | File(s) |
|---|--------|---------|
| 1–3 | Single `_apply_deterministic_sampling()` helper wired into **all 3** payload sites (`_build_payload` /completion, `_infer_chat_completions` non-stream :518, stream :1193): temperature precedence `acceleration.temperature` → **`generation_defaults.temperature`** (was silently dropped → accidental greedy 0.0) → `request.temperature`; pinned `seed` (fixed `_DETERMINISTIC_SAMPLING_SEED=42`, per-request override via `request.seed`); unified `top_k=40/top_p=0.95/repeat_penalty=1.1` across **both** endpoints (chat path previously sent none → server defaults) | `src/backends/llama_server.py`; `seed` field added to `src/inference/model_server.py` `InferenceRequest` |
| 4 | Removed `architect_general` jinja exclusion (`stack_priors.py:~1158`, was commit `0879ed56`); auto-enrolls it into the cc-set so it routes `/v1/chat/completions` where its registry `enable_thinking=false` (model_registry.yaml:493) fires. Recompiled `derived/stack_priors.yaml`. Verified: jinja=True, enable_thinking=False, cc-set 6→7 = {architect_general, coder_escalation, frontdoor, toolrunner, worker_general, worker_math, worker_summarize} | `src/registry/stack_priors.py` + `orchestration/derived/stack_priors.yaml` |

2026-06-27 no-inference hardening: orchestrator `ab75b5ae` adds regression
coverage for `_apply_deterministic_sampling()` through `_build_payload`,
locking `generation_defaults.temperature` precedence, the pinned default seed
`42`, per-request seed override, and shared `top_k`/`top_p`/`repeat_penalty`
defaults. This protects D1's deployed sampling contract; it does not close D2
or D3 because those remain clean-window live validation tasks.

2026-06-28 clean-window packaging: orchestrator `16876006` adds
`scripts/benchmark/j12_think_loop_probe.py` plus unit tests. The runner uses
generated stack-prior primary ports for `frontdoor` and `architect_general`,
sends `/v1/chat/completions` requests with
`chat_template_kwargs.enable_thinking=false`, writes JSONL plus a summary, and
classifies empty outputs, HTTP errors, `<think>` leaks, known
`Wait, I found a reference` loops, repetition loops, and coarse expected-match
counts. It refuses claim-grade execution unless `--confirm-clean-window` is
passed and exits `75` while AutoPilot is active unless
`--allow-active-autopilot` is explicitly used for non-claim-grade live-load
telemetry.

2026-07-04 OpenAI-compatible request-sampling propagation: orchestrator
`fe390e5a` (deployed by scoped API reload to PID `3577452`) closed the code
gap after the Hermes
client-surface audit exposed that `OpenAIChatRequest.temperature` was accepted
but not forwarded. The route now carries caller-explicit `temperature`,
`seed`, `top_p`, and `top_k` through `/v1/chat/completions` ->
`LLMPrimitives.llm_call()` -> `InferenceRequest` -> llama-server payloads.
Omitted OpenAI `temperature` still means "use the role registry/defaults";
explicit `temperature=0.0` forces greedy. The caching backend no longer
manufactures a synthetic role config with `temperature=0.0`, so registry
`generation_defaults.temperature` can reach persistent llama-server backends.
Content-cache keys remain legacy-compatible for default calls and include a
stable sampling key only when explicit sampling controls are present.

2026-07-06 clean-window J12/D2 probe: with AutoPilot stopped, the committed
runner completed
`uv run python scripts/benchmark/j12_think_loop_probe.py --roles frontdoor architect_general --confirm-clean-window`.
The durable report is
`epyc-orchestrator/orchestration/reports/j12_think_loop_probe_20260706T143621Z/`.
Result: `frontdoor` `15/15`, `architect_general` `14/15`, `0` empty outputs,
`0` HTTP/error answers, `0` `<think>` leaks, `0` known wait-reference loops, and
`0` repetition loops on both roles. The architect jinja/chat-completions flip
has no clean-window revert trigger from D2.

#### Outstanding tasks (priority-ordered)

- [x] **D1 — git commit** ✅ **DONE 2026-06-26** — orchestrator `f4a8a3ca` (llama_server.py, inference/model_server.py, registry/stack_priors.py, derived/stack_priors.yaml), root: this docs commit (docs). **Unpushed** — operator pushes manually.
- [x] **D2 — J12 architect think-loop probe** ✅ **DONE 2026-07-06** *(Queue-2 quiesce window; REVERT-GATE for change #4)*. Clean-window run with AutoPilot stopped wrote `epyc-orchestrator/orchestration/reports/j12_think_loop_probe_20260706T143621Z/{results.jsonl,summary.json}`. Result: `frontdoor` `15/15`, `architect_general` `14/15`, `0` empty outputs, `0` HTTP/error answers, `0` `<think>` leaks, `0` known wait-reference loops, and `0` repetition loops on both roles. The architect jinja/chat-completions flip has no D2 revert trigger. The prior 2026-06-27 live-load probe was only non-claim-grade telemetry because AutoPilot was active.
- **[declined: ws58 2026-11-03 content-review: superseded — the N13/v6 era it was tied to is gone; the greedy->sampled change was fenced (orchestrator dcd60332) and the v8 and v10 ratifications set the current quality era]** **D3 — manual canonical bench (sampling quality cert)** *(clean window; certifies #1–3)*. Greedy→sampled(0.1–0.3)+seed shifts output behavior. Certify via P-BENCH canonical recipe (`bench_canonical.sh`/`canonical_recipe.py`) per `/workspace/MEASUREMENT.md`. **Co-schedule with the N13 v6-iqk post-reboot bench** — both want the same clean window.
- **[declined: ws58 2026-11-03 content-review: superseded by the v8/v10 era rows in instrument_eras.yaml; the sampling fence is applied]** **D4 — sampling-quality instrument-era row** *(human-authored; AFTER D2+D3)*. The N13 kernel/AutoPilot-speed fence is now applied in orchestrator `dcd60332` (`E5-cpu-kernel`, `E5-autopilot-speed`, live AutoPilot `pareto_exclude_before_ts=2026-06-26T22:07:11Z`). The remaining D4 work here is the separate **sampling-determinism `autopilot_quality` boundary** after D2/D3, because greedy→sampled quality should not be certified until the architect revert-gate and canonical bench resolve. Its note should use DEMOTE-TO-PRIOR for pre-boundary quality numbers. `instrument_eras.yaml` remains a human-amendment surface (MEASUREMENT.md §4/§5).

Code gap closed 2026-07-04: OpenAI-compatible callers can now request
temperature/seed/top-p/top-k overrides, and omitted sampling preserves registry
generation defaults. This does **not** close D2/D3/D4 because those are
claim-grade live validation and instrument-era tasks.

#### Dependency graph

```
D1 (commit) ── independent, do now
D2 (J12 probe) ── closed 2026-07-06 ──┐
                 ├──► D4 (era rows)   [don't certify a boundary that might revert]
D3 (canon bench)─┘
D3 still wants a quiesce/clean window → co-schedule with Queue-2 + N13 post-reboot bench
```

#### Cross-cutting

- **vs N13 (v6-iqk):** this deployed immediately after the cutover; D3 and D4(a)=E5 share N13's clean-window + era-row closeout. Treat as one regime change for benching/era purposes.
- **vs J12 (campaign):** J12 "wiring" was closed 2026-06-12; change #4 makes architect the live consumer, so the Queue-2 J12 *probe* now has a concrete deployed arm to validate (revert-gate).
- **vs registry-compile-master-reconcile (N-deferred):** change #4 edits the *lean* `stack_priors.py` jinja computation; when master becomes authoritative (`--compile-registry` ON), carry the architect jinja change into master.

#### Key file locations

- Sampler: `src/backends/llama_server.py` (`_apply_deterministic_sampling`, 3 call sites); request sampling DTO: `src/inference/model_server.py`; OpenAI request surface: `src/api/models/openai.py`, `src/api/routes/openai_compat.py`; primitives propagation/cache key: `src/llm_primitives/{primitives.py,inference.py}`, `src/inference/llm_cache.py`.
- Routing gate: `src/registry/stack_priors.py:~1158` (jinja); `src/chat_completions_roles.py` (derivation gate jinja∧enable_thinking==False); `orchestration/derived/stack_priors.yaml` (recompile via `python3 -m src.registry.stack_priors`).
- **Constraint (2026-08-21) — a chat template is executable code in the prompt-construction position**: any chat-template substitution (third-party or vendor-refreshed) must be checked against the in-tree **input-marking** path of the frozen `common/jinja/` engine before it is routed through the gate above — see the *Research Intake Update — 2026-08-21 (intake-1216#record)* section below and [`qwen-chat-template-evaluation.md`](harness-program.md#track-qwen-chat-template-evaluation) task **CT-3**.
- Gates: `scripts/registry/stack_change_pipeline.py check` (uses `.venv/bin/python3`); `src/registry/registry_validator.py`.
- Lifecycle: `scripts/server/orchestrator_stack.py {reload,status}` (architect_general, orchestrator).

#### Reporting

On closing a task: check the box here, update master row **N14** + the routing-index subsystem row, append to `progress/2026-06/`. On full closure (D1–D4 done): extract findings to wiki, move this handoff to `completed/`, delete N14. Memory: [[project_prompt_determinism_plan]], [[feedback_enable_thinking_requires_chat_completions_path]], [[feedback_stack_change_three_gates]].

#### Research Intake Update — 2026-08-21 (intake-1216#record, chat-template engine)

- [x] **PCD-T1** — Record a constraint on any chat-template substitution: a chat template is
      **executable code in the prompt-construction position**. Frozen `production-consolidated-v9`
      (`0db32c06e`) runs a **first-party** Jinja engine at `common/jinja/` (lexer/parser/runtime/
      value/caps, from ggml-org/llama.cpp PR#18462) — **not minja**, whose only occurrences in the
      tree are a stale TODO comment at `common/chat.cpp:749`, a test, and a doc. That engine
      implements **input marking**: `jinja::string` carries an `is_input` flag through one-to-one,
      one-to-many and many-to-one transformations specifically so user content cannot forge special
      tokens, and `common/chat.cpp` normalises input *before* it reaches the runtime. Any decision
      to run a third-party template must be checked against that path. Neither community template
      repository mentions it.
      ✅ 2026-08-21 (constraint recorded + cross-referenced at the operative section) — one-line
      cross-reference added under *Key file locations → Routing gate*, the operative surface a
      template swap passes through, pointing here and at `qwen-chat-template-evaluation.md` CT-3
      (verified present at that file:91). Full text not duplicated.

## Track: re4-protocol-redesign
<!-- gate: none -->

> Folded from `handoffs/active/re4-protocol-redesign.md` @ `c4b6d1388716` on 2026-11-02 (BRF-T1-F2, route 1a, operator D1/D5; retired row EVL-35 → EVL-14). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### RE-4 / K-LCM-1 — LongCoT-Mini Protocol Redesign (design + harness SPEC)

**Status:** ACTIVE/GATED — runner v2 and entry v2 landed 2026-07-21; no inference is authorized by this design note.
**Owning entry:** `coordination/inference-batch/entries/20-eval-tower.yaml` → `RE-4-longcot-mini-calibration` (v2 applied; re-attest current v8 topology before the quiet-window probe).
**Owning handoff:** `handoffs/active/eval-tower-program.md` (open task line: *"RE-4 protocol repair"*).
**Measurement grade:** OBSERVATION (non-saturated research benchmark; hypothesis-only, never a keep/revert/deploy/promote gate). Scoring stays deterministic — **NO LLM-judge** (MEASUREMENT.md).
**Runner code change required:** **YES** — the fix is *structural* (a second, forced-final-answer HTTP turn), so this doc SPECs it for a follow-on implementation pass rather than editing the runner in place.

---

#### 1. Root cause — why the parked protocol floor-saturated

The benchmark requires **both** (a) genuine multi-step reasoning **and** (b) a terminal `solution = <value>` line the deterministic scorer can anchor on. The two generation modes shipped in `longcot_mini_stack_runner.py` each satisfy only *one* of those, so both score ~0%:

**Failure mode 1 — `concise_solution` + `--force-solution-grammar` (the aborted RE-4 run, `longcot_mini_re4_grammar_20260721T013833Z`).**
The grammar `root ::= "solution = " ([^\n])+ "\n"?` forces the output to be exactly one answer line, and the `concise_solution` system prompt tells the model *not* to show derivation. Result: **frontdoor 0/402, worker_general 0/307**, `canary_leak=0`, `missing_from_prompt_index=0`, all rows `reason=mismatch` (perfect marker compliance, every answer wrong). Completion lengths were **13–34 tokens** — the model emitted a blind guess with no reasoning. Concrete rows (frontdoor):

| qid | expected (gold) | forced response | ctoks |
|---|---|---|---:|
| longcot_mini_1 | `["2013^{4025}", 2692, 26]` | `solution = 1, 18, 27` | 13 |
| longcot_mini_100 | `["2^{2013}-6036", 144, 15, 36]` | `solution = [1024, 8, 2, 28]` | 19 |
| longcot_mini_101 | `"8/r7/kn3p2/1pr1pPpp/NP2PbPP/5K2/3B4/1bR1bB2 w - - 122 349"` | `solution = 8/2k5/1p6/1P6/8/8/8/4K3 b - - 0 1` | 34 |

Forcing `solution = X`-only output suppressed exactly the reasoning LongCoT-Mini exists to measure. This is the recorded terminal blocker.

**Failure mode 2 — `standard` prompt at `max_tokens=2048` (the two earlier partial runs, `…234821Z` / `…stack_…011903Z`).**
Free CoT, no grammar. The model reasons in full — but on these long-horizon items (chess games replayed move-by-move over 100s of plies; dependency-chain math; big-exponent algebra) it **never reaches a `solution =` line within 2048 tokens**. Every one of the 11 completed rows hit the 2048 cap mid-reasoning with **0 `solution =` markers present** → the deterministic scorer would return `no_solution_marker` for all of them → also ~0%. And at 2048 tok/item × 507 items × 2 roles the run is too slow for the window (those runs were aborted after 11/21 rows).

**Net:** grammar kills reasoning (mode 1); unbounded-at-2048 never terminates into the marker (mode 2). The scorer, the dataset, and the structural-match machinery are all **fine** — the *generation protocol* is the defect. The "easy" difficulty label is a dataset tag; these items are still genuinely long-horizon and need a large reasoning budget **plus** a guaranteed terminal answer.

Supporting memory: `feedback_accuracy_token_tradeoff_rescue_metric` explicitly flags **truncation caps** as a baseline confound that fakes a floor — precisely mode 2. `feedback_production_sampling_seed_not_temp0` — sampling-sensitive quality benches use production temp + seed 42; the current runner sends `temperature=0.6` **but no `seed`**, so even a good protocol is non-reproducible today (fixed in the runner SPEC below).

---

#### 2. Design requirement (from the postmortem `next_action`)

> Allow **bounded reasoning** while preserving **deterministic final-answer extraction.**

Any redesign must (i) let the model do real CoT with a generous budget, (ii) guarantee a deterministic terminal `solution =` line even when the model is still mid-reasoning at the cap, **without** constraining the reasoning itself, and (iii) keep scoring judge-free.

---

#### 3. Options evaluated

##### (a) Two-phase prompt — free reasoning, then a grammar-forced final line after a reasoning budget  ← **CHOSEN (core mechanism)**
Phase 1 = free CoT, generous cap, no grammar. Phase 2 = only if Phase 1 did not already emit a `solution =` marker, a *second* turn that feeds the Phase-1 reasoning back and applies the `solution = ` grammar to **that turn only**, forcing exactly the final answer line.
- **Pros:** grammar constrains *only* the terminal answer, never the reasoning that produced it → directly satisfies the requirement. Deterministic marker guaranteed for the scorer. Reasoning-token count preserved for the reasoning-compression signal. Short-circuits (0 extra calls) whenever Phase 1 already ended with a marker.
- **Cons:** two HTTP calls on the truncating tail (~2× latency there); needs a structural runner change (new conditional second turn).

##### (b) Unconstrained generation + robust extraction (B7 final-answer-region extractor + math_verify-style parsing; reuse E7-era scorer machinery)
Single call, no grammar, extract with the last-`solution =` anchor plus B7 SCORE-03 final-answer-region fallbacks (last line / `\boxed{}` / colon-anchored).
- **Pros:** parameter-only, no runner code; the adapter *already* does last-marker (final-region) anchoring.
- **Cons:** does **not** solve mode 2 — a mid-reasoning truncation has no marker and no boxed answer, so the region fallback scrapes garbage from the last line → wrong. It cannot *force termination*, so the budget must be pushed very high (slow) with still no guarantee. `math_verify` is math-only and orchestrator-copy-only; LongCoT-Mini answers are SMILES / FEN / JSON arrays/objects — the existing **structural** scorer is the correct one and already exists. **Verdict: insufficient alone.** Its robust-extraction fallback is worth *folding into (a)* as the Phase-1 short-circuit test, not used as the primary fix.

##### (c) Reasoning-budget ladder (n_tokens caps at 512/1024/2048/4096) — measure the accuracy-vs-token curve
Run the same items at several reasoning caps to trace accuracy(R). This is *literally what LongCoT-Mini exists for* (the reasoning-compression premise) and directly serves the rescue-metric memory (which items get rescued by more tokens).
- **Pros:** produces the benchmark's headline signal; cheap to add once (a) exists (re-invoke per rung).
- **Cons:** a **bare** cap-ladder inherits mode 2 — at every rung an unfinished item has no marker → 0, conflating "ran out of budget" with "got it wrong". **Verdict: keep as the experimental structure, but build it ON TOP of (a)** so each rung = free-reasoning-capped-at-R + forced-answer terminal turn. That disentangles budget from marker-presence and yields a true accuracy(R) curve.

##### Chosen design
**Two-phase forced-final-answer generation (a), with (b)'s robust extractor as the Phase-1 short-circuit, deployed over a reasoning-budget ladder (c).** Scoring is the existing deterministic `structural_exact_match` (`LongCoTMiniAdapter.compute_score_for_result` via `score_longcot_run.py`) — unchanged, no judge, canary reported separately.

---

#### 4. Protocol specification (`bulk-inference.longcot-mini-calibration.v2`)

**Per item, per reasoning-budget rung `R`:**
1. **Phase 1 (free CoT):** `POST /v1/chat/completions`, `messages=[user(dataset_prompt)]` (the dataset prompt already ends with the `solution = <value>` format instruction via `SOLUTION_FORMAT_INSTRUCTION`; **no** `concise_solution` system prompt, **no** grammar), `max_tokens=R`, `temperature=0.6`, `seed=42`, `enable_thinking=false`. Record `text1`, `reasoning_tokens = usage.completion_tokens`.
2. **Short-circuit (B):** if `re.search(r"solution\s*=\s*", text1, re.I)` matches → `response=text1`, `phase2_used=false`. No second call.
3. **Phase 2 (forced final line):** only if no marker in `text1`. `messages=[user(dataset_prompt), assistant(text1), user("Output ONLY your final answer now, as a single line, exactly: solution = <value>")]`, `grammar = 'root ::= "solution = " ([^\n])+ "\n"?'`, `max_tokens=64`, `temperature=0.6`, `seed=42`. Record `text2`, `final_answer_tokens`. Set `response = text1.rstrip() + "\n" + text2.strip()` so the scorer's **last-marker** anchor lands on the forced line while the reasoning stays in the row.
4. **Score:** existing deterministic structural scorer over `response`. Canary-leak detection unchanged (reported separately; never folded into pass/fail).

**Reference budget** (non-saturation gate + full calibration run): `R = 4096` (2× the mode-2 truncation point). **Ladder rungs** (follow-on curve): `R ∈ {512, 1024, 2048, 4096}` — brackets the truncation regime; low rungs quantify how much the forced-answer path rescues vs. finished reasoning.

**Arms / roles / n / seed / scoring:**
- **Roles:** `frontdoor` and `worker_general` (v7 quarter stack; each role fans across its 4 CPU quarter ports, one role at a time — unchanged from the entry).
- **Arms:** the reasoning-budget rungs (each `R` is an arm). The probe and the reference full run use the single arm `R=4096`; the ladder run sweeps all four.
- **n:** full = **402 scorable rows** (chemistry 100 + chess 100 + cs 100 + math 102; the 105 null-gold `logic` rows stay excluded). Probe = **30** stratified rows (below).
- **seed:** 42 (production sampling; temp 0.6). *New* — must be added to the payload (runner SPEC §6).
- **scoring:** `structural_exact_match`, deterministic, no judge; `score_longcot_run.py` + `LongCoTMiniAdapter`. Report per-domain accuracy, canary-leak count (separately), and — new — mean `reasoning_tokens` and `phase2_used` rate per role/arm.

##### Non-saturation acceptance test (30-question probe, gates the full run)
- **Probe set:** deterministic — first ~7–8 rows per domain by sorted `question_id` (chemistry/chess/cs/math ≈ 8/8/7/7 = 30), reproducible because the adapter sorts by `question_id`. Expose as a `--limit-per-domain`/explicit-id list in the runner SPEC, or a curated `--probe-ids` file; do **not** use a random slice.
- **Arm:** `frontdoor` only (fastest role), two-phase, `R=4096`.
- **Accept (proceed to full run) iff** overall probe accuracy is **strictly between ~10% and 90%** (i.e. `3 ≤ correct ≤ 27` of 30) — neither floor (~0%) nor ceiling (>90%). Marker presence must be ~100% (two-phase guarantees it); if any row still lacks a marker, that's a runner bug — fix before the full run.
- **Escalation:**
  - **Floor at R=4096** (< ~10%): re-probe at `R=8192`. If still floor, the conclusion is that the "easy" items exceed a practical reasoning budget on this stack — record as an OBSERVATION (`INFRA/marginal`: budget-bound floor, *not* a capability signal); do **not** flip K-LCM-1 as "discriminative".
  - **Ceiling (> 90%):** suite is saturated on this stack → entry fork `marginal` → `DONE_MARGINAL_OBS` (EV-9 saturation), record and stop.
  - **In-band:** proceed to the full 402-row reference run (both roles), then the ladder.

---

#### 5. Entry YAML change — SPEC block (for `20-eval-tower.yaml` → `RE-4-longcot-mini-calibration`)

*Spec only — do not hand-edit the live entry here; the loop owner applies it. Changes vs. the parked entry:*

- `execution.protocol_id`: `bulk-inference.longcot-mini-calibration.v1` → **`…v2`**.
- `execution.command`: **remove** `--prompt-mode concise_solution` and `--force-solution-grammar`; **add** `--prompt-mode standard --two-phase --reasoning-budget "${LONGCOT_MINI_REASONING_BUDGET:-4096}" --final-answer-max-tokens 64 --seed 42`; keep `--endpoint chat`, the two `--role-ports` lines, `--timeout`, `--summary-out`, and the existing `score_longcot_run.py` scoring loop unchanged. Drop `--max-tokens` (superseded by `--reasoning-budget` in two-phase mode). Proposed command core:

  ```
  .venv/bin/python scripts/benchmark/longcot_mini_stack_runner.py
    --run-id "${RUN_ID}"
    --role-ports frontdoor=8080,8180,8280,8380
    --role-ports worker_general=8082,8182,8282,8382
    --endpoint chat --prompt-mode standard
    --two-phase --reasoning-budget "${LONGCOT_MINI_REASONING_BUDGET:-4096}"
    --final-answer-max-tokens 64 --seed 42
    --timeout "${LONGCOT_MINI_TIMEOUT_S:-900}"
    --summary-out "${OUT_DIR}/stack_runner_summary.json"
  # …then the unchanged score_longcot_run.py loop over frontdoor_*/worker_general_* result files
  ```
  Probe invocation: same command + `--probe-ids probe30.txt` (or `--limit-per-domain 8`) and only `--role-ports frontdoor=…`. Ladder: re-invoke once per `R∈{512,1024,2048,4096}` with `--run-id …_R${R}`.
- `execution.est_wall_clock_h`: raise the ceiling — reference run ≈ prior 4h scale; the 4-rung ladder ≈ up to ~4× on the truncating tail (short-circuit reduces it when Phase-1 markers appear early). Set `est_wall_clock_h: 12.0`, keep `timeout_s` generous.
- `outcomes.gate_table`: **prepend a non-saturation *probe* gate** — "30-q frontdoor probe at R=4096 yields overall accuracy in (10%,90%) with ~100% marker presence" as the precondition to the existing gate. Keep the existing `pass/marginal/fail/infra/ambiguous` fork; add to `pass.action`: "record the accuracy-vs-reasoning-budget curve (R∈{512,1024,2048,4096}) for the reasoning-compression premise." Keep `fail.rule` = "scoring is nondeterministic / requires a judge / harness error" (unchanged — scoring is still judge-free).
- `notes`: append one line — "v2 protocol: two-phase (free CoT → forced `solution=` terminal turn), deterministic structural scoring; supersedes the v1 answer-only-grammar protocol that floor-saturated (frontdoor 0/402, worker_general 0/307)."
- `ledger.journal_quarantine_rule`: already records `reasoning_token_count` — keep; add `phase2_used_rate` and `reasoning_budget_R` to the recorded fields.

---

#### 6. Runner code-change SPEC (`scripts/benchmark/longcot_mini_stack_runner.py`)

Structural change → **implement in a follow-on pass** (not in this design task). Precise spec:

**New CLI args (in `main`):** `--two-phase` (store_true), `--reasoning-budget` (int; when set with `--two-phase`, this is the Phase-1 cap and overrides `--max-tokens`), `--final-answer-max-tokens` (int, default 64), `--seed` (int, default 42), and one of `--probe-ids <file>` (newline-delimited `question_id`s) or `--limit-per-domain <int>` for the stratified probe. Thread `seed`/`two_phase`/budgets/`final_answer_max_tokens` into `run_role` → `_run_question`.

**`_run_question` (or a new `_run_question_two_phase`):**
1. Add `"seed": seed` to **every** payload (also fixes the standard/single-phase path's reproducibility gap).
2. Phase 1: current chat call with `max_tokens = reasoning_budget`, **no** grammar, `prompt_mode=standard` (dataset prompt unchanged), `enable_thinking=false`. Capture `text1`, `usage1`.
3. Marker test: `bool(re.search(r"solution\s*=\s*", text1, re.I))`. If present → `response=text1`, `phase2_used=False`, `reasoning_tokens=usage1.completion_tokens`, `final_answer_tokens=0`.
4. Else Phase 2: second chat call, `messages=[user(prompt), assistant(text1), user(FINAL_ANSWER_INSTRUCTION)]`, `grammar=SOLUTION_MARKER_GRAMMAR`, `max_tokens=final_answer_max_tokens`, same `temperature`/`seed`. `response = text1.rstrip() + "\n" + text2.strip()`, `phase2_used=True`, `final_answer_tokens=usage2.completion_tokens`. Define `FINAL_ANSWER_INSTRUCTION = "Output ONLY your final answer now, as a single line, exactly: solution = <value>"`.
5. Row additions: `reasoning_tokens`, `final_answer_tokens`, `phase2_used`, `reasoning_budget`, `text1_len`; keep existing `completion_tokens`/`tokens_per_second` semantics (set `completion_tokens = reasoning_tokens + final_answer_tokens`).

**Probe selection (in `main`, after `load_suite`):** if `--probe-ids`, filter `questions` to that id set; elif `--limit-per-domain N`, group by `question.metadata` domain (available via the adapter's `scoring_config`/`metadata`) and take the first `N` per domain by sorted `question_id`. Deterministic, no sampling.

**Summary additions:** `two_phase`, `reasoning_budget`, `final_answer_max_tokens`, `seed`, and per-role `phase2_used_rate` + `mean_reasoning_tokens`.

**Scorer:** unchanged. `LongCoTMiniAdapter.compute_score_for_result` already anchors on the **last** `solution =` (the B7/SCORE-03 final-answer-region behavior) and canonicalizes JSON/SMILES/FEN — the forced Phase-2 line becomes that last marker. *(Optional belt-and-suspenders, not required since two-phase guarantees a marker: a `no_solution_marker` scorer fallback to `\boxed{}` / last-line, aligned to B7 SCORE-03. Leave off the primary path to keep the ratified pattern intact.)*

**Tests to add** (mirror existing `test_*` siblings; no live inference): monkeypatch the HTTP call to return (i) a Phase-1 text WITH a marker → asserts 1 call, `phase2_used=False`; (ii) Phase-1 WITHOUT a marker → asserts 2 calls, grammar present on the 2nd, `response` ends with the forced line, scorer extracts it; (iii) `seed` present in every payload; (iv) `--limit-per-domain`/`--probe-ids` yields the deterministic 30-row stratified set.

---

#### 7. Probe → full-run sequence

- [x] **RE-4.0 — implement runner v2** ✅ 2026-07-21 (research `9323213d`: two-phase + seed + token accounting + probe selection; 7 tests; v1 byte-identical) (follow-on pass): apply §6 to `longcot_mini_stack_runner.py` + add the four tests; run the new unit tests (no inference). Land on the research repo.
- [x] **RE-4.1 — apply entry v2 spec** ✅ 2026-07-21 (protocol_id v2, two-phase command, probe gate prepended, est 12h; recompiled) (§5) to `20-eval-tower.yaml` (loop owner; recompile the batch entry). Protocol id → `…v2`.
- [ ] **RE-4.2 — non-saturation probe** (operator quiet-window, current v8 topology re-attested, autopilot stopped): frontdoor-only, two-phase, `R=4096`, 30 stratified rows. Score with `score_longcot_run.py`. **Gate:** overall accuracy ∈ (10%, 90%) AND marker presence ~100%. If floor → re-probe `R=8192` (§4 escalation); if ceiling → `DONE_MARGINAL_OBS`, stop.
- [ ] **RE-4.3 — full reference run** (only if RE-4.2 in-band): both roles, two-phase, `R=4096`, all 402 rows. Record per-model deterministic accuracy vs. the 90% saturation line, per-domain, canary-leak count (separately), mean reasoning tokens, `phase2_used` rate. Apply the existing entry gate fork. Absorbs K-LCM-1 and RE-4.5: this is the LongCoT-Mini calibration run (~500 easy deterministic long-horizon items, no LLM judge); on completion package artifacts to coordination/inference-batch/bundles/RE-4/ and write the terminal ledger row (DONE_PASS / DONE_MARGINAL_OBS per the fork).
- **[declined: ws58 2026-11-03 content-review: duplicate of context-and-token-economy.md TB-1 / E-2 (accuracy-vs-budget curve with the rescue set); add the LongCoT-Mini suite there if a second suite is wanted]** **RE-4.4 — reasoning-budget ladder** (follow-on curve; the reasoning-compression signal): re-run the 402 rows at `R∈{512,1024,2048,4096}` (both roles). Emit accuracy(R) per role/domain and the **rescue set** (items wrong at low R, correct at high R) per `feedback_accuracy_token_tradeoff_rescue_metric`. Observation-grade.
- **[declined: ws58 2026-11-03 content-review: merged into RE-4.3 as its packaging step]** **RE-4.5 — package + ledger**: package artifacts to `coordination/inference-batch/bundles/RE-4/`; write the terminal ledger row (`DONE_PASS` / `DONE_MARGINAL_OBS` per the fork); flip `K-LCM-1` only on `DONE_PASS`. Update `handoffs/active/eval-tower-program.md` "RE-4 protocol repair" checkbox.
- [x] **RE-4 runner confidence/persistence parity** ✅ 2026-07-29 (research `0940e5f4`; 23 focused tests): incremental atomic per-question persistence verified; rows now emit `confidence=null`, `confidence_is_real=false`, `confidence_source=not_collected`; explicit infra failures are excluded from the deterministic quality denominator (REL-1). Coverage table: [`handoffs/completed/safetygate-rlvr-provenance-audit-2026-07-22.md`](../completed/safetygate-rlvr-provenance-audit-2026-07-22.md).

---

#### 8. Answer to the task's RETURN

- **Chosen design:** two-phase forced-final-answer generation (free CoT → grammar-forced `solution=` terminal turn *only when* Phase 1 didn't emit one), scored by the existing deterministic structural matcher, deployed over a reasoning-budget ladder {512,1024,2048,4096} with a `R=4096` reference. This gives bounded reasoning + deterministic extraction and produces the accuracy-vs-token curve the benchmark exists for.
- **Probe plan:** 30 stratified rows (8/8/7/7 chem/chess/cs/math by sorted id), frontdoor-only, R=4096, deterministic scorer; accept iff accuracy ∈ (10%,90%) with ~100% marker presence; escalate R→8192 on floor, mark saturated on ceiling.
- **Runner code changes needed:** **YES** (structural). SPEC in §6: `--two-phase`/`--reasoning-budget`/`--final-answer-max-tokens`/`--seed`/probe-selection flags, a Phase-1→Phase-2 conditional second turn, `seed` added to every payload (fixes a standing reproducibility gap), row/summary token accounting, and four monkeypatched unit tests. Scorer (`score_longcot_run.py` / `longcot_mini_adapter.py`) is unchanged. Per the task's "prefer spec-only if the change is structural," the runner was **not** edited by this design task.

## Track: scoring-infra-standardization
<!-- gate: none -->

> Folded from `handoffs/active/scoring-infra-standardization.md` @ `c4b6d1388716` on 2026-11-02 (BRF-T1-F2, route 1a, operator D1/D5; retired row EVL-42 → EVL-14). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Scoring Infrastructure Standardization + Tool-Use Eval Harness

**Scratch**: `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/` (MAIN review custody, KEEP); worktrees: `/mnt/raid0/llm/worktrees/ni08-evl42-root-recipe-20261007`, `/mnt/raid0/llm/worktrees/ni08-evl42-research-20261007` (pinned native custody); private proposals: `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/` (active worker, KEEP).

**Status (2026-07-24): STARTED — Phase 1a + 2a in progress (operator-approved "both, tracked").**
**Owner:** GPU-bench session (this one) for 1a/2a; **1c and 2b are production-touching / large and gated.**

#### Why this exists (the trigger)

The 2026-07-24 architect keep/drop analysis was nearly derailed by a **scorer artifact**: `gpqa_diamond` was
scored with a stale `extract_letter_answer` that dropped bare-letter answers, giving verbose **A4 15% false
parse-failures vs A1's 0%** — which manufactured a *significant* A1/A3 > A4 result that vanished (→ NULL) once
re-scored canonically (A4 gpqa 43.4→53.0%). Root cause is **fragmentation**: the stack has **~10+ independent
answer-scoring implementations**, each rolling its own extraction, each a latent copy of the same
verbose-penalty bug. Operator directive: *standardize scoring infra across the stack; you can't have
independent custom builds per sector.* Plus: there is **no runnable tool-use/coding eval harness**, which the
architect keep/drop decision actually needs (QA can't decide the architect's real job).

#### The fragmentation (audit 2026-07-24)

**Research repo:** `v7_quality_gate_runner` (canonical, tested — the one to promote) · `lib/scorer` (registry) ·
`score_benchmarks` · `score_aa_omniscience_run` · `xmas_function_axis_sweep` · `xmas_cheap_kill` ·
`score_with_claude` (judge) · `short_mk_voting` · adapter-local extractors (`_extract_gsm8k_answer`, …).
**Orchestrator:** `pipeline_monitor/model_grader.grade_answer` (eval-tower LLM-judge; `_extract_classification`) ·
**`api/services/memrl.score_completed_task` (autopilot RL reward path — HIGH RISK if it shares the bug)** ·
`proactive_delegation/rubric_review.grade_candidate` · `graph/answer_resolution.resolve_answer` (agentic flow;
already has bare-letter handling).

#### Phases

##### Track 1 — Scorer standardization
- [x] **1a. Canonical `answer_scoring` library (ADDITIVE, safe).** ✅ 2026-07-24 — DONE. Promoted v7's 15
      validated primitives verbatim into `scripts/benchmark/answer_scoring.py` (single source, module dep = `re`
      only; sympy/Fraction lazy); `v7_quality_gate_runner` imports + re-exports them (−331 lines duplication,
      public API unchanged, external importers intact). `test_answer_scoring.py` locks the bare-letter and
      truncated-boxed regressions. Research `bc33cb76`.
- [x] **1b. Migrate research consumers** to import the canonical lib; delete each duplicate extractor; test
      each. (score_benchmarks, lib/scorer, score_aa_omniscience, xmas_*, short_mk_voting, adapters.)
      ✅ 2026-08-12 (`auditor`, adjudicated closed **by exhaustion**): every migratable consumer IS
      migrated — 1b.1/1b.2 below, with tests — and mainC's 08-11 per-consumer pass proved each
      remaining candidate NOT a duplicate (mechanisms on record in the sub-bullets). Both claimed
      cross-reference comments verified landed at HEAD in git, not just on disk: research
      `answer_scoring.py` (four deltas) and orchestrator `scripts/benchmark/debug_scorer.py`
      (`f8eb36f7`). The one remaining unification candidate (`_extract_multiple_choice_letter`) is
      a gated SCORING CHANGE already tracked at **1c-fix (c)** — closing this row drops nothing.
      Reader hazard found while verifying: the research repo has an UNRELATED
      `scripts/benchmark/debug_scorer.py` (numeric/pattern scorer, no letter extraction) — the
      divergent extractor lives at the ORCHESTRATOR path of that same name.
  - **ADDITIVE PASS 2026-08-11 (`mainC`, operator-authorised: no deletions). Result: NO remaining
    consumer is a safe migration target, and each verdict is PROVEN per consumer, not assumed.**
    The two that genuinely were duplicates are already done as 1b.1/1b.2. Corrections to this row's
    own consumer list, which is partly stale: **`score_benchmarks` does not exist** under that name
    in either repo, and **`lib/scorer` is in `epyc-orchestrator`, not research** — so this list
    spans two repos and reads as if it spans one.
    - **`score_aa_omniscience_run.py` — NOT a duplicate.** Its `extract_answer` is tag-based and
      configurable (`<answer>…</answer>`), not letter extraction, and it feeds `token_f1` rather
      than a boolean match. Two concrete blockers to delegating it to canonical
      `extract_exact_answer`: canonical's single-pattern path compiles with **no flags**, so it
      loses `re.DOTALL` and would stop matching a multi-line `<answer>` block; and canonical falls
      back to the **whole stripped response** where AA falls back to the **last non-empty line** —
      which changes precision/recall/F1 on every unparsed response. This is the "AA configurable
      token-F1" the blast-radius warning named; the mechanism is now on record.
    - **`review_f1/scorer.py` — NOT a duplicate.** PR-finding scoring, different domain entirely.
    - **`debug_scorer._extract_multiple_choice_letter` (orchestrator) — NOT a duplicate, and this
      is the dangerous one.** It sits on the authority/sealed-capture path. It accepts **A-H** vs
      canonical **A-J**, has no `\boxed{}` handling, and — the systematic difference — its
      last-resort strategy returns the **last standalone letter unconditionally**, where canonical
      accepts a bare letter only when exactly ONE candidate exists. It is therefore
      **systematically more permissive: it scores answers canonical declines to parse.** Unifying
      them is a SCORING CHANGE requiring a re-score of the affected sealed captures, not a diff.
    - **`data/vision_mmmu_cutover_20260731/harness.py:88` — NOT a duplicate.** Its
      `extract_letter(text, options)` validates against the live option set (`if c in valid`);
      canonical takes no options and cannot.
    - **Landed additively** (comments only, zero behaviour change): both extractors now carry a
      cross-reference naming the other and enumerating the four deltas, so the next reader cannot
      mistake resemblance for equivalence. Research `answer_scoring.py`, orchestrator
      `debug_scorer.py`.
  - [x] **1b.1 short-m@k multiple-choice vote extraction** ✅ 2026-07-29 (research `53eb754c`; 11 focused tests): replaced its local multiple-choice regex cascade with canonical `extract_letter_answer`; preserves final-answer precedence and adds the verbose-final-line regression.
  - [x] **1b.2 X-MAS function-axis multiple-choice scoring** ✅ 2026-07-29 (research `5ed43e1e`; targeted scorer tests): replaced its local standalone-letter regex with canonical `extract_letter_answer`; preserved the runner's bespoke substring/rubric paths. The one-cell summary fixture now explicitly requests partial-summary mode, so the full module test file validates the intended partial-run behavior.
- [x] **1c-audit. Orchestrator scoring + tool-use audit (read-only, subagent).** ✅ 2026-07-24 — report:
      [`research/deep-dives/2026-07-24-autopilot-scoring-tooluse-audit.md`](../../research/deep-dives/2026-07-24-autopilot-scoring-tooluse-audit.md)
      (59 file:line citations). **Verdicts:** (Q1) **memrl reward NOT AFFECTED** — the live TD reward does zero
      regex answer-extraction (structural success flag + telemetry/prior cost terms; latency length-normalized);
      externally-injected eval rewards use the B7-hardened `debug_scorer` (bare-letter-safe). (Q2) judge-parse
      bug class present but **every affected path dormant or reward-decoupled** (`model_grader` has no callers;
      proactive-review gating flags declared off). (Q3) **tool use IS production-live** via the bespoke Python-REPL
      protocol (`TOOL()/CALL()/FINAL()`) — NOT llama-server native function calling; `ChatRequest.tools` is
      accepted-but-never-consumed (wired-but-dead). An architect tool-use eval can run through the orchestrator
      TODAY via `call_orchestrator_forced(force_role="architect_general", force_mode="repl")`. (Q4) 10 independent
      extraction impls inventoried. **No ⚠ production finding.**
- [ ] **1c-fix (PRODUCTION-TOUCHING, GATED — scoped by the audit).** (a) Vendor the canonical `answer_scoring`
      contract into the orchestrator + a **shared golden-corpus drift test** (data-only coupling, consistent with
      orchestrator→research being a DATA dependency).
      **(a) DONE ✅ 2026-08-12** (`auditor` B15, orchestrator `39ff247b`, accepted after re-running the drift
      suite): `answer_scoring_vendored.py` byte-verbatim from research @`9cc8db2d`, 15-row golden corpus with
      independently-executed verdicts, sha-pinned drift test (18/18; 71/71 pre-existing debug_scorer tests
      unaffected — purely additive, no consumer rewired). Three visible mutations all caught.
      **(c) DONE ✅ 2026-08-12** (`auditor` B15, evidence artifact
      [`artifacts/audit/debug-scorer-letter-inflation-quantification-20260812.md`](../../artifacts/audit/debug-scorer-letter-inflation-quantification-20260812.md),
      epyc-root `f13b8682`): over 122 persisted eval-tower rows (46 deduped), **debug_scorer scores
      +5.74pp raw / +4.35pp deduped higher than canonical**; ~3/4 of disagreements trace to the named
      unconditional Strategy-5 last-letter fallback (incl. a truncated non-answer credited via a stray
      letter). **NEW finding for the unification decision**: debug_scorer's Strategy-4 bold-letter
      handling (`**D**`) catches answers canonical's regex misses entirely — a real capability gap, not
      inflation; any unification must add it to canonical or lose it. debugbench (20) and
      livecodebench-family (22) rows verified 100% substring-scored — outside the letter path, flagged
      pending-oracle-rebuild. **(b) and (d) remain open** — (b) the 500-char review truncation, (d) the
      dead `ChatRequest.tools` decision. (b) Fix the latent verbose bias: `review_service.review()`
      truncates the candidate to **500 chars** before judging (`review_service.py:420`) feeding `all_approved` →
      memrl reward — dormant only while `parallel_execution`/`architect_delegation` stay off, and re-enterable via
      per-request `allow_delegation=True`. (c) `debug_scorer.py:269-272` last-standalone-letter fallback is a
      false-*POSITIVE* (score-inflation) risk vs the canonical lib — re-score a recent eval batch before/after
      consolidation to quantify. (d) Decide fate of dead `ChatRequest.tools` (consume or remove).
      **(b) DONE ✅ 2026-09-17** (orchestrator `9a7181f2`): the prefix cut is replaced by
      `ArchitectReviewService.condense_output()` — head 60% + tail 40% with an explicit marker naming the
      elided character count, so the reviewer sees the conclusion instead of an unfinished fragment, and the
      gap is legible as ours rather than the model's. Budget is config (`review_output_max_chars`, default
      4000); `quick_mode`'s silent `[:200]` now goes through the same helper. Prompt templates byte-identical.
      The site had drifted from `:420` to `:538` — anchor rot; the task TEXT resolved it. Cost established
      before the fix: the old cut was mid-record with no signal to the reviewer, and nothing downstream
      depended on the cap (all three callers consume only the `ArchitectReview`). 8 new tests, verified
      failing pre-change.
      **(d) DONE ✅ 2026-09-17** (same commit) — **deprecated, deliberately not removed.** `ChatRequest.tools`
      / `tool_choice` are confirmed dead (the only `request.tools` consumers read `OpenAIChatRequest`, and no
      client sends them to `/chat`), but they are part of a PUBLISHED `/chat` schema and the model's
      `extra='ignore'` would swallow them silently on removal — identical runtime, worse visibility. They are
      now marked `deprecated` in the schema, the description no longer falsely claims REPL `CALL()` exposure,
      and `/chat` logs a warning when a caller sets them. Removal becomes safe once the log shows no callers.
      6 new tests.
- [x] **1d. Pin a runnable test environment for the research repo's eval-scorer tests.** Found 2026-08-12
      (suite-retirement lane): `test_score_with_claude.py` uses pytest fixtures with no stdlib fallback, but
      NO pytest exists in system python, `.venv-exec`, or user site — a stale `__pycache__` pyc proves pytest
      9.1.1 ran once and vanished. The tests were unrunnable as found; both auditor lanes verified via
      ad-hoc scratch venvs (`/workspace/tmp/effibench-venv`). Fix = a pinned dev-requirements (or repo venv)
      that `--check`-style CI or session-init can assert, so "tests pass" claims are reproducible.
      ✅ 2026-09-24 — research `pyproject.toml` gains a `test` extra pinning `pytest==9.1.1`; README
      "Running Tests" installs it into a gitignored `.venv-test` (never `.venv-exec`) and runs the four scorer
      suites (`test_score_with_claude`, `test_debug_scorer`, `test_niah_scorer`, `test_architect_bench_rescore`):
      52 passed. research `6cf4a076`..`cbb12fc7`. A whole-directory `scripts/benchmark/` run still has 4
      collection errors (`test_aa_omniscience_manifest`, `test_m12_review_fixes`, `test_rope_position_probe`,
      `tests/test_run_benchmark_suite_selection`) — outside this scorer scope.
- [x] **1e. Fix the 4 collection errors in research `scripts/benchmark/`** (`test_aa_omniscience_manifest`,
      `test_m12_review_fixes`, `test_rope_position_probe`, `tests/test_run_benchmark_suite_selection`) so the
      whole directory runs under the pinned `[test]` extra, not just the four scorer suites. Found 2026-09-24 (1d).
  ✅ 2026-10-05 — pinned pytest 9.1.1 with declared benchmark/test extras collects all 2,286 cases without errors in run `37282435460`, including the four named modules (4/17/3/3 cases). This closes collection defects on current source; whole-directory execution/passage is not claimed. See [NI11 evidence](../../progress/2026-10/2026-10-05-ni11-api-order-and-benchmark-collection-validation.md).

##### Track 2 — Tool-use / coding eval harness
- [x] **2a-i. `datasets` + code-execution scorer scaffold.** ✅ 2026-07-24 — DONE. Installed the `benchmark`
      extra (`datasets 5.0.0`; LiveCodeBench loads 2360 items). Built `code_exec_scorer.py` (`extract_code` +
      `score_code`) running generated code vs stdin/stdout or assert-style tests in an isolated subprocess
      (fresh temp cwd, RLIMIT_CPU/AS/CORE/NPROC, wall timeout, minimal env); smoke-tested correct/wrong/runaway/
      functional. Replaces the adapter's placeholder `substring "def "` check. Research `e12149b9`.
- [x] **2a-ii. Wire it to the suites.** ✅ 2026-07-24 — `code_execution` dispatch added to canonical
      `score_response` (functional check() / unittest / stdin-stdout styles); HumanEval oracle validated
      **164/164 canonicals**; BCB unittest oracle validated **90/148** (drops = long-tail deps/env, equal for
      all arms); real-LCB stdin/stdout materialized from the cached contest dataset (the shipped adapter's
      "code_execution" was a stub — commented-out asserts). Research `5b7a1696`, `1d490c26`. Remaining
      sub-item → **harden isolation (unshare/nsjail/container)** before at-scale/untrusted runs (scaffold is
      trusted-code only) — now tracked as its own checkbox **2a-iv** below (was prose here, invisible to the
      dashboard progress metric).
- [x] **2a-iii. Bound the scorer's descendant processes — landed as process-group kill + docstring
      correction (NOT `RLIMIT_NPROC`).** ✅ 2026-07-29 — `scripts/benchmark/code_exec_scorer.py`
      (**`epyc-inference-research`**, not the orchestrator). Two changes: (a) `start_new_session=True` +
      `os.killpg(os.getpgid(proc.pid), SIGKILL)` on timeout, closing a **confirmed orphan leak** —
      `subprocess.run`'s timeout path killed only the direct child, so anything the scored code spawned
      survived it; (b) the module docstring, which **claimed `RLIMIT_NPROC` was set when it never was**, now
      states why that mechanism is wrong here. **`RLIMIT_NPROC` deliberately NOT implemented**: it is enforced
      **per real UID, not per process tree**, and this host runs ~9,534 threads under uid 1000 (5,688 of them
      llama-server) — any per-scorer cap would fail the child's *first* fork under normal fleet load, and would
      fail NONDETERMINISTICALLY as load varies, turning the scorer into an instrument whose results track how
      busy the box is. Verified **by execution: 9/9 checks**, including the real orphan case.
- [ ] **2a-iii-followon. Bound process/thread COUNT via cgroup v2 `pids.max`** — the correct mechanism (counts
      only the scorer's own subtree, unaffected by co-tenants). Verified available on this host: `pids`
      controller present, child cgroup creatable; needs `+pids` in `cgroup.subtree_control`. Pair it with
      `cpuset.cpus`/`memory.max` pinned to the eval quadrant (cpuset 112-119) so the whole bound is enforced at
      the cgroup rather than per-process. Concrete blow-up this bounds: numpy sizes its pool to nproc (192 here).
- [ ] **2a-iv. Harden isolation** — wrap `code_exec_scorer.py` in bubblewrap (`--unshare-net`, read-only root,
      tmpfs `/tmp`). `unshare` + unprivileged userns are already available; `bwrap` is one apt package. MicroVM
      substrate (AgentENV) is recorded EVALUATED-AND-DECLINED: cannot run here (no kvm group, ublk unloaded) and
      its 2 vCPU × 1 GiB default with no cpuset knob would delete the fail-closed cpuset-112-119 guarantee we
      attest.
- [x] **2b. Coding ladder COMPLETE — all four rungs, all arms.** ✅ 2026-07-24. HumanEval n=164 (A4 95.7 /
      A1 95.1 / A3 92.1, tied/saturated); LCB-hard n=53 (A4 54.7 / A1 47.2 / A3 45.3, A4 +9.4pp ns);
      BCB-hard n=90 (A3 31.1 / A4 27.8 / A1 26.7, ns); **SWE-oracle n=40 (A3 52.5 / A1 37.5 / A4 35.0 —
      A3 vs A4 +17.5pp p=0.039 SIG uncorrected, disc 8/1)**. **Pooled 4-rung n=347: 64.8 / 64.6 / 63.4 — dead
      tied (all p≥0.53).** Read: aggregate coding TIED on discriminative suites (real null, not saturation);
      skill texture = A4 contest-algorithmics, **A3 realistic tiers (library-API + repo bug-fix)**; patch
      discipline A1 34 > A3 32 > A4 27 non-empty. ~1,050 GPU inferences, 0 request errors. Artifacts
      `architect-code-eval-20260724/` (pq.jsonl + predictions + harness reports, re-scorable).
- [x] **2b-swe. SWE-bench Verified oracle rung DONE end-to-end.** ✅ 2026-07-24 — gold-calibration 40/40;
      oracle patch-gen (SEARCH/REPLACE → diff conversion) + official docker eval for all three arms; results
      in 2b above. Harness caveat for paired stats: empty-patch instances are absent from the report's
      resolved/unresolved lists — score over the FULL slice (empty = fail) or the pairing silently shrinks.
- [x] **2b-confirm. SWE A3-vs-A4 expansion (SEQUENCED AFTER Laguna, operator 2026-07-24).** Expand the
      gold-calibrated slice 40→150+ (docker gold-validation CPU-side), rerun A3+A4 only → decision-grade
      confirmation of the +17.5pp p=0.039 (uncorrected, ~12 comparisons today — needs confirmation). [declined: operator 2026-11-03 model-audit: A3 (Qwen3.6-27B) deleted; powered A3-vs-A4 confirmation SHELVED in model-evaluation-queue; sequenced after the retired Laguna box]
- [x] **2b-laguna. Fold Laguna-S-2.1 into the candidate process — ⛔ BLOCKED (operator 2026-07-24): needs a
      small llama.cpp kernel upgrade first (inference-research work, OPERATOR-OWNED — do NOT start bring-up
      until the operator green-lights; experimental-branch workflow applies per CLAUDE.md).** On disk:
      `models/Laguna-S-2.1-GGUF/` — UD-IQ2_M **34.7GB (fits MI210)**, Q4_K_M 70GB (CPU-side), and a 2.1GB
      **DFlash BF16 drafter** (own spec-dec path!). Steps: (1) runbook §3 config discovery — bring-up, MTP/
      DFlash spec-dec sweep, optimal serving block → registry; (2) **SWE-oracle 40-slice first** (the
      architect-relevant rung); (3) LCB-hard, then decide BCB-hard; full runbook later if warranted. [declined: operator 2026-11-03 model-audit: Laguna-S-2.1 weights not on disk; Laguna evaluated and sealed in model-evaluation-queue L-IQ2; no Laguna role]
- [x] **2b-agentic-build. Agentic SWE harness BUILT + mock-tested (subagent).** ✅ 2026-07-24 — research
      `d476b318`: `scripts/benchmark/agentic_swe_harness.py` + tests (16/16 green, verified independently).
      Multi-turn bash/edit(SR)/done loop in the instance container, NO-oracle prompting, turn/wall/cmd
      budgets, history compaction (150k chars), tracked-only git-diff patch extraction, in-container
      timeouts, resume-safe predictions consumable by the official harness. Bonus: caught a latent
      `lstrip("ab/")` path-mangling bug in `convert_sr_to_patch.py` (fixed; 0 shipped-run impact, verified).
- [x] **2b-agentic-0. Reset `/testbed` between trials — silent cross-trial contamination path closed.**
      ✅ 2026-07-29 — `DockerEnv.reset_testbed(base_commit)` in `scripts/benchmark/agentic_swe_harness.py`
      (**`epyc-inference-research`**, not the orchestrator), called **fail-closed at the top of `run_instance`**
      (on error: status `testbed_reset_failed`, zero turns, empty patch — a silently-failed reset is exactly
      the contamination this fixes). Reset runs **before** each trial, so a crashed trial cannot poison its
      successor. Command is `git reset --hard <base_commit> && git clean -fd` — **deliberate deviation from
      `-fdx`**: `-x` also deletes IGNORED files, which in a SWE-bench testbed includes the `.egg-info`/build
      artifacts left by `pip install -e .`; deleting those breaks imports and would manufacture false failures.
      `reset --hard` (not `checkout -- .`) so an agent *commit* is undone too. Verified **by execution: 14/14
      checks**, including that the ignored artifact survives and that an agent commit is rolled back.
- **[declined: ws58 2026-11-03 content-review: merged into the smoke (its own text says the two were always coupled)]** **2b-agentic-0-verify. Re-verify the clean-at-base assumption (2b-agentic-smoke, below) now that the
      reset exists** — the two were always coupled: confirm `git status --porcelain` is empty inside the
      container at the start of trial 2 when the same instance runs twice in one sweep.
- [ ] **2b-agentic-smoke. LIVE smoke of the agentic harness (parent session, GPU-gated).** One instance Step 0 (absorbs 2b-agentic-0-verify): confirm `git status --porcelain` is empty inside the container at the start of trial 2 when one instance runs twice. Cheaper first rung (from 2b-agentic): run a tool-use eval through the orchestrator's live REPL loop (`call_orchestrator_forced(force_role="architect_general", force_mode="repl")`) before any per-instance repo-env build. The full SWE-bench agentic harness is owned by mi210-serving-program.md P5-1/P5-2.
      (e.g. django__django-11099 container from the cached gold images) + one served arm via the provided
      CLI (`--dry-run` first); verify /testbed clean-at-base assumption; then a 10-instance pilot before any
      3-arm agentic comparison. Waits for GPU free post-Laguna-kernel work.
      Orchestrator-REPL variant (audit Q3) remains the production-path option. (re-scoped 2026-11-03 from Laguna-kernel dependency: Laguna retired; served arm now Qwen3.8-27B)
- [x] **2b-agentic-capture. Lossless trajectory evidence + live integrity gate.** ✅ 2026-07-26 — Full
      assistant replies and pre-context-truncation tool observations are now always persisted with UTF-8
      sizes and SHA-256 identities. Per-turn live status exposes anomalies; a companion `capture-status.json`
      binds every patch, trajectory, and runner source. Over-budget/legacy/mismatched evidence remains
      observable but exits nonzero and is scoring-ineligible; ordinary resume fails closed. The default
      research smoke targets cover the contract (`make test`: 43 passed; `make lint`: clean).
- [ ] **2c. Eval-tower pool registration decision package (OPERATOR).** Once LCB-hard/BCB-hard/SWE-oracle
      prove discriminative: present options+tradeoffs for registering them into the E7 eval pool (era-sensitive
      instrument change — new-era row vs supplementary-pool vs bench-only). Operator asked for the package
      when the time comes; do NOT register unilaterally.
- [ ] **2d. LCB contamination-window refresh.** The cached LCB snapshot spans 2023-05→2024-03 (likely inside
      these models' training windows). Pull a newer LiveCodeBench release (v5/v6 date-window) for a
      post-cutoff hard slice; re-validate oracle; compare to the current window's scores (a large drop =
      contamination signal on the old window).
- [x] **2e. Runbook: replace the P2 placeholder with the built coding ladder** ✅ 2026-07-29 —
      [`architect-bench-runbook.md`](../../docs/reference/architect-bench-runbook.md) now distinguishes
      HumanEval validation → LCB-hard → BCB-hard → SWE-oracle → agentic, retains canonical/gold gates, and
      separates built harnesses from the still operator-gated live agentic run. It also records model-major,
      one-at-a-time GPU residency with current SMT-sibling affinity, so host placement cannot be misread as
      a model result.
      *(Declined as separate tasks: model-major driver restructure — captured in
      [[feedback_mi210_host_threads_smt_siblings]] and folds into 2e; promoting the SWE scripts from
      artifacts/ into scripts/benchmark/ — already covered by the standing runbook §10 promotion task.)*
- **[declined: ws58 2026-11-03 content-review: duplicate — the SWE-bench agentic harness build is mi210-serving-program.md P5-1/P5-2; the cheaper REPL-loop rung is now in 2b-agentic-smoke]** **2b-agentic. SWE-bench/tau-bench multi-turn harness** for true planning/tool-use. Audit Q3 unblocks a
      cheaper first rung: run a tool-use eval **through the orchestrator's live REPL loop**
      (`call_orchestrator_forced(force_role="architect_general", force_mode="repl")`) — exercises the production
      tool path with no new harness; full SWE-bench (per-instance repo envs) remains the big build.
- [x] **2b-agentic-1. Pin and verify the tool-call parser before any Jackrong-family bench.** ✅ 2026-07-29 —
      `epyc-orchestrator` commit `22c476dd` parses direct JSON inside `<tool_call>` and preserves the existing
      OpenAI-array path. Separate fixtures pin the v2 (6,994 B) and Coder (4,718 B) wire contract to executable
      `CALL()` code; `134` prompt-builder tests and ruff pass. Qwen XML remains deliberately unparsed, so a
      cross-arm parse failure cannot silently become a quality gap ([[feedback_parse_failure_rate_is_a_scoring_artifact]]).
- [x] **2b-swe-hygiene. Adopt the six-point SWE-bench disclosure standard** ✅ 2026-07-29 — harness identity + version pinned;
      the **model-harness pair** as the unit of report; denominator + split; dataset mutation disclosed;
      n/reps/seeds; contamination posture. Applied below to intake-916/917/924. No external SWE-bench figure
      gates a decision without all six.

##### SWE-bench disclosure application — intake-916 / 917 / 924 (2026-07-29)

External coding numbers are observations only. `unknown` is a required disclosure result, not permission
to infer a favorable value; a row with any unresolved field cannot enter an EPYC comparison or decision gate.

| Intake / reported result | Harness identity + model-harness unit | Denominator / split | Dataset mutation | n / reps / seeds | Contamination posture / disposition |
|---|---|---|---|---|---|
| **916** — proprietary KAT-Coder-V2.5, SWE-Bench Pro `65.2` | Paper identifies Claude Code as both training and evaluation harness, but does not pin an evaluable version/config; report only as proprietary KAT-Coder-V2.5 × unspecified vendor harness. | Pro benchmark denominator/split not disclosed in the result row. | Not disclosed. | Not disclosed. | Vendor-run, no independent reproduction found; never attach this result to the downloadable Dev weights or use it for a role decision. |
| **917** — KAT-Coder-V2.5-Dev, Verified `69.40` | `KAT-Coder-V2.5-Dev × claude_code@2.1.195` (pin recorded). | Full/split detail not supplied with the card result. | Not disclosed. | Card says each model/eval set ran once: `n=1`, no repetitions/variance/seeds. | Vendor in-house result; no independent evaluation found. The reported gain is below the vendor-vs-vendor baseline gap, so it is hypothesis-grade only. |
| **924** — Qwopus Fusion, astropy `7/15`; parent claims also cite `152/202` and `335/500` | Fusion harness/version not disclosed; parent figures are distinct parent-model × undisclosed-harness results and must not be inherited by Fusion. | Fusion is an astropy-only `15`-item slice; parent rows use incompatible `202`-slice and full-`500` denominators. | Selection method for the 202 slice not disclosed. | No reproducible n/reps/seeds; the `7/15` is a single small slice. | Self-report only; the benched Q4 artifact is incomplete and non-MTP, while the usable MTP Q5 artifact is unbenched. No Fusion comparison claim is admissible. |

##### Phase 3 — external infrastructure prior art (2026-08-18, intake-1160 metaharness, dive-verified)

Prior art only. **Nothing is imported**, and the package publishes no measurements, so no number from
it can ever be cited.

- **[declined: ws58 2026-11-03 content-review: curiosity — our sandboxed eval arms call local llama-server endpoints that hold no provider secrets; no failure names per-runner secret handling as a problem]** **3a. Host-side auth gateway for sandboxed eval fan-out.** Trials run in containers holding
  **no credentials**: a generated `models.yml` points every provider `baseUrl` at a host-side gateway
  that resolves secrets outside the sandbox, and a cached dependency tree plus mounted runtime means
  trial setup needs zero outbound network. Directly applicable to our sandboxed eval fan-out, where
  secret handling is currently per-runner.
- **[declined: ws58 2026-11-03 content-review: a note ("do NOT import"), not a task]** **3b. Adapter-normalized experiment/run/trace as prior art.** One schema, SQLite store, REST/SSE,
  per-benchmark adapters normalizing progress/scores/tokens/costs/traces while benchmark-native
  artifacts stay on disk. Note as an external instance of this handoff's own problem. **Do NOT import,
  and do NOT treat an external convention as a reason to change ours.**

#### Reporting
Update this handoff + progress after each phase. Per-phase commits. 1c and 2b do not start without an operator
gate (production reward path / agentic build). See [[project_architect_model_selection_bench]],
[`architect-bench-runbook.md`](../../docs/reference/architect-bench-runbook.md) §7 (pre-verdict scoring gate),
[[feedback_parse_failure_rate_is_a_scoring_artifact]].


#### 2026-07-25 — intake Stage-2a dive: ordered-subsequence verifier (BOTH metrics)

_Via `/research-intake` Stage-2 2026-07-25; see [`intake-derived-work-2026-07-25.md`](../completed/frontier-lab-automation.md)._

- [x] Add an **`ordered_subsequence`** verifier to the canonical `answer_scoring` library: given an ordered concept list, lemmatize the completion and check all concepts appear as an ordered subsequence; return graded coverage in [0,1] plus a binary all-in-order flag. Must land in the canonical library — not an 11th bespoke scorer — with unit tests for lemma-boundary and repeated-concept cases. ✅ 2026-08-12 (verified by `mainB` subagent; **the work landed under its other tracking id and these rows were never ticked** — research `9cc8db2d`, filed as ID-7 in [`intake-derived-work-2026-07-25.md:86`](../completed/frontier-lab-automation.md), which IS closed). `score_ordered_subsequence` at `scripts/benchmark/answer_scoring.py:383` in the canonical library, not a new scorer; returns `coverage`, `coverage_in_order`, `all_in_order`, `missing`, `lemmatized`. Re-derived rather than inherited: `git log -S score_ordered_subsequence` → one commit, working tree clean against it, `pytest scripts/benchmark/test_answer_scoring.py` → **12 passed**. Lemma-boundary case is `test_ordered_subsequence_multiword_contiguous` (hyphen/split forms), repeated-concept case is `test_ordered_subsequence_duplicates_need_repeats`. Empty concept list raises rather than scoring 1.0.
  - [x] **Dependency decision (2026-07-29):** the research benchmark environment has no `spacy` installation or pinned English model, while the canonical scorer intentionally has only stdlib import dependencies. Do not silently substitute stemming for the specified lemmatization. Choose either a pinned, reproducible lemmatizer dependency with model/data provenance, or explicitly amend this task to a documented dependency-free lexical verifier; then add the helper without changing the critical generic `score_response()` dispatcher (GitNexus: 60 exact upstream impacts, CRITICAL). ✅ 2026-08-12 — **resolved as the second horn, dependency-free by default.** `_lemma_tokens` tries spaCy lazily and falls back to `[a-z0-9]+` surface matching, with the choice reported per call as `lemmatized: bool` rather than hidden; the fallback direction is conservative (it can MISS an inflected variant, never false-match), so an unlemmatized environment under-scores rather than inflating. No stemming substitution. **Deviation from this row, stated rather than buried**: it did touch `score_response()` — but additively, a new `if scoring_method == "ordered_subsequence"` arm reachable only by that method, so the 60 upstream callers cannot take the new branch. Pinned by `test_ordered_subsequence_dispatch_binary_arm` and by the full file staying 12/12 green.
- [x] **Implement BOTH Ordered Rate and Coverage-with-order, not one.** An earlier note called them redundant; the dive **overturned** that — they diverge by up to **26.5 pts** on weak models (Qwen2-0.5B 30.84 vs 57.34; Phi3-mini 49.54 vs 62.04) and converge only at 405B, so both carry distinct signal exactly in the small/quantized regime we care about. ✅ 2026-08-12 — both shipped and distinguishable: `all_in_order` is the paper's Ordered Rate (binary), `coverage_in_order` is Coverage-with-order (graded, longest in-order chain by DP over all occurrence positions so an early out-of-order mention cannot shadow a later in-order one), and order-blind `coverage` is carried alongside as the third. `test_ordered_subsequence_basic_directions` pins the divergence direction: all concepts present but out of order holds `coverage` at 1.0 while the ordered metrics drop.
- [ ] Source is **ACL 2025 Main and an Outstanding Paper** — **Add an ordered-subsequence verifier to the `instruction_precision` suite** (ACL 2025 Outstanding Paper, arXiv 2506.15629). First count which of the 43 items specify an order; if >= 5 do, add a sequence verifier for them (record the spaCy-lemmatization fragility as a known class, same as the substring/comma brittleness) and re-score; if fewer, record the count and close. Do not cite the paper's 4-bit-vs-API leaderboard as quant-quality evidence.

#### 2026-08-03 — intake Stage-2b: audit our own eval paths for HARNESS-LEVEL answer leakage

_Via `/research-intake` (intake-980#record, plus intake-977). Source-scope correction 2026-10-06: harness-origin answer leaks require infrastructure audits, but their trace-visible adoption can also be detected by an agent-side monitor. Monitoring alone is not a sufficient general guarantee (intake-980#03); preserve the infrastructure obligation without claiming categorical monitor invisibility._

Paper §3.3 reports over 28 submissions across 9 benchmarks and distinguishes harness-level from task-level cheating; these artifact-specific counts do not establish an exhaustive benchmark-name list. Reviewer/monitor traces can expose behavior in either class when the relevant adoption is visible:

- **Harness-level** (developer or scaffold; infrastructure audits required, not categorically monitor-invisible): verifier injection ·
  answer-key injection · **solution injection** (e.g. an `AGENTS.md` in the working tree that contains
  the solutions).
- **Task-level** (agent-initiated, what a monitor can see): online solution retrieval · mining
  version-control history for the fix · verifier prompt injection · hardcoded test answers ·
  **simulating rather than executing**.

The audit found the **top 3 submissions on one benchmark were all cheating**, and 31 confirmed
reward-hacking cases across 6 benchmarks in paper §3.3; the companion blog reports 28 confirmed instances. These are same-work artifact counts, not independent confirmations or a single interchangeable total. Separately, a widely-used benchmark
maintains its own quarantine section for submissions annotated *"Test-set feedback"*, one of which would
otherwise have ranked #1 by 7 medal outcomes.

**Freeze-provenance correction 2026-10-06 (intake-980#02):** the April 10 snapshot is Terminal-Bench 2.0. The read paper/blog text supplies no MLE-bench leaderboard-freeze claim or causal link; prior freeze-causation speculation remains withdrawn. The separate quarantine observation above retains its own provenance and is not evidence that this audit caused an MLE-bench freeze. Completed local leakage audits below retain their dates and outcomes.

- [x] **Audit our eval fan-out and scorer paths against the harness-level list.** Specifically: does any
  prompt-assembly path put reference answers, gold patches, or oracle metadata into a context the model
  under test can read? Does any scorer path let a candidate observe its own grade before the run ends?
  ✅ 2026-08-12 (`mainB` subagent) — **prompt assembly is CLEAN; the leak is not in the prompt, it is in
  the filesystem** (next box). Verified every `_row_to_prompt` construction site in
  `scripts/benchmark/dataset_adapter_modules/{general,coding,math_adapter,reasoning,vision_agentic}.py`
  (17 sites): `expected` / `answer` / `canonical_solution` / `test` / `scoring_config.test_code` /
  `metadata.bug_explanation` are computed alongside the prompt and never concatenated into it. The
  dispatch is the narrow surface it should be — `eval_tower.py:_generate_question` builds `call_kwargs`
  from `dispatch_prompt` plus `force_role`/`force_mode`/`image_path`/`tools`/`n_probs` only; `expected`
  is read into a local for scoring and is not among them. Two by-design inclusions, recorded so nobody
  re-reports them: MBPP puts up to 3 test cases in the prompt as hints (standard MBPP protocol; its
  `expected` is only the function name), and CRUXEval input-prediction shows the output because
  predicting the input from the output *is* the task.
  **Grade observation: none in-run.** Scoring runs in `_score_generation` after the candidate's request
  has already returned, so there is no channel back into the same generation. The rubric-judge path is
  the only one holding `expected_contains`, and it is a separate `force_mode="direct"`,
  `allow_delegation=False` call gated on `check_cross_family(generator_model, role)` — the judge sees
  the reference, the candidate never does. PromptForge trace feedback
  (`eval_tower_trace_feedback.py`) is cross-trial prompt optimisation, not an in-run channel.
  *Not audited* (named rather than implied clean): `recall()`'s episodic-memory payload, which returns
  past-task Q-values and could in principle carry a prior trial's outcome for the same question.
- [x] **Check the working tree the agent sees.** Our own repo carries `CLAUDE.md`, `AGENTS.md` and skill
  files at paths an evaluated agent would naturally read — the exact shape of the solution-injection
  case. Establish what is visible during an eval run, not what we intended to be visible
  ✅ 2026-08-12 (`mainB` subagent) — **the answer key is inside the evaluated model's allowed read root.**
  `REPLEnvironment.ALLOWED_FILE_PATHS` and the live `read_file` both resolve to
  `['/mnt/raid0/llm/', '/tmp/']`, and the question pool lives at
  `/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl` — 1.35 GB, **79,479
  rows of which 78,341 carry a non-empty `expected`**, mode `0664`, each row a single JSON object
  holding both the verbatim `prompt` and its `expected`. The REPL surface advertised to the model
  (`src/prompt_builders/constants.py`) offers `grep(pattern, file_path=...)`, `peek(n, file_path=...)`,
  `list_dir(path)` and `CALL(name, **kw)` + `list_tools()`, so one `grep` of its own prompt text against
  that path returns the row containing its own answer. **Proven functionally, not by reading**:
  `_validate_file_path(pool)` → `(True, None)`; `orchestration.tools.system.read_file(pool)` returns
  content. This is exposure, not an observed exploit — no claim is made that any run did it, and the
  tool-use suite's `get_eval_secret` sentinel counts tool calls, not pool reads.
  **Corroboration that the threat model is already ours**: `src/builtin_tools.py:_register_eval_tools`
  documents minting eval secrets to "a tmpfs path outside read_file's allowed roots, so the eval harness
  can read ground truth while the model-under-test cannot grep it from the repo" — solved for that one
  tool, unsolved for the 78,341-row pool.
  **Second, distinct defect found while proving the first**: `orchestration/tools/system.py:_is_path_allowed`
  gates on `os.path.abspath`, which does **not** resolve symlinks. Demonstrated: a symlink at
  `/mnt/raid0/llm/tmp/<probe> → /etc/passwd` passed the check and `read_file` returned `/etc/passwd`
  (probe removed). The REPL's own `_validate_file_path` uses `realpath` and correctly refused the same
  path — so the two gates that share an allow-list do not share its enforcement.
  *Reachability caveat, stated because it bounds the severity*: this needs the model to be in REPL mode
  with the tool surface attached. `build_react_prompt`'s whitelist also lists `read_file`/`list_directory`,
  but that builder has **no caller outside `src/prompt_builders/`** — dead in the serving path, so ReAct
  is not a second route today.
- [x] **Record the finding either way.** "Audited, no leakage found" is a result worth having on file;
  an unaudited harness is not evidence of a clean one ✅ 2026-08-12 (`mainB` subagent) — recorded above.
  Verdict in one line: **prompt assembly and the judge path are clean; the harness-level exposure is
  filesystem reach, and it is real and reachable.** Two remediation options, neither taken here because
  both touch a production read path and this row authorised an audit, not a fix:
  (a) move `question_pool.jsonl` (and designed-core files) outside `llm_root` — the same tmpfs pattern
  `eval_secret.py` already uses, cheapest and matches an existing precedent;
  (b) narrow `ALLOWED_FILE_PATHS` during eval runs via the existing `ORCHESTRATOR_EDIT_ROOT` task-root
  isolation, which already restricts the REPL to a scratch root when active.
  Independently of the choice, `_is_path_allowed` should use `realpath` like its REPL counterpart.

**Correction carried from the dive, so it is not restated:** the audit does **not** cover MLE-bench, and
it makes no leaderboard-status claim. An earlier framing of it as "plausibly the cause of the MLE-Bench
freeze" was speculation and is retracted — the real on-benchmark antecedents are that benchmark's own
quarantine entries and its issue #124.

#### 2026-08-23 — follow-up from the NIB2-57a reader audit (tier-1 pass)

- [x] **Loader projects non-live records into the live scorer's quality map.** ✅ 2026-10-30 — Fixed in `epyc-orchestrator` commit `0815be05eae49557ef6068031a24bb9c4c5c4d44`: `_baseline_quality_by_role()` now filters to `deployment_status == "live_stack"` before either structured quality or model-filename fallback. The current compiled artifact had `qwen36_35b_a3b_mtp_q8_local` (`benchmark_or_candidate`) with `quality_for_role=0.852` and `quality_overall=0.8387`; the two candidate names in the 2026-08-23 finding are historical and no longer current records. Regression tests poison both candidate lookup paths and exercise degraded and descriptor fallback callers. The higher-is-better prior and existing quality-gap formula/0.75 reference are unchanged; an absent live prior continues to skip the quality-gap dimension. GitNexus upstream impact was HIGH (9 nodes, 3 direct callers); focused caller coverage and 102 q_scorer/q_reward tests passed. No live reload, new measurement, threshold, or grading rule. [belief: cc]

#### 2026-09-07 — laguna's provenance pins are stale in committed history (found during CJ-11)

- **[declined: ws58 2026-11-03 content-review: Laguna is retired (model audit 2026-11-03 re-scoped its last consumer); the laguna bench runner is on no live path]** **Two of laguna's three pinned-file digests do not match the files on disk, and have not
      since committed history.** `laguna_q4_cpu_bench_runner.py` pins three sibling files and
      validates them through `file_identity()`, which **raises `RuntimeError` on mismatch** —
      so this is not a warning, it blocks the path that builds the provenance block.

      | pinned constant | file | last touched | state |
      |---|---|---|---|
      | `EXPECTED_ANSWER_SCORING_SHA256` | `answer_scoring.py` | 2026-09-07 | **matches** (re-pinned by CJ-11) |
      | `EXPECTED_RAW_EVALUATOR_SHA256` | `v7_quality_gate_runner.py` | 2026-08-26 `da06b371` | **STALE** |
      | `EXPECTED_CODE_EXEC_SCORER_SHA256` | `code_exec_scorer.py` | 2026-07-29 `2f30da8a` | **STALE** |

      Both stale files are **clean in the working tree**, so the drift is committed, not local —
      the pins were left behind when those files legitimately changed, one of them ~6 weeks ago.

      **Do not simply re-pin.** Re-pinning is how a provenance check becomes a formality: it makes
      the error go away without anyone establishing that the current bytes are the bytes that were
      meant to be there. Establish first, per file, whether the change that moved it was intended
      and reviewed (`git log -p` from the pin's introduction), THEN re-pin with that commit named
      in the comment. If the check has been blocking laguna since July, also record what has been
      running instead and whether any result was produced by an unvalidated path.

      **The general defect is the same one CJ-12 found in the DTAP judges**: a digest written once
      at authoring time with nothing that recomputes it on a schedule will silently fall out of
      date, and the failure surfaces at the worst moment — when someone finally runs the thing.
      DTAP's answer was `python3 -m harness attest`; this pin set has no equivalent.

- [x] **v7 runner re-seal (sibling pins, not laguna's)** ✅ 2026-09-16 — operator decision RE-SEAL, applied as
      research `6d010a92` ("RATIFIED: re-seal v7 runner pins 6dea92dd/79721927 -> 20a97fbd"). It re-pins
      `dflash2_followups.py` `EXPECTED.runner_sha256` and the P3 bake-off manifest. The request bytes were
      identical in 6/6 stub scenarios, and the only output difference is two keys added by `baf36757`.
      laguna's `EXPECTED_RAW_EVALUATOR_SHA256` was **left on 79721927 on purpose** (a completed campaign), so
      the box above is unaffected. Detail: `progress/2026-09/2026-09-16-sub-v7-repin.md`.

- [x] **Generalize a pin-staleness checker across the benchmark tree.** ✅ 2026-10-07 — [Source and original8/8 controls](../../artifacts/ni08/evl42-success-acceptance-20261007/README.md). One script walks every
      `EXPECTED_*_SHA256` / `file_identity()`-style declared pin under `scripts/benchmark/` and
      reports staleness as its OWN reportable condition (like `python3 -m harness attest`),
      instead of each call site discovering it as a `RuntimeError` at execution time. LOW
      priority — the row above is the one instance known to be actively blocking; this is the
      preventive generalization, not itself urgent.

2026-10-07 MAIN accepted the generalized tracked-AST checker at Research main f770a525 and [original8/8 safe-read/CLI controls](../../artifacts/ni08/evl42-success-acceptance-20261007/README.md). Actual future pin-scan write/read projection stays SC-EVL42-PIN-REPORT-WIRING; no current pin-health scan, expectation update or loaded-code attestation is claimed.

Prospective `scripts/ci/pin_report_fixture.py` preparation owns exclusive report writing, strict original-attachment reopening and the existing fixture_execution_conformant projection. The existing [SC-EVL42-PIN-REPORT-WIRING parent](vidya-belief-substrate-program.md) stays open; its bounded VB-EVL42-PIN-REPORT-CONFORMANCE child verifies29 synthetic source controls before any actual scan can be consumed. Complete/stale reports and original FALSE/NULL remain distinct; no pin-health tuple or retrospective scan is authored.


#### Bounded pin-report source acceptance — 2026-10-07

- [x] **SC-EVL42-PIN-REPORT-SOURCE — implement and verify strict categorical report attachment without claiming actual scan health.** ✅ 2026-10-07 — [MAIN published exact source and original29/29 controls](../../artifacts/ni08/evl42-report-success-acceptance-20261007/README.md). Native TRUE/FALSE/NULL and complete stale/missing/unresolved report state remain separate from pin health. SC-EVL42-PIN-REPORT-WIRING actual producer/consumer scan boundary stays open; snapshots are non-atomic and loaded code remains unproven.
