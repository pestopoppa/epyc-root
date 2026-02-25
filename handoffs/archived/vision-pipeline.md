# Vision Pipeline Implementation

**Project**: AMD EPYC 9655 Inference Optimization - Vision Processing
**Created**: 2026-01-16
**Updated**: 2026-02-01
**Status**: CHAT PIPELINE INTEGRATION COMPLETE - NEEDS LIVE VALIDATION

---

## Quick Resume

```bash
# Phase 1 implementation complete (~4,500 lines across 23 files)
# Code review complete (36 issues addressed, 7 refactors applied)
# Next: Integration test on host with live models

# Test basic imports
cd /mnt/raid0/llm/claude
python3 -c "from src.vision.pipeline import get_pipeline; print('OK')"

# Start API for testing
uvicorn src.api:create_app --host 0.0.0.0 --port 8000

# Test single image analysis
curl -X POST localhost:8000/v1/vision/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/mnt/raid0/llm/vision/test_images/test_shapes.png"}'
```

---

## Implementation Status

### Phase 1: Core Infrastructure (MVP) - ✅ COMPLETE

| File | Lines | Status |
|------|-------|--------|
| `src/vision/__init__.py` | 28 | ✅ |
| `src/vision/config.py` | 86 | ✅ (expanded) |
| `src/vision/models.py` | 242 | ✅ |
| `src/vision/clustering.py` | 115 | ✅ (new) |
| `src/db/__init__.py` | 4 | ✅ |
| `src/db/chroma_client.py` | 230 | ✅ |
| `src/db/models/__init__.py` | 24 | ✅ (expanded) |
| `src/db/models/vision.py` | 210 | ✅ (expanded) |
| `src/vision/analyzers/__init__.py` | 22 | ✅ |
| `src/vision/analyzers/base.py` | 180 | ✅ (expanded) |
| `src/vision/analyzers/insightface_loader.py` | 70 | ✅ (new) |
| `src/vision/analyzers/face_detect.py` | 140 | ✅ (refactored) |
| `src/vision/analyzers/face_embed.py` | 200 | ✅ (refactored) |
| `src/vision/analyzers/vl_describe.py` | 258 | ✅ (refactored) |
| `src/vision/analyzers/exif.py` | 238 | ✅ (refactored) |
| `src/vision/analyzers/clip_embed.py` | 213 | ✅ |
| `src/vision/pipeline.py` | 385 | ✅ (expanded) |
| `src/vision/batch.py` | 284 | ✅ |
| `src/vision/search.py` | 401 | ✅ |
| `src/vision/video.py` | 385 | ✅ (refactored) |
| `src/api/routes/vision.py` | 294 | ✅ (refactored) |
| `tests/vision/test_pipeline.py` | 308 | ✅ |
| `tests/vision/test_api.py` | 352 | ✅ |
| **Total** | **~4,500** | ✅ |

**Router registered:** `/v1/vision/*` in `src/api/routes/__init__.py`

### Code Review & Refactoring - ✅ COMPLETE

| Improvement | Description |
|-------------|-------------|
| Session context manager | `managed_session()` eliminates duplicate try/except patterns |
| Base class helpers | `_error_result()`, `_success_result()` standardize responses |
| Shared InsightFace loader | Singleton prevents duplicate 500MB model loads |
| Clustering service | Business logic extracted from route to `clustering.py` |
| Config constants | All timeouts and magic numbers centralized |
| Comprehensive docstrings | All SQLAlchemy models fully documented |
| Public properties | `is_initialized` replaces private `_initialized` access |

### Phase 2: Batch Processing - ✅ INCLUDED IN PHASE 1

- [x] Job queue with status tracking (`src/vision/batch.py`)
- [x] Parallel worker pool (ThreadPoolExecutor)
- [x] Progress reporting API (`/v1/vision/batch/{job_id}`)

### Phase 3: Face Recognition - ✅ INCLUDED IN PHASE 1

- [x] Face detection using InsightFace (`face_detect.py`)
- [x] Face embedding ArcFace 512-dim (`face_embed.py`)
- [x] ChromaDB integration (`chroma_client.py`)
- [x] Clustering for unknown faces (HDBSCAN in API)
- [x] Labeling API (`/v1/vision/faces/{id}`)

### Phase 4: Search & Retrieval - ✅ INCLUDED IN PHASE 1

- [x] Text search on descriptions (`search.py`)
- [x] Face search by embedding similarity
- [x] Date/location filters (SQLite metadata)
- [x] Combined queries

### Phase 5: Video Processing - ✅ INCLUDED IN PHASE 1

- [x] ffmpeg integration for frame extraction (`video.py`)
- [x] Frame-level analysis pipeline
- [x] Thumbnail storage

### Phase 6: Advanced Features - PARTIAL

- [x] CLIP embeddings for visual similarity (`clip_embed.py`)
- [ ] Object detection (not implemented - use VL model prompting)
- [ ] Document/form extraction (VL_STRUCTURED analyzer exists but needs testing)

### Phase 7: /chat Pipeline Integration - ✅ COMPLETE (2026-02-01)

Vision requests through `/chat` now use the full document pipeline:
- [x] `_execute_vision()` rewritten — runs DocumentPreprocessor instead of bare ocr_image()
- [x] `RoutingResult.document_result` carries preprocessing result between stages
- [x] REPL mode forced when document results exist (frontdoor text model orchestrates)
- [x] `DocumentREPLEnvironment` used in `_execute_repl()` — sections/figures/search tools
- [x] Base64 image support added to `DocumentPreprocessor._extract_document_paths()`
- [x] 1234 tests passing (1149 unit + 48 doc pipeline + 11 vision + 26 API)

