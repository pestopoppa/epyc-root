<!-- RATIFIED 20260730T103218Z. Annex B of MEASUREMENT.md (same trust boundary, same
     amendment rules). CPU bench protocol family. -->

# Annex B — CPU bench protocols

## P-BENCH-1 — Canonical single-instance decode (llama-bench)

- **Entry point**: `bench_canonical.sh` / `canonical_recipe.py` (epyc-inference-research) —
  **never hand-typed commands** (`feedback_use_codified_recipes_not_memory`; the 2026-05-28
  session lost a day to recipe drift + a RUNPATH binary mismatch).
- **Core recipe**: `taskset -c 0-95 -t 96 -fa 1`, no `--numa distribute`, no `GGML_*` env unless
  the variant-under-test IS an env flag (then one flag per arm). The recipe module enforces
  `OMP_DYNAMIC=false` + clang-20 libomp `LD_LIBRARY_PATH` and runs
  `assert_binary_resolves_correctly()` (readelf/ldd — the libllama RUNPATH guard).
- **Preconditions (all enforced or attested)**: no concurrent inference (`pgrep llama` zombie
  check; benches require a region claim per `feedback_no_concurrent_inference` as amended
  07-27); host-health tier — uptime ≤1wk → `drop_caches` + **NUMA-interleave re-warm** (never a
  bare re-read; `feedback_drop_caches_numa_eviction`), ≥1wk → reboot required
  (`feedback_host_throttle_check`); governor + `kernel.numa_balancing` checked per session (it
  self-resets); THP pool noted (production `--no-mmap --mlock` depletes it).
- **Reps**: ≥5 for ≥5% effects; **≥10 for ≤2% effects**; report median + MAD. Cold-vs-warm
  declared. `-fa 1` always explicit (8–10% swing; llama-bench defaults to 0).
- **Reference anchors**: 460 GB/s practical aggregate BW; per-thread share ≈ 4.79 GB/s × 96
  (structural — not recoverable by code); NUMA law: ≤65GB models → 4×48t quarters 6–7×
  aggregate; 130–250GB → 1×96t; 192t anti-optimal.

## P-BENCH-PREFILL-1 — Canonical single-instance CPU prefill (RATIFIED 2026-07-24)

**Scope.** Decision-gating CPU prompt-processing throughput via `llama-bench`; metric = prompt
tokens/s, higher-better. Decode remains under P-BENCH-1; the two may be paired in a
kernel-promotion bundle.

**Entry point & fixed profile.** Only through `bench_canonical.sh` / `canonical_recipe.py`,
never hand-typed. Profile: `-p 2048 -n 0 -r 10`, `taskset -c 0-95`, `-t 96`, `-fa 1`, no
`--numa distribute`. Wrapper-enforced OMP env and binary/library resolution checks mandatory. A
`GGML_*` variable only as the single variant under test, value recorded per arm.

**Release identity.** Both arms MUST provide explicit `--binary`, `--source-root`,
`--library-path`. Candidate = clean committed tree whose binary reports that commit. MUST record:
branch, commit, dirty status, binary + shared-library SHA256s, the exact
`build: <commit> (<number>)` line from every result (must match recorded source HEAD), `ldd`,
model path/size/SHA256, complete argv, environment, date, attestation ref. (Frozen v7 and
v8-candidate `llama-bench` binaries implement no `--version`.) Mixed or production-resolved
candidate libraries invalidate the run.

**Host & cache prep.** All P-BENCH-1 host-health and quiet-window preconditions apply. Before
each matched production/candidate pair: `sync`, drop page cache, sleep 2s, re-warm the model via
`taskset -c 0-95 numactl --interleave=all`. No cache drop between the two arms. Declare arm
order: initial pair production→candidate; any retry = fresh reset, reversed order. Failed strict
preflight, concurrent inference, stale governor/THP/NUMA state, or unresolved process blocker
invalidates the pair.

**Continuous contention accounting (AMENDED 2026-07-25).** Retain every raw `/proc/stat`
aggregate sample, process-group sample, sampling bracket, swap counter, ownership witness, and
competing llama/AutoPilot/KFD witness. Aggregate counters and process-group scans share no
atomic timestamp → a single adjacent interval's signed subtraction is diagnostic telemetry only
and MUST NOT by itself invalidate an arm.

