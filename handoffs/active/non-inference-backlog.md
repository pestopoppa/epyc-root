# Non-Inference Backlog — Round 2 (2026-04-17 audit refresh)

**Status**: ACTIVE — 43 non-inference tasks catalogued. 31/43 done (23 original Round 2 + 4 × 2026-04-21 supplement + 2 × 2026-04-22 supplement = NIB2-47/NIB2-48). Open: NIB2-40..46 (7 items). NIB2-33 moved to excluded (hermes-outer-shell auth deferral).
**Created**: 2026-02 (Round 1, 18/18 complete → [`completed/non-inference-backlog.md`](../completed/non-inference-backlog.md))
**Refreshed**: 2026-04-17 (Round 2 catalogue from cross-cutting audit of all active handoffs)
**Supplemented**: 2026-04-21 (NIB2-31..34 added from handoff hygiene audit)
**Priority**: MEDIUM (as a whole; individual items tagged HIGH/MED/LOW below)

---

## Purpose

Cross-cutting catalogue of work that does **not** require:
- A running llama-server (AR-3, benchmarks, A/B tests, eval tower runs)
- AR-3 trial data, Package D completion, AP-26 sub_lm validation, Ouro P7, EV-4 baseline
- Cloud GPU budget
- Upstream PR merges

This is the "what can I pick up right now with no inference available?" list. Items link to their canonical handoff — update both places when status changes.

**Round 1 (completed/)** closed out 18 items (orchestrator refactoring, test coverage floors, CC local integration Phase 0, etc.). Round 2 catalogues what the 2026-04-17 audit surfaced as newly-unblocked or previously-orphaned.

---

## Highest-leverage sub-day wins (pick-up-and-ship)

- [x] **NIB2-01**: REPL S5 Gap 3 `_batch_llm_query()` combined-op — [`repl-turn-efficiency.md`](repl-turn-efficiency.md) L171-174. ~3-4h. HIGH impact / LOW effort (infrastructure exists; just expose `llm_batch()` as first-class REPL tool). **DONE 2026-04-17**: Added `_batch_llm_query()` to `_CombinedOpsMixin` in `combined_ops.py`, registered in REPL globals, 9 tests passing.
- [x] **NIB2-02**: EV-3 Scoring Verifiers adapter — [`eval-tower-verification.md`](eval-tower-verification.md) L151-157. 2-3h. Download `nvidia/Scoring-Verifiers`, create ~50-line adapter, register in `suites.py`. **DONE 2026-04-17**: Downloaded 4 JSONL files (HE-R/R+ 164 problems, MBPP-R 974, MBPP-R+ 378). Created `scoring_verifiers_adapter.py` with `load_problems()` + `load_scoring_verifiers_suite()`. Registered in `suites.py`.
- [x] **NIB2-03**: EV-0 MathQ-Verify dataset audit — [`eval-tower-verification.md`](eval-tower-verification.md) L129. 4-6h. Zero-code data cleaning (stages 1-4). **DONE 2026-04-21** (stages 1-3): `scripts/benchmark/dataset_audit/mathq_verify_audit.py` applied to 5,670 math-suite questions (aime + math + olympiadbench + physreason). 251 flagged (4.43%). Report: `progress/2026-04/mathq-verify-audit-2026-04-21.md`. Stage 4 (consistency) deferred — requires LLM-based atomic decomposition (inference-gated). Stage 5 skipped per paper ablation insight. V2 refinements identified: gate unbalanced-$ check on LaTeX-present prompts (GSM8K currency false positives), install `antlr4-python3-runtime` for deep parse validation.
- [x] **NIB2-04**: DAR-2 unit test for `_compute_contrastive_adjustment()` with mock store — [`decision-aware-routing.md`](decision-aware-routing.md) L74. 2h. Explicitly deferred in handoff. **DONE 2026-04-17**: 13 tests covering all branches (no context, embedding failure, no candidates, no alternatives, unlearned defaults, positive/negative adjustment, bounds capping, no memory_id).
- [x] **NIB2-05**: Frontdoor top-k=64 first-token log-probability instrumentation — [`learned-routing-controller.md`](learned-routing-controller.md) L132-135 P1.5.1. 2-4h. (Collection needs volume; instrumentation is code only.) **DONE 2026-04-17**: Feature flag `logit_probe` in `features.py`, `n_probs=64` added to payload when enabled, `_write_logit_probe()` captures first-token probs to JSONL at `data/logit_probe.jsonl`. Enable: `ORCHESTRATOR_LOGIT_PROBE=1`.
- [x] **NIB2-06**: Vision tool registry registration in orchestrator — [`multimodal-pipeline.md`](multimodal-pipeline.md) L44. 2-4h. Pure code, unblocks proactive vision delegation. **DONE 2026-04-17**: Created `src/tools/vision/` plugin (manifest.json + analyze.py) with 3 tools (vision_analyze, vision_search, vision_face_identify). Model-agnostic: checks mmproj_path on active models. 12 tests.
- [x] **NIB2-07**: Move `blocked/retrain-routing-models.md` to `archived/` — 5 min once directory permissions fixed. Superseded by Learned Routing Controller Phase 1 (2026-04-15). **DONE 2026-04-17**: Moved via sudo, staged in git.
- [x] **NIB2-08**: AP-21 GEPA ratio knob scaffolding — [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md). ~4h. Ratio-adjustable code path; flip decision gated on AR-3 data but the knob itself is code-only. **DONE 2026-04-17**: Made `gepa_ratio` dynamic — reads from `autopilot_state.json` (default 0.30). Set to 1.0 when AR-3 data confirms GEPA dominance.

