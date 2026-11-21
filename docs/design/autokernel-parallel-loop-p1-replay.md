# AutoKernel parallel loop — P1 gate-evaluator replay (2026-11-21)

**Result: strict agreement 392/471 = 83.2%; 85.8% when SUPERSEDED and WITHDRAWN are counted as one
no-claim class. Both are below the ≥95% target, so AKPL-P1 stays open.** Every one of the 79 disagreements is
assigned to a category below. No category is an evaluator defect that could be fixed without fitting the evaluator
to individual owner rulings. Each one is either owner filing practice that rowflow facts cannot separate, a
recorded rule change, or a row-convention bug with a named fix.

- Evaluator: `epyc-inference-research` `scripts/kernel_rnd/autokernel/loop/gate_eval.py` (pure function, no LLM).
  Replay: `gate_eval_replay.py` in the same directory. Full per-row output:
  `/mnt/raid0/llm/tmp/akpl-p1-replay-20261121/replay.json`.
- Population: every `filing-done/*.verdict.json` with `owner == autokernel` and `filed_at >= 2026-11-06`
  (471 records), plus each row's `out/RESULT.json` and `grants/<row>.ended` line.
- Mapping: evaluator PASS→pass, FAIL→fail, NOISE→fail (a measured null, the runend DROP convention),
  FUTILITY→inconclusive, plus SUPERSEDED/WITHDRAWN. Human labels: `BIT_EXACT_PASS`/`PASS`→pass,
  `partial`/`ABSTAIN`→inconclusive.
- Design and phases: [autokernel-parallel-loop.md](autokernel-parallel-loop.md).

## Headline numbers

| Measure | Value |
|---|---|
| Strict agreement (6 labels) | 392/471 = 83.2% |
| Agreement with SUPERSEDED and WITHDRAWN as one no-claim label | 404/471 = 85.8% |
| Agreement on claim-bearing filings (human pass or fail) | 251/281 = 89.3% |
| Polarity flips (pass↔fail) | 4 of 471 |
| Rows decided by the graph-KLD / speed policy layer | 11 (9 agree; the other 2 are category B2 lifecycle labels and pass every policy check) |
| Deciding layer | {'L0': 88, 'L1': 13, 'L1+L3': 1, 'L2': 2, 'L2+L3': 9, 'L3': 358} |

The policy layer (27B-anchored `graph_kld_policy.json`, in force from 2026-11-18; row `rule.geomean_min` speed floor;
bench floor only on its calibrated 1.5B workload) fires on the C-fold gate rows. There it matches every
claim-bearing filing, for example `c16-fold-gpu` PASS, `c17-fold-cpu-r2` PASS, `c15-fold-cpu` FAIL on geomean
0.960 < 0.995. Most AK rows since 11-06 are science and diagnostic rows. A row's own pre-registered RULE decides
those rows, and the RESULT records the outcome as a declared verdict token (layer L3).

## Confusion (human | evaluator | rows)

| Human | Evaluator | Rows |
|---|---|---|
| SUPERSEDED | SUPERSEDED | 55 |
| SUPERSEDED | WITHDRAWN | 1 |
| SUPERSEDED | fail | 2 |
| SUPERSEDED | inconclusive | 8 |
| WITHDRAWN | SUPERSEDED | 11 |
| WITHDRAWN | WITHDRAWN | 3 |
| WITHDRAWN | inconclusive | 2 |
| fail | SUPERSEDED | 2 |
| fail | fail | 95 |
| fail | inconclusive | 10 |
| fail | pass | 3 |
| inconclusive | SUPERSEDED | 12 |
| inconclusive | WITHDRAWN | 3 |
| inconclusive | fail | 9 |
| inconclusive | inconclusive | 83 |
| inconclusive | pass | 1 |
| pass | SUPERSEDED | 1 |
| pass | fail | 1 |
| pass | inconclusive | 13 |
| pass | pass | 156 |

## Disagreements by category

