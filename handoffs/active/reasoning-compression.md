# Reasoning Compression for Inference Cost Reduction

**Status**: in-progress
**Created**: 2026-03-14 (via research intake)
**Categories**: training_distillation, cost_aware_routing

## Objective

Explore reasoning token compression techniques that can reduce inference cost for reasoning models by 50-60% while maintaining or improving accuracy. OPSDC demonstrates that much reasoning output is actively harmful — compressing it improves both cost and quality. This could fundamentally change how we route to reasoning models.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-110 | OPSDC: On-Policy Self-Distillation for Reasoning Compression | high | new_opportunity |
| intake-126 | FlowSteer: Concise Reasoning via Flow Matching | high | new_opportunity |
| intake-127 | TrimR: Verifier-based Training-Free Thinking Compression | high | new_opportunity |
| intake-129 | short-m@k: Shorter Thinking Chains for Improved Reasoning | high | new_opportunity |
| intake-128 | Adaptive CoT Compression (Self-Optimizing Framework) | high | worth_investigating |
| intake-133 | Reasoning as Compression (Information Bottleneck theory) | medium | worth_investigating |
| intake-134 | CoLaR: Dynamic Latent Compression of Reasoning Chains | medium | worth_investigating |
| intake-130 | Do NOT Think That Much (overthinking analysis) | medium | worth_investigating |
| intake-276 | Brevity Constraints Reverse Performance Hierarchies | high | worth_investigating |
| intake-125 | S3-CoT: Self-Sampled Succinct Reasoning | medium | worth_investigating |
| intake-103 | Thinking to Recall: Reasoning Unlocks Parametric Knowledge | medium | worth_investigating |

## Approach Taxonomy

Three families of techniques, ordered by implementation effort:

### Tier 1 — Zero-training (inference-time only)
- **TrimR** (intake-127): Verifier prunes reasoning tokens at inference. Compatible with our existing scorer infrastructure. **Highest priority — deploy immediately.**
- **short-m@k** (intake-129): Run k parallel generations, stop at first m completions, majority vote. 34.5% more accurate than longest chains. Maps to spec-decode verify-accept paradigm.
- **Conciseness prompting**: Just add "be concise" to Qwen3 worker prompts. OPSDC paper shows 37% token reduction with comparable accuracy on easy problems. Zero effort.

### Tier 2 — Activation steering (no weight changes)
- **FlowSteer** (intake-126): Nonlinear activation steering transforms verbose→concise reasoning. Input-dependent control enables per-request reasoning budget. No retraining needed, but requires activation hook infrastructure.
- **S3-CoT** (intake-125): Self-sampled activation steering for shorter CoT. No teacher model required.

### Tier 3 — Training required
- **OPSDC** (intake-110): Self-distillation, 8x H200 for ~100 steps. Best results (57-59% compression + accuracy gains). Requires GPU access.
- **CoLaR** (intake-134): Latent-space reasoning compression. 53.3% chain reduction, 4.8% performance loss. Bypasses KV cache entirely. Longer-term.

## Open Questions

- Can TrimR's verifier be our existing debug_scorer.py or does it need a specialized verifier?
- Does FlowSteer's activation steering work with quantized GGUF models via llama.cpp?
- OPSDC's difficulty adaptation (56% compression on easy, 35% on hard) — can we extract this as a routing signal without training?
- How does reasoning compression interact with speculative decoding acceptance rates?
- OPSDC shows AIME 2025 accuracy *drops* by 5.4pp — frontier-difficulty problems are harmed. Routing must account for this.

## OPSDC Deep Analysis (arxiv:2603.05433)

**Mechanism**: Same model serves as both teacher and student. Teacher receives conciseness instruction, student doesn't. Reverse KL on student rollouts. Teacher refreshed every M=50 steps for progressive compression.

**Key finding — "reasoning is harmful"**: Under independent per-token error model (p_err=10^-4), removing ~2,750 tokens predicts >=28% relative accuracy improvement. Empirically validated: Qwen3-14B goes 70.0%→86.1% on MATH-500 purely from conciseness training with zero correctness reward.

**Difficulty adaptation is emergent**: Easy problems get 56-59% compression, hard problems 35%. The KL divergence between concise-prompted and base model is itself a difficulty signal usable for routing.

**Routing insight (zero-cost)**: Compare output length with/without conciseness prompt. Large ratio = easy → route to fast model. Small ratio = hard → escalate. Or simpler: just add conciseness instruction, short output = easy, long output = hard.

