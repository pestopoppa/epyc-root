# Deep Dive — AVB Offline Reward Stack (tiny CPU answer-quality oracle for routing)

**Date:** 2026-06-20
**Companion handoff:** [`handoffs/active/learned-routing-controller.md`](../../handoffs/active/learned-routing-controller.md)
**Intake entries:** intake-706, intake-716, intake-717, intake-719 (consolidated from four sibling entries into one actionable insight)
**Scope:** OFFLINE reward modeling only — no live-routing change, no live quality-gating
**Purpose:** Evaluate AVB's "offline reward stack" (a tiny CPU-runnable, reference-grounded answer-quality regressor + its training recipe, dataset, and a published checkpoint) as a candidate **independent quality-oracle label source** for the offline parts of the routing pipeline — specifically to produce a policy-debiased correctness label for the Phase-6 frontdoor verifier (handoff NEXT-A2 / NEXT-A3), and as a CPU-cheap alternative to enabling the disabled ClaudeAsJudge graded-reward path.
**Credibility:** null — all magnitude numbers below are the practitioner's self-reported figures from the repo/model/dataset cards, with **no protocol, n/reps, or attestation**. Per `MEASUREMENT.md` they are **observations** usable for hypothesis formation only, never to gate any keep/revert/deploy/promote decision. Verify against our own eval before relying on any of them.

---

## TL;DR

- The four intake entries are one stack: a **regression** reward model architecture (intake-706), the **training script / recipe** that produces it (intake-716), the **dataset** it trains on (intake-717), and a **published 22M checkpoint** (intake-719). Together they describe a tiny, CPU-friendly, *reference-grounded* answer-equivalence scorer.
- They land on a **real, currently-unfilled gap**: our live reward "quality" term is **binary** (success / partial / failure), and the only graded-quality path we have (ClaudeAsJudge) is **disabled**. A tiny MSE regressor that scores a response against a known reference is a plausible, CPU-cheap way to fill that gap.
- The use is strictly **OFFLINE**: a reference answer only exists in our seeding / eval path, never at live-routing time. So the proposed application is *label generation + eval-time scoring*, not a live router or live quality gate.
- The concrete hook is **handoff NEXT-A2 / NEXT-A3**: the frontdoor verifier (built, default-OFF) was trained on a Q/outcome label that is **policy-biased**. NEXT-A explicitly asked for "a policy-debiased `final_task_quality_score` from a quality oracle independent of the Q-update loop." A reference-grounded MSE scorer is a candidate for exactly that independent label.
- Do **not** propose this for `decision-aware-routing.md` or `retrain-routing-models.md` — both are expansion-FROZEN per fable5-findings-02.

---

## 1. The gap this fills (verified current state)

Our production reward signal for routing/RL is **binary-plus-cost**, not graded:

- `q_reward.py` (≈lines 47–52) maps an outcome to a small fixed ladder — `success = 1.0`, `partial = 0.3`, `failure = -0.5` — and then applies a cost penalty. There is no continuous answer-quality term.
- The only *graded* path in the codebase, **ClaudeAsJudge**, is **disabled**: `model_registry` sets `claude_as_judge.enabled: false`, and the chapter-08 docs list it under **Future Work**, i.e. it has never been the live scorer.

Consequence: anything downstream that wants a fine-grained "how good was this answer" signal — calibrating a verifier, debiasing a correctness label, ranking responses in eval — has nothing to read but a 3-level ladder. A tiny reference-grounded MSE scorer that runs on CPU is therefore (a) filling a genuinely empty slot, and (b) a cheaper alternative to standing up ClaudeAsJudge for the *offline* label-generation use. (It does **not** substitute for ClaudeAsJudge at live time — see §6, there is no reference at live time.)

---

## 2. The recipe (intake-706 + intake-716)

AVB's `finetuning_recipes` repo ships a `reward_models` module. Its design (as documented by the author):

- **Pointwise regression, not Bradley–Terry.** It does **not** rank a chosen-vs-rejected pair; it emits a single scalar quality score for one `(reference, response)` pair. Input is formatted as `"{reference} [SEP] {response}"` and the model is trained with **MSE** against a numeric target.
- **Tiny encoders, raw PyTorch.** Backbones are small sentence-transformers: `all-MiniLM-L6-v2` (≈22M params) and `distilbert-base-cased` (≈66M). No TRL / no RLHF framework — plain PyTorch. Both are CPU-trainable and CPU-servable, which is the whole point for our hardware.
- **Pooling + head (intake-716, the actual `train_reward_model.py`).** The encoder output is **meanmax-pooled** (concatenated mean and max pool), passed through dropout, then a single linear layer to a scalar head. Loss is MSE; training **early-stops on validation MSE**. The 1–5 rubric labels are **normalized to `[0, 1]`** for the target.
- **Two-stage finetune.** Encoder is **frozen first**, then the **last 3 encoder layers are unfrozen**, with **differential learning rates** — head at `5e-4`, encoder at `5e-5`.
- **Augmentation.** Two tricks: **contrastive minimal-edit** pairs (small perturbations that should change the score) and **synthetic-confound** augmentation (decoys engineered to look plausible but be wrong), aimed at making the scorer robust to surface similarity.

