# Context Mode (mksglu/context-mode) — Deep Dive: Tool Compression Patterns for EPYC

- **Source**: https://github.com/mksglu/context-mode
- **Intake ID**: intake-415
- **License**: ELv2 (Elastic License v2) — pattern-adoptable, not component-adoptable
- **Intake verdict**: `adopt_patterns` (pre-deep-dive)
- **Cross-refs**: intake-395 (claude-mem), intake-414 (token-savior-recall), intake-259 (RTK), intake-274 (The Complexity Trap)
- **EPYC handoffs**: `tool-output-compression.md` (Phase 2 live, Phase 3 in design), `context-folding-progressive.md` (Phase 2b L1-L4 done)

This deep dive focuses on four patterns from context-mode that map directly to open EPYC work items: (1) subprocess sandbox isolation for tool output compression, (2) threshold-gated output routing, (3) PreCompact session snapshots for context folding, and (4) FTS5 indexing for large tool outputs. These address known limitations documented in the tool-output-compression handoff (PostToolUse hooks cannot replace built-in Bash tool output) and the context-folding handoff (compaction boundary detection).

---

## 1. Subprocess Sandbox Pattern for Tool Output Compression

### What context-mode does

Context-mode's `PolyglotExecutor` class (`src/executor.ts`) spawns isolated subprocesses per tool call. The key insight: **raw data never enters the conversation context**. The subprocess captures full stdout/stderr, but only a processed summary is returned to the LLM. Raw data stays in the sandbox's temp directory or gets indexed into FTS5 for later retrieval.

The execution flow:

```
Agent requests: "analyze this 45KB access log"
    |
    v
ctx_execute_file(path="access.log", language="python", code="...")
    |
    v
PolyglotExecutor.executeFile()
    |-- writes script to mkdtemp()
    |-- spawns child process (process group isolation, SIGKILL on timeout)
    |-- captures stdout (the ONLY thing returned)
    |-- kills process tree on completion
    |
    v
stdout enters context: "500 requests, 12 errors, top endpoints: /api/users (312), /api/auth (88)"
    (155 bytes instead of 45.1KB)
```

The sandbox enforces a 100MB hard cap (`hardCapBytes`), runs in the project root for shell commands (so git/relative paths work) but in tmpdir for other languages, and supports 11 runtimes with auto-detection.

### EPYC integration architecture

The orchestrator's tool execution path flows through `src/runtime/executor.py` -> `ContextManager` -> `helpers.py:_spill_if_truncated()`. The subprocess sandbox pattern maps onto this at two integration points:

**Integration Point A: Orchestrator REPL pipeline**

The existing flow is:
```
Tool execution -> raw output -> truncate_output(8192 chars) -> _spill_if_truncated(1500 chars)
```

The proposed flow adds a sandbox layer before truncation:
```
Tool execution -> SandboxRouter.route(output, command_class)
    |
    |-- output <= 5KB: pass through unchanged
    |-- output > 5KB: index in FTS5, return summary + retrieval pointer
    |
    v
compressed output -> truncate_output() -> _spill_if_truncated()
```

This is complementary to Phase 2's `compress_tool_output.py`, not a replacement. Phase 2 compresses by pattern matching (pytest failures, git diff headers). The sandbox pattern adds **index-and-summarize** for outputs that do not match any known pattern -- the long tail of unstructured command output.

**Integration Point B: AutoPilot eval tower**

`eval_tower.py` generates `QuestionResult` objects with full answer text, scoring details, and route metadata. These inflate the controller prompt. Wrapping eval execution in a sandbox that indexes results to FTS5 while returning only the pass/fail summary would reduce per-question context from ~2-5KB to ~100-200B.

**Integration Point C: Claude Code sessions (root-archetype)**

This is the exact workaround for the PostToolUse limitation documented in `tool-output-compression.md`:

> PostToolUse hooks **cannot replace built-in tool output** (only MCP tools support `updatedMCPToolOutput`).

Context-mode solves this by being an MCP server whose tools (`ctx_execute`, `ctx_execute_file`, `ctx_batch_execute`) replace the built-in Bash/Read tools. The agent is instructed via SessionStart hooks to use `ctx_execute` instead of Bash for commands that produce large output. Since MCP tool output is fully controllable, the sandbox returns only the compressed result.

