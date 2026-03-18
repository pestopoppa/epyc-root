# OpenDataLoader PDF — Pipeline Integration

**Status**: ACTIVE
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
5. **No prompt injection filtering**: extracted text passed raw to LLM context

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

- [ ] Parse ODL JSON output: extract figure bboxes + semantic types + captions
- [ ] Feed figure context to `figure_analyzer.py`: type, caption, surrounding text, heading position
- [ ] Replace PyMuPDF figure extraction with ODL bboxes (skip `_extract_figures_pymupdf`)
- [ ] Improve `document_chunker.py`: use heading hierarchy from ODL instead of regex splitting
- [ ] Route detected tables to ODL hybrid for 0.93 accuracy extraction
- [ ] Add prompt injection filtering from ODL safety layer

**Key files**:
- `src/services/figure_analyzer.py` — enrich VL prompts with document context
- `src/services/document_chunker.py` — structural splitting from JSON headings
- `src/services/document_preprocessor.py` — orchestrate structured context flow

### Phase 3: Hybrid Mode + Benchmark Integration

**Goal**: Best-in-class table extraction + reproducible comparison with competition
**Effort**: Medium-Large

- [ ] Deploy `opendataloader-pdf-hybrid --port 5002` as sidecar service
- [ ] Experiment: swap hybrid backend from docling-fast → LightOnOCR-2-1B (port 8082)
- [ ] Measure: does GPU-accelerated LightOnOCR beat docling-fast's 0.43s/page?
- [ ] Implement three-way routing: ODL local (simple) → ODL hybrid (tables) → LightOnOCR (scanned)
- [ ] Clone opendataloader-bench, add our pipeline as custom engine
- [ ] Run comparison on 200 PDFs: our pipeline vs ODL local vs ODL hybrid vs docling vs marker
- [ ] Publish results in progress log

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
- [ ] Add `document_extraction` suite to `epyc-inference-research/scripts/benchmark/question_pool.py`
- [ ] Adapt ground truth format (Markdown references → our scoring contract)
- [ ] Scoring methods: NID (reading order), TEDS (table DOM), MHS (heading hierarchy)
- [ ] Register as suite in benchmark infrastructure for reproducible comparisons
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
