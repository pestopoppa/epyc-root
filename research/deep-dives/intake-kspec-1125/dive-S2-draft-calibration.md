# S2-draft-calibration: draft temperature scaling (intake-2964) with TreeSpark (intake-2975) and ForeSpark (intake-2976)

Dive date 2026-11-25. Session intake-kspec-1125. Lane head f19b902. Hardware-agnostic (math and serving-logic question).
Read depth: intake-2964 FULL (86,836 chars, all of it). intake-2975 read through §6 (≈66k of 75k; unread = reference list, appendices).
intake-2976 read abstract, §2-§5, §7.1-7.6, App. B (≈45k of 102k; unread = §8-10, other appendices). The two expansion entries
are PARTIAL on depth, but every claim_anchor sits in a read section.
No compute, no server, no git write. No WebSearch used (papers are days old; no replication could exist).

## Headline

1. The draft-temperature idea is lossless and costs nothing. But **our own offline replay already tested the same lever on the
   retained 27B DFlash2 capture and closed it**: SPEC-DRAFT-SHARPEN, 2026-11-24, verdict CLOSE (`handoffs/active/speculative-decoding.md:L2552-L2555 @ f19b902`).
   Per-T sharpening scale 0.5-1.5 on the selector scores gave holdout V*/V0 = 1.0000 at T0.3 and 1.0047 scale-only (1.0070 with truncation) at T1.0.
   The paper's 5-10% does not carry over to this stack.
2. The lever is a no-op under greedy (T=0) target verification, which is how Q38FN runs. The Q38FN acceptance drop (0.795 to 0.751) under
   ROWEXACT is a target batch-invariance effect, not a draft-calibration gap.
3. Only one served drafter even has a draft distribution at T>0: DFlash2. MTP and the other drafters verify by sample-and-compare, which is
   the paper's T_d=0 (point mass) case by construction.
4. The brief calls SPEC-DISTS-TRUNC a "top-k truncation". It is not. In C21 it truncates the list of per-position draft distributions to the
   capped draft length (`common/speculative.cpp:3155-3163`, call at `:3594-3600` @ 98ff8a4). The vocabulary/sampler truncation lever is the "trunc" arm of SPEC-DRAFT-SHARPEN.
5. TreeSpark and ForeSpark do not bear on intake-2964. Their "calibration" is of acceptance estimates, not the sampling distribution. They
   neither corroborate nor contradict it. Neither shows a gain that applies at np<=2 on our hardware.

## Q1. Is draft temperature lossless? Does it matter under greedy?

- Lossless: yes. The paper states it directly: calibration "preserves the lossless property ... as long as the calibrated distribution q is
  employed consistently in drafting and rejection sampling stages" (§2). The accept rule is min(1, p/q) with residual max(0, p-q); q is only the proposal law.
- Our verify uses exactly that: `common_sampler_spec_reject_step` accepts when `u * q_draft <= p_draft` and resamples from max(0, p - q)
  (`common/sampling.cpp:L1036-L1110` @ 98ff8a4). Any q works if the draft token was sampled from that same q.
- Greedy (T=0): the draft takes the argmax of the scores (`common/speculative.cpp:L1831-L1836`), the verify compares argmax, and argmax is invariant to temperature. So a draft temperature changes nothing at T=0.
- Which served modes can it matter in: only sampled (T>0) DFlash2 on 27B. In C21, `common/speculative.cpp` pushes a draft distribution only in the
  DFlash2 branch (`:L1788-L1830`); the other `dists` mentions are clears (`:1894`, `:2035`) and the cap helper. For MTP and the rest, `spec_dists.size() != spec_draft.size()`
  so `server-context.cpp:L5546-L5555` and `:L6530-L6536` take the sample-and-compare call. A deterministic draft with sample-and-compare has accept probability p(draft), identical to rejection with a point-mass q. That is the paper's T_d=0.
- Paper regime (important): every number was measured at **target T_t=1, top_p=1, top_k unrestricted** ("We disable sampling truncation (top_p=1, top_k=-1)", App. A.1; "target temperature is 1, top-p is 1, top-k is unrestricted", A.4). Our served T is 0.3 or 1.0 with top_k 20, top_p 0.95, min_p 0.05 (capture header, `dice.v1`). Truncation sharpens p, which shrinks the very underconfidence gap the paper corrects. That is a mechanism hypothesis, not tested here.
- Table numbers read: Table 1 accepted length gains 8.82-10.89% (nine rows); throughput gains 5.13% to 22.08% (DSpark C=64, standard error 5.64 points). Table 2 (DeepSeek-trained Qwen3-14B drafters): +2.05% EAGLE-3, +0.10% DFlash, 0% DSpark. That is the "near-zero" table. Calibrating temperatures were chosen on a replay (0.4, 0.4, 0.6), frozen, then tested on held-out requests, 3 seeds.

