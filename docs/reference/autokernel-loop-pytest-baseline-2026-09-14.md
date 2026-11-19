# Historical AutoKernel-loop pytest baseline (2026-09-14)

This is a historical, host-specific baseline. It does not describe the current suite state.

At `origin/main` commit `7ea556f4`, the command `pytest scripts/kernel_rnd/autokernel/loop -q` reported **176 failed / 201 errors / 2509 passed**. The contemporaneous report classified the remaining failures as environmental on that host, including HTTP-child fixtures, live-store and port-bound tests, plus the `test_campaign_footprint.py` and `test_program_md.py` set. The two `test_matched_serving.py` cases `test_actual_matched_keep_validation_reuse_and_other_target_compare` and `test_post_keep_refresh_failure_preserves_keep_and_starts_no_candidate_compare` failed identically on that `origin/main` baseline and were reported as unrelated to floors.

The same host had `/tmp` blocked. Pytest therefore needed `TMPDIR` pointed inside `/mnt/raid0/llm/tmp`; otherwise pytest basetemp setup mass-failed. This is a recorded prerequisite for reproducing that host run, not a universal pytest requirement.

**Current status:** this record contains no rerun or current suite result. Recheck the suite at the exact source revision and host where current status is needed.

**Source:** [`progress/2026-09/2026-09-14-noninf-backlog-followups.md`](../../progress/2026-09/2026-09-14-noninf-backlog-followups.md), lines 260–267; tracked by R23-68 in [`handoffs/active/autokernel-rebuild-program.md`](../../handoffs/active/autokernel-rebuild-program.md).
