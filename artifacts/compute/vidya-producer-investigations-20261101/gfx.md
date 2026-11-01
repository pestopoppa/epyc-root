# VB-AK-R18-GFX-OBSERVATION investigation

Date: 2026-11-01 UTC  
Scope: read-only source and handoff review; no repository edits and no compute run.

## Finding

The producer is Research AutoKernel's native GPU-claim telemetry, specifically `scripts/kernel_rnd/autokernel/loop/gpu_counter.py`, called from `loop/run.py` at GPU claim acquisition/release and phase boundaries. The declared native schema is `epyc.autokernel.gfx_counter_trace.v1`. Its source change is Research commit `26d89b6ea20f21675d9cc4bc07a8db11ec42199e` (“Observe autokernel gate time and GFX counter windows”), identified by both the ROOT handoff and adapters source table. At the time of inspection Research HEAD was `99301fa149af86a6f9743d2b0405c9234ba39586`; the producer path was not present in the checked-out HEAD, although the cited commit is available in git history. Treat the cited source revision as the producer pin pending owner integration; do not silently substitute current HEAD.

The code at the cited revision implements the *native observation carrier*, not Vidya enrollment. `RocmReader` pins the ROCm SMI library path/version/hash and the claimed MI210's PCI BDF, checks the mapped device identity, and collects cumulative GFX activity counter values with monotonic host-call brackets and native counter timestamps. `Collector` records claim-start, phase labels, claim-end, errors, identity, acquisition/release monotonic times. `reduce_trace()` refuses errors, fewer than two samples, malformed or nonpositive timestamps, bracket/order inconsistencies, counter reset/decrease, native/host timing inconsistency, and implausible delta. Its output is an approximate activity-weighted GFX-seconds estimate over the observed sample window only; it explicitly does not establish binary device-busy time, per-process activity, full claim utilization, or reset-free continuity. It is telemetry and never gates a run.

The 2026-11-01 AutoKernel handoff entry says instrumentation and guarded synthetic tests exist, including acquisition/release and oracle/benchmark warmup paths plus refusal cases. A read-only ROCm capability query established API availability only. It explicitly says full-claim busy/idle remain UNKNOWN, no qualifying physical validation has been run, and R18-E remains open. This investigation did not rerun tests or query hardware.

## ROOT wiring status

`handoffs/active/vidya-belief-substrate-program.md` lists `VB-AK-R18-GFX-OBSERVATION` open. `scripts/vidya/adapters/README.md` has a prospective source-table row naming this producer and required native fields, but labels the write-side carrier, strict projection, and real planning-context canary pending. ROOT has an existing AutoKernel measurement projection in `scripts/vidya/adapters/autokernel_unified_arm.py`, and the single existing measurement ladder is `scripts/vidya/claim_tuple.py::grade()`; there is no dedicated GFX trace adapter/reader or ingest path evidenced by the source table/repository search. The unified-arm adapter is not itself evidence that it reads this native trace. No second ladder is needed or allowed.

## Shortest actionable sequence

1. **Owner-reconcile/pin the producer source.** Ensure the producer at `26d89b6...` is available in the maintained Research source path/branch and preserve its exact source revision. Do not infer the checked-out `99301fa...` has those bytes merely because the commit is in history.
2. **Close the write-side join at the source.** Emit an immutable native record at the original run write boundary that binds raw samples/errors and reducer result, phase/window markers, monotonic brackets and native timestamps, claimed-device ownership/acquisition/release, BDF and ROCm library path/version/SHA-256, producer source revision, run ID, and immutable run/provenance locators. Missing, partial, failed, contradictory, or unjoined values must be retained as UNKNOWN/refusal; do not reconstruct a prior run's tuple.
3. **Add strict ROOT projection/ingest.** Reopen and validate the producer record and its named source/run joins, derive only the observed-window GFX activity-weighted metric (or an explicit unknown), then construct an existing measurement `ClaimTuple` and delegate grading to `claim_tuple.grade()`. No new grade, threshold, protocol, or interpretation as physical busy time.
4. **Exercise a real planning-context canary.** Show the actual intended planner/consumer receives this source and can reason with the bounded scope and unknowns; synthetic fixtures alone prove conformance only. Record the canary receipt and only then call the source wired.
5. **First eligible native observation.** At a suitable, authorized AutoKernel GPU run, capture an actual trace with at least two valid observations during an owned claim and its phase boundaries; preserve failures and incomplete joins. This produces a valid prospective observation only for its observed window and stated limits.

Steps 1–4 are source/wiring work; step 5 is the first physical observation and requires an actual eligible run. Do not run it as part of this investigation.

## Can a valid compute row be published?

**Not a valid GFX measurement/compute-result row now.** There is no ROOT reader/projection or real planning canary, and no qualifying physical observation. A passive capability query, synthetic tests, or the producer implementation itself cannot serve as a compute measurement row. The handoff/task row is already published as OPEN, and the adapters README already has the prospective source-table entry; those are valid tracking of the gap, not a valid measured compute row. After source and reader wiring, a real eligible producer run could publish an OBSERVATION ClaimTuple through the existing shared measurement ladder, while retaining unknown scope and without claiming device busy/idle or per-process attribution.

## Evidence locations reviewed

- `handoffs/active/vidya-belief-substrate-program.md`, task `VB-AK-R18-GFX-OBSERVATION`.
- `scripts/vidya/adapters/README.md`, R18-E source-table entry.
- `scripts/vidya/adapters/autokernel_unified_arm.py` (existing AutoKernel measurement projection; distinct from this trace).
- `scripts/vidya/claim_tuple.py`, `grade()` and measurement ladder.
- Research commit `26d89b6ea20f21675d9cc4bc07a8db11ec42199e`: `loop/gpu_counter.py`, `loop/run.py`, `loop/test_gpu_counter.py`, `loop/test_r18e_observation.py`.
- `handoffs/active/autokernel-rebuild-program.md`, 2026-11-01 source-preparation checkpoint.