**Limitations**: AIME 2025 accuracy drops 5.4pp. Forward KL causes catastrophic collapse. Teacher update interval M must be 40-60 (sensitive). Math-only validation. No LoRA testing.

## Implementation Progress (2026-03-14)

### Action 1: Conciseness Prompting — DONE
- Added conciseness instructions to `worker_general.md`, `worker_math.md`, `coder_primary.md`
- Hot-swap files — takes effect on next request, no restart needed
- `architect_*` and `coder_escalation` already had conciseness suffixes

### Action 2: TrimR Evaluation — READY
- Created `epyc-inference-research/scripts/benchmark/eval_trimr.py` (evaluation script)
- Created `epyc-inference-research/docs/experiments/trimr-reasoning-pruning.md` (experiment doc)
- Supports three strategies: `full`, `think-strip`, `trimr` (paragraph-level pruning)
- Uses existing `debug_scorer.py` for quality measurement
- Dry-run validated, awaiting model availability for live evaluation
- Run: `python eval_trimr.py --suites math --n-questions 20 --model-port 8080`

### Action 3: Difficulty-Adaptive Routing Signal — DONE
- Created `epyc-orchestrator/src/classifiers/difficulty_signal.py` (~230 lines)
  - Mirrors `factual_risk.py` architecture exactly
  - 7 regex features: prompt_length, multi_step, constraints, code, math, nesting, ambiguity
  - Weighted score → band (easy/medium/hard)
- Wired into `_route_request()` in routing pipeline (after factual-risk block)
- Added `difficulty_score` and `difficulty_band` to `RoutingResult` and `EscalationContext`
- Config block added to `classifier_config.yaml` (mode: shadow)
- 30 tests in `tests/classifiers/test_difficulty_signal.py` — all passing
- **Currently in shadow mode**: computes and logs, does NOT influence routing