For EPYC's root-archetype, this means:
1. Wrap the highest-impact compressors from Phase 2 as MCP tools
2. Register via `.claude/settings.json` or plugin system
3. Use SessionStart hook to inject routing instructions ("for pytest/git/build commands, use ctx_execute instead of Bash")
4. Compressed output flows through `updatedMCPToolOutput` — the path that works

### Which tool outputs benefit most

Ranked by frequency in EPYC autopilot sessions times average output size:

| Tool Output | Avg Raw Size | Compressed Size | Savings | Priority |
|-------------|-------------|-----------------|---------|----------|
| pytest (full suite) | 20-80KB | 1-3KB (failure focus) | 95%+ | P0 |
| Benchmark results (eval tower) | 5-30KB | 200-500B (summary) | 95%+ | P0 |
| Server logs (orchestrator_stack) | 10-50KB | 200B-1KB (error focus) | 95%+ | P0 |
| git diff (multi-file) | 5-20KB | 1-3KB (hunk focus) | 80%+ | P1 |
| Model registry YAML | 8-15KB | 200B (queried section) | 95%+ | P1 |
| File reads (large configs) | 5-50KB | 500B-2KB (relevant section) | 90%+ | P2 |

---

## 2. 5KB Threshold Gating Design

### What context-mode does

Context-mode implements a binary routing decision based on output size and user intent:

```
if output.length > 5KB AND intent is provided:
    index full output into FTS5 knowledge base
    search for sections matching intent
    return only matching sections + vocabulary for follow-up queries
elif output.length > 5KB AND no intent:
    apply smart truncation (head 60% + tail 40%, line-boundary snapping)
else:
    pass through unchanged
```

The 5KB threshold is hardcoded. The smart truncation preserves both setup context (head) and error messages (tail), with a clear marker: `[47 lines / 3.2KB truncated -- showing first 12 + last 8 lines]`.

### Concrete proposal for EPYC

Add a `ThresholdRouter` class to the orchestrator's tool pipeline, positioned between tool execution and `_spill_if_truncated()`:

```python
# src/services/threshold_router.py

from dataclasses import dataclass
from enum import Enum

class OutputRoute(Enum):
    PASSTHROUGH = "passthrough"      # <= threshold, return as-is
    PATTERN_COMPRESS = "pattern"     # known command class, apply Phase 2 handler
    INDEX_AND_SUMMARIZE = "index"    # unknown command, large output -> FTS5

@dataclass
class RoutingDecision:
    route: OutputRoute
    original_size: int
    compressed_output: str
    retrieval_key: str | None = None  # FTS5 source ID for later retrieval

THRESHOLD_BYTES = 5120  # 5KB, matching context-mode's empirical choice

class ThresholdRouter:
    """Route tool outputs based on size and command classification."""

    def __init__(self, compressor, fts_store=None):
        self._compressor = compressor  # Phase 2 compress_tool_output module
        self._fts_store = fts_store    # Optional FTS5 store for indexing

    def route(self, output: str, command: str, intent: str = "") -> RoutingDecision:
        size = len(output.encode('utf-8'))

        if size <= THRESHOLD_BYTES:
            return RoutingDecision(
                route=OutputRoute.PASSTHROUGH,
                original_size=size,
                compressed_output=output,
            )

        # Try pattern-based compression first (Phase 2 handlers)
        compressed = self._compressor.compress(command, output)
        if compressed != output:
            return RoutingDecision(
                route=OutputRoute.PATTERN_COMPRESS,
                original_size=size,
                compressed_output=compressed,
            )

        # No pattern match -- index and summarize if FTS store available
        if self._fts_store and intent:
            source_id = self._fts_store.index(output, label=command)
            results = self._fts_store.search(intent, source=command)
            summary = self._format_search_results(results, command)
            return RoutingDecision(
                route=OutputRoute.INDEX_AND_SUMMARIZE,
                original_size=size,
                compressed_output=summary,
                retrieval_key=str(source_id),
            )

        # Fallback: smart truncation (head 60% + tail 40%)
        return RoutingDecision(
            route=OutputRoute.PASSTHROUGH,
            original_size=size,
            compressed_output=self._smart_truncate(output),
        )

    def _smart_truncate(self, output: str, max_lines: int = 40) -> str:
        """Head 60% + tail 40% with line-boundary snapping."""
        lines = output.split('\n')
        if len(lines) <= max_lines:
            return output
        head_count = int(max_lines * 0.6)
        tail_count = max_lines - head_count
        truncated_count = len(lines) - head_count - tail_count
        truncated_bytes = sum(len(l) for l in lines[head_count:-tail_count])
        head = '\n'.join(lines[:head_count])
        tail = '\n'.join(lines[-tail_count:])
        marker = (
            f"\n... [{truncated_count} lines / "
            f"{truncated_bytes / 1024:.1f}KB truncated -- "
            f"showing first {head_count} + last {tail_count} lines] ...\n"
        )
        return head + marker + tail
```

