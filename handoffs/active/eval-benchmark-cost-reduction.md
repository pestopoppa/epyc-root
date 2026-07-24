# Eval Benchmark Cost Reduction — Mid-Range Difficulty Filter

**Status**: stub
**Created**: 2026-06-25 (via research intake)
**Categories**: benchmark_methodology, autonomous_research

## Objective

Apply a mid-range difficulty filter (30–70% historical pass rate) to *external fixed-task evals* (Terminal-Bench Core) to reduce per-run evaluation cost by 44–70% while maintaining rank fidelity (Spearman ρ ≥ 0.87). **Not applicable to autopilot's rotating question pool** — see Constraints below.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-727 | Efficient Benchmarking of AI Agents (arxiv:2603.23749) | high | new_opportunity |
| intake-726 | Terminal-Bench / Harbor Framework (GitHub) | high | adopt_component |
| intake-369 | Terminal-Bench paper (arxiv:2601.11868) | medium | worth_investigating |

## Technique

**Mid-Range Difficulty Filter (MR)**: select tasks where historical pass rate ∈ [0.30, 0.70]. Tasks outside this range contribute minimal ranking signal and add pure cost. Motivated by Item Response Theory.

- Evaluated on Terminal-Bench 2.0 (89 fixed tasks, 101 agents, 23 scaffolds) + 7 HAL benchmarks
- Mean Spearman ρ = 0.94, worst-case = 0.87 under scaffold/temporal shift
- 44–70% task reduction (median 58%); $268.8–$870.6 savings per run (HAL benchmarks)

## Constraints: Why This Does NOT Apply to Autopilot's Rotating Pool

Analyzed 2026-06-25 against the live autopilot journal (852 trials, 141 with question_results):

1. **Wrong evaluation objective**: The paper optimizes for *cross-agent rank ordering*. Autopilot performs *within-system regression detection* on an evolving config — opposite sensitivity requirement. Ceiling questions (>70% pass rate) are strong regression signals when they fail; floor questions (<30%) signal breakthroughs. The mid-range filter would discard both classes.

2. **Pool is rotating, not fixed**: 1382 unique qids from suites `general`, `math`, `coder`, `thinking`, `simpleqa`, `hotpotqa`, `gpqa`, `debugbench`, `livecodebench`, `cruxeval`, `bigcodebench`, `instruction_precision`, `vl`, `mode_advantage`, etc. Only 50 qids appear in ≥50 trials — the stable core. Of those 50, **only 3 fall in the 30–70% mid-range**. The filter would reduce the stable core from 50 to 3 questions.

3. **Pass rate polarization**: The 50-qid stable core is highly polarized — ~15 floor questions (<30%, dominated by `simpleqa` and `hotpotqa`) and ~32 ceiling questions (>70%, dominated by `coder`, `debugbench`, `math`, `thinking`). Only `cruxeval`×1, `instruction_precision`×1, `vl`×1 are mid-range.

**Correct use of pass-rate data for autopilot**: rotate out permanently saturated/floor questions and replace with fresh mid-range ones — a *question pool curation* problem, not a subset-selection problem. The differential signal from ceiling/floor qids is low between config mutations, suggesting those slots should be refreshed with harder/more-varied questions.

## Where the MR Filter IS Applicable: TB Core External Evals

The filter is designed for the TB Core v0.1.1 scenario: **89 fixed tasks evaluated repeatedly against different agent configurations**. After establishing a TB Core baseline (see `agent-world-env-synthesis.md` and `autopilot-continuous-optimization.md`):

1. Run our stack against all 89 TB Core tasks to calibrate per-task difficulty
2. Identify the ~37–50 tasks in the 30–70% pass-rate band
3. Use that subset for routine re-evaluations (e.g., after major config changes) to reduce TB run cost by ~44–58%
4. Reserve full 89-task runs for quarterly calibration resets

Cold-start: The paper requires ~10 full-benchmark agent runs before the filter is reliable. Our one-time TB Core run provides 1 data point across a single configuration. To reach 10 points across diverse configs, either run our stack at multiple historical checkpoints or use the published TB2.0 paper dataset (101 agents, 23 scaffolds, temporal window Oct 2025–Jan 2026) as the difficulty calibration corpus — the pass rates are in the paper itself, not behind a submission wall.

## Open Questions

- What is the Harbor adapter implementation cost for our `/v1/chat/completions` endpoint? (Prerequisite for TB Core run — estimate ~1 day: build a thin Terminus-compatible wrapper over our OpenAI-compatible endpoint.)
- After TB Core run: which of the 89 tasks fall in 30–70% for our stack? Does the mid-range band shift meaningfully between our orchestrator config variants?
- Can the TB2.0 paper's published per-task difficulty data (101 agents, 23 scaffolds) serve as a proxy calibration corpus to identify the mid-range subset without running our stack first?

## Notes

- Solo-author preprint (March 2026), not peer-reviewed; credibility_score = 2 (medium). Pilot externally before any autopilot integration.
- The paper's scaffold-driven distribution shift guarantee (ρ ≥ 0.87 under LOSO) holds under temporal shift too — relevant for TB Core re-evaluations over time as our stack evolves.
- Do NOT apply to autopilot regression gates — per-suite resolution-awareness (3/n quantum gate, 2026-06-06) already addresses the small-sample problem differently.

