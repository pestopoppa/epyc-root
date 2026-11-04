# G3 trace scope and residency preparation

The R3 run remains UNKNOWN. Its trace contained attributed target verify dispatches as well as uncorrelated dispatches outside the target intervals; the earlier classifier rejected candidates if an uncorrelated dispatch appeared anywhere in the capture. `invocation_trace_v5.py` preserves those outside-scope events, rejects any uncorrelated dispatch inside a target invocation, and requires ordered, non-overlapping target scopes. It does not assign outside events to an invocation or change the original verdict.

`sysfs_residency.py` provides a prospective high-frequency sample bound to the MI210 PCI/KFD identity, captured PID birth, mapped HIP library and per-PID KFD VRAM, with device-wide VRAM separately reported. Timed analysis requires two distinct valid samples within the invocation and one enclosing the dispatch; missing identity, unstable clocks or insufficient overlap yields UNKNOWN. This is diagnostic instrumentation, not a speed or bandwidth measurement.

Six classifier tests, five sysfs tests, six timed-analysis tests and an active-STOP control passed. `g3-v10-v4-mi210-r5-20261104` passed GPU smoke with a launcher-sealed runtime-manifest digest. Its full native result remains pending.
