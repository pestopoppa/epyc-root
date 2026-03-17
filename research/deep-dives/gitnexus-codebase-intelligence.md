# Deep Dive: GitNexus — Codebase Intelligence for Coding Agents

**Date**: 2026-03-16
**Intake**: intake-151
**Source**: https://github.com/abhigyanpatwari/GitNexus
**License**: PolyForm Noncommercial 1.0.0 (source-available, personal use OK)

## Why This Matters for EPYC

Our coder_escalation and architect_coding nodes currently discover dependencies through trial-and-error REPL cycles — grep for a function name, read the file, find it calls something else, grep again. This is O(N) in dependency depth and burns REPL turns + tokens on exploration that yields no code. GitNexus precomputes the entire dependency graph at index time and serves it in single-query tool responses. The coding agent gets decision-ready context *before* writing code.

**Concrete gap**: When our coder modifies `_execute_turn()` in helpers.py, it has no awareness that 7 node classes call it, that it depends on 15+ helper functions, or that changing its return signature would break the entire graph. GitNexus's `impact` tool answers this in one call.

## Architecture Overview

### 8-Phase Indexing Pipeline

```
Phase 1: STRUCTURE     → File/folder tree, CONTAINS edges
Phase 2: PARSING       → Tree-sitter ASTs → SYMBOL nodes (13 languages)
Phase 3: IMPORTS       → Cross-file import resolution, path normalization
Phase 4: CALLS         → Function call tracking with confidence scores
Phase 5: HERITAGE      → Inheritance (EXTENDS) + interface (IMPLEMENTS)
Phase 6: CLUSTERING    → Leiden community detection → functional groups
Phase 7: PROCESSES     → Entry point detection + execution flow tracing
Phase 8: SEARCH INDEX  → BM25 + semantic embeddings (snowflake-arctic-embed-xs) + HNSW
```

### Graph Schema (KuzuDB Property Graph)

**Nodes**:
- `FILE` (path, size, language)
- `FOLDER` (name, depth)
- `SYMBOL` (name, kind, signature, line, column, isExported)
  - kind: Function | Class | Method | Interface
- `CLUSTER` (name, cohesion, separability)
- `PROCESS` (name, entrySymbol, steps)

**Edges**:
- `CONTAINS` — file/folder hierarchy
- `IMPORTS` — module imports (confidence 0.8–0.95)
- `CALLS` — function calls (confidence 0.3–0.9)
- `EXTENDS` — class inheritance
- `IMPLEMENTS` — interface implementation
- `DEFINES` — file → symbol ownership
- `MEMBER_OF` — symbol → cluster membership
- `STEP_IN` — symbol → process participation

### Confidence Scoring on CALLS Edges

This is a key design decision — not all call relationships are equally certain:

| Resolution Method | Confidence | Description |
|---|---|---|
| Import-resolved | 0.90 | Explicit import traced to target |
| Same-file | 0.85 | No import needed, same scope |
| Fuzzy single match | 0.50 | One candidate found globally |
| Fuzzy multi-match | 0.30 | Ambiguous, multiple candidates |

Tools default to `minConfidence=0.7` to exclude guesses. This lets the agent distinguish "definitely calls X" from "might call X" — critical for impact analysis.

## 7 MCP Tools

### 1. `query` — Process-Grouped Hybrid Search

```
Input:  natural language query + optional process filter
Pipeline:
  1. BM25 keyword search → top 5
  2. Semantic embedding search (HNSW) → top 5
  3. Reciprocal Rank Fusion (k=60) → merged top 10
  4. 1-hop graph expansion (add CALLS/IMPORTS neighbors)
  5. Group by PROCESS (execution flow)
Output: ProcessGroup[] with symbols, definitions, call chains
```

**Key insight**: Results are grouped by execution flow, not raw symbol list. Agent sees "LoginFlow: route → validate → fetchUser → createSession" instead of 4 disconnected functions.

### 2. `context` — 360-Degree Symbol View

```
Input:  symbol name (e.g., "validateUser")
Output:
  - Symbol metadata (kind, file, line)
  - Incoming refs (who calls this, with confidence)
  - Outgoing refs (what this calls)
  - Process participation (which flows include this)
  - Cluster membership (functional area + cohesion score)
```

Maps directly to: "Before modifying this function, here's everything that depends on it and everything it depends on."

### 3. `impact` — Blast Radius Analysis

```
Input:  target symbol + direction (upstream/downstream) + minConfidence
Output:
  depth1: WILL BREAK (direct callers/callees)
  depth2: LIKELY AFFECTED (indirect)
  depth3: MAY NEED TESTING (transitive)
  Grouped by cluster with confidence aggregation
```

