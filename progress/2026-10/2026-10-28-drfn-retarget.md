# Flash-Next drafter retarget — 2026-10-28

The current priority rollup still identified the retired Qwen3.5-122B DR-3 K2
certification as open. The operator's newer directive in the MI210 roadmap
explicitly retires that rerun and calls for a new Flash-Next verifier and low-bit
GPU drafter with new artifacts. Removed the obsolete open boxes, preserved the
historical closed results, added the distinct DR-FN1 task and updated its index
and generated priority basis. No old 122B result is transferred to the new task.

The public experimental IQ2 trunk linked in the handoff is a potential source,
not an established MI210 fit: its external PLE sidecar, runtime footprint,
compatibility and quality remain to be measured. No model was downloaded,
quantized or run for DR-FN1 in this checkpoint.

During this checkpoint the `index_state --check` and `backlog_priority --out`
processes initially started with affinity 0–191 at 23:01:34 UTC. Their captured
PIDs were rebound to sibling CPUs 170–171 before a 23:02:08 UTC clock check.
The unrestricted interval was disclosed to the parallel session; it overlaps
that session's INF-12 diagnostic window, with impact unknown. Subsequent
checks use the permitted sibling pair.
