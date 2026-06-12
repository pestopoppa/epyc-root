# Learned Routing Controller: MLP Distillation from Episodic Memory

**Created**: 2026-04-15
**Status**: REFRESHED 2026-06-12 (BGE+MLP repair follow-up) — classifier fast-path is **STAGED, not live**: fresh `routing_classifier_weights.npz` now exists and wiring preflight passes, but production still attests `routing_classifier=false` across 6 workers pending a rollout decision. The historical "Phase 1 COMPLETE — 92% val acc, flag enabled" claim below describes pre-reset state; current retrain is 81.0% val acc with thresholded >=0.8 precision 94.4% over 61.6% coverage. The BGE repair blocker is cleared (see [retrain-routing-models.md](retrain-routing-models.md)): 275,960 FAISS vectors, 94.6% coverage, diagnose-only HEALTHY. **Phases 1.5+ are FROZEN per fable5-findings-02** pending a future DAR-1 regret replay >=5% plus per-question eval vectors.
**Priority**: ACTIVE for rollout decision of the repaired BGE+MLP fast path; FROZEN for expansion. Do not promote logit/hidden-state/GraphRouter-style expansion until the fable5 routing-freeze gates clear.
**Related**: [routing-intelligence.md](routing-intelligence.md), [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md), [retrain-routing-models.md](retrain-routing-models.md), [decision-aware-routing.md](decision-aware-routing.md), SkillBank (completed handoff)
**Rollback**: Set `ORCHESTRATOR_ROUTING_CLASSIFIER=0` (default). Zero schema/API/data changes. (With weights missing, flag-ON is already functionally equivalent to fallback — but the flag should be reconciled with reality.)

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

- [/] **P4.1** **Feature-extraction position audit** — **Phase A (audit) DONE 2026-05-07; Phase B (experiment) deferred pending FAISS rebuild + per-run inference approval.**

  **Phase A audit findings (analytical, no code):**

  1. **Current pool method confirmed as CLS** (not mean-pool). Per `epyc-orchestrator/scripts/server/orchestrator_stack.py:862`: BGE-large-en-v1.5 launches with `--pooling cls`. Comment in source: "BGE uses CLS token pooling (standard BERT)". This is the BGE-trained pool method (BGE was distilled with [CLS] as the pooled output) — switching to mean-pool or last-layer would diverge from the training distribution.
  2. **Data-scale finding: handoff text says 174K labels, actual on-disk state is ~8K memories.** Production episodic.db at `/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/sessions/episodic.db` has 8,115 rows (135 MB file size is bloat from prior larger state + FTS). The 174K figure was aspirational from a previous epoch; current routing-classifier training would draw from 8K, not 174K. With 8K labels, binomial 95% CI half-width on per-arm val-acc is ~3-4 pp depending on val split — borderline for the ≥1 pp decision-gate.
  3. **FAISS index is currently RESET.** `embeddings.faiss` is 385 KB (current) vs `.bak` 32 MB (Apr 28 snapshot). The live FAISS holds essentially no embeddings. Backup `.bak` files contain ~9.2K embeddings consistent with the DB row count.
  4. **Implication for Phase B**: a real ablation requires (i) rebuilding FAISS from DB (≈40s of BGE inference), (ii) running BGE again for each alternative pool (`--pooling mean`, `--pooling last`) to produce 2 more 8K × 1024-dim matrices. Total inference: 3 × ~40s + 3 × startup ≈ 5 min wall-clock. Plus 3 head retrains (seconds, CPU-bound). The full ablation is cheap, but does require crossing the inference threshold.
  5. **Trinity transfer caveat (re-emphasised)**: Trinity's penultimate-vs-final-token result is decoder-specific. BGE is a bidirectional encoder — its pool methods have different theoretical implications. Trinity's 10-point swing should NOT be expected here. The decision gate of ≥1 pp is appropriate (smaller expected effect size on encoder).

  **Phase B (deferred — explicit per-run inference approval required, per `feedback_no_concurrent_inference`):**

  ```bash
  # Step 1: rebuild FAISS index from live episodic.db (uses current --pooling cls)
  python3 scripts/graph_router/extract_training_data.py
    --output orchestration/repl_memory/training_data_cls.npz

  # Step 2: re-launch BGE with mean pooling
  pkill -f 'llama-server.*bge'  # tear down current cls server
  OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_NUM_THREADS=16 \
    /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
      --model /mnt/raid0/llm/models/bge-large-en-v1.5-f16.gguf \
      --port 8090 --host 127.0.0.1 --threads 16 \
      --embedding --pooling mean &
  python3 scripts/graph_router/extract_training_data.py
    --output orchestration/repl_memory/training_data_mean.npz

  # Step 3: re-launch BGE with last-token pooling
  pkill -f 'llama-server.*bge'
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
    ... --pooling last &
  python3 scripts/graph_router/extract_training_data.py
    --output orchestration/repl_memory/training_data_last.npz

  # Step 4: train 3 heads with identical hyperparameters
  for variant in cls mean last; do
    python3 scripts/graph_router/train_routing_classifier.py \
      --data orchestration/repl_memory/training_data_${variant}.npz \
      --output orchestration/repl_memory/routing_classifier_weights_${variant}.npz
  done

  # Step 5: compare val acc across variants
  python3 scripts/graph_router/ab_test_classifier.py
    --weights orchestration/repl_memory/routing_classifier_weights_*.npz
  ```

  **Decision gate (when Phase B runs)**: best pool method becomes default if Δ val-acc ≥ 1 pp vs CLS baseline AND 95% CI rules out the null. With n=8K, this requires |Δ| ≥ ~4 pp for statistical confidence (half-width is sample-size-bounded, not protocol-bounded). If no variant moves the needle ≥4 pp, mark feature-position as solved (CLS stays default) and move on. If a variant wins, switch default in `orchestrator_stack.py:862` and document.

  **Recommended sequencing**: bundle Phase B with P4.1.3 (IRT-feature variant) into a single inference run — same BGE invocations, +1 head retrain. Total wall-clock for combined P4.1 + P4.1.3 ≈ 10-15 min once authorized.