### Where this fits in the existing pipeline

```
helpers.py:1497 (feature flag: tool_output_compression)
    |
    v
compress_tool_output.py (Phase 2, pattern-based)
    |
    v
[NEW] ThresholdRouter.route()  <-- catches outputs that Phase 2 didn't compress
    |
    v
_spill_if_truncated() (1500 char preview + /tmp spill)
```

The threshold router is a safety net after Phase 2. If a command matches a Phase 2 handler, the router sees already-compressed output (likely under 5KB) and passes through. If no handler matched, the router catches it before it reaches the 8192-char hard truncation in `truncate_output()` -- which currently just cuts at a byte boundary with no head/tail preservation.

### Threshold tuning

Context-mode's 5KB threshold is tuned for Claude Code's 200K context window (5KB = ~1250 tokens = 0.6% of context). For EPYC's local llama.cpp sessions with 8K-32K windows:

| Context Window | Suggested Threshold | Rationale |
|---------------|-------------------|-----------|
| 200K (Claude API) | 5KB | context-mode's default, 0.6% of window |
| 32K (llama.cpp) | 2KB | 0.6% equivalent for 32K |
| 8K (constrained) | 1KB | Aggressive -- almost everything gets compressed |

Make it configurable via `TOOL_OUTPUT_THRESHOLD_BYTES` env var.

---

## 3. PreCompact Snapshot Pattern for Context Folding

### What context-mode does

The `precompact.mjs` hook fires when the host platform is about to compact the conversation. It:

1. Reads all captured session events from SQLite (`SessionDB.getEvents(sessionId)`)
2. Calls `buildResumeSnapshot(events, { compactCount })` to produce a priority-tiered XML snapshot
3. Stores the snapshot in the `session_resume` table
4. The subsequent `sessionstart.mjs` hook retrieves this snapshot and injects it into the new context

The snapshot builder (`session-snapshot.bundle.mjs`) groups events by category and renders them as XML sections with strict budget control:

```xml
<session_resume events="47" compact_count="2" generated_at="2026-04-20T...">

  <how_to_search>
  Each section below contains a summary of prior work.
  For FULL DETAILS, run the exact tool call shown under each section.
  Do NOT ask the user to re-explain prior work. Search first.
  </how_to_search>

  <files count="12">
    context_manager.py (edit x3, read x1)
    eval_tower.py (read x2)
    For full details:
    ctx_search(queries: ["context_manager.py", "eval_tower.py"], source: "session-events")
  </files>

  <errors count="2">
    TypeError: 'NoneType' has no attribute 'compress'
    AssertionError in test_threshold_router
    For full details:
    ctx_search(queries: ["TypeError NoneType compress", "AssertionError threshold_router"], source: "session-events")
  </errors>

  <decisions count="1">
    use 5KB threshold, not 4KB
    For full details:
    ctx_search(queries: ["threshold decision"], source: "session-events")
  </decisions>

  <task_state count="3">
    [pending] implement ThresholdRouter
    [pending] add FTS5 store integration
    [pending] write tests for smart truncation
  </task_state>

  <environment>
    cwd: /mnt/raid0/llm/epyc-orchestrator
  </environment>

  <intent mode="implement"/>
</session_resume>
```

Key design properties:
- **2KB budget**: the snapshot must fit within ~500 tokens. Lower-priority categories (intent, MCP counts, skills) are dropped first.
- **Progressive disclosure**: each section includes pre-computed `ctx_search()` queries so the model can retrieve full details without asking the user.
- **Priority tiers**: P1 (files, tasks, rules, user prompts) > P2 (errors, decisions, git, env) > P3 (MCP tools, subagents, skills) > P4 (intent, data references).
- **Deduplication**: files are aggregated (operation counts), not listed per-event.