### Remaining Work
- [x] Run TrimR evaluation on math/gpqa suites — ✅ 2026-04-09 (Package B). DeepSeek-R1-Distill-Qwen-7B on 4×48t NUMA. **GPQA**: full 58.3% → think-strip 52.6% → trimr 45.7% (2400 avg think tokens, thinking helps ~6pp). **Math (GSM8K)**: 66% all strategies identical (151 avg think tokens — model barely thinks on easy math). **Verdict**: TrimR valuable on hard tasks, irrelevant on easy tasks. Aligns with difficulty-adaptive routing. Prerequisites resolved: `chat.cpp` PEG parser fix, binary rebuild, `--jinja` in stack, `\boxed{}` scorer fix.
- [x] Collect shadow telemetry from difficulty signal in production — ✅ 2026-04-06. Package A collected 635 routing decisions with shadow predictions.
- [x] Validate difficulty signal predictive power against benchmark accuracy — ✅ 2026-04-06. At old thresholds (0.3/0.6): 92% easy, 0% hard, no predictive spread. Recalibrated to 0.15/0.35 for ~40/40/20 split. Medium prompts take 29% longer (p50 36s vs 25s). Re-validation needed at new thresholds.
- [ ] If validated: implement enforce mode (route easy→worker, hard→architect)
- [x] FlowSteer deep-dive (intake-126) — blocked on Qwen3.5 (no `build_cvec()` in `qwen35.cpp`), but SEAL linear baseline works on dense Qwen3/Qwen2.5 via `--control-vector`
- [ ] Generate SEAL control vectors for Qwen3-32B (Action 8 — 2-day experiment). **Prep DONE 2026-04-09**: `generate_pairs.py` (80 contrastive problems), `eval_cvectors.py` (scaling sweep at 0.3/0.5/0.7), experiment design doc. Awaiting model servers.
- [x] Reasoning length alarm: cancel + re-generate when `<think>` exceeds 1.5× band budget (Action 9) — `_check_reasoning_length_alarm()` in helpers.py, double-gated (feature flag + enforce mode), wired into `_execute_turn()` with retry + conciseness nudge, 9 tests
- [x] Implement n-gram loop detection (Action 4) — added `detect_think_block_loop()` to `quality_detector.py`, 8 tests
- [x] Wire band-adaptive token budgets through difficulty_signal enforce mode (Action 5) — `_repl_turn_token_cap()` now accepts `difficulty_band`, returns band-specific cap when mode=enforce (1500/3500/7000). `TaskState.difficulty_band` propagated from `RoutingResult`. Gated behind enforce mode (no behavior change while shadow).
- [x] Compute Omega metric per-suite — ✅ 2026-04-09 (Package B Phase 4). **Critical finding: 7/10 suites show tools/REPL HURT accuracy vs direct.** Worst: agentic -54.5pp, coder -44pp, general -26pp, math -26pp. Only hotpotqa (+12pp) and gpqa (+6pp) benefit from tools. Implication: default routing should prefer direct mode; REPL/tool use should be opt-in for known-beneficial suites.
- [ ] Summarizer quality assessment — shared with `context-folding-progressive.md` Phase 2 (Claude-as-Judge eval of consolidation across model tiers; SFT data collection mirrors `eval_trimr.py` pattern)
- [x] Audit conciseness prompts: verified stylistic language, not suppression (Action 7). **UPDATE 2026-04-07**: intake-276 deep-dive reveals our "be concise" prompts are the weakest form tested — explicit numeric word limits outperform. See Action 12 below.
- [x] **Action 12: Upgrade conciseness prompts to explicit word limits** — ✅ 2026-04-09. Replaced vague "be concise"/"be direct" with format-specific word limits in worker_general.md (MC: letter+1 sentence, yes/no: answer+1 sentence, factual: <15w, open: <60w) and worker_math.md (MC: letter+1 sentence, numeric: <50w, proof: <100w). Removed "Show work step by step" from worker_math registry suffix (contradicts brevity on easy problems). Based on CCoT (2407.19825) 30-60 word sweet spot and TALE (2412.18547) findings.
- [x] **Action 13: Model-tier-differentiated conciseness** — ✅ 2026-04-09. Audit confirmed existing tier differentiation is correct: architect already has aggressive "<150 tokens" + "maximally concise"; frontdoor stays elaborative (user-facing); coder uses "code only". Updated thinking_reasoning suffix from verbose 4-line instruction to "Think step by step in <think> tags. Answer portion: under 50 words." Applied to all 3 thinking model variants in registry.
- [x] **Action 14: Add OAA metric to eval framework** — ✅ 2026-04-07. `eval_metrics.py` with `compute_oaa()` (α-penalized excess tokens), `compute_pti()` (per-token intelligence), `compute_batch_oaa()` (batch JSONL). CLI: `python eval_metrics.py --results path.jsonl`.
- [x] **Action 16: Answer-tag stop sequences for benchmark scoring** — ✅ 2026-04-09 (orchestrator), ✅ 2026-04-10 (research repo port). Replaced `####` marker with `<answer></answer>` XML tags in all benchmark prompts (GSM8K, GAIA, CRUXEval, SimpleQA, HotpotQA, sentinel questions). Added `</answer>` to `direct_stage.py` stop sequences — generation halts immediately after model emits `</answer>`, eliminating post-answer rumination loops. Scorers (`debug_scorer.py`) default to `<answer>` extraction with `####` legacy fallback. `ChatRequest.stop_sequences` field added for request-level overrides. **2026-04-10**: Ported to `epyc-inference-research` — the research repo's `dataset_adapters.py` and `debug_scorer.py` had diverged and still used `####`. All 7 adapter prompts + extract patterns updated; scorer defaults updated with `####` legacy fallback. Files: orchestrator: `dataset_adapters.py`, `direct_stage.py`, `debug_scorer.py`, `requests.py`, `seeding_orchestrator.py`, `sentinel_questions.yaml`; research: `dataset_adapters.py`, `debug_scorer.py`.
- [x] **Action 15: TALE dynamic budget estimation** — ✅ 2026-04-11 (Package C). 40 questions (math+general), 3 conditions. **Static limits outperform TALE on OAA** (static -3.48 vs TALE -5.95). TALE matches baseline on math (95%) but hurts general (50% vs 95%). Pre-pass adds latency without benefit. **Decision: keep Action 12 static limits, TALE deferred.** Revisit if difficulty_signal improves to enable per-suite policy.
- [x] CMV deep-dive: think block stripping (Action 10) — N/A for our architecture (raw LLM output not carried into next-turn context; REPL stdout is what flows forward)
- [x] CMV output spill with retrieval pointer (Action 11) — `_spill_if_truncated()` in helpers.py, writes full output/error to `/tmp/{task_id}_{label}_t{turn}.txt` + appends `peek()` pointer. Feature flag `output_spill_to_file`. 9 tests.

## Deep-Dive Findings (2026-03-15)

### Action 4: N-gram Loop Detection (from S3-CoT/SEER deep-dive)

**Source**: `research/deep-dives/reasoning-compression-s3cot-adaptive.md`, Path D

**What**: Detect repeated reasoning patterns (n-gram repetition in `<think>` blocks) and truncate. SEER finding: failed outputs are consistently ~1,193 tokens longer than successful ones — length itself is a failure signal.

