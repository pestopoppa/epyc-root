# Internal Knowledge-Base RAG

**Status**: stub (proposal — not yet started)
**Created**: 2026-04-25 (from local-RAG architecture review of friend's stack)
**Categories**: search_retrieval, knowledge_management, document_processing
**Priority**: MEDIUM
**Effort**: ~1–2 inference-free days end-to-end (minimal version)
**Depends on**: shared encoder layer extracted from `colbert-reranker-web-research.md` (S3/S4 ONNX runtime + GTE-ModernColBERT-v1 plumbing already in place)
**Sibling consumer**: [`colbert-reranker-web-research.md`](colbert-reranker-web-research.md) — reuses the same ONNX/MaxSim encoder, but for *external* search snippets gated on AR-3 data. This handoff is for *internal* knowledge and is **not** AR-3-gated.

## Objective

Stand up a ColBERT-based RAG over our own markdown knowledge base so every Explore-agent invocation can retrieve relevant prior context instead of grep/find blind across 53+ active handoffs and 24 wiki articles. Same plumbing as the web_research reranker (ONNX Runtime + MaxSim + small embedder), pointed at our own corpus and refreshed on commit via the existing PostToolUse hook pattern that already keeps GitNexus current.

## Why This Matters

| Problem today | Cost |
|---|---|
| Explore subagent grep/finds across `handoffs/active/`, `research/`, `wiki/`, `progress/` blind | Multiple turns per investigation; misses cross-cutting context |
| 53 active handoffs + 24 compiled wiki articles + 246 source documents are all keyword-indexed only | Topical/semantic queries miss documents that don't share keywords |
| GitNexus indexes **code only** — markdown is invisible to the code-intelligence pipeline | Knowledge ↔ code crossover queries (e.g., "where did we discuss this benchmark in handoffs?") have no path |
| `wiki/` (24 compiled articles synthesizing 246 sources) is the highest-density knowledge surface and currently has **no retrieval layer at all** | Highest-leverage corpus is hardest to query |

## Corpora to Index

| Source | Files | Why include |
|---|---|---|
| `wiki/*.md` | 24 articles + INDEX + SCHEMA | Highest-density compiled knowledge — primary corpus |
| `handoffs/active/*.md` | ~53 | In-progress work; the most-queried surface during Explore-agent runs |
| `handoffs/completed/*.md` | many | Historical decisions still load-bearing for active work |
| `research/*.md` (incl. `deep-dives/`) | ~30+ | Intake notes, deep dives, reference material |
| `progress/YYYY-MM/*.md` | many | Daily session summaries — best source for "when did we last touch X?" |
| `docs/chapters/*.md` (in `epyc-inference-research`) | many | Compiled chapter knowledge from research repo |

**Excluded**: `handoffs/archived/*.md` (intentionally — archived state is misleading by design; including it pollutes retrieval signal). `CHANGELOG.md` is a candidate for inclusion if Explore-agent traces benefit, but defer to a later iteration.

## Reusable Plumbing (from colbert-reranker-web-research.md)

| Component | Status | Location |
|---|---|---|
| GTE-ModernColBERT-v1 ONNX model | ✅ on disk | `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/` |
| `onnxruntime` in orchestrator venv | ✅ installed | `epyc-orchestrator` venv |
| MaxSim + per-token 128-dim embeddings | ✅ designed | colbert-reranker-web-research.md S3 |
| EPYC latency probe | ✅ measured | 180 ms / 10-snippet rerank call (S4) |
| `LATEON_MODEL_PATH` env override pattern | ✅ landed | NIB2-47 (extends to alternate ColBERT models) |

**Goal**: extract the encode/MaxSim layer into a shared module that both web_research reranking and internal-KB RAG import. The ONNX session, tokenizer, and MaxSim implementation are corpus-agnostic; only the indexer + storage + query-CLI differ.

## Architecture (proposed)

```
                                                   ┌─ web_research (existing, S5 gated on AR-3)
ColBERT encoder (shared)                           │
  + MaxSim                ──┬──> reranker call ────┘
  + ONNX runtime           │
                            └──> KB indexer ───┬──> per-doc token embeddings (npz/parquet)
                                               ├──> heading/paragraph chunk index (sqlite)
                                               └──> query CLI / Python API ──> Explore subagent
                                                          ▲
                              PostToolUse-on-commit ──────┘  (incremental rebuild for changed files)
```

**Storage**: per-document `.npz` of token embeddings + a SQLite catalog mapping (chunk_id, file_path, line_range, heading_path, mtime, content_hash). Per-document files keep incremental rebuild cheap — only re-encode files whose `content_hash` changed since last index.

**Chunking**: heading-aware (split at `^#{1,3}` boundaries with a max-chars cap). Heading hierarchy carried into the chunk metadata so retrieval results can show breadcrumbs (`handoffs/active/foo.md > ## Phase 2 > ### Subsection`).

**Query**: top-K snippet retrieval with MaxSim against the encoded query, returns `(file_path, heading_path, line_range, snippet, score)` tuples. Default K = 8, callable returns top-3 after rerank.

## Work Items

- [ ] **K1: Extract shared encoder module** — Pull the ONNX session + tokenizer + MaxSim implementation out of the web_research path into `epyc-orchestrator/src/retrieval/colbert_encoder.py` (or similar). Single class instance, lazy-loaded, used by both consumers. ~1 h. Cross-coordinates with `colbert-reranker-web-research.md` S5 — both should import the same module.
- [ ] **K2: Corpus configuration + chunker** — Define `kb_rag_config.yaml` listing corpus roots + glob patterns + exclusions (archived/). Implement heading-aware chunker (`src/retrieval/markdown_chunker.py`). Unit tests on a fixture set. ~2 h.
- [ ] **K3: Initial index build** — Walk corpus, encode every chunk, write per-doc `.npz` + SQLite catalog at `data/kb_rag/index/`. CLI: `python -m epyc.kb_rag build`. Measure end-to-end time on full corpus (expect: ≤5 min for ~150 markdown files at 180 ms/encode). ~3 h.
- [ ] **K4: Query CLI + Python API** — `python -m epyc.kb_rag query "<question>" [--top-k 8]` returns ranked chunks with breadcrumbs. Python API for orchestrator/Explore-agent integration. Result schema: `[{file, heading_path, line_range, snippet, score}, ...]`. ~2 h.
- [ ] **K5: Index-on-commit hook** — Extend the existing PostToolUse-on-commit hook (currently runs `npx gitnexus analyze` for code) to also run `python -m epyc.kb_rag update --since-commit HEAD~1` for markdown changes. Detect changed files via `git diff --name-only` filtered by corpus globs; re-encode only those. ~1 h.
- [ ] **K6: Explore-subagent integration** — Add a thin tool wrapper (e.g., `kb_search` MCP tool or in-orchestrator helper) so Explore subagents call the KB-RAG instead of grep-first for semantic queries. Document the pattern in `.claude/skills/...` or agent file overlays. ~2 h.
- [ ] **K7: Validation pass** — Five hand-curated queries covering different corpora ("where did we discuss ColBERT licensing?", "what are the NPS4 results?", "which handoffs cover KV compaction?"). Compare KB-RAG top-3 vs grep on the same queries; record precision and recall. ~1 h.

## Open Questions

1. **Embedder choice**: reuse the existing GTE-ModernColBERT-v1 (150M, BEIR 54.67) for both encode-query and encode-doc, or pair a smaller embedder for indexing (e.g., mxbai-edge-colbert-32m) with GTE for rerank? Indexing latency is dominated by doc count × tokens-per-doc; for ~150 files this matters less than for a 100K-doc corpus. **Recommendation**: start with GTE for both; revisit only if index-build time exceeds 10 min.
2. **Chunking unit**: pure heading-bounded vs sliding-window (e.g., 512-token windows with 64-token stride)? Heading-bounded gives semantic cohesion but variable size; sliding-window gives uniform size but breaks headings. **Recommendation**: heading-bounded with max-chars cap (split a too-long section at the next `^- ` or paragraph boundary).
3. **Staleness vs immediacy**: index-on-commit means a session that just edited a handoff would query a stale index until commit. Acceptable? **Tentative answer**: yes for the first iteration; add optional `--since-uncommitted` flag later if the staleness window proves painful.
4. **Cross-repo corpora**: include `epyc-inference-research/docs/chapters/*.md` and `epyc-orchestrator/AGENTS.md`-style files? They're outside `epyc-root` but topically essential. **Tentative answer**: yes, behind explicit roots in the config; the indexer doesn't care about repo boundaries.
5. **Wiki re-compile coupling**: `wiki/INDEX.md` notes a "Last compiled" date; wiki articles synthesize source documents. If a wiki article is regenerated, the index naturally re-encodes it. No special handling needed.

## Non-Goals (explicit)

- **No web UI** — CLI + Python API only. Aligned with the "skip Web RAG UI" decision from the architecture review.
- **No auth / scopes / token boundary** — single-user, no external exposure.
- **No replacement for GitNexus** — code stays in GitNexus, markdown goes here. Two indices, no overlap.
- **No vector DB service** — flat per-doc `.npz` + SQLite catalog. We can adopt a vector DB (LEANN, FAISS, qdrant) later if scale demands it; the LEANN evaluation in `handoffs/archived/leann_vector_db.md` was gated on MemRL size and is unrelated to this corpus.

## Cross-References

- **Sibling consumer**: [`colbert-reranker-web-research.md`](colbert-reranker-web-research.md) — extract shared encoder module (K1) coordinates with S5.
- **Indexing pattern**: existing GitNexus PostToolUse hook documented in `/workspace/CLAUDE.md` § "Keeping the Index Fresh" — K5 generalizes this to markdown.
- **Excluded by design**: `handoffs/archived/leann_vector_db.md` (different problem: episodic memory scaling, not document retrieval).
- **Pipeline integration index**: see `pipeline-integration-index.md` for cross-cutting concerns (RAM budget, disk allocation under `data/`).

## Key Files (proposed)

| Path | Purpose |
|---|---|
| `epyc-orchestrator/src/retrieval/colbert_encoder.py` | Shared encoder (K1) |
| `epyc-orchestrator/src/retrieval/markdown_chunker.py` | Heading-aware chunker (K2) |
| `epyc-orchestrator/src/retrieval/kb_rag.py` | Index build + query (K3, K4) |
| `epyc-orchestrator/scripts/kb_rag/build_index.py` | CLI entry point (K3) |
| `epyc-orchestrator/scripts/kb_rag/query.py` | Query CLI (K4) |
| `epyc-orchestrator/data/kb_rag/index/` | Per-doc `.npz` + `catalog.sqlite` (K3 output) |
| `epyc-orchestrator/config/kb_rag_config.yaml` | Corpus roots + globs + exclusions (K2) |
| `.claude/hooks/post_commit_kb_rag_update.sh` | Index-on-commit hook (K5) |

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-494] "Contexts are Never Long Enough: Structured Reasoning for Scalable Question Answering over Long Document Sets"** (arxiv:2604.22294, Stanford OVAL/Genie group, Joshi/Shethia/Dao/Lam)
  - Relevance: **directly proposes an alternative architecture to ColBERT-based RAG** for the same problem this handoff scopes — multi-document QA over a long corpus. SLIDERS extracts salient information into a relational database and replaces text-concatenation reasoning with SQL over persistent structured state, then runs a reconciliation pass using extraction provenance/rationales to repair duplicates and inconsistencies.
  - Key technique: LLM-driven information extraction into a relational schema; SQL-based reasoning as the working surface; provenance- and rationale-aware data reconciliation; pipeline scales to 36M-token corpora.
  - Reported results: +6.6 points avg over GPT-4.1 on three existing long-context QA benchmarks (all baselines fit in context window); +~19 / +~32 points over next-best baseline on two new 3.9M / 36M-token benchmarks where chunk-aggregation collapses.
  - Delta from current handoff approach: this handoff scopes a ColBERT-based RAG over our markdown KB. SLIDERS argues that *for sufficiently large corpora*, structured-DB extraction beats embedding+chunk retrieval. Our current corpus (~24 wiki + ~70 active handoffs) is far below SLIDERS' headline scale, so the headline gain may not materialize at our scale — but the *reconciliation pattern* (provenance + rationale + metadata to detect duplicate/inconsistent records) is independently valuable for our knowledge-base governance work even at small scale.
  - Caveats (Tier 2b): schema hallucination is the #1 production failure mode for LLM-to-SQL pipelines (web evidence: production failures dominated by schema hallucinations and incorrect join paths); long-context relational reasoning research finds models prioritize precision at expense of recall, leading to underprediction (arxiv:2510.03611) — SLIDERS' aggregation step risks missing relations; single-source results from one Stanford group, no independent replication; no CPU-cost data published; references not extracted from arxiv abs page.
  - Action: evaluate SLIDERS' structured-extraction + reconciliation pattern as a **possible upgrade lane** for this handoff's K3/K4 once base ColBERT pipeline is live. Do NOT replace ColBERT plan — treat as a sequential evolution path.

