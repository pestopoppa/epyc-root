# Routing Intelligence: Semantic Classifiers + Factual-Risk Routing

**Created**: 2026-02-18 (consolidated from `classifier-refactoring.md` + `delegation-escalation-factual-risk-routing-track.md`)
**Last audited**: 2026-03-05
**Status**: PHASES 0-2 COMPLETE — Phase 3 scaffolding done (mode: off) — Phases 3-6 enforcement deferred
**Priority**: HIGH
**Blocked by**: Nothing (Phase 0 telemetry complete, Phase 3 scorer ready for shadow mode)

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
| ~~`scripts/benchmark/seeding_types.py`~~ | ✅ Risk fields added to `RoleResult` (2026-03-06) |

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

### Phase 3: Factual-Risk Scorer (shadow mode) — SHADOW ACTIVE (2026-03-15)

Scorer implemented in `src/classifiers/factual_risk.py` (280 lines, regex-only, 43 tests passing).
Pipeline wiring complete (2026-03-06) — `_route_request()` calls `assess_risk()` when mode != "off", attaches score/band to `RoutingResult`. **Activated to shadow mode 2026-03-15** — factual risk score/band now logged on every request in `routing_meta` alongside `difficulty_score`/`difficulty_band`.

Add risk features to a new `src/classifiers/factual_risk.py`:
- Query intent flags (asks-for-facts/dates/names/citations)
- Claim density estimate
- Uncertainty lexical markers
- Regex-only in production (no spaCy — too heavy at 800MB+, remove from design)

Deploy as `shadow` mode — compute and log risk score/band/features, no routing changes.

Config additions to `orchestration/classifier_config.yaml`:
```yaml
factual_risk:
  mode: shadow  # off|shadow|enforce
  threshold_low: 0.3
  threshold_high: 0.7
  force_review_high: true
  early_escalation_high: false
```

**Design requirements** (from audit):
1. **Conformal prediction interaction** — HybridRouter already gates routing via conformal prediction with budget guardrails (`retriever.py`). The factual-risk scorer COMPLEMENTS this: conformal prediction gates on model uncertainty (output-side), factual-risk gates on prompt characteristics (input-side). They should not conflict — risk score feeds as an additional signal, not a replacement. If conformal prediction already rejects a routing, factual-risk should not override.
2. **Per-role risk calibration** — A factual question routed to `architect_general` (235B) vs `worker_general` (7B) has very different actual hallucination risk. `FactualRiskResult` should include `adjusted_risk_score` that factors in the assigned role's capability tier.
3. **Calibration dataset** — Unlike the input classifier which has seeded exemplars, the risk scorer has no ground-truth dataset. Before moving from shadow to enforce, we need a labeled set of prompts with known factual-risk levels. Source candidates: simpleqa failures, seeding diagnostic logs with `passed=False` on factual suites.
4. **No spaCy** — Remove from design entirely. Regex-only in all modes.

**Exit**: Risk features logged on every request, p95 overhead < 5ms (regex mode)

### Phase 4: Risk-Aware Routing (enforce mode) — NOT STARTED

Wire risk outputs into routing decisions:

| Integration Point | Current Location | Change |
|-------------------|------------------|--------|
| Cheap-first bypass | `src/api/routes/chat.py:_try_cheap_first` (~line 208) | `risk >= high` → bypass or strict pass criteria |
| Plan review gate | `src/api/routes/chat_pipeline/routing.py:_plan_review_gate` | `risk_band=high` → force review even if generic heuristics pass |
| Escalation policy | `src/escalation.py:EscalationPolicy.decide()` | Add `risk_score: float` and `risk_band: str` to `EscalationContext` dataclass; high risk + uncertainty → earlier escalation |
| Failure graph veto | `src/api/routes/chat_pipeline/routing.py:_route_request` (lines 99-122) | Hardcoded `risk > 0.5` threshold should be modulated by factual-risk band |
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
| **FailureGraph veto** | `src/api/routes/chat_pipeline/routing.py:_route_request` (lines 99-122) | Always active | **Production** | Hardcoded `risk > 0.5` threshold. Factual-risk should modulate this: high factual-risk prompts should have a LOWER failure-veto threshold (more conservative), low-risk prompts can tolerate higher failure risk |
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
    role_adjustment: float      # multiplier applied (e.g., 0.6 for 235B, 1.0 for 7B)

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

Role capability tiers for adjustment:
- Tier 1 (235B+ models): adjustment = 0.6
- Tier 2 (32B-70B models): adjustment = 0.8
- Tier 3 (7B-14B models): adjustment = 1.0

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
  mode: off  # off|shadow|enforce
  threshold_low: 0.3
  threshold_high: 0.7
  force_review_high: true
  early_escalation_high: false
  role_adjustments:
    tier_1: 0.6  # 235B+
    tier_2: 0.8  # 32B-70B
    tier_3: 1.0  # 7B-14B
