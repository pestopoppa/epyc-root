# LiteParse — Document Parser Deep Dive

**Date**: 2026-05-29
**Intakes**: intake-646 (LlamaIndex v2 blog), intake-647 (github.com/run-llama/liteparse)
**Trigger**: post-intake deep dive to validate/revise the `adopt_component` call.
**Verdict outcome**: verdicts HELD (646 worth_investigating, 647 adopt_component); credibility re-scored up; scope sharpened to *complement, not replacement* of OpenDataLoader.

## What it is

First-party LlamaIndex (run-llama) Rust document parser. Apache-2.0, **v2.0.3 released 2026-05-28** (one day before this dive). GitHub: **6.8k stars / 425 forks / 600 commits / 46 releases**; Rust 70.3% / Py 18.3% / JS 3.8%. Real CI (`ci.yml` + `e2e-output.yml`, 3-OS matrix Ubuntu/macOS/Windows + a HuggingFace-backed regression suite gated by `output-changed`/`output-approved` labels). Three-tier testing: Rust unit/integration (grid projection, coordinate math) → E2E baseline regression vs HF-stored outputs → an LLM-as-judge eval framework (`lp-process`/`lp-evaluate`, Claude Vision ground truth). Credible, actively-maintained first-party repo — not a hobby project.

## Architecture

Cargo workspace: `liteparse-pdfium-sys` (FFI to PDFium C lib, dynamic load + cross-platform binary acquisition) → `liteparse-pdfium` (safe wrapper) → `liteparse` core (`LiteParse` in `parser.rs`). Headline algorithm = **spatial-grid projection** (`projection.rs`): an Anchor System (`SnapKind`) detects columns and aligns text into a character grid mirroring the visual layout (handles rotation, multi-column flow). Explicit design philosophy: **"preserve layout rather than detect structure"** — tables emitted as positioned/ASCII-grid text, not a markdown table DOM, on the premise that LLMs are trained on ASCII tables + code indentation. OCR is a pluggable `OcrEngine` trait: internal `TesseractOcrEngine` (`tesseract` feature) or external `HttpOcrEngine` (EasyOCR/PaddleOCR via a documented `POST /ocr` spec), triggered by heuristics only when native PDFium text extraction is insufficient.

## Dependency footprint reality (the skim's biggest correction)

The v2 blog confirms: "uses a custom fork and build of PDFium, and is compiled against a build of `tesseract-rs`." **Critically, the custom PDFium fork and tesseract are compiled INTO the prebuilt wheels** — the user does not build PDFium. PyPI ships **manylinux x86_64 (glibc 2.28+) wheels, 11.0–13.2 MB**, Python 3.10–3.15 + PyPy 3.11. On the EPYC host, `pip install liteparse` is a self-contained ~13 MB binary — **no JVM, no system PDFium, no system tesseract** for the born-digital path. Remaining deps are conditional and avoidable: **LibreOffice** only for Office→PDF, **ImageMagick** only for image→PDF, **tesseract `.traineddata`** not bundled (point `TESSDATA_PREFIX` at a tessdata dir). For born-digital PDFs none are touched. Dramatically lighter than OpenDataLoader's Java 11+ runtime + per-`convert()` JVM spawn. This is what validates "runs everywhere" for our use case.

## Python API fit

Slots cleanly behind an ABC in `pdf_router.py`:

```python
from liteparse import LiteParse
parser = LiteParse(ocr_enabled=True, ocr_server_url=..., ocr_language="fra", dpi=300, target_pages="1-5")
result = parser.parse("doc.pdf")        # also accepts bytes
result.text                              # full layout-preserved text
for page in result.pages:                # page.page_num, page.text_items
    ...
screenshots = parser.screenshot("doc.pdf", page_numbers=[1,2,3])  # .image_bytes = PNG
```