## Investigation (code-reading / root-cause analysis)

- [x] **NIB2-09**: Per-request `</think>` budget investigation on Qwen3.5 hybrid SSM+MoE — [`per-request-reasoning-budget.md`](per-request-reasoning-budget.md) L45-50. 1-2 days. 4-step plan in llama.cpp-experimental: search `server.cpp`/`common/chat.cpp`/`src/llama-sampling.cpp`, trace hybrid code path, propose fix (`</think>` injection timing vs SSM state update). Steps 3-4 need a running server — keep them out of scope. **DONE 2026-04-17** (Steps 1-2): Full pipeline traced — reasoning-budget.cpp state machine (IDLE→COUNTING→FORCING→DONE), root cause identified (SSM state update race on hybrids), 3 fix options proposed. Handoff updated with line numbers.
- [x] **NIB2-10**: Integration-test-coverage residual unit gaps — [`integration-test-coverage.md`](integration-test-coverage.md) L127-132. 4-8h. Remaining edges in `graph/task_ir_helpers.py`, `graph/budgets.py`, `graph/answer_resolution.py` — test-only writes, no new code paths. **DONE 2026-04-17** (partial): 55 tests for `answer_resolution.py` covering all 7 functions (was zero coverage). `task_ir_helpers.py` and `budgets.py` gaps remain — existing partial coverage, lower priority.
- [x] **NIB2-11**: Package F post-hoc analysis — [`bulk-inference-campaign.md`](bulk-inference-campaign.md). 4-6h. Data already collected; analysis is log-parsing and chart generation. **DONE 2026-04-21**: Package F v2→v3 comparison table + synthesis added to `wiki/inference-serving.md` Key Findings (coder +101%, REAP +50%, frontdoor +13%, worker −1%). Raw data captured inline in bulk-inference-campaign.md § Package F.

## Medium-effort implementation (multi-day, no inference required)

