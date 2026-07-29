# Creativity as Constrained Tail Search

**Format**: Standalone interactive HTML explainer (companion to this index entry)
**Artifact**: [`2026-05-23-creativity-constrained-tail-search.html`](2026-05-23-creativity-constrained-tail-search.html)
**Target system**: `epyc-orchestrator/scripts/autopilot/`
**Date**: 2026-05-23
**Status**: implementation landed in same session (see Progress 2026-05-23 §"AutoPilot constrained-creativity planner upgrade")

## Problem Statement

AutoPilot's planner originally treated creativity as `random.shuffle` over action types appearing &le;1 time in the last 30 trials, then injected three samples as candidates the controller had to defend. Three structural problems followed:

1. Tail candidates competed on equal footing with the obvious answer, with no rubric to judge them &mdash; the "Adjacent Possible" enumeration tended to be performative reasoning that picked the modal action anyway.
2. The mechanism ran every trial including during exploit phases on a working lead &mdash; wasted prompt budget.
3. Even when an off-default action was chosen, no falsifier was recorded, so the next trial's planner could not see what was-supposed-to-happen-but-didn't.

## Synthesis Framework

The HTML report develops a model of creativity grounded in three claims:

| Claim | Operational implication |
|---|---|
| Novelty alone is not creativity (the raw tail is mostly garbage) | Generate ideas under truth-preserving constraints, not by raising temperature |
| Creative ideas live on a ridge of high novelty &times; high validity &times; high compression | Score candidates on three orthogonal axes (info_gain, coherence, cost-adjusted usefulness) rather than six adjacent ones |
| Real insight lowers entropy *out-of-sample* &mdash; delusion only on data already seen | Persist a falsifier with every chosen action and surface still-open claims to the next planner pass |

## Deployed Operationalization

The framing is not abstract; it sits inside an autopilot loop that proposes the next experiment for an LLM orchestration stack. Four concrete moves replaced the prior tail-shuffle mechanism, all landed in the 2026-05-23 session:

1. **Tail samples promoted from candidates to seeds.** Under-used action types are surfaced as inspiration ("directions explored &le;1 time in last 30 trials") rather than mandatory candidates. Diversity priming without forcing the model to argue for noise.

2. **Stagnation gating.** The rich creativity protocol activates only when one of three signals fires: hypervolume slope below &epsilon; (`STAGNATION_HV_EPS = 1e-3`), trustworthy trial count &lt; 5, or three consecutive trials with the same `action_type`. Otherwise the planner uses a lean prompt. Structured creativity has a cost; pay it only when stuck.

3. **Rubric collapsed 6 &rarr; 3 axes.** Information gain (novelty + falsifiability + compression), coherence with evidence, and cost-adjusted usefulness. LLMs grade more crisply across three orthogonal axes than six adjacent ones.

4. **Falsifier persisted to the journal.** A second fenced block (`autopilot_rationale`) carries the chosen action's falsifier and self-scored rubric. Both fields land on `JournalEntry` (new optional fields with `.get(field, default)` migration); a new `ExperimentJournal.unfalsified_hypotheses()` helper surfaces still-open claims to the next planner pass.

Two further refinements: **fusion preference** (if top-two candidates can be encoded as one action that dominates both, prefer the fusion) and **quote-don't-regenerate** (the chosen action's rubric scores must be copied verbatim from the candidate table &mdash; anti-drift guard against performative reasoning).

## Failure Modes Catalogued

The HTML report enumerates the four ways this protocol can fail in practice, each paired with the deployed guard:

| Failure mode | Deployed guard |
|---|---|
| Performative reasoning (LLM writes rubric, picks modal answer) | Quote-don't-regenerate rule on the rationale sidecar |
| Rubric drift / score mushing across adjacent axes | Collapse to 3 orthogonal axes |
| Falsifier inflation (vague non-answers) | Persistence to journal + surface still-open ones to next pass; useless falsifiers age out |
| Local-optimum defence (alternatives dismissed in a sentence) | Stagnation gate + new tail seeds each pass |

None of these guards is bulletproof. They raise the cost of the failure mode enough that the cheaper path is to do the right thing.

## Implementation Map

| Change | File | Notes |
|---|---|---|
| New constants `CREATIVITY_N`, `TAIL_WINDOW`, `TAIL_SEED_COUNT`, `STAGNATION_HV_EPS`, `STAGNATION_STREAK` | `scripts/autopilot/autopilot.py` | Top of file, near `STATE_PATH` |
| Conditional `{stagnation_signal}` + `{exploration_block}` template variables | `scripts/autopilot/autopilot.py` | `CONTROLLER_PROMPT_TEMPLATE` |
| `_build_exploration_block()` helper (lean vs rich fragment selection) | `scripts/autopilot/autopilot.py` | Module-level helper after the template |
| Rationale capture wired into `JournalEntry` construction | `scripts/autopilot/autopilot.py` | Around `extract_action` call + trial record |
| `extract_rationale(text) -> dict` parser for `json:autopilot_rationale` sidecar | `scripts/autopilot/controller_io.py` | Soft contract: missing/malformed returns empty defaults |
| New `falsifier`, `rubric_scores` fields on `JournalEntry` | `scripts/autopilot/experiment_journal.py` | `.get(field, default)` migration path; asdict writer covers it |
| `unfalsified_hypotheses(n=5)` helper for cross-trial feedback | `scripts/autopilot/experiment_journal.py` | Returns `[(trial_id, hypothesis, falsifier), ...]` |
| Operator-facing doc paragraph | `scripts/autopilot/program.md` | New section before "Interaction with Autopilot Infrastructure" |
| Tests | `tests/unit/test_autopilot_controller_io.py` (+6) and new `test_autopilot_creativity.py` (10) | 63/63 autopilot tests green |

## Related Wiki Pages

- [autonomous-research.md](../../wiki/autonomous-research.md) &mdash; broader context on autopilot evolution
- [llm-prompting.md](../../wiki/llm-prompting.md) &mdash; prompt-design patterns

## Related Handoffs

- `handoffs/active/autopilot-continuous-optimization.md` &mdash; long-running autopilot work