**Self-reported numbers (observations, not decision-gating):**

| Metric (author-reported) | MiniLM (22M) | DistilBERT (66M) | RewardBert baseline |
|---|---|---|---|
| Spearman correlation | ~0.718 | ~0.757 | 0.44 |
| Answer-equivalence ROC-AUC | ~0.94 | — | — |
| Confound resistance (% fooled, lower=better) | 8–12% | — | 53% |

These claim a large margin over a "RewardBert" baseline, but with no protocol/n/attestation. Treat as a hypothesis that the architecture *can* produce a usable scorer on the author's data — not as evidence it will on ours.

---

## 3. The dataset (intake-717)

`paper_answers_reward` — an `adopt_component` candidate (i.e. consider pulling it in directly, with verification):

- **22,423 rows** total — train **19,600** / test **2,780**, ~**17.8 MB** on disk.
- **Columns:** `orig_reference_answer`, `orig_response`, `orig_score` (the 1–5 rubric score).
- **Provenance caveat (load-bearing):** the dataset card does **not** document the judge, the rubric, or the source models that produced the scores. There is a *hint* in circulation that it is "~1,645 distinct responses across 18 models," but that is unverified. **Inspect the parquet directly before trusting any provenance claim** — what judge assigned `orig_score`, against what rubric, matters for whether these labels are a clean target or themselves a noisy LLM-judge artifact.

This is useful for **reproducing** AVB's reported numbers (a sanity check that we can hit ~0.72 Spearman on *their* data with *their* recipe), but it is **not** our distribution. The decision-relevant question is whether the recipe transfers to *our* seeding `(reference, response, score)` pairs — see §5.

---

## 4. The published model (intake-719)

`neuraltxt-reward-tiny` — a ready-made checkpoint:

- **22M MiniLM** backbone; a **reference-grounded answer-equivalence scorer** emitting a `0–1` score. This is the trained artifact of the intake-706/716 recipe — usable off-the-shelf for a quick smoke test before we invest in retraining.
- **Self-reported:** answer-equivalence ~**0.93**, confound resistance **6% fooled** (lower=better).
- **Reliability caveat (load-bearing):** **synonym-swap detection is only ~3% caught** — i.e. when a response is *correct but paraphrased* (synonyms substituted), the model frequently fails to recognize equivalence and scores it **low**. This is a direct false-negative risk: a correct, reworded answer would be penalized. Any adoption must stress-test paraphrase/synonym robustness explicitly (see §5), because for our routing labels a paraphrase-blind scorer would inject systematic noise against verbose or reworded specialist outputs.

---

## 5. Proposed offline evaluation (the actual experiment)

This is a candidate experiment, **not** an authorized run. It touches no live path; it is pure offline label-generation + eval.

1. **Reproduce.** Train the intake-706/716 recipe on the intake-717 `paper_answers_reward` data (or load the intake-719 checkpoint) and confirm we land near the author's self-reported Spearman (~0.72 MiniLM / ~0.76 DistilBERT). Pure sanity check that the recipe runs and the artifact behaves as described. CPU-only, minutes-scale.
2. **Retrain on our distribution.** Re-run the same recipe on **our** `(reference, response, score)` pairs harvested from the seeding/eval path — `seed_specialist_routing.py` outputs and the `debug_scorer` expected-fields are where references actually live in our system. Targets come from whatever graded label we can assemble offline.
3. **Gate vs the binary baseline.** Score the same held-out responses with (a) the trained scorer and (b) the live binary `q_reward` ladder. Report **Spearman / rank-agreement of the scorer against the graded ground truth, and its agreement vs the 3-level binary term**. The bar to clear: the scorer must add fine-grained signal the binary ladder cannot (e.g. separate two "partial" outcomes the ladder collapses).
4. **Paraphrase / synonym stress test (mandatory).** Given the intake-719 ~3%-synonym-detection caveat, explicitly construct a paraphrase-correct vs verbatim-correct split and measure how often the scorer wrongly penalizes the paraphrase. If it systematically under-scores correct-but-reworded answers, that disqualifies it as a quality oracle for our (often verbose) specialist outputs — or forces a paraphrase-augmentation stage on top of the recipe.
5. **Confound stress test.** Reproduce the author's confound-resistance check on our data (plausible-but-wrong decoys) to see whether the claimed 6–12% fooled rate holds on our distribution.

