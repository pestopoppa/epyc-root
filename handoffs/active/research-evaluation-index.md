# Research & Evaluation — Active Backlog

**Purpose**: dispatch. Benchmarks, scorers, audits, research programs and their findings.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/research-evaluation-index-history-through-2026-08-10.md`](../archived/research-evaluation-index-history-through-2026-08-10.md).

**IDs are stable.** `EVL-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| EVL-02 | model evaluation queue | [model-evaluation-queue.md](model-evaluation-queue.md) | Rank the queue by lane fit; next: AMSB-C390-1 Coder390 vs 27B same-harness A/B, then the EffiBench-X adoption decision | — |
| EVL-08 | canonical judge suite revamp | [benchmark-suites.md](benchmark-suites.md) | Coordinate CJ-13 live agreement/cost acceptance with its MI210 owner; retain CJ-16's separate cascade evaluation | — |
| EVL-14 | eval tower verification | [eval-tower-program.md](eval-tower-program.md) | Retain EV-PROTO and live calibration acceptance | — |
| EVL-47 | vidya belief substrate program | [vidya-belief-substrate-program.md](vidya-belief-substrate-program.md) | Run proof r4 (ready) in a whole-host window for NONEMPTY-READ-PROOF; two-CPU-model smoke; Canary B assertion; republish R23-4 | — |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
