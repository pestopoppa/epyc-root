# Routing Intelligence: Semantic Classifiers + Factual-Risk Routing

**Created**: 2026-02-18 (consolidated from `classifier-refactoring.md` + `delegation-escalation-factual-risk-routing-track.md`)
**Last audited**: 2026-03-24
**Status**: PHASES 0-3 COMPLETE — Phase 3 shadow mode active since 2026-03-15 — Phases 4-6 enforcement deferred
**Priority**: HIGH
**Blocked by**: Nothing (Phase 3 shadow active, Phase 4 needs calibration dataset before enforce)

---

## Problem

Two interrelated quality gaps in routing/escalation decisions:

1. **9 brittle heuristics** scattered across route modules (`_is_summarization_task`, `_should_use_direct_mode`, `_detect_output_quality_issue`, etc.) — keyword-based, fragile, caused regressions (e.g., date injection: 70% → 45.5%).
2. **No factual-risk signal** in routing — cheap-first accepts/rejects without considering hallucination risk, review triggers use `answer[:100]` as proxy, escalation is retry-count-based only.

These are the same problem: routing decisions lack semantic understanding of the input and output.

---

## Solution: Unified `src/classifiers/` Module

One classifier module serves both needs. Three classifier categories:

| Category | Purpose | Backing | Replaces |
|----------|---------|---------|----------|
| **A: Input** | Classify prompt intent, detect summarization/vision/direct-mode/factual-risk | MemRL embeddings + keyword fallback | `_is_summarization_task`, `_needs_structured_analysis`, `_should_use_direct_mode`, `_is_ocr_heavy_prompt` |
| **B: Output** | Parse verdicts, detect stubs, strip tool noise | Config-driven regex from YAML | `_is_stub_final`, `_strip_tool_outputs`, verdict parsing |
| **C: Quality** | Detect repetition, garble, quality issues + factual risk scoring | Configurable thresholds + risk features | `_detect_output_quality_issue` + new factual-risk scorer |

The factual-risk scorer (from LaCy research) becomes a Category C classifier producing `risk_score`, `risk_band`, and `risk_features` — used by cheap-first, review trigger, and escalation policy.

**Key principle**: New categories = YAML edits, not code changes. Everything in `orchestration/classifier_config.yaml`.

---

## Files Created (Phases 1-2)

| File | Purpose |
|------|---------|
| `src/classifiers/__init__.py` | Public API + lazy singletons (exports `get_classification_retriever()`) |
| `src/classifiers/types.py` | Dataclasses (ClassificationResult, RoutingDecision, MatcherConfig) |
| `src/classifiers/keyword_matcher.py` | Keyword-based classifiers (summarization, coding, stub, etc.) |
| `src/classifiers/output_parser.py` | Structured output parsing (stub, verdict, tool stripping) |
| `src/classifiers/quality_detector.py` | Quality detection (`detect_output_quality_issue()`) |
| `src/classifiers/config_loader.py` | YAML config loading |
| `src/classifiers/classification_retriever.py` | MemRL-backed classification (315 lines, Q-value weighted voting) |
| `orchestration/classifier_config.yaml` | All keywords, patterns, thresholds, output_parsing, exemplars |
| `tests/unit/test_classifiers.py` | 61 unit tests, all passing |

## Files Still to Create (Phases 3-6)

| File | Purpose |
|------|---------|
| ~~`src/classifiers/factual_risk.py`~~ | ✅ Created (2026-03-05) — regex-only scorer, 43 tests |

## Files Still to Modify (Phases 3-6)

| File | Changes |
|------|---------|
| ~~`orchestration/repl_memory/progress_logger.py`~~ | ✅ `log_delegation()` implemented, `delegation_policy_version` added (Phase 0) |
| `src/classifiers/quality_detector.py` | Integrate factual-risk scoring |
| `src/api/routes/chat.py` | Risk-aware condition in `_try_cheap_first` (line ~208) — Phase 4 enforce |
| ~~`src/api/routes/chat_pipeline/routing.py`~~ | ✅ Shadow-mode scoring wired into `_route_request()`, risk on `RoutingResult` (2026-03-06). Plan review gate integration still pending (Phase 4 enforce). |
| ~~`src/escalation.py`~~ | ✅ `risk_score`, `risk_band` added to `EscalationContext` (2026-03-05) |
| `scripts/benchmark/seeding_types.py` | ⚠️ Risk fields NOT on `RoleResult` — claimed complete 2026-03-06 but verification (2026-03-24) shows fields absent. Re-add in Phase 5. |

