# B9/B10 — deterministic re-score of saved outputs, resolved fail-closed

**Date**: 2026-08-12 · **Rows**: B9, B10 of
[`handoffs/active/autopilot-decision-plane-audit-2026-07-22.md`](../../handoffs/active/autopilot-decision-plane-audit-2026-07-22.md)
· **Lane**: `none` — offline re-scoring of already-persisted outputs. No generation, no GPU, no CPU
region, no server started.

**Overlap notice.** These rows were assigned to `auditor`, which adjudicated them earlier the same
day (epyc-root `1aecd6f7`). This pass was run independently and **confirms the auditor's integration
finding and its destroyed-evidence finding**, then goes further: it builds and runs the instrument
the rows describe against the corpus that still exists.

---

## Verdict

| Claim | Status |
|---|---|
| Scorer isolation needs integrating | **REFUTED** — already on orchestrator `main` since 2026-07-29, in the required order |
| The isolation fix is sound | **CONFIRMED** by diff review + 11 counted tests |
| The E8-v5 replay corpus exists | **REFUTED** — destroyed; not on disk, not in git |
| Saved-output verdicts diverge from a deterministic re-score | **REFUTED for the live corpus** — 0 divergences in 5,324 re-scored rows |
| The corpus is otherwise clean | **REFUTED** — 232 rows store an infrastructure outage as a wrong answer |
| The debugbench oracle rebuild has landed | **REFUTED** — scorer-side only; 0 pool rows use the new oracle |

**Corrections applied: 0.** Fail-closed held throughout. Nothing was written back to any corpus.

---

## 1. B9 — integration: already done, and independently reviewed

The row named orchestrator branches `codex/debug-scorer-isolation-20260729` (`79f3d2f3`) and
`codex/e8-bcb190-score-fix-20260729` (`8bc6eaa9`). Both are **ancestors of `main`**, merged the same
day in the order the row requires:

```
cb9e4b4b  Merge codex/debug-scorer-isolation-20260729   parents: c33bcfee, 79f3d2f3
ad415448  Merge codex/e8-bcb190-score-fix-20260729      parents: cb9e4b4b, 8bc6eaa9
                                                                 ^ first parent IS the isolation merge
```

So bcb190 was built **on top of** isolation, not merged around it.

**Reviewed, not assumed.** The row said "reviewed"; that was checked rather than taken. The diff
replaces a shared `NamedTemporaryFile` in `/mnt/raid0/llm/tmp` with a per-invocation
`TemporaryDirectory`, and sets each subprocess `cwd` to it, in both `_score_stdin_program` and
`_score_code_execution`. It also removes a temp-file leak the old code had on several early-return
paths. `tests/unit/test_debug_scorer_code_execution.py` → **11 passed**, all module-level `test_*`
functions, so they are collected and counted by the reporter.

**The collision mechanism is now confirmed mechanically, not inferred.** `bcb_BigCodeBench/190`'s
oracle is a 3,366-character `unittest` whose `tearDown` runs `os.remove(DATABASE_NAME)` with
`DATABASE_NAME = 'test.db'` — a **relative** path. Under the old shared CWD, two concurrent
BigCodeBench rows deleted one another's database. The handoff's "the stored false has no execution
witness" is right, and it is stronger than stated: the oracle actively destroys a shared-name file.

`integrate/scorer-isolation-20260812` @ `3f734141` should **not** be merged. It holds one commit — an
audit note — on top of a stale base; merging it would revert ~6,600 lines of later `main` work.

## 2. The named replay corpus does not exist

Independently confirmed by four searches: the ratified namespace
`e8_quality_baseline_v5_partial_r2_final_c1_capacityfix_20260729T112433Z` and both failed completion
attempts (`…T123150Z`, `…T124832Z`) are absent from `artifacts/operator/`, absent from a
depth-limited filesystem sweep of `/mnt/raid0/llm`, `/workspace` and the backup roots, absent from
`git log --all --diff-filter=A` on those paths, and no file anywhere under `orchestration/`, `data/`
or `benchmarks/` contains the string `BigCodeBench/190`.

**Ordinal 418 therefore cannot be adjudicated, and was not.** No verdict was invented for it. The
one thing that *can* be said is tested rather than assumed: the BCB190 reference answer scores
`True` under the isolated scorer (`test_bcb190_sqlite_answer_still_scores_true`, passing). That is
the *reference*, not the saved model output, so it does not resolve the stored `false`.

## 3. B9/B10 executed against the corpus that does exist

The rows ask for a bounded deterministic completion over already-generated outputs plus a
fail-closed correction ledger. The instrument is the deliverable, so it was built and pointed at the
live persisted corpus: **18 corpora, 6,746 `question_result` rows** under
`epyc-orchestrator/orchestration/reports/`, each carrying a saved answer, a stored verdict, a suite
and the scoring method that actually ran.