### EPYC adoption: PreCompact for context-folding-progressive

The context-folding handoff's `ConsolidatedSegment` dataclass already captures per-segment state. The missing piece is **what to preserve across compaction boundaries**. Context-mode's snapshot schema maps directly onto EPYC's needs.

Proposed `CompactionSnapshot` for the orchestrator:

```python
# src/graph/compaction_snapshot.py

from dataclasses import dataclass, field
from enum import IntEnum

class Priority(IntEnum):
    CRITICAL = 1  # Always preserved
    HIGH = 2      # Preserved unless budget exceeded
    NORMAL = 3    # Preserved if budget allows
    LOW = 4       # Dropped first

@dataclass
class SnapshotSection:
    category: str          # "files", "errors", "decisions", "tasks", "git", "env"
    priority: Priority
    entries: list[str]     # Deduplicated, aggregated entries
    retrieval_queries: list[str]  # Pre-computed search queries for FTS5

@dataclass
class CompactionSnapshot:
    """Priority-tiered session state snapshot for injection after compaction."""

    event_count: int
    compact_count: int
    generated_at: str  # ISO-8601
    sections: list[SnapshotSection] = field(default_factory=list)
    max_bytes: int = 2048  # 2KB budget matching context-mode

    def render_xml(self) -> str:
        """Render snapshot as XML for prompt injection.

        Drops lowest-priority sections first to stay within budget.
        """
        parts = []
        budget = self.max_bytes - 200  # header/footer overhead

        # Sort by priority (CRITICAL first)
        sorted_sections = sorted(self.sections, key=lambda s: s.priority)

        for section in sorted_sections:
            rendered = self._render_section(section)
            if len(rendered.encode('utf-8')) <= budget:
                parts.append(rendered)
                budget -= len(rendered.encode('utf-8'))
            # else: silently drop (budget exceeded)

        header = (
            f'<session_resume events="{self.event_count}" '
            f'compact_count="{self.compact_count}" '
            f'generated_at="{self.generated_at}">'
        )
        body = '\n\n'.join(parts)
        return f"{header}\n\n{body}\n\n</session_resume>"

    def _render_section(self, section: SnapshotSection) -> str:
        entries = '\n    '.join(section.entries[:10])  # cap per-section
        queries = ', '.join(f'"{q}"' for q in section.retrieval_queries[:4])
        search_hint = (
            f"\n    For full details: search(queries=[{queries}])"
            if section.retrieval_queries else ""
        )
        return (
            f'  <{section.category} count="{len(section.entries)}">\n'
            f'    {entries}'
            f'{search_hint}\n'
            f'  </{section.category}>'
        )
```

### What state needs preserving across compaction

Mapping context-mode's categories to EPYC orchestrator state:

| Category | EPYC Equivalent | Priority | Source |
|----------|-----------------|----------|--------|
| files | Files modified by tool steps | CRITICAL | `ContextManager._entries` where type=ARTIFACT |
| tasks | Active `StepExecution` items | CRITICAL | `DispatchResult.steps` |
| rules | Active routing bindings / persona | CRITICAL | `routing_bindings.py` state |
| errors | Failed steps with error messages | HIGH | `StepResult` where status=FAILED |
| decisions | Escalation decisions, role overrides | HIGH | Escalation history in `TaskState` |
| git | Commits made during session | HIGH | Git ops tracked in session log |
| environment | Active model servers, loaded models | HIGH | `ModelServer` registry state |
| intent | Current task type (eval, develop, debug) | LOW | `TaskIR.task_type` |

### Integration with existing two-level condensation

The snapshot fires at the same trigger points as Phase 1's Tier 2 consolidation:
- Compaction trigger threshold reached (75%)
- Escalation boundary
- Sub-task completion

The snapshot captures **cross-segment state** that individual `ConsolidatedSegment` objects do not: which files are still being worked on, which errors are unresolved, what the user last asked for. It complements the segment-based condensation rather than replacing it.

---

## 4. FTS5 Indexing for Tool Output

### What context-mode does

The `ContentStore` class (`src/store.ts`) implements a full-text search engine using SQLite FTS5:

- **Chunking**: splits markdown by headings, keeping code blocks intact, with a 4096-byte max chunk size
- **Dual tokenizer strategy**: Porter stemming (FTS5 MATCH with `tokenize='porter unicode61'`) + trigram tokenizer for substring matching
- **RRF fusion**: both strategies run in parallel, results merged via Reciprocal Rank Fusion (score = 1/(k+rank), k=60)
- **Proximity reranking**: multi-term queries boost results where terms appear close together
- **Fuzzy correction**: Levenshtein distance corrects typos before re-searching
- **Smart snippets**: extraction windows around matching terms instead of truncation
- **Title weighting**: 5x BM25 weight on titles/headings
- **Stopword filtering**: 100+ stopwords including code-specific terms ("update", "fix", "test")
- **Progressive throttling**: calls 1-3 normal, 4-8 reduced, 9+ blocked (redirects to batch)

Schema (reconstructed from source):

```sql
-- Porter stemming table
CREATE VIRTUAL TABLE content_fts USING fts5(
    title, content, content_type, label,
    tokenize='porter unicode61',
    content='content_data',
    content_rowid='id'
);

-- Trigram table for substring matching
CREATE VIRTUAL TABLE content_trigram USING fts5(
    title, content,
    tokenize='trigram',
    content='content_data',
    content_rowid='id'
);

-- Source metadata
CREATE TABLE content_sources (
    id INTEGER PRIMARY KEY,
    label TEXT NOT NULL,
    url TEXT,
    fetched_at TEXT,
    total_chunks INTEGER,
    code_chunks INTEGER,
    ttl_hours INTEGER DEFAULT 24
);

-- Backing data table
CREATE TABLE content_data (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES content_sources(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL,  -- 'code' | 'prose'
    label TEXT NOT NULL
);
```

### EPYC FTS5 store design

For the orchestrator, the FTS5 store serves a different purpose than context-mode's knowledge base. Context-mode indexes documentation and API references. EPYC needs to index **ephemeral tool outputs** -- benchmark results, server logs, eval scores -- that the controller may need to query during a session.

```python
# src/services/tool_output_store.py

import sqlite3
from pathlib import Path
from dataclasses import dataclass

@dataclass
class SearchResult:
    title: str
    content: str
    source_label: str
    rank: float
    content_type: str  # "log", "benchmark", "eval", "structured"

class ToolOutputStore:
    """FTS5-backed store for large tool outputs.

    Indexes outputs that exceed the threshold router's passthrough limit.
    Provides intent-driven retrieval when the controller needs specific
    data from a previous tool execution.

    Lifecycle: one store per orchestrator session. Cleared on session end.
    Storage: /mnt/raid0/llm/tmp/tool_output_store_{session_id}.db
    """

    def __init__(self, session_id: str, db_dir: Path = Path("/mnt/raid0/llm/tmp")):
        self._db_path = db_dir / f"tool_output_store_{session_id}.db"
        self._conn = sqlite3.connect(str(self._db_path))
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;

            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY,
                label TEXT NOT NULL,
                command TEXT,
                indexed_at TEXT DEFAULT (datetime('now')),
                chunk_count INTEGER DEFAULT 0,
                original_bytes INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                source_id INTEGER REFERENCES sources(id),
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'log'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                title, content,
                tokenize='porter unicode61',
                content='chunks',
                content_rowid='id'
            );
        """)

    def index(self, output: str, label: str, command: str = "") -> int:
        """Index a tool output, chunking by logical boundaries.

        Returns source_id for later retrieval.
        """
        chunks = self._chunk_output(output, label)
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO sources (label, command, original_bytes, chunk_count) "
            "VALUES (?, ?, ?, ?)",
            (label, command, len(output.encode('utf-8')), len(chunks))
        )
        source_id = cur.lastrowid
        for title, content, ctype in chunks:
            cur.execute(
                "INSERT INTO chunks (source_id, title, content, content_type) "
                "VALUES (?, ?, ?, ?)",
                (source_id, title, content, ctype)
            )
        self._conn.commit()
        # Rebuild FTS index
        self._conn.execute(
            "INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')"
        )
        self._conn.commit()
        return source_id

    def search(self, query: str, source_label: str = "",
               max_results: int = 5) -> list[SearchResult]:
        """BM25-ranked search over indexed outputs."""
        sanitized = self._sanitize_query(query)
        if not sanitized:
            return []

        sql = """
            SELECT c.title, c.content, s.label, rank, c.content_type
            FROM chunks_fts
            JOIN chunks c ON chunks_fts.rowid = c.id
            JOIN sources s ON c.source_id = s.id
            WHERE chunks_fts MATCH ?
        """
        params = [sanitized]
        if source_label:
            sql += " AND s.label = ?"
            params.append(source_label)
        sql += " ORDER BY rank LIMIT ?"
        params.append(max_results)

        results = []
        for row in self._conn.execute(sql, params):
            results.append(SearchResult(
                title=row[0], content=row[1], source_label=row[2],
                rank=row[3], content_type=row[4]
            ))
        return results

    def _chunk_output(self, output: str, label: str,
                      max_chunk_bytes: int = 4096) -> list[tuple[str, str, str]]:
        """Split output into searchable chunks.

        Strategy varies by content type:
        - Log files: chunk by blank-line-separated blocks
        - Benchmark results: chunk by test/question boundaries
        - Structured (JSON/YAML): chunk by top-level keys
        - Default: chunk by paragraph (double newline)
        """
        chunks = []
        paragraphs = output.split('\n\n')
        current_chunk = []
        current_size = 0

        for i, para in enumerate(paragraphs):
            para_size = len(para.encode('utf-8'))
            if current_size + para_size > max_chunk_bytes and current_chunk:
                content = '\n\n'.join(current_chunk)
                chunks.append((f"{label} chunk {len(chunks)+1}", content, "log"))
                current_chunk = []
                current_size = 0
            current_chunk.append(para)
            current_size += para_size

        if current_chunk:
            content = '\n\n'.join(current_chunk)
            chunks.append((f"{label} chunk {len(chunks)+1}", content, "log"))

        return chunks

    def _sanitize_query(self, query: str) -> str:
        """Sanitize query for FTS5 MATCH, matching context-mode's approach."""
        import re
        words = re.sub(r"['\"\(\)\{\}\[\]\*:^~]", " ", query).split()
        meaningful = [
            w for w in words
            if w.upper() not in ("AND", "OR", "NOT", "NEAR")
            and len(w) > 0
        ]
        if not meaningful:
            return '""'
        return " ".join(f'"{w}"' for w in meaningful)

    def close(self):
        self._conn.close()

    def cleanup(self):
        """Delete the database file."""
        self.close()
        self._db_path.unlink(missing_ok=True)
```