---

## Implementation Phases

### Phase 0: Telemetry Integrity (prerequisite) — ✅ COMPLETE (2026-03-05)

| Item | Status | Detail |
|------|--------|--------|
| `log_delegation()` in `progress_logger.py` | **FIXED** | Implemented at line ~249. Logs `DELEGATION_DECISION` event with complexity, action, confidence, and policy version. Resolves broken call from `delegator.py:153`. |
| `log_exploration()` missing `tokens_spent` | **FIXED** | Parameter exists in signature at `progress_logger.py:329-353`, actively used |
| `delegation_policy_version` in routing logs | **FIXED** | Added to both `DELEGATION_DECISION` and `ROUTING_DECISION` events. Version `"1.0"` is `ProgressLogger.DELEGATION_POLICY_VERSION` class constant. |

### Phase 1: Types + Config + Output Parsers — ✅ COMPLETE (2026-02-19)

All 9 heuristics now delegate to `src/classifiers/`:
- `src/classifiers/types.py` — ClassificationResult, RoutingDecision, MatcherConfig
- `src/classifiers/keyword_matcher.py` — is_summarization_task, is_coding_task, is_stub_final, needs_structured_analysis, should_use_direct_mode, classify_and_route
- `src/classifiers/output_parser.py` — strip_tool_outputs, truncate_looped_answer
- `src/classifiers/quality_detector.py` — detect_output_quality_issue
- `src/classifiers/config_loader.py` — YAML config loading
- `orchestration/classifier_config.yaml` — all keywords, patterns, thresholds, output_parsing
- Original functions in chat_utils.py and chat_review.py are thin delegating wrappers (zero import breakage)
- 61 unit tests in test_classifiers.py, all passing
- **Exit criteria met**: all heuristics delegate to classifiers, existing behavior preserved

### Phase 2: Input Classifier + MemRL Integration — ✅ COMPLETE (built independently)

Built as part of the MemRL subsystem, not tracked in this handoff at the time:

- `src/classifiers/classification_retriever.py` — `ClassificationRetriever` with `classify_prompt()`, `classify_for_routing()`, `should_use_direct_mode()`, Q-value weighted voting, fallback logic (315 lines)
- `orchestration/repl_memory/retriever.py` — `retrieve_for_classification()` at lines 275-294, filters by `action_type="classification"`
- `src/classifiers/__init__.py` — exports `get_classification_retriever()` (lazy singleton)
- `orchestration/classifier_config.yaml` — `classification_exemplars` section with routing, coding, architecture categories

**Exemplar seeding gap closed (2026-03-06)**: `src/api/__init__.py` lifespan now calls `seed_memory(force=False)` after MemRL initialization. Auto-seeds classification exemplars from YAML on first startup; no-op on subsequent starts if store already has memories.

### Phase 3: Factual-Risk Scorer (shadow mode) — ✅ COMPLETE (shadow since 2026-03-15)

Scorer implemented in `src/classifiers/factual_risk.py` (280 lines, regex-only, 43 tests passing).
Pipeline wiring complete (2026-03-06) — `_route_request()` calls `assess_risk()` when mode != "off", attaches score/band to `RoutingResult`. **Activated to shadow mode 2026-03-15** — factual risk score/band now logged on every request in `routing_meta` alongside `difficulty_score`/`difficulty_band`.

**What was built**:
- `src/classifiers/factual_risk.py` — `assess_risk(prompt, context, role)` → `FactualRiskResult`
- Features: `has_date_question`, `has_entity_question`, `has_citation_request`, `claim_density`, `uncertainty_markers`, `factual_keyword_ratio`
- Per-role adjusted risk via capability tiers (see design below)
- Config: `orchestration/classifier_config.yaml` → `factual_risk.mode: shadow`
- Regex-only, no spaCy dependency

**Design requirements to carry forward to Phase 4**:
1. **Conformal prediction interaction** — HybridRouter already gates routing via conformal prediction with budget guardrails (`retriever.py`). The factual-risk scorer COMPLEMENTS this: conformal prediction gates on model uncertainty (output-side), factual-risk gates on prompt characteristics (input-side). They should not conflict — risk score feeds as an additional signal, not a replacement. If conformal prediction already rejects a routing, factual-risk should not override.
2. **Per-role risk calibration** — A factual question routed to `architect_general` (122B) vs `worker_general` (7B) has very different actual hallucination risk. `FactualRiskResult` includes `adjusted_risk_score` that factors in the assigned role's capability tier.
3. **Calibration dataset** — Unlike the input classifier which has seeded exemplars, the risk scorer has no ground-truth dataset. Before moving from shadow to enforce, we need a labeled set of prompts with known factual-risk levels. Source candidates: simpleqa failures, seeding diagnostic logs with `passed=False` on factual suites.

