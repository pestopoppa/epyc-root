# Decision package: kv-cache-program

Destination handoff `handoffs/active/kv-cache-program.md` · not in the 1a list; after the 1a folds, manifest fold 2 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 4 · excluded: 3. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. Should Layer 1 prefill placement get a length threshold once R_cpu(L)/R_gpu(L,ub) are filled from PF1?

- Context: `handoffs/active/heterogeneous-slot-fabric-residency.md:172@7eb7a4a3c911` (manifest `handoffs/active/heterogeneous-slot-fabric-residency.md:172@3ac825873dfb`, id `ddf733cf9e17`)
- Gated worker box(es): `handoffs/active/heterogeneous-slot-fabric-residency.md:172`

- **Option A (recommended)**: Add a length threshold derived from the PF1 crossover. *Tradeoff:* Routes long prefills to the GPU where it wins; one more placement knob to maintain.
- **Option B**: No threshold (status quo placement). *Tradeoff:* Simpler; leaves any measured long-prefill gain unused.

**Recommendation: A.** Decide only after PF1 fills the curves; if the curves cross, a threshold is the direct use of that data. Design-only until then.

## 2. Give the go for HSF-5.P-NEXT GPU attribution (P6) per the REVIVAL CHECKLIST?

- Context: `handoffs/active/heterogeneous-slot-fabric-residency.md:346@7eb7a4a3c911` (manifest `handoffs/active/heterogeneous-slot-fabric-residency.md:346@3ac825873dfb`, id `e6a9fe8a6239`)
- Gated worker box(es): `HSF-5.P-NEXT` (handoffs/active/heterogeneous-slot-fabric-residency.md:346)

- **Option A**: Go now. *Tradeoff:* Produces the GPU attribution the fabric program lacks; needs a GPU window.
- **Option B (recommended)**: Keep deferred. *Tradeoff:* No GPU time used; P6 attribution stays missing.

**Recommendation: B.** The box gives no consumer waiting on P6 today; keep deferred until a fabric decision needs it, then revive via the checklist.

## 3. Set the exact scope of the V11-FA-4b model-level rocWMMA ON/OFF quality A/B (parent stays open "owner decides exact task scope").

- Context: `handoffs/active/kv-unified-stack-rollout.md:1289@7eb7a4a3c911` (manifest `handoffs/active/kv-unified-stack-rollout.md:1289@3ac825873dfb`, id `dd5fec0fbbfb`)
- Gated worker box(es): `V11-FA-4b` (handoffs/active/kv-unified-stack-rollout.md:1289), `V11-FA-4` (handoffs/active/kv-unified-stack-rollout.md:1271)

- **Option A**: Full scope as written (>=100 greedy prompts, both KV variants, drafter OFF and ON, >=200 scored items). *Tradeoff:* Decision-grade for every serving shape; longest GPU time.
- **Option B (recommended)**: Production shape only (q8_0 KV, drafter as served) plus the 200 scored items. *Tradeoff:* Covers what is served at about half the GPU time; f16/drafter-OFF variants unmeasured.
- **Option C**: Close on the 2026-10-28 paired result (delta CI within +/-2 pp, 0 non-finite). *Tradeoff:* No further GPU time; relies on a result whose residency proofs were partly unreconstructable.

**Recommendation: B.** The decision serves the v11 carry/drop of rocWMMA FA for production; the production shape answers that at the lowest cost.

## 4. KVU-12.4: run one more ABA with a tighter anchor floor, or accept NO_DIFFERENCE?

- Context: `handoffs/active/kv-unified-stack-rollout.md:1518@7eb7a4a3c911` (manifest `handoffs/active/kv-unified-stack-rollout.md:1518@3ac825873dfb`, id `aafe475a984b`)
- Gated worker box(es): `KVU-12.4` (handoffs/active/kv-unified-stack-rollout.md:1518), `KVU-12` (handoffs/active/kv-unified-stack-rollout.md:1504)

- **Option A (recommended)**: Accept NO_DIFFERENCE and record the ~23% gap as inside the 12% floor. *Tradeoff:* No compute; the unified-decode gap stays unresolved.
- **Option B**: Run ONE ABA at np4 L64k with anchor floor < ~5% (exclusive window ~2.2 h). *Tradeoff:* Resolves the gap; needs the anchor-variance investigation first and a whole exclusive window.

**Recommendation: A.** The box itself calls accepting right-sized unless the gap matters to a decision, and none is named.

## Excluded (not delivered)

- `V11-FA-4` (handoffs/active/kv-unified-stack-rollout.md:1271): **merged** into choice for `V11-FA-4b`. Same open scope question as V11-FA-4b (owner decides exact task scope).
- `KVU-12` (handoffs/active/kv-unified-stack-rollout.md:1504): **merged** into choice for `KVU-12.4`. KVU-12 parent; its open choice is the KVU-12.4 re-run decision.
- `KVU-12.5` (handoffs/active/kv-unified-stack-rollout.md:1521): **decided**. Operator decision 2026-10-25 via decision tool: np8 A/B pair only; parts (b) and (c) declined.
