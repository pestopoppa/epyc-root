<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. This file is review material outside
     MEASUREMENT.md and its ratified annexes. An agent cannot add it to the
     protocol registry, amend Annex B, or create a ratification receipt. -->

# Proposed P-BENCH-NUMA-TP-1 — CPU NUMA Tensor-Parallel Falsification

**Status:** human-review draft; produces observations only until ratified
**Prepared:** 2026-08-20
**Proposed family:** Annex B / CPU bench
**Metric directions:** decode tokens/s ↑; subgraph time and `AllReduce` latency ↓;
quality error and rank imbalance ↓
**Consumer:**
[`CPU-TP-GRAPH`](CPU-TP-GRAPH.proposed.md)

## Proposed registry row — review text only

| Protocol | Scope | Metric | Status | Annex |
|---|---|---|---|---|
| P-BENCH-NUMA-TP-1 | NPS4 TP reopen profile, repeated `AllReduce`, paired FFN/block/full-model TP | decode tok/s ↑; latency/share ↓ | 📋 proposed, NOT RATIFIED | this draft; if accepted, append/version Annex B |

This row is not an edit to `MEASUREMENT.md`. Ratification must use the existing human-only,
atomic policy transaction and bind the final runner, stopping-rule and evidence-schema hashes.

## 1. Authority and composition

This proposal adds only the experiment-specific contract. It composes with:

- `P-BENCH-1` for the canonical single-instance CPU decode anchor;
- `P-BENCH-2` when a production-shaped multi-instance claim is made;
- `P-BENCH-PLACEMENT-1` whenever affinity, memory policy, mmap mode, instance count or slot
  concurrency changes;
- the core claim grammar and durability rules in `MEASUREMENT.md`.

Until ratification, every output is labelled `OBSERVATION [P-BENCH-NUMA-TP-1-DRAFT]` and cannot
gate keep, close, proceed, deploy or promote. Historical April concurrency data may inform
experiment ordering but may not be retro-certified.

This protocol authorizes no reboot, package installation, production-tree mutation, index edit,
production deployment or AutoKernel campaign mutation.

## 2. Fixed experiment identity

Every campaign manifest binds before the first measured sample:

- production anchor branch/commit/version and binary/shared-library SHA-256s;
- experimental commit/tree cleanliness, compiler, flags, binary/shared-library SHA-256s;
- model absolute path, size, SHA-256 and a retained GGUF metadata dump;
- prompt tokens, seed, context, batch, generated-token count, `-fa`, thread counts and all env;
- live CPU/node maps, rank CPU masks, rank memory policies and topology hash;
- phase, model, quant, transport type, collective algorithm and TP degree;
- campaign seed, complete arm table, sample count and final decision table;
- runner source/tree/SHA-256, tool identities and protocol receipt.

The production anchor for the initial campaign is v9
`0db32c06e3e550065b78311a6031ef3dd2c4f27c`, binary version 10125, re-attested after N25.
Any kernel, microcode, BIOS/NPS, production commit, compiler, model, recipe or runner change starts
a new stratum and invalidates cross-stratum deltas.

## 3. Exclusive ownership and host state

The runner must:

1. hold q0-q3 under one `region-lock` holder for the entire warmup/measurement/cleanup window;
2. prove no competing llama, AutoPilot CPU evaluator or other inference process overlaps the
   held regions;
3. record uptime, governor, frequency, `kernel.numa_balancing`, THP, swap, thermals and free memory;
4. refuse when uptime is at least one week until an operator-initiated reboot is attested;
5. record pre/post ownership and live affinity for every captured PID/TID;
6. record `/proc/<pid>/numa_maps`, `numastat -p <pid>` and node free memory during the phenomenon;
7. continuously retain `/proc/stat` and target process-group CPU deltas using the current
   Annex-B contention-window rules;
8. invalidate the complete block on ownership change, swap I/O, competing inference, rank loss,
   thermal/frequency excursion outside the predeclared band, or incomplete cleanup.

`drop_caches` and rewarm follow Annex B after a valid host-health preflight. A multi-day cache
reset is not a substitute for the one-week reboot rule.

## 4. Executable counter and tracing plan

### 4.1 Live availability audit, 2026-08-20

The following was tested without inference:

| Facility | Live result |
|---|---|
| Host/kernel | EPYC 9655, family 26 model 2; Ubuntu `6.14.0-37-generic`; NPS4 |
| Installed topology tools | `/usr/bin/numactl`, `/usr/bin/numastat`, `lscpu`, `/proc/*/numa_maps` |
| `perf` frontend | absent from PATH and common `/usr/lib/linux-tools*` locations |
| Other direct tools | AMDuProf, LIKWID, PCM and turbostat absent |
| PMU sysfs | generic `cpu`, `ibs_fetch`, `ibs_op`, `msr`; `amd_iommu_0..3`; no `amd_df` or `amd_umc` source |
| Permissions | `perf_event_paranoid=1`, `kptr_restrict=1` |

