# 2026-11-09 Pipeline Management (pipeline-mgmt) wrap-up

## Pushed today
- epyc-root: 35d65c80d anchor marks; 87336043a stale text; ea41b82fd ratification RATIFY-INF45-P23 (TBD 1,2,6,12 ratified; 3,7,8 held); 3b1c932b0 INF-48 triage; 6b8edb465 RTG-22 batch; 9a8592083 ROCK-AITER packet A; 2420715b5 drops; 9ca5cc641 watchdog/LOOP-38/LOOP-57/core.bare watcher; c101886b1 RTG-100 churn split + INF-48 gate; 763f9ed9a + 82ef9c06d hub pin closure and LOG_DIR; 0f04ca9f6 AITER filing; 4ee4d377b dashboard stopped-row fallback (as reported by session).
- epyc-orchestrator: 94af001d P1-4; 0b342a07 / aa86437c P1-8.
- epyc-inference-research: 177692587 TBD tables; 64a287b83 C6 evaluator.

## Results
- AITER timing c9-r2: PORT_CANDIDATES. 27B M=2048 down is 2.45x slower than AITER i8. AITER-PORT-1 opened.
- c9-gemm-tile-select-20261109: TILE_CONFIRMED (15:33Z), filed pass this wrap-up with repo file_result.py `--no-reclaim --verdict-json` (installed copy lacks modules). Down M=2048: base (forced 64x64x64) 7843.98 us; best 160x256x64 3862.97 us = 2.031x, 256x160x64 2.02x; all 9 arms correct (rel_l2 <=1.2e-6, tol 3e-5), baseline determinism bit-identical; control gate_up forced 64x64x64 = 0.487x. AITER-PORT-1 box not ticked (needs real prefill >=1.05x); result noted under the box.
- c9 MMQ spill audit identical v10 vs C9; J=64 ~0% of 27B prod.
- Reliance proof VB-REFOCUS-NONEMPTY-READ-PROOF still OPEN: one-shot and r5 abstained; proof r3 rc=1 HostDegradedDuringCalibration.

## Next actions (for another session)
- Reaper diagnostic ak-q38fn-reaper-diag-c9-20261109 queued behind vidya-r18d r3 (~19:30Z): Pipeline must set ws58-keeper-state/reap-last into the future before it starts (reaping only); the row refuses without it.
- Keeper deploy: branch keeper-frozen-20261109, worktree /mnt/raid0/llm/worktrees/keeper-fixes-20261109 (c303970ee: republish guard, one-sample quiet path, LOOP-11, residency with Docker). Approved, reviewed, NOT deployed. Deploy via deploy_rowflow.sh --emergency at a grant-quiet gap, after AutoKernel's rows. Next churn_up starts the watchdog guard and core.bare watcher.
- C10 path after TILE_CONFIRMED: steps 2-4 (in-tree selection override, real-prefill A/B).
- Installed file_result.py lacks row_worktree / worktree_gate / keep_tail deps (use repo copy); 107 unfiled results.
- Open items: HUB-SUPERVISOR-STALE-ALARM; PIN-CLOSURE-CHECK; LR-8; RAM margin 64->100 GiB with ram_gib injection; smokes without FAIL record; drain ETA uses window end; disk-pause not named in IDLE-WHY; dashboard ready overcount of filed/parked rows; 85 dangling validator cross-refs; inf22-intake worktree (8 dirty paths, one digest to compare); Group A vidya adapters in worktree vb-belief-park-20261108.
- Rowflow2 shadow clock restarted 11-09T11:04Z; earliest cutover ~11-16.

## Self-reported errors
- Pushed a red pin-list test; removed a worktree after a failed push (recovered); overclaimed the dispatcher as root cause.

## Not done
Index pruning and wiki sweep (operator-cadence; deferred, nothing run).
