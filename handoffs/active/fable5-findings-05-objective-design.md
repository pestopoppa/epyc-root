# Fable 5 findings 05 — Objective design: quality × tokens/sec is the wrong product; measure goodput

**Date**: 2026-06-12 (refinement pass; operator question: *"should I keep optimizing quality×speed or quality×(tasks completed per unit time)? A model producing unnecessary tokens at high quality would appear valuable while actually making tasks take longer."*)

## Verdict: your suspicion is correct, and it is worse than you suspect — the current objective vector is fully blind to token bloat.

**What the Pareto vector actually measures** (`src/autopilot_core/tier_specs.py:26-43`; `eval_tower.py:455-683 _aggregate`):
- `quality` = fraction-correct × 3 — bloat-invariant.
- `speed` = `aggregate_batch_tps` = total model-generated tokens ÷ batch wall time — **bloat-invariant by construction**: a config that makes the model 30% more verbose generates 30% more tokens in 30% more time; t/s is unchanged (or slightly *up*, since longer decodes amortize prefill and thread-ramp). The metric rewards token *production rate*, not task *progress rate*.
- `cost` = `mean(cost_tier)/4` (`eval_tower.py:488-489`) — a **routing-tier** average (which role class served the request), **not** a token count. Note: `program.md:123` describes the cost proxy as `sum(tokens_generated/throughput)` (wall-occupancy) — the constitution describes an objective the instrument does not compute. Another stated-vs-running divergence for the findings-01 file.
- `reliability` = non-error fraction — bloat-invariant.

So a verbose config and a terse config at equal correctness are **Pareto-indistinguishable** while differing 30% in wall-per-task — the exact failure you described. The dominance test cannot prefer the terse one on any axis.

**Corroborating evidence that this blindness has been costing you**: an entire manual research domain exists as corrective work the optimizer could not discover natively — TrimR think-block pruning (+6pp GPQA), static brevity word limits (KEEP verdict), the reasoning-compression handoff cluster, tool-output compression, TALE budget evals, `enable_thinking=False` (+33pp on frontdoor *and* massive token savings from killing degenerate `<think>` loops). Every one of these is a human hand-feeding the system token-efficiency because its objective cannot see it. A correctly-shaped objective would have let the autopilot find several of these itself — that is the North Star's "optimally learns" clause failing at the objective layer, upstream of everything findings-01 fixes at the measurement layer.

## Recommended redesign

**Replace the speed axis with task rate; keep quality; keep reliability; retire the tier-cost axis.**

- **`task_rate`** = questions completed ÷ eval wall hours (`n / (eval_wall_s/3600)`). Both inputs are **already journaled** (`eval_wall_s`, n) — the new axis is *replayable over your entire journal history at zero inference cost*, and the frontier rebuild uses the `pareto_epoch` machinery you already built for the 2026-06-02 speed rebase.
- **Goodput** = quality × task_rate / 3 = *solved* tasks per hour — the scalar you actually care about; report it, but keep the two factors as separate Pareto axes so the quality↔rate trade-off surface stays visible (a slow-but-smart config and a fast-but-weaker config should both survive on the frontier; a verbose config now gets strictly dominated).
- **Why retire the tier-cost axis**: deeper-tier (slower) roles already show up in wall time, so task_rate subsumes the occupancy story the cost proxy was reaching for — with measured wall instead of stale per-role throughput constants. Going 4-D → 3-D also **densifies the frontier**: in 4-D with ~9% noise, near-everything is non-dominated by luck, which is part of why 777 trials produced only 5 frontier points of mostly-noise geometry. Fewer, better axes = more decisive dominance = more learning signal per trial. (Keep tier-mix as telemetry — it still matters for capacity planning.)
- **Keep t/s and add `tokens_per_solved_task` as telemetry, not objectives**: t/s diagnoses host throttle (its real remaining job); tokens-per-solved-task is the planner-visible bloat diagnostic that makes compression experiments *self-motivating* (PromptForge/flag mutations that cut tokens at flat quality now show up as task_rate wins — the optimizer inherits the entire brevity/TrimR research direction natively).

**Caveats / instrument coupling** (all consistent with findings-01-impl):
1. Wall time carries the same ~9% host-noise CV as t/s — the sequential/median-cluster admission rules (findings-01 Phase 1.4) apply unchanged to the new axis.
2. `task_rate` depends on the question mix and eval concurrency — both are part of the instrument: fix them per core-version (findings-01 Phase 2.1), bump the policy version on change. Per-suite wall telemetry attributes which suites pay the token bloat.
3. Degenerate-terseness risk (model answers too curtly): bounded — quality is a co-equal axis, and suite scoring requires correct, extractable answers. For production chat the brevity bias is desirable anyway; if a long-form role emerges, give that suite a format-adequacy check rather than re-rewarding tokens globally.
4. Tool tokens stay excluded (already correct: tool output never counted as throughput) — tool use continues to be judged purely by downstream correctness, now plus its wall cost, which is the right price signal.

**Implementation shape** (slots into findings-01-impl as Phase 1.6, ~1–2 days):
1. Add `task_rate` to `objectives_from` (`tier_specs.py`) computed from `eval_wall_s`; journal both vectors for one shadow period.
2. Replay the full journal under the new vector → rebuilt 3-D frontier + a one-page diff report ("which historical 'wins' were bloat artifacts") — this report is itself the decisive observation: if ≥2 of the 5 current frontier points fall off under goodput, the case is proven on your own data.
3. Flip the archive/gate/baseline to the new vector behind a policy-version bump; retire the t/s axis from dominance.
4. Update `program.md`/system-card goal-metric text to match (closing the §"program describes a different cost proxy" divergence).
