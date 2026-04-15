# Eval Tower Verification Framework

**Status**: IN PROGRESS — EV-1/2/6 code complete (2026-04-15). EV-3 pending (Scoring Verifiers download). EV-4/5/7 need inference.
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
