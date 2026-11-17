# 2026-11-17 autopilot-backlog-session (PIP-04 closeout; covers the 2026-11-16/17 rows)

## Orchestrator commits pushed to main

| Commit | Change |
|---|---|
| `0e0fca38` | SearXNG engine set (brave off, yandex on), health-report counter fixes, `_shape_query` retry |
| `86b308bd` | `pdf_router` fails closed (`PdftotextError`) |
| `4f33609d` | needs_ocr routes to LightOnOCR / LiteParse; flag `ORCHESTRATOR_PDF_ROUTE_LIGHTON`, default off |
| `345ebeed` | L3 text-row table fallback; flag `ORCHESTRATOR_L3_TEXTROW`, default off |

## Results

- **SX-6: PROCEED.** SearXNG 50/50 queries, p95 1134 ms versus DDG p95 15667 ms. Recorded in `handoffs/active/knowledge-pipelines.md`; the sentinel never had a ready manifest, so it is not filed through `file_result.py`.
- **LightOnOCR routing, held-out: PASS.** n=226, mean +0.267, one-sided LB95 +0.247, wins 209 / losses 17. Born-digital flagged 16/90, +0.052. Caveat: synthetic-scan set. Interim look skipped (rc=1).
- **ODL borderless tables: closed GO** via the zero-inference text-row extractor: 0.970 on ODL-local text (65/67). pdftotext scores 1.000, which is near-circular.
- KB-GS-1, AGG-1.2 tie, G14 install contract and the parser-quality comparison are closed.

## Infra

- Pinned poppler 24.02 at `/mnt/raid0/llm/tools/poppler-noble` replaces the sudo-chroot pdftotext shim (the shim failure voided the first lighton holdout run, rc=75, superseded by `-r2`).
- needs_ocr sanity guard added to the holdout preconditions.

## Filing audit (grants vs filing-done)

All grants owned by this session with a `.complete`/`.ended` record are FILED: agg12-ingest-cpu, agg12-oolong-real-gpu, kbgs1-four-arm-cpu, parser-odl-hybrid-awk4-tables, pip04-holdout-liteparse-feat, pip04-holdout-lighton-ocr (void, rc=75) and its `-r2`. Ids with no grant record (sx6-sentinel, g14-install-contract, liteparse-route-ocr, paired-comparison, 200pdf-r2-20261116) were closed in-handoff, not through the churn pipeline.

## Remaining

- `PIP02-PADDLE-STACK-ENTRY` (gated on the v11 promotion; not ticked).
- Year-label header work for textrow tables, in progress on branch `l3-textrow-headers`.
- LightOnOCR stack-entry package to be prepared.

## Lessons

- `launcher.out` is append-only: watchers must key on a NEW `==== dry run` block, not on the file's presence of one.
- Bench empty-text checks contradicted the predeclared flag definition; check the predeclared definition before trusting a bench-side proxy.
