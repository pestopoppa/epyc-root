# OpenDataLoader PDF — Pipeline Integration

**Status**: Phase 1 done (NIB2-13). Phase 2 scaffolding landed 2026-05-06 — `src/models/odl_structured.py` (FigureContext, HeadingNode, TableContext, ODLStructuredDocument); `_extract_with_opendataloader_structured()` in pdf_router; `build_figure_prompt_with_context()` additive helper in figure_analyzer; `chunk_by_odl_headings()` additive helper in document_chunker. 2026-06-21 follow-ups (`epyc-orchestrator` `bd3f6f4e`, `55d1ed16`, `4f7f6d1d`, `76dcd42c`, `634a9078`, `fa1b5460`, `a0e8ae09`) wire optional structured payloads through `OCRResult`, `DocumentPreprocessor`, `DocumentChunker`, and `FigureAnalyzer`, route explicitly gated local PDF processing through the ODL structured extractor, use ODL structured figure bboxes instead of PyMuPDF image enumeration in ODL structured mode, suppress unsafe ODL structured metadata when `INJECTION_SCANNING` is enabled, carry ODL table metadata through preprocessing/cache/TaskIR output, add a default-inert ODL table backend routing seam, and add a default-off primary document-body warning policy. ODL headings now drive chunking when present with regex fallback, ODL figure contexts enrich per-figure VL prompts unless the injection scanner suppresses the additive structured context, ODL tables are first-class `TableRef` records for downstream routing, and `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY=warn` can scan extracted OCR/body pages without mutating or blocking source text. 2026-06-27 follow-ups (`epyc-orchestrator` `8aab2d63`, `f61c3103`) wire the explicit `ORCHESTRATOR_ODL_TABLE_BACKEND=hybrid` path through the official `opendataloader_pdf.convert(..., hybrid=...)` SDK surface with env-configured backend URL/timeout/fallback and local-structured fallback, then add hybrid artifact replay fixtures covering official ODL JSON key aliases. 2026-07-04 no-inference corpus probes (`epyc-orchestrator/orchestration/reports/pdf_fastpath_probe_20260704T084521Z.{json,md}`, `pdf_fastpath_probe_valid_20260704T084622Z.{json,md}`, and `pdf_fastpath_probe_valid_structuralmeta_20260704T135015Z.{json,md}`) confirm the local ODL/LiteParse/pdftotext harness is runnable and distinguish corrupt archive fixtures from valid born-digital PDFs. 2026-07-06 adds the `opendataloader_hybrid` backend to the fast-path probe with explicit sidecar dependency checks, so hybrid evidence can fail closed as `missing_dependency` when the sidecar is absent. On the filtered 8-PDF valid set, all four non-hybrid backends succeeded on 7/8; ODL local/structured had the highest median quality score (`0.987`) but much higher median latency (`645-703 ms` vs `21 ms` pdftotext and `16 ms` LiteParse), and the structural-metadata rerun explicitly reports zero ODL headings/tables/figures and zero LiteParse bboxes/page images on this corpus despite `1195` table-like text lines. This remains default-inert unless `PDF_EXTRACTOR=opendataloader`, `ORCHESTRATOR_ODL_STRUCTURED=1`, and/or the table backend env are explicitly set; the injection filters are additionally gated by `INJECTION_SCANNING`. Remaining Phase 2 work: larger structural/table-heavy corpus evidence and hybrid output/table-selection policy. Phase 3 (sidecar deployment + benchmark) remains sidecar/evidence-gated.
**Created**: 2026-03-17 (via research intake deep dive)
**Priority**: P2 — medium priority, medium effort, high payoff for document processing quality
**Categories**: document_processing, multimodal

## Objective