- [ ] **NIB2-12**: `parallel_seeding.py` + `seeding_port_sets.py` — [`routing-and-optimization-index.md`](routing-and-optimization-index.md) § P15 (merged 2026-04-21 from parallel-seeding-eval.md). ~200 LoC, 1 day. Unlocks 2× AR-3 throughput. No blockers.
- [x] **NIB2-13**: OpenDataLoader Phase 1 swap in `pdf_router.py` — [`opendataloader-pipeline-integration.md`](opendataloader-pipeline-integration.md) L36-44. 1-2 days. JVM lifecycle + swap `pdftotext -layout` for `opendataloader_pdf.convert(...)`, retain entropy/garbage quality checks, update `tests/services/test_pdf_router.py`. **DONE 2026-04-17**: Added `_extract_with_opendataloader()` method, `PDF_EXTRACTOR=opendataloader` env var routing, fallback to pdftotext if ODL returns empty. Quality checks retained. ODL package install needed for production.
- [x] **NIB2-14**: Clone `opendataloader-bench`, add `document_extraction` suite with NID/TEDS/MHS scoring — [`opendataloader-pipeline-integration.md`](opendataloader-pipeline-integration.md) L95-107. 1 day. **DONE 2026-04-17**: Created `document_extraction_adapter.py` with `DocumentExtractionAdapter` class, `score_nid()` (reading order), `score_teds()` (table structure), `score_mhs()` (heading hierarchy), `score_document()` (aggregate). Registered in dataset_adapters.py. 18 scoring tests. Repo clone deferred (Git LFS).
- [ ] **NIB2-15**: Goedel-CP-8B GGUF conversion + Q4_K_M/Q8_0 quantization — [`pipeline-integration-index.md`](pipeline-integration-index.md) § P2.S1 (merged 2026-04-21 from lean-proving-pipeline.md). 4-6h conversion is non-inference; quality validation is inference-gated.
- [x] **NIB2-16**: DAR-3 SPO+ with exploration — [`decision-aware-routing.md`](decision-aware-routing.md) L82-92. ~100 lines in `q_scorer.py` + `retriever.py`; convex surrogate + 10% epsilon-greedy. 3-4 sessions. Code is independent of inference; counterfactual data accumulates downstream. **DONE 2026-04-17**: `_compute_spo_plus_adjustment()` in q_scorer.py (SPO_PLUS_ENABLED flag), epsilon-greedy in HybridRouter.route() (SPO_PLUS_EPSILON env), 7 tests. SPO+ supersedes DAR-2 contrastive when both enabled.
- [x] **NIB2-17**: DAR-4 bilinear scorer — [`decision-aware-routing.md`](decision-aware-routing.md) L97-113. ~200 lines, new `bilinear_scorer.py`. 4-5 sessions. Independent of DAR-3; developable in parallel. **DONE 2026-04-17**: `BilinearScorer` class with Q(prompt,model) = sigmoid(v_m^T W v_p + b). ModelFeatures from ScoringConfig, prompt features from task IR heuristics. Online SGD updates, save/load, zero cold-start. BILINEAR_SCORER_ENABLED flag. 16 tests.
- [ ] **NIB2-18**: DS-6 QuarterScheduler scaffolding — [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) § DS-6. 2-3 days. Design is complete (6 gaps resolved 2026-04-09); code-only implementation while Phase E inference runs later.
- [x] **NIB2-19**: DS-7 stack-template YAML schema + `--stack-profile` CLI — [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) § DS-7. 1-2 days. 4 gaps resolved 2026-04-09; implementation deferred but no blockers. **DONE 2026-04-21** (delta pass): audit confirmed scaffolding already complete 2026-04-11 (`stack_templates.py` 282 LOC + `default.yaml` + `--stack-profile` + `--validate-only`). This pass closed Gap 3 (full-restart migration) and Gap 4 fine-grained budget: added `ResourceBudget` dataclass (max_mlock_gb / max_total_gb / reserve_kv_gb), extended `validate_template()` with 3 new checks, added `src/config/stack_migration.py` (~230 LOC) with 6-phase dry-run-capable migration, wired `--migrate-to <profile>` + `--dry-run` CLI. 10 new tests passing (`tests/unit/test_stack_templates_v2.py`). `default.yaml` now carries explicit `resource_budget:` block. **Out of scope**: diff-based migration (gates on DS-6 QuarterScheduler / NIB2-18).
- [x] **NIB2-20**: Attention Matching layer-adaptive compression — [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md). ~1 day. Layer-adaptive keep_ratio code (early 10×, middle 5×, deep 2×). P2 benchmarks need inference; code itself does not. **DONE 2026-04-17**: `compute_layer_adaptive_weights()` + 3 profiles (conservative/aggressive/balanced) + `compress_slot_adaptive()` in `kv_compress.py`. MODEL_LAYER_COUNTS for all production roles. 8 tests.
- [x] **NIB2-21**: ColBERT reranker module scaffolding — [`colbert-reranker-web-research.md`](colbert-reranker-web-research.md) S5. 2h code + eventually 2h inference A/B. `src/tools/web/colbert_reranker.py`: ONNX session, tokenizer, MaxSim, lazy model loading, feature flag. **DONE 2026-04-17**: `colbert_reranker.py` with lazy ONNX session, per-token encoding, MaxSim scoring, `rerank_snippets()` API with graceful degradation. 11 tests.
- [x] **NIB2-22**: Tool-output-compression P3d harness scaffolding — [`tool-output-compression.md`](tool-output-compression.md) L259. 2-4h. Comparison harness setup is code; A/B execution is inference. **DONE 2026-04-17**: Added `TOOL_DEFINITION_VARIANT` env var (verbose/default/compact) to `builder.py` `_resolve_tools()`. Seeding can A/B test by setting env before run.
- [x] **NIB2-23**: REPL S5 Gap 1 `workspace_scan` combined-op (frecency-only fallback) — [`repl-turn-efficiency.md`](repl-turn-efficiency.md). 4-6h. Frecency-ranked file list + code_search summary. Sub_lm quality validation (Gap 1 full) is blocked on AP-26; frecency-only fallback is not. **DONE 2026-04-17**: Added `_workspace_scan(query, limit)` to `_CombinedOpsMixin`, `top_files()` to FrecencyStore. Query re-ranks by filename relevance. 6 tests.
- [x] **NIB2-24**: REPL S5 Gap 2 `STUCK("reason")` signal — [`repl-turn-efficiency.md`](repl-turn-efficiency.md) L174. 6-8h. In `context.py` alongside `FINAL()`, logs + episodic recall for recovery patterns. **DONE 2026-04-17**: `_stuck(reason)` in `_ContextMixin` — logs to exploration_log, queries _recall() for similar situations, suggests recovery via tool co-occurrence, registered as `STUCK` in REPL globals. 13 tests.
- [x] **NIB2-25**: Context Folding Phase 3c `CompactionQualityMonitor` class — [`context-folding-progressive.md`](context-folding-progressive.md) L645-712. 4-6h. Class + wiring is code; telemetry validation against live traffic is inference-gated. **ALREADY DONE**: `CompactionQualityMonitor` at `session_log.py:562-603` + reference miss detection wired at `session_summary.py:284-309`. Verified 2026-04-17.
- [x] **NIB2-26**: Context Folding Phase 3b `role_aware_compaction` flag + per-role `CompactionProfile` — [`context-folding-progressive.md`](context-folding-progressive.md) L576-643. 1-2 days. Code-only; profile tuning lands later. **ALREADY DONE**: `CompactionProfile` at `session_log.py:498-558` (4 profiles: architect, worker_coder, worker_explore, worker_fast) + wired at `session_summary.py:251-281`. Feature flag `role_aware_compaction` registered. Verified 2026-04-17.
- [x] **NIB2-27**: MathSmith canonicalizer proposal retire/rewrite — [`mathsmith-hc-formalizer-eval.md`](mathsmith-hc-formalizer-eval.md) S5. 2h. Pure docs cleanup. **DONE 2026-04-17**: Retired `MATHSMITH_CANONICALIZER_PROPOSAL.md` (3+ months stale). This handoff is the authoritative doc.