The installed topology facilities are executable and mandatory, but cannot establish DRAM
service rate or kernel-vs-barrier attribution by themselves. `numastat` measures placement and
NUMA event deltas; it must never be converted from page faults into a sustained-bandwidth claim.

### 4.2 Required perf recovery — no automatic system install

Before Phase 0, an operator or maintenance transaction must stage an Ubuntu tool matching the
running kernel (expected package name `linux-tools-6.14.0-37-generic`, plus its exact
dependencies), either by restoring the distro package or extracting it into an evidence-bound
read-only tool directory. Package availability is not assumed: failure to obtain and validate it
is a STOP. The runner must not run `apt install`, alter sysctls or enable a kernel PMU.

Record package/source URL or package provenance, package SHA-256, extracted file manifest,
`perf version`, executable SHA-256 and shared-library resolution. A `perf` binary from another
kernel/tool release is allowed only after all named-event probes below pass and its version skew
is disclosed.

The same host/kernel was historically calibrated with these core-PMU aliases:

```text
cycles
instructions
cache-references
cache-misses
branches
branch-misses
ls_dmnd_fills_from_sys.dram_io_all
ls_dmnd_fills_from_sys.dram_io_near
ls_dmnd_fills_from_sys.dram_io_far
ls_hw_pf_dc_fills.dram_io_all
fp_ops_retired_by_type.vector_mac
fp_ops_retired_by_type.vector_all
fp_ops_retired_by_type.scalar_all
```

That historical calibration is a prior, not a current probe. The runner must execute and retain:

```bash
<perf> version
<perf> list
<perf> stat -e cycles,instructions -- true
<perf> stat -e ls_dmnd_fills_from_sys.dram_io_all,ls_hw_pf_dc_fills.dram_io_all -- sleep 0.2
<perf> stat -e ls_dmnd_fills_from_sys.dram_io_near,ls_dmnd_fills_from_sys.dram_io_far -- sleep 0.2
```

Every requested event must produce a numeric count. `<not supported>`, `<not counted>`, permission
failure, missing alias or zero enabled/running time fails the preflight. Do not substitute guessed
raw event codes. A raw code is admissible only when bound to the AMD family-26 model-2 PPR revision
and independently cross-checked against the named alias.

### 4.3 Counter panels

Counter pressure previously caused multiplexing above roughly five simultaneous events. Use
separate fixed diagnostic repetitions, not a large multiplexed group:

- Panel C0: `cycles,instructions,cache-references,cache-misses`.
- Panel C1: `ls_dmnd_fills_from_sys.dram_io_all,ls_hw_pf_dc_fills.dram_io_all,cycles,instructions`.
- Panel C2: `ls_dmnd_fills_from_sys.dram_io_near,ls_dmnd_fills_from_sys.dram_io_far,cycles,instructions`.
- Optional C3: the three `fp_ops_retired_*` aliases, diagnostic only.

Each panel uses the same fixed decode workload and five repetitions. Panel order is randomized
from the committed campaign seed. Throughput claims come from unprofiled canonical samples;
profiled rates are diagnostic and are never pooled with them.

Reject a panel if any event's `time_running/time_enabled < 0.90`, if counts are non-finite, or if
the model does not generate the exact expected token count. Re-run the complete panel once after
a fresh host/cache reset; a second failure yields `mixed_or_unresolved` and stops Phase 0.

Derived diagnostics:

```text
IPC = instructions / cycles
demand_DRAM_bytes = dram_io_all * 64
prefetch_DRAM_bytes = hw_pf_dram_io_all * 64
DRAM_fill_proxy_GBps = (demand_DRAM_bytes + prefetch_DRAM_bytes) / measured_seconds / 1e9
far_fill_fraction = dram_io_far / (dram_io_near + dram_io_far)
cache_miss_fraction = cache_misses / cache_references
```

The 460 GB/s practical socket reference may be shown beside the proxy. It is not an IMC/channel
measurement. If the proxy exceeds 1.25× that reference or near+far differs from the independently
measured demand-all count by more than 5%, attribution is invalid and stops.

### 4.4 Kernel/barrier and TP-eligible share

Use two diagnostic instruments:

1. `perf record -F 499 -g --call-graph fp` plus a retained `perf report --stdio` for sample share
   in GEMV/repack kernels, `ggml_barrier`, scheduler and futex paths. Symbols/build IDs must
   resolve. Sampling overhead does not enter throughput.
