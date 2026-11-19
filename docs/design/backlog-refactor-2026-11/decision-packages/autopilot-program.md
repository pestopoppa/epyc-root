# Decision package: autopilot-program

Destination handoff `handoffs/active/autopilot-program.md` · fold 20 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 13 · excluded: 1. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. AP-58: reseed the speed axis on ANY eligible in-era frontier measurement?

- Context: `handoffs/active/autopilot-continuous-optimization.md:174@7eb7a4a3c911` (manifest `handoffs/active/autopilot-continuous-optimization.md:174@3ac825873dfb`, id `a51c6751025c`)
- Gated worker box(es): `AP-58` (handoffs/active/autopilot-continuous-optimization.md:174)

- **Option A (recommended)**: Reseed on any eligible in-era measurement. *Tradeoff:* Closes the unreachability shape on every early-return path; changes when the speed fence closes.
- **Option B**: Keep reseeding on quality improvement only. *Tradeoff:* No change; the speed fence can stay open forever after a speed-era boundary.

**Recommendation: A.** The same unreachability shape survives on five paths; a design that can leave a fence open indefinitely is the defect.

## 2. Autopilot: what to do with the 419 depressed update-path rows (old_q recorded)?

- Context: `handoffs/active/autopilot-continuous-optimization.md:462@7eb7a4a3c911` (manifest `handoffs/active/autopilot-continuous-optimization.md:462@3ac825873dfb`, id `aab81a1062a5`)
- Gated worker box(es): `handoffs/active/autopilot-continuous-optimization.md:462`

- **Option A (recommended)**: Materialise the 419 (memory_id, old_q, new_q, ts) as a read-only artifact and decide on it. *Tradeoff:* Nothing destroyed; decision on evidence.
- **Option B**: Reverse all 419. *Tradeoff:* Restores the depressed rows; also undoes every legitimate wrong-answer signal.
- **Option C**: Leave as-is. *Tradeoff:* No work; depression stays.

**Recommendation: A.** No predicate separates the two kinds; the box forbids a purge and recommends the artifact.

## 3. AP-54: pick the wiki-fence arming mechanism (gates the AP-54b A/B).

- Context: `handoffs/active/autopilot-continuous-optimization.md:724@7eb7a4a3c911` (manifest `handoffs/active/autopilot-continuous-optimization.md:724@3ac825873dfb`, id `bf59236c91ba`)
- Gated worker box(es): `AP-54b` (handoffs/active/autopilot-continuous-optimization.md:724)

- **Option A (recommended)**: Pick the mechanism once the fence and path recording land. *Tradeoff:* Unblocks AP-54b with a known arming path.
- **Option B**: Defer AP-54b. *Tradeoff:* No A/B; wiki influence on eval rollouts stays unknown.

**Recommendation: A.** The A/B is filed and costed; it needs only the mechanism choice after the code lands.

## 4. AP-63d: switch `parent_trial` consumers (config_diff, PEAF r^2, BSV-3 rows) from the same-species heuristic to `lineage.parent_trial_id`?

- Context: `handoffs/active/autopilot-continuous-optimization.md:768@7eb7a4a3c911` (manifest `handoffs/active/autopilot-continuous-optimization.md:768@3ac825873dfb`, id `382ae70ac5c0`)
- Gated worker box(es): `AP-63d` (handoffs/active/autopilot-continuous-optimization.md:768)

- **Option A (recommended)**: Switch to lineage.parent_trial_id. *Tradeoff:* Config diffs measure against the true parent under orx refill; historical diffs change meaning.
- **Option B**: Keep the same-species heuristic. *Tradeoff:* Continuity; diffs may compare against a non-parent.

**Recommendation: A.** Lineage is the recorded parent; a diff against a heuristic parent mis-attributes changes.

## 5. AP-65: should `_proxy_check` bind (violation at a threshold) instead of warning?

- Context: `handoffs/active/autopilot-continuous-optimization.md:779@7eb7a4a3c911` (manifest `handoffs/active/autopilot-continuous-optimization.md:779@3ac825873dfb`, id `1a02293c5bda`)
- Gated worker box(es): `AP-65` (handoffs/active/autopilot-continuous-optimization.md:779)

- **Option A (recommended)**: Make it a violation at a threshold from S3-AP-08 rotation-drop data. *Tradeoff:* Catches single-easy-suite gains; needs a defensible threshold.
- **Option B**: Record why a warning is the right strength. *Tradeoff:* No gate change; the one leg built for this case never gates.

**Recommendation: A.** It is the only leg for that failure and it currently gates nothing; set the threshold from S3-AP-08.

## 6. Autopilot early abort: how many consecutive infra-failed rows abort an in-flight batch, and abort or continue-and-mark?

- Context: `handoffs/active/autopilot-continuous-optimization.md:915@7eb7a4a3c911` (manifest `handoffs/active/autopilot-continuous-optimization.md:915@3ac825873dfb`, id `abfad8c243c3`)
- Gated worker box(es): `handoffs/active/autopilot-continuous-optimization.md:915`

- **Option A (recommended)**: Abort after N consecutive infra failures (N set by the operator). *Tradeoff:* Stops spending questions on a dead run.
- **Option B**: Continue and mark. *Tradeoff:* Keeps partial data; spends the whole batch.
- **Option C**: Status quo (RELIABILITY_FLOOR blocks at the end as RETRY). *Tradeoff:* No change; questions are spent before the block.

**Recommendation: A.** The floor already rejects such runs; aborting early saves the questions it would reject anyway.

## 7. Ratify or reverse: operator applies can no longer run from a worktree (exit 2).