Example output: "8 production callers in 3 clusters: Auth [3, 90%+], Payment [2, 85%], API [3, 90%]"

### 4. `detect_changes` — Pre-Commit Impact Mapping

```
Input:  staged git diff
Output:
  - Changed symbols (modified/added/deleted)
  - Downstream impact per symbol
  - Regression risk: LOW | MEDIUM | HIGH | CRITICAL
```

### 5. `rename` — Coordinated Multi-File Refactoring

```
Input:  old name, new name, dry_run flag
Output:
  - Edit list with file, line, old/new text
  - Method: "graph" (high confidence) vs "ast_search" (review carefully)
  - Affected file count
```

### 6. `cypher` — Raw Graph Queries

Direct Cypher queries against KuzuDB for anything the predefined tools don't cover.

### 7. `list_repos` — Repository Discovery

Lists all indexed repos with metadata (symbol count, languages, last indexed).

## Hybrid Search Implementation

```
                    ┌──────────────┐
                    │  User Query  │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼────────┐      ┌────────▼────────┐
     │  BM25 (lexical) │      │ Semantic (HNSW)  │
     │  TF-IDF scoring │      │ snowflake-arctic  │
     │  → Top 5        │      │ → Top 5           │
     └────────┬────────┘      └────────┬──────────┘
              │                         │
              └────────────┬────────────┘
                           │
                  ┌────────▼────────┐
                  │  RRF Fusion     │
                  │  score = Σ 1/(k+rank) │
                  │  k = 60         │
                  │  → Merged top 10│
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │ Graph Enrichment│
                  │ 1-hop CALLS +   │
                  │ IMPORTS + cluster│
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │ Process Grouping│
                  │ Group by flow   │
                  └─────────────────┘
```

## Leiden Clustering → Skill Generation

The Leiden algorithm partitions the call graph into communities (functional areas) by optimizing modularity. Each cluster gets:
- Cohesion score (internal coupling strength)
- Separability score (isolation from other clusters)
- Member symbols ranked by call density

When `--skills` flag is passed, each cluster generates a SKILL.md file:
```markdown
# [ClusterName] Skill
**Key Files**: file1.ts, file2.ts, file3.ts
**Entry Points**: validateUser(), processPayment()
**Execution Flows**:
  1. LoginFlow (5 steps): POST /auth → validate → fetch → session → response
**Dependencies**: Database cluster (3 calls), API cluster (5 calls)
```

These are installed as `.claude/skills/generated/` for Claude Code — targeted context per functional area.

## Integration Paths for EPYC

### Path A: Direct Use as MCP Tool Server (simplest)

```
gitnexus analyze /mnt/raid0/llm/epyc-orchestrator
gitnexus mcp  ← runs as stdio MCP server

Our orchestrator's coding agents call GitNexus MCP tools
via tool registry integration:
  - Before code generation: impact(target_function) → inject into prompt
  - After code generation: detect_changes(git diff) → verify blast radius
  - On error: context(failing_function) → understand dependencies
```

**Pros**: Zero reimplementation, immediate value
**Cons**: Node.js runtime dependency, can't customize indexing

### Path B: Python Reimplementation of Core Patterns

Reimplement the valuable patterns using our stack:

1. **AST parsing**: `tree-sitter` has Python bindings (`tree-sitter-python`, `tree-sitter-languages`)
2. **Graph storage**: NetworkX or igraph (in-memory) or KuzuDB (has Python bindings)
3. **Call resolution**: Symbol table + confidence scoring — straightforward port
4. **Clustering**: `leidenalg` Python package (same algorithm)
5. **Search**: We already have FAISS for MemRL — add BM25 via `rank_bm25` + RRF fusion
6. **Impact analysis**: Graph traversal with confidence filtering — standard BFS

**Estimated effort**: ~500-800 lines for core (parse + resolve + cluster + impact)
**Pros**: Full control, Python-native, no runtime dependencies
**Cons**: Significant upfront work, language support matrix to maintain

### Path C: Hybrid — Use GitNexus for Indexing, Query via Python

```
# Index phase (Node.js, one-time)
gitnexus analyze /mnt/raid0/llm/epyc-orchestrator

# Query phase (Python, via KuzuDB bindings)
import kuzu
db = kuzu.Database('.gitnexus/')
conn = kuzu.Connection(db)
result = conn.execute("""
    MATCH (caller)-[c:CALLS]->(target:Function {name: $name})
    WHERE c.confidence >= 0.7
    RETURN caller.name, caller.filePath, c.confidence
    ORDER BY c.confidence DESC
""", {"name": "validate_user"})
```