Each `TextItem`: `text`, bbox `x/y/width/height` f32 in **viewport space, top-left origin, 72 DPI** (NOT corner-pairs, NOT PDF-points — differs from ODL's `[left,bottom,right,top]`; an adapter is needed), `rotation`, font metadata, `confidence: Option<f32>` (None native / 0–1 OCR), colors, mcid. **Reading order is implicit** in `text_items` order (no explicit field). Output = text + per-item bboxes + page PNGs. **No structured table object, no heading-hierarchy object** — tables are positioned text; headings are not semantically typed. This is a real functional gap vs ODL's semantic JSON types (heading/paragraph/table/list/image/caption/formula) that Phase 2 of the handoff depends on.

## Accuracy story (thin, honestly disclosed)

No independent accuracy benchmark (no NID/TEDS/MHS/OmniDocBench/OlmOCR number). Vendor's own eval is LLM-as-judge page-based QA vs **pypdf, PyMuPDF, Markitdown** only — never vs Docling/Marker/LlamaParse/ODL. Vendor explicitly concedes that **dense tables, multi-column, charts, handwritten, scanned PDFs** are significantly better on LlamaParse (cloud), and that the layout-preserving (non-markdown) output **fails standard OCR/table benchmarks by construction** ("not incorrect, but fails the benchmark format"). The v2 "100×" numbers are speed-only (5–100× small docs, ~3× large vs the v1 Node version; 457-page/100 MB in 0.777 s); no accuracy gain claimed v2 vs v1.

## Positioning vs OpenDataLoader (intake-161)

Complementary, not interchangeable:
- **LiteParse** = JVM-free ~13 MB wheel, layout-as-positioned-text, bboxes + page PNGs, no semantic structure, no markdown tables/headings. Best as the **born-digital fast-path text+bbox+screenshot extractor** — competes with `pdftotext` for the Phase 1 slot.
- **OpenDataLoader** = JVM, rule-based XY-Cut++, rich JSON semantic types + markdown tables + heading hierarchy + safety/PII filter (0.84 local / 0.90 hybrid on its 200-PDF bench). Best where **structure matters** (Phase 2 chunker headings, table DOM, figure semantic-type → VL).

LiteParse cannot deliver Phase 2's "biggest win" (semantic structure → chunker / VL context). It can deliver a faster JVM-free Phase 1 path, and its page-PNG screenshots feed the VL/OCR branch. Both coexist behind the `pdf_router` ABC.

## Revision outcome

| Intake | Field | Old → New | Reason |
|--------|-------|-----------|--------|
| 646 | credibility | null → 2 | Makes an empirical (speed) claim — null is wrong per rubric; but vendor-self-reported, speed-only, no repro for the multipliers → 2 |
| 647 | credibility | null → 4 | First-party Apache-2.0, 6.8k★, real 3-OS CI + HF regression + LLM-judge eval; capped <5 because only *accuracy* evidence is LLM-judge vs weak baselines |
| 647 | verdict | adopt_component (kept) | Scope-narrowed: born-digital fast-path text+bbox+screenshot backend, NOT an ODL structural replacement |

Novelty (medium) and relevance (high) unchanged for both.

## Recommended next actions (handoff)

- Bench LiteParse-local vs ODL-local vs `pdftotext` on the born-digital corpus: wall-clock/page, text fidelity, **JVM-free cold-start + RSS footprint** (LiteParse's clearest win), reading-order on multi-column samples — using a **LiteParse-output-aware harness** (positioned-text, not markdown; naive OlmOCR/TEDS mis-scores it).
- Build a small **bbox adapter** (viewport 72-DPI x/y/w/h → ODL-style PDF-point corner-pairs) before LiteParse bboxes feed existing figure/VL consumers.
- Keep ODL as the structural backend for Phase 2 (heading hierarchy, table DOM, figure semantic-type). Route complex/dense-table/scanned docs to ODL + VL-OCR, never to LiteParse.
- Pin LiteParse v2.0.3 in any eval (46 releases, shipped 2026-05-28 — expect API churn).
- Optional: feed `parser.screenshot()` PNGs directly into the VL/LightOnOCR path for the scanned branch (one library for text + page-image).
