# REPL Embedding Retrieval — hybrid search that returns pointers

**Status:** active — Phase 0 signed, applied and proven 2026-09-26 (embedder pool 0.95× → 4.96×). Narrowed 2026-09-27: the Phase-2 kill criterion is PRE-REGISTERED (REPL-EMB-2.1 ✅); next is the offline eval (2.2); REPL-EMB-0.3 and 1.4 are frozen.
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

Phase 0 is done (below). **Narrowed plan (operator, 2026-09-27):** the next work is **REPL-EMB-2.1 → 2.2**, the
kill criterion and then the offline recall eval. The saturation-guard policy (REPL-EMB-1.4, B+D) and the GPU embedder
(REPL-EMB-0.3) are frozen until that eval passes. The orchestrator-vs-baseline comparison moved to its own handoff,
UFH-13 [`thesis-experiment-orchestrator-vs-strongest-model.md`](thesis-experiment-orchestrator-vs-strongest-model.md).

### Narrowed plan (operator, 2026-09-27)

Adopted after a Fable audit of session workspace-8d: evaluate before building, and pre-register the kill criterion
before any more embedder work.
- **Frozen** (marked in place, boxes stay open): REPL-EMB-0.3, the GPU embedder instance; and REPL-EMB-1.4, the
  saturation-guard **B+D** policy. The landed neighbour cap (`neighbour_cap.max_in_flight: 1`) stays as it is, behind
  the default-off `repl_embedding_pool` flag. The policy arms prepared for it (runbook
  `/mnt/raid0/llm/tmp/next-window-runbook-20260927.md`, chunks A0/A3) choose that policy. A0 and A3 (sched-sat,
  low-duty) had already run 10:15-11:31Z, before the freeze; A3-raw did not run. Readings: A0 (neighbour cap 0) is
  *partial* on `:8080` and `:8180` (the rest is cross-node); A3 (embedder `OMP_WAIT_POLICY=passive KMP_BLOCKTIME=0`)
  is NULL on all 3 ports, so keep the declared env. Detail: `progress/2026-09/2026-09-27-orch-design.md`. Nothing
  further runs for 1.4 while it is frozen.
- **Cancelled:** the UFH-12 **A1 duty sweep**. It was not a checkbox here, so nothing is left open for it.
- **Operator's eventual target**, once REPL-EMB-2.2 passes the REPL-EMB-2.1 rule: B+D, **plus** GPU embedder
  redundancy (REPL-EMB-0.3).
- **Next:** REPL-EMB-2.2, zero-stack-change and offline, with VB-UFH12-RETR wired first. REPL-EMB-2.1's rule is
  PRE-REGISTERED (operator-approved 2026-09-27, OP-66 closed).

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

- [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-12 Phase-2 retrieval eval shows dense retrieval pays — **REPL-EMB-0.3 — prepare the GPU embedder instance package (the other half of D1)** via the `stack-change`
  skill. The package adds a small embedder on the MI210 as its own instance, of the same embedding model as the index
  it serves (invariant 4). VRAM is the binding constraint: the MI210 had **1.52 GiB free** on 2026-09-26 (session
  sample, not a protocol measurement). The package must re-sample free VRAM during serving, size the model + KV +
  compute buffers against it, and show the residents' decode unchanged. It is a separate package from Phase 0,
  which was CPU-only, and needs the operator's signature before any apply. The second MI210 (~Oct 2026) changes the
  headroom, so state which card it targets. Filed 2026-09-26.
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): GPU embedder redundancy adds capacity to a feature whose retrieval value is unmeasured; unfreeze trigger: REPL-EMB-2.2 passes the REPL-EMB-2.1 kill rule. The operator's eventual target is then the B+D saturation-guard policy plus GPU embedder redundancy (this box). The box stays open: frozen is not done.

### Phase 1 — pooled async client, chunker, per-request index (no inference needed for tests)

- [ ] **REPL-EMB-1.1 — pooled async embedding client**: one shared `httpx.AsyncClient`, round-robin over
  instances of ONE model, list-batched `/embedding`, ≤ 4 in flight per port, timeouts, LRU cache keyed by
  chunk sha256. Existing client for reference: `orchestration/repl_memory/parallel_embedder.py`
  (its Python-3.11 `asyncio.coroutine` bug was fixed separately in orch `120b55b7`, 2026-09-26).
- [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-12 Phase-2 retrieval eval shows dense retrieval pays — **REPL-EMB-1.4 — cap in-flight embeddings next to a busy frontdoor half, then re-measure G1**
  (operator decision 2026-09-26, from the Phase-0 G1 result). In the REPL-EMB-1.1 scheduler, cap in-flight
  embedding requests on instances whose NUMA node is shared with a frontdoor half that is currently decoding,
  applying the agreed D1 rule: *idle instance anywhere → else the requesting model's own hardware → else
  lexical now, index later.* The node fact comes from `stack_manifest.EMBEDDING_PLACEMENT[port].numa_node`
  (landed in Phase 0). Re-run `scripts/server/embedder_placement_gate.py` G1 with the cap on
  (`--label post-cap`); target S/Q ≥ 0.95 on `:8070`, `:8080` and `:8180`, and report G2 again so the cap's
  throughput cost is visible. Pre-register the G3 warm-up discard if G3 is re-run. Before this run, wire the
  gate driver's write side for the belief kernel (VB-UFH12-PLACEMENT in `vidya-belief-substrate-program.md`).
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): the saturation-guard policy (B+D) is frozen; the landed neighbour cap (`neighbour_cap.max_in_flight: 1`, pool flag default OFF) stays as it is, and no further policy arms or G1 re-measure run; unfreeze trigger: REPL-EMB-2.2 passes the REPL-EMB-2.1 kill rule; then B+D, plus GPU embedder redundancy (REPL-EMB-0.3), is the operator's target. The box stays open: frozen is not done.
- [ ] **REPL-EMB-1.2 — line-aware chunker** that preserves source line ranges for every chunk.
- [ ] **REPL-EMB-1.3 — per-request flat numpy index** (cosine, top-k) plus lexical scorer and
  `rrf_fuse` hybrid; lexical-only path labelled. Tests use a fake embedder.

