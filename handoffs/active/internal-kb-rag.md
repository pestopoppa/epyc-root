# Internal Knowledge-Base RAG

**Status**: K1-K7 CERTIFIED 2026-06-13 — `epyc-orchestrator/src/retrieval/` (additive shared `colbert_encoder.py`, `markdown_chunker.py`, `kb_rag.py` build/update/query) + CLI + `.claude/hooks/post_commit_kb_rag_update.sh` + `.claude/skills/kb-search/SKILL.md` + unit tests. **Fresh K7 build**: 577 files / 18,010 chunks / 1,227.6 MiB embeddings, max corpus mtime `2026-06-13T00:26:51Z`. **K7 certification sweep complete** over the final 70-case pool (50 HotpotQA-template + 20 LoCoMo-template): best aggregate recall@10 is `recency_w0.1_s90_rerank_w0.3` at 0.6298, but `recency_w0.3_s90` is within the 2pp noise band at 0.6167 and is the only config with 0 missed-all-evidence cases. Decision: validate the temporal recency signal; do not promote cross-encoder rerank as a default without a consumer that explicitly prefers first-rank/recall@3 over miss-risk. K8 wikilink scorer deferred; K11 FTS5 lexical signal remains measure-first if exact-match/alias misses remain material.
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
| `onnxruntime` in orchestrator venv | ⚠️ drifted missing 2026-06-12; `/mnt/raid0/llm/pace-env` works | restore orchestrator venv or explicitly bless `pace-env` before K7 |
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

