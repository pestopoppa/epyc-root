# Tulving CAS scoring validity and offline re-score protocol (M-12f, absorbs M-12i)

Date: 2026-11-09. Source: `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260619_141212/tulving_score_rescored_20260914.json` (scorer v2, 20-chapter set, run 20260619_141212, role `ingest_long_context`). Model-free arithmetic over the stored `per_question` rows (456 rows); no bench release, no claim, no belief rows.

## Approved EPYC v3 definition (OP-M12F, 2026-11-11)

The operator selected **gold≥2, zero partial**. Prospective EPYC reports use scorer v3
(`epyc_v3_gt_ge2_partial_zero`): exclude chronological questions with zero or one
gold item; retain eligible questions with incomplete retrieval in the denominator
and give them tau 0.0. Latest-State F1 still uses all latest questions. Both legs
are higher-better. If either leg has no eligible questions, CAS is undefined
(`null`), with the available leg reported separately. This defines EPYC scoring;
the paper's singleton convention remains unverified.

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
