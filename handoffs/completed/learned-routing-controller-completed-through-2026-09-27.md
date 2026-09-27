# Learned Routing Controller — completed history through 2026-09-27

Historical ledger only; current work lives in [`../active/learned-routing-controller.md`](../active/learned-routing-controller.md).

Split out at the operator-invoked wrap-up of 2026-09-27 (ak-ds41-main). The block holds the research-intake updates
of 2026-04-26 to 2026-07-02, the 2026-06-21 implementation checkpoint, and the P4.5 Phase A/B and P4.6 role-dropout
outcomes (both NULL). None of it carries an open task. The active handoff's *Deep-Dive Correction — 2026-07-21* keeps
the synthesis of the five-null streak. Moved verbatim.

---

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
  - ⚠ Caveat 2026-09-17 (sub-scorer-fix): the `suite:livecodebench` preference labels are score-ordered
    from livecodebench results recorded 2026-06, when the suite's only live oracle was
    `substring 'def '`, which any Python answer passes
    (`autopilot-continuous-optimization.md`, 2026-08-12 and 2026-09-17 notes). So this stratum's
    "repair" rests on labels with no correctness signal. Do not use it as evidence for routing until
    it is re-labelled against the executable oracle.
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
- 2026-07-05 fold outcome: the `20260705T185704Z` live rows were folded through
  the offline A9 post-collection workflow as timestamped orchestrator artifacts.
  The planner selected `162` prompt-free candidates across `81` source-record
  groups and matched all four collection targets. The independent
  `reference_token_coverage` scorer produced `162` rows with mean score
  `0.7025` and target agreement `0.9506`, but the candidate-only pairwise
  contract still lacks within-task contrast: binary-label pairing has only `3`
  cross-action pairs and score-ordered pairing has only `6`, both below the
  `100` total / `50` cross-action gate; ranker diagnostics have no eligible
  holdouts. The source-q-reward diagnostic from the same fresh rows has `43`
  cross-action pairs, also below gate. The A9 blocker is therefore acquisition
  design, not unprocessed rows: next collection must force same-task
  cross-action disagreement and direction balance for the still-weak strata;
  do not rerun the same collector or retune the current ranker family.
- 2026-07-05 contrast-aware replan: orchestrator `ee96e423` fixes that
  acquisition-design bug in
  `plan_offline_reward_pairwise_holdout_expansion.py`. Collection targets are
  now considered satisfied only by source-binary directional contrast, while
  row presence is reported separately. Replaying the `20260705T185704Z` live
  slice now reports `81` presence groups but only `2` target-satisfying
  contrast groups, so it emits a new guarded four-batch manifest:
  `offline_reward_pairwise_audit_target_live_20260705T185704Z_contrast_replan_20260705T202257Z_collection_manifest.json`
  plus the matching `_collect.sh`, `_summary.{json,md}`, and `_candidates.jsonl`
  artifacts. The validator has no schema warnings and is blocked only by active
  AutoPilot. Next A9 action is to run that manifest in a clean window and then
  execute the embedded post-collection rebuild/scoring pipeline.
- [x] **A9 contrast-replan guarded collection executed** ✅ 2026-07-07.
  Research timestamp `20260707T015010Z` writes the four expected live batch
  JSONs plus checkpoint JSONLs under
  `epyc-inference-research/benchmarks/results/eval/`. Batch summaries:
  `seeding_eval coder/frontdoor` deduped to the shared backend and scored
  `16/26`; `general architect/coder` scored `16/19` vs `13/19`; `hotpotqa
  architect/frontdoor` scored `18/20` vs `17/20`; `simpleqa architect/coder`
  scored `6/20` vs `6/20`. Rewards injected remained `0`. The remaining A9
  work is to rebuild/score the pairwise contract on these rows and decide the
  next acquisition design; these raw rows are not promotion evidence.

## Research Intake Update — 2026-07-02

### Parked reference: tabular-FM candidate heads (TabPFN / TabFM / TabICL) for the routing head — evaluate only after the fable5 routing-freeze lifts

Zero-shot / in-context tabular foundation models are a candidate backbone for this routing/difficulty head (a tabular classifier over engineered request features), directly targeting the cold-start-on-model-swap pain (P4.1 / P5 / DAR-4 / DAR-5). PARKED — Phases 1.5+ are FROZEN per fable5-findings-02; investigation-only, not a phase/task.

- **[intake-744] TabICL** (arXiv 2502.05564, ICML 2025, credibility 5) — strongest candidate. First step is an **OFFLINE-ONLY bake-off** vs the numpy MLP on the existing routing dataset (batch accuracy / precision-at-coverage), explicitly NOT wired into the live per-request path. GPU-reliant; classification-only; feature-order sensitive.
- **[intake-734/745] TabPFN** (arXiv 2207.01848, Nature 2025) + **[intake-743] TabPFN-3** (arXiv 2605.13986) — small-data in-context prediction; GPU-recommended (CPU only ≲1k rows); TabPFN-3 is non-commercial-licensed and its no-GPU path (tabpfn-client) is SaaS → exclude. Documented **weakest under concept/distribution shift = exactly the cold-start regime** → any spike must validate under shift + test feature-order sensitivity.
- **[intake-735] Google TabFM** — the only **open-weight + CPU-runnable-in-principle** option (`google/tabfm-1.0.0-pytorch`); hard caps ≤10 classes / ≤500 features / ≤100k rows; the BigQuery `AI.PREDICT` path is SaaS → exclude. Open weights govern deploy; the API path does not.

**Double-gate before any build**: (1) fable5 routing-freeze exit AND (2) MI210/ROCm viability (all are CUDA/PyTorch; our numpy MLP is µs-CPU, these are batch-oriented). Do **not** inherit the stale "174K" label figure (live `episodic.db` held 64,396 routing rows on 2026-09-26 — the earlier "≈ 8k" reading is stale; 275,960-row `training_data.npz`). Per this file's own directive, do **not** file this under `decision-aware-routing.md` / `retrain-routing-models.md` (both expansion-FROZEN).

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

---
