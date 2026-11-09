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

---

# 2026-11-09 evening, Pipeline Management (after e98017a0c)

## Landed (each verified on origin/main)
| Repo | Commit | What |
|---|---|---|
| root | 9d597d559 | Disk janitor skips scheduled reaps during a live quiet-host grant unless free disk is under 150 GiB (operator decision, D9-ack). Running copy `compute-flags/disk_janitor.sh` matches git (sha 516ea0cc...), pid 2889054 since 18:33Z. The skip has not been seen firing on a real grant. |
| root | 54a53fabc | Filing auto-supersedes only attempts that did not complete (operator decision, D9-ack). Installed `bin/churn/filing.py` sha equals origin/main. |
| root | 7c8436eaa | C10 gemmdown prefill KEEP (27B pp2048@d32768 1.127x vs C9), C10-FOLD-GATE box, V11-136..140. |
| root | ee6c87c69 | VB-REFOCUS-NONEMPTY-READ-PROOF reopened (operator). |
| research | bf94b0965 | c6-wire (7 commits, two independent reviews); 171 passed, 3 skipped after rebase. C6 admission has not run on real hardware. |
| research | ab91897a5 | C6 harness Q8_K activations; corpus inherits the rowflow-held GPU flock. |

Keeper: c303970ee was deployed through `deploy_rowflow.sh --emergency` at 20:27:22Z (`DEPLOYED.json`); installed `bin/rowflow/rowflow.py` equals the branch blob, not origin/main. Branch `keeper-frozen-20261109` is 6 commits ahead of merge base ca10e057c and 169 behind origin/main, and is unpushed.

## New finding: GPU smokes refused since the keeper deploy
Every GPU smoke that reached the residency check after the deploy failed with `VRAM never showed residency (max None B)`: c10-fold-gate, c10-gemmdown-correct-r2, vidya-r234-native-sweep-20261104b, race-eqv-gpu-r3, vidya-r18d-aa-wire-r4, c6-native-residency-r2 (20:55Z to 21:10Z). Before it, the same check read numbers: 13074432 B on failures at 16:48Z to 17:01Z, 414969856 and 549830656 B on the 20:27Z and 20:28Z passes. The c10-fold-gate job's own log shows `our_vram=1369 MiB` on three runs, so these look like false refusals by the deployed own-process-tree sampler (`sample_gpu_residency`, commits 33444b599 and c303970ee). Cause not proven. The failed rows are unpublished; none was touched here. c6-26-corpus-repin-r2 failed separately (job rc=1 after 10 s).

## Keeper branch: land on main?
Recommendation: do not land yet; decide after the sampler question is answered. For landing: main and the live keeper disagree today, so any main-based deploy reverts the live fixes; the only conflicts against main are a generated index file and one LOOP-11 line; the 61 tests in the four new files pass on the merged tree; the previous emergency (98f29180d) was landed. Against: the residency change appears to be refusing real GPU rows. Not pushed; operator decides.

## Operator decisions recorded
Reaper skip with disk override; failed-attempts-only auto-supersede; AFC no-tools rerun; OP-AK-HOLD exception for ak-q38fn-relianceproof-c9-20261109 (AutoKernel records it); INF-48 archives once AITER-PORT-1, ROCK-AITER, C6 wiring and the canary land, parked items moving to their program handoffs; C6 instrument reseal to C9; keep the 1.5B site model (a deliberate screening model).

## Row status at 21:14Z (read only)
Running: afc-p5e3-n30-q38_flash-r5, c10-fold-cpu-gate, c2-producer-replay-r2, sliders-phase0-fb5-coder30b-r4. `UNFILED-ENDED` 117 by queue_status (the session's last count was 122). Vidya ledger FRESH, lag 0.

## Session errors
A subagent's "model file absent" was repeated unverified; the file exists under `models/bartowski/`. A subagent set then unset `push.default` in the shared clone.

## Not done
Index pruning and wiki sweep: left for the owning session, which holds index edits. Open work is tracked as boxes under PIPE-EVE in `handoffs/active/churn-pipeline.md` and in `rocm-kernel-authoring.md`.