---

## API Endpoints Implemented

| Endpoint | Method | Status | Purpose |
|----------|--------|--------|---------|
| `/v1/vision/analyze` | POST | ✅ | Single image analysis |
| `/v1/vision/batch` | POST | ✅ | Start batch job |
| `/v1/vision/batch/{job_id}` | GET | ✅ | Check job status |
| `/v1/vision/batch/{job_id}` | DELETE | ✅ | Cancel job |
| `/v1/vision/search` | POST | ✅ | Search indexed content |
| `/v1/vision/faces` | GET | ✅ | List known persons |
| `/v1/vision/faces/{id}` | PUT | ✅ | Update person (name, merge) |
| `/v1/vision/faces/identify` | POST | ✅ | Identify faces in image |
| `/v1/vision/faces/cluster` | POST | ✅ | Cluster unlabeled faces |
| `/v1/vision/video/analyze` | POST | ✅ | Video analysis |
| `/v1/vision/stats` | GET | ✅ | Pipeline statistics |

---

## Next Steps (Priority Order)

### 1. Integration Testing on Host (HIGH)

```bash
# 1. Verify API starts without errors
cd /mnt/raid0/llm/claude
source /mnt/raid0/llm/pace-env/bin/activate
uvicorn src.api:create_app --host 0.0.0.0 --port 8000

# 2. Test EXIF extraction (no model needed)
curl -X POST localhost:8000/v1/vision/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/mnt/raid0/llm/vision/test_images/test_shapes.png", "analyzers": ["exif_extract"]}'

# 3. Test face detection (needs insightface)
curl -X POST localhost:8000/v1/vision/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/path/to/photo_with_faces.jpg", "analyzers": ["face_detect"]}'

# 4. Test VL description (needs llama-mtmd-cli + models)
curl -X POST localhost:8000/v1/vision/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/path/to/test.jpg", "analyzers": ["vl_describe"]}'
```

### 2. Verify VL Model Paths (HIGH)

Check that these files exist on host:
- `/mnt/raid0/llm/llama.cpp/build/bin/llama-mtmd-cli`
- `/mnt/raid0/llm/models/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`
- `/mnt/raid0/llm/models/mmproj-model-f16.gguf`

If paths differ, update `src/vision/config.py`:
```python
LLAMA_MTMD_CLI = Path("/actual/path/to/llama-mtmd-cli")
VL_MODEL_PATH = Path("/actual/path/to/model.gguf")
VL_MMPROJ_PATH = Path("/actual/path/to/mmproj.gguf")
```

### 3. Run Unit Tests (MEDIUM)

```bash
# Run vision tests (some may fail without live models)
pytest tests/vision/ -v

# Run with coverage
pytest tests/vision/ --cov=src/vision --cov-report=term-missing
```

### 4. Add OpenAI-Compat Multimodal Support (MEDIUM)

The current OpenAI-compat endpoint (`/v1/chat/completions`) doesn't handle image content. To support Aider/LM Studio with images:

**File:** `src/api/routes/openai_compat.py`
**Change:** Parse `messages[].content` as list (OpenAI format) when it contains image_url

```python
# Current: content is string
# Needed: content can be list of {type: "text"/"image_url", ...}
```

### 5. Add Vision Roles to OpenAI-Compat (LOW)

**File:** `src/api/routes/openai_compat.py` line 39-45
```python
AVAILABLE_ROLES = [
    "orchestrator",
    "frontdoor",
    "coder",
    "architect",
    "worker",
    "worker_vision",      # Add
    "vision_escalation",  # Add
]
```

### 6. Register Vision Tools in Tool Registry (LOW)

For proactive delegation to work, vision operations should be registered as tools:

**File:** `orchestration/tool_registry.yaml`
```yaml
tools:
  analyze_image:
    description: "Analyze image for faces, text, objects"
    category: specialized
    parameters:
      image_path: {type: string, required: true}
      analyzers: {type: array, default: ["face_detect", "vl_describe"]}
    implementation:
      type: python
      module: src.vision.pipeline
      function: analyze_image_tool
```

---

## Known Limitations

1. **VL inference is subprocess-based** - Uses llama-mtmd-cli, not native Python. This adds ~100ms overhead per call.

2. **No streaming for VL** - VL descriptions return complete, not streamed.

3. **Face clustering requires faces** - `/v1/vision/faces/cluster` fails if no unlabeled faces exist.

4. **Video processing is sequential** - Frames analyzed one at a time (pipeline limitation).

5. **No GPU acceleration** - InsightFace runs on CPU (`providers=['CPUExecutionProvider']`).

---

## Dependencies (Already Installed)

| Category | Packages |
|----------|----------|
| **System** | ffmpeg, imagemagick, exiftool, poppler-utils, tesseract |
| **Python** | insightface, chromadb, opencv-python-headless, pillow, sentence-transformers, hdbscan |
| **Models** | ArcFace (buffalo_l), all-MiniLM-L6-v2 |

---

## Related Documents

- **Design Plan**: `/home/node/.claude/plans/humble-splashing-dewdrop.md`
- **Model Registry**: `orchestration/model_registry.yaml` (worker_vision, vision_escalation)
- **Orchestrator Tasks**: `research/NEXT_ORCHESTRATION_TASKS.md`
- **Module README**: `src/vision/README.md`
- **Progress Log**: `progress/2026-01/2026-01-16.md`