**Exit criteria met**: Risk features logged on every request, p95 overhead < 5ms (regex mode)

### Phase 4: Risk-Aware Routing (enforce mode) — NOT STARTED

Wire risk outputs into routing decisions:

| Integration Point | Current Location | Change |
|-------------------|------------------|--------|
| Cheap-first bypass | `src/api/routes/chat.py:_try_cheap_first` (~line 208) | `risk >= high` → bypass or strict pass criteria |
| Plan review gate | `src/api/routes/chat_pipeline/routing.py:_plan_review_gate` | `risk_band=high` → force review even if generic heuristics pass |
| Escalation policy | `src/escalation.py:EscalationPolicy.decide()` | Add `risk_score: float` and `risk_band: str` to `EscalationContext` dataclass; high risk + uncertainty → earlier escalation |
| Failure graph veto | `src/api/routes/chat_pipeline/routing.py:_route_request` (line ~48+) | Hardcoded `risk > 0.5` threshold should be modulated by factual-risk band |
| Review objective | `src/api/routes/chat_review.py` | Replace `answer[:100]` proxy with structured objective |

**Design requirements** (from audit):
1. **EscalationContext extension** — Add fields to existing dataclass (currently has: `current_role`, `failure_count`, `error_category`, `error_message`, `gate_name`, `task_id`, `escalation_count`, `max_retries`, `target_role_requested`, `solution_file`, `scratchpad_entries`). New fields: `risk_score: float = 0.0`, `risk_band: str = "low"`.
2. **Structured review objective** — Specify format: `{"task_type": str, "risk_band": str, "key_claims": list[str], "verification_focus": str}` instead of raw `answer[:100]`.
3. **A/B test methodology** — Before global enable: run seeding harness with `factual_risk_mode=enforce` vs `off` on identical question set. Compare: simpleqa F1, escalation rate, cost per question, p95 latency. Minimum 500 questions per arm. Significance threshold: p < 0.05 on primary metric.

**Exit**: High-risk prompts show higher review/escalation rates without broad inflation

### Phase 5: Seeding/Eval/Debugger Integration — NOT STARTED

- Add risk fields to `RoleResult` in `scripts/benchmark/seeding_types.py` (exists at line 167, already has extensive fields including `cheap_first_attempted`, `think_harder_attempted`, etc.)
- Add threshold sweep support in seeding harness
- Emit Pareto reports: factuality vs cost vs latency

**Integration with existing infrastructure** (from audit):
- `seed_specialist_routing.py` and `question_pool.py` already exist with 53K questions across 19 benchmark suites
- Risk fields should be added to the existing `RoleResult` dataclass, not a new structure
- Threshold sweep should reuse the existing seeding `--suite` mechanism
- Pareto visualization: generate CSV + matplotlib scatter (no new tooling dependency)

### Phase 6: Controlled Rollout — NOT STARTED

| Stage | Duration | Scope | Validation |
|-------|----------|-------|------------|
| `off` | Current | All roles | N/A |
| `shadow` | 7 days | All roles | Verify risk scores are populated, p95 overhead < 5ms, no errors |
| `enforce` canary | 3 days | `frontdoor` role only (highest volume, most diverse queries), 25% of requests | Compare factuality F1, escalation rate, cost vs shadow baseline |
| `enforce` expand | 7 days | `frontdoor` 100% + `worker_general` | Same metrics, wider coverage |
| `enforce` global | Ongoing | All roles | Monitor dashboards |

**Rollback criteria**: Revert to `shadow` if ANY of:
- p95 latency regression > 10% vs baseline
- Cost regression > 5% at equal factuality
- Escalation rate increase > 20% without corresponding factuality improvement
- Any 5xx errors attributed to risk scoring path

---

## Integration Map

The following production-grade routing subsystems exist and must be accounted for in Phases 3-6. This section was added during the 2026-03-05 audit — the original handoff was blind to these systems.

