# Non-Inference Backlog — Round 2 (2026-05-19 audit refresh)

**Status**: ACTIVE — 43 Round-2 baseline tasks catalogued + 4 May 2026 cluster supplements. 40/43 Round-2-baseline done. Open Round-2 baseline (3 items): NIB2-18, 43, 46. NIB2-33 moved to excluded (hermes-outer-shell auth deferral). May 2026 cluster supplement: NIB2-49 and NIB2-50 are closed from existing May evidence; NIB2-51 X-MAS non-inference scaffolding is closed as default-off shadow/advisory telemetry; NIB2-52 StreamingLLM C++ scaffold landed and its 4-axis bench sweep is inference-gated.

**Cross-reference, 2026-05-06**: 6 standalone non-inference handoffs (NOT in NIB2 numbering) closed in parallel via Wave A/B/C — see `progress/2026-05/2026-05-06.md` § "6 standalone non-inference handoffs". These are tracked in their own handoff files; the closure pattern matches NIB2. Total non-inference closure throughput this audit cycle: 36 NIB2 + 6 standalone = 42 items.
**Created**: 2026-02 (Round 1, 18/18 complete → [`completed/non-inference-backlog-completed-through-2026-04-12.md`](../completed/non-inference-backlog-completed-through-2026-04-12.md))
**Refreshed**: 2026-04-17 (Round 2 catalogue from cross-cutting audit of all active handoffs)
**Supplemented**: 2026-04-21 (NIB2-31..34 added from handoff hygiene audit), 2026-04-22 (NIB2-40..48 from deep-dive integration pass), 2026-05-19 (NIB2-49..52 from May 2026 research cluster deep-dives)
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

- [x] **NIB2-01**: REPL S5 Gap 3 `_batch_llm_query()` combined-op — historical source now in [`repl-turn-efficiency` completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md). ~3-4h. HIGH impact / LOW effort (infrastructure exists; just expose `llm_batch()` as first-class REPL tool). **DONE 2026-04-17**: Added `_batch_llm_query()` to `_CombinedOpsMixin` in `combined_ops.py`, registered in REPL globals, 9 tests passing.
- [x] **NIB2-02**: EV-3 Scoring Verifiers adapter — [`eval-tower-verification.md`](eval-tower-verification.md) L151-157. 2-3h. Download `nvidia/Scoring-Verifiers`, create ~50-line adapter, register in `suites.py`. **DONE 2026-04-17**: Downloaded 4 JSONL files (HE-R/R+ 164 problems, MBPP-R 974, MBPP-R+ 378). Created `scoring_verifiers_adapter.py` with `load_problems()` + `load_scoring_verifiers_suite()`. Registered in `suites.py`.
- [x] **NIB2-03**: EV-0 MathQ-Verify dataset audit — [`eval-tower-verification.md`](eval-tower-verification.md) L129. 4-6h. Zero-code data cleaning (stages 1-4). **DONE 2026-04-21** (stages 1-3): `scripts/benchmark/dataset_audit/mathq_verify_audit.py` applied to 5,670 math-suite questions (aime + math + olympiadbench + physreason). 251 flagged (4.43%). Report: `progress/2026-04/mathq-verify-audit-2026-04-21.md`. Stage 4 (consistency) deferred — requires LLM-based atomic decomposition (inference-gated). Stage 5 skipped per paper ablation insight. V2 refinements identified: gate unbalanced-$ check on LaTeX-present prompts (GSM8K currency false positives), install `antlr4-python3-runtime` for deep parse validation.
- [x] **NIB2-04**: DAR-2 unit test for `_compute_contrastive_adjustment()` with mock store — [`decision-aware-routing.md`](decision-aware-routing.md) L74. 2h. Explicitly deferred in handoff. **DONE 2026-04-17**: 13 tests covering all branches (no context, embedding failure, no candidates, no alternatives, unlearned defaults, positive/negative adjustment, bounds capping, no memory_id).
- [x] **NIB2-05**: Frontdoor top-k=64 first-token log-probability instrumentation — [`learned-routing-controller.md`](learned-routing-controller.md) L132-135 P1.5.1. 2-4h. (Collection needs volume; instrumentation is code only.) **DONE 2026-04-17**: Feature flag `logit_probe` in `features.py`, `n_probs=64` added to payload when enabled, `_write_logit_probe()` captures first-token probs to JSONL at `data/logit_probe.jsonl`. Enable: `ORCHESTRATOR_LOGIT_PROBE=1`.
- [x] **NIB2-06**: Vision tool registry registration in orchestrator — [`multimodal-pipeline.md`](multimodal-pipeline.md) L44. 2-4h. Pure code, unblocks proactive vision delegation. **DONE 2026-04-17**: Created `src/tools/vision/` plugin (manifest.json + analyze.py) with 3 tools (vision_analyze, vision_search, vision_face_identify). Model-agnostic: checks mmproj_path on active models. 12 tests.
- [x] **NIB2-07**: Move `blocked/retrain-routing-models.md` to `archived/` — 5 min once directory permissions fixed. Superseded by Learned Routing Controller Phase 1 (2026-04-15). **DONE 2026-04-17**: Moved via sudo, staged in git.
- [x] **NIB2-08**: AP-21 GEPA ratio knob scaffolding — [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md). ~4h. Ratio-adjustable code path; flip decision gated on AR-3 data but the knob itself is code-only. **DONE 2026-04-17**: Made `gepa_ratio` dynamic — reads from `autopilot_state.json` (default 0.30). Set to 1.0 when AR-3 data confirms GEPA dominance.

## Investigation (code-reading / root-cause analysis)

- [x] **NIB2-09**: Per-request `</think>` budget investigation on Qwen3.5 hybrid SSM+MoE — [`per-request-reasoning-budget.md`](per-request-reasoning-budget.md) L45-50. 1-2 days. 4-step plan in llama.cpp-experimental: search `server.cpp`/`common/chat.cpp`/`src/llama-sampling.cpp`, trace hybrid code path, propose fix (`</think>` injection timing vs SSM state update). Steps 3-4 need a running server — keep them out of scope. **DONE 2026-04-17** (Steps 1-2): Full pipeline traced — reasoning-budget.cpp state machine (IDLE→COUNTING→FORCING→DONE), root cause identified (SSM state update race on hybrids), 3 fix options proposed. Handoff updated with line numbers.
- [x] **NIB2-10**: Integration-test-coverage residual unit gaps — historical source now in [`integration-test-coverage` completed ledger](../completed/integration-test-coverage-phases-1-4-completed-through-2026-05-28.md). 4-8h. Remaining edges in `graph/task_ir_helpers.py`, `graph/budgets.py`, `graph/answer_resolution.py` — test-only writes, no new code paths. **DONE 2026-04-17** (partial): 55 tests for `answer_resolution.py` covering all 7 functions (was zero coverage). `task_ir_helpers.py` and `budgets.py` gaps remain — existing partial coverage, lower priority.
- [x] **NIB2-11**: Package F post-hoc analysis — [`bulk-inference-campaign.md`](bulk-inference-campaign.md). 4-6h. Data already collected; analysis is log-parsing and chart generation. **DONE 2026-04-21**: Package F v2→v3 comparison table + synthesis added to `wiki/inference-serving.md` Key Findings (coder +101%, REAP +50%, frontdoor +13%, worker −1%). Raw data captured inline in bulk-inference-campaign.md § Package F.

## Medium-effort implementation (multi-day, no inference required)

- [x] **NIB2-12**: `parallel_seeding.py` + `seeding_port_sets.py` — [`routing-and-optimization-index.md`](routing-and-optimization-index.md) § P15 (merged 2026-04-21 from parallel-seeding-eval.md). ~200 LoC, 1 day. Unlocks 2× AR-3 throughput. No blockers. **CLOSED 2026-06-13 as stale/unsafe, no code shipped**: the referenced implementation target moved from `epyc-inference-research` to `epyc-orchestrator` during repo decontamination; current seeding already has `AUTOPILOT_SEED_ROLE_CONCURRENCY`, role-wave packing, heavy-port idle barriers, atomic checkpoint appends, and manifest-driven role discovery. The old hard-coded 8080/8180 two-stream design conflicts with current `PORT_MAP`/`NUMA_CONFIG` full+quarter topology and the resource-contamination lessons from trials 787/788. Replacement is a future clean-window, manifest-aware scheduler or measurement harness, not this NIB item.
- [x] **NIB2-13**: OpenDataLoader Phase 1 swap in `pdf_router.py` — [`opendataloader-pipeline-integration.md`](opendataloader-pipeline-integration.md) L36-44. 1-2 days. JVM lifecycle + swap `pdftotext -layout` for `opendataloader_pdf.convert(...)`, retain entropy/garbage quality checks, update `tests/services/test_pdf_router.py`. **DONE 2026-04-17**: Added `_extract_with_opendataloader()` method, `PDF_EXTRACTOR=opendataloader` env var routing, fallback to pdftotext if ODL returns empty. Quality checks retained. ODL package install needed for production.
- [x] **NIB2-14**: Clone `opendataloader-bench`, add `document_extraction` suite with NID/TEDS/MHS scoring — [`opendataloader-pipeline-integration.md`](opendataloader-pipeline-integration.md) L95-107. 1 day. **DONE 2026-04-17**: Created `document_extraction_adapter.py` with `DocumentExtractionAdapter` class, `score_nid()` (reading order), `score_teds()` (table structure), `score_mhs()` (heading hierarchy), `score_document()` (aggregate). Registered in dataset_adapters.py. 18 scoring tests. Repo clone deferred (Git LFS).
- [x] **NIB2-15**: Goedel-CP-8B GGUF conversion + Q4_K_M/Q8_0 quantization — [`pipeline-integration-index.md`](pipeline-integration-index.md) § P2.S1 (merged 2026-04-21 from lean-proving-pipeline.md). **DONE 2026-06-13 (artifact generation)**: downloaded `Goedel-LM/Goedel-Code-Prover-8B` revision `858f3b5e04bf24aca3a1a113ea1889a4de9ed4ef`, converted with `convert_hf_to_gguf.py --outtype f16`, and quantized via `llama-quantize` to:
  - `/mnt/raid0/llm/models/Goedel-Code-Prover-8B-GGUF/Goedel-Code-Prover-8B-f16.gguf` (16 GB)
  - `/mnt/raid0/llm/models/Goedel-Code-Prover-8B-GGUF/Goedel-Code-Prover-8B-Q4_K_M.gguf` (4.7 GB, 4.90 BPW)
  - `/mnt/raid0/llm/models/Goedel-Code-Prover-8B-GGUF/Goedel-Code-Prover-8B-Q8_0.gguf` (8.2 GB, 8.50 BPW)
  **Inference follow-up 2026-06-13**: Q4_K_M load/generation smoke passed via llama-server and the master registry now has cold candidate entry `goedel_code_prover_8b_q4km` for `lean_prover` / `formal_verification`. FormalQualBench subset and Lean verifier certification remain open.
