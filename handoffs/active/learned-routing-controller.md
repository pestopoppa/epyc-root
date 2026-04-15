# Learned Routing Controller: MLP Distillation from Episodic Memory

**Created**: 2026-04-15
**Status**: Phase 1 COMPLETE — 92% val acc, flag enabled. Phase 2 P2.1-P2.2 DONE (endpoint built), P2.3+ needs inference.
**Priority**: HIGH (low-hanging fruit — infrastructure exists, just needs retraining with better data)
**Related**: [routing-intelligence.md](routing-intelligence.md), [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md), SkillBank (completed handoff)
**Rollback**: Set `ORCHESTRATOR_ROUTING_CLASSIFIER=0` (default). Zero schema/API/data changes.

---

## Problem

The routing MLP classifier (`routing_classifier.py`) exists but was trained on raw, unnormalized action labels from the episodic store. The store has ~30 distinct action strings that should map to ~5 clean routing targets. Escalation events (10K+ labeled examples of "frontdoor was wrong") aren't being used as training signal. The classifier feature flag is OFF.

Meanwhile, the fallback KNN retrieval pipeline (FAISS + Q-ranking, 10-50ms/request) runs on every request because the classifier was never production-validated.

## Solution

Retrain the existing MLP with normalized labels and per-class confidence thresholds. The infrastructure is complete — this is a data quality + calibration improvement, not a new build.

### Architecture (unchanged — already wired)

```
Request arrives
    |
[MLP classifier]  <1ms, ~200K params, numpy-only
    |
conf >= per-class threshold?
    |--- Yes --> route immediately (strategy: "classifier")
    |--- No  --> fall through to full MemRL pipeline (10-50ms)
                    |
              [Episodic KNN + Q-ranking + risk gate]
                    |
              Log (embedding, decision, outcome) --> write-only append
                    |
              Periodic retrain --> updated weights file
```

### Key Insight: Episodic Memory Becomes Write-Only

Once the MLP handles the common case, episodic memory shifts from **runtime query target** (expensive FAISS lookup per request) to **write-only append log** (cheap INSERT). It becomes an experience replay buffer for retraining, not an inference engine. The full retrieval pipeline only fires on MLP fallthrough.

---

## Decision Surfaces

### Phase 1 (current): Role selection only

| Surface | Choices | Training data |
|---------|---------|---------------|
| **Role selection** | 5 classes (frontdoor, architect_general, architect_coding, coder_escalation, worker_explore) | 174K normalized episodic memories |

### Future phases: Additional surfaces (independent models)

| Surface | Choices | Training data | Status |
|---------|---------|---------------|--------|
| Mode selection | direct vs repl | Action field encodes mode | Data exists, needs extraction |
| Escalation prediction | Binary (will frontdoor fail?) | 10,528 positive + 56,457 negative | Ready |
| Context injection budget | Continuous (0-2000 tokens) | SkillBank effectiveness_score | Needs collection |
| Multi-turn budget | Integer (1-10 REPL turns) | Session turn counts | Needs extraction |

**Excluded**: Speculative decoding parameters (hardware-bound, not task-dependent).

**Architecture decision**: Independent models per surface, not shared trunk. Routing has 174K clean labels; other surfaces have 10K or less. Don't risk degrading the best-data task with noisy co-training. Merge to multi-task only after all surfaces have abundant data + experiment confirms no routing accuracy regression.

---

## Training Data

### Action Label Normalization

The episodic store has ~30 distinct action strings. Mapping to 5 clean classes:

| Raw action | Count | Map to | Rationale |
|---|---|---|---|
| `frontdoor` | 70,060 | **frontdoor** | Clean organic data |
| `architect_general` | 41,624 | **architect_general** | Clean organic data |
| `architect_coding` | 36,710 | **architect_coding** | Clean organic data |
| `escalate:frontdoor->coder_escalation` | 10,528 | **coder_escalation** | Destination = correct initial route. 91% failure at frontdoor = high-conviction signal |
| `WORKER` | 7,497 | **worker_explore** | Seeding data, 88% task_type=chat |
| `SELF` | 2,066 | **frontdoor** | SELF = frontdoor handles it. 100% failure — negative signal |
| `ARCHITECT` | 2,034 | **architect_general** | Seeding data, spread across task types |
| `SELF:direct` | 1,893 | **frontdoor** | Includes mode annotation |
| `SELF:repl` | 1,552 | **frontdoor** | Includes mode annotation |
| `escalate:coder->architect` | 16 | **architect_coding** | Destination = correct route |

**Excluded** (2,250 memories): `<empty>` (2,138 "Hello" probes), `frontdoor:repl/direct/react` (17 seeded), `persona:*` (15 seeded), code snippet exemplars (~80).

**Post-normalization distribution:**

| Class | Count | % |
|---|---|---|
| frontdoor | 75,571 | 43% |
| architect_general | 43,658 | 25% |
| architect_coding | 36,726 | 21% |
| coder_escalation | 10,528 | 6% |
| worker_explore | 7,497 | 4% |
| **Total** | **173,980** | |

3 zero-data classes (worker_math, worker_vision, ingest_long_context) deferred — MLP uses 8 output neurons but unused classes receive no gradient until data exists.

---

## Implementation Plan

### Phase 1: Retrain with Normalized Labels

- [x] **P1.1** Update `extract_training_data.py` with label normalization mapping — DONE 2026-04-15
- [x] **P1.2** Re-embed 157K memories via 8 parallel BGE servers (17 min) — DONE 2026-04-15
- [x] **P1.3** Run extraction + training — **92.0% val accuracy** (4 classes, 157K samples) — DONE 2026-04-15
- [x] **P1.4** Add per-class confidence thresholds + calibration (precision >= 0.9) — DONE 2026-04-15

