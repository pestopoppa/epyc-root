# Benchmark Methodology

**Category**: `benchmark_methodology`
**Confidence**: verified
**Last compiled**: 2026-04-27 late-evening
**Sources**: 36 documents

## Summary

The project uses a purpose-built 8-suite (expanded to 23-suite) benchmarking framework to evaluate models for specific roles in the multi-model orchestrator. Unlike generic leaderboard benchmarks (MMLU, HumanEval), each suite tests a capability that maps directly to an agent role: can a model follow precise formatting (instruction_precision), chain multi-step reasoning (thinking), generate working code (coder), or produce valid tool calls (agentic). 61 baseline models have been evaluated across 381 total configurations.

The framework operates on two parallel scoring tracks. The `v1/` track uses Claude-as-Judge with a 0-3 rubric for open-ended quality assessment, chosen after experiments showed algorithmic scoring severely underscored models (38% vs 89% for the same output). The `debug/` track uses deterministic machine verifiers (multiple_choice, exact_match, code_execution, substring, programmatic, f1, llm_judge) for automated regression testing and MemRL reward injection without API costs. The deterministic pool now contains 56,448 questions across 23 suites, with 577 curated YAML questions and 55,871 drawn from HuggingFace datasets via runtime adapters.

Cost-aware reward design is layered on top of benchmark results for the MemRL routing system. The reward formula `quality_base - lambda * max(0, cost_ratio - 1.0)` gates cost penalties behind correctness, following the industry consensus established by xRouter (Salesforce), RouteLLM (LMSYS/ICLR 2025), and FrugalGPT (Stanford). Lambda=0.15 creates meaningful cost differentiation across the 13.4x speed range of the model pool (frontdoor at 18.3 t/s vs architect at 6.75 t/s) without overwhelming quality signal. Extended reward dimensions cover quality-gap penalty (over-qualified model selection), memory-tier penalty (WARM when HOT suffices), and web research effectiveness (source diversity, completeness, query strategy).

Benchmark hardening in December 2025 addressed ceiling effects where top models scored 89-93%. Every tier was bumped up one difficulty level with post-doctoral T3 questions added, spreading the score distribution meaningfully across model classes. A mode-advantage suite (90 questions) was specifically designed to produce strong routing signal for MemRL by including tasks that structurally require specific execution modes (react, REPL, delegation, specialist escalation).

## Key Findings