### High-value indexing targets in EPYC

| Output Source | Typical Size | Query Patterns | Chunks Expected |
|-------------|-------------|----------------|-----------------|
| `eval_tower.py` results | 5-30KB per tier | "which questions failed", "route X accuracy", "worst scoring model" | 10-50 per eval run |
| `orchestrator_stack.py` logs | 10-100KB | "startup errors", "model loading time", "OOM events" | 20-100 per session |
| Benchmark sweep results | 20-200KB | "best p_split for 7B", "throughput at batch size 8" | 50-200 per sweep |
| `seeding_scoring.py` details | 5-50KB | "wrong answers for math", "scoring distribution" | 10-50 per seeding run |
| Model registry diffs | 8-15KB | "what changed for coder role", "new quant options" | 5-10 per registry |

### RRF fusion: worth adopting?

Context-mode runs Porter stemming and trigram matching in parallel with RRF (k=60) fusion. For EPYC's use case (tool outputs, not documentation), Porter stemming alone is likely sufficient. The trigram strategy adds value for substring matching in code ("useEff" -> "useEffect"), but tool output searches are typically natural-language queries ("which tests failed", "what was the throughput").

**Recommendation**: Start with Porter-only FTS5. Add trigram + RRF later if search quality proves insufficient. This halves the schema complexity and query cost.

---

## 5. Impact on AutoPilot

### Current context inflation profile

An autopilot session running a T1 eval (100 questions) generates approximately:

| Source | Per-Question | Total (100q) | After Phase 2 | After Phase 2 + Sandbox |
|--------|-------------|--------------|----------------|------------------------|
| Question + expected answer | 200B | 20KB | 20KB (no change) | 20KB (no change) |
| Model answer | 500B-2KB | 50-200KB | 50-200KB (no change) | 50-200KB (no change) |
| Scoring details | 500B-1KB | 50-100KB | 50-100KB (no change) | 200B summary + FTS5 |
| Route/timing metadata | 200B | 20KB | 20KB (no change) | 20KB (no change) |
| **Orchestrator prompt context** | | **140-340KB** | **140-340KB** | **110-260KB** |

