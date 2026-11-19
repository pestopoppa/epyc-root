# E5 corrected-placement readiness — static manifest review

2026-11-02. The remeasurement and grid are owned by
[RE-MEASURE E5 Stage-B](../../handoffs/active/numa-placement-and-contention.md#track-batched-decode-measurement); this is
preparation, not a second execution or a measurement verdict. P1-2 in the GPU serving
handoff depends on that work. The authoritative scope excludes the W3 dense control.

The A7 placement manifest directory in `epyc-inference-research/data/batched_decode/`
`e5_manifests_a7_placement1/` contains the following JSON inventory. These are files,
not a count of valid decision-grade cells or a revised execution plan:

| Model group | Files | C1b files declaring multi-node cpusets with `numactl_policy=none` |
| --- | ---: | ---: |
| qwen36_q8_0 | 12 | 6 |
| qwen3_next_80b | 8 | 4 |
| gemma4_26b_a4b_q4km_mtp | 8 | 4 |
| qwen36_27b_q8 (W3, excluded) | 12 | 6 |

A read-only audit expanded each `instances[].cpu_list` against the live
`/sys/devices/system/node/node*/cpulist` map and inspected the declared
`numactl_policy`; it did not launch a server. For the C1b instances, the first mask
`0-47,96-143` spans nodes 0–1 and the second `48-95,144-191` spans nodes 2–3.
The [placement protocol](../../measurement/protocols/bench-cpu.md#p-bench-placement-1--numa-placement-and-concurrency)
rejects a multi-node cpuset with no `numactl` policy. An explicit defect control is
not thereby eligible for decision-gating placement claims. Do not automatically book
the inventory: W3 remains excluded by operator ruling, and the owner must reconcile
pruning, already-banked cells, manifest identities, and actual weights.

Before any placement row can be published, the owner must build a protocol-complete
execution plan and launcher. In particular:

The [A0–A4 preparation](gpu-serving-e5-a0-a4-preparation.md) spells out the
arm definitions and the unresolved recipe, anchor and runner inputs; it is not
a runnable grid.

1. Make the C1b policy explicit and correct per instance; preserve any defect
   replication as a separately labelled control, not a corrected-placement cell.
2. Drop caches and record cache state before every placement arm, pair cold and warm
   arms, and capture actual per-instance memory policy, `pages_by_node` and
   `local_fraction` during the run. A policy in JSON cannot establish that the
   launched process applied it or that pages were cold.
3. Specify the A0–A4 placement arms, interleaved execution, production acceleration
   recipe, `np=1` anchor gate, achieved concurrency and repetitions required by the
   ratified protocol. Retain per-stream and system-wide rates and the skip audit.
4. Qualify banked Gemma results against the same runtime evidence. The existing owner
   handoff records that its C1b files declare no interleave and that inspected C1
   artifacts do not independently attest the runtime policy and per-cell cache drop;
   the `decision_grade` field alone cannot establish placement compliance. Preserve
   the owner handoff's existing instruction not to rerun the banked Gemma group while
   its evidence is assessed; this review does not authorize a rerun.

This review does not validate a launcher, prove cache or page residency, authorize
compute, change a production placement, or modify the measurement protocol.