- Claude-as-Judge scoring achieves semantic understanding of correct answers in unexpected formats, providing consistent 0-3 graded evaluation. Algorithmic pattern matching underscored by 51 percentage points on the same output in early experiments. [06-benchmarking-framework.md]
- Benchmark hardening eliminated the 89-93% ceiling effect. Expected post-hardening ranges: 30-50% for draft models (0.5-1.5B), 50-70% for general models (4-8B), 60-80% for specialized thinking models (8B+), 70-85% for large models (14B+). No model hits 90%+. [06-benchmarking-framework.md]
- Speculative decoding preserves quality (same model) while delivering 10x speed. MoE expert reduction trades quality for speed in a predictable curve: MoE4 at 85% quality/33.6 t/s, MoE3 at 78%/37.7 t/s vs baseline 89%/2.89 t/s. [06-benchmarking-framework.md]
- Instruction precision is the hardest gate for orchestration: models scoring below 70% are disqualified from frontdoor/dispatcher roles. All three coder quants (Q4KM, Q8, f16) hit an identical ceiling of 20/33 on instruction_precision -- this is a model-level weakness, not quantization-dependent. [07-benchmark-suite-construction.md, numa-orchestrator-deployment.md]
- Agent-generated benchmark questions had significant error rates: 2 answer errors in math and 17 answer errors across 76 mode-advantage tasks. All expected answers must be verified by computation, especially for modular arithmetic, financial calculations, and combinatorial counting. [07-benchmark-suite-construction.md]
- The 3-way seeding evaluation uses binary rewards (1.0/0.0) for Q-value updates to keep Q-values as faithful P(success) estimates, storing cost metrics separately in episodic memory. Cost is applied at routing time, not during learning, enabling later Optuna threshold tuning without retraining. [08-cost-aware-rewards.md]
- Nine suites now sample fresh questions from HuggingFace datasets on each run, totaling 35,560+ questions from MMLU (14K), ARC-Challenge+HellaSwag (11K), HotpotQA (7.4K), SimpleQA (4.3K), and others. Static YAML fallback for agentic, long_context, mode_advantage, web_research, and skill_transfer. [07-benchmark-suite-construction.md]
- Scoring propagation bug (fixed 2026-03-03): `question_pool.py` defaulted per-question scoring to `exact_match` ignoring YAML top-level defaults. This caused 50 web_research questions to be silently scored with exact_match instead of F1. [07-benchmark-suite-construction.md]
- SpecExec thesis partially refuted on EPYC 9655: verification cost scales 4-5x from N=1 to N=64 for Q4_K_M models. Only f16 models show near-flat behavior (1.69x at N=64). Dequantization compute overhead prevents the pure bandwidth-bound regime SpecExec assumes. [specexec-verification-profile.md]
- Optimal K for linear speculation is 16. Increasing draft-max from 16 to 256 provides zero throughput benefit because acceptance rate decay of linear sequences neutralizes verification cost savings. Tree speculation is the only path to more accepted tokens per round. [specexec-verification-profile.md]
- Self-speculation (layer skip) is not viable on either hybrid SSM or dense architectures without early-exit fine-tuning. Hybrid models suffer from SSM checkpoint/restore overhead (-44% to -52%). Dense models achieve near-zero acceptance rates (0.5-1.5%) because intermediate logits are untrained for next-token prediction. [self-speculation-benchmark.md]
- Draft model selection matters more than K: Qwen2.5-Coder-0.5B at 185 t/s with 91% acceptance dramatically outperforms Qwen3.5-0.8B at 44 t/s with 73% acceptance. The fastest drafter and best-matched target pair yield more gain than any tree or K optimization. [specexec-verification-profile.md]
- Comprehensive sweep (1,290 measurements) showed previously assumed optimal params were mostly wrong: coder tree helps contrary to prior assumption (ps=0.05 wins), 480B tree is harmful (-19%) contrary to prior assumption, and registry throughput values were inflated 2.3-3.6x from warm-cache single-prompt measurements. [progress/2026-03-21]
- The benchmark/seeding control-plane test infrastructure has achieved 100% coverage on all 10 seeding modules (`seeding_checkpoint`, `seeding_eval`, `seeding_infra`, `seeding_injection`, `seeding_legacy`, `seeding_orchestrator`, `seeding_rewards`, `seeding_scoring`, `seeding_tui`, `seeding_types`) plus `eval_log_format` via 167+ characterization tests (tranches A-I, 2026-04-14). All original 7 enforced orchestrator slice files also hold at 100%. Coverage was achieved test-only (no runtime behavior modifications) despite CRITICAL blast radius on key symbols like `_eval_single_config`, `evaluate_question_3way`, and `_precompute_embedding`. [integration-test-coverage.md, progress/2026-04-14 sessions 7-17]
- Specialist routing entrypoints (`seed_specialist_routing.py`, `seed_specialist_routing_v2.py`) advanced to 78%/76% coverage through tranches J-L, characterizing main() branches, debug-replay paths, evolve initialization failures, continuous-mode loops, preflight/resume handling, and v2 helper surfaces. Remaining gaps are concentrated in high-complexity replay/evolution hooks. [progress/2026-04-14 sessions 18-20]
- Integration test infrastructure (61 tests, 2026-04-13) uses a real `REPLEnvironment` with mock LLM primitives (`MockLLMPrimitives`), real in-memory `StubFailureGraph`/`StubHypothesisGraph` implementations (not MagicMock), and FastAPI `TestClient` with dependency overrides. This design principle -- "REPL is real, only LLM calls are mocked" -- allows testing the full graph execution loop while remaining independent of inference servers. [integration-test-coverage.md]
- Scoring Verifiers 4-metric protocol (Top-1, Bottom-1, Spearman rho, MAE) establishes that accuracy alone is insufficient for verifier evaluation: SWE-RM showed identical-accuracy verifiers producing opposite RL outcomes (AUC 0.805 smooth vs 0.710 collapse). Reasoning models dominate verification by 5-9pp. Self-evaluation bias degrades Top-1 by 10-15pp. [eval-tower-verification.md]
- Terminal-Bench 2.0 introduces outcome-driven verification (test final container state, not intermediate commands), container-per-test isolation, and three-property test design (specificity, solvability, integrity). The reward file mechanism (`reward.json` with graded metrics) is applicable to T1/T2 eval tiers needing partial credit. [integration-test-coverage.md]
- Math-Verify symbolic comparison fixes a 66% underestimation in math scoring: accuracy 0.1328 vs lm-eval-harness 0.0802 on MATH dataset. Three-step cascading comparison (string, numeric, symbolic) handles LaTeX, equivalent expressions, set notation, and percentages. Critical caveat: NOT thread-safe (`signal.alarm()`). [math-verify-integration-analysis.md]
- **DeepPlanning's rule-based deterministic scoring eliminates LLM-as-judge variance for constraint satisfaction tasks.** Every score is computed by programmatic Python rules that check constraints against the agent's output -- no inter-rater disagreement, no stochastic variance, O(1) compute per evaluation. The 8-dimension commonsense taxonomy (route consistency, sandbox compliance, itinerary structure, time feasibility, business hours, duration rationality, cost calculation, activity diversity) with 21 checkpoints provides a concrete template for building rule-based benchmark suites. All-or-nothing dimension scoring is harsh but realistic -- a plan with one temporal overlap is a broken plan. [deepplanning-agent-benchmark.md](../research/deep-dives/deepplanning-agent-benchmark.md)
- **Case accuracy vs composite reveals a critical evaluation gap.** DeepPlanning's 26-model leaderboard shows models scoring 60-80 composite (average constraint satisfaction) with near-zero case accuracy (all constraints satisfied simultaneously). The pattern holds across model families: Gemini-3-Pro-Preview achieves 41.8 composite but 0.7% travel case accuracy. This directly motivates adding case-level "all-pass" binary metrics alongside averaged quality scores in the eval tower. A growing composite-vs-case gap indicates fragility inappropriate for deployment. [deepplanning-agent-benchmark.md](../research/deep-dives/deepplanning-agent-benchmark.md)
- **Simula's double-critic rejection sampling addresses sycophancy bias in LLM-as-judge scoring.** Instead of a single "Is this correct?" assessment, two independent queries are made: "Is this CORRECT?" and "Is this INCORRECT?". Accept only when critics agree (Critic 1 YES, Critic 2 NO). A sycophantic model saying "yes" to both triggers rejection. Empirical validation on MATH: positive lift exists whenever `p(accept|correct) > p(accept|incorrect)`. LEXam shows correct failure mode: 61% rejection rate when teacher accuracy is only 57%. Cost is 2x judge inference per scored item. Applicable to Q-Scorer quality verification with prompt-only changes. [simula-synthetic-data-generation.md](../research/deep-dives/simula-synthetic-data-generation.md)
- **Simula's calibrated Elo complexity scoring enables principled difficulty stratification.** Batch-wise pairwise scoring aggregated into per-sample Elo ratings provides calibrated, cross-dataset complexity comparisons. Validation: model-assigned Elo aligns with human-annotated complexity labels on MATH (5-level) and Global MMLU (education levels). Rejected samples have systematically higher Elo scores than accepted ones. For EPYC: a `complexity_scorer.py` utility could stratify any benchmark suite by difficulty band, enabling adaptive testing that starts at medium difficulty and escalates/de-escalates based on model performance. [simula-synthetic-data-generation.md](../research/deep-dives/simula-synthetic-data-generation.md)
- **New model quality benchmarks reveal critical serving infrastructure gaps (2026-04-19).** Five models (M2.7, Qwen3.6, SG4-31b, SG4-26b-MM, SG4-26b-Q4KM) required iterative debugging: Gemma4 needed `use_chat_api + repeat_penalty 1.05 + reasoning off + KV q8_0`; Qwen3.6 entered `<think>` loops until `use_chat_api + reasoning off`; M2.7 needed `--jinja` for correct template (37% training data leakage without it). SG4-26b Q4KM proved irrecoverable (16.2%) and was deprecated. The benchmark infrastructure gained `--all-suites`, `--spec-type` passthrough, binary peak search for lookup_ngram sweeps, and per-model `disable_thinking`/`repeat_penalty` support. [progress/2026-04-19](../progress/2026-04/2026-04-19.md)
- **Context-regime coverage is now mandatory before any class-level CPU optimization conclusion (CPU23 protocol)**. A track may not claim closure or class-wide deployment guidance unless 2K/8K/32K + long-prompt-mid-stream interference were all measured AND the conclusion direction is stable across regimes (or explicitly split by regime). Prevents decode-only overgeneralization. **The CPU23 closure scope is the 3-proxy minimum-gate** (sync-bound MoE Coder-30B Q4_K_M + BW-bound MoE Qwen3.6-35B Q8_0 + dense/hybrid Qwen3.6-27B Q8) measured on 4 metrics × 3 regimes (Phase 2.2, 2026-04-28). **Explicitly NOT a class-wide closure**: Next-80B Q4_K_M, REAP-246B Q4_K_M, gemma-26B Q4_K_M, dense 32K throughput, and multi-concurrent-decode interference are deferred. The earlier 2026-04-27 partial probe on `-pg pp,tg` mode (combined prefill + 32-token decode) tested only 3 regimes × 1 metric × 2 model proxies and was DOWNGRADED on peer review (closure inflation). [cpu-context-regime-coverage.md]
- **Apples-to-apples build flags are required for any bit-exactness validation**. A 0.116-PPL chunk-1 discrepancy that initially looked like a NUMA_MIRROR Phase 1a regression was traced to pure `-march=znver5` codegen drift in fp ops vs an unflagged `-O3` build. Building a third `build_znver5/` baseline (znver5 only, no MIRROR) restored bit-exactness. The lesson: any baseline comparison for a feature flag MUST hold all OTHER compile flags constant. PPL determinism is real (re-running the same build twice produces byte-identical output), so any non-zero delta between two builds points to a real code/codegen difference, but that difference may not be the feature you intended to test. [progress/2026-04-27]
- **Closure language must enumerate which gates were met, not extrapolate**. Peer review on 2026-04-27 identified 10 closure-inflation events across CPU21/22/23/24/25 where one falsified hypothesis was generalized to a broader exhaustion conclusion: CPU22 closed by inference (15% sync ceiling) without running its own gate (≥10% on 2 sync-bound models, no crash, PPL bit-exact); CPU23 marked complete after 3 of 4 regimes × 1 of 4 metrics × 2 of 5 models; CPU24 attribution incomplete on MiniMax + 2-rep stability; CPU21 narrowed scope from libgomp+libomp matrix to libgomp only without acknowledging the gap. Remediation policy: any closure claim must explicitly enumerate which gates were met AND which were not, OR be explicitly downgraded from "closed" to "partial" or "needs revalidation". CPU20 protocol updated with retroactive artifact-bundle backfill rule. [cpu-benchmark-rigor-and-revalidation.md, progress/2026-04-27]
- **Retroactive artifact-bundle backfill is acceptable; papering over is not**. CPU20 mandates seven required artifact files per closure (README.md, system-state.txt, process-pre.txt, process-post.txt, ld_debug.log, results.csv, decision.md). When a track is already declared closed before the protocol was enforced, the backfill rule is: either reconstruct each file from existing logs + a fresh system-state snapshot + a re-run smoke command for `ld_debug.log`, OR explicitly downgrade from "closed" to "needs revalidation" with a `decision.md` stating "retroactive backfill incomplete; track downgraded". Creating empty placeholder files or fabricating decision.md without supporting artifacts is NOT acceptable. CPU21/23/24/25 are tracked for backfill in remediation Phase 2.5. [cpu-benchmark-rigor-and-revalidation.md]
- **≥5 reps required for sub-5% throughput deltas on this hardware**. Discovered via CPU22 Phase 3: an initial 3-rep Next-80B Q4_K_M measurement showed env=1 = 22.65 t/s vs env=0 = 21.31 t/s (+6.3%, would have been a positive signal for the work-stealing prototype). Re-running both at 5 reps converged to ~23.3 t/s (Δ -0.3%, neutral). The 3-rep result was a measurement artifact from cache-warmup state divergence between consecutive runs. **Rule**: 3 reps is fine for ≥10% deltas; for sub-5% deltas use ≥5 reps; for ≤2% claims consider ≥10 reps. Always report std alongside mean. [data/cpu_optimization/2026-04-28-cpu22-work-stealing/]
- **First-decode TTFT amplification under concurrent prefill is class-dependent**. CPU23 Phase 2.2 measured the long-prompt-mid-stream interference scenario via `llama-server --parallel 2`: rep-1 decode under concurrent 30K-token prefill showed 9.6× TTFT amplification on sync-bound MoE Coder-30B (4.77 t/s vs baseline 47.99), 1.15× on BW-bound MoE Q8 frontdoor, 1.08× on dense/hybrid. Steady-state continuous batching is essentially baseline (±2%) on all 3 classes — rep-2-onward decodes interleave efficiently with ongoing prefill. Per-iter latency variance in single-user mode (no interference) is uniformly low (CV 0.24-0.57%), so variance alone is NOT a stall signal absent active interference — the rep-1 stall is specifically a continuous-batching scheduler-wait artifact. [cpu-context-regime-coverage.md, data/cpu_optimization/2026-04-28-cpu23-interference-metrics/]
- **Sibling-directory `.md` references inside artifact-bundle READMEs need the agents_reference_guard hook to resolve relative-to-file-dir, not just relative-to-PROJECT_DIR**. Discovered when CPU21 Phase 2.1 README's reference to `decision.md` (sibling file in same dir) was rejected by the hook because it resolved to `$PROJECT_DIR/decision.md` (doesn't exist) instead of `$DIR/decision.md` (exists). Hook fix landed in commit `12b1e27`: try the file's own directory first, then fall back to `$PROJECT_DIR`. Strictly additive — anything that resolved before still resolves. [scripts/hooks/agents_reference_guard.sh]

