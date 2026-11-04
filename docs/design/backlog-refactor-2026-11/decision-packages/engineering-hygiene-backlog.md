# Decision package: engineering-hygiene-backlog

Destination handoff `handoffs/active/engineering-hygiene-backlog.md` · fold 3 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 9 · excluded: 2. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. Backup W2: choose the off-host target for `backup_critical.sh`.

- Context: `handoffs/active/frontier-f4-continuity-backup.md:21@7eb7a4a3c911` (manifest `handoffs/active/frontier-f4-continuity-backup.md:21@3ac825873dfb`, id `b5445199e975`)
- Gated worker box(es): `handoffs/active/frontier-f4-continuity-backup.md:21`

- **Option A (recommended)**: Configure an off-host target. *Tradeoff:* Real backup in a different failure domain.
- **Option B**: No backup. *Tradeoff:* Same-array data has no backup.

**Recommendation: A.** Tooling landed; only the target is missing.

## 2. LOOP-46: sign off the D9 hook edit (judge the commit it guards, not the shared clone)?

- Context: `handoffs/active/non-inference-backlog.md:1103@7eb7a4a3c911` (manifest `handoffs/active/non-inference-backlog.md:1103@3ac825873dfb`, id `a6ab3df6978d`)
- Gated worker box(es): `LOOP-46` (handoffs/active/non-inference-backlog.md:1103)

- **Option A (recommended)**: Sign off. *Tradeoff:* Stops false refusals on worktree commits.
- **Option B**: Decline. *Tradeoff:* False refusals continue.

**Recommendation: A.** The defect refused a valid worktree commit.

## 3. LOOP-50: sign off wiring the tick/deletion science gate as blocking in pre-commit.extras?

- Context: `handoffs/active/non-inference-backlog.md:1110@7eb7a4a3c911` (manifest `handoffs/active/non-inference-backlog.md:1110@3ac825873dfb`, id `e00730df34ba`)
- Gated worker box(es): `LOOP-50` (handoffs/active/non-inference-backlog.md:1110)

- **Option A (recommended)**: Sign off (blocking). *Tradeoff:* Bad ticks refused at commit.
- **Option B**: Advisory only. *Tradeoff:* Reported, not refused.

**Recommendation: A.** Spec and backtest exist.

## 4. LOOP-53: implement the `EPYC_ALLOW_SCRATCH_DELETE` override (logged) or remove it from the message?

- Context: `handoffs/active/non-inference-backlog.md:1113@7eb7a4a3c911` (manifest `handoffs/active/non-inference-backlog.md:1113@3ac825873dfb`, id `ff748d37fa1b`)
- Gated worker box(es): `LOOP-53` (handoffs/active/non-inference-backlog.md:1113)

- **Option A (recommended)**: Implement the logged override. *Tradeoff:* Operator-approved installers run unattended.
- **Option B**: Remove it from the message. *Tradeoff:* No override path.

**Recommendation: A.** It blocked two operator-approved tools.

## 5. NIB2-94: rotate the HF token that sat in a curl argv (readable in `ps`) for ~68 minutes on 2026-10-20?

- Context: `handoffs/active/non-inference-backlog.md:327@7eb7a4a3c911` (manifest `handoffs/active/non-inference-backlog.md:327@3ac825873dfb`, id `c25e11233421`)
- Gated worker box(es): `NIB2-94` (handoffs/active/non-inference-backlog.md:327)

- **Option A (recommended)**: Rotate the token. *Tradeoff:* Closes the exposure for certain; every consumer must pick up the new token file.
- **Option B**: Decline rotation (record the reason). *Tradeoff:* No work; relies on nobody having read `ps` during the window on a shared host.

**Recommendation: A.** The host is shared and the exposure was confirmed; rotation is cheap compared with an unbounded credential.

## 6. NIB2-97 (b): D9-ack the `scripts/hooks/earlyoom_audit.sh` /proc snapshot (hook-file edit)?

- Context: `handoffs/active/non-inference-backlog.md:332@7eb7a4a3c911` (manifest `handoffs/active/non-inference-backlog.md:332@3ac825873dfb`, id `0308fb5f4d6a`)
- Gated worker box(es): `NIB2-97` (handoffs/active/non-inference-backlog.md:332)

- **Option A (recommended)**: Acknowledge. *Tradeoff:* The next earlyoom kill leaves a memory snapshot; one more hook to maintain.
- **Option B**: Decline. *Tradeoff:* Only the 30 s sampler (a) remains; the trigger instant is not captured.

**Recommendation: A.** INC-20261021 left no sample at the trigger; (a) samples every 30 s and can miss the instant.

## 7. NIB2-89: D9-ack landing the H-4 self-restart generalisation under scripts/coordination/** (no runtime effect while bus_supervisor stays DOWN)?

- Context: `handoffs/active/non-inference-backlog.md:446@7eb7a4a3c911` (manifest `handoffs/active/non-inference-backlog.md:446@3ac825873dfb`, id `c726738c619e`)
- Gated worker box(es): `NIB2-89` (handoffs/active/non-inference-backlog.md:446)

- **Option A (recommended)**: Acknowledge and land dormant. *Tradeoff:* Code is ready if supervision is ever re-enabled; review cost only.
- **Option B**: Decline. *Tradeoff:* Nothing lands; the NIB2-81 "Remaining" line stays open.

**Recommendation: A.** It has no runtime effect under the 2026-09-23 ruling; the host-cron half stays with OP-9/FW-3.

## 8. Operator review of `refactor/containment-scanner` (safety boundary for INC-20260823): merge or reject?

- Context: `handoffs/active/refactoring-multirepo-2026-10.md:197@7eb7a4a3c911` (manifest `handoffs/active/refactoring-multirepo-2026-10.md:197@3ac825873dfb`, id `8ef5527bb58e`)
- Gated worker box(es): `handoffs/active/refactoring-multirepo-2026-10.md:197`

- **Option A (recommended)**: Merge after reading CONTAINMENT-SCANNER-CHANGES-FOR-REVIEW.md. *Tradeoff:* The boundary change lands with an operator review on record.
- **Option B**: Reject. *Tradeoff:* The current scanner stays; the review notes stay on the branch.

**Recommendation: A.** A safety boundary needs the operator's review either way; the notes are prepared on the branch.

## 9. C5-05: delete the `campaign.py` CLI cluster (~20k LOC), a fourth plane outside the three approved?

- Context: `handoffs/active/refactoring-multirepo-2026-10.md:271@7eb7a4a3c911` (manifest `handoffs/active/refactoring-multirepo-2026-10.md:271@3ac825873dfb`, id `71f2858d4bb0`)
- Gated worker box(es): `C5-05` (handoffs/active/refactoring-multirepo-2026-10.md:271)

- **Option A (recommended)**: Approve the deletion. *Tradeoff:* Removes ~20k LOC and a fourth plane; any remaining caller must move first.
- **Option B**: Approve it as a fourth plane. *Tradeoff:* Keeps the code; the plane count grows.
- **Option C**: Keep it as-is, undecided. *Tradeoff:* No work; the refactor plan stays blocked here.

**Recommendation: A.** The refactor approved three planes and this one is outside them; deletion follows that approval.

## Excluded (not delivered)

- `LOOP-26` (handoffs/active/non-inference-backlog.md:1080): **decided**. The no-blocking-question rule is an issued operator directive; the task is a write-up.
- `LINT-PIPEFAIL-EARLY-EXIT` (handoffs/active/non-inference-backlog.md:927): **decided**. Operator D9 ack 2026-10-23 option "hooks + coordination only" recorded in the box.