## Infra & governance

- [x] **NIB2-28**: Coverage gate floor raises per Phase B plan — [`integration-test-coverage.md`](integration-test-coverage.md). 1-2h. Policy-only bumps; tests already at the higher floors. **DONE 2026-04-17**: Raised 5 floors to 100% (seeding_infra, executor, registry, output_parser, onboard, seeding_orchestrator). Note: seeding_injection.py has pre-existing regression (53% vs 100% floor).
- [ ] **NIB2-29**: `orchestrator_stack.py` port-doc update for 8080-8084 / 8180-8184 stream split (if NIB2-12 adopted) — [`routing-and-optimization-index.md`](routing-and-optimization-index.md) § P15. <1h.
- [x] **NIB2-30**: GitNexus post-commit hook embeddings-preservation verification — [`CLAUDE.md`](../../CLAUDE.md) § Keeping the Index Fresh. 1h. Verify hook handles `--embeddings` flag correctly. **DONE 2026-04-17**: No PostToolUse hook configured (only PreToolUse hooks exist). `.gitnexus/meta.json` shows `embeddings: 0` — no embeddings to preserve. Issue is moot; `--embeddings` flag only matters when embeddings exist.

---

## Round 2 supplement (added 2026-04-21 — cross-cutting hygiene audit)