Per adjacent sample pair retain: elapsed, aggregate total/busy deltas, target group CPU delta,
target core-equivalents, signed external core-equivalents, swap delta, exclusion reasons. An
interval is eligible only when: elapsed and aggregate total delta positive; aggregate busy
monotonic and ≤ total; target CPU monotonic; target use ≥ `0.75 ×` configured CPU count (72
cores for the canonical 0-95 profile); ownership stable; zero swap I/O; no competing
llama/AutoPilot/KFD witness. `target_delta > busy_delta` is retained as signed sampling
telemetry, not a malformed interval.

Select the longest contiguous eligible sequence with aggregate elapsed ≥ 10s (ties → earliest
start). From its endpoints compute, without clamping,
`signed_external_core_equivalents = (aggregate_busy_delta − target_group_cpu_delta) / (CLK_TCK × elapsed_seconds)`.
The arm passes only when a qualifying window exists and the value is in `[-1.0, 4.0]`
core-equivalents (< −1.0 = persistent counter-alignment failure, not negative contention).
Startup/teardown intervals excluded for low target use stay in the artifact. Any sampling
failure, ownership change, swap I/O, or competing witness anywhere in the arm remains an
unconditional invalidation. The two 2026-07-24 startup-race artifacts remain invalid and MUST
NOT be retro-certified. The amendment is prospective — no pre-amendment artifact may be
retro-certified under the sustained-window algorithm.

**Reps & result.** ≥10 reps per arm for a release non-inferiority claim. Retain every
`samples_ts`; report per-arm median + MAD. Comparison ratio = `candidate_median /
production_median`. Cold model-load time is not part of the metric; cache state + warm-up
policy remain part of the attestation.

**CPU kernel-promotion decision rule.**
- Every non-IQ regression cell: ratio ≥ 0.98 PASS; < 0.95 FAIL.
- Ratio in [0.95, 0.98): one fresh reversed-order pair; pool all 20 samples/arm; pooled-median
  ratio ≥ 0.98 or the cell FAILS.
- Newly enabled IQ kernel path: neither its prefill ratio nor its paired P-BENCH-1 decode ratio
  may be < 0.95, and at least one must be ≥ 1.05 — else insufficient release utility.
- Model-load, correctness/coherence, numerical-safety, attribution, or cleanup failure = FAIL
  regardless of throughput.
- Every required cell must pass before promotion; a failed cell blocks pending repair or an
  explicit operator waiver.

**Grammar**: `CPU prefill <value> tok/s [P-BENCH-PREFILL-1, n=<reps>, YYYY-MM-DD, attest <ref>]`.

## P-BENCH-2 — Canonical multi-instance / aggregate (production-shaped)

For quarter-split or concurrent-instance claims: launch via `orchestrator_stack.py` (never
ad-hoc); canonical OMP env stack (PROC_BIND=spread, PLACES=cores, WAIT_POLICY=active,
KMP_BLOCKTIME=10); mlock + sequential loading; **live-affinity verification**
(`affinity_preflight.py` — topology_hash certifies intent, not reality); contention matrix
certified fresh. Aggregate metric = sum of per-instance decode over identical prompt sets, same
wall window.

## P-BENCH-3 — Batched/slot decode (the CPU14/E1/E2 regime)

Single instance, `-np N` sweep {1,2,4,8,16}, fixed question batch; metrics = aggregate
tasks/hour AND per-stream p50/p95 latency, reported per-N. Required before any batched-serving
or batched-kernel claim. (This regime previously had no protocol — that absence is why it stayed
an evidence vacuum.)

## P-BENCH-4 — Single-instance server-native speculative decode (FG-4b)

**Scope.** Decision-grade only when `llama-bench` cannot exercise the production feature under
test: one CPU-only, single-instance `llama-server` serving a native speculative-decode request.
Prospective; applies to the FG-4b A4 CPU serving shape and a separately identified equivalent
shape. Decode t/s, higher-better. Does NOT cover llama-bench, aggregate/multi-instance, batched
slots, quality, registry mutation, or deployment authorization.

**Pinned instrument.** Evidence must name the ratified runner's repository, commit, Git tree,
path, and SHA-256; runner source must exactly match in a clean worktree. Record: production
`llama-server` branch/commit/binary SHA-256/version, model path/SHA-256, complete argv, complete
effective environment, CPU list, topology derivation, request payload, all raw server responses.
Any missing, substituted, dirty, or mismatched identity → observation. The pre-ratification
runner at research commit `919e83a2` is explicitly nonconforming (3 samples, mean, no forced
`ignore_eos`) and MUST NOT be retro-certified.