| Category | Rows | Class | Explanation |
|---|---|---|---|
| A. Lifecycle label: SUPERSEDED vs WITHDRAWN | 12 | Convention drift (no evaluator bug) | Both labels mean the row closed with no claim; the filer uses them interchangeably for rows withdrawn in favour of a successor. Recommendation: one no-claim label, or file WITHDRAWN only when no successor exists. |
| B. No-claim vs inconclusive on a row with no completed run | 21 | Convention drift | Rows that never produced a completed RESULT are filed SUPERSEDED in 55 cases and inconclusive in others with the same rowflow facts (successor exists, rc 75/1, exited/stopped). No deterministic rowflow fact separates the two; a rule that tried (`exited`/`job-rc-N` = a run, not a lifecycle event) moved 15 rows each way and was reverted. |
| B2. Completed run with a harness-failure verdict, filed as no-claim | 9 | Convention drift | The run completed (rc 0) with a declared harness failure (FUTILITY_INPUT, FAIL_WINDOW, invalid-run) and the owner filed SUPERSEDED because a successor re-ran it. Applying `harness failure + successor -> SUPERSEDED` was tested and lowered agreement to 74.3% (58 inconclusive filings flipped), so it was rejected. |
| C. DROP(diagnostic) filed pass/fail before the DROP-as-pass guard | 6 | Recorded rule change | FILER-DROP-AS-PASS-GUARD (epyc-root bba1c010a, 2026-11-20) forbids pass for a DROP verdict and corrected c6-admission-live-proof-r12 to inconclusive; these up-farows rows were filed 2026-11-16/17 under the old practice. The evaluator follows the current rule (diagnostic -> inconclusive). |
| D. Overloaded FUTILITY token | 12 | Vocabulary bug in the row convention: the same token names a harness failure in some rows and a candidate negative in others (FUTILITY_IDENTITY = store-identity proof vs candidate output identity; FUTILITY_BELOW_BASELINE filed fail 7x, inconclusive 3x) | Fix: split the tokens (e.g. FUTILITY_STORE_IDENTITY vs FAIL_OUTPUT_IDENTITY) in job.py templates; the evaluator then needs no change. |
| E. Named answer whose negative polarity is only in prose | 3 | Evaluator limit / row-convention bug: the declared token (ANSWERED, MEASURED, FILED) carries no polarity, and the RULE outcome (FAIL, not KEEP-candidate) lives only in the free-text reason | Fix: the row template must write a polar token (PASS/KEEP/FAIL/DROP) next to the answer. |
| F. Verdict read from results.jsonl or a non-RESULT file | 8 | Harness gap: no out/RESULT | Fix: row_scaffold's check_complete already requires RESULT.json with a verdict for new rows; these are older rows. |
| G. Negative token filed inconclusive (owner judged the instrument) | 6 | Judgment call by the owner: the declared rule fired FAIL/NO_GAIN/DROP, but the owner ruled the measurement unfit (flake, missing witness, OFF-arm also failing) | This is the irreducible noise-vs-regression judgment the plan keeps for the critic tier; the evaluator cannot see it from RESULT. |
| H. Other | 2 | See row notes | See row notes. |

What would move the number, and why this replay did not do it:

- **A + B + B2 (42 rows) are a filing-practice question.** Owners file rows that never
  produced a claim inconsistently as SUPERSEDED, WITHDRAWN or inconclusive. Three candidate lifecycle rules
  were each tried against the replay and rejected:
  - `exited` means a run: net −2 rows.
  - harness failure plus a successor means SUPERSEDED: −8.5 points.
  - `ready/.withdrawn/` means withdrawn: −24 points, because every filed manifest is archived there.

  A single filing rule settles all three categories. One option: "no completed RESULT means no-claim; a
  successor makes it SUPERSEDED, otherwise WITHDRAWN". With that rule the evaluator would agree by construction.
  It is a filing-convention decision for the row owners, not an evaluator change.
- **C (6) is a recorded rule change** (FILER-DROP-AS-PASS-GUARD, bba1c010a). Under the current rule the
  evaluator is right.
- **D, E, H (17) are row-template bugs.** Two template changes in job.py remove these
  disagreements: write one polar token per row, and split the overloaded FUTILITY tokens.
- **F (8) is older rows without RESULT.json.** New scaffolded rows require it.
- **G (6) is the owner's noise-vs-regression judgment.** The plan keeps that judgment with an LLM (critic
  tier).