The scoring details are the primary target. Currently, each `QuestionResult` includes full answer text and scoring rationale. With the sandbox pattern, scoring details are indexed to FTS5 and only the pass/fail + score is returned to the controller prompt.

### Token savings estimates by intervention

| Intervention | Mechanism | Est. Savings | Implementation Effort |
|-------------|-----------|-------------|----------------------|
| Threshold router on tool outputs | Route >5KB to FTS5, return summary | 15-25% of total context | Medium (new module) |
| Smart truncation (head+tail) | Replace byte-boundary cut with head 60%/tail 40% | 5-10% (preserves error info, no size change) | Low (modify `truncate_output()`) |
| PreCompact snapshots | Preserve essential state across compaction | 0% direct savings, but prevents re-exploration | Medium (new module + hook) |
| FTS5 for eval results | Index scoring details, return pass/fail only | 20-40% during eval runs | Medium (new store) |
| **Combined** | | **30-50% context reduction in eval-heavy sessions** | |

### Compaction frequency reduction

The indirect benefit is more significant than raw token savings. With less context inflation per tool call, the compaction trigger fires less frequently:

- Current: compaction fires every ~25-30 tool calls (at 75% of 32K = 24K tokens)
- After compression: compaction fires every ~40-50 tool calls
- Fewer compactions = less information loss = higher task completion rate

This directly addresses the handoff's note: "Session time extends from ~30 minutes to ~3 hours" -- not from compression alone, but from reduced compaction frequency.

---

## 6. Implementation Roadmap

### Phase A: Smart Truncation (1 day)

**What**: Replace `truncate_output()` byte-boundary cut with head 60% / tail 40% line-snapping.

**Where**: `src/tools/base.py:80-95` (the 8192-char hard cap)

**Why first**: Zero new dependencies, zero risk, immediate quality improvement. Error messages currently lost to tail truncation are preserved. This is a pure upgrade to existing code.

**Dependencies**: None.

### Phase B: Threshold Router (2-3 days)

**What**: Add `ThresholdRouter` class with configurable threshold. Wire into `helpers.py` after Phase 2 compression, before `_spill_if_truncated()`.

**Where**: New file `src/services/threshold_router.py`, integration at `helpers.py:1497`.

**Why second**: Catches the long tail of outputs that Phase 2 handlers miss. Does not require FTS5 -- fallback is smart truncation from Phase A.

**Dependencies**: Phase A (for the smart truncation fallback).

### Phase C: FTS5 Tool Output Store (3-5 days)

**What**: Implement `ToolOutputStore` with per-session SQLite database. Wire into threshold router's `INDEX_AND_SUMMARIZE` path.

**Where**: New file `src/services/tool_output_store.py`.

**Why third**: Enables the full index-and-retrieve pattern. Requires the router (Phase B) to know when to index vs pass through.

**Dependencies**: Phase B. SQLite3 is already available (Python stdlib). No new pip dependencies.

**Risk**: SQLite FTS5 extension may not be compiled into the system Python's sqlite3 module. Mitigation: test `CREATE VIRTUAL TABLE ... USING fts5(...)` at startup. If FTS5 unavailable, the router falls back to smart truncation only. On the EPYC server (Ubuntu), FTS5 is enabled by default in Python 3.10+.

### Phase D: PreCompact Snapshot (3-5 days)

**What**: Implement `CompactionSnapshot` with priority-tiered XML rendering. Integrate with context-folding's compaction trigger points.

**Where**: New file `src/graph/compaction_snapshot.py`, integration in `helpers.py` at compaction trigger.

**Why fourth**: Requires understanding of what state is being captured (informs snapshot categories). Phases A-C provide the tool output compression that reduces what needs to be captured. Also requires FTS5 store (Phase C) for the "search for full details" retrieval pointers.

**Dependencies**: Phase C (for retrieval pointers in snapshot), context-folding Phase 1 (for `ConsolidatedSegment` data).

### Phase E: MCP Tool Wrapping for Claude Code (2-3 days)

**What**: Wrap Phase 2 compressors + threshold router as MCP tools. Register in root-archetype settings. SessionStart hook for routing instructions.

**Where**: New MCP server definition (possibly in `epyc-root/scripts/mcp/`), `.claude/settings.json` registration.

**Why last**: Requires all compression infrastructure (Phases A-C) to exist. This is the delivery mechanism for Claude Code sessions, not the compression logic itself.