- Context: `handoffs/active/autopilot-continuous-optimization.md:932@7eb7a4a3c911` (manifest `handoffs/active/autopilot-continuous-optimization.md:932@3ac825873dfb`, id `7e04aae01257`)
- Gated worker box(es): `handoffs/active/autopilot-continuous-optimization.md:932`

- **Option A (recommended)**: Ratify. *Tradeoff:* Applies mutate global state from the canonical tree only; mains in worktrees must switch to apply.
- **Option B**: Reverse. *Tradeoff:* Applies work anywhere; a worktree apply can mutate global state from a non-canonical tree.

**Recommendation: A.** The box calls it defensible: an apply mutates global state; ordinary worktree work is unaffected.

## 8. SEQ-B1: keep the joint promotion gate, or move the rate axis to advisory (human-amendment-only)?

- Context: `handoffs/active/autopilot-sequential-allocation.md:184@7eb7a4a3c911` (manifest `handoffs/active/autopilot-sequential-allocation.md:184@3ac825873dfb`, id `44ae1f547a78`)
- Gated worker box(es): `SEQ-B1` (handoffs/active/autopilot-sequential-allocation.md:184)

- **Option A (recommended)**: Keep the joint gate. *Tradeoff:* A candidate that buys quality with throughput can never be promoted.
- **Option B**: Move the rate axis to advisory. *Tradeoff:* Quality-for-throughput trades can promote; rate regressions pass with a warning.

**Recommendation: A.** The box notes the joint gate may be exactly what is wanted; changing it is an era-level trust change.

## 9. Axis 1: goodput vs raw rate.

- Context: `handoffs/active/objective-task-rate-goodput.md:106@7eb7a4a3c911` (manifest `handoffs/active/objective-task-rate-goodput.md:106@3ac825873dfb`, id `4ca6b654a912`)
- Gated worker box(es): `handoffs/active/objective-task-rate-goodput.md:106`

- **Option A**: (a) Quality-scaled goodput replaces raw rate. *Tradeoff:* Era boundary; redefines a banked axis.
- **Option B (recommended)**: (b) Raw rate stays + a quality floor gates admission, plus fix `or 0.0` absent-vs-zero. *Tradeoff:* Closes the dominance hole without redefining the axis.
- **Option C**: (c) Status quo. *Tradeoff:* ~1 row in 6 enters at zero quality.

**Recommendation: B.** The box recommends (b) plus the data fix, which is needed under any option.

## 10. W6d: weight the mix by production traffic instead of equal thirds?

- Context: `handoffs/active/objective-task-rate-goodput.md:210@7eb7a4a3c911` (manifest `handoffs/active/objective-task-rate-goodput.md:210@3ac825873dfb`, id `e7dd93b2a9d6`)
- Gated worker box(es): `handoffs/active/objective-task-rate-goodput.md:210`

- **Option A (recommended)**: Production-traffic-weighted. *Tradeoff:* qph tracks real throughput; needs the production task-tier distribution first.
- **Option B**: Keep equal thirds. *Tradeoff:* Clean default; diverges from production.

**Recommendation: A.** Cheapest to change while a frontier restarts; the distribution must be established first.

## 11. P0.1: run or pause the autopilot candidate species?

- Context: `handoffs/active/orchestration-robustness-audit-2026-07-11.md:155@7eb7a4a3c911` (manifest `handoffs/active/orchestration-robustness-audit-2026-07-11.md:155@3ac825873dfb`, id `54d3037a0833`)
- Gated worker box(es): `handoffs/active/orchestration-robustness-audit-2026-07-11.md:155`

- **Option A (recommended)**: Run. *Tradeoff:* Species keep producing candidates.
- **Option B**: Pause. *Tradeoff:* Stops the species; no candidates from them.

**Recommendation: A.** The box gives no evidence for a pause; run keeps the default behaviour.

## 12. T2.2: should the reasoner's GPU residency raise the composite route's `cost_tier`?

- Context: `handoffs/active/scaffold-autopilot-cost-lever-deployment.md:117@7eb7a4a3c911` (manifest `handoffs/active/scaffold-autopilot-cost-lever-deployment.md:117@3ac825873dfb`, id `f1207a80a7bd`)
- Gated worker box(es): `handoffs/active/scaffold-autopilot-cost-lever-deployment.md:117`

- **Option A (recommended)**: Raise cost_tier for the composite route. *Tradeoff:* Scaffold is not scored as free; real capacity cost counted.
- **Option B**: Keep the current cost_tier. *Tradeoff:* Scaffold looks free on the Pareto cost axis.

**Recommendation: A.** The box states the residency is a real capacity cost.

## 13. T0.1 approval: register the `scaffold_then_nothink` lever as a gated placeholder (T4.2)?

- Context: `handoffs/active/scaffold-autopilot-cost-lever-deployment.md:125@7eb7a4a3c911` (manifest `handoffs/active/scaffold-autopilot-cost-lever-deployment.md:125@3ac825873dfb`, id `491fd493eb48`)
- Gated worker box(es): `handoffs/active/scaffold-autopilot-cost-lever-deployment.md:125`

- **Option A (recommended)**: Approve; register as placeholder with kill_condition. *Tradeoff:* Lever exists in the registry, gated until §8 passes.
- **Option B**: Do not register. *Tradeoff:* No lever.

**Recommendation: A.** The row stays placeholder/gated until the measurement gate.

## Excluded (not delivered)

- `handoffs/active/objective-task-rate-goodput.md:134`: **decided**. Operator decision D2 2026-09-16 recorded in the box (option (c) with (b) interim).
