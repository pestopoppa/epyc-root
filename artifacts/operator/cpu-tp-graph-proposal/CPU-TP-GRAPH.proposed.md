# CPU-TP-GRAPH — Full-Graph NUMA Tensor Parallelism Falsification

**Status:** PROPOSED / BLOCKED — not indexed and not dispatchable. Phase 0 remains an
INF-25 revalidation probe until every prerequisite below is satisfied. A new active
implementation handoff is permitted only after Phase 0 and Phase 1 pass.
**Created:** 2026-08-20
**Priority:** MEDIUM
**Categories:** hardware_optimization, inference_serving, numa_optimization, local_inference
**Workstream:** Inference Acceleration → CPU Optimization
**Standing owner:** [INF-25 / CPU1](../../../handoffs/active/intra-process-tensor-parallel-decode.md)
**Target host:** Beelzebub, AMD EPYC 9655, one socket, 96 physical cores, 192 logical CPUs,
NPS4, 12 DDR5 channels. All maps must be re-attested live.
**Kernel era:** `production-consolidated-v9` at
`0db32c06e3e550065b78311a6031ef3dd2c4f27c`; `llama-server --version` = `10125`.
The v8 commit `67a433bf45a8a091d83b4ea0b32ff0735fd51800` / version `10107` is a rollback
anchor, not the baseline for new work.
**Implementation rule:** create an isolated experimental worktree from the current frozen
production tip. Do not reuse the presently dirty `llama.cpp-experimental` checkout and never
modify or build in the frozen production tree.
**Evidence repo:** `epyc-inference-research`
**Protocol proposal:**
[`P-BENCH-NUMA-TP-1.draft.md`](P-BENCH-NUMA-TP-1.draft.md)
— NOT RATIFIED and not in force.

## Authority and related record

- [CURRENT-CAMPAIGN](../../../handoffs/active/CURRENT-CAMPAIGN.md) — current v9 production era and live
  opportunity-cost posture.
- [CPU1 active constraint](../../../handoffs/active/intra-process-tensor-parallel-decode.md) and
  [CPU1 completed ledger](../../../handoffs/completed/intra-process-tensor-parallel-decode-completed-through-2026-05-28.md).
- [N25 topology cutover](../../../handoffs/active/numa-topology-cutover-resume-20260730.md) — current blocker.
- [N24 placement defect](../../../handoffs/active/numa-placement-defect-20260730.md).
- [CPU2 shape-specialized decode](../../../handoffs/active/cpu-shape-specialized-gemv-decode.md) and
  [CPU24 counter attribution](../../../handoffs/completed/cpu-uncore-fabric-attribution.md).
- [NUMA_MIRROR closure](../../../handoffs/completed/numa-mirror-integration.md),
  [CPU15 expert parallelism](../../../handoffs/active/large-moe-expert-parallelism.md), and
  [N12 private weights](../../../handoffs/completed/numa-private-weights-quarter-roles.md).
- [Qwen3.8 replacement](../../../handoffs/active/qwen38-27b-replace-qwen36.md).
- [MEASUREMENT.md](../../../MEASUREMENT.md) and
  [Annex B](../../../measurement/protocols/bench-cpu.md).

## Why this is blocked

Every row is a hard precondition, not a phase task.

| ID | Required state | Current state on 2026-08-20 | Unblock proof |
|---|---|---|---|
| P-A | N25 committed, reconciled in its handoff, and reloaded | **FAIL:** N25 remains ACTIVE/applied-uncommitted; P0-1/P0-3 remain open | Dated N25 PASS/closure entry, clean intended diff, reload attestation |
| P-B | Current v9 baseline pinned after N25 | **FAIL:** topology authority is not final | Commit, build flags, binary/library hashes, version 10125, model hash |
| P-C | Quiet full-host window | **TRANSIENT:** q0-q3 were free at audit, but this must be reacquired at run time | One `region-lock` holder owning q0-q3 for the complete session |
| P-D | Host health eligible under Annex B | **FAIL:** uptime exceeded one week | Operator-initiated reboot and post-reboot attestation; drop-caches alone is insufficient |
| P-E | Reopen attempt recorded under INF-25 | **FAIL:** no accepted new trigger/profile exists | Dated INF-25 note; leave CPU1's permanent checklist boxes unchecked |
| P-F | TP measurement protocol ratified | **FAIL:** the linked annex is a human-review draft only | Human ratification receipt plus registry/annex transaction |
| P-G | Counter toolchain preflight passes | **FAIL:** `perf` frontend absent; no DF/UMC PMU, uProf, LIKWID or PCM installed | Evidence-bound `perf` recovery and numeric event probes, or STOP |