**Dependencies**: Phases A-C. Claude Code MCP server API.

**Risk**: SessionStart hook injection of routing instructions may be fragile across Claude Code updates. Mitigation: fall back to CLAUDE.md-based routing instructions (lower compliance but still functional).

### Dependency graph

```
Phase A (smart truncation)
    |
    v
Phase B (threshold router) ----> Phase E (MCP tools for Claude Code)
    |
    v
Phase C (FTS5 store) ----------> Phase E
    |
    v
Phase D (PreCompact snapshot)
```

Phases A and B are independently valuable without the rest. Phase C unlocks the full context-mode-style pattern. Phase D and E are quality-of-life improvements built on the foundation.

---

## 7. Intake Verdict Delta

**Pre-deep-dive verdict**: `adopt_patterns`

**Post-deep-dive verdict**: `adopt_patterns` -- **confirmed and narrowed**.

### Patterns to adopt

1. **Subprocess sandbox isolation** (via MCP tool wrapping) -- directly solves the PostToolUse hook limitation documented in tool-output-compression.md Phase 2. This is the highest-value pattern.

2. **5KB threshold gating** -- simple, empirically validated heuristic. The threshold itself may need tuning for EPYC's smaller context windows, but the binary routing decision (passthrough vs index-and-summarize) is sound.

3. **Head 60% / tail 40% smart truncation** -- trivial to implement, strictly better than current byte-boundary cut. Should be adopted immediately.

4. **PreCompact priority-tiered XML snapshot** -- the schema and budget discipline (2KB, priority-ordered section dropping) are well-designed. The progressive-disclosure pattern (summary + pre-computed search queries) is genuinely novel vs the context-folding handoff's current approach.

5. **FTS5 with Porter stemming for tool outputs** -- the basic pattern is worth adopting. The full RRF + trigram + fuzzy correction stack is over-engineered for EPYC's use case.

### Patterns to skip

1. **11-language polyglot runtime** -- EPYC only needs Python and shell. The runtime detection and compilation infrastructure is irrelevant.

2. **24-hour TTL URL cache** -- EPYC does not fetch external URLs during orchestrator sessions. Not applicable.

3. **Progressive throttling** (calls 1-3 normal, 4-8 reduced, 9+ blocked) -- designed for interactive Claude Code sessions where the human might abuse search. EPYC's programmatic orchestrator controls call frequency directly.

4. **Platform adapter matrix** (12 platforms) -- EPYC targets one platform (its own orchestrator + Claude Code root-archetype). The abstraction layer is unnecessary.

5. **Session event extraction from tool calls** (the `extractEvents` module) -- context-mode extracts events by pattern-matching tool names and inputs. EPYC's orchestrator has structured `StepResult` and `TurnRecord` objects that already capture this data with higher fidelity.

### License note

ELv2 prohibits providing the software as a managed service. Since EPYC is adopting **patterns** (architectural decisions, schema designs, threshold heuristics) rather than copying code, there is no license concern. All code in this deep dive is original.

### Delta from intake-414 (Token Savior)

intake-414 focuses on AST-level symbol navigation (structural code understanding). Context-mode focuses on **tool output compression** (runtime data). They are complementary, not competing:
- Token Savior: reduces context from code reads (file content)
- Context Mode: reduces context from command execution (tool output)

EPYC should adopt patterns from both: Token Savior's content-hash staleness detection for code, context-mode's threshold gating for tool outputs.

### Delta from intake-395 (claude-mem)

claude-mem's 3-layer progressive disclosure (`search -> timeline -> get_observations`) is a client-side convention, not a server-side retrieval system. Context-mode's FTS5 + BM25 is a genuine server-side search with ranking. EPYC should adopt context-mode's store design over claude-mem's.

### Delta from Phase 2 (existing tool-output-compression)

Phase 2 is pattern-based compression (pytest -> failure focus, git diff -> hunk focus). Context-mode adds:
- **Catch-all for unmatched outputs** via threshold gating + FTS5 indexing
- **Retrieval path** for later querying of compressed-away data
- **Smart truncation** as a better fallback than byte-boundary cut

These are complementary layers. Phase 2 handles known command classes with high compression ratios. The context-mode patterns handle the long tail of unknown outputs and provide a retrieval mechanism for data that was compressed away.
