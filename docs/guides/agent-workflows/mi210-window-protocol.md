# MI210 window and handover protocol (AKX-ALL-15 / 15a / 15b)

Owner: operator-adhoc-ops-20261105 (took the lines from dormant workspace-ec, 2026-11-07). Docs only; nothing here arms or restarts anything.

## Cycle (manual window, ACK-with-fixes in review round 2)
1. Requester writes a schedule entry in `/mnt/raid0/llm/tmp/gpu-window/schedule.json` (duration within the standing policy cap, 60 min default; approved policy may allow longer) and a compute grant (`mi210_0`, plus q3 for AK rows).
2. The stack owner session runs `python3 -m src.runtime.gpu_window_executor open ...` from `epyc-orchestrator`. Reload ownership stays with the stack owner: the executor drains and unloads `:8083`; AutoKernel never does. `gpu_window park` alone only writes the window file and frees nothing.
3. The requester runs its GPU batches only inside the window, under gpu-quiet EXCLUSIVE, holding the device flock for the whole window.
4. Restore: the executor `close`, or the watchdog `tick` at `expected_end` + 10 min, reloads `:8083` and runs the serving proof (linkage plus a request). Restore refuses while the device is busy (foreign KFD process, gpu-quiet EXCLUSIVE, AK flock).
5. Receipts: the window id, the executor status file and the batch receipts go in the requesting handoff.

## Watchdog (F2)
`scripts/server/gpu_window_watchdog.cron` (orchestrator) ticks `gpu_window_executor tick` every minute and at boot. Evidence it is live: `/mnt/raid0/llm/tmp/gpu-window/mi210.json.executor-status.json` is rewritten every pass (`verdict ok`, `holder production`, `fresh_for_s 180`). Check: `generated_at_epoch` within 180 s of now.

## AK-requested windows (F3-F6, NACK until a third review ACKs)
- F3 `--compute-grant` verified against the coordinator grant file: orchestrator `4b871cc5`, on origin/main and in the shared checkout.
- F4 window-scoped flock, F5 compute-request sender and handshake, F6 `expected_end` abort: research `d6b1a5ac` on `feat/g1-ak-20261004`, not on research main; 70 tests pass there (`test_gpu_window.py`, `test_gpu_window_round2.py`, run 2026-11-07).
- Gate to ACK: a third review of `d6b1a5ac`, then merge, then one real AK-requested window with receipts.

## Publish-time guard (job.py:46 class)
`rowflow2.publish` refuses a row whose launcher or sibling `job.py` requires a GPU-quiet ancestor lock unless the row declares `gpu: exclusive` (or `quiet`). Test: `scripts/coordination/rowflow2/tests/test_pass4.py::test_gpu_quiet_guard_cpu_row_refused_at_publish`.