The blocked file deliberately has no active index row. Index ownership changes only after the
operator accepts the trigger and the prerequisites pass.

## Executive decision

Prior work has tested interleaving, private complete copies, complete mirrored copies,
CCD-aware scheduling, expert sharding, and process-level MoE expert parallelism. Those results
make a large generic NUMA-locality win unlikely.

CPU1 also already designed the paired transformer layout proposed here: output/head-sharded
QKV, local attention, input-sharded attention output, output-sharded FFN gate/up,
input-sharded FFN down, and approximately one or two reductions per layer. Therefore the reopen
trigger is **not architectural novelty**. The narrower unimplemented question is:

> Can four persistent process-local worker pools, one per NPS4 node, execute CPU1's existing
> paired layout with physically disjoint quantized shards and two full-hidden `AllReduce`
> operations per transformer block cheaply enough to improve one-request decode?

This document preserves the implementation design. It does not itself reopen CPU1. Phase 0 is
the reopen probe CPU1 requires; Phase 2 is the first implementation phase and must live in a
new active handoff if Phase 0 and Phase 1 pass.

## What the evidence does and does not establish

### Binding negatives

- NUMA_MIRROR recorded historical deltas near zero for Coder-30B Q4, Qwen3.6-35B Q8,
  and Qwen3.6-27B Q8. It closed full-copy mirroring on single-socket NPS4. This design does
  not reopen that mechanism; it uses disjoint physical shards and sharded activations.
- CPU1's per-CCD barrier, affinity, first-touch and scheduling experiments were neutral or
  placement-sensitive after baseline correction. Do not repeat those phases under a new name.
- CPU15's corrected production-relevant MoE expert-parallel result was approximately noise.
  Expert sharding remains out of scope.
- N12 closed private full model copies for the tested quarter roles; a rank here owns only its
  shard, not a complete private model.

### Historical priors, not a reopen proof

- CPU2 contains a 26%-versus-41% practical-bandwidth framing and a hybrid-model
  barrier-by-op-count hypothesis. The same ledger also contains later dense DRAM-bound
  conclusions. It is a layered historical record, not current Qwen2.5 attribution.
- CPU24 predates CPU1's completed-ledger compaction; it is not newly discovered post-CPU1
  evidence. Its reusable contribution is the counter method and conclusion vocabulary.
- The April 48×4 data records large aggregate throughput for a Qwen3-Coder-30B-A3B MoE model,
  but no Qwen2.5-Coder-32B dense arm. It can motivate a question and cannot supply the
  model-specific Phase 0 gate or be retro-certified under P-BENCH-PLACEMENT-1.
- The former `ngram-mod` 2.80× result is retracted. Corrected N25 evidence attributes it to
  warm-context self-copy; corrected deltas were near neutral and ngram-only arms regressed.
  It is not an opportunity-cost comparator.
- AutoKernel's historical +7.939% discovery is nonpromotable evidence. The current v20 GPU
  campaign is stopped/reconcile-required and cannot run this CPU architectural experiment.

## Precise hypotheses

**Null.** Four ranks do not materially improve single-stream decode because quarter-sized GEMV
shards under-use their worker pools, input-dimension quantized repacking loses SIMD efficiency,
two `AllReduce` operations across every block accumulate too much latency, and the baseline is
already limited by core-side DRAM service rather than avoidable remote access or scheduling.

**Alternative.** Persistent node executors remove enough flat-pool scheduling/barrier cost,
physically disjoint quantized shards avoid redundant weight traffic, head-sharded attention and
KV remain local, and paired projection layouts avoid intermediate gathers. Only the attention
output and FFN down paths require full-hidden `AllReduce`.

No bottleneck class is assumed. Phase 0 must classify the current model/era as one of:

1. `dram_service_dominated`;
2. `sync_or_scheduling_dominated`;
3. `remote_or_placement_dominated`;
4. `mixed_or_unresolved`.

Only classes 2 or 3 proceed. Class 1 closes the reopen probe. Class 4 stops without a decision;
it does not silently become permission to implement.

## Target models

### Primary mechanism model

`Qwen2.5-Coder-32B-Instruct-Q8_0.gguf`, locally catalogued at
`lmstudio-community/Qwen2.5-Coder-32B-Instruct-GGUF/`.

Metadata read from the local GGUF on 2026-08-20:

