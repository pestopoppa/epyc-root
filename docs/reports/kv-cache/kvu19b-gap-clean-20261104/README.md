# KVU-19b clean descriptive remeasurement

The native result records twelve full-run children, alternating unified and
split KV, with return code zero and verified child termination for all twelve.
Each child has at least 76 in-process positive own-PID VRAM samples with all
four selected ggml libraries mapped. The declared host affinity was 0–191 and
the children ran on CPUs 184–191; see `row.json` and `RESULT.json` for the
complete recipe and custody.

The split and unified median step times were 7.317 ms and 8.2615 ms,
respectively; unified was 12.9083% slower by the recorded median comparison.
This is a descriptive remeasurement, not a formal timing-gate verdict or a
causal attribution. The KVU-19b-gap parent remains open.

`keeper-grant.txt` preserves lines 795883–795885 from
`/mnt/raid0/llm/tmp/compute-flags/ws58-calendar-keeper.log`, including the
19:53:01Z resource snapshot and grant for MI210 and CPUs 0–191.

`RESULT.json` contains the complete child records and device samples. `raw/`
contains the original child stdout and stderr and the native belief sidecar;
the 24 stdout/stderr SHA-256 values match the native result. The copied grant
end, row, assets, specification and runtime hashes retain the original custody
references. `SHA256SUMS` inventories this capsule's own files.
