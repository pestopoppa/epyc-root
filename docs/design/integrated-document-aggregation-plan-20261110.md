# Integrated document aggregation plan: exhaustive QA over 1M+ token corpora

**Status**: design only, rev 2, 2026-11-10 (operator-approved; no compute run). Tracked by `## Track: integrated-aggregation` in [`handoffs/active/knowledge-pipelines.md`](../../handoffs/active/knowledge-pipelines.md) (boxes AGG-0.1 to AGG-0.5).

Rev 2 (operator revision): §(b) is now ONE integrated pipeline over the current document flow with a cost-based
planner; SLIDERS closes as **superseded**; constructed golds need hand-verification; Phase 0 also tests the
planner's small-corpus path against today's flow.

Scope: operator-requested design audit. No compute, no processes.
Evidence labels: **[measured]** = a number with a file:line; **[inferred]** = derived from measured numbers;
**[speculation]** = my estimate. Paths: ROOT = `/workspace`, ORCH = `/workspace/repos/epyc-orchestrator`,
SL = `/mnt/raid0/llm/scratch/sliders/sliders`.

---

## (a) Audit of `sliders-paths-forward.md`

**Right (kept):**
- The call-site table (SL `modules/extract_schema.py:99` relevance chain, `:1031-1048` doc×chunk×sample fan-out,
  `modules/generate_schema.py:157` schema induced per question) is accurate; I re-read those lines.
- Diagnosis that SLIDERS pays its extraction cost **per question** and that retrieval is the wrong tool for
  exhaustive aggregation. Ingest-once + SQL is the correct structural lever (operator agrees).
- `DocumentREPLEnvironment._search_sections` is a lexical substring scan over one document
  (ORCH `src/repl_document.py:221-240`) — correct, and therefore not a corpus-scale retriever.

**Wrong or materially misleading:**
1. **It blames the wrong stage for the 757 calls.** One 10-K at SLIDERS' `chunk_size: 16000` chars
   (SL `default_config.yaml:159`) is roughly 30-45 chunks [inferred: CORNING PDF 1.4 MB; parse ratio is
   speculation]. Relevance + extraction is therefore ~60-90 calls, not 757. `diag-r234c-sliders.md` §B shows the
   real runaway: unbounded decodes (slots at n_decoded 17.4k, 1.4-3.8 t/s per slot under `-np 4`), 19,430 SQL
   emissions, controller calls queued 3.77M ms behind them. The blow-up is **reconciliation/PK/SQL loops plus
   uncapped generation** — decode-side, not O(chunks).
2. **"Jev gives only ~1.3-2x" undercounts two levers.** (i) prompt-prefix caching: SLIDERS'
   `extract_schema.prompt` is 17,258 bytes (≈4-5k tokens [speculation]) — comparable to the 4k-token chunk it
   wraps, so a cached prefix halves prefill per extraction call; the backend already forwards `cache_prompt` and
   `id_slot` (ORCH `src/backends/llama_server.py:130-148, 333-334`) and `prefill_metrics.py` pins the
   instructions+schema-then-state prompt order (routing-program.md:3462). (ii) the native catalogue:
   `run_typed_decisions_native` scores a whole catalogue of closed-set questions in **one** constrained generation
   (ORCH `src/typed_decisions/native.py:419-431`), so N reconciliation conflicts become 1 call. Measured
   native-vs-JSON on the worker: 1.46 s vs 14.0 s (9.6x) at equal accuracy (routing-program.md:3120-3122)
   [measured, 24-question set].
3. **The 0.68^N argument misuses the number.** recall@5 = 0.676 is a 5-pointer budget on code/doc navigation
   queries (harness-program.md:2476). A prefilter takes k = 30-100 per field [speculation], and the design below
   never relies on retrieval for exhaustiveness.
4. **"No verified CPU prefill rate."** Qwen3.6-35B-A3B Q8 llama-bench pp512 **500.6 t/s** on the iqk kernel,
   whole host (memory `project_kernel_lineage.md:80`) [measured, llama-bench]. The Phase-0 run itself: 4.05M
   prompt tokens in ≈7 h effective on 24 cores, Coder-30B Q4 ≈ **160 t/s** incl. cache hits [inferred, diag §B].
