# TOC-CMP-4 pre-registration: compaction A/B (2026-11-09)

Status: written before any run. Nothing here has been measured. The operator selected option (a) on
2026-11-09 and approved low-rank booking conditional on pilot cost, as recorded in the TOC-CMP-4 handoff.
The implemented three-arm set in section 2 governs; the alternative below is historical context.

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

## 7a. Validity rule: boundary not reached (operator-approved 2026-11-09)

A run whose trajectory ends before its forced boundary turn (no `boundary` event) carries no compaction
and is **voided**, not scored as zero blocked actions. Arms are paired by point, so the whole point is voided
(all arms and repeats; ledger rows kept and marked void) and **replaced by the next reserve point of the same
stratum, in the same seeded order** (hash order continuing after the frozen 10 per stratum; the reserve is
part of the receipt). Voided points, their replacements and any exhausted reserve are reported in the run
output and the receipt; a replacement is never chosen by outcome. Voids do not count against the section 7
10% dropped-run limit, but the void rate is reported per stratum beside every contrast. The frozen 30-point
sha256 is unchanged by replacements; replacements are listed separately.

## 8. What would change my mind

If BAPS is ~0 in all arms at the base rate (nothing to improve), the endpoint is uninformative and the A/B is closed as
"floor effect", not as "arms equal". Record the base BAPS before interpreting any contrast.

## 9. Decision record

Operator-approved 2026-11-09: option (a), with the 720-run cell at low rank once the pilot gives a per-run time.

## 10. Isolated pilot adapter (2026-11-17; prospective)

The pilot adapter under `scripts/experiments/toc-cmp-4-live/` runs the REPL graph with a
row-owned loopback server. It uses a private endpoint rather than claiming the production
frontdoor's `:8070`: the running production API can route unrelated traffic to that port.
All pilot arms share the same pinned model, production kernel, chat template and server
shape (four slots, 65,536 tokens per slot). This is an isolated diagnostic pilot, not a
measurement of live tenant contention or a deployment of experimental graph flags.

The first eight points in the frozen receipt are all in the early stratum. Preserve that
prospective ordering; report stratum coverage explicitly. Their variability cannot establish
the MDE assumption for middle or late boundaries. No confirmatory arm conclusion follows
from the pilot. Missing external grades remain UNKNOWN for accuracy and Pass^3; graph finish
flags do not substitute for correctness. Missing post-boundary actions do not score zero BAPS.

Stop at the fixed pilot matrix, the allocator STOP/deadline or the launcher's declared time
cap, preserving raw attempts and partial/void/UNKNOWN outcomes. The publisher smoke is a
separate instrument qualification and contributes no official pilot observations. The
720-run booking and live-stack validation remain separate from adapter preparation.

The analysis implementation preserves paired point and repeat resampling. For a future
complete cell it reports marginal 95% intervals, Holm-adjusted empirical bootstrap tail
areas and conservative Bonferroni simultaneous intervals, requiring both adjusted tests
and simultaneous intervals to pass before applying the MDE. The simultaneous intervals
are explicitly Bonferroni, not labelled Holm-adjusted intervals. This conservative
implementation detail is declared before pilot data; synthetic arithmetic tests do not
establish interval coverage or the model's effect size.

## 11. v2 amendment (2026-11-21; prospective, written before the next run)