## Actionable for EPYC

- The deterministic debug suite (577 curated + 55,871 HF-backed questions) enables fully automated regression testing and MemRL reward injection without Claude API costs. Any new model entering the stack can be benchmarked end-to-end with `run_overnight_benchmark_suite.sh`.
- Stratified tier sampling (`--stratify-tiers`) should be used for suites with real tier metadata (MMLU, Math, IFEval) to ensure balanced difficulty representation. Other suites fall through to uniform random.
- The mode-advantage suite provides strong MemRL routing signal by shifting the reward distribution from ~5% specialist-wins to ~25-35%, enabling the router to learn when to route rather than just that routing has a cost.
- All benchmark throughput values MUST be verified by sweep at deployment thread counts, not extrapolated from different configurations. The 2026-03-21 sweep corrected 3.6x inflated coder throughput that was biasing Q-scorer routing decisions.
- The test coverage strategy for benchmark control-plane code uses risk-weighted classification: must-test branches (recovery paths, failure control-plane, parsing fallbacks) are prioritized over acceptable-gap branches (import fallbacks, portability paths, environment-specific branches). Gate floors are raised incrementally only after corresponding test tranches land, not by forcing brittle branch-chasing. At least one dead code path was identified and fixed through this process (`output_parser.py` `common_perf_print` break shadowed by earlier skip pattern).
- Math-Verify integration (Apache-2.0, pip install + ~10-line change) should replace binary exact-match in `score_answer_deterministic()` for math suites. The 66% underestimation directly affects routing decisions. Thread safety workaround required if `_eval_question()` uses threading.
- The Scoring Verifiers 4-metric protocol (Top-1, Bottom-1, Spearman rho, MAE) should be adopted as the standard for evaluating any new verifier before it enters the RLVR pipeline. ECE and AUC tracking (EV-2, implemented) provide the calibration infrastructure.
- Terminal-Bench's outcome-driven verification pattern should be adopted for new llama-server integration tests. Container-per-test infrastructure deferred until measured need. The task.yaml metadata pattern is worth adopting for test classification across the integration test suite.
- Future work: dynamic lambda by task priority (interactive=higher lambda, batch=lower), multi-objective Pareto frontier maintenance, token-level cost accounting (prompt vs completion), and cache-aware cost reduction with RadixAttention.

## Scoring Verifiers Evaluation Protocol

The Scoring Verifiers framework (COLM 2025, NVIDIA Research) establishes a 4-metric evaluation standard for verifier quality that goes beyond simple accuracy. Accuracy alone is insufficient: SWE-RM demonstrated empirically that two verifiers with identical accuracy can produce completely different RL training outcomes (AUC 0.805 smooth training vs AUC 0.710 training collapse).

The four metrics are: **Top-1 Accuracy** (can the verifier identify the best solution), **Bottom-1 Accuracy** (can it identify the worst solution), **Spearman rho** (rank correlation between predicted and ground truth ordering), and **MAE** (score accuracy vs actual pass rate). Together these capture selection quality, rejection quality, full ordering quality, and calibration accuracy.

Key results: reasoning models dominate verification by 5-9 percentage points (o3-mini 88.2% Top-1 vs Qwen2.5-Coder-32B 79.1%). Distilled reasoning provides almost no benefit (78.2%) -- full reasoning is required. Test case scaling curves show standard models plateau at 15-20 test cases while reasoning models keep improving past 25; the sweet spot is 15 tests with a reasoning verifier. A critical methodological finding: never show the candidate solution to the test generator, as this causes 10-15pp Top-1 degradation from self-evaluation bias. Quantile selection (5 quality-stratified solutions per problem at 0%, 25%, 50%, 75%, 100% pass rates) is the recommended evaluation methodology.

Benchmark datasets are available at HuggingFace `nvidia/Scoring-Verifiers`: HE-R (164 problems, ~9.6 tests/problem), HE-R+ (164, ~764 tests/problem), MBPP-R (978, ~3.0 tests/problem), and MBPP-R+ (378, ~108.5 tests/problem).

> Source: [Eval Tower Verification](/workspace/handoffs/active/eval-tower-verification.md) -- intake-367/368, 4-metric protocol, reasoning model dominance, SWE-RM calibration gap

## Terminal-Bench Test Methodology Patterns

Terminal-Bench 2.0 (arxiv:2601.11868) provides five patterns directly applicable to the eval and integration test infrastructure:

1. **Outcome-driven verification** -- tests verify the FINAL STATE of a container, not intermediate commands. This contrasts with the current integration test approach (mock LLM calls, check return values) and recommends adding tests that start real servers, run operations, and verify end state.
2. **Container-per-test isolation** -- Docker per task with pinned dependencies and no shared state between tests. This is the biggest infrastructure gap relative to the current mock-based test suite.
3. **Three-property test design** -- Specificity (accept ALL correct end states), Solvability (oracle solution exists), Integrity (cannot cheat by shortcuts). These properties should be formalized for T0/T1/T2 eval tiers.
4. **Reward file mechanism** -- `reward.json` with graded metrics instead of binary pass/fail. Applicable to T1/T2 eval tiers that need partial credit scoring.
5. **Structured task.yaml metadata** -- difficulty, timeout budget, category tags, expected duration. Could inform a test registry for the integration test suite.