Excluding A + C + F (the categories with a recorded or convention explanation that makes no claim about a
candidate), agreement on the remaining population is
392/445 = 88.1%. That figure is a diagnostic, not the gate.

Caveat: the layer-L3 token vocabulary was written while reading this same corpus, so the agreement is
**in-sample**. Re-run the replay on filings after 2026-11-21 as a holdout before relying on these numbers:
`python3 -m autokernel.loop.gate_eval_replay --since 2026-11-22`.

## Row notes

- `rka-a3b-gpu-d-np-sweep-20261118-r3`: declared DROP_MULTI (no D2 np gain >= 3%) but the owner filed the RECOMMEND_D2 answer as pass: the row asked two questions; the RESULT verdict answers only one (row-convention bug: one polar token per row).
- `s3-aku-13-loo-cpu-c14-20261118`: MEASURED (data collected) but the owner filed inconclusive because the Goodhart count was 4/5 against a rule needing 5/5; polarity only in prose (same class as E).

## Re-run under the 2026-11-21 filing rule

Operator ruling 2026-11-21: **no result → no claim**. A row with no finished RESULT is SUPERSEDED when a
successor exists, otherwise WITHDRAWN, never inconclusive. `gate_eval` now applies it (gate id
`filing.no_result_no_claim`). "Finished" means a RESULT exists, the job ended rc 0 (any end reason) and the
record does not say `complete:false`. Polar tokens (`polar`, `FUTILITY_HARNESS_*`, `FUTILITY_CANDIDATE_*`) are
accepted next to the legacy vocabulary. No historical row carries them yet, so they do not change this replay.

"Ruled" agreement re-reads each owner label under the rules in force today. A no-result row's correct label is
the rule's. A lifecycle label on a row that ran to a finished RESULT means "ran but could not decide", which is
inconclusive. A pass on `DROP(diagnostic…)` is inconclusive under FILER-DROP-AS-PASS-GUARD (bba1c010a). The
no-result part agrees **by construction**: the ruling defines the label. It is reported as such.

