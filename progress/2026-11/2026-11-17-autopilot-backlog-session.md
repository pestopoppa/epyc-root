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

## STACKCHG-OCR-LIGHTON-20261117 — applied, brought up, serving-proven (19:32–20:05Z)

| Repo | Commit | What |
|---|---|---|
| research | 58991b4d1 | registry `server_mode.ocr_pdf_lighton` + durable holdout evidence |
| orchestrator | ceab8814, fc3cfa15 | aux service `ocr_pdf_lighton` :9003 + PDF route env; derived recompile |
| orchestrator | d6c133ac | pdf_router: pdftoppm page renderer when PyMuPDF absent; `resolve_poppler_tool()` (env dir → PATH → pinned noble) |
| orchestrator | be98b951 (branch `deps/liteparse-pin`, push pending operator) | pin liteparse==2.12.0 + py-cpuinfo in pyproject/uv.lock |

Bring-up found three deployment gaps that no preflight covered, all fixed:
1. API venv has no PyMuPDF → every needs_ocr PDF raised LightOnOCRError. Fixed d6c133ac.
2. API PATH has no poppler → pdftotext probe could not run. Fixed d6c133ac (+ `/mnt/raid0/llm/tools/poppler-noble/pdftoppm` wrapper).
3. liteparse not installed in the orchestrator venv → every non-OCR PDF raised LiteParseUnavailableError. Installed 2.12.0 (uv), pinned be98b951.

Serving proof: llama-server argv[0] and libggml-cpu map into kernels/builds/cpu-20260921-ffc1bac82; linkage PASS; /health OK; real page completion returned a table. API pid 1979574 env carries ROUTE_LIGHTON=1, LIGHTON_URL=:9003, L3_TEXTROW=1. `extract_pdf` under the live API env over 6 smoke PDFs + 1 scan: 0 failures, routing equals the held-out legacy_router needs_ocr flags 6/6. API health "degraded" only because the main model servers are intentionally down. stack-change-pending marker cleared. Rollback: `ORCHESTRATOR_PDF_ROUTE_LIGHTON=0` + `reload orchestrator`. [no-belief: deployment proof, the measurement is the already-filed held-out PASS]

Lesson: stack-change preflight validates registry/topology, not the consuming code path's runtime deps. Bring-up must exercise the feature through the live process env, not only the new server.
