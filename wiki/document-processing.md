# Document Processing

**Category**: `document_processing`
**Confidence**: verified
**Last compiled**: 2026-06-21
**Sources**: 4 documents

## Summary

Document processing in the EPYC orchestrator currently uses a binary routing pipeline by default: born-digital PDFs go through `pdftotext -layout` (fast, ~100ms/page, no structure) while scanned/image PDFs route to LightOnOCR-2-1B (slow, ~1-3s/page on GPU, high accuracy). The gated OpenDataLoader path now supplies structured headings, figure context, figure bboxes, table metadata, scanner-gated structured metadata, a default-inert table-backend seam, and default-off primary body injection warnings to downstream preprocessing. Remaining critical gaps are the real ODL hybrid table sidecar/client, per-page complexity routing, and LiteParse born-digital evidence.

OpenDataLoader PDF (intake-161, Apache 2.0) has been evaluated as a comprehensive upgrade. Its local mode uses the XY-Cut++ algorithm (rule-based, no ML) at 0.05s/page -- essentially free and comparable to pdftotext latency. It provides structured JSON output with semantic types (heading, paragraph, table, list, image, caption, formula), bounding boxes, heading hierarchy, and correct reading order (0.91 NID score). The hybrid mode routes complex pages to an AI backend (docling-fast, SmolVLM 256M) achieving 0.90 overall accuracy and 0.93 table accuracy at 0.43s/page, placing first among all evaluated engines above docling (0.86), marker (0.83), and pymupdf4llm (0.57).

A three-phase integration plan has been designed and is actively tracked. Phase 1 replaces pdftotext with OpenDataLoader local mode in `pdf_router.py` -- same latency, better reading order, structured output. Phase 2 (the biggest win) now has its main consumer path wired: ODL headings can drive chunking, ODL figure bboxes replace PyMuPDF image enumeration in structured mode, ODL figure context can enrich VL prompts, ODL tables flow through preprocessing/cache/TaskIR output as first-class table records, and `ORCHESTRATOR_ODL_TABLE_BACKEND` provides the local-vs-future-hybrid routing seam. When `INJECTION_SCANNING` is enabled, unsafe ODL structured headings/captions/tables suppress that additive metadata before it reaches chunking or VL prompts; `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY=warn` separately scans primary OCR/body pages and emits warnings without mutating source text. Phase 3 deploys the hybrid mode as a sidecar service and integrates the opendataloader-bench 200-PDF dataset for reproducible quality comparison.

The Java 11+ runtime dependency is manageable through a sidecar pattern. The Python SDK wraps a Java CLI where each `convert()` call spawns a JVM, so batch processing or persistent subprocess warming is recommended for production. The structured JSON output improves every downstream consumer: chunker, figure analyzer, LLM context quality.

## Key Findings

- Current pipeline has NO table extraction -- pdftotext mangles tables, LightOnOCR outputs bboxes but no structured table data [opendataloader-pdf-pipeline-integration.md]
- OpenDataLoader local mode matches pdftotext latency (0.05s/page) while providing reading order (0.91), heading hierarchy, table detection, and figure bboxes [opendataloader-pdf-pipeline-integration.md]
- ODL hybrid achieves 0.90 overall / 0.93 table accuracy, #1 among all evaluated engines [opendataloader-pdf-pipeline-integration.md]
- XY-Cut++ algorithm: recursive segmentation extended with pre-mask processing, multi-granularity segmentation, hierarchical mask mechanism, cross-modal matching. 98.8 BLEU on DocBench-100 [arXiv:2504.10258]
- VL figure analysis is currently blind -- models receive cropped images without document context. This is the single highest-value improvement from ODL integration [opendataloader-pipeline-integration.md]
- ODL local mode is rule-based (XY-Cut++), not ML -- no GPU needed, deterministic output, no weights to convert [opendataloader-pdf-pipeline-integration.md]
- Safety features include hidden text filtering, off-page content removal, and optional PII sanitization [opendataloader-pdf-pipeline-integration.md]
- Java SDK spawns JVM per convert() call -- sidecar pattern or persistent subprocess recommended [opendataloader-pipeline-integration.md]
- The 200-PDF opendataloader-bench dataset (MIT license) could be added to EPYC benchmark infrastructure for reproducible comparisons [opendataloader-pipeline-integration.md]
- neural-txt (intake-718) is a CPU-cheap 135M task-specialist + Outlines constrained-decoding harness for structured NLP (bullets / Q&A pairs / KG triplets) — but it is a CONDITIONAL watch-item with NO live consumer slot: `document_formalizer` is a 1B OCR VLM and the ODL pipeline has no cheap structured-NLP-extraction stage today. Re-surface only if such a stage appears. Educational repo, no benchmarks (observations) [opendataloader-pipeline-integration.md, intake-718]