**Pros**: Use GitNexus's excellent indexing, query natively in Python
**Cons**: Still need Node.js for indexing, graph schema coupling

### Path D: REPL Tool Integration (minimal, highest ROI)

Add 3 new REPL tools to our orchestrator that shell out to `gitnexus` CLI:

```python
# In orchestration/tools/codebase_intelligence.py

@tool("codebase_impact")
def codebase_impact(symbol: str, min_confidence: float = 0.7) -> str:
    """Analyze blast radius before modifying a symbol."""
    # Shell out to gitnexus MCP or query KuzuDB directly
    ...

@tool("codebase_context")
def codebase_context(symbol: str) -> str:
    """Get 360-degree view of a symbol's relationships."""
    ...

@tool("codebase_changes")
def codebase_changes() -> str:
    """Analyze impact of current staged changes."""
    ...
```

Wire these into the coder_escalation and architect_coding prompt templates. The model calls `codebase_impact("_execute_turn")` before modifying it and gets "8 callers in 3 clusters" in one REPL turn instead of 5+ grep cycles.

**Pros**: Minimal code, immediate integration with existing tool registry
**Cons**: Subprocess overhead, limited customization

## Recommended Actions (Prioritized)

### HIGH — Immediate value

1. **Install and index**: `npx gitnexus analyze /mnt/raid0/llm/epyc-orchestrator` — see what the graph looks like for our codebase. Zero-risk exploration.

2. **Path D implementation**: Add 3 REPL tools (impact, context, changes) that query the GitNexus index. ~100 lines, integrates with existing tool registry. This alone would save 3-5 REPL turns per coding task by front-loading dependency context.

3. **Prompt injection**: When coder_escalation is about to modify a function, auto-inject its `context` output (callers, callees, cluster) into the prompt. Similar to how we inject `gathered_context` in `_execute_turn()`.

### MEDIUM — Deeper integration

4. **Pre-commit validation**: Wire `detect_changes` into our generation_monitor. After the coder produces code, check blast radius against the graph before accepting.

5. **Skill generation**: Run `gitnexus analyze --skills` on our orchestrator. The generated SKILL.md files per functional cluster could replace our manual agent role descriptions with data-driven ones.

6. **Hybrid search for MemRL**: The BM25 + semantic + RRF pattern is directly applicable to our episodic memory retrieval. Currently we use FAISS alone — adding BM25 lexical matching would improve retrieval for exact function/class name queries.

### LOWER — Long-term architecture

7. **Python reimplementation**: If GitNexus proves valuable but the Node.js dependency is friction, reimplement the core (AST → graph → cluster → impact) in Python. tree-sitter, leidenalg, and kuzu all have Python bindings.

8. **Cross-repo graph**: Index all 4 EPYC repos into one graph. GitNexus supports multi-repo via global registry. This would capture cross-repo dependencies (orchestrator → llama.cpp binary, research → orchestrator registry).

## Performance Characteristics

| Operation | Latency | Notes |
|---|---|---|
| Index (small repo, <1k files) | 2-5s | One-time |
| Index (medium, 5-10k files) | 30-60s | One-time |
| Hybrid search | <100ms | BM25 + semantic + RRF |
| Impact analysis | <500ms | Graph traversal + filtering |
| Context lookup | <50ms | Direct node retrieval |
| Storage per 10k symbols | 10-50MB | KuzuDB + HNSW index |

## Key Patterns Worth Adopting

### 1. Confidence-scored edges
Not all relationships are equally certain. Encoding confidence on CALLS edges lets tools filter by trust level. Our MemRL Q-values are analogous — confidence on routing decisions.

### 2. Precomputed relational intelligence
Index-time computation of clusters, processes, and impact analysis means single-query responses. Analogous to our prefix caching — front-load work to make runtime cheap.

### 3. Process-grouped results
Organizing search results by execution flow rather than raw symbol list gives the agent actionable context. We could apply this pattern to our session_log: group REPL turns by "what flow was the model working on."

### 4. Entry point scoring heuristic
The weighted scoring (exported +2.0, route pattern +1.5, handler pattern +1.0, framework location +0.8) for detecting process entry points is a simple, effective pattern. Applicable to our task_type classification.

### 5. Dual-confidence refactoring
The `rename` tool distinguishes graph-resolved edits (high confidence, apply automatically) from AST-search edits (lower confidence, flag for review). This graduated trust model maps to our cascading_tool_policy.
