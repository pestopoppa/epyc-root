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
  - Relevance: **adjacent, not identical, to gap #5** ("No prompt injection filtering") — the OpenAI privacy filter is a PII detector, not a prompt-injection detector. But it is in the same architectural slot (a small preprocessing classifier that runs on extracted text before it reaches the LLM context), so it's worth tagging as a candidate plug-in for any future pipeline step that needs to mask sensitive spans before downstream-LLM ingestion.
  - Key technique: bidirectional token classifier (AR-pretrained, converted to encoder), 1.5B total / 50M active sparse-MoE (128 experts top-4), banded attention (band=128, effective 257-token window) at 128k context, BIOES span decoding over 8 PII classes. Apache 2.0.
  - Reported results: no quantitative numbers disclosed in the model card at fetch time (2026-04-23). Self-identified failure modes: non-English degradation, uncommon names / regional conventions, span fragmentation, novel credentials. 1,888 downloads/month on HF.
  - Delta from current approach: this pipeline does not currently have a PII-masking step. If/when a step is added (either for KB ingestion or if the orchestrator ever handles third-party user data), this is the default Apache-2.0 option to evaluate. Does not address gap #5 (prompt injection) — that remains an open requirement.
  - Action: **track only**. Do not add a privacy step to Phase 1 or Phase 2 of this pipeline unless a concrete requirement surfaces.
