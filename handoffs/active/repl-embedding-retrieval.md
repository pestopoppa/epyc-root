# REPL Embedding Retrieval — hybrid search that returns pointers

**Status:** active — Phase 0 signed, applied and proven 2026-09-26 (embedder pool 0.95× → 4.96×). Narrowed 2026-09-27: the Phase-2 kill criterion is PRE-REGISTERED (REPL-EMB-2.1 ✅); next is the offline eval (2.2); REPL-EMB-0.3 and 1.4 are frozen. 2026-10-01: `context.search` landed as an opt-in experiment arm (orch `b384cdbb`); defaults unchanged; the 2.1 kill rule governs any default.
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

- [x] **REPL-EMB-1.1 — pooled async embedding client**: one shared `httpx.AsyncClient`, round-robin over
  instances of ONE model, list-batched `/embedding`, ≤ 4 in flight per port, timeouts, LRU cache keyed by
  chunk sha256. Existing client for reference: `orchestration/repl_memory/parallel_embedder.py`
  (its Python-3.11 `asyncio.coroutine` bug was fixed separately in orch `120b55b7`, 2026-09-26).
  ✅ 2026-10-01 — on orch main: `4f534f95` (pooled client plus the busy-frontdoor neighbour cap, `src/embedding_pool/`,
  flag `repl_embedding_pool`, default OFF) and `cc808487` (capped-grant peak). Hermetic tests: `002b6fc4`, `1fe1d5f8`.
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
  Cap code landed in `4f534f95`; post-cap G1 2026-09-27 = 0.921/0.918/0.862 on `:8070`/`:8080`/`:8180` (< 0.95 target),
  `data/embedder_placement/post-cap-20260927.json` (epyc-orchestrator working tree, untracked).
- [x] **REPL-EMB-1.2 — line-aware chunker** that preserves source line ranges for every chunk.
  ✅ 2026-10-01 — minimal version landed with context.search (orch `d02942f7`..`b384cdbb`,
  `src/repl_environment/context_search.py` `chunk_sections`): a chunk is a run of whole lines of one section and keeps
  its section, char span and first line number.
- [x] **REPL-EMB-1.3 — per-request flat numpy index** (cosine, top-k) plus lexical scorer and
  `rrf_fuse` hybrid; lexical-only path labelled. Tests use a fake embedder.
  ✅ 2026-10-01 — minimal version landed with context.search (orch `d02942f7`..`b384cdbb`,
  `src/repl_environment/context_search.py`): BM25 plus a flat cosine index fused with `rrf_fuse`, one index per
  embedding model (invariant 4), fake-embedder tests (`tests/unit/test_ufh12_context_search.py`). Every fallback is
  labelled in `mode`: `lexical` = dense off; `lexical_fallback:<reason>`, e.g. `index_timeout`.

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
  - 2026-10-20 (attribution correction, factual; the rule text above is UNCHANGED): the "UFH-07's 45 behavioural questions" named in the Query set bullet above are the 45 behavioural questions from intake-1357#03 (integrallis/act-context@fd115351d0ab742993aa5d7006f1369fb15b6e74, `experiments/probe_regrade`: 15 classes x 3 questions over seaborn, pylint and pytest at pinned commits), not a UFH-07 artifact. Frozen file and gold: see the REPL-EMB-2.5 note dated 2026-10-20 (query-set update).
- [ ] **REPL-EMB-2.2 — offline eval**: corpus = real spill files, context bundles, UFH-07's 45 behavioural
  questions; arms = grep/BM25, BGE, Granite-97M-R2, hybrid RRF, ColGREP over the spill dir. Report
  recall@k, CPU-s and latency per arm; apply the rule from 2.1.
  - 2026-10-20 (intake P4-RETRIEVAL): the extension arms (EmbeddingGemma 2 @768/@256, potion-code-16M-v2, potion-base-8M) and the EPYC speed block ride THIS launch; see REPL-EMB-2.5 to 2.7 below. REPL-EMB-2.1's rule text is unchanged.
  - 2026-10-20 (attribution correction, factual; the rule text above is UNCHANGED): the "UFH-07's 45 behavioural questions" named in this entry's corpus line are the 45 behavioural questions from intake-1357#03 (integrallis/act-context@fd115351d0ab742993aa5d7006f1369fb15b6e74, `experiments/probe_regrade`: 15 classes x 3 questions over seaborn, pylint and pytest at pinned commits), not a UFH-07 artifact. Frozen file and gold: see the REPL-EMB-2.5 note dated 2026-10-20 (query-set update).