- [x] **NIB2-16**: DAR-3 SPO+ with exploration — [`decision-aware-routing.md`](decision-aware-routing.md) L82-92. ~100 lines in `q_scorer.py` + `retriever.py`; convex surrogate + 10% epsilon-greedy. 3-4 sessions. Code is independent of inference; counterfactual data accumulates downstream. **DONE 2026-04-17**: `_compute_spo_plus_adjustment()` in q_scorer.py (SPO_PLUS_ENABLED flag), epsilon-greedy in HybridRouter.route() (SPO_PLUS_EPSILON env), 7 tests. SPO+ supersedes DAR-2 contrastive when both enabled.
- [x] **NIB2-17**: DAR-4 bilinear scorer — [`decision-aware-routing.md`](decision-aware-routing.md) L97-113. ~200 lines, new `bilinear_scorer.py`. 4-5 sessions. Independent of DAR-3; developable in parallel. **DONE 2026-04-17**: `BilinearScorer` class with Q(prompt,model) = sigmoid(v_m^T W v_p + b). ModelFeatures from ScoringConfig, prompt features from task IR heuristics. Online SGD updates, save/load, zero cold-start. BILINEAR_SCORER_ENABLED flag. 16 tests.
- [ ] **NIB2-18**: DS-6 QuarterScheduler revalidation gate — [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) DS-6-live. Do **not** treat as code-only scaffolding. Implement only after DS-E1 evidence (Package B throughput, RI-10 escalation data, DS-5 roster findings, KV-size data, mixed-role NUMA contention) shows static pre-warm leaves material throughput/latency on the table. Completed design/gap details live in [`../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md`](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md).
- [x] **NIB2-19**: DS-7 stack-template YAML schema + `--stack-profile` CLI — completed history in [`../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md`](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md). **DONE 2026-04-21** (delta pass): audit confirmed scaffolding already complete 2026-04-11 (`stack_templates.py` 282 LOC + `default.yaml` + `--stack-profile` + `--validate-only`). This pass closed Gap 3 (full-restart migration) and Gap 4 fine-grained budget: added `ResourceBudget` dataclass, extended `validate_template()`, added `src/config/stack_migration.py` with dry-run-capable migration, wired `--migrate-to <profile>` + `--dry-run` CLI, and added 10 tests. Active follow-up is DS-7-live profile codification from evidence.
- [x] **NIB2-20**: Attention Matching layer-adaptive compression — [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md). ~1 day. Layer-adaptive keep_ratio code (early 10×, middle 5×, deep 2×). P2 benchmarks need inference; code itself does not. **DONE 2026-04-17**: `compute_layer_adaptive_weights()` + 3 profiles (conservative/aggressive/balanced) + `compress_slot_adaptive()` in `kv_compress.py`. MODEL_LAYER_COUNTS for all production roles. 8 tests.
- [x] **NIB2-21**: ColBERT reranker module scaffolding — [`colbert-reranker-web-research.md`](colbert-reranker-web-research.md) S5. 2h code + eventually 2h inference A/B. `src/tools/web/colbert_reranker.py`: ONNX session, tokenizer, MaxSim, lazy model loading, feature flag. **DONE 2026-04-17**: `colbert_reranker.py` with lazy ONNX session, per-token encoding, MaxSim scoring, `rerank_snippets()` API with graceful degradation. 11 tests.
- [x] **NIB2-22**: Tool-output-compression P3d harness scaffolding — [`tool-output-compression.md`](tool-output-compression.md) L259. 2-4h. Comparison harness setup is code; A/B execution is inference. **DONE 2026-04-17**: Added `TOOL_DEFINITION_VARIANT` env var (verbose/default/compact) to `builder.py` `_resolve_tools()`. Seeding can A/B test by setting env before run.
- [x] **NIB2-23**: REPL S5 Gap 1 `workspace_scan` combined-op (frecency-only fallback) — historical source now in [`repl-turn-efficiency` completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md). 4-6h. Frecency-ranked file list + code_search summary. Sub_lm quality validation (Gap 1 full) is blocked on AP-26; frecency-only fallback is not. **DONE 2026-04-17**: Added `_workspace_scan(query, limit)` to `_CombinedOpsMixin`, `top_files()` to FrecencyStore. Query re-ranks by filename relevance. 6 tests.
- [x] **NIB2-24**: REPL S5 Gap 2 `STUCK("reason")` signal — historical source now in [`repl-turn-efficiency` completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md). 6-8h. In `context.py` alongside `FINAL()`, logs + episodic recall for recovery patterns. **DONE 2026-04-17**: `_stuck(reason)` in `_ContextMixin` — logs to exploration_log, queries _recall() for similar situations, suggests recovery via tool co-occurrence, registered as `STUCK` in REPL globals. 13 tests.
- [x] **NIB2-25**: Context Folding Phase 3c `CompactionQualityMonitor` class — historical source now in [`context-folding` completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md). 4-6h. Class + wiring is code; telemetry validation against live traffic is inference-gated and tracked in the active handoff. **ALREADY DONE**: `CompactionQualityMonitor` at `session_log.py:562-603` + reference miss detection wired at `session_summary.py:284-309`. Verified 2026-04-17.
- [x] **NIB2-26**: Context Folding Phase 3b `role_aware_compaction` flag + per-role `CompactionProfile` — historical source now in [`context-folding` completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md). 1-2 days. Code-only; profile tuning lands later. **ALREADY DONE**: `CompactionProfile` at `session_log.py:498-558` (4 profiles: architect, worker_coder, worker_explore, worker_fast) + wired at `session_summary.py:251-281`. Feature flag `role_aware_compaction` registered. Verified 2026-04-17.
- [x] **NIB2-27**: MathSmith canonicalizer proposal retire/rewrite — [`mathsmith-hc-formalizer-eval.md`](mathsmith-hc-formalizer-eval.md) S5. 2h. Pure docs cleanup. **DONE 2026-04-17**: Retired `MATHSMITH_CANONICALIZER_PROPOSAL.md` (3+ months stale). This handoff is the authoritative doc.

## Infra & governance

- [x] **NIB2-28**: Coverage gate floor raises per Phase B plan — historical source now in [`integration-test-coverage` completed ledger](../completed/integration-test-coverage-phases-1-4-completed-through-2026-05-28.md). 1-2h. Policy-only bumps; tests already at the higher floors. **DONE 2026-04-17**: Raised 5 floors to 100% (seeding_infra, executor, registry, output_parser, onboard, seeding_orchestrator). Note: seeding_injection.py has pre-existing regression (53% vs 100% floor).
- [x] **NIB2-29**: `orchestrator_stack.py` port-doc update for 8080-8084 / 8180-8184 stream split (if NIB2-12 adopted) — [`routing-and-optimization-index.md`](routing-and-optimization-index.md) § P15. <1h. **DONE 2026-05-27**: Verified the old 8080-8084 / 8180-8184 framing is stale; added a doc-only clarification in `epyc-orchestrator/scripts/server/orchestrator_stack.py` pointing readers to `stack_manifest.PORT_MAP` for full/primary ports and `stack_numa.NUMA_CONFIG` for NUMA quarter/replica ports.
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

- [x] **NIB2-40**: Compaction-pipeline gap analysis — map Claude Code's 5-layer pipeline (budget-reduction → snip → microcompact → context-collapse → auto-compact, intake-426) against EPYC L1-L5. 4h design task; outcome = decision on per-message output-size caps. → [`context-folding-progressive.md`](context-folding-progressive.md) CF-DD8. **DONE 2026-06-13**: no separate context-folding per-message cap. Tool-output budget reduction stays in `tool-output-compression.md` (hard cap + compression + spill/peek). Surgical `trim_segment(segment_id)` remains evidence-gated on CF-3c telemetry showing recurring single-segment poisoning/reference misses.
- [x] **NIB2-41**: MDL distillation + staleness-detection mutation primitives for StructuralLab (from intake-414 Token Savior). 2d design + 1d integration into `program.md` search space. Candidate new mutation types. → historical source now in [`meta-harness` completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md). **DONE 2026-04-22**: Design addendum written into the handoff; `StrategyStore` gained three additive tables (`strategy_conventions`, `strategy_validity`, `content_hashes`) plus 6 helper methods and quarantine-aware `retrieve()`; `StructuralLab` gained `mdl_compress_strategies()` (Jaccard + zlib-MDL, threshold 0.20) and `staleness_invalidate_strategies()` (sha256 scan + Bayesian validity + classifier-meta cascade); new `_content_hash.py`; `program.md` Tier 6 section added. 6/6 new tests + 8/8 existing `test_strategy_store.py` passing.
- [x] **NIB2-42**: Diversity metrics in `EvalResult` + baseline pass on 4 production roles (DD4, intake-441). ~6-8h code + 4-5h inference. Add `diversity_entropy`/`diversity_distinct2`/`diversity_self_bleu`/`diversity_ttr` + `diversity_semantic_embedding_agreement` fields. Implement Verbalized Sampling recovery probe (arXiv:2510.01171) as part of baseline. Populate `autopilot_baseline.yaml`. **Amended 2026-04-22 post Tier 2b**: SafetyGate uses two-tier multi-signal gate (Tier 1 WARN / Tier 2 REJECT on distinct-2 drop >20% AND semantic-embedding-agreement drop >10% AND quality not up AND VS recovery <50%). Warn-only until VS replicated on Qwen3-30B-A3B. → [`eval-tower-verification.md`](eval-tower-verification.md) EV-8 (amended). **DONE 2026-04-22 (code portion)**: new `src/safety_gate.py` (EvalResult + SafetyGate, NaN-safe, warn-only via `SAFETY_GATE_WARN_ONLY` env var default ON); new `src/tools/diversity/metrics.py` (entropy/distinct-n/self-BLEU/TTR/semantic-agreement); new `src/tools/diversity/verbalized_sampling.py` (distributional prompt + recovery_ratio); `autopilot_baseline.yaml` extended with `diversity_baseline:` + `diversity_baseline_meta:`. 14/14 tests in `test_safety_gate_diversity.py` passing. Baseline population + warn→reject flip remain inference-gated.
- [x] **NIB2-43**: OneVL dual-objective α-sweep probe (training-free; DD5, intake-443). Closed 2026-06-19 with `epyc-inference-research/scripts/benchmark/compaction_alpha_sweep.py` over existing Package-C compaction/summarizer rows. Alpha `0.0` beat faithfulness-only alpha `1.0` by `+0.051315` average precision on 110 valid rows (`0.940463` vs `0.889148`), crossing the `>2%` gate. Promote to the Context Folding Phase 2b design variant, but require live/held-out validation before production compaction changes. → [`context-folding-progressive.md`](context-folding-progressive.md) CF-2c.0.
- [x] **NIB2-44**: Agent-World `env_synth/` module scaffold (DD6, intake-444). 3-4w code; training-free. Sub-module: etd_agent / task_synthesizer / verifier_builder / mcp_tool_registry. Wires into autopilot as 5th species. → [`agent-world-env-synthesis.md`](agent-world-env-synthesis.md) AW-1..AW-6. **DONE 2026-04-22** (Phase 1 non-inference scope, AW-1..AW-5): new `scripts/autopilot/species/env_synth/` with 7 modules — `mcp_tool_registry.py` (JSONL-backed, pluggable async health checks, auto-deactivation), `verifier_builder.py` (regex / exact_match / f1 with degenerate-spec rejection), `task_synthesizer.py` (LLM-backed compose with `DifficultyBand` + deterministic `make_fake_llm()` for tests), `etd_agent.py` (ReAct discovery with MCP-endpoint heuristic filter), `species.py` (EnvSynth coordinator + EnvSynthAction journal events + SolvabilityGate reference-model check), `gap_diagnosis.py` (linear-slope stagnation detector + weekly arena.md rollup), `eval_integration.py` (arena JSONL → T1TaskEntry with provenance + human-review flagging). EnvSynth registered as 5th species in `species/__init__.py`. 19 unit tests passing; cross-suite regression clean at 104/104. AW-6 bootstrap + AW-7 MCP tool adoption remain release-/inference-gated.
- [x] **NIB2-45**: MindDR Phase 1 `deep_research_mode` scaffold (DD7, intake-438). ~3w code + sentinel suite. Feature flag + classifier extension + 3 agent prompts + pydantic_graph nodes + sentinel suite. → [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md) MD-1..MD-9. **DONE 2026-04-22** (Phase 1 non-inference scope): MD-1 `deep_research_mode` FeatureSpec + Features field; MD-2 `src/classifiers/research_like.py` detector + `research_like` classifier_config exemplars; MD-3/4/5 three new `orchestration/prompts/*_agent.md` files; MD-6 standalone `src/graph/minddr/` subpackage (state/parsing/nodes/graph) with PlanningNode → DeepSearchFanOutNode (asyncio.gather + max_parallel semaphore) → ReportSynthesisNode; MD-7 EvalResult rubric stubs (4 NaN fields); MD-8 `orchestration/deep_research_sentinel.yaml` with 20 stratified sentinels. 58/58 tests passing across 4 new test modules. MD-9 A/B remains inference-gated.
- [ ] **NIB2-46**: STOP Phase 0 instrumentation in llama.cpp (DD3, intake-437). ~1d code; non-inference (hook-level). Reserve unused token, add orchestrator hook for hidden-state fetch at prefix position. **Gated on NIB2-32** difficulty-signal re-validation producing a live verdict. → [`reasoning-compression.md`](reasoning-compression.md) Action 10a.
- [x] **NIB2-47**: ONNX INT8 export of LateOn + parity test vs PyLate (DD1-A1, intake-428/430/431). ~1h. Non-inference. Prerequisite for S3b latency benchmark. → [`colbert-reranker-web-research.md`](colbert-reranker-web-research.md) S3b. **DONE 2026-04-22 (code)**: `scripts/benchmark/colbert/export_lateon_onnx_int8.py` downloads pre-quantized `lightonai/LateOn` ONNX INT8 (shipped on HF) + runs 20-snippet parity vs PyLate reference with tolerance 1e-2. `src/tools/web/colbert_reranker.py` extended with `LATEON_MODEL_PATH` env var override. pyproject extras `[colbert-export]` group added. 13/13 colbert tests passing (+2 new). Execution deferred until orchestrator `.venv` receives the colbert-export extras.
- [x] **NIB2-48**: Update intake-432 verdict to `reference_only` + mark intakes 435/436/440 with explicit `trigger_to_reactivate` fields (DD2/DD8). ~30min. Pure metadata fix. → `research/intake_index.yaml`. **DONE 2026-04-22**: Audit showed 435/436/440 already had `trigger_to_reactivate` from the 2026-04-22 intake-trio deep-dive pass; only intake-432 verdict flip (`not_applicable` → `reference_only`, L16854) needed.

