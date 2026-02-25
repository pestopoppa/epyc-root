# Session Persistence Layer

> **Status**: PHASE 7 COMPLETE - All phases implemented
> **Updated**: 2026-01-26
> **Plan File**: `/home/node/.claude/plans/delegated-rolling-lamport.md`

## Implementation Status

### Phase 1: Core Persistence (COMPLETE)
- [x] `src/session/` module structure
- [x] `SessionStore` protocol (ChromaDB-ready interface)
- [x] Session, Finding, Checkpoint models with serialization
- [x] `SQLiteSessionStore` implementation (WAL mode, numpy embeddings)
- [x] API routes integration (`src/api/routes/sessions.py`)

### Phase 2: Document Caching (COMPLETE)
- [x] `to_cache_dict()` / `from_cache_dict()` on all document models
- [x] Hash-based source change detection (SHA-256)
- [x] Per-session SQLite OCR cache (`src/session/document_cache.py`)
- [x] SessionStore integration methods
- [x] Figure images intentionally excluded from cache (descriptions preserved)

### Phase 3: Checkpoint & Resume (COMPLETE)
- [x] `checkpoint()` method on REPLEnvironment (JSON-serializable state)
- [x] `restore()` method on REPLEnvironment (state restoration)
- [x] Non-serializable artifacts marked with `__unserializable__` marker
- [x] `get_checkpoint_metadata()` for lightweight state queries
- [x] Context injection via `ResumeContext.format_for_injection()`

### Phase 4: Idle Monitoring & Auto-Summary (COMPLETE)
- [x] `SessionPersister` class for per-session checkpoint management
- [x] Checkpoint triggers: 5 turns / 30 min idle / explicit
- [x] Auto-summary after 2hr idle (heuristic default, LLM optional)
- [x] `IdleMonitor` class for background multi-session monitoring

### Phase 5: Key Findings (COMPLETE)
- [x] `mark_finding()` REPL function with tags and source tracking
- [x] `list_findings()` REPL function for session findings
- [x] `get_findings()` / `clear_findings()` for external access
- [x] Findings included in checkpoint/restore
- [x] `sync_findings()` in SessionPersister syncs REPL findings to store
- [x] Heuristic extraction: KEY:, FINDING:, IMPORTANT:, NOTE:, CONCLUSION:
- [x] Confidence scoring (0.8 for explicit prefixes, 0.5 for NOTE:)
- [x] Unconfirmed findings (`confirmed=False`) for user review

### Files Created
- `src/session/__init__.py` - Module exports
- `src/session/models.py` - Dataclasses (Session, Finding, Checkpoint, etc.)
- `src/session/protocol.py` - Abstract SessionStore interface
- `src/session/sqlite_store.py` - SQLite + numpy implementation
- `src/session/document_cache.py` - Per-session OCR caching
- `src/session/persister.py` - SessionPersister & IdleMonitor
- `src/cli_sessions.py` - Session management CLI (list, search, show, resume, etc.)
- `src/cli_orch.py` - Unified `orch` CLI entry point

### Files Modified
- `src/api/models/sessions.py` - Added new Pydantic models
- `src/api/models/__init__.py` - Exported new models
- `src/api/routes/sessions.py` - Replaced in-memory dict with SQLiteSessionStore
- `src/models/document.py` - Added cache serialization methods
- `src/repl_environment.py` - Added `checkpoint()`, `restore()`, `get_checkpoint_metadata()`, `mark_finding()`, `list_findings()`
- `orchestration/repl_memory/progress_logger.py` - Added session lifecycle events
- `pyproject.toml` - Added `orch` and `orch-sessions` entry points

## Architecture Decisions

| Decision | Choice | Notes |
|----------|--------|-------|
| Storage backend | Abstract interface → SQLite initial | ChromaDB-ready design |
| Embeddings | Store from day 1 | Use TaskEmbedder (896-dim) |
| Location | `/workspace/orchestration/repl_memory/sessions/` | Collocate with MemRL |
| Crash recovery | WAL mode + checkpoints | Every 5 turns / 30 min idle |
| Summary generation | Hybrid | Heuristic default; `/summarize` for LLM |
| Retention | Forever | User manages manually |

## Storage Layout