| Field | Global | TP4 local |
|---|---:|---:|
| transformer blocks | 64 | 64 |
| hidden size | 5120 | 1280 input columns where sharded |
| Q heads | **40** | **10** |
| KV heads | 8 | 2 |
| FFN intermediate | 27648 | 6912 |

All relevant dimensions divide by four; 1280 and 6912 also divide by a 32-element quant block.
The earlier expectation of 64 Q heads was wrong. Phase 0 must nevertheless re-read metadata and
record the exact model SHA-256.

Qwen2.5 is a plain dense mechanism model and a locally present catalogue artifact, not the
current production-served model. Results must be described as mechanism research.

### Current-artifact control

Use `Qwen3.8-27B-Q8_0.gguf`, which replaced Qwen3.6-27B in the current stack, if the v9 CPU
binary can execute the chosen control shape. It is a hybrid/self-draft artifact; TP coverage is
limited to compatible transformer sublayers. Record the TP-eligible wall-time fraction and the
resulting Amdahl ceiling. Do not compare a partial-coverage control as though it were a fully
sharded dense model.

If hybrid coverage cannot be implemented within the Phase 3 budget, use a second quantization
of the primary dense model. Retain Qwen3.6-27B only as an optional historical-continuity arm,
never as the current production control.

## Proposed execution architecture

Four persistent executor processes map one-to-one to NPS4 nodes. Physical cores only in the
first campaign; live maps are authoritative:

| Rank | Node | Expected physical CPUs; verify live |
|---:|---:|---|
| 0 | 0 | 0-23 |
| 1 | 1 | 24-47 |
| 2 | 2 | 48-71 |
| 3 | 3 | 72-95 |

SMT siblings remain unused. Each rank owns one private worker pool, node-bound shard storage,
preallocated collective buffers, and head-sharded KV state.

Tensor layouts are `REPLICATED`, `OUTPUT_SHARDED`, `INPUT_SHARDED`, and `HEAD_SHARDED`.
Every TP tensor records global/local shape, rank, global offset, quant-block alignment and
NUMA ownership.

- Q/K/V and FFN gate/up: output-dimension shards; quantized rows stay intact.
- Attention output and FFN down: input-dimension shards with a dedicated quantized repack when
  the stock row representation cannot consume a true column shard.
- Reading complete rows and masking unused columns is forbidden: it recreates mirrored traffic
  and vacates the experiment.
- Block entry/output are replicated. Q/K/V, attention and KV are head-sharded. FFN intermediate
  remains sharded.
- Exactly two full-hidden `AllReduce` operations occur per compatible block: after attention
  output projection and after FFN down. “Reduce to rank 0” is valid only when followed by an
  explicit broadcast; segmented reduce-scatter is valid only when followed by all-gather.

Prototype central reduce+broadcast, binary tree, and reduce-scatter+all-gather. Select by the
complete repeated sequence cost, not isolated notification latency.

Every process is launched by an owning runner that records PIDs. Timeout cleanup sends SIGTERM
only to those captured PIDs, confirms exit, then escalates the same PIDs to SIGKILL if needed.
Any rank loss, timeout or incomplete cleanup invalidates the complete sample.

## Gate sequence

### Phase 0 — INF-25 model-specific reopen probe

No TP mechanism source change. The trace-only v9 diagnostic patch allowed by the protocol may
measure per-node and barrier time; it must pass its instrumentation-overhead/parity gate.

1. Satisfy P-A through P-G.
2. Re-read model metadata and record v9 binary, libraries, model and host identity.
3. Measure a current single-instance baseline and a new four-node aggregate headroom arm under
   the proposed protocol. Do not use the April MoE bundle as the gate.
4. Capture core-side DRAM-fill proxy, IPC, local/far fill fraction, CPU utilization,
   `numa_maps`, kernel/barrier sample share, and TP-eligible wall-time share using the exact
   instrument plan in the annex.
5. Emit one bottleneck class. An unavailable or invalid counter panel yields
   `mixed_or_unresolved`, not an inferred “not DRAM-bound” result.

Proceed to Phase 1 only when all three hold:

- current four-node aggregate throughput is at least 1.5× the current full-socket baseline;
- TP-eligible projections account for at least 60% of token latency;
- attribution is `sync_or_scheduling_dominated` or `remote_or_placement_dominated`.

The first two are necessary triage conditions, not proof that aggregate throughput can be
converted into one-stream TP. `dram_service_dominated` closes the INF-25 reopen attempt.
`mixed_or_unresolved` stops and requests a better instrument; it neither closes nor proceeds.

