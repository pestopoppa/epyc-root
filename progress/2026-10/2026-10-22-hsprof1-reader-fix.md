# 2026-10-22 hsprof1 reader filler fix (coordinator 3c4ca599)

Filler `s5-hsprof1-beam-reader` failed rc=1 13:11Z (`BEAMLoadError`: pyarrow not importable). No inference run; filler is re-queue-ready.

## Root cause (two defects)
1. `run_hs_prof1_beam_arm.sh` defaulted `PY` to the orchestrator venv (Python 3.11, no pyarrow); the BEAM parquet loader refuses without it.
2. The oddity: the traceback paths were the SHARED research clone because the job set `RESEARCH=<pinned worktree>` and then sourced `gpu_recipe_lib.sh`, which reassigns `RESEARCH=/workspace/repos/epyc-inference-research`. The pin check ran before the source (passed on the worktree); `run_phase` ran after it, so the arm script executed from the shared clone (older: no cloud judge, no belief producer). Not a .pth/PYTHONPATH/edit. Would have hit the judge phase too.

## Fix
- Research branch `hsprof1-belief-write` d72fc01da (pushed): arm script `PY` default = research venv (3.13.7, pyarrow 25.0.1; orch `src.user_modeling`, cloud_judges, run_benchmark, judge/score/belief_capture all import fine there), plus `PHASE=preflight` (pyarrow, `_orch()`, BEAM `extract_all` = 400 questions / 20 conversations, modules resolve to the tree, run_benchmark import, belief writer if EPYC_ROOT set). Negative test under the orch venv exits rc=5 with a clear message.
- Job `s5-hsprof1-beam_job.sh` (backup `.bak-pre-pyfix-3c4ca599`): variable renamed `ARM_TREE`/`ARM_COMMIT` (immune to the lib clobber), repinned to d72fc01da, `export PY=<research venv>`, preflight runs before `ram_admit` and server launch (exit 5 BLOCKED, no GPU grant spent).
- No pip installs into any venv. Poller 881865 had only a `sleep` child throughout.
