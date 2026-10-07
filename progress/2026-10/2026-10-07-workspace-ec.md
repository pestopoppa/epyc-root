# 2026-10-07 Wrap-up — workspace-ec (research intake: Q38FN on 2x DGX Spark, Stage 4)

## Summary

Stage 4 of the intake of the myllmbox 2x DGX Spark Q38FN recipe, applying the operator-approved Stage-3 rev2 (+5.0% go/no-go; "approved. Proceed to stage 4"). 26 intake entries (intake-1937 to intake-1962) are dive-verified with 268+ claim anchors; four tasks filed, zero checkbox flips, no index rows, no pruning, no wiki sweep.

Verified outcome: two-Spark aggregate bandwidth (546 GB/s peak, not pooled) is within 2% of our 537.6 GB/s; like-for-like (official 10-expert NVFP4, TP2) the independent median is 53.7 tok/s vs our 52.66; the 93/177 tok/s headline is a 5-of-512-expert healed checkpoint with MTP up to K=7 and a best-window peak. The remaining gap is streaming efficiency. The draft-head vocab trim is not a CPU lever (our B10).

## Tasks filed (4 new, 0 flipped)

1. **cpu-decode-roofline-program.md**: Q38P-1 (measure Q38FN MTP step bytes, expert union, tokens/step, streaming GB/s; parts split by timing need), Q38P-2 (after Q38P-1, schedule or decline B10's IQ4_XS head requant probe).
2. **mi210-big-model-and-acceleration-roadmap.md**: Q38P-3 (ROCm 10.1 value assessment, staged, reboot only inside the v11 window, +5.0% go/no-go; host fact: in-kernel amdgpu of kernel 6.14.0-37), Q38P-4 (vLLM-on-MI210 probe with bundled userspace; also the in-kernel-driver compatibility test).
3. **speculative-decoding-mtp-refresh.md**: note amendment under CAFE-3 only (controller priors, expert-union ordering, d sweep, RecoverSSM monitor); gates unchanged.

## Checklist-sync gate

Flips yours: 0 committed, 0 uncommitted (nothing completed in a handoff; the work was intake-index and plan work). New tasks: 4.

## Derived-actionables gate

Newly filed tasks 4; explicit declines 5 (vocab trim, 5-of-10 expert cut for now, draft-vocab coverage/prefix-cache alignment checks, 2-node TP/EP, adopting vLLM/SGLang as MI210 serving stacks pending Q38P-4). Written, not filed, by design: the physics-normalised comparison clause for C1 (knowledge retention, carried to the next wiki compile); a one-line correction to docs/runbooks/rocm-upgrade-checklist.md (TheRock lists gfx90a Linux as Release Ready on the 2026-10-06 page, not "Build Passing only", intake-1962#record); both are for the owning session or the operator-invoked /wrap-up since the approved plan did not authorise edits to the wiki or the runbook.

## Index

`INDEX_EDITS.md` (out of repo, /mnt/raid0/llm/tmp/intake-q38fn-cluster/) holds proposed Next-action cell text for INF-70 and INF-34; not applied. Only the generated index_state block changed (open count +4); `index_state.py --check` exit 0.

## README freshness

`check_readme_freshness.py` printed no warnings.

## Deferred to the operator-invoked /wrap-up

Index pruning (nothing seen that it would handle from this lane) and the wiki compilation sweep (hardware-optimization and inference-serving pages should absorb the Spark physics comparison and the ROCm 10.1 value-assessment facts).

## Evidence

Scratch, reports and dive artifacts: /mnt/raid0/llm/tmp/intake-q38fn-cluster/ (STAGE3_PLAN.md rev2.1, INTAKE_STAGE1.md, INTAKE_STAGE2.md, dive-*/, dive-s3/). Plan digest recorded in `.research-session.json` as stage3_filing.plan_sha256.


---

# 2026-10-07 (pre-pause) — workspace-ec full wrap-up before token-budget PAUSE

## Summary

Operator-invoked /wrap-up ahead of a PAUSE at 97% weekly token usage. Evidence copies: `artifacts/ec-wrapup-20261007/` (`SAVE_RESTORE_TEST.md`, `JETLONG_SMALL_RESULTS.md`, `ec-disk-inventory-20261007.md`).

## Jet-Long hybrid-input bug FIXED (e6ea79421)

Branch `llama.cpp-experimental-jetlong-hip-20261006`, commit `e6ea79421`. Root cause: `llm_graph_input_mem_hybrid::set_input` never filled the Jet-Long inputs and `can_reuse` never blocked reuse, so qwen35/qwen35moe above native read uninitialised indices, giving either a get_rows assert or SILENTLY WRONG attention. **Every pre-fix above-native result on hybrid models is INVALID.** New T4 tests (ub 1/4/16/64, tail, decode, IMRoPE+NeoX, q8_0+f16) all pass; real-model 27B at -ub 16 no crash. Gap: the synthetic harness bypassed the hybrid input class. Ticks: JETLONG-SMALL-UB-BUG.

## Save/restore pre-test on CPU 27B (fixed build, -ub 16, ctx-checkpoints 8, cache-ram 8192, DFlash2)

Evidence `artifacts/ec-wrapup-20261007/SAVE_RESTORE_TEST.md`.
- Check (2) first FAILED: v10 checkpoints only at n-4/n-16 of each prompt, so a full re-prefill.
- The PREFILL-ONLY boundary trick PASSED: 3556-token prefix, then Q1 prompt_n 58, Q1b prompt_n 74 (restored ckpt 3539), extension prompt_n 2219.
- Save (280.8 MB, 70 ms) and restore (36 ms) in a fresh server; extension prompt_n == delta 2203, byte-identical output, acceptance 33/41 in both.
- First observed hybrid prefix reuse. Follow-on: HYBRID-PREFIX-REUSE (465954bc0, kv-unified-stack-rollout.md). Ticks: JETLONG-SAVERESTORE-PRETEST.

## GPU 27B windows (not completed)

Operator authorised `jetlong-gpu27b-20261007T023630Z` (02:41-04:46Z). Window A opened 02:42Z and stopped :8083, but gpu-quiet EXCLUSIVE timed out after 600 s: AK lanes' back-to-back shared claims starve exclusive with FIFO off. :8083 restored by the executor. Rerun CANCELLED for the token budget; entry unused. Scripts updated to the prefill-only pattern with a 1800 s acquire timeout. New task GPUQUIET-WRITER-PREFERENCE.

## Small-model Jet-Long (Qwen3-0.6B, native 32k)

Evidence `artifacts/ec-wrapup-20261007/JETLONG_SMALL_RESULTS.md`. 1x: N 6/6, J 6/6. 2x: J 6/6, Y 5/6, X 5/6. 4x: Y 3/6, X 0/6, J not run (CPU too slow).

## Q38FN-cluster intake (Stages 1-4 by its subagent; 1dc782956, ade638969; intake-1937..1962)

Like-for-like parity: our CPU champion 52.7 tok/s vs 53.7 on 2x DGX Spark TP2 official NVFP4. Our CPU streams 137-174 GB/s vs 446.8 measured. ROCm 10.1 still supports gfx90a; host amdgpu is in-kernel (6.14), not DKMS; vLLM lists gfx90a at ROCm 6.3+. D1 (5-expert cut) declined. Tasks Q38P-1..4 owned by workspace-ec.

## Other filings

- HYBRID-PREFIX-REUSE filed and owned (465954bc0).
- cafe-llama tasks owned (38b5b4ef0); AK seeds injected by workspace-89.
- Standing-approval branch: epyc-orchestrator `feat/gpu-window-standing-approval-20261007` @ 7dfc4c32, WIP, pushed, **TESTS NOT RUN**. Ratify script `/mnt/raid0/llm/tmp/gpuwin-standing/ratify_gpu_window_standing_approval_20261007.sh` is NOT operator-ready (`__ORCH_FILE_SHA__` placeholder; needs the branch merged first). Operator approved a 180-min standing approval plus a workspace-ec consumer row. New task GPUWIN-STANDING-APPROVAL.

## Disk (section from unpushed shared-clone commit aeac9ab4e, verbatim apart from heading levels)

### Execution

Operator-approved deletion for workspace-ec executed. Removed 15 worktrees (verified clean, merged to origin/main) and 2 slot files. 7 worktrees skipped due to uncommitted changes or unmerged branches.

**Worktrees removed:** 15 (14.7 GiB projected)  
**Worktrees skipped:** 7 (dirty/unmerged)  
**Slot files removed:** 2 (CN.bin, CY2.bin from yarn-e1-20261004)  

**Disk freed:** 15 GiB (102G → 117G available)  
**Before:** 3.4T used, 102G avail  
**After:** 3.4T used, 117G avail

### Addendum (pre-pause)

Inventory `artifacts/ec-wrapup-20261007/ec-disk-inventory-20261007.md`. **INCIDENT:** two worktrees owned by workspace-89 (ratify-token-rules-20261005, token-rules-record-20261006) were removed because my inventory misattributed them. Both were clean and on main, so no data was lost; workspace-89 was told. ARCHIVE-FIRST items still on disk (tmp/ds41-specdec-recipe 4.4G, copy-spec-eval-20261006 1.8G). Local-only experimental llama.cpp branches are unpushed (jetlong-proto, jetlong-hip, specwidth, champion-specwidth candidate 8e597b701, kshift-probe, yarn-mscale).

## Shared-clone state

/workspace local main is 1 commit ahead (aeac9ab4e, progress only); a push was rejected and the merge was blocked by dirty files. Needs operator reconciliation; not a data risk (its content is carried above).

## Pending with workspace-89

Champion candidate 8e597b701 regression gates; FIFO lock default-on; AK GPU run 2 (EC_JETLONG_GPU_DONE touched).

## RESUME HERE (priority order)

1. GPU 27B Jet-Long windows: new entry, gpu-quiet writer-preference or a lane pause.
2. Finish standing-approval tests, fix the ratify script, merge, operator --apply.
3. HYBRID-PREFIX-REUSE correctness on :8070.
4. Q38P-1 measurement.
5. CAFE-1/2.
6. ARCHIVE-FIRST disk items.
7. Push or retire the local llama.cpp branches.