**Implementation**:
- Add n-gram repetition detector to `session_log.py` or as a post-generation filter
- Detect 3-gram or 4-gram repeats within `<think>` blocks (sliding window)
- When repetition ratio exceeds threshold (e.g., 0.15), truncate reasoning and force answer extraction
- Estimated effort: ~1 day, ~100 lines

**Why not S3-CoT**: S3-CoT's activation steering (VL-D in residual stream) is incompatible with Qwen3.5 hybrid SSM architecture (Mamba2 layers don't have standard residual streams). Only viable for dense models (Qwen3, Llama).

### Action 5: Band-Adaptive Token Budgets (from Overthinking/CIB deep-dive)

**Source**: `research/deep-dives/overthinking-info-bottleneck.md`

**What**: Replace flat REPL token cap (5000) with difficulty-band-adaptive budgets:

| Band | Token Budget | Rationale |
|------|-------------|-----------|
| easy | 1,500 | 92% of correct answers come in first solution round |
| medium | 3,500 | Standard budget |
| hard | 7,000+ | Hard problems need full computation buffer |

**Dependency**: Requires difficulty_signal.py in `enforce` mode (currently `shadow`).

**Implementation**: In `_repl_turn_token_cap()` (`src/graph/helpers.py`), read difficulty_band from routing context and return band-specific cap instead of flat 5000.

**Theoretical backing**: CIB (Proposition 4.1) proves flat token penalties are provably suboptimal. The optimal penalty is semantic — tokens that carry new information should cost less than redundant tokens. Band-adaptive budgets are a practical approximation.

### Action 6: Omega Metric for Reasoning Routing (from Reasoning Recall deep-dive)

**Source**: `research/deep-dives/reasoning-recall-cot-controllability.md`

**What**: Compute per-suite Omega metric (weighted pass@k improvement from reasoning ON vs OFF). Suites with high Omega benefit from reasoning; suites with low Omega waste tokens on reasoning.

**Formula**: `Omega = sum_{k=1}^{N} [k * (pass@k_ON - pass@k_OFF) / pass@k_OFF] / sum_{k'=1}^{N} k'`

**Implementation**: Run `seed_specialist_routing.py` with reasoning ON/OFF for each suite, compute Omega, store as per-suite annotation in model_registry.yaml. Use to validate whether `difficulty_signal.py` bands correlate with actual reasoning benefit.

**Cross-reference**: Feeds into `routing-intelligence.md` Phase 5 (seeding/eval integration).

### Action 7: Controllability Validation (from CoT Controllability deep-dive)

**Source**: `research/deep-dives/reasoning-recall-cot-controllability.md` (Paper 2, OpenAI arxiv:2603.05706)

**Key findings that validate our approach**:
1. **Conciseness prompting is safe**: Stylistic/length control has <=2.7pp accuracy cost. Our worker prompt edits (Action 1) fall in this category.
2. **Content suppression is dangerous**: "Don't reason about X" has 6-16.7pp cost and 0.1-15.4% compliance. Never instruct models to skip specific reasoning steps.
3. **Smaller models are least controllable**: RL-trained 7B-14B models (our workers) are the models LEAST responsive to conciseness prompts. Conciseness gains may be smaller than expected at worker tier.
4. **Computational buffer effect**: Even meaningless tokens improve accuracy by 21-27% on factual recall. Aggressive compression risks removing useful computation.

**Action**: Audit our conciseness prompts to ensure they use stylistic language ("be concise", "focus on key steps") and never suppression language ("don't think about", "skip reasoning for"). Already looks correct but should be verified.

### Action 8: SEAL Control Vectors for Dense Models (from FlowSteer deep-dive)

**Source**: `research/deep-dives/flowsteer-concise-reasoning.md`

**What**: Generate linear control vectors (SEAL baseline) for reasoning conciseness on dense Qwen3-32B using llama.cpp's existing `tools/cvector-generator/`. Contrastive pairs: concise vs verbose reasoning on MATH prompts. Deploy via `--control-vector-scaled`.

**Compatibility**: Dense Qwen3 (`qwen3.cpp` has `build_cvec()`), Qwen2.5 (`qwen2.cpp` has `build_cvec()`). NOT Qwen3.5 (`qwen35.cpp` lacks `build_cvec()` — same S3-CoT/FlowSteer blocker). Quantization: control vectors added in F32 residual stream, should work with GGUF but no published validation.

