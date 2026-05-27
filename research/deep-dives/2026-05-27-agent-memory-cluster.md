# Agent-Memory Cluster — 2026-05-27

Source-level deep dive of the four intakes from the 2026-05-27 `/research-intake` of `github.com/quarqlabs/agent-oss`. Both repos were cloned to `/tmp` and read at file:line; the paper was read in full via ar5iv.

**Intakes in scope:**
- **intake-610** — Quarq Agent / agent-oss (`github.com/quarqlabs/agent-oss`, Apache-2.0) — memory-first agent, claims 99.59% LongMemEval-S
- **intake-611** — agentmemory V4 (`github.com/JordanMcCann/agentmemory`, MIT) — verified LongMemEval real-retrieval #1, 96.2%
- **intake-612** — LongMemEval-V2 (arxiv:2605.12493, UCLA NLP) — agent-experience memory benchmark
- **intake-613** — OSS Insight "Agent Memory Race of 2026" (landscape blog)

## Executive Summary

The headline reverses on inspection. **agent-oss's 99.59% is not a benchmark result** — it is 240/241 on a *partial* LongMemEval-S run (≈48% of the 500-question suite), self-graded by a custom binary judge with 11 explicit leniency rules, using a model id `gpt-5`, against a "cleaned" dataset variant, with **no results file committed** (only `reports/eval_checkpoint.json = {"question_id":"4dfccbf7","last_chunk_index":43}`). The verified field leader is **agentmemory at 96.2% (481/500)** — full run, real-retrieval enforced by a hard `assert not USE_DIRECT_CONTEXT`, official LongMemEval judge prompts, committed `longmemeval_results_opus6.json` + `fullrun_opus6.log`. Both repos are solo/small efforts; agentmemory is the credible one.