### Phase 1 — collective-cost falsifier

No weight sharding. Benchmark exact model hidden size and exact block count. For the Qwen2.5
primary, one token sequence contains 64 blocks × 2 = 128 `AllReduce` operations over 5120
elements. Test FP32 and a reduced-width transport only if its numerical conversion is separately
validated.

- **PASS:** upper confidence bound for projected collective fraction is at most 10% of current
  canonical token latency.
- **FAIL:** lower confidence bound is above 15%; close before tensor work.
- **INCONCLUSIVE:** every other result, including the former 10–15% gap; stop without Phase 2.

### Phases 2–4 — gate-locked

No checklist item below is dispatchable until a dated PASS for the preceding phase is recorded.

**Phase 2: real-weight FFN prototype.** Build RMSNorm → output-sharded gate/up → local
activation/gating → input-sharded down → one `AllReduce` → residual. Sweep 8/12/16/24 threads
per rank. Compare A/B/C as defined in the annex.

- PASS: lower confidence bound for complete FFN improvement is at least 10%.
- FAIL: upper confidence bound is below 5%.
- INCONCLUSIVE: the interval intersects 5–10%; archive evidence and stop without Phase 3.

**Phase 3: complete transformer block.** Add head-sharded QKV, rank-local RoPE/attention/KV,
input-sharded output projection, the first `AllReduce`, and the Phase 2 FFN path.

- PASS: lower confidence bound for complete-block improvement is at least 8%, collective share
  at most 15% of TP block time, no rank idle more than 20%, placement verified, quality passed.
- Otherwise stop. A positive FFN with a neutral block is an FFN research result, not a graph-TP
  pass.

**Phase 4: default-off full-model integration.** Preserve the disabled path exactly. Production
candidacy discussion requires all of:

- primary end-to-end TG lower confidence bound at least +10%;
- current-artifact control or second dense quantization lower confidence bound at least +5%;
- prompt-processing-rate lower confidence bound no worse than -5%, and TTFT-latency upper
  confidence bound no worse than +5%;
- numerical/PPL, memory (at most 1.25×), soak, shutdown and failure-injection gates pass;
- complete P-BENCH-PLACEMENT-1 reference matrix plus the annex A/B/C mechanism matrix.

A positive median below those confidence gates is research-only. An interval wholly within ±3%
is a decisive neutral. Any interval spanning neutral and positive regions is inconclusive; do
not extend sampling beyond the precommitted ceiling.

## Opportunity cost

Do not promote this above live, protocol-backed production work. The placement/topology cutover
must land first. The retracted ngram result and nonpromotable AutoKernel discovery observation
are not live competing gains. Reassess priority from CURRENT-CAMPAIGN at the moment P-A through
P-G pass rather than preserving a stale percentage here.

## AutoKernel relationship

At the 2026-08-20 audit, AutoKernel v20 could not execute this handoff: it was a GPU
kernel-source campaign, was stopped/reconcile-required, and generic arbitrary source-candidate
execution remained unfinished. Re-attest its live state, but do not inject CPU TP into v20.

After controller recovery and a separately deployed CPU architectural campaign, this design may
seed three bounded hypotheses:

1. four-rank full-hidden `AllReduce` implementation and repeated-sequence cost;
2. real-weight paired FFN sharding with a quant-block-aligned input-column repack;
3. persistent node executors versus the flat pool, but only after Phase 0 attributes meaningful
   sync/scheduling cost.

Those are future campaign inputs, not permission to mutate the current campaign or production.

## Activation and completion

On a Phase 0 + Phase 1 PASS:

1. create a narrow active implementation handoff beginning at Phase 2;
2. add exactly one new INF row and annotate INF-25 with the dated trigger/profile result;
3. add forward links from CPU1 and NUMA_MIRROR without changing either closure;
4. file the known one-line host erratum in
   [`numa-prefill-decode-disaggregation.md`](../../../handoffs/active/numa-prefill-decode-disaggregation.md),
   replacing “2-socket / 8-NUMA” with the attested one-socket NPS4 topology;
5. add the write-side Vidya source adapter task before collecting decision-grade measurements.

Negative completion requires a protocol-backed failed gate, preserved commands/raw evidence,
the exact failure mechanism or unresolved classification, and cross-links among CPU1, CPU15,
NUMA_MIRROR and the eventual implementation handoff. No production wiring or freeze mutation is
authorized by this document.
