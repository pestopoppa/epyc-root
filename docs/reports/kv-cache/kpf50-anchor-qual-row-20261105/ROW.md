Published row (four-CPU smoke PASS; full execution pending):

`KPF-50.ANCHOR-QUAL | CPU | kpf50-anchor-qual-20261105/spec.json | Qualify retained fixed-root anchor preflight on five sealed synthetic cases; distinct four-CPU partial smoke | publisher CPU grant; 300s reservation`

Launcher: `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf50-anchor-qual-20261105/launch.sh`

Completion ID: `kpf50-anchor-qual-20261105`

Expected full result: `full-results/RESULT.json`, status
`SYNTHETIC_ANCHOR_QUALIFIED`, partial=false, scan_complete=true.

The smoke exercised the positive and changed-root cases only. This row qualifies anchor-check
controls only and is distinct from existing KPF50 custody/window/maps/residency
qualification rows.