**Decision shape:** if the scorer beats the binary ladder on rank-agreement with graded truth **and** survives the paraphrase + confound stress tests, it becomes a candidate offline quality-oracle label source for the verifier debiasing below. If it fails the paraphrase test, record the null and stop — a paraphrase-blind oracle is worse than the honest binary ladder.

All numbers produced by this experiment would be **observations** until run under a codified recipe with operator approval, per `MEASUREMENT.md` / `MEASUREMENT_POLICY.md`.

---

## 6. OFFLINE-only constraint — why this is not a live-routing change

There is **no reference answer available at live-routing time.** The live chat pipeline (`chat_pipeline`) carries no `expected_answer` plumbing — references exist only in the **seeding/eval** path (`seed_specialist_routing.py`, the `debug_scorer` expected-fields). A *reference-grounded* scorer is, by construction, only computable where a reference exists.

Therefore the only viable use is **offline**:

- **Offline quality-oracle label generation** — producing a graded `final_task_quality_score`-style label on seeding/eval data, to train or recalibrate downstream heads.
- **Offline eval scoring** — a finer-grained answer-quality readout in eval than the binary ladder.

It is explicitly **not** a live router, **not** a live quality gate, and **not** a replacement for ClaudeAsJudge at inference time (ClaudeAsJudge is reference-free; this scorer needs a reference). This boundary is the single most important framing of the whole stack.

---

## 7. Anchor: handoff NEXT-A2 / NEXT-A3 (the frontdoor verifier debiasing)

The live anchor in [`handoffs/active/learned-routing-controller.md`](../../handoffs/active/learned-routing-controller.md) is **Phase 6 → P6.2 → NEXT-A2 / NEXT-A3** (NEXT-A itself is closed / superseded — do not re-touch its body text).

- The Phase-6 **frontdoor verifier** (~68k params, built, staged behind the default-OFF `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE`) was trained on a **Q-value / outcome correctness label** that the handoff repeatedly flags as **policy-biased** — it learns "good routes *per the current policy*," not "good routes in absolute terms."
- NEXT-A's open ask (recorded at P6.2's "NEXT-A" recommendation) was precisely: *train a policy-debiased correctness label from `final_task_quality_score` produced by a **quality oracle independent of the Q-update loop**.*
- The AVB reference-grounded MSE scorer is a candidate for **exactly that independent label**. Trained on `(reference, response)` from the seeding/eval path and *not* derived from the Q/TD-update loop, it is independent of the policy that the verifier is trying to defend — which is the property NEXT-A required. NEXT-A3's "defer until data-infrastructure refresh" path is the natural place to fold this in: when the post-`--repair-embeddings` data is re-extracted, an AVB-scored quality label could ride alongside the outcome label as the debiased target.

This is a **candidate label source for an existing, scoped task** — not a new phase, not a new handoff, not a live-behavior change.

---

## 8. Frozen-handoff guardrails

Two sibling handoffs are **expansion-FROZEN** per fable5-findings-02 (2026-06-12; the DAR-1 replay showed 0.00% identifiable regret, so expansion is gated on a future ≥5% regret signal):

- `decision-aware-routing.md`
- `retrain-routing-models.md`

**Do not** propose the reward model as new work under either. The only live home for this insight is the offline-label / verifier-debiasing slot under `learned-routing-controller.md` (NEXT-A2/A3), which is ACTIVE for the verifier rollout decision and not under the routing expansion freeze.

---

## 9. Dropped cross-reference (correction)

An earlier draft cross-linked the recipe's internal **meanmax pooling** (§2) to the handoff's open **P4 / P6 pooling question**. That is wrong and is dropped: P4.1's pooling ablation is about **BGE input pooling** (CLS vs mean vs last for the routing *embedding*), and P4.1.3 is an **IRT-feature audit**, not a pooling question. The reward model's meanmax pooling is an internal detail of a *separate, offline* MiniLM/DistilBERT scorer and has nothing to do with the BGE input-pooling ablation. No cross-ref between the two.

---

## 10. Summary of caveats (all load-bearing)

1. **All magnitude numbers are self-reported observations** — no protocol, never decision-gating.
2. **Dataset provenance (intake-717) is undocumented** — verify the parquet's judge/rubric/source-models before trusting `orig_score` as a clean target.
3. **Synonym-swap blindness (intake-719, ~3% caught)** — a paraphrase-correct answer can be scored low; mandatory paraphrase stress test before any adoption.
4. **OFFLINE-only** — no live reference, so no live-routing or live-gating use.
5. **Frozen handoffs** — not a proposal for decision-aware-routing / retrain-routing-models.
6. **Policy-bias is the point** — its value is as an *independent* (non-Q-loop) label for NEXT-A2/A3 verifier debiasing.