Terminal-Bench also defines an 8-category failure taxonomy (Disobey Task Specification, Step Repetition, Context Loss, Premature Termination, and 4 others) that maps to orchestrator failure modes. The recommendation is to adopt outcome-driven verification for new llama-server integration tests, defer container-per-test infrastructure until measured need (current mock-based tests provide fast CI), and adopt task.yaml metadata for test classification.

## Tulving Episodic Memory Benchmark

The Tulving Episodic Memory Benchmark (arXiv 2501.13121, ICLR 2025) introduces a complementary evaluation paradigm to the existing RULER/NIAH/LongBench/ZeroSCROLLS suite. Where those benchmarks test retrieval ("find the needle"), Tulving tests episodic memory: can a model track entity states across 200 chapters and order events chronologically? The benchmark generates synthetic book-like narratives with controlled ground truth (dates, locations, entity names, event contents) using a skewed geometric distribution for entity frequency, enabling multi-occurrence tracking evaluation.

Two metrics: **Simple Recall Score** (F1 grouped by matching event count bins: 0/1/2/3-5/6+, averaged across bins) and **Chronological Awareness Score** (average of Latest State score and Kendall τ temporal ordering score). The chronological score is dramatically harder — even GPT-5 only achieves 0.804 vs 0.942 recall. 11 datasets span 10K-1M tokens across 4 narrative styles (default, world news, sci-fi, ordered).

Key findings for benchmark methodology:
- **95% deterministic scoring.** Ground truth items are specific tokens (dates, location names, entity names). Exact + normalized string matching covers ~95% of cases. The LLM-as-judge handles only ~5% partial matches (e.g., "Bethpage State Park" vs "Bethpage Black Course" = 0.5). This aligns with our ch07 deterministic scoring philosophy.
- **Sharp cliff between 10K and 100K tokens.** Single-event recall drops 15pp, multi-event recall drops 31-33pp from 10K→100K (GPT-4o). This is a cliff, not gradual degradation. Only Gemini-2.5 family survives with <2% recall loss.
- **Reasoning models catastrophically fail at long context.** DeepSeek-R1 drops from 0.988→0.572 recall (-42%) and 0.964→0.147 chronological (-85%) from 10K→100K. o1 drops -61%/-95%. o1-mini drops -64%/-96%. These models excel at short-context episodic tasks and collapse at 100K — their effective context utilization windows are much shorter than advertised context lengths.
- **RAG chunk granularity is critical.** Chapter-level RAG (event-boundary-aligned) matches in-context performance (0.82 vs 0.81 F1). Paragraph-level RAG degrades to 0.60 because event information distributes across paragraphs. Event-boundary-aligned chunking >> fixed-size chunking for episodic tasks.
- **Fine-tuning fails for episodic knowledge.** GPT-4o-mini fine-tuned on single-event QA achieves 0.83 F1 on single-event questions but 0.00 on hallucination avoidance (0-event questions) and 0.19-0.37 on multi-event. It memorizes single facts without temporal/relational understanding.

Pre-generated datasets are available on Figshare (MIT license). Integration into our harness requires: download 20ch dataset, llama-server adapter, deterministic F1 scorer, suite registration. The 200ch variant is proposed as a YaRN context extension quality gate (P3b in research-evaluation-index).

> Source: [intake-408](/workspace/research/intake_index.yaml) -- arXiv 2501.13121, ICLR 2025; [decision-aware-routing.md](/workspace/handoffs/active/decision-aware-routing.md) -- routing intelligence data; [research-evaluation-index.md](/workspace/handoffs/active/research-evaluation-index.md) P3b -- integration plan

> Source: [Integration Test Coverage](/workspace/handoffs/active/integration-test-coverage.md) -- intake-369, Terminal-Bench 2.0 methodology patterns, outcome-driven verification, container-per-test, three-property test design

## Math-Verify Integration for Math Benchmarks

Math-Verify (HuggingFace, Apache-2.0) provides robust symbolic math comparison that addresses a critical scoring gap: current binary exact-match scoring underestimates model capability by approximately 66% on math questions (Math-Verify accuracy 0.1328 vs lm-eval-harness 0.0802 on MATH dataset). This underestimation affects routing decisions and model selection.

The library implements a three-step cascading comparison: string match, then numeric comparison, then symbolic simplification with specialized handlers for relations, sets/intervals, matrices, and symbols. It correctly handles LaTeX-formatted answers vs plain text, equivalent expressions ("2x+1" vs "1+2x"), numeric precision ("0.333" vs "1/3"), set notation ("{1,2,3}" vs "{3,2,1}"), and percentage equivalence ("9%" = "0.09" = "9/100").

Critical integration caveats: (1) `verify(gold, pred)` is NOT symmetric -- gold answer must always be the first argument, (2) NOT thread-safe due to `signal.alarm()` usage -- if `_eval_question()` uses `ThreadPoolExecutor`, must switch to multiprocessing or set `timeout_seconds=None` with external timeout, (3) open interval "(1,2)" converts to `Tuple(1,2)` which could false-positive for coordinate pairs, (4) dependency on ANTLR4 runtime. Integration is low effort (pip install + ~10-line change in `score_answer_deterministic()`) with a fallback to exact match if Math-Verify fails.

A complementary tool, MathQ-Verify (arxiv:2505.13903), verifies question quality rather than answer quality via a 5-stage pipeline. Ablation shows Stage 5 (completeness) actually hurts F1 by +0.57pp -- deploy stages 1-4 only. A referenced finding (arxiv:2504.06514) shows that questions with missing premises cause models to generate MORE reasoning tokens, meaning filtering flawed questions also reduces inference cost.

**NIB2-03 audit applied stages 1-3 to the EPYC question pool (2026-04-21)**: 5,670 math-suite questions (aime + math + olympiadbench + physreason) scanned via `scripts/benchmark/dataset_audit/mathq_verify_audit.py`; 251 flagged (4.43%). Stage 4 (symbolic consistency between atomic assumptions and conclusions) deferred because it requires LLM-based decomposition. Signal finding: GSM8K's use of `$` as a **currency** symbol (`$10`, `$68`) collides with LaTeX math delimiters — 244 flags on the `math` suite alone. The heuristic is correct but the prompts are legible; mitigation is to gate the unbalanced-`$` check on prompts that also contain LaTeX commands. Smaller false-positive signal on AIME's `\sqrt{N}` shapes (~10 flags) will be tightened in a v2 pass. Without a working `antlr4-python3-runtime`, sympy-level parse validation is skipped to avoid flooding false positives. [`progress/2026-04/mathq-verify-audit-2026-04-21.md`]

> Source: [Math-Verify Integration Analysis](/workspace/research/deep-dives/math-verify-integration-analysis.md) -- intake-377/379, symbolic comparison, 66% underestimation fix, thread safety caveats

## Open Questions

- Claude-as-Judge integration with graded quality scores (0-3) combined with cost penalty is implemented but disabled. Enabling it would provide richer signal than binary pass/fail + cost but adds API cost.
- The llm_judge scoring method (using local worker model for physics/math semantic equivalence) has unknown accuracy compared to Claude-as-Judge. Validation data needed.
- Adaptive per-call timeouts during 3-way seeding may mask genuine infrastructure issues vs genuinely slow models. The boundary between legitimate slow generation and stalled inference is unclear.
- Optuna threshold optimization for separated Q-values and cost metrics is designed but not yet implemented.
- Remaining integration test gaps (real LLM output parsing, think-harder config with actual CoT injection, budget controls with realistic token counts, streaming chat) require a running inference stack. Should these be maintained as a separate `@pytest.mark.integration_live` tier?
- The post-AR-3 analysis index defines 7 phases with 11 go/no-go metrics. Can this checklist-driven analysis pattern be generalized to future multi-day inference campaigns?
- What is the actual impact of Math-Verify's 66% underestimation correction on routing decisions? Do models currently penalized on math suites recover meaningfully when scored with symbolic comparison?
- Should Terminal-Bench's container-per-test pattern be adopted for llama-server integration tests, or does the current mock-based approach provide sufficient coverage?
- Can Simula's double-critic pattern be applied to the Q-Scorer without architectural changes (prompt-only modification)? What is the agreement rate and how does disagreement frequency correlate with model reliability?
- Should case-level "all-pass" binary metrics be added to the eval tower alongside averaged quality scores? DeepPlanning shows composite-vs-case gap is a fragility indicator.
- What is the optimal batch size for Elo complexity scoring of benchmark questions? Simula uses K appearances across batches to reduce noise -- what K is practical for our local LLM throughput?

