# Reasoning Effort Levels — prompt-conditioned quality/token ladder

**Status (2026-07-20): STUB — idea captured, not yet designed.** Operator idea, raised while reading the
R2a result in [`architect-model-selection-bench.md`](architect-model-selection-bench.md).

**One-line purpose:** give every role a **tunable reasoning-effort dial** — a spectrum of prompt
conditions (and token budgets) trading generated tokens for quality — instead of the current binary
"reasoning on / reasoning off", so latency-sensitive roles can buy *some* reasoning without paying full CoT.

## Motivating evidence (measured, not hypothesised)

Arm A4 = **Qwen3.6-35B-A3B (production frontdoor)**, GPQA-Diamond, **identical 50 questions**,
`enable_thinking=false` in BOTH arms — the only change is what the prompt asks for:

| Prompt condition | accuracy | mean tokens |
|---|---:|---:|
| "Answer with the letter only" | 52.0% | 537 |
| "Reason step by step, then answer" | **84.0%** | 2150 |
| **Δ** | **+32.0pp** (McNemar b=19 c=3, **p=8.6e-04**) | **4.0×** |

So the two endpoints of the ladder are real, large, and cheap to measure. 84.0% also sits within noise
of the vendor-published 86.0% for this model, so the high end is a genuine ceiling, not an artifact.
Full protocol + provenance in the R2a section of the architect bench handoff.

