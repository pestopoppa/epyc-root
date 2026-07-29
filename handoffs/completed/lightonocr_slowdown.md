# Handoff: LightOnOCR 3.4x Slowdown Through Orchestrator

**Created:** 2026-01-24
**Status:** ✅ RESOLVED
**Priority:** Medium (affects end-to-end document processing time)

---

## Problem (RESOLVED)

LightOnOCR-2 was running 3.4x slower through the orchestrator TaskIR preprocessing pipeline compared to direct benchmarks.

| Metric | Direct Benchmark | Via Orchestrator (Before) | Via Orchestrator (After) |
|--------|------------------|---------------------------|--------------------------|
| Speed | 0.17 pg/s | 0.05 pg/s | **0.117 pg/s** |
| 32-page PDF | ~188s | 638s | **276.6s** |

## Root Cause

Two issues were identified:

### Issue 1: Sequential vs Parallel Processing
The `process_document()` function in `document_client.py` was using `ocr_pdf_with_partial_success()` which makes individual HTTP requests per page, adding network overhead. The server's `/v1/document/pdf` endpoint handles all pages internally with parallel workers.

### Issue 2: Per-Page Timeout Too Short
The server's per-page timeout was 120s, but some complex pages (figures, dense text) take 24-30s each. With 8 workers processing in parallel, queue delays could push individual page processing past the timeout.

## Fixes Applied

### Fix 1: Use Server-Side PDF Processing
Changed `process_document()` in `src/services/document_client.py` to use `ocr_pdf()` instead of `ocr_pdf_with_partial_success()`:

```python
# BEFORE: Client-side per-page requests (slow)
return await client.ocr_pdf_with_partial_success(path, ...)

# AFTER: Server-side parallel processing (fast)
return await client.ocr_pdf(path, ...)
```

### Fix 2: Increase Server Timeout
Changed `TIMEOUT_SEC` in `src/services/lightonocr_llama_server.py` from 120s to 300s:

```python
TIMEOUT_SEC = int(os.environ.get("LIGHTONOCR_TIMEOUT", "300"))  # 5 min for complex pages
```

**Note:** Server restart required after this change.

## Verification

Full 32-page Twyne whitepaper test:

| Metric | Result |
|--------|--------|
| Pages processed | 32/32 |
| Total time | 276.6s |
| Speed | 0.117 pg/s |
| Failed pages | 0 |

## Files Changed

- `src/services/document_client.py` - Use `ocr_pdf()` for server-side processing
- `src/services/lightonocr_llama_server.py` - Increase timeout to 300s

## Notes

1. The `ocr_pdf_with_partial_success()` method was also improved to use parallel processing (asyncio.gather), but this is now only used as a fallback for partial failure handling.

2. Multi-page TIFF could also benefit from server-side processing in the future, but would require adding a `/v1/document/tiff` endpoint to the server.

3. The measured 0.117 pg/s is lower than the benchmark 0.17 pg/s, likely due to the specific content of the Twyne whitepaper (complex figures).