Status: nothing here has been measured. It applies to the next CONFIRMATORY or successor-pilot run and amends sections 2,
3, 4 and 6 only where stated; the option-(a) triple, the 0.10 BAPS MDE, the Holm-adjusted three-contrast rule and the
section 7/7a stopping and validity rules stay in force for the three v1 arms. The 96-run pilot already filed (r3) is a v1
pilot and is not re-labelled. Sources (research intake ak-intake-20261121, dives under
`research/deep-dives/ak-intake-20261121/`): CompAct-Bench protocol (intake-2762#record, intake-2778#record), Aggron prose-only
compaction (intake-2761#record), the async judge arm (intake-2770#record), CompactionBench (intake-2786#record).
Outcome-blind: every rule below is fixed by task and trajectory properties, never by an arm's result.

### 11.1 Controls (apply to every arm, v1 and new)

1. **Pre-filter (solved-in-all-uncompacted-repeats).** A candidate point is eligible only if its task was solved in ALL
   of k = 3 uncompacted `full_history` reference repeats on the same model and build (reference trajectory of at least 8
   rounds, so a 25/50/75% boundary has room). Input: the uncompacted reference runs; the filter is applied BEFORE the
   frozen point list is drawn, the tasks excluded are counted, and the sha256 of the filtered candidate list is recorded in
   the receipt beside the frozen 30-point hash. Analysis: BAPS and accuracy are conditional on solvable tasks; the report
   states this estimand and the exclusion count. If fewer than 30 eligible points remain the cell is a pilot, never a
   confirmation (extends section 3's pilot-labelling rule).
2. **Matched post-boundary action budget.** All arms at a point resume with the same budget B = min(25, ceil(1.5 x the
   median post-boundary action count of the point's uncompacted reference solves)); a continuation ends at B actions, a
   verified FINAL or the turn cap, whichever is first. B is computed from the reference runs, per point, before any arm
   runs. Analysis: BAPS keeps its first-five window; accuracy and Pass^3 are graded at termination under B; a run that
   hits B without FINAL is incorrect, recorded `budget_exhausted`, and counted separately from an error exit.
3. **Retention-ratio matching (self-built IRC calibration).** Compaction-producing arms (`summary_only`,
   `prose_only_frozen_append`) are calibrated so that the retained artifact is 10% of the boundary history in
   characters, accepted within [0.097, 0.103] (the CompAct tolerance). Iterative Ratio Calibration is self-built, because
   the CompAct prompt is not released (compact-page dive): re-prompt the same compactor with the previous attempt's measured
   ratio and the target until in tolerance, at most 4 rounds, temperature 0.3 as in the graph, the number of rounds and the
   achieved ratio recorded per point and arm. A point that cannot reach tolerance in 4 rounds is recorded with its achieved
   ratio and analysed with the ratio as a covariate (reported, not dropped). `pointer_only`, `prune_pointer` and the floor
   arm are not summaries; their retained ratio is measured and reported but not calibrated.
4. **Boundary placement 25/50/75%.** The forced boundary is placed at 25%, 50% or 75% of the point's reference
   trajectory length, one boundary per point assigned by a seeded permutation balanced across the three levels after
   length stratification, recorded in the receipt. These map to the existing early / middle / late strata (so the section 4
   stratified bootstrap is unchanged); each stratum keeps the >= 10 points rule for confirmation.
5. **Six-type error annotation on failed continuations.** Every incorrect continuation (any arm) receives a post-hoc
   label from the CompAct six types: critical omission (CO), factual distortion (FD), premature commitment (PC),
   lost resolution (LR), progress/state loss (PSL) and constraint/goal distortion (CGD); labels overlap, so a run carries
   a set. The annotator is an LLM blind to the arm and to the other arm's result, run offline over the retained trajectory
   and wire artifacts, with a 10% double-annotated sample for agreement (Cohen's kappa reported; labels are descriptive,
   never gating). Unannotated runs are UNKNOWN, not "none".

### 11.2 New arms

| Arm | Definition | Inputs | Analysis |
|---|---|---|---|
| `persistence_floor` | At the boundary all older history and any summary are dropped; the continuation sees the task statement, the system prompt, the reconstructed environment state (workspace as at the boundary) and the raw tail common to every arm (the last 20% of the budget), plus a one-line notice that earlier turns are not shown. No summary, no pointer | boundary environment snapshot from the reference run; orchestrator `context_arm_ab` arm `persistence_floor` (commit 52df680d) | Floor: how much of any arm's accuracy is environment persistence. Reported beside every contrast; an arm that does not beat the floor by the MDE is reported "not above persistence floor". Joins the contrast family (see 11.3). |
| `prose_only_frozen_append` | Prose tool output (reasoning and retrieved documents) is summarised; file, shell, SQL and test output is kept verbatim. Progressive indexed form: history is cut into fixed-size segments (4,096 characters of prose); each segment is summarised as it closes; the summary is appended after the unchanged prefix and is never rewritten or re-summarised; a segment index maps each summary to the verbatim span. NOT blocked on kv-prefix-fork P1 (it creates no concurrent sequence). The scheduler accepts the name; the arm body is not yet implemented (TOC-CMP-ARM-PROSE-FROZEN) and the graph refuses it with a named reason | the same boundary history; the prose / non-prose classifier rule of TOC-CMP-NONPROSE-TALLY | Contrasts with `summary_only` (same compactor, same 10% budget per control 3). Its prefix-cache reuse tally (11.4) is a primary secondary because the arm exists to keep the prefix stable. |
| `async_compaction_next_k_judge` | Compaction runs asynchronously while the agent takes its next k actions on the pre-compaction context; a judge scores whether those actions are consistent with the finished summary (alignment and non-contradiction, the V2-Fast judge of TOC-CMP-JUDGE-SHIM); accepted actions are carried, rejected ones are discarded and the step re-run on the summary | two sequences sharing the pre-compaction prefix | **BLOCKED on kv-prefix-fork P1.** Defined here so the contrast family is fixed in advance; refused by `arms_v2.resolve_arms` until P1 lands. No v2 run may schedule it. |

### 11.3 Analysis changes

- The contrast family is every pairwise contrast among the arms ACTUALLY RUN in the cell (v1 triple plus the floor and
  `prose_only_frozen_append` is five arms, ten contrasts); Holm adjustment and the Bonferroni simultaneous intervals use
  that count, and the MDE rule is unchanged. Contrasts against `persistence_floor` are reported with the others.
  The family is fixed by the receipt before the run; adding an arm afterwards voids the cell. `analysis.analyze(...,
  arms=resolve_arms(...))` implements this; the default remains the v1 triple.
- Sample size: 11.1 and the extra arms raise runs per model to points x repeats x arms = 30 x 8 x 5 = 1,200
  (1,800 at 12 repeats). This is stated before any run; booking remains a separate compute decision (section 6).
- Floor effect (section 8) is judged on the arm set as run; a floor arm with BAPS ~ 0 is reported, not hidden.

### 11.4 Prefix-cache reuse tally (every run, every arm)

Per arm, report prefix-cache reuse = sum of cached prompt tokens / sum of prompt tokens, token-weighted over all turns and
over post-boundary turns separately, beside accuracy and cost. Source: the per-turn server counts already in the trajectory
artifact (`cached_prompt_tokens`, `prompt_tokens`, taken from the llama-server slot timings; never estimated). A turn with
a missing count is excluded and counted as unobserved; a run with no observed turns reports no reuse (None, not 0).
Voided points are excluded. Implemented in `scripts/experiments/toc-cmp-4-live/arms_v2.py` (`prefix_reuse`,
`prefix_reuse_by_arm`), recorded per run in `RUNS.jsonl` and per arm in the ledger summary by `runner.py`; offline tests in
`test_arms_v2.py`. The tally is descriptive: a higher reuse is not an accuracy claim.
