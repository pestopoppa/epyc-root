# Outer-Coordinator Learned Head (Claude-driven loop)

**Status**: TERMINAL `not_pursued` 2026-07-29 — OC-0 completed; no implementation or OC-1 draft is justified without a measured Claude-loop bottleneck and decision-level provenance
**Created**: 2026-04-26 (via Trinity deep-dive — intake-474, ICLR 2026)
**Updated**: 2026-07-29 (OC-0 terminal disposition)
**Priority**: SPECULATIVE (long-term; do not start before tri-role + DAR + LRC Phase 4 land)
**Categories**: agent_architecture, autonomous_research, routing_intelligence
**Related**: [tri-role-coordinator-architecture.md](tri-role-coordinator-architecture.md), [meta-harness-optimization.md](meta-harness-optimization.md), [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md)
**Deep-dive**: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) (sections 2.3 and 3 — outer-coordination layer)

---

## 2026-07-28 Parked-Status Review

The implementation trigger remains closed. The routing-and-optimization index
still freezes DAR, tri-role, and outer-coordinator expansion until the DAR
regret and per-question-vector gates pass. The post-v8 AutoPilot campaign is
rebuilding its E8 speed and quality baselines; it has not produced an OC-0
measurement showing that Claude decision tokens are a material share of run
cost. Fugu remains useful competitive intelligence, but it does not satisfy
either local trigger.

- **Dependency evidence**:
  [`routing-and-optimization-index.md`](routing-and-optimization-index.md)
  continues to keep this lane frozen behind the routing gates.
- **ROI evidence**: no measured Claude-loop token-cost bottleneck or
  replaceable-token fraction has been filed.
- **Disposition**: remain active but parked. Do not start OC-0 or draft OC-1;
  re-review only when a dependency gate lands or a measured outer-loop
  bottleneck is attached.

## Terminal OC-0 disposition — `not_pursued` (2026-07-29)

OC-0.1 through OC-0.6 are complete. They separate the few contextual proposal
choices from deterministic or human enforcement, define a same-era outcome
vector, and compare the published design space. The decisive result is
negative: no durable planner/critic token ledger exists, so the replaceable
token fraction cannot be estimated honestly; current quality/provenance data
also cannot support a trainable decision label. This is insufficient evidence
to enter OC-1, not evidence that a learned head is ineffective.

**Decision:** close as `not_pursued — insufficient ROI evidence and blocking
provenance`, with no code, model, benchmark, or control-plane change. Reopen
only on a new, durable observation package containing per-decision provider
usage, realized outcome linkage, and current-era paired quality evidence. The
physical move to `handoffs/completed/` is deferred solely until concurrent
writers release the active handoffs that link here; moving now would break
their live references.

## 2026-05-28 Audit Reset — Executor Start Here

This file is an intentional parking lot for a speculative outer-loop idea. It should stay active because it is referenced by the Trinity/DAR/LRC routing program, but it is not an implementation queue.

| Condition | Action |
|---|---|
| Tri-role telemetry, DAR gates, or LRC Phase 4 are still unresolved | Do not start OC-1. Keep this as a reference and update only if new evidence changes the scoping inputs. |
| A measured autopilot/Claude token bottleneck appears | Run OC-0 only: inventory decisions, classify which are codifiable, identify a fitness signal, and estimate replaceable token fraction. |
| Claude decision tokens are <20% of autopilot run cost | Close as `not_pursued` after appending the OC-0 evidence. |
| Claude decision tokens are >50% and decisions are routinely uniform | Escalate to a rules-first replacement before learned-head training. |
| Claude decision tokens are >50% and decisions are context-dependent with a usable fitness signal | Draft OC-1+ implementation phases; do not skip OC-0 review. |

OC-0 deliverable skeleton:

```markdown
### OC-0 Scope Result

| Decision Claude makes | Current source/path | Uniform / context-dependent / arbitrary | Candidate replacement | Failure mode |
|---|---|---|---|---|

Fitness signal:
Replaceable token-cost estimate:
Recommendation: not_pursued / rules-first / learned-head spike
```