**FlowSteer MLP (nonlinear)**: Deferred — no llama.cpp infrastructure for MLP ODE solve at intervention points. SEAL is the deployable subset.

**Effort**: ~2 days. Risk: low (worst case: no effect, revert).

### Action 9: Reasoning Length Alarm (from short-m@k deep-dive)

**Source**: `research/deep-dives/short-mk-parallel-reasoning.md`, Phase 0

**What**: When a `<think>` block exceeds 1.5× the band budget tokens and is still generating, cancel the generation and re-generate with a fresh seed. Take the shorter result. This is effectively sequential short-1@2.

**Why it works**: short-m@k paper shows shorter reasoning chains are up to 34.5% more accurate within the same question. Correct reasoning is concise; incorrect reasoning wanders (95-188 backtracks for correct vs 269-352 for incorrect). Easy problems have the highest wrong/right token ratio (2x), making length alarm most discriminative there.

**Three-layer stack** (complementary and additive):
1. Conciseness prompting shifts length distribution leftward (deployed)
2. Band-adaptive budgets cap the right tail (implemented, awaiting enforce)
3. Length alarm + re-generation actively selects for shorter chains (this action)

**Implementation**: ~80 lines in `src/graph/helpers.py`, integrates with `difficulty_signal.py` bands and `detect_think_block_loop()`. Gate behind feature flag. Effort: ~1 day.

**Full short-m@k**: Parallel generation infeasible (architect models run -np 1, VRAM constrained). Sequential short-1@k (Phase 1, ~150 lines) worth trying for math tasks after Phase 0 validates.

### Action 10: Think Block Stripping from Carried Context — N/A

**Source**: `research/deep-dives/cmv-structural-trimming-repl.md`, intake-141 (arxiv:2602.22402)

**Investigation**: CMV's Pass 3 removes `<think>` blocks from carried context. Investigated whether this applies to our REPL architecture.

**Finding**: Does NOT apply. In our architecture, `state.last_output` is the REPL execution stdout (Python code output), not the raw LLM response. The raw LLM response (`raw_llm_output`) is consumed within a single turn for code extraction, FINAL() rescue, and workspace updates, then discarded. Think blocks never leak into subsequent turns. This differs from Claude Code where the full assistant message (including think blocks) stays in conversation history.

### Action 11: Output Spill with Retrieval Pointer — DONE

**Source**: `research/deep-dives/cmv-structural-trimming-repl.md`, intake-140/141

**What**: When REPL output or error exceeds the prompt builder's preview limit (1500/500 chars), write full content to a temp file and append a `peek()` retrieval pointer to the truncated preview. Gives the model agency to access the full output on demand.

**Gap identified**: REPL stdout can be arbitrarily long. The session log only stores 200-char previews. The repl_tap.log is a diagnostic interleaved log, not per-turn queryable. There was no mechanism for the model to access full output from a truncated turn.

**Implementation**:
- `_spill_if_truncated()` in `src/graph/helpers.py` (~30 lines)
- Writes to `/mnt/raid0/llm/tmp/{task_id}_{label}_t{turn}.txt`
- Truncates at `max_chars - 150` to leave room for the pointer within the builder's own truncation limit
- Wired into `_execute_turn()` before `build_root_lm_prompt()` call
- Feature flag: `output_spill_to_file` (production=True, test=False, env=`OUTPUT_SPILL_TO_FILE`)
- 9 tests in `tests/unit/test_output_spill.py`

## Research Intake Update — 2026-04-04

### New Related Research
- **[intake-258] "Think Anywhere in Code Generation"** (arxiv:2603.29957)
  - Relevance: Introduces on-demand inline reasoning during code generation — model learns to invoke `<thinkanywhere>` blocks at high-entropy positions (assignments, returns)
  - Key technique: Cold-start training + RLVR (GRPO with hierarchical rewards) teaches Qwen2.5-Coder-7B to adaptively reason mid-generation
  - Reported results: +18.8pp on LeetCode, +12.2pp on MBPP; 238-306 fewer reasoning tokens than GRPO baseline; upfront thinking shortened ~35-50%
  - Delta from current approach: Our reasoning compression focuses on post-hoc pruning/compression of existing think blocks. Think Anywhere instead trains the model to place reasoning precisely where needed — a complementary angle. The finding that high-entropy positions predict reasoning need could strengthen our difficulty_signal.py routing (currently uses prompt features, not generation-time entropy).

## Notes

