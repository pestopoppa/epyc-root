# Decision package: kernel-champion-and-promotion

Destination handoff `handoffs/active/kernel-champion-and-promotion.md` · fold 10 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 3 · excluded: 4. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. Fast-forward the shared orchestrator checkout to include device-busy fix `6ce26fc9` (AKX-ALL-15 G1 executor)?

- Context: `handoffs/active/autokernel-all-devices-all-dimensions.md:347@7eb7a4a3c911` (manifest `handoffs/active/autokernel-all-devices-all-dimensions.md:347@3ac825873dfb`, id `4179c24feea9`)
- Gated worker box(es): `AKX-ALL-15` (handoffs/active/autokernel-all-devices-all-dimensions.md:347)

- **Option A (recommended)**: Approve the fast-forward now. *Tradeoff:* G1 manual-window cycle gets the device-busy guard; touches a shared clone other sessions run from, so it must happen at a quiet boundary.
- **Option B**: Hold the checkout at `4b871cc5`. *Tradeoff:* No shared-clone risk; the G1 cycle keeps running without the device-busy guard and AKX-ALL-15 cannot close.

**Recommendation: A.** The fix is reviewed and small; the third-review ACK in the box is what closes AKX-ALL-15, and that needs the fixed checkout.

## 2. May `build_store.sh` adopt path-independent builds (prefix maps + pinned UI dist) in the fold recipe (CH-28d)?

- Context: `handoffs/active/autokernel-champion-aggregate.md:223@7eb7a4a3c911` (manifest `handoffs/active/autokernel-champion-aggregate.md:223@3ac825873dfb`, id `af3725484c61`)
- Gated worker box(es): `CH-28d` (handoffs/active/autokernel-champion-aggregate.md:223)

- **Option A (recommended)**: Approve editing `build_store.sh` after the double-build `mode=exact` check. *Tradeoff:* Makes hip comparison exact and removes EXPLAINED-UI; one more recipe change on the promotion path.
- **Option B**: Keep the change in the side file `c3-fold-prep/build_store.sh` only. *Tradeoff:* Zero risk to the CH-28 script; every fold keeps needing EXPLAINED-UI and non-exact hip comparisons.

**Recommendation: A.** The change is already implemented in a side file and is verifiable by building twice; exact comparison removes a recurring manual explanation.

## 3. Ratify the forward-port rule (V6R-4b / OP-58) into CLAUDE.md § Experimental Kernel Workflow?

- Context: `handoffs/active/autokernel-champion-aggregate.md:884@7eb7a4a3c911` (manifest `handoffs/active/autokernel-champion-aggregate.md:884@3ac825873dfb`, id `25cd905212ac`)
- Gated worker box(es): `V6R-4b` (handoffs/active/autokernel-champion-aggregate.md:884)

- **Option A (recommended)**: Ratify the proposed text as written. *Tradeoff:* Prevents a repeat of INC-20260925 (bundled revert lost our own repack); adds a per-feature-commit discipline to every consolidation.
- **Option B**: Ratify with edits. *Tradeoff:* Same protection with operator wording; costs one more drafting round.
- **Option C**: Decline. *Tradeoff:* No new rule; the INC-20260925 failure mode stays unguarded.

**Recommendation: A.** The text is drafted, narrow, and traces to a real incident; only the operator may edit CLAUDE.md.

## Excluded (not delivered)

- `AKX-ALL-15c` (handoffs/active/autokernel-all-devices-all-dimensions.md:382): **decided**. AKX-ALL-15c was filed as the operator decision of 2026-10-04 (first AK GPU-lane job = dequant-GEMV); remaining work is execution.
- `CH-31-DEF1` (handoffs/active/autokernel-champion-aggregate.md:266): **decided**. CH-31-DEF1 was filed by operator decision (AMENDMENT 9, 2026-10-24); the next step is engineering localisation.
- `V11-086-ORACLE-4` (handoffs/active/autokernel-champion-aggregate.md:323): **decided**. OPERATOR DECISION 2026-10-23 "A3 as accepted: REG passes" recorded in the box; integrity installed (3c4ca599).
- `FD-OFF-PROD` (handoffs/active/cpu-fused-decoder-blocks.md:70): **decided**. Operator direction 2026-10-24 (3c4ca599): fix in the champion, not production; resolved in champion fold C5 (fused decode default-OFF).