## Actionable for EPYC

- **Phase 1 (small effort, immediate gains)**: Replace `pdftotext -layout` with `opendataloader_pdf.convert(format="markdown,json")` in `src/services/pdf_router.py`. Keep quality check logic on ODL output. Requires `pip install opendataloader-pdf` and Java 11+.
- **Phase 2 (medium effort, biggest win)**: The gated structured consumer path is wired: enrich VL model prompts with figure semantic type, caption, surrounding text, and heading position from ODL JSON; replace PyMuPDF figure extraction with ODL bboxes; use heading hierarchy instead of regex when present; carry ODL table metadata through preprocessing/cache/TaskIR output; suppress unsafe ODL structured metadata under `INJECTION_SCANNING`; expose a default-inert `ORCHESTRATOR_ODL_TABLE_BACKEND` seam; and expose default-off body warnings through `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY=warn`. Remaining work: implement the real ODL hybrid table sidecar/client path for 0.93 accuracy.
- **Phase 3 (medium-large effort)**: Deploy `opendataloader-pdf-hybrid --port 5002` as sidecar. Experiment with swapping hybrid backend to LightOnOCR-2-1B (already running). Implement three-way routing: ODL local (simple) -> ODL hybrid (tables) -> LightOnOCR (scanned). Clone opendataloader-bench, add EPYC pipeline as custom engine, run 200-PDF comparison.
- **Benchmark integration**: Add `document_extraction` suite to `epyc-inference-research/scripts/benchmark/question_pool.py` using opendataloader-bench 200-PDF dataset. Scoring: NID (reading order), TEDS (table DOM), MHS (heading hierarchy).
- **JVM management**: Pre-warm JVM in persistent subprocess or run ODL as sidecar service on dedicated port.

## Open Questions

- JVM cold start cost -- can we pre-warm via persistent subprocess and what is the startup latency?
- Does the Python SDK support single-page processing, or only whole documents?
- Is the JSON output schema versioned and stable across ODL releases?
- Can LightOnOCR-2-1B serve as the ODL hybrid backend (replacing docling-fast) and would GPU-accelerated OCR beat 0.43s/page?
- What is JVM heap usage for large documents (100+ pages)?
- How does SmolVLM 256M (in ODL hybrid) compare to our Qwen2.5-VL-7B for chart/image description?

## Related Categories

- [Multimodal](multimodal.md) -- Vision pipeline benefits from structured document context; figure analysis is a shared concern
- [Search & Retrieval](search-retrieval.md) -- Better document parsing improves downstream retrieval quality
- [Tool Implementation](tool-implementation.md) -- PDF router is a core orchestrator service

## Source References

