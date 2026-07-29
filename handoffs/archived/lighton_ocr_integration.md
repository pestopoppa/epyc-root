# LightOnOCR-2 Integration Handoff

**Created:** 2026-01-20
**Status:** ✅ COMPLETE - Production Ready
**Last Updated:** 2026-01-21 (Document Pipeline Integration complete)

---

## Summary

LightOnOCR-2-1B-bbox converted to GGUF and optimized for CPU inference via llama.cpp.
**Result: 19x speedup** (0.009 → 0.17 pg/s) over PyTorch baseline.

**NEW (2026-01-21):** Complete document pipeline integration with:
- Document models, client, chunker, preprocessor
- REPL document functions (section, figures, search_sections)
- API endpoints (/v1/documents/*)
- Dispatcher role mappings for document tasks

---

## Quick Start

```bash
# Start optimized server (8 workers × 12 threads)
./scripts/document/start_lightonocr_llama.sh --port 9001

# Test health
curl http://localhost:9001/health

# OCR a PDF
curl -X POST http://localhost:9001/v1/document/pdf \
  -F "file=@document.pdf" -F "max_pages=100"
```

---

## Performance Results

| Configuration | Speed | Memory | vs PyTorch |
|---------------|-------|--------|------------|
| PyTorch CPU (baseline) | 0.009 pg/s | ~5 GB | 1x |
| llama.cpp 1×12t | 0.045 pg/s | ~1.2 GB | 5x |
| llama.cpp 4×24t | 0.09 pg/s | ~5 GB | 10x |
| **llama.cpp 8×12t** | **0.17 pg/s** | **~10 GB** | **19x** |

### Thread Scaling (8-page benchmark)

| Config | Total | Per-page | Throughput | Notes |
|--------|-------|----------|------------|-------|
| **8×12t** | 47.2s | 40.6s | **0.170 pg/s** | ← OPTIMAL |
| 4×24t | 54.6s | 25.8s | 0.147 pg/s | Good balance |
| 2×48t | 83.2s | 20.2s | 0.096 pg/s | Lower throughput |
| 1×96t | 123.4s | 15.4s | 0.065 pg/s | Best latency |

**Key insight:** More workers > more threads per worker for throughput.

---

## Model Files

| File | Size | Location |
|------|------|----------|
| Text model (Q4_K_M) | 379 MB | `/mnt/raid0/llm/models/LightOnOCR-2-1B-bbox-Q4_K_M.gguf` |
| Vision encoder (F16) | 782 MB | `/mnt/raid0/llm/models/LightOnOCR-2-1B-bbox-mmproj-F16.gguf` |
| HuggingFace source | 1.9 GB | `/mnt/raid0/llm/hf/LightOnOCR-2-1B-bbox/` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           FastAPI Server (lightonocr_llama_server.py)        │
├─────────────────────────────────────────────────────────────┤
│  POST /v1/document/pdf → Semaphore(8) controlled dispatch   │
├─────────────────────────────────────────────────────────────┤
│  Worker Pool: 8 × llama-mtmd-cli subprocesses               │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ × 2 more      │
│  │ 12 thr │ │ 12 thr │ │ 12 thr │ │ 12 thr │              │
│  └────────┘ └────────┘ └────────┘ └────────┘              │
│  Each: Q4_K_M text + F16 mmproj (~1.2 GB)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Server Files

| File | Purpose |
|------|---------|
| `src/services/lightonocr_llama_server.py` | FastAPI server with worker pool |
| `src/services/lightonocr_server.py` | PyTorch version (deprecated, slow) |
| `scripts/document/start_lightonocr_llama.sh` | Startup script (recommended) |
| `scripts/document/start_lightonocr_server.sh` | PyTorch startup (deprecated) |

---

## Launch Quirks

### llama-mtmd-cli Usage

```bash
# Correct usage (non-interactive)
llama-mtmd-cli \
  -m /path/to/LightOnOCR-2-1B-bbox-Q4_K_M.gguf \
  --mmproj /path/to/LightOnOCR-2-1B-bbox-mmproj-F16.gguf \
  --image /path/to/image.png \
  -p "Extract text" \
  -t 12 -n 2048

# WITHOUT --image and -p: enters interactive chat mode (avoid in scripts)
```

### Known Issues

1. **Empty `-p ""` causes "invalid argument"** - use `-p "OCR"` or similar
2. **Default context 16384 uses ~1.8 GB KV cache** - acceptable for 8 workers
3. **Vision encoding fixed ~8s** - bottleneck, independent of thread count
4. **BOS token is `,` (comma)** - unusual but works correctly

### Environment Variables

```bash
export LIGHTONOCR_WORKERS=8      # Number of parallel workers
export LIGHTONOCR_THREADS=12     # Threads per worker
export LIGHTONOCR_MAX_TOKENS=2048
export LIGHTONOCR_TIMEOUT=120    # Per-page timeout in seconds
```

---

## GGUF Conversion Commands

```bash
cd /mnt/raid0/llm/llama.cpp

# Convert text model
python3 convert_hf_to_gguf.py /mnt/raid0/llm/hf/LightOnOCR-2-1B-bbox/ \
  --outfile /mnt/raid0/llm/models/LightOnOCR-2-1B-bbox-F16.gguf \
  --outtype f16

# Quantize
./build/bin/llama-quantize \
  /mnt/raid0/llm/models/LightOnOCR-2-1B-bbox-F16.gguf \
  /mnt/raid0/llm/models/LightOnOCR-2-1B-bbox-Q4_K_M.gguf Q4_K_M

# Convert vision encoder (mmproj)
python3 convert_hf_to_gguf.py /mnt/raid0/llm/hf/LightOnOCR-2-1B-bbox/ \
  --mmproj \
  --outfile /mnt/raid0/llm/models/LightOnOCR-2-1B-bbox-mmproj-F16.gguf \
  --outtype f16
```

---

## Remaining Tasks

- [x] Add to `orchestrator_stack.py` ✅ (2026-01-21)
- [x] Create integration tests ✅ (2026-01-21)
- [ ] Test with diverse document types (scanned, handwritten)
- [x] Model registry updated with launch quirks (2026-01-21)
- [x] Document pipeline integration ✅ (2026-01-21)

---

## Document Pipeline Integration (2026-01-21)

### New Files Created

| File | Purpose |
|------|---------|
| `src/models/document.py` | Data classes: BoundingBox, PageOCRResult, OCRResult, Section, FigureRef, DocumentPreprocessResult |
| `src/services/document_client.py` | Async HTTP client for LightOnOCR server |
| `src/services/document_chunker.py` | Semantic chunking by markdown headers |
| `src/services/document_preprocessor.py` | Main preprocessing service combining OCR + chunking |
| `src/repl_document.py` | REPL extension with document functions |
| `src/api/routes/documents.py` | FastAPI endpoints for document processing |
| `tests/integration/test_document_pipeline.py` | Comprehensive integration tests |

### Files Modified

| File | Change |
|------|--------|
| `src/dispatcher.py` | Added doc, document, document_formalizer, ocr role mappings |
| `src/api/routes/__init__.py` | Added documents_router import and registration |

### API Endpoints

```
GET  /v1/documents/health          - Check OCR server status
POST /v1/documents/process         - Process PDF/image by path or base64
POST /v1/documents/process/upload  - Process uploaded file (multipart)
POST /v1/documents/preprocess-taskir - Preprocess TaskIR with documents
```

### REPL Document Functions

```python
sections()           # List all section titles
section(n)          # Get section n content (1-indexed)
figures(section=n)  # List figures, optionally filtered
figure_image(id)    # Get figure base64
search_sections(q)  # Search sections by content
document_info()     # Get document metadata
```

### Data Flow

```
User Input (PDF/image)
    ↓
DocumentPreprocessor.needs_preprocessing(task_ir)  # Auto-detect
    ↓
DocumentFormalizerClient.ocr_pdf()  → LightOnOCR server (port 9001)
    ↓
DocumentChunker.process()  # Split by markdown headers
    ↓
DocumentPreprocessResult {sections, figures, total_pages}
    ↓
DocumentREPLEnvironment  # Provides section(), figures(), etc.
    ↓
Enriched TaskIR with ocr_result field
```

### Usage Example

```python
from src.services.document_preprocessor import preprocess_documents

task_ir = {
    "inputs": [{"type": "path", "value": "/path/to/doc.pdf"}]
}

result = await preprocess_documents(task_ir)
if result.success:
    doc = result.document_result
    for section in doc.sections:
        print(f"{section.title}: {len(section.content)} chars")
```

---

## Definition of Done

- [x] Model downloaded to `/mnt/raid0/llm/hf/`
- [x] GGUF conversion complete (text + mmproj)
- [x] Q4_K_M quantization (379 MB)
- [x] FastAPI server with worker pool
- [x] Benchmarked: 0.17 pg/s (19x faster than PyTorch)
- [x] Optimal config determined: 8×12 threads
- [x] Model registry updated (with launch quirks and optimized config)
- [x] Documentation complete
- [x] Added to orchestrator stack ✅ (2026-01-21)
- [x] Integration tests created ✅ (2026-01-21)
- [x] Document pipeline integration ✅ (2026-01-21)
  - [x] Document models (BoundingBox, Section, FigureRef, etc.)
  - [x] Async HTTP client for OCR server
  - [x] Semantic chunking by markdown headers
  - [x] Document preprocessing service
  - [x] REPL document functions
  - [x] API endpoints (/v1/documents/*)
  - [x] Dispatcher role mappings
  - [x] Comprehensive integration tests

---

## Next Steps (Future Work)

1. **Test with diverse document types**
   - Scanned documents (lower quality images)
   - Handwritten text
   - Multi-column layouts
   - Tables and complex figures

2. **GPU acceleration** (if needed)
   - llama.cpp supports CUDA - could achieve 50-100x over current CPU
   - Would require RTX 4090 or similar

3. **Batch API for high-volume processing**
   - Current: single PDF at a time
   - Future: queue-based processing for document batches

4. **Figure cropping and VL analysis**
   - Extract figure images from bounding boxes
   - Route to Qwen2.5-VL for figure descriptions

---

## Conclusion

**LightOnOCR-2 integration is COMPLETE and production-ready.**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Speed | 0.009 pg/s | 0.17 pg/s | **19x** |
| Memory | ~5 GB | ~10 GB (8 workers) | Acceptable |
| Integration | None | Full pipeline | ✅ |

The optimization pattern (PyTorch → llama.cpp GGUF) is reusable for other VLM models.
