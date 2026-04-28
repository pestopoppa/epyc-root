# RAG Alternatives

**Category**: `rag_alternatives`
**Confidence**: research (pre-deployment, evaluation-gated)
**Last compiled**: 2026-04-28
**Sources**: 1 active handoff (sliders-local-validation), 1 intake entry (intake-494)

## Summary

Embedding-based retrieval (ColBERT/late-interaction or dense bi-encoder) is the dominant architecture for knowledge-base QA at EPYC's scale (≤10K markdown documents per the wiki/handoffs/research corpora). This page documents **architectural alternatives** that replace retrieval with persistent structured state, the conditions under which alternatives become viable, and the closure-inflation discipline applied to "alternative architecture failed our test → architecture class is not viable" claims.

The leading alternative tracked in 2026 is **SLIDERS** (intake-494, Stanford OVAL/Genie, arxiv:2604.22294), which extracts salient information from documents into a relational database and replaces text-concatenation reasoning with SQL queries over persistent structured state. SLIDERS' headline appeal is the "aggregation bottleneck" framing: even when each chunk fits the context window, chunk-extract-then-combine pipelines must re-reason over an ever-growing pile of intermediate evidence. SQL over a pre-extracted DB decouples reasoning cost from raw token count.

A third pattern — **persistent compiled wikis** — is itself a RAG alternative (this knowledge base is an instance). Knowledge is pre-compiled into curated articles by the `project-wiki` skill rather than synthesized at query time; retrieval falls back to semantic search over the curated surface. This trades latency (articles are pre-written) for curation burden and staleness risk.

The 2026-04-28 update on SLIDERS surfaced a **critical adoption blocker**: every code path in the released repo is hard-wired to GPT-4.1 / GPT-4.1-mini via the OpenAI / Azure OpenAI APIs, with no local-model code path. Initial intake framing that SLIDERS "runs locally on any capable LLM" was unsupported. Local adoption requires both endpoint substitution and validation that small-model SQL-agent loops survive — gated as a Phase 0 falsification experiment in `sliders-local-validation.md`.

## Structured DB + SQL: SLIDERS (intake-494)

**Architecture (per the released MIT codebase at `github.com/stanford-oval/sliders`)**:

1. **Per-question schema induction** from a fixed taxonomy library (`sliders_taxonomy.json`) keyed by query-type (Ordering / Multiple Choice / Other) × document-type (Narration / Policy / Dataset / Other). Schema is NOT free-form and NOT fixed up-front; users may also pin a schema. The taxonomy library partly mitigates schema-hallucination risk vs free-form schema generation.
2. **LLM-driven extraction** with `_quote`, `_rationale`, `_confidence` columns capturing provenance.
3. **Reconciliation** via a controller_executor_loop with up to 5 controller iterations × 5 SQL attempts × 3 retries × 20 inspections; primary_key_selector picks PKs (up to 10 candidates × 10 inspections); row-grouping by PK; non_pk_canonicalization two-pass mode; null_handling with `placeholder_text=UNKNOWN`. Cost-heavy by construction.
4. **SQL generation + execution** over the materialized DB, then answer synthesis with citations.

**Reported results**:
- +6.6 pp avg (LLM-judge metric, soft/hard evaluator prompts) over the union of baselines (RAG / base GPT-4.1 / DocETL / Chain-of-Agents / RLM) across FinanceBench, Loong, and Oolong existing benchmarks. Note: averaged across the baseline family, NOT specifically vs GPT-4.1 long-context — abstract phrasing can be misread.
- **WikiCeleb100** (3.9M tokens, new): +~19 pp over next-best baseline.
- **FinQ100** (36M tokens, SEC 10-Q derived, new): abstract reports +~32 pp; repo README reports +~50 pp. Unresolved discrepancy at intake date — defer to repo numbers for adoption realism only after independent confirmation.
- Baselines actually re-implemented in the repo: CoA + RLM only. RAG / LongRAG / GraphRAG / DocETL numbers were run externally and are harder to replicate.

**Code/data status**: code released MIT; eval-ID CSVs ship; corpora (FinanceBench, Loong, Oolong, WikiCeleb100, FinQ100) are NOT shipped — repo provides regeneration drivers (`experiments/wiki_celeb.py`, `experiments/sec_10q.py`) but the user must download from external sources (Wikipedia, SEC EDGAR).

## Phase 0 Falsification Gate (sliders-local-validation.md)

Bounded 2–3 session experiment, gated. **Does NOT block `internal-kb-rag.md`** — KB-RAG K1–K7 ships independently regardless of SLIDERS' verdict.

