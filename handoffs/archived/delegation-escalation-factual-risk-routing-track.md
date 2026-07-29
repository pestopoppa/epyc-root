# Handoff: Delegation/Escalation Factual-Risk Routing Track (LaCy-Aligned)

- **Created**: 2026-02-14
- **Status**: ACTIVE (research-complete, implementation-ready)
- **Priority**: High
- **Blocked by**: None
- **Primary paper**: LaCy (`arXiv:2602.12005`)

---

## 1) Executive Summary

This track adds a **factual-risk-aware delegation policy** to the orchestrator so we can make better `when to escalate/delegate` decisions than confidence/loss heuristics alone.

Core idea:
- Keep existing cheap-first, delegation, and escalation pipeline.
- Add a lightweight **risk scorer** that predicts whether low-cost roles are likely to hallucinate on the current request.
- Route based on **expected factual utility per cost**, not just retry count or generic quality heuristics.

Expected outcome:
- Higher factual accuracy on knowledge-sensitive prompts.
- Fewer wasteful escalations on low-risk prompts.
- Cleaner tuning loop via `seed_specialist_routing.py` + ClaudeDebugger.

---

## 2) Research Context and Why This Track Exists

This work sits at the intersection of four mature research threads:

1. **LLM cascades / routing for cost-quality tradeoff**
- FrugalGPT (`arXiv:2305.05176`)
- Language Model Cascades (`arXiv:2207.10342`)
- Current lesson: dynamic routing beats static single-model policies on cost-normalized quality.

2. **Learning-to-delegate / learning-to-defer**
- A Little Learning Is a Dangerous Thing (`arXiv:2206.01855`, cited by LaCy)
- Current lesson: defer policies need calibrated uncertainty + task-dependent features.

3. **Tool/decomposition pipelines for correctness**
- Toolformer (`arXiv:2302.04761`)
- PAL (`arXiv:2211.10435`)
- ReAct (`arXiv:2210.03629`)
- Current lesson: decomposition and tool-use improve reliability, but routing to those paths is the bottleneck.

4. **Post-hoc factuality checks**
- Chain-of-Verification (`arXiv:2309.11495`)
- Current lesson: late verification helps, but earlier routing with factual-risk signals can reduce downstream repair load.

### What LaCy specifically adds for us

LaCy focuses on training a model to emit `<CALL>` when a stronger backend should be invoked. The crucial finding for orchestration is:
- **Loss/confidence-only gating is insufficient.**
- Combining confidence with **token-type/factuality-sensitive signals** improves call placement and downstream factual metrics.

For this codebase, that translates to:
- Stop treating all low confidence equally.
- Prioritize escalation for **factual-risk-heavy spans/tasks**.

---

## 3) Current Architecture Assessment (Delegation/Escalation)

### A. Cheap-first gate exists but factual-risk signal is missing
- `src/api/routes/chat.py:166` implements `_try_cheap_first`.
- Gate is currently based on short-answer checks + repetition/garble heuristics from `_detect_output_quality_issue`.
- `try_cheap_first_quality_threshold` exists in config (`src/config.py:791`) but no explicit numeric quality score pipeline currently drives acceptance.
- Gap: no explicit factual-risk feature before accepting cheap answer.

### B. Review gate uses weak retrieval objective proxy
- `src/api/routes/chat_review.py:107` builds routing retrieval objective from `answer[:100]`.
- This can correlate with stylistic similarity, not factual risk.
- Gap: review trigger should be keyed by **query+claim-risk**, not answer prefix alone.

### C. Escalation policy is mostly retry-count and error-category based
- Unified policy: `src/escalation.py:218`.
- Graph fallback helpers still largely failure-count logic (`src/graph/nodes.py:677`).
- Gap: escalation decisions do not ingest task-level factual-risk features.

### D. Telemetry gaps block learning loop quality
- `src/proactive_delegation/delegator.py:151` calls `progress_logger.log_delegation(...)`, but `ProgressLogger` has no `log_delegation` method (`orchestration/repl_memory/progress_logger.py`).
- `src/api/routes/chat_pipeline/stream_adapter.py:278` calls `log_exploration(...)` without required `tokens_spent`.
- Gap: incomplete logs prevent clean reward attribution and debugger diagnostics.

### E. Strong existing assets to integrate with (good news)
- Seeding/tuning harness already present:
  - `scripts/benchmark/seed_specialist_routing.py`
  - `scripts/benchmark/seeding_eval.py`
  - `scripts/benchmark/seeding_orchestrator.py`
- Debug loop already present:
  - `docs/chapters/26-claude-debugger.md`
  - `src/pipeline_monitor/diagnostic.py`
  - `src/pipeline_monitor/claude_debugger.py`

---

## 4) Target Architecture (Decision-Complete)

### 4.1 New Control Concept

