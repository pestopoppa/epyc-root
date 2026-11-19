# Decision package: routing-program

Destination handoff `handoffs/active/routing-program.md` · fold 26 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 4 · excluded: 0. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. fable5-02 ">=5% regret": selector self-consistency regret or counterfactual outcome regret?

- Context: `handoffs/active/decision-aware-routing.md:300@7eb7a4a3c911` (manifest `handoffs/active/decision-aware-routing.md:300@3ac825873dfb`, id `7fbcb4958021`)
- Gated worker box(es): `handoffs/active/decision-aware-routing.md:300`

- **Option A (recommended)**: Counterfactual outcome regret (~8.1-8.4 pp). *Tradeoff:* Measures what routing costs.
- **Option B**: Self-consistency regret (current, ~0 by definition). *Tradeoff:* Gate passes vacuously.

**Recommendation: A.** A definitionally-zero criterion gates nothing.

## 2. EPD-1b: backfill historical outcome labels in the live memory store (`q_value > 0.5` -> success)?

- Context: `handoffs/active/learned-routing-controller.md:212@7eb7a4a3c911` (manifest `handoffs/active/learned-routing-controller.md:212@3ac825873dfb`, id `724eb13073a5`)
- Gated worker box(es): `EPD-1b` (handoffs/active/learned-routing-controller.md:212)

- **Option A**: Run the backfill UPDATE. *Tradeoff:* EP-5 can use every row; a live-store write whose label rule is a threshold proxy.
- **Option B (recommended)**: No backfill; EP-5 filters to rows updated after 24b43990. *Tradeoff:* No live-store write; EP-5 trains on fewer rows.

**Recommendation: B.** Filtering gets EP-5 correct labels with no irreversible write; backfill can follow if EP-5 is data-starved.

## 3. Run a `--keep-enabled` bracket to actually enable live learned routing?

- Context: `handoffs/active/retrain-routing-models.md:125@7eb7a4a3c911` (manifest `handoffs/active/retrain-routing-models.md:125@3ac825873dfb`, id `c1930211713c`)
- Gated worker box(es): `handoffs/active/retrain-routing-models.md:125`

- **Option A (recommended)**: Run the bracket. *Tradeoff:* Live routing turns on with a bracketed fallback; production routing changes.
- **Option B**: Keep routing disabled. *Tradeoff:* No production change; the retrained models stay unused.

**Recommendation: A.** The bracket form is the box's own mechanism for a reversible enable.

## 4. TD-30e: sign ONE ratification package for two instrument-era rows (OC1-coherence-gate-v1, CLS1 harness1 labels) in `instrument_eras.yaml`?

- Context: `handoffs/active/typed-decision-plane.md:562@7eb7a4a3c911` (manifest `handoffs/active/typed-decision-plane.md:562@3ac825873dfb`, id `2e6c9de59695`)
- Gated worker box(es): `TD-30e` (handoffs/active/typed-decision-plane.md:562)

- **Option A (recommended)**: Sign the package. *Tradeoff:* Both instruments get era rows; their results become citable under a declared era.
- **Option B**: Sign OC1 only. *Tradeoff:* Coherence gate gets its era; CLS1 labels stay unrecorded.
- **Option C**: Decline. *Tradeoff:* Neither instrument has an era row; results stay unratified.

**Recommendation: A.** Both drafts exist and the file is a human-only trust boundary; one package is the box's design.

