# Handoff: Figure Analysis Not Performed in Document Pipeline

**Created:** 2026-01-24
**Status:** ✅ COMPLETED
**Priority:** High (core document understanding feature missing)

---

## Problem

The document formalizer pipeline detects figures (via LightOnOCR bounding box output) but does NOT analyze them with the vision model. All 11 figures in the Twyne whitepaper have empty descriptions.

```
Pages with figures: [3, 6, 7, 9, 13, 19, 20, 22, 25, 29, 32]
Analysis: "" (empty for all 11 figures)
```

## Solution Implemented

### New Module: `src/services/figure_analyzer.py`

Created a new module that:
1. Takes a PDF path and list of `FigureRef` objects (with bboxes)
2. Renders relevant pages to images using pypdfium2
3. Crops figure regions based on bounding box coordinates
4. Calls the vision API (`/v1/vision/analyze`) for each figure with concurrency control
5. Returns `FigureRef` objects with populated descriptions

Key features:
- **Parallel processing**: Uses asyncio.Semaphore for controlled concurrency (default: 4 concurrent)
- **Page caching**: Renders each page only once, even if multiple figures exist on the same page
- **Graceful error handling**: Continues on individual figure failures
- **Configurable**: Custom prompts, timeouts, and concurrency limits

### Updated: `src/services/document_preprocessor.py`

- Imports and uses the new `figure_analyzer` module
- When `describe_figures=True`, automatically calls `analyze_figures_async()`
- Logs success/failure and adds warnings on partial failures
- `DocumentPreprocessor` now takes an optional `FigureAnalyzer` instance for dependency injection

## How to Use

### Enable figure analysis in preprocessing:

```python
from src.services.document_preprocessor import DocumentPreprocessor, PreprocessingConfig

# Enable figure analysis
config = PreprocessingConfig(describe_figures=True)
preprocessor = DocumentPreprocessor(config=config)

# Process document
result = await preprocessor.preprocess(task_ir)

# Figures now have descriptions
for fig in result.document_result.figures:
    print(f"{fig.id}: {fig.description}")
```

### Via API endpoint:

```bash
curl -X POST http://localhost:8000/v1/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/document.pdf",
    "describe_figures": true
  }'
```

## Files Modified

| File | Change |
|------|--------|
| `src/services/figure_analyzer.py` | **NEW** - Figure analysis module |
| `src/services/document_preprocessor.py` | Added figure analyzer integration |
| `tests/integration/test_document_pipeline.py` | Added 12 new tests for figure analysis |

## Tests Added

All 48 tests pass:

```
TestFigureAnalyzer (10 tests):
- test_figure_analyzer_init
- test_figure_analyzer_custom_config
- test_image_to_base64
- test_crop_figure_normalized
- test_crop_figure_non_normalized
- test_analyze_single_figure_mocked
- test_analyze_single_figure_timeout
- test_analyze_single_figure_api_error
- test_analyze_figures_empty_list
- test_analyze_figures_nonexistent_pdf

TestFigureAnalyzerIntegration (2 tests):
- test_preprocessor_with_figure_analysis
- test_preprocessor_figure_analyzer_injection
```

## Performance Considerations

- ~5s per figure for vision model analysis
- 11 figures × ~5s = ~55s additional processing time for Twyne whitepaper
- Parallel processing with semaphore reduces wall-clock time
- Page images are cached to avoid redundant rendering

## Dependencies

- Vision model endpoint: `/v1/vision/analyze` (must be running)
- pypdfium2 for PDF rendering (already installed)
- PIL for image cropping (already installed)
- httpx for async HTTP requests (already installed)