Tool: [`scripts/audit/deterministic_rescore_ledger.py`](../../scripts/audit/deterministic_rescore_ledger.py)
· Ledger: [`deterministic-rescore-ledger-20260812.json`](deterministic-rescore-ledger-20260812.json)

| Disposition | Rows |
|---|---:|
| **agree** (stored verdict reproduces exactly) | **5,324** |
| **divergence** | **0** |
| excluded | 1,422 |

**The correction ledger is empty, and that is the finding.** Every stored verdict in the live corpus
that can be deterministically re-scored reproduces under today's isolated scorer.

### Exclusions, by reason

| Reason | Rows | What it means |
|---|---:|---|
| `answer_not_persisted` | 820 | the corpus never saved the output — verdict unauditable, forever |
| `method_unrecorded` | 223 | no scoring method recorded; the pool's is not a safe substitute (see §5) |
| `inband_infrastructure_error` | 213 | the "answer" is an `[ERROR: …]` string (see §4) |
| `answer_empty` | 107 | zero-token generation; all stored `false`, the only verdict possible |
| `nondeterministic_method:llm_judge` | 39 | would require inference — excluded *by method name, before the scorer is called* |
| `quarantined_suite` (debugbench) | 20 | see §6 |

## 4. NEW — 232 rows store an infrastructure outage as a wrong answer

Measured with the orchestrator's own REL-1 predicate
(`src.autopilot_core.measurement_guards.inband_error_text`), not a local re-implementation:

**232 rows across 10 of the 18 corpora have a saved answer that is an in-band error string** —
`[ERROR: Inference failed: chat_completions HTTP 500]`, `[ERROR: Backend unavailable (circuit
open): http://localhost:8082]` — and **all 232 are stored `correct: false`.** They sit in the
denominator as wrong answers instead of being excluded as infrastructure failures.

(213 are classified as such by the ledger; the other 19 are pre-empted by an earlier exclusion —
14 `method_unrecorded`, 5 `llm_judge`.)

Concentration: 117 in `eval_tower_math_rebaseline_E7c/…worker_math`, 83 in the same run's
`…worker_general`, 18 in `ev_baseline_e7_tier1`, the rest in single digits.

**This is the B10 defect class with the sign reversed.** B10 is about a stored `false` that a clean
re-score says should be `true` — a verdict the run did not earn, biased *up*. These are verdicts the
run did not earn, biased *down*. A ledger that only hunted for favourable corrections would have
walked straight past them.

Fail-closed disposition: they are **excluded and reported, not corrected to `true`**. An outage is
not evidence the model would have answered correctly.

## 5. NEW — the pool's scoring method disagrees with what actually ran, on 52.7% of rows

**This defect was found by making it.** The first version of this tool took the scoring method from
`question_pool.jsonl` and reported **629 divergences, 584 of them favourable** — a result that would
have read as a large, one-directional scoring correction.

Every one was an artifact. The corpus records the method that actually scored the row
(`result.scoring_method`), and it disagrees with the pool on **3,557 of 6,746 rows (52.7%)**:

| recorded (what ran) | pool (today) | rows |
|---|---|---:|
| `math_verify` | `exact_match` | 2,638 |
| `math_verify` | `substring` | 919 |
| *(absent)* | various | 223 |

The math suite is fed by `scripts/benchmark/dataset_adapter_modules/math_adapter.py`, which assigns
`math_verify`; the YAML pool row for the same `question_id` says `exact_match`. Re-scoring with
`exact_match` swaps in a **more permissive** scorer — its last-resort branch takes the final line of
the answer — and manufactures favourable corrections out of nothing.

The tool now takes the recorded method as authoritative, excludes rows that recorded none, and
excludes drift cases where the recorded method would need a `scoring_config` belonging to a
different method. The regression is pinned by
`test_method_drift_uses_recorded_method_not_pool`.

**Standing hazard:** any future offline re-score that joins this corpus to the pool for its scoring
method will reproduce this error and report a large favourable correction.

## 6. debugbench — 20 rows excluded and flagged, none re-scored

Per the oracle-vacuity finding
([`debugbench-oracle-vacuity-20260812.md`](debugbench-oracle-vacuity-20260812.md), `mainC`),
debugbench rows are **counted and listed, never re-scored under either oracle**. Re-scoring them
would launder an uninterpretable verdict into an adjudicated-looking ledger.

**20 rows, across 8 corpora — 11 stored `true`, 9 stored `false`:**