Items surfaced by the 2026-04-21 handoff audit that were not in the original Round 2 catalogue. Same reporting protocol as NIB2-01..30.

- [x] **NIB2-31**: SearXNG Docker deploy + `_search_searxng()` implementation — [`searxng-search-backend.md`](searxng-search-backend.md). **Audit 2026-04-21 confirmed SX-1..4 already done 2026-04-14** (Docker + `_search_searxng()` + engine tuning + telemetry). Scoped-down non-inference residual: **DONE 2026-04-21**: `scripts/analysis/searxng_health_report.py` go/no-go analyzer produces PROCEED/HOLD/INSUFFICIENT_DATA verdict with thresholds for bad-query rate, fallback rate, latency ratio. Handoff updated with run instructions. SX-5 load test + SX-6 default swap remain inference-gated via AR-3 Package D Phase 6b.
- [x] **NIB2-32**: Reasoning compression Action 3 shadow-data validation at recalibrated thresholds (0.15/0.35) — [`reasoning-compression.md`](reasoning-compression.md) L93. 1-2d. Log-only analysis: cross-correlate shadow-mode difficulty bands against Package B benchmark accuracy. **PARTIAL 2026-04-21**: Analysis script delivered (`scripts/analysis/difficulty_signal_validation.py`, ~220 LoC, Spearman + verdict). NIB2-35 persistence fix landed same day; script now runs on the new top-level `difficulty_*` fields in `seeding_diagnostics.jsonl`. Needs a fresh benchmark run (n≥100) to produce a live verdict — execute after Package D accumulates trials post-2026-04-21. Report: `progress/2026-04/difficulty-signal-revalidation-2026-04-21.md`.
- [x] **NIB2-35** (added 2026-04-21): Persist `routing_meta.difficulty_*` + `factual_risk_*` to `seeding_diagnostics.jsonl` — prerequisite for NIB2-32 re-validation. ~20 LoC in `scripts/benchmark/seeding_types.py` (RoleResult) + emit site. Pure code, no inference. Discovered while executing NIB2-32. **DONE 2026-04-21**: added `difficulty_score`/`difficulty_band` to `RoleResult` (joining existing `factual_risk_*`); added 4 fields to `ChatResponse` with `_attach_routing_telemetry()` finalizer in `_handle_chat`; extended `build_diagnostic()` + all 4 call sites in `seed_specialist_routing[_v2].py`; analyzer `difficulty_signal_validation.py` prefers the new top-level fields and falls back to legacy progress-log join. 2 new tests + 44 related tests passing.
- [x] **NIB2-34**: Routing Intelligence Phase 4 expanded calibration dataset — [`routing-intelligence.md`](routing-intelligence.md) Phase 3 Design Req 3 + `routing-and-optimization-index.md` P1 RI-1 (supplement). 1-2d. Build labeled prompt set from seeding diagnostic logs + AA-Omniscience 600-q benchmark (intake-381, Apache 2.0). **DONE 2026-04-21**: `scripts/build_factual_risk_calibration_v2.py` produces 2,600-example dataset (v1 2,000 + AA-Omniscience 600 across 6 domains: Finance/Health/Humanities/Law/Sci&Eng/SWE) at `orchestration/factual_risk_calibration_v2.jsonl` with 70/15/15 stratified splits. 4-class labels (CORRECT/INCORRECT/PARTIAL/NOT_ATTEMPTED) + per-prompt `risk_features` from `factual_risk.assess_risk()`. NOT_ATTEMPTED dominates (70%) because AA-Omniscience and v1-tier examples have no inference outcomes yet — will reclassify after next benchmark run. Data size sufficient for n=500/arm target; fresh seeding-diagnostics yielded 0 new entries (all v1 already captured them).

## Round 2 supplement (added 2026-04-22 — deep-dive integration pass)

