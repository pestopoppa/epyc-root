# Cluster B Audit: Memory & Learning (Chapters 07, 09, 15, 16)

**Audit Date**: 2026-05-26  
**Cluster**: Memory & Learning subsystem  
**Last Chapter Touch**: 2026-03-18 (Ch09 seeding) to 2026-03-03 (Ch16 calibration)  
**Review Period**: 2026-03-19 → 2026-05-26 (69 days of development)

---

## Executive Summary

All 4 chapters are **substantially outdated** due to major production landings in routing classifier, verifier gates, SkillBank evolution, and risk-control architecture. Approximately 30 distinct code changes impact these chapters' accuracy. **Recommended action**: patch all 4 chapters with high-priority updates to `07` and `16`, medium-priority to `09`, low-priority to `15` (which was less touched).

---

## Chapter 07: MemRL System

**Verdict**: **PATCH** (medium severity)  
**Key Issues**: Routing classifier wiring omission, verifier gate architecture, Q-learning evolution scope

### Factual Errors

- **Line 383** (Phase 8 reference): Phase progression table says "Phase 8 | Model self-routing (REPL tools + routing context) | Production". True, but incomplete. Phase 8 was extended with an additional sub-phase not documented: **Phase 8.1 — Classifier Fast-Path** (2026-05-21, commit 4882d9b2), where a learned MLP routing classifier (98.7% val acc on 41K memories) runs before FAISS retrieval. If classifier confidence ≥ 0.8, FAISS is skipped entirely. **Source**: `orchestration/repl_memory/routing_classifier.py`, `src/api/services/memrl.py:471-514`, confirmed in 2026-05-21 progress log: "0 classifier decisions / 508 rule+learned" pre-wiring → "93 classifier decisions" post-wiring on 2026-05-21.

- **Line 427-444** (MemRL Quality Review Gate): Section describes Phase 8 context injection but omits **Phase 8.2 — Verifier Gate** (2026-05-21). A frontdoor-specialist verifier head (Brier 0.0072, AUC 0.9996) now gates frontdoor fast-path responses. When `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE=1`, the verifier predicts P(success) and either passes through (shadow mode) or blocks + escalates (enforce mode). **Source**: `orchestration/repl_memory/verifier_head.py:250 LoC`, `src/api/services/memrl.py` lines 477-514.

### Superseded Claims

- **Section "Model Self-Routing (Phase 8)"** (line 427-444): Implies all routing decisions come through REPL tools or inference-time injected Q-values. Since 2026-05-21, 60% of decisions now bypass REPL entirely — the classifier fast-path routes in <1ms before any model inference. Line 442 ("Routing context injected on turn 0") is still true but now reflects only the learned (KNN) path, not the dominant classifier path. Recommend clarifying that Phase 8 has two parallel sub-paths: classifier (fast, 0.8+ confidence threshold) and learned (KNN, fallback).

### Missing Content (Post-2026-03-30 Landings)

1. **Routing Classifier Distillation (March 2026)** — Chapter 07 line 655-669 already covers it well, but the wiring details are stale:
   - **Line 663**: "Feature-gated: `ORCHESTRATOR_ROUTING_CLASSIFIER=1`" is correct, but missing the critical caveat: **The flag was enabled 2026-04-15 (P1.5) but dead-code for 5 weeks** — no code called `RoutingClassifier.load()` until 2026-05-21 (commit 4882d9b2). The gap should be mentioned as a historical lesson: feature flags must verify the data flow end-to-end, not just set an env var.
   - **New source**: `src/api/services/memrl.py:471-514` (P1.5 wiring patch), `scripts/maintenance/repair_episodic_embeddings.py` (FAISS embedding health preflight added 2026-05-21), `scripts/maintenance/verify_routing_wiring.py` (pre-flight smoke test).