5. **GPU numbers mis-attributed.** Registry `:2659-2661` (74-114 t/s) is the 35B MTP on the MI210 JSON fixture,
   not gemma and not the 27B. The 27B-class MI210 proxy is Qwen3.6-27B Q8 pp512 **856 t/s** (memory
   `project_mi210_gpu_inference.md:24`) [measured, different 27B].
6. **The kill gate is unanchored.** "+10 pp over the best baseline" with no table-recall metric cannot tell an
   ingest defect from a QA defect; §(c) separates them.
7. **Its experiment is a second system.** It proposed a standalone ingest beside the document flow — exactly what
   the operator now rules out (§(b)).

**Missing:** a zero-LLM extraction path (the ODL structured document already carries tables:
`src/models/odl_structured.py:100` `TableContext`, surfaced by `DocumentChunker.extract_tables_from_structured`
`src/services/document_chunker.py:193` into `DocumentPreprocessResult.tables` `src/models/document.py:376-393`;
and our corpus records that on Oolong the RLM's biggest win was regex with **zero** sub-LLM calls,
frontier-lab-automation.md:262); metadata-derived primary keys (FinanceBench jsonl has company/doc_name);
incremental ingest and lazy backfill; and that `ingest_long_context` is an alias on :8083 shared with
`architect_critic` (registry `:2140-2153`).

---

## (b) ONE pipeline: the current document flow, with every scale-dependent stage as an optional layer

### b.1 The current flow, end to end (file:line)

| Step | Where | What it produces |
|---|---|---|
| 1 Detect + route | `DocumentPreprocessor.needs_preprocessing` `src/services/document_preprocessor.py:431`, `_extract_document_paths` `:655`, `enrich_task_ir` `:898` | document paths from the task IR; triggers preprocessing |
| 2 Parse | `PDFRouter` `src/services/pdf_router.py:115` (ODL runtime check `:41`, garbage/entropy quality gates `:160-188`) → `ODLStructuredDocument` `src/models/odl_structured.py:126` with `HeadingNode:51`, `FigureContext:72`, `TableContext:100`; `_extract_structured_document` `document_preprocessor.py:286`; routing default ODL (P-DOCPARSE-1, knowledge-pipelines.md:21; ODL-013 r2 NO DECISION) | structured document (headings, tables, figures, bboxes) |
| 3 Chunk | `DocumentChunker.process` `src/services/document_chunker.py:291`, `chunk_by_odl_headings` `:405`, `extract_tables_from_structured` `:193`, `assign_page_ranges` `:241` | `DocumentPreprocessResult` (`src/models/document.py:376`: sections, figures, **tables**, pages) |
| 4a Whole-doc read | `routing_decision.py:229-260`: route to `ingest_long_context` when the request's token count exceeds the default role's per-request n_ctx, else default; triviality guard `:421` demotes easy short prompts | one 27B call on :8083, ≤ 262k tokens (registry `:2140-2153`) |
| 4b REPL over one doc | `DocumentREPLEnvironment` `src/repl_document.py:53` (`_section:115`, `_sections:135`, `_figures:151`, `_search_sections:221` substring scan), factory `create_document_repl:323` | agent navigation inside one document |
| 4c Hybrid pointer search | `context.search` in the context bundle `src/repl_environment/context_bundle.py:265, 580-636` → `context_search.py` (`chunk_sections:206`, `BM25Index:255`, `DenseEmbedder:306`, `pool_dense_embedder:332`, `rrf_fuse`), opt-in arm, pointers only, one index per request | top-k (section, line) pointers |
| 5 KB-RAG (own-KB only) | `src/retrieval/markdown_chunker.py:93 chunk_markdown`, `kb_rag.py` build/update/query (knowledge-pipelines.md:9), ColBERT `colbert_encoder.py` | persistent per-file ColBERT index with content-hash incremental update (knowledge-pipelines.md:85) |

