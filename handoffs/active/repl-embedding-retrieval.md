# REPL Embedding Retrieval — hybrid search that returns pointers

**Status:** active — Phase 0 signed, applied and proven 2026-09-26 (embedder pool 0.95× → 4.96×); operator kept it with a G1 shortfall on `:8180` and asked for a Phase-1 in-flight cap (REPL-EMB-1.4).
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

Phase 0 is done (below). The next dispatchable work is **REPL-EMB-1.1 + REPL-EMB-1.4**: the pooled client
with the operator-requested in-flight cap, then the G1 re-measure (target ≥ 0.95).

## Operator decisions (2026-09-26)

- **D1 — placement: AGREED.** Embedder instances sit next to each serving model (dedicated CPU cores; a
  small embedder on each MI210). Selection rule: *idle instance anywhere → else the instance sharing the
  requesting model's hardware → else lexical now, index later.* Leading candidate model:
  **Granite-97M-R2** (8K context, ~107 texts/s single server, best Phase-B recall); its costs are
  measured in the Phase-2 eval, not assumed.
- **D2 — REPL tool gate: WAIVED for retrieval, conditionally.** `repl-turn-efficiency.md:14` ("Do not add
  new REPL tools before S4") does not block this handoff, **provided Phase 2 passes its pre-registered
  kill criterion**. If Phase 2 fails the criterion, the waiver lapses and Phases 3-5 stop.
- **D3 — Phase-0 G1 shortfall: KEEP + cap.** The applied placement is kept although `:8180` landed in the
  pre-registered rollback band (0.86 < 0.90; rollback would restore 0.53). Phase 1 adds the in-flight cap
  (REPL-EMB-1.4) and re-measures G1 against ≥ 0.95.

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

- [x] **REPL-EMB-0.1 — prepare the placement package via the `stack-change` skill**: disjoint cores per
  embedder instance (off frontdoor's 0-95), per-slot ctx ≥ the chunk size, and the Granite-97M-R2
  instance plan from D1. Output one package for the operator's signature; do not apply it unsigned.
  ✅ 2026-09-26 — package [`artifacts/operator/stack-change-ufh12-phase0-20260926/PACKAGE.md`](../../artifacts/operator/stack-change-ufh12-phase0-20260926/PACKAGE.md)
  (root `b9c6ce5a`); signed 2026-09-26T17:46Z, receipt
  `artifacts/operator/receipts/RATIFY-UFH12-PHASE0-EMBEDDER-PLACEMENT-20260926.json` (pins match the landed files).
- [x] **REPL-EMB-0.2 — after signature: apply, bring up, and prove** distinct affinity per instance from
  `/proc/<pid>/task/*/status` and a parallel-throughput probe showing the pool scales past one server.
  ✅ 2026-09-26 — applied ~18:11-18:35Z: orchestrator `5af57377` (merge) + `a439070e` (derived regen),
  research `7640269b`. Evidence: `epyc-orchestrator/data/embedder_placement/{pre,post,g3-post,g3b-post}-20260926.json`.

  | Gate (PACKAGE §4) | pre → post | Signed band | Result |
  |---|---|---|---|
  | G2 pool scaling (whole pool ÷ one port, texts/s) | 0.95× → **4.96×** (45.6 texts/s) | PASS ≥ 4.0 | PASS |
  | G0 idle frontdoor decode (`:8070` Q median, tok/s) | 52.6 → 53.1 | within A/A floor | PASS |
  | G1 saturated ÷ idle decode `:8070` | 0.34 → 0.91 (17.6 → 48.4 tok/s) | PASS ≥ 0.95; 0.90-0.95 needs-operator | needs-operator |
  | G1 `:8080` | 0.50 → 0.91 | same | needs-operator |
  | G1 `:8180` | 0.53 → 0.86 | < 0.90 = ROLLBACK | **rollback band — overridden by the operator** |
  | G3 CPU speech, pool saturated | STT RTF ≤ 0.24, TTS first packet ≤ 0.12 s | RTF ≤ 0.40, ≤ 500 ms | PASS (re-run) |

  G3's first run (`g3-post-20260926.json`) recorded verdict ROLLBACK from one cold first request (saturated
  STT RTF 0.956; quiet TTS first packet 6.1 s); the re-run `g3b-post-20260926.json` discards a warm-up
  request and passes on 5/5. The warm-up discard was not in the pre-registered method — treat G3 as a pass
  under a post-hoc amendment, and pre-register the warm-up for every later G3 run.
  Serving proofs P1-P8 (PACKAGE §10) pass: affinity tool rc=0, node-local memory 97.8-98.9%, P6 cosine 1.0,
  P7 402-token input accepted (above the old 256-token per-slot context), 6/6 embedders
  healthy, episodic index 0 stale.

  **Operator decision on G1 (2026-09-26): KEEP**, overriding the pre-registered rollback band for `:8180`
  (rolling back restores 0.53, which is worse than the 0.86 kept), and add the Phase-1 scheduler cap
  (REPL-EMB-1.4). This is one of the three needs-operator options the package pre-registered
  (keep / 4-instance pool / Phase-1 scheduler cap), taken as keep + cap.

### Phase 1 — pooled async client, chunker, per-request index (no inference needed for tests)

- [ ] **REPL-EMB-1.1 — pooled async embedding client**: one shared `httpx.AsyncClient`, round-robin over
  instances of ONE model, list-batched `/embedding`, ≤ 4 in flight per port, timeouts, LRU cache keyed by
  chunk sha256. Existing client for reference: `orchestration/repl_memory/parallel_embedder.py`
  (its Python-3.11 `asyncio.coroutine` bug is being fixed separately, 2026-09-26).
- [ ] **REPL-EMB-1.4 — cap in-flight embeddings next to a busy frontdoor half, then re-measure G1**
  (operator decision 2026-09-26, from the Phase-0 G1 result). In the REPL-EMB-1.1 scheduler, cap in-flight
  embedding requests on instances whose NUMA node is shared with a frontdoor half that is currently decoding,
  applying the agreed D1 rule: *idle instance anywhere → else the requesting model's own hardware → else
  lexical now, index later.* The node fact comes from `stack_manifest.EMBEDDING_PLACEMENT[port].numa_node`
  (landed in Phase 0). Re-run `scripts/server/embedder_placement_gate.py` G1 with the cap on
  (`--label post-cap`); target S/Q ≥ 0.95 on `:8070`, `:8080` and `:8180`, and report G2 again so the cap's
  throughput cost is visible. Pre-register the G3 warm-up discard if G3 is re-run. Before this run, wire the
  gate driver's write side for the belief kernel (VB-UFH12-PLACEMENT in `vidya-belief-substrate-program.md`).
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
does. The **first standing baseline** is the benchmark *quality* of the strongest model on the stack — the operator named **Qwen3.8-Flash-Next**, the public-benchmark leader of the stack (2026-09-26);
speed comparison is deferred. The later **speed baseline** is a large MoE hybrid across CPU+RAM and both
MI210s (Qwen3.8-Flash-Next or DeepSeek v4.1), compared on concurrency × tasks/hr × aggregate tok/s.

- [ ] **REPL-EMB-B.1 — define the quality baseline run**: Qwen3.8-Flash-Next (strongest stack model) alone, same suites the
  orchestrator is scored on, as the standing comparison row for orchestrator evaluations.
- [ ] **REPL-EMB-B.2 — speed baseline (after B.1; the operator deferred speed comparison)**: large MoE hybrid
  across CPU+RAM and both MI210s (Qwen3.8-Flash-Next or DeepSeek v4.1), measured on concurrency × tasks/hr ×
  aggregate tok/s. Related scoped baselines: `reviewer-latency-and-sampling-budget.md` LB-7 (review plane),
  INF-78 OAB-4 (27B plain seat vs orchestrator REPL).

## Key files (epyc-orchestrator)

| Surface | Path |
|---|---|
| RRF fusion | `src/trace/navigation.py:178` `rrf_fuse` |
| Scout admission / cancel | `src/api/routes/chat_pipeline/scout_stage.py` |
| Spill summary (to replace) | `src/repl_environment/environment.py` `_spill_output` (~:716) |
| Document REPL search | `src/repl_document.py:221` `_search_sections` |
| Existing embedder client | `orchestration/repl_memory/parallel_embedder.py` |