2. A v9-based, trace-only experimental build that times each GGML node category and barrier wait
   with per-thread counters written after the token. It must not change work assignment,
   placement, tensor layout, arithmetic or synchronization. The patch and source diff are sealed.

The trace build is paired against its instrumentation-disabled self for five fixed blocks. If
median decode overhead exceeds 2% or output parity fails, node/barrier shares are descriptive only,
the classification becomes `mixed_or_unresolved`, and Phase 0 stops. Thus Phase 0 permits a
trace-only patch but no TP mechanism patch.

TP-eligible wall share is the sum of Q/K/V, attention-output, FFN gate/up and FFN-down node times
divided by complete steady-state token time. Samples must overlap decode; after-run snapshots are
not evidence of the phenomenon.

### 4.5 Attribution table and stop rule

All thresholds below are proposed policy values and require human ratification.

| Class | Required evidence |
|---|---|
| `dram_service_dominated` | median DRAM-fill proxy ≥70% of 460 GB/s; GEMV/repack sample share ≥70%; traced barrier/wait share <15% |
| `sync_or_scheduling_dominated` | proxy <70%; traced barrier/wait share ≥15%; far-fill fraction <20% |
| `remote_or_placement_dominated` | proxy <70%; far-fill fraction ≥20% **or** measured local page fraction misses intended placement by >10 percentage points |
| `mixed_or_unresolved` | more than one row matches, no row matches, trace overhead fails, or any required panel is invalid/unavailable |

Only `sync_or_scheduling_dominated` and `remote_or_placement_dominated` may pass the attribution
part of Phase 0. `dram_service_dominated` fails the reopen probe. `mixed_or_unresolved` is a STOP,
not a negative and not permission to proceed.

## 5. Phase 0 profile and headroom design

### Arms

- H0: current v9 canonical full-socket single-instance decode under P-BENCH-1.
- H1: four simultaneous rank-local instances, one per live NPS4 node, identical model/quant and
  workload, using a sealed experimental multi-instance runner.
- H2: H0 diagnostic counter/trace panels; these do not contribute to the rate comparison.

The H1 runner captures every child PID, live TID affinity, memory policy, `numa_maps`, start order,
per-instance decode tokens/time and a common wall bracket. It uses sequential model loading and
refuses if node free memory cannot satisfy all four copies plus the declared safety reserve.

The aggregate ratio is `sum(H1 per-instance decode tok/s) / H0 decode tok/s`. It is a necessary
triage ratio, never described as single-stream TP scaling.

### Fixed sample rule

- H0/H1: ten paired blocks, arm order randomized within each block from the committed seed.
- H2: five repetitions per counter panel and five trace blocks.
- No early stop and no post-hoc extension.
- Report median paired log ratio, median/MAD per arm and the fixed-seed 95% percentile bootstrap
  interval over paired blocks (100,000 resamples). This CI proposal requires ratification; it is
  not imported from another protocol by implication.

Phase 0 PASS requires the aggregate-ratio lower bound ≥1.50, TP-eligible-share lower bound ≥0.60,
and a permitted attribution class. Any other result follows §4.5 and the handoff decision table.

## 6. Phase 1 repeated-collective design

The standalone program owns four processes and q0-q3. It allocates and first-touches every buffer
under the declared node policy before timing. The primary Qwen2.5 shape is 5120 elements and the
exact sequence is 128 complete `AllReduce` calls (64 blocks × two). A sample is the complete
sequence, not one collective multiplied after measurement.

Algorithms:

- central reduce then broadcast;
- binary-tree reduce then tree broadcast;
- segmented reduce-scatter then all-gather.

Test FP32. A BF16/FP16 transport is a separate arm and is inadmissible until deterministic
conversion and full-model quality tolerances are specified. Every rank writes a per-round arrival,
start/end timestamp and checksum. A sample fails on rank skew, checksum mismatch, timeout, worker
loss or cleanup failure.

Run 30 samples per algorithm in a seed-randomized Latin-square order after five warmups. Report
complete-sequence p50/p95/p99, per-call distribution, rank idle fraction, CPU time and algorithm
memory traffic. No early stopping or extension.

Let `F = sequence_latency / H0_token_latency`, using paired session-level anchor samples.

- PASS: 95% upper bound for F ≤0.10.
- FAIL: 95% lower bound for F >0.15.
- INCONCLUSIVE: all other intervals; stop without tensor work.

This exhaustive rule replaces the former undefined 10–15% band.

## 7. Later A/B/C mechanism matrix

Phases 2–4 remain conditional on Phase 0 and Phase 1 PASS. Every comparison uses:

- A — exact baseline arithmetic and graph on the canonical v9-derived experimental binary;
- B — A plus only the four-rank executor, affinity, buffer and loader/configuration changes
  required by C; tensors and arithmetic remain unsharded;
- C — B plus physical TP shards, sharded activations/KV and exact `AllReduce` mechanism.

This separates configuration/executor cost from the sharding mechanism. A and B must pass output
identity. C must pass the phase's numerical/quality tolerance. The input-dimension shard must be a
physical quant-block-aligned representation; full-row reads followed by masking invalidate C.

For placement-sensitive full-model Phase 4, first execute P-BENCH-PLACEMENT-1 A0–A4 as the
current production reference matrix. Then execute A/B/C at the exact proposed TP placement. The
mechanism matrix supplements; it does not replace the mandatory placement matrix.

### Fixed throughput stopping rule

For every Phase 2–4 rate comparison:

- exactly 30 paired A/B/C blocks per model/quant/shape;
- arm order within block randomized from the committed seed;
- no interim decision, early stop, retry of selected samples or extension beyond 30;
- a failed environmental block is retained as INVALID and the complete block is rerun once after
  a fresh reset; a second invalidation stops the stratum;
- final statistic is median paired log-rate ratio with the same fixed-seed 100,000-resample
  percentile bootstrap interval, plus per-arm median/MAD;
- thresholds and decisions are exactly those in the handoff. An interval crossing two decision
  regions is INCONCLUSIVE and stops; collecting block 31 is forbidden.

Latency comparisons use paired log latency ratios with lower-better orientation. p95/p99 are
reported descriptively unless a separate ratified tail-latency gate is added.

## 8. Correctness, quality and reliability

- Phase 1: every collective result matches a deterministic single-process reference at the
  declared tolerance and checksum.
- Phase 2: FFN output compared elementwise with identical weights/input; report max absolute,
  max relative and norm error.
- Phase 3: complete block output and KV slice compared with baseline over retained real prompt
  states.
- Phase 4: deterministic generation comparison and PPL/quality under the applicable ratified
  quality protocol. If reduction order prevents bit identity, proposed maximum PPL regression is
  0.5%; this threshold requires ratification here or an explicit quality-protocol reference.
- Sustained soak includes clean startup/shutdown, coordinator loss, one worker failure and timeout
  cleanup. No broad process-name kill is allowed; only captured PIDs may be signalled.

Correctness, ownership, placement, cleanup or quality failure overrides any speed result.

## 9. Evidence bundle

Write to:

```text
epyc-inference-research/data/cpu_optimization/YYYY-MM-DD-full-graph-numa-tp/
  README.md
  COMPLETE
  SHA256SUMS
  campaign-manifest.json
  host-attestation.json
  tool-attestation.json
  stopping-rule.json
  commands/
  raw/
  perf/
  trace/
  numa/
  quality/
  summary.json
```

The manifest enumerates every file and SHA-256. Publication uses staging, validation, `COMPLETE`,
fsync, atomic rename and parent fsync. Scratch paths cannot support a claim. Record all samples,
including invalids, warmups and outliers; never replace a bad value silently.

Before collecting any decision-grade measurement, add the write-side Vidya source-adapter row and
handoff task required by repository policy. The adapter projects native records into the existing
`ClaimTuple`; it does not define a second grading ladder.

## 10. Proposed claim grammar

```text
CPU TP Phase <n> <metric> <value> <direction>, model=<sha256>, tp=4,
arm=<A|B|C|H0|H1>, blocks=<n>, date=<YYYY-MM-DD>,
[P-BENCH-NUMA-TP-1, attest <durable-ref>, receipt <ratification-ref>]
```

Counter-derived values must say `core-side DRAM-fill proxy`; never relabel them IMC/channel
bandwidth. Collective results must say `AllReduce` and name the algorithm/transport/message size.

## 11. Human ratification checklist

- [ ] Confirm proposed attribution thresholds and exact class precedence.
- [ ] Confirm fixed n=10 Phase 0, n=30 Phase 1/later phases, bootstrap construction and seed rule.
- [ ] Confirm the full decision table, including INCONCLUSIVE/STOP behavior.
- [ ] Confirm trace-only instrumentation and its 2% overhead gate.
- [ ] Confirm restored `perf` provenance and named-event preflight.
- [ ] Confirm Qwen2.5 mechanism model and Qwen3.8/second-quant control policy.
- [ ] Bind exact runner/schema/tool hashes and evidence path.
- [ ] Apply the protocol, Annex B/registry change and receipt through the atomic human-only
  transaction. Until that completes, leave this file marked NOT RATIFIED.
