# Decision package: memory-program

Destination handoff `handoffs/active/memory-program.md` · fold 24 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 6 · excluded: 1. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. M-12f: exclude single-item questions from the Chronological Order score before CAS is a headline?

- Context: `handoffs/active/episodic-memory-integrity.md:567@7eb7a4a3c911` (manifest `handoffs/active/episodic-memory-integrity.md:567@3ac825873dfb`, id `e87399d100cb`)
- Gated worker box(es): `handoffs/active/episodic-memory-integrity.md:567`

- **Option A (recommended)**: Exclude questions with <2 ground-truth items. *Tradeoff:* CAS measures ordering where defined.
- **Option B**: Keep them (score 0.0). *Tradeoff:* Two thirds of the tau leg stays structurally 0.0.

**Recommendation: A.** 30 of 45 questions have undefined ordering.

## 2. CFI-2: reach 256-token blocks on the episodic path by widening memory-k or adding a stable memory-library prefix?

- Context: `handoffs/active/episodic-memory-integrity.md:730@7eb7a4a3c911` (manifest `handoffs/active/episodic-memory-integrity.md:730@3ac825873dfb`, id `cf9eb12d15db`)
- Gated worker box(es): `CFI-2` (handoffs/active/episodic-memory-integrity.md:730)

- **Option A**: Widen k. *Tradeoff:* More memories per block; higher token and latency cost per request.
- **Option B (recommended)**: Stable memory-library prefix. *Tradeoff:* Meets the block minimum with a cacheable prefix; prefix must be maintained.

**Recommendation: B.** The block minimum exists for caching; a stable prefix serves it without growing per-request retrieval.

## 3. M-27d.1: should eval/external rows be in the default recall pool or behind a `context.source` filter?

- Context: `handoffs/active/episodic-memory-integrity.md:740@7eb7a4a3c911` (manifest `handoffs/active/episodic-memory-integrity.md:740@3ac825873dfb`, id `4cceb142a76e`)
- Gated worker box(es): `handoffs/active/episodic-memory-integrity.md:740`

- **Option A (recommended)**: Behind a filter, via a flagged A/B. *Tradeoff:* Separates interactive from autopilot rows.
- **Option B**: Keep in the default pool. *Tradeoff:* Non-seed rows keep appearing.

**Recommendation: A.** The box requires a flagged A/B for a retrieval change.

## 4. D-e1: raise the 12/8 REPL memory defaults?

- Context: `handoffs/active/repl-session-memory-maturity.md:177@7eb7a4a3c911` (manifest `handoffs/active/repl-session-memory-maturity.md:177@3ac825873dfb`, id `ac59e7fac97f`)
- Gated worker box(es): `handoffs/active/repl-session-memory-maturity.md:177`

- **Option A (recommended)**: Decide inside D-c1's real-workload measurement. *Tradeoff:* One measurement answers both.
- **Option B**: Raise now. *Tradeoff:* Synthetic basis.

**Recommendation: A.** The box folds it into D-c1.

## 5. D-f2: fence findings, documents and tags too?

- Context: `handoffs/active/repl-session-memory-maturity.md:356@7eb7a4a3c911` (manifest `handoffs/active/repl-session-memory-maturity.md:356@3ac825873dfb`, id `2e9b41cb0a9c`)
- Gated worker box(es): `handoffs/active/repl-session-memory-maturity.md:356`

- **Option A (recommended)**: Fence them. *Tradeoff:* Consistent concurrency.
- **Option B**: Record why appends are safe. *Tradeoff:* No code.

**Recommendation: A.** Append-style writes need either a fence or a proof.

## 6. Add an importance-scored background consolidation pass to AutoMem?

- Context: `handoffs/active/unified-trace-memory-service.md:323@7eb7a4a3c911` (manifest `handoffs/active/unified-trace-memory-service.md:323@3ac825873dfb`, id `a1ad61d866f5`)
- Gated worker box(es): `handoffs/active/unified-trace-memory-service.md:323`

- **Option A (recommended)**: Add as optional extension. *Tradeoff:* Inference-free compaction.
- **Option B**: Skip. *Tradeoff:* No change.

**Recommendation: A.** It is inference-free and mirrors an existing loop.

## Excluded (not delivered)

- `DHM-4` (handoffs/active/dev-harness-trace-mining.md:37): **decided**. Operator decision 2026-10-23: 30-item pilot first; the remaining step is operator labelling, not a choice.