### Phase 2 — offline retrieval eval, then online shadow (decides the method from data)

- [x] **REPL-EMB-2.1 — pre-register the decision rule and kill criterion BEFORE running**: "cheapest arm
  within X of the best recall@k; cost = CPU-seconds + latency", and a kill criterion against lexical
  (if no dense/hybrid arm beats grep/BM25 by the pre-registered margin, stop at lexical).
  ✅ 2026-09-27 — **PRE-REGISTERED (frozen)**: recall@5, M = 0.10, n ≥ 120, paired-bootstrap lower bound > 0,
  cheapest-within-X = 0.05, exactly as drafted below. Operator-approved in chat on 2026-09-27, session
  https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ (master queue OP-66, closed). Changing k, M, X, n or the CI
  condition later needs a **new registration** (a dated, operator-approved amendment recorded here), and any verdict
  under an amended rule is flagged as such. Nothing has run.
  **Rule (as registered 2026-09-27):**
  - *Metric.* recall@k is the fraction of queries with at least one returned pointer that overlaps a gold span (same
    source, at least one line of overlap). **Primary k = 5.** k ∈ {1, 3, 10} are reported and not decided on.
  - *Query set, frozen before any arm runs:*
    - UFH-07's 45 behavioural questions, plus at least 75 queries from real spill-follow and context-bundle traces,
      for **n ≥ 120**.
    - Gold spans are labelled blind to every arm's output.
    - The corpus, query and label digests go into `FROZEN-AT-LAUNCH.sha256`.
  - *Arms:* grep, BM25 (the lexical baseline L is the better of the two), BGE, Granite-97M-R2, hybrid RRF (`rrf_fuse`
    over lexical plus one dense arm) and ColGREP. Each index uses one embedding model (invariant 4).
  - *Cost:* CPU-seconds per query, with the index build reported separately, and p50/p95 query latency.
  - **Kill rule (applied first).** UFH-12 continues past Phase 2 only if hybrid recall@5 − L ≥ **M = 0.10** AND the
    paired (by-query) bootstrap 95% lower bound of that difference is > 0. Otherwise UFH-12 **stops at lexical**:
    - the D2 waiver lapses;
    - Phases 3-5 stop;
    - the embedder fleet goes to the operator as a keep-for-episodic-memory-or-reclaim question.
  - **Selection rule (only if the kill rule passes):** take the cheapest arm, by CPU-s per query with latency as the
    tie-break, whose recall@5 ≥ best − **X = 0.05**.
  - **Why these numbers.**
    - *k = 5.* Search returns pointers that are read through `get`/`peek` under the print caps. Following more than
      about five pointers costs more in re-fetches than the search saves, so recall beyond 5 is not the working regime.
    - *M = 0.10.* With n ≈ 120 and roughly 30% discordant queries, the paired SE of the difference is ≈ 0.05, so 0.10
      is about 2 SE, the smallest effect this n separates from zero. It is also the size of gain that could pay for
      the embedder fleet's standing cost: the Phase-0 G1 still shows 9-14% frontdoor decode lost with the pool
      saturated (S/Q 0.86-0.91).
    - *X = 0.05 = M/2.* An arm within half the material margin counts as equivalent, so the cheaper one wins. The
      pair reads: "equivalent below X, materially better above M".
    - *Small n kills by design.* At n = 45 the paired SE is ≈ 0.08, so the CI condition will usually fail. The burden
      of proof sits on the new component, not on grep.
    - *Alternatives for the operator.* M = 0.05 with n ≥ 400 (finer, but needs a much larger labelled set), or k = 3
      (stricter on ranking).
  - Report n, per-arm recall@{1,3,5,10}, CPU-s and latency, with every post-hoc amendment flagged.
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

The "orchestrator vs single-model baseline" comparison is owned by UFH-13
([`thesis-experiment-orchestrator-vs-strongest-model.md`](thesis-experiment-orchestrator-vs-strongest-model.md)) since
2026-09-27; this section keeps the history and B.2. The **first standing baseline** is the benchmark *quality* of the strongest model on the stack — the operator named **Qwen3.8-Flash-Next**, the public-benchmark leader of the stack (2026-09-26);
speed comparison is deferred. The later **speed baseline** is a large MoE hybrid across CPU+RAM and both
MI210s (Qwen3.8-Flash-Next or DeepSeek v4.1), compared on concurrency × tasks/hr × aggregate tok/s.

- [x] **REPL-EMB-B.1 — define the quality baseline run**: Qwen3.8-Flash-Next (strongest stack model) alone, same suites the
  orchestrator is scored on, as the standing comparison row for orchestrator evaluations.
  ✅ 2026-09-27 — promoted to its own handoff, UFH-13
  [`thesis-experiment-orchestrator-vs-strongest-model.md`](thesis-experiment-orchestrator-vs-strongest-model.md). The run
  is defined there as arm A0: the pinned MMLU-Pro 200 + GPQA 195 manifest (sha256 `1532906b…adb1`), cap 16384, through
  /v1 (--transport v1, TE-3a). Its decision rule was pre-registered 2026-09-27 (OP-66 closed).
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
