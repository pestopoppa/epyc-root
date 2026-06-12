# Eval Tower Verification Framework

**Status**: IN PROGRESS — EV-1/2/6 code complete (2026-04-15). EV-3 pending (Scoring Verifiers download). EV-4/5/7 need inference. AA-Omniscience hallucination suite integrated (2026-04-15).
**Created**: 2026-04-14 (from deep-dive research, 5 papers + 2 subsystem threads)
**Updated**: 2026-04-15
**Priority**: MEDIUM (depends on AP-27 and Ouro P7)
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

### EV-3: Download Scoring Verifiers benchmarks (~50 lines)

- [ ] Download from HuggingFace `nvidia/Scoring-Verifiers` (HE-R+, MBPP-R+)
- [ ] Create adapter class in `dataset_adapters.py` (following existing adapter pattern)
- [ ] Register in `suites.py` as new evaluation suites
- [ ] Validate: load datasets, verify schema, count problems

**Files**: `dataset_adapters.py`, `suites.py`, data storage at `/mnt/raid0/llm/data/eval/`

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

- [ ] Formalize T0/T1/T2 as RLVR verification functions with deterministic reward signals
- [ ] Design reward signal per tier: T0 = binary, T1 = calibrated continuous, T2 = process-attributed
- [ ] Integrate Ouro-2.6B (P7) as T0 sentinel verification candidate
- [ ] Export eval environments for actual RL model training when DGX Spark available
- [ ] Track three metrics (quality + ECE + AUC) as the minimal signal for RLVR reward design

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
- [ ] Wire through `to_grep_lines()` for log parsing. (Pending — depends on existing `to_grep_lines()` refactor path; can land alongside the baseline-population run.)
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
- [ ] Extend `EvalResult` with rubric fields: `rubric_reasoning_trajectory`, `rubric_tool_calls`, `rubric_outline`, `rubric_content_stage`.
- [ ] LLM-as-judge scoring functions per rubric dimension (deterministic fallback via regex+structure for T1 low-cost runs).
- [ ] Create `deep_research_sentinel` suite: 20-40 research-like queries with multi-dimensional ground truth. 10 BrowseComp-style + 10 WideSearch-style + 10 mixed.
- [ ] Wire rubric scoring into existing `to_grep_lines()` — one `METRIC rubric_<dim>: <score>` line per dimension.

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