| System | Location | Feature Flag | Status | Interaction with Factual-Risk |
|--------|----------|--------------|--------|-------------------------------|
| **RoutingClassifier MLP** | `orchestration/repl_memory/routing_classifier.py` | `routing_classifier=False` | Implemented, off | Fast-path bypasses retrieval. Risk scoring must run AFTER MLP decision (risk is prompt-side, MLP is routing-side — no conflict, but risk should be logged alongside MLP predictions for calibration) |
| **GraphRouter + GAT** | `orchestration/repl_memory/routing_graph.py`, `graph_router_predictor.py` | `graph_router=False` | Implemented, off | Blend formula needs risk-aware weighting when enabled. Risk band should be an input feature to the GAT, not a post-hoc filter |
| **BindingRouter** | `src/routing_bindings.py` | `binding_routing=False` | Implemented, off | Risk override priority should be between Q_VALUE (20) and USER_PREF (30) — user preference always wins, but risk can override learned Q-values |
| **FailureGraph veto** | `src/api/routes/chat_pipeline/routing.py:_route_request` (line ~48+) | Always active | **Production** | Hardcoded `risk > 0.5` threshold. Factual-risk should modulate this: high factual-risk prompts should have a LOWER failure-veto threshold (more conservative), low-risk prompts can tolerate higher failure risk |
| **Conformal prediction risk gate** | `orchestration/repl_memory/retriever.py` (HybridRouter) | Always active | **Production** | Already does risk-gating on OUTPUT uncertainty. Factual-risk scores INPUT characteristics. Complementary signals — must not double-gate (if conformal already rejects, factual-risk is moot) |
| **Think-harder in EscalationPolicy** | `src/escalation.py` (lines 347-358) | Always active | **Production** | Penultimate retry uses CoT boost. Risk-aware escalation should trigger think-harder EARLIER for high-risk prompts (before penultimate retry) |
| **Cost-aware Q-scoring** | `orchestration/repl_memory/q_scorer.py` | Always active | **Production** | Risk score should feed into reward shaping: high-risk prompts that produce correct answers should get a reward bonus (model handled a hard case) |
| **Plan review gate** | `src/api/routes/chat_pipeline/routing.py:_plan_review_gate` | `plan_review=True` | **Production** | High factual-risk should lower the plan review trigger threshold |
| **SkillAugmentedRouter** | `src/api/routes/chat_pipeline/routing.py` (via `route_with_skills`) | `skillbank=False` | Implemented, off | Skills may change risk profile — e.g., a "web_search" skill reduces factual-risk because it can verify claims. Skill presence should attenuate risk score |
| **HypothesisGraph** | Graph nodes | Active | **Production** | Per-action confidence is complementary to factual-risk. Could be combined: hypothesis confidence × (1 - factual_risk) = routing confidence |

---

## Factual-Risk Scorer Design

```python
@dataclass
class FactualRiskResult:
    risk_score: float           # [0, 1] — raw prompt-based risk
    adjusted_risk_score: float  # [0, 1] — adjusted for assigned role capability
    risk_band: str              # "low" | "medium" | "high"
    risk_features: dict         # for telemetry/debugging
    role_adjustment: float      # multiplier applied (e.g., 0.6 for 122B+, 1.0 for 7B)

def assess_risk(prompt: str, context: str = "", role: str = "") -> FactualRiskResult:
    features = _extract_features(prompt)
    raw_score = _compute_score(features)
    adjustment = _role_capability_factor(role)  # lower for stronger models
    adjusted = raw_score * adjustment
    band = _band(adjusted)
    return FactualRiskResult(raw_score, adjusted, band, features, adjustment)
```

Features (fast, deterministic, regex-only):
- `has_date_question`, `has_entity_question`, `has_citation_request`
- `claim_density` (assertion-like sentence ratio)
- `uncertainty_markers` (hedging language count)
- `factual_keyword_ratio`

Role capability tiers for adjustment (updated 2026-03-24 for current production stack):
- Tier 1 (122B+ models — architect_general 122B, architect_coding 480B): adjustment = 0.6
- Tier 2 (30B-35B models — frontdoor 35B, coder_escalation 32B): adjustment = 0.8
- Tier 3 (3B-7B models — worker_explore 30B-A3B, worker candidates): adjustment = 1.0

---

## Actual Config Shape (`orchestration/classifier_config.yaml`)

The config uses these top-level sections (aligned with Phase 1 implementation):