This is the most active research front discovered during the 2026-03-14 intake run. 7 of 10 expansion entries cluster around reasoning compression, approaching the problem from different angles. The theoretical foundation (Information Bottleneck, intake-133) explains why: CoT traces contain information about the response that isn't directly accessible from the prompt, so compression is lossy but bounded. The practical implication is that our current REPL token cap (5000 tokens) is a crude version of what these methods do adaptively — we should upgrade to difficulty-aware reasoning budgets.

## Research Intake Update — 2026-04-06

### New Related Research
- **[intake-264] "Embarrassingly Simple Self-Distillation Improves Code Generation"** (arxiv:2604.01193)
  - Relevance: Simplest possible self-distillation — temperature-sample own outputs, SFT on them. No verifier, teacher, or RL needed.
  - Key technique: Simple Self-Distillation (SSD) — resolves precision-exploration conflict by reshaping token distributions contextually
  - Reported results: Qwen3-30B 42.4% → 55.3% pass@1 on LiveCodeBench v6 (+12.9pp); generalizes across 4B-30B scale
  - Delta from current approach: Our Tier 3 (OPSDC, intake-110) requires RL + reward model. SSD achieves meaningful gains with just SFT on self-generated data. The finding that self-generated data beats curated data challenges Doc-to-LoRA data curation assumptions.

- **[intake-266] "A Survey of On-Policy Distillation for Large Language Models"** (arxiv:2604.00626)
  - Relevance: First unified taxonomy of on-policy distillation — contextualizes OPSDC (intake-110) and SSD (intake-264) within f-divergence framework
  - Key technique: Three-axis OPD taxonomy (feedback signal × teacher access × loss granularity)
  - Delta from current approach: Explains why off-policy (static teacher data) causes exposure bias → compounding errors. Validates our Tier 3 direction but suggests teacher-free approaches (SSD) may be underweighted.

### Deep-Dive Correction (2026-04-06)
**Caveat on intake-264 (SSD)**: The 42.4→55.3% LCBv6 result is less impressive than it sounds — Nanbeige-3B (a 3B model) scores 76.9 on LCBv6, and Qwen3-32B baseline is already at 55.7%. Thinking models gain only +2-3pp from SSD. Requires 8xB200 for SFT — not actionable for our inference-only stack. The precision-exploration conflict theory is legitimate but the practical impact is near-zero for GGUF consumers. **Worth monitoring only** for: (a) SSD-trained checkpoints appearing as GGUFs on HuggingFace, (b) inference-time adaptations of the distribution reshaping idea.

**Caveat on intake-266 (OPD Survey)**: Training-only methods exclusively. The exposure bias framing (DAgger bound: on-policy correction reduces error accumulation from O(eT²) to O(eT)) is the main extractable insight — it explains why OPSDC's self-rollout approach works from first principles. The "agent-level distillation" open problem is already addressed by our completed SkillBank pipeline. Useful as a theoretical reference only.

## Research Intake Update — 2026-04-08

### New Related Research
- **[intake-286] "Self-Distilled RLVR (RLSD)"** (arxiv:2604.03128)
  - Relevance: Extends the OPSDC/SSD distillation line — combines self-distillation for token-level magnitude with RLVR for update direction
  - Key technique: RLSD separates environment-anchored update direction (RLVR/GRPO) from self-distilled update magnitude (token-level policy differences). Stop-gradient + clipping on teacher signal.
  - Reported results: Claims higher convergence ceiling and superior training stability vs pure RLVR or pure OPSD
  - Delta from current approach: Extends our Tier 3 understanding (OPSDC, intake-110). Addresses the known OPSD instability (information leakage → progressive collapse) by limiting distillation to magnitude only. Still requires training infrastructure (8x GPU) — not actionable for inference-only stack.
  - Known limitations: OPSD component has structural information leakage risk even with clipping; GRPO's sequence-level credit assignment remains a bottleneck; hyperparameter sensitivity to clipping bounds not fully ablated.
  - Status: MONITOR ONLY — training method, same actionability caveat as intake-264/266.

## Research Intake Update — 2026-04-08

### New Related Research — Memento Cluster (Block-Level Reasoning Compression)

A cluster of 4 closely related papers/repos on training models to self-compress their reasoning chains by segmenting into blocks and generating dense summaries ("mementos"). This represents a new Tier 3+ approach that goes beyond our existing compression taxonomy.

