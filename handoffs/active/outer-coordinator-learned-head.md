# Outer-Coordinator Learned Head (Claude-driven loop)

**Status**: SCOPING ONLY — no implementation tasks until OC-0 completes
**Created**: 2026-04-26 (via Trinity deep-dive — intake-474, ICLR 2026)
**Priority**: SPECULATIVE (long-term; do not start before tri-role + DAR + LRC Phase 4 land)
**Categories**: agent_architecture, autonomous_research, routing_intelligence
**Related**: [tri-role-coordinator-architecture.md](tri-role-coordinator-architecture.md), [meta-harness-optimization.md](meta-harness-optimization.md), [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md)
**Deep-dive**: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) (sections 2.3 and 3 — outer-coordination layer)

---

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

- [ ] **OC-0.1** Enumerate the per-turn decisions Claude makes in the autopilot loop today. Read `scripts/autopilot/` and the autopilot handoff to inventory: which model to dispatch to, when to plan vs execute, when to compact context, when to verify, when to terminate. Produce a table.
- [ ] **OC-0.2** For each decision in the table, mark whether it is (a) routinely-uniform (Claude always picks the same option in similar contexts — codifiable), (b) genuinely-context-dependent (would need a learned head), or (c) currently-arbitrary (needs a clearer rule before being learned).
- [ ] **OC-0.3** Identify the fitness signal: what quantity would the learned head be optimising? Per-task pass rate is too narrow for an autopilot loop. Possible candidates: pass-rate × token-cost, time-to-completion, autopilot trial success, eval-tower aggregate score across a session.
- [ ] **OC-0.4** Cost-benefit estimate: how many Claude tokens per autopilot run today, and what fraction is spent on the decisions the head would replace? If <20%, defer indefinitely. If >50%, this becomes a real candidate.
- [ ] **OC-0.5** Decide whether to escalate to OC-1+ (write the rest of this handoff) or to close as `not_pursued — insufficient ROI / blocking dependencies`. Either outcome is fine; the scoping is the deliverable.

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
  - Relevance: **direct prior art for the question this handoff poses** — can a learned head replace Claude-driven outer-loop coordination? Conductor answers "yes, with a 7B end-to-end RL coordinator" for reasoning benchmarks. Sibling paper to Trinity (intake-474, the inner-pool analogue).
  - Key technique: 7B LLM trained end-to-end with RL on terminal task reward; emits *both* (a) communication topology among workers and (b) targeted natural-language per-worker instructions; randomized-pool training yields agent-pool-agnostic generalization at inference; self-as-worker recursion provides a new test-time scaling axis.
  - Reported results: 7B Conductor exceeds best individual worker on LiveCodeBench and GPQA; SOTA claim in multi-LLM coordination regime; no public code/weights.
  - Delta from this handoff: OC-0 scoping must now treat Conductor as the *primary* peer architecture alongside Trinity. The relevant axes for OC-0 to compare against:
    - Action space: Trinity tri-role `(LLM, role)` ⊂ Conductor `(LLM, role, topology, NL-instruction)`. Conductor's superset suggests OC-0 should consider whether topology + NL-instruction are *necessary* for Claude-driven outer-loop replacement, or whether Trinity's narrower action space is sufficient at our scale.
    - Optimizer cost: Trinity ES on 10K params is CPU-feasible; Conductor 7B RL is GPU-only. **OC-0 must address whether GPU budget is acquirable or whether the design is bounded to ES-class optimizers**.
    - Replication risk: neither publication releases code; Trinity's ES recipe is more reproducible from paper alone than Conductor's multi-turn RL pipeline.
  - Caveats (Tier 2b): single-source from one author team across both Trinity + Conductor; multi-agent failure literature (MAST, arxiv:2503.13657) documents inter-agent misalignment as 36.9% of production failures — terminal-reward RL does not directly address verification failures; pool-agnostic generalization beyond the randomization distribution is unverified.
  - Required action before OC-0 completes: add Conductor row to the OC-0 peer-comparison table; document the GPU-budget gate; cite the Tier 2b failure-mode literature as a known unknown.