```yaml
keyword_matchers:
  summarization:
    keywords: ["summarize", "summary", "tldr", ...]
    case_sensitive: false
  structured_analysis:
    keywords: [...]
    case_sensitive: false
  coding_task:
    keywords: [...]
    case_sensitive: false
  stub_final:
    patterns: [...]
    normalize: true

routing_classifiers:
  direct_mode:
    context_threshold: 500
    repl_indicators: ["implement", "write code", ...]
    use_memrl: true
  specialist_routing:
    use_memrl: true
    categories:
      summarization: { keywords: [...] }
      coding: { keywords: [...] }

quality_detection:
  repetition_unique_ratio: 0.3
  garbled_short_line_ratio: 0.7
  min_answer_length: 10
  prefix_strip: [...]
  # Note: source of truth for thresholds is ChatPipelineConfig in src/config.py

output_parsing:
  tool_output_delimiter: "---"
  tool_prefix_patterns: [...]
  loop_detection_probe_chars: 200
  loop_min_answer_keep: 50

classification_exemplars:
  summarization:
    - { prompt: "...", expected_role: "worker_general" }
  coding:
    - { prompt: "...", expected_role: "worker_general" }
  complex_coding:
    - { prompt: "...", expected_role: "coder_general" }
  architecture:
    - { prompt: "...", expected_role: "architect_general" }

# --- Phase 3 additions (to be added) ---
factual_risk:
  mode: shadow  # off|shadow|enforce — shadow since 2026-03-15
  threshold_low: 0.3
  threshold_high: 0.7
  force_review_high: true
  early_escalation_high: false
  role_adjustments:
    tier_1: 0.6  # 122B+ (architect_general 122B, architect_coding 480B)
    tier_2: 0.8  # 30B-35B (frontdoor 35B, coder_escalation 32B)
    tier_3: 1.0  # 3B-7B (workers, candidates)
```

---

## Baselines (updated 2026-03-24)

Current metrics to measure Phase 4-6 impact against. **Re-measure before starting enforce mode.**

### Known Values (from comprehensive sweep 2026-03-21 + frontdoor benchmark 2026-03-19)

| Role | Model | Per-instance t/s | Instances | Aggregate t/s | Quality |
|------|-------|-------------------|-----------|---------------|---------|
| frontdoor | Qwen3.5-35B-A3B Q4KM moe6 | **12.7** | 4 | ~50.8 | 83% (151/183) |
| coder_escalation | Qwen2.5-Coder-32B Q4KM dm=32 | **10.8** | 4 | ~43.3 | 74% (133/183) |
| architect_general | Qwen3.5-122B-A10B Q4KM | **4.3** | 1 | 4.3 | 2.57 avg |
| architect_coding | Qwen3-Coder-480B Q4KM dm=24 | **7.0** | 1 | 7.0 | Unscored |
| worker_explore | Qwen3-Coder-30B-A3B Q4KM | **39.1** | 1 | 39.1 | — |

### Q-Scorer `baseline_tps_by_role` (q_scorer.py, updated 2026-03-21)

⚠️ **Frontdoor discrepancy**: Q-scorer uses 19.6 t/s (moe6+lookup) but lookup is disabled since 2026-03-19 (segfault). Actual per-instance is 12.7 t/s (moe6-only). **This inflates frontdoor cost penalty by ~1.5x**, systematically under-penalizing frontdoor routing cost. Should be corrected to 12.7 when confirmed stable.

### Still TBD (need seeding baseline sweep)

| Metric | Source | Notes |
|--------|--------|-------|
| simpleqa F1 | Seeding harness | Threshold 0.5 (lowered from 0.8 on 2026-03-03) |
| Escalation rate (frontdoor) | Seeding harness | Need baseline run |
| Escalation rate (worker) | Seeding harness | Need baseline run |
| Cheap-first pass rate | Seeding harness | Need baseline run |
| p50/p95 latency | `/mnt/raid0/llm/tmp/inference_tap.log` | Need baseline run |
| Cost per question (avg tokens) | Seeding harness | Need baseline run |

**Action item**: Run baseline seeding sweep (`seed_specialist_routing.py --suite thinking,coder,simpleqa`) before starting Phase 4 enforce mode.

---

## Research References

- LaCy: `arXiv:2602.12005` (factual-risk-aware call placement)
- FrugalGPT: `arXiv:2305.05176` (LLM cascades/routing)
- Language Model Cascades: `arXiv:2207.10342`
- Chain-of-Verification: `arXiv:2309.11495` (factuality checks)
- Learning to Route LLMs: `arXiv:2501.12388`
- Bipartite Routing Graphs: `arXiv:2410.03834` (ICLR 2025, used by GraphRouter)
- GEPA: `arXiv:2507.19457` (ICLR 2026 Oral, genetic-Pareto prompt evolution — outperforms GRPO by 6% avg with 35x fewer rollouts. Available as `dspy.GEPA`. Applicable to Phases 4-5: evolve risk-scorer prompts and threshold frontiers. See intake-240)

