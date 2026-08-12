# Quantifying `debug_scorer`'s last-standalone-letter inflation vs the canonical extractor

**Date**: 2026-08-12 · **Lane**: `none` (offline re-scoring of persisted eval outputs; zero
inference, zero process management, no branch switching) · **Source row**:
[`handoffs/active/scoring-infra-standardization.md`](../../handoffs/active/scoring-infra-standardization.md)
1c-fix (c) — *"`debug_scorer.py:269-272` last-standalone-letter fallback is a false-POSITIVE
(score-inflation) risk vs the canonical lib — re-score a recent eval batch before/after
consolidation to quantify."* Companion work: 1c-fix (a) vendored the canonical
`answer_scoring` library into the orchestrator repo (`epyc-orchestrator`, a separate clone from
this one) at `scripts/benchmark/answer_scoring_vendored.py`, commit `39ff247b`, used here as the
canonical side of the comparison.

**Scope amendment (mid-task, from the launching auditor)**: exclude and flag `suite=debugbench`
and `suite=livecodebench`-family rows from the dual re-score — their oracles are separately
confirmed vacuous (`artifacts/audit/debugbench-oracle-vacuity-20260812.md`,
`artifacts/audit/unscoreable-rows-livecodebench-cruxeval-mah-20260812.md`) and a bias number over
a non-discriminating oracle would be meaningless. **Acknowledged and applied — see §1.**

---

## Verdict

| Question | Answer |
|---|---|
| Persisted (response, expected, verdict) rows scored via `debug_scorer`'s multiple-choice letter path exist? | **YES** — 122 rows across 7 committed eval-batch reports (46 after deduping identical repeated generations) |
| Does `debug_scorer` score MORE answers "correct" than canonical on the same rows? | **YES, net positive**: batch accuracy **+5.74pp raw (+4.35pp deduped)**, `debug_scorer` higher |
| Is the inflation attributable to the named mechanism (Strategy 5, unconditional last-standalone-letter)? | **Mostly yes, but not purely** — of 11 raw disagreements (4 unique), 8 raw (3 unique) trace to Strategy 5; the other 3 raw (1 unique) trace to a *different* mechanism (bold-letter Strategy 4, which canonical lacks entirely — see §4) |
| Any reverse-direction cases (canonical scores true, debug_scorer false)? | **YES, one** — also a Strategy-5 misfire, on a genuinely different truncated response |
| `debugbench` / `livecodebench`-family rows in this quantification? | **ZERO** — see §1; both suites score exclusively via `substring`, never `multiple_choice`, so the amendment's exclusion removes nothing from this dataset but is confirmed, not assumed |

---

## 1. Amendment: debugbench / livecodebench exclusion, counted

Per the mid-task scope amendment, before analyzing anything I counted every `debugbench` and
`livecodebench`-family row across **all** persisted `question_results*.jsonl` reports under
`epyc-orchestrator/orchestration/reports/` (6,746 `question_result` rows total, any scoring
method):

```
suite=debugbench       : 20 rows  — 100% scoring_method=substring
suite=livecodebench     : 22 rows  — 100% scoring_method=substring
```

Neither suite has a single row scored `multiple_choice` anywhere in the persisted corpus. The
letter-extraction bug this task quantifies only fires inside `_score_multiple_choice` →
`_extract_multiple_choice_letter`, which these suites never reach. **Disposition: EXCLUDED
because absent, not filtered out of a larger set** — flagged here as pending-oracle-rebuild per
the amendment, contributing 0 rows to §2/§3 either way.

## 2. Method and inputs

**Where the rows live.** `debug_scorer.score_answer` is the production scorer for eval-tower
batches (`scripts/autopilot/eval_tower.py:_score_generation` →
`seeding_scoring.score_answer_deterministic` → the orchestrator's own `debug_scorer.py`, path-pinned
per `seeding_scoring.py:32-60`). Each batch persists one `question_results.<label>.jsonl` per arm
under `orchestration/reports/<run>/`; each `row_type=question_result` row carries the full model
`answer` text, `result.correct` (the verdict `debug_scorer` produced), `result.scoring_method`,
`result.suite`, and `result.question_id` — but **not** the gold `expected` value, which lives only
in the question pool.