- [ ] **EV-10a — Paired skill-vs-no-skill efficacy check** (adopt SkillsBench methodology). For any candidate skill / agent-file / prompt mutation, eval-tower should report the *paired* delta (with-artifact minus without-artifact) on the relevant suite, **per-suite, with an explicit negative-delta guard**: a mutation that improves the aggregate but regresses a specific suite (the SkillsBench 16/84 pattern) must surface, not hide. **Do NOT rebuild the regressor** — `skill_transfer_regression.py` (from completed/07-skillsbench-eval-suite.md, 2026-03-03) already flags per-skill cells dropping >threshold across a before/after checkpoint pair; EV-10a is the *wiring* of that detector (and the paired no-artifact arm) into the autopilot `apply_mutation_isolated` → `ctx.accept()` path (cross-ref `meta-harness-optimization.md` 2026-05-27 SkillOpt section), plus honoring the **dev/test_normal split discipline** (2026-04-30 AppWorld update) — require improvement on BOTH splits. Net-new work is the no-artifact baseline arm + accept-path hook, not the regression math. **DECISION LOGIC LANDED 2026-05-27** — `epyc-orchestrator/scripts/autopilot/skill_efficacy.py` `evaluate_skill_efficacy()` (per-suite delta + negative-delta guard + strict aggregate-gain) and `evaluate_skill_efficacy_split()` (dev/test both-arms discipline); 19 tests in `tests/unit/test_skill_efficacy.py` pass. Pure sidecar, NO live wiring. Remaining (deferred to next AR-3 restart, AP-29/30/31 pattern): the no-artifact baseline eval arm + the `apply_mutation_isolated`→`ctx.accept()` call site.
- [ ] **EV-10b — Surrogate-verifier scoring for leak-constrained tasks** (adopt CoEvoSkills pattern). Where a task has no exposable ground truth, score via a self-authored assertion suite from an **independent, cross-family verifier session** (reuse EV-6 `check_cross_family()`), returning only an opaque correctness bit to the artifact-author path. This is the eval-side complement to EV-5 (ThinkPRM process verification) and EV-7 (RLVR reward). **Guard**: keep a ground-truth oracle as authoritative arbiter where one exists (per the CoEvoSkills precision failure mode); the surrogate is for dense feedback, not final scoring. **SCAFFOLD LANDED 2026-05-27** — `skill_efficacy.py` `surrogate_proxy_reward()` (fraction of self-authored assertions passing), `surrogate_feedback()` (dense vs **opaque-oracle-bit anti-overfit** decision), `require_cross_family()` (injected `check_cross_family` so the sidecar doesn't import the in-flight `eval_tower.py`). Pure functions; the verifier-LLM assertion authoring is inference-gated (caller injects outcomes, per the `verbalized_sampling.py` convention).
- **Cross-cutting**: EV-10a is the empirical instrument that makes the `meta-harness-optimization.md` SkillOpt recommendation auditable — without paired, per-suite, negative-delta-guarded efficacy measurement, the autopilot cannot distinguish a genuinely-helpful skill edit from a SkillsBench-style net-negative self-generation. **Priority MEDIUM**, mostly code (no new model for 10a; 10b reuses cross-family infra). Do NOT block EV-3/4/5 on this. **Inference-gated validation is tracked in [bulk-inference-campaign.md](bulk-inference-campaign.md) Package K as K-SKILL-1** (two-stage: AR-3-restart wiring → paired-mutation A/B; post-AR-3/AR-4 class).

## Research Intake Update — 2026-06-03

### New Related Research
- **[intake-658] "Which Model Reviews Code Best?" (Factory Research code-review benchmark)** (https://factory.ai/news/code-review-benchmark)
  - Relevance: a **turn-key, fully open-sourced** code-review eval methodology that validates two patterns eval-tower already scaffolds, and supplies a task family we have NOT built (find-bugs-in-a-diff against a human-curated golden set; our suites are answer-correctness / debug-fix / agentic-coding). Released materials: golden set (50 real PRs from Sentry/Grafana/Keycloak/Discourse/Cal.com + curated bug ground truth) under the `droid-code-review-evals` org, and scoring scripts as `review-droid-benchmark`.
  - Key technique → maps onto **EV-6 directly**: their **judge-swap self-favoring-bias ablation** (swap the judge model, observe ≤2pp impact) is exactly our cross-family verification check (`check_cross_family()`). Also liftable: **findings-F1 scoring** (precision = fraction of findings that are real bugs; recall = fraction of golden-set bugs found) with a *semantic* LLM judge (not string-match) — slots into ch07's F1 verifier + ch06's Claude-as-Judge; and a **≥3-run Mean-F1 + StdDev** stability protocol.
  - Reported results: GPT-5.2 60.5% F1 @ $1.25/PR (top); Opus 4.6 59.8% @ $3.11; Sonnet 4.6 57.4% @ $1.15; Kimi K2.5 51.9% @ $0.41; MiniMax M2.7 45.6% @ $0.15. **Cost explains only ~21% of quality variance.** Even the best model misses ~40% of golden-set bugs.
  - Delta from current approach: we'd point the judge at our **local** models (gemma4-26B-A4B worker_general, coder roles, any peer-verifier) and reuse existing Claude-as-Judge plumbing — a reviewer-model F1 suite naturally lands in [`multi-file-coding-completion-capability.md`](multi-file-coding-completion-capability.md). **Caveat**: vendor self-benchmark (models adjacent to their own product), 50 PRs / 5 repos only — treat rankings as indicative; the judge-swap check mitigates *judge* bias but not golden-set/PR-selection bias. Verdict: adopt_patterns.

#### Deep-dive: full methodology + reproduction plan (2026-06-03)
Deep-dive of `review-benchmark.md` + the released repos + `eval_common.py` source → full write-up in [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md) (Part 4). **Corrections**: (1) judge model is **`claude-opus-4-6` hardcoded** (Anthropic SDK), not Sonnet 4; (2) **"open source" is overstated** — harness repo is **unlicensed**, the v3 golden set (167) is **gitignored**, only Augment upstream **v1 (145)** is genuinely open; (3) provenance is **Greptile → Augment → Factory** (Factory added 31 bugs Droid itself surfaced → self-curation bias); (4) **low-severity golden comments are scored as neither TP/FP/FN** (load-bearing); (5) all 13 models at reasoning_effort=High, 3 runs (malfunction-excluded), **micro-averaged** P/R/F. **EV-NEW (review-finding-F1 suite)** — reuse Augment v1 + the 5 PR sets, re-implement the ~80-LOC scorer (do **not** vendor the unlicensed file), drive **local** models via `/v1/chat/completions` over diff+context (document the divergence from their agentic whole-repo setup), judge with a **local cross-family verifier** and run the ≤2pp judge-swap as a concrete **EV-6** instance; index by model/quant not role; per-PR incremental persistence. Absolute F1 is **not** comparable to their leaderboard — internal-only.