| ordinal | stored | question | corpus |
|---:|---|---|---|
| 4 ×3 | false | `debugbench_number-of-atoms_java` | `ev_baseline_corev2_tier1` |
| 24 ×3 | false | `debugbench_queries-on-number-of-points-inside-a-circle_cpp` | `ev_baseline_corev2_tier1` |
| 3 | true | `debugbench_reduction-operations-to-make-the-array-elements-equal_java` | `ev_baseline_corev2_tier2` |
| 8 | true | `debugbench_relative-ranks_cpp` | `ev_baseline_corev2_tier2` |
| 13 | true | `debugbench_relative-ranks_cpp` | `ev_baseline_corev2_tier2` |
| 26 | true | `debugbench_reverse-odd-levels-of-binary-tree_cpp` | `ev_baseline_corev2_tier2` |
| 1 ×4 | true | `debugbench_search-in-a-binary-search-tree_cpp` | `ev_baseline_e7_tier1` |
| 1 | false | `debugbench_search-in-a-binary-search-tree_cpp` | `ev_baseline_e7_tier1_diag` |
| 11 | true | `debugbench_special-array-with-x-elements-greater-than-or-equal-x_cpp` | `ev_baseline_e7_tier2` |
| 25 | true | `debugbench_search-in-a-binary-search-tree_cpp` | `ev_baseline_e7_tier2` |
| 1 | true | `debugbench_search-in-a-binary-search-tree_cpp` | `r3_current_arm_rebaseline_20260723` |
| 4 | false | `debugbench_number-of-atoms_java` | `r3_current_arm_rebaseline_corev2_20260723` |
| 24 | false | `debugbench_queries-on-number-of-points-inside-a-circle_cpp` | `r3_current_arm_rebaseline_corev2_20260723` |

The **11 stored passes** are the ones that matter: under a vacuous oracle a pass is indistinguishable
from echoing the buggy input.

### NEW — the oracle rebuild has not reached the data plane

`debug_scorer.py` gained a `code_patch` verifier (`_score_code_patch`, commit `53f7aea0`). But:

- **0 rows** in `question_pool.jsonl` use `scoring_method: code_patch`
- **0 rows** in `core_v2.jsonl` or `core_v2_ledger_20260703_min5.jsonl` use it
- all **4,253** debugbench pool rows still carry `substring` + a 100-character `expected`, and the
  expected prefix is still present in the prompt — mainC's own decisive vacuity test, still `True`

The scorer can now express a correct oracle; **no question asks it to.** Until the pools are
regenerated, every debugbench score remains vacuous and the quarantine above stays in force.

## 7. Verification of this audit's own work

**23 tests, module-level, collected and counted** —
[`tests/test_deterministic_rescore_ledger.py`](../../tests/test_deterministic_rescore_ledger.py).

A zero-divergence headline is the easiest number to produce by accident, so each guard was
**mutation-tested: the mutation was applied to the harness, the suite was re-run, and the failure
count moved.** All seven mutants were killed:

| # | Mutation | Result |
|---|---|---|
| M0 | baseline | 23 passed |
| M1 | remove the debugbench quarantine | **3 failed** |
| M2 | score with the pool's method instead of the recorded one | **2 failed** |
| M3 | always exit 0 (gate goes green on a divergence) | **1 failed** |
| M4 | drop the REL-1 in-band-error exclusion | **1 failed** |
| M5 | collapse `answer_not_persisted` into `answer_empty` | **1 failed** |
| M6 | remove the `--max-rows` abort | **1 failed** |
| M7 | let `llm_judge` reach the scorer | **1 failed** |
| — | restored | 23 passed |

Two of those tests mutate **real corpus rows through the real scorer**: flipping a stored verdict
must produce a divergence, and corrupting the saved answer must change the fresh verdict. Both pass
— so the zero is a measurement over a non-empty scored set, not an empty-input artifact.

"Can this check pass by deleting what it inspects?" No: `--max-rows` aborts rather than truncating,
an empty scored set fails the two real-corpus tests, and `build_ledger` **raises** if a quarantined
row ever carries a verdict or if any entry is marked applied.

The suite also caught an error in its own first draft — it asserted the wrong `exact_match` verdict
for a synthetic answer — which is direct evidence the real scorer is being exercised.

## 8. Scope and limits, stated

- **Instrument drift is real and is reported, not hidden.** The re-score uses today's scorer
  (`b66a2cff…`), not the one that produced the stored verdicts; the E8-era pin is `90b2fe1f…`. The
  ledger records both and sets `scorer_drifted_from_e8_pin: true`. A divergence would therefore have
  been evidence of *stored-verdict / current-instrument disagreement*, not proof the stored verdict
  was wrong — which is exactly why nothing is applied.
- **This does not re-open the E8 baseline.** The E8 era advanced to E9 under operator signature
  2026-08-11. Nothing here applies state, publishes a baseline, or produces a receipt.
- **820 stored verdicts are permanently unauditable** — their corpus
  (`eval_tower_calibration_baseline_HE-R+/frontdoor_ev4b`) saved `answer_hash` but not `answer`. No
  future pass can check them either.
- Read-only throughout. No corpus or pool file was modified; a byte-hash test asserts it.
