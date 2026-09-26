# REPL Embedding Retrieval — hybrid search that returns pointers

**Status:** active — plan agreed with the operator 2026-09-26; Phase 0 package not yet prepared.
**Created:** 2026-09-26
**Owner index:** [user-facing-harness-index.md](user-facing-harness-index.md) (UFH-12).
**Depends on:** UFH-07 (tool-output-compression, TOC-SP-3 + trajectory artifact), INF-78 (OAB-8 scouts),
EVL-37 (repl-turn-efficiency S4 gate, waived for retrieval — D2 below), UFH-01 (HS-TD-3 context selection
as a typed decision — coordinate, do not fork).
**Design canvas:** https://claude.ai/artifact/UnjtMaouUFYs9xz5umnwPd

## Start here

Build embedding-backed **hybrid** retrieval (lexical + dense, fused with `rrf_fuse` in
`epyc-orchestrator` `src/trace/navigation.py:178`) inside the orchestrator REPL. Four invariants hold in
every phase:

1. **Search returns POINTERS, never summaries** — `(source, line range, score, one-line snippet)`.
2. **Reads still go through `get`/`peek`**, so OAB-12 pull accounting and the print caps keep holding.
3. **No hash-vector fallback.** If no embedder is available, degrade to lexical and **label** the result
   as lexical — never silently substitute a pseudo-embedding.
4. **An index belongs to ONE embedding model.** The scheduler chooses among *instances* of that model,
   never across models.

The first dispatchable task is **REPL-EMB-0.1** (prepare the Phase-0 stack-change package).

## Operator decisions (2026-09-26)

- **D1 — placement: AGREED.** Embedder instances sit next to each serving model (dedicated CPU cores; a
  small embedder on each MI210). Selection rule: *idle instance anywhere → else the instance sharing the
  requesting model's hardware → else lexical now, index later.* Leading candidate model:
  **Granite-97M-R2** (8K context, ~107 texts/s single server, best Phase-B recall); its costs are
  measured in the Phase-2 eval, not assumed.
- **D2 — REPL tool gate: WAIVED for retrieval, conditionally.** `repl-turn-efficiency.md:14` ("Do not add
  new REPL tools before S4") does not block this handoff, **provided Phase 2 passes its pre-registered
  kill criterion**. If Phase 2 fails the criterion, the waiver lapses and Phases 3-5 stop.

## Scheduling and ownership

Embedding work is owned by the **orchestration API**: request lifecycle, R2 (nothing outlives `/chat`),
cancellation, a sha256-keyed chunk cache, and priorities. Reuse the existing `scout_stage.py`
admission (`src/api/routes/chat_pipeline/scout_stage.py`, live `/slots`) and its cancel machinery rather
than building a second scheduler.

## Tasks

### Phase 0 — fix embedder placement (stack change; needs operator signature)

Verified 2026-09-26 in `/proc`: all six BGE embedders `:8090`-`:8095` pin their 4 OMP compute threads to
the **same** cores 0/96, 32/128, 48/144, 88/184 — inside frontdoor's 0-95 — so the pool delivers one
server's compute. Per-slot context is 256 tokens (`-c 512 -np 4`), a known defect (`wiki/kv-cache.md:93`).

- [ ] **REPL-EMB-0.1 — prepare the placement package via the `stack-change` skill**: disjoint cores per
  embedder instance (off frontdoor's 0-95), per-slot ctx ≥ the chunk size, and the Granite-97M-R2
  instance plan from D1. Output one package for the operator's signature; do not apply it unsigned.
- [ ] **REPL-EMB-0.2 — after signature: apply, bring up, and prove** distinct affinity per instance from
  `/proc/<pid>/task/*/status` and a parallel-throughput probe showing the pool scales past one server.

### Phase 1 — pooled async client, chunker, per-request index (no inference needed for tests)

- [ ] **REPL-EMB-1.1 — pooled async embedding client**: one shared `httpx.AsyncClient`, round-robin over
  instances of ONE model, list-batched `/embedding`, ≤ 4 in flight per port, timeouts, LRU cache keyed by
  chunk sha256. Existing client for reference: `orchestration/repl_memory/parallel_embedder.py`
  (its Python-3.11 `asyncio.coroutine` bug is being fixed separately, 2026-09-26).
- [ ] **REPL-EMB-1.2 — line-aware chunker** that preserves source line ranges for every chunk.
- [ ] **REPL-EMB-1.3 — per-request flat numpy index** (cosine, top-k) plus lexical scorer and
  `rrf_fuse` hybrid; lexical-only path labelled. Tests use a fake embedder.

### Phase 2 — offline retrieval eval, then online shadow (decides the method from data)

- [ ] **REPL-EMB-2.1 — pre-register the decision rule and kill criterion BEFORE running**: "cheapest arm
  within X of the best recall@k; cost = CPU-seconds + latency", and a kill criterion against lexical
  (if no dense/hybrid arm beats grep/BM25 by the pre-registered margin, stop at lexical).
- [ ] **REPL-EMB-2.2 — offline eval**: corpus = real spill files, context bundles, UFH-07's 45 behavioural
  questions; arms = grep/BM25, BGE, Granite-97M-R2, hybrid RRF, ColGREP over the spill dir. Report
  recall@k, CPU-s and latency per arm; apply the rule from 2.1.
- [ ] **REPL-EMB-2.3 — online shadow**: run all arms, show one, and log which returned spans the model
  opens next (UFH-07 trajectory artifact field `spill_pointer_follows`).
- [ ] **REPL-EMB-2.4 — wire the eval's write side into the belief kernel** (row in
  `scripts/vidya/adapters/README.md`, task VB-UFH12-RETR in `vidya-belief-substrate-program.md`).

### Phase 3 — replace the synchronous spill summary

- [ ] **REPL-EMB-3.1 — replace `_spill_output`'s summary** (`src/repl_environment/environment.py`
  `_spill_output` ~:716-800: a 512-token worker call on the CPU frontdoor, ~12 s at ~42 tok/s est.) with
  pointer + verbatim head/tail + top-k task-relevant chunks + `search()`. Merge with UFH-07 TOC-SP-3
  rather than landing a parallel mechanism.
