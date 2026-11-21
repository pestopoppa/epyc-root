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

## Wrap-up 7 (since 5cef49e1b)
- PFXC-R8-REPLAY box `b1afde3da`; r7d real-trace replay in flight.
- Q8MF reuse boxes (root `92d253b50`, research seeds `8c32de012`). Box audit `8358514c2` annotated R22-2, draft-window and indexer results.
- AKX-P1d live replay PASS (`65b2a96c9`; box stays open: W4/W5/W6 uncovered, AKX-P1e). AKX-ALL-29.4 guardband r2/r3 inconclusive, r4 PASS and ticked (`815ac30c6`, `378f7e5d9`, `e7ad3456d`): n_half=325, alpha_obs_max 0.089, 0 NMSE failures; short-process residency proven by an in-process witness (narrower reading, disclosed).
- Canonical gpu_common: research `b018078ce`, `51ae8b2d8`; row_scaffold import root `60f04a96a`; follow-up to resolve from origin/main in flight.
- Q38FN draft window W4096 FAIL (+27% tok/s at 64k, -5.5% at 32k, acceptance gate failed; fork `3c80eb453`). Indexer top-k FAIL (-33 ms/step at 32k but greedy identity broken by tie order; fork `aaec7962a`). Follow-ups TOPK-EXACT and W8192/adaptive in flight.
- AK-DTREE: Q8MF-V3 NO_GAIN (A3 slope 0.23 ms/row, W12 47.8 / W16 49.8 ms vs wvsk16 53.0/60.7; op ~0.73 TB/s). ATTN-ROUTE-V2 both candidates LOSS. GDN-ROWS `ba89d5047` committed, gate in flight. HBM-CEILING box `34c36d2de` + repack fork `369fa2717`, row ak-dtree0-q8mf-hbm-gpu-20261120 queued. V4 composite branch llama.cpp-experimental-dtree-v4-20261120 in flight.
- Scheduler: pipeline partial-quarter fix `73f498cb2`. Indexer CPU row stopped for builds (already filed fail).
- Wrap-up ticks: DTREE-0-Q8MF-V3 and DTREE-ATTN-ROUTE-V2 build boxes (landed; verdicts on their gate boxes). No index row edits needed.

## Wrap-up 8 (since 203c3bb6b) — autokernel

- **HBM stream ceiling**: 1498.2 GB/s = 93.6% of 1600 (bs256, 4 waves/CU, unroll 4); standalone row refused by publisher (<5 min), number recorded on the V4 gate.
- **DTREE-0-Q8MF-V4 gate DROP** (filed fail; boxes `5bfb28c15`, `c0346cb50`, `5e8e9bf05`): correct 152/152; W1/8/12/16 X 32.1/43.5/53.2/61.0, V3 34.6/43.5/47.8/49.5, V4 38.0/61.0/95.9/108.4 ms. MMVQ load pattern does not carry to 16 columns. Receipt-ack added this wrap-up (receipt FAILED vs box DROP).
- **HBM-CEILING** (`f79ba2198`, `8ea44891a`): repack clears the bar; V3R/V3 op GB/s 1.13-1.26x on every 27B shape; V3R 850-983 GB/s flat vs MMVQ n1 1080-1190.
- **In-place repack KEEP** (fork `0689c70ee`, knob GGML_HIP_Q8_MF_INPLACE=1; gate filed pass, tick `e0df6d004`): 184/184 correct; 27B W8/12/16 V3I 40.1/43.5/44.1 ms vs X 44.3/53.3/60.9. Costs: W1 +14.5%, prefill +7.7%, VRAM +54 MiB.
- **GDN-ROWS gate r2 KEEP** (filed pass, tick `810837134`): 267/0 both arms; tree-verify GDN ms W16 4.76 -> 3.97.
- **PFXC r7d real-trace replay NEUTRAL** (filed fail; `17a9ca2ee`, stop rule `c2acfe186`): hit 92.97 vs 93.00%, prefill 0.99x; A2 proven; P3 is harness-side.
- **Measured tree acceptance** (P5 logs): 27B T12 +5.8%, T16 +11.0% vs chain (Infernix assumed +12/+17%); A3B T4 +0.7%, T6 +4.4%. At V3 cost the 27B tree is ~-4%.
- **DTREE-TREE-QUALITY** (box `caf9348ca`, notes `b0fd55606`/`2bf4c11d0`): sim validated; greedy best-first W12 +6.0%, W16 +3.66%; oracle 6.99. Greedy builder fork `74de2c3e7` + `fa9191562`. C16 r3 rows pending build claim (box stays open).
- **Lineage/tooling**: composite rebased on C16 (branch llama.cpp-experimental-dtree-v4c16-20261120); row_scaffold reads origin/main (`0b96e0a87`, research `41119de1b`); AK journal program.md learnings (research `86167b529`, `3ab8362e5`).
- **Memory rules added**: compounded-gain threshold; write the hand-back ledger before respawning.
- Follow-up to Pipeline: publisher withdrew row tf1-cpu-s1b-35b-c14-q1q2-20261120 as "superseded" during our publish.