Observations: steps 2-3 already produce **one shared parse artifact** with tables; 4a/4b/4c are three
consumers of it chosen by ad-hoc rules (token count vs n_ctx; opt-in flags); the per-request `context.search`
index is rebuilt every request and thrown away; the only persistent index (KB-RAG) is a different code path over
markdown files, not over `DocumentPreprocessResult`. So today we already have "standalone processes we switch
between" — three of them. The aggregation layer must not become the fourth.

### b.2 The integrated design

**Invariant: one parse, one chunk table, N indexes over it, one planner.** Everything below reads
`DocumentPreprocessResult` (sections with line/page ranges, `tables`) and never re-parses.

```
PDF/MD ──PDFRouter/ODL──▶ DocumentPreprocessResult ──▶ corpus store  (content-hash per doc & chunk)
                                                        ├─ L0 chunks        (always; chunk_by_odl_headings)
                                                        ├─ L1 lexical       (BM25, always; ~free)
                                                        ├─ L2 dense/ColBERT (opt; EG2@256 or GTE-ModernColBERT)
                                                        ├─ L3 facts-det     (opt; tables+regex → DuckDB, no LLM)
                                                        └─ L4 facts-llm     (opt, lazy per field; 35B extract, 27B audit)
question ──▶ PLANNER (typed) ──▶ {whole_doc | repl_nav | retrieval | sql(+backfill)} ──▶ answer (27B)
```

- **Corpus store** = `DocumentPreprocessResult` persisted per doc under a content hash (the KB-RAG
  `content_hash` pattern, knowledge-pipelines.md:85) in a DuckDB file beside the index files. `chunks`,
  `tables`, `facts`, `schema_fields`, `index_manifest` are tables in the same store. L1-L4 are **index builders
  over `chunks`/`tables`**, registered like `context_search`'s per-request index but persistent and keyed by
  (corpus_id, content_hash, builder, model_id) — the "index identity" rule REPL-EMB-2.5 already set
  (harness-program.md:2529 (d)). The fact store is therefore **L3/L4 of the same registry**, not an ingest.
- **Layer cost model** (per 1M corpus tokens; [speculation] unless marked): L0 parse+chunk: CPU seconds, no LLM.
  L1 BM25: seconds. L2 dense: ~250 chunks × embed ≈ minutes on the embedder role (per-query p50 16 ms for EG2-256
  contended, harness-program.md:2476 [measured]). L3 deterministic facts: seconds. L4 LLM facts: ≈ 0.9-1.1M prefill
  + ~60k decode, ≈ 250 calls on worker_general (CPU quarter ≈ 2.5-3 h; MI210 27B ≈ 0.5 h) — built **lazily per
  schema field**, only over L2-admitted chunks, only once per (field, chunk hash).
- **Planner** = one typed decision per question (`run_typed_decisions_native`, `native.py:419`): a Choice over
  the four paths plus a Score for "needs exhaustive aggregation", with corpus-size and index-availability facts
  injected as state (sizes are deterministic, so the model decides only the question type; the thresholds below
  pick the path when confidence is high and the model's choice is used only inside the ambiguous band — JEV-6
  two-threshold rule, DESIGN.md:25-31). Receipt: `decision_receipt.v1` (HS-TD-4, harness-program.md:202). It
  replaces the ad-hoc token-count rule at `routing_decision.py:229` **for document requests only**; that rule
  stays as the fallback when the planner is unavailable (never "unavailable = answered").

**Switch-points (all [speculation], to be replaced by Phase-0 receipts):**