## Q2. C21 code: is there a draft-temperature knob?

Absent as an independent knob. Present as an implicit coupling: draft temperature equals the target request temperature.
- `tools/server/server-context.cpp:L4736-L4739` passes `/* .temperature = */ slot.task->params.sampling.temp` into the draft params. There is no separate draft-temp field (`common/speculative.h:68` has one `temperature`).
- `common/speculative.cpp:L1812-L1830` (DFlash2): `dist.probs[k] = exp((scores[k]-max)/dp.temperature)`, normalised over the `selector_top_k` candidates (K=16 in the capture; read from GGUF meta `dflash.selector_top_k`, `:1417-1419`). So q is softmax(score/T_target) over 16 ids, and mass outside the 16 is zero. The draft token is then sampled from that q (`:L1826-L1828`).
- The scale arm of SPEC-DRAFT-SHARPEN is q = softmax(scale*score/T), equivalent to T_d = T/scale. Implementing a knob would be one multiplier at `:1820`. Cost: trivial. Value: measured ~0 (below).
- SPEC-DISTS-TRUNC (what it really is): `common_speculative_cap_draft` resizes `dists` together with the draft when n-max caps it (`:3155-3163`; caller `:3594-3600`), so the verify gate `spec_dists.size()==spec_draft.size()` still holds. In-house A/B was NULL in all four cells (L2540). It is a correctness fix, not a calibration lever.
- Residual and accept use the 16-candidate q (`sampling.cpp:L1048-L1055` builds `q_probs` from `ids/probs`; tokens outside get q=0).

## Q3. Can the retained DICE capture replay a draft-temperature sweep offline with zero GPU?

