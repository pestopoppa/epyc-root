# Handoff: SLIDERS Local-LLM Validation

**Status**: STUB / Phase 0 falsification gate not yet run
**Created**: 2026-04-28 (from intake-494, refined deep-dive 2026-04-28)
**Priority**: LOW (speculative — does NOT block any production work)
**Categories**: rag_alternatives, knowledge_management, context_management
**Related**: [`internal-kb-rag.md`](internal-kb-rag.md), [`context-folding-progressive.md`](context-folding-progressive.md), [`research-evaluation-index.md`](research-evaluation-index.md)
**Source paper**: SLIDERS (arxiv:2604.22294, Stanford OVAL/Genie group, Joshi/Shethia/Dao/Lam, submitted 2026-04-24)
**Source code**: `github.com/stanford-oval/sliders` (MIT, also on PyPI as `sliders-genie`)

> **Does NOT block `internal-kb-rag.md`. KB-RAG K1–K7 ships independently. SLIDERS is an ALTERNATIVE architecture (DB+SQL replacing retrieval), not an upgrade lane on the ColBERT path. Sequential evaluation only after KB-RAG K7 ships, and only if Phase 0 below passes.**

## Agent Operating Instructions

- This handoff is gated by a Phase 0 falsification test. Do NOT begin Phase 1 until Phase 0 produces a written GO verdict.
- Phase 0 is bounded — if either gate condition trips, CLOSE the handoff as `not_viable_local` and document the closure with the failing measurement. Do not iterate trying to make it work.
- All Phase 0 work happens against the upstream MIT-licensed `github.com/stanford-oval/sliders` repo, in a scratch directory. **Do not vendor SLIDERS into our repos until Phase 1 passes.**
- Closure-inflation policy (per `feedback_closure_inflation.md`): on close, enumerate which gate(s) tripped and which did not. Do not generalize to "structured-DB QA architectures are not viable on local LLMs" — only "SLIDERS as released, on Coder-30B at this corpus scale, fails gate X".
- After Phase 0 completes (either verdict): update `progress/YYYY-MM/YYYY-MM-DD.md`, update the row in `research-evaluation-index.md`, and update the entry in `master-handoff-index.md`.

## Objective

Determine whether SLIDERS — a structured-DB+SQL alternative to retrieval-based RAG that replaces text-concatenation reasoning with persistent relational state — can run on EPYC's local Coder-30B-class models. The released SLIDERS code is hard-wired to GPT-4.1 / GPT-4.1-mini via the OpenAI / Azure OpenAI APIs at every stage. Local-model adoption requires both endpoint substitution and validation that small-model SQL-agent-loop quality survives.

## Why this is gated, not an active workstream

- **Frontier-API-only by construction**: every stage (schema induction, relevance gating, extraction with quote+rationale columns, primary-key selection, reconciliation controller+executor, SQL generation, answer synthesis, citation generation) calls GPT-4.1 / GPT-4.1-mini. There is no local-model code path in the released repo.
- **Schema hallucination risk**: schema hallucination is the #1 production failure mode for LLM-to-SQL pipelines (web evidence: production failures dominated by schema hallucinations + incorrect join paths). SLIDERS' per-question schema induction (from the fixed `sliders_taxonomy.json` library) partially mitigates this, but the schema is still LLM-driven. Coder-30B may schema-hallucinate at a rate that breaks the controller/executor loop (5 iter × 5 SQL × 3 retries × 20 inspections — brittle to small-model errors).
- **Scale gap**: SLIDERS' headline gains (+~32 pp / +~50 pp on 36M-token FinQ100) are at corpus scales 100× our wiki+handoff corpus. The headline gain likely does not materialize at our scale even if local-model substitution works.
- **Stronger architectural alternatives exist for our scale**: the ColBERT-based KB-RAG (`internal-kb-rag.md` K1–K7) is the sized-appropriate architecture for our 24 wiki articles + 70 active handoffs + 30 research notes + 246 source documents. SLIDERS is for orders-of-magnitude-larger corpora.

## Phase 0 — Falsification Gate (mandatory before any Phase 1+ work)

Goal: a single written verdict, GO or `not_viable_local`. ~2–3 sessions of work. No production code, no integration with KB-RAG.

