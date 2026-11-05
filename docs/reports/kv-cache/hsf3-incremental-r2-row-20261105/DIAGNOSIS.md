# HSF-3 incremental successor preparation

Unpublished and unexecuted. Original grant ended rc=1 at 2026-11-04T23:48:24Z (started 23:48:21Z), step job-run; no result. No original stderr was located, so the exact thrown exception is unconfirmed.

A deterministic input/reader incompatibility is established independently: sealed prior.json includes a progress frontier of 69,820,239 bytes, while original census.py rejects files greater than 67,108,864 bytes before frontier matching. Metadata-only inspection found current /mnt/raid0/llm/epyc-orchestrator/logs/progress/2026-06-01.jsonl at exactly 69,820,239 bytes. That prior frontier cannot pass the old 64 MiB source cap.

Successor changes only that file cap to an explicit bounded 128 MiB, retains the prior SHA-256 seal, all stability and ambiguity refusals and the appended-record scope, and captures full-run stdout/stderr in out/. It does not weaken stable-read requirements, so live mutation can still cause refusal. No full census, tests, compute, or publisher smoke was run. Separate smoke output location is smoke/; out/RESULT.json remains absent. No gap distribution, independent replicate, source-wide absence claim, or HSF-3 completion follows.

The old row remains terminal: this is a new, unpublished scope with a larger documented source bound justified by the sealed prior geometry, not an automatic retry of its failed run. Launcher precondition refuses any existing out/ directory, enforcing one full attempt; smoke explicitly refuses every path under out/. Publisher-controlled fresh native smoke paths outside out/ remain supported.

Launcher correction: FILLER_SMOKE=1 now executes only the census synthetic branch and checks FILLER_DRYRUN_RESULT_PATH; it neither creates nor requires absence of full out/. Full execution alone creates out/ atomically with mkdir, captures stdout/stderr, and checks out/RESULT.json. runtime.sha256 now binds launch.sh as well as census.py and prior.json. No execution or publication performed.
