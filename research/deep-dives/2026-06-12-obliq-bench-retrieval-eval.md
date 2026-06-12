# OBLIQ-Bench — Deep-Dive: Oblique-Query Retrieval Eval (intake-689)

**Date**: 2026-06-12
**Intake**: intake-689 — "OBLIQ-Bench: Exposing Overlooked Bottlenecks in Modern Retrievers with Latent and Implicit Queries" (arXiv:2605.06235, Tchuindjo / Shah / Khattab, MIT)
**Refined verdict**: `worth_investigating` → **methodology-reuse, NOT dataset-reuse**. Use the gap-metric + oblique-query construction recipe to build our OWN code/KB oblique eval slice; do NOT fold OBLIQ's social/political corpora into the Phase-B reranker eval corpus. The LateOn numbers in the paper are usable as one *directional* data point but do not change the LateOn-vs-GTE adoption decision (that gate stays first-stage recall + EPYC latency).
**Supersedes**: the 2026-06-10 intake-689 note in `colbert-reranker-web-research.md` ("fold an oblique-query slice into the Phase-B reranker eval corpus") — refined below.

## TL;DR / Refined recommendation

- **Dataset IS released** (HF `dianetc/OBLIQ-Bench`, **CC-BY-4.0**, 2.92 GB, 808,636 rows, 5 subsets, 1,238 queries total) — license is clean to *use*, but the **content** (geopolitical tweets, WildChat chat logs, congressional hearings, researcher writing-style snippets) is **out-of-domain** for our two retrieval workloads (web_research ColBERT reranking + internal code/KB-RAG). Folding it into the Phase-B corpus would *test the wrong distribution*.
- **The transferable asset is the METHODOLOGY**, not the data: (1) the `gap(t)=V_t−R_t` retrieval-verification gap metric, and (2) the 5-stage oblique-query construction pipeline. Both re-apply cleanly to build an *EPYC-internal* oblique code/KB eval (e.g. "find the handoff that describes the bug where X" without sharing surface vocabulary).
- **LateOn IS evaluated** with numbers (Twitter 0.010 / WildChat 0.003 / Math 0.128 / Writing 0.149 / Congress 0.083 NDCG@10) — but these are **near-floor on out-of-domain oblique social/legal text** and tell us nothing about LateOn's strength on *code/BEIR-style* retrieval, which is the axis our adoption decision turns on. **Do not cite OBLIQ LateOn numbers as evidence against LateOn adoption.** The relevant LateOn evidence remains its BEIR 57.22 / decontaminated 60.36 (intake-428).
- **The paper's core claim DIRECTLY supports our existing architecture**: the bottleneck is first-stage *recall* (surfacing), not *verification* — "reasoning LLMs reliably recognize latent relevance whenever relevant documents are surfaced, but even sophisticated retrieval pipelines fail to surface most relevant documents." This is an argument to **keep/strengthen the LLM-rerank stage** we already run, and to invest in first-stage recall (dense retriever choice, candidate-pool width), not to drop reranking.
- **The verification ceiling is NOT reproducible on our stack**: the oracle is a **closed GPT-5.2 listwise tournament** over ~300-candidate pools. We have no GPT-5.2. We can *approximate* the verification arm with an open reasoning model (e.g. our architect/Qwen3.x route as a listwise judge), but absolute gap magnitudes (e.g. Congress 0.913 vs 0.079) are **not** reproducible — only the *relative* "verification ≫ retrieval" direction transfers.
- **Iterative query rewriting is NOT a fix** and can hurt: on Writing-Style the multi-hop agent "hurts considerably" and rewriting "can actively damage retrieval." Relevant negative-result for any future plan to bolt query-rewriting onto web_research/KB-RAG before measuring.

## What it is

OBLIQ-Bench is a retrieval benchmark built specifically around **oblique queries** — queries whose relevant documents do *not* share surface vocabulary with the query, so lexical and even dense single-stage retrievers under-surface them while BEIR/BRIGHT-style aggregate scores look saturated and hide the gap.

### The three obliqueness mechanisms (5 tasks)