- **[intake-492] "Flywheel — local-first MCP memory layer for AI agents over Obsidian/Markdown vaults"** (`github.com/velvetmonkey/flywheel-memory`)
  - Relevance: Flywheel is the closest *running implementation* of the architecture this handoff scopes — hybrid BM25 + optional local semantic search over a markdown vault, with section-aware snippets, frontmatter, and linked-context expansion in a single MCP call. Apache-2.0, Node/MCP, fully self-hostable. Self-reported HotpotQA 90.0% doc recall and LoCoMo 81.9% evidence recall provide a reproducible academic-style harness we could borrow as evaluation templates for our own retrieval pipeline.
  - Key technique: BM25 + local semantic hybrid; auto-wikilink suggestions on mutation using aliases + co-occurrence + graph + semantic scorer (with an accept/reject learning loop that updates the link weights); SHA-256 conflict detection + atomic rollback for safe vault writes; YAML "policies" — declarative search-then-write workflows with preview + atomic execute; multi-vault index sharding.
  - Delta from current handoff approach: this handoff plans Python+ColBERT+ONNX over our own corpora. Flywheel's runtime (Node/MCP/Obsidian) is not portable as-is. The portable wins are architectural: (a) the wikilink learning-loop scorer for our wiki cross-references, (b) the SHA-256 conflict + atomic-undo write contract for any agent that mutates handoffs/wiki, (c) the HotpotQA / LoCoMo harness as a reusable eval rig for K4-K5 retrieval-quality measurement.
  - Caveat (Tier 2b): single-author / independent project, self-reported benchmarks with explicit "directional, not apples-to-apples" caveat, no peer review, credibility 2/6 per `feedback_credibility_from_source_not_readme.md`.
  - Action: borrow Flywheel's HotpotQA/LoCoMo harness pattern for K4 retrieval-quality eval; evaluate the learning-loop wikilink scorer separately as an enhancement to the wiki-governance work.
