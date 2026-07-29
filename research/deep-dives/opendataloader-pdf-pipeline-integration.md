# Deep Dive: OpenDataLoader PDF — Pipeline Integration Assessment

**Date**: 2026-03-17
**Intake ID**: intake-161
**Source**: [opendataloader-project/opendataloader-pdf](https://github.com/opendataloader-project/opendataloader-pdf)
**PyPI**: [opendataloader-pdf 2.0.0](https://pypi.org/project/opendataloader-pdf/) (2026-03-11)
**XY-Cut++ paper**: [arXiv:2504.10258](https://arxiv.org/abs/2504.10258) — Liu et al.

---

## 1. What It Is

Java-based PDF parser (Apache 2.0) with Python/Node.js/Java SDKs. Two modes:

| Mode | How | Accuracy | Speed | GPU |
|------|-----|----------|-------|-----|
| **Local** | Rule-based XY-Cut++ + border/cluster table detection | 0.72 overall, 0.49 table | 0.05 s/page | None |
| **Hybrid** | Local + routes complex pages to AI backend (docling-fast, SmolVLM 256M) | 0.90 overall, 0.93 table | 0.43 s/page | Optional |

Benchmark ([opendataloader-bench](https://github.com/opendataloader-project/opendataloader-bench), 200 PDFs):

| Engine | Overall | Reading Order | Table | Heading | Speed |
|--------|---------|---------------|-------|---------|-------|
| **opendataloader [hybrid]** | **0.90** | **0.94** | **0.93** | **0.83** | 0.43s |
| docling | 0.86 | 0.90 | 0.89 | 0.80 | 0.73s |
| opendataloader (local) | 0.84 | 0.91 | 0.49 | 0.76 | **0.05s** |
| marker | 0.83 | 0.89 | 0.81 | 0.80 | — |
| pymupdf4llm | 0.57 | 0.89 | 0.40 | 0.41 | — |

Metrics: NID (reading order), TEDS (table DOM similarity via APTED), MHS (heading hierarchy).

### XY-Cut++ Algorithm

From [arXiv:2504.10258](https://arxiv.org/abs/2504.10258): Extends classic recursive XY-Cut with:
- **Pre-mask processing** using shallow semantic labels as structural priors
- **Multi-granularity segmentation** for different layout regions
- **Hierarchical mask mechanism** capturing document topology
- **Cross-modal matching** between visual regions and textual semantics
- 98.8 BLEU on DocBench-100, +24% over baselines on complex layouts

### Output Formats

- **JSON**: Semantic types (heading, paragraph, table, list, image, caption, formula), bounding box [left, bottom, right, top] in PDF points per element, page number, font metadata
- **Markdown**: LLM-optimized, with tables as markdown tables
- **HTML**: Web rendering
- **Annotated PDF**: Visual debugging with colored bboxes

### Safety Features

- Filters hidden text (transparent, zero-size fonts)
- Removes off-page content and suspicious invisible layers
- Optional `--sanitize` flag for PII (emails, URLs, phones → placeholders)

---

## 2. Current Orchestrator Pipeline

```
PDF Input
    ↓
[pdftotext probe] → ~100ms, text only, no structure
    ↓
[Quality check] → entropy, garbage ratio, word length
    │
    ├─ PASS (born-digital):
    │   ├─ Text: raw pdftotext output (no reading order, no tables)
    │   └─ Figures: PyMuPDF bbox extraction
    │
    └─ FAIL (scanned/image):
        └─ LightOnOCR-2-1B (text + bboxes, ~1-3s/page on GPU)
            ↓
[document_chunker] → split by markdown headers
    ↓
[figure_analyzer] → route figures to VL model for description
    ↓
[DocumentPreprocessResult] → to orchestrator
```

**Key files** (epyc-orchestrator):
- `src/services/pdf_router.py` — PDFRouter class, quality assessment, pdftotext/LightOnOCR dispatch
- `src/services/document_preprocessor.py` — OCR → chunking → figure analysis pipeline
- `src/services/lightonocr_server.py` — FastAPI wrapper for LightOnOCR-2-1B-bbox
- `src/services/document_chunker.py` — Markdown header-based chunking
- `src/services/figure_analyzer.py` — VL model figure description
- `src/services/document_client.py` — HTTP client for OCR server

### Current Gaps

1. **No table extraction**: pdftotext outputs tables as jumbled text; LightOnOCR outputs bboxes but no structured table data
2. **No reading order**: pdftotext uses `-layout` flag (visual positioning) — multi-column documents get interleaved
3. **Binary routing**: either pdftotext (fast, low accuracy) or LightOnOCR (slow, high accuracy) — no per-page complexity routing
4. **No prompt injection filtering**: extracted text passed raw to LLM context

---

## 3. Integration Strategies

### Strategy A: Coarse-Draft Preprocessing (User's Suggestion)

```
PDF Input
    ↓
[OpenDataLoader local] → 0.05s/page, structured markdown + bboxes
    ↓                      (correct reading order, table structure, figure positions)
    ├─ Clean pages: use directly (skip LightOnOCR)
    ├─ Complex pages: pass structured context to LightOnOCR/VL model
    │   └─ "Here is the layout: 3 columns, table at (x0,y0,x1,y1), 2 figures..."
    │       → LightOnOCR focuses on the hard parts with layout context
    └─ Figures: bbox coordinates → crop → route to VL model with position context
```

**Why this is smart**: OpenDataLoader local mode at 0.05s/page is essentially free (same order as pdftotext). It gives us:
- Correct reading order (XY-Cut++ vs pdftotext's layout heuristic)
- Table locations with structure (even at 0.49 accuracy, it identifies tables)
- Figure bboxes with semantic types
- Heading hierarchy

This structured pre-pass gives LightOnOCR and the VL models *context about what they're looking at*, rather than processing blind.

### Strategy B: Replace pdftotext Entirely

```
PDF Input
    ↓
[OpenDataLoader local] → 0.05s/page
    ↓
[Quality check] → same entropy/garbage logic, but on better-ordered text
    │
    ├─ PASS: use OpenDataLoader output (structured markdown + bboxes)
    └─ FAIL: fall back to LightOnOCR (scanned docs)
```

Drop-in replacement for pdftotext in `pdf_router.py`. Same speed, better reading order (0.91 vs pdftotext's unscored), table detection, heading hierarchy. Minimal code change.

**Trade-off**: Java 11+ dependency. Python SDK is a wrapper around Java CLI — each `convert()` call spawns a JVM (batch recommended).

### Strategy C: Selective Table Re-Parsing

```
PDF Input
    ↓
[pdftotext probe] → existing fast path
    ↓
[Quality check]
    ├─ PASS + no tables detected: use pdftotext as-is
    ├─ PASS + tables detected: re-parse table regions with OpenDataLoader
    └─ FAIL: LightOnOCR
```

Keeps existing pipeline, adds OpenDataLoader only for table extraction where pdftotext fails. Targeted improvement with minimal blast radius.

### Strategy D: Hybrid Backend Server

```
[OpenDataLoader hybrid server] running on port 5002
    ↓
pdf_router.py routes to it instead of/alongside LightOnOCR
```

Run `opendataloader-pdf-hybrid --port 5002` as a sidecar service. Route complex documents to it. Gets the 0.90/0.93 accuracy for documents that need it.

---

## 4. Recommended Strategy: A+B+D — Three-Phase Integration

**Phase 1**: Replace pdftotext with OpenDataLoader local mode (Strategy B)
- Swap `pdftotext -layout` for `opendataloader_pdf.convert(format="markdown,json")`
- Keep quality check logic (now evaluating better-ordered text)
- Immediate gains: reading order, heading hierarchy, basic table detection
- Same latency budget (~50ms/page)

**Phase 2**: Structured context for downstream models (Strategy A) — **Biggest win**
- Pass figure bboxes + semantic types + surrounding text + captions to VL models
  - Current gap: `figure_analyzer.py` sends cropped images cold, no document context
  - With ODL: VL model receives "This is a bar chart under heading 'Q3 Revenue', caption: 'Figure 3: ...', preceded by paragraph about quarterly earnings"
- Use heading hierarchy to improve `document_chunker` (structural splits, not regex)
- Pass table bboxes to ODL hybrid for focused table extraction at 0.93 accuracy

**Phase 3**: ODL hybrid sidecar + benchmark integration
- Run `opendataloader-pdf-hybrid --port 5002` as sidecar for complex tables
- Explore swapping hybrid backend from docling-fast to LightOnOCR-2-1B (already running on port 8082) — could beat 0.43s/page if GPU-accelerated OCR is faster than docling-fast
- Integrate [opendataloader-bench](https://github.com/opendataloader-project/opendataloader-bench) — add our pipeline (pdftotext + LightOnOCR) as a custom engine to get ground-truth comparison on the same 200 PDFs
- Three-way routing: ODL local (simple pages) → ODL hybrid (complex tables) → LightOnOCR (scanned docs)

### Routing Architecture (Target State)

```
PDF Input
    ↓
[OpenDataLoader local] → 0.05s/page, structured markdown + JSON + bboxes
    ↓
[Per-page complexity assessment]
    │
    ├─ Simple page (text, lists, headings):
    │   └─ Use ODL local output directly ✓
    │
    ├─ Complex tables detected:
    │   └─ Route table regions to ODL hybrid (0.93 acc, ~0.4s)
    │      OR LightOnOCR if faster on our GPU
    │
    ├─ Scanned/image page (quality check fails):
    │   └─ LightOnOCR-2-1B full-page OCR (GPU, ~1-3s)
    │
    └─ Figures detected (with bboxes + surrounding context):
        └─ Crop + route to VL model WITH:
           - Semantic type (chart/diagram/photo/formula)
           - Caption text (ODL extracts separately)
           - Surrounding paragraph context
           - Position in heading hierarchy
```

---

## 5. Technical Considerations

### JVM Dependency
- Requires Java 11+ at runtime
- Python SDK spawns JVM per `convert()` call — batch processing recommended
- Package: 22.3 MB wheel
- **Mitigation**: Pre-warm JVM in a persistent subprocess, or run as a sidecar service

### Integration Points

**`pdf_router.py` changes**:
```python
# Current
result = subprocess.run([self.pdftotext_path, "-layout", str(pdf_path), "-"], ...)

# Proposed (Strategy B)
import opendataloader_pdf
opendataloader_pdf.convert(
    input_path=[str(pdf_path)],
    output_dir=str(self.temp_dir),
    format="markdown,json",
    use_struct_tree=True
)
# Read markdown for text, JSON for bboxes
```

**`document_chunker.py` changes** (Phase 2):
- Replace regex header splitting with OpenDataLoader's heading hierarchy from JSON
- Use semantic types (heading level, paragraph, table, list) for chunk boundaries

**`document_preprocessor.py` changes** (Phase 2):
- Use figure bboxes from JSON instead of PyMuPDF extraction
- Pass table bboxes to LightOnOCR for focused table OCR

### Performance Budget

| Step | Current | With OpenDataLoader |
|------|---------|---------------------|
| Text extraction | pdftotext: ~100ms/page | ODL local: ~50ms/page |
| Figure extraction | PyMuPDF: ~50ms/page | ODL JSON bboxes: ~0ms (included in extraction) |
| OCR (if needed) | LightOnOCR: ~1-3s/page | Same (scanned docs) OR ODL hybrid: 430ms/page |
| Table extraction | None (gap) | ODL local: 0.49 acc / ODL hybrid: 0.93 acc |
| Prompt injection | None (gap) | ODL built-in filter |

### What Won't Change
- LightOnOCR remains the scanned document path (1B model, GPU inference)
- VL models remain for figure description (semantic understanding)
- document_chunker remains (but gets better input)

---

## 6. Open Questions

1. **JVM cold start**: How much does the first `convert()` call cost? Can we pre-warm via persistent subprocess?
2. **Batch vs single page**: Does the Python SDK support processing a single PDF page? Or only whole documents?
3. **JSON schema stability**: Is the JSON output schema versioned/stable for parsing?
4. **LightOnOCR as hybrid backend**: Can we swap docling-fast for our GPU-accelerated LightOnOCR-2-1B? Would this beat 0.43s/page?
5. **SmolVLM 256M**: How does its chart/image description compare to our Qwen2.5-VL-7B? (Likely worse — but at 256M it could serve as a fast triage layer)
6. **Memory footprint**: JVM heap usage for large documents (100+ pages)?
7. **opendataloader-bench integration**: Can we add our pipeline as a custom engine for apples-to-apples comparison on the same 200 PDFs?

### Non-Questions (Resolved)

- **Table accuracy at 0.49 local**: Use hybrid for any table — 0.93 is worth the 0.4s latency. Local mode's table detection still useful for *identifying* tables to route.
- **Java dependency**: Not a blocker. Python SDK abstracts it; sidecar service pattern isolates it. Java 11 is readily available.
- **llama.cpp for local mode**: Not applicable — ODL local is rule-based (XY-Cut++), not an ML model. No weights to convert.

---

## 7. Verdict

**WORTH INVESTIGATING → CREATE HANDOFF**

Three key value propositions, in order of impact:

1. **Structured context for VL models** (Phase 2): Biggest win. Figures currently analyzed blind; ODL gives semantic type, caption, surrounding text, heading position. This is free additional context that improves vision model output quality.

2. **Table extraction** (Phase 2-3): Currently a gap — pdftotext mangles tables, LightOnOCR outputs bboxes but no table structure. ODL hybrid gives 0.93 table accuracy.

3. **Reading order** (Phase 1): XY-Cut++ at 0.91 reading order accuracy vs pdftotext's unscored layout heuristic. Immediate quality improvement for multi-column documents.

The Java dependency is manageable (sidecar pattern). The 0.05s/page local mode fits within the existing latency budget. The structured JSON output improves *every downstream consumer* (chunker, figure analyzer, LLM context).

**Next step**: Create handoff `opendataloader-pipeline-integration.md` with the three-phase plan. First action: install `opendataloader-pdf`, run on sample documents from the orchestrator's test corpus, integrate into opendataloader-bench for ground-truth comparison.