- [x] **K1: Extract shared encoder module** — Pull the ONNX session + tokenizer + MaxSim implementation out of the web_research path into `epyc-orchestrator/src/retrieval/colbert_encoder.py` (or similar). Single class instance, lazy-loaded, used by both consumers. ~1 h. Cross-coordinates with `colbert-reranker-web-research.md` S5 — both should import the same module.
- [x] **K2: Corpus configuration + chunker** — Define `kb_rag_config.yaml` listing corpus roots + glob patterns + exclusions (archived/). Implement heading-aware chunker (`src/retrieval/markdown_chunker.py`). Unit tests on a fixture set. ~2 h.
- [x] **K3: Initial index build** — Walk corpus, encode every chunk, write per-doc `.npz` + SQLite catalog at `data/kb_rag/index/`. CLI: `python -m epyc.kb_rag build`. Measure end-to-end time on full corpus (expect: ≤5 min for ~150 markdown files at 180 ms/encode). ~3 h.
- [x] **K4: Query CLI + Python API** — `python -m epyc.kb_rag query "<question>" [--top-k 8]` returns ranked chunks with breadcrumbs. Python API for orchestrator/Explore-agent integration. Result schema: `[{file, heading_path, line_range, snippet, score}, ...]`. ~2 h.
- [x] **K5: Index-on-commit hook** — Extend the existing PostToolUse-on-commit hook (currently runs `npx gitnexus analyze` for code) to also run `python -m epyc.kb_rag update --since-commit HEAD~1` for markdown changes. Detect changed files via `git diff --name-only` filtered by corpus globs; re-encode only those. ~1 h.
- [x] **K6: Explore-subagent integration** — Add a thin tool wrapper (e.g., `kb_search` MCP tool or in-orchestrator helper) so Explore subagents call the KB-RAG instead of grep-first for semantic queries. Document the pattern in `.claude/skills/...` or agent file overlays. ~2 h.
- [x] **K7: Validation pass — Flywheel-template eval** (rewritten 2026-04-28, from intake-492). Adopt Flywheel's HotpotQA + LoCoMo eval **methodology** (NOT its harness code — Flywheel ships as Node/MCP/Obsidian-coupled `demos/hotpotqa/` + `demos/locomo/`; we re-implement in Python against our own corpus). Two protocols:
  - **HotpotQA-style retrieval probe**: assemble a 4,960-doc-pool-equivalent over our wiki + active handoffs + research + completed-handoffs (target: 4,000–5,000 markdown chunks after K2 chunking; pool size dictated by corpus size, not arbitrary number). Curate ~50 multi-hop questions whose ground-truth evidence spans 2+ documents. Measure document-recall@k for k ∈ {3, 5, 10}, and KB-RAG top-3 vs grep on the same questions. **Note**: 4,960-doc pool is sui generis (Flywheel's choice — neither HotpotQA-distractor 10-doc nor fullwiki); record this methodology choice explicitly so future cross-paper comparison is honest.
  - **LoCoMo-style multi-session probe**: simulate ~20 multi-session "agent investigations" (e.g., "follow the v3 kernel rebase across handoffs and progress logs over 4 weeks"). Measure evidence-recall (did KB-RAG return the chunks containing the load-bearing facts?) and answer accuracy with a small judge LLM in noisy-grading mode. Match Flywheel's reported single-hop / multi-hop split if the question pool supports it.
  - **Variance band**: per Flywheel README, ~1 pp run-to-run variance from LLM non-determinism is the noise floor. Any cross-paper or cross-config delta under ~2 pp is within noise — record this explicitly so KB-RAG decisions never chase noise.
  - Effort revised: ~2 sessions (vs original 1 h estimate). Output: `data/kb_rag/eval/hotpotqa_template_results.json` + `loco_template_results.json` + a one-page summary in `data/kb_rag/eval/SUMMARY.md`.
  - Cross-link: intake-492 (Flywheel) and `research/intake_index.yaml` entry. Harness code is NOT being lifted — only methodology.
  - **2026-06-12 diagnostic note**: a small hand-curated 8-case sweep ran against the stale May-30 index with `/mnt/raid0/llm/pace-env`. It is not a K7 substitute. Before a decision-grade sweep: restore/bless runtime, refresh the index, create the K7 query/evidence set, then rerun configs.
  - **2026-06-13 seed eval note**: fresh build + 20-case seed sweep completed at `/mnt/raid0/llm/tmp/kbrag_k7_eval_20260612/summary.json`. Index: 577 files / 18,010 chunks / 1.2 GiB embeddings, max corpus mtime `2026-06-13T00:26:51Z`. Best recall@10 config: `recency_w0.1_s90` at 0.6417 overall (HotpotQA-template 0.6944, LoCoMo-template 0.5625), 0 missed-all-evidence cases. `rerank_w0.3`/`rerank_w0.6` improve recall@3 to 0.4417 and first-evidence rank to ~2.1 but lose recall@10 and miss 3 all-evidence cases. Treat as calibration evidence, not certification: the harness metadata explicitly says this is a seed suite, not the final 50+20 pool.
  - **2026-06-13 certification-pool note**: `feat/kbrag-k7-eval` commit `edba4d9` adds `scripts/kb_rag/k7_cert_cases.json` with the final 70-case decision pool (50 HotpotQA-template + 20 LoCoMo-template). Validation command checked JSON parse, protocol counts, duplicate IDs, and existence of every evidence file; `tests/unit/test_kb_rag_eval.py` still passes. Run with `--cases scripts/kb_rag/k7_cert_cases.json` against the fresh K7 index.
  - **2026-06-13 certification result**: clean-window parallel sweep completed against `/mnt/raid0/llm/tmp/kbrag_index_k7_20260612`; combined artifacts at `/mnt/raid0/llm/tmp/kbrag_k7_cert_parallel_20260613_075405/combined/{summary.json,rows.jsonl,cases.json}` (`420` rows, `ok=true`, no missing evidence files). Overall recall@10 ranking: `recency_w0.1_s90_rerank_w0.3` 0.6298 / missed-all-evidence 3; `recency_w0.3_s90` 0.6167 / missed 0; `recency_w0.1_s90` 0.6131 / missed 1; `rerank_w0.6` 0.5905 / missed 5; `rerank_w0.3` 0.5810 / missed 4; `maxsim` 0.5690 / missed 5. Protocol split for the zero-miss candidate: HotpotQA-template recall@10 0.6567, LoCoMo-template recall@10 0.5167. Because the top two configs differ by only 1.31pp (< the declared 2pp noise floor), prefer `recency_w0.3_s90` for safety/default-candidate decisions and reserve `recency_w0.1_s90_rerank_w0.3` for workloads optimizing first-evidence rank/recall@3.
- [ ] **K8 (LOW priority, defer): wikilink learning-loop scorer** (NEW 2026-04-28, from intake-492). Flywheel's auto-wikilink suggestion uses an accept/reject feedback loop that updates a graph-edge scorer over time (alias + co-occurrence + graph + semantic context). Adapt as a wiki-cross-reference quality signal for the existing wiki/INDEX.md compilation pipeline. Defer until KB-RAG K1–K7 ships and we have a measured wiki-cross-link gap to address. NOT blocking K1–K7.

## Open Questions

1. **Embedder choice**: reuse the existing GTE-ModernColBERT-v1 (150M, BEIR 54.67) for both encode-query and encode-doc, or pair a smaller embedder for indexing (e.g., mxbai-edge-colbert-32m) with GTE for rerank? Indexing latency is dominated by doc count × tokens-per-doc; for ~150 files this matters less than for a 100K-doc corpus. **Recommendation**: start with GTE for both; revisit only if index-build time exceeds 10 min.
   - **New candidate to track (2026-05-29, via research intake intake-652)**: **LFM2-ColBERT-350M** (Liquid AI) — a late-interaction retrieval/reranker embedder in the LFM2 "Nanos" line, open-weights (license `lfm1.0`, source-available, non-blocker for self-host). Direct architectural analogue to GTE-ModernColBERT for this corpus. **Deployment caveat (verified against Liquid docs 2026-05-29)**: this model requires **PyLate + a PLAID index** for inference — it does **NOT** support GGUF / llama.cpp / standard Transformers / ONNX / MLX (model chart lists HF-only, those formats unavailable). So it is a **PyLate/HF-only eval candidate**, NOT a drop-in for our existing GTE-ModernColBERT/MaxSim plumbing — adopting it would mean standing up a PyLate/PLAID path. No BEIR number verified yet — benchmark against GTE-ModernColBERT on the HotpotQA-style probe (K-eval) via PyLate before any swap. Deep dive: `research/deep-dives/lfm2-lfm25-family-deep-dive.md`.
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

## Research Intake Update — 2026-05-20

### New Related Research

- **[intake-572] "Mirage: A Unified Virtual Filesystem For AI Agents"** (Strukto AI; github.com/strukto-ai/mirage, Apache-2.0)
  - **Relevance**: Mirage's two-layer cache architecture (index cache for metadata/listings + file cache for object bytes, RAM-default with optional shared Redis backend) is a third independent data point alongside markdownfs (intake-520) and this handoff's K1–K7 design. The cache-layer separation specifically maps to our K3 (content_hash for diff-detection) + K5 (PostToolUse-on-commit reindex) boundary.
  - **Delta from current plan**: Mirage uses a FUSE mount as its primary access path and chooses Unix command semantics over JSON-RPC; we chose ColBERT + heading-aware chunking with a `kb-search` Skill surface. The architectures are not interchangeable, but Mirage's RAM-default + Redis-shared cache shape is a useful reference for any future multi-process retrieval scenario (e.g., autopilot parallel-species workers sharing a hot KB cache). No work-item delta — file as a third-party design corroboration for the "shared cache layer over a derived index" pattern.

### Mirage Pattern Adoption — 2026-05-20 (design references, no runtime dep)

Three patterns lifted from `strukto-ai/mirage` source audit. Apply at design time for the K1–K7 work; do NOT take a dependency on Mirage itself (single-author, v0.0.2a0, viral hype-cycle stars, native-compile deps including mfusepy + tree-sitter-bash + jq + numpy>=2.4.3; revisit at v0.1.0 + sustained 2nd committer + first published benchmark, earliest 2026-08).

- **K-Pattern-A — Per-source `SUPPORTS_SNAPSHOT` flag + content-fingerprint contract** (Mirage `python/mirage/resource/base.py:46`). Each chunk source (markdown file, code symbol, transcript, eventual ingestable PDF) declares a class-level boolean: does its `chunk_fingerprint` (mtime+sha256 of source range) remain stable when content is unchanged? Sources that answer yes participate in the on-commit reindex diff (K5) and the drift-detection contract (K-Pattern-B); sources that answer no (e.g., a live-pulled web doc, a Skill that runs against current `git log`) bypass diffing and are always re-fetched. Cleaner than implicit special-casing every source type, and shifts the "is this stable enough to cache" decision to the source author rather than the indexer. Apply as part of K1 (source-type taxonomy) and K3 (content-hash for diff-detection) — add a `supports_snapshot: bool` field to each chunk source's metadata.

- **K-Pattern-F — `live_only_prefixes` companion declaration for non-replayable sources** (Mirage `workspace/snapshot/state.py:74`). Some sources (a `git log`-backed wiki page, a live `gh api`-driven status snippet, a Skill result that depends on the current process's mtime) can be indexed for retrieval but cannot be replayed deterministically from a snapshot. Mirage surfaces this honestly via a `LIVE_ONLY_MOUNTS` list in the snapshot state dict rather than pretending all backends are content-addressable. Apply at K2 (chunk-source registry): a chunk-source declared `live_only=True` produces retrievable text but is never written into the persistent vector index — only into the hot RAM cache for the session that issued the query. Avoids the failure mode where a six-month-old vector index returns embeddings of long-vanished `git status` snippets.

- **K-Pattern-V — `FORMAT_VERSION`-gated compiled-artifact state dict** (Mirage `workspace/snapshot/state.py:106-110`). The compiled KB index file (chunks.json or the ColBERT shard tarball) carries a `FORMAT_VERSION = "k7-v1"` constant; load-time mismatch surfaces an explicit "regenerate via `npx kb-compile`" error rather than silently mis-deserializing and producing garbage retrieval. Cleaner than ad-hoc try/except migrations — and crucial when we change the chunk schema (e.g., switching from heading-path tuples to hierarchical breadcrumb strings) since we'll inevitably do that as the corpus grows. Apply as the very first line of the eventual compiled-artifact format: `{"format_version": "k7-v1", "compiled_at": "...", "source_repo_head": "...", "chunks": [...]}`. Make `format_version` a required field at the schema level so the validator rejects untagged artifacts.

## Research Intake Update — 2026-05-20 (chunking-quality evaluation)

### New Related Research

- **[intake-579] "Adaptive Chunking: Optimizing Chunking-Method Selection for RAG"** (arxiv:2603.25333, Ekimetrics, LREC 2026)
  - **Relevance to K2**: Proposes 5 intrinsic, document-only metrics (RC, ICC, DCC, BI, SC) that can score K2 `markdown_chunker.py` output on fixture corpora **without downstream RAG ground truth** — a candidate unit-test quality signal for the heading-aware markdown chunker. Reported +30% questions resolved and +8-10 pp answer correctness via per-document method selection on a 33-doc / 3-domain / ~1.18M-token corpus.
  - **Caveat**: 33-doc corpus is a small empirical base; two metrics (ICC, BI) rest on the cohesion-within-chunk premise that intake-581 (HOPE) empirically falsifies.

- **[intake-580] "ekimetrics/adaptive-chunking"** — MIT-licensed Python implementation (`github.com/ekimetrics/adaptive-chunking`)
  - **Lift potential for K7 eval**: Modular chunker ABC means K2's `markdown_chunker.py` can be slotted in as an additional candidate. The 5 metric implementations are the most lift-able piece (core MIT; only FMRE pulls `maverick-coref` CC BY-NC-SA 4.0). Useful for K7 if we want intrinsic chunk-quality scores alongside the HotpotQA/LoCoMo retrieval probes — those are corpus-extrinsic; the Ekimetrics suite is chunk-intrinsic and would catch chunker regressions that don't yet show up in retrieval-recall.

- **[intake-581] "A New HOPE: Domain-agnostic Automatic Evaluation of Text Chunking"** (arxiv:2505.02171, Brådland et al., SIGIR 2025) — **corroborates K2 design choice**
  - **Relevance to K2**: K2 chose heading-aware splitting at `^#{1,3}` boundaries with a max-chars cap (handoff Open-Question #2). That choice produces more-independent chunks at structural boundaries — and HOPE empirically finds semantic INDEPENDENCE between passages is the load-bearing retrieval-quality signal (+56.2% factual correctness with independence enforcement; intrachunk concept unity has **minimal impact**). The architectural choice was previously un-defended in the handoff; HOPE provides empirical support.
  - **Action for K7**: when the eval runs, capture HOPE three-level scoring on K2 chunker output as a secondary quality signal alongside the HotpotQA/LoCoMo retrieval-recall numbers. Will also serve as the side-by-side reference against the Ekimetrics metric suite (cross-link `opendataloader-pipeline-integration.md` 2026-05-20 update — same evaluation question over there).

### Next Actions

- [ ] Bookmark the Ekimetrics MIT 5-metric implementation as candidate eval scaffolding for K7 — gate adoption on the HOPE-vs-Ekimetrics side-by-side that opendataloader Phase 2 work will produce on PDF-extracted text. The markdown-input case here is similar enough that the metric-validity verdict from there should transfer with a small re-check on markdown fixtures.
- [ ] When defending K2's heading-aware chunking choice in any future review, cite HOPE's independence finding as empirical support rather than relying on the "natural for markdown" argument alone.

## Research Intake Update — 2026-05-21

### Hy-MT2-1.8B-1.25bit as optional multilingual pre-processor (narrow scope)

- **[intake-586] Hy-MT2 (Tencent Hunyuan, 2026-05-21 release)** — 33-language translation model family. The 1.8B-1.25bit variant is 440 MB on-disk (claimed 1.5x decode speedup) — small enough to live as a research-intake-pipeline tool rather than a server role.
- **Why this lands on the KB-RAG handoff**: CLAUDE.md routing guidance explicitly calls out Chinese-lab papers / EU/JP sources as a "prefer-SearXNG" case. Today, ingest of foreign-language abstracts relies on frontdoor (Qwen3.6) or ingest_long_context (Qwen3-Next-80B thinking ON) translating inline. Per user framing 2026-05-21, those models "already handle translation somewhat" — so a dedicated MT specialist is **overkill at 7B/30B scale** and only marginally useful at 1.8B-1.25bit scale.
- **Concrete adoption scope (narrow)**: optional tool, not a stack role. If/when the ColBERT ingest pipeline encounters foreign-language snippets that the existing model handles poorly (measure first), the 1.8B-1.25bit variant is a low-cost candidate to slot in as a pre-encode translation step. No standing role allocation. No autopilot routing.
- **Higher-leverage artefact (correctly scoped — see correction 2026-05-21)**: The **STQ1_0 llama.cpp kernel** (PR #22836) is generic at inference — it can decode any Sherry-QAT'd 1.25-bit weights. The **Sherry algorithm itself is QAT (training-time)**, not PTQ — applying it to an arbitrary worker would require ~10B tokens of QAT training that we have no infrastructure for. Today the only public Sherry-QAT'd weights are Tencent's Hy-MT1.5-1.8B and HY-1.8B-2bit; no Qwen3.6 / gemma4-26B-A4B / Qwen3.5-122B / Qwen3-Next-80B Sherry releases exist. So the kernel is "a decoder for weights only Tencent currently produces, and only at 1.8B class." Tracked on [[angelslim-techniques-evaluation]]; the PR #22836 watch is consolidated on `tq3-quantization-evaluation.md` (2026-06-12; formerly `llama-cpp-kernel-push-rebase`, archived to `../completed/`).

### What NOT to do

- Do NOT add Hy-MT2-30B-A3B or 7B as a stack role — existing multilingual coverage suffices for the workflows we run today.
- Do NOT commit to autopilot routing for a translation specialist before measuring whether the existing models actually have a quality gap on the foreign-language snippets the KB-RAG ingest actually receives.

Cross-references: [[searxng-bash-websearch-bridge]] (multilingual web-search ingest), [[colbert-reranker-web-research]] (external snippet pipeline), [[angelslim-techniques-evaluation]] (umbrella for the quant/early-exit techniques).

## Test Scope — Multilingual Ingest Quality-Gap Measurement (added 2026-05-21)

The 2026-05-21 Hy-MT2 intake left an open empirical question: do existing stack models (Qwen3.6 frontdoor, Qwen3-Next-80B ingest_long_context, gemma4-26B-A4B worker_general) have a measurable quality gap on foreign-language ingest content that a dedicated MT specialist (Hy-MT2-1.8B-1.25bit, 440 MB) would close? The answer is **contingent on what languages we actually see**, so the only way to resolve it is direct measurement. This subsection scopes that test.

### Hypothesis

- **H0 (overkill)**: For the foreign-language content the research-intake / KB-RAG pipeline actually encounters, inline translation via Qwen3-Next-80B (thinking ON) yields downstream summaries of equal quality to a pipeline that pre-translates with Hy-MT2-1.8B-1.25bit. The specialist provides no measurable lift.
- **H1 (niche found)**: For ≥1 language stratum the existing inline-translation pipeline measurably underperforms a pre-translate-then-summarize pipeline using Hy-MT2-1.8B-1.25bit. The gap is large enough to justify slotting the 440 MB specialist as an optional pre-encode step.

Decision threshold (set in advance to avoid post-hoc rationalization): **H1 holds if the pre-translation pipeline wins ≥60% pairwise on at least one non-Chinese-English stratum AND the win rate on Chinese/English is not significantly worse than baseline (i.e., no regression on the strong-coverage languages).**

### Language Stratification (refined 2026-05-21)

This is the load-bearing design choice. A test that pulls only Chinese-English samples will under-report H1 because all three stack models already cover that pair well. Required strata (≥10 samples each, target 40 total):

| Stratum | Sample target | Why | Hy-MT2 emphasis |
|---------|---------------|-----|-----------------|
| **Chinese (Simplified) → English** | 10 | Strong-coverage control; H1 must NOT win here or scoring is biased | Yes (general pair) |
| **European mainstream → English** (Italian, French, German, Russian) | 10 | **Primary user interest** — high-resource EU where existing stack models *should* be strong; a Hy-MT2 win here is the meaningful niche finding, since these are the languages the user's actual research-intake pipeline encounters | Yes (33-language scope) |
| **Japanese / Korean technical → English** | 10 | Medium-coverage; CJK shared script complications | Yes |
| **Mixed-script / structured content** (Chinese paper with English equations/code, JSON-embedded MT) | 10 | Tests structural fidelity; tokenizer-fertility edge case | IFMTBench-style |

Total: 40 snippets, ~200-500 tokens each (paper abstract scale, matches our actual research-intake unit of work).

**Dropped stratum (2026-05-21)**: Mandarin-minority/dialect (Tibetan/Mongolian/Uyghur/Cantonese). Per user direction — not represented in actual research-intake content. Hy-MT2's marketed strength on this stratum is therefore irrelevant to the user's workflow; testing it would inflate the H1 conclusion in a way that doesn't generalize to actual use.

**Re-scoring implication**: dropping the Hy-MT2-favorable stratum makes the test more honest, not less. If Hy-MT2 still wins on European-mainstream — where existing models *should* already be strong — the niche is real. If it doesn't, H0 holds for the user's actual content mix.

### Sample Provenance

SearxNG returns snippets (~150-300 chars) per result, not full documents. For 40 full-snippet samples in the 200-500 token range, sources to draw from:

1. **Recent research-intake foreign-language sources** — papers from Chinese labs (Tencent Hunyuan, DeepSeek, Kimi, Qwen, Kuaishou, Baichuan, MiniMax, AntGroup) plus any European-language technical content the user encounters. Pull abstracts directly. Already-indexed examples in `intake_index.yaml`: intake-543 (SkillSynth), intake-546 (Training-Free GRPO), intake-590-596 (Hunyuan MT family).
2. **WMT competition test sets** — Flores-200 is the canonical multilingual corpus. Free, standardized, covers all four required strata (zh, en, it, fr, de, ru, ja, ko all natively supported).
3. **Manual curation** — for the mixed-script-structured stratum, Flores-200 doesn't cover composite documents; hand-curate from intake-indexed papers that mix Chinese prose + English equations / code blocks.

Provenance log: record each sample's source URL, language, character/token count, and content type (paper abstract, blog post, structured doc) so the test is reproducible.

### Pipelines

**Pipeline A — Baseline (current production)**:
```
foreign-language snippet
  → Qwen3-Next-80B (ingest_long_context, thinking=ON, --enable-thinking=true)
  → English summary (target ~100-150 tokens)
```

**Pipeline B — Specialist pre-translation**:
```
foreign-language snippet
  → Hy-MT2-1.8B-1.25bit GGUF (one-shot translation prompt, --enable-thinking=false)
  → English translation (raw)
  → Qwen3-Next-80B (ingest_long_context, thinking=ON, same prompt as A)
  → English summary (target ~100-150 tokens)
```

**Pipeline C — Control (chain-of-thought confound check)**:
```
foreign-language snippet
  → Qwen3-Next-80B step 1: "Translate to English" (thinking=OFF)
  → English translation (raw)
  → Qwen3-Next-80B step 2: same summarization prompt as A and B (thinking=ON)
  → English summary
```

Pipeline C is mandatory: if B beats A, we must verify whether the gain is from Hy-MT2 specifically or from the two-step (translate → summarize) decomposition itself. C controls for that. If B ≈ C and both beat A, the lift is structural (decomposition) not specialist-specific, and Hy-MT2 is still overkill.

### Prerequisites

- [ ] **STQ1_0 llama.cpp PR #22836 either landed OR confirmed to load via existing GGUF support**. If the 1.25-bit GGUF cannot load without the new kernel, fall back to the BF16 safetensors variant via a temporary HF transformers loader OR use the 2-bit GGUF (also released, no special kernel needed). Document which variant was used — speedup numbers do not transfer across variants.
- [ ] **Hy-MT2-1.8B weights downloaded** to `/mnt/raid0/llm/models/` (pick variant per above)
- [ ] **Test launch recipe verified** — Hy-MT2-1.8B likely needs `--enable-thinking=false` (fast-thinking model per release notes), verify chat template + sampling params before bulk run
- [ ] **Approval to run** — per `feedback_speed_verify_via_llama_bench`, NEVER launch `run_benchmark.py` autonomously; user runs ALL benchmarks manually. Same constraint applies here: prepare commands, do not execute. Per `feedback_no_concurrent_inference`, get explicit per-run approval to avoid contaminating concurrent agent work.
- [ ] **Sample set frozen** before any pipeline runs — no swapping samples post-hoc

### Metrics

Three layers, listed in order of decision weight:

1. **Downstream KB-RAG retrieval quality** (primary, load-bearing). For each summary produced by A/B/C, index it into the ColBERT KB-RAG (`epyc-orchestrator/src/retrieval/kb_rag.py`) and measure NDCG@5 / MRR on a held-out query set drawn from the source documents' topics. If a pipeline produces summaries that retrieve worse, the pipeline is worse — this is the only metric that directly maps to the KB-RAG use case. Threshold: ≥0.05 lift in NDCG@5 to count as a win.
2. **Pairwise LLM-as-judge** (secondary). Use a sibling model (gemma4-26B-A4B worker_general, NOT Qwen3-Next-80B which is in-the-loop on A) as the judge. Present A vs B vs C summaries blind, ask for preference + reasoning. Bias caveat: LLM judges have known position bias — randomize order; verbosity bias — normalize length. Threshold: ≥60% A-vs-B win for H1 on the relevant stratum.
3. **Structural / terminology fidelity** (tertiary, manual spot-check). On ~5 mixed-script / structured samples, manually verify whether: (a) JSON delimiters are preserved, (b) named entities (people, places, model names, paper titles) are translated correctly, (c) equations / code blocks pass through unmodified. Hy-MT2 is explicitly trained for structural preservation (IFMTBench) — if it loses on this metric, the specialist-framing is wrong.

### Confounders to control

- **Length normalization**: longer translations may retrieve better simply by having more keywords. Cap summary lengths consistently across pipelines.
- **Sampling stochasticity**: run each pipeline 3× per sample with temperature > 0, report median. OR run at temperature=0 if reproducibility is more important than diversity.
- **Order effects in pairwise judging**: randomize A/B/C presentation order per sample.
- **Tokenizer fertility skew**: Hy-MT2-1.8B may tokenize the source language differently from Qwen3-Next-80B. Record tokens-in for each pipeline; if costs are wildly different, factor that into the decision (a 10% quality lift that costs 5× the tokens is not a win for an optional tool).
- **Hy-MT2 prompt sensitivity**: Hy-MT2 is fast-thinking + translation-SFT — generic chat prompts will degrade it. Use the prompt format documented in the model card / HY_MT2_0_Report.pdf, not a generic "translate the following" prompt.

### Acceptance Criteria

| Outcome | Decision |
|---------|----------|
| H0 confirmed on all strata | Mark `intake-586` as `not_applicable` (downgrade from `worth_investigating`). Remove Hy-MT2 from candidate-tools list. Close [[angelslim-techniques-evaluation]] sub-track for translation models specifically (Sherry/STQ1_0 quant track continues independently). |
| H1 confirmed on 1+ stratum, B ≫ C (specialist-specific lift) | Add Hy-MT2-1.8B-1.25bit (or whichever variant won) as optional pre-encode step in the KB-RAG ingest pipeline, gated by language detection. Specify which stratum triggers the tool route. Update `intake-586` verdict to `adopt_component`. |
| H1 confirmed but B ≈ C (structural-decomposition lift) | Pipeline change without Hy-MT2: switch ingest_long_context summarization to a 2-step (translate then summarize) prompt for the affected strata. Hy-MT2 specialist is NOT adopted — the win was decomposition, not the specialist. Mark `intake-586` as `not_applicable` (specifically); update relevant prompts in `epyc-orchestrator`. |
| Mixed results, ambiguous threshold | Escalate to user for stratum-by-stratum decision. Do NOT auto-adopt. |
| Test infeasible (samples unavailable, STQ1_0 not loadable + 2-bit GGUF crashes, etc.) | Document the blocker. Defer test until the prerequisite resolves; do NOT proceed with adoption decision based on partial evidence. |

### Cost Estimate

- Sample curation: ~1-1.5 hours manual (most time on the mixed-script-structured stratum since Flores-200 covers all single-language strata natively after the 2026-05-21 refocus)
- Pipeline A baseline run (50 × 3 reps): ~30 min on ingest_long_context :8083
- Pipeline B run (50 × 3 reps): ~20 min Hy-MT2 + ~30 min Qwen3-Next-80B = ~50 min total
- Pipeline C run (50 × 3 reps): ~60 min on ingest_long_context (2 calls per sample)
- KB-RAG retrieval eval: ~10 min (precomputed query set)
- LLM-as-judge pairwise on gemma4-26B-A4B: ~20 min (150 judgments × 3 pipelines)
- Total: ~3-4 hours user-attended runtime + 2-3 hours sample curation

### What this test does NOT decide

- Whether to deploy a translation route as a first-class stack role (still NO regardless of outcome — even H1 maps to "optional pre-encode tool", not a server role).
- Whether the AngelSlim 1.25-bit quantization recipe scales beyond 1.8B (separate question, gated on Tencent releases per the AngelSlim stub correction).
- Anything about other AngelSlim techniques (Sherry, SpecExit, Tequila, DAQ) — those are tracked on [[angelslim-techniques-evaluation]] and are independent of this test.

### Reporting

When the test runs, record results in `progress/2026-MM/YYYY-MM-DD.md` with: sample set + provenance, per-stratum NDCG@5 / win-rate / structural-fidelity numbers, decision under the acceptance criteria above, and update both this handoff and `intake-586` verdict accordingly. Per `feedback_handoff_driven_tracking`, no test runs without a handoff update afterward.

Cross-references: [[angelslim-techniques-evaluation]] (umbrella for Sherry/SpecExit/Tequila/DAQ — independent of this MT test), [[searxng-bash-websearch-bridge]] (multilingual ingest origin), [[colbert-reranker-web-research]] (external snippet pipeline).

## Research Intake Update — 2026-05-26

### New Related Research
- **[intake-609] "FastMCP — Pythonic framework for building MCP servers and clients"** (`github.com/prefecthq/fastmcp`, Apache-2.0, v3.3.1)
  - Relevance: K6's original phrasing offered "`kb_search` MCP tool OR in-orchestrator helper" — the **skill route** (`.claude/skills/kb-search/SKILL.md`) shipped 2026-05-06 and satisfies the Explore-subagent integration goal. The MCP-tool variant was not built and is not currently needed.
  - 2026-05-26 update: standalone `fastmcp>=3` is now pinned in `epyc-orchestrator/pyproject.toml` and `src/mcp_server.py` runs on it (migration verified, 40 MCP tests pass). If a future workflow needs an MCP-tool variant of `kb_search` (e.g., a different agent runtime that does not consume Claude Code skills, or a multi-MCP-client scenario), the framework choice is settled and the scaffold pattern in `src/mcp_server.py` is the reference. **No outstanding K6 work is unblocked** — the skill route is the production path.
  - Cross-ref: the FastMCP v3 middleware pattern being built out in [`tool-output-compression.md`](tool-output-compression.md) Phase 4 (P4b) is the precedent if a `kb_search` MCP variant is ever added.

## Research Intake Update — 2026-05-27

### New Related Research
- **[intake-611] "agentmemory V4 — LongMemEval real-retrieval #1 (96.2%)"** (`github.com/JordanMcCann/agentmemory`, MIT)
  - Relevance: its retrieval engine is **local and self-hostable** (all-mpnet-base-v2 embedder + ms-marco-MiniLM cross-encoder reranker) — directly compatible with our ONNX/MaxSim stack, unlike OpenAI-bound peers.
  - Key technique: **six-signal hybrid retrieval** — semantic + BM25 lexical + graph activation + importance + confidence + temporal proximity, fused per query; deterministic HNSW (SHA-256 content-based level assignment).
  - Reported results: 96.20% LongMemEval_S real-retrieval (481/500), beats PwC Chronos 95.6%; per-category single-session 100% / knowledge-update 97.4% / temporal 96.2% / multi-session 93.2%.
  - Delta from current approach: our K1–K6 layer is single-signal ColBERT MaxSim over markdown. agentmemory adds BM25 + graph-activation + temporal-proximity signals plus a cross-encoder rerank stage — additive on top of the existing encoder, and corroborates the `colbert-reranker-web-research.md` rerank direction.
- **[intake-610] "Quarq Agent (agent-oss)"** (`github.com/quarqlabs/agent-oss`, Apache-2.0)
  - Relevance: hybrid vector+keyword retrieval with a **self-correcting fallback pass** when initial evidence is incomplete — a retrieval-policy pattern for kb_rag query-time.
  - Key technique: self-correcting fallback retrieval + HyDE query optimization.
  - Reported results: 99.59% on a 241-q LongMemEval-S *partial checkpoint* (unverified — see intake-610 contradicting_evidence; verified field full-run SOTA is ~96.2%).
  - Delta from current approach: adds a fallback retry loop on low-evidence queries; we currently do single-pass MaxSim retrieval.

## Research Intake Deep-Dive — 2026-05-27 (six-signal retrieval → scoped K9/K10)

Source-level deep dive of intake-611 (agentmemory V4) + intake-610 (agent-oss) at `research/deep-dives/2026-05-27-agent-memory-cluster.md` (both repos cloned + read at file:line). The Phase-4a note above flagged "six-signal hybrid retrieval" as a candidate; the deep dive **scopes it down** — most of agentmemory's six signals are tuned to conversational agent-memory and do not transfer to a structured-markdown corpus. Concrete, gated additions to the **already-landed K1–K6 ColBERT layer**:

- [x] **K9 — Cross-encoder rerank stage.** ✅ CODE LANDED 2026-05-27; K7 measured 2026-06-13. New `src/retrieval/cross_encoder.py` (ONNX, mirrors `colbert_encoder.py`; graceful no-op when model absent) + `cross_encoder.rerank()` blend `(1−w)·maxsim + w·sigmoid(CE_logit)` (agentmemory `reranking.py:62`). Wired into `kb_rag.query(rerank=…, rerank_weight=…)` over the top-`4×K` pool (`KB_RAG_RERANK` / `_WEIGHT` / `_POOL_MULT` env overrides). Model downloaded: `cross-encoder/ms-marco-MiniLM-L-6-v2` ONNX int8 at `/mnt/raid0/llm/models/ms-marco-minilm-l6-v2-onnx`. Live smoke: relevant logit +8.0 vs irrelevant −11.3; rerank flips a lower-base relevant doc to top. 4 unit tests (mocked + real-model skipif). **K7 verdict**: useful for first-rank/recall@3, not default-safe; rerank configs missed 3-5 all-evidence cases on the certification pool.
- [x] **K10 — Temporal Gaussian recency signal.** ✅ CODE LANDED 2026-05-27; K7 measured 2026-06-13. `_recency_score(mtime, now, σ_days)` Gaussian + blend in `kb_rag.query(recency_weight=…, recency_sigma_days=…)`; `mtime` now SELECTed from the K3 catalog. Default `recency_weight=0.0` → identical to MaxSim-only (back-compat); env overrides `KB_RAG_RECENCY_WEIGHT` / `KB_RAG_RECENCY_SIGMA_DAYS` for sweeps. 2 unit tests (monotonicity + tie-break reorder). **K7 verdict**: validated; `recency_w0.3_s90` is the safest default candidate (0 missed-all-evidence, recall@10 within noise of the aggregate winner).
- [ ] **K11 (optional, measure-first) — FTS5 lexical signal.** SQLite FTS5 porter-stemmed `rank` as a third signal. ColBERT MaxSim is already lexical-strong, so marginal; only adopt if the K7 eval shows exact-match / variant-form misses. Low cost (SQLite already in the stack).

### Diagnostic Update — 2026-06-12

Tiny, non-certifying K-RAG diagnostic artifacts live at `/mnt/raid0/llm/tmp/k_rag_diag_20260612/` (`summary.json`, `rows.jsonl`, `cases.json`). Corpus state during the run: 137 files / 4,634 chunks, catalog max mtime `2026-05-30T11:22:46Z`, while current Fable/J9/J13/J7 docs are from 2026-06-12. Runtime state: orchestrator `.venv` failed to import `onnxruntime`; `/mnt/raid0/llm/pace-env` loaded both ColBERT and cross-encoder.

Results over 8 hand-curated file-recall cases:
- MaxSim baseline: mean recall@3 `0.5208`, @5 `0.5833`, @10 `0.7083`, perfect@10 `5/8`.
- Recency-only sweeps (`weight=0.1/0.3`, `sigma=90`) were neutral on this stale set.
- Cross-encoder rerank (`weight=0.3/0.6`) improved recall@10 to `0.75` and perfect@10 to `6/8`, with no @3 gain.

Decision: keep K9 worth-testing in the formal K7 sweep, keep K10 neutral/default-off, and do not promote any KB-RAG default weights from this diagnostic.

### K7 Harness Update — 2026-06-12

Branch `feat/kbrag-k7-eval` in `/mnt/raid0/llm/tmp/kbrag-k7-worktree` is committed at `280c092` (`Add KB-RAG K7 eval harness`). It adds:
- `scripts/kb_rag/eval_k7.py` plus `kb_rag eval` CLI subcommand.
- `scripts/kb_rag/k7_seed_cases.json`: 20 curated multi-hop evidence-file recall cases (12 HotpotQA-template, 8 LoCoMo-template), validated against disk with zero missing evidence files.
- Metrics: recall@3/5/10, perfect@k, first/all evidence ranks, protocol splits, config comparison across MaxSim, recency, rerank, and hybrid configs.
- Validation: `ruff check`, `ruff format --check`, `tests/unit/test_kb_rag_eval.py` pass; existing retrieval suite passes with the known exception that orchestrator `.venv` lacks `onnxruntime` for the real cross-encoder test. `/mnt/raid0/llm/pace-env` loads ONNX Runtime and discriminates the real cross-encoder smoke (`4.79` relevant vs `-11.29` irrelevant logit).

Operational note: the fresh index build is CPU-heavy under ONNX Runtime, not CPU-light. The first unconstrained attempt was stopped to avoid contaminating live AutoPilot timing; the current build writes to `/mnt/raid0/llm/tmp/kbrag_index_k7_20260612` under `nice=15`, `taskset`-constrained to CPUs `168-175`, with thread env caps. Full K7 sweep should run against that tmp index when complete, then document the result before any default-weight promotion.

**Explicitly NOT adopting** (deep-dive rationale): spreading-activation graph signal (agentmemory's entity extraction is regex-based and brittle on structured markdown — would need spaCy/LLM NER at high cost for low gain), importance×confidence (all KB chunks ≈ equal importance by design), node-activation LRU recency (a static-doc corpus has no meaningful access-frequency signal). agentmemory's six-signal weights are hand-tuned to **conversational** QA over 46 iterations — any blend we adopt must be re-tuned on our query distribution via K7, not copied.

**Self-correcting two-pass retrieval (from agent-oss, intake-610).** Backend-agnostic pattern worth a K-track later: if a downstream consumer (Explore subagent / orchestrator) signals "evidence incomplete", emit gap-queries and re-retrieve at a lower MaxSim threshold before answering (agent-oss `agent.py:1488-1566`). Defer behind K9/K10 — it needs a consumer that emits the incompleteness signal; note it here so it isn't re-discovered.

Cross-refs: [[colbert-reranker-web-research]] (shared encoder + rerank), `research/deep-dives/2026-05-27-agent-memory-cluster.md`, intake-610/611.

## Research Intake Deep-Dive — 2026-05-27 (Understand-Anything: lift-not-fork shopping list — GATED, do not action yet)

Deep-dive of [intake-625](../../research/intake_index.yaml) at `research/deep-dives/2026-05-27-understand-anything-vs-gitnexus.md` (Lum1104/Understand-Anything cloned at commit `26edf61` — full 547-commit history + all 9 agent files + 7-phase `SKILL.md` read). Two of UA's three design-reference patterns have a natural home **here**, but the revisit-trigger has four gates and none are currently met — record now so the patterns aren't re-discovered later.

**Pattern A — LLM-annotation layered on Tree-sitter structural truth (KB chunking skeleton).** UA's `file-analyzer.md:15` enforces a two-phase split: a deterministic `extract-structure.mjs` (334 LOC, 10 first-class Tree-sitter langs) produces a *structural skeleton* (functions, classes, imports, exports, size, complexity); the LLM then annotates the **skeleton + source** with summary, tags, complexity-grade, and semantic edges. A separate `merge-batch-graphs.py` canonicalizes IDs and drops orphans deterministically after the LLM. **Application here:** for code-doc chunks, feed skeleton-only to the annotator instead of raw source (cheaper, less drift); make the K3 catalog hold the skeleton; add a canonicalization pass before the K5 index write. Concrete artifact to port: `understand-anything-plugin/skills/understand/extract-structure.mjs` (or build the equivalent on our existing parsers).

**Pattern B — Dependency-ordered guided context expansion (BFS from entry-point).** UA's `tour-builder.md` Phase 1 is a **deterministic** topology script: fan-in / fan-out rankings, an explicit entry-point scoring rubric (`README.md` at root = +5, `main.{ts,py,go,rs,...}` = +3, root/one-deep = +1, high-fan-out top-10% = +1, low-fan-in bottom-25% = +1), BFS-with-depth-bands from the top entry point, bidirectional-cluster detection. The LLM only writes narrative around this; ordering is computed. **Application here:** for a KB query hit, expand context by BFS over `[[wiki-link]]` cross-references (depth ≤ 2), not by flat top-k. Bands the LLM sees the same way UA bands tour steps. Also applies to handoff-index reading order (entry = `master-handoff-index.md`, edges = `[[…]]` graph), but that's a separate skill — not a kb_rag task.

**Pattern C — Code → business-domain mapping schema.** UA's `domain-analyzer.md` ships a 3-level `domain → flow → step` hierarchy with `flow_step.weight` as monotonic ordering in [0,1] and `step.filePath + lineRange` as the round-trip anchor back to source. Schema is well-specified; caveat is that UA leaves the filePath/lineRange anchor as a *soft prompt rule*, not an enforced post-write check. **Application here:** orthogonal to kb_rag's current scope — only relevant if a future handoff explicitly asks for a code-to-domain view; if lifted, enforce the anchor at write time.

**Gating — DO NOT LIFT YET.** All four gates must hold before any of the above is actioned (intake-625 verdict_justification, deep-dive §6):
1. **Internal pull** — kb_rag declares an explicit chunk-skeleton or guided-expansion requirement that current K1–K10 + measure-first K11 does *not* cover. The current K9/K10 work (cross-encoder + Gaussian recency) and any K7 outcomes must be **measured** before adding a structural-skeleton chunker — additional retrieval features only after K-RAG-1 lands.
2. **Sustainability** — UA shows a sustained second-committer ≥30 commits / ≥60 days. Today: Lum1104 = 83% of 547 commits; second-largest contributor = 9 commits (1.6%).
3. **Stability** — UA ships a `CHANGELOG.md` and a written schema-stability commitment for `knowledge-graph.json`. Today: no CHANGELOG.
4. **Empirical** — third-party-published full-rebuild + incremental benchmark on a >1 k-file repo. Today: only GitHub social signals (39 127 ★ / 3 116 forks, 10 weeks old) — explicitly *not* a substitute per [[feedback_credibility_from_source_not_readme]].

**Earliest realistic revisit:** 2026-08. **Do NOT** install the `understand-anything` plugin on epyc-root, **do NOT** swap GitNexus, **do NOT** lift UA's 9-agent decomposition (no ablation justifies it). If gate 1 fires before 2026-08, the lift-not-fork shopping list above is the action plan — port the deterministic phase scripts, not the prompts.

Cross-refs: [[meta-harness-optimization]] (parallel "do-not-lift the 9-agent decomposition" note), `research/deep-dives/2026-05-27-understand-anything-vs-gitnexus.md`, intake-625, [[project_gitnexus_cli_only_setup]] (GitNexus is the production code-intelligence layer; UA does not displace it).

## Research Intake Update — 2026-06-10

### New Related Research
- **[intake-686] "turbovec — Google TurboQuant vector index (Rust + Python, SIMD-accelerated quantized vector search)"** (github.com/RyanCodrai/turbovec)
  - Relevance: a low-RAM local vector index applying Google TurboQuant (arxiv:2504.19874, ICLR 2026) to standalone retrieval — ~8x RAM cut (31 GB → 4 GB for 10M docs) with FAISS-parity/better search. Candidate low-RAM index for the KB-RAG corpus and the orchestrator's FAISS repl_memory/strategy_store path.
  - Key technique: data-oblivious quantization (no training), random rotation + per-coordinate Lloyd-Max (TQ+), 2/4-bit packing, hand-written AVX-512BW/NEON nibble-LUT distance kernels with runtime ISA detection.
  - Reported results: 16x raw compression at 2-bit; +0.3–3.4 R@1 vs FAISS PQ; x86 search +1–6% (4-bit), ARM +12–20%.
  - Delta from current approach: NextPLAID (intake-355) is the existing Rust-local-PQ comparable; turbovec is not yet integrated. **The 12–20% headline is ARM/NEON-specific — on EPYC's AVX-512 x86 the gain is only 1–6%, so the value is compression/RAM, not QPS.** Needs a recall+RAM+QPS bench at AVX-512 before any swap; separately mine its AVX-512BW kernels against our Q8_0 GEMV kernels. credibility 3 (TurboQuant has independent third-party ports).

### Deep-Dive Refinement (2026-06-12) — refined to NO-GO / parked
The intake premise doesn't hold against our **actual** baseline: repl_memory/strategy_store run `faiss.IndexFlatIP` (EXACT, dim=1024 BGE-large, `faiss_store.py:103`), **not** a PQ index — so turbovec's 8x-RAM/PQ-parity story has nothing to beat. Live footprint is ~304 MB (episodic ~72.8K vecs + strategy ~1.3K) of 1.1 TB → the ~266 MB saving is 0.024% of RAM; the 31 GB→4 GB headline is a 10M-doc corpus we don't have. The +12–20% QPS is ARM/NEON-only; on EPYC AVX-512 it's PQ-parity-to-negative. **Kernel-mining REJECTED** — turbovec's AVX-512BW kernel is a FastScan nibble-LUT *distance scanner* (LUT-throughput-bound); our Q8_0 kernel is a BW-bound 8x8 integer GEMV — different op/layout/bottleneck, nothing ports. KB-RAG is multi-vector MaxSim, which turbovec's single-vector MIPS API doesn't model. **WATCH-gate:** revisit only if a single-vector corpus exceeds ~1M vectors under real RAM pressure. Full: `research/deep-dives/2026-06-12-turbovec-vector-index.md`.

### Incremental wiki/KB refresh (merged from autowiki stub, 2026-06-12)

Scope inherited from `autowiki-incremental-kb-generator.md` (now in [`../completed/autowiki-incremental-kb-generator.md`](../completed/autowiki-incremental-kb-generator.md)) per the 2026-06-12 Fable 5 portfolio pass — it was an extension of this handoff's compiled-KB work (intake-657, Factory.ai AutoWiki patterns; full mining in `research/factory-ai-harvest-2026-06-03.md` Part 3E). Goal: refresh generated wiki/KB pages **incrementally** (only pages whose sources changed), closing the staleness gap the project-wiki lint flags. The reproducible core (SaaS parts — App Cloud Sync, web viewer, GitHub-Wiki sync — excluded):

- **Page → source-paths manifest**: every generated page declares its source file set with a content hash per source-set; on a push, recompute only pages whose source-set intersects the git diff (first run full, later runs reuse prior work). Pages follow a structured topic taxonomy ({architecture overview, module breakdown, API, conventions, setup}, cross-linked).
- **Change-driven ColBERT re-embed**: re-embed only the changed chunks into the existing ColBERT index (current build = 409 files / 13,537 chunks / 17 min full rebuild) rather than rebuilding — extends the K3 content-hash + K5 on-commit machinery already landed; cross-ref [`colbert-reranker-web-research.md`](colbert-reranker-web-research.md) for the shared encoder.
- **CI/nightshift trigger**: a push-triggered job with a `paths:` filter, or a `scripts/nightshift/` schedule — the OSS equivalent of Factory's `/install-wiki` GitHub Action.

Open design questions (carried from the stub, unresolved):

1. The page→source-paths manifest is also the basis for **drift detection** — does it subsume / improve the `scripts/validate/` document-drift validator?
2. Generator model: which local model writes the pages, and how do we keep it from hallucinating structure (lint gate on output)?
3. Scope: in-repo git-versioned wiki only (we already have this — git = versioning); any app/UI sync is SaaS-only, skip.
4. Trigger cadence: on-push CI vs nightshift batch — and how does it coordinate with the autopilot loop without contending for inference?
