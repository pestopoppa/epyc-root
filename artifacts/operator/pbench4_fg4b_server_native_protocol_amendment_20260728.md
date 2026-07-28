
## P-BENCH-4 — Single-instance server-native speculative decode (FG-4b)

**Scope and direction.** This is the decision-grade instrument only when
`llama-bench` cannot exercise the production feature under test: one CPU-only,
single-instance `llama-server` serving a native speculative-decode request. It
applies prospectively to the FG-4b A4 CPU serving shape and to a separately
identified equivalent serving shape. Decode throughput is higher-better. This
protocol does not cover `llama-bench`, aggregate/multi-instance throughput,
batched/slot serving, quality, a registry mutation, or deployment authorization.

**Pinned instrument.** The evidence must name the ratified runner's repository
commit, Git tree, path, and SHA-256, and the runner source must exactly match
those values. Record the production `llama-server` branch, commit, binary
SHA-256/version, model path/SHA-256, complete argv, complete effective
environment, CPU list, topology derivation, request payload, and all raw server
responses. Any missing, substituted, dirty, or mismatched identity makes the
result an observation. The pre-ratification runner at research commit
`919e83a249ed9060d0608305700e6eeddb8daa71` is explicitly nonconforming: it
uses three samples and a mean and does not force `ignore_eos`; it MUST NOT be
retro-certified under P-BENCH-4.

**Exclusive ownership and host state.** Launch exactly one CPU-only server with
`-np 1`. Before launch, the runner's quiet-host preflight must prove no competing
inference process and retain its process witness. It must require the enclosing
`region-lock` invocation to hold the exact physical footprint (for FG-4b A4,
`q0` and `q1`) under one matching `bench` role, request tag, complete-region
set, and ancestor-holder PID. The runner verifies that same ownership before
launch and after server teardown while the enclosing lock remains held; a merely
globally-held region, a different owner, or a changed holder is a failure.
Record the runner's host-health attestation, including uptime, governor, NUMA
balancing, THP, and memory state. After the clean-host and uptime gate and before
server start, synchronously perform `sync` then privileged `drop_caches=3`; a
failed cache action invalidates the arm. This is a topology-local node-0 `taskset`
serving shape with no `numactl`.

**Live affinity and request witnesses.** After readiness, inspect the live server
PID's effective CPU affinity and require it to exactly equal the recorded CPU list.
Immediately before every warmup and measured request, retain a witness proving
that only the runner's permitted process tree owns live inference and that the
server PID still has that exact affinity. A launch command or topology intent alone
is insufficient; an absent, competing, or mismatched witness invalidates the arm.

**Request, warmup, and repetitions.** The request payload is fixed and retained,
including deterministic sampling fields, `stream: false`, `cache_prompt: false`,
`max_tokens: 512`, and `ignore_eos: true`. Every measured response must finish
with `finish_reason == "length"`, report exactly `timings.predicted_n == 512`,
and have finite positive `timings.predicted_per_second`. Warmup requests use the
same retained request shape at 64 tokens; cold samples are excluded until three
consecutive positive decode rates are within 5% of their median, with at most
eight attempts. Then run exactly five independent 512-token measured requests.
Do not retry, replace, discard, or pool a sample. Report the median and median
absolute deviation (MAD) of those five server-reported decode rates; preserve all
five values and raw responses. A failed warmup, request, timing, host, lock,
affinity, cleanup, or publication check invalidates the entire arm.

**Sealed publication.** Write all evidence into a fresh staging directory. The
manifest must list every staged evidence file (other than itself and `COMPLETE`)
with SHA-256 values; validate completeness and the five-sample median/MAD, write
`COMPLETE` in staging, fsync every file plus the staging and parent directories,
then atomically rename the directory and fsync the parent again. Partial, mutable,
or unsealed output is an observation only. The record must cite the operator
attestation receipt that ratified this protocol. A registry-patch proposal may be
emitted only as non-applying review material and must identify its evidence hash as
the SHA-256 of the exact written `evidence.json` bytes, never a reserialized object.

**Claim grammar.**
`A4 server-native speculative decode <median> tok/s, MAD <mad> [P-BENCH-4, n=5, YYYY-MM-DD, attest <receipt>]`.

This protocol is prospective. It authorizes neither an automatic registry edit
nor a keep/revert/deploy/promote decision without the separately applicable
decision gate.
