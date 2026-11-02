# Decision package: deepseek-v41-flash-evaluation

Destination handoff `handoffs/active/deepseek-v41-flash-evaluation.md` · not in the 1a list; after the 1a folds, manifest fold 11 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 5 · excluded: 2. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. Delete `DeepSeek-V4.1-Flash-DSpark.gguf` (10 GB, no references) and record its graveyard row?

- Context: `handoffs/active/deepseek-v41-flash-evaluation.md:1525@7eb7a4a3c911` (manifest `handoffs/active/deepseek-v41-flash-evaluation.md:1525@3ac825873dfb`, id `536849e3996d`)
- Gated worker box(es): `DS41-W7.2` (handoffs/active/deepseek-v41-flash-evaluation.md:1525)

- **Option A (recommended)**: Approve the delete. *Tradeoff:* Frees 10 GB; irreversible.
- **Option B**: Keep. *Tradeoff:* No risk; disk stays used.

**Recommendation: A.** DS41-W6.2 was cancelled and nothing references it.

## 2. DS41-B3.1: does the -0.0 Engram gate case matter?

- Context: `handoffs/active/deepseek-v41-flash-evaluation.md:1744@7eb7a4a3c911` (manifest `handoffs/active/deepseek-v41-flash-evaluation.md:1744@3ac825873dfb`, id `3dfb940c9a08`)
- Gated worker box(es): `DS41-B3.1` (handoffs/active/deepseek-v41-flash-evaluation.md:1744)

- **Option A (recommended)**: Accept +1 at -0.0. *Tradeoff:* Close now; differs from torch copysign at -0.0.
- **Option B**: Match copysign exactly. *Tradeoff:* Bit-faithful; one more graph change.

**Recommendation: A.** Tests are exact at +0.0 and bit-identical elsewhere.

## 3. DS41-T3.3b: put the authored template into the DS41 launch recipe?

- Context: `handoffs/active/deepseek-v41-flash-evaluation.md:1752@7eb7a4a3c911` (manifest `handoffs/active/deepseek-v41-flash-evaluation.md:1752@3ac825873dfb`, id `ca9a66b85dec`)
- Gated worker box(es): `DS41-T3.3b` (handoffs/active/deepseek-v41-flash-evaluation.md:1752)

- **Option A (recommended)**: Adopt after parity results. *Tradeoff:* 14/14 parity; one known divergence.
- **Option B**: Keep stock template. *Tradeoff:* No change.

**Recommendation: A.** Parity is shown and the divergence is documented.

## 4. DS41-C34: delete the partial build dir?

- Context: `handoffs/active/deepseek-v41-flash-evaluation.md:360@7eb7a4a3c911` (manifest `handoffs/active/deepseek-v41-flash-evaluation.md:360@3ac825873dfb`, id `62df0de65687`)
- Gated worker box(es): `DS41-C34` (handoffs/active/deepseek-v41-flash-evaluation.md:360)

- **Option A (recommended)**: Delete. *Tradeoff:* Frees disk.
- **Option B**: Keep. *Tradeoff:* No risk.

**Recommendation: A.** Run 10 uses build-cpu.

## 5. DS41-C92: floor selection prefers the contaminated COR exact floor (4.533%) over the cleaner carried lineage floor; quarantine the record or re-order selection?

- Context: `handoffs/active/deepseek-v41-flash-evaluation.md:913@7eb7a4a3c911` (manifest `handoffs/active/deepseek-v41-flash-evaluation.md:913@3ac825873dfb`, id `9d93f21e4e84`)
- Gated worker box(es): `DS41-C92` (handoffs/active/deepseek-v41-flash-evaluation.md:913)

- **Option A**: Quarantine the 4.533% record. *Tradeoff:* One-record fix; leaves the selection rule able to prefer the next contaminated floor.
- **Option B (recommended)**: Re-order selection (carried lineage floor first after an anchor advance). *Tradeoff:* Fixes the class of error; changes which floor every later verdict reads.

**Recommendation: B.** The defect is the selection order, and it recurs after each anchor advance; quarantining one record treats one instance.

## Excluded (not delivered)

- `DS41-W5d` (handoffs/active/deepseek-v41-flash-evaluation.md:1431): **decided**. Operator choice "1017-only + microbench" 2026-10-23 recorded in the box.
- `DS41-C61` (handoffs/active/deepseek-v41-flash-evaluation.md:536): **not-a-choice**. Sampling task; any change goes through stack-change.