Add a **Factual Risk Scorer** producing:
- `risk_score` in `[0,1]`
- `risk_band` in `{low, medium, high}`
- `risk_features` map (for telemetry and debugging)

The scorer is used in three places:
- Cheap-first prefilter (accept/reject cheap answer path).
- Review trigger (whether architect review is required).
- Escalation override (early escalation/delegation on high factual risk).

### 4.2 Flow Integration

1. **Ingress**
- Build lightweight task signature from prompt/context.
- Compute factual-risk features before first model call.

2. **Cheap-first**
- Existing `_try_cheap_first` still runs.
- Add accept condition:
  - `expected_factual_utility(cheap_role) - cost_penalty > specialist_baseline_margin`
  - operationally approximated by threshold policy over `risk_score`, historical role Q-value, and answer quality checks.

3. **Execution + optional review**
- If cheap answer passes, still trigger review when `risk_band=high` even if generic heuristics pass.
- Replace `answer[:100]` objective proxy with structured review objective including user query and risk features.

4. **Escalation**
- Existing retry policy remains fallback.
- Add risk-aware branch:
  - high factual risk + uncertainty signals can trigger earlier escalation/delegation.

5. **Learning loop**
- Log risk features + decision + outcome.
- Use seeding harness to estimate policy frontier (factuality vs cost).
- Feed diagnostics into ClaudeDebugger to tune thresholds.

---

## 5) Interface and Data Model Additions

### 5.1 Config (`src/config.py`)

Add `ChatPipelineConfig` fields:
- `factual_risk_enabled: bool = False`
- `factual_risk_mode: str = "shadow"`  (`off|shadow|enforce`)
- `factual_risk_threshold_low: float`
- `factual_risk_threshold_high: float`
- `factual_risk_force_review_high: bool = True`
- `factual_risk_early_escalation_high: bool = False`
- `factual_risk_extractor: str = "regex"` (`regex|spacy`)

### 5.2 Response Telemetry (`src/api/protocols.py` / response model)

Add optional fields:
- `factual_risk_score: float | None`
- `factual_risk_band: str | None`
- `factual_risk_features: dict[str, float | int | str] | None`
- `delegation_policy_version: str | None`

### 5.3 Progress Logger (`orchestration/repl_memory/progress_logger.py`)

Add/extend events:
- `ROUTING_DECISION`: include risk score/band/features snapshot.
- `ESCALATION_TRIGGERED`: include risk band + escalation reason subtype.
- Add explicit `log_delegation(...)` helper aligned with current caller in proactive delegator.

---

## 6) Implementation Plan (Phased)

### Phase 0: Telemetry Integrity and Schema Readiness (must-do first)

Files:
- `orchestration/repl_memory/progress_logger.py`
- `src/proactive_delegation/delegator.py`
- `src/api/routes/chat_pipeline/stream_adapter.py`
- `src/api/routes/chat.py`

Actions:
- Implement missing `log_delegation(...)` method (or redirect caller to existing method with correct schema).
- Fix `log_exploration(...)` calls to always include `tokens_spent`.
- Add versioned policy metadata (`delegation_policy_version`) to routing logs.

Acceptance:
- No runtime logging exceptions in delegated/streaming paths.
- New fields visible in progress JSONL and diagnostic records.

### Phase 1: Factual-Risk Feature Extractor (shadow-only)

Files:
- `src/api/routes/chat_pipeline/routing.py`
- new module `src/routing/factual_risk.py` (or equivalent)

Features (fast, deterministic):
- query intent flags: asks-for-facts/dates/names/citations.
- claim density estimate.
- uncertainty lexical markers.
- optional spaCy mode (noun-phrase/entity ratios) behind config flag.

Acceptance:
- Extractor p95 overhead < 5ms in regex mode, < 15ms in spaCy mode.
- Feature dictionary stable across runs.

### Phase 2: Router and Cheap-First Integration

Files:
- `src/api/routes/chat.py` (`_try_cheap_first`)
- `src/api/routes/chat_routing.py`
- `src/api/routes/chat_pipeline/routing.py`

Policy:
- In `shadow`: compute and log only, no behavior change.
- In `enforce`: apply thresholds:
  - `risk <= low`: favor cheap-first.
  - `low < risk < high`: current behavior + review sensitivity.
  - `risk >= high`: bypass cheap-first or require strict pass criteria.

Acceptance:
- Shadow parity: no route changes when mode is `shadow`.
- Enforce mode toggles route frequencies according to risk bands.

### Phase 3: Review and Escalation Coupling

Files:
- `src/api/routes/chat_review.py`
- `src/escalation.py`
- `src/graph/nodes.py`

Actions:
- Replace review objective proxy (`answer[:100]`) with structured objective containing prompt + risk signature.
- Add risk-aware escalation branch in unified policy and graph fallback helpers.
- Keep retry-count logic as fallback path.