- **[intake-289] "Memento: Teaching LLMs to Manage Their Own Context"** (Microsoft Research)
  - Relevance: Directly applicable — trains models to segment reasoning into blocks, compress each into a memento, mask original block KV states. 2-3x peak KV reduction on Qwen3-8B/32B, Phi-4 14B.
  - Key technique: Dual information stream — memento KV states retain implicit block info even after text masking. Removing this channel drops 15pp on AIME24. Custom vLLM fork with native block masking.
  - Reported results: Qwen3-32B AIME26: -2.6pp at 2x KV reduction. Gap shrinks with scale (-6.3pp@8B → -3.5pp@32B). RL closes remaining gap.
  - Delta from current approach: Our TrimR/FlowSteer operate post-hoc; Memento trains the model itself to compress. Requires SFT on OpenMementos (228K traces, MIT). vLLM-based, not llama.cpp — porting block masking to llama-server is non-trivial but conceptually similar to our ISWA hybrid buffer.
  - Composability: Orthogonal to Hadamard+q4_0 KV quantization — compresses attention span, not precision. Multiplicative savings possible.
  - **New handoff stub created**: `memento-block-reasoning-compression.md`

- **[intake-290] "OpenMementos-228K"** (HuggingFace dataset, MIT)
  - Relevance: Training data for Memento approach. 228K reasoning traces with block boundaries and compressed summaries (54% math, 27% science, 19% code). ~6x trace-level compression.
  - Key technique: 5-stage data pipeline (sentence splitting → boundary scoring → segmentation → summary generation → iterative refinement). Judge-feedback loop: 28% → 92% pass rate.
  - Delta: The data pipeline itself is valuable — could generate context-folding training data (Phase 2) or TrimR evaluation sets.

- **[intake-292] "InftyThink" (ICLR 2026)** (arxiv:2503.06692)
  - Relevance: Predecessor approach — iterative reasoning with periodic summarization. Sawtooth memory pattern. 3-11% improvement on MATH500/AIME24/GPQA.
  - Delta: Text-level only (no KV retention) — Memento shows 15pp loss from missing KV channel. SFT-only (no RL). Peer-reviewed at ICLR.

- **[intake-293] "InftyThink+" (arxiv:2602.06960)** + **[intake-294] "Accordion-Thinking" (arxiv:2602.03249)**
  - Relevance: Add RL to iterative summarization. InftyThink+: 21% AIME24 gain on 1.5B. Accordion: 3x throughput with Fold/Unfold toggle.
  - Delta: All text-level — lack Memento's dual stream. Accordion's Fold/Unfold toggle is the most directly usable pattern for our architecture.

### Impact on Existing Actions
- **Tier 3 taxonomy expanded**: Memento/InftyThink/Accordion form a new sub-family alongside OPSDC (self-distillation) and CoLaR (latent compression). All require training but offer fundamentally different compression vs. inference-only approaches.
- **Context-folding synergy**: OpenMementos' data pipeline (boundary scoring + iterative refinement) validates our Phase 2 approach and could provide training data for Phase 3 RL.
- **KV cache composition**: Memento block masking + Hadamard+q4_0 quantization = multiplicative KV savings. Worth investigating once llama.cpp block masking is feasible.

## Research Intake Update — 2026-04-13

### New Related Research
- **[intake-350] "Latent Briefing: KV Cache Compaction for Multi-Agent Systems"** (github:CuriousCaliBoi/latent-briefing)
  - Relevance: Complements CoLaR (intake-134) as another latent-space approach to reducing inter-agent token overhead. While CoLaR bypasses KV cache via latent reasoning compression, Latent Briefing operates directly on KV cache — compacting an orchestrator's trajectory cache before injecting into a worker agent. Both target the same goal (reduce cost of multi-step reasoning chains) from different abstraction layers.
  - Key technique: Attention-score-driven MAD thresholding + PGD reweighting for cross-model KV transfer
  - Delta from current approach: KV-level technique, not reasoning-level. More relevant to triattention-kv-selection.md handoff. Cross-reference only.

## Research Intake Update — 2026-04-15

### New Related Research
- **[intake-374] "Rethinking Generalization in Reasoning SFT"** (arxiv:2604.06628)
  - Relevance: Directly informs CoT data quality requirements for reasoning compression. Verified long-CoT traces yield consistent cross-domain gains (+8-12% over No-CoT). "Repeated exposure > coverage" — repeating 2.5k samples 8x outperforms one-pass 20k under fixed 640-step budget. Safety degrades as reasoning improves — asymmetric generalization.
  - Key technique: Conditional analysis of SFT generalization across optimization dynamics, data quality, and model capability
  - Reported results: 14B models show 15-20% better generalization than 1.7B; dip-and-recovery trajectory in cross-domain performance during training
  - Delta from current approach: Our Tier 3 approaches (OPSDC, CoLaR) assume SFT generalizes. This paper shows generalization is conditional on data quality and model capability — weaker models may only imitate surface patterns. Relevant for selecting compression training data and evaluating which models benefit from reasoning compression SFT.

