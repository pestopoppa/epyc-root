# TOC-CMP-4 pre-registration: compaction A/B (DRAFT for operator ack, 2026-11-09)

Status: written before any run. Nothing here has been measured. The arm set (section 2) is the one open choice; it is
pre-registered as option (a), the recommendation recorded in the TOC-CMP-4 box. If the operator picks option (b), only
section 2 and the run count in section 6 change; the rest stands.

## 1. Question and primary endpoint

Does replacing a folded history by a different compaction artifact change how often the model's next actions are
blocked or error out, compared with the other arms, at the same context boundary?

Primary endpoint: **blocked actions per step (BAPS)**, defined in TOC-MP-3(b): blocked or error actions among the
first 5 actions after the compaction boundary, divided by actions taken (at most 5), with deliberate re-reads of the
spilled log counted separately and excluded from the numerator. Lower is better.

Source field, verified 2026-11-09 in `src/graph/trajectory_artifact.py` (`note_turn`, lines 262-275): per turn, when
`features().context_arm_ab` is True, the artifact carries `blocked` (bool), `log_follow_attempts`, `log_follows`,
`code_sha256` and `turn_wall_s`. BAPS is therefore derivable per point from existing turn records; no schema addition is
needed. The boundary turn index comes from `ORCHESTRATOR_CONTEXT_FORCE_TURNS` / `ORCHESTRATOR_CONTEXT_TRIAL_INDEX`.

Secondary (reported, never gating): accuracy of the final answer, **Pass^3** (section 5), log-follow rate, turn wall
seconds, injected tokens at the boundary.

## 2. Arms (option (a): implemented names only)

| Arm | Implemented as | Role |
|---|---|---|
| `summary_only` | `context_arm_ab.ARMS` | the summary-compaction baseline |
| `pointer_only` | `context_arm_ab.ARMS` | pointer to the full log, no summary |
| `prune_pointer` | `context_arm_ab.ARMS` | pruned history plus pointer |

Not in `ARMS` and therefore NOT pre-registered under (a): `raw tail` and `FIFO`. `full_history` and `summary_pointer`
exist in `ARMS` but are outside this contrast; `full_history` may run as a diagnostic ceiling only if budget remains
and is excluded from every test below. If the operator chooses (b), add `raw_tail` and `fifo` to `ARMS` first and
extend this table; the three-arm contrasts then become the six pairwise contrasts, with section 4's correction updated.

## 3. Design

- Unit of analysis: one **compaction point** = (task, forced boundary turn) pair, identical across arms and repeats
  (paired by point).
- Points: **at least 30 paired points per model**, drawn once, before the run, from the stratified boundary set below,
  and frozen (sha256 of the point list recorded in the receipt). Strata: boundary turn early / middle / late tercile of
  the task's trajectory, as fixed by the point list, not by outcomes.
- Repeats: **8 per (point, arm)**, up to 12 if the interim rule in section 7 asks for them. Repeats differ only in
  sampling seed; arm order is randomised per point by a seeded permutation recorded in the receipt.
- Models: each model is analysed separately; no pooling across models for the primary test.
- Config pinning: per run record model pin, build, sampling config, region, `ORCHESTRATOR_CONTEXT_BUDGET_TOKENS`,
  `ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION`, and prompt hashes. A run missing any pin is invalid, not imputed.
- Reconciliation with TOC-MP-3(a) (n >= 2 trials, prefer 4): the larger pre-registered number (8) governs only if the
  cost in section 6 fits an inference window; otherwise the run is a pilot labelled as such, never a confirmation.

## 4. Primary analysis

Per point and arm, BAPS is the mean over its repeats. For each pair of arms the paired difference d_i = BAPS_a - BAPS_b
is formed per point.

- Estimator: mean of d_i over points.
- Interval: **boundary-stratified bootstrap**, 10,000 resamples; resample points within each boundary stratum, then
  resample repeats within the selected points. Percentile 95% interval. Seed recorded.
- Minimum detectable effect: **0.10 BAPS** (the pre-registered MDE). With 30 points, 80% power and two-sided alpha 0.05,
  the design detects 0.10 only if the SD of the per-point paired difference of repeat means is at most
  0.10 x sqrt(30) / (1.96 + 0.84) = **0.196**. This is an assumption about an unmeasured quantity: the pilot (section 7)
  measures it, and if it exceeds 0.196 the experiment is declared under-powered for 0.10 before any claim.
- Multiplicity: three pairwise contrasts, Holm-adjusted over the three. A contrast is reported as an effect only if its
  adjusted interval excludes 0 AND |mean d| >= 0.10; smaller significant shifts are reported as "below the MDE".
- Formal-gate posture: until OP-ABSEQ, OP-PQP and OP-ALPHAWIN are decided, interim looks are futility-only (section 7).

## 5. Pass^3 and accuracy

Pass^3 per point and arm = C(c, 3) / C(r, 3), with c correct repeats out of r (the unbiased estimator of the chance that
three independent attempts all succeed), averaged over points, with the same stratified bootstrap. It is reported beside
accuracy (mean correct rate) because a method can raise accuracy while lowering reliability. No Pass^3 threshold gates.

## 6. Cost, stated before the run

Runs per model = points x repeats x arms = 30 x 8 x 3 = **720** (1,080 at 12 repeats). Duration per run is unknown
until the pilot; the row stays a BACKLOG compute row until a measured per-run time shows 720 runs fit a window. This is
a compute decision for the owning session, not made here.

## 7. Stopping rules (sufficiency)

- Pilot: first 8 points x 3 arms x 4 repeats (96 runs), used ONLY to estimate the SD of per-point paired differences,
  the per-run duration and the base BAPS. It decides nothing about the arms.
- Stop-for-futility at 15 points: if the pilot-and-interim SD estimate makes the 0.10 MDE unreachable at 30 points
  (SD above 0.196 by a margin whose rule is: lower 80% confidence bound on SD above 0.196), stop and report the
  experiment as under-powered rather than extend.
- Stop-on-answer: none before 30 points (interim looks are futility-only).
- Invalid-run policy: a run with a transport failure or missing pin is re-run once with the same seed; a second failure
  drops that (point, arm, repeat) and is counted in the receipt; more than 10% dropped voids the cell.

## 8. What would change my mind

If BAPS is ~0 in all arms at the base rate (nothing to improve), the endpoint is uninformative and the A/B is closed as
"floor effect", not as "arms equal". Record the base BAPS before interpreting any contrast.

## 9. Operator ack needed

Option (a) versus (b) in section 2, and whether a 720-run cell may be booked once the pilot gives a per-run time.
