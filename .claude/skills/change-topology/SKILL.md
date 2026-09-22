---
name: change-topology
description: Change WHERE a role runs — NUMA instances, cpu_shape, numactl policy, mlock, numa_pre_evict_gib, ports, and moves between CPU and GPU. Use when editing stack_topology.yaml or the stack_numa.py shape table, when a role gains or loses an instance, or when a role moves device. Invoked from stack-change phase 2; never run standalone against a real tree.
---

# change-topology

Sub-skill of [`stack-change`](../stack-change/SKILL.md). Read that skill's
[`DERIVATION.md`](../stack-change/DERIVATION.md) first — it says which files are
source and which are generated, and this skill only ever edits sources.

**It runs inside stack-change's scratch copy.** Phases 0–5 of the umbrella have
already happened; this skill is the transform for one class of intent. It never
touches a real tree, never signs, never brings anything up.

## What this skill owns

| Surface | What it owns here |
|---|---|
| `epyc-orchestrator/orchestration/stack_topology.yaml` | `numa_mode`, `numa_config.<HOST role>`: `instances` (`cpu_shape` + `port`), `placement_policy`, `numactl_policy`, `numactl_policy_instances`, `mlock`, `gpu_host_lane`, `numa_pre_evict_gib` |
| `epyc-orchestrator/scripts/server/stack_numa.py` | the shape table: `_CPU_SHAPES`, `_SHAPE_CLASSES`, and the invariant in `_assert_instance_invariants` |
| ports | every `instances[i][1]`, and its restatement in `launch_manifest.port_map` |
| device | which roles run on the MI210 — **through the topology, see below** |

It does NOT own which model a role serves (`change-role`), nor retirement
(`retire-model`), nor `serving_shape.n_ctx`/`kv_quant` themselves — but it is
the skill that must recompute capacity when those change, because capacity is a
*placement* question.

## The fact this skill exists to carry

> **The capacity report decides "is this a GPU role" from
> `shape_class == "gpu_host_lane"` in the TOPOLOGY — never from the registry's
> `device:` key.**

`stack_manifest.serving_shape_instances()` sets `"on_gpu": shape_class ==
"gpu_host_lane"` (`scripts/server/stack_manifest.py:1429`), where `shape_class`
comes from `NUMA_INSTANCE_SHAPE_CLASSES`, i.e. from the `cpu_shape` each
instance declares in `stack_topology.yaml`. The registry's `device:` is read
into the same row and then **not used for the decision**.

Both directions were demonstrated in-process on 2026-09-22 against the live
declarations:

- Flip `architect_general`'s instance class to `full` and the row reads
  `device='ROCm0' shape_class='full' on_gpu=False` — the role silently leaves
  the GPU leg of the capacity report and is summed against host RAM.
- Give a CPU role a `gpu_host_lane` class and
  `validate_serving_shape_capacity()` **raises**: *"GPU role(s) ['frontdoor']
  declare no `serving_shape.vram_non_kv_gib`"*. Nothing downstream compiles.

That raise is the good case. The bad case is revision 2's blocker (b) on
2026-09-22: **a device move authored in the registry alone** — `device: ROCm0`
set, topology untouched — produces a role the capacity gate scores against host
RAM while the launcher puts its weights in VRAM. A device move is a topology
edit **and** a registry edit, in one diff, or it is not a device move.

## Phases

### 1 — classify the intent
One of: `instance-count` · `shape-change` · `policy` (`numactl`, `mlock`,
`numa_pre_evict_gib`) · `port` · `device-move` · `role-loses-its-server`.
A `device-move` and a `shape-change` that introduces a **new** shape are the two
expensive ones; everything else is a data edit plus a recompile.

### 2 — if the shape is new, land all three places in ONE diff
`_CPU_SHAPES` · `_SHAPE_CLASSES` · the undersubscription exemption.

This session needed `NUMA_FULL_T48 = ("0-95", 48)`: the full 96-core cpuset run
with 48 threads. `_assert_instance_invariants` requires a non-GPU instance's
`-t` to equal the **physical** core count of its cpuset and fatals at import
otherwise, so a deliberately undersubscribed shape needs an explicit exemption
in the same change — `stack_numa.py` carries no exemption mechanism today, so
the shape and the mechanism land together or the module will not import.

A shape in `_CPU_SHAPES` and not in `_SHAPE_CLASSES` is the same failure one
level up: `NUMA_INSTANCE_SHAPE_CLASSES` builds by `_SHAPE_CLASSES[name]` and
raises `KeyError` on the first instance that names it. `scripts/topology_check.py`
asserts all three together.