```

---

## Baselines (snapshot 2026-03-05)

Current metrics to measure Phase 3-6 impact against. **These must be re-measured before starting enforce mode.**

| Metric | Current Value | Source | Notes |
|--------|---------------|--------|-------|
| simpleqa F1 | ~0.5 threshold | `dataset_adapters.py` | Threshold lowered from 0.8 → 0.5 on 2026-03-03 |
| Escalation rate (frontdoor) | TBD — measure via seeding | Seeding harness | Need baseline run |
| Escalation rate (worker) | TBD — measure via seeding | Seeding harness | Need baseline run |
| Cheap-first pass rate | TBD — measure via seeding | Seeding harness | Need baseline run |
| p50 latency | TBD — measure via inference tap | `/mnt/raid0/llm/tmp/inference_tap.log` | Need baseline run |
| p95 latency | TBD — measure via inference tap | `/mnt/raid0/llm/tmp/inference_tap.log` | Need baseline run |
| Cost per question (avg tokens) | TBD — measure via seeding | Seeding harness | Need baseline run |

**Action item**: Run a baseline seeding sweep (`seed_specialist_routing.py --suite thinking,coder,simpleqa`) before starting Phase 3, record results here.

---

## Research References

- LaCy: `arXiv:2602.12005` (factual-risk-aware call placement)
- FrugalGPT: `arXiv:2305.05176` (LLM cascades/routing)
- Language Model Cascades: `arXiv:2207.10342`
- Chain-of-Verification: `arXiv:2309.11495` (factuality checks)
- Learning to Route LLMs: `arXiv:2501.12388`
- Bipartite Routing Graphs: `arXiv:2410.03834` (ICLR 2025, used by GraphRouter)

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
| 2026-03-06 | Claude | Closed Phase 2 exemplar seeding gap (auto-seed on API init). Shadow-mode pipeline wiring in `_route_request()`. Risk fields on `RoutingResult` and `RoleResult`. Config loader default fallback aligned. Ready for shadow mode — flip `factual_risk.mode` to `"shadow"`. |

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

## CRITICAL: Q-Scorer baseline_tps Calibration (2026-03-20)

**File**: `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` lines 62-67

The `baseline_tps_by_role` values used for cost penalty normalization are **inflated** — they came from one-off peak measurements, not systematic benchmarks. The comprehensive spec param sweep (2026-03-20) reveals the real sustained throughput:

| Role | Registry (inflated) | Sweep (real) | Source of inflated value |
|------|-------------------|-------------|------------------------|
| `coder_escalation` | **39.44** | **10.8** (Q4KM 48t) | Single warm-cache summarization prompt, 2026-01-28 |
| `frontdoor` | 18.3 | ~19.6 (35B moe6+lu) | Likely reasonable (close to sweep) |
| `architect_general` | 6.75 | **2.5** (122B 192t) / **4.2** (122B 96t) | Unclear origin, possibly old 235B model |
| `architect_coding` | 10.3 | TBD (480B sweep pending) | Unclear origin |

**Impact**: With `coder_escalation` baseline at 39.44 but real throughput at ~10.8, the cost penalty formula (`cost_ratio = elapsed / expected_elapsed`) thinks coder is ~3.6x slower than expected on EVERY request. This systematically penalizes the coder role's Q-values, biasing routing away from coder escalation.

**Fix (two sources of truth)**:
- **Q-scorer `baseline_tps_by_role`**: Use deployment-mode t/s from the comprehensive sweep (e.g. coder Q4KM 48t = 10.8). These reflect real production throughput under NUMA pinning.
- **Registry `throughput` field**: Use `run_benchmark.py --speed-questions 3` values (192t interleave reference). These are for quality/speed tracking across model versions.
- **Registry `draft_max`/`p_split`**: Use deployment-mode optimal params from sweep (may differ from 192t optimal).
- The two numbers will differ (192t vs NUMA deployment) and that is intentional — they measure different things.

**Note on methodology**: `run_benchmark.py` always runs at 192t with `numactl --interleave=all` — it has no NUMA deployment awareness. The comprehensive sweep (`bench_all_spec_sweeps.sh`) measures at actual deployment thread counts with taskset. Both are valid; they serve different purposes.

---

## Future Direction: Dynamic Stack Assembly (2026-03-24)

### Problem

The orchestrator stack (which models, how many instances, NUMA pinning, acceleration) is currently statically configured. But the optimal config depends on runtime conditions:

| Scenario | Optimal frontdoor config | Why |
|----------|------------------------|-----|
| Single user, serial chat | 1×30B-A3B spec (39 t/s) | Max per-request speed |
| Single user, pipeline (FD→coder→arch) | 1×35B moe6 + free cores for coder | Internal concurrency needs parallel models |
| Burst traffic / multi-session | 4×35B moe6 (50.8 t/s agg) | Parallel users, throughput > latency |
| Code-heavy session | 1×35B + 4×coder + 1×arch | Coder needs more cores than frontdoor |

### Proposal

The routing-intelligence agent (or autopilot) should have authority to **reconfigure the stack at session boundaries**:

1. **Observe**: Queue depth, request types, latency distribution, core utilization
2. **Decide**: Pick optimal model assignment and instance count per role
3. **Execute**: Drain in-flight requests, restart instances with new config, re-mlock
4. **Verify**: Confirm health checks pass, measure first-request latency

### Constraints

- **Single primary user** (Daniele): high concurrency is rare, but internal pipeline concurrency exists
- **Hot-swap latency**: Reconfiguring requires draining + restart + mlock. Minimum ~30-60s for a full stack change. Cannot switch mid-inference.
- **Session-boundary switching** is practical: at conversation start, pick config based on declared intent (code session vs research vs general)
- **RoundRobinBackend** already supports this — swap the backends list and the next request goes to the new config

### Connection to Routing Intelligence

This is the **infrastructure layer** below semantic routing. The classifier decides *which role* handles a request; the stack assembler decides *how that role is provisioned*. They compose:

```
Request → Classifier (role selection) → Stack Assembler (instance selection) → Backend
```

The Q-scorer's `baseline_tps_by_role` would need to be dynamic too — if the stack assembler switches frontdoor from 4×35B to 1×30B-spec, the baseline t/s changes from 12.7 to 39.1.

### See Also

- `autopilot-continuous-optimization.md` — Autonomous tuning framework
- `numa-orchestrator-deployment.md` — Current static NUMA deployment
- `RoundRobinBackend` in `epyc-orchestrator/src/backends/round_robin.py` — Runtime instance routing
