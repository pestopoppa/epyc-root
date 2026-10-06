# FIFO region-lock review (branch feat/region-lock-fifo-20261005, b4ee7473 4ac866b7 96c8ccb9)

Verdict: CHANGES-REQUESTED (one small test-hygiene fix; code itself sound, plus nits).

1. Baseline (under region-lock q1/role build, 656s queue wait behind AK): 122 passed, 1 FAILED (expected 123).
   Failure: TestNestingAudit::test_cross_role_mutex_off_does_not_falsely_serialize_different_roles.
   Cause: test env leak. `region-lock run` does os.environ.setdefault(ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT,"1") (region_lock_cli.py:64) and the child
   pytest inherits it; the test assumes it is unset (cross_role=False only declines to SET it, never clears it). Global mutex ON => roles serialize.
   Fix: monkeypatch.delenv / set "0" in the _lock_tmpdir fixture and in _cpu_worker when cross_role is False. NOT a NestedLockError. Tests use ORCHESTRATOR_TMP_DIR=tmp_path (prod lock dir untouched).
   Nesting detection did not fire on the pytest subprocess under the outer hold (different lock files/inodes, no overlap): no false positive. Form used: plain, under outer lock.
2. Non-vacuity: pre-branch (merge-base 6bb8d860): file cannot even import (ModuleNotFoundError src.runtime.lock_queue) => collection error, trivially "fails".
   Branch with FIFO forced off (plugin /mnt/raid0/llm/tmp/fifo-review/fifo_off.py patches is_fifo_enabled=False; tests otherwise hard-set EPYC_LOCK_FIFO=1): 7 failed / 12 passed.
   Fail: fifo_order_three_contenders, all_region_before_newer_single, nested_descendant_refuses_fast, gpu_quiet writer_preference, all_region_bench_before_newer_autokernel (cross-role (a)),
   claim_hold_child_reacquire_refuses_fast, cross_role_mutex_off (fails for the env-leak reason, not FIFO).
   PASS with FIFO off (NON-DISCRIMINATING, weak): test_no_barging_by_rerequesting_releaser, test_two_roles_alternating_cannot_starve_a_third_waiting_role (starvation test), test_no_deadlock_across_per_role_and_global_queues_three_contenders
   (plus ticket-mechanics unit tests and cleanup_on_timeout/legacy_coexists, which are expected to pass). Cause: re-request gap (50ms) >> 10ms poll, so a plain flock waiter wins anyway. Tighten (zero gap / many iterations).
   Base worktree removed (no --force); copied test file deleted first.
3. Ticket cleanup (throwaway /mnt/raid0/llm/tmp/fifo-review/sigtest2.py, temp lock dir): timeout path => ticket removed (finally). Normal exit => removed at acquire.
   SIGTERM waiter: no handler, finally does NOT run, file stays, but reaped on next read (pid dead) - OK. SIGKILL: same; reaped by pid-death; start_ticks mismatch and boot_id mismatch both verified reaped.
   BUG(nit-to-medium): an unreaped ZOMBIE (SIGKILLed child whose parent has not wait()ed) still passes os.kill(pid,0) and /proc stat, so its ticket stays "live" and BLOCKS younger overlapping waiters
   (verified: younger waiter timed out; cleared after parent reaped). Fix: treat state 'Z' (and 'X') in /proc/<pid>/stat as dead in ticket_is_live.
4. Nesting: raises only if (a) a ppid-chain ancestor (<=64 hops, stops at pid<=1) is an owner per /proc/locks of an overlapping lock FILE (role:<role>:<region>, global:<region> only when cross-role on and not shared, gpu_quiet.lock),
   or (b) an ancestor has a live ticket with overlapping resources. Name-blind: tmux/bash/AK-loop ancestors only count if they themselves hold/queue that flock. Different-role holders with cross-role OFF do not overlap.
   Real false-positive classes: shared-in-shared (ancestor holds gpu-quiet/role region SHARED, descendant requests SHARED: would not deadlock under flock, now NestedLockError; also covers writer-preference rationale only);
   multithreaded ancestor whose thread A waits/holds while thread B spawns an unrelated lock-taking child. Neither hits the audited scripts.
5. Scripts audited: no script nests region-lock inside a hold, except the known bench.sh pattern. dca-yarn-kernel-20261004/gpu_slot_dca.sh `slot` calls bench.sh (requests `--gpu-quiet shared`) and does NOT export
   BENCH_UNDER_GPU_EXCLUSIVE=1; if the main wraps `slot` in `region-lock run --gpu-quiet exclusive` it now raises NestedLockError (was a silent self-deadlock). Export BENCH_UNDER_GPU_EXCLUSIVE=1 in gpu_slot_dca.sh or require the caller to.
   Safe: stack-change-8083-batch run78.sh/run78_inner.sh (gpu-quiet exclusive only; python helpers gpu_window/decode_during_prefill/q38_t7/coherence_gate import no lock), apply_8_1*/regen3 (single build hold),
   q36-depth run_after_calib.sh + q36_depth_recipe.py (arm L strips the wrapper, "ONE claim"), yarn-e1 validate_all/selftest (under build 0-95; dry-run/selftest never launch a server), cpu_leg block.sh + yarn_cpu_leg.py
   (the wrapper `region-lock run 0-95 bench` is a sibling of nothing: OK ONLY if block.sh is NOT itself run under a region-lock hold - with FIFO on or off a nested hold would fail/deadlock), dca real_model_ppl_cpu.sh/run_repro (top level, not nested).
6. Other: no double-grant path found (flock stays the mutex; ticket removed after acquire; legacy clients just race). Dead head waiter cannot block forever (reaped by pid/start/boot), except the zombie case above.
   Clock: monotonic_ns is per-boot but stale cross-boot tickets are reaped by boot_id, so ordering across boots is moot. Lock dir: ORCHESTRATOR_TMP_DIR / fixed /mnt/raid0/llm/tmp, worktree-invariant; CLI _lock_dir and cpu/gpu qdir resolve to the same dir.
   Nits: (i) timeout_s is applied twice when deadline_s is None (admission wait then flock wait) => up to 2x timeout for plain cpu_region_lock; (ii) head-of-line: an older all-region ticket blocks a younger q0 request even if q0 is free (by design, costs idle compute);
   (iii) pid-namespace caveat: liveness uses os.kill/proc in the caller's pidns; clients from another pid namespace (devcontainer vs host) sharing the lock dir would reap each other's tickets;
   (iv) shared joiners get no `global:` key so a queued cross-role exclusive does not gate them (flock decides).