| Measure (472 filings, owner autokernel, since 2026-11-06) | Before (P1 code at origin) | After |
|---|---|---|
| Strict agreement vs historical owner labels | 393/472 = 83.3% | 392/472 = 83.0% |
| Ruled agreement (labels re-read under today's rules) | — | **444/472 = 94.1%** |
| Policy-decided verdicts agreeing (filable with 0 LLM turns) | — | 109/110 |

Per group (the categories of the disagreement table above; "agreed-in-P1" = rows that agreed in the first replay):

| Group | Strict before | Strict after | Ruled after |
|---|---|---|---|
| agreed-in-P1 | 393/393 | 390/393 | 393/393 |
| A lifecycle label | 0/12 | 0/12 | 12/12 |
| B no-claim vs inconclusive | 0/21 | 2/21 | 21/21 |
| B2 completed run, harness failure, filed no-claim | 0/9 | 0/9 | 7/9 |
| C DROP(diagnostic) filed pass/fail | 0/6 | 0/6 | 4/6 |
| D overloaded FUTILITY token | 0/12 | 0/12 | 0/12 |
| E polarity only in prose | 0/3 | 0/3 | 0/3 |
| F no out/RESULT | 0/8 | 0/8 | 7/8 |
| G owner judged the instrument | 0/6 | 0/6 | 0/6 |
| H other | 0/2 | 0/2 | 0/2 |

By ruled label: SUPERSEDED 80/80, WITHDRAWN 20/20, pass 157/163, fail 96/106, inconclusive 91/103.

**94.1% is below the ≥95% gate, so AKPL-P1 stays open.** The 28 rows that still disagree:
- D + E + H (17) are row-template bugs. The polar tokens fix them for new rows only. Historical rows cannot be
  re-tokenised without inventing what their RESULT never said.
- G (6) is the owner's noise-vs-regression judgment (critic tier).
- C (2) are DROP(diagnostic) rows filed fail. B2 (2): `c17-fold-gpu-20261121` declared FAIL on a finished run,
  filed SUPERSEDED, and `lb49-sinks-identity-cpu-20261110` declared FAIL(build). F (1): `c6-port35186-remeasure-r2`.
  For these, rc 0 with a RESULT but no verdict.

What would close P1: a holdout of filings made after the polar tokens land
(`python3 -m autokernel.loop.gate_eval_replay --since 2026-11-22 --categories <this file>`) at ≥95%. That needs
the AK loop running again. Zero-LLM filing is wired: `runend.py <row> --gate-eval --file` files a
`policy_decided` verdict at once and exits 4 with a draft otherwise.

## Every disagreement

| Row | Human | Evaluator | Gate | Declared | Cat |
|---|---|---|---|---|---|
| `ak-dtree-kernels-opgate-gpu-20261119` | WITHDRAWN | SUPERSEDED | `lifecycle.superseded` | — | A |
| `ak-dtree0-q8packed-gate-gpu-20261120` | WITHDRAWN | SUPERSEDED | `lifecycle.superseded` | — | A |
| `ak-surface-proof-a-20261106` | WITHDRAWN | SUPERSEDED | `lifecycle.superseded` | — | A |
| `akx-all-13a-q38fn-threads-20261118` | WITHDRAWN | SUPERSEDED | `lifecycle.superseded` | — | A |
| `c14-fold-gpu-20261118` | WITHDRAWN | SUPERSEDED | `lifecycle.superseded` | — | A |
| `c14-kld-diag-gpu-20261118` | WITHDRAWN | SUPERSEDED | `lifecycle.superseded` | — | A |
| `c15-cpu-fa-splitkv-speed-20261118` | WITHDRAWN | SUPERSEDED | `lifecycle.superseded` | — | A |
| `c6-admission-live-proof-r10` | WITHDRAWN | SUPERSEDED | `lifecycle.superseded` | — | A |
| `race-eqv-gpu-r4-20261110` | SUPERSEDED | WITHDRAWN | `lifecycle.withdrawn` | — | A |
| `rka-a3b-gpu-d-np-sweep-20261118` | WITHDRAWN | SUPERSEDED | `lifecycle.superseded` | — | A |
| `rka-a3b48-d-remeasure-20261118-r3` | WITHDRAWN | SUPERSEDED | `lifecycle.superseded` | — | A |
| `rka-a3b48-d-remeasure-20261118` | WITHDRAWN | SUPERSEDED | `lifecycle.superseded` | — | A |
| `ak-asm-t1-harness-r3-20261121` | inconclusive | WITHDRAWN | `lifecycle.withdrawn` | — | B |
| `ak-c14-c6-dispatch-reprofile-20261119` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `ak-draft-head-svd-cpu-20261121-r2q0` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `ak-dtree-batch-identity-gpu-20261119-r2` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `ak-dtree-build-gpu-20261120-r5` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `ak-dtree0-gdnr-gate-gpu-20261120` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `ak-lb49-sinks-gate-c10-20261110-r5` | pass | SUPERSEDED | `lifecycle.superseded` | — | B |
| `ak-lb49-sinks-gate-c9-20261109-r3` | SUPERSEDED | inconclusive | `run_end.no_result` | — | B |
| `ak-mmq-h10b-dense-ctxstate-bracket-20261110-r2` | inconclusive | WITHDRAWN | `lifecycle.withdrawn` | — | B |
| `ak-pfxc-probe-gpu-20261120` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `ak-q38fn-relianceproof-c10-20261110-r5` | fail | SUPERSEDED | `lifecycle.superseded` | — | B |
| `ak-sl2-m1-floor-20261107-r3` | SUPERSEDED | inconclusive | `run_end.no_result` | — | B |
| `am-port-ea-ladder-gpu-20261119` | fail | SUPERSEDED | `lifecycle.superseded` | — | B |
| `am-port2-l4-vs-ea-gpu-20261119` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `c6-admission-live-proof-r3` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `inf75-c12-w5s-census-20261117-r2` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `rka-verify-tile-a3b48-e2e-20261117` | inconclusive | WITHDRAWN | `lifecycle.withdrawn` | — | B |
| `up-convsnap-gpu-20261115-r3` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `up-convsnap-gpu-20261115-r5` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `up-farows-hip-gpu-20261116-r14` | WITHDRAWN | inconclusive | `run_end.no_result` | — | B |
| `yarn-gpu-512k-20261120` | inconclusive | SUPERSEDED | `lifecycle.superseded` | — | B |
| `ak-c10-q38fn-floor-20261110` | SUPERSEDED | inconclusive | `declared.harness_failure` | FAIL_WINDOW | B2 |
| `ak-q38fn-idxk-cache-cpu-20261120-r2` | SUPERSEDED | inconclusive | `declared.futility` | FUTILITY_NOT_ENGAGED | B2 |
| `c17-fold-cpu-20261121` | SUPERSEDED | inconclusive | `declared.invalid_run` | FAIL(CH33 FAIL(invalid-run); speed not run) | B2 |
| `c17-fold-gpu-20261121` | SUPERSEDED | fail | `declared.negative` | FAIL(per-step geomean 0.9911 < 0.995; P2 0.9692 < 0.98; P3 0 | B2 |
| `lb49-sinks-identity-cpu-20261110` | SUPERSEDED | fail | `declared.negative` | FAIL(build) | B2 |
| `race-eqv-gpu-r5-20261110` | SUPERSEDED | inconclusive | `declared.futility` | INVALID_BASELINE_UNUSABLE | B2 |
| `rka-a3b-gpu-d-np-sweep-20261118-r2` | SUPERSEDED | inconclusive | `declared.harness_failure` | FUTILITY_INPUT | B2 |
| `rka-a3b-mmvf8-e2e-gpu-20261118` | SUPERSEDED | inconclusive | `declared.harness_failure` | FUTILITY_INPUT | B2 |
| `rka-a3b48-d-remeasure-20261118-r2` | WITHDRAWN | inconclusive | `declared.harness_failure` | FUTILITY_INPUT | B2 |
| `up-farows-hip-gpu-20261116-r10` | pass | inconclusive | `declared.diagnostic` | DROP(diagnostic: GRAPH_PRESENCE; NA (no attach) coherent: st | C |
| `up-farows-hip-gpu-20261116-r2` | pass | inconclusive | `declared.diagnostic` | DROP(diagnostic: NOT_ENGAGED; no 'engaged' line in the serve | C |
| `up-farows-hip-gpu-20261116-r3` | pass | inconclusive | `declared.diagnostic` | DROP(diagnostic: GATHER_OTHER; V1 garbage, V2 garbage, gathe | C |
| `up-farows-hip-gpu-20261116-r5` | fail | inconclusive | `declared.diagnostic` | DROP(diagnostic: NOT_FIXED; C1: coherent=False gen_same 0/32 | C |
| `up-farows-hip-gpu-20261116-r6` | pass | inconclusive | `declared.diagnostic` | DROP(diagnostic: KERNEL_MISMATCH; 32 of 50 VERIFY lines MISM | C |
| `up-farows-hip-gpu-20261116-r7` | fail | inconclusive | `declared.diagnostic` | DROP(diagnostic: NOT_COHERENT; C1 (graphs on) garbage: gen_s | C |
| `ak-c10-q38fn-floor-r5-20261111` | fail | inconclusive | `declared.harness_failure` | FUTILITY_NOISY_NOT_REGISTERED | D |
| `ak-dtree-a-argmax-gpu-20261119-r2` | fail | inconclusive | `declared.harness_failure` | FUTILITY_IDENTITY | D |
| `ak-dtree-a-argmax-gpu-20261119` | fail | inconclusive | `declared.harness_failure` | FUTILITY_IDENTITY | D |
| `ak-dtree-attn-share-gpu-20261120-r3` | pass | inconclusive | `declared.futility` | NOT_JUDGEABLE | D |
| `ak-dtree-batch-a3b-gpu-20261120-r4` | inconclusive | fail | `declared.futility_candidate_negative` | FUTILITY_BELOW_BASELINE | D |
| `ak-gap-1-sample-gpu-20261121` | fail | inconclusive | `declared.harness_failure` | FUTILITY_IDENTITY | D |
| `ak-gdn-spec-split-cpu-20261119` | pass | inconclusive | `declared.harness_failure` | FUTILITY_SHARE (Q38FN GATED_DELTA_NET share 1.11% < 3.0% of  | D |
| `ak-rsreplay-gate-gpu-20261121-r2` | inconclusive | fail | `declared.futility_candidate_negative` | FUTILITY_BELOW_BASELINE | D |
| `ak-rsreplay-gate-gpu-20261121-r3` | inconclusive | fail | `declared.futility_candidate_negative` | FUTILITY_BELOW_BASELINE | D |
| `inf86-ckpt-spacing-20261111` | pass | inconclusive | `declared.futility` | PARTIAL | D |
| `rka-a3b-n4-step-gpu-20261118` | fail | inconclusive | `declared.futility` | FUTILITY | D |
| `up-farows-hip-gpu-20261116-r9` | pass | inconclusive | `declared.harness_failure` | FUTILITY_CONTROL_BAD: R1 (knob 0 control) not coherent: gen_ | D |
| `ak-dtree0-q8mf-hbm-gpu-20261120` | fail | pass | `declared.answered` | FILED | E |
| `ak-q38fn-draftfa-w8192-cpu-20261120-r3` | fail | pass | `declared.answered` | ANSWERED | E |
| `aku-07j-07h-restart-exercise-20261118` | fail | pass | `declared.answered` | MEASURED | E |
| `ak-c14-c6-dispatch-reprofile-20261119-r2` | pass | inconclusive | `run_end.no_result` | — | F |
| `ak-iq3s-zmm-oracle-20261109-r4` | pass | inconclusive | `run_end.no_result` | — | F |
| `ak-q38fn-draftfa-window-cpu-20261119` | fail | inconclusive | `run_end.incomplete` | — | F |
| `ak-q38fn-indexer-topk-cpu-20261119` | fail | inconclusive | `run_end.incomplete` | — | F |
| `ak-q38fn-relianceproof-c9-20261109-r4` | fail | inconclusive | `run_end.no_result` | — | F |
| `c10-c6-dispatch-reprofile-20261110-r2` | pass | inconclusive | `run_end.no_result` | — | F |
| `c10-q38fn-quality-iqkq8pf-20261110-r2` | pass | inconclusive | `run_end.no_result` | — | F |
| `c6-port35186-remeasure-r2-20261111` | pass | inconclusive | `declared.none` | — | F |
| `ak-dtree0-q8packed-gate-gpu-20261121` | inconclusive | fail | `declared.negative` | NO_GAIN | G |
| `ak-gap-1-idsort-step2-gpu-20261121-r2` | inconclusive | fail | `declared.negative` | FAIL(correctness) | G |
| `ak-gap-1-sample-gpu-20261121-r3` | inconclusive | fail | `declared.negative` | NO_WIN | G |
| `ch37-df2-12-1-27b-c14-gpu-20261119-r1` | inconclusive | fail | `declared.negative` | FAIL | G |
| `up-bundle1-gpu-20261115-r4` | inconclusive | fail | `declared.negative` | FAIL(1 new non-LIGHTNING_INDEXER ROCm0 failures; decode not  | G |
| `up-convsnap-gpu-20261115-r4` | inconclusive | fail | `declared.negative` | DROP(ROCm0 failure sets differ ex-LIGHTNING_INDEXER (fold 8, | G |
| `rka-a3b-gpu-d-np-sweep-20261118-r3` | pass | fail | `declared.negative` | DROP_MULTI(no D2 np with gain >= 0.03: {'D2@np4': 0.0091, 'D | H |
| `s3-aku-13-loo-cpu-c14-20261118` | inconclusive | pass | `declared.answered` | MEASURED | H |

## Wiring (done this step)

- `runend.py <row> --gate-eval` drafts `<rowdir>/verdict.json` from the evaluator. It refuses, with exit 3, a
  lifecycle verdict, which is not filable as pass/fail/inconclusive.
- `watch_rows.sh --gate-eval` drafts on every ENDED event and appends `gate=[…]` to the event line. It is opt-in,
  so existing watchers do not change.
- Still open for the P1 done-when: "new rows file with zero LLM turns". The draft is automatic, but `runend.py
  --file` is still an owner step. Making it automatic needs the agreement gate above first.