Integrate [OpenDataLoader PDF](https://github.com/opendataloader-project/opendataloader-pdf) into the orchestrator's document processing pipeline to improve reading order, add table extraction, and provide structured context to downstream models (LightOnOCR, VL models).

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-161 | OpenDataLoader PDF - PDF Parser for AI-ready data | medium | worth_investigating |

**Deep dive**: `research/deep-dives/opendataloader-pdf-pipeline-integration.md`
**XY-Cut++ paper**: [arXiv:2504.10258](https://arxiv.org/abs/2504.10258)
**Benchmark repo**: [opendataloader-bench](https://github.com/opendataloader-project/opendataloader-bench)

## Current Pipeline Gaps

1. **No table extraction**: pdftotext outputs tables as jumbled text; LightOnOCR outputs bboxes but no structured table data
2. **No reading order**: pdftotext `-layout` interleaves multi-column text
3. **Binary routing**: pdftotext (fast) OR LightOnOCR (slow) — no per-page complexity routing
4. **Blind figure analysis**: VL models receive cropped images without document context (caption, surrounding text, semantic type)
5. **Hybrid/table evidence gap**: the local structured path carries ODL table metadata, the explicit ODL hybrid SDK client is wired, and fixture replay covers official ODL JSON aliases; sidecar deployment, benchmark evidence, and benchmark-backed routing policy are not implemented

## Three-Phase Plan

### Phase 1: Replace pdftotext with ODL Local

**Goal**: Same latency, better reading order + structured output
**Effort**: Small (swap extraction call in `pdf_router.py`)

- [ ] Install `opendataloader-pdf` (Python SDK, requires Java 11+)
- [ ] Run ODL local on sample documents from orchestrator test corpus
- [ ] Compare reading order, heading detection, table identification vs pdftotext
- [ ] Swap `pdftotext -layout` for `opendataloader_pdf.convert(format="markdown,json")` in `pdf_router.py`
- [ ] Keep quality check logic (entropy/garbage/word-length) on ODL output
- [ ] Handle JVM lifecycle: persistent subprocess or batch warming
- [ ] Update tests in `tests/services/test_pdf_router.py`

**Key files**:
- `src/services/pdf_router.py` — `_extract_with_pdftotext()` → new `_extract_with_opendataloader()`
- `src/models/document.py` — may need new fields for structured JSON output

### Phase 2: Structured Context for Downstream Models (Biggest Win)

**Goal**: VL models + chunker get rich structural context from ODL JSON output
**Effort**: Medium

- [x] Parse ODL JSON output: extract figure bboxes + semantic types + captions
- [x] Route explicitly gated local PDFs into ODL structured extraction and preserve `structured_data` into preprocessing
- [x] Feed figure context to `figure_analyzer.py`: type, caption, surrounding text, heading position
- [x] Replace PyMuPDF figure extraction with ODL bboxes in ODL structured mode (skip `_extract_figures_pymupdf`)
- [x] Improve `document_chunker.py`: use heading hierarchy from ODL instead of regex splitting
- [x] Suppress unsafe ODL structured metadata before chunking / VL prompt enrichment when `INJECTION_SCANNING` is enabled
- [x] Carry detected ODL tables through preprocessing/cache/TaskIR output as first-class table records
- [x] Add a default-inert ODL table backend routing seam for local structured vs future hybrid extraction
- [x] Define primary extracted-text prompt-injection policy for document bodies
- [x] Implement the ODL hybrid table sidecar/client path for 0.93 accuracy extraction

**Key files**:
- `src/services/figure_analyzer.py` — enrich VL prompts with document context
- `src/services/document_chunker.py` — structural splitting from JSON headings
- `src/services/document_preprocessor.py` — orchestrate structured context flow

**2026-06-21 implementation checkpoint (`epyc-orchestrator` `bd3f6f4e`)**

- Added `coerce_structured_document()` and preserved `OCRResult.structured_data` through API/cache dict conversions.
- `DocumentPreprocessor.preprocess()` now extracts structured payloads from TaskIR metadata or the returned OCR result, passes them to `chunk_document()`, and forwards ODL figure contexts to figure analysis.
- `DocumentChunker.process()` now prefers ODL headings and falls back to the existing regex splitter when structured headings do not align with extracted text.
- `FigureAnalyzer` now accepts per-figure contexts and builds per-figure prompts without changing the base prompt path for context-free figures.
- Validation: GitNexus LOW for `chunk_by_odl_headings`, `build_figure_prompt_with_context`, and `FigureAnalyzer.analyze_figures`; MEDIUM for `DocumentPreprocessor.preprocess`. `py_compile` passed. `ruff` passed. Focused tests passed: `tests/unit/test_odl_structured.py`, `tests/unit/test_pdf_router.py`, `tests/unit/test_figure_analyzer.py`, and `tests/integration/test_document_pipeline.py::TestDocumentPreprocessor::test_preprocess_uses_structured_context_when_available` (`61 passed, 2 skipped`).
- Residual risk: ODL figure-context alignment assumes ODL figure order matches extracted figure order; mismatch degrades to an un-enriched prompt. The current OCR server endpoints still do not emit `structured_data`; this slice preserves and consumes it when present, but does not yet make the LightOnOCR endpoint itself produce it.

**2026-06-21 producer-path checkpoint (`epyc-orchestrator` `55d1ed16`)**

- `DocumentClient.process_document()` now uses the local ODL structured extractor for PDF inputs only when both `PDF_EXTRACTOR=opendataloader` and `ORCHESTRATOR_ODL_STRUCTURED=1` are set.
- The bridge preserves `PDFExtractionResult.structured_data` into `OCRResult.structured_data`, so local PDF processing can feed the Phase 2 consumer path without requiring TaskIR metadata injection.
- The implementation deliberately calls the structured ODL helper directly, not `PDFRouter.extract()`, so this opt-in path does not fall through to LightOnOCR/model-backed OCR fallback. Default PDF processing still uses the existing OCR-client path.
- Validation: GitNexus MEDIUM for `DocumentPreprocessor.preprocess`, LOW for `process_document`, LOW for `DocumentFormalizerClient.ocr_pdf`, and LOW for `PDFRouter.extract`. `py_compile`, `ruff`, `git diff --check`, focused tests (`63 passed, 2 skipped`), and the full `tests/integration/test_document_pipeline.py` file (`51 passed`) passed.
- Residual risk: page text remains document-level because the structured helper returns whole-document markdown, not per-page markdown. Figure bboxes still come from PyMuPDF until the ODL bbox replacement task is completed.

**2026-06-21 ODL bbox checkpoint (`epyc-orchestrator` `4f7f6d1d`)**

- `PDFRouter` now adapts `ODLStructuredDocument.figures[*].bbox` into normalized `ExtractedFigure` bboxes when ODL structured data is present.
- The adapter uses PyMuPDF only to read page dimensions for PDF-point-to-normalized-coordinate conversion; it does not enumerate images or extract figure bytes.
- `PDFRouter.extract()` and the local `DocumentClient` producer path both prefer the ODL bbox adapter when `structured_data` is present, and tests assert `_extract_figures_pymupdf()` is not called in that mode.
- Validation: GitNexus LOW for `_extract_local_structured_pdf`, `_extract_figures_pymupdf`, and `PDFRouter.extract`; `py_compile`, `ruff`, `git diff --check`, focused PDF/document tests (`21 passed, 2 skipped`), and the broader ODL/PDF/figure/document suite (`114 passed, 2 skipped`) passed.
- Residual risk: ODL structured figures currently carry bbox/caption/type context, but not extracted image bytes. Downstream figure analysis crops from the source PDF using the bbox, so this is acceptable for the current pipeline.

**2026-06-21 ODL structured-context injection checkpoint (`epyc-orchestrator` `76dcd42c`)**

- `DocumentPreprocessor.preprocess()` now routes optional ODL structured metadata through the existing `src.security.injection_scanner.scan_content()` path when `INJECTION_SCANNING` is enabled.
- Unsafe ODL headings, figure captions/surrounding text/breadcrumbs, and table captions/markdown/rows suppress the additive structured document before chunking and figure analysis. The fallback path keeps OCR text processing intact, so structured metadata cannot steer section titles or VL prompts after a scanner hit.
- Default-off compatibility is preserved: with injection scanning disabled, existing ODL structured metadata continues to drive heading chunking and figure context.
- Validation: GitNexus MEDIUM for `DocumentPreprocessor.preprocess` and `ODLStructuredDocument`, LOW for `scan_content`; `py_compile`, `ruff`, `git diff --check`, focused injection/ODL tests (`41 passed`), and the broader ODL/PDF/figure/document suite (`116 passed, 2 skipped`) passed.
- Residual risk: this is structured-metadata filtering, not a full body-level policy for primary OCR text. That policy remains open because blocking source document text requires separate product/security semantics and false-positive handling.

**2026-06-21 ODL table-carrier checkpoint (`epyc-orchestrator` `634a9078`)**

- Added `TableRef` to the document preprocessing result model, with cache serialization and default-empty backwards compatibility.
- `DocumentChunker.process()` now converts `ODLStructuredDocument.tables` into `TableRef` records with page, bbox, caption, markdown, rows, and best-effort section association.
- `DocumentPreprocessor.enrich_task_ir()` now emits table summaries alongside sections and figures, and archive preprocessing preserves table IDs through merged document results.
- Validation: GitNexus MEDIUM for `DocumentPreprocessResult` and `TableContext`; `py_compile`, `ruff`, `git diff --check`, focused table/cache/enrichment tests (`36 passed`), and broader ODL/PDF/figure/document/archive tests (`153 passed, 2 skipped`) passed.
- Residual risk: this is the table-routing substrate, not full hybrid extraction. The next table step is a gated ODL hybrid sidecar/router decision backed by fixture or benchmark evidence.

**2026-06-21 ODL table backend seam checkpoint (`epyc-orchestrator` `fa1b5460`)**

- `PDFRouter` now owns a narrow table backend selector via `ORCHESTRATOR_ODL_TABLE_BACKEND`, plus an `extract_opendataloader_structured()` helper used by the direct local structured path.
- The current effective backend remains local structured ODL. Explicit `ORCHESTRATOR_ODL_TABLE_BACKEND=hybrid` requests are logged and fall back to local ODL because no hybrid sidecar/client exists yet.
- `DocumentClient.process_document()` now reaches local structured PDF extraction through the router helper instead of duplicating result assembly and page-count logic.
- Validation: GitNexus LOW for `PDFRouter`, `process_document`, `_extract_local_structured_pdf`, and `PDFRouter.extract`; `py_compile`, `ruff`, `git diff --check`, focused ODL/router/client tests (`4 passed`), and the broader ODL/PDF/cache/document suite (`106 passed, 2 skipped`) passed.
- Residual risk: this is only the default-inert routing seam. The actual hybrid sidecar/client, table-selection policy, and opendataloader-bench/fixture evidence remain open.

**2026-06-27 ODL hybrid SDK client checkpoint (`epyc-orchestrator` `8aab2d63`)**

- `PDFRouter` now exposes a real default-off hybrid path for `ORCHESTRATOR_ODL_TABLE_BACKEND=hybrid` using the official OpenDataLoader Python SDK options: `hybrid`, `hybrid_url`, `hybrid_timeout`, and `hybrid_fallback`.
- Added env knobs `ORCHESTRATOR_ODL_HYBRID_BACKEND` (default `docling-fast`), `ORCHESTRATOR_ODL_HYBRID_URL` (default `http://localhost:5002`), `ORCHESTRATOR_ODL_HYBRID_TIMEOUT_MS` (default `60000`), and `ORCHESTRATOR_ODL_HYBRID_FALLBACK` (default enabled).
- Local structured extraction and hybrid extraction now share the same markdown/JSON output reader, so parsed `ODLStructuredDocument` semantics stay identical across local and hybrid modes.
- If the hybrid SDK path is unavailable, errors, or produces no output, the router falls back to local structured ODL rather than changing default extraction behavior.
- Validation: GitNexus LOW for `PDFRouter`, `_extract_with_odl_table_backend`, and `extract_opendataloader_structured`; `py_compile`, `ruff`, `git diff --check`, focused PDF router tests (`24 passed, 2 skipped`), broader document/PDF unit slice (`72 passed, 2 skipped`), and `tests/integration/test_document_pipeline.py` (`55 passed`) passed.
- Residual risk: this still does not deploy or supervise `opendataloader-pdf-hybrid --port 5002`, and it does not assert live 0.93 table accuracy. Next work is fixture-backed hybrid output replay plus opendataloader-bench/local corpus evidence before changing routing policy.

**2026-06-27 ODL hybrid fixture replay checkpoint (`epyc-orchestrator` `f61c3103`)**

- Added deterministic `.md`/`.json` hybrid replay fixtures under `tests/unit/fixtures/`.
- `ODLBoundingBox.from_dict()` now accepts official ODL-style `bounding box` and `page number` aliases in addition to the existing `bbox`, `page`, and `page_number` shapes.
- `TableContext.from_dict()` now accepts table `content` as a markdown-form alias.
- Added parser-level and router-output-reader tests so hybrid artifact replay preserves heading/table/figure coordinates and rows without a live sidecar.
- Validation: GitNexus MEDIUM for `ODLStructuredDocument`, `TableContext`, and `ODLBoundingBox`; classmethod symbols were not individually indexed. `py_compile`, `ruff`, `git diff --check`, focused ODL/PDF tests (`50 passed, 2 skipped`), broader document/PDF unit slice (`75 passed, 2 skipped`), and `tests/integration/test_document_pipeline.py` (`55 passed`) passed.
- Residual risk: fixture replay proves parser compatibility, not extraction quality. The next evidence step remains a live/local-corpus sidecar benchmark before routing policy changes.

**2026-06-21 document body injection policy checkpoint (`epyc-orchestrator` `a0e8ae09`)**

- `DocumentPreprocessor` now has an explicit primary body policy gate via `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY`.
- Default behavior remains `source`: primary OCR/PDF body text is not scanned, mutated, suppressed, or blocked beyond the existing source-content path.
- `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY=warn`, combined with `INJECTION_SCANNING`, scans page body text with the existing injection scanner and appends warnings such as `Document body injection scan warning (page N: ...)` without altering chunked document content.
- The structured metadata scanner remains independent: unsafe ODL headings/figures/tables can still suppress additive structured context, while source OCR body text stays available for downstream chunking.
- Validation: GitNexus MEDIUM for `DocumentPreprocessor.preprocess`; HIGH for `scan_content` and deliberately no scanner edit. `py_compile`, `ruff`, `git diff --check`, focused body/structured policy tests (`4 passed`), and the broader document/ODL/PDF/cache/scanner suite (`124 passed, 2 skipped`) passed.
- Residual risk: warn-mode is annotation only. Any future `block` or redact behavior needs separate false-positive/product semantics and broader caller evidence.

### Phase 3: Hybrid Mode + Benchmark Integration

**Goal**: Best-in-class table extraction + reproducible comparison with competition
**Effort**: Medium-Large

- [ ] Deploy `opendataloader-pdf-hybrid --port 5002` as sidecar service
- [x] Add a sidecar-aware `opendataloader_hybrid` backend to `scripts/benchmark/pdf_fastpath_probe.py` so hybrid preflights report missing SDK/sidecar dependencies explicitly instead of silently skipping or forcing live infra ✅ 2026-07-06
- [x] Stamp the effective ODL backend in router results (`opendataloader_structured` vs `opendataloader_hybrid`) and add an opt-in probe guard that fails no-structural-signal corpora before they are used as table-routing evidence ✅ 2026-07-06
- [x] Run local OpenDataLoader benchmark demo smoke without inference or persistent artifacts: `/mnt/raid0/llm/opendataloader-bench/pdf_validation.py` completed 18 demo pages from a temp cwd using the benchmark venv; output was temp-local only. ✅ 2026-07-06
- [x] Add a repeatable structural/table-heavy candidate manifest builder for quiet-window probe batches. ✅ 2026-07-06
- [ ] Install the hybrid extra on the target host (`pip install -U "opendataloader-pdf[hybrid]"`), start `opendataloader-pdf-hybrid --port 5002`, and confirm `GET /health` before claiming live sidecar evidence.
- [ ] Experiment: swap hybrid backend from docling-fast → LightOnOCR-2-1B (port 8082)
- [ ] Measure: does GPU-accelerated LightOnOCR beat docling-fast's 0.43s/page?
- [ ] Implement three-way routing: ODL local (simple) → ODL hybrid (tables) → LightOnOCR (scanned)
- [ ] Clone opendataloader-bench, add our pipeline as custom engine
- [ ] Run comparison on 200 PDFs: our pipeline vs ODL local vs ODL hybrid vs docling vs marker
- [ ] Publish results in progress log

**2026-06-28 benchmark-environment checkpoint**:

- Read-only sidecar located the current Phase 3 entrypoints: `opendataloader-pdf-hybrid --port 5002` for the hybrid sidecar, `uv run src/run.py` in this handoff's custom harness notes, and the upstream benchmark repo's documented `python pdf_validation.py --config <config_path>` path under `/mnt/raid0/llm/opendataloader-bench`.
- Expected upstream artifacts are `*_result.json`, `*_metric_result.json`, `*_run_summary.json`, runtime/stage logs, per-metric JSON files, and `result/{save_name}/CDM/` outputs.
- Local-only validation `uv run --with pytest python -m pytest tools/test_environment_and_smoke.py::TestCDMCalculation -q` failed for environment reasons, not routing/policy reasons: `/share/texlive/pdflatex` is missing, so CDM checks returned `0.0` and LaTeX bbox smoke outputs were not produced.
- Follow-up attempted the documented Docker path (`ghcr.io/zeng-weijun/omnidocbench-eval:repro-ubuntu2204`) instead of installing TeX Live on the host. The pull did not complete because GHCR layer downloads for `baf0dae3bf9f` / `18bba57308dc` repeatedly retried and then went quiet; the pull process was terminated and verified gone. No complete image is present locally.
- No persistent benchmark evidence was written. The evidence gap remains: no live `opendataloader-pdf-hybrid` sidecar benchmark and no benchmark-backed table-selection policy evidence.
- Next run should retry the documented container pull/run or use a host with the expected TeX Live layout, execute `python pdf_validation.py --config <config_path>` against a temp-mounted result directory, and only then consider hybrid/table routing policy edits.

**2026-07-04 local fast-path corpus checkpoint (`epyc-orchestrator` report artifacts)**

- Ran `scripts/benchmark/pdf_fastpath_probe.py` with transient `opendataloader-pdf`
  and `liteparse` dependencies while AutoPilot remained live; no model inference
  or sidecar load was used.
- The first 12-PDF sample intentionally included locally discovered archive
  PDFs and produced `pdf_fastpath_probe_20260704T084521Z.{json,md}`. It showed
  `8/12` archive `docs/*.pdf` files were corrupt/truncated across pdftotext,
  ODL, and LiteParse, so those fixtures are not valid born-digital evidence.
- The filtered `pdfinfo`-valid 8-PDF sample produced
  `pdf_fastpath_probe_valid_20260704T084622Z.{json,md}`. Results:
  pdftotext `7/8` success, median latency `22.439 ms`, median quality `0.822`;
  ODL local `7/8`, `644.072 ms`, `0.987`; ODL structured `7/8`,
  `685.962 ms`, `0.987`; LiteParse `7/8`, `18.384 ms`, `0.935`.
  The shared failure was `Statistics.pdf`, an image/figure-heavy PDF with empty
  extractable text.
- Structured ODL returned zero headings/tables/figures for all successful PDFs,
  and PyMuPDF was unavailable in this runtime, so this is fast-path extraction
  evidence only. It does not support a router-policy flip; the next evidence
  target remains a table-heavy/structural corpus plus hybrid sidecar output.
- Follow-up rerun `pdf_fastpath_probe_valid_structuralmeta_20260704T135015Z`
  used the same valid 8-PDF corpus after extending the harness with
  `--corpus-name`, `--corpus-kind`, `--manifest`, per-backend structural totals,
  and overall `structural_signal_totals`. The rerun preserved the same
  direction: pdftotext `7/8`, `20.819 ms`, `0.822`; ODL local `7/8`,
  `645.011 ms`, `0.987`; ODL structured `7/8`, `702.757 ms`, `0.987`;
  LiteParse `7/8`, `16.180 ms`, `0.935`. Structural totals were
  `structured_headings=0`, `structured_tables=0`, `structured_figures=0`,
  `liteparse_bboxes=0`, `liteparse_page_images=0`, and
  `table_like_lines=1195`, confirming that this corpus is useful only for
  fast-path text extraction evidence.

**2026-07-06 hybrid sidecar probe preflight checkpoint (`epyc-orchestrator` `6adc48fe`)**

- `scripts/benchmark/pdf_fastpath_probe.py` now treats `opendataloader_hybrid`
  as a first-class backend and checks both `opendataloader_pdf` importability
  and `ORCHESTRATOR_ODL_HYBRID_URL` reachability before invoking the router's
  hybrid extractor.
- Missing module or unreachable sidecar cases become explicit
  `missing_dependency` records with concrete detail. This keeps Phase 3
  evidence-gated and no-inference by default: the harness can be run before the
  sidecar is deployed, but it cannot accidentally turn absence of sidecar
  infrastructure into empty-output quality evidence.
- Validation: GitNexus LOW for `_run_backend` and
  `_opendataloader_dependency_failure`; `python3 -m py_compile
  scripts/benchmark/pdf_fastpath_probe.py tests/unit/test_pdf_fastpath_probe.py`;
  `uv run pytest -q tests/unit/test_pdf_fastpath_probe.py` (`10 passed`);
  `uv run ruff check scripts/benchmark/pdf_fastpath_probe.py
  tests/unit/test_pdf_fastpath_probe.py`.
- Remaining gate: no `opendataloader-pdf-hybrid --port 5002` sidecar was
  started, and no 200-PDF benchmark evidence exists yet. The next live window
  should deploy the sidecar, run the hybrid probe on a structural/table-heavy
  corpus, then decide whether any router policy change is justified.

**2026-07-06 backend-attribution + structural-signal guard checkpoint (`epyc-orchestrator` `d6b171fd`)**

- `PDFRouter._extract_with_odl_table_backend()` now carries the effective
  backend through the structured extraction path. Successful explicit hybrid
  output reports `PDFExtractionResult.method="opendataloader_hybrid"`; local
  structured output and hybrid-empty fallback report
  `opendataloader_structured`. This makes later production/preprocessing
  evidence distinguish the producer without enabling hybrid by default.
- `scripts/benchmark/pdf_fastpath_probe.py` now reports
  `structural_signal_pdf_count` and `structural_signal_pdf_fraction`, and
  `--require-structural-signal` exits `3` when no PDF/backend pair produced
  table/layout signal. This prevents another fast-path text corpus with zero
  ODL tables/headings/figures from being misread as table-routing evidence.
- Validation: GitNexus LOW for `_select_odl_table_backend`,
  `_extract_with_odl_table_backend`, `extract_opendataloader_structured`,
  `run_probe`, `_run_backend`, `_structural_signal_totals`, and probe `main`;
  `python3 -m py_compile src/services/pdf_router.py
  scripts/benchmark/pdf_fastpath_probe.py tests/unit/test_pdf_router.py
  tests/unit/test_pdf_fastpath_probe.py`; `uv run pytest -q
  tests/unit/test_pdf_router.py tests/unit/test_pdf_fastpath_probe.py`
  (`38 passed, 2 skipped`); focused `ruff` and `git diff --check` passed.
- Remaining gate: still no sidecar deployment, structural/table-heavy corpus,
  or benchmark-backed three-way routing policy. This slice only improves
  attribution and corpus qualification.

**2026-07-06 OpenDataLoader benchmark demo smoke (read-only preflight)**

- A sidecar preflight created the local benchmark venv in
  `/mnt/raid0/llm/opendataloader-bench` with `uv sync`, then removed the
  transient `uv.lock`; no EPYC repo files were edited by the sidecar.
- The documented benchmark path ran successfully from a temp working directory:
  `/mnt/raid0/llm/opendataloader-bench/.venv/bin/python
  /mnt/raid0/llm/opendataloader-bench/pdf_validation.py --config <temp-yaml>`.
  The config pointed ground truth at
  `/mnt/raid0/llm/opendataloader-bench/demo_data/omnidocbench_demo/OmniDocBench_demo.json`
  and prediction data at
  `/mnt/raid0/llm/opendataloader-bench/demo_data/end2end`; CDM was omitted so
  the run stayed offline and did not require TeX, ImageMagick, or Ghostscript.
- The smoke processed 18 demo pages with no timeouts or exceptions. Key metrics:
  `text_block ALL_page_avg=0.335621`, `table TEDS=0.796747`, and
  `reading_order ALL_page_avg=0.224300`.
- Live sidecar deployment remains blocked: base Python cannot import
  `opendataloader_pdf` / `opendataloader_pdf_hybrid`, and
  `opendataloader-pdf-hybrid` is not on `PATH`. Next action is explicit host
  install of `opendataloader-pdf[hybrid]`, start
  `opendataloader-pdf-hybrid --port 5002`, then confirm
  `GET /health` before claiming hybrid-sidecar evidence.

**2026-07-06 structural/table-heavy manifest-builder checkpoint (`epyc-orchestrator`)**

- Added `scripts/benchmark/build_pdf_probe_manifest.py`, a no-inference
  preflight that scans local PDFs, samples the first pages with `pdftotext`
  when available, ranks candidates by table-like line density, path hints,
  page count, and size, and writes a `pdf_probe_manifest.v1` JSON object that
  `pdf_fastpath_probe.py --manifest` can consume directly.
- The intended quiet-window batch shape is now explicit:

  ```bash
  uv run python scripts/benchmark/build_pdf_probe_manifest.py \
    --root /mnt/raid0/llm/cloud-llm-vault/epyc/claude \
    --root /mnt/raid0/llm/models/hy-mt2-1.8b/base-metadata \
    --output orchestration/reports/pdf_structural_candidates_$(date -u +%Y%m%dT%H%M%SZ).json \
    --limit 40 --max-files 400 --sample-pages 3 --min-table-like-lines 1

  uv run --with opendataloader-pdf --with liteparse \
    python scripts/benchmark/pdf_fastpath_probe.py \
    --manifest orchestration/reports/<manifest>.json \
    --backend pdftotext --backend opendataloader_structured --backend liteparse \
    --corpus-name structural-table-heavy-candidates \
    --corpus-kind structural_table_heavy \
    --require-structural-signal \
    --output-json orchestration/reports/<run>/summary.json \
    --output-md orchestration/reports/<run>/summary.md
  ```

- Hybrid evidence remains a separate quiet-window step after the sidecar is
  installed and health-checked; add `--backend opendataloader_hybrid` only when
  `opendataloader-pdf-hybrid --port 5002` is live.
- Smoke validation used roots under `/mnt/raid0/llm/epyc-root/tmp` and
  `/mnt/raid0/llm/models/hy-mt2-1.8b/base-metadata`, selected `3/3` candidates,
  and successfully fed the manifest into `pdf_fastpath_probe.py` with
  `--backend pdftotext --require-structural-signal`. This is corpus-prep
  evidence only; no router policy changes follow until ODL/LiteParse/hybrid
  results on the manifest exist.

**2026-07-06 manifest/probe checkpoint (`epyc-orchestrator`)**

- Built the repeatable quiet-window manifest
  `orchestration/reports/pdf_structural_candidates_20260706T145900Z.json`
  from the configured `epyc/claude` and `hy-mt2-1.8b/base-metadata` roots.
  The manifest selected `27/27` PDFs, all of which carried structural signal
  under the cheap preflight.
- Ran the structural/table-heavy probe on that manifest with
  `pdftotext`, `opendataloader_structured`, and `liteparse`, producing
  `orchestration/reports/pdf_fastpath_probe_structural_20260706T145900Z.{json,md}`.
  Results: `27` PDFs, `81` successful backend attempts, structural signal on
  `27/27` PDFs, `table_like_lines=19725`, pdftotext median latency/quality
  `121.591 ms / 0.928`, ODL structured `2877.039 ms / 1.000`, LiteParse
  `91.897 ms / 0.959`.
- Interpretation: the manifest is rich enough to support the next evidence
  step, but the local structured path is still much slower than the text
  fast paths. Hybrid-sidecar evidence remains absent, so routing policy stays
  default-inert.

**2026-06-28 benchmark adapter local-PDF checkpoint (`epyc-inference-research` `5d14d3d`, `5ab748d`)**

- `document_extraction_adapter.py` now matches the current local OpenDataLoader-bench layout: source PDFs under `pdfs/` and Markdown ground truth under `ground-truth/`.
- The adapter no longer treats Markdown files as pseudo-PDFs; availability requires both local directories and missing PDFs are skipped.
- A generic benchmark-suite wrapper, `DocumentExtractionDatasetAdapter`, emits prompt dictionaries with `scoring_method=document_extraction`, `pdf_path`, and `nid/teds/mhs/aggregate` metric metadata while preserving the direct `DocumentExtractionAdapter` PDF-object API.
- `dataset_adapters.get_adapter("document_extraction")` now returns the lazy wrapper. This CRITICAL fanout symbol was handled in the main thread after GitNexus refresh because `get_adapter` affects 15 benchmark processes (`impactedCount=38`, risk `CRITICAL`).
- Validation: `python3 -m py_compile` on touched research files; fatal ruff slice (`E9,F401,F821,F822,F823`) passed; full-file ruff remains blocked by pre-existing unrelated `dataset_adapters.py` F841/F541 lint debt; focused pytest slice passed (`147 passed`); direct registry smoke confirmed absent local dataset reports `0` rows rather than a registration failure.
- Remaining evidence gate: the actual `/mnt/raid0/llm/opendataloader-bench` Git LFS dataset is still absent, so no 200-PDF baseline has been run.

**Target routing architecture**:
```
PDF Input
    ↓
[ODL local] → 0.05s/page, structured output
    ↓
[Per-page assessment]
    ├─ Simple text page → use directly
    ├─ Complex tables → ODL hybrid (0.93 acc)
    ├─ Scanned/image → LightOnOCR-2-1B (GPU OCR)
    └─ Figures → crop + VL model with structured context
```

### Benchmark Suite Integration

**Goal**: Add opendataloader-bench's 200-PDF dataset to our benchmark infrastructure
**Effort**: Small

- [ ] Clone opendataloader-bench repo (MIT license, 200 PDFs via Git LFS)
- [x] Add `document_extraction` suite to the benchmark adapter path consumed by `question_pool.py`
- [x] Adapt ground truth format (Markdown references → our scoring contract)
- [x] Scoring methods: NID (reading order), TEDS (table DOM), MHS (heading hierarchy)
- [x] Register as suite in benchmark infrastructure for reproducible comparisons
- [ ] Run baseline: our current pipeline (pdftotext + LightOnOCR) on the 200 PDFs

**Dataset details**:
- 200 real-world PDFs in `pdfs/` directory (Git LFS)
- Ground truth: Markdown files in `ground-truth/`
- Metrics: NID/NID-S (reading order), TEDS/TEDS-S (tables), MHS/MHS-S (headings)
- Evaluation pipeline: `uv run src/run.py` with per-engine and per-document filtering

## Open Questions

1. JVM cold start cost — can we pre-warm via persistent subprocess?
2. Single-page processing support in Python SDK?
3. JSON output schema stability across versions?
4. Can LightOnOCR serve as ODL hybrid backend (replace docling-fast)?
5. opendataloader-bench: custom engine integration effort?

## Dependencies

- Java 11+ runtime on EPYC host
- `pip install opendataloader-pdf` (22.3 MB, Python >=3.10)
- Optional: `pip install "opendataloader-pdf[hybrid]"` for Phase 3

## Notes

- ODL local mode is rule-based (XY-Cut++ algorithm), not ML — no GPU needed, deterministic output
- Python SDK wraps Java CLI — each `convert()` spawns JVM. Sidecar pattern recommended for production.
- The structured context improvement for VL models (Phase 2) is the highest-value item — figures are currently analyzed without any document context.

## Research Intake Update — 2026-04-17

### Evaluated and skipped

- **[intake-398] google/magika** — evaluated 2026-04-17, verdict **not_applicable**.
  Deep dive (`research/deep-dives/magika-filetype-detection.md`) confirmed:
  OpenDataLoader is PDF-only (not a filetype detector — original question malformed);
  EPYC's corpus is homogeneous known-format URL-fetch (arXiv PDFs, GitHub READMEs,
  HTML, HF cards) where format is declared by URL/MIME/extension; no pipeline stage
  needs generic byte-sniffing; live test on EPYC misclassified JSON as JSONL;
  80 MB onnxruntime + 225 ms cold-start for zero accuracy gain.
  Reconsider only if EPYC starts ingesting arbitrary binary corpora.

## Research Intake Update — 2026-04-22

### New Related Research

- **[intake-436] "Web Retrieval-Aware Chunking (W-RAC) for Efficient and Cost-Effective Retrieval-Augmented Generation Systems"** (arxiv:2604.04936)
  - Relevance: Directly applicable to Phase 1 chunking strategy. W-RAC claims an order-of-magnitude reduction in chunking-related LLM costs vs traditional LLM-based chunking, with comparable or better retrieval performance.
  - Key technique: Decouple text extraction from semantic chunk planning using ID-addressable units; LLM is used for *grouping decisions only*, not content generation — eliminating a major hallucination source in agentic chunking pipelines.
  - Reported results: Comparable or better retrieval performance vs traditional chunking; order-of-magnitude LLM cost reduction.
  - Delta from current approach: Current pipeline is pdftotext → document_chunker (non-LLM). W-RAC is relevant if we ever add LLM-guided chunking for hard cases (scanned PDFs, complex layouts). Candidate benchmark: compare W-RAC vs current chunker on opendataloader-bench NID/TEDS/MHS metrics when we build that evaluation harness.

### Next Actions

- [ ] If/when LLM-based chunking is proposed for difficult document classes: evaluate W-RAC's ID-addressable-unit pattern as the preferred design
- [ ] Cite as prior art in Phase 2 (hybrid routing) design if cost becomes a bottleneck

## Research Intake Update — 2026-04-23

### New Related Research

- **[intake-449] "OpenAI Privacy Filter: PII Token-Classifier (1.5B MoE / 50M active, Apache 2.0)"** (huggingface.co/openai/privacy-filter)
  - Relevance: **adjacent, not identical, to the remaining document-body safety policy** — the OpenAI privacy filter is a PII detector, not a prompt-injection detector. But it is in the same architectural slot (a small preprocessing classifier that runs on extracted text before it reaches the LLM context), so it's worth tagging as a candidate plug-in for any future pipeline step that needs to mask sensitive spans before downstream-LLM ingestion.
  - Key technique: bidirectional token classifier (AR-pretrained, converted to encoder), 1.5B total / 50M active sparse-MoE (128 experts top-4), banded attention (band=128, effective 257-token window) at 128k context, BIOES span decoding over 8 PII classes. Apache 2.0.
  - Reported results: no quantitative numbers disclosed in the model card at fetch time (2026-04-23). Self-identified failure modes: non-English degradation, uncommon names / regional conventions, span fragmentation, novel credentials. 1,888 downloads/month on HF.
  - Delta from current approach: this pipeline does not currently have a PII-masking step. If/when a step is added (either for KB ingestion or if the orchestrator ever handles third-party user data), this is the default Apache-2.0 option to evaluate. Does not address the remaining document-body prompt-injection policy, which is separate from the 2026-06-21 ODL structured-metadata scanner integration.
  - Action: **track only**. Do not add a privacy step to Phase 1 or Phase 2 of this pipeline unless a concrete requirement surfaces.

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-452] "OpenAI Privacy Parser — inverse of OpenAI Privacy Filter (returns PII spans instead of masking)"** (`github.com/chiefautism/privacy-parser`)
  - Relevance: lightweight Apache-2.0 Python wrapper over the exact intake-449 opf 1.5B weights — returns structured character spans instead of `<REDACTED>` masks. Three backends: pure-regex (1.000 F1 on fixture, µs), model-only (0.733 F1, ~500 ms CPU), and HybridPIIParser (model + span-merge + regex backstop, **0.929 F1, ~600 ms CPU**).
  - Key technique: BIOES + tuned Viterbi over opf logits → char spans → span-merge → regex backstop for URL/secret/account_number. The model+regex hybrid pattern is the non-trivial engineering contribution beyond intake-449.
  - Delta from current approach: this pipeline's remaining document-body PII/injection policy is still separate from pre-commit hygiene and from the 2026-06-21 ODL structured-metadata scanner integration. If a PII step is ever added, `HybridPIIParser` is a drop-in — avoids re-wrapping the raw opf weights ourselves. ~600 ms CPU latency is acceptable for offline/batch KB ingestion but would dominate per-request orchestrator latency.
  - Action: **track only** — consistent with the intake-449 action above. No pipeline change. Bookmark for the offline/batch slot when a concrete requirement surfaces. Does not address primary document-body prompt-injection handling.

## Research Intake Update — 2026-05-20

### New Related Research

- **[intake-579] "Adaptive Chunking: Optimizing Chunking-Method Selection for RAG"** (arxiv:2603.25333, Ekimetrics, LREC 2026)
  - **Relevance**: Directly applicable to Phase 2 ("Replace `document_chunker.py`: use heading hierarchy from ODL instead of regex splitting") AND to Phase 3 benchmark-suite work. Proposes per-document chunker selection driven by 5 intrinsic, document-only metrics — References Completeness (RC), Intrachunk Cohesion (ICC), Document Contextual Coherence (DCC), Block Integrity (BI), Size Compliance (SC) — with no downstream RAG ground truth required for scoring.
  - **Key technique**: 5-metric intrinsic scoring drives per-document method selection across {recursive s=600, recursive s=1100, page-based, LLM-regex}. Selection happens at chunker-output time; the framework is chunker-agnostic, so additional candidates (heading-driven from ODL JSON, structural with table-aware refinement, etc.) can be slotted in.
  - **Reported results**: Retrieval Completeness 67.7 (adaptive) vs 58.1 (LangChain recursive) vs 59.1 (page); Answer Correctness 78.0 vs 70.1 vs 73.3; +30% questions resolved (65 vs 49). Corpus: 33 documents / 3 domains (technical, legal, sustainability reporting) / ~1.18M tokens (CLAIR corpus). Mean intrinsic score 91.07% adaptive vs 89.80% LLM-regex vs 88.62% recursive (s=1100).
  - **Delta from current approach**: Phase 2 currently scopes a single chunker (heading-driven from ODL JSON). Ekimetrics argues for per-document selection across a chunker zoo — a meaningful architectural shift if adopted. The 5-metric scoring is independently a candidate quality gate for opendataloader-bench (Phase 3) alongside NID/TEDS/MHS.
  - **Tier 2b risk — DO NOT adopt before resolving**: intake-581 (HOPE, SIGIR 2025) empirically falsifies the cohesion-as-quality premise behind Ekimetrics' ICC and BI metrics, finding instead that semantic INDEPENDENCE between passages is the load-bearing retrieval-quality signal (+56.2% factual correctness when enforced). Two intrinsic-eval frameworks now exist with contradictory load-bearing signals. A side-by-side measurement on a sample of our corpus is required before we commit either set to Phase 2 chunker quality criteria. Secondary risks: 33-doc corpus is small; only 4 baselines (no MarkdownHeaderTextSplitter, no W-RAC, no Meta-Chunking); FMRE metric pulls `maverick-coref` (CC BY-NC-SA 4.0).
  - **Sibling**: intake-436 (W-RAC) attacks cost via decoupled LLM grouping; intake-579 attacks quality via method-selection. Complementary levers in the same problem space.

- **[intake-580] "ekimetrics/adaptive-chunking" — Official MIT-licensed implementation** (`github.com/ekimetrics/adaptive-chunking`, 67 stars, 3 forks at intake)
  - **Relevance**: Modular Python 3.11+ implementation of intake-579. Each chunker is an independent module behind a small ABC, so our ODL-heading chunker (or current `document_chunker.py`) can be slotted in as an additional candidate and scored by the same harness. Core dependencies minimal; PDF backends are Docling (default open-source), PyMuPDF, Azure Document Intelligence. Resumable metrics computation (skip already-computed documents on rerun) makes large-corpus evaluation interruptible.
  - **License caveat**: Core MIT, but FMRE metric requires `maverick-coref` (CC BY-NC-SA 4.0). Lifting the full 5-metric suite needs license clearance OR a coref-free reimplementation of RC.
  - **Action**: candidate eval scaffold for Phase 3 benchmark integration — NOT a runtime dependency for Phase 1/2.

- **[intake-581] "A New HOPE: Domain-agnostic Automatic Evaluation of Text Chunking"** (arxiv:2505.02171, Brådland/Goodwin/Andersen/Nossum/Gupta, SIGIR 2025)
  - **Relevance**: Direct alternative to intake-579 with empirically contradictory load-bearing signal. Proposes HOPE (Holistic Passage Evaluation) at three levels — intrinsic + extrinsic (inter-passage) + passages-document coherence — evaluated across 7 domains and reporting significant correlation with downstream RAG quality. Empirically finds intrachunk concept unity has **minimal impact** on retrieval; inter-passage SEMANTIC INDEPENDENCE is the load-bearing property (+56.2% factual correctness, +21.1% answer correctness when enforced).
  - **Delta from current approach**: The heading-driven Phase 2 chunker naturally produces more-independent chunks (boundaries at structural breakpoints), which HOPE CORROBORATES while Ekimetrics ICC would PENALIZE for low intrachunk cohesion. The architectural choice in Phase 2 is currently un-defended in the handoff; HOPE provides empirical support.
  - **Discovered via**: Tier 2b contradicting-evidence search on intake-579 — `expanded_from: intake-579`.

### Next Actions

- [ ] When Phase 2 deeper integration begins (replace regex chunker with ODL heading hierarchy), instrument chunker output with BOTH Ekimetrics 5-metric scoring AND HOPE three-level scoring on a 10-document fixture slice. Capture downstream answer-correctness from a small RAG eval on the same slice. Let the data settle which metric set correlates with downstream quality on our actual workload before committing to either as a quality gate.
- [ ] During Phase 3 benchmark integration (opendataloader-bench): consider adding intrinsic chunk-quality scores alongside NID/TEDS/MHS. Re-use the Ekimetrics MIT scaffold (modulo coref-dependent FMRE) — it is the cheapest way to get an instrumented harness.
- [ ] If/when LLM-guided chunking is proposed for hard document classes (cross-link intake-436 W-RAC trigger), evaluate the three frameworks side-by-side rather than picking one upfront. Cross-link: `internal-kb-rag.md` 2026-05-20 update — same evaluation question applies to K2 markdown chunker quality.

## Research Intake Update — 2026-05-29

### New Related Research

> **Deep dive 2026-05-29** → `research/deep-dives/liteparse-document-parser-deep-dive.md`. Verdicts held (647 adopt_component, 646 worth_investigating); credibility re-scored (647 null→4: real 3-OS CI + HF regression + LLM-judge eval; 646 null→2: speed-only empirical claim). Scope sharpened to **complement, not replacement** — see deps + structure-gap notes below.

- **[intake-647] "LiteParse" — run-llama (LlamaIndex) Rust document parser** (`github.com/run-llama/liteparse`, Apache-2.0, **6.8k stars / 425 forks / 600 commits / 46 releases**, v2.0.3 @ 2026-05-28, 3-OS CI + HF regression suite)
  - **Relevance**: Direct **adopt_component** as the **born-digital fast-path** text+bbox+screenshot backend (competes with `pdftotext` for the Phase 1 slot) — **NOT an ODL structural replacement**. Pure-Rust core (PDFium + Tesseract OCR, pluggable EasyOCR/PaddleOCR HTTP backends) with native PyO3 / napi-rs / WASM bindings. Fully local, no cloud/API key, no LLM. Crucially **JVM-free**.
  - **Dependency footprint (deep-dive correction)**: the custom PDFium fork + `tesseract-rs` are **compiled into the prebuilt manylinux x86_64 wheel (glibc 2.28+, 11–13 MB, Py 3.10–3.15)** — on EPYC, `pip install liteparse` is self-contained: **no JVM, no system PDFium/tesseract build**. LibreOffice (Office→PDF) + ImageMagick (image→PDF) + tessdata are conditional and untouched on the born-digital path. This is the concrete "runs everywhere" win over ODL's Java 11+ per-`convert()` JVM spawn.
  - **Structure gap (why it is NOT a replacement)**: LiteParse emits text + per-item bboxes (viewport 72-DPI `x/y/w/h`, top-left — needs an adapter to ODL's PDF-point corner-pairs) + page PNGs, with **reading order implicit** and **NO semantic structure** — no heading-hierarchy object, no table DOM (tables = positioned ASCII-grid text), no figure semantic-type. It therefore cannot supply Phase 2's "biggest win" (headings → chunker, table DOM, figure semantic-type + caption → VL); ODL stays for those.
  - **Key technique**: spatial-grid text projection for reading-order/layout preservation — keeps tables as *positioned text* rather than markdownifying them (a different design point from ODL's structure-to-markdown).
  - **Delta from current approach**: a candidate JVM-free backend for `pdf_router.py` born-digital path, slottable behind the same ABC as the ODL/pdftotext backends. Not a drop-in for complex/dense-table/scanned docs (see Tier 2b risk).
- **[intake-646] "Up to 100x Fast Parsing with LiteParse v2.0 and Rust"** (LlamaIndex blog, Logan Markewich)
  - **Reported results (VENDOR, unverified)**: 5–100× speedup on small docs / ~3× on large docs vs prior Node version; 457-page / 100 MB PDF parsed in 0.777 s. No parsing-accuracy/quality benchmark (no NID/TEDS/MHS) — speed-only marketing numbers.
  - **Tier 2b contradicting evidence — DO NOT adopt blind**: LlamaIndex's own docs state that for **complex documents (dense tables, multi-column, charts, handwritten, scanned PDFs) LlamaParse cloud is significantly better** — LiteParse is scoped to *fast, local, born-digital text* (real-time apps, coding agents). Additionally, LiteParse's **non-markdown, layout-preserving output fails standard OCR benchmarks (e.g. OlmOCR)** by construction — "not incorrect, but fails the benchmark format." So head-to-head NID/TEDS scoring vs ODL needs a LiteParse-aware harness, not off-the-shelf OCR-benchmark scoring.
  - **Sibling**: intake-161 (OpenDataLoader) — the incumbent in this handoff; LiteParse is the JVM-free, spatial-grid-projection contender.

### Next Actions

- [ ] Bench **LiteParse-local vs OpenDataLoader-local vs pdftotext** on the orchestrator born-digital test corpus: reading order, table fidelity, speed, **JVM-free deploy footprint**. Use a LiteParse-output-aware quality harness (its non-markdown layout output breaks naive OlmOCR/TEDS scoring — confirmed in intake-646 Tier 2b). Decide adopt_component vs ODL-only for the fast path. 2026-07-04 status: runnable harness + small born-digital evidence exist; table-fidelity/structural corpus evidence remains open.
- [ ] Route complex/dense-table/scanned docs **away** from LiteParse (vendor docs concede LlamaParse-cloud-class quality is needed there; our equivalent is the ODL + VL-OCR path) — LiteParse is a born-digital fast-path backend only.

### Fast-Path Evidence Checkpoint — 2026-07-03

- Added `epyc-orchestrator/scripts/benchmark/pdf_fastpath_probe.py`, a no-inference harness for comparing `pdftotext`, `opendataloader`, `opendataloader_structured`, and `liteparse` on local PDF files. The script records latency, text hashes, quality heuristics, table-like line counts, ODL structured object counts, and LiteParse bbox/page-image counts when available; missing packages are explicit `missing_dependency` records rather than silent empty outputs.
- Added focused coverage in `tests/unit/test_pdf_fastpath_probe.py`. Validation passed together with the existing PDF router slice: `uv run pytest -q tests/unit/test_pdf_fastpath_probe.py tests/unit/test_pdf_router.py` (`33 passed, 2 skipped` after the ODL markdown-output regression), focused Ruff, py_compile, and diff-check.
- Installed `poppler-utils` and `openjdk-17-jre-headless` in the devcontainer so the incumbent `pdftotext` and ODL local paths can actually run. No repo devcontainer files were changed.
- Initial smoke artifact: `epyc-orchestrator/orchestration/reports/pdf_fastpath_probe_20260703T183037Z/summary.{json,md}`. On `/mnt/raid0/llm/llama.cpp/docs/development/llama-star/idea-arch.pdf`, `pdftotext` succeeded with median latency `8.864 ms`, quality heuristic `0.822`, and `1801` extracted chars; the candidate Python packages were absent.
- Transient-dependency smoke artifact: `epyc-orchestrator/orchestration/reports/pdf_fastpath_probe_20260703T183917Z/summary.{json,md}` using `uv run --with opendataloader-pdf --with liteparse`. On the same sample, all four backends succeeded: `pdftotext` `9.769 ms` / quality `0.822` / `1801` chars; `opendataloader` `238.128 ms` / quality `0.987` / `953` chars; `opendataloader_structured` `303.437 ms` / quality `0.987` / `953` chars; `liteparse` `11.070 ms` / quality `0.935` / `1963` chars.
- The all-backend smoke exposed and fixed a local ODL markdown bug: `PDFRouter._extract_with_opendataloader()` now runs ODL in a temp output directory and reads `<stem>.md`, instead of letting this SDK version write a sibling Markdown file beside the source PDF and return empty text. Regression coverage asserts the source directory stays clean.
- Multi-PDF smoke artifact: `epyc-orchestrator/orchestration/reports/pdf_fastpath_probe_20260703T184840Z_multi/summary.{json,md}`. On three local born-digital PDFs (`2`, `15`, and `13` pages), all `12/12` backend attempts succeeded. Median latency / quality: `pdftotext` `36.299 ms` / `0.917`; `liteparse` `34.757 ms` / `0.972`; `opendataloader` `1083.843 ms` / `1.000`; `opendataloader_structured` `1122.449 ms` / `1.000`. Structured ODL emitted no heading/table/figure objects on this small sample set, so this still does not prove structural advantage.
- Gate status: still open. The next evidence step is a representative born-digital corpus with structural/table-heavy PDFs before touching `src/services/pdf_router.py` policy. LiteParse looks like a plausible pdftotext-class fast-path candidate; ODL local looks better as a structured/complex-document path unless a sidecar removes JVM startup cost. The 2026-07-04 structural-metadata rerun makes the current 8-PDF corpus explicitly insufficient for table/heading policy decisions.

## Research Intake Update — 2026-06-12

### New Related Research (deep-dived, from the intake-694 open-weights roundup)
- **PaddleOCR-VL-1.6** (2026-06, Apache-2.0 — distinct from the pluggable PaddleOCR HTTP *engine*): a 1B-param VLM document parser (ERNIE-4.5-0.3B backbone), **OmniDocBench v1.6 overall 96.33 (SOTA: text / formula / tables / layout, + Real5 SOTA)**. Official **GGUF + mmproj** (`PaddlePaddle/PaddleOCR-VL-1.6-GGUF`), llama-mtmd CPU path — so it's runnable on our stack. Unlike the PaddleOCR engine (Phase-1 fast-path slot), this is a full VLM parser overlapping the **LightOnOCR slow-path + ODL structural extraction**. **Action (eval-gated):** bench PaddleOCR-VL-1.6 vs LightOnOCR on the doc test corpus for structured layout/table/formula extraction. **P1 follow-up — warrants its own intake entry.** See `research/deep-dives/2026-06-12-open-weights-roundup-followups.md`.

## Research Intake Update — 2026-06-20

### neural-txt — conditional cheap-specialist watch-item (intake-718)

- neural-txt (AVB) is a CPU-cheap 135M task-specialist + constrained-decoding (Outlines) harness for structured NLP (bullets / Q&A pairs / KG triplets). CONDITIONAL watch-item: there is NO live consumer slot today (`document_formalizer` is a 1B OCR VLM; this pipeline has no cheap text-extraction stage). Re-surface ONLY if this pipeline grows a structured-NLP-extraction stage.
- Its reward-model reranking half (NeuralTxtReward / neuraltxt-reward-tiny) is folded into intake-719 / the AVB offline-reward digest — not duplicated here.
- No benchmarks (educational repo, observations).
