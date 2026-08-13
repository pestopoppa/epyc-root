# OpenDataLoader PDF — Completed Scope Through 2026-08-13

> **Historical ledger only.** Current work, gates, dependencies, and reporting instructions live in [`../active/opendataloader-pipeline-integration.md`](../active/opendataloader-pipeline-integration.md).

**Compacted**: 2026-08-13
**Scope**: landed implementation, validated scaffolding, historical observations, and corrected claims that no longer belong on the active handoff's first screen.

## Landed implementation

| Date | Area | Durable result | Evidence |
|---|---|---|---|
| 2026-04-17 | Phase 1 seam | Added ODL extraction behind `PDF_EXTRACTOR`, retained empty/garbage fallback, and introduced sibling document-extraction scoring. | NIB2-13/NIB2-14 completion records; orchestrator/research history. |
| 2026-05-06 | Structured models | Added `ODLStructuredDocument`, heading/table/figure carriers, structured figure prompts, and heading-aware chunking. | Orchestrator Phase-2 scaffold and focused tests. |
| 2026-06-21 | End-to-end carriers | Preserved structured data through OCR, preprocessing, cache and TaskIR; routed bboxes, table records, scanner suppression, and default-off body warnings. | Orchestrator commits `bd3f6f4e`, `55d1ed16`, `4f7f6d1d`, `76dcd42c`, `634a9078`, `fa1b5460`, `a0e8ae09`. |
| 2026-06-27 | Hybrid table path | Wired the official `opendataloader_pdf.convert(..., hybrid=...)` surface with configured URL/timeout/fallback and fixture replay for official JSON aliases. | Orchestrator commits `8aab2d63`, `f61c3103`. |
| 2026-07-03/04 | Fast-path probe | Added a fail-closed local probe for pdftotext, ODL local/structured/hybrid and LiteParse with latency, output hashes, quality heuristics, and structural counters. | `orchestration/reports/pdf_fastpath_probe_*`; focused probe/router tests. |
| 2026-07-17 | Availability-aware default | Made ODL the default when Java+SDK are available, with explicit env override, pdftotext fallback, cached availability, batch path, and extraction attribution. | Phase-1 Wave-2 implementation and tests. |
| 2026-07-17/18 | Model-producer scaffolding | Added guarded PaddleOCR producer, prompt/postprocess experiments, and existing-artifact comparison materialization. | Research `odl_bench` history and recorded artifacts. |
| 2026-08-13 | Unlimited-OCR scaffold | Added guarded producer, CLI/adapter dispatch, manifest stub, response artifacts, and fake-process E2E coverage. | Research `fdb2164f`; independent `26 passed`. |

## Historical observations, not promotion evidence

- The 8-PDF valid born-digital probe had 7/8 successes per non-hybrid backend. ODL's median heuristic quality was `0.987`, but latency was roughly `645–703 ms` versus `21 ms` pdftotext and `16 ms` LiteParse. The fixture produced zero ODL headings/tables/figures and zero LiteParse bbox/page-image counts, so it cannot choose a structural parser or routing policy.
- The July PaddleOCR full-page prompts were off-label. The official architecture is a layout pipeline plus cropped-element recognition and assembly, so the recorded `table.TEDS=0.0`/`0.058` values were voided and must not be cited as model quality.
- The local OmniDocBench page dataset contains 1,651 pages and 665 table regions, but lacks the immutable source-PDF mapping needed to replay PDF extractors. Earlier ODL `table.TEDS=0.783813` rested on a tiny 18-page/10-table subset and is not decision-gating.
- OpenDataLoader's 200-PDF benchmark is `/mnt/raid0/llm/opendataloader-bench-upstream`; `/mnt/raid0/llm/opendataloader-bench` is a different OmniDocBench clone. Bare-name/path-presence checks are invalid.

## Metric-contract corrections

- Committed `scripts/benchmark/odl_bench/` rows are structural text edit distance, table TEDS, reading-order edit distance, and speed. NID/MHS are implemented in sibling `scripts/benchmark/document_extraction_adapter.py`, not in the package's row schema.
- The Phase-2 chunker contract compares non-coreference Ekimetrics (SC/BI/ICC/DCC) and contradictory HOPE signals on the same digest-pinned ten-document fixture, then reports one downstream RAG answer-correctness endpoint. RC/FMRE are excluded; intrinsic-only gating is forbidden.
- Ekimetrics' published/adapted RC/FMRE path carried an earlier boundary-corruption defect (`str.find()` returned `-1` while the code caught `ValueError`). Its historical RC=99.0 claim is excluded from this program's quality design.

## 2026-08-13 audit disposition

| Workstream | Accepted | Still open in active handoff |
|---|---|---|
| ODL-011 | Premise/metric-contract preflight only. | Implement/register/test Ekimetrics and HOPE with common endpoint. |
| ODL-013 | Existing harness and July artifacts as scaffolding only. | Representative LiteParse-aware comparison and policy verdict. |
| Unlimited-OCR | Producer/dispatch code and fake E2E coverage. | Quant-compliant default artifact and granted live demo. |

- [x] **ODL-011 premise and metric-contract audit**: corrected the package/sibling metric attribution and confirmed the accepted tree has no registered Ekimetrics/HOPE arm. ✅ 2026-08-13
- [x] **ODL-013 premise and harness preflight**: confirmed the July tooling is reproducible scaffolding but no 2026-08-13 representative result exists. ✅ 2026-08-13
- [x] **Unlimited-OCR producer scaffold and `odl_bench` registration**: accepted guarded producer/dispatch code and fake-process E2E coverage; kept artifact/demo gates open. ✅ 2026-08-13

The downloaded Unlimited-OCR body is Q5_K and `output.weight` is Q6_K; the latter violates the explicit `lm_head >= Q8_0` prerequisite. No live demo was run. Exact hashes, sizes, and verification are recorded in [`progress/2026-08/2026-08-13-auditor.md`](../../progress/2026-08/2026-08-13-auditor.md).

## Closed checkpoints retained by this ledger

- Phase-1 extractor swap, quality fallbacks, availability handling, batch warming, and focused tests.
- Structured heading, figure, table, cache/TaskIR, bbox, injection-scanning, and hybrid-client wiring.
- Local fast-path harness, dependency checks, structural counters, and small-corpus artifact capture.
- Full OmniDocBench page dataset acquisition/integrity check and explicit source-PDF blocker discovery.
- PaddleOCR artifact smoke/producer/postprocess work followed by the architecture-correct retraction.
- ODL-011 and ODL-013 2026-08-13 premise/preflight audits and Unlimited-OCR code-only acceptance.

## Durable references

- [Current active handoff](../active/opendataloader-pipeline-integration.md)
- [Document Parser Table Bench](../active/document-parser-table-bench.md)
- [OpenDataLoader deep dive](../../research/deep-dives/opendataloader-pdf-pipeline-integration.md)
- [LiteParse deep dive](../../research/deep-dives/liteparse-document-parser-deep-dive.md)
- [2026-08-13 auditor progress](../../progress/2026-08/2026-08-13-auditor.md)