## Objective

Investigate whether a Trinity-style learned coordinator head (≈10K-parameter linear layer over a small backbone, trained via sep-CMA-ES against task fitness) can automate part of the **outer Claude-driven loop** — the layer where Claude (Claude Code, autopilot) makes coordination decisions across the inner inference pool.

This is the *direct* Trinity analogue. Trinity's coordinator (Qwen3-0.6B + 10K head) replaces what we currently do with Claude. The user's standing observation — *"we use Claude to drive our autopilot, isn't that similar?"* — flagged that our outer layer matches Trinity's heterogeneous-pool regime more closely than our inner pool does.

## Why this is speculative, not actionable yet

- **Long-term**: depends on tri-role (`tri-role-coordinator-architecture.md`) landing first, since the outer coordinator's action space includes a role axis.
- **Long-term**: depends on `decision-aware-routing.md` and `learned-routing-controller.md` Phase 4 producing reliable inner-pool routing, so the outer head has something predictable to dispatch onto.
- **Cost-benefit unclear**: every Claude turn is expensive in tokens — replacing some of that decision-making with a learned head saves tokens, but the head must be trained against a reliable fitness signal that captures *autopilot success*, not just per-task accuracy. We do not yet have that signal at the right granularity.
- **Risk of premature optimisation**: Claude's per-turn reasoning is not currently a known bottleneck. Replacing it with a learned head should be motivated by a measured pain point, not by analogy alone.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-474 | TRINITY: An Evolved LLM Coordinator (ICLR 2026) | high | new_opportunity |

Trinity's setup mapped onto our outer layer:

| Aspect | Trinity | Our outer-layer analogue |
|---|---|---|
| Coordinator | 0.6B SLM + 10K head | Claude (Claude Code / autopilot) |
| Pool | 7 LLMs (3 closed frontier + 4 open) | Inner orchestrator pool (open-source) + Claude itself |
| Action space | (LLM, role) per turn | (sub-agent or self, role, when-to-delegate, when-to-verify) per turn |
| Training | sep-CMA-ES against terminal binary reward | Would need: autopilot success oracle |

The mismatch is in the action-space — our outer loop does *more* than `(model, role)` selection. It also decides when to plan, when to compress, when to escalate, when to call tools. Any learned-head replacement must scope which decisions it covers.

## Phase OC-0: Scoping (REQUIRED before any implementation)

Goal: produce a written scope document that answers the questions below. No code, no models, no benchmarks. Deliverable is a section appended to this handoff, reviewed by the user, before OC-1+ phases are even drafted.

### OC-0.1 — committed autopilot decision inventory (2026-07-29)

This is an inventory, not a proposal to learn or automate any row. It was read
from the committed `scripts/autopilot/autopilot.py` / `actions.py` controller
surface; concurrent worktree changes were intentionally excluded. The apparent
"Claude decision" is often a constrained choice already made by deterministic
code, a SafetyGate, or an operator boundary.

