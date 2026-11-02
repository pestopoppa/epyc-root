# Decision package: reviewer-control-plane

Destination handoff `handoffs/active/reviewer-control-plane.md` · fold 25 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 4 · excluded: 1. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. GC-4b: DeepSeek-V4.1-Flash residency policy (Engram tables resident vs mmap-streamed).

- Context: `handoffs/active/glm52-reviewer-capability-gates.md:218@7eb7a4a3c911` (manifest `handoffs/active/glm52-reviewer-capability-gates.md:218@3ac825873dfb`, id `d10bb01c2ee7`)
- Gated worker box(es): `GC-4b` (handoffs/active/glm52-reviewer-capability-gates.md:218)

- **Option A (recommended)**: Decide after the port loads and Engram access is measured. *Tradeoff:* Policy on data.
- **Option B**: Decide now (resident). *Tradeoff:* ~483 GiB resident.

**Recommendation: A.** The box says it only matters once measured.

## 2. GC-external-1a: declare the tie/abstention estimand and report its rate?

- Context: `handoffs/active/reviewer-calibration-accounting.md:230@7eb7a4a3c911` (manifest `handoffs/active/reviewer-calibration-accounting.md:230@3ac825873dfb`, id `ad1d5cad4c94`)
- Gated worker box(es): `handoffs/active/reviewer-calibration-accounting.md:230`

- **Option A (recommended)**: Declare and report. *Tradeoff:* Honest estimand.
- **Option B**: Keep skipping ties. *Tradeoff:* Silent cleaning.

**Recommendation: A.** Skipping ties as cleaning hides a rate.

## 3. HG-4: set the escalation-precision human-audit sampling rate and cadence.

- Context: `handoffs/active/reviewer-escalation-and-human-gate-policy.md:38@7eb7a4a3c911` (manifest `handoffs/active/reviewer-escalation-and-human-gate-policy.md:38@3ac825873dfb`, id `990dfadd68a7`)
- Gated worker box(es): `HG-4` (handoffs/active/reviewer-escalation-and-human-gate-policy.md:38)

- **Option A (recommended)**: Set a rate and cadence. *Tradeoff:* Precision becomes defined.
- **Option B**: No audit. *Tradeoff:* Precision undefined.

**Recommendation: A.** The box says precision is undefined without it.

## 4. LB-6b / OP-5b: pick the budget-gate threshold (quality gain per throughput cost).

- Context: `handoffs/active/reviewer-latency-and-sampling-budget.md:27@7eb7a4a3c911` (manifest `handoffs/active/reviewer-latency-and-sampling-budget.md:27@3ac825873dfb`, id `54d928f046ce`)
- Gated worker box(es): `LB-6b` (handoffs/active/reviewer-latency-and-sampling-budget.md:27), `LB-6` (handoffs/active/reviewer-latency-and-sampling-budget.md:25)

- **Option A (recommended)**: Pick one of the drafted candidate thresholds. *Tradeoff:* Enforce-mode flips can proceed.
- **Option B**: Pick a variant. *Tradeoff:* Same, with a custom value.
- **Option C**: No threshold. *Tradeoff:* No enforce-mode flip anywhere in the series.

**Recommendation: A.** The candidates are drafted with the metric and procedure.

## Excluded (not delivered)

- `LB-6` (handoffs/active/reviewer-latency-and-sampling-budget.md:25): **merged** into choice for `LB-6b`. LB-6 parent; the open choice is LB-6b.
