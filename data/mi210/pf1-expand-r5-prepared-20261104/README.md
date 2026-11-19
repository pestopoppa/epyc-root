# PF1 r5 same-frame refinement

The prepared packet evaluates L256/384/512/768 in one three-block frame. Previous r3/r4 windows disagree at L384 and are not pooled. The existing ±0.07 indifference band, ±10% disabled-control median, A0 strict NUMA placement, GPU-skew covariate amendment and in-window HIP/capture requirements remain in force. A point inside the band is unresolved; it can lie between a clearly-below lower bound and a later sustained clearly-above bound.

This is exploratory decision support, not a PF1/NPD gate or a causal explanation of A0 drift. Inspect publisher PASS separately before calling the row ready.

Static design controls: a ratio sequence [0.80, 1.00, 1.20, 1.30] yields coarse L256–512 while L384 stays unresolved; replacing the final ratio with 1.00 yields no sustained upper endpoint. No inference was used for these controls.

The canonical publisher reported PASS, but the captured plumbing record shows eight actual threads on CPUs 88–95 and an engine CPU claim 0–95. This does not meet the session’s four-CPU smoke limit; no throughput from the smoke is a pilot observation. The published source and grants were not altered.

A separate unsubmitted r6 correction selects four inherited CPUs, sets four benchmark and loader threads, and retains the r5 scientific frame and captured-PID stop cleanup. Its model-free checks pass. Keep it unsubmitted while r5 remains active to avoid duplicating the same measurement; see corrected-r6-packet.tar.gz. The full-run engine still claims the required quiet host.