Items surfaced by the 8 research deep dives landed 2026-04-22 (`/workspace/research/deep-dives/{lighton, qwen35-omni, stop-learnable, diversity-collapse, onevl, agent-world, minddr, intake-trio}.md`). Each entry maps to a specific deep-dive action item and a target handoff.

- [ ] **NIB2-40**: Compaction-pipeline gap analysis — map Claude Code's 5-layer pipeline (budget-reduction → snip → microcompact → context-collapse → auto-compact, intake-426) against EPYC L1-L5. 4h design task; outcome = decision on per-message output-size caps. → [`context-folding-progressive.md`](context-folding-progressive.md) Phase 2c addendum + DD8 reference.
- [ ] **NIB2-41**: MDL distillation + staleness-detection mutation primitives for StructuralLab (from intake-414 Token Savior). 2d design + 1d integration into `program.md` search space. Candidate new mutation types. → [`meta-harness-optimization.md`](meta-harness-optimization.md) Tier 2b refinement.
- [ ] **NIB2-42**: Diversity metrics in `EvalResult` + baseline pass on 4 production roles (DD4, intake-441). ~6-8h code + 4-5h inference. Add `diversity_entropy`/`diversity_distinct2`/`diversity_self_bleu`/`diversity_ttr` + `diversity_semantic_embedding_agreement` fields. Implement Verbalized Sampling recovery probe (arXiv:2510.01171) as part of baseline. Populate `autopilot_baseline.yaml`. **Amended 2026-04-22 post Tier 2b**: SafetyGate uses two-tier multi-signal gate (Tier 1 WARN / Tier 2 REJECT on distinct-2 drop >20% AND semantic-embedding-agreement drop >10% AND quality not up AND VS recovery <50%). Warn-only until VS replicated on Qwen3-30B-A3B. → [`eval-tower-verification.md`](eval-tower-verification.md) EV-8 (amended).
- [ ] **NIB2-43**: OneVL dual-objective α-sweep probe (training-free; DD5, intake-443). ~3-5h inference. Score existing summarizer outputs with α·helpfulness + (1-α)·task-success; α ∈ {0.0, 0.25, 0.5, 0.75, 1.0}. Gate: if α<1.0 outperforms α=1.0 by >2%, promote to Phase 2b design variant. → [`context-folding-progressive.md`](context-folding-progressive.md) Phase 2c addendum.
- [ ] **NIB2-44**: Agent-World `env_synth/` module scaffold (DD6, intake-444). 3-4w code; training-free. Sub-module: etd_agent / task_synthesizer / verifier_builder / mcp_tool_registry. Wires into autopilot as 5th species. → [`agent-world-env-synthesis.md`](agent-world-env-synthesis.md) AW-1..AW-6.
- [ ] **NIB2-45**: MindDR Phase 1 `deep_research_mode` scaffold (DD7, intake-438). ~3w code + sentinel suite. Feature flag + classifier extension + 3 agent prompts + pydantic_graph nodes + sentinel suite. → [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md) MD-1..MD-9.
- [ ] **NIB2-46**: STOP Phase 0 instrumentation in llama.cpp (DD3, intake-437). ~1d code; non-inference (hook-level). Reserve unused token, add orchestrator hook for hidden-state fetch at prefix position. **Gated on NIB2-32** difficulty-signal re-validation producing a live verdict. → [`reasoning-compression.md`](reasoning-compression.md) Action 10a.
- [x] **NIB2-47**: ONNX INT8 export of LateOn + parity test vs PyLate (DD1-A1, intake-428/430/431). ~1h. Non-inference. Prerequisite for S3b latency benchmark. → [`colbert-reranker-web-research.md`](colbert-reranker-web-research.md) S3b. **DONE 2026-04-22 (code)**: `scripts/benchmark/colbert/export_lateon_onnx_int8.py` downloads pre-quantized `lightonai/LateOn` ONNX INT8 (shipped on HF) + runs 20-snippet parity vs PyLate reference with tolerance 1e-2. `src/tools/web/colbert_reranker.py` extended with `LATEON_MODEL_PATH` env var override. pyproject extras `[colbert-export]` group added. 13/13 colbert tests passing (+2 new). Execution deferred until orchestrator `.venv` receives the colbert-export extras.
- [x] **NIB2-48**: Update intake-432 verdict to `reference_only` + mark intakes 435/436/440 with explicit `trigger_to_reactivate` fields (DD2/DD8). ~30min. Pure metadata fix. → `research/intake_index.yaml`. **DONE 2026-04-22**: Audit showed 435/436/440 already had `trigger_to_reactivate` from the 2026-04-22 intake-trio deep-dive pass; only intake-432 verdict flip (`not_applicable` → `reference_only`, L16854) needed.