### 3 — if it is a device move, re-measure VRAM
`vram_non_kv_gib` is the **KV-free resident** figure. It may not be copied from
`vram_gib` (KV-inclusive at some past context), estimated from file size, or
carried over from the other device. Measure it on a real load with
`/workspace/scripts/measure/vram_headroom_probe.py`, which separates the
**transient peak** (per-image mmproj buffers, per-chunk speech buffers, compute
buffer scaling with batch — remedy: reserve headroom) from an **allocation
ratchet** across identical cycles (fragmentation — remedy: none, it caps the
context you may declare). Reporting one as the other is how "we need headroom"
becomes a mechanism nobody measured.

### 4 — recompute capacity, both legs
`scripts/capacity.sh`. Per instance, per device. The host leg reports UNGATED
rather than passing when `/proc/meminfo` is unreadable; treat UNGATED as a
failure of this phase, not as a pass.

### 5 — recompute the contention recert
Any cpuset change invalidates the contention matrix for the affected regions
(§H of the alias runbook). Say which regions changed and queue the recert; do
not carry the old matrix forward silently.

### 6 — hand back to stack-change
Report the edited surfaces, the capacity delta, the recert requirement, and any
`UNVALIDATED` marker. The umbrella packages and the operator signs.

## Scripts — they assert, they do not advise

```bash
scripts/topology_check.py            # shape table, invariants, overlap, phantoms, device parity
scripts/topology_check.py --intent <yaml>   # also gates n_ctx changes on evidence
scripts/capacity.sh                  # both legs, per instance; non-zero on a failing or UNGATED leg
scripts/affinity_check.py            # LIVE affinity of every running instance vs its declared shape
```

Each exits non-zero with the specific violation. None of them start, stop or
signal a process; `affinity_check.py` reads `/proc` and `ps` only.

## Refuses

- **Overlapping instances of one role that could co-place.** Two instances of
  the same role **in the same shape class** whose cpusets intersect are always
  a defect: they are launched together, compete for the same physical cores,
  and the capacity report counts them as independent. The rule is per class,
  not per role, because `numa_mode: both` deliberately runs `frontdoor`'s
  `full` (`0-95`, :8070) alongside its two `half` instances (:8080, :8180) —
  all three were live on 2026-09-22 — and those halves are disjoint from each
  other. Full-vs-half intersection is the declared `both` shape; half-vs-half
  intersection is oversubscription with no name.
- **A device move without `vram_non_kv_gib` re-measured on a real load.** On
  2026-09-22 the 27B's live KFD reading exceeded declared non-KV + the
  server-reported KV by **3.71 GiB**, unexplained. The session refused to guess
  a replacement figure, and that refusal was correct: a guessed VRAM
  declaration passes the gate and fails at HIP allocation time, in production,
  during a load.
- **An `n_ctx` extrapolation without an explicit `UNVALIDATED` marker.** A
  context you have not served at is a hypothesis. It may ship, marked; it may
  not ship as a measured number.
- **A `numa_config` block for a role that no longer launches a server.** An
  alias that moved onto another host's process keeps no NUMA wiring. Leaving
  the block produces phantom instances in the capacity report — they consume
  budget that nothing allocates — and **8 declaration-parity violations** that
  block every later pipeline stage, one class per run. `topology_check.py`
  fails on any `numa_config` role that appears in another role's `shared_with`
  or has no `role_launch_meta` entry.
- **A shape added to `_CPU_SHAPES` alone.** See phase 2.
- **Editing a derived file** to make a check pass — `stack_priors.yaml`,
  `model_descriptors.yaml`, the procedure enums and the lean registry are all
  outputs. The staleness presents as a *content* error, which is what makes it
  expensive.

## Verifies

- **Live affinity, not just the topology hash.** `affinity_check.py` compares
  each running instance's actual `sched_getaffinity` mask to the cpuset its
  declared `cpu_shape` names. A matching topology hash proves the declaration
  did not change; it proves nothing about where threads ran.
- **VRAM sampled DURING first load**, not after. `llama-bench` and a settled
  server both make 0% a *normal* reading, so a post-hoc sample cannot see the
  peak that would have failed. Use the probe while the load is happening.
- **No phantom instances** in the capacity report: every `numa_config` role
  launches a server of its own.
- The capacity report is regenerated after the edit, not quoted from before it.

## TODO — outside this skill's scope

- `stack_numa.py` has no undersubscription exemption mechanism. Phase 2 asserts
  the absence loudly; the mechanism itself is an orchestrator code change.
  (audit §4.5, "one diff")
- `gpu_host_lane` restates the device that `device:` also declares. The audit's
  fix principle (§2) says the instance SHAPE should be derived from the role's
  declared device rather than restated in the topology; `stack_numa.py:255`'s
  own comment says the same. Until then this skill's device-parity check is the
  recompute-and-diff gate that makes the restatement legal.
