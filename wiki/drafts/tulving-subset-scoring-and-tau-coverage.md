# Tulving scoring: the subset IS the metric, and Kendall tau needs full coverage

**Category**: `benchmark_methodology`
**Confidence**: verified (local re-score of stored responses + the benchmark authors' own shipped
artifacts; zero inference)
**Date**: 2026-09-14
**Source**: EVL-10 M-12e, `epyc-inference-research` `dcb769c1`; handoff
`handoffs/active/episodic-memory-integrity.md` (M-12e); `intake-408#record`
**Folds into**: [Benchmark Methodology](../benchmark-methodology.md) (the scorer-subset defect class)
and [Memory-Augmented Models](../memory-augmented.md) (the 2026-06-20 Tulving baseline numbers)

## The defect class: a composite metric silently scored over the wrong population

`score_tulving_run.py` appended **every** scored question to the Simple Recall input list
(`simple_inputs.append(scored)`, unconditional at `:121` as of research `9e63af0c`). The Tulving
benchmark's Simple Recall Score is defined over the *recall* questions only — the rows whose `get`
column is `"all"`. The `latest` and `chronological` rows are the **Chronological Awareness** subset,
a disjoint population with its own metric.

The result was not a rounding error and not noise. It was a different quantity carrying the
published name: 90 of 456 questions were double-counted into a metric they are not part of, and
because Simple Recall averages *within* bins before averaging *across* bins, the failing
Chronological Awareness rows landed in bins 1 and 2 and dragged exactly two of the four populated
bins down.

**The general shape**, which is what to carry away: when a metric is a fold over bins or subsets, the
subset predicate is part of the metric definition, not an implementation detail. A subset bug is
invisible in every per-question artifact — each row's `f1` was correct — and shows up only in the
headline. There is no way to detect it from the data; you have to check the definition.

## How the definition was established (not from the paper prose)

The dataset ships the answer, and it is cheap to check:

| check | result |
|---|---|
| `epbench/data/result_lenient_all_book_200.csv` (the authors' 12-arm per-question results) | **548 rows** |
| 196-chapter `df_qa.parquet`, rows with `get == "all"` | **548 of 686** |
| the other rows | 69 `latest` + 69 `chronological` |

The `all` in `result_lenient_all_book_200.csv` is the **get style**, not "all questions". The
published per-question result file *is* the Simple Recall subset, so the subset is settled by
counting, not by reading.

## Third defect found by the same method: the bins key on EVENTS, not items

The paper bins by "number of matching events". The scorer binned by `len(ground_truth_items)`. The
parquet carries the authors' own bin labels in `bins_items_correct_answer`, so the basis is
recoverable by reproducing that column:

| candidate basis | reproduces the authors' bins |
|---|---|
| `n_chapters_correct_answer` (matching events) | **686 / 686** |
| `n_items_correct_answer` (ground-truth items) | 629 / 686 |

One answer item can be the answer for several chapters, so item count under-bins multi-chapter
answers. `nb_events` now rides in the prompt metadata and is the bin basis; the `nb_gt` fallback is
reported per run (`simple_recall_bin_basis`), never applied silently. **A column name that looks like
a synonym is not one** — `bins_items_correct_answer` is named after items and is computed from
chapters.

## Kendall tau over a partial match rewards emitting less

`chronological_tau` greedily matched predicted items to ground-truth items, then computed Kendall tau
over the matched indices **with no coverage requirement**. A model that emits 2 of 9 ordered items in
the right order scored **1.0** — a perfect chronology score for answering 22% of the question. The
metric therefore paid for withholding, which is the opposite of what a temporal-ordering score is
for.

It now fails closed: tau is 0.0 unless the matched set covers the FULL ground truth.
`chronological_tau_detail()` reports `coverage`, the uncovered `tau_raw` as a diagnostic that must
never be averaged into a headline, and a per-question `status` of `scored` / `partial` /
`too_short`.

## The corrected 2026-06-20 baseline (run `20260619_141212`, 20ch / 456 QA)

Re-scored offline from the stored responses — the scorer loads no model and opens no socket. The
pre-fix code reproduces the previously compiled figures exactly, so the comparison is clean:

| metric | as compiled | corrected | why it moved |
|---|---|---|---|
| Simple Recall Score | **0.5530** | **0.5684** | scored over 366 `get=="all"` questions, not 456; bins keyed on matching events |
| Chronological Awareness Score | **0.1593** | **0.1593** | unchanged on this run — see below |
| avg F1 | 0.4309 | 0.4309 | diagnostic over all questions; unaffected |
| by-retrieval-type F1, avg decode 17.27 t/s | unchanged | unchanged | — |

Attribution, so neither fix is credited with the other's effect: subset fix alone **0.5755**,
bin-basis fix alone **0.5402**, both **0.5684**.

**CAS is unchanged for a reason worth recording, not because the tau defect is harmless.** No
partial-coverage question on this run matched two or more items without covering the whole list, so
every raw tau the old code would have credited was already 0.0 (`_kendall_tau` of a <2-element list).
The defect is real and **latent**: 37 of 45 chronological questions are now labelled partial, and the
200-chapter set has ground-truth lists up to 9 items, where it will bite.

**A second CAS validity caveat, separate from the defect:** 30 of the 45 chronological questions on
this run have fewer than two ground-truth items (15 have zero), so ordering is undefined for them and
they contribute 0.0 to the tau leg. Two thirds of that leg is structurally zero. This is why CAS is
reported as a diagnostic and never as a headline until the metric's own construction is settled.

## Version the scorer, or the two numbers get compared

`score_tulving_run.py` now carries `SCORER_VERSION = 2` in its summary and its markdown. A v1 figure
and a v2 figure are different quantities under one name, and the belief-kernel write hook
(`tulving_episodic_capture.py`, SC67) **refuses** any row with `scorer_version < 2` for exactly that
reason. Re-scoring an old run does not promote it either: run `20260619_141212` never recorded which
arm it was (memory-off / retrieved / full book), so it stays pre-hook and emits zero claim rows.