## The core design question
**Are there useful intermediate points, and is the accuracy/token curve smooth or a step?** If it is
smooth, effort becomes a real dial. If it is a step function (you either reason or you don't), the
"ladder" collapses to a binary and the work is just picking the threshold per role.

## ⚠ INVARIANT — effort is calibrated PER MODEL, and never inherited (operator, 2026-07-20)
**The ladder is a property of a (model, quant) pair, not of a role and not of the stack.** Every model
gets its own curve measured independently; a level that is optimal for one model says nothing about the
same level on another. Two independent results from 2026-07-20 already show per-model divergence on
*adjacent* dials:
- **Native thinking (R2b):** Qwen3.6-35B-A3B fails to terminate `<think>` on 48% of items even at a
  16384-token budget, making thinking-ON catastrophic **for that model**. Whether Qwen3.5-122B-A10B-IQ2
  does the same is a *separate measurement* — explicitly not generalized.
- **Spec-dec draft depth:** the measured optimum differs per model on the same GPU and kernel
  (122B-IQ2 → `n-max 2`; 27B-dense and 35B-A3B → `n-max 4`). Inheriting one model's setting cost ~29%
  throughput. Same failure shape, different dial.

**Consequences, binding on the design:**
1. Effort levels are **defined** generically (prompt templates) but **certified per model** — no level is
   "enabled" for a model until that model's own curve has been measured.
2. A **role default is a (model × level) pair.** Swapping the model bound to a role, or changing its
   quant, **invalidates the level** and requires re-calibration (see E-7).
3. Store the curves **indexed by model/quant, never by role** ([[feedback_model_not_role_indexing]]),
   so a model serving three roles is measured once and a role swap cannot silently inherit a stale level.
4. Do not extrapolate across quants of the same model either — quantization is exactly what the parent
   architect bench is testing for reasoning damage.

## ⚠ Design constraint learned the hard way (2026-07-20)
**Do NOT implement effort as a bare `max_tokens` cap.** A hard cap truncates the model *mid-derivation*,
and a truncated answer scores **wrong** — you lose the quality without the model ever getting to state a
cheaper answer. This exact failure was observed repeatedly today (AIME at 4096: response cut mid-working,
scored a garbage `1`; CoT at 8192: ~20% truncation; and the historical `enable_thinking` probe whose
"+33pp for thinking-off" is most likely this same artifact — see
[[feedback_parse_failure_rate_is_a_scoring_artifact]]).
**Effort must be steered primarily by the PROMPT** ("answer in at most two sentences of reasoning",
"give a brief justification then answer"), so the model *plans* a short answer and still emits a
well-formed final answer. A token cap is at best a backstop, and if used it needs a
`--reasoning-budget-message`-style graceful-close so the model terminates cleanly instead of being cut.

## Prioritized task list
- [ ] **E-1 — Design the ladder.** Draft 4–5 effort levels, e.g. L0 answer-only → L1 one-line
      justification → L2 brief step-by-step (bounded) → L3 full CoT → (L4 native `<think>` on).
      Levels must be *prompt* variants; note which also set a budget backstop.
- [ ] **E-2 — Measure the curve, once per model.** Sweep the levels on the **already-pinned**
      GPQA-Diamond items (`artifacts/architect-bench-gpu-20260720/questions_gpqa_diamond_cot.json`) so
      results are paired with everything measured today. Plot accuracy vs mean tokens → **one Pareto
      frontier per (model, quant)** — see the per-model INVARIANT above. Report truncation +
      parse-failure + empty-content rate at every level (a level that truncates or fails to terminate is
      **disqualified, not scored** — scoring it as "wrong" is the artifact that has already bitten twice).
      **Coverage target: every model in the production stack**, not just the architect-bench arms —
      gemma-4-26B-A4B (worker), Qwen3-Next-80B (ingest), the reviewer arm, and any drafter used
      standalone. Cheapest first; the frontdoor + architect curves are the two that gate E-4.
- [ ] **E-3 — Evaluate by rescue-rate, not mean accuracy.** Per
      [[feedback_accuracy_token_tradeoff_rescue_metric]]: score an effort level by how often it *rescues*
      tasks the cheaper level got wrong, versus its token cost. Mean accuracy hides that a level may only
      help on a narrow band of hard items.
- [ ] **E-4 — Per-role defaults, expressed as (model × level) pairs.** Map levels → roles *given the
      model currently bound to each role*; a bare "frontdoor = L2" is malformed (see INVARIANT).
      Operator's stated prior: **architect + reviewer should reason; frontdoor arguably too.** Frontdoor
      is the hard case — interactive, and it pays the token cost most, so it wants the **knee** of its own
      curve, not the top. Note the architect and reviewer currently share one model (122B-A10B-IQ2), so
      they share one curve but may sit at different points on it.
- [ ] **E-7 — Re-calibration trigger.** Make the invariant enforceable, not aspirational: a model swap,
      quant change, or kernel promotion **invalidates** that model's certified levels. Record each curve
      with its `(model, quant, kernel/era)` stamp and add a validator that flags a role whose bound model
      no longer matches the model its effort level was certified against. Same failure mode the registry
      already had — a role launching an artifact that had no model-indexed row of its own.
- [ ] **E-5 — Dynamic selection (stretch).** Let the router pick effort from task difficulty rather than
      pinning it per role — a natural extension of [[project_learned_routing_controller]]. Needs a
      difficulty signal that is cheaper than just running the hard path.
- [x] **E-6 — Interaction with the `<think>` axis.** ✅ 2026-07-21. Effort (prompt) and `enable_thinking`
      (native channel) are **independent axes**; measured the grid. R2b/R2d established unlimited native
      `<think>` LOSES for both models via a **non-termination tail** (18% A1 / 50% A4). **Budget-cap result
      (`--reasoning-budget N --reasoning-budget-message`):** force-closing `<think>` drove non-termination
      to **0%** and recovered accuracy to ≈ think-off for both models at both budgets, at ~1.6–3× tokens
      (vs 6× unlimited) — **no capped arm is statistically distinguishable from think-off (all p ≥ 0.62),
      and none beats it.** Higher budget (6144) was consistently ≤ lower (2048). **Conclusion: the native
      channel can be made *safe* with a budget cap, but the accuracy lever is the PROMPT (axis 1, +32pp),
      not native `<think>`.** Full table in `architect-model-selection-bench.md` §R2d + §E-6; driver
      `run_budget.sh`, analysis `e6_budget_analyze.py`; data `artifacts/architect-bench-gpu-20260720/e6_reasoning_budget/`.
- [ ] **E-6b — retest budget-cap on a NON-saturated suite.** E-6 ran on `gpqa_diamond_cot` (~85–90%
      ceiling), where "capped thinking ties think-off" may be a ceiling effect. Re-run the budget sweep on
      `olympiadbench_numeric` (harder) to see whether native thinking, once it terminates, *ever* beats the
      prompt-CoT baseline. Cheap: reuse `run_budget.sh` with the olympiad suite.

## Dependency graph
`R2a (done)` → `E-1 design` → `E-2 curve (per model, fan-out)` → `E-3 rescue-rate` → `E-4 role defaults` → `E-5 dynamic`.
`E-2` fans out per model and is the long pole; `E-4` cannot start until the frontdoor + architect curves exist.
`E-6` depends on **R2b** (thinking ON/OFF ablation, architect bench). `E-7` gates any deploy of `E-4`.
`E-4` is operator-gated (production config).

## Cross-cutting concerns
- **This is a production-config change surface**, hence operator-gated. Nothing here edits the stack.
- Token cost is a **throughput** cost on a shared box: 4× output tokens on the frontdoor is a real
  capacity hit, not just per-request latency. Weigh against `feedback_cpu_decode_bw_bound`.
- Prompt-effort levels interact with **agent-file compression operating points** (roles already carry an
  `agent_file_compression_operating_point`) — both change the prompt; don't tune them blind to each other.
- Whatever ladder is chosen must be expressible per-role in the registry, and **indexed by model/quant,
  not role**, for the measurement rows ([[feedback_model_not_role_indexing]]).

## Reporting instructions
Record per level × model: accuracy, mean/median/p90 tokens, truncation rate, parse-failure rate, and
rescue-rate vs the next-cheaper level. Flip the checkboxes here; a per-role default change is a proposal
to the operator, not an edit.

## Key file locations
- Pinned item sets + all R1/R2 evidence: `epyc-inference-research/artifacts/architect-bench-gpu-20260720/`
- Runner (already supports `--limit`, `--repeats`, per-question JSONL, truncation capture):
  `epyc-inference-research/scripts/benchmark/v7_quality_gate_runner.py`
- Analysis: `architect_bench_analyze.py`, `thinking_ablation_analyze.py`, `architect_bench_rescore.py`
- Prompt text currently lives in the adapters: `epyc-inference-research/scripts/benchmark/dataset_adapters.py`
  (`gpqa_diamond` = letter-only, `gpqa_diamond_cot` = full CoT — these are already L0 and L3).