For EPYC the value is **pattern transfer, not adoption**: both systems are cloud-LLM-bound at the generation layer (agent-oss is hard-wired to OpenAI end to end; agentmemory's *retrieval engine* is fully local but its benchmark generator/judge are Claude Opus + GPT-4o). The transferable wins, ranked by ROI against our already-landed ColBERT KB-RAG and our B1 User-Modeling slot, are below. LongMemEval-V2 is a real aspirational eval target but is web-agent-specific (WebArena/ServiceNow) and infra-heavy.

---

## intake-610 — agent-oss (source-level)

7,327 LOC Python; the live system is a single 2,207-line `agent.py` (`agent_v1/v2/v3.py` are dead prototypes kept in tree). Verified each advertised feature against code:

| Claim | What the code actually does | Verdict |
|---|---|---|
| **Temporal Truth Protocol** | Single-timestamp schema. `created_at` = storage time (`datetime.now()`); event date lives **inside the free-text `content` string**. A learn-time prompt converts relative→absolute dates (agent.py:1707); a reason-time prompt tells the LLM to trust the in-text date over the `[STORED_AT]` prefix (agent.py:1096). No `event_time` column, no temporal index, no temporal retrieval. | **Prompt-only.** Real failure-mode mitigation, zero structural mechanism. |
| **Hybrid retrieval + self-correcting fallback** | Union-then-dedupe by UUID (agent.py:841-851), re-sorted by storage recency — **no score fusion**. Keyword search is case-insensitive substring (agent.py:426-442), not BM25. The fallback (agent.py:1488-1566): if gen-LLM emits `REQUIRED_DATA` + gap queries, re-retrieve at a lower threshold, merge, re-generate with a `CRITICAL OVERRIDE` prompt. | Fusion is weak; **the two-pass self-correcting loop is genuinely good and backend-agnostic.** |
| **Quantitative fidelity** | Numbers stored as free text; enforced by dense ingest/reason prompts + a `<thinking>` "NUMERIC EVIDENCE TABLE" (agent.py:1196-1199). No numeric schema. | **Prompt-only**, coupled to GPT-4.1 instruction-following. |
| **Memory separation** | **Real, structural.** Semantic + Episodic = separate folders + separate FAISS indices (`VectorMemoryManager`); Procedural = a different schema entirely (rule objects with `target_entity`/`tags`, no FAISS, tag-routed via a second LLM call, agent.py:871-945). Three labeled blocks injected at generation. | **Structural — worth studying for B1.** |
| **HyDE** | Mislabeled. Actually multi-query decomposition: gpt-4o-mini emits 4 query angles (comprehensive/entity/action/literal-noun) + keywords + search mode (agent.py:625-812). | Useful pattern, not classical HyDE. |
| **LongMemEval 99.59%** | 240/241 partial run; judge = single `gpt-5` call with 11 leniency rules (run_dataset_evals.py:176-206); dataset = HF `longmemeval_s_cleaned.json`; no results file committed. | **Not a usable number.** |

**Backend:** hard OpenAI. `raise ValueError` on missing `OPENAI_API_KEY` at import; `ChatOpenAI(gpt-4.1)` ×2, `OpenAIEmbeddings(text-embedding-3-large, dim=1536)`; no `base_url`/litellm/provider-agnostic path. Embeddings baked at 1536-dim — swapping the embedder forces a full index rebuild.

**Transferable (backend-agnostic):** (1) self-correcting two-pass retrieval (`REQUIRED_DATA` → gap-query → re-retrieve → re-generate); (2) multi-query decomposition; (3) structural semantic/episodic/procedural separation. **Not transferable:** Temporal Truth Protocol and quantitative fidelity (prompt-only, GPT-4.1-coupled); the benchmark numbers.

## intake-611 — agentmemory V4 (source-level)

~11,928 LOC Python. The retrieval engine is the asset.

**Six-signal fusion** (retrieval.py:240-242) — a hardcoded weighted linear sum (weights sum to 1.0, hand-tuned over 46 iterations against LongMemEval's *conversational* QA distribution):

```
score = 0.30·semantic + 0.12·lexical + 0.18·activation
      + 0.18·graph    + 0.10·importance + 0.12·temporal
```
- `semantic` = cosine(query, node) via all-mpnet-base-v2 (local)
- `lexical` = SQLite FTS5 BM25-like rank, max-normalized (porter stemmer) — **not** standalone BM25
- `activation` = `min(1, node.activation)`, an LRU access counter
- `graph` = `spreading_activation()` — BFS from recently-accessed seed IDs, decay 0.5/hop, over a regex-extracted entity graph (graph.py:63-86, 126-329)
- `importance` = `importance · calibrated_confidence`
- `temporal` = Gaussian `exp(-0.5·((t−center)/σ)²)`, σ default 168h

**Then** a local cross-encoder reranker (ms-marco-MiniLM-L-6-v2) over the top `4×limit` pool, final blend `0.70·fusion + 0.30·sigmoid(CE_logit)` (reranking.py:62).

**Deterministic HNSW** (ann_index.py:87-104): pure-Python HNSW; SHA-256 of the first 16 float dims sets each node's level, so the graph is insertion-order-independent (plus `PYTHONHASHSEED=42`). **Important caveat:** the 95.6→96.2 jump came *from finding a seed whose graph structure happens to suit LongMemEval's query distribution* (per the repo's own FINAL_REPORT). It is reproducible, not generalizable — do not read 96.2 as +0.6 of real signal over 95.6.

**Verification:** dataset = HF `xiaowu0162/longmemeval-cleaned` (`longmemeval_oracle.json`, standard split); `has_answer`/`answer_session_ids` stripped at ingest; `assert not USE_DIRECT_CONTEXT` guards real-retrieval; judge = gpt-4o temp0 seed42, official prompts verbatim (one strictly-harder temporal deviation). Results + per-case log committed. **Credible.** Generator (Claude Opus 4.6) + judge (GPT-4o) are cloud, but `MemoryStore`/`RetrievalEngine` run with `dependencies = []` (TF-IDF fallback) — the retrieval engine is fully self-hostable.

**Transferability into our ColBERT-MaxSim markdown RAG** (single-signal dense over wiki/handoffs today):

| Component | Value | Cost | Decision |
|---|---|---|---|
| **Cross-encoder reranker** | HIGH (+3-8% on hard cases) | LOW (~67 LOC, drop-in over top-K) | **Adopt** — coordinates with `colbert-reranker-web-research.md` |
| **Temporal Gaussian decay** | HIGH (our corpus is dated: progress/, dated handoffs) | ~1h (needs a per-chunk timestamp) | **Adopt** |
| FTS5 lexical signal | MEDIUM (ColBERT already lexical-strong) | LOW | Optional / measure |
| Spreading-activation graph | LOW-MED (regex extraction brittle on structured markdown) | HIGH (proper NER/LLM extraction) | **Skip** |
| importance×confidence | LOW (all KB chunks ≈ equal importance) | — | **Skip** |
| activation (recency/freq) | LOW (static KB) | — | **Skip** |

Weights are tuned to conversational QA — any blend we adopt needs re-tuning on our query distribution (defer to the K7 eval harness).

## intake-612 — LongMemEval-V2 (paper)

Reframes memory from chat-history recall (V1, arxiv:2410.10813) to **web-agent environment expertise**: 451 human-curated questions over WebArena (Magento/Reddit) + WorkArena (ServiceNow) trajectories; multimodal (screenshots); Small haystack 100 traj/~25M tok, Medium ~500 traj/~115M tok. Five abilities: static state recall, dynamic state tracking, workflow knowledge, environment gotchas, premise awareness (abstention). Frontier models answer 1.6-4.5% without context → genuine environment-specificity.

Operationalizes memory as `Insert(trajectory)` / `Query→evidence`, truncate to 200K, fixed reader = **Qwen3.5-9B** (CPU-viable), GPT-5.2 judge for gotchas/abstention.

Two methods: **AgentRunbook-R** (RAG with 3 pools: raw-slice/event/note; 58.6% Small) and **AgentRunbook-C** (trajectories-as-files + a coding agent in a sandbox with a workflow doc, query-time manifests, helper scripts; 72.5% Small) — C beats off-the-shelf Codex (69.9%) and the slice+notes RAG baseline (51%). Ablations: workflow-doc −4.8pp (framing matters), helper scripts −3.5pp, manifest −0.2pp accuracy but big latency win. Latency: R ~27s, C ~108-140s. Oracle upper bound ~84% → ~12pp headroom; gotchas plateau at 34-48% for all methods (the unsolved category).

**Relevance to EPYC:** AgentRunbook-C *is* the REPL-as-evidence-retriever pattern — and we already have a REPL + skill-bank + (via `unified-trace-memory-service.md`) a SQLite trajectory store. The missing pieces are the **manifest** (query-time index of what memory holds) and the **workflow document** (reframe the agent as a memory module). But LME-V2 itself needs WebArena/ServiceNow environments or pre-collected haystacks to run — it is an aspirational eval target, not a drop-in. Our current markdown RAG would land in the 42-51% RAG-baseline band. Reader Qwen3.5-9B fits our CPU profile.

Referenced-arxiv expansion candidates (NOT ingested this run — recorded for a future, scoped intake): A-MEM (2502.12110), Memory-R1 (2508.19828), ReasoningBank/Agent-Workflow-Memory (2509.25140), Mem-α (2509.25911), "Coding agents as long-context processors" (2603.20432), FileGramBench (2604.04901), MemGPT (2310.08560), MemoryArena (2602.16313).

## intake-613 — OSS Insight landscape (corroboration)

Five Q1-2026 memory repos, four architectures, >80k combined stars: MemPalace (43k★, ChromaDB verbatim — and the article confirms the **AAAK compression −12.4pt** correction, refining intake-326), OpenViking (filesystem tiered loading), code-review-graph (code KG, 6.8-49× token reduction), SimpleMem (multimodal), engram (single Go binary SQLite+FTS5 — *distinct* from the LongCat/paper Engram, see `project_engram_vs_longcat_distinction`). Stated open problem: **no system unifies general-conversation memory and code-specific knowledge graphs** — exactly the seam where our GitNexus (code) + internal-kb-rag (markdown) + B1 (user) memories sit unintegrated. Neither agent-oss nor agentmemory appears in this coverage.

---

## Integration Decisions (no new handoff — folds into existing active work)

1. **Six-signal retrieval → `internal-kb-rag.md`** (pipeline-integration-index P5). Scope down to the two HIGH-ROI signals: cross-encoder reranker (coordinate with `colbert-reranker-web-research.md`) + temporal Gaussian decay. FTS5 lexical optional/measure; graph/importance/activation skipped. Weights re-tuned via the existing K7 eval harness. Added as a deep-dive follow-up section there.
2. **agent-oss patterns → `delta-mem-reproduction.md`** (owns B1). Correction to the original intake note: the Temporal Truth Protocol is *prompt-only* — the structurally interesting agent-oss pattern for B1 is the **episodic/semantic/procedural separation** (three stores, three retrieval policies), plus the **self-correcting two-pass retrieval** loop (also relevant to internal-kb-rag). Temporal-truth/quantitative-fidelity demote to "prompt patterns, low-cost, GPT-4.1-coupled."
3. **LongMemEval-V2 → `research-evaluation-index.md` P3 + noted in `delta-mem-reproduction.md`** as the updated memory eval target, with the honest caveat that it is web-agent-specific and needs WebArena/ServiceNow haystacks; reader Qwen3.5-9B is CPU-viable. AgentRunbook-C flagged as a forward cross-ref against our REPL + `unified-trace-memory-service.md` (not actioned this run).

**Cross-refs:** [[internal-kb-rag]] · [[delta-mem-reproduction]] · [[colbert-reranker-web-research]] · [[unified-trace-memory-service]] · intake-326 (MemPalace) · intake-346 (Mem0) · 2026-05-19-frozen-memory-cluster.md
