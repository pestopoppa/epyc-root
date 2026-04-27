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

### Phase 4: Trinity-Derived Methodology Audits (NEW 2026-04-26)

Source: deep-dive [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) on Trinity (intake-474, ICLR 2026, Sakana AI). Trinity is the most direct prior art for this handoff's thesis. These four tasks are the *portable methodology lessons* — they apply regardless of whether we end up adopting their full architecture.

Order tasks by cost: P4.1 is cheapest (audit only), P4.4 is most expensive (overnight ES run). Each phase's go/no-go feeds the next.

- [ ] **P4.1** **Feature-extraction position audit (cheap)**: Trinity's ablation shows penultimate-vs-final-token costs >10 points on LiveCodeBench (decoder-specific result). For our BGE encoder, the analogous knob is CLS vs mean-pool vs last-layer hidden states. Today our 1031-dim input is BGE-large pooled output (verify exact pool method by reading `embedder.py`). Run a comparative ablation on the existing 174K-label training set — three head retrains, no architecture change, single training session. Decision gate: if mid-pool ablation shows ≥1-point val-acc spread, document the best pool method and switch the default; if not, mark BGE feature-position as solved and move on.
- [ ] **P4.2** **Block-ε-separability diagnostic (medium cost)**: Trinity's optimizer-choice argument rests on the loss surface being block-ε-separable (formal Hessian-based definition; their empirical evidence is a "block-diagonal-10" head retaining competitive performance). Mirror this on our setup: train identical 2-layer heads with (a) full-rank weights, (b) block-diagonal-10 weights (10 disconnected blocks), (c) diagonal-only weights, on existing 175K episodic labels. If mid-rank ≈ full-rank within ~2 points val acc, our routing geometry matches Trinity's and ES becomes methodologically appropriate (gates P4.4). If full-rank dominates, our problem is not block-ε-separable and Trinity's optimizer argument does NOT transfer to us. Either outcome is informative — record in deep-dive Section 6 ("Open Questions").
- [ ] **P4.3** **SVD-scale fine-tuning trial (medium cost)**: Trinity uses singular-value FT on the backbone — learn only singular-value scales, keep orthogonal matrices fixed (~9K extra params). Their ablation: removing SVD-FT costs −3 to −4 points across all four benchmarks. This is a parameter-efficient adaptation cheaper than LoRA and applicable to whatever backbone we use as the routing-head feature extractor. Currently we treat BGE as fully frozen. Implement SVD-FT on BGE's last `k` transformer blocks, retrain the head end-to-end, A/B against frozen-BGE on val set. Decision gate: if Δ ≥ +2 points val acc, promote SVD-FT to default; if flat, record null result and move on.
- [ ] **P4.4** **sep-CMA-ES cold-start spike (large cost; gated on P4.2 favourable + a cold-start surface)**: Trinity trains the routing head with sep-CMA-ES against terminal binary reward (no labels). Population λ≈32, replication m=16, total budget 1.5k–40k evaluations. Direct application to our setup: when a *new* routing surface comes online (Phase 2/3 hidden-state probe, or a new role surface, or a new model added to the pool), there are zero episodic labels to distill from. ES against eval-tower fitness can train the head from cold. Replication budget estimate (deep-dive Section 5): population λ≈45 for our 200K-param head, m=16 reps, ≈720 fitness evals per generation, ≈10 generations as feasibility-test target ≈ 10h overnight at 32-way concurrency. Prerequisites: (a) eval-tower wired as a per-question scorable, parallelisable fitness oracle (Math-Verify adoption is on the critical path — see `routing-and-optimization-index.md` cross-cutting concern #13), (b) `pycma` or equivalent sep-CMA-ES library vendored. Decision gate: if cold-start ES achieves within 5 points of SFT-trained head with comparable wall-clock, adopt as the cold-start recipe; if not, record null and stick with SFT distillation.

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

## Research Intake Update — 2026-04-26

### New Related Research

- **[intake-474] "TRINITY: An Evolved LLM Coordinator"** (arxiv:2512.04695, ICLR 2026, openreview:5HaRjXai12)
  - Authors: Jinglue Xu, Qi Sun, Peter Schwendeman, Stefan Nielsen, Edoardo Cetin, Yujin Tang
  - Relevance: Validates this handoff's lightweight-head architectural choice at a slightly larger scale and offers a training recipe for the cold-start case where distillation labels are unavailable. Trinity = ≈0.6B base LM + ≈10K-parameter head; this handoff's classifier ≈ embedding model + ≈200K MLP parameters — same shape, comparable budget.
  - Key technique: penultimate-token hidden state of a 0.6B LM is read out to logits over agent roles (Thinker / Worker / Verifier); the head is trained with **separable CMA-ES** rather than supervised distillation. No SFT, no RL, no labelled data — fitness comes from end-task success on the agent pool.
  - Reported results: 86.2% on LiveCodeBench; outperforms individual constituent models across coding/math/reasoning/domain-knowledge benchmarks; robust OOD generalization.
  - Delta from current approach: Phase 1 of this handoff trains the MLP via supervised distillation from normalized episodic labels (92% val acc). Trinity demonstrates that a comparably-sized head can be trained without labelled targets when end-task fitness is observable — directly addresses the cold-start problem flagged for new role surfaces (Phase 1.5+) where episodic labels do not yet exist. Also hints at an alternative input encoder choice: penultimate-token of a small LM rather than a separate embedding model.
  - Recommended follow-up: in Phase 2/3, evaluate sep-CMA-ES as a fallback trainer for new routing surfaces that lack episodic distillation data. Confirm whether penultimate-token-of-0.6B-LM beats embedding-model + MLP on our routing accuracy benchmark before considering an encoder swap.
  - **Deep-dive**: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) — Trinity is the most direct prior art for this handoff's thesis. Sections 2 (cross-check vs our stack), 3 (portable / not portable), and 5 (replication budget estimate, ≈10h overnight at 32-way concurrency for a sep-CMA-ES feasibility test) directly inform Phase 2/3 design. Specific portable items mapped to this handoff: action #2 (block-ε-separability diagnostic on our 175K-label landscape), action #3 (sep-CMA-ES cold-start spike), action #5 (SVD-scale FT on the backbone, ~9K extra params), action #7 (audit BGE feature-extraction position — CLS vs mean-pool vs last-layer; Trinity's 10-point penultimate-vs-final swing is a reminder this matters).
