# m4-2b-champion-control (M4.2b): amendment — PAIRED C2 within one window (written 2026-10-24, BEFORE any compute)

Amends `PREDECLARATION.md` in this directory (sha256 `f8a4dce8447f47a59ff7ad5bded8f187ecc13bdafe773d31aed0f6743192b133`, not
edited; `job.sh` still refuses on its mismatch) and its `verdict.py` (sha256 `05fa4ef9d20f7ca2d92bb7f37d3f65b7e640c0cf7a80389e91ba4456d1fc7b8c`,
replaced by the `verdict.py` pinned in §8). It supersedes, for C2 only: §3 clause 5 (C-solo drift), §4 (the C2 rule), §5 (outcomes),
and the replacement-load placement in §2. Everything else in PREDECLARATION.md stands: binaries, server, protocol, harness, per-server
proofs, the 120 s VRAM drain wait, own-pid residency, the 60 GiB own-pid guard, claim class, placement. C1 and C3 stay as decided in
M4.2 (`VERDICT.json` sha256 `4b47d4b766fbb194a7ca69d04b72c8668a9a20b5982305f52c8bd79f580c2078`). Item:
`handoffs/active/gpu-serving-tie-in-program.md` → M4 → M4.2 → M4.2b. Nothing in this directory has run when this file is written; no
M4.2b number exists.

## 1. The operator decision (2026-10-24, "Pair within one load")

- Alternate champion and candidate as A-B-A-B within the SAME grant window.
- Judge C2 as a PAIRED ratio (candidate C2 / champion C2) per adjacent pair; decide on the pooled paired ratio.
- The 2.8 ms C-solo drift check becomes a per-pair FLAG, not a voiding condition.
- Keep the pass band 22.05x ± 10 % (19.845-24.255), applied to the paired ratio.

Why: 3 of the 6 earlier loads of this harness exceeded the 2.8 ms bar (PREDECLARATION §3, "known risk"), and inside the M4.2a load C-solo
went 282 → 885 ms. That is host drift, and the remedy is the ABA host-drift protocol: compare inside one window, alternating.

"One load" is read as one grant window. A paired comparison inside one *server* load is not possible: a load is one server process
of one binary, and two Qwen3.8-27B-Q8_0 + DFlash2 servers (46.6 GiB own-pid VRAM each, M4.2a) do not fit on the 64 GiB MI210 together.
So the design stays PREDECLARATION §2's: fresh loads CH, M4, CH, M4 in one window.

## 2. Which quantity the band applies to

C2 is the slot-order head-of-line ratio of one load: C2_L = median(B short TTFT) / median(A short TTFT). It has no units and lower is
better. The band 22.05 × (1 ± 0.10) is a band on that ratio: 22.05 is PB-HOL-1's off-path B/A (the champion lineage, base image,
2026-10-21), and ± 10 % is a RELATIVE tolerance (PREDECLARATION §4 basis: ~3 % host drift plus a 3-rep sample). The paired ratio
p = C2_candidate / C2_champion should be 1, not 22.05. So the band cannot be laid on p as written. The faithful transfer keeps both of
the band's numbers:

> **C2_paired = 22.05 × P**, with P the pooled paired ratio. This is the candidate's C2 put on the reference scale: anchored to the
> champion measured in the same window instead of to the champion measured on 2026-10-21. It is judged against the UNCHANGED band with
> the UNCHANGED M4.2a comparison code: 19.845 ≤ C2_paired ≤ 24.255. That is the same test as 0.9 ≤ P ≤ 1.1, the band's own ± 10 %
> around "equal to the champion".

The decision depends only on P and the band's relative width. The 22.05 anchor sets the units and cancels out of the test, so it does
not matter that PB-HOL-1 ran the base image and not exactly `141e4bcf5`. No new threshold is introduced.

The two candidate readings in the brief, and why neither is the decision quantity as stated:

- **(1) Both binaries' raw C2 judged against the band, plus their agreement.** The raw candidate C2 against the band is the M4.2a
  cross-day test again: in a window that slows both binaries alike (M4.2a read 25.2x), the candidate FAILs on window drift. That is the
  failure this design exists to remove. "Agreement" needs a tolerance that nobody predeclared, so it would invent a threshold. What
  (1) does answer correctly is a *window* question: is the champion's own C2 inside the band, so does this window look like PB-HOL-1's?
  That part is kept, but only to tell PASS from WINDOW_DRIFT_ONLY (§4). It never fails the candidate. The candidate's raw C2 is
  reported as NON-GATING.
- **(2) A paired difference C2_candidate − C2_champion.** Its expected value is 0, so neither 22.05 nor a relative ± 10 % applies; an
  absolute ± 2.205x would be a new threshold. A difference is also not scale-free: a window that inflates both binaries by a factor k
  inflates any real difference by k too, so the same code change would read differently in a slow window. A ratio cancels a shared
  multiplicative slowdown, and the band is relative, so the band's own scale is the ratio.

