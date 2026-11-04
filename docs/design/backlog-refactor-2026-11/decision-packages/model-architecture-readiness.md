# Decision package: model-architecture-readiness

Destination handoff `handoffs/active/model-architecture-readiness.md` · not in the 1a list; after the 1a folds, manifest fold 27 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 1 · excluded: 0. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. Log-linear gated DeltaNet: port on the 795M f32 research checkpoint (16K positions) or wait for a production-scale model?

- Context: `handoffs/active/log-linear-gated-deltanet-readiness.md:208@7eb7a4a3c911` (manifest `handoffs/active/log-linear-gated-deltanet-readiness.md:208@3ac825873dfb`, id `fd6c29184921`)
- Gated worker box(es): `handoffs/active/log-linear-gated-deltanet-readiness.md:208`

- **Option A**: Port now; the checkpoint validates it. *Tradeoff:* The port is ready when a deployable model appears; build cost with no deployable output yet.
- **Option B (recommended)**: Wait for a production-scale log-linear GDN. *Tradeoff:* No build now; port starts later.

**Recommendation: B.** The checkpoint is explicitly not deployable; decide once the oracle exists and a production-scale model is in sight.