- **[intake-378] "On the Role of Reasoning Patterns in the Generalization Discrepancy of Long CoT SFT"** (arxiv:2604.01702) — **UPGRADED to high relevance / new_opportunity after deep dive**
  - Relevance: Contradicts naive "more CoT = better" assumption. DeepSeek-R1's divergent, branch-heavy exploration patterns cause WORSE generalization despite lower training loss. Filtering branch-heavy trajectories improves AIME25 by 5.1%, BeyondAIME by 5.5%.
  - Key technique: Trajectory filtering to remove frequently branching reasoning patterns
  - **Deep dive quantitative findings**:
    - Propose steps: R1=33.3% vs gpt-oss=22.5%; Propose→Propose transition: R1=0.53 vs gpt-oss=0.34
    - Llama3.1-8B: 21pp average gap (29.5% vs 50.5%) from same problem set, same budget, different reasoning traces
    - "Dilution effect": R1's lower SFT loss comes from trivial routine tokens, not better reasoning learning. Low loss is a MISLEADING quality signal.
    - Random 10% step deletion: gpt-oss data degrades significantly (tight dependency); R1 data is unaffected or improves (redundancy confirmed)
    - Filtering by branching keywords ≠ filtering by length — limited overlap between the two filters
  - Delta from current approach: Three actionable implications for our Tier 1 approaches:
    - (1) The random step deletion experiment directly validates TrimR/short-m@k — branch-heavy reasoning IS safe to prune at inference time
    - (2) Branching density (Propose step %) could serve as a runtime quality signal for routing: high branching = unproductive exploration → truncate or escalate
    - (3) If we use R1-distilled data (OpenR1-Math-220k) for any future training, must filter by branching density first
  - **Deep dive**: `research/deep-dives/sft-generalization-reasoning-patterns.md`

- **[intake-374 supplement] "Data Repetition Beats Data Scaling in Long-CoT SFT"** (arxiv:2602.11149, not yet in index)
  - Independent confirmation: 128 epochs on 400 samples beats 1 epoch on 51,200 samples by 12-26pp on AIME'24/25 (Kopiczko et al., Qualcomm). Token accuracy serves as saturation indicator. No increased catastrophic forgetting.

### Training Data Strategy (intake-374/378/2602.11149 synthesis)

For any future Tier 3 training (OPSDC, CoLaR, SEAL SFT, RLVR):

1. **Depth > breadth**: 128 epochs on 400 curated samples beats 1 epoch on 51.2k by 12-26pp (arxiv:2602.11149, confirmed by intake-374's "2.5k × 8 > 20k × 1" finding). Don't scale data beyond saturation.
2. **Filter by branching density**: Use intake-378 Proxy 2 (branching keyword proportion) to remove divergent, branch-heavy traces before training. DeepSeek-R1 traces produce 21pp worse generalization than convergent traces on Llama3.1-8B — even with identical problems and budget.
3. **Token accuracy = saturation indicator**: Stop adding epochs when token accuracy plateaus. Beyond saturation, additional epochs waste compute without generalization gains.
4. **Safety evaluation mandatory**: Reasoning SFT asymmetrically improves reasoning while degrading safety (intake-374). Any future fine-tuning must include safety benchmarks alongside capability measurement.

### Formalizer Complements Compression (cross-reference)

The formalizer pipeline (`mathsmith-hc-formalizer-eval.md`, `src/formalizer.py`) reduces overthinking at the source — complementary to, not competing with, Tier 1-3 compression:

- **Formalizer** reduces INPUT ambiguity: fills in missing premises, clarifies constraints → solver doesn't waste tokens exploring alternative interpretations
- **Compression** reduces OUTPUT tokens: prunes redundant reasoning after generation (Tier 1), steers toward conciseness (Tier 2), or trains for shorter traces (Tier 3)

Theoretical link: CIB (Conditional Information Bottleneck, `research/deep-dives/overthinking-info-bottleneck.md`) shows formalizer raises I(Z; Y | X), which Proposition 4.1 proves reduces optimal reasoning length. The S4 A/B test in the formalizer handoff should measure total pipeline token cost (formalizer + solver) vs solver-only baseline, at equal or better accuracy — providing empirical validation. Source: user insight connecting arxiv:2504.06514 (missing premises → overthinking) to formalizer value proposition.
