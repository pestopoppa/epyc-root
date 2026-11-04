# Decision package: numa-placement-and-contention

Destination handoff `handoffs/active/numa-placement-and-contention.md` · fold 17 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 3 · excluded: 1. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. T12: re-decide `-c` provisioning (production 32768 = 12.5% of the trained window; architect_general 8192/request via slots: 2).

- Context: `handoffs/active/numa-placement-defect-20260730.md:1023@7eb7a4a3c911` (manifest `handoffs/active/numa-placement-defect-20260730.md:1023@3ac825873dfb`, id `462f9dd9b9ab`)
- Gated worker box(es): `handoffs/active/numa-placement-defect-20260730.md:1023`

- **Option A**: (A) Max-provision fleet-wide + a compaction/eviction policy above the server. *Tradeoff:* Full window everywhere; the policy machinery does not exist and the worst-case KV sum is uncomputed.
- **Option B (recommended)**: (B) Staged: raise `-c` only where the lineup's full-window KV sum fits RAM with stated margin (package recommendation). *Tradeoff:* Gains window where safe; needs the mechanical KV-sum computation first.
- **Option C**: (C) Keep 32768. *Tradeoff:* No risk; the rationing rests on a cost premise the measurement removed.

**Recommendation: B.** The package shows the cost moves from launch to load, so a margin-checked staged raise is the safe use of the measurement.

## 2. RC-6a: ratify the `MEASUREMENT.md` P-REV-1 PR (copy-paste-ready blocks) that gates the decision-grade reviewer tier?

- Context: `handoffs/active/reboot-gated-inventory-and-staging.md:363@7eb7a4a3c911` (manifest `handoffs/active/reboot-gated-inventory-and-staging.md:363@3ac825873dfb`, id `615ec0285b76`)
- Gated worker box(es): `handoffs/active/reboot-gated-inventory-and-staging.md:363`

- **Option A (recommended)**: Ratify after the two kappa/estimand amendment candidates land. *Tradeoff:* Unblocks the whole decision-grade reviewer tier; trust-boundary edit.
- **Option B**: Ratify as-is now. *Tradeoff:* Faster; skips the amendments the row itself says land first.
- **Option C**: Decline. *Tradeoff:* Reviewer tier stays observation-grade.

**Recommendation: A.** The row orders the amendments first; the LB-6b threshold half of S-18 is delivered with LB-6b.

## 3. WP-6 / WP-7 full ratification of within-role placement (inference-gated).

- Context: `handoffs/active/within-role-placement-state-machine.md:377@7eb7a4a3c911` (manifest `handoffs/active/within-role-placement-state-machine.md:377@3ac825873dfb`, id `09f1cb2d6b97`)
- Gated worker box(es): `WP-6` (handoffs/active/within-role-placement-state-machine.md:377)

- **Option A (recommended)**: Approve the measurement (>=8-sample vision_escalation re-bench) and ratify on its result. *Tradeoff:* Closes the series; needs a bench on the current single worker_vision instance.
- **Option B**: Hold ratification. *Tradeoff:* No compute; WP-6/WP-7 remain partially ratified (per-role policy already ratified).

**Recommendation: A.** The only open gate in the checklist is the higher-sample re-bench; ratification follows its result.

## Excluded (not delivered)

- `handoffs/active/batched-decode-measurement.md:767`: **decided**. Token 2 Block A signed and applied 2026-08-11.