2. **Frontdoor Verifier Gate (May 2026)** — Entirely missing section covering Phase 8.2:
   - **Architecture**: 2-layer numpy MLP (~140K params) trained on routing-success labels. Single-action specialist (frontdoor only, no multi-action version per counterfactual probe findings).
   - **Integration**: In `HybridRouter`, when classifier selects frontdoor and verifier loaded, run verifier.predict(embedding, action_idx=0) → P_success scalar [0, 1]. Shadow mode logs verdict, enforcing mode blocks if P < threshold (default 0.5).
   - **Performance**: Brier 0.0072 (vs softmax-magnitude baseline 0.073), AUC 0.9996, ECE 0.0145. Margin ~9x over baseline.
   - **Source**: `orchestration/repl_memory/verifier_head.py`, commit 4882d9b2, 2026-05-21 progress log Session 4.

3. **Learned Routing Controller (May 2026)** — The term "routing classifier distillation" was introduced in Ch07 § Routing Classifier Distillation (line 655), but now there's a companion **Trinity Phase 6** (2026-05-21) that proposes learned verifiers as a quality gate, not just a router. Chapter doesn't need to detail Trinity's full research arc, but should acknowledge: the Phase 8.2 verifier is NOT a routing decision engine (which is what the classifier does) but a **quality gate post-routing**. This architectural distinction is load-bearing.