Acceptance:
- High-risk prompts exhibit higher review/escalation rates without broad escalation inflation.

### Phase 4: Seed/Eval/Debugger Integration

Files:
- `scripts/benchmark/seed_specialist_routing.py`
- `scripts/benchmark/seeding_types.py`
- `scripts/benchmark/seeding_eval.py`
- `src/pipeline_monitor/diagnostic.py`
- `src/pipeline_monitor/claude_debugger.py`

Actions:
- Persist risk fields in role results and diagnostics.
- Add tuning knobs and sweeps for risk thresholds.
- Emit Pareto reports: factuality vs cost vs latency.

Acceptance:
- Debugger can recommend threshold updates from empirical runs.
- Seeding outputs include risk-stratified metrics.

### Phase 5: Controlled Rollout

Rollout stages:
- `off` -> `shadow` (7 days of traffic replay/live shadow)
- `shadow` -> `enforce` on selected roles/tenants
- Global enable if KPI gates pass

Rollback:
- Single config switch to `off`.
- Keep legacy routing path untouched during first release.

---

## 7) Evaluation and KPI Framework

Primary KPI:
- **Factuality@Cost** (weighted factual score normalized by token+latency budget)

Secondary KPIs:
- escalation rate by risk band
- cheap-first pass rate by risk band
- review trigger precision for high-risk bucket
- p50/p95 latency and token cost deltas

Offline eval set composition:
- factual Q&A with date/entity sensitivity
- mixed coding + factual prompts
- low-risk conversational controls

Online safety gates:
- no >10% latency regression at p95
- no >5% token-cost regression at equal factuality
- factual metric uplift in medium/high-risk slices

---

## 8) Test Plan (Required Before Enable)

Unit tests:
- extractor determinism and threshold banding
- policy transitions (`off/shadow/enforce`)
- escalation/review branching with risk inputs
- logger schema coverage for new fields

Integration tests:
- chat direct + delegated + streaming paths include risk telemetry
- no exceptions in progress logger calls
- seeding pipeline reads/writes new diagnostic fields

Regression tests:
- existing orchestration routing tests remain green
- shadow mode yields route-equivalent behavior vs baseline

---

## 9) Risks and Mitigations

Risk: false positives over-escalate and increase cost.
- Mitigation: shadow calibration first, hard caps, hysteresis thresholds.

Risk: spaCy feature extraction adds latency.
- Mitigation: regex extractor as default; spaCy optional and benchmarked.

Risk: metric gaming (policy overfits proxy, not factuality).
- Mitigation: evaluate with independent factual metrics and holdout sets.

Risk: telemetry drift breaks tuning loop.
- Mitigation: schema versioning + contract tests in seeding/debugger path.

---

## 10) Defaults Chosen (to avoid implementation ambiguity)

- Start with **telemetry-first** rollout.
- Default extractor: `regex`.
- Default deployment mode: `shadow`.
- Default optimizer target: maximize **Factuality@Cost**, not raw cheap-first pass rate.
- Keep existing escalation/retry behavior as fallback until `enforce` passes gates.

---

## 11) Literature References (Research Track)

Core track:
- LaCy: Learning to Call in Pretraining. `https://arxiv.org/abs/2602.12005`
- FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance. `https://arxiv.org/abs/2305.05176`
- Language Model Cascades. `https://arxiv.org/abs/2207.10342`
- A Little Learning Is a Dangerous Thing (Learning to Defer with One-Sided Feedback). `https://arxiv.org/abs/2206.01855`

Delegation/tooling/reliability context:
- Toolformer. `https://arxiv.org/abs/2302.04761`
- PAL: Program-aided Language Models. `https://arxiv.org/abs/2211.10435`
- ReAct. `https://arxiv.org/abs/2210.03629`
- Chain-of-Verification Reduces Hallucination in Large Language Models. `https://arxiv.org/abs/2309.11495`

Additional papers explicitly cited in LaCy refs and relevant to this track:
- Learning to Route LLMs with Preference Data. `https://arxiv.org/abs/2501.12388`
- Dynamic LLM Routing from Benchmarking to Policy Learning. `https://arxiv.org/abs/2504.12337`
- Self-Adaptive Language Toolkit. `https://arxiv.org/abs/2305.11711`

Internal architecture references:
- `docs/chapters/10-orchestration-architecture.md`
- `docs/chapters/18-escalation-and-routing.md`
- `docs/chapters/21-benchmarking-framework.md`
- `docs/chapters/26-claude-debugger.md`
- `docs/guides/model-routing.md`

---

## 12) Immediate Next Session Checklist

1. Land Phase 0 telemetry integrity fixes.
2. Add risk extractor module and shadow logging (Phase 1).
3. Wire seeding/diagnostic fields for threshold tuning.
4. Run initial seeding benchmark sweep and produce first Pareto report.
5. Decide enforce-mode activation based on KPI gates.