| Decision in one controller turn | Current chooser / mechanism | Non-negotiable constraint | OC-0.2 classification |
|---|---|---|---|
| Which experiment/action type to propose (`seed_batch`, numeric, prompt/code mutation, structural experiment, deep eval, compact, rollback, etc.) | Planner proposal, normally through the draft-critique provider path | Universal schema validation, allowed action types, feature/dependency state, blacklist and dirty-target fences run before dispatch | **Context-dependent.** The choice may be learnable; the guards are not. |
| Which role/model/task mix to evaluate for a seeder batch | Seeder receives the selected action plus active-role/stack-prior context | Active registry roles and placement/availability checks bound the selectable pool; this is not a free model catalogue | **Context-dependent.** Revisit only after the inner-pool role surface is stable. |
| Which one-variable numeric surface and parameter to probe | Planner or deterministic numeric fallback | One explicit parameter, operator-suppressed surface list, apply failure/no-change handling, and live config validation | **Split:** fallback rotation is **uniform**; surface/parameter choice is **context-dependent**. |
| Whether a proposed action is admissible at all | Deterministic dispatcher, SafetyGate, blacklist/retry logic, sequential-evidence gates | Must never be delegated to a learned head: fail-closed validation, trust/era fences, cleanliness checks, and retry caps are enforcement | **Uniform.** Retain deterministic enforcement. |
| Whether to replace a blocked/repeated/blacklisted proposal with a seed or replayable numeric fallback | Deterministic fallback helpers informed by blacklist and trial counter | Avoid repeat no-op loops; W8/sequence requirements must preserve replayable evidence | **Uniform.** Policy constants may be measured later, but dispatch remains deterministic. |
| Whether to force baseline-reference, fresh-eval, higher-tier, coverage, or frontier-rerun work | Deterministic sequential/outcome/coverage-pressure helpers | These actions preserve estimand, paired evidence, and minimum coverage rather than maximize a one-turn score | **Uniform.** Retain deterministic evidence maintenance. |
| Whether to apply, keep, revert, or roll back a mutation/config/flag action | Action handler plus SafetyGate, local gate checks, simplicity checks, and checkpoint restore | A learned head may suggest; it cannot bypass quality, attestation, rollback, or baseline-update authority | **Uniform** at acceptance/revert; the upstream proposal is separately **context-dependent**. |
| Whether to compact a slot / manage context and when to checkpoint | Explicit `slot_compact` action plus interval/shutdown checkpoint logic | Compaction inputs and checkpoint durability are operational safeguards, not an unconstrained planner preference | **Split:** compaction timing may be **context-dependent**; checkpoint durability is **uniform**. |
| Whether to retain and surface prior strategy/convention memory | Bounded StrategyStore retrieval and planner-prompt construction | Visibility, bounds, provenance, and no-crash fallback behavior are deterministic | **Currently arbitrary.** Retrieval exists, but no outcome-backed ranking rule yet distinguishes useful from merely available memory. |
| Whether to stop, pause, or escalate for review | Loop caps on meta/skip/rejected drafts plus operator/authority gates and terminal checkpointing | Operator boundaries, trust-boundary writes, and loud-stop conditions remain human/deterministic | **Uniform.** Retain deterministic/human control; only a future risk predictor is a candidate. |

### OC-0.3 — fitness signal: a gated outcome vector, not a scalar reward (2026-07-29)

The candidate target is the **next eligible experiment outcome vector**, not
per-task pass rate and not the existing Pareto score copied into a new learner:

```text
eligibility = realized outcome_status=ok
              AND no bug_corrupted_by/supersession
              AND same named protocol + instrument era + tier

label = (quality delta, task-rate/latency efficiency, reliability,
         controller-token cost, elapsed wall time)
```

Quality, efficiency, and reliability stay a **per-tier Pareto vector** rather
than being scalarized: the committed controller already represents its runtime
objectives as `(quality, speed, -cost, reliability)` and has a shadow
task-rate vector. A future offline coordinator may learn a ranking only among
eligible, same-tier outcomes; it may not convert a quality/safety loss into a
cheaper-action win. Controller-token cost and end-to-end elapsed time are
recorded as required evaluation dimensions, not substitutes for quality.

This is deliberately **not a train-now label**. The current journal is useful
for outcome eligibility and realized trial metadata, but the decision-plane
audit records missing historical eval-core/content-hash provenance, a
constant-valued quality core identifier, and no reliable per-decision
controller-token attribution. Before OC-1, the minimum data contract is: one
stable action/decision id; planner and critic token counts; realized (not
intended) apply/revert outcome; protocol/era/core/dataset identity; paired
quality result; and explicit exclusion reasons. Until then, this vector can
guide only offline schema work and must not drive action selection, promotion,
or a learned-head claim.

### OC-0.4 — cost-benefit result: denominator absent, so no ROI claim (2026-07-29)

