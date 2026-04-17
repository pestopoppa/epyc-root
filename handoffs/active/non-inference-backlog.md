# Non-Inference Backlog — Round 2 (2026-04-17 audit refresh)

**Status**: ACTIVE — 28 unblocked non-inference tasks catalogued across all active handoffs
**Created**: 2026-02 (Round 1, 18/18 complete → [`completed/non-inference-backlog.md`](../completed/non-inference-backlog.md))
**Refreshed**: 2026-04-17 (Round 2 catalogue from cross-cutting audit of all active handoffs)
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

- [ ] **NIB2-01**: REPL S5 Gap 3 `_batch_llm_query()` combined-op — [`repl-turn-efficiency.md`](repl-turn-efficiency.md) L171-174. ~3-4h. HIGH impact / LOW effort (infrastructure exists; just expose `llm_batch()` as first-class REPL tool).
- [ ] **NIB2-02**: EV-3 Scoring Verifiers adapter — [`eval-tower-verification.md`](eval-tower-verification.md) L151-157. 2-3h. Download `nvidia/Scoring-Verifiers`, create ~50-line adapter, register in `suites.py`.
- [ ] **NIB2-03**: EV-0 MathQ-Verify dataset audit — [`eval-tower-verification.md`](eval-tower-verification.md) L129. 4-6h. Zero-code data cleaning (stages 1-4).
- [ ] **NIB2-04**: DAR-2 unit test for `_compute_contrastive_adjustment()` with mock store — [`decision-aware-routing.md`](decision-aware-routing.md) L74. 2h. Explicitly deferred in handoff.
- [ ] **NIB2-05**: Frontdoor top-k=64 first-token log-probability instrumentation — [`learned-routing-controller.md`](learned-routing-controller.md) L132-135 P1.5.1. 2-4h. (Collection needs volume; instrumentation is code only.)
- [ ] **NIB2-06**: Vision tool registry registration in orchestrator — [`multimodal-pipeline.md`](multimodal-pipeline.md) L44. 2-4h. Pure code, unblocks proactive vision delegation.
- [ ] **NIB2-07**: Move `blocked/retrain-routing-models.md` to `archived/` — 5 min once directory permissions fixed. Superseded by Learned Routing Controller Phase 1 (2026-04-15).
- [ ] **NIB2-08**: AP-21 GEPA ratio knob scaffolding — [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md). ~4h. Ratio-adjustable code path; flip decision gated on AR-3 data but the knob itself is code-only.

## Investigation (code-reading / root-cause analysis)

- [ ] **NIB2-09**: Per-request `</think>` budget investigation on Qwen3.5 hybrid SSM+MoE — [`per-request-reasoning-budget.md`](per-request-reasoning-budget.md) L45-50. 1-2 days. 4-step plan in llama.cpp-experimental: search `server.cpp`/`common/chat.cpp`/`src/llama-sampling.cpp`, trace hybrid code path, propose fix (`</think>` injection timing vs SSM state update). Steps 3-4 need a running server — keep them out of scope.
- [ ] **NIB2-10**: Integration-test-coverage residual unit gaps — [`integration-test-coverage.md`](integration-test-coverage.md) L127-132. 4-8h. Remaining edges in `graph/task_ir_helpers.py`, `graph/budgets.py`, `graph/answer_resolution.py` — test-only writes, no new code paths.
- [ ] **NIB2-11**: Package F post-hoc analysis — [`bulk-inference-campaign.md`](bulk-inference-campaign.md). 4-6h. Data already collected; analysis is log-parsing and chart generation.

## Medium-effort implementation (multi-day, no inference required)