| Corpus size C (tokens) | Question type | Path | Layers on | Why (break-even) |
|---|---|---|---|---|
| C ≤ ~60k | any | `whole_doc` on worker_general (CPU) or `ingest_long_context` | L0 only | one prefill ≈ C; any index costs more than it saves at Q=1 |
| 60k < C ≤ ~200k (one 10-K) | lookup / navigation | `whole_doc` if Q=1, else `repl_nav` + L1 | L0, L1 | 27B prefill 200k ≈ 4 min at 856 t/s; BM25 build is seconds, so after the 2nd question retrieval wins |
| 200k < C ≤ ~1M | lookup / navigation | `retrieval` (L1 + L2 pointers → REPL) | L0-L2 | whole-doc exceeds 262k per-request ctx (registry `:2140`); embedding 1M tokens ≈ minutes, amortised from Q=1 |
| any C | **aggregation** over ≥ ~10 facts | `sql`: L3 first; L4 backfill only for fields L3 lacks | L0-L4 (L4 lazy) | retrieval misses facts (prior note's valid point); L3 is free; L4 ≈ 1.1M prefill per 1M tokens **once** vs whole-doc ≈ C prefill **per question**, so L4 breaks even at Q ≈ 1-2 questions per field for C ≥ 200k and is never built below ~60k |
| C ≥ ~1M, repeated use | lookup too | `sql` when the field exists, else `retrieval` | L0-L4 | a filled column answers a lookup in 1 SQL call vs 3-5 retrieval turns |

Break-even arithmetic for the aggregation row [inferred from the stage estimates]: whole-doc cost per question
≈ C × ⌈C/262k⌉-calls (B2 in §(c)); L4 cost ≈ 1.1 × C once + ~15k per question. Equal at Q ≈ 1.1 for a
single field over the whole corpus; with lazy per-field backfill the first question pays only the admitted
chunks for its fields (≈ 20-40% of C [speculation]), so L4 is cheaper than whole-doc **from the first
aggregation question** at C ≥ ~200k. Below ~60k nothing is built: the planner answers `whole_doc` and the
request is byte-identical in cost to today's path (Phase-0 arm P-small verifies this).

**Turning things off at small scale, concretely:** L2-L4 builders are gated by (C, Q-so-far, question type);
L1 is always on because its cost is below measurement noise; `context.search` stays opt-in as today but reads
L1/L2 from the store instead of rebuilding per request (one code change in `context_bundle.py:580-636`, which
is also a saving for today's flow); the typed planner call costs ~1.5 s on the worker (routing-program.md:3122
[measured, native id_only]) and is skipped entirely when C ≤ 60k and Q = 1 (deterministic rule, no LLM).

### b.3 Stage detail for L3/L4 and the `sql` path (Jev technique, model, hardware, estimates)

| Stage | Jev technique | Model / hardware | Per 1M corpus tokens [label] | Per question [label] |
|---|---|---|---|---|
| L3 deterministic facts: `DocumentPreprocessResult.tables` rows → `facts(doc_id, entity, period, field, value, unit, quote, chunk_id, page, line_start, line_end, confidence, extractor, audit_status)`; regex numeric spans | none | Python | 0 calls [speculation: 40-70% of statement cells] | 0 |
| L4a admission: per field, L2 top-K per doc; high sim admit, low reject, margin band → typed one-token gate (`n_tokens=1`, `n_probs`, yes/no grammar) | TD-23 native; URE-1 two thresholds | worker_general 35B-A3B Q8, CPU quarter | ≈ 80-100 gate calls, ≈ 0.4M prefill [speculation] | 0 |
| L4b extraction: one grammar (row schema; `quote` required; `confidence` Score), **cached schema prefix** (`cache_prompt`+`pin_slot`; order instructions+schema→chunk), deterministic `quote in chunk` reject, `n_predict` capped, `-np 2` | grammar (`llg_grammar.py:40`), Score, TD-29.M4 prefix reuse | worker_general, CPU quarter | ≈ 150 calls, ≈ 0.6M prefill, ≈ 60k decode [speculation] | 0 |
| L4c audit: confidence ≤ Medium + 5% random re-extracted; disagreement → `disputed` | CJ-13/16 cascade; JEV-6 | Qwen3.8-27B + DFlash2, MI210 :8083 | ≈ 15-25 calls, ≈ 100k prefill [speculation] | 0 |
| L4d reconcile: deterministic unit/scale; PK from metadata; residual conflicts → **one native catalogue call** | native catalogue Choice | worker_general | 1-3 calls [speculation] | 0 |
| `sql` path: planner → SQL under a **catalog-generated grammar** (schema hallucination 0 by construction) → execute → missing field ⇒ lazy L4 backfill for that field (hybrid top-K per doc, K≈30) → answer with rows+quotes; native Score self-check "answer supported?" (HS-TD-2 shape) | typed route (TD-11 owner), grammar SQL, Score | 27B MI210 for SQL+answer; 35B CPU for backfill | — | 3-4 calls, ≈ 8-20k prefill [speculation]; backfill ≈ 30-80 calls once per new field |

Compared with the Phase-0 observation (4.05M prompt tokens, 757 calls, **one** question on **one** ~0.15M-token
10-K): ≈ 1.1M prefill / ≈ 250 calls per 1M corpus tokens **once**, ≈ 15k tokens / 4 calls per question.
Hardware recommendation: CPU-35B extract / GPU-27B audit (CPU quarters are the filler bins; the audit model
should be the stronger one). Alternative if wall time matters more than quarter-hours: extract on the 27B GPU
(≈ 0.5 h per 1M tokens), audit with the 35B — weaker audit, stated as a choice.

Not adopted from SLIDERS: per-question schema induction, LLM PK selection, null-PK handling, two-pass
canonicalisation, `num_samples_per_chunk`. Adopted: the row shape (value, quote, rationale, confidence —
SL `prompts/sliders/extract_schema.prompt`), the taxonomy's field library as a schema seed
(`sliders_taxonomy.json`: `question_type`, `document_type`), the absence arbiter as a deterministic
"field has zero rows in doc" flag.

---

## (c) Phased plan

**Benchmark.** FinanceBench (150 Q, 84 docs, 35/150 multi-evidence, 50/50/50 metrics-generated /
domain-relevant / novel-generated [measured, local jsonl]) is **single-document**, mostly single-fact; it tests
ingest fidelity, not cross-corpus aggregation. Better fits: **Oolong** (aggregation/counting at 32K-1M,
intake_index.yaml:4324; regex solves its synthetic subset, so only `real` is fair [local availability
unverified — speculation]); **FinQ100** (36M tokens, not shipped, EDGAR 403, knowledge-pipelines.md:3056).
Phase 0 uses FinanceBench docs with **constructed cross-document aggregation questions whose gold is computed
from the per-question gold answers of the 50 metrics-generated questions** (same metric across companies →
how-many / which / sum / rank). **Every constructed gold is hand-verified by the operator or a named reviewer
against the filings before any run; unverified questions are excluded, never "assumed".**

**Phase 0 — cheapest falsification; three arms in one CPU quarter + one short MI210 window.**
- Corpus: 10 FinanceBench 10-Ks (FB5 pins + 5, sha256-pinned), ≈ 1-1.5M tokens [speculation].
- Questions: 20 constructed aggregation (hand-verified) + 10 original FinanceBench single-fact on those docs,
  frozen before the run; plus the **P-small arm**: 10 original FinanceBench questions each against its single
  10-K only (C ≈ 120-180k).
- Arms: **P-large** (planner → `sql`, L3+lazy L4) on the 30; **P-small** (planner on one doc) on the 10; baselines
  **B1** REPL agent + hybrid retrieval over the same chunks, 27B GPU, ≤ 30 calls; **B2** `ingest_long_context`
  whole-document read per doc then aggregate (≈ 1.5M prefill per question, so 5 questions only, labelled);
  **B-today** = the current flow unchanged (routing_decision.py:229 rule + 4a/4b) on the P-small 10.
- Metrics (predeclared): **M1 table recall** of the 30 questions' gold evidence facts after L4d (isolates
  ingest); **M2 answer accuracy** (CJ-8 three-valued local judge, string check on the 10 single-fact);
  **M3 ingest cost** = prefill tokens / corpus tokens, LLM calls / 100 chunks; **M4 per-question calls and
  prefill**; **M5 small-corpus parity** = P-small vs B-today on the same 10: accuracy equal within 1 question,
  calls and prefill tokens equal within +1 call / +2k tokens (the planner call) per question, and
  **no L2-L4 index built** (store manifest empty for those runs).
