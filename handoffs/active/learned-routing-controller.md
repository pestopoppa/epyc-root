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

- [x] **P1.5.1** Instrument frontdoor to log top-k=64 first-token log-probabilities — DONE 2026-04-17, re-verified 2026-07-03. `src/backends/llama_server.py` adds `n_probs=64` only for `frontdoor` when `ORCHESTRATOR_LOGIT_PROBE=1`, and `_write_logit_probe()` appends hashed prompt metadata plus first-token top-k probabilities to `data/logit_probe.jsonl`. 2026-07-03 coverage pins the default-off feature flag/env gate, frontdoor-only payload behavior, sanitized JSONL writes, and runtime-flag-isolated feature registry defaults.
- [ ] **P1.5.2** Collect over ~1000+ requests — FROZEN under the 2026-06-12 routing-expansion guard. Reopen only after a current-traffic DAR-1 replay shows >=5% identifiable routing regret and N2 per-question vectors exist; then enable `ORCHESTRATOR_LOGIT_PROBE=1` in a coordinated collection window.
- [ ] **P1.5.3** Train linear probe (512 params), evaluate accuracy — gated by P1.5.2 collection.
- [ ] **P1.5.4** Decision gate: >= 80% → proceed to Phase 2; < 60% → stay with BGE+MLP — gated by P1.5.3.

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
- [x] **P4.1.3** **IRT-feature audit (intake-496 LLM Bandit)** — **COMPLETE 2026-06-27; label-proxy positive, cached observed-outcome null.** Orchestrator adds `scripts/graph_router/irt_feature_ablation.py`, an evidence-only diagnostic that fits train-split IRT difficulty/discrimination targets from the existing label-proxy matrix, projects those two scores from the BGE embedding columns, appends them to the routing features, and trains the same numpy `RoutingClassifier` head without writing production weights. The 80K-row run in `orchestration/reports/p413_irt_feature_ablation/report_20260627_sample80k.json` used `64K` train / `16K` validation rows from the current `275,960`-row `training_data.npz`: baseline `1031`-feature head reached `69.20%` validation accuracy, while the IRT-augmented `1033`-feature head reached `78.22%` (`+9.02pp`, gate threshold `+1pp`). The follow-up cached observed-outcome diagnostic in `scripts/graph_router/observed_irt_feature_ablation.py` wrote `orchestration/reports/p413_observed_irt_feature_ablation/report_20260627_cached_p45.json` from the P4.5 soft-label embedding artifact (`540` qids, `710` observed role cells): baseline role-success accuracy was `53.70%`, observed-IRT role-success accuracy was also `53.70%` (`0.00pp`), with worse argmax match (`77.78%` vs `78.70%`). **Decision**: do not escalate observed IRT features from the cached outcome matrix. Treat the label-proxy lift as a lead for a future promotion-grade prompt×action outcome dataset only, not as deployable routing evidence.
- [x] **P4.2** **Block-ε-separability diagnostic (medium cost)** — **COMPLETE 2026-06-27, NULL FOR BLOCK-SEPARABILITY / FULL-RANK DOMINATES**. Trinity's optimizer-choice argument rests on the loss surface being block-ε-separable (formal Hessian-based definition; their empirical evidence is a "block-diagonal-10" head retaining competitive performance). Orchestrator `60c0b784` adds `scripts/graph_router/block_separability_diagnostic.py` plus focused tests and writes `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/p42_block_separability/report_20260627_sample80k.json`. The 80K-row offline diagnostic used a fixed 64K/16K train/val split from `orchestration/repl_memory/training_data.npz`: majority baseline `49.33%`, full-rank `81.09%`, block-10 `56.55%`, diagonal `49.33%`. Result: block-10 is `-24.54pp` vs full, so the routing-label geometry does **not** match Trinity's block-separable assumption for this surface. **Decision**: DAR-4 should prefer full-rank/shared structure, not rank-restriction as a default mitigation; P4.4 sep-CMA-ES is no longer justified by P4.2 and should remain gated to a future true cold-start/no-label surface rather than this trained-label classifier.
- [ ] **P4.3** **SVD-scale fine-tuning trial (medium cost; currently artifact/env-blocked for the true experiment)**: Trinity uses singular-value FT on the backbone — learn only singular-value scales, keep orthogonal matrices fixed (~9K extra params). Their ablation: removing SVD-FT costs −3 to −4 points across all four benchmarks. This is a parameter-efficient adaptation cheaper than LoRA and applicable to whatever backbone we use as the routing-head feature extractor. **2026-06-27 feasibility checks**: the live feature extractor is `bge-large-en-v1.5-f16.gguf`, served through llama-server `/embedding`, and both orchestrator/research registry state point to that GGUF. No local trainable `BAAI/bge-large-en-v1.5` HF checkpoint was found, only GGUF/HF download metadata. The only local trainable BGE-family checkpoint is `/mnt/raid0/llm/hf/BAAI_bge-m3`, with `pytorch_model.bin`, tokenizer files, `colbert_linear.pt`, and `sparse_linear.pt`, but using it would change the extractor and would not answer the original BGE-large last-block SVD-FT question. Available envs are partial (`torch+transformers+safetensors` in `/mnt/raid0/llm/tmp/a9-neuraltxt-cpu-venv` and `/mnt/raid0/llm/comfyui-ernie-test/ComfyUI/.venv`; `datasets` only in research `.venv`), with no single env containing the full `torch`/`transformers`/`peft`/`accelerate`/`sentence-transformers`/`safetensors` stack. **Next real gate**: acquire/restore a trainable BGE-large checkpoint and an isolated full training environment, then implement SVD-FT on the last `k` transformer blocks, retrain the head end-to-end, and A/B against frozen BGE-large on the same validation split. **Allowed interim work**: a BGE-M3 proxy or feature-space spectral scaling run may be performed only if reported as proxy evidence, not as P4.3 completion. Decision gate for the true trial remains: if Δ ≥ +2 points val acc, promote SVD-FT to default; if flat, record null and move on.
- [ ] **P4.4** **sep-CMA-ES cold-start spike (large cost; no longer justified for the current trained-label surface after P4.2)**: Trinity trains the routing head with sep-CMA-ES against terminal binary reward (no labels). P4.2 refuted the block-separable rationale on the current episodic-label classifier, so do **not** spend an overnight ES run here just to chase Trinity transfer. Keep this only for a future true cold-start surface with sparse/no distillation labels (Phase 2/3 hidden-state probe, a new role surface, or a new model added to the pool) where ES against eval-tower fitness could train the head from cold. Replication budget estimate (deep-dive Section 5): population λ≈45 for our 200K-param head, m=16 reps, ≈720 fitness evals per generation, ≈10 generations as feasibility-test target ≈ 10h overnight at 32-way concurrency. Prerequisites remain: (a) eval-tower wired as a per-question scorable, parallelisable fitness oracle (Math-Verify adoption is on the critical path — see `routing-and-optimization-index.md` cross-cutting concern #13), (b) `pycma` or equivalent sep-CMA-ES library vendored.
- [x] **P4.5** **Journal-derived soft-label SFT — zero-inference cold-start (Fugu Stage 1 analog)** — **COMPLETE 2026-06-26, NULL RESULT (soft labels do NOT beat hard labels; keep hard-label training)**. See "P4.5 Phase B Outcome" below for the full A/B. Original spec: Fugu Stage 1 trains via KL divergence against a per-worker reward distribution rather than contrastive binary labels. The equivalent for our LRC: for each `qid` with ≥5 appearances in the autopilot journal `question_results`, compute mean correctness per role across all trials → apply softmax(τ=2) → use as a soft probability distribution over roles for that question type. Train LRC via KL(predicted_logits ∥ soft_labels) instead of cross-entropy on hard winner-take-all labels. **Cost: zero additional inference** — all data is already in `orchestration/autopilot_journal.jsonl`. Current data: 546 qids with ≥5 appearances, ~5 roles → ~2,730 soft-label examples. Implementation: (a) extract per-qid per-role mean correctness from `question_results` in journal (script already feasible given the earlier per-question analysis); (b) apply softmax τ=2 to get probability vectors (τ=2 gives soft distributions; τ→0 is winner-take-all; τ→∞ is uniform — tune τ on a held-out quality check); (c) retrain LRC head via KL loss. Decision gate: if val acc improves ≥1 pp over hard-label baseline, adopt as the default Phase 1 training signal going forward. **Critical caveat**: the stable core has 3/50 mid-range qids (30–70% pass rate) — the remaining 47 are polarized floor/ceiling. This means the soft labels will be mostly near-deterministic (one role clearly dominates each question type), so the KL signal will be similar to hard labels for those cases. The real benefit is on the ~300 qids in the rotating pool with genuine mid-range histories (53% mid-range at ≥5 appearances), where the soft labels capture real uncertainty across roles. **Priority**: HIGH relative to P4.3/P4.4 — zero inference cost makes this the lowest-risk next experiment.
- [x] **P4.6** **Randomized-pool training for stack-change robustness (Conductor analog, added 2026-06-25)** — **COMPLETE 2026-06-27, NULL RESULT under the current P4.5 soft-label objective**. Orchestrator `688c6076` adds opt-in `--role-dropout-rate` training for the KL/soft-label arm and focused unit coverage; `a404e3bc` records 10 offline runs at rates `0.2` and `0.3` across five seeds. No run beat the hard-label arm by the +1pp role-success gate, so decision remains **keep current hard-label training**. Artifacts: `orchestration/reports/p46_role_dropout/{summary.json,summary.md,rate_*_seed_*.json}`. Future available-role robustness should be revisited only with an architecture/input contract that exposes role availability to the model, not by retuning this soft-label-only dropout path.

### Phase 5: IRT-Stratified Cold-Start Onboarding (NEW 2026-04-28, from intake-496)

Source: intake-496 (LLM Bandit) — model identity vectors + Item Response Theory (IRT) discrimination-score-stratified prompt selection enable cold-starting a new specialist with 20–50 carefully chosen prompts instead of a full benchmark sweep.

**Why this matters for EPYC**: every model swap currently triggers a full benchmark sweep against the q-scorer baselines. Recent swaps (worker → 30B-A3B 2026-03-21, q-scorer recalibration 2026-03-21, coder Q4KM 2026-03-24) each cost a sweep. If the IRT-stratified cold-start workflow produces baselines within ~2 points of the full sweep, future swaps compress from a multi-hour sweep to a focused ~30-minute calibration. **This is the most actionable single experiment from intakes 495/496.**

Sequencing note: P5 is gated on having an IRT scorer (built in P5.1), NOT on Phase 2/3 completing. P5 can run in parallel with Phase 2 hidden-state work.

- [x] **P5.1** **IRT discrimination scorer substrate (~80–100 LoC, ~2 sessions)** — **COMPLETE 2026-06-27 as artifact-only scorer; outcome-matrix calibration remains a P5.2/P5.1b evidence task**. Orchestrator `3e0dcae9` adds `scripts/graph_router/irt_scorer.py` plus focused tests. The scorer is numpy-only and sidecar-only: it accepts direct prompt×model/action `responses` matrices with NaN masks for observed per-model outcomes, estimates `(latent_difficulty, latent_discrimination)`, fits global Platt calibration, and persists a compact NPZ artifact with canonical action map, calibration metadata, and a linear BGE-embedding projector for future prompt scoring. It also supports the current `training_data.npz` contract (`X`, `y`, `q_weights`, `label_map`) in explicitly marked `response_source="label_proxy"` mode so P4.1.3/DAR-5 feature experiments can proceed without inference. **Caveat**: the real cold-start adoption gate still requires observed per-model outcome responses, not just label-proxy routing labels. **Validation**: ruff + `tests/unit/test_irt_scorer.py` and `tests/unit/test_graph_router_action_space.py` (`15 passed`); real artifact smoke over 2,000 rows from `orchestration/repl_memory/training_data.npz` wrote `/mnt/raid0/llm/tmp/irt_prompt_scores_smoke.npz` with 8 actions, Platt params, and projector arrays.
- [ ] **P5.2** **Cold-start A/B vs on-disk full sweep (~70 LoC harness, 1 session)** — **HARNESS + KEYED-EMBEDDING BUILDER + ACCEPTANCE GATE COMPLETE 2026-06-27; promotion-grade observed-outcome run remains**. Orchestrator `6d0d1ecb` adds `scripts/calibration/irt_cold_start_ab.py` and tests. The harness flattens legacy baseline JSON artifacts (for example `benchmarks/results/runs/20260303_170903/worker_general_baseline.json`), selects an IRT-stratified subset across difficulty bins, compares subset vs full baseline summary (`avg_algorithmic_score`, `avg_tokens_per_second`, `pass_rate`), and writes a JSON report. It deliberately refuses to make a fake comparison unless baseline prompts can be matched to keyed IRT scores (`prompt_hashes`/`question_ids`) or keyed prompt embeddings plus the P5.1 projector. Orchestrator `a07edeff` adds `scripts/calibration/build_irt_prompt_embeddings.py`, which embeds baseline prompts through the live embedding fleet and writes both keyed prompt embeddings and optional keyed IRT-score artifacts. Orchestrator `039c6062` adds `--acceptance-gate`, wall-clock speedup checks, configurable metric thresholds, and zero-inference `--input-embeddings` reuse that rekeys cached embedding rows to the target baseline before writing new artifacts. **Smokes**: unkeyed label-proxy artifact correctly reports `blocked_missing_irt_scores` (`full_records=91`, `scored_records=0`); a two-record live embedder smoke over `worker_general_baseline.json` produced 1024-dim prompt embeddings and keyed IRT scores, and the harness then reached `status=ok` with `scored_records=2`. A full keyed plumbing run over all 91 `worker_general_baseline.json` records produced `/mnt/raid0/llm/tmp/worker_general_baseline_prompt_embeddings_20260627_185242.npz`, `/mnt/raid0/llm/tmp/worker_general_keyed_irt_scores_20260627_185242.npz`, and `/mnt/raid0/llm/tmp/worker_general_irt_cold_start_20260627_185242.json`; the harness scored all 91 records with a 50-prompt subset and reported relative deltas of 2.29% (`avg_algorithmic_score`), 3.54% (`avg_tokens_per_second`), and 9.0% (`pass_rate`). The new acceptance gate wrote `orchestration/reports/p52_irt_cold_start_acceptance/worker_general_cached_label_proxy_20260627.json` and correctly rejected the label-proxy subset: score and speed were within 5%, but pass-rate relative error was 9.0% and wall-clock speedup was only 1.94× vs the required 5×. This remains plumbing evidence only because the scorer is label-proxy-derived, three over-context prompts were truncated by the embedder path, and promotion still requires observed per-model outcome scores. **Next acceptance task**: run the same gate with a promotion-grade observed-outcome IRT scorer; accept only if all configured baseline features are within threshold and the measured wall-clock speedup clears the gate.
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

**2026-07-03 window-2 re-triage (intake sweep + MI210)**: ES is the one training family that needs **only forward passes** — no autograd/flash-attn — so it sidesteps the "gfx90a training-viability [unverified]" gate that blocks every gradient-based fine-tune (F3-W3 QLoRA, agent-world GRPO). The MI210 (batched forward ~910–1129 tok/s @32-way) is now a viable *population-eval accelerator* for it (T1); the live evidence-plane ledger supplies the honest fitness signal ES needs (T2). **This section owns the ROUTER-scoped path only**; the genuinely-uncovered sliver flagged by the sweep is a **NON-router ES target** (a small verifier/specialist or a frontdoor-target drafter LoRA-SVD adapter), which routing-freeze does not touch. Two hard gates before any such spike, both adversarially confirmed: (1) **fitness oracle must be a held-out eval slice, NOT the live authority eval-tower** — wiring the tower as an ES oracle is an operator-only, human-amendment-only change and a textbook Goodhart risk (P4.4 lists this prereq as UNMET); (2) **no LoRA-SVD→GGUF weight-reconstruction path exists** in our llama.cpp+GGUF stack (ESSA assumes PyTorch/BitsAndBytes) — that tooling is the real first task, not the ES loop. Decisive cheapest test unchanged: ~200-iter NES, pop≈16–30, on a small Q4_K/Q8_0 GGUF we already serve, held-out fitness + bounded off-task KL (intake-565 guardrail). Refs: intake-564/563/532/565; deep-dive `research/deep-dives/2026-05-19-es-llm-scale-cluster.md`.

## Research Intake Update — 2026-06-20

### Offline reward-model stack (intake-706 / 716 / 717 / 719)

A 2026-06-20 deep-dive consolidated four sibling intake entries — AVB's "offline reward stack" — into one actionable insight: a **tiny, CPU-runnable, reference-grounded answer-quality regressor** plus its training recipe (intake-706 architecture + intake-716 `train_reward_model.py`), its dataset (intake-717 `paper_answers_reward`, 22,423 rows), and a published 22M MiniLM checkpoint (intake-719 `neuraltxt-reward-tiny`). It scores `"{reference} [SEP] {response}"` via MSE (pointwise regression, **not** Bradley–Terry) on small sentence-transformers — CPU-trainable and CPU-servable on our hardware.

- **Fills a real, currently-empty slot.** Our live reward "quality" term is **binary** (`q_reward.py`: success 1.0 / partial 0.3 / failure −0.5 + cost penalty), and the only graded-quality path, **ClaudeAsJudge, is disabled** (`model_registry` `claude_as_judge.enabled: false`; ch08 lists it as Future Work). A tiny reference-grounded MSE scorer is a CPU-cheap way to produce a graded answer-quality label offline — an alternative to standing up ClaudeAsJudge for *offline* label generation.
- **Anchors on NEXT-A2 / NEXT-A3.** The Phase-6 frontdoor verifier (~68k params, built, default-OFF behind `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE`) was trained on a **policy-biased** Q/outcome label. NEXT-A asked for "a policy-debiased `final_task_quality_score` from a quality oracle **independent of the Q-update loop**." This reference-grounded scorer — trained on seeding/eval `(reference, response)` pairs, not the Q/TD loop — is a candidate for exactly that independent label, foldable into NEXT-A3's post-`--repair-embeddings` re-extraction. (Do NOT edit the NEXT-A/A2/A3 bodies — this section only.)
- **OFFLINE-only.** There is **no reference answer at live-routing time** (`chat_pipeline` has no `expected_answer` plumbing); references exist only in the seeding/eval path (`seed_specialist_routing.py`, `debug_scorer` expected-fields). The use is offline quality-oracle label generation + eval scoring — **not** a live router, live quality gate, or live ClaudeAsJudge replacement.
- **Caveats (load-bearing).** All magnitude numbers (self-reported MiniLM Spearman ~0.718 / DistilBERT ~0.757 vs RewardBert 0.44; answer-equiv ROC-AUC ~0.93–0.94; confound resistance 6–12% fooled) are **observations** — no protocol, never decision-gating (`MEASUREMENT.md`). intake-717's dataset card omits judge/rubric/source-model **provenance — verify the parquet first**. intake-719 catches only ~3% of **synonym swaps** (paraphrase-correct answers scored low) — a mandatory paraphrase/synonym stress test before any adoption. Do **not** propose this under `decision-aware-routing.md` or `retrain-routing-models.md` (both expansion-FROZEN per fable5-findings-02).

Full digest: [2026-06-20-avb-offline-reward-stack.md](../../research/deep-dives/2026-06-20-avb-offline-reward-stack.md)

### Implementation checkpoint — 2026-06-21

The A9 offline reward-oracle lane now has working scorer plumbing and two
observation artifacts in `epyc-orchestrator`:

- `8fecf4a2` adds
  `scripts/graph_router/score_offline_reward_oracle_neuraltxt.py` and unit
  tests for the optional-dependency `paperbd/neuraltxt-reward-tiny` adapter;
- `6b99b2b1` records the first real-checkpoint smoke report at
  `orchestration/reports/offline_reward_oracle_neuraltxt_20260621/`
  (`50` source rows, `69` scored rows, Spearman `0.7564`, agreement
  `0.7391`);
- `71beeb4f` records the broader binary/stress observation report at
  `orchestration/reports/offline_reward_oracle_neuraltxt_broad_20260621/`
  (`89` source rows, `87` scored rows, Spearman `0.8018`, agreement
  `0.7701`, paraphrase/confound stress `0/29`);
- `40b9c44f` records the held-out-style observation report at
  `orchestration/reports/offline_reward_oracle_neuraltxt_heldout_20260621/`
  over `seeding_live_seed42.json` and `seeding_20260305_203724.jsonl`
  (`178` source rows, `144` scored rows, Spearman `0.2728`, agreement
  `0.6181`, `tp=41 fp=0 fn=55 tn=48`);
- `78bdc573` adds threshold calibration to the evaluator and regenerates the
  held-out report: best agreement is threshold `0.16`
  (`tp=60 fp=4 fn=36 tn=44`), best zero-false-positive threshold is `0.25`
  (`tp=53 fp=0 fn=43 tn=48`), and best F1 is a degenerate all-positive
  threshold `0.00`.
- `ba48a522` adds
  `scripts/graph_router/reconstruct_answer_equivalence_targets.py` and records
  the prompt-free audit at
  `orchestration/reports/offline_reward_oracle_answer_equivalence_20260621/`.
  The conservative deterministic proxy agrees with the current held-out target
  on `130/178` rows, flags `48` disagreement rows, and finds only `10/178`
  deterministic proxy positives. The disagreements split into `43` current
  positives that are not deterministically reconstructable and `5` current
  negatives that look deterministically equivalent.
- `0fcebf26` adds
  `scripts/graph_router/prepare_answer_equivalence_review.py` and records the
  redacted review queue at
  `orchestration/reports/offline_reward_oracle_answer_equivalence_review_20260621/`.
  The committed manifest has `48` rows with `review_bucket`,
  `manual_label`, `judge_label`, `semantic_label`, `final_label`,
  `label_source`, and `label_status` slots, and excludes prompt/reference/
  response text. The private packet for actual review text is intentionally
  outside git at
  `/mnt/raid0/llm/tmp/a9_answer_equivalence_review_20260621_private.jsonl`.
- `1e08e459` seeds source-backed labels into the review queue. All `43`
  `current_positive_not_deterministically_reconstructable` rows have source
  `passed=True` and are now `final_label=equivalent`,
  `label_source=source_passed_true`, `label_status=seeded`. The remaining `5`
  `current_negative_deterministically_equivalent` rows stay
  `label_status=needs_semantic_judge` because deterministic equivalence
  conflicts with source `passed=False`.
- `419440ea` adds a prompt-free manual label overlay for those remaining `5`
  conflict rows and regenerates the redacted review manifest as
  `labeling_complete`: final labels are `47` equivalent and `1`
  not-equivalent, with label status split `43` seeded / `5`
  manual-reviewed. The overlay stores only item IDs, labels, label source/
  status, and note codes; prompt/reference/response text stays outside git.
- `87728c44` records the final-label NeuralTxt rerun at
  `orchestration/reports/offline_reward_oracle_neuraltxt_final_labels_20260621/`.
  The report scores all `178` base held-out rows, uses reviewed
  `final_label` targets for the `48` answer-equivalence review rows, and keeps
  original binary targets for the other `130` rows. Result: Spearman `0.2416`,
  Pearson `0.3630`, threshold-`0.5` agreement `0.7528`
  (`tp=21 fp=13 fn=31 tn=113`), best agreement threshold `0.66`
  (`tp=18 fp=6 fn=34 tn=120`), and no-false-positive threshold `0.84`
  recalls only `6/52` positives.
- 2026-06-21 follow-up: the evaluator now reports target-source, suite, and
  role-key slices for the final-label run. The aggregate `0.7528` agreement is
  mostly carried by the negative-heavy `original_binary_reward` subset
  (`130` rows, `5` positives / `125` negatives, agreement `0.9000`,
  Spearman `0.3129`, confusion `tp=5 fp=13 fn=0 tn=112`). The reviewed
  `answer_equivalence_final_label` subset is the actual failure surface:
  `48` rows, `47` positives / `1` negative, agreement `0.3542`, Spearman
  `-0.0579`, confusion `tp=16 fp=0 fn=31 tn=1`. Worst slices are
  `livecodebench` (`24` positives, `tp=1 fn=23`) and `frontdoor:direct`
  (`44` positives / `5` negatives, `tp=14 fp=3 fn=30 tn=2`).
- 2026-06-21 follow-up: the evaluator now emits a machine-readable
  `decision_gate`. The first final-label report was explicitly `blocked` by
  aggregate agreement/Spearman/balanced-accuracy thresholds,
  answer-equivalence slice negatives/agreement/Spearman, and missing
  paraphrase/confound stress rows. This prevents the negative-heavy aggregate
  from being mistaken for NEXT-A2/A3 adoption evidence.
- 2026-06-21 follow-up: the final-label report now reuses the already-scored
  held-out stress rows, producing a `322`-row final-label-with-stress artifact:
  `178` base/final-label rows plus `144` held-out stress rows (`48` base,
  `48` paraphrase, `48` confound). Stress checks now pass (`48` groups,
  paraphrase penalty rate `0.0000`, confound fooled rate `0.0000`). The
  `decision_gate` remains `blocked` by aggregate agreement `0.6925`, Spearman
  `0.2771`, best balanced accuracy `0.6949`, and the same
  `answer_equivalence_final_label` slice failure (`48` rows, `47` positives /
  `1` negative, agreement `0.3542`, Spearman `-0.0579`, `tp=16 fp=0 fn=31
  tn=1`). The blocker is now the scorer/target quality signal itself, not
  missing stress evidence.
- 2026-06-21 follow-up: the answer-equivalence audit now has an explicit
  `review_candidates` export that can include target/proxy-agreed negatives.
  The regenerated review manifest has `173` labeled rows: `47` equivalent and
  `126` not-equivalent (`125` from the agreed-negative bucket, `5`
  manual-reviewed conflict rows, `43` source-passed positives). The evaluator
  now honors `target_score` before legacy `binary_reward`, so these final
  labels are actually authoritative in the report. The latest
  final-label-with-stress artifact still has `322` rows and still blocks, but
  the blocker has moved: answer-equivalence coverage passes (`173` rows,
  `47` positives / `126` negatives), while quality misses remain
  (`agreement=0.7457` vs `0.75`, Spearman `0.1845` vs `0.2`, confusion
  `tp=16 fp=13 fn=31 tn=113`). Aggregate quality also remains below gate
  (`agreement=0.6925`, Spearman `0.2771`, best balanced accuracy `0.6949`).
  A9 now needs a better oracle/scorer, not more coverage plumbing.
- 2026-06-21 follow-up: a separate deterministic
  `reference_token_coverage` scorer now clears the same final-label-with-stress
  gate at threshold `0.86` (`322` rows, aggregate agreement `0.9410`,
  Spearman `0.8270`, best balanced accuracy `0.9439`; answer-equivalence slice
  agreement `0.9017`, Spearman `0.6866`; stress `48` groups, paraphrase
  penalty `0.0000`, confound fooled `0.0000`). `d03cf706` records the scorer
  and report, and the follow-up adoption packet at
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/adoption_manifest.json`
  has schema `offline_reward_oracle_adoption_manifest.v1`,
  `status=adoptable_offline_oracle`, `oracle_threshold=0.86`, and an explicit
  offline-only/forbidden-live-use contract. The manifest builder rejects the
  failed NeuralTxt final-label report (`decision_gate.status=blocked`) and
  writes no adoption artifact for it.
- 2026-06-21 follow-up: `scripts/graph_router/export_offline_reward_oracle_labels.py`
  consumes the adoption manifest plus the private scored JSONL and emits a
  prompt-free row-level label export at
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_labels.jsonl`
  with summary files beside it. The export has `322` labels, `161` oracle
  positives / `161` oracle negatives, and target agreement `0.9410`; it strips
  prompt/reference/response/expected/answer fields and fails closed on
  non-adoptable manifests. This is now the durable offline label table for
  NEXT-A2/A3 preparation. It is not yet a verifier NPZ because these A9 rows do
  not carry the memory IDs needed to join directly to
  `extract_verifier_training_data_debiased.py`; the next integration step is an
  explicit source-row/role-to-feature join or a separate benchmark-row embedding
  extractor, not a silent replacement of the existing outcome-backed verifier
  labels.
- 2026-06-21 follow-up: `scripts/graph_router/build_offline_reward_feature_manifest.py`
  now validates that label export against the original benchmark source rows
  and emits
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_feature_manifest.jsonl`
  plus summary files. The manifest has `322` prompt-free feature-input rows,
  `89` unique source records, and records the real label provenance as
  `source_record_index_base=one_based` for all rows while storing the resolved
  zero-based `source_record_offset`. Prompt/expected/answer text is represented
  only by SHA-256 hashes and lengths. This closes the source/role join gap for
  NEXT-A2/A3 preparation; the remaining integration step is an embedding/NPZ
  extractor that consumes this manifest, embeds source prompt/context rows, and
  joins labels by `join_key`.
- 2026-06-21 follow-up: `scripts/graph_router/build_offline_reward_verifier_npz.py`
  now consumes the feature manifest and emits a verifier-compatible offline NPZ
  at
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_verifier_data.npz`
  plus summary files. The artifact has `322` rows, embeds `89` unique source
  records, uses feature dimension `1031` (`1024` BGE embedding plus the 7
  engineered features), appends the live 10-action one-hot, and carries
  balanced oracle labels (`161` positive / `161` negative). Metadata remains
  prompt-free; prompt/expected/answer text is represented only by SHA-256 hashes
  and source offsets. This closes the manifest-backed NPZ extraction step for
  NEXT-A2/A3 preparation.
- 2026-06-21 follow-up: the first offline frontdoor-specialist verifier
  train/eval on `offline_reward_verifier_data.npz` is a null result for
  promotion. The frontdoor subset has `224` rows (`142` positive / `82`
  negative); the validation split has `44` rows. The verifier improves Brier
  over the best softmax baseline by `+0.0298` (passes the `>=0.02` softmax
  comparison gate), but is worse than the constant base-rate Brier baseline by
  `-0.0101`; ROC-AUC is `0.7478` (misses `>=0.75`) and ECE is `0.1465` (misses
  `<=0.05`). No live weight was promoted and
  `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE` remains default-off.
- 2026-06-21 follow-up: the broader multi-action verifier path now consumes the
  same manifest-backed NPZ directly by using the verifier feature prefix as the
  classifier-baseline input when no row-aligned `X` matrix is present. This
  offline eval covers all `322` rows (`161` positive / `161` negative) with a
  `64`-row validation split and represented actions `{frontdoor: 224,
  architect_general: 10, coder_escalation: 88}`. It is better than the
  frontdoor-only attempt but still not promotable: Brier delta is `+0.1008`
  versus the best softmax baseline and `+0.0412` versus constant base-rate, and
  ROC-AUC is `0.8916`, but ECE is `0.1783` (misses `<=0.05`). No live weight was
  promoted; the next offline step is calibration/data improvement, not a runtime
  verifier gate change.
- 2026-06-21 follow-up: a disjoint train/calibration/test scout adds
  temperature/bias post-hoc calibration to the same multi-action verifier path.
  The split is `194` train / `64` calibration / `64` test rows. Calibration
  improves Brier (`0.2325` -> `0.1854`) and accuracy (`0.7188` -> `0.7344`) on
  the held-out test split, while preserving ROC-AUC `0.8709`, but ECE remains
  failed (`0.1810` -> `0.1788`, gate `<=0.05`). No live weight was promoted;
  simple post-hoc scaling is not enough, so the next offline step is better
  data/model calibration.
- 2026-06-21 follow-up: the feature-contract repair now adds a prompt-free
  source-family axis. `build_offline_reward_feature_manifest.py` emits
  `source_family_onehot[4]` derived from source path metadata
  (`orchestrator_live_seed`, `seeding_eval`, `three_way_eval`, `other`), and
  `build_offline_reward_verifier_npz.py` adds the explicit
  `source_family_response_telemetry` contract while keeping the old
  `prompt_only` and `response_telemetry` contracts intact. The regenerated
  expansion manifest has `524` rows and engineered feature dimension `11`.
  The new conflict-dropped NPZ summary records `336` retained rows,
  `feature_dim=1039`, `source_family_onehot[4]`, and `0` conflicting
  model-input groups. Robustness remains `not_promotion_grade`: calibrated pass
  rates are `0/10` for `temperature_bias`, `0/10` for `ece_temperature_bias`,
  `0/10` for `isotonic`, and `1/10` for `quantile_histogram`. The best
  aggregate mean ECE is still too high (`isotonic=0.1119`,
  `ece_temperature_bias=0.1225`, `quantile_histogram=0.1174`). No live verifier
  weights or runtime gate changed. This partially improves discrimination but
  confirms the next useful A9 step is a model-family or split-stratification
  repair, not another scalar post-hoc calibration pass.
- 2026-06-21 follow-up: the model-family scout now compares
  `logistic_l2`, `hist_gradient_boosting`, `random_forest`, and
  `mlp_sklearn` over the same source-family conflict-dropped NPZ, split seeds,
  softmax baseline, and calibration gates. It remains `not_promotion_grade`.
  Best discrimination/Brier families improve the measured ceiling
  (`hist_gradient_boosting` raw AUC `0.9000`, temperature-bias mean Brier
  `0.1269`; `random_forest` raw AUC `0.8951`), but calibrated ECE still fails.
  Highest pass counts are only `2/10` (`logistic_l2` + isotonic,
  `random_forest` + ECE-temperature); no family/method reaches the required
  `10/10`. This narrows the next A9 step again: the blocker is not simply the
  NumPy MLP head. Prefer source-stratified calibration/evaluation and/or more
  balanced evidence rows before another verifier family sweep.
- 2026-06-21 follow-up: the same model-family scout now aggregates
  source-family metrics across split seeds. The stratum readout identifies the
  actual remaining evidence problem: `orchestrator_live_seed` is nearly
  calibrated (`hist_gradient_boosting:raw` mean ECE `0.0575`, mean AUC
  `0.9469`), `seeding_eval` has no two-class metric coverage (`11` retained
  rows total), and `three_way_eval` drives the failure (best mean ECE only
  `0.1340` from `logistic_l2:quantile_histogram`). Next A9 work should target
  balanced, source-family-aware evidence expansion or calibration for the
  `three_way_eval` family, plus enough `seeding_eval` positives/negatives to
  become measurable.

These reports prove the adapter can emit real non-baseline `oracle_score`
values and that the evaluator can consume them. NeuralTxt does **not** prove the
NEXT-A2/A3 label-quality gate. The held-out-style run is a cautionary signal:
with broader role coverage and graded `q_reward` inputs, rank agreement drops
sharply and threshold `0.5` behaves conservatively (zero false positives, many
false negatives). Calibration explains the operating points but does not
rescue the scorer for labels. The answer-equivalence audit confirms that exact
deterministic reconstruction is also insufficient, and the expanded final-label
rerun does not rescue NeuralTxt for NEXT-A2/A3 labels. Coverage is now adequate,
but rank correlation stays weak, useful no-false-positive recall is too low,
and the sliced view shows the long-response/code answer-equivalence rows are
where NeuralTxt fails. The current adoptable offline baseline is the
deterministic token-coverage manifest above. Next step is to consume that
manifest-backed NPZ in a stronger NEXT-A2/A3 offline reward-signal experiment:
improve data/model calibration for the broader multi-action consumer before any
runtime verifier gate change. The source-family and model-family repairs are
now measured and insufficient for promotion, so prefer source-stratified
calibration/evaluation or more balanced evidence rows over another scalar
calibration retry. The first source-stratified readout points at
`three_way_eval` calibration and `seeding_eval` coverage as the concrete next
targets. Do not feed NeuralTxt labels into
learned-routing reward signals from the failed NeuralTxt report alone.
- 2026-06-21 follow-up: orchestrator `caba3929` completed the seeding-eval
  NPZ/robustness rebuild from
  `offline_reward_feature_manifest_with_seeding_eval_expansion.jsonl`. The
  source-family control and intended `source_action_response_telemetry`
  artifact both retain `532/720` rows after exact conflict dropping, with
  canonical action coverage `architect_general=212`, `coder_escalation=78`,
  `frontdoor=242`. The source-action contract adds
  `source_family_x_action_onehot[40]` interaction features (`z_dim=1089`), but
  still fails promotion: 10-seed calibrated pass counts are `0/10` for
  `temperature_bias` and `0/10` for `quantile_histogram`; mean calibrated
  ROC-AUC/ECE are `0.7054/0.1308` and `0.6724/0.1400`. This closes the
  seeding-eval rebuild as another null result, not a live gate. Next A9 work
  should shift away from retuning this MLP/calibrator setup and toward better
  balanced offline evidence or a materially different reward/verifier design.
- 2026-06-21 follow-up: orchestrator now has a repeatable A9 stop-condition
  artifact at
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_verifier_decision_summary.{json,md}`.
  It summarizes `14` verifier/calibrator/model-family artifacts: all `14` are
  `not_promotion_grade`, `0` are promotion-grade, and the best pass rate is
  only `0.2` (`random_forest:ece_temperature_bias`). Decision:
  `stop_current_verifier_family`; runtime gate changes remain disallowed. Next
  A9 work must change the reward-oracle/label contract or collect materially
  different balanced evidence, not retune the same verifier family again.
- 2026-06-21 follow-up: orchestrator now has that materially different
  prompt-free contract:
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_pairwise_preference_contract.{jsonl,summary.json,summary.md}`.
  The new `within_task_pairwise_preference_v1` contract converts the `720`-row
  feature manifest into `280` within-task preference pairs across `103`
  contrastive source-record groups and `8` action-pair directions, including
  `87` cross-action routing preferences and `193` same-action response-quality
  contrasts. It changes the learning target from absolute binary prompt/action
  classification to within-source-record positive-over-negative preference,
  keeps prompt/answer/expected text excluded, and explicitly allows no runtime
  gate change. Next A9 work is an offline pairwise reward-ranker train/eval,
  not another absolute verifier retune.
- 2026-06-21 follow-up: orchestrator now has that offline pairwise
  reward-ranker train/eval:
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_pairwise_ranker_eval_summary.{json,md}`.
  The evaluator uses group-disjoint splits, symmetric pair augmentation, and
  the `pairwise_action_response_delta_v1` prompt-free feature contract; it
  explicitly excludes target/leakage fields (`oracle_score_delta`,
  `preferred_oracle_score`, `rejected_oracle_score`) and prompt/answer/
  expected/reference/response text. The five-seed model-family diagnostic marks
  `pairwise_ranker_signal`; best family is `random_forest` with mean accuracy
  `0.6615`, mean AUC `0.7631`, mean Brier `0.1922`, and mean ECE `0.0610`
  against a random-pair baseline accuracy/AUC of `0.5/0.5`. Runtime gate
  changes remain disallowed. Next A9 work is cross-validating on an expanded
  pairwise contract, especially more cross-action preference rows.
- 2026-06-21 follow-up: orchestrator now has the expanded pairwise
  cross-validation artifact:
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_pairwise_preference_contract_score_ordered.{jsonl,summary.json,summary.md}`
  and
  `offline_reward_pairwise_ranker_score_ordered_eval_summary.{json,md}`.
  The builder keeps the original `binary_label` mode as the default and adds an
  explicit `score_ordered` mode that orders rows with distinct offline oracle
  scores inside the same source-record group. This expands the prompt-free
  contract from `280` to `365` pair rows, contrastive groups from `103` to
  `133`, and canonical cross-action rows from `87` to `143` while preserving
  the no-runtime-gate policy. The expanded ranker still marks
  `pairwise_ranker_signal`; best family remains `random_forest` with mean
  accuracy/AUC `0.6552/0.7475` over five group-disjoint seeds. This is a
  coverage cross-check, not a promotion artifact. Next A9 work is to validate
  the signal on an independently held-out source-family/task-family split or
  collect more non-overlapping cross-action preferences before any downstream
  routing use.
- 2026-06-21 follow-up: orchestrator now has that independent held-out
  pairwise validation:
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_pairwise_ranker_score_ordered_holdout_summary.{json,md}`.
  The random group split still reports `pairwise_ranker_signal`, but the
  held-out source-family/suite check is mixed: `7/9` eligible holdouts pass and
  `2/9` fail. Blockers are `source_family:seeding_eval` (best
  `random_forest`, mean accuracy/AUC `0.5705/0.6289` over `156` test pairs)
  and `suite:livecodebench` (best `logistic_l2`, mean accuracy/AUC
  `0.5978/0.6750` over `92` test pairs). The top-level holdout decision is
  `mixed_holdout_signal`, runtime gate changes remain disallowed, and the next
  A9 step is targeted collection of non-overlapping cross-action preferences
  for those weak strata rather than downstream routing use.
- 2026-06-21 follow-up: orchestrator now has the targeted pairwise holdout
  expansion for the failed `suite:livecodebench` stratum:
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_pairwise_holdout_expansion_*`
  plus
  `offline_reward_pairwise_preference_contract_score_ordered_holdout_expanded.{jsonl,summary.json,summary.md}`
  and
  `offline_reward_pairwise_ranker_score_ordered_holdout_expanded_summary.{json,md}`.
  The new planner selects non-overlapping prompt-free source/role keys and
  found `778` livecodebench candidate rows across `209` candidate groups; a
  focused seeding-only diagnostic found no new non-overlapping `seeding_eval`
  candidates in the current artifact scan. The expanded pairwise contract grows
  to `889` pair rows, `512` cross-action pair rows, and `301` contrastive
  groups. Random group-disjoint eval strengthens to `pairwise_ranker_signal`
  with best `random_forest` mean accuracy/AUC `0.8525/0.9495`. Independent
  holdout remains mixed (`7/9` pass), but `suite:livecodebench` is repaired:
  best `logistic_l2`, mean accuracy/AUC `0.8807/0.9677` over `616` test pairs.
  Current blockers are `source_family:seeding_eval` and `suite:thinking`.
  Runtime gate changes remain disallowed.
- 2026-06-21 follow-up: orchestrator also ran the analogous targeted
  `suite:thinking` expansion:
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_pairwise_thinking_expansion_*`
  and
  `offline_reward_pairwise_ranker_score_ordered_hard_holdouts_expanded_summary.{json,md}`.
  The planner found `1,359` prompt-free thinking candidate rows across `363`
  non-overlapping groups, scored/exported them with target agreement `0.9360`,
  and rebuilt a `1,271`-pair score-ordered contract (`769` cross-action rows).
  This is a diagnostic null rather than a repair: random group-disjoint signal
  remains strong (`hist_gradient_boosting` mean accuracy/AUC `0.8121/0.9210`),
  but independent holdout worsens to `5/9` passing. `suite:thinking` still
  fails (`logistic_l2`, mean accuracy/AUC `0.5732/0.6770` over `410` test
  pairs), and new failures appear for `source_family:orchestrator_live_seed`
  and `suite:general`. Treat the livecodebench-expanded artifact as the better
  current A9 pairwise checkpoint; do not use the hard-holdout-expanded artifact
  for downstream routing.
- Seeding sidecar audit: the `seeding_eval` blocker is not a planner path
  mistake. Current seeding livecodebench files expose only frontdoor-family
  remaining groups after existing-manifest exclusions and missing-response
  skips, so they fail the cross-action gate. Repairing
  `source_family:seeding_eval` requires new or regenerated seeding data with a
  second canonical action for the same source-record groups.
- 2026-06-27 follow-up: orchestrator `10e5133b` prioritizes the expanded-gap
  collection queue after the 5-fold cross-validation pass. The planner now marks
  priority `0` source-family blockers
  `source_family:orchestrator_live_seed:architect_general>frontdoor`,
  `source_family:seeding_eval:architect_general>coder_escalation`, and
  `source_family:seeding_eval:architect_general>frontdoor`; priority `1` is
  `suite:general:architect_general>coder_escalation`; priority `2` remains
  lower-value direction-balance cleanup. The plan still allows no runtime gate
  change and still marks collection batches as unsafe during active AutoPilot
  because they consume live model slots. Next A9 action is the priority-0 live
  collection batch set in a clean/coordinated measurement window, then rebuild
  the pairwise contract and rerun holdouts.
- 2026-06-28 follow-up: orchestrator `926fd30b` turns that queue into a
  first-class guarded acquisition window instead of a prose-only runbook. The
  pairwise holdout planner can now emit
  `offline_reward_pairwise_collection_window.v1` manifests plus executable
  shell scripts with an active-AutoPilot refusal guard (`exit 75`). Current
  artifacts:
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_pairwise_expanded_gap_collection_manifest.json`
  and
  `orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/collect_offline_reward_pairwise_expanded_gap.sh`.
  The generated window contains `9` batches: the three priority-0
  source-family gaps, the priority-1 `suite:general` gap, and five lower-value
  cleanup strata. The collection still must run only in a coordinated window;
  the script refuses to run while AutoPilot is active because even
  `seed_specialist_routing.py --dry-run` consumes live model slots.
- 2026-07-04 follow-up: the clean-window A9 collection and same-record repair
  completed, and the guarded collection manifest is now exhausted
  (`status=no_runnable_batches`). The reference-token candidate-only contract
  remains below coverage (`32` pair rows / `32` cross-action rows), but the
  source-q-reward diagnostic built from the same `626` prompt-free candidate
  rows clears coverage (`180` / `180`) and the source-reward ranker diagnostic
  passes aggregate signal, 5-fold group-disjoint CV, and `3/3` eligible
  independent holdouts. The target is now preregistered in
  `offline_reward_source_reward_pairwise_target_contract.{json,md}` as
  `source_q_reward_passthrough`: an offline training target candidate only, not
  independent oracle evidence, with `runtime_gate_change_allowed=false`. Do not
  rerun the exhausted collector; any live use still requires a separate
  deployment gate.
- 2026-07-05 follow-up: research commit `955beb6` records a new quiet-window
  A9 audit-target collection for the remaining weak strata:
  `source_family:seeding_eval coder_escalation/frontdoor` (`28` questions),
  `suite:general architect_general/coder_escalation` (`20`),
  `suite:hotpotqa architect_general/frontdoor` (`20`), and `suite:simpleqa
  architect_general/coder_escalation` (`20`). The files live under
  `benchmarks/results/eval/` with timestamp `20260705T185704Z`, alongside the
  updated `seen_questions.jsonl`. Treat these as raw collection rows; the next
  A9 action is rebuilding/scoring the pairwise contract and rerunning the
  relevant holdout diagnostics, not another live collection pass.

## Research Intake Update — 2026-07-02

### Parked reference: tabular-FM candidate heads (TabPFN / TabFM / TabICL) for the routing head — evaluate only after the fable5 routing-freeze lifts

Zero-shot / in-context tabular foundation models are a candidate backbone for this routing/difficulty head (a tabular classifier over engineered request features), directly targeting the cold-start-on-model-swap pain (P4.1 / P5 / DAR-4 / DAR-5). PARKED — Phases 1.5+ are FROZEN per fable5-findings-02; investigation-only, not a phase/task.

- **[intake-744] TabICL** (arXiv 2502.05564, ICML 2025, credibility 5) — strongest candidate. First step is an **OFFLINE-ONLY bake-off** vs the numpy MLP on the existing routing dataset (batch accuracy / precision-at-coverage), explicitly NOT wired into the live per-request path. GPU-reliant; classification-only; feature-order sensitive.
- **[intake-734/745] TabPFN** (arXiv 2207.01848, Nature 2025) + **[intake-743] TabPFN-3** (arXiv 2605.13986) — small-data in-context prediction; GPU-recommended (CPU only ≲1k rows); TabPFN-3 is non-commercial-licensed and its no-GPU path (tabpfn-client) is SaaS → exclude. Documented **weakest under concept/distribution shift = exactly the cold-start regime** → any spike must validate under shift + test feature-order sensitivity.
- **[intake-735] Google TabFM** — the only **open-weight + CPU-runnable-in-principle** option (`google/tabfm-1.0.0-pytorch`); hard caps ≤10 classes / ≤500 features / ≤100k rows; the BigQuery `AI.PREDICT` path is SaaS → exclude. Open weights govern deploy; the API path does not.

**Double-gate before any build**: (1) fable5 routing-freeze exit AND (2) MI210/ROCm viability (all are CUDA/PyTorch; our numpy MLP is µs-CPU, these are batch-oriented). Do **not** inherit the stale "174K" label figure (live `episodic.db` ≈ 8k rows; 275,960-row `training_data.npz`). Per this file's own directive, do **not** file this under `decision-aware-routing.md` / `retrain-routing-models.md` (both expansion-FROZEN).

---

## P4.5 Phase A Outcome — 2026-06-26

**Status**: data extraction complete; MLP retraining blocked on BGE server (ports 8090/8091 offline).

**Script**: `scripts/graph_router/extract_journal_soft_labels.py` (new, committed 2026-06-26).

**Artifacts** (in `orchestration/reports/p45_soft_labels/`):
- `soft_labels.jsonl` — 540 per-qid soft-label records (qid, suite, role_correctness, soft_labels vector over 6 canonical roles, recommended_role)
- `suite_priors.json` — per-suite soft label priors for label smoothing on episodic training data
- `routing_analysis.md` — per-suite per-role correctness diagnostic
- `extraction_summary.json` — run metadata

**Data note on qid recovery**: The journal `question_results` stores only `qid` (a SHA256 hash of `suite::prompt_text`), not the prompt text itself. The question pool JSONL's hashes don't match — questions come from dynamic HuggingFace dataset loads at eval runtime. Question text recovery from qids is blocked without the original runtime HF samples. BGE embedding of question texts is therefore blocked as well. The `soft_labels.jsonl` dataset provides soft-label targets but NOT embeddings; Phase B requires BGE to embed the question texts (see below).

**STATISTICALLY ROBUST routing misses** (Wilson 95% CI, BOTH arms n≥20 — these are real, not sample-size noise):

| Suite | frontdoor | better route | gain | Interpretation |
|-------|----------:|--------------|-----:|----------------|
| cruxeval | 0% (n=22) | worker_general 87% (n=188) | **+87pp** | frontdoor cannot do code-output prediction; worker_general nails it |
| cruxeval | 0% (n=22) | coder_escalation 47% (n=74) | +47pp | (same suite, second-best route) |
| bigcodebench | 33% (n=165) | coder_escalation 69% (n=109) | **+36pp** | code-gen belongs on coder, not frontdoor |
| gpqa | 39% (n=245) | coder_escalation 65% (n=37) | **+26pp** | hard science reasoning → coder beats frontdoor |
| general | 84% (n=591) | architect_general 98% (n=48) | +14pp | small gap; architect is far costlier — cost-aware routing may correctly keep frontdoor |

**METHODOLOGY CORRECTION (2026-06-26)**: The first-pass analysis flagged `simpleqa` (4.9% fd → "100% architect") and `mode_advantage_hard` (→ "100% worker_general") as SEVERE routing misses. **Both were wrong — sample-size noise.** The "architect 100%" on simpleqa was n=1 (a single lucky draw). With Wilson CIs and n≥20 required on both arms, simpleqa drops out entirely. simpleqa scores ~5% across *every* route (worker_general 5.8% n=311, frontdoor 4.9% n=61, unknown 5.0% n=437) — this is a **capability/benchmark-difficulty ceiling**, not a routing problem. SimpleQA is obscure-factual-recall trivia ("Who received the IEEE Frank Rosenblatt Award in 2010?"); small quantized local models genuinely cannot answer it, and re-routing won't help (only a larger or RAG-augmented model would). This is exactly the `feedback_verify_test_method_before_calling_it_a_bug` + `feedback_eval_saturation_masks_model_gap` trap — verify sample size before calling a gap a defect.

**Genuinely actionable finding**: coding/reasoning suites (cruxeval, bigcodebench, gpqa) are being routed to frontdoor when coder_escalation/worker_general handle them far better, at comparable cost. The cruxeval result is the standout (0% → 87%). This is a real, cost-justified routing improvement candidate — but note it is **suite-level evidence from autopilot eval**, and production routing operates per-request without suite labels; the value is in the LRC learning these patterns from question *content*, which is exactly what Phase B (BGE-embedded soft-label retrain) would capture.

**Phase B — MLP retraining** (blocked on BGE):
1. Start BGE server (`orchestrator_stack.py start` → BGE server on port 8090)
2. Run `scripts/graph_router/embed_soft_label_dataset.py` (needs to be written) to embed the 540 qid-question-text pairs
3. Alternative (no BGE): apply `suite_priors.json` as label smoothing on existing episodic training data by classifying episodic memories by suite type (keyword heuristics or BGE similarity to suite representative questions)
4. Run `scripts/graph_router/train_routing_classifier_kl.py` (needs to be written) for KL-divergence MLP retrain
5. Decision gate: ≥1 pp val acc improvement → adopt

---

## P4.5 Phase B Outcome — 2026-06-26 (NULL RESULT)

**Status**: COMPLETE. Soft-label SFT does **not** improve routing over hard labels on the autopilot journal data. Decision: **keep hard-label (cross-entropy) training.** Scripts retained as reusable infrastructure for future, larger, less-polarized datasets.

**qid→text recovery unblocked**: The earlier "blocked" claim was wrong — I had used the wrong hash. The journal qid is `sha1(f"{suite}\x00{prompt}")[:16]` (SHA1 + null separator), NOT SHA256/`::`. With the correct hash, **1367/1382 journal qids (98.9%) and 540/540 soft-label records resolve** to question-pool text. No blocker.

**Pipeline run** (2 BGE servers on 8090-8091, `-c 2048 -np 4` for 512 tokens/slot):
1. `embed_soft_label_dataset.py` — resolved 540 qids → text, embedded via BGE (CLS pooling), built 1031-d features (1024 BGE + 5 task-type one-hot + norm_ctx_len + has_images, matching production RoutingClassifier). Output `soft_labels_embedded.npz`.
2. `train_routing_classifier_kl.py` — trained HARD (cross-entropy on argmax) and SOFT (KL divergence on full distribution) arms on the SAME 432-train/108-val split. KL gradient at logits is `(probs − soft_target)`, vs `(probs − one_hot)` for CE — only the target differs.

**Result (5-seed robustness, role-success accuracy = predicted role can actually solve the qid)**:

| seed | hard | soft | delta | adopt? |
|------|-----:|-----:|------:|--------|
| 1 | 53.7% | 53.7% | +0.000 | no |
| 7 | 49.1% | 49.1% | +0.000 | no |
| 13 | 51.8% | 51.8% | +0.000 | no |
| 42 | 53.7% | 52.8% | −0.009 | no |
| 99 | 55.6% | 55.6% | +0.000 | no |

Delta ≈ 0 across all seeds (gate was ≥+1pp). **Robust null.**

**Why null** (mechanistic, not a bug): role-success accuracy depends only on the *argmax* predicted role. By construction hard_label = argmax(soft_label), and on this data both training objectives converge to the same argmax decision boundary for essentially every val question — so the metric cannot distinguish them. Even at τ=2 (which produces genuinely soft targets, ~0.42 max mass for a polarized question), the extra probability mass KL spreads to non-dominant roles does not change which role wins. The signal that would make soft labels pay off — many questions where *multiple* roles are viable with meaningfully different success rates — is rare in the 540-record set (it is frontdoor-dominated: 415/540 argmax = frontdoor).

**This confirms the original caveat** (polarized stable core → soft ≈ hard), now with measurement rather than prediction.

**What would change the verdict** (future, not now):
- A much larger journal corpus with more genuinely-contested questions (multiple viable roles at different success rates).
- A different metric than argmax role-success (e.g. expected success under the predicted *distribution*, or cost-weighted role-success) — but that changes what "better routing" means and needs an operator decision.
- The genuine routing misses found in Phase A (cruxeval/bigcodebench/gpqa → specialist) are a *content* signal the LRC could learn directly; they don't depend on soft-vs-hard labeling. That remains the actionable thread, independent of this null.

**Artifacts**: `orchestration/reports/p45_soft_labels/{soft_labels_embedded.npz, kl_ab_report.json}`; scripts `scripts/graph_router/{embed_soft_label_dataset.py, train_routing_classifier_kl.py}`.

## P4.6 Role Dropout Outcome — 2026-06-27 (NULL RESULT)

**Status**: COMPLETE. The opt-in training augmentation landed, but the measured
dropout variants do **not** improve the current LRC training objective. Decision:
**keep current hard-label training**.

**Implementation**:
- Orchestrator `688c6076` adds `--role-dropout-rate`,
  `--role-dropout-min-roles`, and `--role-dropout-max-roles` to
  `train_routing_classifier_kl.py`.
- Dropout applies only to the SOFT/KL arm. It masks secondary positive target
  mass, protects the argmax role, and renormalizes, so one-hot hard-label rows
  remain behaviorally unchanged.
- Focused unit coverage verifies renormalization, one-hot no-op behavior, and
  invalid-parameter rejection.

**Offline A/B**:
- Dataset: existing `orchestration/reports/p45_soft_labels/soft_labels_embedded.npz`
  (`432` train / `108` val / `6` actions).
- Rates: `0.2` and `0.3`.
- Seeds: `42`, `43`, `44`, `45`, `46`.
- Gate: adopt only if dropout soft arm beats the hard arm by `>=+1pp`
  role-success accuracy.

| rate | runs | hard RSA | dropout RSA | delta | best delta | adopt runs |
|---:|---:|---:|---:|---:|---:|---:|
| 0.2 | 5 | 0.5296 | 0.5222 | -0.0074 | +0.0000 | 0 |
| 0.3 | 5 | 0.5296 | 0.5222 | -0.0074 | +0.0000 | 0 |

**Interpretation**: role dropout on label distributions alone does not create
the "available role subset" learning problem described by Conductor; the model
still receives the same prompt features and no availability mask. The current
soft-label data is also polarized, so protecting the argmax leaves the decision
boundary largely unchanged. If availability robustness is revisited, it should
use an explicit role-availability input/contract or a hard-label trainer variant
designed around masked candidate sets, not more retuning of this KL path.

**Artifacts**:
`orchestration/reports/p46_role_dropout/{summary.json,summary.md,rate_*_seed_*.json}`.
