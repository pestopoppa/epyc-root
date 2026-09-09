# 2026-09-09 — adhoc session: qwen38-mtp community follow-up (PRs #75, #76)

Operator-directed. No compute taken, no benchmark rerun (explicit operator instruction:
"DO NOT rerun anything without my explicit permission"). All measured figures are yesterday's,
read from `/mnt/raid0/llm/tmp/maxperf-20260908/sweep.json`.

## Task 1 — should the champion max-perf numbers update sudoingX's table?

**Verdict: not as a main-table row; as a supplementary section in `sweeps/instinct-cdna.md`.**

PR #70 (merged upstream 2026-09-09 as `3097ca3`) is `probe.py` at `--parallel 1` on the MTP
self-draft path. Yesterday's numbers are our own server-side harness at np=4 on the DFlash2
drafter, champion `ef81196d5`. Different instrument, different drafter, different kernel tip —
not a faster measurement of the same quantity.

**Correction made in-session.** I first argued the maintainer's "a row nobody can rebuild breaks
the property that makes the table citable" applied. The operator challenged it; they were right.
`ef81196d5bdd4190b46dff4ae7eecc333a46c8ce` **is** public and rebuildable —
`github.com/pestopoppa/llama.cpp`, branch `ak/champion/llama-cpp-0db32c06e3e5`, confirmed via the
GitHub API. Only the *comparability* half of the objection survives. #70's tip (`9e18beb0`) was
private; this one is not, and the PR says so.

## Task 2 — PR #75, MI210 concurrency sweep (submitted)

<https://github.com/sudoingX/qwen38-mtp/pull/75> — supplementary section appended to
`sweeps/instinct-cdna.md`. No table row.

| slots (`-np`) | aggregate tok/s | per slot | p95 dev / 3 launches |
|---:|---:|---:|---:|
| 1 | 79.2 | 79.2 | 0.44% |
| 2 | 109.4 | 54.7 | 1.60% |
| 4 | 167.8 | 41.9 | 3.33% |
| 8 | 179.1 | 22.4 | 1.82% |

**Review before submission found four defects in my own draft. All fixed before it went out.**

1. **The prompt set differs per `np`** — see the finding below. Disclosed as note 1 of the PR.
2. **"Aggregate" is the sum of per-slot `timings.predicted_per_second`**, not a wall-clock batch
   rate. It deliberately excludes scheduling tail, so it flatters the number against any
   client-side instrument. Was unstated; now stated.
3. **My dispersion claim was false.** I wrote "grows with concurrency, 7.5x". p95 dev falls back
   to 1.82% at np=8, so it is **not monotone**. Restated as "np=4 is the least stable point
   measured", no trend claimed from four points at n=3.
4. Context length was missing (`-c 16384`, differs from the 32768 in the section above), as were
   the warmup and sampling parameters.

Also disclosed: the np=8 clock excursion (1695–1700 MHz on one launch, `clock_stable: false`).

Verified rather than assumed: VRAM conversions (33.1 / 34.5 / 37.7 / 43.1 GiB), the +6.8% and
93.7%-of-peak arithmetic, and that the DFlash2 draft model is the **same file** as #70's DFlash
arm (both `2,056,414,752 B`) — so the two sections are consistent on the drafter.

**Operator number check.** The operator quoted 167.1 aggregate / ~41.8 per stream. The np=4 sweep
point is **167.76** / 41.94 (n=3 launches). `167.117` is a different experiment — the R23-58 THP
OFF arm, n=24. Not two readings of one number. PR uses 167.8.

## Task 3 — PR #76, Quant column (submitted)

<https://github.com/sudoingX/qwen38-mtp/pull/76>. Operator-directed after I proposed a column and
argued against re-sorting; operator ruled **column AND sort by quant**, so both shipped.

- 41 of 68 rows named no quant in the row itself — but reading all 64 footnotes resolved **66 of
  68**. Only sudoingX's own two earliest rows have no quant recorded anywhere; marked `—`.
- Sorted by bits-per-weight ascending, ties keeping contribution order.
- Integrity checked **mechanically**, not by eye: the multiset of Baseline / With flag / n-max /
  Acceptance / Contributor cells is identical before and after, and all 68 card cells are
  preserved. Pure reorder plus one column.
- Distribution now visible for the first time: **45 of 68 rows are 4-bit tier** (22 UD-Q4_K_XL,
  17 Q4_K_M) against single rows for IQ2, Q2, Q3_K_M, NVFP4 and Q8_K_XL. The table is far more a
  4-bit table than it looked.
- Judgment call recorded in the PR: the A5000 footnote names both `Q4_K_M` and the `UD-Q4_K_M`
  that upstream later replaced it with; used `Q4_K_M`, the file the numbers were measured on.
- Evidence cited for why quant belongs in the table at all: the repo's own **open issue #39 §2** —
  same card, same context, same `probe.py`, UD-Q4_K_XL peaks at n-max 3 and a ~3.7bpw quant at
  n-max 2, near-identical acceptance, ~14% cost for copying the wrong n-max.

## FINDING — `calibrate_floor` fires a DIFFERENT PROMPT SET at each `np`

`scripts/kernel_rnd/autokernel/loop/serving.py:577` — `ex.map(one, range(recipe.np))` with
`_PROMPTS[i % len(_PROMPTS)]`. So `np=1` measures prompt #1 alone, `np=2` prompts #1–2, `np=8`
all eight. The prompts are deliberately distinct (no shared KV prefix, which is correct for
per-request work), but the consequence is:

> **Any comparison ACROSS `np` values is confounded with the prompt mix.** Yesterday's
> maximum-performance sweep is such a comparison.

**Precisely scoped — this is NOT a defect for the harness's designed use.** The autokernel loop
A/Bs kernels at a *fixed* np on the canonical recipe, where both arms fire the identical prompt
set and the mix cancels exactly. The confound appears only when `np` itself is the swept
variable. Against the prompt dependence measured on this very hardware in PR #70 (2.4x span
across three prompts at n-max 8), that is not a small caveat for an np sweep.

The np=4→8 turnover is large and monotone across all three launches at each point, so it is
unlikely to be a pure prompt artifact — but it was not controlled for, and the sweep cannot
separate the two. Disclosed publicly in PR #75 rather than left for a reviewer to find.

**Not filed as a task in `autokernel-rebuild-program.md`:** that handoff is owned by the INF-66
AK rebuild session and this session has no lane. Prepared text is in the wrap-up report for that
session to apply; a prompt-matched np sweep is the experiment that would settle it, and it needs
compute the operator has not authorized.

## Deferred, with named blockers

| Item | Blocker |
|---|---|
| Prompt-matched `np` sweep (fixed prompt set across all np) | Needs GPU seam + operator authorization; operator instruction this session was explicitly no reruns |
| MTP-path concurrency sweep on MI210 (stated as absent in PR #75) | Same — needs compute authorization |
| Quant for the two unresolved table rows | External: only sudoingX can confirm their own two earliest rows |
| PR #75 / #76 outcomes | External: maintainer review |
