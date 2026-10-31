# `shell_scan.lex()` migration — implementation report

## Changes

- Added `shell_scan.lex(command)` as the canonical quote/heredoc/comment stripping and command-segmentation API.
- Kept `shell_scan.segments(command)` as a compatibility wrapper with the same signature and return values.
- Migrated exactly `process_pattern_kill_scan.py`, `operator_apply_copy_scan.py`, and `pytest_worker_scan.py` to `lex()`.
- Preserved public scanner verdict functions, worker threshold (`>16` or `auto`), pkill-only hook blocking (pgrep remains allowed), copy containment/empty-corpus refusal, and shell-hook fallback/exit behavior.
- Added shared lexer controls, a baseline-vs-current scanner verdict corpus, comment false-positive coverage for the pytest guard, and end-to-end hook checks for real unsafe invocations after a heredoc.

## Semantic parity

The frozen pre-migration verdicts were generated from ROOT `12ffc57a5b3e38d7a63d0a3e666e435c99fa97cb` in an isolated temporary source tree and stored in `tests/hooks/fixtures/shell_scan_migration_baseline.json`. The parity test compares the three scanner verdicts on ten commands. The only expected difference is `pytest -q tests/ # pytest -n auto`: the old pytest scanner returned `auto`, while `lex()` correctly removes the comment and returns an empty verdict. Every other scanner verdict matches the pinned baseline, including malicious real commands after heredocs.

## Validation

- **129 passed**, no skips, in 4.83 seconds.
- Tests: `scripts/hooks/tests/test_shell_scan.py`, `scripts/hooks/tests/test_shell_scan_migration_parity.py`, `scripts/hooks/tests/test_process_pattern_kill.py`, `scripts/hooks/tests/test_operator_apply_copy.py`, `tests/hooks/test_pytest_worker_scan.py`, `scripts/hooks/tests/test_filesystem_containment.py`.
- R6 mutex: `/mnt/raid0/llm/tmp/compute-flags/prep-locks/32-33.lock`; effective CPUs `128-129` (physical region 32–33); `OMP_NUM_THREADS=1`.
- Captured pytest PID `673895`, `/proc` start ticks `157104637`; absent after wait. 50 RSS samples, peak sampled process-tree RSS `56,152,064` bytes; elapsed `5.077` seconds. Full process birth map and command are in `lane-validation-receipt.json`; raw output is `lane-validation.log`.
- Initial setup attempt used the base `/usr/bin/python3` and stopped before collection with `No module named pytest`; PID absence and its low RSS are recorded in `setup-refusal.md`. The successful run used the existing read-only `/workspace/tmp/pytestenv` interpreter; no environment was installed or modified.

## GitNexus and callers

GitNexus status at the start of this session was stale. Its wrapper refused re-indexing because cross-role global region locks were not enabled. Manual call-site search found the three migrated scanners, plus `drop_caches_write_scan.py`, `filesystem_containment_scan.py`, and `scripts/dev_harness/m2_guards.py` consuming the existing `segments()` API. The existing API remains callable. A stale-index `impact`/`context` snapshot reported LOW risk and 11 affected symbols for `segments`; current exact callers were checked by source search. No high/critical blast radius was found.
