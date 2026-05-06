---
name: kb-search
description: Semantic search over the project's compiled markdown knowledge base (wiki/, handoffs/active/, handoffs/completed/, research/, progress/, docs/chapters/). Use BEFORE grep/find when investigating a topic, looking up prior decisions, or searching for cross-cutting context. ColBERT-backed; returns ranked chunks with file path, heading breadcrumb, and line range.
---

# KB Search (Internal Markdown RAG)

Use this skill when an Explore subagent or session would otherwise grep/find blindly across:

- `wiki/` (24 compiled articles synthesizing 246 source documents)
- `handoffs/active/` (~53 in-progress work items)
- `handoffs/completed/` (historical decisions still load-bearing)
- `research/` (intake notes + deep-dives)
- `progress/YYYY-MM/` (daily session summaries)
- `docs/chapters/` (epyc-inference-research compiled chapters)

The retrieval index is ColBERT-backed (GTE-ModernColBERT-v1 ONNX INT8, 128-dim per-token, MaxSim ranking) — semantically richer than keyword grep, and aware of heading hierarchy.

## When to use

- "Where did we discuss X?" — semantic queries that may not share keywords with the target document.
- "What decisions did we make about Y?" — surface prior handoffs / progress entries.
- Topical / cross-cutting investigations spanning >1 file.
- Replacements for blind `grep -r "concept"` over the markdown corpus.

## When NOT to use

- Code search → use GitNexus (`gitnexus_query`) — code is in a separate index.
- Specific exact string match (file paths, error message tokens) → grep is faster and exact.
- Files outside the corpus globs (e.g. `agents/`, `scripts/`, `.claude/`) — those aren't indexed here.
- `handoffs/archived/` is INTENTIONALLY EXCLUDED — archived state is misleading by design.

## How to invoke

```bash
python3 /workspace/repos/epyc-orchestrator/scripts/kb_rag/cli.py query "your question"
```

Defaults: top-K = 8 ranked chunks. Add `--top-k 3` for tighter results, `--json` for parseable output.

Result schema:

```
[score]  /path/to/file.md:line_start-line_end
  H1 > H2 > H3                    # heading breadcrumb
  first 200 chars of chunk text...
```

## Workflow

1. Query the KB:
   ```
   python3 /workspace/repos/epyc-orchestrator/scripts/kb_rag/cli.py query "<question>"
   ```
2. Read the top 1-3 results in full via the `Read` tool using the returned `file_path` and `line_range`.
3. If results are insufficient, try a reformulated query (semantic variants, related concepts) before falling back to grep.
4. Cross-reference: the heading breadcrumb tells you exactly where in the file the chunk lives — useful for navigating long handoff documents.

## Refreshing the index

The index is rebuilt incrementally on commit via `.claude/hooks/post_commit_kb_rag_update.sh`. To rebuild from scratch:

```bash
python3 /workspace/repos/epyc-orchestrator/scripts/kb_rag/cli.py build
```

To check index state:

```bash
python3 /workspace/repos/epyc-orchestrator/scripts/kb_rag/cli.py stats
```

## Boundaries

- This skill is for the markdown corpus only. For code, use GitNexus tools.
- The encoder requires `onnxruntime` and the GTE-ModernColBERT-v1 ONNX model at `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/`. If absent, `kb_rag query` returns no results — fall back to grep.
- Index location: `/workspace/repos/epyc-orchestrator/data/kb_rag/index/` (gitignored).

## Verification

Before relying on the result of a `kb_rag query`:

1. Spot-check the top result's snippet against the original file via `Read`.
2. If the question was about a decision, confirm the `progress/` entry or handoff status reflects current state — KB-RAG returns chunks frozen at last index time.
3. For `handoffs/active/*.md` results: check the file's `Status` line — if "DONE" / "ARCHIVED", the recommendation may be stale.
