# OpenDataLoader PDF — Pipeline Integration

**Status**: Phase 1 done (NIB2-13). Phase 2 SCAFFOLDING LANDED 2026-05-06 — `src/models/odl_structured.py` (FigureContext, HeadingNode, TableContext, ODLStructuredDocument); `_extract_with_opendataloader_structured()` in pdf_router; `build_figure_prompt_with_context()` additive helper in figure_analyzer; `chunk_by_odl_headings()` additive helper in document_chunker. Gated behind `ORCHESTRATOR_ODL_STRUCTURED=1`. 17 new unit tests + 38/38 existing tests still pass (back-compat verified). Phase 2 deeper integration (replace PyMuPDF figure extraction, replace regex chunker entirely, document_preprocessor refactor) is multi-day per-service work, deferred. Phase 3 (sidecar + benchmark) inference-gated.
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

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-452] "OpenAI Privacy Parser — inverse of OpenAI Privacy Filter (returns PII spans instead of masking)"** (`github.com/chiefautism/privacy-parser`)
  - Relevance: lightweight Apache-2.0 Python wrapper over the exact intake-449 opf 1.5B weights — returns structured character spans instead of `<REDACTED>` masks. Three backends: pure-regex (1.000 F1 on fixture, µs), model-only (0.733 F1, ~500 ms CPU), and HybridPIIParser (model + span-merge + regex backstop, **0.929 F1, ~600 ms CPU**).
  - Key technique: BIOES + tuned Viterbi over opf logits → char spans → span-merge → regex backstop for URL/secret/account_number. The model+regex hybrid pattern is the non-trivial engineering contribution beyond intake-449.
  - Delta from current approach: this pipeline's gap #5 (no PII/injection filter) remains open. If a PII step is ever added, `HybridPIIParser` is a drop-in — avoids re-wrapping the raw opf weights ourselves. ~600 ms CPU latency is acceptable for offline/batch KB ingestion but would dominate per-request orchestrator latency.
  - Action: **track only** — consistent with the intake-449 action above. No pipeline change. Bookmark for the offline/batch slot when a concrete requirement surfaces. Does not address prompt-injection filtering (still gap #5).

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

- [ ] Bench **LiteParse-local vs OpenDataLoader-local vs pdftotext** on the orchestrator born-digital test corpus: reading order, table fidelity, speed, **JVM-free deploy footprint**. Use a LiteParse-output-aware quality harness (its non-markdown layout output breaks naive OlmOCR/TEDS scoring — confirmed in intake-646 Tier 2b). Decide adopt_component vs ODL-only for the fast path.
- [ ] Route complex/dense-table/scanned docs **away** from LiteParse (vendor docs concede LlamaParse-cloud-class quality is needed there; our equivalent is the ODL + VL-OCR path) — LiteParse is a born-digital fast-path backend only.

## Research Intake Update — 2026-06-12

### New Related Research (deep-dived, from the intake-694 open-weights roundup)
- **PaddleOCR-VL-1.6** (2026-06, Apache-2.0 — distinct from the pluggable PaddleOCR HTTP *engine*): a 1B-param VLM document parser (ERNIE-4.5-0.3B backbone), **OmniDocBench v1.6 overall 96.33 (SOTA: text / formula / tables / layout, + Real5 SOTA)**. Official **GGUF + mmproj** (`PaddlePaddle/PaddleOCR-VL-1.6-GGUF`), llama-mtmd CPU path — so it's runnable on our stack. Unlike the PaddleOCR engine (Phase-1 fast-path slot), this is a full VLM parser overlapping the **LightOnOCR slow-path + ODL structural extraction**. **Action (eval-gated):** bench PaddleOCR-VL-1.6 vs LightOnOCR on the doc test corpus for structured layout/table/formula extraction. **P1 follow-up — warrants its own intake entry.** See `research/deep-dives/2026-06-12-open-weights-roundup-followups.md`.