## Wrap-up 9 (after fa2aa116a) — GDN-ROWS KEEP, greedy builder, r3 NOT_JUDGEABLE

- **GDN-ROWS gate r2 KEEP** (tick `810837134`): 267/0 both arms; tree-verify GDN ms W1/4/8/12/16 0.43/2.13/2.12/3.56/4.76 -> 0.31/1.86/1.86/2.59/3.97; llama-bench G1/G0 within noise.
- **Greedy tree builder**: fork `74de2c3e7` (common_dtree_build_greedy, LLAMA_DTREE_POLICY=greedy, test-dtree-greedy 288/288) + `fa9191562` (drafter/server wiring); v4c16 fast-forwarded.
- **v4c16 build fix**: llguidance OFF; build rc=0 at 21:48Z, test-dtree-ops PASS.
- **r3 published** (box `bde142ba3`); smoke 27B L chain 116 tok/s (r2: 86), A3B L 119.
- **r3 BOTH rows NOT_JUDGEABLE** (22:00/22:06Z): first greedy arm (27B G12, A3B G6) HTTP 500 -> row aborted. Cause: greedy-builder position bookkeeping bug (fa9191562). Result notes added to AK-DTREE-2e-REOPEN and DTREE-TREE-QUALITY (both open).
- **In flight**: fresh agent's r4 (no G arms, per-arm isolation) and the greedy position fix.
- **rowflow release verb live** (`466e6b97a`) after a hand-release incident (grant file edited by hand).
- **Stopped two stale agents** (Q38FN TOPK-EXACT/W8192 agent; superseded greedy-builder agent). Rows `ak-q38fn-draftfa-w8192-cpu-20261120` (granted/running) and `ak-q38fn-indexer-topk-exact-cpu-20261120` (queued) still need filing at verdict.
- **Memory rule added**: no hand edits to grant files; use the rowflow release verb.

## Wrap-up 10 (after 79f440a40): 22:2xZ-23:59Z

- **Overnight queue push** (machine dedicated): chainverify, sclk-detm, c16-fold gpu/cpu, H15 np2 A/B, H11-UNIQ, greedy-fix rows, Q38FN split-KV / idxk-cache / w8192 / topk-exact, q0 fills. Build lanes opened by pausing w8192 (STOP, rc75 resumable).
- **c16-fold-gpu PASS** (78948be46): 27B KLD 0.0, top-1 100%; Q38FN PPL 3.577; decode geomean 1.0447.
- **r4 tree rows** (C16+V3I+GDN-ROWS): 27B FUTILITY (T16/L 0.860, round-cost 1.319 vs break-even 1.134; kernel verify predicted ~1.10 -> server-level overhead). A3B FUTILITY. V3I chain ~7% faster than old path.
- **Greedy builder root cause**: prompt rollback by winner length after spec_draft swap; fix 15bec7cd0 + regression test.
- **LSA CPU sparse op gate KEEP_OP** (ae985eb95): op 3.97x at T24; e2e ceiling 27B 32k 6.0% f16 KV. Impl milestone 1 on fork lsa-cpu-sparse-20261120 @ 3dd113132.
- **u3-variance PASS SIZE_OK_POWER_LOW** (d45a9ac66); **draft-splitkv r3q0 inconclusive** (640189bb9: draft FA -24%, tok/s +5.3%, numerics change -> needs 27B-anchored KLD rule and 48t rerun).
- **QDEC-CPU-MULMAT** closed (ticked this wrap-up): Q6_K error is the deliberate Q8_0_R8 repack, kept per speed>correctness; IQ3_XXS fixed by 17d092de0.
- **Pipeline fixes**: stale build-wait records cleared (5dc723189), LSA auto-tick dup (0166ee63a), C16 SHA typo in fold jobs fixed; granter any-of bug seen (q1,q2 granted q0).