**Selection.** Scanned all 14 persisted report directories (7,742 total `question_result` rows across
files with any `answer` text). Kept rows where `result.scoring_method == "multiple_choice"` (2,654
of these) **and** `result.suite != "scoring_verifiers"` (2,513 of the 2,654) — `scoring_verifiers`
rows use textual `choices=["correct","incorrect"]` labels, not lettered options, so the letter
extractor structurally never fires meaningfully on them (verified: 2-token responses like
`"correct"`/`"incorrect"` never match any of `debug_scorer`'s five letter strategies). That leaves
141 genuine lettered-MCQ rows (`mmlu*`, `gpqa`, `gpqa_diamond`, `gpqa_diamond_cot`, `hellaswag`,
`real_suite_v1`, under the coarser `result.suite` labels `mmlu_pro`/`general`/`thinking`/`gpqa`/
`gpqa_diamond`/`gpqa_diamond_cot`/`real_suite_v1`); 122 of those 141 carry a non-empty persisted
`answer` (19 rows have no stored response text and were dropped, not scored either way).

**Joining `expected`.** Streamed `epyc-inference-research/benchmarks/prompts/question_pool.jsonl`
(gitignored — `.gitignore:89` — provenance is content hash + mtime, not a commit) once, matching
`id == question_id`; all 40 distinct `question_id`s needed were found (0 missing). Every joined row
has `expected` as a bare letter (`A`–`D` observed; no `E`–`J` cases in this sample) and empty
`scoring_config` (`{}` — no `choices`), so canonical's `expected.upper().strip()` comparison and
`debug_scorer`'s `_expected_choice_letter` regex resolve to the same target letter.

**Sanity check.** Re-ran `debug_scorer.score_answer` on all 122 joined rows and compared to the
originally-persisted `result.correct`: **0 mismatches** — confirms the join is correct and the
replay is faithful to what actually happened at eval time.

**Dual re-score.** For each row, called (a) `debug_scorer.score_answer(answer, expected,
"multiple_choice", scoring_config)` — the real production function — and (b)
`answer_scoring_vendored.score_response(answer, expected, {"scoring_method":"multiple_choice",
"scoring_config": scoring_config})` — the vendored canonical function, both against the current
committed `main`. `debug_scorer.py` was pinned to commit `f8eb36f7` (the last commit to touch the
file) rather than the working tree, because the working tree currently carries an unrelated,
uncommitted, in-flight local diff (a `code_patch` programmatic verifier for the debugbench oracle
rebuild — a different session's WIP). **Verified byte-identical** between `f8eb36f7` and the
working tree specifically for the multiple-choice code path (`_score_multiple_choice` through
`_extract_multiple_choice_text_index`, lines 233-342) before using the pinned copy, so the
uncommitted WIP has zero bearing on this measurement.

**Deduping.** 25 of the 40 distinct `question_id`s recur across multiple eval-batch reports; 19 of
those recur with byte-identical response text (deterministic/cached re-generation), 6 recur with
genuinely different text (independent re-sampling). Reporting both: raw N=122 (every persisted
scoring event) and deduped N=46 (unique `(question_id, answer_text)` pairs, collapsing only the
byte-identical repeats so genuinely independent generations are never merged).

**Input hashes** (sha256, all inputs read-only, nothing modified):

| Input | Hash / identity |
|---|---|
| `answer_scoring_vendored.py` (canonical side) | `d331f98ec0a3962828b4dd3d8c2895ccc9b7e71bd5f7348e9f1899191c1daca8` @ orchestrator commit `39ff247b` |
| `debug_scorer.py` (production side, pinned) | `abe31dce82397ca3dc87fb9a6f02b55f23a3bd5dfe00e02acf79e6511826076a` @ orchestrator commit `f8eb36f7` |
| `question_pool.jsonl` (gold `expected` source) | `64218c27e07400acf3b10a3cac05a410d5ee67814f353788ab75a19c84dde584`, 1,350,221,880 bytes, mtime 2026-08-04T07:02:15Z (gitignored, not a git ref) |
| 7 `question_results.*.jsonl` report files (all rows sourced from these) | all 7 at orchestrator commit `dc5c1f59f6d88fdf576e9f28e8cc47b6c60a1adc` (2026-08-03), working tree clean against it — see file list in §5 |

## 3. Headline numbers

| | Raw (N=122, every persisted event) | Deduped (N=46, unique question×response) |
|---|---|---|
| Agree | 111 | 42 |
| Disagree | 11 | 4 |
| **Inflation** (`debug_scorer`=True, canonical=False) | **9** | **3** |
| Reverse (`debug_scorer`=False, canonical=True) | **2** | **1** |
| `debug_scorer` batch accuracy | 59/122 = 48.36% | 22/46 = 47.83% |
| canonical batch accuracy | 52/122 = 42.62% | 20/46 = 43.48% |
| **Batch-level score delta (debug − canonical)** | **+7 rows = +5.74pp** | **+2 rows = +4.35pp** |

`debug_scorer` scores this batch **higher** than the canonical extractor by 4-6 percentage points,
consistent with the audit's prediction of a false-positive (score-inflation) risk, not a
verbose-penalty risk (that bug class was already fixed on both sides — B7 hardening on
`debug_scorer`, the 2026-07-24 incident fix on canonical).

**Extraction-strategy attribution** (which of `debug_scorer`'s 5 letter strategies fired, traced
by instrumenting a byte-identical copy of `_extract_multiple_choice_letter` to report its match
site, N=122 raw):

| Strategy | Uses (of 122) | Disagreements caused (raw / unique) | Direction |
|---|---|---|---|
| S1 explicit "answer/choice/option is X" | 0 | 0 | — |
| S2 letter alone on its own line | 73 | 0 | — |
| S3 letter at start of output | 0 | 0 | — |
| S4 `**bold letter**` | 3 | 3 / 1 | inflation (see §4, different mechanism) |
| **S5 last standalone letter, unconditional** | **30** | **8 / 3** | **6/8 (2 unique) inflation; 2/8 (1 unique) reverse** |
| No match | 16 | 0 | — |

**So the row's named mechanism (S5) is real and is the majority contributor**: it fires on 30/122
rows (24.6% of this batch) and is responsible for 8 of the 11 raw disagreements. Net effect *within
S5 alone*: 2 unique inflation cases vs 1 unique reverse case — consistent with the mechanism being
structurally noise-prone (any stray A–H token on a truncated or option-enumerating response has
roughly a 1-in-(number of options) chance of coincidentally matching the gold letter either way),
not a mechanism that is monotonically "more correct." The remaining 3 raw / 1 unique disagreement
(S4, bold-letter) is a **different** effect, described in §4 for completeness since it also
contributes to the debug-vs-canonical delta even though it is not the mechanism named in 1c-fix (c).

## 4. Mechanism evidence — the 4 unique disagreements, read in full

**Inflation, S5, `gpqa_Organic Chemistry_0308` / `gpqa_diamond_2305aa77f736`** (same underlying
generation, scored under two suite labels; expected=`C`). The response is **truncated mid-derivation**
by the token budget (`"...The problem specifies the"`, no terminal punctuation) and never states a
multiple-choice selection — it is reasoning through labeled chemistry intermediates called
"Compound A", "Compound B", "Compound C", "Compound D" as part of a synthesis pathway, unrelated to
the MCQ answer options. `debug_scorer` Strategy 5 grabs the **last standalone A–H letter anywhere**,
which happens to be a `C` from `"...that Compound C acts as the dienophile..."` — coincidentally
equal to the gold letter — and credits the row as answered correctly. Canonical declines outright
(returns `""`): no explicit marker, no bare final line (the last line is prose, not a lone letter),
and the single-candidate fallback also fails because multiple standalone letters are present
(`A`,`B`,`C`,`D` as compound labels). **This is the textbook case the audit named**: the model never
actually answered, and `debug_scorer` credits it anyway off a coincidental token match.

**Inflation, S4 bold, `real_suite_v1_0026`** (expected=`D`). The response is complete and states
`"The correct option is **D**."` — genuinely correct, genuinely a final answer. Canonical *misses*
it: its `(?:answer|option|...)\s*(?:is|:|=|\.|-)?\s*\(?([A-Ja-j])\)?` pattern requires the letter to
follow immediately (optionally parenthesized) but the response wraps it in markdown bold
(`**D**`), which the pattern's `\(?...\)?` group does not accept; the bare-final-line rule also
misses it because the final line has leading prose (`"The correct option is "`) rather than being
just the letter; and the single-candidate fallback fails because the response also enumerates all
four options (`A) 7.91  B) 6.21  C) 0.21  D) –0.21`) earlier, so four standalone letters are
present. `debug_scorer`'s Strategy 4 (`\*\*([A-H])\*\*`, which canonical has **no equivalent of at
all**) catches the bold-wrapped letter correctly. **This is a genuine `debug_scorer` capability
canonical lacks, not the named permissiveness bug** — worth carrying into any future unification
decision as a case where naively swapping extractors would introduce a regression, not just remove
one.

**Reverse, S5, `mmlu_elementary_mathematics_02287`** (expected=`D`). Response is truncated
(`"...= ("`) after walking through all four options in order (`"Option A: ...", "Option B: ...",
"Option C: ...", "Option D: ..."`) without reaching a stated conclusion. `debug_scorer` Strategy 5
grabs the actual **last** standalone letter in the truncated text, which is an unrelated `A` (from
prose after the option list, e.g. "...Adult Tickets..." context — not itself a standalone letter,
but a genuine standalone `A` appears later in the reasoning) — wrong, scores False. Canonical's
priority-3 marker regex (`(?:answer|option|choice|letter)\s*(?:is|:|=|\.|-)?\s*...`) matches
`"Option D"` directly because its separator group is *optional*, so each `"Option X"` occurrence in
the enumerated list is itself a match, and canonical takes the **last** one — which happens to be
`"Option D:"`, coincidentally the gold letter, since the model enumerated in fixed A→D order and D
is both the last-listed and the correct option here. **Neither extractor is reading the model's
actual final choice in this case** (there isn't one, it's truncated) — canonical's win here is also
substantially coincidental (any consistently-ordered enumeration would have its highest letter
mentioned last, whether or not that's the gold answer), not a demonstration that canonical is
immune to this class. This nuance is recorded so the reverse case is not over-read as
"canonical is simply more accurate" — both sides are exploiting incidental structure of truncated
responses in different ways; canonical's decline-by-default posture (§2/§3, 111/122 and 42/46
agreement) is what actually differs, not perfect judgment on the disputed 11/4.

## 5. Scope and limits, stated

- **N=122 raw / 46 deduped is what exists in the currently-persisted corpus for this suite/route
  slice**, not a designed sample — every `multiple_choice`, non-`scoring_verifiers`, non-empty-answer
  row across all 14 persisted eval-batch report directories that could be joined to a gold `expected`
  was included (0 excluded for join failure, 19 excluded for missing response text, 2,513
  `scoring_verifiers` rows excluded because the letter extractor does not meaningfully engage them —
  argued, not merely asserted, in §2). This is not the full historical eval record: only reports
  still present on disk under `orchestration/reports/` were scanned; older or rotated reports outside
  that tree were not searched, so a larger persisted corpus may exist elsewhere.
- **The 5.74pp / 4.35pp delta is specific to this 122/46-row slice** (mostly `gpqa`/`gpqa_diamond`/
  `mmlu_pro`/`real_suite_v1` calibration and baseline runs from 2026-07-23 through 2026-08-03) — it
  is evidence of the *direction and existence* of the bias at production scale, not a universal
  constant; a suite with fewer truncated/verbose responses would show a smaller effect, one with more
  would show larger.
- **Read-only throughout.** No source file was modified except the two 1c-fix (a) deliverables
  committed separately (`39ff247b`); no inference was run; no process was started, stopped, or
  signaled; no branch was switched. Working files (`persisted_mc_rows.json`, `pool_lookup.json`,
  `dual_rescore_FINAL_traced.json`, and the 122-row extraction) are scratch artifacts under
  `/workspace/tmp/b15-vendor-work/`, not committed — this document is the persisted record of the
  finding.
- **Source `question_results.*.jsonl` files used** (all at orchestrator commit `dc5c1f59f`, working
  tree clean against it):
  `orchestration/reports/ev_baseline_corev2_tier1/question_results.T1.jsonl`,
  `orchestration/reports/ev_baseline_corev2_tier2/question_results.T2.jsonl`,
  `orchestration/reports/ev_baseline_e7_tier1/question_results.T1.jsonl`,
  `orchestration/reports/ev_baseline_e7_tier1_diag/question_results.T1.jsonl`,
  `orchestration/reports/ev_baseline_e7_tier2/question_results.T2.jsonl`,
  `orchestration/reports/r3_current_arm_rebaseline_20260723/question_results.T1.jsonl`,
  `orchestration/reports/r3_current_arm_rebaseline_corev2_20260723/question_results.T1.jsonl`.

## 6. What this means for the 1c-fix (c) gated decision

This does not authorize unifying `debug_scorer` onto the canonical extractor — that unification is
still the separate gated SCORING CHANGE the handoff names, and it needs a re-score of the affected
*sealed* captures specifically (this artifact re-scores *unsealed* eval-batch persistence, a
different population), plus a decision on the S4 bold-letter capability gap (§4) so a swap does not
trade one bias for another. What this artifact supplies is the number the gate asked for: **on a
122-row (46 unique) production sample, `debug_scorer` scores 4.35-5.74 percentage points higher than
the canonical extractor would, and roughly three-quarters of the measured disagreements trace to the
named unconditional-last-standalone-letter mechanism** — the risk was real, not hypothetical, and is
now sized.