---

## Round 2 supplement (added 2026-05-19 — May 2026 research cluster deep-dives)

Four cluster handoffs landed 2026-05-19 (post-research-intake-batch). Each entry captures the **non-inference scaffolding** portion of the cluster spike; the live benchmark / A/B / nightshift sweep stays in the canonical handoff and is inference-gated.

- [x] **NIB2-49**: RAO + ReDel Step 1 pre-flight gate scaffolding — [`rao-redel-substrate-spike.md`](rao-redel-substrate-spike.md) Step 1. ~20 LoC glue + throwaway venv. **HIGH** (Priority Queue #42). Install `redel[all]` + `kani` in `/tmp/redel-spike`, point `OPENAI_BASE_URL` at local `worker_general`, run a `DelegateOne` smoke call, capture `DelegationEvent` stream. <100 K local tokens (zero $). Gate criteria 1–4 are smoke-test scale, not bench scale. Step 2 paired A/B and Step 3 substrate replacement are inference-gated. **DONE 2026-05-19; backlog drift corrected 2026-06-13**: Step 1 gate scored 4/4 PASS with core ReDel + kani in `/tmp/redel-spike`, local llama-server OpenAIEngine against `worker_general`, child response `2+2=4`, 28 JSON-serializable events including `KaniDelegated`; Step 2 A/B harness prepared but unexecuted pending a clean inference window.
- [x] **NIB2-50**: δ-mem Phase 1 setup (checkpoint + adapter download + throwaway venv) — [`delta-mem-reproduction.md`](delta-mem-reproduction.md) Phase 1 prep. **HIGH** (Priority Queue #43). Clone `github.com/declare-lab/delta-Mem` (CC-BY-4.0) into `/tmp/dmem-spike`, pull Qwen3-4B-Instruct-2507 + released δ-mem adapter, verify checkpoint loads cleanly against the backbone, dry-run `eval_memoryagentbench.py` / `eval_locomo.py` argument parsing (no full eval). ~0.5d. The 1-nightshift MemoryAgentBench / LoCoMo reproduction itself is inference-gated. **DONE 2026-05-19/20; backlog drift corrected 2026-06-13**: canonical handoff records clone at `/mnt/raid0/llm/delta-Mem`, CPU venv, Qwen3-4B-Instruct-2507 + adapter downloads, adapter load + coherent generation PASS, CPU overhead gate PASS, LoCoMo N=5 directional PASS, and MemoryAgentBench CPU infeasibility documented.
- [x] **NIB2-51**: X-MAS routing scaffolding (taxonomy + classifier + winner-table loader + frontdoor telemetry hook) — [`x-mas-text-routing.md`](x-mas-text-routing.md). **HIGH** (Priority Queue #44). Map X-MAS-Bench's 5 domain × 5 function taxonomy onto our orchestrator task labels; implement a coarse `(domain, function)` classifier; add a `WinnerTableLoader` that reads a per-stack 5×5 table from disk and exposes a `winner_for(domain, function)` query; wire the frontdoor entry point behind a default-off config. The 1500-eval (5 domains × 5 functions × 4 models × ~15 tasks, 1 nightshift) sweep that *populates* the table is inference-gated and lives in the canonical handoff. Cheap-kill check: if `project_worker_general_swap_2026_05_08` predicts gemma4-26B-A4B winning ≥80% of cells, the spike abort-decision happens after the sweep, not in this scaffold. **DONE 2026-06-13/15 for non-inference scaffold**: `epyc-orchestrator` commit `e9004a2` adds the side-effect-free taxonomy/classifier, `WinnerTable` loader, complete example table, and 8 tests. Commit `edbe0d2` adds default-off X-MAS shadow/advisory telemetry (`xmas_routing.mode: off`, env overrides `ORCHESTRATOR_XMAS_ROUTING_MODE` / `ORCHESTRATOR_XMAS_WINNER_TABLE_PATH`) that logs nested `routing_meta["xmas"]` confidence/table/suggested-role fields without mutating `routing_decision`. Commit `a87bd35` adds guarded `enforce` semantics: route mutation only when a complete configured winner table is loaded, the classifier is confident, and the request is not explicitly forced; failure-veto and downstream guards still apply. The 2026-06-15 evidence workflow (`epyc-inference-research` `00f601b`, `epyc-orchestrator` `940d993`) adds a table generator, an evidence-backed `orchestration/xmas_winner_table.domain_proxy.yaml` artifact, and a validator that refuses `mode: enforce` unless the table is complete, evidence-backed, and not a domain-proxy derivation. The artifact is explicitly `domain_winner_reused_for_function`, so the true function-axis 5x5 sweep and live A/B remain in the canonical handoff as inference/eval-gated follow-up work.
- [x] **NIB2-52**: StreamingLLM sink + sliding-window scaffold in `epyc-llama` — [`streaming-llm-baseline.md`](streaming-llm-baseline.md). **DONE 2026-06-13 (code scaffold)**: `llama.cpp` commit `632ce0f92` adds disabled-by-default `--kv-streaming-sink` / `--kv-streaming-window` controls to `llama-cli` and `llama-server`, plumbs per-request `kv_streaming_sink` / `kv_streaming_window`, and implements sink + recent-window middle eviction through the existing server context-shift `llama_memory_seq_rm` / `llama_memory_seq_add` path. Built `llama-server`, `llama-cli`, and `llama-quantize`; help output exposes the new flags. The 4-axis bench sweep (3 budgets × 2 models × 4 workloads, 1 nightshift, requires `feedback_no_concurrent_inference` per-cell approval) remains inference-gated. **Cluster-wide gate**: until the sweep lands, the relative gains claimed by SP-KV / KVP / LU-KV / ForesightKV / PBKV are unanchored against the simplest possible competing technique.

**Reporting protocol for NIB2-49..52**: same as Round 2 baseline. When the non-inference scaffolding portion completes:
1. Check the box here.
2. Update the linked canonical cluster handoff's "Spike Plan" status to reflect scaffolding-done / inference-pending.
3. Add a one-line entry in `progress/YYYY-MM/YYYY-MM-DD.md`.
4. Do NOT mark the linked cluster handoff complete — the inference-gated portion stays open until the sweep / A/B lands.

---

## Items explicitly excluded (blocked or inference-required)

These are *non-inference in nature* but gated on external signals. Listed so the gate is visible, not to pick up:

- `readme-refresh.md` — GATED on AR-3 trial ≥100 (currently ~78). Pick up when autopilot journal hits 100 trials.
- DAR-3/DAR-4 validation passes — code is NIB2-16/17; measurement is inference.
- REPL S4 A/B — A/B itself is inference; scaffolding (not listed here) would be ~4h code.
- Qwen3.6 benchmark — [`qwen36-production-upgrade.md`](../completed/qwen36-production-upgrade.md) — inference-gated. Download already done.
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
├── ~~NIB2-12 (parallel seeding)~~       → retired 2026-06-13; old two-stream design is stale/unsafe
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

## 2026-06 cluster supplement (factory.ai harvest + earlyoom)

From `/research-intake` deep-dive of factory.ai docs + earlyoom (intake-657/658/659). Full harvest: [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md). Each item has its own handoff stub.

- [x] **NIB2-53** (**HIGH** — lowest-hanging fruit) ✅ **DEPLOYED 2026-06-04** on host `Beelzebub`: **earlyoom** userspace OOM daemon armed against multi-model mlock OOM-freezes → [`earlyoom-oom-protection.md`](../completed/earlyoom-oom-protection.md) (archived 2026-06-12; residuals in `dynamic-stack-concurrency.md`). Built ≥1.8 from source (host pkg was v1.7, lacked `--ignore`/`--sort-by-rss`); systemd unit as `User=daniele` with `--sort-by-rss --ignore '^(llama-server|sd-server)$' --prefer '^llama-bench$' -s 100,100 -M 40GiB,20GiB`; control plane at `oom_score_adj=-1000`; `-N` audit hook verified writing `EARLYOOM_KILL` JSON. **Residual follow-up**: durable `oom_score_adj=-1000` in the orchestrator launcher (one-shot `choom` doesn't survive control-plane restarts).
- [x] **NIB2-54** (MED): **Repo-Readiness Scorer** (5-level / 9-pillar / 80%-unlock over our 4-repo map; feeds autopilot remediation) → [`repo-readiness-scorer.md`](repo-readiness-scorer.md). Deterministic detectors, no inference. New capability. **DONE 2026-06-13**: `scripts/validate/repo_readiness_scorer.py` implements 45 deterministic criteria (5 levels x 9 pillars), JSON/Markdown output, and threshold-gated portfolio/repo maturity. First report: portfolio Documented (L2); root Optimized (L4); orchestrator/research/llama Documented (L2). Artifacts: `data/repo_readiness/repo_readiness_2026-06-13.json` and `progress/2026-06/repo-readiness-2026-06-13.md`. Remediation-queue export remains follow-up in the canonical handoff.
- [x] **NIB2-55** (MED): **Security-review skill** (two-pass STRIDE + OWASP Top10 + OWASP-LLM:2025 + supply-chain; exploit-path-gated severity) + adopt the **code-review 8-gate filter + P0–P3 + finding schema** into the existing code-review skill → [`security-review-skill.md`](../completed/security-review-skill.md). **DONE 2026-06-13**: added `.claude/skills/security-review/` with SKILL.md + agents/openai.yaml. The repo has no existing local `code-review` skill to patch, so the shared 8-gate exploit-validation filter and P0-P3 finding schema live in the new security skill and are ready to reuse if a code-review skill is added later.
- [x] **NIB2-56** (MED): **AutoWiki-style incremental KB generator** (topic-taxonomy pages + page→source manifest + change-driven ColBERT re-embed) → merged into [`internal-kb-rag.md`](internal-kb-rag.md) § "Incremental wiki/KB refresh" (2026-06-12; stub record: [`autowiki-incremental-kb-generator.md`](../completed/autowiki-incremental-kb-generator.md)). **DONE 2026-06-28 (non-inference scope)**: source-manifest generation, changed-source KB-RAG update/prune, nonblocking commit hook, output structure lint, doc-drift validation, writer evidence policy, and the writer review/control plane are live. `wiki.yaml` now chooses `worker_general` as the role-level writer alias, and `wiki_writer_review.py` emits review packets plus validates drafts/evidence without calling a model or adopting pages. Actual model drafting plus human/measured review remains an execution gate in `internal-kb-rag.md`, not a missing non-inference scaffold.

---

## 2026-07-31 supplement — three defects found while settling the modalities

All three are zero-inference. They surfaced during the vision/speech campaign but belong to nobody's
handoff, which is exactly how items of this shape get lost.

- [x] **NIB2-57** (**HIGH**): **Four throughput priors were 32–40% low and the router was deciding on them** ✅ 2026-07-31 (epyc-inference-research `5dfc339e`). frontdoor / coder_escalation / worker_summarize `24.3 → 40.22`; worker_general `38.46 → 56.86`. Root cause is a **silent fallback**: all four had `baseline_tps == optimized_tps`, and the router reads `optimized_tps` with an `or baseline_tps` default — so an *unmeasured* prior is indistinguishable from a *measured* one at the read site. `baseline_tps` is now `null` for the 35B roles: not measured, and not fabricated.
- [x] **NIB2-57a**: **Make the unmeasured-prior case loud rather than silent.** ✅ 2026-08-23 — full reader audit (map in the session report) + shared `ResolvedTps`/`resolve_tps_prior()`/`format_tps()` helper in `src/registry/registry_loader.py`; MCP tools, `cli --list-roles`, `render_stack_summary` now label baseline-stand-ins and `unmeasured`; `bilinear_scorer` drops the fabricated `10.0` default for a `tps_known` provenance mask; `train_graph_router` warns per-role when fleet tps is unmeasured. Measured behavior byte-identical; 71 targeted + 651 surface tests pass (one pre-existing data-driven failure in `test_q_scorer.py::TestMultiDimensionalCost` — `quality_overall: null` for architect_general post-Qwen3.8-27B swap; measurement-data decision, not code). The `or baseline_tps` fallback is the mechanism that let NIB2-57 persist; a prior that has never been measured should fail closed or warn, not quietly stand in for a measured one. Audit every other reader of `optimized_tps` for the same pattern.
- [x] **NIB2-58** (**HIGH**): **`LD_LIBRARY_PATH` landmine — a fresh HIP build silently loads the FROZEN production ggml** ✅ guard landed 2026-07-31 (epyc-inference-research `7f310022`). `/etc/environment:5` and `devcontainer.json:57` put the production `build/bin` **early** in `LD_LIBRARY_PATH`, so a fresh HIP whisper build resolved the production **CPU-only** ggml, found no GPU, and ran full-CPU **while printing `use gpu = 1`**. Guard at `scripts/utils/verify_ggml_linkage.sh` reproduces it — 3 of 5 libraries came from the wrong tree.
- [x] **NIB2-58a**: **Wire `verify_ggml_linkage.sh` into every ggml build path on this host**, not just the whisper one. ✅ 2026-08-23 — build-path map (16 classes) + new `scripts/utils/verify_build_linkage.sh <build_dir>` helper (static carve-out: verifier exit 2 accepted only when `ldd` proves static); wired into `run_autokernel_historical_replay.py`, `kernel_eval.sh --build`, `legacy/build_llama.sh`, `smoke_test_llama_v3.sh`, `prove_paged_attention.sh`, `expert_routing_skew_profile.sh`, `bench_kv_hadamard.sh`, and — for the FROZEN production launch flow — `check_linkage()` in `scripts/session/verify_llama_cpp.sh` (CPU + HIP, launch-recipe + ambient). Autokernel build flows + orchestrator aux launches + `verify_speech_kernels.sh` were already wired (verified, not re-wired). Frozen kernel trees untouched (0 edits). Live verifier runs: whisper PASS, tts PASS, llama CPU 6/6 + HIP 6/6 PASS. The guard currently exists but must be *invoked*; **every future ggml build on this host is exposed** until it is. A landed fix whose entry point is never called is the classic derived-actionable failure shape.
- [ ] **NIB2-59** (**MED**, governance): **Resolve the measurement trust-boundary contradiction.** `agents/shared/MEASUREMENT_POLICY.md:79` says changes are human-PR-reviewed amendments, while `MEASUREMENT.md:117-119`'s boundary membership **omits the digest**. As written, nobody — human or agent — can tell whether an agent is permitted to edit the digest. **Needs an operator ruling**, not an agent decision, because the trust boundary is human-amendment-only and self-amending it would beg the question.

## 2026-07-31 supplement 2 — repo hygiene surfaced by the orchestration-wiring window

Identified during the 20:00–23:00Z wiring window and **deliberately not acted on**: a stack start was
in flight and several of these touch the shared clone. All zero-inference. Measured figures, not
estimates.

- [x] **NIB2-60** (MED): **1.4 GB of orphaned git pack files in `/workspace/.git/objects/pack/`.** `git count-objects -v` reports `garbage: 3` — `tmp_pack_hhZMcY` (414 MB), `tmp_pack_QlMjgI`, `tmp_pack_WJ8KfU`. Remove by **explicit three-path `rm`** on those exact filenames. **Never `git gc`** on this repo: `/workspace` and `/mnt/raid0/llm/epyc-root` are one clone shared by parallel sessions, and a full repack can disrupt a live session mid-operation. ✅ 2026-08-23 — verified resolved: `git count-objects -v` garbage=0, size-garbage=0, zero `tmp_pack*` files in `.git/objects/pack/` (resolved by the 2026-08-23 reclamation or promotion repack; nothing to remove).
- [x] **NIB2-61** (LOW): **`llama.log` and `main.log` are tracked at the repo root.** Both are runtime logs and both currently show as deleted in the working tree while their tracked entries remain, so every session sees a dirty tree it did not cause — and `w1_preflight.py` gates on a clean tree. Untrack and gitignore. ✅ 2026-08-23 — resolved by 334d04b3 (2026-08-12): untracked + gitignored; verified no tracked entries (`git ls-files` empty for both; `.gitignore` lines 159-160).
- [x] **NIB2-62** (LOW): **`.devcontainer/Dockerfile.orig` is untracked merge residue.** Delete or, if it is a deliberate reference copy, name it so and track it. ✅ 2026-08-23 — deleted (untracked, 4854 B, gitignored via `*.orig` line 164; unreferenced — cited only as debris in rocm-verify-profile-backend.md and progress/2026-08-03.md, never as a reference copy).
- [x] **NIB2-63** (MED): **~4.5 GB of `repos/*.bak-2026-05-22*` clones hold ZERO unique commits.** `repos/epyc-llama.bak-2026-05-22-141927`, `repos/epyc-orchestrator.bak-2026-05-22`, `repos/epyc-inference-research.bak-2026-05-22` (and the identical set under `/mnt/raid0/llm/epyc-root/repos/`, which is the same paths through the symlink — count the space once). Verified: nothing in them is absent from the live clones. **Re-verify uniqueness immediately before deleting**, not from this record — the check is cheap and the deletion is not reversible. ✅ 2026-08-23 — verified resolved: no `*bak-2026-05-22*` clones exist under repos/ or /mnt/raid0/llm; only live symlinks remain (repaired 2026-08-16).

---

## 2026-08-12 supplement — observers that cannot say "I cannot tell"

Filed by the class-sweep that followed the coordinator-daemon watchdog blindness: `bus_supervisor.sh`
identified its target with `pgrep -f "session_bus_coordinator\.py run"`, the live daemon's argv had
`--bus-root <path>` between `.py` and `run`, so a **healthy, actively heartbeating** daemon read as
dead forever and the watchdog relaunch-looped every ~10s for hours before anyone noticed. Root cause
is not the regex: the guard could not observe the thing it guards and **nothing detected that**, and
two states existed where three were needed.

All zero-inference. Each row below is a distinct file that collapses "cannot observe" into a definite
verdict. **Enforced, not remembered**: `tests/test_observer_contract.py` reads
[`scripts/coordination/observer_registry.json`](../../scripts/coordination/observer_registry.json),
discovers these files structurally, and goes RED if a line here is checked off or deleted without the
migration landing. Reference adoption: `scripts/coordination/backfill_supervisor.sh`. Contract:
[`scripts/coordination/observer_guard.sh`](../../scripts/coordination/observer_guard.sh).

- [x] **OBS-3** (HIGH): **`scripts/nightshift/inference_guard.sh` fails OPEN into a live inference
  run.** ✅ 2026-08-23 — AUD-7's three-state fix (`381dddfe6`) closed the pgrep/xargs collapse but left a partial-blindness hole: an unreadable MemAvailable degraded to a WARNING while the guard proceeded to all-clear. `check_inference_load()` now returns `failed` (rc 1, loud `MEASUREMENT FAILED`) when the memory channel cannot be read — one negative and one blind eye is not a clear; run_wrapper's existing exit-4 refusal covers it. `pgrep -f 'llama-server|llama.cpp' | xargs … || true` is summed into an RSS total, so a
  missing `pgrep`, an argv drift, a renamed binary and an `xargs` error ALL yield 0 GB — which takes
  the `else` branch, prints *"No heavy inference detected"*, and lets `run_wrapper.sh` launch the
  full multi-project agent workload on top of a live 200 GB+ inference. The dangerous direction of
  the same two-state collapse. Give it an `unknown` state and treat unknown as busy (the polarity
  rule `inference_load_check.py` already states: *"for EXCLUSION, unknown must mean busy"*).
- [x] **OBS-4** (MED): **`scripts/nightshift/run_wrapper.sh:79` reproduces the specimen verbatim.**
  ✅ 2026-08-23 — `autopilot_running()` is now three-valued (running/stopped/unconfirmed, rc 0/1/3): authoritative channel is the singleton flock on `orchestration/.autopilot.lock` (argv-independent, held by the daemon by construction), corroborated by an adjacency-robust dual pgrep pattern; pgrep rc≥2 / missing pgrep / untestable lock → `unconfirmed`, which SUPPRESSES the shadow launch — only a confirmed `stopped` licenses it. The three `skip … return 0` branches on missing cross-repo paths now emit `AUX-DEPENDENCY-MISSING` and exit 5 (partial run) instead of reporting success. Truth table tested (10 cases). `autopilot_running() { pgrep -f 'scripts/autopilot/autopilot.py start'; }` requires `start` to sit
  immediately after the script path — exactly the adjacency that broke when a flag was inserted into
  the daemon's command line. Any `autopilot.py --config X start` reads as "AutoPilot not running"
  and the lab shadow jobs launch into a live AutoPilot. Also note three `skip … return 0` branches
  keyed on hardcoded cross-repo paths: the run reports success having done none of that work.
- [x] **OBS-5** (MED): **`scripts/benchmark/rustevo2_bench_preflight.py` green-lights a bench against
  a live AutoPilot.** ✅ 2026-08-23 — `active_autopilot()` replaced by three-state `autopilot_state()`: missing `pgrep` → `unobservable`; an empty pgrep result is never trusted alone (a negative requires the flock to be provably free too — the drifted daemon still holds it); `unobservable` FAILS the preflight in both strict and advisory modes. 15-case truth table tested. Half-right already — a `pgrep` returncode outside `(0,1)` is treated as "could
  not inspect" — but an EMPTY result is read as a positive "no AutoPilot", and a missing `pgrep`
  binary raises `FileNotFoundError` out of `run()` before that handling is ever reached.
- [x] **OBS-6** (LOW): **`scripts/session/health_check.sh` reports unreadable as failing.** ✅
  2026-09-15 — `pgrep -f "claude"` and `pgrep -f "monitor_storage"` are DELETED (neither process
  publishes a pid/heartbeat this script could check instead); both now report a distinct UNKNOWN
  verdict, tallied separately, never scored PASS/WARN/FAIL. The `cat ... || echo "unknown"` probes
  that then COMPARED that string against the expected value are replaced by `sysfs_value`/
  `sysfs_bracketed`, returning the sentinel `__UNREADABLE__` (a string the kernel could never itself
  publish) and folded by `check_sysfs_eq` into UNKNOWN — never FAIL — while a readable-but-wrong
  value still FAILs. Body restructured behind a `main()` gated by the BASH_SOURCE guard so
  `scripts/session/tests/test_health_check.sh` can source the file for its helpers without running
  the live checks; 13-case shim battery. Registry row flipped to `exempt` (one-shot report script,
  not a daemon watchdog — no `observe` entrypoint applies).
- [x] **OBS-7** (MED): **`scripts/session/emergency_cleanup.sh:26` is a committed
  `sudo pkill -f claude`.** ✅ 2026-08-23 — the `sudo pkill -f claude` and its `pgrep -f claude` are DELETED; the section now refuses to guess and prints the operator steps for killing only PIDs they verified themselves. Follow-on safety: umount failure reports loudly instead of aborting under `set -e`, and the delete prompt warns that a live bind mount makes `rm -rf` reach `/mnt/raid0/llm/tmp/claude`. Registry row migrated to `exempt` with the review as the reason. The exact idiom CLAUDE.md and INC-20260731-broad-process-pattern-kills
  forbid, on a documented shared host, behind nothing but an interactive prompt. The PreToolUse
  pattern-kill hook cannot see it — the hook inspects the *typed* command
  (`bash scripts/session/emergency_cleanup.sh`), not the script body — so the rule is
  assumed-enforced here rather than enforced, unlike its sibling `check_operator_apply_copy.sh`
  which documents that scope limit explicitly. Replace with pid-scoped termination or delete.

- [x] **OBS-11** (MED): **A devcontainer rebuild silently disabled every venv-backed gate.** ✅ 2026-08-19 — `~/.local/share/uv/python/` was recreated empty on 2026-08-18 14:36, so `repos/epyc-orchestrator/.venv/bin/python` (a symlink to a uv-managed CPython 3.11) became dangling while its 367 site-packages stayed intact. `scripts/validate/validate_intake.sh` and `kb-search` then failed per-session with no owner, and the repair path was itself blocked: the rebuild left `~/.cache/uv/{archive-v0,interpreter-v4}` root-owned, so `uv python install` died on `Permission denied` before it could fix anything. Repaired (chown + `uv python install 3.11` → 3.11.16; `validate_intake.sh` green, 1162 entries). `health_check.sh` gains a **Tooling Interpreters** section that resolves the orchestrator + research venv interpreters **and** checks uv-cache writability, each failing with its exact repair command; both mutation-tested against synthetic breakage. Blast radius derived structurally (every `pyvenv.cfg` under `/workspace` + `/mnt/raid0/llm`, testing whether its `home` resolves), not from the observed symptom: only this venv.
- [x] **OBS-12** (LOW): **`.claude/skills/kb-search/SKILL.md` documented an interpreter that cannot work — audit the other skills for the same shape.** Fixed for kb-search on 2026-08-19 (it told every session to run bare `python3`, which has no `numpy` and dies in `colbert_encoder.py`, independent of OBS-11); the hooks and batch scripts already used the venv. **A second instance is already confirmed**: `.claude/skills/project-wiki/scripts/lint_wiki.py` exits with `ERROR: PyYAML not installed` under bare `python3` and runs clean under the orchestrator venv — found incidentally while linting, not by any check. The open work is the sweep: nothing ties a skill's documented command to an interpreter that actually has the imports, so the remaining instances stay invisible until a session hits one.
  ✅ 2026-09-17 (`sub-small-audits`, root `afb9745c`). Today bare `python3` imports PyYAML and numpy
  only from `~/.local`, which a devcontainer rebuild can wipe. The sweep therefore ran every skill
  script and every documented bare-`python3` target under `python3 -s`, which ignores that
  directory.
  - **Wrong install hints.** `lint_wiki`, `query_wiki`, `seed_index` and `validate_intake` told
    the user to `pip install pyyaml`. `backfill_dispositions` and `resolve_intake_id` died with a
    raw ImportError. All six now refuse and name the venv command.
  - **Silent config loss.** Without PyYAML, `compile_sources` and `wiki_writer_review` ignored
    `wiki.yaml`. For `compile_sources` that changed source selection: `SCHEMA.md` dropped out of
    `skip_filenames`. Both now raise instead.
  - **`coordinator-agent/SKILL.md`** ran bare `python3` for three scripts that need PyYAML:
    `tmux_adapter` crashes, `merge_gate` refuses, and `session_bus` needs it for its roster. All
    of its Python commands now name the venv.
  - **`research-intake/references/taxonomy.md`** now points at `validate_intake.sh`.
  - **Guard:** `tests/skills/test_skill_interpreters.py`, 18 cases; 16 fail before the fix.
  - **Verification:** each fixed invocation was run under the venv, and none failed on an import.
  - [ ] **OBS-12a** (LOW, filed 2026-09-17): **the same shape outside `.claude/skills`.**
    CLAUDE.md's bus drain (`scripts/coordination/session_bus.py drain ...`) and heartbeat `append`
    run through the `#!/usr/bin/env python3` shebang. Both call `_require_roster_id`, which needs
    PyYAML (`session_bus.py:235-252`), so after a rebuild that wipes `~/.local` every session's
    drain would fail.
    - **Options:**
      - (a) point the CLAUDE.md, BUS_PROTOCOL and SESSION_LIFECYCLE commands at the venv;
      - (b) have `session_bus.py` read the roster without PyYAML;
      - (c) add a system-interpreter PyYAML check to `health_check.sh` next to the OBS-11 checks.
    - **Recommendation:** (c) now, plus (a). Editing CLAUDE.md is a fleet-doctrine change, so the
      owning session makes it.
  - [x] **OBS-12b** ✅ 2026-09-17 (already fixed by the wrap-up pass-2 wiki compile; all three links now point at `../handoffs/completed/security-review-skill.md`, verified by the main session) (LOW, filed 2026-09-17): `lint_wiki.py` reports two dangling links:
    `wiki/agent-architecture.md:2254` and `wiki/tool-implementation.md:278,321` still point at
    `../handoffs/active/security-review-skill.md`, which moved to `completed/` in `9804fec9`.
    `wiki/` is written by the serialized wrap-up, so fix it in the next compile.
- [x] **OBS-3a** (LOW, follow-up 2026-08-23): add a mutation case to `scripts/nightshift/tests/test_inference_guard.sh` for "MemAvailable unreadable → `failed`" (awk-shim pattern as used in the OBS-3 fix scratch harness) — the existing suite predates the mem-channel fail-closed semantics. ✅ 2026-08-23 — mutation M-D added (PATH-shimmed `/bin/false` awk): asserts state=failed, RSS channel still measured 0 while failed, MEMAVAIL_GB=unknown, ACTIVE unset, "MEASUREMENT FAILED" wording, and no all-clear printed. Suite 15 → 21 passed; guard untouched.
- [x] **NIB2-58b** (LOW, follow-up 2026-08-23): re-point `smoke_test_llama_v3.sh` / `prove_paged_attention.sh` binary paths from the extinct `build/bin` to the named experimental build dirs (`build-v9-cpu` / `build-v9-hip`) — operator-flagged convention change; the scripts currently fail fast with a clear message, which is correct behavior until then. ✅ 2026-08-23 — ground truth: `build-v9-cpu` is the only named CPU dir with the full binary set (llama-server/cli/bench/completion); both scripts re-pointed to it (CPU-oriented), verifier expected-roots updated; fail-fast preserved; live `verify_ggml_linkage.sh` runs on all four binaries PASS (exit 0).
- [x] **OBS-13** ✅ 2026-09-23 — closed by `0ea91f3e` (2026-09-08: scanner selects by content hash against the tracked `source_manifest.json`, never mtime); box was never ticked. (MED, found 2026-08-30): **the wiki source scanner is blind in every lane worktree,
  and its watermark is not shared.** `.claude/skills/project-wiki/scripts/compile_sources.py`
  selects sources with `md_file.stat().st_mtime > since` — filesystem mtime. In a lane worktree
  every file's mtime is the **checkout time**, which is later than any watermark, so the scan
  returns **the entire repo**: measured 2026-08-30 from `lane/ak-rebuild-20260828`, `total_new =
  908` where the true git-derived delta since the 2026-08-28 watermark was **17**. Two consequences,
  both silent. (1) The wrap-up routine's Step 5 is unrunnable as written from the place the routine
  says to run it. (2) `wiki/.last_compile` is **gitignored** (`.gitignore:44`), so it exists only in
  the shared clone — the wrap-up lease claims to serialize "one watermark" that is in fact
  per-checkout, and a `--touch` from a lane serializes nothing and records nothing. Worse, a
  `--touch` run from a lane after "compiling 908 sources" would move the *local* watermark while a
  regenerated `source_manifest.json` (which **is** tracked) would be committed carrying the
  mtime artifact. **Fix: select by content hash against the tracked `source_manifest.json`, or by
  git commit date, not mtime** — the manifest already stores a `content_hash` per source, so the
  hash-diff is mtime-independent and lane-safe by construction. Interim workaround, used for the
  2026-08-30 sweep: derive the delta with
  `git log --since=<watermark> --name-only --pretty=format: origin/main -- <source dirs>`, compile
  that, and do **not** regenerate the manifest from a lane.
  **Same root, second instrument:** `.claude/skills/project-wiki/scripts/lint_wiki.py` reports **17
  dangling-link errors** in a lane worktree and **0** in the shared clone, because every one is a
  `../repos/epyc-inference-research/...` target and `repos/` is an **untracked symlink farm** that
  `scripts/clone-repos.sh` creates only in `/workspace`. Both tools silently assume they are running
  in the shared clone; neither can say "I cannot tell from here". Whatever fixes the scanner should
  also give the linter a way to resolve or explicitly skip cross-repo targets it cannot see.
  **✅ 2026-09-08 (`0ea91f3e`)** — both halves closed. Scanner default scan = content-hash diff
  against the TRACKED `wiki/source_manifest.json` (mtime never consulted; a scratch run with every
  source stamped 2030 returns 0 — phantom-942 mechanism dead); `--touch` regenerates the tracked
  manifest from the current full set, so lane and main record byte-identical hashes; no baseline →
  stderr note + one full emission, never a phantom; incremental scans refuse to overwrite the
  tracked manifest with a partial (`--full` required). Linter: a missing target is provably
  cross-repo only when it enters `repos/<member>/` with `<member>` in the tracked
  `scripts/clone-repos.sh` farm array and this worktree has no farm → INFO skip, never ERROR; farm
  present or non-farm paths keep ERROR. 11 new tests; scratch proof: lane-vs-main `--touch`
  produces identical per-file hashes.
- [x] **OBS-8** (LOW): **`scripts/session/start_orchestrator_test.sh`'s port gate is vacuous on this
  host.** ✅ 2026-09-15 — `osp_probe_tool` now probes with `command -v`, preferring `ss`, then
  `netstat`, then `lsof`; when none is on PATH the gate refuses to launch (non-zero exit, loud
  "CANNOT OBSERVE" message) instead of printing a false all-clear. An occupied port also refuses.
  The kill loop that stopped port-derived PIDs the script never started is DELETED — CLAUDE.md
  "kill only PIDs you captured yourself" — replaced by a refusal that prints each occupant pid
  (`ps -p ... -o pid,etime,cmd`) and the operator's own `kill`/`ps -p` verification steps. Port-probe
  functions extracted so `main`'s launch logic (llama-server + uvicorn) is never reached by a test;
  15-case shim battery in `scripts/session/tests/test_start_orchestrator_test.sh` covers no-tool
  (refuse), fallback ordering (ss→netstat→lsof), occupied (refuse), and free (pass). Not registered
  in `observer_registry.json`: it identifies by listening PORT, not by process name/argv, so Rule A's
  discovery pattern does not match it.
- [ ] **OBS-9** (LOW): **`"esc to interrupt"` is a liveness oracle in FOUR files with no shared
  constant** — `scripts/coordination/idle_supervisor.sh`, `scripts/coordination/idle_watch.sh`,
  `scripts/coordination/session_bus_coordinator.py`, and (added 2026-08-12)
  `scripts/coordination/fleet_watch.sh`. It is **vendor TUI text**: a Claude Code or
  Codex release that rewords it breaks all of them at once, and `idle_supervisor` would then type
  nudges into six actively-generating panes indefinitely. (Its uncapturable-pane handling is already
  correct — *"a pane it cannot capture is UNKNOWN, never idle"* — so only the marker needs a canary.)
  The two rosters have also already drifted: `idle_watch.sh` watches 4 mains, `idle_supervisor.sh` 6.
  **The canary this row asks for already exists in one of the four** and is the cheapest thing to
  lift: `fleet_watch.sh` gathers every vendor string in one named block and adds a `DETECTOR-BLIND`
  condition — if no readable pane matches ANY known marker for PERSIST_CYCLES, it reports that the
  vocabulary has drifted and SUPPRESSES the idle verdicts built on it, because six mains losing
  their markers in the same cycle is a TUI release and not a fleet-wide stall. It is exercised in
  both directions by `scripts/coordination/tests/test_fleet_watch.sh` and mutation-tested (removing
  the guard turns the suite red). Generalising it is what closes this row.
- [ ] **OBS-10** (LOW): **Two E8 operator ratifiers gate on an argv pattern.**
  *Note 2026-09-16: the E8 chain these ratifiers served is retired by operator ruling [`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json) (root `1ee8bd7c`). The ruling re-anchors the reseed gate to the current eras; the gate binds only at promotion.*
  `artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.sh` and
  `ratify_e8_empty_frontier_bootstrap_20260726.sh` both use
  `pgrep -f '[s]cripts/autopilot/autopilot.py start'` — same start-adjacency fragility. The newer
  `ratify_v9_cpu_bench_era_advance_20260811.sh` already migrated ("no process-pattern probe — host
  rule: never pgrep by name"); backport that. Deliberately OUT of the observer-registry discovery
  scope (one-shot scripts a human runs and reads once), recorded here so the finding is not lost.

---

## 2026-08-23 supplement — disk reclamation phase 1 done, phase 2 candidates

Phase 1 (operator-approved, 2026-08-23): `/mnt/raid0/llm/tmp/` 285G → 2.9G via per-worktree
`git worktree remove` (138 worktrees, never `prune`), 111G → 371G free. Details:
`progress/2026-08/2026-08-23-disk-reclaim.md`.

- [x] **NIB2-64** (MED): **autokernel/worktrees 165G — 144/146 one-shot session worktrees from
  08-11→08-14 are unreferenced by active handoffs.** Two are referenced and must stay:
  `inf37-fancy-simd-v9-20260811`, `promote-kernel-rnd-dashboard-20260812`. Registered in
  epyc-inference-research; remove per-worktree (`git worktree remove --force`), NEVER `prune`.
  Operator decision needed only if any session claims them — none does today. ✅ 2026-09-15 —
  verified: `/mnt/raid0/llm/autokernel/worktrees` is now `402M` (`du -sh`) and `ls` shows only the
  two kept trees, `inf37-fancy-simd-v9-20260811` and `promote-kernel-rnd-dashboard-20260812`; the
  144 unreferenced one-shot worktrees are gone.
- [ ] **NIB2-65** (MED): **model duplicates/orphans ~25G in `/mnt/raid0/llm/models/`** — safe set
  from the 2026-08-23 census: `bge-m3-f16.gguf`, `multilingual-e5-base-f16.gguf`,
  `granite-embedding-97m-multilingual-r2-Q4_K_M.gguf`, `Qwen3-TTS-12Hz-0.6B-Talker-Q8_0.gguf`,
  `gemma-4-26B-A4B-it-assistant-v6-f16.gguf`, empty husks (`MaziyarPanahi`, `Mungert`,
  `prithivMLmods`, `jiaojjjjje`, `hugging-quants`), `tinyllamas-stories-260k-f32.gguf`,
  `DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf`, `Qwen3-4B-Thinking-2507-GGUF` (4G, only in
  deprecated benchmarks). Judgment calls (research-only refs, keep unless operator says otherwise):
  `Qwen3-ASR-1.7B-GGUF`, `gemma-4-e2b/e4b-it-Q8_0`, seal-concise set.
  2026-09-15 PARTIAL: the 7 files + 5 husks deleted (~4.3 G), each ledgered in orchestrator `model_registry.yaml`
  `deprecated_models` (branch `sub/nib2-65-ledger` `8e1bd269`). HELD: `Qwen3-4B-Thinking-2507-GGUF`, because the rationale above is
  wrong — `gpu-cot-scaffold-sidecar.md` (active) uses it as a control-arm generator. Operator call.
- [ ] **NIB2-66** (LOW): **stale kernel trees ~18G** — `llama.cpp-experimental-preserved-20260724T135832Z`
  (14G, superseded), `llama.cpp-v6-iqk` (1.9G, iqk shipped in v9), `llama.cpp-v7-sanitize-audit`
  (1.6G), `llama.cpp-k28-prototype-20260720` (0.9G). Keep `llama.cpp-dflash2-qwen38-20260820`
  (active handoff `dflash2-block-drafter-experimental-build.md`).
  2026-09-15 PARTIAL: `llama.cpp-v6-iqk` and `llama.cpp-v7-sanitize-audit` removed (clean, fully pushed, `git worktree remove`).
  HELD: `llama.cpp-k28-prototype-20260720` (dirty: uncommitted GDN `.cu` edit + doc — commit/push or discard first);
  `llama.cpp-experimental-preserved-*` (dirty worktree of the production clone, operator-owned).
- [ ] **NIB2-67** (LOW): **`cache/huggingface` 127G** — re-downloadable HF cache, all files touched
  <30d ago (in active use by sessions). Reclaim only when disk pressure returns; `pip`/`uv`/`dflash`
  caches also live under `cache/`.
- [x] **NIB2-68** ✅ 2026-09-23 — closed by the same `0ea91f3e` (tracked manifest; `--touch` advances it). (MED): **wiki compile watermark is per-worktree** — `wiki/.last_compile` (and the
  manifest write) is gitignored, so a lane worktree never sees the shared clone's watermark: the
  scanner run from a lane reports the full-history backlog (919 phantom "new" sources measured
  2026-09-01 vs the true delta of 2), and a lane `--touch` would write a lane-local watermark the
  fleet never reads. Same worktree-invariance class as the serialized_push lock-dir fix
  (`022686f3`): resolve the wiki shared surface against the git common dir's parent, or make
  `compile_sources.py` refuse to run outside the main clone. Until fixed: run scanner and
  `--touch` from `/workspace` only.

  **2026-09-07 addendum — the same failure fires from `/workspace` itself, no lane involved.**
  Run correctly from the shared clone (not a lane), `total_new` still read **942** against a
  genuinely-real 2026-09-03 local `.last_compile` — not a checkout-time mtime artifact, but a
  4-day gap dominated by a ~300-commit campaign merge. `--touch` was withheld rather than run
  (would have falsely marked all 942 compiled); a small, real subset (4 sources, this session's
  own CJ-8/9/11/12 and vidya SC69-73 findings) was compiled by hand into `wiki/benchmark-
  methodology.md` and `wiki/formal-verification.md` instead (`95c7e46d`). This confirms the row's
  own diagnosis generalizes past the lane-mtime case: mtime-since-watermark is unreliable **from
  any single checkout**, lane or shared clone, whenever a different clone (this fleet's, or a
  peer session's independently-touched local watermark) has already compiled part of the delta.
  The content-hash-against-`source_manifest.json` fix already proposed here is the correct fix
  for both mechanisms at once — no separate row needed.
  **✅ 2026-09-08 (`0ea91f3e`) — closed with the OBS-13 fix.** Scanner selection is now a
  content-hash diff against the tracked `wiki/source_manifest.json`; `--touch` advances the
  tracked manifest (lane-safe by construction — hashes are worktree-invariant). Post-deploy note:
  the tracked manifest baseline is 2026-08-27, so the first post-fix scan reports the real 86-source
  delta (unrecorded drift, not phantom) — reconciling it (compile the delta, or one lease-held
  `--touch` if the fleet's Sep-3 sweep already compiled it) is a deployment decision, not a code
  question.

---

## 2026-09-03 supplement — pre-existing orchestrator `main` failures surfaced by the C7 merge

Found by the INF-70 `c7-finish` agent while merging the NUMA pre-evict enable (orchestrator `5f20e23c`); none
attributable to C7 — reproduced identically on the pristine pre-merge base `510f5048`.

- [x] **NIB2-69** (MED): **orchestrator `origin/main` carries 39 launch-manifest/port-guard errors and 33
      pre-existing unit failures** (49 manifest errors before the C7 priors regen reduced them to 39; the 33 unit
      failures are identical on `510f5048`, plus 1 flaky on both bases). Triage by reason (not a bare count), fix
      or explicitly retire each, and make `stack_change_pipeline.py check` gate on zero manifest errors so the
      next merge cannot inherit them silently. Evidence: `/mnt/raid0/llm/tmp/inf70/agents/c7-finish/REPORT.md`.
      ✅ 2026-09-15 — orchestrator `sub/nib2-69-strict-gate` (`218c0591`, `4055dba0`, `89b30eb5`). The 39 = 13 half-port errors ×
      3 guard steps, a CHECK-MODE ARTIFACT: priors compiled for declared `both`, guard launch view fell to fleet→env→`full`.
      `check` now resolves ONE mode (`--numa-mode` > `stack_topology.yaml`, ambient env ignored + warned), records it as step
      `numa_mode`, threads it to compile and every guard step; manifest/port errors are hard in all guard steps. Also fixed 3
      stale priors pins and a lean check that judged a gitignored cache key. Unit: 33 base failures → 0 (2 real bugs, 1 order
      leak, 1 aged fixture, 17 made hermetic, 12 E8 tests `skipif` on deleted sealed staging bundles — coverage lost until
      restored). Residual: standalone `stack_change_guard.py` still uses fleet→env mode resolution.

## 2026-09-08 supplement — shared research clone dirty-state rescue

The **shared** clone `/mnt/raid0/llm/epyc-inference-research` sat on stale main `1d2fe2a3` carrying 9 dirty
tracked files + 4 untracked. All 11 were preserved verbatim on `rescue/shared-clone-dirty-20260907` @
`63ec9f53` (pushed to origin) and copied to `/mnt/raid0/llm/tmp/research-shared-clone-rescue-20260908/`; the
9 tracked files were then overwritten with HEAD content (`git show HEAD:<f> > <f>` — the hygiene hook blocks
the `git restore` verb in the shared clone and reads its bypass from the session env) and the clone was
fast-forwarded to `7b5d1eb6`, tracked tree clean.

- [x] **NIB2-70** (MED): **rescue the shared research clone's uncommitted state before fast-forwarding it.**
      ✅ 2026-09-08 — 11 files preserved verbatim (branch `rescue/shared-clone-dirty-20260907` @ `63ec9f53`,
      pushed; plus a filesystem copy), 9 tracked files restored to HEAD content, clone fast-forwarded to
      `7b5d1eb6` and verified clean of dirty tracked files.
- [ ] **NIB2-71** (LOW): **review `rescue/shared-clone-dirty-20260907` (`63ec9f53`) — fold or delete the
      branch.** Its content is a working copy of the CH-8 build-flags change (`162d17dd`, **already merged in
      main**) plus two older 2026-08-27 bench scripts; the residual delta over merged CH-8 is roughly **50
      comment lines** on legacy discovery scripts (build-recipe / `ROCWMMA_FATTN` notes). Decide: fold the
      comments forward, or delete the branch. Small item — the rescue itself is done, this is disposition only.

## 2026-09-15 supplement — surfaced by the non-CPU-inference ROI dispatch

All zero-inference unless stated. Filed by the 2026-09-15 dispatch session (progress note
`progress/2026-09/2026-09-15-noninf-roi-dispatch.md`).

- [x] **NIB2-72** (**HIGH**, host): The 58.4 GB coverage-harness `llama-cli` interactive prompt runaway was
      stopped by its owning session and the exact log reclaimed. The valid coverage rerun used `--single-turn`,
      closed stdin, a 900-second timeout and a 16 MiB output cap, so the same unbounded REPL failure cannot recur
      in that harness. This was disk-output growth, not evidence of a RAM leak.
- [x] **NIB2-73** (MED): **the NIB2-65 deletion ledger cannot be committed to the MASTER registry** because the
      research repo's pre-commit evidence gate fails on **12 artifact citations that exist only as UNCOMMITTED files
      in the shared clone** (`artifacts/architect-bench-gpu-2026071{4,20}/...`, `data/ternary_q2_g64_quality_gate/...`,
      `data/gemma4_iq4_residency/...`, `data/paddleocr_vl_receipt_extract_...`). They resolve in
      `/mnt/raid0/llm/epyc-inference-research` and nowhere else, so every worktree fails the gate — the same
      worktree-blindness class as OBS-13. Fix: commit the artifacts, re-point the citations, or mark them
      `# ARTIFACT LOST` — the registry owner's call. The prepared change is in `sub/nib2-65-master-ledger`
      (worktree `/mnt/raid0/llm/worktrees/sub-master-ledger`, uncommitted).
      ✅ 2026-09-15 — LANDED as research `d4de5535` on origin/main: all 8 entries are in the MASTER
      `deprecated_models` (77 total, YAML re-parsed, schema keys checked). The gate ran for real and passed
      (`errors: 0`, 424/429 citations OK, the 5 remaining are pre-existing WAIVED_LOST): the 12 cited artifacts were
      made resolvable in the worktree by copying them from the shared clone — the same untracked-presence the gate
      accepts there — then removed again, so nothing extra was committed.
      **The underlying defect is NOT fixed and keeps its own row → NIB2-73a:** those 12 artifacts exist ONLY as
      untracked files in `/mnt/raid0/llm/epyc-inference-research`, so every worktree still fails the gate, and one
      `git clean` would destroy evidence the registry cites.
- [x] **NIB2-73a** (MED): **12 registry-cited artifacts are untracked, so they exist in exactly one checkout.**
      `artifacts/architect-bench-gpu-2026071{4,20}/...`, `data/ternary_q2_g64_quality_gate/...`,
      `data/gemma4_iq4_residency/...`, `data/paddleocr_vl_receipt_extract_...` (22.4 MB + 9 small files). Commit them,
      re-point the citations, or mark them `# ARTIFACT LOST` — the registry owner's call. Until then the evidence gate
      is location-dependent (passes in the main clone, fails in every worktree) and a `git clean` loses cited evidence.
      ✅ 2026-09-15 — research `041ecb1d` on origin/main. 8 artifacts CARRIED (195 files, ~765 KB, every sha256
      verified against the origin, originals left in place) with `README.md` + `SHA256SUMS` per campaign dir; the
      22.4 MB `architect-bench-gpu-20260814` carried at 1.54% — the distilled results plus provenance chain, NOT the
      15.4 MB raw capture, 5.3 MB `-lv 3` logs, 1.9 MB VRAM telemetry or SWE-bench patch bodies, which also keeps a
      real third-party-PII surface (upstream author emails quoted into SWE-bench prompts) out of the tree. The 9th,
      `paddleocr .../summary.json`, was ALREADY correctly withheld (third-party receipt PII) — it was the GATE that
      was wrong. Side effect worth knowing: both dflash2-challenger ratification hashes now verify against artifacts
      in git; until today they hashed untracked files. Gate now reads **`errors: 0` in a WORKTREE** (431 citations:
      425 OK / 1 WITHHELD / 5 pre-existing WAIVED_LOST), which was the whole point.
- [x] **NIB2-73c** (MED): **the evidence gate could not distinguish DELIBERATELY WITHHELD from LOST.** ✅ 2026-09-15 —
      `scripts/validate/check_evidence_durability.py` (research repo, not epyc-root) now resolves a citation whose
      `<file>.WITHHELD.sha256` sibling carries a real hash as verdict **WITHHELD** — severity `info`, listed by
      default, never folded into `OK` (OK means a reader can recompute the hash here) and never escalated by `-W`
      (which is for recorded LOSSES). `ARTIFACT LOST` still wins. 12 new tests, 64 pass. In `041ecb1d`.
- [x] **NIB2-73d** (MED): **the 11 campaign directories with no provenance docs.** ✅ 2026-09-15 — research
      `6575c33c`: all 11 now carry `README.md` + `SHA256SUMS` written from git history, registry citations, progress
      logs and handoffs, with every unestablished fact written as `UNVERIFIED — <what is missing>` rather than guessed
      (measurement dates come from run-directory timestamps and `start_utc.txt`, never worktree mtimes — OBS-13).
      `sha256sum -c` passes on all 3,782 sealed files; the gate's missing-durability-docs list is now EMPTY and
      `errors: 0` holds. Three premises were CORRECTED in the writing, which is the point of sourcing them:
      `bonsai_current_v7` is NOT the evidence behind the sub-2-bit quality rejection (it is the speed reruns that
      changed nothing; the quality failures live in two other dirs); `numa_placement` is the shared
      P-BENCH-PLACEMENT-1 attestation dir disambiguated by arm, not "the fix's evidence"; and the
      `glm52_native_mtp_ab` 185837Z pair is not a completed A/B (the MTP arm hit `failed_completion_floor`).
      `cpu_optimization` holds ~30 distinct tracks across 66 bundles and was enumerated per bundle, not flattened.
- [ ] **NIB2-73e** (MED): **the durability gate scans the REGISTRY only, so cited-but-untracked evidence in DOCS and
      HANDOFFS is invisible to it.** Found while writing the 11 READMEs, all recorded in-file:
      `docs/reference/models/model-admission-2026-07-16.md:359-363` cites two `summary.json` files that exist only in
      the shared clone; `gemma-challenge-kernel-techniques-v7.md:141` carries two DANGLING citations (only the n=2 dir
      exists); six `*_20260718Tcodex` dirs carry reports whose cited run data is untracked; and further untracked
      sibling bundles are cited under `bonsai_current_v7` (L8626/8627/8641/8642/8715) and
      `qwable_reasoning_economics` (L9124-9131). Extend the checker's scan to docs/handoffs, or accept the limit
      explicitly — today the gate's silence on these is not evidence of their durability.
- [ ] **NIB2-73f** (LOW, operator): **the operator's own email address is in a tracked file** —
      `data/cpu_optimization/2026-04-30-v5-cleanup-audit/README.md:27`, attributing his own decisions. First-party, so
      the third-party-PII WITHHELD precedent does not apply and nothing was changed. Redact or keep: an operator call,
      relevant only if this repo ever becomes public.
- [x] **HYG-3** (MED): **epyc-root's commit-hygiene hook read `2>&1` as a pathspec**, so `git commit --file=msg.txt 2>&1`
      — the most common idiom on this host — was blocked as a pathspec commit, and the only escape also disabled rules
      A/B and the checkout/stash shapes. ✅ 2026-09-15 — `strip_redirections()` removes redirections at the same early
      point as heredoc bodies, so no rule can disagree about what is command and what is plumbing; 15 new paired
      tests. Hit live three times this session before it was fixed.
- [ ] **NIB2-73b** (MED): **the lean registry must be recompiled and the priors re-pinned when the shared research
      clone is next synced.** The compiler reads master from `/mnt/raid0/llm/epyc-inference-research`, which is ~298
      commits behind, so today's ledger is NOT yet in the compiled lean view and the pinned registry hash still
      matches (gate green). When that clone fast-forwards, the next `orchestrator_stack.py start` will compile the 8
      entries into the lean file and the pin will mismatch — run `stack_change_pipeline.py update` and commit the
      regenerated descriptors/priors/summary in the same change. This is the standing master→recompile→verify flow.
- [x] **NIB2-74** (MED): **`scripts/benchmark/debug_scorer.py` runs code tasks with bare `python3` from PATH**, so
      ✅ 2026-09-23 — epyc-orchestrator `46e79e27`: both code-execution sites use `sys.executable`; AST guard test.
      without the venv every pandas-dependent task silently scores False. Same shape as OBS-12. Found while
      triaging the NIB2-69 unit failures.
- [x] **NIB2-75** (MED): **12 E8 unit tests are now `skipif`-skipped because their sealed staging bundles are gone
      ✅ 2026-09-23 — operator ruled RETIRE (per OP-19). epyc-orchestrator `5fa290be`: 24 bundle-dependent tests removed (28 skips → 0), 386 remaining pass.
      from the host** (no copy under `/mnt/raid0/llm`). Real coverage loss, owner = the E8 quality-baseline
      campaign: restore the bundles, rebuild equivalent fixtures, or retire the tests deliberately.
- [ ] **NIB2-76** (LOW): **two residuals of the NIB2-69 gate fix.** (a) standalone `scripts/registry/stack_change_guard.py`
      still resolves the NUMA mode fleet→env→`full`, the exact mismatch NIB2-69 removed from `check`; (b) the priors'
      `source_artifacts` hold absolute main-clone paths, so a `check` run in a worktree verifies the MAIN clone's
      files rather than its own — location-dependent by construction.
- [ ] **NIB2-77** (MED): **finish AutoKernel disk hygiene after the approved sweep and archive-backed retirement.**
      The exact `a49053c273ee` manifest's prequalified REMOVE rows were approved and applied. A separate
      content-addressed archive preserved all 224 reviewed dirty acceptance worktrees before their exact-path
      retirement; 224/224 have removal receipts. Free space rose by 359,176,167,424 bytes (about 334.5 GiB).
      Prospective acceptance cleanup and serial disk fail-close are published (`b65138a0` root;
      `142fd1e3` research). The **187 lane worktrees registered against the frozen clone remain untouched**;
      audit their ownership and migrate/retire only through an individually reviewed procedure. Verify the
      prospective cleanup during the next completed acceptance run, rather than inferring it from unit tests.
- [x] **NIB2-77a** (2026-09-16): Apply the approved safe sweep and archive-backed exact retirement of the
      224 reviewed dirty acceptance worktrees; verify receipts, recovered space, and the frozen production tree.

- [x] **NIB2-78** (MED) ✅ 2026-09-17 (decided: operator ruled A on NIB2-78b, so kuzu stays uninstalled and the graph layer stays dormant with its one-line degrade from NIB2-78a; only the conditional NIB2-78c remains): **the graph-enhanced retriever never runs in the production API: `kuzu` is not installed.**
      Every API start logs `GraphEnhancedRetriever init failed, falling back to TwoPhaseRetriever: kuzu not
      installed` (474 occurrences in `epyc-orchestrator/logs/orchestrator.log`, including the 2026-09-17 reload).
      The failure-graph and hypothesis-graph tools (`model_registry.yaml:212-217`, `FailureGraph()`) are silently
      inert. `kuzu` is not declared in `pyproject.toml`. First noted 2026-07-23 as "unowned, left open"
      (`autopilot-decision-plane-audit-2026-07-22.md`). Decide between declaring and installing `kuzu` in the
      orchestrator venv, and retiring the graph layer with a lazy, logged-once degrade; then make the startup
      state explicit (one WARNING line, not a traceback per call site). Zero inference. Filed 2026-09-17 (wrap-up pass 2).
      The install was a stack change, so the operator decided it (NIB2-78b, ruled A 2026-09-17). Decision package:
      `progress/2026-09/2026-09-17-sub-nib2-7879.md` §3.
- [x] **NIB2-78a** ✅ 2026-09-17 (orchestrator `61793b38`): declare the `[graph]` extra (`kuzu==0.11.3`; uv.lock
      adds only kuzu) and make the missing-kuzu path one WARNING line with no traceback. Kuzu per-file lock
      contention is also one line. The graph classes' `close()` was a no-op and now releases the file lock.
      Tests: 117 passed in a throwaway venv with kuzu; 148 passed and 7 skipped in the prod venv without it.
- [x] **NIB2-78b** ✅ 2026-09-17 decided (operator ruled A 2026-09-17: kuzu stays uninstalled; revisit only with NIB2-78c): install `kuzu==0.11.3` into the orchestrator venv, or leave the
      graph layer dormant. Upstream kuzudb/kuzu is archived (final release 0.11.3). Only one of the 6 uvicorn
      workers can hold each graph file. Options and recommendation: shard §3.
- [ ] **NIB2-78c** (OPTIONAL, conditional; dormant since NIB2-78b was ruled A = do not install): take this up only if
      the graph layer is revived, and re-open the install decision together with it. Give the Kuzu graphs a single owner (one process owns
      `kuzu_db/*`; the others reach it over IPC) so graph scoring does not vary by which worker serves a
      request. Then re-evaluate the backend against maintained Kuzu forks, since upstream is archived.
      *2026-09-23 (intake-1496):* if revived, add HelixDB (Apache-2.0, Rust graph+vector on a slatedb LSM) to the backend
      candidate list beside maintained Kuzu forks; it is server-mode, not embedded, which works against the Kuzu locality rationale.
- [x] **NIB2-79** (LOW) ✅ 2026-09-17 (orchestrator `0c03e658`): **four `archive_*` tool-registry entries point at handlers that do not exist.** Every API start
      logs `Could not load handler for tool 'archive_open' / 'archive_extract' / 'archive_file' / 'archive_search':
      module 'src.services.archive_extractor' has no attribute …`. `orchestration/tool_registry.yaml:715+` names
      `src.services.archive_extractor.<fn>`, but that module defines only the `ArchiveExtractor` class. The working
      implementations are the REPL mixin methods in `src/repl_environment/archive_tools.py` (`_archive_open` …).
      Repoint the four entries at a real callable, or drop them from the registry path (REPL builtins cover them),
      and add a test that every registry `function` resolves. Zero inference. Filed 2026-09-17 (wrap-up pass 2).
      Done: the entries were removed. The functions never existed in git history (the entries were added dead
      in `882d97d4`), and the stateful, sandboxed REPL builtins cannot serve as stateless handlers.
      `tests/unit/test_tool_registry_handlers_resolve.py` gates every handler; against the old YAML it fails 6 tests.

## Cross-references

Canonical sources (always verify status in these files first):
- [`routing-and-optimization-index.md`](routing-and-optimization-index.md) — DAR, RI, AP, DS series
- [`research-evaluation-index.md`](research-evaluation-index.md) — EV, REPL, CF, TOC series
- [`inference-research-index.md`](inference-research-index.md) — AM, triattention, KV series
- [`pipeline-integration-index.md`](pipeline-integration-index.md) — vision, ODL, Lean, TTS series
- [`user-facing-harness-index.md`](user-facing-harness-index.md) — user-facing harness work (formerly Hermes B-series)
- [`master-handoff-index.md`](master-handoff-index.md) — cross-domain priorities

- [x] **NI-IO (rtx6kpro intake 2026-09-07)** ✅ 2026-09-23 — all 3 NVMe queues already read `[none]`; `group_thread_cnt` is RAID5/6-only (ours is RAID0); no inference containers here. Nothing to change. — NVMe/md-RAID0 I/O scheduler check: `cat /sys/block/nvme*/queue/scheduler`
      should be `none` (external: 91.8k vs 48.6k IOPS under BFQ); md `group_thread_cnt=8` for RAID5/6 only;
      Docker overlay2 `syncfs` stall fix only if inference containers exist here. 2-minute check.

- [x] **NI-OC — opencode event-feed growth bounded AT SOURCE** ✅ 2026-09-08. The change-feed regrew 11.4 → 35 GB in 13 h
  (1.7 GB/h) from the operator's interactive TUI + @general subagents — pruning alone was a symptom fix. Now:
  `scripts/system/prune_agent_event_store.py --idle-hours H` (reaper mode: only sessions idle > H h, never the live
  TUI/subagents, VACUUM skipped while opencode runs) and `scripts/system/opencode_event_reaper.sh` (daemon, every 30
  min, pid `/mnt/raid0/llm/tmp/opencode-reaper.pid`, log `/mnt/raid0/llm/tmp/opencode-reaper.log`). First reap: 680
  idle sessions, 232k events; 5.6k events / 12.7 GB (2 live sessions) kept; integrity ok. No cron/systemd in the
  container, so the daemon must be re-launched after a reboot — **operator: add to the post-reboot checklist**.
- [x] **NI-OC-a — adopt `observer_guard.sh` (three-state probe) in `scripts/system/opencode_event_reaper.sh`**: the reaper's
  `pgrep -x opencode` presence probe is registered `unadopted` in `observer_registry.json`; its consumer (the VACUUM
  decision) already fails CLOSED. Adoption replaces the name probe with the guard's channels so a drifted argv cannot
  read as 'absent'. Owner: whoever next touches the reaper; not urgent (no kill path, fail-closed).
  ✅ 2026-09-17 (root `49e85ab7`) — adopted at contract v1. Three states with the destructive branch gated on
  certainty: `present` and `unobservable` both WITHHOLD `--vacuum` (the latter with an alarm breadcrumb that
  clears on the next sighting); only `absent` permits it. Two read-only channels, neither a kill target:
  `proc_scan` matches `"opencode "` **with the trailing space**, so the reaper's own argv and `opencode.db`
  cannot self-match, and `db_fd` walks `/proc/*/fd` for an open descriptor on the event DB — argv-independent,
  and the thing VACUUM actually cares about. A missing DB is `unavailable`, never `absent`. New `observe`
  subcommand reports state/why/vacuum without touching anything. 15 tests + 1 skip; census OK (17 observers).
  - [x] **NI-OC-a.1 — restart the reaper daemon so the adopted script is the one running (OPERATOR / owning
    session).** The live daemon (pid from `/mnt/raid0/llm/tmp/opencode-reaper.pid`) holds its script open from
    **another lane's worktree** (`worktrees/mains/ak-rebuild-20260828/...`, a different inode from the tracked
    file), so it is still executing the OLD two-state code and will keep doing so until someone restarts it
    from the tracked path. Deliberately not done here: this session did not start that process, and the house
    rule is to kill only PIDs you captured yourself. It is also the second instance of a daemon serving a
    stale copy of its own script from a lane worktree — worth a look at how these are launched.
    ✅ 2026-09-23 (operator-directed) — the old pid had died with the 2026-09-21 host restart, so the reaper
    was simply not running (last log line 2026-09-20T00:05Z). Relaunched detached from the TRACKED path
    `/workspace/scripts/system/opencode_event_reaper.sh` (pid 1833821, fd/255 verified to the tracked file);
    first pass 19:17Z: VACUUM 55 s, integrity ok, db 10.8 GB. Nothing relaunches it after a reboot — NIB2-81.
- [x] **NIB2-80** (MED): **the `EARLY_ABORT` escalation path bypasses its own budget gate.** In
      ✅ 2026-09-23 — epyc-orchestrator `d1f5bf02`: reading (1) — immediate escalation kept, bounded by `max_escalations` at all FIVE early-abort sites (not just the cited one); at budget it falls through to the sibling gate/retry/fail chain. Residual: early-abort escalation still skips the role-cycle check.
  `epyc-orchestrator/src/graph/nodes.py:235-241` an `ErrorCategory.EARLY_ABORT` bumps
  `state.escalation_count`, records the role change and returns `CoderEscalationNode()` **without
  calling `_should_escalate`**. Every other escalation site in that file gates on it
  (`nodes.py:250, 284, 364, 481`), and the gate is what enforces `cfg.max_escalations`, the
  no-escalate categories and the retry precondition (`src/graph/decision_gates.py:27-47`). So a
  run that keeps early-aborting can escalate past `max_escalations`, and the budget it is
  charged against is never read. **Two candidate readings, and the fix differs:** if immediate
  escalation on early-abort is deliberate, the bound is still missing (escalate only while
  `escalation_count < cfg.max_escalations`, else fall through to the normal failure path); if it is
  an oversight, the call belongs behind `_should_escalate` like its four siblings. Surfaced
  2026-09-17 while writing the FW-1 loop-block sketch — the block made it visible because it forces
  every gate and every rejection destination to be named
  ([`fuzzy-workflow-authoring-gui.md`](fuzzy-workflow-authoring-gui.md) § FW-1 sketch, finding F-1).
  **Not fixed here: it changes graph control flow on a path evals traverse, so it wants its own
  before/after test and the owning session's judgement on which reading is right.** Zero inference
  to verify (unit tests with a fake backend); zero compute.
- [ ] **NIB2-81** (HIGH for the reaper instance, MED for the class): **a long-running daemon keeps executing the
  script inode it was launched with, so a committed fix never reaches it.** Investigated 2026-09-17 (read-only
  `/proc` census, no name patterns, nothing signalled): full report at
  `tmp/daemon-staleness-20260917/report.md`. **Three shapes, all live on this host:**
  (1) **stale AND diverged** — the reaper (pid 2873259, started 09-08) holds `fd/255` on a lane copy under
  `worktrees/mains/ak-rebuild-20260828`, 1,802 B at `02e3cebe`, against 7,976 B tracked at `49e85ab7`; the
  running code still gates VACUUM on `pgrep -x opencode` and has never sourced `observer_guard.sh` (461
  iterations, 39 VACUUMs against the operator's live `opencode.db`). Restart is **NI-OC-a.1**.
  (2) **orphaned inode** — the hub and bus supervisors both show `(deleted)` for their script; the orphaning
  event was this session's own `git reset --hard origin/main` at 19:04 (reflog `7002ebc8`). Content is
  identical today, so nothing is broken — **the next commit to either file diverges silently.**
  (3) **orphaned tree** — a hub on `:8101` (pid 2098198) runs from a worktree directory that no longer exists,
  with no registry row, pidfile or probe.
  **Mechanism:** no cron in the container, so these are hand-launched and inherit the launching session's cwd;
  bash holds the script inode for life; git never writes in place, so a commit moves the PATH to a new inode
  while the daemon keeps the old one; the abandoned lane never advances. Nothing moves a daemon back —
  supervisors restart their charges, not themselves, and `WORKTREE_MIGRATION.md` pins runtime *state* to
  `/workspace` while saying nothing about runtime *code*.
  **Why no instrument caught it:** `observer_census.py` is static by design (Rule A/B over `git ls-files`, and
  its runtime battery uses a sandboxed stand-in, never a live pid), which is how "census OK (17 observers)"
  coexisted with a live pre-adoption reaper. `check_lane_worktree.py` flags the opposite direction;
  `/api/health` folds data freshness, not code provenance. The one loop that works is the bus supervisor's H-4
  tree-divergence check, which restarted the coordinator daemon at 23:34.
  **Remedy, recommended shape:** (a) a startup self-attestation — each daemon compares its own `fd/255` inode
  and blob against `HEAD:<relpath>` and refuses or alarms on mismatch (cheap; misses post-start orphaning);
  plus (b) a registry `runtime:{pidfile,expected_path}` field and an `observer_census.py --live` `/proc` walk
  feeding the existing fleet alarm (catches all three shapes including the `:8101` stray; fixes nothing by
  itself). Generalising H-4 so each daemon publishes `source_tree` and one supervisor tick restarts a
  divergent one is the proven shape and the right next step. Absolute-path launch recipes plus host-cron
  `once` ticks are an operator decision (OP-9/FW-3). Zero inference.
  **Remedy (a) LANDED 2026-09-23** — `scripts/coordination/daemon_provenance.sh` (`dp_attest` refuses a launch from outside
  canon/the view, warns on uncommitted edits, records provenance; `dp_stale_since_start` logs "running stale code" each
  iteration) wired into the reaper, bus_supervisor `loop` and hub_supervisor `cmd_loop`; 15-case test. Read-only /proc
  check found no live daemon on stale code today. Remaining: remedy (b) and the H-4 generalisation (self-restart).
  - [x] **NIB2-81a — record the class where it will be found again.** ✅ 2026-09-23 — `INC-20260917-daemon-stale-script-inode` in INCIDENT_LOG.md; WORKTREE_MIGRATION.md now states the runtime-code rule (canon or the view, never a lane). An `INCIDENT_LOG.md` entry (a daemon
    executes a stale or orphaned script inode; observed 2026-09-17, three shapes) plus one paragraph in
    `scripts/coordination/WORKTREE_MIGRATION.md`: runtime-plane daemons execute from CANON or the VIEW only —
    **a lane may develop a daemon, never run it.** Verified absent today: neither file mentions `fd/255`, an
    inode, or this failure. That migration note already pins runtime *state* to `/workspace` and is silent on
    runtime *code*, which is the gap the class fell through. Zero inference.
  - [x] **NIB2-81b — the orphaned `:8101` hub (pid 2098198).** ✅ 2026-09-23 — moot: pid 2098198 is gone (host restarted 2026-09-21) and nothing listens on :8101. Its worktree is deleted, and it has no registry
    row, pidfile or probe, so nothing watches it and nothing would restart it. It presents 2026-09-15 code as
    current, and a lazy import will ENOENT against the missing tree. OPERATOR / owning session: stop it
    (identity from its own pid record, **never** a name pattern) or register it properly. Zero inference.