```
/workspace/orchestration/repl_memory/sessions/
├── sessions.db          # Session metadata (SQLite, WAL mode)
├── session_embeddings.npy  # Content embeddings for future semantic search
└── state/
    └── {session_id}/
        ├── manifest.json    # Metadata + artifact refs + source hashes
        ├── ocr_cache.db     # Cached DocumentPreprocessResult
        ├── artifacts.json   # JSON-serializable REPL artifacts
        ├── findings.jsonl   # Key findings (append-only)
        ├── summary.txt      # LLM-generated session summary
        └── history.jsonl    # Optional conversation log
```

## API Endpoints (New)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sessions` | GET | List sessions with filtering |
| `/sessions` | POST | Create new session |
| `/sessions/{id}` | GET | Get session details |
| `/sessions/{id}` | DELETE | Delete session |
| `/sessions/{id}/resume` | POST | Resume with context injection |
| `/sessions/{id}/findings` | GET/POST | Manage key findings |
| `/sessions/{id}/tags/{tag}` | POST/DELETE | Manage tags |
| `/sessions/{id}/checkpoints` | GET | List checkpoints |
| `/sessions/{id}/archive` | POST | Archive to cold storage |
| `/sessions/search` | GET | Search sessions |

### Phase 6: MemRL Integration (COMPLETE)
- [x] Added session lifecycle event types to EventType enum
- [x] Added logging methods: `log_session_created`, `log_session_resumed`, `log_session_checkpointed`, `log_session_archived`, `log_session_finding`
- [x] Integrated SessionPersister with ProgressLogger via optional `progress_logger` parameter
- [x] Added emit methods for session events in SessionPersister
- [x] Fork task_id on resume with lineage tracking (implemented in Session model)

### Phase 7: CLI & UX (COMPLETE)
- [x] `orch` unified CLI entry point with subcommands
- [x] `orch sessions list [--status STATUS] [--project PROJECT]`
- [x] `orch sessions search QUERY`
- [x] `orch sessions show SESSION_ID [--findings] [--checkpoints]`
- [x] `orch sessions resume SESSION_ID [--output json|text]`
- [x] `orch sessions archive SESSION_ID`
- [x] `orch sessions findings SESSION_ID`
- [x] `orch sessions delete SESSION_ID [--force]`
- [x] `orch status` for quick system status check
- [x] Partial session ID matching for all commands
- [x] pyproject.toml entry points: `orch`, `orch-sessions`

## Implementation Complete

## Key Findings from Implementation

1. **MemRL lineage tracking** - Session.fork_task_id() creates `{original_id}__r{N}` pattern for Q-learning to track resume trajectories

2. **ChromaDB migration path** - SessionStore protocol uses `where={}` filters compatible with ChromaDB metadata filtering

3. **Embedding storage ready** - SQLiteSessionStore stores 896-dim embeddings via numpy memmap (matches TaskEmbedder)

4. **Document change detection** - SessionDocument.compute_file_hash() for SHA-256 verification on resume

5. **Document cache design** - Per-session SQLite (not shared) allows clean session deletion; figure images intentionally excluded to save ~10x storage space (re-extract on demand via bbox coordinates)

6. **REPL checkpoint design** - Non-serializable artifacts (functions, objects) are marked with `{"__unserializable__": True, "type": "ClassName"}` rather than silently dropped, enabling debugging and partial restoration

7. **Idle monitoring architecture** - `SessionPersister` is per-session (stateful), `IdleMonitor` is singleton (stateless queries) - separation allows both interactive and background use cases

8. **Heuristic finding extraction** - Regex patterns detect KEY:, FINDING:, IMPORTANT: etc. with confidence scores (0.8 for explicit, 0.5 for NOTE:). Unconfirmed findings allow user review before persistence.

9. **ProgressLogger integration** - SessionPersister accepts optional `progress_logger` parameter; events flow into MemRL's Q-scoring system via standard EventType enum.

10. **CLI partial ID matching** - All session commands support partial UUID prefix matching (e.g., `71f753d0` matches `71f753d0-c0a6-4f67-...`), with disambiguation when multiple sessions match.

11. **Unified `orch` entry point** - Single CLI that routes to subcommands (sessions, run, stack, status) for consistent UX across orchestration operations.

## Related Research Track

**MemRL → ChromaDB Evaluation** (separate investigation):
- Current MemRL uses SQLite + numpy
- Session persistence designed for ChromaDB compatibility
- Evaluate migration benefits after Phase 1 stabilizes

---

**Implementation Complete** - All 7 phases of session persistence layer have been implemented. The system is ready for production use.