- [ ] **REPL-EMB-2.3 — online shadow**: run all arms, show one, and log which returned spans the model
  opens next (UFH-07 trajectory artifact field `spill_pointer_follows`).
- [ ] **REPL-EMB-2.4 — wire the eval's write side into the belief kernel** (row in
  `scripts/vidya/adapters/README.md`, task VB-UFH12-RETR in `vidya-belief-substrate-program.md`).
- [ ] **REPL-EMB-2.5 — candidate-arm preflight and frozen arm manifest for the 2.2 extension arms (deterministic infrastructure; no recall or speed claim).** In an ISOLATED venv outside the orchestrator lock (production `uv.lock` pins sentence-transformers 5.3.0, transformers 4.57.6 and torch 2.9.0 and is NOT touched), write a saved manifest that pins: (a) the compatibility matrix for sentence-transformers >= 6.1.0 and transformers >= 5.19.0 with the lock gap stated (the maintainer-run MTEB results used ST 6.1.0 and transformers 5.20.1); (b) exact revisions: google/embeddinggemma-2 `914f7f89142e33e77833254d9c9b90c3cef7303b`, minishlab/potion-code-16M-v2 `e9d2a44ca6a05ac6685f3b23709ea57eb7352d5b`, minishlab/potion-base-8M (resolve and pin the HF commit), the ggml-org/embeddinggemma-2-GGUF BF16 and Q8_0 commits, and the sha256 of the incumbent `bge-large-en-v1.5-f16.gguf`; (c) per-arm encoding config: EmbeddingGemma 2 query `task: search result | query: {q}` and document `title: none | text: {chunk}` (the CodeRetrieval forms for queries labelled code-intent), mean pooling, FP32 on CPU with a BF16 reference and never FP16, MRL 768 and 256 with L2 re-normalisation after truncation, the effective input cap actually used (the card says 8,192 tokens, config.json says 262,144 positions; 800-char chunks are far below both), static arms as 256-d lookup-and-mean; (d) an isolated index identity per arm (model, revision, dim, dtype or quant, prompt hash, runtime) so no vector is ever scored against another model's index; (e) the count of code-intent queries with blind code-span gold in the frozen 2.1 query set; (f) one `DenseEmbedder` adapter per arm (the adapter applies the document-side prefix, because `ContextSearchIndex` only prefixes queries) and the reference-parity gate script: finite 768-d vectors, per-item norms, per-item cosine against the ST FP32 reference, invalid and NaN counts, plus the sentence-transformers text-only versus full-model equivalence check with RSS. Gate is predeclared before any run: zero non-finite vectors and per-item cosine >= 0.99 between ST BF16 and ST FP32 on >= 200 chunks and the 45 UFH-07 questions; an arm that fails is recorded as failed, never dropped.
  - 2026-10-20 (execution note, factual; checkbox NOT ticked): **partial, gate not yet run.** Done: harness in epyc-orchestrator `scripts/benchmark/` (`repl_emb_arms.py` arm specs, index identity and one `DenseEmbedder` adapter per arm family; `repl_emb_arm_manifest.py`; `repl_emb_parity_gate.py`; `tests/unit/test_repl_emb_arms.py`, 7 passed), new files only, shipped `context_search.py`/BM25/`rrf_fuse` loaded unchanged by file path and driven end to end by a fake adapter in the test (document prefix applied by the adapter, told apart from the query call by the `admission_wait_s` the shipped index passes). Isolated venv (outside the orchestrator lock; `uv.lock` untouched, it pins sentence-transformers 5.3.0, transformers 4.57.6, torch 2.9.0): sentence-transformers 6.1.0, transformers 5.20.1, torch 2.14.1+cpu, model2vec 0.10.0 (matches the maintainer-run versions). Manifest `data/repl_retrieval_eval/arm-manifest-20261020/arm_manifest.json`, manifest_sha256 `80937c8d47babf9470bd4e9f081456d7f6d4c9f7d5cf5d54bb9129813d933517` (self-verifying): pins potion-base-8M to `bf8b056651a2c21b8d2565580b8569da283cab23` (HF API main HEAD today), ggml-org/embeddinggemma-2-GGUF to `58faf90940886df2d62be555c8765d00dac362c5` (BF16 sha256 `68bae29d...`, Q8_0 sha256 `2188ac1d...`, both equal the HF LFS oids), incumbent `bge-large-en-v1.5-f16.gguf` sha256 `3379a0e9cea28fc6d7136df8ea7a88ef99ccce5963b9a6f7af9609997be762e3` (669,603,712 bytes), file digests of the EmbeddingGemma 2 and potion snapshots, per-arm encoding config and a per-arm index identity (9 arms). Item (e): the frozen 2.1 query set does not exist yet (2.2 not launched, no `data/repl_retrieval_eval/<run-id>/`), so the code-intent-with-blind-gold count is recorded as `null` with that reason and must be recounted at the 2.2 freeze. The UFH-07 "45 behavioural questions" are not a local artifact (the 4/45 vs 27/45 figures in the handoffs are from an external source), so the gate script takes the set as a JSONL and the 45 questions cannot be run yet; a deterministic proxy item set was prepared (211 real project-text chunks through the shipped chunker: code 80, json/yaml 51, prose 80; 45 first-line proxy queries) and is labelled proxy, not UFH-07. NOT done: the ST BF16-vs-FP32 gate run and the text-only-vs-full RSS check. Reason: every CPU region (q0-q3) was held by other sessions from 16:44 to 17:10 UTC (`region-lock status`); a build-role waiter on q0 was queued 26 minutes and killed unacquired. No model was loaded; no vector was computed.
  - 2026-10-20 (query-set update, factual; supersedes the sentence above saying the 45 questions are not a local artifact): the 45 questions are the intake-1357#03 probe set, `integrallis/act-context@fd115351d0ab742993aa5d7006f1369fb15b6e74` `experiments/probe_regrade` (`regrade_nodes.json` + `results/probes.json`; 15 classes x 3 questions; seaborn `22cdfb0c...`, pylint `273a8b25...`, pytest `6e7dc8ba...`, shallow-cloned at those commits, all three resolved). Frozen as a held-out stratum: `data/repl_retrieval_eval/arm-manifest-20261020/probe45-intake1357.jsonl`, file sha256 `1cd90d56b6c9aaf3cc777c4fa3fe5276005400f22c86079adf5229a50bafc48b`, 45 rows (id, class, repo, commit, question, reference answer, gold). Gold = the class span (path, start_line..end_line) the probe was minted for, read from `regrade_nodes.json` at the pinned commit; every span was checked to lie inside its file; the minting test file is recorded per row as `alt_locus` and is not gold unless the 2.2 freeze registers it. code-intent is `null` on every row (labelled blind at the 2.2 freeze, so item (e) stays `null`). The >= 75 real spill-follow and context-bundle trace queries are a separate stratum and are not collected yet. Manifest re-issued with a `heldout_query_set` section: `manifest_sha256` `5360026d9430a8f4aa73f1ff7a5beab473b6d977d0084a4e0b50206ea68e5286` (supersedes `80937c8d...`). The gate script now accepts this file as the question set. Not run on it yet.
  - 2026-10-20 (gate run, factual; checkbox NOT ticked): the vector-parity gate ran under a `region-lock` build claim on q0+q2 (CPU only; ST lanes on cores 0-7, 8 threads), isolated venv sentence-transformers 6.1.0 / transformers 5.20.1 / torch 2.14.1+cpu (+pillow 13.0.0, torchvision 0.29.1+cpu, which the EmbeddingGemma 2 processor imports). Items: 211 real project-text chunks (code 80, json/yaml 51, prose 80) through the shipped chunker plus the 45 intake-1357#03 questions (`probe45-intake1357.jsonl`, sha256 `1cd90d56...`). Reference = ST FP32 full model. Result on that set (scope complete: >=200 chunks and the 45 questions): zero non-finite vectors in every lane; ST BF16 vs ST FP32 per-item cosine min 0.999919 (docs) / 0.999947 (queries), mean 0.999968 / 0.999966: **PASS (>= 0.99)**. Text-only load (`vision_config`/`audio_config` = None) vs full model: per-item cosine min 0.99999988, zero non-finite; RSS after load 1782.4 MB vs 3589.6 MB, peak RSS 3914.2 MB vs 5701.7 MB. `max_seq_length` reads as 1e30 (unbounded) in ST, so the cap in force is the shipped 800-char clip. An earlier run on a proxy query set (first-line of chunks, labelled proxy) gave the same lane verdicts. Per-item cosines, norms, lane configs: `data/repl_retrieval_eval/arm-manifest-20261020/parity/{probe45,proxy}/parity.json` (epyc-orchestrator). Manifest re-issued, `manifest_sha256` `1493832e4e8667b73afc162da0f66c4bfdd141887b6c6de2a444ca3fa846fb84` (supersedes `5360026d...`; adds pillow/torchvision to the venv pins and the built llama runtime string). Remaining before a tick: the a-priori items (e) code-intent count and the trace stratum are 2.2-freeze items, not gate items; main to decide whether the done criterion is met.
