# Benchmark Methodology

**Category**: `benchmark_methodology`
**Confidence**: verified
**Last compiled**: 2026-04-18
**Sources**: 28 documents

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
- [Intake entries: 15 papers](/workspace/.claude/skills/project-wiki/data/) -- ARC, MMLU, GSM8K, HumanEval, MBPP, IFEval, BFCL, SpecExec, PhysReason, and others (all verdict: already_integrated)