An honest numeric estimate is **not currently possible**. The durable trial
journal records evaluated-model token fields (for example instruction-token
count and generated-token/eval metrics), but not planner/critic provider usage
per controller turn. The planner configuration exposes output **caps** (local
planner default 2,048; brief/draft caps 1,536/2,048); caps are not observed
Claude consumption. PEAF's documented ~150 cached input plus ~50–100 output
tokens is a forecast addendum, not a complete planner-turn ledger.

Consequently, neither the numerator (tokens a small head could actually
replace) nor the denominator (total Claude controller tokens per run) exists.
The 20%/50% thresholds cannot be evaluated, and this work must be treated as
**not qualified for OC-1** rather than guessed into a positive ROI. The minimal
future measurement is provider-reported input/output/cache tokens for draft,
critique, and any follow-up turn, joined to a stable controller decision id and
run id; only then may a descriptive replacement fraction be computed. It is an
observation metric, not a promotion or deployment gate.

- [x] **OC-0.1** Enumerate the per-turn decisions Claude makes in the autopilot loop today. Read `scripts/autopilot/` and the autopilot handoff to inventory: which model to dispatch to, when to plan vs execute, when to compact context, when to verify, when to terminate. Produce a table. ✅ 2026-07-29 — committed controller inventory above; it separates planner suggestions from the deterministic/human gates that must remain outside any learned head.
- [x] **OC-0.2** For each decision in the table, mark whether it is (a) routinely-uniform (Claude always picks the same option in similar contexts — codifiable), (b) genuinely-context-dependent (would need a learned head), or (c) currently-arbitrary (needs a clearer rule before being learned). ✅ 2026-07-29 — classification is in the OC-0.1 table; enforcement and evidence-maintenance rows are uniform, proposal/routing/compaction timing are contextual candidates, and StrategyStore retrieval ranking is currently arbitrary.
- [x] **OC-0.3** Identify the fitness signal: what quantity would the learned head be optimising? Per-task pass rate is too narrow for an autopilot loop. Possible candidates: pass-rate × token-cost, time-to-completion, autopilot trial success, eval-tower aggregate score across a session. ✅ 2026-07-29 — selected the same-era, same-tier eligible outcome vector above; it remains an offline-only candidate pending decision-level provenance and token attribution.
- [x] **OC-0.4** Cost-benefit estimate: how many Claude tokens per autopilot run today, and what fraction is spent on the decisions the head would replace? If <20%, defer indefinitely. If >50%, this becomes a real candidate. ✅ 2026-07-29 — no observed planner/critic token ledger exists, so the replacement fraction and thresholds are uncomputable; OC-1 is not qualified until that provenance is collected.
- [x] **OC-0.6** **Design-space-reference table (NEW 2026-04-28, from intake-474 + intake-493)**: populate a comparison table of published learned-coordinator architectures inside the OC-0 deliverable. **Framing — this is competitive intelligence, not a list of architectures EPYC is committing to copy. The table answers "what are others publishing in this design space?" so OC-0.5 can decide informedly, NOT "which one do we replicate?"** ✅ 2026-07-29 — complete with the four-row table and synthesis below.

  | System (intake) | Action space | Optimizer + cost | Replication risk | Code/weights status | What to learn from / what NOT to copy |
  |---|---|---|---|---|---|
  | Trinity (intake-474, ICLR 2026 Sakana AI) | `(LLM, role)` per turn from a 7-LLM pool with tri-role {Thinker, Worker, Verifier} | sep-CMA-ES on 0.6B SLM + 10K-param head, ≈10h overnight at 32-way concurrency, CPU-feasible | LOW (paper recipe is reproducible from method section) | No public weights; methodology is reproducible | LEARN: tri-role action space (+5–8 pts in their ablation, optimizer-independent), sep-CMA-ES against terminal fitness as cold-start, SVD-FT for parameter-efficient adaptation. DO NOT COPY: penultimate-token finding (decoder-specific to their backbone), frontier-pool gain numbers (heterogeneous-pool-specific). |
  | Conductor (intake-493, ICLR 2026 Sakana AI, six-author overlap with Trinity) | `(worker_id, NL_subtask, access_list_into_prior_steps)` per coordination step; topology emerges from access-list selections; "role" is NOT a Conductor primitive | GRPO end-to-end RL on 7B base, 200 iter × batch 256 × **2× H100 80GB** | MEDIUM (code/weights promised in supplementary but not visible at intake date 2026-04-28; Sakana Fugu commercialization is the real public-artefact blocker, NOT GPU compute) | Promised post-anonymization | LEARN: end-to-end terminal-reward training as a coordination objective, randomized-pool training for pool-agnostic generalization. DO NOT COPY: 7B GPU-class architecture (out of CPU stack), recursive self-as-worker (small +1–2.2 pp gain not worth the action-space complexity at our scale). LCB headline of +1.03 pp vs GPT-5 is within pass@1 noise — do not over-weight. |
  | BaRP (intake-495, routing primitive) | One chosen model arm conditioned on prompt features and a performance/cost preference vector; no multi-turn topology or subtask generation | REINFORCE contextual bandit with entropy regularization; offline logged-bandit simulation | MEDIUM: relevant deployment-feedback shape, but high-variance policy gradient and public-benchmark transfer are unresolved | Paper pattern only; do not replace the existing router wholesale | LEARN: chosen-arm feedback is not full-information training, and preference conditioning can remain explicit. DO NOT COPY: call this an outer coordinator or assume its score/cost headlines transfer to long-output autopilot work. |
  | LLM Bandit (intake-496, routing primitive) | Per-request model choice conditioned on prompt, model identity, and preference vector; no coordination topology | PPO/GAE multi-objective policy; IRT difficulty/discrimination and 20–50-prompt onboarding claim | MEDIUM/HIGH: single-author evidence, short-output benchmark regime, and PPO is overpowered for a small arm count | Paper pattern only | LEARN: IRT-stratified calibration and availability/model-identity inputs. DO NOT COPY: the claimed cost reduction, the small-pool PPO machinery, or treat a model router as a learned outer loop. |

  **OC-0.6 synthesis (2026-07-29):** this is competitive intelligence,
  not an adoption shortlist. Trinity is the only CPU-feasible outer-loop
  analogue, but its compact `(LLM, role)` action space is materially narrower
  than EPYC's controller. Conductor proves that a larger language-mediated
  action space is publishable, not that it is locally economical or
  reproducible. BaRP and LLM Bandit are deliberately included as *inner-routing*
  contrasts: they inform feedback and calibration data design, but do not
  establish a learned coordinator. None of the four changes the OC-0.4 result:
  no measured controller-token replacement fraction exists, so OC-1 remains
  unqualified.

  Deliverable: this table appended to the OC-0 scope document, with explicit framing as competitive intelligence per user feedback (2026-04-28). Output is a markdown sub-section, no code. ~1 session.