- [x] **REPL-EMB-2.6 — EmbeddingGemma 2 llama.cpp lane on an EXPERIMENTAL branch only (frozen v10 untouched).** The frozen `production-consolidated-v10` tree (`ffc1bac82`) registers `LLM_ARCH_GEMMA_EMBEDDING` but not `gemma-embedding2`. In a new git worktree (never switch the branch of the shared `/mnt/raid0/llm/llama.cpp` clone) cut `experimental/gemma-embedding2-on-v10-<YYYYMMDD>` from the CURRENT production tip and apply the C++ model part of upstream PR #30054 (merge `4fbc76dec51d0add466f0210855c0596589b60d4`: `src/models/gemma-embedding2.cpp`, `src/models/models.h`, `src/llama-arch.cpp`, `src/llama-arch.h`, `src/llama-model.cpp`); that merge is 1,407 commits ahead of v10, so apply its diff with `git apply --3way` (resolve conflicts by hand on the experimental branch), do not merge, and skip the converter because ggml-org already publishes BF16 and Q8_0 GGUFs. Build CPU-only in its own build dir under `region-lock run --cpu-list <cores> --role build`, and prove the binary contains the arch (binary mtime after the apply commit, `strings` shows `gemma-embedding2`, `verify_ggml_linkage.sh`). Serve BF16 and Q8_0 with a harness-owned llama-server on a non-production port (embedding mode, mean pooling, caller-supplied prefixes, recorded Euclidean normalisation, resolved input cap) and run the 2.5 parity gate against the ST FP32 reference, predeclared as: zero non-finite vectors and per-item cosine >= 0.99 for BF16 and >= 0.98 for Q8_0; report vector parity separately from retrieval quality. Record apply conflicts, build log and the pass/fail table. A failed gate is an outcome, not a blocker: the EmbeddingGemma 2 llama.cpp rows are then reported as parity-failed and the ST lane still runs. No promotion, no frozen-tree or kernel-store write. ✅ 2026-10-20
  - 2026-10-20 (execution note, factual; checkbox NOT ticked): **partial, not built, gate not run.** Worktree `/mnt/raid0/llm/worktrees/llama-gemma-embedding2-20261020`, branch `experimental/gemma-embedding2-on-v10-20261020` cut from `ffc1bac82` (the current production tip). `git apply --3way --index` of the five model files of `4fbc76dec51d0add466f0210855c0596589b60d4` (patch cut with `git format-patch -1 -- <5 files>`): `llama-arch.cpp`, `llama-arch.h`, `llama-model.cpp` applied cleanly; `models.h` applied cleanly via the direct-application fallback; no conflict markers (apply log `/mnt/raid0/llm/tmp/repl-emb-25-26-20261020/apply.log`); commit `d871e67e0`. First CPU-only build (Release, GGML_NATIVE, shared libs, UI off) failed on two v10 API gaps in the new `gemma-embedding2.cpp`: `load_swa_pattern` is not declared (the `llama_model_base` helper is newer than v10) and `build_inp_embd(tok_embd, float)` has no such overload in v10. Hand-resolved in commit `966c24d6e`: the helper body is inlined (array form first, else scalar period, default 6) and the token scale is applied as v10's `gemma4.cpp` does (`ggml_scale(inpL, ubatch.token ? sqrtf(n_embd) : 1.0f)`); this port is NOT yet compiled and NOT numerically checked. Build, `strings gemma-embedding2`, `verify_ggml_linkage.sh`, the BF16/Q8_0 server legs and the parity table are NOT done: no CPU region claim was obtainable (see 2.5 note). GGUFs downloaded to `/mnt/raid0/llm/tmp/repl-emb-25-26-20261020/gguf/` at the pinned commit (sha256 equal to the HF LFS oids). Frozen tree check after: `/mnt/raid0/llm/llama.cpp` HEAD `ffc1bac82`, 0 tracked modifications (one stray `git apply` run with the frozen tree as cwd failed on a missing patch file before writing anything); `kernels/production` untouched.
  - 2026-10-20 (build + server legs, factual; checkbox NOT ticked): build done under a `region-lock` build claim (q0+q2, `taskset` 48-71). Branch `experimental/gemma-embedding2-on-v10-20261020` HEAD `966c24d6e`; CPU-only Release, GGML_NATIVE, `LLAMA_BUILD_UI=OFF`, build dir `build-cpu` (targets llama-server only; `llama-embedding` is not a target with examples off). Proof: `llama-server --version` = `10305 (966c24d6e)`; `libllama.so` mtime 18:09:50 and `llama-server` 18:10:25 UTC, both after the port commit (17:11:05 UTC); `strings libllama.so.0` shows `gemma-embedding` and `gemma-embedding2`; `verify_ggml_linkage.sh` PASS (all ggml/llama/mtmd libs resolve inside `build-cpu/bin`). Two harness-owned servers on non-production ports (18741/18742 for the proxy run, 18743/18744 for the 45-question run; PIDs captured, each killed and confirmed dead): `--embedding --pooling mean --embd-normalize 2 -c 8192 -b 2048 -ub 2048 -np 1 --threads 16`, `/props` n_ctx 8192 and build `b10305-966c24d6e`; prefixes caller-supplied (the adapter), model input clipped to 800 chars. Parity vs ST FP32 on 211 chunks + the 45 questions: **BF16** zero non-finite, per-item cosine min 0.999990 (docs) / 0.999997 (queries), mean 0.999997 / 0.999998: **PASS (>= 0.99)**. **Q8_0** zero non-finite, min 0.999063 / 0.999847, mean 0.999838 / 0.999880: **PASS (>= 0.98)**. Server-returned norms 0.99999988-1.0 (L2 normalised). This is vector parity only, not retrieval quality. Port patch and evidence: `data/repl_retrieval_eval/arm-manifest-20261020/parity/` (`v10-port-fix.patch`, `pr30054-model.patch`, `apply.log`, `build-proof.txt`, `server-*.log`). Frozen tree after: `/mnt/raid0/llm/llama.cpp` HEAD `ffc1bac82`, 0 tracked modifications; `kernels/production/cpu/llama-server` mtime unchanged (2026-09-21). The experimental branch is local to the clone (not pushed), no promotion, no kernel-store write. The v10 port is a hand-resolved API adaptation (inlined `load_swa_pattern`, in-graph token scale), so parity is evidenced numerically by the above, not by a reading of upstream.
