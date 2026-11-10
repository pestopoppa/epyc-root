---
name: kb-search
description: Semantic search over the project's compiled markdown knowledge base (wiki/, handoffs/active/, handoffs/completed/, research/, progress/, docs/chapters/). Use BEFORE grep/find when investigating a topic, looking up prior decisions, or searching for cross-cutting context. ColBERT-backed; returns ranked chunks with file path, heading breadcrumb, and line range.
---

# KB Search (Internal Markdown RAG)

Use this skill when an Explore subagent or session would otherwise grep/find blindly across:

- `wiki/` (compiled articles synthesizing the source documents; ~30 pages, see `wiki/INDEX.md`)
- `handoffs/active/` (~40 in-progress work items, 2026-11-09)
- `handoffs/completed/` (historical decisions still load-bearing)
- `research/` (intake notes + deep-dives)
- `progress/YYYY-MM/` (daily session summaries)
- `docs/chapters/` (epyc-inference-research compiled chapters)
- Agent memory is not yet indexed; see `/mnt/raid0/llm/tmp/ws58-kt5-memory-split-proposal.md` (KT-5).

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
/workspace/repos/epyc-orchestrator/.venv/bin/python /workspace/repos/epyc-orchestrator/scripts/kb_rag/cli.py query "your question"
```

> **Use the orchestrator venv interpreter, not bare `python3`.** The retrieval stack needs
> `numpy` + `onnxruntime`, which the devcontainer's system `python3` does not have — a bare
> `python3` invocation dies on `ModuleNotFoundError: numpy` inside `colbert_encoder.py`.
> Same convention as `.claude/hooks/post_commit_kb_rag_update.sh` (`KB_RAG_PYTHON`).
> If the venv interpreter itself is a dangling symlink, restore it with `uv python install 3.11`
> (its `pyvenv.cfg` pins a uv-managed CPython 3.11).

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
   /workspace/repos/epyc-orchestrator/.venv/bin/python /workspace/repos/epyc-orchestrator/scripts/kb_rag/cli.py query "<question>"
   ```
2. Read the top 1-3 results in full via the `Read` tool using the returned `file_path` and `line_range`.
3. If results are insufficient, try a reformulated query (semantic variants, related concepts) before falling back to grep.
4. Cross-reference: the heading breadcrumb tells you exactly where in the file the chunk lives — useful for navigating long handoff documents.

## Refreshing the index

The index is rebuilt incrementally on commit via `.claude/hooks/post_commit_kb_rag_update.sh`. To rebuild from scratch:

```bash
/workspace/repos/epyc-orchestrator/.venv/bin/python /workspace/repos/epyc-orchestrator/scripts/kb_rag/cli.py build
```

To check index state:

```bash
/workspace/repos/epyc-orchestrator/.venv/bin/python /workspace/repos/epyc-orchestrator/scripts/kb_rag/cli.py stats
```

## Boundaries

- This skill is for the markdown corpus only. For code, use GitNexus tools.
- The encoder requires `onnxruntime` and the GTE-ModernColBERT-v1 ONNX model at `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/`. If absent, `kb_rag query` returns no results — fall back to grep.
- Index location: `/mnt/raid0/llm/epyc-orchestrator/data/kb_rag/index-qd-v2/` (gitignored). Set `KB_RAG_INDEX_DIR` to override; default it with `KB_RAG_INDEX_DIR="${KB_RAG_INDEX_DIR:-/mnt/raid0/llm/epyc-orchestrator/data/kb_rag/index-qd-v2}"` before the query command below when unset.
- **Prefix convention (OP-24, 2026-08-12)**: the index records which ColBERT role
  convention produced its vectors (`index_meta.prefix_convention`), and `query`
  encodes the query the same way. The live store `index-qd-v2` (2026-11-09) uses the
  model's trained `[Q] ` / `[D] ` prefixes plus native PyLate tokenization and
  document punctuation pruning. Current code REFUSES the old `index-qd-v1` store
  (`IndexConventionError`), so it is not a rollback target; the prefix-free
  `data/kb_rag/index/` (convention `none`) still reads, via
  `KB_RAG_INDEX_DIR=.../data/kb_rag/index`. On a refused convention `query` returns
  no rows (fail closed), so an empty result over a known-good topic means: run
  `cli.py stats` and check `prefix_convention` before concluding "no hits". Never
  point the reader at a store built under a different convention.

## Verification

Before relying on the result of a `kb_rag query`:

1. Spot-check the top result's snippet against the original file via `Read`.
2. If the question was about a decision, confirm the `progress/` entry or handoff status reflects current state — KB-RAG returns chunks frozen at last index time.
3. For `handoffs/active/*.md` results: check the file's `Status` line — if "DONE" / "ARCHIVED", the recommendation may be stale.
