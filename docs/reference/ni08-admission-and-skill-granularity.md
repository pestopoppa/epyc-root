# Admission rules and skill-result granularity — source review

MAIN accepted AP-51, EV-10d and EV-10f on 2026-10-06. Design/documentation only: no gate changes, model runs or efficacy claims. Source pin: epyc-orchestrator `48a546e90fbc202a0c2ae103203621ba29175915`. Original proposal is retained at `/mnt/raid0/llm/tmp/ni08-equation-designs-20261006/proposal.md`; MAIN corrected its legacy speed label against the actual current tier spec.

## AP-51: three rules act at different stages

| JIT-Agent rule | Meaning | EPYC comparison |
|---|---|---|
| Eq.4 preference-pair construction | Reward strictly increases; latency and cost do not worsen; at least one efficiency improvement is strict. A weighted gain scales the preference pair. | This does not define an archive predicate. |
| Stage-III bank retention | Reward matches/exceeds the frontier and at least one reward/latency/cost dimension strictly improves. | Distinct from training-pair selection. |
| Eq.6 reward channels | Efficiency credit requires reward at least the incumbent, including equality; below-incumbent reward suppresses both efficiency channels. | This shapes training rewards, rather than independently admitting archive entries. |

These distinctions follow [JIT-Agent v2 §4.1](https://arxiv.org/html/2608.25593v2#S4.SS1); `intake-1320#02` identifies the local claim. No performance comparison is inferred.

EPYC `ParetoArchive.update()` applies non-dominance within the same evaluation tier, excluding T0 from frontiers. Dominance requires every objective to be at least as good and one strictly better; non-dominance can retain a quality decrease paired with another gain. The current registered `TierSpec` builds **quality↑, corrected questions/eval-wall-hour↑, −cost↑, reliability↑** (`tier_specs.py` `_rate_objectives_from`, `OBJECTIVE_AXES_4D`, `TIER_SPECS`); legacy tokens/second vectors are replay-only and cannot mix with the live frontier. Trusted fingerprint reproductions use componentwise median representatives (`pareto_archive.py` representative-admission methods). Thus the current axis is a task rate, despite old archive type comments saying “speed.” None of these layers computes JIT's preference-pair weight.

## EV-10d: scalar proposal reward versus measured-result admission

[Harness-R1 §3](https://arxiv.org/html/2608.02276v1#S3) defines reward using the mean outcome difference from rerunning the full same batch, including previously successful tasks. Valid complete patches may receive negative reward; invalid/no-op/ultimately incomplete candidates receive zero and remain in the candidate group. Its scope is same-batch/transductive, without persistent cross-batch patch memory. Those facts do not prove a universal selection-bias correction. Local discussion locator: `intake-1323#record`.

EPYC `SafetyGate.check()` makes baseline/per-suite keep, retry or revert decisions, including resolution-aware suite thresholds. The failure counter increments only on counted failed verdicts, once per result; retry-not-revert evidence neither increments nor resets it. `should_rollback()` compares that counter against three. Numeric archive eligibility is a separate same-tier multi-objective decision. Invalid/skipped action outcomes are handled and excluded outside this scalar gate; their absence from the numeric frontier is not a zero-valued proposal-group contribution. This source comparison supports no change to acceptance, rollback or training rules.

## EV-10f: suite aggregates cannot identify hidden task regressions

`scripts/autopilot/skill_efficacy.py::evaluate_skill_efficacy()` intersects suite-keyed mappings, computes one delta per suite and their mean, and applies a per-suite negative-delta guard plus aggregate-gain condition. Its split variant repeats that calculation on dev and test. Neither API receives per-task outcomes. A rising suite mean may therefore conceal task regressions; WikiSkill does not supply the missing task comparison. This is an interface limitation, not evidence that particular current tasks regressed. The accompanying handoff retains verified effect pointers and treats `intake-1321#record` only as discussion.