---

## KPIs

- **Primary**: Factuality@Cost (weighted factual score / token+latency budget)
- **Secondary**: escalation rate by risk band, cheap-first pass rate by risk band, p50/p95 latency deltas
- **Safety gates**: no >10% p95 latency regression, no >5% cost regression at equal factuality

---

## Verification

```bash
# Phase 1-2 tests (existing)
python3 -m pytest tests/unit/test_classifiers.py -v
python3 -m pytest tests/unit/ -x -q

# Phase 3 (when implemented)
python3 -m pytest tests/unit/test_factual_risk.py -v

# Seeding baseline
python3 scripts/benchmark/seed_specialist_routing.py --suite thinking,coder,simpleqa --debug

# Full gates
make gates
```

---

## Audit Log

| Date | Auditor | Summary |
|------|---------|---------|
| 2026-03-05 | Claude | Phase 2 marked complete (built independently). Phase 0: 1/3 items fixed, 2 remain. Added Integration Map (10 subsystems). Fixed stale file paths (chat_pipeline/ refactor). Strengthened Phase 3 design (removed spaCy, added per-role calibration, conformal interaction). Extended Phase 4 (EscalationContext fields, A/B methodology). Expanded Phase 6 (rollback criteria, canary %). Added baselines section. Updated config shape to match actual YAML. |
| 2026-03-05 | Claude | Implemented Phase 0 (2 remaining telemetry items), Phase 3 scorer scaffolding (280 lines, 43 tests, mode: off), EscalationContext risk fields, factual_risk config section. Zero inference, zero behavior change — all behind mode: off or default values. |
| 2026-03-06 | Claude | Closed Phase 2 exemplar seeding gap (auto-seed on API init). Shadow-mode pipeline wiring in `_route_request()`. Risk fields on `RoutingResult`. Config loader default fallback aligned. Ready for shadow mode — flip `factual_risk.mode` to `"shadow"`. ⚠️ Originally claimed `RoleResult` risk fields added — verified absent 2026-03-24; deferred to Phase 5. |
| 2026-03-24 | Claude | Full audit against accrued inference research knowledge. **Fixed**: status line (shadow active, not "mode: off"), `_route_request` line refs (99-122 → ~48), role capability tiers (235B → 122B), config shape (off → shadow), false `RoleResult` risk fields claim. **Added**: production baselines table from comprehensive sweep, Q-scorer frontdoor discrepancy (19.6 vs 12.7 moe6-only). **Trimmed**: Dynamic Stack Assembly section → cross-ref to `dynamic-stack-concurrency.md`. **Added**: Outstanding Work Contextualization section with acceleration constraints and model stack implications. |

---

## Outstanding Work Contextualization (2026-03-24)

This section maps the remaining phases (4-6) against the full body of inference research findings accumulated since the handoff was created. The goal is to ensure Phase 4+ design decisions account for what we now know about the production model stack, acceleration constraints, and routing dynamics.

### What Changed Since Phase 3 Was Designed

1. **Production stack overhaul (2026-03-19)**: architect_general switched from 235B to 122B (+25pp quality, saves 64GB). Frontdoor lookup disabled (segfault). NUMA 4-way deployment for frontdoor/coder (6-7x aggregate throughput).

2. **Acceleration research concluded**: ALL Qwen3.5 hybrid self-acceleration approaches exhausted (tree, MoE self-draft, attention-only, MTP-1, layer-exit — all net negative). Speculation only viable on dense models (Coder-32B) and pure MoE (REAP-25B). This is permanent — it's an architectural constraint of Delta Net recurrent layers.

3. **REAP MoE pruning viable**: Cerebras REAP-25B-A3B achieves 39.6 t/s (vs 39.1 baseline), 60% quality (87% agentic). Pre-pruned models available as GGUFs. Opens a new model tier for routing: cheap/fast pure-MoE models with speculative decoding.

4. **Worker model candidates**: Nanbeige-3B (P0) and MiroThinker-8B (P1) pending evaluation. If Nanbeige-3B proves viable as worker, it changes the routing cost model significantly — 3B models are extremely fast on EPYC.