**Training results (2026-04-15):**

| Class | Val Accuracy | Val Samples | Calibrated Threshold |
|-------|-------------|-------------|---------------------|
| frontdoor | 91.5% | 14,459 | 0.447 |
| architect_general | 95.1% | 8,406 | 0.362 |
| architect_coding | 95.7% | 7,342 | 0.560 |
| worker_explore | 56.7% | 1,297 | 0.806 |
| coder_escalation | — | 0 (no objectives) | 0.950 (default) |

**Note**: coder_escalation (10K entries) excluded from training — all escalation memories have empty objective fields (logged at escalation time, not initial routing). Worker_explore accuracy is low (56.7%) because seeding data was 88% task_type=chat with low Q-values, making it look like frontdoor. Both gaps will improve as organic data with proper objectives accumulates.

- [x] **P1.5** Enable `ORCHESTRATOR_ROUTING_CLASSIFIER=1` in `orchestrator_stack.py` — DONE 2026-04-15. Takes effect on next API restart.
- [x] **P1.6** Add extraction step to autopilot `structural_lab.py` before classifier training — DONE 2026-04-15

### Phase 1.5: Logit-Based Probe (No llama.cpp changes)

Validate "piggyback on frontdoor" concept before investing in hidden-state extraction.

- [ ] **P1.5.1** Instrument frontdoor to log top-k=64 first-token log-probabilities
- [ ] **P1.5.2** Collect over ~1000+ requests
- [ ] **P1.5.3** Train linear probe (512 params), evaluate accuracy
- [ ] **P1.5.4** Decision gate: >= 80% → proceed to Phase 2; < 60% → stay with BGE+MLP

### Phase 2: Hidden State Probe (llama.cpp fork changes required)

**SSM hybrid awareness**: Frontdoor is Jamba-style (Mamba SSM + attention). Probe attention layers only. Mean-pool across all token positions (SSM last-token state is recency-biased).

- [x] **P2.1** Enumerate attention layer indices — DONE 2026-04-15. Qwen3.5-35B-A3B: 41 layers, attention at 0,4,8,12,16,20,24,28,32,36,40 (11 layers), hidden_dim=2048
- [x] **P2.2** Add `/hidden-states` endpoint to llama.cpp-experimental — DONE 2026-04-15. Commit `4c7fe20c6`. Graph capture + context mean-pooling + C API + server endpoint.
- [ ] **P2.3** Collect mean-pooled hidden states at each attention layer during inference (needs live server test)
- [ ] **P2.4** Train independent linear probes per attention layer — find best
- [ ] **P2.5** If complementary, use learned attention pooling (N learnable weights)
- [ ] **P2.6** Decision gate: >= 90% → Phase 3; < 80% → stay with BGE+MLP

### Phase 3: BGE Elimination (Conditional on Phase 2)

- [ ] **P3.1** Replace BGE embedding with hidden-state features in MLP input
- [ ] **P3.2** Remove BGE model from inference path (~300MB RAM, ~5-10ms/request saved)
- [ ] **P3.3** Update episodic store schema (hidden states instead of BGE embeddings)

### Retraining Strategy

**Batch retraining, manually triggered initially.** Training on 174K samples is <1 minute on CPU. Automate frequency after understanding distribution shift patterns.

Future: automatic trigger after N new decisions, idle-window scheduling, staleness detection.

---

## Relationship to Existing Systems

| System | Relationship | Impact |
|--------|-------------|--------|
| **Episodic memory** | Becomes write-only during inference (read only for retraining) | None — still logs everything |
| **Autopilot** | Consumer of episodic data, separate from MLP | None — independent data flows |
| **SkillBank** | Complementary: SkillBank = "what model should do", MLP = "which model does it" | None — different optimization axes |
| **Q-Scorer** | Continues scoring outcomes → feeds episodic store → feeds MLP retraining | None — unchanged |
| **HybridRouter** | MLP classifier fast-path already wired (line 767) | Toggle via feature flag |

---

## Open Questions

1. **Class imbalance** — frontdoor is 43%. Start with class-weighted loss, measure per-class recall.
2. **SSM probing viability** (Phase 2) — no literature on probing Mamba/Jamba hidden states. Phase 1.5 de-risks.
3. **Mean-pool vs attention-pool** (Phase 2) — test both for hidden states across token positions.

---

## Key Files

All orchestrator paths relative to `/mnt/raid0/llm/epyc-orchestrator/`.

| Component | Path | Status |
|-----------|------|--------|
| **MLP classifier** | `orchestration/repl_memory/routing_classifier.py` | EXISTS — 2-layer numpy MLP, ~200K params |
| **Training script** | `scripts/graph_router/train_routing_classifier.py` | EXISTS |
| **Data extraction** | `scripts/graph_router/extract_training_data.py` | EXISTS — needs label normalization (P1.1) |
| **Classifier weights** | `orchestration/repl_memory/routing_classifier_weights.npz` | EXISTS — needs retraining |
| **HybridRouter fast-path** | `orchestration/repl_memory/retriever.py` (line 767) | EXISTS — wired with fallback |
| **Feature flag** | `src/features.py` (line 108, `routing_classifier`) | EXISTS — default OFF |
| **A/B test scaffold** | `scripts/graph_router/ab_test_classifier.py` | EXISTS |
| **Autopilot hooks** | `scripts/autopilot/species/structural_lab.py` | EXISTS |
| Episodic store | `orchestration/repl_memory/sessions/episodic.db` | 175K memories (2026-04-04 to 2026-04-15) |
| Q-Scorer | `orchestration/repl_memory/q_scorer.py` | Reward computation |