## Progress checklist

- [ ] BLOCKED: needs Harbor adapter + TB Core baseline (agent-world-env-synthesis) before MR/TB filter applies

## Research Intake Update — 2026-07-11

### New Related Research
- **[intake-802] "llm-inference-bench"** (GitHub `local-inference-lab/llm-inference-bench`; **UNLICENSED** — deep-dive corrected first-pass "MIT" (that refers to the GSM8K dataset); single-author, no CI/tests)
  - Relevance: a serving-benchmark harness whose **statistical-rigor methodology** is directly transferable to our eval framework, independent of its GPU-serving target.
  - Key techniques worth mining (adopt_patterns, NOT adopt_component — it's coupled to vLLM/SGLang GPU serving we don't run in prod, no llama.cpp/CPU path): (1) **McNemar paired-significance test** for A/B quant comparisons — a concrete upgrade for gating quant swaps beyond raw accuracy deltas; (2) **Wilson confidence intervals** on GSM8K/MMLU-Pro/GPQA-Diamond — pairs with our small-sample per-suite resolution-awareness; (3) concurrency×context-length throughput matrix + Prometheus server-side ground truth (reference for [[dynamic-stack-concurrency]] baselines).
  - Delta: our bench stack (bench_canonical.sh) uses Claude-as-judge + codified recipes and lacks explicit paired-significance testing; McNemar/Wilson are low-cost additions to chapters 06/07 methodology.
  - **Deep-dive (2026-07-11) verified the methodology is REAL, not README aspiration** — credibility bumped **2→3**: `wilson_interval` (`llm_decode_bench.py:11476`), `mcnemar_exact_p` (`:11487`, the rigorous **exact binomial** variant), and `build_paired_comparison` (`:11523`) are implemented, **stdlib-only** (math/statistics; no scipy), and cleanly separable from the vLLM/SGLang+Prometheus serving code. The tool is **AIPerf-0.7.0 parity-validated** (`docs/aiperf-parity-report-2026-04-26.md`, aggregate tok/s within −0.3…−3.6%) — first-pass "zero empirical numbers" was wrong. McNemar is the principled successor to our 3/n resolution gate. Full note: [`research/deep-dives/2026-07-11-paired-significance-eval-methodology.md`](../../research/deep-dives/2026-07-11-paired-significance-eval-methodology.md).
  - [x] A1 landed the reusable clean-room primitives ✅ 2026-07-17: `wilson_interval`/`expected_calibration_error`/`roc_auc` in `epyc-orchestrator/src/llm_primitives/stat_tests.py` (stdlib-only; 8 duplicate call-sites swapped w/ quantified equivalence — ROC Δ=0.0, ECE ≤3.2e-8) + the `dataset_sha256`+`test_profile` equality gate (`require_matched_comparison`) in `scripts/autopilot/paired_stats.py`; canonical exact McNemar stays `paired_stats.py::mcnemar_from_vectors`.
  - [x] A1 documented paired-McNemar as the formal successor to the 3/n resolution gate in chapter 06 (tracked: `epyc-inference-research/docs/chapters/06-benchmarking-framework.md` §Paired Significance Testing) ✅ 2026-07-17
  - [x] Pairing/discordant-flip screening wired into the eval-scoring/quant-A/B path ✅ 2026-07-17: `eval_tower.screen_paired_arms` (`scripts/autopilot/eval_tower.py:1124`) emits exact-McNemar p + per-arm Wilson CIs over the flip pairs, gated by `require_matched_comparison` on `dataset_sha256`+`test_profile`; called from the math-rebaseline A/B path at `eval_tower.py:3004` (`paired_significance` key). Commit `e93c6263`.
  - [ ] RESIDUAL (**owned by the inference-batch `/loop`, not this handoff**): `screen_paired_arms` output is currently **observation-grade** — it is reported in the result dict but is not reachable through a codified recipe, so per MEASUREMENT.md its McNemar p may not gate a keep/revert/promote decision. Promoting it to decision-gating rides on **EV-11 math re-baseline** (`coordination/inference-batch/entries/20-eval-tower.yaml` → `EV-11-math-rebaseline`), which is BLOCKED on the **EV-11b ECE-binning operator decision**. Do not edit `eval_tower.py` for this from a side session — see [`inference-batch-loop.md`](inference-batch-loop.md) (single-writer).
- [x] Operator-review candidate: port `wilson_interval` + `mcnemar_exact_p` + the pairing/discordant-flip core of `build_paired_comparison` (`llm_decode_bench.py:11476–11640`) into the eval-scoring / quant-A/B path (NOT `canonical_recipe.py`, speed-only); gate on `dataset_sha256`+profile match; document paired-McNemar as the formal successor to the 3/n resolution gate in chapter 06. ✅ 2026-07-17 — all three legs landed; see the A1 items above. Chapter 06 §"Paired Significance Testing (Quant A/B)" is live at `epyc-inference-research/docs/chapters/06-benchmarking-framework.md:347`. Chapter 07 was never owed a section (suite construction, not test methodology). Only the decision-gating residual above remains.
