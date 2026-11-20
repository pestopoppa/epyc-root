# 2026-11-20 autokernel (wrap-up 5; covers work since wrap-up 4 root 83387347a and the cadence sweep a8b94439f)

## AK-DTREE program: P5 measured, negative, parked at the ceiling
- 27B `ak-dtree-batch-27b-gpu-20261119-r2` (fork `51b885a8c`, vs linear DFlash2 on the C14 store), 3 ABBA pairs, verdict FUTILITY_BELOW_BASELINE: auto 0.862 [0.845, 0.879], T12 0.706 [0.694, 0.718], T16 0.725 [0.682, 0.767] of linear tok/s.
- A3B `ak-dtree-batch-a3b-gpu-20261119` (fork `47f08e797`): auto 0.881, T4 0.697, T6 0.648. Oracle gate clean on every arm. AK-DTREE-2e and DTREE-P5 ticked (`5288aaab4`).
- Measured ceiling (P6 loss branch): best tree arm is 0.862x (27B) / 0.881x (A3B) of linear. Program PARKED, not closed: new box `AK-DTREE-2e-REOPEN` reopens 2e only if DTREE-0 (wvsk16 route; early smoke 1.16 ms/row at 12 rows vs 4.46 default; the paired row `ak-dtree0-wvsk16-gpu-20261120` itself read NO_EFFECT, slope 2.13 vs 4.07 with a wide default CI) or DTREE-0-Q8MF lowers the 12-16-row verify cost. P5 rows are republishable as `-r3`.
- Fork branch `llama.cpp-experimental-dtree-kernels-20261119`: `47f08e797` (H15 conv fusion wrote outputs over its own inputs) and `51b885a8c` (HTTP 500, commit-after-sample).

## H15 champion bug
- Fix `41918e3a6` (fork `llama.cpp-experimental-h15-alias-20261120`, from C14 `eee3da838`); box CH-H15-ALIAS filed in `7b7712eb9`.
- C14 verify finished 09:14-09:38Z (`/mnt/raid0/llm/tmp/h15-c14-verify.log`, 0.8B Q8_0 `test-multiseq-ubatch`, GPU): fix build OK (worst max logit diff 0.510-0.584, tol 1.50); the UNFIXED C14 store fails `mixed` (seq 0 pos 27-35 differ, max |d| 1.67-13.83, `n_fail == 0` assertion). Reproduces on the champion store, fix cures it. Box stays open for the 27B np=2 decode A/B and the composite presence gate.

## YaRN 512K
- CPU row stopped and banked 09:36Z under operator directive; the 351K slot `/mnt/raid0/llm/cache/kv_slots/yarn-cy2-351k-20261120` is protected (KEEP markers, `guarded_rm` protected_paths).
- Rescoped to GPU `yarn-gpu-512k-20261120`: run 1 stopped on CPU-scale ETA priors and was filed inconclusive (harness defect). r2 has since FINISHED with PASS (`RESULT.json` re-read): resumed to depth 517,343, 510K probe needles 5/5, 16.5 tok/s; 400K probe 5/5, 20.2 tok/s; VRAM peak 41.9 GiB. Box YARN-GPU-512k is ticked. Commits `f9d72f2e9`, `1ed9b90cb`, `c8260c978`, `ad4bd8797`, `64cf3027c`.

## Other landed work
- Research tests: box AK-STATIC-REGISTRY-CGROUP-NLINK-FLAKE filed, tests 247 -> 1 flaky (`648774335`); root pin `ec5857e32`.
- Intake intake-2718..2746: two plan rounds; the operator rejected r1 over hardware-dismissal reasoning (memory updated); Stage 4 `43e2a69ec` (46 boxes). The NEW-12 hold was lifted for GGUF-RECIPE-SEARCH only.
- ROCm decision (operator 2026-11-20): STAY ON ROCm 6.2 for builds and production; profiling via the rocprofv2 ATT adapter. ROCM-PROFILER-DECISION ticked, ROCPROF-ATT-ADAPTER-1 now reads "route decided: adapter". Evidence: 2026-11-05 ROCm 10.1 A/B NO-GO; package `/mnt/raid0/llm/tmp/rocm72-decision-20261120.md`.
- Clock: DETM row approved and published (`b8edb46ce`); clock reclaim `c80dedbc3`.
- Pipeline fixes live: F2-F9, zombie pid (`b2cc849a4`), GPU-idle sub-quarter packing (`c0cf5d5a2`), holds.yaml fail-closed. The AK-FIXES-F2-F9 / AK-HOOKS-C1-C6 boxes belong to the pipeline session (churn-pipeline.md) and were not ticked here.

## Lessons (memory + docs)
- Build region claims; run programs to the deliverable (no mid-program operator checkpoints); reverse-engineer foreign-hardware principles (few-row MMQ) instead of dismissing a source on hardware grounds.

## Cleanup
- Removed leftover root worktrees `ak-dtree-file2-20261120` and `ak-dtree2-p5d-20261120` (clean, `git cherry` empty). `llama-dtree-kernels-20261119`, `llama-dtree-20261119`, `llama-h15-20261120` untouched.

## Deferred (named blockers)
- CH-H15-ALIAS 27B np=2 A/B and presence gate: needs the next composite build slot.
- AK-DTREE-2e-REOPEN: waits on DTREE-0 / DTREE-0-Q8MF-GATE verdicts.

## Wrap-up 6 (since 754a417ae)
- Tree-mask intake intake-2747..2751 (`1990329a5`, `f2b734c6c`; research seeds `3744ee460`). Compounded-gain seed review (research `0d86d13f9`); new memory rule on the compounded-gain threshold.
- AK-DTREE verify-cost program (`a7bf68d9c`, `9df7c2138`, `7abbd233a`, `7cb92ffd1`, `ecb837198`, `c58e570be`, `657455384`, `2777185ea`, `8f3d987d9`):
  | Item | Verdict |
  |---|---|
  | wvsk16 witness | NO_EFFECT (2.0 ms/row) |
  | Q8MF v1 | DROP |
  | Q8MF v2 (5ccc76716) | NO_GAIN by rule; W16 -11%; slope 0.42-0.46 ms/row, intercept is the blocker (V2 GEMMs ~0.7 TB/s) |
  | ATTN-SHARE | OPEN (gv_fattn served; FA 2-9% of marginal cost) |
  | ATTN-ROUTE v1 (888470ff3) | LOSS (+1.2-2.4%) |
  | A3B MMVF=8 | KEEP_CANDIDATE (-18 to -21%, 1.28 ms/row) |
  In flight under a new driver: Q8MF-V3, ATTN-ROUTE-V2, GDN-ROWS.
- DTREE-ATTN-NP gated on bb's shared-prefix measurement (~0); bb box PREFIX-GROUP-DISPATCH (`f6eeaaba7`).
- PFXC prefix cache: boxes `c00cb899a`, `0e0e76b79`, `a9896834a`, `42eeb0b81`; fork llama.cpp-experimental-pfxc-20261120 (`62e955b9b`, `05c7c4ebf`, `947d1007d`). Probe r2: hit rate +3.0 pt, prefill 0.914x. Pending: r8 real-trace replay.
- Seed AK-H-MTP-DEGEN-1 (research `bfba8134e`). tool_call_parse_error contract (bb, orchestrator `1a10541b`); autokernel role file edit `5511efe5c`.
- Filler ak-q38fn-draftfa-window-cpu stopped for the build window (rc 75).
- Wrap-up ticks: DTREE-0-Q8MF-V2 and DTREE-ATTN-ROUTE build boxes (both landed; verdicts on their gate boxes).
