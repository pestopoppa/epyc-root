# 2026-10-22 CME-7T raw-reply capture and CME-7S rerun prep (3c4ca599)

Zero inference. No server was started, nothing armed.

## CME-7T (research `2f704ba4a`, on origin/main)
- `clbench_epyc_local/system.py` appends every parse-failed, empty-content or `finish_reason: length` reply to a JSONL sidecar: untruncated `content`, `reasoning_content`, `finish_reason`, `completion_tokens`, `interaction`, `attempt`, `error`, `will_retry`. Events: `parse_fail`, `empty`, `runaway`.
- `runaway` is its own event (plus a stderr line and `runaway_count` in the run artifacts) whenever a reply ends on `length`, whether or not the retry later validates.
- `run_clbench_epyc_local.sh` exports `CLBENCH_EPYC_RAW_LOG=$OUT_ROOT/raw_replies.jsonl`, next to `cache_hit_report.json`.
- Tests: stub server accepts dict replies; 3 new tests; 15 pass.

## CME-7S prep (job files outside git, under `/mnt/raid0/llm/tmp/fillers-3c4ca599/`)
- `gpu_recipe_lib.sh`: opt-in `GPU_RECIPE_EXTRA_ARGS` appended to the server argv (unset = unchanged). `s5-cme7-poker-smoke_job.sh` sets `-lv 4`, nothing else does. `bash -n` clean on both. No job using the lib was running (only the idle hsprof1 poller 881865); the edits were atomic replaces.
- Job: output dir `cme7-poker-out-s2`; COMPLETE only for report verdict PASS or MISS; counts runaway events and checkpoint lines in the log; refuses rc 7 if the shared research clone lacks `08ace05fd` / `2f704ba4a`. Backup `.bak-pre-cme7s-3c4ca599`.
- Finding: the shared clone `/mnt/raid0/llm/epyc-inference-research` was at `cd69f694c`, behind origin/main, so `install_into_clbench.sh` would have copied the OLD system.py. Not pulled (shared clone); its owner fast-forwards it before the grant.
- Proposed 18-cell FILLERS row and arm steps: `s5-cme7-poker-smoke.row-proposed-cme7s.md`, `arm_cme7s.sh.txt` (also archive the stale `grants/s5-cme7-poker-smoke.complete`, which makes `filler_run6.sh` exit). Row passes `validate_fillers.py --for-grant` with a live-PID stand-in.
