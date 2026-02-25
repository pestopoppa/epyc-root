# Handoff: NextPLAID Multi-Vector Code & Document Retrieval

## Status

Phases 1-5 COMPLETE. Debugger integration COMPLETE.
- :8088 `nextplaid-code` — LateOn-Code 130M (code index, AST-chunked, 128-dim)
- :8089 `nextplaid-docs` — answerai-colbert-small-v1-onnx (docs index, 1350 chunks, 96-dim)
- Incremental reindex wired into `make gates` (dual-container aware).
- Claude Debugger can detect NextPLAID downtime and reload containers via `RELOAD_SERVICE:` directive.

## Goal

Add a **multi-vector retrieval layer** to the REPL tool environment using [NextPLAID](https://github.com/lightonai/next-plaid) (Apache 2.0, Rust, CPU-optimized). This gives agents token-level code search and document retrieval — a capability the current single-vector FAISS stack cannot provide.

**What this is NOT**: This does not replace or modify the episodic memory system (FAISS + BGE + Q-scoring). The episodic store handles routing/escalation memories (467 entries, 1024-dim BGE embeddings, Q-value ranking). NextPLAID handles a fundamentally different problem: finding relevant **code passages** and **documentation sections** within large corpora using multi-vector late interaction (ColBERT).

## Why Multi-Vector Matters for REPL Flows

Single-vector retrieval (BGE-large → 1 embedding per document) averages token semantics into one vector. When a query matches a specific function signature buried in a 500-line file, the document-level embedding dilutes that signal. ColBERT preserves **~300 token-level embeddings per document** (128-dim each) and uses MaxSim matching — every query token finds its best match across all document tokens. This is precisely the retrieval pattern needed for:

- **Code search**: "find the function that handles escalation routing" → matches on token overlap with actual function names, parameter types, docstrings
- **Context retrieval for delegation**: Coder (B1) and workers (C) need relevant code snippets before executing; current `recall()` only searches episodic memories, not the codebase itself
- **Documentation lookup**: Agents querying project docs, model quirks, benchmark results

## Architecture

### What Changes

```
NEW (additive):
┌──────────────────────────────────────────────────┐
│              NextPLAID (:8088)                     │
│  Docker: ghcr.io/lightonai/next-plaid:cpu-1.0.4  │
│                                                    │
│  Indices:                                          │
│  ├── code    (LateOn-Code model)                  │
│  │   └── src/**/*.py, orchestration/**/*.py       │
│  ├── docs    (GTE-ModernColBERT-v1 or ColBERT-sm) │
│  │   └── docs/**/*.md, handoffs/**/*.md           │
│  └── config  (ColBERT-small)                      │
│      └── orchestration/*.yaml, *.json             │
│                                                    │
│  Storage: /mnt/raid0/llm/claude/cache/next-plaid/ │
│  Port: 8088 (avoids 8080-8087 model servers)      │
└──────────────────────────────────────────────────┘
         ↑                    ↑
    code_search()        doc_search()
    (REPL native fn)     (REPL native fn)

UNCHANGED:
┌──────────────────────────────────────────────────┐
│  EpisodicStore (SQLite + FAISS) — MemRL routing  │
│  BGE Pool (8090-8095) — fast routing embeddings  │
│  TwoPhaseRetriever — Q-value + semantic ranking  │
│  recall() — episodic memory REPL tool            │
└──────────────────────────────────────────────────┘
```

### Port Allocation

| Port | Service | Status |
|------|---------|--------|
| 8080-8087 | LLM model servers | Existing |
| 8088 | **NextPLAID-code** (LateOn-Code-edge) | Active |
| 8089 | **NextPLAID-docs** (answerai-colbert-small-v1) | Active |
| 8090-8095 | BGE embedding pool | Existing |

### Model Selection

| Index | Model | Why |
|-------|-------|-----|
| `code` | `lightonai/LateOn-Code` | Purpose-built for code retrieval; understands syntax, identifiers, types |
| `docs` | `lightonai/answerai-colbert-small-v1-onnx` | Lightweight text model; docs are natural language, don't need heavy model |
| `config` | Same as `docs` | YAML/JSON configs are small; share the model |

**Decision**: `LateOn-Code` is gated/private on HuggingFace (files return 404 even with auth token). Using `LateOn-Code-edge` instead — the lightweight code variant (48-dim embeddings, ONNX INT8). Both code and docs indices created with this single model. Search quality validated: correct top-1 results on all test queries, ~40ms p95 latency.

## Implementation Plan

### Phase 1: Deploy & Index (non-breaking)

**1a. Docker deployment**

```bash
# Create storage directory
mkdir -p /mnt/raid0/llm/claude/cache/next-plaid

# Pull and run (CPU mode, INT8 quantization)
docker pull ghcr.io/lightonai/next-plaid:cpu-1.0.4
docker run -d --name nextplaid \
  -p 8088:8080 \
  -v /mnt/raid0/llm/claude/cache/next-plaid:/data/indices \
  ghcr.io/lightonai/next-plaid:cpu-1.0.4 \
  --host 0.0.0.0 --port 8080 \
  --index-dir /data/indices \
  --model lightonai/LateOn-Code \
  --int8

# Verify
curl -s http://localhost:8088/health
```

**Note on `--model`**: NextPLAID downloads the ONNX model on first start. The `LateOn-Code` model is ~130MB. Verify it caches inside the Docker volume (`/data/indices`) or bind-mount the HF cache:
```bash
-v /mnt/raid0/llm/cache/huggingface:/root/.cache/huggingface
```

**1b. Indexing script** — `scripts/nextplaid/index_codebase.py`

```python
"""Index project source code and docs into NextPLAID."""
from next_plaid_client import NextPlaidClient, IndexConfig
from pathlib import Path
import glob

CLIENT_URL = "http://localhost:8088"
PROJECT_ROOT = Path("/mnt/raid0/llm/claude")

# File patterns to index
CODE_PATTERNS = [
    "src/**/*.py",
    "orchestration/**/*.py",
    "orchestration/repl_memory/**/*.py",
    "scripts/**/*.py",
    "tests/**/*.py",
]

# Files to skip
SKIP_PATTERNS = {"__pycache__", ".pyc", "node_modules", ".git"}

def collect_files(patterns, root):
    """Collect files matching glob patterns."""
    files = []
    for pattern in patterns:
        for path in root.glob(pattern):
            if any(skip in str(path) for skip in SKIP_PATTERNS):
                continue
            files.append(path)
    return sorted(set(files))

def chunk_file(path, max_chars=2000):
    """Split file into chunks preserving function/class boundaries.

    Strategy: split on blank lines between top-level definitions.
    Each chunk gets metadata: file path, line range, chunk index.
    """
    text = path.read_text(errors="replace")
    # For now: simple fixed-size chunks with overlap
    # TODO: AST-aware chunking for Python files
    chunks = []
    lines = text.split("\n")
    chunk_lines = []
    char_count = 0
    start_line = 1

    for i, line in enumerate(lines, 1):
        chunk_lines.append(line)
        char_count += len(line) + 1
        if char_count >= max_chars:
            chunks.append({
                "text": "\n".join(chunk_lines),
                "file": str(path.relative_to(PROJECT_ROOT)),
                "start_line": start_line,
                "end_line": i,
            })
            # Overlap: keep last 3 lines for context continuity
            chunk_lines = chunk_lines[-3:]
            char_count = sum(len(l) + 1 for l in chunk_lines)
            start_line = i - 2

    if chunk_lines:
        chunks.append({
            "text": "\n".join(chunk_lines),
            "file": str(path.relative_to(PROJECT_ROOT)),
            "start_line": start_line,
            "end_line": len(lines),
        })

    return chunks

def main():
    client = NextPlaidClient(CLIENT_URL)

    # Create index (4-bit quantization for storage efficiency)
    try:
        client.create_index("code", IndexConfig(nbits=4))
    except Exception:
        pass  # Index may already exist

    files = collect_files(CODE_PATTERNS, PROJECT_ROOT)
    print(f"Collected {len(files)} files to index")

    all_chunks = []
    all_metadata = []

    for f in files:
        chunks = chunk_file(f)
        for chunk in chunks:
            all_chunks.append(chunk["text"])
            all_metadata.append({
                "file": chunk["file"],
                "start_line": str(chunk["start_line"]),
                "end_line": str(chunk["end_line"]),
            })

    print(f"Total chunks: {len(all_chunks)}")

    # Batch ingest (NextPLAID handles batching internally)
    BATCH_SIZE = 100
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch_docs = all_chunks[i:i+BATCH_SIZE]
        batch_meta = all_metadata[i:i+BATCH_SIZE]
        client.add("code", documents=batch_docs, metadata=batch_meta)
        print(f"  Indexed {min(i+BATCH_SIZE, len(all_chunks))}/{len(all_chunks)}")

    print("Done.")

if __name__ == "__main__":
    main()
```

**1c. Validation**

```bash
pip install next-plaid-client  # Into pace-env
python scripts/nextplaid/index_codebase.py

# Test query
python -c "
from next_plaid_client import NextPlaidClient
c = NextPlaidClient('http://localhost:8088')
results = c.search('code', ['escalation routing policy'])
for r in results:
    print(r)
"
```

### Phase 2: REPL Integration

**2a. NextPLAID client wrapper** — `src/repl_environment/code_search.py`

New mixin providing `code_search()` and `doc_search()` as native REPL functions, following the same pattern as `_RoutingMixin` in `src/repl_environment/routing.py`.

```python
"""Code and document search via NextPLAID multi-vector retrieval.

Provides mixin with: code_search, doc_search.
"""
from __future__ import annotations
import json
import logging
from typing import Any

from src.repl_environment.types import wrap_tool_output

logger = logging.getLogger(__name__)

NEXTPLAID_URL = "http://localhost:8088"


class _CodeSearchMixin:
    """Mixin providing multi-vector code/doc search tools.

    Required attributes (provided by REPLEnvironment.__init__):
        config: REPLConfig
        artifacts: dict
        _exploration_calls: int
        _exploration_log: ExplorationLog
    """

    _nextplaid_client: Any = None  # Lazy-loaded

    def _get_nextplaid_client(self):
        if self._nextplaid_client is None:
            try:
                from next_plaid_client import NextPlaidClient
                self._nextplaid_client = NextPlaidClient(NEXTPLAID_URL)
                # Quick health check
                # TODO: check if health endpoint exists, else try a trivial search
            except ImportError:
                logger.warning("next-plaid-client not installed")
                return None
            except Exception as e:
                logger.warning(f"NextPLAID unavailable: {e}")
                return None
        return self._nextplaid_client

    def _code_search(self, query: str, limit: int = 5, index: str = "code") -> str:
        """Search codebase for relevant code passages using multi-vector retrieval.

        Unlike recall() which searches episodic memories (past routing decisions),
        code_search() finds actual source code in the project matching your query.
        Uses token-level matching — searches for exact function names, parameter
        types, and code patterns, not just semantic similarity.

        Args:
            query: Natural language or code pattern to search for.
                   e.g., "escalation policy implementation",
                         "def embed_task_ir", "FAISS index configuration"
            limit: Max results to return (default 5).
            index: Which index to search ("code" or "docs"). Default "code".

        Returns:
            JSON with matching code passages, file paths, and line ranges.
        """
        self._exploration_calls += 1

        client = self._get_nextplaid_client()
        if client is None:
            output = json.dumps({
                "results": [],
                "error": "NextPLAID not available (install: pip install next-plaid-client)",
            })
            self.artifacts.setdefault("_tool_outputs", []).append(output)
            return wrap_tool_output(output)

        try:
            raw_results = client.search(index, [query])

            results = []
            for r in raw_results[:limit]:
                meta = r.get("metadata", {}) if isinstance(r, dict) else {}
                results.append({
                    "file": meta.get("file", "unknown"),
                    "lines": f"{meta.get('start_line', '?')}-{meta.get('end_line', '?')}",
                    "score": round(r.get("score", 0.0), 4) if isinstance(r, dict) else 0.0,
                    "snippet": (r.get("document", "")[:300] if isinstance(r, dict) else str(r)[:300]),
                })

            response = {"results": results, "index": index, "query": query}

            self._exploration_log.add_event(
                "code_search", {"query": query, "index": index}, response
            )

            output = json.dumps(response, indent=2)
            self.artifacts.setdefault("_tool_outputs", []).append(output)
            return wrap_tool_output(output)

        except Exception as e:
            output = json.dumps({"results": [], "error": str(e)})
            self.artifacts.setdefault("_tool_outputs", []).append(output)
            return wrap_tool_output(output)

    def _doc_search(self, query: str, limit: int = 5) -> str:
        """Search project documentation for relevant sections.

        Searches markdown docs, handoffs, model registry, and config files.
        For code search, use code_search() instead.

        Args:
            query: What to look for in documentation.
            limit: Max results (default 5).

        Returns:
            JSON with matching doc passages and metadata.
        """
        return self._code_search(query, limit=limit, index="docs")
```

**2b. Register in REPL globals** — `src/repl_environment/environment.py`

Add to `_build_globals()`:
```python
globals_dict["code_search"] = self._code_search
globals_dict["doc_search"] = self._doc_search
```

Add `_CodeSearchMixin` to REPLEnvironment's base classes.

**2c. System prompt update** — `orchestration/prompts/repl_tools.md`

Add to the tool documentation section that models see:
```
## code_search(query, limit=5)
Search the project codebase for code matching your query. Uses token-level
matching (not just semantic similarity) — can find specific function names,
class definitions, and code patterns.

Returns: JSON with file paths, line ranges, scores, and code snippets.

Example: code_search("FAISS index initialization") → finds faiss_store.py:__init__
Example: code_search("def retrieve_for_routing") → finds exact function
Example: code_search("escalation policy rules") → finds policy implementation
```

### Phase 3: Incremental Index Updates

**3a. File watcher / pre-commit hook** — Keep index fresh on code changes.

Option A (lightweight): Re-index changed files on each `make gates` run.
```bash
# In Makefile, add to 'gates' target:
nextplaid-reindex:
    python scripts/nextplaid/reindex_changed.py
```

Option B (real-time): Use `watchfiles` (already in many Python stacks) to watch `src/` and re-index on save. Overkill for now.

**Recommended**: Option A. The codebase changes infrequently enough that re-indexing on `make gates` is sufficient.

**3b. Reindex script** — `scripts/nextplaid/reindex_changed.py`

```python
"""Re-index only files changed since last indexing."""
import subprocess
from pathlib import Path

# Get changed files since last index timestamp
# Store timestamp in cache/next-plaid/.last_indexed
TIMESTAMP_FILE = Path("/mnt/raid0/llm/claude/cache/next-plaid/.last_indexed")

def get_changed_files():
    if not TIMESTAMP_FILE.exists():
        return None  # Full reindex needed

    last_time = TIMESTAMP_FILE.read_text().strip()
    result = subprocess.run(
        ["git", "diff", "--name-only", f"--since={last_time}", "HEAD"],
        capture_output=True, text=True,
        cwd="/mnt/raid0/llm/claude"
    )
    return [f for f in result.stdout.strip().split("\n") if f.endswith(".py")]
```

### Phase 4: Dedicated Doc Model (COMPLETE)

Deployed dedicated doc-retrieval model on second container:
- `:8089` runs `answerai-colbert-small-v1-onnx` (33M params, text-optimized)
- `:8088` continues with `LateOn-Code-edge` (code-optimized)
- `code_search.py` routes by index: code→:8088, docs→:8089 (with fallback)
- `index_codebase.py` / `reindex_changed.py` support `--code-url` / `--docs-url`
- Docs index must be re-encoded with new model embeddings after container launch

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `scripts/nextplaid/index_codebase.py` | Full codebase indexing script |
| `scripts/nextplaid/reindex_changed.py` | Incremental re-index on changes |
| `src/repl_environment/code_search.py` | `_CodeSearchMixin` — REPL integration |
| `tests/unit/test_code_search.py` | Unit tests (mock NextPLAID client) |

### Modified Files

| File | Change |
|------|--------|
| `src/repl_environment/environment.py` | Add `_CodeSearchMixin` to bases, register `code_search`/`doc_search` in globals |
| `orchestration/prompts/repl_tools.md` | Document new tools for model system prompts |
| `Makefile` | Add `nextplaid-reindex` target to `gates` (Phase 3) |
| `pyproject.toml` | Add `next-plaid-client` to optional dependencies |

### NOT Modified

| File | Why |
|------|-----|
| `orchestration/repl_memory/faiss_store.py` | Episodic memory unchanged |
| `orchestration/repl_memory/episodic_store.py` | Episodic memory unchanged |
| `orchestration/repl_memory/parallel_embedder.py` | BGE pool unchanged |
| `orchestration/repl_memory/retriever.py` | TwoPhaseRetriever unchanged |
| `src/repl_environment/routing.py` | `recall()` unchanged |

## Hardware Fit

NextPLAID is CPU-first with memory-mapped indices. On the EPYC 9655:

- **96 cores / 192 threads**: ONNX encoding parallelizes across cores; centroid routing is embarrassingly parallel
- **1.13TB DDR5**: Memory-mapped indices load instantly; no RAM pressure even with large codebases
- **NVMe RAID0**: Index I/O is negligible on 2x P44 Pro
- **No GPU needed**: BEIR benchmarks show CPU QPS is ~85-100% of GPU QPS for NextPLAID

Estimated resource usage for this project's codebase (~500 Python files, ~50K lines):
- Index size: ~10-20MB (19KB/doc × ~1000 chunks)
- Encoding time: ~30s full reindex
- Query latency: ~30-50ms (encoding + search)
- RAM overhead: <200MB (Docker + ONNX model + mmap'd index)

## Open Questions

1. **Per-index model support**: Can one NextPLAID instance serve multiple indices with different models? Or does `--model` apply globally? If global, Phase 4 needs two containers or we accept a single model for all indices.

2. **ONNX model cache location**: Verify the ONNX model downloads into the Docker volume, not `~/.cache` inside the container (ephemeral). Mitigation: bind-mount HF cache.

3. **Chunking strategy**: The initial implementation uses fixed-size character chunks. AST-aware chunking (split on class/function boundaries) would produce better retrieval units. Defer to Phase 2 if simple chunking works acceptably.

4. **Search result format**: NextPLAID returns results in a specific format. Need to verify the exact response structure from `client.search()` and adapt the mixin accordingly. The code above assumes a dict format — may need adjustment after live testing.

5. **Docker restart policy**: Should NextPLAID start with `orchestrator_stack.py`? Or separate `docker compose` for infrastructure services? Recommend: add to orchestrator stack as an infrastructure dependency (like BGE pool).

## Resume Instructions

```bash
# 1. Verify Docker is available
docker --version

# 2. Start NextPLAID
mkdir -p /mnt/raid0/llm/claude/cache/next-plaid
docker pull ghcr.io/lightonai/next-plaid:cpu-1.0.4
docker run -d --name nextplaid \
  -p 8088:8080 \
  -v /mnt/raid0/llm/claude/cache/next-plaid:/data/indices \
  -v /mnt/raid0/llm/cache/huggingface:/root/.cache/huggingface \
  ghcr.io/lightonai/next-plaid:cpu-1.0.4 \
  --host 0.0.0.0 --port 8080 \
  --index-dir /data/indices \
  --model lightonai/LateOn-Code \
  --int8

# 3. Install client
pip install next-plaid-client

# 4. Verify health
curl -s http://localhost:8088/health

# 5. Run full codebase index
python scripts/nextplaid/index_codebase.py

# 6. Test search
python -c "
from next_plaid_client import NextPlaidClient
c = NextPlaidClient('http://localhost:8088')
r = c.search('code', ['escalation routing policy'])
print(r)
"

# 7. Implement Phase 2 (REPL integration)
# See 'Files to Create/Modify' section above
```

## Documentation & Architecture Updates

After implementation, the following docs must be updated to reflect the new retrieval layer. Grouped by phase.

### Phase 1 (Deploy & Index)

**`CLAUDE.md` — Component Flow** (line ~162)

Current:
```
Memory:     EpisodicStore(SQLite) → FAISSStore(4042 vectors) → ParallelEmbedder → BGE pool(:8090-8095)
```
Add line:
```
Retrieval:  NextPLAID(:8088) → LateOn-Code(ONNX) → code index(mmap) — multi-vector code/doc search
```

**`CLAUDE.md` — Directory Structure** (`/mnt/raid0/llm/` tree)

Add under `claude/`:
```
    ├── cache/next-plaid/       # NextPLAID indices (mmap'd)
```

Add under `scripts/`:
```
    │   ├── nextplaid/          # Indexing & reindexing scripts
```

**`docs/chapters/12-production-server-stack.md`** — Server Topology

Add to **Auxiliary Services** table (after `:9001 document_formalizer`):

| Port | Service | Model | Purpose |
|------|---------|-------|---------|
| 8088 | nextplaid | LateOn-Code (ONNX, INT8) | Multi-vector code & doc retrieval |

Add to **Memory Architecture → Tier Allocation** tree:
```
│   └── NextPLAID: <1GB (Docker + ONNX + mmap'd index)
```

**`logs/canvases/component_topology.canvas`** — Obsidian Canvas

Add node to `layer_infra` group:
```json
{
  "id": "nextplaid",
  "type": "text",
  "x": 1100,
  "y": 40,
  "width": 160,
  "height": 80,
  "text": "**NextPLAID**\n:8088\nLateOn-Code\nMulti-vector search",
  "color": "6"
}
```

Add edge from `layer_tools` to `nextplaid`:
```json
{"id": "edge_tools_nextplaid", "fromNode": "repl_tools", "toNode": "nextplaid", "label": "code_search()"}
```

### Phase 2 (REPL Integration)

**`docs/chapters/11-repl-environment.md`** — Built-In Functions

Add new table section after "Extended Functions (Archive/Web)" (~line 66):

```markdown
### Code & Document Retrieval

| Function | Purpose | Example |
|----------|---------|---------|
| `code_search(query)` | Multi-vector code search (NextPLAID) | Find function definitions, patterns |
| `doc_search(query)` | Multi-vector doc search (NextPLAID) | Find relevant documentation sections |
```

**`docs/chapters/11-repl-environment.md`** — Research Context Tracker Node IDs

Add to the node ID table (~line 138):

| Prefix | Tool | Example |
|--------|------|---------|
| CS | code_search | CS1, CS2 |
| DS | doc_search | DS1 |

(Requires corresponding update in `src/research_context.py` to register the new prefixes.)

**`docs/chapters/15-memrl-system.md`** — Scope Clarification

Add note at top of "Episodic Memory Architecture" section (~line 11):

```markdown
> **Scope**: The MemRL episodic store handles *routing memories* (task→action→outcome).
> For *codebase retrieval* (finding source code and documentation passages), see
> the NextPLAID integration in [Ch11: REPL Environment](11-repl-environment.md).
> These are complementary systems with different embedding models, dimensions,
> and retrieval algorithms.
```

**`docs/ARCHITECTURE.md`** — Module Responsibilities

Add to "Core Modules" table (~line 184):

| Module | Responsibility | Dependencies |
|--------|---------------|--------------|
| `src/repl_environment/code_search.py` | Multi-vector code/doc retrieval (NextPLAID) | next-plaid-client |

**`docs/ARCHITECTURE.md`** — Architecture Diagram

Add `NextPLAID` box to the Backend Layer section (~line 80):
```
│  │ NextPLAID  │
│  │  Backend   │
│  │  (:8088)   │
│  └────────────┘
```

**`docs/diagrams/orchestration_topology.md`** — Mermaid Routing Graph

Add to the MemRL subgraph or create a new Retrieval subgraph:
```mermaid
subgraph Retrieval["Code Retrieval Layer"]
    NP[(NextPLAID<br/>:8088)]
    CI[("code index<br/>(LateOn-Code)")]
end

S8 -->|"code_search()"| NP
NP --> CI
```

### Phase 3 (Incremental Reindex)

**`CLAUDE.md` — Verification Gates** (~line after "Markdown lint")

Add gate step:
```
6. **Index freshness** (`scripts/nextplaid/reindex_changed.py`) — when NextPLAID is running
```

**`Makefile`** — Gates target

Document the new `nextplaid-reindex` target in the Makefile's help/comments.

### Cross-Cutting

**`orchestration/model_registry.yaml`**

Add NextPLAID as an infrastructure service entry (not a model server, but tracked for health checks):
```yaml
infrastructure:
  nextplaid:
    port: 8088
    type: retrieval
    model: lightonai/LateOn-Code
    quantization: int8
    docker_image: ghcr.io/lightonai/next-plaid:cpu-1.0.4
    indices: [code, docs]
    health_endpoint: /health
```

**`scripts/server/orchestrator_stack.py`**

Add NextPLAID to the infrastructure startup sequence (alongside BGE pool). It should start before the orchestrator API since `code_search()` is a soft dependency (graceful degradation if unavailable).

**`CHANGELOG.md`**

Add entry on completion:
```markdown
## YYYY-MM-DD
- **NextPLAID integration**: Added multi-vector code & doc retrieval via NextPLAID (:8088).
  New REPL tools: `code_search()`, `doc_search()`. Uses LateOn-Code ColBERT model
  with token-level MaxSim matching. Complementary to episodic memory (FAISS/BGE).
  See handoff: `handoffs/active/nextplaid-code-retrieval.md`.
```

### Documentation Update Checklist

| Doc | Section | Update | Phase |
|-----|---------|--------|-------|
| `CLAUDE.md` | Component Flow | Add `Retrieval:` line | 1 |
| `CLAUDE.md` | Directory Structure | Add `cache/next-plaid/`, `scripts/nextplaid/` | 1 |
| `CLAUDE.md` | Verification Gates | Add index freshness step | 3 |
| `docs/chapters/12-production-server-stack.md` | Auxiliary Services table | Add `:8088 nextplaid` row | 1 |
| `docs/chapters/12-production-server-stack.md` | Memory Architecture | Add NextPLAID RAM line | 1 |
| `docs/chapters/11-repl-environment.md` | Built-In Functions | Add code_search/doc_search table | 2 |
| `docs/chapters/11-repl-environment.md` | Research Context Tracker | Add CS/DS node prefixes | 2 |
| `docs/chapters/15-memrl-system.md` | Episodic Memory Architecture | Add scope clarification note | 2 |
| `docs/ARCHITECTURE.md` | Module Responsibilities | Add code_search.py row | 2 |
| `docs/ARCHITECTURE.md` | Architecture Diagram | Add NextPLAID backend box | 2 |
| `docs/diagrams/orchestration_topology.md` | Mermaid graph | Add Retrieval subgraph | 2 |
| `logs/canvases/component_topology.canvas` | Infrastructure Layer | Add nextplaid node + edge | 1 |
| `orchestration/model_registry.yaml` | infrastructure section | Add nextplaid entry | 1 |
| `scripts/server/orchestrator_stack.py` | Startup sequence | Add NextPLAID Docker start | 1 |
| `Makefile` | gates target | Add nextplaid-reindex | 3 |
| `CHANGELOG.md` | Top entry | Add integration summary | final |

## Success Criteria

- [x] NextPLAID container runs on :8088 (Docker, LateOn-Code-edge, INT8, 88MB RAM)
- [x] Codebase indexed (460 files → 4,599 code chunks + 140 files → 1,345 doc chunks, 389.7s)
- [x] `code_search("def retrieve_for_routing")` returns `retriever.py:87-133` (score 6.34) ✓
- [x] `code_search("FAISS IndexFlatIP")` returns `faiss_store.py:47-89` (score 5.29) ✓
- [x] REPL agents can call `code_search()` — registered in sandbox globals, 12/12 unit tests pass
- [x] No regression — 153/153 REPL tests pass
- [x] Index stays fresh via `make gates` → `nextplaid-reindex` target ✓
- [x] Query latency: 39.6ms mean, 42.6ms p95 ✓
- [x] Phase 1 doc updates: CLAUDE.md, Ch12, canvas, model_registry.yaml ✓
- [x] Phase 2 doc updates: Ch11, Ch15, ARCHITECTURE.md, topology diagram ✓
- [x] Phase 3 doc updates: CLAUDE.md verification gates, Makefile, pyproject.toml ✓
- [x] CHANGELOG.md entry written ✓
- [x] Phase 4: Dedicated doc model on :8089 (answerai-colbert-small-v1-onnx)
- [x] Phase 4: Dual-client routing in code_search.py (code→:8088, docs→:8089)
- [x] Phase 4: Fallback (docs container down → code container)
- [x] Phase 4: index_codebase.py + reindex_changed.py support --code-url/--docs-url
- [x] Phase 4: model_registry.yaml split into nextplaid_code + nextplaid_docs
- [x] Phase 4: 18 unit tests (12 existing + 6 new dual-client/fallback tests)
- [x] Phase 5: Model upgrade LateOn-Code-edge → LateOn-Code (130M, 128-dim, +11.2% MTEB Code)
- [x] Phase 5: AST-aware chunking via tree-sitter (functions, classes, methods with signatures)
- [x] Phase 5: ColGrep CLI installed (v1.0.6) for agent-facing hybrid search
- [x] Phase 5: Search results enriched with unit_type, unit_name, signature metadata
- [x] Phase 5: 20 unit tests (18 existing + 2 new AST metadata tests)
