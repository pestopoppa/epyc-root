# Tulving CAS scoring validity and offline re-score protocol (M-12f, absorbs M-12i)

Date: 2026-11-09. Source: `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260619_141212/tulving_score_rescored_20260914.json` (scorer v2, 20-chapter set, run 20260619_141212, role `ingest_long_context`). Model-free arithmetic over the stored `per_question` rows (456 rows); no bench release, no claim, no belief rows.

## Finding

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
| Exclude `nb_gt` < 2 (15 questions) | -0.2667 | 0.0704 |
| Only fully scored (8 questions) | -0.5000 | -0.0462 |

Latest-State F1 is 0.4075 (45 questions) in every variant.

Among the 15 questions with defined ordering, tau values are 0.0 (7), -1.0 (6), +1.0 (2).

## Conclusions

1. The 0.1593 headline is inflated, not deflated, by the zero-filled undefined questions: excluding them LOWERS CAS to 0.0704, because the defined tau values are negative. Direction matters: zero-fill acts as a floor at 0.
2. The tau leg has n=15 defined (n=8 fully scored): far too small for a headline; do not publish CAS from the 20ch set. Any CAS shown must carry the defined-question count and the partial count beside it.
3. Recommendation: report CAS with undefined questions excluded and the exclusion count stated, or report the Latest and Order legs separately. The paper's own convention for single-item questions was NOT verified here (no paper access in this pass); the choice stays open until that is checked. The code is unchanged.

## Offline re-scoring protocol (M-12i, merged)

- A re-score reads stored per-question rows only, runs the committed scorer at a named commit, and writes a JSON plus a one-line scorer version.
- It is a protocol result, never a back-filled claim tuple: no belief rows are emitted and the artifact is cited as "offline re-score of run X under scorer vN".
- Any re-scored figure states populated bins and counts (M-12g) and the defined/partial/undefined counts for chronological questions.
- Byte-identity check: re-running on the same rows reproduces the committed summary exactly (done for v2, 2026-09-14).
