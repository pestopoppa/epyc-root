# P2-5j — MI210 host-thread placement sweep protocol

**Status:** execution design only, 2026-07-29. This document starts no server, changes no
registry, takes no lock, and is not an operator grant. It is the placement-selection attachment to
the P2-5c / P-SHED-1 campaign.

**Execution amendment, 2026-08-11:** P2-2c was cancelled when MiniCPM-o was deprecated, and the
operator has now granted the active AutoKernel session all inference/compute resources plus authority
to tear down the resident stack. Those two historical gates are satisfied. The sweep still requires
the lane's Steps 0–7 preflight/activation choreography, fresh host health, and successful CPU/GPU
claims; none may be replaced by the broad compute grant.

**Measurement-constitution audit, 2026-08-11:** this historical four-arm design varies CPU
affinity, so ratified `P-BENCH-PLACEMENT-1` controls it. That protocol requires its full A0–A4
composite, an `np=1` production-anchor gate, cold/warm cache pairing, and measured
`/proc/<pid>/numa_maps` locality. P2-5j as written has none of those complete gates, while
`P-SPEED-OBJ` is the task-rate protocol for whole-system/cross-device decisions and cannot confirm
an instrument-level decode-tok/s placement effect. Therefore the four-arm campaign below is
**observation-only**: it may populate bounded AutoKernel G1 context, but cannot select a placement,
authorize a carve, or re-derive the serving ceiling. A decision-bearing successor requires either
(a) a human-ratified P2-5j protocol amendment or (b) a redesigned execution satisfying the existing
`P-BENCH-PLACEMENT-1` composite in full. This trust-boundary correction does not prevent building or
testing the receipt/context tooling.

## Question and claim

The MI210 (`0000:43:00.0`, `numa_node=1`) has only been compared with eight host threads on
`184-191` and `88-95`. Both sets are on NUMA node 3 and are therefore cross-node from the device.
The incumbent `184-191` has measured lineage, but it has never been compared with a device-local
placement. This is a symmetric test: remote submission state and DMA locality can hurt the
incumbent, but locality can also change first-touch and shared submission-state behaviour in either
direction.

The observation is GPU throughput, **higher is better**. A row retains the P-GPU-1 instrument
fields but is explicitly non-gating because the controlling placement composite is absent:

`GPU lane host placement <arm> <median> tok/s, MAD <mad> [P-GPU-1, n=10, YYYY-MM-DD, attest <ref>]`.

P2-5j does not itself authorize a carve, registry edit, activation, or production traffic. In its
current four-arm form it also does not select the host placement. It ranks a topology signal for a
future constitution-compliant placement decision and supplies bounded AutoKernel context.

## Arms and fixed shape

Every arm uses exactly eight host threads, the same production-named v9 HIP binary, model and
model hash, GPU device, launch flags, effective environment, sampling policy, prompt corpus,
warm-up/discard policy, request count, and server port policy. The only intentionally varying
field is the server `taskset` CPU list.

| Arm | `taskset` host CPUs | NUMA relation | Purpose |
|---|---|---|---|
| I — incumbent | `184-191` | node 3, cross-node | Current lane placement and comparison baseline. |
| H — historical physical | `88-95` | node 3, cross-node | Reproduces the other already-compared eight-thread placement. |
| Lp — local physical | `40-47` | node 1, device-local | Device-local counterpart to the physical-thread arm. |
| Ls — local SMT | `136-143` | node 1, device-local | Primary device-local candidate; SMT siblings of `40-47`. |

The selection shape is the checked-in lane serving shape in
`epyc-orchestrator/orchestration/gpu_shadow_lane_np_ceiling.yaml`:
`np_slots: 8`, `slot_context_tokens: 8192`, total context `65536`, MTP off. The run pins the
exact resolved launch argv rather than reconstructing these values. A placement win does **not**
transfer the old `np × context` ceiling table: P2-5c must regenerate the table at the winning
placement before a new serving shape, carve, or residency verdict can cite it.

The CPU region for each arm is derived by the existing SMT-fold-and-region-mapping code and
acquired with the GPU-device claim for that arm. It is not inferred from the old q3 label: local
arms must acquire their Q0B-derived region, while I/H acquire the q3-derived region. A failed or
changed claim/holder invalidates the arm.

## Codified instrument and execution order