- **Kill gate (any trips → `superseded_v2_not_viable`, name the gate):** M1 < 0.70; M3 > 2.0× corpus tokens or
  > 150 calls / 100 chunks; M2 on the 20 aggregation questions not > B1 by ≥ 25 pp (n = 20, binomial SE ≈ 0.10,
  ≈ 2.5 SE; if B1 is already strong the lever is unnecessary — also an answer); median per-question calls > 8;
  **M5 fails** (the integrated planner must cost nothing on small corpora or it is a second system by stealth).
- Compute: ingest one CPU quarter (`-np 2`, `n_predict` cap, `cache_prompt`+`pin_slot`), ≈ 3-4 h [speculation];
  GPU window ≈ 1.5-2 h for audit, 30 P-large Qs, B1, B2×5, P-small and B-today [speculation]. Zero-LLM stages
  unclaimed at nice 19. **Stop-on-futility:** M1 computed before the GPU window is requested; M5's "no index
  built" check is a manifest read, done first.

**Phase 1 (GO only):** 25-30 docs (~4M tokens), Oolong-real if obtainable, incremental re-ingest of 3 changed
docs through the content-hash path, one lazy-backfill field, and the planner's mid-size `retrieval` path against
today's `context.search` arm. Gate: M1 ≥ 0.75, M4 unchanged, backfill ≤ 100 calls, mid-size parity as M5.
**Phase 2:** integration decision package — `context_bundle.py` reads L1/L2 from the store; planner replaces the
document branch of `routing_decision.py:229`; `facts_query` REPL tool; TD-11 owns the route policy.

