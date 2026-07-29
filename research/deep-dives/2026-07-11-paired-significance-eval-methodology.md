# Methodology note: paired significance testing for quant A/B eval

**Date:** 2026-07-11
**Companion handoff:** [`handoffs/active/eval-benchmark-cost-reduction.md`](../../handoffs/active/eval-benchmark-cost-reduction.md)
**Source:** intake-802 (`github.com/local-inference-lab/llm-inference-bench`, `llm_decode_bench.py:11476–11640`)
**Scope:** adopt two stdlib-only statistical functions into our eval-scoring layer; do NOT adopt the source's serving harness.
**Credibility:** the source functions are VERIFIED-implemented (read in source), statistically sound, and the tool is AIPerf-0.7.0 parity-validated (`docs/aiperf-parity-report-2026-04-26.md`). The repo itself is unlicensed / single-author / no-CI — we lift the *technique*, not a dependency.

---

## What to adopt

Two functions + one pairing routine, all **stdlib-only** (`math`, `statistics` — no scipy/numpy):

- **`wilson_interval(correct, total, z=1.959964)`** (`:11476`) — Wilson score 95% CI on suite accuracy; replaces reporting a bare "X/N correct".
- **`mcnemar_exact_p(b, c)`** (`:11487`) — **exact binomial** McNemar p-value on the discordant pairs of a paired A/B run (baseline vs candidate quant on the **same** question set). Exact (not chi-square-with-continuity) is the correct choice for the small-discordant-count regime.
- **`build_paired_comparison()`** (`:11523`) — pairs by `item_id`, counts discordant flips, runs McNemar, reports `significant_at_0_05`, per-side Wilson CIs, `delta_pp`, per-category deltas, and completion-token cost (mean/p50/p90/ratio).

## Why it fits us

- We compare quants on **fixed question pools** → the correct test is **paired McNemar on discordant items**, NOT two independent Wilson intervals (the latter is underpowered).
- It **formalizes our 3/n resolution gate** ([[feedback_per_suite_gate_resolution_artifact]] — "identical per-suite regression = 1-question flip"): McNemar answers "are these flips more than 1-question noise?" with a p-value, superseding the ad-hoc quantum heuristic.
- Chapters 06/07 and `canonical_recipe.py` currently have **no** paired-significance testing — this is net-new, not duplicative.
- The stat layer consumes a plain `report` dict (`runs: [{item_id, correct, completion_tokens, category, ...}]`) with **no GPU/Prometheus entanglement** → ~40 lines for the two core functions, ~120 for the full paired comparison. Trivial adapter from our per-item Claude-judge outputs.

## Guardrails to copy from the source

- **Gate on `dataset_sha256` + `test_profile` equality before comparing** (the source refuses to compare mismatched inputs).
- Report **per-category deltas + completion-token cost** alongside the p-value — a damaged quant that "thinks longer" surfaces as token inflation + truncation (`hit_max_tokens`), not just accuracy loss ([[feedback_pair_speed_with_correctness_check]]).

## Do NOT adopt

The source's Prometheus/prefill/decode-burst harness — it is vLLM/SGLang-coupled with no llama.cpp/CPU path.

## MEASUREMENT note

A McNemar p-value is a **decision-gating** statistic. Usable to gate a quant keep/revert **only** via a codified recipe with operator approval, not ad hoc — target integration is the eval-scoring path referenced by `eval-benchmark-cost-reduction.md`, NOT `canonical_recipe.py` (which is speed-only).

## Single next action

With operator approval, port `wilson_interval` + `mcnemar_exact_p` + the pairing/discordant-flip core of `build_paired_comparison` into the eval-scoring layer, and document paired-McNemar as the formal successor to the 3/n resolution gate in chapter 06.