### Implications for Phase 4 (Enforce Mode)

- **Role-adjusted risk calibration needs updating**: The tier system was designed around {235B, 32-70B, 7-14B}. Actual production is {480B, 122B, 32-35B, 30B-A3B, 3-7B candidates}. The tier boundaries should be re-drawn based on measured quality per suite, not parameter count.
- **Cheap-first bypass**: With frontdoor at 12.7 t/s (not 19.6) and quality at 83%, the cost/quality tradeoff of cheap-first bypass shifts. High factual-risk prompts that bypass cheap-first now cost more in latency terms.
- **A/B test methodology**: The seeding harness has 23 suites and 56,448 questions. Phase 4 A/B should use the full harness, not just `thinking,coder,simpleqa`. Include `agentic` suites since that's where model differentiation is largest.
- **REAP models as routing targets**: If REAP-25B or pre-pruned 363B/246B prove quality-viable, the routing classifier needs new role mappings. Pure MoE models with speculation offer a speed/quality tradeoff not available with hybrids.

### Implications for Phase 5 (Seeding/Eval Integration)

- **RoleResult risk fields**: Still missing (false completion claim). Must be added before risk-aware seeding analysis.
- **Omega metric integration**: Pre-compute per-suite Omega values (reasoning benefit) using seeding infrastructure. Store in registry. Feed to difficulty_signal.py for per-question reasoning budget decisions.
- **Pareto dimensions**: Original design had 3D (factuality × cost × latency). Add 4th dimension: **acceleration compatibility** — models that support speculation have different cost curves than those that don't. A REAP-25B at 39.6 t/s has fundamentally different cost per token than a hybrid 35B at 12.7 t/s.

### Implications for Phase 6 (Controlled Rollout)

- **Canary scope**: Original plan canaries on `frontdoor` first. With 4-instance round-robin, canary could run on 1/4 instances (25% traffic) with minimal infrastructure change.
- **Dynamic baselines**: If stack assembly is implemented (see `dynamic-stack-concurrency.md`), the Q-scorer baselines change per profile. Rollout must account for which stack profile is active.

## Research Intake Update — 2026-03-14

### New Related Research
- **[intake-120] "Reasoning Models Struggle to Control their CoT"** (arxiv:2603.05706)
  - Relevance: CoT controllability metrics directly inform factual-risk routing decisions — models that can't hide reasoning are easier to monitor
  - Key technique: CoT-Control evaluation suite (13,000+ tasks) measuring whether models can selectively hide/alter chain-of-thought
  - Reported results: 0.1%-15.4% controllability across frontier models; lower controllability = higher monitorability
  - Delta from current approach: Routing intelligence currently scores factual risk but doesn't account for reasoning model monitorability. Low CoT controllability means reasoning traces are trustworthy signals for routing decisions.

- **[intake-103] "Thinking to Recall"** (arxiv:2603.09906)
  - Relevance: Shows CoT reasoning expands factual recall boundary but creates hallucination risks through generative self-retrieval — directly relevant to factual risk scoring
  - Key technique: Hallucination-free trajectory filtering improves accuracy by +8-12%
  - Delta from current approach: Factual risk classifier (Phase 3) could incorporate reasoning trace quality assessment — filtering hallucinated intermediate steps before scoring final-answer confidence.

### Deep-Dive Findings (2026-03-15)

**Source**: `research/deep-dives/reasoning-recall-cot-controllability.md`

#### Omega Metric — Per-Suite Reasoning Benefit Signal

The Omega metric (arxiv:2603.09906) measures how much reasoning expands a model's effective capability boundary per benchmark suite. High Omega = reasoning is critical; low Omega = reasoning tokens are wasted.

**Integration path**: Compute Omega per-suite using existing seeding infrastructure (pass@k with reasoning ON vs OFF). Store as annotation in model_registry.yaml. When difficulty_signal.py moves to enforce mode, use pre-computed Omega values to decide whether a reasoning model is worth the extra tokens for a given question type.

**Cross-reference**: Also tracked in `reasoning-compression.md` Action 6.

#### Output-Side Verified-Fact Filtering

Paper 1 shows hallucinated intermediate facts in `<think>` blocks predict hallucinated final answers (41.4% vs 26.4% accuracy on SimpleQA). This suggests an output-side complement to our input-side `factual_risk.py`:

```
Input  → factual_risk.assess_risk(prompt)     → input risk score (fast, regex)
Output → factual_risk.verify_reasoning(trace)  → output risk score (slow, model-based)
Combined = f(input_risk, output_risk)
```

