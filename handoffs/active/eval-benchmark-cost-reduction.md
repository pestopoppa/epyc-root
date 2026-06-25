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
