# 2026-10-21 queue-builders-3: five inference queue items made runnable (no inference run)

Lane worktrees `/mnt/raid0/llm/worktrees/qb3-{root,orch,research}` from fresh origin/main; shared clones untouched. Foreground tests under `nice -n 19`; tiny single-process tests (fake servers, CPU 0/1 taskset) ran UNLOCKED, no region-lock claim taken.

- HIL-15a/16a/18a: orchestrator `scripts/trace/hil15a_flagon_run.py` (+ `tests/unit/test_hil15a_flagon_run.py`), `07cfc175`..`f71480e6`. Mock-proved end to end; `auc_table` single-class-fold crash fixed.
- D-RI-PREVIEW-1: `scripts/benchmark/run_repl_preview.py`, `dripreview1_filler_job.sh`, root `artifacts/queue-builders-3-20261021/dripreview1/PREDECLARED.md`. Decided FILLER. Job proven under the real `filler_run.sh` with a stub region-lock and fake server.
- AKR-SG shakedown: research `run_paired_serving_ab.py`, `ab_server_pair.py`, `metrics_map.py`, 8 tests (`6a70318d8`); `paired_loadgen` zero-effect-is-decisive bug fixed.
- CME-7 smoke: venv `/mnt/raid0/llm/tmp/clbench-venv`, repo copy `/mnt/raid0/llm/tmp/clbench-epyc-repo`; runner underscore-flag bug fixed; full clbench poker quick_test ran against a FAKE endpoint (`76f5143d9`, `2e479ee01`). CME-5 sizing recorded.
- HS-PROF-1: recipe re-pointed to store build `gpu-20261020-dd3d9721c`; two-phase runner with scripted judge and `table` (`69cea0ae9`).
- Belief wiring: 4 README source rows + 4 VB tasks (VB-HIL15A-WRITE, VB-DRIPREVIEW-WRITE, VB-AKRSG-WRITE, VB-HSPROF1-WRITE). FILLERS.md rows updated (ready=y for all five).
- Not done, by design: any model run; arming the dripreview1 launcher (needs the pushed job in the shared clone).