Yes, and it has been done. What the capture must hold: the raw draft scores (not just probabilities), and the target's post-sampler row at every verified node.
- 27B DFlash2 capture (`ak-dice-capture-27b-dflash2-gpu-20261123-r2`, 192 units, 7499 rounds, all `verify: rejection`, L2541): each `dice.v1` round record carries `lat_tok` (D x K token ids), `lat_sc` (predecessor-conditioned RAW selector scores), `chain`, `ck`, `nodes`, and `rows` (target post-sampler (id, prob) at each verified node). I checked a record on disk: keys `lat_tok, lat_sc, nodes, rows, chain, ck, top_k, top_p, min_p, T`. Because raw scores are stored, any T_d is recoverable as softmax(score/T_d). No need for draft logits over the full vocabulary: the served q is already limited to the 16 candidates.
- The replay exists: `scripts/kernel_rnd/dice_replay/draft_sharpen_replay.py`, predeclared in `PREDECLARATION_DRAFT_SHARPEN.md` (research eef7c25a1). It computes per-position 1-TV along the realized chain, the same estimator the paper calls L_pos.
- Its baseline check passed: replay vs realized acceptance 1.0029 / 1.0044 / 0.9864 at T0.1 / 0.3 / 1.0, all within 2%. (The paper's own replay-vs-online mean error is 1.83-2.64%, max 8.72%, App. B.2, so our validation is at least as tight.)
- Limitation both share: the replay holds the drafted chain fixed, but a different q would draft a different chain. That is an approximation, not a fix we can apply from this capture. The superset-tree rows partly cover nearby chains but not arbitrary re-draws.
- Result (L2555): fit T1.0 best scale-only 1.3 (T_d about 0.77), holdout scale-only 1.0047 [1.0024, 1.0071]; T0.3 best scale 1.0, nothing. Verdict CLOSE.
- Gap vs the paper's optimum: the paper's best T_d is 0.4-0.6 at T_t=1 (scale 1.7-2.5). Our grid stopped at scale 1.5. But our T1.0 calibration optimum was interior (1.3), so the curve had already turned; the paper also reports curves "approximately unimodal". Widening the grid is not worth a box.
- A3B MTP capture (`ak-dice-capture-a3b-mtp-cpu-20261123-r2`): records carry `mtp_top`, the top-10 (id, logit, prob) per drafted depth, with `verify: sample_compare`. I read the first record on disk: top-1 prob is 0.9993 / 0.9997 / 0.9966 / 0.9977 at depths 1-4, so MTP is already near-sharp. Whether softening MTP (T_d>0) helps is the open direction (opposite to the paper's sharpening). That could be replayed from `mtp_top`, CPU only. It would also need a served MTP q, which C21 does not produce (build cost, not a decline reason).

## Q4. TreeSpark and ForeSpark

TreeSpark (intake-2975):
- Its "calibration" is a Platt map on edge acceptance: p_hat = sigmoid(a*logit(q0)+b), a=0.67, b=-0.46 (Qwen3-4B), fitted on greedy-match labels of ancestors-accepted edges (held-out ECE 0.0105). It is used to rank and stop tree growth. **Sampling still draws from q_T, T = target T**, and the paper says feeding q_T to the calibrator breaks it. So it is not draft temperature scaling and has no T_d knob.
- Direction note: raw q0 overestimates greedy-match (mean prediction 0.622 vs realized 0.498). Intake-2964 says drafters are underconfident versus the target distribution at T=1. These are different estimands (probability of matching the target argmax vs distribution overlap), so no contradiction; do not cite one as support for the other.
- Load-adaptive shrink: verify cost on A100 is flat for 1 to 56 nodes at bs<=4 (34-38 ms) and 7.3x at bs=64. A price ladder theta*(bs,T) selects the chain when no tree wins. At bs=16 and T>0 no branching tree beat the chain ("no branching tree was faster than the chain", §4/§5.5). At bs=1, sampled-tree gain was +3.0-3.4% at T=1 and +6.1% at T=0.5 in interleaved A/B; the headline "8-14% faster" (Table 4, +14/+8/+10%) is vs a cache-free target-only decoder in a Python harness.
- Relevance to np=1 vs np>1: it corroborates our parked sampled-tree result (27B V1/V0 1.02-1.07 against break-evens 1.10-1.34, L2541). Their flat-verify-cost premise does not hold on our 27B GDN stack beyond W8 (implied round-cost ratios 1.007 / 1.235 / 1.319 at T8/T12/T16, L2541). Not a new lever; it is the DTREE-GDN-BATCH reopen trigger restated.
Correction 2026-11-25 (status audit): the "monitor until DTREE-GDN-BATCH reopens" routing for TreeSpark (intake-2975, KS-S2-draft-calibration-4, M2 trigger b) rested on the premise that trees are parked. That was wrong at write time: the C21 sampled tree (V2 RRS) was already KEEP at official T1 (row ak-c21-tree-official-gpu-20261124: T10 1.0303 [1.0223,1.0433], T16 1.0352 [1.0189,1.0614]; progress/2026-11/2026-11-24-handoff-df2.md:45). The DTREE-GDN-BATCH box is open pending the C20 fold decision (its GDN row is KEEP, 3.619 ms), not parked. New disposition: fold TreeSpark's edge-acceptance Platt calibration and load-adaptive shrink-to-chain in as arms of DTREE-HEADROOM-REPLAY (handoffs/active/speculative-decoding.md) instead of a monitor. History above is kept unchanged.

ForeSpark (intake-2976):
- Its "calibration" is per-position temperature (theta_j) on the acceptance-estimator logit (post-draft) and scale+bias per entry of the pre-draft estimator, fitted on greedy Alpaca traces (App. B). "Temperature" there is not a sampling temperature. Name collision: a reader could wrongly cite it for intake-2964.
- Estimator: a one-hidden-layer net (r=256) from the target's context feature at the anchor plus the anchor embedding, predicting acceptance for every draft length before drafting. Joint scheduler: concave envelope plus one global sort (88 microseconds at 192 requests).
- Gains are at high load on 8-way tensor parallel H100/B200: up to 1.77x over DSpark on Qwen3-14B decode-only, 1.40x and 1.34x on the GLM models; at load 1 it is 1.15 / 1.07 / 0.96x (decode) and 1.11 / 0.98 / 0.98x (end-to-end). At temperature 1.0 the gain over DSpark is 1.76x.
- Our regime: DFlash2 drafter is 14.7% of the round and its GEMMs 6.7% (`handoffs/active/speculative-decoding.md:L1242, L1251 @ f19b902`, Q8MF-DRAFTER-SHARE). ForeSpark's saving comes from drafter work being up to 40% of step time and 75% discarded at load 512 (3.77 of 15 kept). At np 1-2 that is not our situation. Does not transfer at np<=2; unknown at np>=8 (we do not serve it).
Correction 2026-11-25 (status audit): the served 27B DFlash2 runs at np4, not np1-2 as the ForeSpark lines above state. The conclusion is unchanged: the drafter is 14.7% of the round and np<8, so ForeSpark's gain regime is not ours.

Corroborate or contradict 2964? Neither. TreeSpark and ForeSpark both use the target T as the draft T and do not study T_d. The only independent evidence on T_d remains our own replay, which says ~0 for DFlash2 under truncated serving T.

## Per-claim verdicts

| Entry | # | Claim (short) | Verdict | Locator |
|---|---|---|---|---|
| 2964 | 0 | Open drafters rank top-1 well but are underconfident | PARTIAL | §4.2; DeepSeek-trained exceptions Table 2 / B.1; measured only at T_t=1 untruncated |
| 2964 | 1 | One T_d<1 gives ~5-10% accepted length | PARTIAL | §5.1, Table 1; regime T_t=1, no truncation; our 27B replay +0.47% max |
| 2964 | 2 | Dirichlet/diagonal add little | CONFIRMED | §5.2.2, Table 3 |
| 2964 | 3 | Token-adaptive head does not beat global T | PARTIAL | Table 4: DFlash heads 4.1091 vs 4.0751 (+0.83%); EAGLE-3 +0.07-0.24%; DSpark -0.13% |
| 2964 | 4 | Chain drafting only | CONFIRMED | §2 |
| 2975 | 0 | Parent-conditioned dist from Markov head, calibrated to edge acceptance | CONFIRMED | §3.4 Eq.1, Eq.3 |
| 2975 | 1 | Beats DDTree at equal budget and a tuned chain | PARTIAL | Table 2 (+9-16% over DDTree, greedy) confirmed; over chain only at bs=1; parity at bs=16 sampled |
| 2975 | 2 | Load-aware policy shrinks to chain | CONFIRMED | §4, Table 1, Fig 2-3 (A100, T=0 cost model; sim excludes drafter cost) |
| 2975 | 3 | Lossless at any temperature | CONFIRMED | §3.3 Prop 1; TV 0.047 vs 0.46 control, one position |
| 2976 | 0 | Drafting large share at load; most discarded | CONFIRMED | Abstract, §2 (up to 40%; 3.77 of 15 kept at load 512) |
| 2976 | 1 | Work-conserving joint budgets per request | CONFIRMED | §5.2-5.4 |
| 2976 | 2 | vLLM prototype beats DSpark and AR | PARTIAL | §7.2: peak at high load; load 1 is 0.96-1.15x; TP8 H100/B200 |

Counts: C = 6, P = 6, O = 0, NF = 0.

## Principles table

| Principle | Source evidence | MI210 (gfx90a) verdict | EPYC Zen 5 verdict | Why (mechanism) | Port cost |
|---|---|---|---|---|---|
| Draft temperature T_d<T_t sharpens q, lossless | 2964 §5.1, Table 1 | DOES-NOT-TRANSFER (27B DFlash2 sampled; replay CLOSE, <=+0.47%) | DOES-NOT-TRANSFER at greedy (argmax invariant); UNKNOWN-NEEDS-PROBE for A3B MTP softening | Our target is truncated (top_k 20, top_p .95, min_p .05) and q is on 16 selector ids; paper gap measured untruncated at T_t=1 | Knob is one multiplier at `speculative.cpp:1820`; no value |
| Draft T is a no-op under greedy | 2964 §2 (accept rule); math | ALREADY-PRESENT (argmax path `:1831-1836`) | ALREADY-PRESENT | Accept compares argmax; temperature never changes argmax | none |
| Dirichlet / diagonal scaling | 2964 Table 3 | DOES-NOT-TRANSFER | DOES-NOT-TRANSFER | Paper shows no gain over scalar T | n/a |
| Token-adaptive temperature head | 2964 Table 4 (<=0.83% vs scalar; token oracle +16-17%) | DOES-NOT-TRANSFER | DOES-NOT-TRANSFER | Learned heads failed to reach the oracle; training-heavy is not the reason, the measured gain is | n/a |
| Offline trajectory replay for screening | 2964 §5.2.1, B.2 (1.83-2.64% mean error) | ALREADY-PRESENT (dice_replay family) | ALREADY-PRESENT | Same per-position 1-TV estimator; ours validated within 1.4% | none |
| Edge-acceptance Platt calibration for tree stopping | 2975 §3.4 (a=0.67, b=-0.46) | UNKNOWN-NEEDS-PROBE (only if tree track reopens) | not applicable (no drafted trees on CPU) | Absolute scale matters for a stop threshold, not for ranking (+0.03-0.04 tau only) | two scalars; needs greedy match labels from a tree run |
| Load-adaptive tree shrink to chain | 2975 §4 | TRANSFERS-WITH-CHANGES | DOES-NOT-TRANSFER | Our 27B verify cost rises past W8 already at np=1 (1.007 / 1.235 / 1.319) | needs DTREE-GDN-BATCH first |
| Pre-draft acceptance estimator + joint draft/verify budget | 2976 §5.2-5.3 | DOES-NOT-TRANSFER at np<=2 | DOES-NOT-TRANSFER | Drafter is 14.7% of our round; their win is drafting cost at high load | moderate; no gain at our np |

## In-house comparison (pinned)

- `handoffs/active/speculative-decoding.md:L2521-L2549 @ f19b902`: DICE capture and replay. 27B capture 192 units, 7499 rounds all rejection, sample_compare 0 with SPEC-DISTS-TRUNC; replay V0 reproduces served acceptance within 1%; sampled tree PROJECTED_LOSS. SPEC-DISTS-TRUNC A/B NULL (L2530, L2540).
- `:L2552-L2555`: SPEC-DRAFT-SHARPEN CLOSE (the direct answer to intake-2964).
- `:L966-L975`: Q38FN ROWEXACT: lossless at greedy, spec -14%, acceptance 0.795 to 0.751 (block 0). The acceptance drop is a target-logit batch-invariance effect at T=0; draft temperature cannot touch it.

## Derived-actionables ledger

| ID | Action | Disposition |
|---|---|---|
| KS-S2-draft-calibration-1 | Cite SPEC-DRAFT-SHARPEN as the in-house result for intake-2964. Do not carry the paper's 5-10% to our stack. | knowledge-only |
| KS-S2-draft-calibration-2 | Offline CPU replay of A3B MTP draft softening from `mtp_top` (top-10 logits, sample_compare capture). Zero GPU. Stop on futility if best T_d gain upper CI < 1.02. Only on a keep would a served MTP q be built. | immediate (small expected value) |
| KS-S2-draft-calibration-3 | Record the SPEC-DISTS-TRUNC vs SPEC-DRAFT-SHARPEN-trunc naming split so the two are not conflated again. | immediate (wiki note) |
| KS-S2-draft-calibration-4 | TreeSpark edge-acceptance calibration and price ladder: attach to DTREE-GDN-BATCH reopen criteria. | monitor |
| KS-S2-draft-calibration-5 | ForeSpark pre-draft estimator: no action at np<=2. | decline (reason: measured drafter share 14.7%, not 40%) |

## Dive-surfaced sources

None ingested. Identifiers read literally in the sources (arXiv:2607.05147 DSpark; arXiv:2608.02123 PCTree; arXiv:2607.08642 DominoTree; arXiv:2606.18394 JetSpec) are already adjacent to intake-738 or are tree-drafting variants; none settles draft temperature. Recommend decline for dive; PCTree (2608.02123) is the only candidate if the tree track reopens.

Correction 2026-11-25 (status audit): the "monitor until DTREE-GDN-BATCH reopens" routing for TreeSpark (intake-2975, KS-S2-draft-calibration-4 / KS-S2-4, M2 trigger b) rested on the premise that trees are parked. That was wrong at write time: the C21 sampled tree (V2 RRS) was already KEEP at official T1 (row ak-c21-tree-official-gpu-20261124: T10 1.0303 [1.0223,1.0433], T16 1.0352 [1.0189,1.0614]; progress/2026-11/2026-11-24-handoff-df2.md:45). The DTREE-GDN-BATCH box is open pending the C20 fold decision (its GDN row is KEEP, 3.619 ms), not parked. New disposition: fold TreeSpark's edge-acceptance Platt calibration and load-adaptive shrink-to-chain in as arms of DTREE-HEADROOM-REPLAY (handoffs/active/speculative-decoding.md) instead of a monitor. History above is kept unchanged.
