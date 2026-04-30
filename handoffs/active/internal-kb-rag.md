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
- [ ] **K7: Validation pass — Flywheel-template eval** (rewritten 2026-04-28, from intake-492). Adopt Flywheel's HotpotQA + LoCoMo eval **methodology** (NOT its harness code — Flywheel ships as Node/MCP/Obsidian-coupled `demos/hotpotqa/` + `demos/locomo/`; we re-implement in Python against our own corpus). Two protocols:
  - **HotpotQA-style retrieval probe**: assemble a 4,960-doc-pool-equivalent over our wiki + active handoffs + research + completed-handoffs (target: 4,000–5,000 markdown chunks after K2 chunking; pool size dictated by corpus size, not arbitrary number). Curate ~50 multi-hop questions whose ground-truth evidence spans 2+ documents. Measure document-recall@k for k ∈ {3, 5, 10}, and KB-RAG top-3 vs grep on the same questions. **Note**: 4,960-doc pool is sui generis (Flywheel's choice — neither HotpotQA-distractor 10-doc nor fullwiki); record this methodology choice explicitly so future cross-paper comparison is honest.
  - **LoCoMo-style multi-session probe**: simulate ~20 multi-session "agent investigations" (e.g., "follow the v3 kernel rebase across handoffs and progress logs over 4 weeks"). Measure evidence-recall (did KB-RAG return the chunks containing the load-bearing facts?) and answer accuracy with a small judge LLM in noisy-grading mode. Match Flywheel's reported single-hop / multi-hop split if the question pool supports it.
  - **Variance band**: per Flywheel README, ~1 pp run-to-run variance from LLM non-determinism is the noise floor. Any cross-paper or cross-config delta under ~2 pp is within noise — record this explicitly so KB-RAG decisions never chase noise.
  - Effort revised: ~2 sessions (vs original 1 h estimate). Output: `data/kb_rag/eval/hotpotqa_template_results.json` + `loco_template_results.json` + a one-page summary in `data/kb_rag/eval/SUMMARY.md`.
  - Cross-link: intake-492 (Flywheel) and `research/intake_index.yaml` entry. Harness code is NOT being lifted — only methodology.
- [ ] **K8 (LOW priority, defer): wikilink learning-loop scorer** (NEW 2026-04-28, from intake-492). Flywheel's auto-wikilink suggestion uses an accept/reject feedback loop that updates a graph-edge scorer over time (alias + co-occurrence + graph + semantic context). Adapt as a wiki-cross-reference quality signal for the existing wiki/INDEX.md compilation pipeline. Defer until KB-RAG K1–K7 ships and we have a measured wiki-cross-link gap to address. NOT blocking K1–K7.

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
  - **Framing**: ALTERNATIVE architecture to ColBERT-based RAG (NOT an upgrade lane on the same path). SLIDERS replaces retrieval with persistent SQL state — they share a problem statement but not a code path.
  - Relevance: directly addresses the same problem this handoff scopes — multi-document QA over a long corpus — but via per-question schema induction + LLM extraction into a relational database + SQL reasoning + provenance-aware reconciliation. Code released at `github.com/stanford-oval/sliders` (MIT) and on PyPI as `sliders-genie`.
  - Reported results (concrete): +6.6 pp avg vs union of baselines (RAG / base GPT-4.1 / DocETL / Chain-of-Agents / RLM) across FinanceBench / Loong / Oolong; **WikiCeleb100** (3.9M tokens, new) +~19 pp over next-best; **FinQ100** (36M tokens, SEC 10-Q derived, new) abstract reports ~32 pp / repo README reports ~50 pp — unresolved discrepancy.
  - Critical adoption blocker (Tier 2b): code paths hard-wired to **GPT-4.1 / GPT-4.1-mini** via Azure OpenAI / OpenAI public API at every stage (schema induction, relevance gating, extraction, primary-key selection, reconciliation controller+executor, SQL generation, answer synthesis, citation generation). **NO local-model code path** in the released repo. Earlier intake claim that SLIDERS "runs locally on any capable LLM" was unsupported. Adoption requires both endpoint substitution AND SQL-agent-loop revalidation on a Coder-30B/35B-class local model.
  - Other Tier 2b: schema hallucination is #1 LLM-to-SQL production failure; long-context relational reasoning underpredicts (arxiv:2510.03611); single-source (one Stanford group); per-query reconciliation cost is heavy (5 controller iter × 5 SQL × 3 retries × 20 inspections × LLM calls per stage); per-question schema induction uses a fixed taxonomy library (`sliders_taxonomy.json`) keyed by query-type × document-type, partly mitigating schema-design overhead.
  - Action: SLIDERS is an alternative architecture for K3/K4, NOT an upgrade lane. Do not block ColBERT plan on it. **Sequential evolution as a separate validation experiment** AFTER base ColBERT ships AND a focused experiment confirms a Coder-30B-class local model can drive the controller/executor loop. The reconciliation-pattern (provenance + rationale + metadata) is independently valuable for knowledge-base governance even at small scale and can be lifted without the full architecture.

- **[intake-492] "Flywheel — local-first MCP memory layer for AI agents over Obsidian/Markdown vaults"** (`github.com/velvetmonkey/flywheel-memory`)
  - Relevance: Flywheel is the closest *running implementation* of the architecture this handoff scopes — hybrid BM25 + optional local semantic search over a markdown vault, with section-aware snippets, frontmatter, and linked-context expansion in a single MCP call. Apache-2.0, Node/MCP, fully self-hostable.
  - Eval methodology (NOT code) is the portable win: HotpotQA 90.0% doc recall on a **sui generis 4,960-doc pool** (neither standard 10-doc distractor nor fullwiki — flag for cross-paper comparison), LoCoMo 81.9% evidence recall over 695 questions / 272 sessions, **~1pp run-to-run variance from LLM non-determinism**. Harness code itself ships as `demos/hotpotqa/` and `demos/locomo/` directories — demo-coupled to the Node/MCP/Obsidian runtime — so borrowing the harness means re-implementing the methodology in Python, not lifting code.
  - Key patterns: (a) wikilink learning-loop scorer (accept/reject feedback updates link weights) for our wiki cross-references; (b) hash-before-write + single-step undo log as a **portable abstract contract** for agent mutations (Node/Obsidian implementation is NOT lift-and-shift); (c) HotpotQA / LoCoMo eval methodology as a reusable template for K4 retrieval-quality measurement.
  - Caveat (Tier 2b): credibility 3 (1,092 commits + 3,292 tests + 385 releases + dual-OS dual-Node CI as engineering-rigor signals; capped at 3 by no peer review, no independent replication, contributor-graph confirmation not obtained). Self-reported benchmarks with ~1pp variance band — any cross-paper delta under ~2pp is within noise.
  - Action: borrow Flywheel's HotpotQA/LoCoMo eval **methodology** (4,960-doc pool, 695q LoCoMo split, ~1pp variance band) as a Python template for K4 retrieval-quality eval — harness code is Node/MCP/Obsidian-coupled and must be re-implemented. Evaluate the learning-loop wikilink scorer separately as an enhancement to the wiki-governance work.

## Research Intake Update — 2026-04-30

### New Related Research

- **[intake-519] "Granite-Embedding-97M-Multilingual-R2"** (HF `ibm-granite/granite-embedding-97m-multilingual-r2`, Apache 2.0, IBM, released 2026-04-29)
  - Relevance to KB RAG: **MEDIUM**. Candidate dense embedder for K-track retrieval. 97M params, ModernBERT backbone, 32K context, 384-dim embeddings, 200+ languages with 8 programming languages (code retrieval @ 60.5). MTEB Multilingual Retrieval 59.6 — claimed best open <100M-class multilingual score. Apache 2.0; ONNX, OpenVINO (incl. INT8), Sentence Transformers, vLLM-embedding endpoint; GGUF convertible (no native release).
  - Why it matters here: KB content is heavy on code + English + occasional multilingual; the 32K context is unusual at this scale and would let a single embedding cover entire CLAUDE.md / handoff files without chunking — directly relevant to K2/K3 indexing decisions. Throughput claim ~3× gte-multilingual-base 305M on reference HW makes ingestion-side cost low.
  - Tier 2b: BGE-M3 (~305M, ~63.0 MTEB) wins on raw quality but is 3× larger; retrieval-quality gap likely narrows on EPYC's English-heavy KB workload. The 59.6 / +8.7-vs-e5-small claim is self-reported on the model card; corroboration limited to the HF leaderboard and the Granite-R2 paper (arxiv:2508.21085, "Granite Embedding R2 Models"). No native GGUF — for CPU-quantized deployment plan to use OpenVINO INT8 path or our own ONNX→GGUF pipeline.
  - Action: when the K-track moves from stub to design phase, A/B Granite-97M-r2 vs (a) BGE-M3 (quality ceiling), (b) multilingual-e5-base (size-matched competitor), on a curated slice of CLAUDE.md + handoff content. Measure NDCG@10 + per-doc encode latency on EPYC.
  - Verdict: `worth_investigating`. Cross-ref `colbert-reranker-web-research.md` 2026-04-30 update — same model, evaluated for the web-research side of the dense-then-rerank stack.

#### Deep-dive refinement (2026-04-30) — bench plan persisted, K2 is the gate

Deep-dive at [`/workspace/research/deep-dives/granite-embedding-97m-r2-evaluation.md`](../../research/deep-dives/granite-embedding-97m-r2-evaluation.md). Bench handoff at [`granite-97m-r2-bench-plan.md`](granite-97m-r2-bench-plan.md).

**Critical infra finding**: there is **no production multilingual retrieval today** — only English-only BGE-large-en-v1.5 routing pool on `:8090–:8095` (`/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/parallel_embedder.py`). Granite-97m-r2 (or any multilingual embedder) would be **net-new infrastructure**, not a swap-in.

**The bench cannot run with "K-track activation" as the gate** — it needs the **K2 chunker output** specifically, since the eval corpus depends on having chunked KB content. The bench handoff includes a fallback eval-corpus path (100 code snippets from `epyc-orchestrator/src/` + 30 NL queries with manual labels, ~half day) that does NOT require K2, so the bench can run earlier if a K2-blocked K-track scope is undesirable. Decide which path to take when this handoff exits stub status.

**Other corrections**: ModernBERT IS supported in llama.cpp; the "Ollama unsupported" note refers only to Ollama's wrapper. 2,894 docs/s is GPU not CPU — calibrate expectations before benching. BGE-M3 ~63.0 figure is from MMTEB 131-task aggregation, NOT apples-to-apples with IBM's 18-task 59.6 — the bench needs to produce same-corpus same-metric numbers to settle the comparison.

### Architectural corroboration from intake-520 (2026-04-30)

- **[intake-520] "markdownfs (mdfs)"** (https://github.com/subramanya1997/markdownfs, MIT) — deep dive at [`/workspace/research/deep-dives/markdownfs-rust-mcp-vfs.md`](../../research/deep-dives/markdownfs-rust-mcp-vfs.md).
  - Relevance to this handoff: **architectural validation only — no code dependency, no plan change**.
  - The mdfs project ships a forward-looking design doc, `docs/semantic-index.md`, that independently arrives at the same architecture as K1–K7 here:

    | mdfs `semantic-index.md` | This handoff (K1–K7) |
    |---|---|
    | FS canonical, vector DB derived | git + filesystem canonical, FAISS/.npz derived |
    | Heading-aware chunking (title / heading / subsection) | Heading-aware split at `^#{1,3}` with max-chars cap (K2) |
    | Metadata: file_path, heading_path, commit_hash, author, perms | Metadata: file_path, heading_path, line_range, mtime, content_hash (K3) |
    | Index update: on write / on commit / on revert | PostToolUse-on-commit hook + content_hash diff (K5) |
    | Result shape: `{path, heading, score, excerpt}` | `{file, heading_path, line_range, snippet, score}` (K4) |
    | Principle: vector layer accelerates retrieval, FS remains truth | Same — FS is canonical, retrieval is derived |

  - Reading: this is independent corroboration that "FS-truth + derived vector index + heading-aware chunking + on-commit reindex" is the convergent architectural shape for markdown-agent-workspace retrieval, not a private design choice. Useful as design-risk reduction for K1–K7.
  - Caveats from the deep dive that do NOT change our plan: mdfs itself is 17-day-old / single-author / just-pivoted / MCP-runs-as-root / single-writer-per-state.bin and is **not adopt-as-substrate** material. The architectural pattern is portable; mdfs's own implementation is not.
  - No work-item delta. Pattern B is a confirmation, not a new K-task.
