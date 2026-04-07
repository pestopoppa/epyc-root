# qmd Semantic Search Addon

Documentation for integrating [tobi/qmd](https://github.com/tobi/qmd) as a
semantic search layer for the research-intake skill. **Deployment is a separate
work item** — this document captures the integration pattern.

## Overview

qmd is a local hybrid search engine for markdown knowledge bases. It combines
BM25 full-text search, vector semantic search, and LLM re-ranking into a single
pipeline — all running locally via node-llama-cpp with GGUF models.

## Model Requirements

~2GB total GGUF models on CPU (no GPU required):

| Model | Size | Purpose |
|-------|------|---------|
| Embedding (~300M params) | ~600MB | Semantic vector encoding |
| Reranker (~600M params) | ~800MB | Cross-encoder relevance scoring |
| Query expansion (~1.7B params) | ~700MB | Expand terse queries for better recall |

All models run via node-llama-cpp. No API keys needed.

## Search Pipeline

1. **Query expansion**: LLM rewrites the query into multiple search variants
2. **BM25 full-text search**: Fast keyword matching across all indexed documents
3. **Vector semantic search**: Embedding similarity for conceptual matches
4. **Reciprocal Rank Fusion (RRF)**: Merge BM25 and vector results
5. **LLM re-ranking**: Cross-encoder scores top candidates for final ordering
6. **Position-aware blending**: Combine re-ranked results with positional context

## MCP Server Integration

qmd provides an MCP server that exposes two tools:

- `query` — search the corpus, returns ranked results with snippets
- `get` — retrieve a specific document by path

To integrate with Claude Code, add to `.claude/settings.json` (or project MCP config):

```json
{
  "mcpServers": {
    "qmd": {
      "command": "npx",
      "args": ["qmd", "serve", "--corpus", "/workspace"]
    }
  }
}
```

## Corpus Configuration

Point at the repo root (~359 markdown files):

```
/workspace/
├── research/          # intake_index.yaml, taxonomy.yaml, deep-dives/
├── handoffs/          # active/, completed/, archived/
├── progress/          # daily session logs
├── wiki/              # SCHEMA.md, future wiki pages
├── agents/            # role definitions
└── .claude/skills/    # skill definitions
```

## Use Case: Replace Grep-Based Cross-Referencing

Currently, Phase 2 of research-intake uses keyword grep to find related
chapters, handoffs, and experiments. qmd would replace this with semantic search:

- **Before**: `grep "speculative decoding" handoffs/active/*.md`
- **After**: `query("techniques similar to speculative decoding")` returns
  conceptually related handoffs even when they use different terminology

This improves recall on entries where the technique name differs from existing
vocabulary (e.g., "draft-verify paradigm" vs "speculative decoding").

## Natural Markdown Chunking Algorithm

qmd uses a break-point scoring system for semantic chunking:

| Break Point | Score |
|-------------|-------|
| H1 heading | 100 |
| H2 heading | 90 |
| H3 heading | 80 |
| H4 heading | 70 |
| H5 heading | 60 |
| H6 heading | 50 |
| Code fence boundary | 80 |
| Blank line | 20 |

Scores decay with squared distance from the break point. This produces chunks
that align with document structure rather than splitting mid-paragraph.

This algorithm is directly applicable to context-folding segment boundary
detection (noted in cross-cutting concern #4 of the KB governance handoff).

## Deployment Notes

- Requires Node.js 18+
- First run indexes the corpus (~30s for 359 files)
- Index is cached locally, incremental updates on file changes
- Memory: ~2GB for models + ~100MB for index
- Latency: <500ms per query on CPU
