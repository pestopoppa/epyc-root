# RAG Alternatives

**Category**: `rag_alternatives`
**Confidence**: research (pre-deployment, evaluation-gated)
**Last compiled**: 2026-11-01 (intake backfill, IDs ≤2060, workspace-58). Earlier: 2026-10-31 (operator wiki sweep, workspace-58): Mainplane 'retrieval over compaction' intake verdict. Earlier: 2026-06-21. Earlier: 2026-06-21
**Sources**: 1 active handoff (sliders-local-validation), 3 intake entries (intake-494, intake-710/711 OKF, intake-698 MRAgent)

## Compiled Update — 2026-11-01 (intake backfill, IDs ≤2060)

Verified research-intake findings (dive-verified entries not previously compiled into the wiki). Each bullet carries its anchored claim or `#record` citation; EPYC relevance is stated per entry.

- **PageIndex vectorless RAG** (intake-890#record) LLM-built hierarchical document tree with LLM reasoning down the tree instead of embeddings. Dive corrections: the 98.7% FinanceBench figure belongs to the commercial Mafin 2.5 product, and the independent evaluation reports 9 of 16 queries timed out (Qwen3-32B via Ollama). Adopt patterns only.
- **ArgRAG explainable RAG** (intake-1052#record) QBAF over the claim plus top-k passages with uniform base score 0.5 and Quadratic Energy semantics; two contestation primitives (Contest Base Score, Contest Polarity) trigger deterministic recompute. Relevant as an auditable alternative to opaque RAG answer generation.
- **Multi-objective HPO for LLM and RAG** (intake-1389#00) Multi-objective BO (qLogEHVI/qLogNEHVI) over seven RAG knobs with a 50-evaluation budget per run. Dispatch premise of results tables was wrong: the comparison is figure-only, and the one table lists per-objective optima.
- **CDS4RAG** (intake-1391#01) Splits RAG knobs into retriever and generator blocks tuned cyclically; retriever evaluation is ~50% cheaper than generator evaluation. The dispatch framing (AI vs non-AI knobs) was wrong.

## Summary

Embedding-based retrieval (ColBERT/late-interaction or dense bi-encoder) is the dominant architecture for knowledge-base QA at EPYC's scale (≤10K markdown documents per the wiki/handoffs/research corpora). This page documents **architectural alternatives** that replace retrieval with persistent structured state, the conditions under which alternatives become viable, and the closure-inflation discipline applied to "alternative architecture failed our test → architecture class is not viable" claims.

The leading alternative tracked in 2026 is **SLIDERS** (intake-494, Stanford OVAL/Genie, arxiv:2604.22294), which extracts salient information from documents into a relational database and replaces text-concatenation reasoning with SQL queries over persistent structured state. SLIDERS' headline appeal is the "aggregation bottleneck" framing: even when each chunk fits the context window, chunk-extract-then-combine pipelines must re-reason over an ever-growing pile of intermediate evidence. SQL over a pre-extracted DB decouples reasoning cost from raw token count.

A third pattern — **persistent compiled wikis** — is itself a RAG alternative (this knowledge base is an instance). Knowledge is pre-compiled into curated articles by the `project-wiki` skill rather than synthesized at query time; retrieval falls back to semantic search over the curated surface. This trades latency (articles are pre-written) for curation burden and staleness risk.

The 2026-04-28 update on SLIDERS surfaced a **critical adoption blocker**: every code path in the released repo is hard-wired to GPT-4.1 / GPT-4.1-mini via the OpenAI / Azure OpenAI APIs, with no local-model code path. Initial intake framing that SLIDERS "runs locally on any capable LLM" was unsupported. Local adoption requires both endpoint substitution and validation that small-model SQL-agent loops survive — gated as a Phase 0 falsification experiment in `sliders-local-validation.md`.

## Key Findings

- Structured DB + SQL can remove repeated evidence aggregation, but SLIDERS is not locally deployable without replacing its hosted-model dependency and validating the resulting SQL-agent loop.
- Persistent compiled wikis are a practical low-latency alternative to query-time synthesis, with curation effort and staleness as their principal costs.
- Architecture-level rejection requires a bounded falsification gate; one failed implementation does not close the whole structured-state design class.

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

## Structured-Knowledge Format: OKF (intake-710/711)

The **Open Knowledge Format** (OKF v0.1, Google Cloud) is a vendor-neutral spec that formalizes the "LLM-wiki" pattern (Karpathy gist, Obsidian, AGENTS.md/CLAUDE.md) into a portable format — explicitly a *format, not a platform*: producible without SDKs, consumable without integrations. An OKF bundle is a directory of markdown files with YAML frontmatter, where each file is one concept, the **file path IS the concept identity**, and concepts cross-link via plain markdown links to form a graph. This is the compilation-vs-retrieval / structured-knowledge axis: it standardizes the curated-markdown surface that the persistent-compiled-wiki alternative already produces, rather than introducing a new retrieval mechanism.

**Adoption verdict (2026-06-20): 5 of 6 conventions were already satisfied by existing EPYC infrastructure; only 2 genuinely-new conventions were adopted**, both landed in `wiki/SCHEMA.md ## Conformance`:

1. **`schema_version` / okf-style version stamp** — the wiki taxonomy is now stamped `schema_version: "1.0"` so parallel agents and cross-repo consumers can detect backward-incompatible drift.
2. **Permissive-consumption contract** — codifies as an *intentional* contract that intake-entry consumers MUST preserve unknown/extra keys and MUST NOT reject an entry for carrying extra fields (already the de-facto behavior of `validate_intake.py`, now protected against silent regression).

**Rejected as already-covered**: reserved `index.md` (we have `wiki/INDEX.md` progressive-disclosure index), permissive validator (already implemented), per-file dated change history, equivalent section headings, and GitNexus graph visualization. Confidence: **external (vendor spec)** — OKF informs interoperability framing and KB-doc schema hygiene, not a deployment dependency.

> Source: [intake-710/711](https://arxiv.org/abs/2606.09821) OKF (Google Cloud); [`wiki/SCHEMA.md`](SCHEMA.md) ## Conformance (added 2026-06-20)

## Active Reconstruction vs Static Retrieve-then-Reason: MRAgent (intake-698)

MRAgent ("Memory is Reconstructed, Not Retrieved") frames a **process-level** RAG alternative orthogonal to SLIDERS' structural one: rather than fixing memory access *before* inference (the static retrieve-then-reason pipeline that ColBERT/dense RAG implements), it **actively reconstructs** memory by interleaving LLM reasoning with retrieval — iteratively exploring and **pruning retrieval paths on intermediate evidence** over a Cue-Tag-Content associative graph. The pitch: static retrieval cannot adapt to evidence accumulated during reasoning, while evidence-conditioned path-pruning keeps token/runtime cost bounded against combinatorial blowup. Reported LongMemEval 86.76% vs Mem0 53.01% and ~118k tokens vs 245k–3,268k for baselines.

**EPYC disposition**: comparative datapoint only. It is **cloud-LLM-bound** (Gemini-2.5-Flash / Claude-Sonnet-4.5 for both graph construction and retrieval reasoning) with no CPU/local/quantized path, and it loses to Mem0 on LoCoMo multi-hop F1 (43.69 vs 45.17), so its accuracy/token figures are observations, not decision-gating. The transferable asset is the **active-reconstruction retrieval policy + token-cost discipline via path-pruning**, which is logged alongside KB-RAG's parked self-correcting two-pass retrieval as a second instance of the same deferred-pending-a-consumer-signal pattern. See also [Search & Retrieval](search-retrieval.md) for the retrieval-policy framing.

> Source: [intake-698](https://arxiv.org/abs/2606.06036) MRAgent — active reconstruction (LLM-reasoning-in-the-loop retrieval); cloud-LLM-bound; token-cost discipline transferable

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

- [`sliders-local-validation.md`](../handoffs/active/knowledge-pipelines.md#track-sliders-local-validation) — Phase 0 falsification gate, bounded 2–3 sessions, gates on schema-hallucination > 20% and call-count > 5× baseline, "Does NOT block `internal-kb-rag.md`" header
- [intake-494](https://arxiv.org/abs/2604.22294) SLIDERS (Joshi/Shethia/Dao/Lam, Stanford OVAL/Genie, submitted 2026-04-24) — credibility 4 (Stanford major-lab signal +1, within-12mo +1, code released +1, peer-review pending +1, no independent corroboration 0); +6.6 pp avg over union of baselines on existing benchmarks; +~19 pp WikiCeleb100; +~32/~50 pp FinQ100 (abstract-vs-README discrepancy unresolved at intake date); GPT-4.1 hard-wired adoption blocker (Tier 2b); per-query reconciliation cost-heavy by construction
- [`research/intake_index.yaml`](../research/intake_index.yaml) intake-494 — full Tier 2b critique enumerating frontier-API-only architecture, headline-number disagreement, schema-hallucination as #1 LLM-to-SQL production failure, long-context relational reasoning underprediction (arxiv:2510.03611), single-source results, per-document amortization caveat
- [intake-710/711](https://arxiv.org/abs/2606.09821) OKF — Open Knowledge Format v0.1 (Google Cloud): markdown+YAML-frontmatter knowledge bundles as a structured-knowledge / compilation-vs-retrieval alternative; 5/6 conventions already in the KB, only `schema_version` stamp + permissive-consumption contract adopted (now in [`wiki/SCHEMA.md`](SCHEMA.md) ## Conformance, 2026-06-20)
- [intake-698](https://arxiv.org/abs/2606.06036) MRAgent ("Memory is Reconstructed, Not Retrieved") — active-reconstruction retrieval policy (Cue-Tag-Content graph + evidence-conditioned path pruning) as a process-level RAG alternative to static retrieve-then-reason; cloud-LLM-bound comparator, token-cost discipline is the transferable lever; cross-linked from [Search & Retrieval](search-retrieval.md)

## Compiled Update — 2026-10-31 (operator wiki sweep, workspace-58)

**Confidence: judged** (intake analysis, no compute); no measurement exists for the one new element.

- **Retrieval over compaction is prior art, not a new technique.** The Mainplane pointer-only hand-off keeps the full transcript searchable and drops the summary; MemGPT, Cursor dynamic context discovery, Claude Code and OpenClaw already keep transcripts searchable beside a summary, and our REPL already emits read_file/peek pointers. The only new element is dropping the summary, and its evidence is n=1 hand-off cost with no accuracy measurement. Stage 4 files TOC-MP-1..4 plus monitor notes rather than an adoption. ([progress 2026-10-30](../progress/2026-10/2026-10-30.md); [repl-session-memory-maturity](../handoffs/active/memory-program.md#track-repl-session-memory-maturity))

Sources: [2026-10-30 progress](../progress/2026-10/2026-10-30.md) · [repl-session-memory-maturity](../handoffs/active/memory-program.md#track-repl-session-memory-maturity) · [tool-output-compression](../handoffs/active/context-and-token-economy.md#track-tool-output-compression)

## Compiled Update — 2026-11-07 (SLIDERS answered, ODL-011 declined, ODL-013 re-run authorised)

**Confidence: verified** (tick and decision text in the knowledge-pipelines handoff; no new measurement)

- **SLIDERS Phase 0 is on: "evaluate now, low-priority filler"** (operator E4, 2026-11-07), answering the K7-precondition decision. Box 0.4 (`data/sliders_validation/04_phase0_verdict.md`) is the open work item: clone stanford-oval/sliders into scratch, catalogue every GPT-4.1 call site, substitute the local OpenAI-compatible coder endpoint, run FinQ5 end to end, then write the verdict. Non-inference prep runs first. No verdict exists yet.
- **ODL-011 declined (operator).** Intrinsic chunk scores cannot gate alone, the routing default is unchanged, and the arm needs an LLM judge plus a RAG answer-correctness endpoint with no current consumer. Re-file only if the ODL-013 P-DOCPARSE-1 verdict leads to a routing change.
- **ODL-013 re-run authorised (operator E2 "Ratify + Re-run")**: row `pip04-odl013-rerun-r2-20261107`, four arms on the 200-PDF corpus. The default stays unchanged until the decision-capable gate closes.
- **Unlimited-OCR default is quant-compliant**: `Unlimited-OCR-Q5_K_M-outq8.gguf` re-hashed to the recorded SHA-256 `b4c9ba49...c926e2`; 155 tensors, only `output.weight` changed Q6_K to Q8_0, 154 byte-identical to the Q5_K_M source.

Sources: [knowledge-pipelines](../handoffs/active/knowledge-pipelines.md)

## Compiled Update — 2026-11-09 (SLIDERS client timeout, KB index cutover)

**Confidence: verified** (handoff notes and job logs; no SLIDERS gate recorded, n = 0)

- **SLIDERS on a local model measures its own timeouts first.** The released client hard-codes a 200 s request timeout and issues up to 16 concurrent calls; against a 2-slot server the requests expire in the queue (76 abandoned in r3's first question, 5,516 s, 100 LLM calls, 0 SQL executions, answer `[Error] Request timed out.` recorded as `ok`). The r4 row patches the timeout to 3,600 s on both import paths, uses 4 slots and counts `[Error]` answers as `fail`. Any FB5 gate read from r3 would have been a timeout rate, not a schema-hallucination rate.
- **A re-arm must reassess, not copy.** r3 was r2's spec verbatim (one quarter, about 13 h); the operator objected. See the `inference-backlog-scheduling` skill, section 4.
- **KB RAG default moved to `index-qd-v2`** (orchestrator `b4e25aa1`, rebuild row PASS). The shared orchestrator clone's local `main` still read `index-qd-v1` (62 commits behind), so `PIP04-KB-INDEX-BREAK` stays open until that clone is fast-forwarded and the update hook fails loudly.

Sources: [knowledge-pipelines](../handoffs/active/knowledge-pipelines.md) · [inference-backlog-scheduling skill](../.claude/skills/inference-backlog-scheduling/SKILL.md)