---

## (d) Reuse versus new build

| Component | Reuse (grounded) | New |
|---|---|---|
| Parse | `PDFRouter` `pdf_router.py:115`, `ODLStructuredDocument` `odl_structured.py:126`, P-DOCPARSE-1 routing (knowledge-pipelines.md:21) | none |
| Chunk | `DocumentChunker.process` `document_chunker.py:291`, `chunk_by_odl_headings:405`, `extract_tables_from_structured:193` | persist `DocumentPreprocessResult` under content hash (store writer, small) |
| L1/L2 | `context_search.py` `BM25Index:255`, `DenseEmbedder:306`, `rrf_fuse`; KB-RAG incremental pattern (knowledge-pipelines.md:85); index identity rule (harness-program.md:2529) | persistent index registry keyed by (corpus, hash, builder, model); `context_bundle.py:580-636` reads it |
| L3 | `DocumentPreprocessResult.tables` (`document.py:393`), `TableContext` (`odl_structured.py:100`) | table→facts mapper, regex spans, DuckDB schema (DuckDB present in the SLIDERS venv, knowledge-pipelines.md:3056; orchestrator has sqlite only, `pyproject.toml:65` — dependency decision) |
| L4 / planner | `native.py:419, 1293`, `confidence.py:73`, `llg_grammar.py:40`, `llama_server.py:130-148` cache/pin, `prefill_metrics.py` receipts, HS-TD-4 receipt, CJ-13/16 pattern, SL extraction prompt row shape + taxonomy | question catalogues, thresholds from a held-out curve, `extract_rows.py` (grammar, quote check, cap), `sql_grammar.py` (catalog→GBNF), backfill |
| Whole-doc path | `routing_decision.py:229-260`, `ingest_long_context` alias | planner fallback wiring only |
| Eval | FinanceBench pins + jsonl; CJ-8 judge; `scripts/row_jobs/sliders_phase0_job.py` numeric preflight (knowledge-pipelines.md:3059) | constructed set + verification record; M1-M5 scorer |

New code ≈ 1.5-2.2k lines Python plus prompts [speculation]; nothing from SLIDERS' orchestration is vendored.

---
