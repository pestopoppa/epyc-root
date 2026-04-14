# Benchmark Methodology

**Category**: `benchmark_methodology`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 23 documents

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

## Actionable for EPYC

- The deterministic debug suite (577 curated + 55,871 HF-backed questions) enables fully automated regression testing and MemRL reward injection without Claude API costs. Any new model entering the stack can be benchmarked end-to-end with `run_overnight_benchmark_suite.sh`.
- Stratified tier sampling (`--stratify-tiers`) should be used for suites with real tier metadata (MMLU, Math, IFEval) to ensure balanced difficulty representation. Other suites fall through to uniform random.
- The mode-advantage suite provides strong MemRL routing signal by shifting the reward distribution from ~5% specialist-wins to ~25-35%, enabling the router to learn when to route rather than just that routing has a cost.
- All benchmark throughput values MUST be verified by sweep at deployment thread counts, not extrapolated from different configurations. The 2026-03-21 sweep corrected 3.6x inflated coder throughput that was biasing Q-scorer routing decisions.
- Future work: dynamic lambda by task priority (interactive=higher lambda, batch=lower), multi-objective Pareto frontier maintenance, token-level cost accounting (prompt vs completion), and cache-aware cost reduction with RadixAttention.

## Open Questions

- Claude-as-Judge integration with graded quality scores (0-3) combined with cost penalty is implemented but disabled. Enabling it would provide richer signal than binary pass/fail + cost but adds API cost.
- The llm_judge scoring method (using local worker model for physics/math semantic equivalence) has unknown accuracy compared to Claude-as-Judge. Validation data needed.
- Adaptive per-call timeouts during 3-way seeding may mask genuine infrastructure issues vs genuinely slow models. The boundary between legitimate slow generation and stalled inference is unclear.
- Optuna threshold optimization for separated Q-values and cost metrics is designed but not yet implemented.

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
- [Intake entries: 15 papers](/workspace/.claude/skills/project-wiki/data/) -- ARC, MMLU, GSM8K, HumanEval, MBPP, IFEval, BFCL, SpecExec, PhysReason, and others (all verdict: already_integrated)
