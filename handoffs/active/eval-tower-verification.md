# Eval Tower Verification Framework

**Status**: IN PROGRESS — EV-1/2/3/6 code complete. EV-3 was schema-corrected and validated on 2026-06-19; EV-4/5/7 need inference. AA-Omniscience hallucination suite integrated (2026-04-15).
**Created**: 2026-04-14 (from deep-dive research, 5 papers + 2 subsystem threads)
**Updated**: 2026-07-14
**Priority**: MEDIUM (depends on AP-27 and Ouro P7) — *2026-07-14 audit note: [research-evaluation-index.md](research-evaluation-index.md) carries this handoff at HIGH; discrepancy flagged by the backlog ROI audit — both stated here, owner decides.*
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
| intake-363 | LLM-as-a-Verifier | Logprob-based multi-criteria verification: R(t,τ) = (1/CK) Σ p_θ(v_g\|t,c,τ)·φ(v_g). llama.cpp has full vocab access (no k=20 truncation). Cross-family verification critical. |
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

llama.cpp `get_token_probabilities()` at `tools/server/server-common.cpp` L1755:
1. Calls `llama_get_logits_ith(ctx, idx)` for full vocabulary (128K+ tokens)
2. Creates `vector<llama_token_data>` with ALL tokens
3. Sorts by logit descending, applies softmax over ENTIRE distribution
4. Returns top `n_probs` entries — no hard-coded upper limit

| Aspect | Gemini API (k=20) | llama.cpp (unlimited) |
|--------|--------------------|-----------------------|
| Score token coverage | May miss low-prob tokens | Complete |
| Probability mass | ~80% accuracy | Zero truncation loss |
| Determinism | Non-deterministic (GPU routing) | Deterministic at temp=0 |
| Cost | API pricing | Local compute only |

### Confirmation Bias Mitigation

**The biggest risk**: Repeated verification can AMPLIFY bias. From arxiv:2603.18740, adversarial success increased from 52% (first attempt) to 87% after 4 iterative review rounds.

**Mitigations** (in order of effectiveness):
1. **Cross-family verification**: Different model family for verifier vs generator. Gemini verifying GPT: +4.6pp. Same-family: +1.7pp. This is the strongest defense.
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

**Files modified**: `eval_tower.py` (QuestionResult dataclass + _eval_question)

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

- [ ] Run current eval tower on Scoring Verifiers HE-R+ benchmark
- [ ] Record ECE, AUC, Top-1, Bottom-1, Spearman ρ, MAE as baseline
- [ ] Identify calibration violations — which question types produce miscalibrated confidence?
- [ ] This baseline is the comparison point for all subsequent verification improvements

**Dependencies**: Inference stack must be running. Can be folded into a Package B/C run.

### EV-5: Deploy ThinkPRM-1.5B for T2 process verification (~100 lines)

- [ ] Download ThinkPRM-1.5B from HuggingFace, quantize to Q4_K_M GGUF (~2GB)
- [ ] Add server config for ThinkPRM in `orchestrator_stack.py` (load only during T2 eval, unload main models — sequential loading per memory note)
- [ ] Implement verification pass in `eval_tower.py` `eval_t2()`:
  - After standard scoring, identify N most uncertain questions (lowest |confidence - 0.5|)
  - For each uncertain question: send to ThinkPRM with verification CoT prompt
  - Extract step-level verdicts and P("yes")/(P("yes")+P("no")) score
  - Store per-step attribution in `QuestionResult.details`
- [ ] Cross-family verification: enforce that ThinkPRM model family differs from evaluated models

**Files**: `eval_tower.py` L324-355 (eval_t2), `orchestrator_stack.py`, new verification module

### EV-6: Cross-family verification constraint — ✅ 2026-04-15

- [x] Added `VERIFICATION_FAMILIES` dict and `check_cross_family()` function to `eval_tower.py`
- [x] Supports Qwen, Llama, DeepSeek, Ouro, Mistral, Gemma families
- [x] Returns True (safe) if families differ or either is unknown (permissive default)
- [x] Runtime guard for EV-5 (ThinkPRM) and EV-7 (AP-27 RLVR)

**Files modified**: `eval_tower.py` (module-level VERIFICATION_FAMILIES + check_cross_family)

### EV-7: AP-27 RLVR integration (depends on EV-1–4 + Ouro P7)