## Related Categories

- [Hardware Optimization](hardware-optimization.md) -- benchmark results directly depend on NUMA configuration, thread counts, and memory topology
- [Speculative Decoding](speculative-decoding.md) -- acceleration methods benchmarked across all suites
- [Routing Intelligence](routing-intelligence.md) -- MemRL Q-values derived from benchmark reward signals
- [Cost-Aware Routing](cost-aware-routing.md) -- reward formula design and cost normalization
- [MoE Optimization](moe-optimization.md) -- expert reduction benchmarked for quality/speed trade-offs

## Source References

- [Chapter 06: Benchmarking Framework](/mnt/raid0/llm/epyc-inference-research/docs/chapters/06-benchmarking-framework.md) -- Claude-as-Judge methodology, 8-suite framework, quality vs speed trade-offs, orchestrator benchmark pipeline
- [Chapter 07: Benchmark Suite Construction](/mnt/raid0/llm/epyc-inference-research/docs/chapters/07-benchmark-suite-construction.md) -- Deterministic scoring, 23-suite pool (56,448 questions), HuggingFace adapters, reconstruction instructions
- [Chapter 08: Cost-Aware Reward Design](/mnt/raid0/llm/epyc-inference-research/docs/chapters/08-cost-aware-rewards.md) -- Reward formula, cost normalization, industry consensus, extended reward dimensions
- [Self-Speculation Benchmark](/mnt/raid0/llm/epyc-inference-research/docs/experiments/self-speculation-benchmark.md) -- Layer-skip results on Qwen3.5 hybrid SSM (net negative)
- [HiSpec External Draft Benchmark](/mnt/raid0/llm/epyc-inference-research/docs/experiments/hispec-external-draft-benchmark.md) -- Checkpoint optimization validation, freeze-recurrent results
- [SpecExec Verification Profile](/mnt/raid0/llm/epyc-inference-research/docs/experiments/specexec-verification-profile.md) -- Batch verification latency curves, draft model cost profiling, large-K linear results
- [NUMA Orchestrator Deployment](/workspace/handoffs/completed/numa-orchestrator-deployment.md) -- Comprehensive spec sweep (1,290 measurements), coder quant decision matrix
- [Progress 2026-03-21](/workspace/progress/2026-03/2026-03-21.md) -- Sweep results correcting inflated registry values
- [Integration Test Coverage](/workspace/handoffs/active/integration-test-coverage.md) -- 61 integration tests (graph execution, node-level, observability, API endpoints), mock LLM + real REPL design pattern, `GraphRunContext` factory fixture
- [Progress 2026-04-14 Sessions 7-20](/workspace/progress/2026-04/2026-04-14.md) -- Coverage tranches A-L bringing all 10 seeding modules + eval_log_format to 100%, specialist routing to 78%/76%, enforced slice held at 100%
- [Bulk Inference Campaign](/workspace/handoffs/active/bulk-inference-campaign.md) -- Packages B-E results (RI-9, TrimR, difficulty, Omega, tool A/B, CF 2a-2c, TALE), post-AR-3 analysis framework
- [Eval Tower Verification](/workspace/handoffs/active/eval-tower-verification.md) -- Scoring Verifiers 4-metric protocol, reasoning model dominance, SWE-RM calibration gap, ThinkPRM process verification, cross-family verification constraint
- [Math-Verify Integration Analysis](/workspace/research/deep-dives/math-verify-integration-analysis.md) -- intake-377/379, symbolic math comparison, 66% underestimation fix, ANTLR4 parsing, thread safety caveats
- [DeepPlanning Agent Benchmark deep dive](/workspace/research/deep-dives/deepplanning-agent-benchmark.md) -- intake-412, rule-based deterministic scoring, 26-model leaderboard, multi-granularity scoring (dimension/composite/case), reasoning-mode gap data, error taxonomy, reverse-generation methodology
- [Simula Synthetic Data Generation deep dive](/workspace/research/deep-dives/simula-synthetic-data-generation.md) -- intake-410, double-critic rejection sampling (sycophancy-resistant verification), calibrated Elo complexity scoring (cross-dataset difficulty stratification), taxonomy-based coverage analysis
- [Progress 2026-04-19](/workspace/progress/2026-04/2026-04-19.md) -- Five-model quality benchmark campaign (M2.7, Qwen3.6, SG4-31b, SG4-26b-MM), serving infrastructure debugging, benchmark tooling upgrades
- [Intake entries: 15 papers](/workspace/.claude/skills/project-wiki/data/) -- ARC, MMLU, GSM8K, HumanEval, MBPP, IFEval, BFCL, SpecExec, PhysReason, and others (all verdict: already_integrated)

## Per-model compression-tolerance curve as model-onboarding deployment gate (2026-04-30)

**TL;DR**: `agent-file-prose-compression.md` (NEW handoff, HIGH priority, per intake-509 follow-up) elevates per-model compression-tolerance from a one-off A/B into a **deployment gate baked into the `/new-model` onboarding pipeline**. A model that fails ≥95% baseline compliance at the candidate compression level is flagged before reaching production.

### Why this matters as a methodology pattern

Three structural advantages over runtime compression A/Bs:

1. **Static, build-time, human-reviewed.** Compression is run once per agent file, the diff is reviewed by a human, the result is committed. Non-determinism of the compressor is replaced by a human gate. No 5-minute prompt-cache pressure, no live failure modes — the eval is reproducible.
2. **Monolog target, not aggregation.** Agent reads agent file as instructions to itself. There is no downstream verifier comparing confidence markers across multiple authors, so the hedge-stripping failure mode that blocks runtime `/caveman` deployment does not apply here. The eval surface is therefore narrower and more tractable.
3. **Per-model differentiation IS the eval signal.** A 1.7B drafter has less capacity to fill in caveman-style blanks than a 30B verifier. The eval explicitly measures **the compression-tolerance curve per model**, not a single binary "does it work". This makes the eval a proper deployment-gate input, not a yes/no.

### Eval gate

Pilot: `agents/shared/ENGINEERING_STANDARDS.md`. Compress at ladder of levels (e.g. 20% / 30% / 40% / 50% reduction). For each level, run a per-model compliance suite measuring whether the agent respects RFC 2119 directive polarity (`must`/`must not`/`never`/`always`/`MAY`/`SHOULD`), procedural ordering, and bundled examples. **Gate**: ≥95% baseline compliance at ≥30% token reduction. Models that fail at any level are tagged with their max-tolerable-compression level in the registry; orchestrator routing respects the per-model max.

### Cross-model deployment-gate matrix

| Model class | Expected compression tolerance |
|-------------|-------------------------------|
| Opus-class verifier (high-capacity, instruction-following well-trained) | 40-50% likely OK |
| Sonnet-class worker | 30-40% likely OK |
| Haiku-class drafter | 20-30% likely OK |
| Local 30B-A3B coder | empirical, no priors |
| Local 1.7B drafter | likely degrades fast |

Per-model curve becomes part of the model registry and enters routing decisions: if a route requires compressed agent files but the candidate model fails the gate at the required compression level, the route is rejected at deployment time, not at runtime.

### Sources

