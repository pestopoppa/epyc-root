# Pipelines & Integration — Active Backlog

**Purpose**: dispatch. Ingestion, document/RAG pipelines, knowledge base plumbing.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/pipeline-integration-index-history-through-2026-08-10.md`](../archived/pipeline-integration-index-history-through-2026-08-10.md).

**IDs are stable.** `PIP-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| PIP-04 | internal kb rag | [knowledge-pipelines.md](knowledge-pipelines.md) | Fix PIP02-R36-DEVNULL-FENCE, republish R36; file ODL-013/G14/OCR r2 rows; operator ratifies P-DOCPARSE-1 annex | — |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