Chosen: the paired ratio on the band's scale (C2_paired = 22.05 × P). It answers "is the candidate's off path different from the
champion's in this window" with the band unchanged.

## 3. C2 rule (mechanical: `verdict.py`, §8)

Over VALID loads only (§4), in execution order:

1. per load: C2_L = median(valid B) / median(valid A) (the M4.2a quantity; unrounded inside the computation);
2. **adjacent pairs** = consecutive valid loads whose roles differ. The ABAB gives 3 pairs: (CH1, M4a), (M4a, CH2), (CH2, M4b). Per pair,
   p = C2_candidate / C2_champion;
3. **P = geometric mean of p over all adjacent pairs** (ratios are pooled on the log scale, so p and 1/p weigh the same);
4. **C2_paired = round(22.05 × P, 3)**. In the band → PASS or PASS_WINDOW_DRIFT; below 19.845 → FAIL_LOW; above 24.255 → FAIL_HIGH;
5. NOT_MEASURED if there are < 2 valid loads of either binary or < 2 adjacent pairs.

Why all three overlapping pairs and a geometric mean: under a window that drifts steadily by a factor d per load (both binaries alike),
the three pairs read d, 1/d, d, so P = d^(1/3). The two disjoint pairs alone would read d, and a median of the three would also read d.
So the overlapping geometric mean cuts the drift bias three-fold, which is the point of alternating. It is computed with no new parameter.

Direction: lower TTFT is better; a higher C2 means a longer head-of-line wait. The off path should reproduce the champion, so the test
is two-sided.

## 4. Load validity, the drift flag, replacements