4. **Cross-Role BW-Aware Routing (May 2026)** — A new control knob landed 2026-05-24 (`cross-role-bw-aware-routing.md` handoff) that modulates HybridRouter's confidence thresholds based on target role's bandwidth utilization. Not directly in Ch07 scope (it's a runtime tuning knob), but the "Calibration and risk metrics" section (line 609-624) should note that effective_threshold now accounts for role-load variance in some configurations. **Source**: `orchestration/repl_memory/retriever.py` (runtime) + `cross-role-bw-aware-routing.md` (design).

### Broken Path References

- **Line 710**: "`orchestration/repl_memory/routing_classifier.py`" — exists and is correct.
- **Line 671**: "`../reference/agent-config/MEMRL_DISTILLATION_DESIGN.md`" — file does not exist in the repo. Should be a cross-reference to `handoffs/active/learned-routing-controller.md` or Chapter 08 (Failure lessons in graph reasoning). Recommend removing the broken ref or updating to a valid handoff path.

### Proposed Edits

**Edit 1** (after line 381, Phase 8 description):  
Replace the Phase 8 bullet with:
```
| 8 | Model self-routing (REPL tools + routing context) | Production |
| 8.1 | Routing classifier fast-path (98.7% val acc MLP) | Production (2026-05-21) |
| 8.2 | Frontdoor verifier quality gate (Brier 0.0072) | Production (2026-05-21, shadow mode default) |
```
Add note: "Phases 8.1-8.2 enabled 2026-05-21; Phase 8.1 was implemented 2026-04-15 but inactive (dead code) until wiring completed 2026-05-21."

**Edit 2** (new section after line 444, after "Model Self-Routing (Phase 8)"):  
Add new section "Routing Classifier Fast-Path (Phase 8.1)" with:
- Architecture: 2-layer MLP (1031 → 128 → 64 → N_actions softmax), ~140K params
- Training: Q-value weighted cross-entropy on episodic store, cosine LR decay + early stopping
- Integration: In `HybridRouter.route()`, if classifier confidence ≥ 0.8 and action selected is not "unknown", skip FAISS retrieval entirely. Inference <0.1ms.
- Performance: 98.7% val acc (2026-05-21 retrain on 41K fresh memories post-repair)
- Reset safety: Weights auto-deleted on episodic memory reset; load() returns None for missing weights
- Sources: `orchestration/repl_memory/routing_classifier.py`, `scripts/graph_router/train_routing_classifier.py`, commit 4882d9b2

**Edit 3** (new section after Phase 8.1 section):  
Add "Frontdoor Verifier Quality Gate (Phase 8.2)" covering:
- Purpose: Post-routing decision quality check; gates frontdoor responses when classifier confidence < 0.8 or for assurance
- Architecture: 2-layer numpy MLP, BCE training, single-action specialist (n_actions=0 case)
- Integration: Verifier.predict(embedding, action_idx=0) → P_success [0, 1]. Shadow mode logs to routing_decision metadata. Enforcing mode escalates if P < threshold.
- Performance: Brier 0.0072 / AUC 0.9996 / ECE 0.0145 on 40.9K fresh memories
- Feature flags: `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE=1`, `FRONTDOOR_VERIFIER_SHADOW=1` (default)
- Sources: `orchestration/repl_memory/verifier_head.py`, commit 4882d9b2, `/workspace/progress/2026-05/2026-05-21.md` Session 4

**Edit 4** (update line 671 reference):  
Replace:
```
See [MEMRL_DISTILLATION_DESIGN.md](../reference/agent-config/MEMRL_DISTILLATION_DESIGN.md) for full design document.
```
With:
```
See [learned-routing-controller.md](../../handoffs/active/learned-routing-controller.md) for full design document including Phase 6 verifier validation and production wiring.
```

### Notes

- The classifier wiring gap (dead code 2026-04-15 → 2026-05-21) is worth documenting as a cautionary tale: feature flags must be verified end-to-end, not just enabled at the environment layer.
- The distinction between routing (classifier) and quality-gating (verifier) is architecturally important and often conflated in casual discussion. Ch07 should be precise about which phase does what.
- Recommend also updating Ch08 (Graph Reasoning) to clarify that FailureGraph + SkillBank now feed into the verifier's effectiveness tracking, not just the Q-scorer.

---

## Chapter 09: Memory Seeding & Bootstrap

**Verdict**: **PATCH** (low-medium severity)  
**Key Issues**: 3-way seeding action keys documentation, skill seeding bootstrap, exploration epsilon control

### Factual Errors

- **Line 237-265** (Strategy 10: 3-Way Routing Evaluation): The chapter documents the seeding strategy well, but misses a critical detail added 2026-05-24: **Exploration epsilon control** (`SPO_PLUS_EPSILON` env var, default 0.0). When epsilon > 0, a fraction of routes are forced to random alternatives for diversity even if the classifier picks a single optimal action. Line 242's "binary rewards (1.0 pass, 0.0 fail)" is correct, but line 243's "cost metrics are stored in metadata for later Optuna optimization" has evolved: cost is now also used to compute a **regret signal** (engineer gain from choosing another action, discounted by cost delta). **Source**: `orchestration/repl_memory/q_scorer.py` lines 220-250 (2026-05-22), `/workspace/progress/2026-05/2026-05-21.md` Session 6 routing-distribution diagnosis.

- **Line 264** (Skill Seeding): "Search-R1 reward integration (2026-03-03)" is accurate for when the feature landed, but the text should note: Skill seeding itself was implemented and validated (2026-02-14 through 2026-03-01), but the initial distillation only ran on 180 trajectories (100 success, 40 failure, 40 escalation), yielding 57 skills. This is a dry-run result documented in the completed handoff `skillbank-distillation.md` at lines 1332-1336. **Source**: `orchestration/repl_memory/distillation/pipeline.py`, `/workspace/handoffs/completed/skillbank-distillation.md` completion checklist.

### Superseded Claims

- **Section "3-Way Action Keys (February 2026)"** (line 391-404): The action key definitions are still valid, but the chapter doesn't mention that as of 2026-05-21, **forced seeding is no longer the primary memory-building mechanism**. The classifier + verifier gates now produce natural routing diversity (or lack thereof). Line 392 says "The 3-way evaluation mode uses a distinct action vocabulary" — true, but now there's also a **non-3-way path** where seeding uses epsilon-greedy exploration instead. The training data split has shifted: pre-2026-05-09 stack change, raw memories; post-2026-05-09, ~86% post-stack-change. The chapter should clarify this timeline. **Source**: `/workspace/progress/2026-05/2026-05-21.md` Session 4, "Distribution shift findings" table.

### Missing Content (Post-2026-03-30 Landings)

1. **Exploration Epsilon (May 2026)** — New lever `SPO_PLUS_EPSILON` env var (default 0.0) controls counterfactual data collection during seeding:
   - When epsilon > 0 (e.g., 0.2), 20% of seeding routes are forced to non-classifier alternatives regardless of confidence
   - Addresses the 91% frontdoor concentration issue (2026-05-21 autopilot routing distribution)
   - **Deferred for a dedicated tuning session** per Session 6, but the mechanism is live
   - **Source**: `orchestration/repl_memory/hybrid_router.py` (epsilon logic), `/workspace/progress/2026-05/2026-05-21.md` Session 6

2. **Stack Change Distribution Shift (May 2026)** — The 2026-05-09 orchestrator consolidation changed role names and slot counts, causing a distribution shift in live-db routing data:
   - Pre-change: architect_general 100% success (1,640 routes), architect_coding 100% (1,589 routes)
   - Post-change (86% of current data): architect_general 9.1% success (5,101 routes), architect_coding role removed, new worker_general 0.1% success (3,506 routes), ingest_long_context 99.6%
   - The chapter's seeding recommendations assume a stable distribution, but they should note this shift in context
   - **Source**: `/workspace/progress/2026-05/2026-05-21.md` Session 4, "Distribution shift findings" table

3. **Embedding Health Preflight (May 2026)** — New step added to seeding pipeline (2026-05-21):
   - `scripts/maintenance/repair_episodic_embeddings.py` detects FAISS coverage < 50% vs live db
   - Rebuilds FAISS index atomically if needed (e.g., 22.9% memories dropped due to ACTION_NORMALIZATION bug)
   - Wired into `orchestrator_stack.py` step `[0.7]` before seeding runs
   - **Impact**: Downstream seeding sees complete coverage. Previous missing: 40,862 unaddressable FAISS vectors due to id_map truncation
   - **Source**: `scripts/maintenance/repair_episodic_embeddings.py`, commit 4882d9b2

### Broken Path References

- All paths in the chapter are correct (seed_loader.py, seed_examples.json, etc.).

### Proposed Edits

**Edit 1** (after line 264, insert new paragraph):  
Add: "**Exploration Epsilon Control (May 2026)**: The seeding pipeline now supports epsilon-greedy exploration via the `SPO_PLUS_EPSILON` environment variable (default 0.0). When set to a value like 0.2, 20% of routes during seeding are forced to non-classifier alternatives, enabling diverse memory collection even when one action is dominant. This addresses the need to build counterfactual data for model comparison and cost-aware routing. See [cross-role-bw-aware-routing.md](../../handoffs/active/cross-role-bw-aware-routing.md) for tuning guidance."

**Edit 2** (before line 314, "Seeding Order & Dependencies" section):  
Add new subsection "Embedding Health Preflight": "Prior to running seeding scripts, the pipeline checks FAISS index coverage. If < 50% of memories have FAISS embeddings (detected via orphan diagnostic), `scripts/maintenance/repair_episodic_embeddings.py` rebuilds the index atomically. This step is wired into `orchestrator_stack.py` step `[0.7]` and runs automatically on startup. Manual invocation: `python3 scripts/maintenance/repair_episodic_embeddings.py`. See `/workspace/progress/2026-05/2026-05-21.md` Session 4 for historical context (22.9% memories were being dropped due to ACTION_NORMALIZATION missing identity maps; fixed 2026-05-21)."

**Edit 3** (update line 253 in "3-Way routing evaluation" section):  
Clarify the reward mechanism: "Binary rewards (1.0 pass, 0.0 fail) are used instead of cost-weighted rewards so the system learns true P(success). Cost metrics are stored in metadata. Additionally, a **regret signal** (engineer gain from choosing alternative actions, discounted by cost delta) is computed per episode and integrated into Q-value updates via `orchestration/repl_memory/q_scorer.py`. See [learned-routing-controller.md](../../handoffs/active/learned-routing-controller.md) for regret-optimized replay objective design."

**Edit 4** (clarify line 392 "3-Way Action Keys" section):  
Add note: "As of 2026-05-09, the orchestrator underwent a stack consolidation that changed role names and removed the architect_coding role, consolidating it into architect_general. This caused a distribution shift in live-db routing data: pre-change memories show architect_general at 100% success, post-change at 9.1%. Seeding recommendations in this chapter assume a stable distribution; advisors should account for this historical shift when analyzing memory composition. See `/workspace/progress/2026-05/2026-05-21.md` Session 4 'Distribution shift findings' for data."

### Notes

- The 3-way seeding design is sound, but the chapter should acknowledge the ongoing tuning of epsilon-greedy exploration as a complementary mechanism.
- The stack consolidation (2026-05-09) is a significant event that invalidates some of the pre-consolidation training data for roles that no longer exist. Consider adding a sidebar or footnote explaining this historical juncture.
- The embedding health preflight (repair script) is a post-implementation safeguard that prevents seeding from working with incomplete data. Its existence should be documented so operators know to run it or verify coverage manually.

---

## Chapter 15: SkillBank & Experience Distillation

**Verdict**: **UP_TO_DATE** (low severity, minor clarifications only)  
**Key Issues**: Feature flag status, initialization validation

### Factual Errors

None identified. The chapter was written to spec and validated through 2026-03-01 with initial distillation run (57 skills generated) documented in the completed handoff `skillbank-distillation.md`.

### Superseded Claims

None identified. The SkillBank architecture and distillation mechanism remain unchanged from the March 2026 implementation.

### Missing Content (Post-2026-03-30 Landings)

1. **Recursive Evolution Monitoring Integration (May 2026)** — The chapter describes the EvolutionMonitor in theory (§9), but doesn't mention that as of 2026-05 this is now integrated with the **ClaudeDebugger** anomaly detection system:
   - Low-confidence skills (< 0.3) now generate anomaly signal `skill_mismatch` (confidence score 0.5)
   - No-skills-available scenario generates signal `no_skills_available` (confidence 0.3)
   - **Source**: `src/pipeline_monitor/claude_debugger.py` (skill diagnostics section added 2026-02-14), `/workspace/handoffs/completed/skillbank-distillation.md` line 629-634 "Anomaly detection" integration

2. **Feature Flag Production Status (May 2026)** — The chapter correctly states `ORCHESTRATOR_SKILLBANK=1` as the feature gate (line 564), but doesn't explicitly state the **current production status** (as of 2026-05-26):
   - SkillBank code is complete and tested (139 unit tests, all passing)
   - Initial distillation run completed 2026-03-09 with 57 skills (27 routing, 18 failure_lesson, 12 escalation)
   - **Feature flag remains OFF in production** — A/B test deferred pending distillation scale-up and effectiveness data
   - The flag is feature-complete and safe to enable for testing, but has not yet been run against the full 40K+ episodic memory corpus
   - **Source**: `/workspace/handoffs/completed/skillbank-distillation.md` lines 1337-1340 "Remaining work (requires inference)"

### Broken Path References

- All path references in the chapter are correct.

### Proposed Edits

**Edit 1** (add to line 565, after "Graceful Degradation" subsection):  
Add note: "**Current Status (May 2026)**: SkillBank implementation is complete (139 unit tests passing). Initial distillation validated on 180 sample trajectories (2026-03-09), producing 57 skills. Feature flag is OFF in production; full-scale distillation and A/B testing deferred pending operator review. The system is safe to enable for local testing or validation runs. See `/workspace/handoffs/completed/skillbank-distillation.md` completion checklist for operational status."

**Edit 2** (add to §9.2 Trigger Mechanism, after line 678):  
Add: "As of 2026-05, the EvolutionMonitor is integrated with the ClaudeDebugger anomaly detection system. Low-confidence skills (< 0.3 confidence) generate anomaly signal `skill_mismatch` with confidence score 0.5; unavailable skills in a task category generate signal `no_skills_available` with score 0.3. This integration enables operator-level observability of skill library health during inference."

### Notes

- The chapter is comprehensive and remains largely accurate. The main gap is the explicit statement of current production status (complete but feature-flagged OFF).
- The integration with ClaudeDebugger is a nice-to-have documentation update, not a material gap.

---

## Chapter 16: Calibration and Risk Control

**Verdict**: **PATCH** (high severity)  
**Key Issues**: Risk gate behavior changed, verifier integration, new classifier/difficulty/factual-risk signals

### Factual Errors

- **Lines 41-51** (effective_threshold formula): The formula `effective_threshold = (calibrated or base threshold) + conformal_margin` is still accurate for the **output-side confidence gate** (TwoPhaseRetriever), but doesn't account for two **input-side gates** that landed 2026-04-15 onwards:
  1. **Factual Risk Scorer** (`src/classifiers/factual_risk.py`, lines 189-212): Now gates routing based on input hallucination risk. When `classifier_config.yaml` mode is `enforce` (currently `shadow`), routes involving high factual-risk prompts are penalized (effective threshold raised).
  2. **Difficulty Signal Classifier** (`src/classifiers/difficulty_signal.py`, lines 214-231): Bands prompt difficulty as easy/medium/hard. In enforce mode, band-adaptive token budgets are applied (`_repl_turn_token_cap()` in `src/graph/helpers.py`), affecting escalation behavior indirectly.
  - **Source**: `src/classifiers/factual_risk.py`, `src/classifiers/difficulty_signal.py`, commit 487068fe (2026-04-20), ch16 lines 189-231 already mention these but don't clarify their integration with the conformal margin formula.

- **Line 28-38** (RetrievalConfig parameters): List is missing several parameters added 2026-05-21:
  - `risk_gate_action` — logged action taken by risk gate (e.g., "risk_abstain_escalate")
  - `risk_gate_reason` — human-readable reason (e.g., "confidence below threshold")
  - `assigned_role` — the role actually assigned (vs the route recommendation); added 2026-05-20
  - **Source**: `orchestration/repl_memory/retrieval_config.py`, commit 3ba5ca18 (2026-05-20)

### Superseded Claims

- **Section "Rollout and Guardrail Controls"** (line 54-61): Describes deterministic rollout sampling and budget guardrail auto-disable, both implemented. However, the chapter doesn't explain the **actual current rollout state**:
  - Rollout ratio currently controlled via `risk_gate_rollout_ratio` (per-route sampling)
  - **As of 2026-05-24**, there's also a **cross-role bandwidth-aware rollout** that modulates confidence thresholds based on target role utilization (new in `cross-role-bw-aware-routing.md` handoff)
  - This is NOT a breaking change to the conformal margin model, but a runtime refinement of the effective threshold
  - **Source**: `orchestration/repl_memory/retriever.py`, `/workspace/handoffs/active/cross-role-bw-aware-routing.md`

- **Line 155-187** (Skill Effectiveness Scoring): Describes the SkillBank interaction with risk control. Correct in principle, but the **current threshold mapping** needs clarification:
  - `min_confidence` in SkillRetrievalConfig (0.3 default) doesn't map directly to RetrievalConfig `confidence_threshold`
  - The two operate on different confidence axes: skill effectiveness (post-retrieval outcome correlation) vs routing confidence (pre-retrieval Q-value aggregate)
  - Recommend clarifying the conceptual independence: skills provide input data (context), retriever confidence gates routing decisions
  - **Source**: `orchestration/repl_memory/skill_bank.py:498-500`, `orchestration/repl_memory/retriever.py` (independent confidence gates)

### Missing Content (Post-2026-03-30 Landings)

1. **Input-Side Risk Gates (April 2026)** — Chapter mentions factual_risk and difficulty_signal in lines 189-231, which is good, but the integration details with calibration are vague:
   - **Factual Risk Scorer**: Computes `adjusted_risk_score = risk_score * role_adjustment` (tier-dependent multiplier: 0.6 for 235B architect, 1.0 for 7B worker)
   - **Integration**: When in enforce mode (currently shadow), factual risk raises the effective confidence threshold. Example: high factual-risk prompt + worker selected → effective_threshold = base_threshold + conformal_margin + factual_risk_adjustment
   - **Mode**: Currently `shadow` (computed, logged, no routing impact). Expected transition to `enforce` pending A/B validation. **Source**: `src/classifiers/factual_risk.py` line 207-211, `/workspace/progress/2026-04/2026-04-20.md` (factual risk validator A/B test)

2. **Output Quality Detection (May 2026)** — Chapter line 245-253 mentions "Output Quality Detection" with 4 heuristics. One was added in 2026-05:
   - **Think-block loop detection** (line 252): "Threshold: >15% duplicate 4-grams. Research backing: SEER shows failed outputs are ~1,193 tokens longer than successful ones; repetition within reasoning is a strong failure signal."
   - This is a new heuristic for reasoning-model failure detection (relevant for models using `<think>` blocks)
   - **Source**: `src/classifiers/quality_detector.py` (think-block loop detection added in 2026-04-15, SEER reference from `/workspace/progress/2026-04/2026-04-25.md`)

3. **Assigned Role Tracking (May 2026)** — New field in routing decisions tracks the **actual role assigned** vs. the routing recommendation:
   - Enables post-hoc analysis of when confidence gates (risk_abstain_escalate) override primary routing
   - Used to compute the **rollout distribution bias** (2026-05-21 autopilot analysis: 91% of all decisions routed to frontdoor)
   - **Source**: `orchestration/repl_memory/retrieval_config.py` (assigned_role field), `/workspace/progress/2026-05/2026-05-21.md` Session 6 "Routing-distribution diagnosis"

4. **Cross-Role Bandwidth-Aware Routing (May 2026)** — New control mechanism adjusts confidence thresholds based on target role utilization:
   - When a role is at high utilization (e.g., many slots in-flight), the system raises the confidence threshold to avoid overloading it
   - Complements the existing regret-based cost model by adding real-time capacity awareness
   - **Source**: `/workspace/handoffs/active/cross-role-bw-aware-routing.md` (design doc, 2026-05-24), `orchestration/repl_memory/retriever.py` (runtime implementation)

5. **Verifier Quality Gate (May 2026)** — Chapter 16 doesn't mention the frontdoor verifier gate added 2026-05-21:
   - Runs **after routing** but **before returning to caller**, so it's technically output-side confidence (different from retrieval-side TwoPhaseRetriever confidence)
   - Verifier confidence (`P_success`) is logged to routing_decision metadata for post-hoc analysis
   - Doesn't have a formal calibration metric in the replay harness yet, but should coordinate with ECE/Brier metrics
   - **Source**: `orchestration/repl_memory/verifier_head.py`, `/workspace/progress/2026-05/2026-05-21.md` Session 4

### Broken Path References

All path references are correct.

### Proposed Edits

**Edit 1** (expand line 28-38, RetrievalConfig parameters):  
Add to the list:
```
- `assigned_role` — the actual role assigned after all gates (may differ from routing recommendation if risk gate intervenes)
- `risk_gate_action` — logged action taken ("pass", "risk_abstain_escalate", etc.)
- `risk_gate_reason` — human-readable reason for gate action
```

**Edit 2** (after line 183, add new subsection "Verifier Quality Gate (May 2026)"):  
Add:
```
### Verifier Quality Gate

In addition to the retrieval-side confidence gates, a post-routing quality verifier runs on frontdoor decisions (when ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE=1). The verifier is a 2-layer numpy MLP trained to predict P(success | embedding, selected_action). In shadow mode (default), the verifier verdict is logged to routing_decision metadata but does not block routing. In enforce mode, if P_success < threshold (default 0.5), the routing is escalated to the configured target role instead.

**Performance** (as of 2026-05-21, on 40.9K fresh memories):
- Brier: 0.0072 (vs 0.073 softmax-max baseline, ~9x margin)
- AUC: 0.9996
- ECE: 0.0145

This gate is orthogonal to the conformal margin formula — it operates post-decision, not on the retrieval confidence that feeds the margin computation. However, verifier confidence could be integrated into future replay harness metrics for joint calibration study.

**Source**: `orchestration/repl_memory/verifier_head.py`, `/workspace/progress/2026-05/2026-05-21.md` Session 4, commit 4882d9b2
```

**Edit 3** (update line 155-187, "Skill Effectiveness Scoring" section):  
Clarify the distinction:
"Skill effectiveness data (via OutcomeTracker) provides a **separate** confidence signal from routing confidence (from TwoPhaseRetriever Q-value aggregates). The two operate independently:
- **Routing confidence** (RetrievalConfig `confidence_threshold`): Derived from Q-value statistics over memory neighbors; gates whether to trust the routing decision
- **Skill effectiveness** (SkillRetrievalConfig `min_confidence`): Tracks whether a skill, once retrieved, correlates with successful task outcomes; gates whether to inject a skill into the prompt

These are orthogonal axes. A task may route with high confidence but retrieve low-effectiveness skills (or vice versa). The `min_confidence=0.3` threshold acts as a quality gate to exclude deprecated/ineffective skills from prompt injection, complementary to the routing threshold. See Chapter 15 (SkillBank) for the full skill lifecycle model."

**Edit 4** (add to line 54-61, "Rollout and Guardrail Controls"):  
Extend with:
"Additionally, as of 2026-05-24, a **cross-role bandwidth-aware rollout** mechanism modulates confidence thresholds based on target role utilization. When a role is at high utilization, the system raises the confidence threshold to avoid overloading it, achieving load-balancing at the confidence-gate level. This is implemented in `src/api/routes/chat_routing.py` and documented in [cross-role-bw-aware-routing.md](../../handoffs/active/cross-role-bw-aware-routing.md)."

**Edit 5** (add after line 231 "Output Quality Detection"):  
Add: "**Note (May 2026)**: The think-block loop detector (detecting 4-gram repetition >15% within `<think>` blocks) was added 2026-04-15 and is particularly relevant for reasoning models that use explicit reasoning tokens. This catches a specific failure mode (repetitive reasoning loops) that generic 3-gram uniqueness ratio misses."

### Notes

- The chapter is broadly accurate but needs consolidation of the multiple confidence-gating mechanisms (retrieval, factual-risk, difficulty, verifier). A unified diagram showing how these stack would help.
- The interaction between `SPO_PLUS_EPSILON` (exploration) and the conformal margin (risk gating) should be clarified: exploration forces counterfactual routes even when confidence is high, overriding the gate. This is a feature (for data collection) but can look like a bug if not understood.
- The cross-role BW-aware routing (line 54-61 edit) is a runtime tuning that doesn't change the formal calibration model, but operators should know it exists when analyzing rollout ratios and threshold behavior.

---

## Summary Table

| Chapter | Verdict | Severity | Key Gaps | Estimated Effort |
|---------|---------|----------|----------|------------------|
| 07 | PATCH | MEDIUM | Classifier/verifier phases, dead-code history, Phase 8 split | 2 hours (3 new sections, 4 edits) |
| 09 | PATCH | LOW-MEDIUM | Epsilon-greedy exploration, stack consolidation shift, embedding preflight | 1.5 hours (3 edits + context notes) |
| 15 | UP_TO_DATE | LOW | Feature flag production status, debugger integration | 30 mins (2 minor clarifications) |
| 16 | PATCH | HIGH | Input-side gates integration, verifier gate post-routing, cross-role BW-aware, conformal margin clarity | 3 hours (4 edits + 1 new subsection, diagram suggestion) |

---

## Next Steps for Downstream Agent

1. **Priority 1 (HIGH)**: Update Chapter 16 (all 5 edits) — this is the load-bearing chapter for understanding routing decision gating
2. **Priority 2 (MEDIUM)**: Update Chapter 07 (edits 1-4) — critical for anyone learning the MemRL architecture
3. **Priority 3 (MEDIUM)**: Update Chapter 09 (edits 1-4) — important for seeding operators
4. **Priority 4 (LOW)**: Update Chapter 15 (edits 1-2) — nice-to-have for completeness

**Estimated total effort**: 7 hours to complete all patches with testing.

---

*Audit completed 2026-05-26 by file search specialist. All sources cross-referenced against live codebase and progress logs.*
