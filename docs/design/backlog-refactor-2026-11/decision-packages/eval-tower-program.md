# Decision package: eval-tower-program

Destination handoff `handoffs/active/eval-tower-program.md` · fold 2 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 9 · excluded: 0. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. EV-11 re-baseline: ratify the implemented closed-bin ECE (EV-11b) so `screen_paired_arms` can become decision-gating via a codified recipe?

- Context: `handoffs/active/eval-benchmark-cost-reduction.md:77@7eb7a4a3c911` (manifest `handoffs/active/eval-benchmark-cost-reduction.md:77@3ac825873dfb`, id `a3b9213737aa`)
- Gated worker box(es): `handoffs/active/eval-benchmark-cost-reduction.md:77`

- **Option A (recommended)**: Ratify closed-bin ECE for EV-11. *Tradeoff:* EV-11 math re-baseline unblocks; screen McNemar p can gate keep/revert.
- **Option B**: Keep `screen_paired_arms` observation-grade. *Tradeoff:* No change; paired screens cannot gate decisions.

**Recommendation: A.** Closed-bin ECE is already implemented (inference-batch-loop P2 note); the open item is the operator binning ruling.

## 2. Cluster E: approve the interim neutralisation (ECE/AUC observation-only) so constant 0.0 stops inflating the rlvr tier score?

- Context: `handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md:144@7eb7a4a3c911` (manifest `handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md:144@3ac825873dfb`, id `0b33d447bc6c`)
- Gated worker box(es): `handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md:144`

- **Option A (recommended)**: Approve interim neutralisation (sign off if scoring weights are touched). *Tradeoff:* Stops the inflation now; ECE/AUC stop contributing until real confidence lands.
- **Option B**: Wait for the final real-confidence decision. *Tradeoff:* No interim change; the inflated rlvr score persists.

**Recommendation: A.** Logprob passthrough already landed; neutralising a constant is a correction, not a new policy.

## 3. Adopt a judge anchor rule: every judge-scored gating metric is paired with a judge-independent verifier and the gap is reported (intake-875)?

- Context: `handoffs/active/eval-tower-verification.md:609@7eb7a4a3c911` (manifest `handoffs/active/eval-tower-verification.md:609@3ac825873dfb`, id `ccf4635e2175`)
- Gated worker box(es): `handoffs/active/eval-tower-verification.md:609`

- **Option A (recommended)**: Adopt. *Tradeoff:* Detects reward hacking (gap widening with N); each gated metric needs an anchor.
- **Option B**: Do not adopt. *Tradeoff:* No extra work; judge-only gates stay unanchored.

**Recommendation: A.** Cheap where verifiers exist and it guards against a known failure mode.

## 4. Run the dual-judge offline audit (clean vs bias-augmented rubric, gap per judge config; intake-874)?

- Context: `handoffs/active/eval-tower-verification.md:613@7eb7a4a3c911` (manifest `handoffs/active/eval-tower-verification.md:613@3ac825873dfb`, id `56a745685590`)
- Gated worker box(es): `handoffs/active/eval-tower-verification.md:613`

- **Option A (recommended)**: Run it. *Tradeoff:* Quantifies rubric bias per judge; runnable on the stack with no training.
- **Option B**: Skip. *Tradeoff:* No compute; bias stays unmeasured.

**Recommendation: A.** The box says it is runnable today and no training is required.

## 5. Extend the bias-robustness probe set with the four CHERRL bias families plus an exploitability axis (intake-874)?

- Context: `handoffs/active/eval-tower-verification.md:614@7eb7a4a3c911` (manifest `handoffs/active/eval-tower-verification.md:614@3ac825873dfb`, id `05740a5bbc21`)
- Gated worker box(es): `handoffs/active/eval-tower-verification.md:614`

- **Option A (recommended)**: Extend. *Tradeoff:* Wider coverage and a second reporting axis; probe authoring work.
- **Option B**: Keep the current set. *Tradeoff:* No work; the four families stay unprobed.

**Recommendation: A.** Probe authoring is zero-inference and the families come from a reviewed intake.

## 6. Split (scope, do not delete) the cross-family judge claim at the top of eval-tower-verification.md (intake-875/1168)?

- Context: `handoffs/active/eval-tower-verification.md:616@7eb7a4a3c911` (manifest `handoffs/active/eval-tower-verification.md:616@3ac825873dfb`, id `25b1e5dbea70`)
- Gated worker box(es): `handoffs/active/eval-tower-verification.md:616`

- **Option A (recommended)**: Scope the claim to the failure mode it holds for. *Tradeoff:* Record becomes accurate; edits a headline rule.
- **Option B**: Leave the single rule. *Tradeoff:* No edit; a rule falsified for one failure mode keeps being cited as a reward-hacking defence.

**Recommendation: A.** The box records the claim as falsified for one mode; scoping keeps the true half.

## 7. EV-14b: should the measured band BLOCK (record sub-band deltas as `unresolved`)?

- Context: `handoffs/active/eval-tower-verification.md:737@7eb7a4a3c911` (manifest `handoffs/active/eval-tower-verification.md:737@3ac825873dfb`, id `3b54b3699cee`)
- Gated worker box(es): `EV-14b` (handoffs/active/eval-tower-verification.md:737)

- **Option A (recommended)**: Give the gate the third state (`unresolved`). *Tradeoff:* Sub-band deltas stop counting as improvements; uses the state `self_criticism.py` already computes.
- **Option B**: Keep MAD non-blocking. *Tradeoff:* No change; sub-band deltas keep counting as wins.

**Recommendation: A.** The third state is already computed and discarded; using it is the minimal correction.

## 8. B7 scorer-semantics sign-off for EV-4 (textual multiple-choice label handling changed scoring semantics).

- Context: `handoffs/active/inference-batch-loop.md:197@7eb7a4a3c911` (manifest `handoffs/active/inference-batch-loop.md:197@3ac825873dfb`, id `12c46ff2e68b`)
- Gated worker box(es): `handoffs/active/inference-batch-loop.md:197`

- **Option A (recommended)**: Sign off and re-run EV-4. *Tradeoff:* Unblocks the first live v7 entry; new scorer semantics become the era's.
- **Option B**: Hold EV-4 BLOCKED_PRECONDITION. *Tradeoff:* No re-run.

**Recommendation: A.** The scoring change fixes label handling and preflight now fails closed; the sign-off is the only blocker.

## 9. Eval-tower pool registration for LCB-hard / BCB-hard / SWE-oracle once they prove discriminative.

- Context: `handoffs/active/scoring-infra-standardization.md:234@7eb7a4a3c911` (manifest `handoffs/active/scoring-infra-standardization.md:234@3ac825873dfb`, id `a8b6d1f2a115`)
- Gated worker box(es): `handoffs/active/scoring-infra-standardization.md:234`

- **Option A**: New-era row. *Tradeoff:* Clean era boundary; resets comparability.
- **Option B (recommended)**: Supplementary pool. *Tradeoff:* Keeps the existing era; supplementary results do not gate.
- **Option C**: Bench-only. *Tradeoff:* No era change; no eval-tower role.

**Recommendation: B.** Supplementary keeps era comparability while the suites prove themselves; deliver only after discrimination is shown.