- [x] **OC-0.5** Decide whether to escalate to OC-1+ (write the rest of this handoff) or to close as `not_pursued — insufficient ROI / blocking dependencies`. The OC-0.6 design-space-reference table is one input to this decision, alongside OC-0.1–0.4 (decision inventory + fitness signal + cost-benefit). Either outcome is fine; the scoping is the deliverable. ✅ 2026-07-29 — `not_pursued`: no observed planner/critic token ledger, no replaceable-token fraction, and no current decision-level provenance; reopen only with the named observation package.

**Gate**: OC-0 must complete and be reviewed before any OC-1+ work is drafted. If escalated, OC-1+ phases will be written based on OC-0's scope.

## Open Questions (resolve in OC-0)

1. Is Claude's per-turn reasoning actually a measured bottleneck (latency or token cost), or are we proposing a fix in search of a problem?
2. Is there a fitness signal for *autopilot session success* that is computable per-session, parallelisable for ES population evaluation, and not itself dependent on a frontier model?
3. Does a 10K-parameter head over a 0.6B backbone have the *capacity* to model decisions that currently require Claude-class reasoning? Trinity's coordinator picks `(LLM, role)` — a low-bandwidth decision. Outer-loop decisions may be higher-bandwidth.
4. Where does this sit relative to `meta-harness-optimization.md`, which already optimises the harness via PromptForge? Are these the same project at different layers, or genuinely separate?
5. If the head replaces only *some* decisions, where is the boundary, and what is the failure mode when the head is wrong (Claude-corrected vs propagated)?