- [ ] **REPL-EMB-3.2 — A/B** the replacement vs the current summary on latency, accuracy and re-fetches.

### Phase 4 — `context.search()` on bundles and the document REPL

- [ ] **REPL-EMB-4.1 — `context.search()`**: `repl_view` closure + namespace key, `op="search"` pull
  accounting, lazy index on first call (the bundle is built twice per request), `describe` /
  `render_root_block` entries, and extend the `test_oab7_context_bundle.py` `dir(view)` test.
- [ ] **REPL-EMB-4.2 — replace `DocumentREPLEnvironment.search_sections`** (`src/repl_document.py:221`)
  with the hybrid search primitive.
- [ ] **REPL-EMB-4.3 — evaluate via `rlm-contested-claims` E3b.**

### Phase 5 — SEARCH for OAB-8 scouts

- [ ] **REPL-EMB-5.1 — deliver a SEARCH command primitive** for OAB-8 scouts. INF-78 is owned by another
  session: deliver the primitive and its tests; that session wires it.

## Context — orchestrator-vs-baseline evaluation (operator direction 2026-09-26)

No active handoff owns an "orchestrator vs single-model baseline" comparison; recorded here until one
does. The **first standing baseline** is the benchmark *quality* of the strongest model on the stack;
speed comparison is deferred. The later **speed baseline** is a large MoE hybrid across CPU+RAM and both
MI210s (Qwen3.8-Flash-Next or DeepSeek v4.1), compared on concurrency × tasks/hr × aggregate tok/s.

- [ ] **REPL-EMB-B.1 — define the quality baseline run**: strongest stack model alone, same suites the
  orchestrator is scored on, as the standing comparison row for orchestrator evaluations.

## Key files (epyc-orchestrator)

| Surface | Path |
|---|---|
| RRF fusion | `src/trace/navigation.py:178` `rrf_fuse` |
| Scout admission / cancel | `src/api/routes/chat_pipeline/scout_stage.py` |
| Spill summary (to replace) | `src/repl_environment/environment.py` `_spill_output` (~:716) |
| Document REPL search | `src/repl_document.py:221` `_search_sections` |
| Existing embedder client | `orchestration/repl_memory/parallel_embedder.py` |