| Mechanism | Task | Corpus | #docs | #queries | Paper definition |
|---|---|---|---|---:|---|
| **Descriptive** | Twitter-Conflict | X/Twitter full-archive tweets, geopolitical conflict from Feb 2026 | 72,122 | 281 | "seek documents that express a latent property implicitly, such as an implicit stance or behavioral failure mode" |
| **Descriptive** | WildChat Errors | WildChat-4.8M convos, filtered to 2025 | 507,729 | 40 | (as above — latent failure-mode property) |
| **Analogue** | Math Meta-Program | Putnam / Amer. Math. Monthly / qual exams | 3,508 | 151 | "seek all documents that share an archetype with the content of the query, despite differing in surface topic" |
| **Analogue** | Writing-Style | snippets from 64 researchers across unrelated subjects | 10,389 | 512 | (as above — shared archetype = authorship/style) |
| **Tip-of-the-Tongue** | Congress Hearings | GovInfo congressional transcripts (110th–119th) + 10 tech hearings | 213,650 | 254 | "seek an obscure passage from a partial, lossy, and abstract recollection" |

### Gap metric

For a query `t`:
- `V_t = max_{m∈ℳ} Q(m,t)` — best achievable quality over a powerful (prohibitively expensive) verifier class ℳ (here: GPT-5.2 listwise tournament).
- `R_t = max_{r∈ℛ} Q(r,t)` — quality of the best *efficient* single-stage retriever class ℛ (BM25 / dense / late-interaction).
- `gap(t) = V_t − R_t` — the headroom a verification/rerank stage can recover that first-stage retrieval leaves on the table.