- A load is VALID iff PREDECLARATION §3 clauses 1-4 and 6 hold, unchanged: harness complete, proofs (own port, graphs ON + HSA knob `0`
  from environ, own-pid residency ≥ 40 GiB, binary sha = the role's store sha), the job watcher's own-pid VRAM peak non-null and
  ≤ 61 440 MiB with no trip, ≥ 2 valid A and ≥ 2 valid B reps under the M4.2a predicate, one window id.
- **Clause 5 is now a FLAG.** A load whose median(end 3 C-solo) − median(start 3 C-solo) > 2.8 ms, or whose 6 solo shorts are not all
  answered (the drift cannot be measured), is drift-flagged. Every pair it belongs to carries the flag. A flag never voids a load or a
  pair, and never turns a PASS into a FAIL or a FAIL into a PASS. It only separates PASS from WINDOW_DRIFT_ONLY.
- **Replacement placement (changed):** an INVALID load is retried with the SAME binary IMMEDIATELY. It used to be appended at the end of
  the queue. The immediate retry keeps the valid sequence alternating, so the pairs stay adjacent in time. Still at most 2 replacements,
  and only while the grant holds the per-load need.

## 5. What each outcome decides

| outcome (`VERDICT.json` `outcome`) | C2 cond | M4.2 overall (with C1 PASS, C3 PASS from the pinned M4.2 VERDICT.json) | decides |
|---|---|---|---|
| **PASS** | PASS: C2_paired in 19.845-24.255, no pair drift-flagged, champion pooled C2 in the band | **PASS** | Tick **M4.2b** and **M4.2**: the candidate's off path equals the champion's, in a window that also looks like PB-HOL-1's. The M4.2a FAIL is attributed to the cross-day band and window, recorded, not re-judged. Next: M4's production gate, then the fold through the ledger (re-cut on the current champion first, fresh-tip rule). |
| **WINDOW_DRIFT_ONLY** | PASS_WINDOW_DRIFT: C2_paired in the band, but ≥ 1 pair drift-flagged and/or the champion's own pooled C2 outside 19.845-24.255 | **PASS** | Same ticks as PASS: the candidate is not different from the champion under this window, and the drift is shared, so it is not the candidate's. It also decides that the M4.2a 25.227x was window drift, and that the absolute 22.05x band is window-dependent, so any later off-identity check of this kind is run paired, never against the cross-day band. Record the flagged pairs and the champion's C2. |
| **FAIL_CANDIDATE** | FAIL_HIGH (C2_paired > 24.255) or FAIL_LOW (< 19.845), flagged or not | **FAIL** | The candidate differs from the champion by more than the band's ± 10 % in the same window. Pairing removes shared drift, so this is the candidate's. Tick M4.2b (it decided). File **M4.2c**: localise it as a build-level difference (the source diff is behaviour-equivalent: codegen / `common_params` layout; a rebuild of `141e4bcf5` with the same recipe as a second champion arm; a disassembly diff of `update_slots`; for FAIL_LOW also check that the default really is `slot`). M4 is not shippable as-is. |
| **INCOMPLETE** | NOT_MEASURED: < 2 valid loads of either binary, or < 2 adjacent pairs | **INCOMPLETE** | No claim. If the window ran its whole plan, it is not repeated automatically: a further window needs a new written diagnosis naming the invalidating clause (proofs / residency / guard / harness), from `loads.jsonl` and `diag.jsonl`. If the window was cut before the 4 planned loads, the next grant runs a fresh window (windows are never pooled). |

A decided C1 or C3 that is not PASS makes the overall FAIL/INCOMPLETE by the original combination rule (`outcome` FAIL_PRIOR). With the
pinned M4.2 VERDICT.json both are PASS.

NON-GATING (reported, never the verdict): per-pair p and flags; per-load C2, C-solo drift, solo-64K calibration, own-pid VRAM; the
champion's pooled C2 and the candidate's raw pooled C2 against the band; C2_paired over unflagged pairs only, under the 2.8 ms bar and
under 5 % / 10 % relative bars (what voiding would have decided); C2_paired over the two disjoint pairs only; the diagnostics sampler.

## 6. Known limits, recorded before compute

- **Residual drift.** A steady per-load drift d leaves P = d^(1/3). An identical candidate would read FAIL_HIGH only if d > 1.1³ = 1.331,
  i.e. the window slows by more than 33 % per load (about 15 min) in the same direction for the whole hour. M4.2a's worst in-load
  movement was B 71.7 → 85.5 s (+19 %). The selftest covers d = 1.15 and d = 1.25 (both PASS_WINDOW_DRIFT) and a +20 % candidate shift
  inside a d = 1.15 window (FAIL_HIGH).
- **Noise.** M4.2a's within-load B reps spread ± 10 %, the size of the band. Pooling 3 pairs of 3-rep medians reduces that but does not
  remove it. The band is the operator's and is not widened. The NON-GATING per-pair p values show whether a verdict rests on one pair.
- Pairs overlap, so the three p values are not independent. P is a point estimate judged against the band, not a test statistic.

## 7. Window sizing (ABAB, unchanged in load count)

The schedule is still four fresh loads, and the window is still ATOMIC: the job refuses (rc 3) a window that cannot hold the whole ABAB.
Per-load costs: the harness's own ESTIMATE with `--c-reps 3` is 1031 s, and its preflight refuses a load with < 1031 × 1.15 = 1186 s to
deadline. The drain wait is ≤ 120 s before EVERY load. The measured M4.2a load took 733 s, so LOAD_EST = 880 s (733 + 120 drain + 27
slack). The 4th load must START with NEED_LOAD = 1340 s to deadline (1186 + 120 + 34 slack). Hence ABAB_NEED = 30 s pre + 3 × 880 +
1340 = **4010 s**, plus the engine's 90 s deadline margin = 4100 s, rounded up to **`--min-window 4200` (70 min)**, unchanged. Grant at
least 75 min. 105 min is recommended, because an immediate retry now runs BEFORE the remaining planned loads, and without the slack a
retry can push the 4th planned load out of the window (then: no PASSED marker, INCOMPLETE, and a fresh window on the next grant).

## 8. Files and pins (this directory)

- `AMENDMENT-M4.2b-paired.md` (this file; `job.sh` pins its sha256 and refuses on mismatch; the value is in the job.sh header and the FILLERS row).
- `verdict.py` sha256 `b4d0404343392a60f75f87a66d01acc710cf21522ec9e910cc7af3c94987e6bb`: paired C2 rule; the drift is a flag;
  29-case selftest, run in every DRY. It includes the two required shapes: a drifting window where both binaries slow equally (in-load
  C-solo +603 ms; progressive × 1.15 and × 1.25 per load), which must not FAIL the candidate, and a real candidate shift of ± 20 %
  (quiet, drifting, and flagged), which must FAIL. It also covers the band edges at ± 8 % / ± 12 %, the immediate-retry alternation,
  and a non-alternating sequence that gives NOT_MEASURED. The 05fa4ef9… verdict.py it replaces is no longer accepted by job.sh.
- Unchanged and still pinned: `PREDECLARATION.md` `f8a4dce8…b133`, `pb_hol_1.py` `9452fdfd…0e26`, `diag_sampler.py` `f78cf1ab…0a59`,
  `precond.sh` `ac5d545c…818c`, the M4.2 VERDICT.json `4b47d4b7…2078`, both store binaries (`f0fe65c8…3882`, `901743a0…3e90`).
- No repo code: the candidate branch `experimental/m4-srpf-batch-fill-20261023` @ `c6ca031ac` is unchanged and not rebuilt.
  `../m4-srpf-pbhol-2a/` is not touched.