- [x] Formalize T0/T1/T2 as RLVR verification functions with deterministic reward signals. ✅ 2026-07-11 — `epyc-orchestrator` commit `7ee919d8` adds the pure `src/autopilot_core/rlvr_tiers.py` contract and shared exports.
- [x] Design reward signal per tier: T0 = binary, T1 = calibrated continuous, T2 = process-attributed. ✅ 2026-07-11 — no promotion authority changed; the contract returns observe-only rewards and blockers.
- [ ] Integrate Ouro-2.6B (P7) as T0 sentinel verification candidate
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
- [ ] One-day baseline pass: 4 production roles × 20 open-ended prompts × 4 completions (temperature 0.7 baseline + T=1.0 ladder point for recovery probe). **Inference-gated; baseline yaml schema ready (`orchestration/autopilot_baseline.yaml` diversity_baseline: + diversity_baseline_meta: blocks).**
- [x] **Amended SafetyGate policy** (originally "reject if distinct-2 drops >20% AND quality not up"): **DONE 2026-04-22 (NIB2-42)**: `SafetyGate` in `src/safety_gate.py`. Tier 1 WARN / Tier 2 REJECT (all 4 signals). Warn-only default via `SAFETY_GATE_WARN_ONLY` env var (default ON).
  - **Tier 1 WARN**: distinct-2 drops >20% AND quality not up → log warning, investigate.
  - **Tier 2 REJECT**: only when ALL of: (a) distinct-2 drops >20%, (b) semantic-embedding-agreement drops >10%, (c) quality not up, (d) **Verbalized Sampling probe fails to recover >50% of the gap**. Multi-signal reject prevents rejecting models that merely lack a calibrated sampling prompt.
  - Warn-only mode mandatory until Verbalized Sampling replication on Qwen3-30B-A3B produces baseline recovery data.
- [x] **Verbalized Sampling recovery probe**: implement distributional-prompt variant ("generate 5 diverse responses with probabilities...") as part of the diversity baseline. A model that recovers >50% via VS is NOT a candidate for rejection. **DONE 2026-04-22**: `src/tools/diversity/verbalized_sampling.py` with `VS_DISTRIBUTIONAL_PROMPT` template, `recovery_ratio()`, `format_vs_prompt()`, `parse_vs_completions()`. Never calls inference directly; caller injects completions.
- [ ] Deferred: temperature-ladder experiment (T=0.7/1.0/1.3); CoT-suppression ablation.

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
AP-27 in [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) is the parent work item. This handoff provides the implementation plan that AP-27 lacks. AP-27 becomes a pointer: "see eval-tower-verification.md EV-1–EV-7."

### 2. Ouro P7 ↔ T0 Sentinel
Ouro-2.6B-Thinking (research-eval P7) is a candidate T0 sentinel verifier. Its looped architecture achieves 90.85% MATH-500 at only 2.6B params. If Ouro's MATH-500 performance validates on our CPU, it becomes the cross-family verification model for T0 (it's ByteDance architecture, distinct from our Qwen/Llama stack).

### 3. Decision-Aware Routing ↔ Reward Signal
The [decision-aware-routing.md](decision-aware-routing.md) changes the Q-scorer reward signal. The eval tower verification framework must be able to assess whether the new reward signal is calibrated (ECE) and discriminative (AUC). DAR-2/3/4 changes should be validated through EV-4 calibration baselines.

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
  - Two concrete uses: (a) **commercial-baseline benchmark** — run our local stack (Hermes + Qwen3.6 worker + 30B-A3B coder) on the same AppWorld split for apples-to-apples SGC comparison against published Gemini 3 Flash numbers (37.5% test_normal SGC vanilla / 48.2% with HALO trace-loop optimization); (b) **eval-as-corpus** — span-tree format may be a useful logging target if we standardize agent trace observability across the orchestrator (cross-ref `meta-harness-optimization.md` 2026-04-30 update).
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