- [ ] **REPL-EMB-2.7 — extension arms and the EPYC speed block, inside the SAME launch as 2.2 (do not launch 2.2 without it).** After 2.4 and 2.5 are done and 2.6 is done or recorded as failed, add these arms to 2.2's frozen-at-launch manifest (2.1's k, M, X, n and CI rule are untouched; operator approval of this plan is the dated approval of the arm list only): EmbeddingGemma 2 @768 and @256 (ST FP32 lane, plus the GGUF BF16 and Q8_0 lanes if 2.6 passed), potion-code-16M-v2 and potion-base-8M, each dense-only and hybrid with the shipped BM25 via `rrf_fuse` (the published 0.75/0.25 weighted fusion is a reported, non-deciding variant for the static arms), and semble end-to-end on the code-intent subset as a reported-only diagnostic. Report per arm and per query category (UFH-07 questions, spill-follow queries, context-bundle queries): recall@{1,3,5,10}, lexical-only versus dense-only versus hybrid, paired-bootstrap CIs against L and against BGE, every failure, invalid or timeout counted as a miss. Speed block, measured under a held `region-lock` CPU claim on cores disjoint from serving roles: encode throughput (chunks/s and tokens/s; batch sweep 1/8/32/128; threads 1 and 4; a full-socket leg only if a claim is granted), p50/p95/max single-query latency (>= 200 distinct queries x 3 repeats; in-process and as-served legs), CPU-seconds per query, index-build time for 4,096 chunks, RSS and on-disk size, for the incumbent BGE-large f16 GGUF as served, BGE-large through ST FP32 (same-runtime control), Granite-97M-R2, EmbeddingGemma 2 per lane and both static arms; ABA-ordered repeats with the A/A spread carried in its unit as the noise floor. Translate each arm's measured chunks/s into `context_search.py`'s index budget (`INDEX_ASSUMED_TEXTS_PER_S` 25, clamp(5+n/25, 10, 60) s, `MAX_DENSE_CHUNKS` 4096): implied build time and expected `lexical_fallback:index_timeout` exposure. Apply the 2.1 kill and selection rules to the registered arms exactly as written (binding); recompute over registered plus extension arms and flag any changed verdict as an extension-only result for operator decision, with no default-flag change on it. Publisher and leaderboard numbers appear only in a labelled provenance box. Write the run through the VB-UFH12-RETR writer (2.4) with arm identity fields; put corpus, query, label and arm-manifest digests in `FROZEN-AT-LAUNCH.sha256`. Recall and parity legs may run in any window; only timing legs need the exclusive claim.
  - 2026-10-20 (pilot timing screen, factual; checkbox NOT ticked; NOT the 2.7 speed block and NOT a quality result): bounded CPU speed pilot under `region-lock` q1+q2 (CPUs 24-71, 48 physical cores), isolated venv (sentence-transformers 6.1.0, transformers 5.20.2, torch 2.14.1+cpu, model2vec 0.10.0), pinned revisions as in 2.5, 4,096 chunks of ~800 chars from orchestrator `src` + `handoffs/active` (corpus sha256 `b818663c310192edb545cfaf62a494946a78e160fb2f006bd61dc636d0851649`), 200 queries. Evidence: `artifacts/research/emb-speed-20261020/` (summary.md, manifest.json, results.jsonl, results_retime.jsonl, scripts). Headline, 48 threads, batch 32, 256-chunk subset, median chunks/s; query p50/p95 ms (200 x 3), pass 1 ; end re-time:

    | model | chunks/s pass 1 ; re-time | query @16 thr | query @4 thr | index build 4,096 chunks |
    |---|---|---|---|---|
    | BGE-large ST FP32 | 13.0 ; 12.0 | 65/84 ; 69/95 | 103/156 ; 130/200 | 316-400 s |
    | EmbeddingGemma 2 ST FP32 | 20.7 ; 18.5 | 49/66 ; 53/68 | 64/99 ; 79/130 | 215-225 s |
    | EmbeddingGemma 2 ST BF16 | 41.7 ; 41.8 | 32/43 ; 33/42 | 41/55 ; 53/71 | 110-114 s |
    | potion-code / potion-base (single thread, 4,096 chunks) | ~2,000-3,900 / ~2,600-2,800 ; not re-timed | not run | not run | 2.0 s / 1.4 s |

    Ranking: BF16 about 3x and FP32 about 1.5x BGE-large on documents; BF16 about 2x lower query latency. **Noise floor**: A/A (BGE vs BGE, batch 32 x 16 threads, interleaved) 4.7 % of chunks/s; repeat spreads 1-22 % in headline legs; differences under ~10 % are not distinguishable. **Contamination (label every absolute number with it)**: peers held q0 and q3 (two 35B Q8 CPU decoders) and a GPU queue ran concurrently (GPU use 0-100 %, 1-2 KFD procs), loadavg 3-124, claimed-core frequency 3.5-4.5 GHz; legs are ABA-interleaved so the ranking, not the absolute chunks/s, is the finding. BF16 vs FP32 per-item cosine on 200 chunks: mean 0.99997, min 0.99992. MRL@256 is slice + L2 renorm only and saves no encode time (storage/search only). Token counts/chunk: BGE 216, EG2 222, potion-code 198, potion-base 216. Reduced/skipped: throughput subsets (16 chunks at 1 thread, 64 at batch 1, 128 at threads-4 batch 32, else 256; the first run was stopped mid threads-4 and re-planned); **the as-served llama-server incumbent leg and potion single-query latency are NOT done and are owed to 2.7's in-launch speed block** (with Granite-97M-R2, RSS/on-disk size, CPU-seconds per query, and uncontended windows). Speed breaks ties only inside the 2.1 quality margin; no adoption claim.