The execution instrument is the existing server-native sweep path,
`epyc-inference-research/scripts/benchmark/server_numa_np_sweep.py`, with a dedicated, pinned
single-instance cell manifest for each arm. Its `build_instance_command()` is deliberately the
placement-aware `taskset` launcher; it must not be wrapped in
`canonical_recipe.CANONICAL_PREFIX`, whose all-host `0-95` prefix would erase the variable being
tested. This is the same deliberate exception the runner documents for quarter placements.

The manifest/runner imports, rather than copies, the canonical environment and validation
constants through `scripts/lib/canonical_recipe.py` and is launched through the checked-in
benchmark entry path (`bench_canonical.sh` only where its wrapper applies). In particular, the
implementation uses `build_canonical_env()` / `CANONICAL_OMP_ENV`, the clang-20 library-path
validation, binary-resolution validation, and host-environment validation from that module. The
run record captures their resolved values. No remembered OMP, library-path, cache, or benchmark
defaults may be typed into a new placement script.

For each of ten balanced blocks, randomize a permutation of I/H/Lp/Ls before the block starts;
do not run all repetitions of one arm consecutively. For every arm:

1. Acquire the arm's derived CPU region plus the MI210 device flock, and record the holder.
2. Capture P-GPU-1 before-state evidence and the declared CPU-stack interference state.
3. Start a fresh server using the pinned manifest, complete the fixed warm-up, discard the
   warm-up result, then use `affinity_preflight.py` plus per-thread `/proc` evidence to prove every
   live server thread has exactly the arm's CPU mask.
4. Run the frozen request corpus at the fixed shape; record prompt and decode throughput, latency,
   request outcomes, and raw samples.
5. Capture after-state evidence, verify cleanup and no listener/KFD leak, then release only at the
   run boundary.

Any affinity mismatch, ownership/claim change, model/binary/environment drift, incomplete
hardware-state capture, request failure, competing inference not declared in the arm, or teardown
failure invalidates that sample; it is not silently retried into the same result set. The next
valid sample is recorded as a fresh attempt with its reason for replacement.

## Repetitions, decision rule, and falsification

Use **n=10 valid repetitions per arm**. This is the P-BENCH-1/P-GPU-1 floor for a placement effect
at or below two percent, and it is the correct conservative floor because this change could be a
small locality effect. Report every raw sample, each arm's median and MAD, and the paired
placement ratios to I. Arm order is part of the artifact.

`Ls` is a device-local **signal** only when all ten valid pairs retain complete P-GPU-1 instrument
fields and its paired comparison with I clears the pre-registered practical threshold of **at least
2% higher median throughput**. `Lp` is evaluated by the same rule. A signalled local arm must also
be non-inferior to H; this prevents attributing an incumbent-SMT anomaly to locality. No signal is
a placement win under the current constitution; `P-SPEED-OBJ` is inapplicable to this tok/s scope.

A claimed observation-only device-local signal is falsified if any required evidence field is
absent, fewer than ten valid paired repetitions remain, the local arm misses the 2% threshold, or
its live affinity/claim differs from the arm definition. In those cases the result is either
invalid or **no demonstrated device-local signal**. In every case I remains the placement baseline
pending a constitution-compliant successor sweep. H may diagnose an SMT representation effect but
cannot by itself justify a move off q3.

## Gates and sequencing

Execution waits for all of the following: P2-2c completion, the operator-granted Steps 0–7 lane
activation choreography, the runbook's inference authorization, an owner-approved quiet window,
fresh host-health evidence, a production-named kernel, current contention/affinity certification,
and successful acquisition of the arm's CPU and GPU claims. `inference` owns stack changes; this lane
does not reload or launch around its inference work. Do not carve q3, amend Q0B, or flip any
production activation switch before the sweep result and the combined P2-5c verdict.

The operator-selected HYBRID option C remains intact: P3-1/P3-2 may begin on I after activation,
but their absolute latency and token-economics remain placement-pending. P3-3 sign-off remains
last, on the selected final placement.

## Optional early-warning mini-probe

If scheduling needs an early signal, run only I versus Ls at the same fixed shape for five
observation-grade, balanced repetitions (estimated 2–4 hours). It can prioritize the full
campaign but cannot select a placement, close a class, amend a ceiling, or authorize a carve.
The same authority limit now applies to the full four-arm campaign until the constitution gap
above is resolved.