- [ ] **NIB2-12**: `parallel_seeding.py` + `seeding_port_sets.py` — [`parallel-seeding-eval.md`](parallel-seeding-eval.md) L29-32. ~200 LoC, 1 day. Unlocks 2× AR-3 throughput. No blockers.
- [ ] **NIB2-13**: OpenDataLoader Phase 1 swap in `pdf_router.py` — [`opendataloader-pipeline-integration.md`](opendataloader-pipeline-integration.md) L36-44. 1-2 days. JVM lifecycle + swap `pdftotext -layout` for `opendataloader_pdf.convert(...)`, retain entropy/garbage quality checks, update `tests/services/test_pdf_router.py`.
- [ ] **NIB2-14**: Clone `opendataloader-bench`, add `document_extraction` suite with NID/TEDS/MHS scoring — [`opendataloader-pipeline-integration.md`](opendataloader-pipeline-integration.md) L95-107. 1 day.
- [ ] **NIB2-15**: Goedel-CP-8B GGUF conversion + Q4_K_M/Q8_0 quantization — [`lean-proving-pipeline.md`](lean-proving-pipeline.md) S1 (queued-for-blocked, but conversion is non-inference and 4-6h). Quality validation is inference-gated.
- [ ] **NIB2-16**: DAR-3 SPO+ with exploration — [`decision-aware-routing.md`](decision-aware-routing.md) L82-92. ~100 lines in `q_scorer.py` + `retriever.py`; convex surrogate + 10% epsilon-greedy. 3-4 sessions. Code is independent of inference; counterfactual data accumulates downstream.
- [ ] **NIB2-17**: DAR-4 bilinear scorer — [`decision-aware-routing.md`](decision-aware-routing.md) L97-113. ~200 lines, new `bilinear_scorer.py`. 4-5 sessions. Independent of DAR-3; developable in parallel.
- [ ] **NIB2-18**: DS-6 QuarterScheduler scaffolding — [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) § DS-6. 2-3 days. Design is complete (6 gaps resolved 2026-04-09); code-only implementation while Phase E inference runs later.
- [ ] **NIB2-19**: DS-7 stack-template YAML schema + `--stack-profile` CLI — [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) § DS-7. 1-2 days. 4 gaps resolved 2026-04-09; implementation deferred but no blockers.
- [ ] **NIB2-20**: Attention Matching layer-adaptive compression — [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md). ~1 day. Layer-adaptive keep_ratio code (early 10×, middle 5×, deep 2×). P2 benchmarks need inference; code itself does not.
- [ ] **NIB2-21**: ColBERT reranker module scaffolding — [`colbert-reranker-web-research.md`](colbert-reranker-web-research.md) S5. 2h code + eventually 2h inference A/B. `src/tools/web/colbert_reranker.py`: ONNX session, tokenizer, MaxSim, lazy model loading, feature flag.
- [ ] **NIB2-22**: Tool-output-compression P3d harness scaffolding — [`tool-output-compression.md`](tool-output-compression.md) L259. 2-4h. Comparison harness setup is code; A/B execution is inference.
- [ ] **NIB2-23**: REPL S5 Gap 1 `workspace_scan` combined-op (frecency-only fallback) — [`repl-turn-efficiency.md`](repl-turn-efficiency.md). 4-6h. Frecency-ranked file list + code_search summary. Sub_lm quality validation (Gap 1 full) is blocked on AP-26; frecency-only fallback is not.
- [ ] **NIB2-24**: REPL S5 Gap 2 `STUCK("reason")` signal — [`repl-turn-efficiency.md`](repl-turn-efficiency.md) L174. 6-8h. In `context.py` alongside `FINAL()`, logs + episodic recall for recovery patterns.
- [ ] **NIB2-25**: Context Folding Phase 3c `CompactionQualityMonitor` class — [`context-folding-progressive.md`](context-folding-progressive.md) L645-712. 4-6h. Class + wiring is code; telemetry validation against live traffic is inference-gated.
- [ ] **NIB2-26**: Context Folding Phase 3b `role_aware_compaction` flag + per-role `CompactionProfile` — [`context-folding-progressive.md`](context-folding-progressive.md) L576-643. 1-2 days. Code-only; profile tuning lands later.
- [ ] **NIB2-27**: MathSmith canonicalizer proposal retire/rewrite — [`mathsmith-hc-formalizer-eval.md`](mathsmith-hc-formalizer-eval.md) S5. 2h. Pure docs cleanup.

## Infra & governance

- [ ] **NIB2-28**: Coverage gate floor raises per Phase B plan — [`integration-test-coverage.md`](integration-test-coverage.md). 1-2h. Policy-only bumps; tests already at the higher floors.
- [ ] **NIB2-29**: `orchestrator_stack.py` port-doc update for 8080-8084 / 8180-8184 stream split (if NIB2-12 adopted) — [`parallel-seeding-eval.md`](parallel-seeding-eval.md). <1h.
- [ ] **NIB2-30**: GitNexus post-commit hook embeddings-preservation verification — [`CLAUDE.md`](../../CLAUDE.md) § Keeping the Index Fresh. 1h. Verify hook handles `--embeddings` flag correctly.

---

## Items explicitly excluded (blocked or inference-required)

These are *non-inference in nature* but gated on external signals. Listed so the gate is visible, not to pick up:

- `readme-refresh.md` — GATED on AR-3 trial ≥100 (currently ~78). Pick up when autopilot journal hits 100 trials.
- `root-archetype-linter-templates-upstream.md` — Gated on local clone of the `root-archetype` repo.
- DAR-3/DAR-4 validation passes — code is NIB2-16/17; measurement is inference.
- REPL S4 A/B — A/B itself is inference; scaffolding (not listed here) would be ~4h code.
- Qwen3.6 benchmark — [`qwen36-production-upgrade.md`](qwen36-production-upgrade.md) — inference-gated. Download already done.
- Package D post-AR-3 analyses — blocked on AR-3 completion.
- MathSmith S2 HC benchmark + S3 drafter spec decode tests — inference-gated.

---

## Reporting protocol

When you complete an NIB2-NN item:
1. Check the box here.
2. Update the linked canonical handoff's TODO / next-steps section to match.
3. Add a one-line entry in `progress/YYYY-MM/YYYY-MM-DD.md`.
4. If the item belonged to a phased handoff (e.g. "Phase 2c ByteRover enhancement"), bump that handoff's status line.
5. On completing all 30 items: move this file to `completed/` as Round 2, and run a fresh audit to open Round 3.

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
