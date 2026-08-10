# Pipelines & Integration — Active Backlog

**Purpose**: dispatch. Ingestion, document/RAG pipelines, knowledge base plumbing.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/pipeline-integration-index-history-through-2026-08-10.md`](../archived/pipeline-integration-index-history-through-2026-08-10.md).

**IDs are stable.** `PIP-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| PIP-01 | colbert reranker web research | [colbert-reranker-web-research.md](colbert-reranker-web-research.md) | S5: Implement reranker — HOLD as of 2026-06-12 gate analysis. Add reranking to research.py, gated behind web_research_rerank flag, only if… | — |
| PIP-02 | document parser table bench | [document-parser-table-bench.md](document-parser-table-bench.md) | Resolve PP-DocLayoutV3 weights and record cache path + size — a separate download from the GGUF | — |
| PIP-03 | ernie image turbo evaluation | [ernie-image-turbo-evaluation.md](ernie-image-turbo-evaluation.md) | Run content-filter audit live with --execute (harness ready in orchestrator ed6f65f5) and review outputs | — |
| PIP-04 | internal kb rag | [internal-kb-rag.md](internal-kb-rag.md) | K8 (LOW priority, defer): wikilink learning-loop scorer (NEW 2026-04-28, from intake-492). Flywheel's auto-wikilink suggestion uses an acce… | — |
| PIP-05 | opendataloader pipeline integration | [opendataloader-pipeline-integration.md](opendataloader-pipeline-integration.md) | Evaluate LightOnOCR-2-1B as a structural/table/reading-order parser against docling-fast | — |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