- [OpenDataLoader deep dive](/workspace/research/deep-dives/opendataloader-pdf-pipeline-integration.md) -- XY-Cut++ algorithm, benchmark results, four integration strategies, technical considerations
- [OpenDataLoader pipeline integration handoff](/workspace/handoffs/active/opendataloader-pipeline-integration.md) -- Three-phase plan, work items, benchmark suite integration
- [intake-161](https://github.com/opendataloader-project/opendataloader-pdf) OpenDataLoader PDF -- Initial intake evaluation
- [arXiv:2504.10258] XY-Cut++ paper -- Algorithm details, DocBench-100 results
- [intake-718](https://github.com/avbiswas/neural-txt) neural-txt (AVB) -- 135M structured-NLP specialist + Outlines constrained decoding; conditional watch-item, no consumer slot, no benchmarks

## ODL structured-output Phase 2 scaffolding (2026-05-06)

Phase 1 of the ODL integration (markdown-only extraction via `_extract_with_opendataloader()`) landed via NIB2-13. Phase 2 — wiring ODL's structured JSON output into figure-analyzer + chunker — landed 2026-05-06 as additive scaffolding, then gained end-to-end producer/consumer follow-ups on 2026-06-21. Existing pdftotext/PyMuPDF/regex-chunker paths are unchanged when `ORCHESTRATOR_ODL_STRUCTURED` is unset.

New module `epyc-orchestrator/src/models/odl_structured.py` defines a normalized layer over ODL JSON: `ODLBoundingBox`, `HeadingNode` (with `build_heading_tree` + `flatten_heading_tree` walkers), `FigureContext` (bbox + semantic_type + caption + surrounding_text + heading_breadcrumb), `TableContext`, and `ODLStructuredDocument.from_json()` that tolerates partial/missing keys across ODL versions.

`pdf_router.py` gains `_extract_with_opendataloader_structured()` — invokes ODL with `format=["markdown","json"]` into a temp dir, parses both outputs, returns `(text, ODLStructuredDocument | None, latency_ms)`. `PDFExtractionResult` gains an optional `structured_data` field (default `None` preserves back-compat). The routing path adds an `ORCHESTRATOR_ODL_STRUCTURED=1` gate that opts into the structured path; falls through to pdftotext on empty ODL output. As of `epyc-orchestrator` `fa1b5460`, `PDFRouter.extract_opendataloader_structured()` also owns the table-backend selection seam. `ORCHESTRATOR_ODL_TABLE_BACKEND=hybrid` is accepted as an explicit future request but falls back to local structured ODL until a sidecar/client exists.

`figure_analyzer.py` gains additive helper `build_figure_prompt_with_context(base_prompt, figure_context)` that folds heading breadcrumb + semantic_type + caption + surrounding_text into the VL prompt when a `FigureContext` is supplied; returns base prompt unchanged when `None`. Existing `FigureAnalyzer` class untouched.

`document_chunker.py` gains additive helper `chunk_by_odl_headings(text, structured_doc, max_section_length=10000)` that slices markdown text at ODL-detected heading boundaries instead of regex matches, with paragraph-boundary sub-split for long sections and a single-section fallback when the structured doc has no headings.

`document_preprocessor.py` now consumes optional structured metadata from TaskIR or local ODL PDF extraction. It passes safe structured headings into chunking, forwards figure contexts into VL analysis, emits table summaries into enriched TaskIR, and suppresses unsafe ODL structured headings/figures/tables when `INJECTION_SCANNING` is enabled. The structured-metadata suppression remains separate from primary OCR text. Primary body text defaults to source behavior, while `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY=warn` adds page-level injection warnings without mutating or blocking extracted body content.

Sources: [`handoffs/active/opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md), `epyc-orchestrator/src/models/odl_structured.py`, `epyc-orchestrator/src/services/pdf_router.py`, `epyc-orchestrator/src/services/document_preprocessor.py`, `epyc-orchestrator/tests/unit/test_odl_structured.py`.

## LiteParse — JVM-free born-digital fast-path candidate (2026-05-29)

LiteParse (run-llama/LlamaIndex, Apache-2.0, intake-646 blog / intake-647 repo) is a pure-Rust document parser that occupies a **different design point** from OpenDataLoader and is a *complement, not a replacement*. Deep dive: [`research/deep-dives/liteparse-document-parser-deep-dive.md`](../research/deep-dives/liteparse-document-parser-deep-dive.md).

- **Deployment win vs ODL**: the custom PDFium fork + tesseract-rs are compiled into a self-contained ~13 MB manylinux x86_64 wheel (glibc 2.28+, Py 3.10–3.15). On EPYC, `pip install liteparse` needs **no JVM and no system PDFium/tesseract build** — sidestepping ODL's Java 11+ per-`convert()` JVM-spawn cold-start. LibreOffice (Office→PDF) + ImageMagick (image→PDF) + tessdata are conditional and untouched on the born-digital path.
- **Algorithm**: spatial-grid projection ("preserve layout, don't detect structure") — tables emitted as positioned ASCII-grid text, NOT a markdown table DOM. Output = text + per-item bboxes (viewport 72-DPI `x/y/w/h`, top-left — needs an adapter vs ODL's PDF-point corner-pairs) + page PNGs. **Reading order is implicit; no heading-hierarchy, table, or figure-semantic-type objects.**
- **Why it is NOT an ODL replacement**: it cannot supply Phase 2's structural context (headings → chunker, table DOM, figure semantic-type + caption → VL). It competes with `pdftotext` for the Phase 1 born-digital slot only; ODL stays for structure. Vendor concedes complex/dense-table/scanned/multi-column docs need LlamaParse-cloud-class quality (our equivalent = ODL + VL-OCR).
- **Maturity / credibility**: 6.8k★ / 425 forks / 600 commits / 46 releases, v2.0.3 @ 2026-05-28; real 3-OS CI + HF regression suite + LLM-judge eval framework. Speed claims (457pg/100 MB in 0.777 s; 5–100× small / ~3× large vs the prior Node version) are vendor self-reported and **speed-only — no independent accuracy benchmark** (NID/TEDS/OmniDocBench); its non-markdown output fails standard OCR benchmarks by construction, so a LiteParse-output-aware harness is required for head-to-head scoring.
- **Gated next action**: bench LiteParse-local vs ODL-local vs pdftotext on the born-digital corpus (text fidelity, JVM-free cold-start + RSS, multi-column reading order) under the opendataloader-pipeline-integration handoff (P1b). Verdict: 647 = adopt_component (born-digital fast-path backend), 646 = worth_investigating.

Sources: [`research/deep-dives/liteparse-document-parser-deep-dive.md`](../research/deep-dives/liteparse-document-parser-deep-dive.md), [`handoffs/active/opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md), [`handoffs/active/pipeline-integration-index.md`](../handoffs/active/pipeline-integration-index.md), intake-646/647.

## neural-txt — cheap structured-NLP specialist, no consumer slot yet (2026-06-20)

neural-txt (AVB, intake-718) is a CPU-cheap **135M task-specialist LM paired with an Outlines constrained-decoding harness** for structured NLP extraction — bullet-point summaries, Q&A pairs, and knowledge-graph triplets. It is the closest research candidate to a "cheap structured-extraction stage" the ODL pipeline could theoretically grow, which is why it is tracked here rather than dismissed.

- **Verdict: CONDITIONAL watch-item — NO live consumer slot today.** The ODL/LightOnOCR pipeline has no cheap structured-NLP-extraction stage, and `document_formalizer` is a 1B OCR VLM (a different design point entirely). There is nothing in the current pipeline that would route work to a 135M structured-NLP specialist. Re-surface this entry ONLY if such a stage appears in the pipeline (e.g. a post-OCR triplet/Q&A extraction step feeding a KB or RAG index).
- **Constrained-decoding is the transferable part**: the Outlines-style schema-constrained decoding harness (guarantee well-formed bullets / KG-triplet JSON without post-hoc parsing) is the engineering pattern worth remembering even though the 135M weights themselves have no slot — it is the same reliability lever as the privacy-parser/PII-span work tracked elsewhere in this handoff (intake-449/452), applied to extraction output rather than masking.
- **Confidence: external — educational repo, no benchmarks.** All capability claims are observations (no decision-grade numbers); do not gate any pipeline change on neural-txt figures. Its reward-model reranking half (NeuralTxtReward / neuraltxt-reward-tiny) is folded into intake-719 / the AVB offline-reward digest, not duplicated here.

Sources: [`handoffs/active/opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md) (Research Intake Update 2026-06-20), intake-718.