**Ratification transaction.** Human receipt + appended measurement policy + changelog entry are
one fail-closed transaction: stage and fsync every candidate, both policy preimages, and a
durable transaction journal before replacing either policy file; hold the shared measurement
trust-boundary lock across startup recovery and the whole transaction; publish the receipt only
after the authoritative runner accepts it against the updated policy; the receipt MUST be
created with a no-replace operation, containing directory fsynced. A valid durable receipt is the commit
record — startup recovery commits its bound policy files; without one, recovery atomically
restores and fsyncs both journaled preimages. Recovery is mandatory after trapped failures,
signals, abrupt process death, host restart.

**Exclusive ownership & host state.** Exactly one CPU-only server, `-np 1`. The quiet-host
preflight MUST prove no competing inference (witness retained). The enclosing `region-lock`
invocation must hold the exact physical footprint (FG-4b A4: `q0`+`q1`) under one matching `bench` role, request
tag, complete-region set, and ancestor-holder PID; the runner verifies that same ownership
before launch AND after server teardown while the lock is still held — a merely globally-held
region, different owner, or changed holder is a failure. Record host-health attestation (uptime,
governor, NUMA balancing, THP, memory). After the clean-host/uptime gate and before server
start: `sync` then privileged `drop_caches=3`; a failed cache action invalidates the arm.
Topology-local node-0 `taskset` serving shape, no `numactl`.

**Live affinity & request witnesses (as superseded 2026-07-29 — all-thread request-boundary
witness).** After readiness, the live server PID's effective affinity must exactly equal the
recorded CPU list. Immediately before AND after each warmup and each measured request, the
witness MUST enumerate every numeric TID in `/proc/<server-pid>/task`. Each enumeration is valid only when: TID set
stable across collection; leader TID retained; ≥1 worker TID; no affinity outside the expected
CPU list; both all-thread and worker-thread affinity unions exactly equal that list. The
persisted per-request witness retains complete `before`/`after` observations and rejects any
difference. TID appearance/removal, leader disappearance, incomplete worker set, or out-of-mask
affinity invalidates the arm. These are stable `/proc` snapshots, not continuous scheduler
tracing — a transient change wholly between snapshots is not observable; that is a disclosed
residual risk and may not be described as continuously monitored affinity.
*Supersession record*: this witness supersedes the one in receipt
`artifacts/operator/ratify_pbench4_fg4b_server_native_20260729T055435Z.json` (SHA-256
`8da155e4…154e`); that receipt remains durable historical provenance only — it cannot ratify
the affinity-hardened runner or support a new P-BENCH-4 claim. A new human receipt must bind the
exact runner repo/commit/tree/source SHA-256 and the contract containing this witness, naming
the prior receipt path + SHA-256 as superseded provenance.

**Request, warmup, reps.** Fixed retained payload: deterministic sampling fields,
`stream: false`, `cache_prompt: false`, `max_tokens: 512`, `ignore_eos: true`. Every measured
response must finish `finish_reason == "length"`, report exactly `timings.predicted_n == 512`,
and have finite positive `timings.predicted_per_second`. Warmup = same shape at 64 tokens; cold
samples excluded until three consecutive positive decode rates are within 5% of their median
(≤8 attempts). Then exactly five independent 512-token measured requests — no retry, replace,
discard, or pooling. Report median + MAD of the five server-reported rates; preserve all five
values and raw responses. Any failed warmup, request, timing, host, lock, affinity, cleanup, or
publication check invalidates the entire arm.

**Sealed publication.** All evidence into a fresh staging directory; the manifest MUST list
every staged file (except itself and `COMPLETE`) with SHA-256s; validate completeness and the
five-sample median/MAD; write `COMPLETE` in staging; fsync every file + staging + parent
directories; atomically rename; fsync parent again. Partial, mutable, or unsealed output =
observation only. The record MUST cite the operator attestation receipt that ratified this
protocol. A registry-patch proposal may be emitted only as non-applying review material and MUST
identify its evidence hash as the SHA-256 of the exact written `evidence.json` bytes, never a
reserialized object.

**Grammar**: `A4 server-native speculative decode <median> tok/s, MAD <mad> [P-BENCH-4, n=5,
YYYY-MM-DD, attest <receipt>]`. Prospective; authorizes neither an automatic registry edit nor
any keep/revert/deploy/promote decision without the separately applicable gate.