---

## Items explicitly excluded (blocked or inference-required)

These are *non-inference in nature* but gated on external signals. Listed so the gate is visible, not to pick up:

- `readme-refresh.md` — GATED on AR-3 trial ≥100 (currently ~78). Pick up when autopilot journal hits 100 trials.
- `root-archetype-linter-templates-upstream.md` — Gated on local clone of the `root-archetype` repo.
- DAR-3/DAR-4 validation passes — code is NIB2-16/17; measurement is inference.
- REPL S4 A/B — A/B itself is inference; scaffolding (not listed here) would be ~4h code.
- Qwen3.6 benchmark — [`qwen36-production-upgrade.md`](qwen36-production-upgrade.md) — inference-gated. Download already done.
- Package D post-AR-3 analyses — blocked on AR-3 completion.
- **NIB2-33 (retired 2026-04-21)**: Hermes outer shell auth — `hermes-outer-shell.md` L242 explicitly defers auth until a multi-user use case materializes ("No auth on any endpoint… Not implementing until there's a concrete multi-user use case"). Revisit when a second human user or a multi-tenant scenario is in sight.
- MathSmith S2 HC benchmark + S3 drafter spec decode tests — inference-gated.

---

## Reporting protocol

When you complete an NIB2-NN item:
1. Check the box here.
2. Update the linked canonical handoff's TODO / next-steps section to match.
3. Add a one-line entry in `progress/YYYY-MM/YYYY-MM-DD.md`.
4. If the item belonged to a phased handoff (e.g. "Phase 2c ByteRover enhancement"), bump that handoff's status line.
5. On completing all 43 items: move this file to `completed/` as Round 2, and run a fresh audit to open Round 3.

---

## Dependency & priority graph

```
HIGHEST LEVERAGE (do first):
├── NIB2-01 (_batch_llm_query)          → unblocks REPL efficiency wins
├── NIB2-12 (parallel seeding)           → 2× AR-3 throughput
├── NIB2-09 (</think> investigation)    → unblocks Qwen3.5 hybrid budget control
└── NIB2-06 (vision tool register)      → proactive vision delegation

CODE THAT WILL PAY OFF WHEN INFERENCE RUNS:
├── NIB2-13/14 (OpenDataLoader swap + bench)
├── NIB2-16/17 (DAR-3/DAR-4)
├── NIB2-18/19 (DS-6/DS-7)
├── NIB2-20 (AM layer-adaptive)
├── NIB2-25/26 (CF Phase 3b/3c)
└── NIB2-21/22 (ColBERT + tool-output harness scaffolding)

CLEAN-UP / LOW-EFFORT:
├── NIB2-04 (DAR-2 unit test)
├── NIB2-07 (retrain-routing archive move, 5min)
├── NIB2-27 (canonicalizer doc)
├── NIB2-28/29/30 (infra)
└── NIB2-05 (top-k instrumentation)
```

---

## Cross-references

Canonical sources (always verify status in these files first):
- [`routing-and-optimization-index.md`](routing-and-optimization-index.md) — DAR, RI, AP, DS series
- [`research-evaluation-index.md`](research-evaluation-index.md) — EV, REPL, CF, TOC series
- [`inference-acceleration-index.md`](inference-acceleration-index.md) — AM, triattention, KV series
- [`pipeline-integration-index.md`](pipeline-integration-index.md) — vision, ODL, Lean, TTS series
- [`hermes-agent-index.md`](hermes-agent-index.md) — B-series (Hermes outer shell, P2)
- [`master-handoff-index.md`](master-handoff-index.md) — cross-domain priorities