Reported gaps (gold-only NDCG@10) are large: Twitter ~0.331 oracle vs 0.068 best retriever (gap ≈ 0.263); **Congress 0.913 oracle vs 0.079 retriever (gap ≈ 0.878)**. (Pooled NDCG@10 collapses these because the pool is *defined* by the retrievers' own top-k — the gold-only view is the honest one.)

### Construction pipeline (the reusable recipe)

1. **Human defines a latent attribute lens** (e.g. implicit stance; failure-mode; authorship; archetype).
2. **LLM annotates the whole corpus** with extracted attribute values `f(d)`.
3. **Cluster** attribute values into groups of docs with near-equivalent properties.
4. **LLM generates an abstract query per cluster**, deliberately avoiding source vocabulary (this is what makes it "oblique").
5. **Pool top-k from all retrievers + inject gold**, then LLM judges unjudged candidates as potential gold (TREC-style pooling).
   - Writing-Style skips stages 2–3 (authorship is ground truth); Congress skips stage 3 (one passage per query).

### Oracle / verification ceiling

A **listwise tournament rerank** over a candidate pool = union of ~300 top-k results across all retrievers + injected gold, judged by **GPT-5.2** (closed). The paper's thesis rests on this oracle: verification is near-solved *given surfacing*; retrieval is the bottleneck.

### Retrievers evaluated (full list)

BM25 · Qwen3-Embedding-0.6B · Qwen3-Embedding-4B · **LateOn 0.1B (LightOn, 149M)** · Gemini-Embedding-2 · GPT-5.2 Query Rewriter · GPT-5.2 Multi-Hop Agent · Oracle GPT-5.2 Tournament.

## Fit to EPYC

### Dataset-reuse vs methodology-reuse

**Dataset-reuse: NO (domain mismatch).** Our two retrieval surfaces are:
- (a) **web_research ColBERT reranking** — reranks ~10 *web search snippets* (`colbert-reranker-web-research.md`).
- (b) **internal KB-RAG** — MaxSim over ~13.5k markdown chunks of handoffs/wiki/research/progress (`internal-kb-rag.md`, GTE-ModernColBERT-v1, live build 409 files / 13,537 chunks).

Both are **code/doc/technical-English** retrieval. OBLIQ's corpora (geopolitical tweets, chat logs, congressional speech, researcher prose) share neither vocabulary distribution, document length, nor relevance structure with ours. Phase-B's eval corpus is explicitly spec'd as **~100 code snippets + 30 NL queries** with comparators granite-97m-r2 / e5-base / BGE-M3 / BGE-large — folding OBLIQ rows in would dilute that with off-distribution social text and produce numbers that don't generalize to our workload. **Do not add OBLIQ rows to the Phase-B corpus.**

**Methodology-reuse: YES (high value).** The 5-stage construction recipe is corpus-agnostic. Applied to our KB, it builds an *oblique code/KB slice*: e.g. cluster handoffs by a latent attribute ("describes a NUMA first-touch pinning bug"; "a benchmark that was later falsified") and generate queries that *avoid the surface terms* ("the issue where re-reading a file after dropping caches halved throughput" → should surface `feedback_drop_caches_numa_eviction`). This is exactly the query class that grep/keyword KB-RAG misses today (the stated motivation in `internal-kb-rag.md`: "topical/semantic queries miss documents that don't share keywords"). The `gap(t)` metric then quantifies how much our LLM-rerank stage recovers over first-stage MaxSim on *our* obliques.

### LateOn / DenseOn-decision relevance

- The LateOn-upgrade decision (`lighton-denseon-lateon-retrieval-upgrade.md`, S3b/S4b/S5) turns on: same-family drop-in (+2.55pp BEIR vs GTE), ONNX INT8 parity, EPYC latency ≤200ms/10 snippets, and an A/B on decontaminated web_research sentinels. **OBLIQ does not move any of those gates.**
- OBLIQ's LateOn numbers (0.003–0.149 NDCG@10) are **floor-level and out-of-domain** — they reflect oblique social/legal obliqueness, not code/BEIR retrieval. Citing them against LateOn would be the `feedback_classify_eval_failures_by_reason` failure mode: a low score from *task mismatch*, not model capability. **The load-bearing LateOn evidence stays BEIR 57.22 / decontaminated 60.36.**
- The *one* genuinely useful cross-read for the LateOn decision: OBLIQ shows **all** sub-150M single-stage retrievers (LateOn included) under-surface obliques, which **reinforces that the LLM-rerank stage is the value-add**, not the first-stage model choice. I.e. it slightly *lowers* the stakes of LateOn-vs-GTE (both are first-stage; the rerank stage matters more) and *raises* the priority of the dense first-stage recall question (granite-97m-r2 bench / candidate-pool width).

### Open-model verification ceiling

The oracle is **closed GPT-5.2** — non-reproducible here. We can build an **open approximation**: use an EPYC reasoning route (architect_general Qwen3.5-122B or frontdoor Qwen3.6, both already in the stack, both needing `enable_thinking=False` per `feedback_qwen3x_enable_thinking_false`) as a **listwise verifier** over a candidate pool, and report `gap_open(t) = V_open_t − R_t`. This yields a *lower bound* on the recoverable gap (open verifier ≤ GPT-5.2), which is sufficient to justify the rerank stage internally — we don't need the absolute GPT-5.2 ceiling, only "does a reasoning verifier recover material recall our first-stage missed?" on *our* obliques. Absolute parity with the paper's 0.913 numbers is **not** a goal and **not** achievable.

## Decision gates & exact next steps

1. **CITE for the LateOn decision: only directionally, with a caveat.** In `lighton-denseon-lateon-retrieval-upgrade.md` and the reranker handoff, record OBLIQ as evidence that *first-stage recall is the bottleneck and the LLM-rerank stage is the value-add* — NOT as a LateOn score. **Action = the cross-ref note only; no gate change to S3b/S4b/S5.** (intake-689 note refresh, see RETURN.)
2. **BUILD an oblique code/KB eval using their recipe — gate it behind the existing Phase-B corpus work.** The Phase-B corpus (100 code snippets + 30 NL queries) is already the binding prerequisite for the granite-97m-r2 bench. **Extend it with an oblique slice**: add ~15–20 *oblique* NL queries constructed via OBLIQ stages 1→4 against our KB (latent-attribute lens → cluster handoffs → vocabulary-avoiding query). This is non-inference authoring work; do it when the Phase-B corpus is built, not before.
3. **Answer to "cite it / build our own / both?" → BOTH, but weighted to BUILD.** Cite is a one-line cross-ref (cheap, do now in docs). Build is the real deliverable and is *gated on Phase-B corpus existence* (itself gated on K2 chunker activation per `granite-97m-r2-bench-plan.md`).
4. **Open verification-ceiling probe (optional, inference-gated, operator-run).** When an oblique KB slice exists and an A/B window opens, measure `gap_open(t)` with an open listwise verifier. Exact operator command to prepare (DO NOT run here):
   ```
   # Build oblique slice qrels first (non-inference), then:
   cd /mnt/raid0/llm/epyc-inference-research
   python3 scripts/benchmark/eval_oblique_kb.py \
     --corpus /mnt/raid0/llm/epyc-orchestrator/.kb_rag_index \
     --queries benchmarks/datasets/oblique_kb/queries.jsonl \
     --qrels   benchmarks/datasets/oblique_kb/qrels.tsv \
     --first-stage gte-moderncolbert-v1 \
     --verifier-route architect_general \
     --report gap_open
   # (harness eval_oblique_kb.py does not exist yet — ~1 day authoring, non-inference; mirrors bench_colbert_rerank.py once that lands)
   ```
   Per repo policy (`feedback_speed_verify_via_llama_bench`, `feedback_no_concurrent_inference`): the user runs all benchmarks manually; the above is a *prepared* command, not for execution by an agent.
5. **DECONTAMINATE any built slice** against embedding training data using the already-planned S7 protocol (xxhash64 + 13-gram containment, threshold 0.5) before any A/B — same guard the LateOn handoff already mandates.

## Risks & contradicting evidence

- **Domain mismatch (primary risk).** OBLIQ measures obliqueness in *social/political/stylistic* text. Our obliqueness (if any) lives in *technical-doc / code* retrieval, which may be structurally different (code obliqueness is often *symbolic* — identifier renames, indirection — not *latent-stance*). The transfer of the *recipe* is sound; the transfer of any *quantitative* OBLIQ result is not. Treat all OBLIQ numbers as out-of-domain.
- **It may not reproduce a gap on OUR corpus at all.** It is entirely possible our KB/code queries are *not* very oblique (our users phrase queries with technical surface terms that overlap the docs). The build-our-own step is partly a *test of whether obliqueness even exists* in our workload — if `gap_open` is small, that itself is a useful null result that *de-prioritizes* further rerank investment. Don't pre-commit to "obliqueness is a problem for us."
- **Closed-oracle non-reproducibility.** Absolute gaps (0.263–0.878) are GPT-5.2-specific and cannot be reproduced or cited as our expected headroom. Any internal number must come from our open verifier and be labeled a lower bound.
- **Pooled-vs-gold metric trap.** The pooled NDCG@10 in the dataset card shows ~0 gap because the pool is built from the retrievers themselves; the honest gold-only view shows the large gaps. If we reuse OBLIQ's pooling code, we must evaluate gold-only, or we'll reproduce a misleading null. (`feedback_observe_before_diagnosing`.)
- **Source-data ToS.** Dataset is CC-BY-4.0 but composed from Twitter/X, WildChat, GovInfo — each with its own terms. Not a license *blocker* for analysis (`feedback_license_not_a_blocker`), but a reason *not* to redistribute it into our repos; reference by HF URL only.
- **No benchmark harness code released.** Only the HF dataset is public; no GitHub harness link in the paper. Building our own eval harness is required regardless — which aligns with the methodology-reuse (not dataset-plug-in) conclusion.

## Cross-refs

- `handoffs/active/colbert-reranker-web-research.md` — Phase-A/B reranker bench; intake-689 note refined here. Eval-corpus prereq (100 code snippets + 30 NL queries; comparators granite-97m-r2 / e5-base / BGE-M3 / BGE-large).
- `handoffs/active/internal-kb-rag.md` — KB-RAG (GTE-ModernColBERT-v1, 13,537 chunks, MaxSim); target for the oblique-KB slice; K7 flywheel eval.
- `research/deep-dives/lighton-denseon-lateon-retrieval-upgrade.md` — LateOn/DenseOn upgrade decision (intake-428/430/431); OBLIQ does NOT change its gates.
- `research/deep-dives/granite-embedding-97m-r2-evaluation.md` + `handoffs/active/granite-97m-r2-bench-plan.md` — Phase-B corpus + dense first-stage choice (gated on K2 chunker).
- `research/deep-dives/reason-mxbai-colbert-32m-edge-retriever.md` — 3rd reranker slot (CPU-latency fallback).
- Memory: `feedback_classify_eval_failures_by_reason` (out-of-domain low score ≠ capability), `feedback_qwen3x_enable_thinking_false` (open verifier route config), `feedback_speed_verify_via_llama_bench` / `feedback_no_concurrent_inference` (operator-run benches), `feedback_license_not_a_blocker`.
- Source: arXiv:2605.06235 · dataset HF `dianetc/OBLIQ-Bench` (CC-BY-4.0).