## Relationship to Existing Systems

| System | Relationship | Why this isn't already covered there |
|---|---|---|
| `tri-role-coordinator-architecture.md` | Adds tri-role to the *inner-pool* router | Inner-pool focus; doesn't touch the outer Claude-driven loop |
| `meta-harness-optimization.md` | Optimises harness *components* (prompts, templates, code) via PromptForge | Optimises the static configuration; this handoff would optimise *per-call decisions* |
| `autopilot-continuous-optimization.md` | Runs the autopilot loop and accumulates Q-values | Consumes routing decisions; this handoff would inject a learned head into that consumption |
| `learned-routing-controller.md` | Trains the *inner* MLP routing classifier | Inner-pool only; no outer-loop coverage |

There is genuinely nowhere else this scope lives today. That justifies a stub.

## Notes

This handoff exists primarily so that the outer-coordinator analogue is *not lost* as a design idea. It is explicitly speculative. Do not promote out of SCOPING status without OC-0 completion + user approval. If after OC-0 the verdict is `not_pursued`, archive this handoff with the scoping document as the closing artifact.

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-493] "Learning to Orchestrate Agents in Natural Language with the Conductor"** (arxiv:2512.04388, ICLR 2026, Sakana AI)
  - **Framing**: competitive intelligence — what other groups are publishing in the outer-coordinator design space. **NOT a target architecture EPYC is committing to copy.** Treat as a guideline of what is being attempted, so we can selectively learn from it; do not pattern-match our roadmap to its choices.
  - Relevance: closest published attempt at the question this handoff poses (can a learned head replace Claude-driven outer-loop coordination?). Sibling paper to Trinity (intake-474, the inner-pool analogue) — six-author overlap, parallel design-space probes underpinning Sakana Fugu.
  - Key technique: 7B LLM trained end-to-end via **GRPO** (200 iterations × batch 256 × **2× H100 80GB**) with terminal task reward. Action space per coordination step is `(worker_id, NL_subtask, access_list_into_prior_steps)` — communication topology emerges as a *derived* consequence of access-list selections, NOT a separately emitted object; "role" is not a Conductor primitive. Randomized-pool training yields agent-pool-agnostic generalization; self-as-worker recursion provides a small (+1–2.2 pp) test-time scaling axis.
  - Reported results (concrete): LiveCodeBench V6 **+1.03 pp** vs best individual worker GPT-5 (within typical pass@1 noise); GPQA-Diamond **+2.7 pp** vs Gemini-2.5-Pro; open-source-only inference after randomized-pool finetune **+~10 pp** vs Claude Sonnet 4 (the strongest ablation result). LCB headline should not be read as a Trinity-style margin.
  - Code/weights status: **promised in supplementary post-anonymization but NOT visible at intake date (2026-04-28)**. Sakana Fugu commercialization is the real public-artefact blocker, not GPU compute — 2× H100 is rentable for low-three-digit dollars.
  - Delta from this handoff: OC-0 scoping should reference Conductor as a design-space data-point. Relevant comparison axes (record what others did, do not commit to matching):
    - Action space: Trinity emits `(LLM, role)` tuples; Conductor emits `(worker_id, NL_subtask, access_list)`. We are not bound to either; OC-0 is free to pick a smaller or different action space if appropriate to our orchestrator.
    - Optimizer cost: Trinity ES on 10K params is CPU-feasible; Conductor 7B GRPO is GPU-required (2× H100). For EPYC, ES-class optimizers remain the realistic path; Conductor is a North-Star data point, not a target.
    - Replication risk: Conductor weights pending public release; Trinity's ES recipe is the more reproducible-from-paper option.
  - Caveats (Tier 2b): six-author overlap with Trinity means the two papers are not independent corroboration of each other; multi-agent failure literature (MAST, arxiv:2503.13657) documents inter-agent misalignment as 36.9% of production failures — terminal-reward RL does not directly address verification failures; pool-agnostic generalization beyond the randomization distribution is unverified; +1.03 pp LCB margin is within noise.
  - Recommended action before OC-0 completes: add Conductor + Trinity rows to OC-0 design-space-reference table (NOT a "primary peer" comparison) with explicit "competitive intelligence, not target architecture" disclaimer; cite Tier 2b failure-mode literature as a known unknown.