The input-side scorer gates whether to run the expensive output-side verification — only prompts with medium/high input risk warrant output verification. This extends Phase 4 (enforce mode) with a two-stage risk assessment.

**Implementation**: Extract factual claims from `<think>` blocks using entity/date/number patterns (similar to existing `_extract_features` but applied to model output). Cross-reference against high-confidence sources. Gate behind `factual_risk.mode = "enforce"` AND high input-side risk score to control cost.

### Context-Folding Process Reward Integration

**Cross-reference**: `context-folding-progressive.md` Phase 3

Process reward telemetry from the context-folding progressive handoff provides a `segment_advantage` signal computed at consolidation boundaries. This signal measures per-turn contribution to task progress using token_budget_ratio, on_scope, and tool_success_ratio rewards with position-weighted advantage broadcasting (from ReSum-GRPO, arxiv:2509.13313).

**Integration path for Phase 5**: The `segment_advantage` signal can enrich MemRL Q-values — episodes with high segment advantage should receive a Q-value bonus, improving routing accuracy for tasks that benefit from sustained multi-turn reasoning. Position-weighted advantage broadcasting is also directly applicable to delegation episode training (later turns in a delegation loop carry more signal about whether the delegation succeeded).

## Research Intake Update — 2026-03-20

### New Related Research
- **[intake-174] "Reason-ModernColBERT: Late-Interaction Retriever for Reasoning Tasks"** (HuggingFace: lightonai/Reason-ModernColBERT)
  - Relevance: Late-interaction (ColBERT MaxSim) dramatically outperforms dense retrieval on reasoning-intensive tasks — our episodic memory uses FAISS dense vectors for strategy retrieval
  - Key technique: 150M ColBERT model with ModernBERT backbone, trained on ReasonIR-HQ reasoning triplets
  - Reported results: +7.3 NDCG@10 over dense retrieval on same data; competitive with 7B+ models at 150M params
  - Delta from current approach: Our `strategy_store.py` uses single-vector FAISS similarity — multi-vector late interaction could capture token-level reasoning patterns missed by dense embeddings

- **[intake-176] "ReasonIR: Training Retrievers for Reasoning Tasks"** (arxiv:2504.20595)
  - Relevance: Training data methodology for reasoning-aware retrieval — directly applicable to improving episodic memory retrieval quality
  - Key technique: Synthetic reasoning query generation with hard negatives
  - Reported results: 29.9 NDCG@10 on BRIGHT (SoTA at publication)
  - Delta from current approach: Our episodic memory training data is derived from Q-values, not reasoning-focused triplets — ReasonIR's data generation pipeline could improve routing classifier training data

## CRITICAL: Q-Scorer baseline_tps Calibration

**File**: `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` lines 64-74

**History**: Original values were inflated (one-off peaks, not systematic benchmarks). Bulk fix applied 2026-03-21 using comprehensive sweep data. Most roles now correct.

**Remaining issue — frontdoor**:
| Role | Q-scorer value | Actual deployed t/s | Gap | Impact |
|------|----------------|---------------------|-----|--------|
| `frontdoor` | **19.6** (moe6+lookup) | **12.7** (moe6-only, lookup disabled) | +54% | Under-penalizes frontdoor cost in routing Q-values |

Lookup was disabled on frontdoor 2026-03-19 (segfault after 1-3 prompts on Qwen3.5 hybrids). The Q-scorer still uses the pre-segfault throughput. **Fix**: Update to 12.7 once moe6-only deployment is confirmed as permanent config.

**Two sources of truth** (by design):
- **Q-scorer `baseline_tps_by_role`**: Deployment-mode t/s (NUMA-pinned, taskset). Used for cost penalty normalization in routing decisions.
- **Registry `throughput` field**: 192t `numactl --interleave=all` reference values. Used for quality/speed tracking across model versions.
- These intentionally differ — they measure different things.

---

## Future Direction: Dynamic Stack Assembly

Spun out to dedicated handoff: [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) (2026-03-24).

**Key relationship**: Routing intelligence decides *which role* handles a request (quality decision); stack assembly decides *how that role is provisioned* (capacity decision). They compose but are developed independently. The Q-scorer's `baseline_tps_by_role` must become dynamic if stack assembly changes instance counts per role.

See also: [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md), [`numa-orchestrator-deployment.md`](numa-orchestrator-deployment.md).