> **Follow-ons if the 2.2 verdict selects a non-BGE arm (owned trigger, no checkbox; intake P4-RETRIEVAL M12, 2026-10-20).** Trigger: a dated 2.2 report in which, on the REGISTERED arms, hybrid recall@5 - L >= 0.10 with a paired-bootstrap lower bound > 0 and the 2.1 selection rule picks a non-BGE arm, or the operator accepts an extension-only verdict. Then, as separate packages: (1) a stack-change package for the pool model and launch recipe; (2) prefix entries for the selected model in `context_search.py` plus a document-side prefix seam (today `_QUERY_PREFIXES` is BGE-only and only queries are prefixed); (3) a G1 decode-interference re-measure for the selected arm (a pool-free static arm may need none) and an `INDEX_ASSUMED_TEXTS_PER_S` update from the 2.7 numbers; (4) EmbeddingGemma 2 GPU timing on the MI210 (HIP, and Vulkan) inside the frozen REPL-EMB-0.3 package; (5) before ANY embedding-dimension change in the episodic, skill or session stores (1024-d in `faiss_store.py`, `memrl.py`, `sqlite_store.py`), an explicit migration, because `sqlite_store._load_embeddings` unlinks a mismatched `session_embeddings.npy`.

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
  **2026-10-01 — LANDED AS AN OPT-IN EXPERIMENT ARM**, orch main `b384cdbb`, reviewed by workspace-8d. The box stays open.
  - Field `ChatRequest.context_search` (default false; requires `context_bundle`). The actor CLI's `--context-search`
    fails closed (exit 1) without the server's `context_pulls.search` echo.
  - Returns POINTERS only; reads go through `context.get`. Accounting is a separate `context_pulls.search` block, not
    `op="search"` pull records, so the pull fields stay exact.
  - Field off: the root block, view and echo are byte-identical to `08edc054`; a golden test pins this (`5cae6c6b`).
  - Index build budget per search: clamp(5 + n/25, 10, 60) s for n chunks not yet embedded; the build resumes batch by
    batch on the next search.
  - Consumer: DS41-C100's `orsv` arm (workspace-76); API reloads are coordinated with workspace-8d.
  - **The REPL-EMB-2.1 kill rule still governs any default:** context.search stays per-request opt-in and
    `repl_embedding_pool` stays OFF by default unless REPL-EMB-2.2 passes (hybrid recall@5 − L ≥ 0.10, n ≥ 120,
    bootstrap lower bound > 0).
  - Open until 2.2 decides and `search_sections` (4.2) is resolved.