## Research Intake Update — 2026-06-25

### New Related Research

- **[intake-728] "Sakana Fugu Technical Report"** (arxiv:2606.21228, Sakana AI, June 2026)
  - Relevance: Fugu is the commercial productization of Trinity (intake-474) + Conductor (intake-493) — the direct competition/calibration point for this handoff's scoping question. Its release settles the "does this design pattern work at production scale?" question: yes, at frontier-level benchmarks, though with important caveats below.
  - Key technique: LLM trained to orchestrate a diverse pool of frontier models (GPT-5.5, Gemini 3.1 Pro, Claude Opus 4.8) via adaptive agent scaffolds. Two variants: Fugu (picks one best worker per query, latency comparable to a single model call); Fugu Ultra (coordinates full team, max quality). Agent pool opt-out for compliance/privacy. Training: evolutionary algorithms + RL + large-scale fine-tuning.
  - Reported results (self-reported, June 2026, non-standardized scaffolds): Fugu Ultra — SWE-Bench Pro 73.7%, LiveCodeBench 93.2%, GPQA-D 95.5%, MRCRv2 93.6%. Fugu — SWE-Bench Pro 59.0%, LiveCodeBench 92.9%, GPQA-D 95.5%.
  - **Critical caveats (Tier 2b, credibility_score 1)**: (1) Methodology concern: multi-agent relay team vs single-model sprinter — Fugu Ultra coordinates multiple frontier models and verifies/recurses, then reports that score against solo frontier baselines; comparison is not apples-to-apples. (2) Claude Fable 5 and Mythos Preview excluded from agent pool (not publicly accessible) — Fugu Ultra orchestrates the *second tier* of frontier models to claim parity with the *first tier*. (3) Real-world testing showed 30-minute Fugu Ultra wait times and performance below Fable 5 within 24h of launch (TechTimes, June 24, 2026). (4) SWE-Bench Pro 73.7% context: standardized SEAL leaderboard top is GPT-5.4 at 59.1%, Claude Opus 4.8 at 69.2% vendor-reported — Fugu's 73.7% is plausible but non-standardized. (5) Benchmarks are self-reported.
  - Delta from this handoff: (1) Confirms that the Trinity/Conductor approach scales to production at frontier-equivalent quality — the OC-0 scoping question is effectively answered by a third party. (2) The Fugu/Fugu-Ultra two-tier design (single-best-worker vs full-team) is a direct design reference for our latency/quality tradeoff axis in OC-0. (3) Agent pool opt-out for compliance is a concrete implementation pattern (not available in Trinity/Conductor papers). (4) Conductor code/weights: promised at intake time but blocked by commercialization — Fugu's launch likely means weights remain commercial. Revise OC-0 replication risk upward.
  - Recommended action: Add Fugu as a calibration row in the OC-0 design-space table: "Trinity + Conductor → Fugu: real-world validation that the pattern works, latency cost is ~30 min for Ultra, compliance opt-out is implemented." Do NOT interpret Fugu's benchmark scores as a ceiling — they are non-standardized multi-agent scores, not single-model baselines.