- [ ] **0.1 Catalogue GPT-4.1 call sites**: clone `github.com/stanford-oval/sliders` (MIT) into a scratch directory under `/mnt/raid0/llm/scratch/sliders/`. Read every Python file. Produce `data/sliders_validation/01_call_site_catalog.md` listing every distinct LLM call site with: stage name (one of: schema_induction, relevance_gating, extraction, primary_key_selection, reconciliation_controller, reconciliation_executor, sql_generation, answer_synthesis, citation_generation), file path + line number, model expected (GPT-4.1 vs GPT-4.1-mini), prompt template length (tokens), output structure (free-form vs JSON vs SQL).
- [ ] **0.2 Local-model substitution**: substitute the OpenAI client at all sites with our local OpenAI-compatible Coder-30B endpoint. Use the existing `epyc-orchestrator` Coder-30B wrapper as the Python adapter (do not vendor a new client). Produce `data/sliders_validation/02_substitution_diff.md` showing the unified diff. Do NOT modify any prompt templates yet — first measure the unmodified-prompt baseline.
- [ ] **0.3 FinQ5 end-to-end run**: pick the first 5 questions from FinQ100 (we will need to regenerate the corpus from SEC EDGAR via SLIDERS' `experiments/sec_10q.py` — this is bounded, ~30 minutes if EDGAR is reachable). Run SLIDERS end-to-end on each question with the Coder-30B substitution. Record per-question, per-stage:
  - Pass/fail vs expected answer (FinQ100 ships with ground-truth)
  - Total LLM call count (target: ≤ 5× the GPT-4.1 baseline reported in the paper, since we're API-free)
  - Schema hallucination rate (defined: SQL emitted by Coder-30B references columns / tables that were not in the per-question schema spec). Detect via repo's existing schema-validation step.
  - Wall-clock time per question
  - Output: `data/sliders_validation/03_finq5_results.json`
- [ ] **0.4 Gate decision**: write `data/sliders_validation/04_phase0_verdict.md` containing one of:
  - **`not_viable_local`** if EITHER schema hallucination > 20% (averaged over 5 questions × all SQL emissions) OR per-question call count > 5× the GPT-4.1 baseline. State which gate(s) tripped, with the actual measured numbers. CLOSE this handoff. Do NOT generalize to "structured-DB QA architectures are not viable on local LLMs" — the closure is specific to SLIDERS as released, on Coder-30B, at FinQ5 scale.
  - **`go_phase_1`** if BOTH gates met. Document the FinQ5 pass rate and per-stage call counts. Proceed to Phase 1.
  - **`inconclusive`** is NOT an allowed verdict. If the run was incomplete or the substitution failed at the API layer, fix the bug and re-run; do not close the gate as inconclusive. (The single exception: if EDGAR is unreachable and FinQ regeneration is impossible, document that and propose an alternative bounded test set in 0.3.)

## Phase 1 — Conditional: FinanceBench Subset (only after Phase 0 GO)

- [ ] **1.1** Run SLIDERS+Coder-30B on a 10-question FinanceBench subset (FinanceBench corpus is referenced by SLIDERS as one of its three existing-benchmark baselines). Record same metrics as Phase 0.3.
- [ ] **1.2** Run our internal-kb-rag K7 evaluation pipeline on the *same* 10 questions but with a chunk-RAG over the FinanceBench corpus. Compare answer accuracy and recall on the same questions, with the ~1pp Flywheel variance band as the noise floor.
- [ ] **1.3** Decision: does SLIDERS-on-Coder-30B beat ColBERT-on-Coder-30B on this benchmark by enough to justify maintaining a parallel architecture? If delta < 5 pp, close as `phase_1_inconclusive_no_advantage`. If delta ≥ 5 pp, escalate to Phase 2 scoping.

## Phase 2 — Conditional & Speculative: Alternative-Architecture Scoping (only after Phase 1 escalates)

- [ ] **2.1** SCOPING ONLY. Produce a written scope for "SLIDERS as alternative architecture for K3/K4 of KB-RAG". Consider: parallel paths (maintain both ColBERT and SLIDERS, route per-query) vs replacement (drop ColBERT) vs hybrid (use SLIDERS for high-aggregation queries, ColBERT otherwise). Include explicit cost estimate (LLM call count per query × specialist cost). **Hard rule**: do NOT merge SLIDERS into the KB-RAG handoff. Maintain two paths or close — never blur the distinction.

## Closure Section (TO BE FILLED ON CLOSE)

When this handoff closes (either via Phase 0 `not_viable_local` or Phase 1 `phase_1_inconclusive_no_advantage` or Phase 2 deciding not to escalate), append a closure block here with:
- Final verdict
- Which gate(s) tripped, with measured numbers
- Closure-inflation discipline statement: which specific claim is being closed, and which broader claims are NOT being closed (e.g., "SLIDERS-as-released on Coder-30B at FinQ5 scale fails gate X" does NOT close "structured-DB QA architectures are not viable on EPYC")
- Move handoff to `handoffs/completed/` with the closure block as the closing artefact

## Out of Scope

- Wholesale adoption of SLIDERS into production KB retrieval. That is what Phase 2 scoping deliberately defers.
- Modifying SLIDERS prompts to "fix" Coder-30B failures during Phase 0. Phase 0 measures unmodified-prompt baseline; prompt engineering for small models is a separate (and probably unbounded) work item.
- Re-implementing SLIDERS in our codebase. Phase 0 runs against upstream MIT code in a scratch directory.
- Validation against datasets that SLIDERS does not ship code to regenerate (e.g., Loong, Oolong if not reproducible). FinQ100 / WikiCeleb100 / FinanceBench subset are the in-scope corpora.

## Cross-References

- **Source intake**: intake-494 in `research/intake_index.yaml` (full Tier 2b critique + GPT-4.1-only adoption blocker documented).
- **Sibling KB architecture**: `internal-kb-rag.md` K1–K7 (ColBERT-based RAG, the sized-appropriate alternative for our corpus scale).
- **Cross-cutting in research-evaluation-index**: registered as a monitoring/experimental row (this handoff's Phase 0 gate is the exit criterion).
- **Master-handoff-index**: dispatched via `research-evaluation-index.md` entry.

## Effort Estimate

- Phase 0: ~2–3 sessions, single-shot gated. Bounded.
- Phase 1 (conditional on Phase 0 GO): ~2 sessions.
- Phase 2 (conditional on Phase 1 escalate): ~1 session, scoping only.
- Total even in best case: ≤ 6 sessions. Most likely outcome: Phase 0 closes the handoff as `not_viable_local` after ~2 sessions.