- [ ] **REPL-EMB-4.2 — replace `DocumentREPLEnvironment.search_sections`** (`src/repl_document.py:221`)
  with the hybrid search primitive.
- [ ] **REPL-EMB-4.3 — evaluate via `rlm-contested-claims` E3b.**
- [x] **REPL-EMB-4.4 — deploy context.search for the DS41-C100 `orsv` arm**: on workspace-76's "ALL GPU CALLS DONE",
  workspace-8d does an API-only reload (`orchestrator_stack.py reload orchestrator`) onto `b384cdbb`+ and a runtime
  `POST /config {"repl_embedding_pool": true}` for the `orsv` arm. Afterwards decide whether to pin the flag in
  `orchestration/runtime_flags.spec.yaml` (now `repl_embedding_pool: baseline`) or reset it — the REPL-EMB-2.1 kill
  rule keeps it OFF by default.
  ✅ 2026-10-01 — API-only reload at 12:22Z onto `b384cdbb` (PID 1690649), then the runtime
  `POST /config {"repl_embedding_pool": true}`, read back as true.
  - Pin or reset is decided: the flag stays OFF by default per the REPL-EMB-2.1 kill rule, and nothing is pinned in
    `runtime_flags.spec.yaml`. It is enabled at runtime only for the experiment arm.
  - The ~13:10Z reload for the `context.get` fix (INF-78 OAB-35, orch `2d97ade2`, PID 1767532) reset the pool to OFF,
    its default. workspace-76 rescheduled `orv`/`orsv` for a later DS41 pause, and will ask workspace-8d to
    re-enable the pool at runtime (`POST /config {"repl_embedding_pool": true}`) before the arm runs.
  - 2026-10-03 correction: **"runtime-only" was wrong.** The pool was re-enabled 2026-10-01 for workspace-76's `orsv`
    arm, with no API reload. It came back **ON** after the host reboot (down ~2026-10-01 20:57Z to ~10-03 03:20Z) and
    the 10-03 stack restart. workspace-ec turned it OFF that morning. The record in `orchestration/runtime_flags.json`
    reads `set_by api:127.0.0.1`, `ts 2026-10-03T03:51:31Z`, `value false`; the session's own estimate was ~04:0xZ. `POST /config` writes that
    gitignored override file (`src/features.py` `runtime_flags_path()`), and every API start reads it back. So an
    experiment enable outlives API restarts and reboots. REPL-EMB-4.5 below.
