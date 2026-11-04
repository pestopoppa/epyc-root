# Decision package: vidya-belief-substrate-program

Destination handoff `handoffs/active/vidya-belief-substrate-program.md` · not in the 1a list; after the 1a folds, manifest fold 4 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 4 · excluded: 3. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. VB-SL2-STEPS: give the `target_sample_steps_est` block its own `belief_measurements` rows?

- Context: `handoffs/active/vidya-belief-substrate-program.md:1432@7eb7a4a3c911` (manifest `handoffs/active/vidya-belief-substrate-program.md:1432@3ac825873dfb`, id `3cd4e57b32bc`)
- Gated worker box(es): `VB-SL2-STEPS` (handoffs/active/vidya-belief-substrate-program.md:1432)

- **Option A (recommended)**: Project it, labelled with its estimator string. *Tradeoff:* The estimate becomes queryable; risk of being read as the server counter, mitigated by the estimator string.
- **Option B**: Keep it inside `serving_beliefs` only. *Tradeoff:* No new rows; the data stays bound by native_sha256 but unprojected.

**Recommendation: A.** Write-side wiring is cheap and permanent (Belief Kernel rule); the estimator string prevents conflation.

## 2. Go to push `f8/vidya-correction-fix` (`2c0c7334b`: adapter fix + 121 intake index blocks)?

- Context: `handoffs/active/vidya-belief-substrate-program.md:3629@7eb7a4a3c911` (manifest `handoffs/active/vidya-belief-substrate-program.md:3629@3ac825873dfb`, id `42799be0257c`)
- Gated worker box(es): `VB-REFOCUS-PUSH-CORRECTION-FIX` (handoffs/active/vidya-belief-substrate-program.md:3629)

- **Option A (recommended)**: Go, after cite-check on the merged tree and pending-corrections = 0. *Tradeoff:* Lands the correction fix; touches 121 index blocks at once.
- **Option B**: Hold. *Tradeoff:* No change; the correction defect stays on main.

**Recommendation: A.** The box names the checks that make the push safe; it is blocked only on this go.

## 3. VB-LOOP-TEXT: should device-only claims count as usable evidence for a model target?

- Context: `handoffs/active/vidya-belief-substrate-program.md:3633@7eb7a4a3c911` (manifest `handoffs/active/vidya-belief-substrate-program.md:3633@3ac825873dfb`, id `da174e921f35`)
- Gated worker box(es): `VB-LOOP-TEXT` (handoffs/active/vidya-belief-substrate-program.md:3633)

- **Option A (recommended)**: Show them as a separate "device-scope" group. *Tradeoff:* Planner sees what the claim is about; small render change.
- **Option B**: Count them as usable model evidence. *Tradeoff:* No change; three different models received the same 12 device claims.

**Recommendation: A.** The smoke showed the same claims for three models; a separate group is honest without a new grading rule.

## 4. When to fast-forward the shared orchestrator clone before the autopilot spin-up (VB-AP-SPINUP-ORCH-CLONE)?

- Context: `handoffs/active/vidya-belief-substrate-program.md:3637@7eb7a4a3c911` (manifest `handoffs/active/vidya-belief-substrate-program.md:3637@3ac825873dfb`, id `ca4f3d06e5ac`)
- Gated worker box(es): `VB-AP-SPINUP-ORCH-CLONE` (handoffs/active/vidya-belief-substrate-program.md:3637)

- **Option A (recommended)**: In the same step as the next autopilot start. *Tradeoff:* Start runs reader-lane code; must check for other sessions' uncommitted edits first.
- **Option B**: Now, ahead of the start. *Tradeoff:* Earlier; risks other sessions' edits and is what the box forbids.

**Recommendation: A.** The box itself fixes the timing; the operator only needs to name the start.

## Excluded (not delivered)

- `P1-AC9-TARGET-CROWDING` (handoffs/active/vidya-belief-substrate-program.md:3690): **decided**. Operator decided (B) amend AC9 on 2026-10-24; remaining is implementation.
- `VB-TICK-CONTRACT` (handoffs/active/vidya-belief-substrate-program.md:3894): **decided**. The tick contract is already in CLAUDE.md (Belief Kernel section) and SESSION_LIFECYCLE.md Two axioms.
- `KT-2-FU` (handoffs/active/vidya-belief-substrate-program.md:4261): **decided**. Decided by the standing CLAUDE.md Belief Kernel rule: a source producing findings gets a source-table row.