- [ ] **P4.1.3** **IRT-feature audit (intake-496 LLM Bandit, +1 session bundled with P4.1)**: extend the P4.1 ablation to include an IRT-based prompt feature variant. Train a quick IRT (Item Response Theory) score predictor over the BGE pooled output that emits `(latent_difficulty, latent_discrimination)` per prompt; concatenate this 2-D output to the BGE embedding as a fourth feature variant. Compare against BGE-CLS / BGE-mean / BGE-last on val acc. Decision gate: if IRT-augmented features show ≥1-point val-acc improvement over the best pure-BGE variant, escalate IRT to a separate phase plan (cross-link to DAR-5 in `decision-aware-routing.md`). If null, record the result and stick with the best pure-BGE variant. **Bundled with P4.1**: same training infrastructure, same 174K labels, +1 session for IRT scorer training and one extra retrain.
- [ ] **P4.2** **Block-ε-separability diagnostic (medium cost)**: Trinity's optimizer-choice argument rests on the loss surface being block-ε-separable (formal Hessian-based definition; their empirical evidence is a "block-diagonal-10" head retaining competitive performance). Mirror this on our setup: train identical 2-layer heads with (a) full-rank weights, (b) block-diagonal-10 weights (10 disconnected blocks), (c) diagonal-only weights, on existing 175K episodic labels. If mid-rank ≈ full-rank within ~2 points val acc, our routing geometry matches Trinity's and ES becomes methodologically appropriate (gates P4.4). If full-rank dominates, our problem is not block-ε-separable and Trinity's optimizer argument does NOT transfer to us. Either outcome is informative — record in deep-dive Section 6 ("Open Questions"). **Outcome of P4.2 directly gates DAR-4's bilinear-scorer architecture choice (full-rank vs rank-restricted W) per [`decision-aware-routing.md`](decision-aware-routing.md) DAR-1.5 audit (2026-05-07). DAR-1.5 conclusion: per-action Q-table architectures (DAR-2 / DAR-3) are trivially block-diagonal (`ε_H=0` by construction) so DAR-3 is unblocked unconditionally; bilinear architectures (DAR-4) introduce shared-W coupling by design and need rank-restriction or sep-CMA-ES if P4.2 confirms our landscape is separable.**
- [ ] **P4.3** **SVD-scale fine-tuning trial (medium cost)**: Trinity uses singular-value FT on the backbone — learn only singular-value scales, keep orthogonal matrices fixed (~9K extra params). Their ablation: removing SVD-FT costs −3 to −4 points across all four benchmarks. This is a parameter-efficient adaptation cheaper than LoRA and applicable to whatever backbone we use as the routing-head feature extractor. Currently we treat BGE as fully frozen. Implement SVD-FT on BGE's last `k` transformer blocks, retrain the head end-to-end, A/B against frozen-BGE on val set. Decision gate: if Δ ≥ +2 points val acc, promote SVD-FT to default; if flat, record null result and move on.
- [ ] **P4.4** **sep-CMA-ES cold-start spike (large cost; gated on P4.2 favourable + a cold-start surface)**: Trinity trains the routing head with sep-CMA-ES against terminal binary reward (no labels). Population λ≈32, replication m=16, total budget 1.5k–40k evaluations. Direct application to our setup: when a *new* routing surface comes online (Phase 2/3 hidden-state probe, or a new role surface, or a new model added to the pool), there are zero episodic labels to distill from. ES against eval-tower fitness can train the head from cold. Replication budget estimate (deep-dive Section 5): population λ≈45 for our 200K-param head, m=16 reps, ≈720 fitness evals per generation, ≈10 generations as feasibility-test target ≈ 10h overnight at 32-way concurrency. Prerequisites: (a) eval-tower wired as a per-question scorable, parallelisable fitness oracle (Math-Verify adoption is on the critical path — see `routing-and-optimization-index.md` cross-cutting concern #13), (b) `pycma` or equivalent sep-CMA-ES library vendored. Decision gate: if cold-start ES achieves within 5 points of SFT-trained head with comparable wall-clock, adopt as the cold-start recipe; if not, record null and stick with SFT distillation.

### Phase 5: IRT-Stratified Cold-Start Onboarding (NEW 2026-04-28, from intake-496)

Source: intake-496 (LLM Bandit) — model identity vectors + Item Response Theory (IRT) discrimination-score-stratified prompt selection enable cold-starting a new specialist with 20–50 carefully chosen prompts instead of a full benchmark sweep.

**Why this matters for EPYC**: every model swap currently triggers a full benchmark sweep against the q-scorer baselines. Recent swaps (worker → 30B-A3B 2026-03-21, q-scorer recalibration 2026-03-21, coder Q4KM 2026-03-24) each cost a sweep. If the IRT-stratified cold-start workflow produces baselines within ~2 points of the full sweep, future swaps compress from a multi-hour sweep to a focused ~30-minute calibration. **This is the most actionable single experiment from intakes 495/496.**

Sequencing note: P5 is gated on having an IRT scorer (built in P5.1), NOT on Phase 2/3 completing. P5 can run in parallel with Phase 2 hidden-state work.

- [ ] **P5.1** **IRT discrimination scorer (~80–100 LoC, ~2 sessions)**: implement an Item Response Theory model over BGE prompt embeddings, fit on the existing 174K routing memories using observed per-model outcomes as IRT responses. Output per prompt: `(latent_difficulty, latent_discrimination)`. The discrimination score is what stratified-sampling uses — high-discrimination prompts separate model abilities; low-discrimination prompts are uninformative. Calibrated via Platt scaling against held-out outcomes. **Files**: new `irt_scorer.py`. Reuse for DAR-5 (intake-496 prompt features) and P4.1.3 (IRT-feature audit).
- [ ] **P5.2** **Cold-start A/B vs on-disk full sweep (~70 LoC harness, 1 session)**: pick an existing specialist (e.g., `architect_coding`) for which we already have a full benchmark sweep on disk. Use the IRT scorer to select 50 IRT-stratified prompts from the seeding/eval pool. Re-onboard the specialist using only those 50 prompts; produce an estimated baseline_tps / baseline_quality / memory_cost vector. Compare against the on-disk full sweep. Record agreement (e.g., per-feature absolute error and correlation). **Decision gate**: if the IRT-stratified estimate agrees with the full sweep within agreement threshold X (proposed: ≤ 5% relative error on each baseline feature) and the latency advantage is real (≥ 5× faster than the full sweep wall-clock), adopt IRT cold-start as the default new-model onboarding workflow; otherwise record null and continue with full sweeps. **Files**: new `scripts/calibration/irt_cold_start_ab.py`; reads existing on-disk sweep artefacts; produces a comparison report.
- [ ] **P5.3** **(conditional)** Production rollout: if P5.2 passes its decision gate, document the cold-start workflow in `routing-intelligence.md` as the standard new-model onboarding procedure, and add a `tools/onboard_specialist.py` CLI that wraps P5.1 + the calibration harness. ~1 session, no new code beyond CLI assembly.

### Phase 6: Per-Decision Verifier (NEW 2026-05-21, scoping only)

**Source**: deep-dive [`research/deep-dives/2026-05-21-recursive-reasoning-routing.md`](../../research/deep-dives/2026-05-21-recursive-reasoning-routing.md) Hypothesis C ("GRAM-as-verifier"). User-authorized scoping on 2026-05-21 in response to the standing thread on training a network dedicated to routing.

**Thesis**: today's router has no separate verifier head. Confidence comes from the softmax magnitude of the same MLP that emits the class prediction. A *distinct* verifier — trained on a *distinct* objective (probability that the proposed action is correct) — is a real architectural advance that none of `decision-aware-routing.md`, `outer-coordinator-learned-head.md`, or any prior Phase of this handoff proposes.

**The verifier interface**:

```
                  ┌────────────────────────────────────────┐
   request ─────► │  Existing routing pipeline:            │
                  │   BGE embed ─► RoutingClassifier MLP   │
                  └─────────────┬──────────────────────────┘
                                │ (top class, top prob)
                                ▼
                  ┌────────────────────────────────────────┐
                  │  NEW: Verifier head                    │
                  │   in:  (1024-d BGE) ⊕ (5-d one-hot)    │
                  │   out: P(action is correct) ∈ [0,1]    │
                  └─────────────┬──────────────────────────┘
                                │
                  P_correct ≥ τ ─┤── Yes ► route via MLP top class
                                └── No  ► fall through to FAISS KNN
```

This *replaces the per-class confidence threshold* (currently the per-class calibrated threshold from P1.4, e.g., frontdoor 0.447, architect_coding 0.560) with a *learned* gate trained on the actual correctness label.

**Training data exists** (per P1 normalization table): 10,528 positive failure examples (escalation memories = MLP routed wrong) + 56,457 negative examples (no escalation = MLP routed right) = ~67K labels in the canonical 174K snapshot. Live episodic.db is at 8K rows per [P4.1 Phase A audit](#phase-4-trinity-derived-methodology-audits-new-2026-04-26) — would need rebuild from episodic memory before training.

**Decision gates**:
- The scoping subtasks (P6.1, P6.2, P6.3) each end in a binary decision before the next escalates.
- DO NOT branch a separate handoff. All work stays under this index.
- DO NOT start P6.4+ recursive port without P6.2 demonstrating that a *simple* MLP verifier moves the needle. Occam's razor gates the recursion lever.

#### P6.1 — Verifier-vs-DAR-vs-threshold audit (analytical, no code, 1 session)

The current routing pipeline already has TWO mechanisms that overlap with a "verifier":
1. **Per-class confidence threshold** (P1.4) — discards low-confidence top-class predictions and falls through to KNN.
2. **DAR-2 contrastive Q-score** (per [decision-aware-routing.md](decision-aware-routing.md) DAR-2 ✅ 2026-04-15) — sharpens Q-value margins so the routing decision is robust.

Question: does adding a separate verifier head *materially* differ from these two, or is it equivalent at scale?

- [ ] **P6.1.1** Read `decision-aware-routing.md` DAR-1 through DAR-5; identify where DAR's loss function differs from a calibrated "P(action correct)" prediction. Specifically: does DAR's contrastive adjustment converge to the same gradient signal as a logistic-regression verifier on the correctness label? If yes, the verifier may be redundant.
- [ ] **P6.1.2** Inspect the per-class threshold calibration logic (P1.4) in `routing_classifier.py` or its training script. Is the threshold derived from a held-out *correctness* signal, or just from softmax precision/recall on the class label? If correctness signal, the threshold IS already a degenerate verifier (single scalar per class).
- [ ] **P6.1.3** Write a 1-paragraph audit answering: "What does a separate verifier head *give us* that the per-class threshold + DAR-2 contrastive sharpening don't?"
  - If answer is "nothing material" → mark P6 closed, archive Hypothesis C, end of Phase 6.
  - If answer is "calibrated P(correct) at decision time, conditioned on both embedding AND proposed action, with a single decision threshold rather than 5 per-class thresholds" → proceed to P6.2.
- [x] **P6.1.4** Append the audit to this Phase. ~1 session, no code, deliverable is a paragraph and a binary go/no-go. **DONE 2026-05-21 — see "P6.1 Audit Outcome" below.**

##### P6.1 Audit Outcome (2026-05-21)

**Verdict**: a separate verifier head IS materially distinct from the per-class threshold + DAR-2 contrastive sharpening. **Phase 6 escalates to P6.2 (MLP verifier baseline).**

**Three-way comparison of the candidate gating mechanisms**:

| Axis | Per-class threshold (P1.4) | DAR-2 contrastive Q-adjust | Proposed verifier head |
|---|---|---|---|
| **Where in pipeline** | Decision-time, in `routing_classifier.py:155-159` `predict_action()` | Post-outcome, in `q_scorer.py:492-568` `_compute_contrastive_adjustment()` | Decision-time, between MLP and FAISS fallback |
| **Input signal** | `best_prob` (scalar softmax peak) + `best_idx` (1 of N) | `selected_q`, `alt_q_values[]` (sampled from top-10 similar memories) | `(1024-d embedding) ⊕ (5-d action one-hot)` — full joint input |
| **Training objective** | Class-precision: "given top-1 = class X, was the class label X correct?" | Q-ranking: "is selected Q above (success) / below (failure) competitors' Q-values?" | **Correctness**: "given embedding and action, P(no escalation downstream)" |
| **Per-instance adaptivity** | Zero — a single per-class scalar fixed at calibration time | Zero at decision time (DAR-2 is a *training* signal modifier, not a gate) | Full — learns embedding-conditional accept/reject patterns |
| **What it can represent** | `accept(x, a) = (p_softmax(a\|x) > τ_a)` — a 1-D calibrator over softmax per class | Q-value ranking sharpness in episodic memory (accumulates over time) | Arbitrary `P_correct = f(embedding, action)` — strictly more expressive than the threshold |
| **What it cannot represent** | Embedding-conditional risk: "cluster Y + frontdoor fails even at high softmax" | Decision-time gating (operates only on accumulated Q-values, not on this request) | (none of the above are limitations of the verifier) |
| **Failure-mode locus** | Fixed once at calibration; per-request adaptivity = 0 beyond per-class lookup | Distribution drift in Q-values over time; no per-decision protection | Retraining cycle (same as classifier); susceptible to escalation-label bias |
| **Latency** | ~µs (single comparison) | N/A at decision time (post-outcome path) | <1ms (single 70K-param MLP forward pass) |

**Material distinction (the load-bearing finding)**:

The per-class threshold is the **degenerate case** of the verifier — it is the family of verifier functions `f(p_softmax(a|x), a)` collapsed to a step function with a single per-class breakpoint. The general verifier function `P_correct(x, a)` is strictly more expressive because:
- The threshold ignores the embedding `x` entirely except through its compression into a softmax peak.
- The verifier observes the full 1024-d embedding AND the action jointly. It can learn patterns of the form "embedding-cluster Y + action frontdoor fails even when softmax is confident" — patterns the threshold provably cannot represent (the threshold sees only a scalar peak; it cannot tell embedding-cluster Y apart from cluster Z if both produce the same softmax peak).

The classifier itself emits a distribution over actions ("which action?") and uses the softmax peak as a proxy for confidence. The verifier evaluates a specific action ("is this action right?"). For an N=5 multi-class problem these are genuinely different questions — the classifier's softmax cannot encode action-specific accept/reject patterns the way a (x, a) → P(correct) head can.

DAR-2 is **not** a decision-time gate — it modifies the reward signal feeding the Q-value TD update over time. It improves the *learned ranking quality* of stored Q-values but does not look at any individual incoming request. A verifier and DAR-2 are orthogonal: DAR-2 improves the population of Q-values episodic memory holds; the verifier gates whether any given request should trust the current MLP prediction.

**Caveats and risks to address in P6.2**:

1. **Embedding-saturation risk**: the existing classifier achieves 92% val accuracy on the 174K-label class objective. If the 8% miss rate is Bayes-irreducible (i.e., the BGE embedding alone does not contain enough signal to separate the remaining hard cases), then a verifier head reading the same embedding cannot recover them either. **P6.2.5 gate explicitly requires ROC-AUC ≥ 0.75 on the held-out CORRECTNESS split — not the class split — to catch this.**
2. **Escalation-label bias**: escalation memories (the 10.5K positives) only fire when the system actually escalated. Cases where the MLP was wrong but the user did not escalate are missing from the training set. The verifier's correctness label is therefore a noisy proxy correlated with the existing escalation policy. **P6.2.2 must operationalize "correctness" as either (a) explicit downstream-quality-threshold gates, or (b) survivor-bias-aware reweighting of the negative class, not just "no escalation observed".**
3. **MC-dropout overlap**: if P6.4 demonstrates that multi-pass dropout on the existing classifier already produces a calibrated correctness predictor (variance-of-top-class-prob correlated with correctness ≥ 0.05 AUC over softmax magnitude), the verifier's information-theoretic edge may shrink to nothing in practice. **Let P6.4 run in parallel with P6.2 design — whichever produces a calibrated correctness signal at lowest cost wins.**
4. **DAR-2 interaction is benign, not redundant**: DAR-2 sharpens the *training* signal feeding the classifier (via Q-value TD updates); the verifier gates *inference-time* decisions. They compose without conflict — DAR-2 makes the classifier more confident on the right cases; the verifier catches cases where the classifier is confidently wrong. This is orthogonal capability, not duplicate.

**Decision**: proceed to P6.2 (MLP verifier baseline). The verifier framing introduces a primitive — a per-decision, embedding-conditional, action-specific correctness gate — that none of the existing mechanisms can express. The Occam-gated P6.2.5 acceptance criteria will determine whether the *expressive* superiority translates into an *empirical* win on our data. If P6.2 fails its gate, the verifier is closed without recursion-related sunk cost.



#### P6.2 — Baseline MLP verifier (the Occam gate, ~1-2 sessions)

If P6.1 escalates: build the *simplest possible* verifier head and test it before considering anything recursive.

- [x] **P6.2.1** Add `VerifierHead` class to `orchestration/repl_memory/routing_classifier.py` (or a new sibling file `verifier_head.py`). Architecture: 1029-d input (1024 BGE ⊕ 5 one-hot action) → Dense(64, ReLU) → Dense(32, ReLU) → Dense(1, Sigmoid). ~70K params, numpy-only, same style as `RoutingClassifier`. Output: P(action is correct) ∈ [0, 1]. **DONE 2026-05-21** — `verifier_head.py` (sibling file). Architecture: 1031-d features (matches classifier `input_dim`) ⊕ 8-d action one-hot = 1039-d input → 64 → 32 → 1 sigmoid. Param count: 68,673.
- [x] **P6.2.2** Add `extract_verifier_training_data.py` under `scripts/graph_router/`. Joins episodic memories with escalation events to produce `(embedding, action, correct)` triples. Correctness label: `correct=1` if no escalation downstream, `correct=0` if escalation event followed within the session. Stratify train/val/test 80/10/10. **DONE 2026-05-21 — with revised label scheme**. The cached reembedded.npz contained no routable rows under the `coder_escalation` action (per P1.4 note — escalation events lack initial-routing embeddings). **Pivoted from escalation-based to Q-value-threshold-based correctness**: `correct = (q_weight > 0.5)`. Rationale: Q-values are the TD-updated outcome of all task results that used a given routing memory — a per-memory aggregate success signal. Result: 134,905 positive (85.6%) + 22,615 negative (14.4%). Inverse-frequency sample weighting (pos=0.58, neg=3.48). **Caveat recorded**: Q-values are themselves shaped by the routing policy (DAR-2 contrastive sharpening, TD-update dynamics) — the verifier learns "good routes per current policy", not "good routes in absolute terms". P6.2 results below are interpreted with this caveat in mind.
- [x] **P6.2.3** Add `train_verifier_head.py`. Binary cross-entropy loss with class-weighting (negatives outnumber positives ~6:1). <1 min training on CPU per P1.6 retrain timing. Save weights to `orchestration/repl_memory/verifier_head_weights.npz`. **DONE 2026-05-21** — 100 epochs, lr=0.05 cosine decay, batch=256, patience=15, BCE + inverse-frequency weighting. Training wall-clock: 45 seconds on CPU (~157K samples, 80/20 split). Best val loss 0.0092 at epoch 81 (no early stopping triggered). Final val accuracy 99.79%.
- [x] **P6.2.4** Evaluate calibration via reliability diagram (binned P(correct) vs empirical correctness rate) and ROC-AUC on val set. Compute Brier score. Compare against (a) the per-class threshold baseline and (b) the softmax-of-top-class baseline. **DONE 2026-05-21 — with critical disaggregation. See "P6.2 Eval Outcome" below.** Headline numbers blow past every gate, but a per-action breakdown reveals the result is dominated by class-conditional triviality on three of four classes; the genuine signal is on action[0] (frontdoor) and IS real, just smaller than the headline implies.
- [x] **P6.2.5** **Decision gate**: if Brier improves by ≥ 0.02 AND ROC-AUC ≥ 0.75 AND calibration error (ECE) ≤ 0.05 → verifier survives Occam. Wire as a fallback gate in `retriever.py` behind a NEW feature flag `ORCHESTRATOR_VERIFIER_GATE` (default OFF; orthogonal to existing classifier flag). Else: record null result, archive Hypothesis C, end of Phase 6. **GATES PASS 2026-05-21 — but wiring DEFERRED pending user review of the disaggregation below.** Headline ΔBrier +0.122 / AUC 0.9999 / ECE 0.0042 all exceed their thresholds, but the genuine within-action signal is more modest. Recommend the user review the disaggregation before authorizing the production wire-in.

##### P6.2 Eval Outcome (2026-05-21)

**Verdict (headline)**: all three P6.2.5 gates PASS — ΔBrier vs the stronger baseline (softmax_max) is **+0.1220** (≥ +0.02 gate), ROC-AUC is **0.9999** (≥ 0.75 gate), ECE is **0.0042** (≤ 0.05 gate).

**Verdict (honest, after disaggregation)**: the headline is dominated by class-conditional triviality — three of four active classes have near-deterministic correctness rates that any predictor with action-one-hot access will trivially memorize. The **genuine demonstration of the verifier's information-theoretic edge** is on action[0] = frontdoor, the only class with substantial within-action variance.

**Aggregate metrics** (val set, n=31,504):

| Predictor | Brier ↓ | ROC-AUC ↑ | ECE ↓ | Notes |
|---|---|---|---|---|
| **verifier (P6.2)** | **0.0025** | **0.9999** | **0.0042** | 68,673 params, joint (features, action) input |
| softmax_max (clf top-1 prob) | 0.1245 | 0.7557 | 0.1082 | the per-class-threshold gate's input |
| softmax_taken (clf p(taken_action\|x)) | 0.1319 | 0.7669 | 0.1246 | softmax mass on the *taken* action |
| constant base rate (0.856) | 0.1211 | — | — | uninformative reference |
| **action-only marginal** | **0.0787** | **0.8494** | 0.0018 | predict per-action mean train correctness |

**Per-action disaggregation** (correctness label = `q_weight > 0.5`):

| Action | n_val | Per-action correctness rate (train) | Verifier Brier | Marginal Brier | Verifier intra-action AUC |
|---|---|---|---|---|---|
| 0 (frontdoor) | 14,459 | **0.7818** | **0.0055** | **0.1686** | **0.9997** |
| 1 (architect_general) | 8,406 | 1.0000 | 0.0000 | 0.0000 | — (no variance) |
| 2 (architect_coding) | 7,342 | 0.9936 | 0.0000 | 0.0057 | 1.0000 |
| 4 (worker_explore) | 1,297 | 0.0000 | 0.0000 | 0.0000 | — (no variance) |

**Where the signal lives**:

- **Action[0] (frontdoor)** is the only class where the correctness label is non-trivially distributed (78.2% positive, 21.8% negative). The verifier achieves **Brier 0.0055** vs the marginal-action baseline's **Brier 0.1686** — a **30× improvement**. Intra-action ROC-AUC of **0.9997** demonstrates that the verifier learns embedding-conditional discrimination of which frontdoor decisions succeed vs fail. **This IS the demonstration of the joint-conditioning edge the P6.1 audit predicted.**
- **Action[1] (architect_general)**: 100% positive in training data — verifier and marginal both trivially correct. No signal to learn.
- **Action[2] (architect_coding)**: 99.4% positive — near-trivial. The verifier reaches Brier 0.0000 by leveraging the action one-hot.
- **Action[4] (worker_explore)**: 0% positive — trivially separable from the rest. Both verifier and marginal achieve Brier 0.0000.

The aggregate 0.9999 AUC is not "the verifier learned to predict routing correctness with near-perfection across the board" — it is "the verifier learned the marginal per-action correctness rates (which a 4-bucket lookup table could also do) AND on top of that learned to discriminate within action[0]". The 30× Brier improvement on action[0] is the real win, masked by the easy-classes contribution to the aggregate.

**Caveats** (load-bearing for any production wire-in):

1. **Q-value correctness label is policy-biased.** Architect_general's 100% correctness rate is almost certainly not a real-world success rate — it reflects the TD-update dynamics under the current routing policy + DAR-2 contrastive sharpening. The verifier is learning "good routes per current policy", not "good routes in absolute terms". This bias is acceptable for a *gate that defends the current policy from itself* (i.e., predicts when the classifier will be wrong relative to the policy's own success criterion), but does NOT generalize to a verifier of new routes.
2. **Action[4] (worker_explore) being 0% correct is suspect.** Per the Phase 1 normalization note, worker_explore data is 88% `task_type=chat` with low Q-values because chat tasks often hit the legacy frontdoor-by-default logic. The verifier learns to predict "worker_explore → incorrect", which is a true statement about the training distribution but may be wrong as the worker_explore role evolves.
3. **Aggregate ranking AUC is misleading** because most of the val ranking is between deterministic classes (action[1]/[2] positives vs action[4] negatives) — i.e., the verifier's "discrimination" is largely the marginal action distribution, not embedding-conditional discrimination. Always report the per-action disaggregation, never just the aggregate.
4. **No counterfactual data.** The training set contains `(embedding, taken_action, correct)` triples — there are no `(embedding, untaken_action, ?)` examples. At inference, if the classifier proposes a counterfactual action (one not typically taken for this embedding), the verifier extrapolates without ground truth. This is the standard offline-policy limitation; needs an A/B in shadow mode to detect drift.
5. **No held-out distribution test.** Train/val is i.i.d. (random split). The verifier's robustness on a different task distribution (different time period, different user population, different model versions in the pool) is unmeasured.

**Recommendation**: do NOT wire `ORCHESTRATOR_VERIFIER_GATE` to production retriever yet. The headline numbers pass the gate but the real signal is narrow (essentially "improved frontdoor confidence calibration"). Two concrete next steps before wiring:

- **NEXT-A**: train and evaluate a **policy-debiased** correctness label — e.g., `correct = (final_task_quality_score > threshold)` joined per-session from a quality oracle independent of the Q-update loop. This addresses caveats 1 and 2. Estimated: 1-2 sessions of data-pipeline work to join task_outcome events with routing decisions.
- **NEXT-B**: write a **shadow-mode evaluation harness** that runs the verifier in parallel with the current per-class threshold for ≥ 1 week, logging both decisions and downstream outcomes, without changing routing behavior. This addresses caveats 4 and 5. Estimated: 1 session of harness code, then wall-clock waiting.

**Artifacts** (preserved for re-runs):
- `orchestration/repl_memory/verifier_head.py` — VerifierHead class (created 2026-05-21)
- `scripts/graph_router/extract_verifier_training_data.py` — data extraction (created 2026-05-21)
- `scripts/graph_router/train_verifier_head.py` — train + eval harness (created 2026-05-21)
- `/tmp/p6_2_verifier_training_data.npz` — verifier training NPZ (regenerable)
- `/tmp/verifier_head_weights.npz` — trained weights (68,673 params; NOT in production directory yet)

##### P6.2 NEXT-A Result (2026-05-21) — counterfactual probe is the real story

**Setup**: rebuilt training data using `outcome` field from `episodic.db.backup-20260415` instead of `q_weights > 0.5` to address the policy-bias caveat (#1). Join key: memory_id from reembedded.npz ⋂ backup db. Result: 153,847 rows (97.7% of reembedded), label distribution 86.1% positive / 13.9% negative.

**Finding 1 — Q-value label and outcome label are interchangeable in this data**:

```
Action                  n        outcome_rate   Q-rate
[0] frontdoor          70,996   0.784          0.784
[1] architect_general  40,312   1.000          1.000
[2] architect_coding   36,686   0.994          0.994
[4] worker_explore      5,853   0.000          0.000
```

Q-values in this dataset were initialized from outcome and `update_count=0` everywhere — TD updates never moved Q substantially. So the "policy bias on Q-values" caveat (#1) was a false alarm on THIS data; the Q-label IS the outcome label by construction. The retrained verifier produces near-identical metrics: Brier 0.0021 (was 0.0025), AUC 0.9999 (same), ECE 0.0036 (was 0.0042).

**Finding 2 — counterfactual probe falsifies the "joint conditioning" interpretation**:

I queried the trained verifier with the SAME 14,239 frontdoor val embeddings, paired with each possible action one-hot, to see whether the verifier discriminates by `(embedding, action)` jointly or just by action.

| Action paired with frontdoor embedding | Mean P_correct | Median | % endorsed (>0.5) |
|---|---|---|---|
| 0 (frontdoor — taken in training) | 0.7806 | 0.9997 | 78.7% |
| 1 (architect_general — counterfactual) | **1.0000** | **1.0000** | **100.0%** |
| 2 (architect_coding — counterfactual) | **0.9930** | **1.0000** | **100.0%** |
| 4 (worker_explore — counterfactual) | **0.0000** | **0.0000** | **0.0%** |

The verifier is essentially `P_correct = per_action_marginal(action) + intra_action_refinement(embedding | action=frontdoor)`. For actions 1, 2, 4 the embedding contributes nothing — the verifier outputs the marginal action rate regardless of what's in the embedding. This is **architecturally** what the verifier should be able to do (the input includes the joint), but the training data didn't supply enough action-conditional variance to teach it. Intra-action AUC matrix:

| Action | n_val | Intra-action AUC | Verifier Brier | Softmax_max Brier | Status |
|---|---|---|---|---|---|
| 0 frontdoor | 14,239 | **0.9997** | **0.0046** | 0.1942 | genuine discrimination (~42× Brier improvement) |
| 1 architect_general | ~8,000 | — | 0.0000 | 0.0000 | no within-class variance — nothing to learn |
| 2 architect_coding | ~7,000 | — | 0.0000 | 0.0057 | near-trivial; verifier returns 1.0 |
| 4 worker_explore | ~1,300 | — | 0.0000 | 0.0000 | no within-class variance — verifier returns 0.0 |

The verifier IS effective on frontdoor specifically — 0.7321 → 0.9997 ROC-AUC, a substantial intra-action win — and that win is real, embedding-conditional discrimination. It's just NOT what the headline 0.9999 aggregate AUC suggested.

**Finding 3 — production wire-in is unsafe under current training data**:

- For frontdoor routes: verifier ADDS genuine signal (good).
- For architect_general / architect_coding routes: verifier RUBBER-STAMPS at ~100% regardless of embedding (effectively erases the existing softmax-magnitude gate's discrimination on these classes — REGRESSION).
- For worker_explore routes: verifier REJECTS at 0% regardless of embedding (would prevent any worker_explore deployment — REGRESSION).

The training data has no architect_general failure examples and no worker_explore success examples, so the verifier cannot learn what those would look like. Wiring this verifier to production would systematically lock in the seeded biases for those classes.

**Decision update**: **Do NOT wire the multi-action verifier.** P6.2.5's aggregate gates pass but the per-action analysis shows the deployment would regress 3 of 4 classes. The methodology is validated (joint conditioning DOES learn within frontdoor) but the data does not yet support a production multi-action verifier.

**Two paths forward** (replace original NEXT-A scope which is now resolved):

- **NEXT-A2 — frontdoor-specialist verifier**: train a binary success-predictor on frontdoor decisions only (70K training samples, 22% failures). Avoids the label-leakage trap by construction (no other classes in scope). Gates on Brier improvement over softmax magnitude *restricted to frontdoor inputs*. ~1 session of code. Useful if our top operational pain point is "the MLP is over-confident in frontdoor on certain inputs."
- **NEXT-A3 — defer until data infrastructure refresh**: see "Operational Findings" section below. The reembedded.npz is a frozen 2026-04-15 snapshot; the live episodic.db has 52K newer routing memories with no cached embeddings (FAISS reset). A proper multi-action verifier needs the new data + balanced failure coverage across classes. Costs one bundled BGE-inference run.

##### Operational Findings (2026-05-21) — surfaced during NEXT-A work, NOT verifier-blocking

These findings are about data infrastructure, not the verifier itself, but should be considered before autopilot restart:

1. **reembedded.npz is 100% disjoint from live db**. The 157,520 IDs in `reembedded.npz` have zero overlap with the 52,667 routing memories currently in `episodic.db`. The live db has been growing with new memories since 2026-04-16; the cached embeddings are a frozen 2026-04-15 snapshot. Recoverable only via the backup at `episodic.db.backup-20260415` (153,847 of 157,520 IDs joinable, used for NEXT-A debiased label).
2. **Live db routing memories have minimal FAISS embeddings**. `embeddings.faiss` is 385 KB (reset); `.bak` is 32 MB (Feb 24). 52K routing memories were written without corresponding embeddings being computed or indexed.
3. **Implication for autopilot restart**: the classifier MLP fast-path is unaffected (stateless feed-forward). The KNN fallback path (FAISS similarity over episodic memories) cannot function as designed because there are essentially no current embeddings to match against. If the per-class threshold gates fail confidence for any request, the fallback returns trivial neighbors.
4. **Implication for any retrained verifier or classifier**: training new versions on the current data state would either (a) use the frozen 2026-04-15 distribution again (stale), or (b) require re-embedding the live db's 52K rows (BGE inference run, user authorization required per `feedback_no_concurrent_inference`).
5. **No log scrubbing needed**. Episodic logs reflect real task outcomes. The data state is incomplete (missing embeddings), not corrupt. Q-saturation is a property of the initial-Q-from-reward initialization, not TD-dynamics contamination.

**Recommendation to user before autopilot restart**:
- Either accept the current state and restart autopilot (classifier MLP fast-path still works; KNN fallback degrades silently).
- Or authorize ONE bundled BGE-inference session that:
  - Re-embeds the live db's 52K routing memories into a fresh FAISS + new reembedded.npz.
  - Rebuilds the verifier training extract using fresh outcomes for the new memories.
  - Enables P4.1 Phase B (audited but deferred per `feedback_no_concurrent_inference`) at the same time.
  - Total wall-clock estimate: ~5–15 min per the P4.1 estimate.

##### P6.2 NEXT-B Status (2026-05-21) — deferred pending NEXT-A2/A3 decision

NEXT-B (shadow-mode eval harness) was scoped to run a verifier alongside the existing per-class threshold for ≥ 1 week. **Deferred** because:
- The current multi-action verifier would regress 3 of 4 classes if shadow-deployed (per Finding 3 above) — shadow-mode would just confirm what the counterfactual probe already shows.
- The right next step depends on whether the user authorizes NEXT-A2 (frontdoor-specialist verifier — cheap, no inference) or NEXT-A3 (data infrastructure refresh — bundled BGE-inference run).

If NEXT-A2 is chosen, NEXT-B's shadow harness can be retargeted to evaluate the frontdoor-specialist on frontdoor-routed requests specifically. If NEXT-A3 is chosen, NEXT-B becomes a routine shadow harness on the retrained multi-action verifier with proper data coverage.

**Additional artifacts** (debiased pipeline):
- `scripts/graph_router/extract_verifier_training_data_debiased.py` — outcome-based extractor (created 2026-05-21)
- `/tmp/p2_2_verifier_training_data_debiased.npz` — debiased training NPZ
- `/tmp/verifier_head_weights_debiased.npz` — retrained weights (substantively identical to original)

##### A3 Implementation (2026-05-21) — orphan-embedding preflight + repair tool

**User-authorized 2026-05-21**: implement an episodic-store health preflight that detects and (on flag) repairs the orphan-FAISS state surfaced during NEXT-A work. Goal: make autopilot/orchestrator restart self-healing wrt FAISS gaps.

**Implementation**:

1. **New: `scripts/maintenance/repair_episodic_embeddings.py`** — standalone diagnostic + repair tool.
   - `--diagnose-only`: read-only. Reports `n_db_routing`, `n_faiss_vectors`, `n_reembedded`, `overlap_live`, `faiss_coverage`. Exit 0 if healthy, 1 if orphaned.
   - `--repair`: invokes `scripts/graph_router/reembed_episodic_store.py` (existing 8-parallel-BGE primitive) to produce a fresh `reembedded.npz`, then rebuilds `embeddings.faiss` + `id_map.npy` atomically with backups (writes to `.new`, renames; originals saved as `.pre-repair-<timestamp>`). Re-validates by re-opening FAISS and checking ntotal.
   - Threshold: `faiss_coverage < 50%` OR `overlap_live < 50%` → ORPHANED. Repair guarded by `--min-orphans` (default 1000) to avoid touching small drift.

2. **Wired into `scripts/server/orchestrator_stack.py`** at step `[0.7] Episodic embedding health check`, between model-path validation and server-launch sequence:
   - Diagnostic always runs (read-only, ~1 sec on cold cache).
   - If unhealthy AND `--repair-embeddings` flag passed: runs full repair before launch (~5-15 min wall-clock for the current 52K-orphan state).
   - If unhealthy AND no flag: prints warning + manual-repair instructions; does NOT block startup.
   - Import is defensive (`ImportError` → skip-with-log; `Exception` → log-and-continue) to avoid breaking older deployments.
   - New CLI arg: `--repair-embeddings`.

**Verified on current state (2026-05-21 12:23)**:

```
========================================================================
Episodic Embedding Health Report
========================================================================
  Routing memories in db:          53,087
  Vectors in FAISS index:              94
  IDs in reembedded.npz:          157,520
  FAISS coverage:                    0.2%  (threshold ≥ 50%)
  reembedded ⋂ live db:              0.0%  (threshold ≥ 50%)
  Orphan count (db − FAISS):       52,993
  Status:                      ORPHANED — repair recommended
========================================================================
```

Diagnostic + import path both verified to work as the orchestrator_stack `[0.7]` hook will invoke them. `--repair-embeddings` flag is registered and visible in `start --help`.

**Operational procedure for first restart**:
```
python3 scripts/server/orchestrator_stack.py start --repair-embeddings
```
This will trigger the bulk repair on first restart, ~5-15 min, then proceed with normal launch. After that, the orphan state is gone — subsequent restarts diagnose-clean in ~1 sec and proceed immediately.

**Artifacts**:
- `scripts/maintenance/repair_episodic_embeddings.py` (created 2026-05-21, ~280 LoC)
- `scripts/server/orchestrator_stack.py` (modified 2026-05-21, +60 LoC at step [0.7] + 1 CLI arg)

##### A2 Result (2026-05-21) — frontdoor-specialist verifier PASSES gates

**Setup**: filtered the debiased verifier training data to frontdoor (action=0) only. Stripped the 8-d action one-hot from inputs (since there's only one action, the one-hot is constant and meaningless). Trained `VerifierHead(feature_dim=1031, n_actions=0)` — 68,161 params, 64×32 hidden — on 70,996 frontdoor samples with 22% failure rate. BCE loss + inverse-frequency class weighting, 100 epochs cosine LR decay.

**Intra-action val metrics** (action[0] only, n=14,199, 78.8% positive base rate):

| Predictor | Brier ↓ | ROC-AUC ↑ | ECE ↓ | Acc@0.5 |
|---|---|---|---|---|
| **frontdoor verifier (A2)** | **0.0043** | **0.9997** | **0.0066** | **0.9960** |
| softmax max prob (clf top-1) | 0.1941 | 0.7348 | 0.1851 | — |
| softmax p(frontdoor\|x) | 0.2034 | 0.7378 | 0.2056 | — |
| constant base rate (0.788) | 0.1670 | — | — | — |

**A2 decision gates** (same thresholds as P6.2.5):

| Gate | Verifier | Threshold | Status |
|---|---|---|---|
| ΔBrier vs best baseline (softmax_max) | **+0.1898** | ≥ +0.02 | **PASS** (9.5× margin) |
| ROC-AUC | **0.9997** | ≥ 0.75 | **PASS** |
| ECE | **0.0066** | ≤ 0.05 | **PASS** |

**This is the genuine joint-conditioning win** the P6.1 audit predicted, isolated from the action-marginal label-leakage trap the multi-action verifier fell into. The frontdoor verifier:
- Cannot memorize per-action marginals (only one action in scope).
- Achieves a ~45× Brier improvement vs softmax_max baseline on frontdoor val rows.
- Reaches 99.6% accuracy on a 22%-failure-rate task — the classifier+softmax-threshold alone gets the trivial 78.8% from always predicting positive.
- Calibration is excellent: reliability bins show |gap| ≤ 0.005 for the two dominant bins ([0,0.1] and [0.9,1.0]) which together cover 96.8% of val samples.

**Caveats specific to A2** (lighter than multi-action ones):
1. **Outcome label is still from backup-20260415** — frozen snapshot of the routing policy as of that date. Generalization to current live-db distribution is unmeasured. Mitigated once A3 repair runs: a re-extraction on the post-repair `reembedded.npz` will give a current-distribution training set.
2. **No counterfactual generalization issue** here (the action is fixed at frontdoor, so there are no untaken-action examples to worry about).
3. **Frontdoor-only coverage**: this verifier ONLY gates frontdoor routes. For other classes, no gate. The existing per-class threshold mechanism handles them. Acceptable.

**Deployment shape** (NOT YET WIRED — same Occam discipline as multi-action verifier):

```
Request ─► BGE embed ─► RoutingClassifier MLP → top class + softmax
                                  │
            top class == frontdoor?
                    │   no  ─► per-class threshold (unchanged)
                    │   yes ─►
                                  │
              frontdoor verifier (A2)
                                  │
            P(success) ≥ τ_fd?
                    │   yes ─► route via frontdoor
                    │   no  ─► fall through to KNN  ← REQUIRES A3 HEALTHY
```

**Phase 6 status synthesis**:

| Step | Status | Decision-relevant finding |
|---|---|---|
| P6.1 audit | ✅ DONE | Verifier framing materially differs from threshold + DAR-2; proceed |
| P6.4 MC-dropout proxy | ✅ DONE (null) | No falsification of verifier value; classifier trained w/o dropout |
| P6.2 multi-action verifier | ✅ DONE (gate passes but invalid) | Counterfactual probe revealed 3-of-4 classes are action-marginal lookups — would regress production if wired |
| P6.2 NEXT-A debiased label | ✅ DONE (no-op) | Q-label ≡ outcome-label in this snapshot; bias caveat doesn't apply |
| **A3 orphan-embedding preflight + repair** | ✅ DONE | Detects ORPHANED state; `--repair-embeddings` flag triggers bulk fix; safe for first autopilot restart |
| **A2 frontdoor-specialist verifier** | ✅ DONE (PASS) | All gates pass with 9.5× Brier margin; ready to wire as frontdoor-only gate AFTER A3 runs |
| Wire `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE` flag | DEFERRED | Pending: (a) A3 repair runs on first restart, (b) shadow-mode eval of A2 on fresh post-repair data |

**Recommended sequencing**:

1. **First autopilot restart** with `--repair-embeddings`: rebuilds FAISS, restores KNN fallback. ~5-15 min.
2. **Re-extract debiased training data** from the fresh reembedded.npz (no inference, just re-join). Confirms A2 generalization holds on current distribution.
3. **Retrain A2 frontdoor verifier** on the fresh data. If gates still pass, wire the gate behind `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE` (default OFF). If regression, A2 is over-fit to the April snapshot and we close out Phase 6.

**Artifacts**:
- `scripts/graph_router/train_frontdoor_verifier.py` (created 2026-05-21)
- `/tmp/frontdoor_verifier_weights.npz` — 68,161 params, intra-action val AUC 0.9997

##### Open Action — restart authorization

User authorization required for the first `orchestrator_stack.py start --repair-embeddings` run (BGE inference, ~5-15 min). This is a one-time bulk operation; subsequent restarts will diagnose-clean in ~1 sec.

##### A3/A2 Production Wiring (2026-05-21) — done

User authorized 2026-05-21 and the following four-step sequence was executed end-to-end:

**Step A — RoutingClassifier loading wired into production routing path**

Pre-existing gap discovered during A2 wiring: the P1.5 task ("enable `ORCHESTRATOR_ROUTING_CLASSIFIER=1`") had flipped the feature flag but the actual *loading code* was never written. `HybridRouter` accepted a `routing_classifier` parameter but nothing in `src/api/services/memrl.py` ever called `RoutingClassifier.load(...)` and passed it in. **Every production request was taking the full KNN path** since 2026-04-15.

Fix landed at `src/api/services/memrl.py:471` (before the `HybridRouter` construction). The new block:
- Checks `features().routing_classifier` (existing flag, default OFF)
- Loads weights from `ROUTING_CLASSIFIER_WEIGHTS` env override or `DEFAULT_WEIGHTS_PATH` (which points at `orchestration/repl_memory/routing_classifier_weights.npz`)
- Logs param count, action count, and weights path on success
- Gracefully degrades if weights missing (logs warning, fast-path stays disabled)
- Threads the loaded classifier into `HybridRouter(routing_classifier=…)`

**Step B — Classifier retrained on the post-stack-change distribution**

The April 2026-04-15 weights were trained on a distribution where `architect_general` was 100% successful. The 2026-05-09 stack consolidation (`project_stack_consolidation_2026_05`) reshuffled the role pool and architect_general's empirical success rate dropped to 9.1% in post-change data. The April-weights classifier was therefore mis-routing aggressively into architect_general failures.

Retrained via `train_routing_classifier.py` on the post-repair `/tmp/p6_4_training_data_fresh.npz` (40,956 samples):

| Metric | April 2026-04-15 | Fresh 2026-05-21 |
|---|---|---|
| Train accuracy | 92.0% | **98.7%** |
| Val accuracy | 92.0% | **98.7%** |
| Best val loss | 0.099 | **0.017** |
| Per-class val acc — frontdoor | 91.5% | **99.6%** |
| Per-class val acc — architect_general | 95.1% | 93.9% |
| Per-class val acc — architect_coding | 95.7% | 100.0% |
| Per-class threshold — frontdoor | 0.447 | 0.611 |
| Per-class threshold — architect_general | 0.362 | 0.604 |
| Per-class threshold — architect_coding | 0.560 | 0.379 |

Fresh weights staged to production path: `orchestration/repl_memory/routing_classifier_weights.npz` (522KB, 140,872 params). Next API restart picks them up via Step A's loading code.

**Coverage caveat**: fresh classifier still only trained on 3 classes (frontdoor, architect_general, architect_coding) because the normalizer-bug-driven 22.9% drop excluded `coder_escalation`, `worker_general`, `ingest_long_context` from the reembed. Normalizer fix landed (next bullet), but rebuilding the missing classes' embeddings requires another `--repair-embeddings` run.

**Step C — Frontdoor verifier gate wired in retriever.py + memrl.py**

`HybridRouter.__init__` now accepts `frontdoor_verifier` (default None) and a configurable `frontdoor_verifier_threshold` (default 0.5, env override `FRONTDOOR_VERIFIER_THRESHOLD`). The classifier fast-path in `route()` was extended:

```
classifier predicts top class
    ├── confidence < per-class threshold → fall through to KNN (unchanged)
    └── confidence ≥ threshold AND routing[0] == "frontdoor" AND verifier loaded
            verifier.predict(features, action_idx=0) → P_success
                ├── P_success ≥ threshold OR shadow mode → return via fast-path (with verifier metadata)
                └── P_success <  threshold AND enforcing → fall through to KNN
```

For non-frontdoor routes the verifier is bypassed (no signal to add). Loading wired in `memrl.py` behind `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE` (default OFF) — same defensive style as the classifier. Two related env vars:
- `FRONTDOOR_VERIFIER_THRESHOLD` — default 0.5
- `FRONTDOOR_VERIFIER_SHADOW` — set to `1` for shadow mode (verifier runs and is logged via `last_decision_meta`, but never gates)

Fresh frontdoor-specialist weights staged at `orchestration/repl_memory/verifier_head_weights.npz` (253KB, 68,161 params).

**Step D — Shadow-mode capability**: implemented inline via `FRONTDOOR_VERIFIER_SHADOW=1` (no separate harness needed — `last_decision_meta` records `verifier_verdict`, `verifier_p_success`, `verifier_shadow` on every fast-path decision, so existing telemetry captures the shadow signal). A week of live shadow traffic can be analyzed against downstream outcomes to validate the gate before enforcing-mode rollout.

**Step normalizer-fix — bonus, also done 2026-05-21**

Added 7 missing entries to `ACTION_NORMALIZATION` (5 identity maps for canonical actions whose raw label IS the canonical name — `coder_escalation`, `ingest_long_context`, `worker_explore`, `worker_math`, `worker_vision` — plus `worker_general → worker_explore` and `coder → architect_coding` for renamed/legacy labels). Closes the 22.9% silent drop discovered during the first `--repair-embeddings` run. Next `--repair-embeddings` run will capture the missing 12K memories.

**Bug fixes landed during this work**

1. `repair_episodic_embeddings.py` — `np.save` auto-appends `.npy` to its path; my original code constructed `id_map.new` via `Path.with_suffix(".new")` and then renamed `id_map.new → id_map.npy`, but np.save had actually written to `id_map.new.npy`. The rename silently failed (`FileNotFoundError` swallowed by the orchestrator_stack wrapper), leaving FAISS rebuilt with 40,956 vectors but `id_map.npy` stuck at 94 entries. Fixed by explicit naming + post-write existence validation. Production `id_map.npy` was manually corrected (the bug version preserved as `id_map.npy.broken-1779368503`).
2. `VerifierHead.join/join_batch` — IndexError when `n_actions == 0` (single-action specialist case, e.g., frontdoor-only). `oh = np.zeros(0)` is empty, so `oh[action_idx] = 1` raises. Fixed to skip the one-hot construction entirely when `n_actions <= 0`.

##### Rollout sequence to enable in production

1. **Restart the API service.** It will:
   - Pick up the fresh classifier (98.7% val acc) automatically — `routing_classifier` flag is already on.
   - Pick up the fresh frontdoor verifier ONLY IF `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE=1` is set (default OFF).

2. **For initial verifier rollout (recommended)**: set `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE=1` + `FRONTDOOR_VERIFIER_SHADOW=1`. Verifier runs and decisions are logged via `last_decision_meta` but no fast-path is gated. ≥1 week of traffic accumulates shadow-mode signal.

3. **After shadow validation**: unset `FRONTDOOR_VERIFIER_SHADOW` (or set to `0`). Gate enforces — frontdoor routes with verifier P_success < 0.5 fall through to KNN instead of fast-path routing.

4. **Optional follow-up**: another `orchestrator_stack.py start --repair-embeddings` to ingest the previously-dropped 12K memories (coder_escalation, worker_general, ingest_long_context). Will trigger because the diagnostic will report ORPHANED for those 12K rows. Once they're in, classifier can be retrained for full 4+ class coverage.

##### Files touched (all in /mnt/raid0/llm/epyc-orchestrator/)

| File | Change |
|---|---|
| `src/api/services/memrl.py` | +60 LoC — RoutingClassifier + VerifierHead loading, wired into HybridRouter |
| `orchestration/repl_memory/retriever.py` | +50 LoC — verifier gate in fast-path, constructor args, env-var threshold + shadow flag |
| `orchestration/repl_memory/verifier_head.py` | bug fix — `join`/`join_batch` handle `n_actions=0` |
| `orchestration/repl_memory/routing_classifier_weights.npz` | NEW — fresh weights, 98.7% val acc on current distribution |
| `orchestration/repl_memory/verifier_head_weights.npz` | NEW — frontdoor-specialist verifier, intra-action AUC 0.9996 on fresh val |
| `scripts/graph_router/extract_training_data.py` | +7 entries to ACTION_NORMALIZATION — closes 22.9% drop |
| `scripts/maintenance/repair_episodic_embeddings.py` | bug fix — id_map.new.npy filename handling |
| `orchestration/repl_memory/sessions/id_map.npy` | repaired in-place (broken version preserved) |

**Files**:
- New: `orchestration/repl_memory/verifier_head.py`
- New: `scripts/graph_router/extract_verifier_training_data.py`
- New: `scripts/graph_router/train_verifier_head.py`
- Modified (conditional on P6.2.5 pass): `orchestration/repl_memory/retriever.py` — add verifier gate
- Modified (conditional): `src/features.py` — add `verifier_gate` flag

#### P6.3 — Recursive verifier (DEFERRED, conditional on P6.2 pass)

Only if P6.2 demonstrates that a simple MLP verifier moves the needle, escalate to a recursive verifier port informed by the HRM → TRM → GRAM lineage (intake-582/583/584).

- [ ] **P6.3.1** Port the SamsungSAILMontreal `TinyRecursiveModels` repo to a CPU-only training mode (it currently requires CUDA). Adapt the input adapter to consume 1024-d BGE embeddings + 5-d action one-hot, output a scalar correctness probability. Use the MLP-only variant (no self-attention) since context is fixed-size.
- [ ] **P6.3.2** Apply the **Augmented-HRM training recipe** from intake-585 — data augmentation (Gaussian noise on embeddings), input perturbation (random one-hot flips during training), bootstrapping (verifier-as-teacher for itself). The mechanistic-analysis finding is that THIS recipe, not the recursive architecture, is the load-bearing lever.
- [ ] **P6.3.3** A/B against P6.2 MLP verifier on the same train/val/test split. Decision gate: Brier improvement ≥ 0.01 over P6.2 baseline AND latency ≤ 5ms per decision (vs MLP verifier <1ms). If both gates pass, promote recursive verifier as default. Else: stick with MLP verifier, archive recursive verifier as null result.

**Open recursion questions to answer in P6.3.1**:
- Do we need GRAM-style stochastic trajectories (multi-sample at inference) or is deterministic recursion enough? Hypothesis: deterministic suffices for a binary verifier — multi-trajectory was load-bearing for GRAM only because its task (N-Queens multi-solution coverage) has multiple equally-correct outputs; verifier outputs are scalar-valued.
- How many recursive iterations? TRM uses 42 effective recursions/step × 16 supervision steps. For a verifier, that's wildly over-budgeted. Start with T=2, n=4 (8 effective recursions) and grow only if accuracy plateaus.

#### P6.4 — Cheap MC-dropout proxy for GRAM multi-trajectory (Hypothesis B, parallel to P6.1, ~1 session)

Separate cheap experiment that does NOT depend on P6.1/P6.2 outcome. The deep-dive's Hypothesis B argues that GRAM-style width-scaling (parallel trajectories at inference) is approximated for free by MC-dropout on the existing MLP.

- [x] **P6.4.1** Add an `mc_predict()` method to `RoutingClassifier` that runs N=10 forward passes with dropout p=0.1 applied to the two hidden layers. Returns (mean_probs, std_probs) over the 10 samples. **DONE 2026-05-21** — `routing_classifier.py:163-200` `mc_predict()` returns full `(n_samples, N, n_actions)` tensor so callers can derive any uncertainty signal.
- [x] **P6.4.2** Compute two derived signals: (a) **mean argmax** as the predicted class, (b) **variance of top-class probability** across passes as an uncertainty signal. **DONE 2026-05-21** — eval harness `scripts/graph_router/mc_dropout_eval.py` derives four candidates: max softmax (baseline), variance-of-top-class, entropy-of-mean-distribution, max-of-mean-distribution.
- [x] **P6.4.3** Evaluate on the existing val set: does using `mean argmax` change any decisions vs single-pass argmax? Does the variance signal correlate with correctness better than the softmax magnitude? Compute the same Brier / ROC-AUC / ECE metrics as P6.2. **DONE 2026-05-21** — see "P6.4 Eval Outcome" below.
- [x] **P6.4.4** **Decision gate**: if the MC-dropout uncertainty signal beats softmax-magnitude as a correctness predictor by ≥ 0.05 AUC, wire it as the fallback gate (cheaper than P6.2). If not, record null and rely on P6.2. **DONE 2026-05-21 — GATE FAILS**. ΔROC-AUC = −0.0136 to −0.0697 across the hyperparameter sweep. Hypothesis B archived; rely on P6.2 verifier head.

##### P6.4 Eval Outcome (2026-05-21)

**Verdict**: clean null. Test-time MC-dropout uncertainty is **worse** than the existing softmax magnitude as a correctness predictor across all three metrics (ROC-AUC, Brier, ECE) and across a hyperparameter sweep. Hypothesis B (Hypothesis B from `research/deep-dives/2026-05-21-recursive-reasoning-routing.md`) is empirically falsified.

**Setup**:
- Weights: `autopilot_checkpoints/20260416_134815/routing_classifier_weights.npz` (Phase 1 production weights, 140,872 params)
- Data: 157,520 samples × 1031-d features extracted from cached `sessions/reembedded.npz` via `extract_training_data.py`
- Val split: 31,504 samples (seed=42, val_split=0.2 — identical to training-time split)
- Deterministic val accuracy: **91.99%** (matches the handoff's stated 92% figure precisely — load and split reproducible)

**Hyperparameter sweep results** (correctness label = "deterministic argmax matched val label"):

| Config | Det val acc | MC mean val acc | Flip rate | Best MC predictor | Best MC AUC | Baseline AUC | ΔROC-AUC | Gate (≥ +0.05) |
|---|---|---|---|---|---|---|---|---|
| p=0.05, N=20 | 0.9199 | 0.9157 | 2.14% | mc_max_prob_mean | 0.9101 | **0.9237** | −0.0136 | FAIL |
| p=0.10, N=10 | 0.9199 | 0.9068 | 4.22% | mc_max_prob_mean | 0.8693 | **0.9237** | −0.0544 | FAIL |
| p=0.20, N=20 | 0.9199 | 0.9030 | 5.16% | mc_max_prob_mean | 0.8540 | **0.9237** | −0.0697 | FAIL |

Monotone pattern: lower dropout rate → MC predictors closer to (but still below) baseline; higher dropout → MC predictors substantially worse. **No setting beats softmax magnitude** on ROC-AUC, Brier, or ECE.

**Mechanistic interpretation**: the classifier was trained **without** dropout (`routing_classifier.py:268-326` — pure mini-batch SGD with cosine LR decay, no dropout in train or forward). Test-time dropout is therefore **noise injection** into a network that wasn't conditioned to be invariant under it — variance reflects "how much does the model wobble under random feature suppression?" which turns out to be weakly correlated with correctness (best AUC 0.91) compared to "how confident is the model in its top class?" (AUC 0.92). The Bayesian-posterior interpretation of MC-dropout (Gal & Ghahramani 2016) explicitly requires train-time dropout — applied without it, MC-dropout is just feature-noise sensitivity, and feature-noise sensitivity is not a calibrated correctness signal on this model.

**Implication for Phase 6**: Hypothesis B closed. The verifier's information-theoretic edge identified in the P6.1 audit (joint conditioning on `(embedding, action)` rather than the marginal `p_softmax(a|x)`) remains the only candidate route to improving correctness prediction beyond the existing per-class threshold. **Proceed to P6.2.**

**Re-opening criteria for Hypothesis B**: if the classifier is ever retrained **with** dropout (i.e., adding dropout to the train-time forward pass), re-run this eval. With train-time dropout, MC-dropout becomes the Bayesian posterior approximator it is in the literature, and the result may flip. Until then, the falsification stands.

**Artifacts** (preserved for re-runs):
- `orchestration/repl_memory/routing_classifier.py:163-200` — `mc_predict()` method (added 2026-05-21)
- `scripts/graph_router/mc_dropout_eval.py` — eval harness (created 2026-05-21)
- `/tmp/p6_4_training_data.npz` — ephemeral training NPZ (regenerable from `reembedded.npz`)

**Files**:
- Modified: `orchestration/repl_memory/routing_classifier.py` — add `mc_predict()` method (small change, <50 LoC)
- New: `scripts/graph_router/mc_dropout_eval.py` — evaluation harness

**Why this runs in parallel to P6.1**: P6.4 is a property of the *existing* MLP and doesn't depend on the verifier architecture question. If P6.4 already explains away the verifier idea (i.e., MC-dropout is a sufficient calibrator), that's a faster falsification path than P6.1's analytical audit. Run both; let whichever finishes first inform the other.

#### Phase 6 dependency graph

```
P6.1 (audit, no code)  ──pass──► P6.2 (MLP verifier) ──pass──► P6.3 (recursive verifier)
        │                                │
        └── parallel ────────────────────┤
                                         │
P6.4 (MC-dropout proxy, no dep) ─────────┘
                                         │
                                         ▼
              Either P6.2 OR P6.4 surviving its decision gate is sufficient to
              justify continued Phase 6 investment. If BOTH yield null results,
              archive Hypothesis C and Hypothesis B; Phase 6 closes.
```

#### Phase 6 open questions

1. **Correctness label semantics**: is "no escalation within this session" the right correctness label, or does that conflate "MLP was right" with "MLP was wrong but user gave up"? P6.2.2 must resolve this — likely needs a more nuanced label like "MLP routed and the downstream task completed with quality ≥ threshold".
2. **Joint vs cascaded training**: should the verifier be trained jointly with the classifier (shared backbone) or as a fully decoupled head? P6.2 starts cascaded (frozen classifier, train verifier on its outputs) for engineering simplicity; joint training is a follow-up if cascaded plateaus.
3. **Verifier latency budget**: if P6.2 verifier adds ≥ 2ms per decision, the orchestrator may want to skip it for low-stakes routes. Per-route gating policy is a P6.2.5 question, not a P6.2.1 question.
4. **Interaction with [DAR-2](decision-aware-routing.md) contrastive sharpening**: if both DAR-2 and a verifier are active, do their decision boundaries reinforce or contradict? P6.1.3 audit must address this.

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

## Research Intake Update — 2026-05-19

### Gradient-free training paths for the MLP router — ES cluster

If the Phase 1 MLP routing classifier (92% val acc) plateaus on the available labelled routing-decision dataset, four newly-ingested ES-at-LLM-scale entries offer gradient-free alternatives that don't require additional labelled data:

- **[intake-532] EGGROLL** (arxiv:2511.16652) — rank-r perturbation ES at billion-param scale; the broad "scale-out" reference.
- **[intake-563] ES-at-Scale** (arxiv:2509.24372) — **pop=30 suffices for billion-parameter LLM fine-tuning**. For our MLP head this is even more tractable; population fits trivially in 1.1 TB RAM.
- **[intake-564] ESSA** (arxiv:2507.04453) — **INT4/INT8 quantized inference for fitness evaluation + LoRA-SVD parameter restriction**. The only ES-LLM paper that operates the optimizee in low-bit quant — exactly EPYC's CPU comfort zone (per `project_q8_8x8_avx512bw_outcome`). For the MLP router specifically: same SVD-restricted parameter trick could compress the classifier's adapter-space to a few hundred singular values, then ES-train on labelled routing decisions without backprop.
- **[intake-565] Matching Accuracy, Different Geometry** (arxiv:2604.01499) — **the qualifying study**. ES and GRPO match on accuracy but produce nearly orthogonal updates with ES inducing **substantially larger off-task KL drift**. **Implication for this handoff**: if we adopt any ES-style training of the MLP router, we MUST also measure routing accuracy on held-out task distributions, not just the training task. The off-task drift caveat is the load-bearing reason to insist on a multi-distribution evaluation, not just the train-task gate.

**Action**: keep this on the radar but do NOT branch a separate handoff. If/when Phase 1 plateaus and gradient labels run out, the natural escalation is ESSA-style LoRA-SVD + INT4/INT8 ES (CPU-feasible today) under the four-point ES-LLM evaluation protocol documented in `routing-and-optimization-index.md` (off-task KL, linear-mode-connectivity, iteration-budget control).
