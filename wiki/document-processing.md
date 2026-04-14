# Document Processing

**Category**: `document_processing`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 4 documents

## Summary

Document processing in the EPYC orchestrator currently uses a binary routing pipeline: born-digital PDFs go through `pdftotext -layout` (fast, ~100ms/page, no structure) while scanned/image PDFs route to LightOnOCR-2-1B (slow, ~1-3s/page on GPU, high accuracy). This pipeline has four critical gaps: no table extraction (pdftotext mangles tables), no reading order for multi-column documents, no per-page complexity routing, and blind figure analysis where VL models receive cropped images without document context (caption, surrounding text, semantic type).

OpenDataLoader PDF (intake-161, Apache 2.0) has been evaluated as a comprehensive upgrade. Its local mode uses the XY-Cut++ algorithm (rule-based, no ML) at 0.05s/page -- essentially free and comparable to pdftotext latency. It provides structured JSON output with semantic types (heading, paragraph, table, list, image, caption, formula), bounding boxes, heading hierarchy, and correct reading order (0.91 NID score). The hybrid mode routes complex pages to an AI backend (docling-fast, SmolVLM 256M) achieving 0.90 overall accuracy and 0.93 table accuracy at 0.43s/page, placing first among all evaluated engines above docling (0.86), marker (0.83), and pymupdf4llm (0.57).

A three-phase integration plan has been designed and is actively tracked. Phase 1 replaces pdftotext with OpenDataLoader local mode in `pdf_router.py` -- same latency, better reading order, structured output. Phase 2 (the biggest win) enriches downstream models with structural context: VL models would receive figure semantic type, caption, surrounding text, and heading position instead of cold cropped images. The document chunker would use heading hierarchy from JSON instead of regex splitting. Phase 3 deploys the hybrid mode as a sidecar service and integrates the opendataloader-bench 200-PDF dataset for reproducible quality comparison.

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

## Actionable for EPYC

- **Phase 1 (small effort, immediate gains)**: Replace `pdftotext -layout` with `opendataloader_pdf.convert(format="markdown,json")` in `src/services/pdf_router.py`. Keep quality check logic on ODL output. Requires `pip install opendataloader-pdf` and Java 11+.
- **Phase 2 (medium effort, biggest win)**: Enrich VL model prompts with figure semantic type, caption, surrounding text, and heading position from ODL JSON. Replace PyMuPDF figure extraction with ODL bboxes. Improve document_chunker to use heading hierarchy instead of regex. Route detected tables to ODL hybrid for 0.93 accuracy.
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
