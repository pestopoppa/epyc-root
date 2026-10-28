# HSF restore r3 and W3 READY packet checkpoint — 2026-10-28

This checkpoint records two diagnostic READY packets and their current limits. Neither packet closes its parent inference task. No handoff/index row, FILLERS table, queue, grant, production kernel, or diagnostic seal/receipt was changed here.

## HSF-5.P restore r3

The r2 normal grant failed at 2026-10-28 23:30:07Z (`rc=1`): run9 supplied `FILLER_CPUS=184-191`, but `job.sh` launched `restore.py` without setting that affinity. The failure is preserved under `/mnt/raid0/llm/tmp/codex-hsf5p-restore-r2-20261028`.

The separate successor `/mnt/raid0/llm/tmp/codex-hsf5p-restore-r3-20261028` validates the normal grant identity and executes Python under `/usr/bin/taskset -c "$FILLER_CPUS"`. Its exact same launcher supports `--smoke` under the exclusive GPU lock, using CPUs 184-185. Model-free tests passed for normal 184-191 affinity, rejection of wrong ID/CPU scope, smoke 184-185 affinity, no-grant run9 poller entry, and two restore response controls. The no-grant entry test verified a live `launcher up pid=` line and no job start. The in-flight cutoff fixture ran only in a separate packet copy with a fake HTTP server: STOP and absolute-deadline alarms each returned `rc=75`, wrote `partial=true`, and reaped the captured direct child. Descendants were not censused.

The exact `launch.sh --smoke` run at 23:36:03Z passed under `gpu-quiet` exclusive, with wall 183.28 s and 144,955.58 ms of measured generation across 6,144 continuation tokens. Three restore checks had equal positive saved/erased/restored/cache counts (4,116) and equal positive byte counts. Captured server PID 3460557 / start ticks 135305372 had 320/320 positive KFD, expected HIP mapping, and VRAM samples; maximum sampled VRAM was 52,093,886,464 bytes. Direct child exited 0 and was reaped; descendant census was false. This is a diagnostic restore-equality smoke, not the full profiled HSF task or parent closure.

The keeper-format candidate is staged as BACKLOG/ready=y with an unarmed launcher at:

- `/mnt/raid0/llm/tmp/compute-flags/ready/codex-hsf5p-restore-r3-20261028.json`
- `/mnt/raid0/llm/tmp/compute-flags/ready/codex-hsf5p-restore-r3-20261028.row.md`

Its source packet, result, cleanup, residency and log hashes are bound in the JSON. No launcher poller was started and no shared FILLERS/queue/grant state was edited; keeper admission and the scheduled run remain outstanding. r2 and the two short r3 attempts (35 s and 40 s, below the smoke minimum) remain preserved and are not qualifying smokes.

The isolated cutoff fixture used CPUs 184-191 from 23:44:25–23:44:28Z while UFH14 GPU work was active. Treat this interval as potential coactivity only; no impact inference is made.

## W3 canonical half-B READY packet

The staged packet is `/mnt/raid0/llm/tmp/compute-flags/ready/inf75-w3-canonical-halfb-20261028.json` with row `/mnt/raid0/llm/tmp/compute-flags/ready/inf75-w3-canonical-halfb-20261028.row.md`. Its same-launcher smoke log reports `rc=0`, 111.930 s total, six requests over a 66.971 s request span, result writing, and captured server cleanup. The smoke scope is a non-admitted two-primary-CPU, 512-context/ub64 CPU execution. It records `canonical_W3_observed=false`; therefore it is launcher/request-path evidence only, not canonical W3 census evidence. The staged packet is not a completed W3 inference run, and no matching live FILLERS row or keeper admission record was present in the current read-only check.

## Next actions and limits

- Keeper owns whether/when to arm HSF r3; after admission, the scheduled three-check grant run must be judged separately from the smoke.
- W3 still requires its actual canonical half-B run and native census result; the smoke cannot substitute for it.
- INF-33 checkpoint/chunk-logit parity remains open; CPU reference evidence remains CPU-only and GPU comparison is outstanding.
- No historical run was converted into a ClaimTuple. This note is a bounded observation of committed evidence and preserves its scope.
