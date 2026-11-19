# Tulving CAS scoring validity and offline re-score protocol (M-12f, absorbs M-12i)

Date: 2026-11-09; source-convention verdict added 2026-11-19. Source: `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260619_141212/tulving_score_rescored_20260914.json` (scorer v2, 20-chapter set, run 20260619_141212, role `ingest_long_context`). Model-free arithmetic over the stored `per_question` rows (456 rows); no bench release, no claim, no belief rows.

## Approved EPYC v3 definition (OP-M12F, 2026-11-11)

The operator selected **gold≥2, zero partial**. Prospective EPYC reports use scorer v3
(`epyc_v3_gt_ge2_partial_zero`): exclude chronological questions with zero or one
gold item; retain eligible questions with incomplete retrieval in the denominator
and give them tau 0.0. Latest-State F1 still uses all latest questions. Both legs
are higher-better. If either leg has no eligible questions, CAS is undefined
(`null`), with the available leg reported separately. This defines EPYC scoring.
The paper's exclusion of zero/single-item questions is now verified below;
this establishes agreement on eligibility, not equivalence of the complete scoring pipelines.

## Source-convention verdict (M-12f, 2026-11-19)

**Yes: the paper explicitly excludes both zero- and single-item ground truths
from ordering evaluation.** Appendix B.3.3, printed page 34, says to
“consider only the questions that are related to a ground truth answer of size
at least 2 (otherwise there is no order).” Table 4's caption, printed page 10,
also restricts ordering to questions involving at least two events.
Source: [arXiv 2501.13121v1, Appendix B.3.3](https://arxiv.org/pdf/2501.13121v1#page=34)
and [Table 4](https://arxiv.org/pdf/2501.13121v1#page=10), version 2025-01-21;
PDF SHA-256 `7c54fb94d5f09cd152eeb2ac2b10e4c5b547df2b4532753bf2420a92d73e262c`.

The released aggregation code independently confirms the exclusion at upstream
commit `892b22af097d4389d4f1b9cd47b5c51fdacd9bef`:
[`epbench/src/evaluation/evaluation_wrapper.py`, lines 235–236](https://github.com/ahstat/episodic-memory-benchmark/blob/892b22af097d4389d4f1b9cd47b5c51fdacd9bef/epbench/src/evaluation/evaluation_wrapper.py#L235-L236)
filters ground-truth index length greater than one before setting denominator
`N` (Git blob `75f0e3ecd0441bba1b293a0577cd6de97709fb49`). Short rows can reach
per-row judge evaluation, but are excluded from aggregate ordering coverage.

M-12f is resolved: OP-M12F's prospective EPYC v3 eligibility agrees with the
paper on this question, so excluded questions must not enter the ordering
denominator as zeroes. The historical 20ch result remains diagnostic, never a
CAS headline: v3 CAS is **0.07042657698264104**, with **15 eligible** ordering
questions, **7 eligible partials** assigned zero, and **30 excluded** short-gold
questions. These numbers come from the existing offline record below; no new
inference or re-score was run for this verdict.

The source paper also conditions order comparison on full item matching.
This finding does not establish equivalence of semantic matching, partial-case
aggregation, or composite leaderboard CAS. It does not deploy the payload
scorer into research or admit v3 under SC67; those boundaries remain as stated
below. The paper-convention uncertainty is closed rather than carried as an
additional prerequisite for the approved EPYC definition.

In particular, pinned upstream
[`epbench/src/evaluation/ranking.py`](https://github.com/ahstat/episodic-memory-benchmark/blob/892b22af097d4389d4f1b9cd47b5c51fdacd9bef/epbench/src/evaluation/ranking.py#L115-L165)
(Git blob `3c6089ff7d840ee4d18c910a89e70032c8ba9b5d`) also filters Latest bins
to two-or-more events and clamps the summarized ordering product at zero.
EPYC v3's all-latest leg and signed ordering leg remain explicitly local
choices; agreement on singleton exclusion does not put the two CAS figures on
one scale.

The lane-owned scorer payload
`proposed/m12f/payload/research/scripts/benchmark/score_tulving_run.py` now selects
v3 by default through both the Python API and CLI. Explicit `--cas-definition v2_native` is retained only to reproduce historical diagnostics; it is not the
prospective default. The installed research-repo scorer is not changed by this
ROOT commit. SC67 admission is separate: v3 plus `--belief-measurements` is
refused before reading inputs, creating outputs, or loading the writer. No
protocol identity, grade ladder, or measurement warrant is amended.

## Historical v2 finding

`compute_chronological_awareness_score` (`scripts/benchmark/tulving_episodic_adapter.py:543`, research repo) averages Latest-State F1 and mean Kendall tau over ALL `chronological` questions. Ordering is undefined for questions with fewer than two ground-truth items, and the scorer gives those tau 0.0.

| `nb_gt` | questions | `tau_status` | tau |
|---|---|---|---|
| 0 | 15 | too_short | 0.0 |
| 1 | 15 | too_short | 0.0 |
| 2 | 12 | 6 scored, 6 partial | |
| 3 | 3 | 2 scored, 1 partial | |

30 of 45 chronological questions are structurally 0.0; 7 more are `partial` (matched set did not cover the full ordered ground truth, fail-closed to 0.0); 8 are `scored`.

## Re-score variants (reproduced from stored rows)

| Variant | tau leg | CAS |
|---|---|---|
| As committed (all 45, undefined = 0.0) | -0.0889 | 0.1593 |
| **EPYC v3: gold≥2; eligible partials = 0 (15 questions)** | **-0.2667** | **0.0704** |
| Only fully scored (8 questions) | -0.5000 | -0.0462 |

Latest-State F1 is 0.4075 (45 questions) in every variant.

Among the 15 questions with defined ordering, tau values are 0.0 (7), -1.0 (6), +1.0 (2).

## Conclusions

1. The historical v2 0.1593 figure is inflated, not deflated, by the zero-filled undefined questions: excluding them LOWERS CAS to 0.0704, because the defined tau values are negative. Direction matters: zero-fill acts as a floor at 0.
2. The tau leg has n=15 defined (n=8 fully scored): far too small for a headline; do not publish CAS from the 20ch set. Any CAS shown must carry the defined-question count and the partial count beside it.
3. OP-M12F resolves the EPYC choice: use v3 and state the eligible, excluded, and eligible-partial counts. The v2 value is historical only; v3 CAS 0.0704 is still diagnostic on this small set. Paper equivalence is not asserted.

## Offline re-scoring protocol (M-12i, merged)

- A re-score reads stored per-question rows only, runs the committed scorer at a named commit, and writes a JSON plus a one-line scorer version.
- It is a protocol result, never a back-filled claim tuple: no belief rows are emitted and the artifact is cited as "offline re-score of run X under scorer vN".
- Any re-scored figure states populated bins and counts (M-12g) and the defined/partial/undefined counts for chronological questions.
- Byte-identity check: re-running on the same rows reproduces the committed summary exactly (done for v2, 2026-09-14).

## v3 application and reproducibility (2026-11-19)

[Offline diagnostic record](tulving-cas-v3-offline-2026-11-19.json): CAS v3
**0.07042657698264104**, latest F1 **0.40751982063194875** (45 questions), order
**-0.26666666666666666** (15 eligible, including 7 partials assigned zero).
Excluded: 15 empty and 15 singleton gold lists. Eight eligible questions have
full coverage. SRS arithmetic is unchanged: 0.5684169470017096 over 366 recall
questions; bin populations 150 / 150 / 48 / 18 / 0. This is arithmetic over stored
rows, not a fresh model evaluation or a full raw-response/gold replay.

The record binds the existing research input by repository path, source commit,
and SHA-256 `c640f010c113744f3e4b9bde8c87362a3c6577cae1354dfca9fb697afa9c33fe`;
it also binds the scorer implementation by SHA-256. No input rows are copied.
To reproduce, import `versioned_epyc_cas` from the payload scorer, load the
source JSON's `per_question` list, and call the function with rows filtered on
`get_style == "latest"` and `get_style == "chronological"`, respectively.
Only recorded native `nb_gt`, `tau_full_coverage`, `kendall_tau` and `f1` fields
are used. No sidecar is emitted.

Validation: all **65 tests pass** with `EPYC_ROOT` set to this lane, including
default API/CLI selection, zero/single-item exclusion, partial retrieval,
undefined populations, historical v2 comparisons, and refusal of default/explicit
v3 SC67 output. Run the three fixture modules under
`proposed/m12f/payload/{research/scripts/benchmark,candidate-ROOT}` with
`python3 -m pytest`; exact module paths are in `proposed/m12f/run-fixtures.py`.
Payload source pins were refreshed for the scorer and its regression tests.