- [ ] **EV-10a — Paired skill-vs-no-skill efficacy check** (adopt SkillsBench methodology). For any candidate skill / agent-file / prompt mutation, eval-tower should report the *paired* delta (with-artifact minus without-artifact) on the relevant suite, **per-suite, with an explicit negative-delta guard**: a mutation that improves the aggregate but regresses a specific suite (the SkillsBench 16/84 pattern) must surface, not hide. **Do NOT rebuild the regressor** — `skill_transfer_regression.py` (from completed/07-skillsbench-eval-suite.md, 2026-03-03) already flags per-skill cells dropping >threshold across a before/after checkpoint pair; EV-10a is the *wiring* of that detector (and the paired no-artifact arm) into the autopilot mutation accept path (cross-ref `meta-harness-optimization.md` 2026-05-27 SkillOpt section), plus honoring the **dev/test_normal split discipline** (2026-04-30 AppWorld update) — require improvement on BOTH splits. Net-new work is the no-artifact baseline arm + accept-path hook, not the regression math. **DECISION LOGIC LANDED 2026-05-27** — `epyc-orchestrator/scripts/autopilot/skill_efficacy.py` `evaluate_skill_efficacy()` (per-suite delta + negative-delta guard + strict aggregate-gain) and `evaluate_skill_efficacy_split()` (dev/test both-arms discipline); 19 tests in `tests/unit/test_skill_efficacy.py` pass. **DEFAULT-OFF LIVE-BRANCH WIRING LANDED 2026-06-13** — `epyc-orchestrator` `924ca50` wires `AUTOPILOT_SKILL_EFFICACY_GATE` into prompt/GEPA/code mutation handlers: pre-mutation no-artifact eval arm, post-mutation per-suite compare, `eval_result.details["skill_efficacy"]`, and revert before epoch acceptance on reject. Remaining: deploy/restart and paired-mutation A/B validation; keep flag isolated from `AUTOPILOT_BSV2_ACCEPT_GATE`.
- [ ] **EV-10b — Surrogate-verifier scoring for leak-constrained tasks** (adopt CoEvoSkills pattern). Where a task has no exposable ground truth, score via a self-authored assertion suite from an **independent, cross-family verifier session** (reuse EV-6 `check_cross_family()`), returning only an opaque correctness bit to the artifact-author path. This is the eval-side complement to EV-5 (ThinkPRM process verification) and EV-7 (RLVR reward). **Guard**: keep a ground-truth oracle as authoritative arbiter where one exists (per the CoEvoSkills precision failure mode); the surrogate is for dense feedback, not final scoring. **SCAFFOLD LANDED 2026-05-27** — `skill_efficacy.py` `surrogate_proxy_reward()` (fraction of self-authored assertions passing), `surrogate_feedback()` (dense vs **opaque-oracle-bit anti-overfit** decision), `require_cross_family()` (injected `check_cross_family` so the sidecar doesn't import the in-flight `eval_tower.py`). **READ-ONLY REPORT CONSUMER LANDED 2026-07-11** — `epyc-orchestrator` commit `fd709e4a` makes `eval_task_coverage_report.py` summarize journaled `eval_details.details.surrogate_feedback` / `eval_details.surrogate_feedback` rows (accepted, dense-feedback, opaque-only oracle conflicts, average proxy reward) and render them in Markdown without touching accept gates. Remaining: inference-gated verifier-session assertion authoring / producer wiring; caller still injects outcomes per the `verbalized_sampling.py` convention.
  - [x] EV-10b read-only report consumer for journaled surrogate feedback. ✅ 2026-07-11
- **Cross-cutting**: EV-10a is the empirical instrument that makes the `meta-harness-optimization.md` SkillOpt recommendation auditable — without paired, per-suite, negative-delta-guarded efficacy measurement, the autopilot cannot distinguish a genuinely-helpful skill edit from a SkillsBench-style net-negative self-generation. **Priority MEDIUM**, mostly code (no new model for 10a; 10b reuses cross-family infra). Do NOT block EV-3/4/5 on this. **Inference-gated validation is tracked in [bulk-inference-campaign.md](bulk-inference-campaign.md) Package K as K-SKILL-1** (remaining stage: deploy/restart + paired-mutation A/B; post-AR-3/AR-4 class).

### EV-11/12/13 (NEW 2026-07-14) — backlog ROI audit waypoints

Formalized from the 2026-07-14 backlog ROI audit ([backlog-roi-audit-2026-07-14.md](backlog-roi-audit-2026-07-14.md) §A):

- [x] **EV-11 — math_verify scoring flip** ✅ 2026-07-17 (Wave-2 B1): GSM8K+MATH-500 adapter → `scoring_method=math_verify` (GSM8K prompt `<answer>`→`\boxed{}` for extraction); eval_tower HARD-FAILS on missing math-verify (no silent exact_match fallback; the 0/1,819-question no-op is fixed). math-verify 0.9.0 installed. 113 eval_tower tests green.
  - [ ] **EV-11a — companion fix (BLOCKS re-baseline)**: `debug_scorer._score_math_verify` non-greedy `\boxed{(.+?)}` truncates `\boxed{\frac{1}{2}}`→`\frac{1`→parse-fail→silent exact_match→wrong; breaks MATH-500 frac/sqrt/matrix answers. Fix = drop manual extraction, pass raw answer to native `math_verify.parse()` (balanced-brace aware). Owner: debug_scorer.
  - [ ] **EV-11b — ECE binning decision**: eval_tower `_aggregate` inline ECE (top bin open, `c<hi`) vs `stat_tests.expected_calibration_error` (top bin closed) differ 0.15-0.40 on binary-confidence math suites; feeds SafetyGate/journal (CRITICAL path). Behavior CHANGE → operator-gated, bundle w/ re-baseline.
  - [ ] **EV-11c — fresh math re-baseline (INFERENCE → batch manifest)**: gated on EV-11a fix + EV-11b decision; production temp+seed42; record dataset_sha256+test_profile per arm; era-label supersede (never edit historical). Pre-decided forks in the Wave-3 manifest entry EV-11-math-rebaseline.
- [x] **EV-12 — execution-free patch verifier as gating signal** ✅ 2026-07-17 (module landed `epyc-orchestrator/src/verification/patch_verifier.py`: `verify_patch(patch, base) -> VerdictResult`; git-apply-check/hunk-context/AST-compile/import-sanity/ruff — none execute patched code; `to_report()` validates live against verification_report.schema.json; `.to_check()` = the eval-tower hook signal for Wave-2 B1; 30 tests. Remaining: B1 wires the eval_tower hook + coder_escalation pre-gate A/B (inference).)
- [ ] **EV-13 — review-finding-F1 suite** (M; intake-658, audit RE-3, formalizes the EV-NEW prose below): local code-review benchmark per the Factory-methodology deep-dive (Augment v1 145-bug golden set, ~80-LOC scorer, local models via /v1/chat/completions, ≤2pp judge-swap as first concrete EV-6 cross-family instance); feeds coder-pool composition + Strand Phase C.
  - [x] **EV-13a — build leg** ✅ 2026-07-17: NEW `epyc-inference-research/scripts/benchmark/review_f1/` (clean-room micro-avg P/R/F1 scorer w/ low-severity-neither rule + Mean-F1/StdDev ≥3-run protocol; /v1 harness w/ per-PR atomic incremental persistence + resume, model/quant indexing, judge-swap plumbing, mock/--dry-run transports; assemble_golden_set.py + checksum) + 22 self-contained tests. No inference, no unlicensed vendoring; run-leg CLI documented in review_f1/README.md.
  - [ ] **EV-13b — run leg (INFERENCE → batch-manifest entry)**: source Augment-v1 145-bug set (github.com/ai-code-review-evaluations/golden_comments; raw items lack structured criterion/location → semantic-matcher rides the run leg) + 5 PR diffs; assemble golden_set.json; run the documented harness CLI over local models (≥3 runs) + EV-6 ≤2pp cross-family judge-swap; index by model/quant.

## Research Intake Update — 2026-06-03

### New Related Research
- **[intake-658] "Which Model Reviews Code Best?" (Factory Research code-review benchmark)** (https://factory.ai/news/code-review-benchmark)
  - Relevance: a **turn-key, fully open-sourced** code-review eval methodology that validates two patterns eval-tower already scaffolds, and supplies a task family we have NOT built (find-bugs-in-a-diff against a human-curated golden set; our suites are answer-correctness / debug-fix / agentic-coding). Released materials: golden set (50 real PRs from Sentry/Grafana/Keycloak/Discourse/Cal.com + curated bug ground truth) under the `droid-code-review-evals` org, and scoring scripts as `review-droid-benchmark`.
  - Key technique → maps onto **EV-6 directly**: their **judge-swap self-favoring-bias ablation** (swap the judge model, observe ≤2pp impact) is exactly our cross-family verification check (`check_cross_family()`). Also liftable: **findings-F1 scoring** (precision = fraction of findings that are real bugs; recall = fraction of golden-set bugs found) with a *semantic* LLM judge (not string-match) — slots into ch07's F1 verifier + ch06's Claude-as-Judge; and a **≥3-run Mean-F1 + StdDev** stability protocol.
  - Reported results: GPT-5.2 60.5% F1 @ $1.25/PR (top); Opus 4.6 59.8% @ $3.11; Sonnet 4.6 57.4% @ $1.15; Kimi K2.5 51.9% @ $0.41; MiniMax M2.7 45.6% @ $0.15. **Cost explains only ~21% of quality variance.** Even the best model misses ~40% of golden-set bugs.
  - Delta from current approach: we'd point the judge at our **local** models (gemma4-26B-A4B worker_general, coder roles, any peer-verifier) and reuse existing Claude-as-Judge plumbing — a reviewer-model F1 suite naturally lands in [`multi-file-coding-completion-capability.md`](multi-file-coding-completion-capability.md). **Caveat**: vendor self-benchmark (models adjacent to their own product), 50 PRs / 5 repos only — treat rankings as indicative; the judge-swap check mitigates *judge* bias but not golden-set/PR-selection bias. Verdict: adopt_patterns.

#### Deep-dive: full methodology + reproduction plan (2026-06-03)
Deep-dive of `review-benchmark.md` + the released repos + `eval_common.py` source → full write-up in [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md) (Part 4). **Corrections**: (1) judge model is **`claude-opus-4-6` hardcoded** (Anthropic SDK), not Sonnet 4; (2) **"open source" is overstated** — harness repo is **unlicensed**, the v3 golden set (167) is **gitignored**, only Augment upstream **v1 (145)** is genuinely open; (3) provenance is **Greptile → Augment → Factory** (Factory added 31 bugs Droid itself surfaced → self-curation bias); (4) **low-severity golden comments are scored as neither TP/FP/FN** (load-bearing); (5) all 13 models at reasoning_effort=High, 3 runs (malfunction-excluded), **micro-averaged** P/R/F. **EV-NEW (review-finding-F1 suite — now tracked as the EV-13 checkbox above, 2026-07-14)** — reuse Augment v1 + the 5 PR sets, re-implement the ~80-LOC scorer (do **not** vendor the unlicensed file), drive **local** models via `/v1/chat/completions` over diff+context (document the divergence from their agentic whole-repo setup), judge with a **local cross-family verifier** and run the ≤2pp judge-swap as a concrete **EV-6** instance; index by model/quant not role; per-PR incremental persistence. Absolute F1 is **not** comparable to their leaderboard — internal-only.

## Research Intake Update — 2026-06-20

### DRACO rubric methodology (intake-713 → EV-9)

- **[intake-713] DRACO (Perplexity AI, arXiv 2602.11685)** — a deep-research benchmark contributing rubric-methodology refinements to EV-9 (Multi-dimensional rubric, L240). **Ownership note**: this handoff (`eval-tower-verification.md`) is the OWNING handoff for EV-9; `research-evaluation-index.md` holds only a collective EV-4/8/9/10 pointer, not the EV-9 detail. Methodology transfer only — see numbers caveat below.
- **[intake-713] DRACO scoring — separate positive/negative rubric weighting** — fold into EV-9's LLM-as-judge scoring functions (the per-dimension scorers at EV-9 task 2): weight positive (reward-bearing) and negative (penalty-bearing) rubric criteria independently rather than as a single symmetric score. CPU-portable; no new model required (refines the existing judge prompt + aggregation).
- **[intake-713] DRACO validation — multi-judge ranking-stability across ≥2 LOCAL judges** — validate rubric-score rankings for stability across at least two local judge models. **Reuse the existing `src/bradley_terry.py`** (from autopilot P17.BT-1) as the ranking-stability primitive rather than building a new ranker. CPU-portable; pairs naturally with EV-6 cross-family discipline (the ≥2 judges should be cross-family).
- **[intake-713] DRACO saturation testing — reject sentinels scoring >90%** — when constructing the `deep_research_sentinel` suite (EV-9 task 3), reject sentinel queries that any candidate scores >90% on (saturated → non-discriminative). This is also a **chapter-07 recommendation** — flagged as a recommendation only; we do NOT edit chapters here.
- **[intake-713] DRACO content axes — ADDITION, not a swap** — EV-9's existing four rubric dims (`rubric_reasoning_trajectory` / `rubric_tool_calls` / `rubric_outline` / `rubric_content_stage`) are **MindDR-process** dimensions. DRACO's four **CONTENT** axes — Factual Accuracy / Breadth-Depth / Presentation / Citation — are an ADDITION to consider alongside them, NOT a replacement. The `deep_research_sentinel` suite already exists (MD-8 done 2026-04-22); these ideas refine HOW it is constructed/scored, not WHETHER it exists.
- **[intake-713] DRACO production-query sampling — DESIRABLE-BUT-GATED** — DRACO's task-construction front-end samples real production queries. EPYC has no Perplexity-scale traffic, so this is gated: substitute = draw from [`frontier-f1-real-task-corpus.md`](frontier-f1-real-task-corpus.md) once its soak yields ≥100 real records. Do not block EV-9 construction on this; use synthetic/curated queries until the corpus matures.
- **[intake-713] DRACO reported numbers — external observations only** — Perplexity Deep Research 70.5% (and the rest of DRACO's leaderboard) are external/closed-system observations on Perplexity's stack; they are NOT runnable here and are NOT decision-gating for EPYC. Methodology transfer only — no number is lifted as a target or baseline.

## Research Intake Update — 2026-06-23

### EV-9 saturation: empirical instance — our production review suite cannot resolve top-of-stack models (operator-flagged)

The DRACO "reject sentinels scoring >90% / saturated → non-discriminative" methodology (L409) now has a **concrete, dated instance from our own production review suite**, surfaced during the 2026-06-22 MTP-refresh promotion analysis (see [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) "Eval-resolution caveat"):

- **Symptom**: gemma-4-31B (31B **dense**) and gemma-4-26B-A4B (~3.8B-active **MoE**) both score ~90% on our `benchmarks/results/reviews/summary.csv` suites — i.e. a small MoE *appears tied* with a much larger dense model of the same family. Operator (correctly) flagged this as implausible.
- **Diagnosis = instrument saturation, NOT model parity and NOT quantization**: public dense-Q4 gemma-4-31B ≈ 92% (above our 90%) rules out a Q4 penalty; the dense 31B is genuinely ~1–3pp stronger on standard suites and ~8–10pp on frontier/agentic suites **we do not run**. Our suites sit in the saturated 90–94% band, so they cannot resolve the real gap — the exact failure mode EV-9 saturation-rejection exists to prevent, observed on a *deploy-gating* comparison rather than a sentinel-construction screen.
- **EV-9 implication (operator-review candidate, NOT actioned here — eval trust boundary is human-amendment-only)**: (1) the >90%-saturation reject rule (L409) should extend beyond `deep_research_sentinel` construction to a **standing audit of the production review suites** — any suite where the top-2 stack models are within noise at >90% is non-discriminative for promotion decisions and needs a harder tier; (2) this is direct motivation for the **frontier/harder eval tier** the eval tower lacks (pairs with EV-8 redundancy pruning, L238 — prune saturated suites, add discriminative ones). The Qwen-Scope feature-coverage-saturation proxy (EV-8) could *flag* such suites evaluation-free.
- **Cross-refs**: memory `feedback_eval_saturation_masks_model_gap`; sibling resolution-artifact precedent `feedback_per_suite_gate_resolution_artifact` (per-suite 1-question flips). The MTP-refresh Pareto-domination call (worker A4B over dense 31B) stays valid **for the worker role** (~90% bar + speed-dominated); it must NOT be generalized to "A4B = dense-31B in capability."

## Research Intake Update — 2026-07-16 (Reviewer control plane: EV-9/ECE/AUC reuse contract)

The Architect→Reviewer control-plane series ([`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)) REUSES this handoff's machinery rather than duplicating it: H4 ([`reviewer-calibration-accounting.md`](reviewer-calibration-accounting.md)) calls the EV-tier ECE/AUC implementations for reviewer Brier/ECE/AUC, and H3's grading turn builds on the EV-9 rubric-judge prompts/scoring (`rubric_scoring.py`). Boundary: reviewer-calibration metrics (FA/FR/CR) are a SEPARATE instrument gating reviewer-role promotion — they do not enter the T0-T3 model-quality axes; the plane invokes the tower, never the reverse. New intake relevant to EV work: intake-834 (Agentic Rubrics — weighted-axis rubric artifact, authoring/grading split, decision bands S≥0.85/≤0.5), intake-836 (judge overcorrection FR≫FA — motivates symmetric tolerance monitoring on any judge), intake-837/838 (judge-bias probe set + Consistency-Rate reporting — applicable to EV-9 rubric judges too).