- **0.1**: Catalogue every GPT-4.1 / GPT-4.1-mini call site (schema_induction, relevance_gating, extraction, primary_key_selection, reconciliation_controller, reconciliation_executor, sql_generation, answer_synthesis, citation_generation). File path + line + prompt template length + output structure.
- **0.2**: Substitute OpenAI client at all sites with the local Coder-30B OpenAI-compatible endpoint. Diff for review.
- **0.3**: Run FinQ5 (5-question subset of FinQ100, regenerated from SEC EDGAR). Record per-stage LLM call count, schema-hallucination rate (SQL referencing columns/tables not in schema spec), wall-clock time per question.
- **0.4 — gate**: `not_viable_local` if schema hallucination > 20% averaged over all SQL emissions OR per-question call count > 5× the GPT-4.1 baseline. Specific verdict, not "structured-DB alternatives are not viable on local LLMs". `go_phase_1` if both gates met.

If Phase 0 passes, Phase 1 runs FinanceBench 10-question subset comparison vs internal-kb-rag K7 results on the same questions. If Phase 1 escalates, Phase 2 is scoping-only — produce a written scope for "SLIDERS as alternative architecture for K3/K4 of KB-RAG" with explicit cost estimate. Hard rule: do NOT merge SLIDERS into the KB-RAG handoff. Maintain two paths or close.

## Compilation vs Retrieval: Wikis as Alternative

A pattern adjacent to RAG-vs-SQL that EPYC actively uses: **persistent LLM-compiled wikis** (this knowledge base, plus the `wiki/INDEX.md` index, plus the per-category articles like `kv-cache.md`, `quantization.md`). Knowledge is pre-compiled by `project-wiki` skill from handoffs / research / progress logs into curated articles. Retrieval at query time falls back to semantic search over those curated articles, plus optional KB-RAG over the underlying corpora.

Tradeoff: latency (pre-written articles) vs curation burden + staleness risk. EPYC uses a hybrid — `project-wiki` for stable / cross-cutting topics where curation pays off, KB-RAG for dense ad-hoc cross-referencing during Explore-agent runs.

## Closure-Inflation Discipline Note

Per `feedback_closure_inflation.md` memory: SLIDERS-as-released failing the Phase 0 gate on Coder-30B at FinQ5 scale would be a **specific** closure ("SLIDERS as released, on Coder-30B, at FinQ5 scale, fails gate X"). It does NOT close:
- "Structured-DB QA architectures are not viable on local LLMs" (different implementations / models / SQL agent patterns could still be viable).
- "Per-question schema induction is unworkable" (SLIDERS' specific taxonomy library is one design; alternatives exist).
- "EPYC must rely entirely on retrieval-based RAG" (wiki compilation is already an alternative we use successfully).

Document the closure scope explicitly in the closure block when the gate is decided.

## Open Questions

- What is the LLM-call cost amortization on our ~24 wiki + ~70 active handoff corpus (target scale: 10K–50K tokens, vs FinQ100's 36M)? Headline gain likely does not materialize at our scale even if local-model substitution works.
- Can SLIDERS' reconciliation pattern (`_quote` + `_rationale` + `_confidence` columns + controller-executor loop) be adopted independently of the SQL-as-primary architecture — e.g., as a knowledge-base governance signal? Worth investigating after Phase 0 closes.
- What boundary conditions (corpus size, query diversity, schema complexity, LLM capability) make SLIDERS-vs-ColBERT the right choice? The current decision is corpus-size driven, but query-pattern (single-document QA vs cross-document aggregation) likely matters too.

## Related Categories

- [Knowledge Management](knowledge-management.md) — KB-RAG and wiki compilation as the primary architectures
- [Search & Retrieval](search-retrieval.md) — ColBERT-based retrieval (the dominant path EPYC uses)
- [Context Management](context-management.md) — progressive folding for conversation history; SLIDERS frames its problem as the *cross-document* analogue of folding's *cross-turn* aggregation bottleneck

## Source References

- [`sliders-local-validation.md`](../handoffs/active/sliders-local-validation.md) — Phase 0 falsification gate, bounded 2–3 sessions, gates on schema-hallucination > 20% and call-count > 5× baseline, "Does NOT block `internal-kb-rag.md`" header
- [intake-494](https://arxiv.org/abs/2604.22294) SLIDERS (Joshi/Shethia/Dao/Lam, Stanford OVAL/Genie, submitted 2026-04-24) — credibility 4 (Stanford major-lab signal +1, within-12mo +1, code released +1, peer-review pending +1, no independent corroboration 0); +6.6 pp avg over union of baselines on existing benchmarks; +~19 pp WikiCeleb100; +~32/~50 pp FinQ100 (abstract-vs-README discrepancy unresolved at intake date); GPT-4.1 hard-wired adoption blocker (Tier 2b); per-query reconciliation cost-heavy by construction
- [`research/intake_index.yaml`](../research/intake_index.yaml) intake-494 — full Tier 2b critique enumerating frontier-API-only architecture, headline-number disagreement, schema-hallucination as #1 LLM-to-SQL production failure, long-context relational reasoning underprediction (arxiv:2510.03611), single-source results, per-document amortization caveat