- [intake-509](https://github.com/mattpocock/skills) Skills For Real Engineers — `/caveman` source
- intake-450 — veniceai/skills (sibling SKILL.md authoring rubric)
- intake-301 — AXI/TOON encoding (orthogonal layer)
- [`handoffs/active/agent-file-prose-compression.md`](../handoffs/active/agent-file-prose-compression.md) NEW — `/agent-file-compress` skill + per-model deployment gate

## 2026-05-04 Update — Probe B 4-config protocol formalized

The 4-config Probe B methodology used throughout 2026-04-29/30 multi-arch coverage was applied formally on 2026-05-04 to close two `todo_or_undecided` slots in the v5 deployment draft (Qwen3.5-122B-A10B and Qwen3-Coder-REAP-246B-A35B). The protocol details are now explicit in [`handoffs/active/qwen35-122b-a10b-arch-class-probe.md`](../handoffs/active/qwen35-122b-a10b-arch-class-probe.md) — referenced here as the canonical methodology for any new model arch-class assignment.

### Pre-flight: reproducibility tripwire

Run before trusting any new bench output:

```
OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  numactl --interleave=all -- taskset -c 0-95 \
  llama-bench -m Coder-30B-A3B-Q4_K_M -t 96 -fa 1 --mmap 0 -p 0 -n 32 -r 5
```

Expected: 47-49 t/s cold-boot, ~58 t/s warmed. If outside this band, host is degraded — investigate before benchmarking anything else. 2026-05-04 baseline: 47.86 ± 0.36 t/s (cold-boot canonical).

### 4 envelope configs (single-instance 96t, n=5 reps)

| Config | Env block | Tests |
|---|---|---|
| **c0** default v5 | (none) | baseline |
| **c1** CPU1 stack | `GGML_CCD_POOLS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1` | sync-bound MoE class |
| **c2** mbind off | `GGML_NUMA_REPACK_INTERLEAVE=0` | mbind-sensitive class |
| **c3** combined | c1 + c2 | hybrid SSM dense pattern (Nemotron-9B-v2) |

All configs use the canonical OMP env stack + `numactl --interleave=all -- taskset -c 0-95 -t 96 -fa 1 --mmap 0`. n=5 reps; σ should land ≤ 1% per config under tight conditions.

### Decision gates

| Outcome | Verdict |
|---|---|
| Any single config ≥ +5% with σ ≤ 1% | Wire env block into v5 deployment draft for the role |
| All within ±2% under tight Probe B | Mark `arch_class: ...` analogue with `env: {}` (default v5) |
| ≥ +1% with z ≥ 3 vs c0 (statistically significant under tight σ) | Pragmatic flip — wire the winning env block, document the marginal delta |

The "z ≥ 3" gate was applied 2026-05-04 to close 122B-A10B's c2 +1.28% (z=3.0, σ=0.42%). The flip was justified despite being below the strict +5% gate because the σ was unusually tight (0.42% per-run, n=5) and the signal cleanly separated from c0/c1/c3.

### PPL bit-exact gate ≠ perf gate

Q6_K AVX-512BW Phase A demonstrated: a kernel can be **bit-exact** (5/5 PPL identical to scalar generic across production lineup) yet still **fail the perf gate** (geomean -0.28%, REAP-246B -1.01%) because the multi-thread regime is BW-saturated — ALU width doesn't help when cycles are spent waiting on DRAM. This is consistent with `project_q8_8x8_avx512bw_outcome` "+1-3% at 12-96t (BW-saturated)" pattern.

**Methodology corollary**: PPL gate (correctness) and perf gate (deployment) are independent. A kernel passing PPL is necessary but not sufficient for default-on flip — perf gate at production-relevant thread counts must also pass.

### Failure mode: Phase A.2 strict gate failure → Phase B/C de-prioritization

When the Phase A perf gate fails (Q6_K, 2026-05-04), the compounding rationale for downstream work (Q5_K body, blanket Q{5,6,8}_K default-on flip) is **falsified**, not just delayed. The "expected aggregate +2-7% on Q4_K_M decode" projection was contingent on the kernel showing some BW-utilization improvement; with -0.28% geomean confirmed, the path is closed unless new evidence emerges (different binary, different model class, different thread regime).

### Sources (2026-05-04)

- [`progress/2026-05/2026-05-04.md`](../progress/2026-05/2026-05-04.md) — full session log with all 3 probes (Q6_K Phase A, 122B-A10B Probe B Phase 1+2, REAP-246B Probe B)
- [`handoffs/active/qkernel-q5q6-default-on-flip.md`](../handoffs/active/qkernel-q5q6-default-on-flip.md) — Q6_K Phase A failure documented
- [`data/cpu_optimization/2026-05-04-q6k-default-on-validation/findings.md`](../../epyc-inference-research/data/cpu_optimization/2026-05-04-q6k-default-on-validation/findings.md) — Phase A.1+A.2 bundle
- [`data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings.md`](../../epyc-inference-research/data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings.md) + [`findings_phase2.md`](../../epyc-inference-research/data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings_phase2.md) — 122B Probe B
- [`data/cpu_optimization/2026-05-04-reap246b-arch-probe/findings.md`](../../epyc-inference-research/data/cpu_optimization/2026-05-04-reap246b-arch-probe/findings.md) — REAP-246B Probe B

### Multi-day uptime → bimodal bench throughput (2026-05-04 evening)

After 6+ hours of full-suite benchmark activity (May-4 sweep: REAP-246B, MiniMax-M2.7, Qwen3-Next-80B, etc., ~500 GB cumulative model loads), the same canonical recipe + same binary that gave 48.71 t/s in the morning produced 28.96-29.98 t/s in the evening (5 consecutive runs). Freq sample healthy (4.3 GHz, 96/96 cores boosting), NUMA pages perfectly balanced, libomp + wrapping verified at process level, `thp_fault_fallback=0`. Drop-caches did NOT recover throughput.

Definitive A/B test ruled out launcher / subprocess.run wrapping bugs: standalone preflight + `python -c "subprocess.run([sys.executable, preflight])"` produced 29.89 / 29.98 — identical bench numbers from both invocation modes.

The phenomenon matches `feedback_host_throttle_check.md` reset behavior — reboot reliably restores canonical baseline — but the documented signature there (cores stuck at 1998 MHz) does NOT match the freq sample, indicating a DIFFERENT multi-day-uptime hysteresis (likely kernel scheduler / CCD prefetcher / NUMA balancer state below /proc visibility).

**Methodology corollary**: the canonical-recipe preflight gate (5 checks: uptime / libomp / wrapping / tripwire bench / freq under load) is necessary but NOT sufficient — multi-day uptime can produce a state where ALL gates pass except tripwire bench. **Tripwire is the only canary that actually catches this.** When tripwire fails despite freq healthy, **reboot** rather than digging for a code-side cause. Don't `--skip-preflight` to bypass — the bench results would be at 60% of canonical baseline and not comparable.

Open instrumentation idea: capture full bench process state (numa_maps, smaps, vmstat delta, perf-stat) on tripwire FAIL so we have evidence next time the state appears. Tracked as deferred work in [`progress/2026-05/2026-05-04.md`](../progress/2026-05/2026-05-04.md) § "Evening session".

Source: [progress/2026-05/2026-05-04.md](../progress/2026-05/2026-05-04.md) § Evening session, [handoffs/active/qwen36-benchmark-fixes.md](../handoffs/active/qwen36-benchmark-fixes.md) 2026-05-04 update.

### Stack consolidation methodology (2026-05-04)

May-4 Claude-as-Judge scoring under canonical recipe + the morning's 9-model sweep produced enough data to consolidate the production hot tier from 4 model classes (Qwen3.5-35B-A3B, Qwen2.5-Coder-32B, Llama-3-8B × 2 roles) to 2 (Qwen3.6-35B-A3B Q8 + Qwen3-Coder-30B-A3B Q4). The consolidation argument:

1. **Score before t/s, not the other way around.** Llama-3-8B at 38% on agentic and general suites was disqualifying regardless of its 13.8 t/s; Qwen3-Coder-30B-A3B at 84% overall (87% agentic, 77% coder, 90% math) wins on capability AND was already 3× faster post-canonical (43.4 t/s).
2. **Test the same model on the actual target workload's suite.** "Don't deploy Nemotron-Nano-9B for general/coder/agentic" was a defensible no-go when Nemotron's 99% was on a 3-suite subset (no coder, no math, no instruction_precision); per-suite where comparable, it beat Qwen3-Coder, but the missing suites are the ones that matter.
3. **Single-model consolidation across slots is cheap when the GGUF mmap is shared.** Qwen3-Coder-30B-A3B as coder_escalation + worker_general + toolrunner is a single 16-GB resident binding; net savings vs three separate hot-tier residents (8B + 8B + 32B ≈ 33 GB).
4. **Latency vs decode-rate as separate optimization axes.** Initial argument for keeping toolrunner on a smaller Qwen3-4B Q8 (low-latency tool emission) didn't survive the agentic-suite numbers — Qwen3-Coder won on agentic AND on decode rate. The remaining argument (TTFT on sub-100-token prompts) lacks a measurement; not enough to justify a separate slot.

This methodology generalizes: **rank candidates per-suite, weight by traffic share, prefer single-model resident bindings when capability passes the floor for ALL traffic on that slot.** A single 16-GB MoE that hits 84% on all relevant suites beats a fleet of specialists each tuned to one suite.

Source: [progress/2026-05/2026-05-04.md](../progress/2026-05/2026-05-04.md) § Evening session, [handoffs/active/qwen36-production-upgrade.md](../handoffs/active/qwen36-production-upgrade.md) 2026-05-04 update, [`epyc-orchestrator` branch `feature/stack-swap-2026-05-04`](.../../) commits fee69b8 + 587219c.

### Stack consolidation methodology — extended 2026-05-06 with role-elimination data

Two refinements landed after re-benching the architect candidates and cross-checking REAP-246B's master CSV row:

#### 1. Role elimination via cross-role comparison

`architect_coding` was supposed to be the "hardest coding escalation" target. Its model (Qwen3-Coder-REAP-246B-A35B Q4_K_M) had been deployed there since 2026-03-29 without ever being scored on the canonical 183-question battery. Master CSV cross-check (`benchmarks/results/reviews/summary.csv`) revealed:

- REAP-246B coder = **7/10 (70%)**
- Worker (Qwen3-Coder-30B-A3B Q4) coder = 23/30 (77%) — *cheaper, better*
- Frontdoor (Qwen3.6-35B-A3B Q8) coder = 29/30 (97%) — *27pp better, 3.8× faster*

The role's purpose is no longer met by its current model AND no other available model class would do better than the existing frontdoor. **Conclusion**: the role itself is redundant. Hard coding escalations route to coder_escalation (which now also runs the frontdoor model on a separate slot, shared GGUF mmap).

**Methodology rule**: when a role's stated purpose ("hardest X") is no longer served by the current model AND no alternative model in the eval pool can serve it better than an already-deployed sibling role, **eliminate the role** rather than swap. Saves a slot AND removes a routing decision the orchestrator no longer needs to make.

Result: 139 GB warm-tier RAM reclaimed; coder escalation chain shortened from 3 (frontdoor → coder_escalation → architect_coding) to 2 (frontdoor → coder_escalation).

#### 2. Architect re-bench: speed × long-context-capability tiebreaks quality-tied candidates

Re-bench of the 3 architect_general candidates (Qwen3.5-122B-A10B Q4, Qwen3.6-27B Q4, Qwen3.6-27B Q8) on the full 183-question battery:

| Candidate | Total | t/s | long_context | Verdict |
|---|---|---|---|---|
| Qwen3.5-122B-A10B Q4 | 196/210 (93%) | 12.34 | 24/27 (89%) | KEEP |
| Qwen3.6-27B Q4 | 173/183 (95%) | 6.53 | not tested | reject |
| Qwen3.6-27B Q8 | 166/183 (91%) | 4.42 | not tested | reject |

Quality essentially tied (93-95%) — but 122B-A10B is **2× faster** (MoE 10B-active beats dense 27B) AND the only candidate with proven long-context capability (89% on long_context suite). For architect/synthesis workloads, latency matters more than the 1-2pp quality ceiling, and long-context capability is hard to retrofit.

**Methodology rule**: when quality scores are tied within ~3pp, **don't swap** — speed and long-context are real differentiators. Re-bench the existing candidate properly before treating it as inferior to "newer" alternatives.

Source: [progress/2026-05/2026-05-06.md](../progress/2026-05/2026-05-06.md), [handoffs/active/qwen36-production-upgrade.md](../handoffs/active/qwen36-production-upgrade.md) 2026-05-06 update, [`epyc-orchestrator` branch `feature/stack-swap-2026-05-04`](.../../) commits `7491a12` + `dad42a0`, [`benchmarks/results/reviews/may5_architect_candidates/`](../../epyc-inference-research/benchmarks/results/reviews/may5_architect_candidates/) per-question CSVs.

### Multi-day uptime hysteresis recurs at <2d (2026-05-06)

After the 2026-05-04 evening reboot the system ran clean for ~24h, then preflight tripwire failed at **29.49 t/s @ 1.5d uptime** — earlier than the documented 2.0d warn threshold. Same pattern: freq healthy, libomp + wrapping correct, NUMA balanced, drop_caches no-op. Reboot recovered the bench to 45.55 t/s.

Pattern is now confirmed across **two independent occurrences** with different initial uptimes (2.3d on May 4, 1.5d on May 6) producing the same ~60% throughput collapse. **The 2.0d preflight uptime warn threshold is not conservative enough.** Either tighten to 1.0-1.5d, OR accept that the threshold is purely advisory and the tripwire bench is the only reliable canary (warn doesn't fail-fast; only tripwire fails preflight).

Open instrumentation: still no signal in `/proc` to distinguish fast vs slow state. Capturing numa_maps + smaps + vmstat delta + perf-stat sample on tripwire FAIL would help root-cause if the pattern persists.

Source: [progress/2026-05/2026-05-06.md](../progress/2026-05/2026-05-06.md), [`scripts/lib/canonical_recipe.py`](../../epyc-inference-research/scripts/lib/canonical_recipe.py) `UPTIME_WARN_DAYS = 2.0` constant.

### Stack consolidation arc closed 2026-05-06 — final outcome

The May 4-6 stack consolidation thread merged into epyc-orchestrator main on 2026-05-06 via merge commit `a268040` (9 commits). Final production stack quality + RAM accounting:

| Role | Pre-2026-05-04 | Post-merge | Quality Δ | RAM Δ |
|---|---|---|---|---|
| frontdoor | Qwen3.5-35B-A3B Q4 (82%) | Qwen3.6-35B-A3B Q8 (93%) | +11pp | +18 GB |
| coder_escalation | Qwen2.5-Coder-32B Q4 (77%) | Qwen3.6-35B-A3B Q8 (93%) shared GGUF mmap | +16pp | +0 (shared) |
| worker_general / toolrunner | Llama-3-8B Q4 (38%) | Qwen3-Coder-30B-A3B Q4 (84%) shared | +46pp | +11 GB shared |
| worker_summarize | Qwen2.5-Coder-32B Q4 (77%) | Qwen3.6-35B-A3B Q8 (93%) shared with frontdoor | +16pp | -18.5 GB |
| architect_general | Qwen3.5-122B-A10B Q4 (94%) | unchanged | 0 | 0 |
| ingest_long_context | Qwen3-Next-80B-A3B Q4 (warm) | promoted hot; Stage 1 of three_stage_summarization | 0 | 0 |
| ~~architect_coding~~ | REAP-246B Q4 (70% coder) | **REMOVED** (frontdoor 97% > REAP 70%) | — | **-139 GB** |
| ~~thinking_reasoning~~ | Qwen3-Next-80B-A3B-Thinking | **REMOVED** (GGUF deleted from disk) | — | 0 |
| ~~worker_pool~~ | 3-tier hot/warm pool | **DEPRECATED** (config-only; superseded by worker_general consolidation) | — | 0 |

**Net: ~157 GB warm-tier reclaimed** (139 + 18.5 - 0 frontdoor Q8 increment offset by GGUF mmap sharing).

### Long-context bench finding — frontdoor model wins

Frontdoor (Qwen3.6-35B-A3B Q8) scored **27/27 (100%)** on the canonical long_context suite — beating every other tested candidate:

| Candidate | long_context score |
|---|---|
| Qwen3.6-35B-A3B Q8 (frontdoor) | **27/27 (100%)** |
| Qwen3-Next-80B-A3B Q4 (ingest_long_context) | 25/27 (93%) |
| Qwen3.5-122B-A10B Q4 (architect_general) | 24/27 (89%) |
| Qwen3-Coder-30B-A3B Q4 (worker_general) | 16/27 (59%) — degenerate repetition |

This drove the **three_stage_summarization stage inversion**: previous design had frontdoor as Stage 1 (full context, fast draft) + ingest_long_context as Stage 2 (quality review on reduced context). Inverted: ingest_long_context for Stage 1 (SSM-hybrid linear attention scales O(n) per token at large contexts) + frontdoor for Stage 2 (highest long_context quality). Each model now matched to its stage's demand profile.

### Single-source-of-truth refactor

The May-4/6 audit caught that orchestrator_stack.py's HOT_SERVERS / WARM_SERVERS / HOT_ROLES / SERIAL_ROLES were hand-edited dict literals duplicating wiring data already in NUMA_CONFIG. Adding/removing roles required editing 5 places consistently. Architect_coding registry-removal had been propagated to NUMA_CONFIG but NOT to HOT_SERVERS — `start` would have crashed.

Refactor (commit `bd2455d`):
- New `ROLE_LAUNCH_META` dict: per-role tier + mode + aliases + mode-specific kwargs (15 lines)
- `_build_servers_from_classification()` computes HOT_SERVERS + WARM_SERVERS at module load from NUMA_CONFIG + ROLE_LAUNCH_META
- `_validate_role_classification()` runs at module load; rejects port collisions, NUMA_CONFIG/ROLE_LAUNCH_META mismatches, missing classifications
- `validate_against_registry()` runs at `start` command; warns on drift between launcher and registry's process_layout / server_mode

Result: adding a role is now 2 places (NUMA_CONFIG + ROLE_LAUNCH_META) with self-validation; removing/renaming catches dangling refs at module load instead of at launch.

Source: [progress/2026-05/2026-05-06.md](../progress/2026-05/2026-05-06.md), [`epyc-orchestrator` merge `a268040`](../../epyc-orchestrator/), [`handoffs/active/qwen36-production-upgrade.md`](../handoffs/active/qwen36-production-upgrade.md).

## 2026-05-08 — Five bench harness fixes surfaced during gemma4 evaluation

The 2026-05-08 worker_general swap (gemma4-26B-A4B MTP) ran the harness end-to-end across two suites under conditions that exposed five distinct latent bugs. All were silent or partial failures pre-fix; none would have flagged in routine sweeps because each only manifests under specific config combinations.

### 1. `--lookup` flag deprecated upstream — wasn't replaced in our path

`scripts/lib/executor.py:339` still appended a literal `--lookup` to llama-server cmds for any config requesting prompt lookup acceleration. Production llama-server rejected this with `error: invalid argument: --lookup` (the flag was renamed to `--spec-type ngram-simple --spec-ngram-size-n N` in upstream months ago). Every `*_lookup` and `*_lookup_n*` config had been failing exit-1 silently for an unknown duration. Fix: route through the upstream flag, plumb a new `spec_ngram_size_n` parameter through `ServerManager.start` and the harness `_start_server` wrapper.

### 2. Lookup ngram sweep wasn't actually varying ngram

`_sweep_lookup_ngram._test_ngram` issued an inference call to the running server for each candidate ngram value (n=2, 3, 5, 9, 17, 33, 65, 128), assuming the legacy `--lookup` flag's per-request override semantics. Upstream `--spec-type ngram-simple` is **server-startup-fixed**, so all 8 sweep steps were running the same fixed-ngram server and reporting duplicate tps. Fix: restart the server with `spec_ngram_size_n=n` per sweep step; `_ServerState` gained a `lookup_ngram` slot to track the current value.

### 3. Port-bind race after rapid restart cycles

The MoE expert sweep + speculative-decoding draft-model swaps in a single bench run cycle the server through 6+ restarts. Some of those restarts left port 8080 in TIME_WAIT or partially released; the next launch hit `couldn't bind to server socket: ... double free or corruption` and crashed before model load. Fix: new `ServerManager._is_port_free(port)` + `_reserve_port(preferred, timeout=30, hops=10)` static helpers polled-then-hopped to the next free port (cmd argv updated to match), with a 30s wait before fallback. All downstream URLs use `self.port` and follow the hop transparently.

### 4. Speed tests routed through subprocess that didn't exist

`_run_speed_test` (the standard speed-only config runner) called `executor.run_inference` (the **subprocess** path that spawns standalone `llama-completion` / `llama-speculative` / `llama-lookup` binaries), even when a server was running with the right state. The harness's own preflight log warned `Missing subprocess binaries (server-mode still works): completion, speculative, lookup` — those binaries aren't built on production hosts. Every `spec_*` and `*_lookup` speed test exited 1 with `binary not found`. Fix: `_run_speed_test(..., ss=None)` accepts the server state and prefers `ss.server.run_inference` when running, mirroring the `_sweep_lookup_ngram` pattern. Backwards-compatible default.

### 5. `--skip-moe-reduction` kept moe`<X>`_* configs when X equaled the production target

`registry.get_baseline_experts(role)` had a fallback chain `accel.baseline_experts → accel.experts → 8`. The middle term was wrong: `accel.experts` is the **production-target reduction count** (e.g. `experts: 4` for "we want to deploy with 4 experts active"), NOT the **GGUF default** (the model's native expert count, e.g. 8 for Qwen3-30B-A3B). The `--skip-moe-reduction` filter `c.moe_experts is None or c.moe_experts == baseline_experts` then kept `moe<production_target>_*` configs because they "matched the baseline". 19 of 22 MoE roles in the registry were vulnerable. Fix: removed the dangerous `accel.experts` fallback; added explicit `baseline_experts` to all 20 affected role blocks (8 for Qwen3 family, 10 for Qwen3-Next-80B-A3B verified via direct GGUF metadata read).

### Plus

- New `--skip-speed-tests` CLI flag filters all `cfg.speed_test_only` configs for quality-only runs (e.g. tool_compliance-focused evaluations).
- `tool_compliance.yaml` gained `inference_params.max_tokens: 2048` (was inheriting the global default of 512); pre-fix, gemma4 `t3_q2_llm_delegation` truncated at exactly 512 ctok mid-prompt and scored 0/3.
- Added `constraints.forbid: [prompt_lookup]` to gemma4_31b/26b registry blocks — MTP-only models can't coexist with ngram-simple lookup (both consume the spec-decode slot).

### Lessons that generalize

- **Silent-failure backstop**: a CI guardrail that asserts every `*_lookup` config produces `tps > 0` would have caught (1)–(4) months earlier. The harness currently has no such assertion — every speed test that fails exit-1 just gets logged and skipped.
- **Field-name semantics in registries**: when a YAML key has both a "production-target" and a "GGUF-baseline" interpretation, name them distinctly (`experts` vs `baseline_experts`) AND have the registry loader REQUIRE both for any MoE role (or default the missing one explicitly with a warning, not silently fall back to the wrong one).
- **Flag deprecation needs a sweep**: when an upstream flag is renamed, search for it across all callers. The `--lookup` rename existed in upstream's CHANGELOG but didn't propagate to our harness.

Source: [progress/2026-05/2026-05-08.md § session 2 § Bench harness bugs fixed](../progress/2026-05/2026-05-08.md), commits `f106b7a` (harness fixes) + `a295618` (bench data) on `epyc-inference-research:feature/preflight-canonical-gate`.
