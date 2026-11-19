# Prospective marker identity integration

This draft consumes client capture JSON, producer JSONL, and **normalized** profiler marker JSON snapshots. It composes the existing single-task request/task/row checks and clock-offset envelope intersection with a new requirement: each matched marker has positive integer `pid` and `tid` fields equal to its corresponding server clock-sync event. It fails closed on missing, duplicate, orphan, wrong-process, or wrong-thread markers. Output includes hashes and the offset interval, and remains consistency-only.

```
python3 -B verify_marker_identity.py client.json server.jsonl profiler-markers.json
python3 -B -m unittest -v test_verify_marker_identity
```

This is an offline consumer suitable for future finalized live-capture artifacts. Marker input schema is `epyc.nemo.profiler-markers.v1`, with `clock_domain` and `markers` records containing `marker`, integer `timestamp_ns`, integer `pid`, integer `tid`. This extends the older normalized draft format with producer identity; **no raw rocprof adapter or PID/TID semantics have been qualified**. Do not fabricate fields, treat these tests as a live capture, or accept the normalized input without independent profiler-version and normalization validation. This check does not authenticate records, prove same-run custody, qualify the clock offset or drift, verify graph attribution or reconcile tokens, and does not authorize a build or capture.

Copied dependencies come from `nemo-verification-link-successor`; only `single_task_binding.py` was extended to return its already-calculated clock constraints. Original r14 and reference producer packets were not modified.