- [x] **REPL-EMB-4.5 — make an experiment-arm flag enable expire.** (filed 2026-10-03, from the 10-03 post-reboot reset)
  A runtime `POST /config` flag write persists in `orchestration/runtime_flags.json` across API restarts and host
  reboots. REPL-EMB-4.4 assumed it was runtime-only, and `repl_embedding_pool` came back ON after the reboot, against
  the REPL-EMB-2.1 kill rule's OFF default.
  - Fix, in the orchestrator: an experiment enable carries an expiry (a `ttl_s` or `expires_at` on the flag record,
    honoured at load) or an explicit `restore` step that the enabling session must run. A flag past its expiry
    loads as its spec baseline and logs a WARNING.
  - Test: an expired record loads as the baseline; an unexpired one survives a simulated restart.
  - Reconcile with the 2026-10-01 13:10Z note above, which says that reload reset the pool to OFF. Establish which
    write paths persist, or whether a reload rewrites the file, before relying on either behaviour.
  - Until it lands, the enabling session restores the flag itself after the arm, and checks `/config/attest` after
    any restart.

  Completion: app main `7c70ced67c7a`; actual CI `37289613683` passes 19 runtime-flags and 48
  feature fixtures. Atomic writes persist; expiry ignores expired records without rewriting the file.
  Six-hour pool-enable default, explicit UTC expiry/TTL and load-start cache crossing are covered.
  See `progress/2026-10/2026-10-05-ni08-temporary-runtime-flag-expiry-validation.md`; no reload ran.

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
