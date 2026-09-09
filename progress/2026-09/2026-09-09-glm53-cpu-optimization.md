# GLM53 CPU optimization — 2026-09-09

Continues the [September8 implementation session](2026-09-08-glm53-support-audit.md).
Candidate kernel `04ffb8ad0` completed the matched canonical48 CPU run pair.

CANDIDATE observations (same local UD-Q4_K_XL artifact; unrebooted host, no
promotion attestation): five2029-token prefills median144.0811 versus117.5111
prompt tokens/s (+22.6%); five512-token decode repetitions median9.60451 MTP
versus7.69689 plain output tokens/s (+24.8%); one24-prompt workload pass
10.82479 versus7.67426 output tokens/s (+41.1%). All36 paired responses match
exact token arrays. The five repeated512 outputs also match preserved original
`2346de909` outputs exactly. Bounded quality screen3/5 versus original2/5; all
five final plain/MTP quality responses are token-identical. Q8 prefill changes
22/24 workload trajectories against the original kernel; no lossless-Q8 claim.

Both servers exited rc0 and are confirmed absent: plain3008684 at00:08:13Z,
MTP3054886 at00:26:13Z. Physical q0-q3 CPU locks released. Production untouched.

The Qwen optimization reachability audit found GLM already uses the major
shared champion paths. The implementation exposes IQK Q8 prefill above logical
row32 and scopes row-exact arithmetic to verified target batches, preserving
prompt chunks and draft state. Decode improvement is parallel-verification
amortization, not an independently demonstrated Q8 dot-kernel gain.

[Implementation report and raw evidence](../../docs/reference/models/glm53-cpu-optimization-20260908.md).

Independent final audit PASS, SHA256
`7bce7808c1042a49ce012d4593ef5bc3ff0b573d4c1d34027a34c7656bbb3626`:
seven measured fixed512 windows contain1262 completed verification events,
2314/3777 drafts accepted,1039 events with acceptance and743 with actual
rejection. Plain has zero events. Exact generated tokens do not imply exact
logits; fixed512 tests use ignore_eos. All raw evidence and request identities
are retained. Broader natural-EOS/role-quality certification is not claimed.

Portable workload helpers and pinned inputs committed as `49612aae5`; benchmark
identity remains kernel `04ffb8ad0`. Wrapper/client10/10, serve-plan6/6,
artifact4/4 (+one opt-in skip), py_compile and diff checks pass. Main independently
reran the six new client checks successfully. Candidate tree is clean.

## Reprofile and next levers

Operator requested fresh profiling after the integrated improvements. Canonical48
plain/MTP profiles captured prefill and decode separately with model load excluded.
The2029-token MTP attempt exposed a selector-width assertion across ubatches;
fix7c78663de suppresses unused prompt-catch-up export, and c463f601b adds a
full-ubatch control. Old-binary negative control aborts; both repaired aliases
pass selection equality and declared logit tolerance. The original experimental
source/build is current and clean; production remains frozen.

Final matched fixed2029/512 profiles have exact plain/depth3 tokens and real
accepted/rejected drafts. CANDIDATE observations:7.3249 plain versus8.8855 MTP
output tokens/s. MTP expert self cycles31.53%, Q8 25.71%, OpenMP23.37%; expert
cycles/output rise15.14% while Q8 falls45.40% and OpenMP falls25.59%. Expert
kernels/conversion also account for32.7% of prefill cycles. Rank next work as
exact multirow K-expert reuse, exact batched Q8, then measured graph granularity.
No speedup forecast from cycle shares and no DRAM saturation claim.

One corrected flat-key depth2 control is rejected:8.6150 output tokens/s and
first divergence at generated index58. An earlier nested-key attempt was ignored
and retained as an instrument diagnostic. No broader depth sweep was performed.
All owned server PIDs are confirmed absent and q0-q3 claims released.

[Full report](../../docs/reference/models/glm53-cpu-next-levers-20260909.md).
Independent audit SHA256:
`41628e353a153fd33fd34a9fd95d9ba9b5d41e91064a9350d30dc829e6a62fff`.

## Three-lever implementation started

Operator authorized exact expert batching, exact Q8 verification batching, and
node-level worker-wait measurements followed by bounded scheduling work. Three
subagents handle independent implementation/measurement tasks; main reviews
scope, numerical invariants and integration. Preserved c463 source/binary
baseline lives at `glm53-validation-20260908/baseline-c463f601b`.

The earlier near-11 result is 10.82479 output tokens/s on the 24-prompt workload;
the five repeated 512-token median is 9.60451. The later 8.8855 profile uses a
different, long prompt and instrumentation, so it does not establish regression.
New comparisons retain separate workload identities and unprofiled repeats.
Implementation and validation are in progress; no new speed gain is claimed.

The compiled expert-kernel gate passes (`lever-build-20260909T081400Z`): Q4_K
49,152 and Q5_K 98,304 outputs are bit-identical to the serial Ny=1 path, with
optimized-branch trace witnesses. The binary is newer than the expert source;
`libggml-cpu.so` SHA256 is
`a043d602b9f91302e0e54296cda41d2e325d2a01a1656912614977f06ed9b94f`.
The four-case Q8 test also passed in that build, but Q8 source and its test were
edited afterward. Rebuild and revalidation are required before attributing that
gate to the current source.

The first plain-baseline and profiler-off runs are superseded because their
launches omitted `GGML_IQK_Q8_0=1`, `GGML_IQK_Q8_0_MIN_ROWS=32`,
`GGML_ROWEXACT_N=16`, `LLAMA_SPEC_EXACT=row`, and reasoning-off request state.
`GGML_IQK=1` was present. They are diagnostic records, not canonical recipe observations.
Corrected profiling and final comparisons use explicit launch receipts and
bracketed/interleaved controls. No new full-model speed gain is claimed yet.

Catch-up publication audit found all six GLM documentation commits through
`7fcb2e7c` local-only while `origin/main` advanced independently: `aaa83713`,
`da6390e0`, `7e0f341e`, `3911b462`, `66a7d756`, and `7fcb2e7c`. Publication is
being reconciled through the isolated `lane/glm53-three-levers-20260909`
worktree; the shared dirty root clone is not a safe merge or commit surface.
Committed candidate base `c463f601b` is backed up on private fork branch
`experimental/glm53-text-mtp-20260908`; the current uncommitted kernel
experiments are not part of that push, and upstream/production remain untouched.

## Current operator gates and microdiagnostics

The specialized mode-1 Q8 source passed its compiled gate. Normal execution
and CTest pass all four exact operator cases with an active rows=4 trace, covering
Ny2/3/4, native and converted Q8, noncontiguous input, broadcast stride, multiple
heads, and three-thread chunk tails. The built `libggml-cpu.so` SHA256 is
`9ca2c34504642ff3523b48a688c56b351e579c57b3e1c3a14730b7b69571799d`; the
test binary SHA256 is
`31ba209bbed602c0369706d6188c34b6e7f041f601736bdde2f7034be1319131`.
Evidence is under `lever-micro-20260909T083200Z`. A first exact Q8 diagnostic is
negative: 0.960x for the 64-head MLA shape and 0.943x for the output projection.
The interleaved repeat is still pending, so this does not yet reject the lever or
establish the cause.
Subsequent mode-2 source development adds two-weight-row tiling; its compiled
gate remains separate and is not covered by these mode-1 results.

The expert reuse microdiagnostic produced 80/80 unique cells across Q4_K/Q5_K,
widths1–4, two arms, and five paired rounds at 48 requested graph threads with
200 timed iterations per cell. Every paired output hash matches and remains stable
across rounds. Median paired serial/optimized ratios for widths2/3/4 are
1.0746/1.1197/1.1491 for Q4_K and 1.1080/1.1564/1.2273 for Q5_K. Width1 controls
are 1.0165 and1.0127. Pair ranges are wide, including 1.018–1.349 for Q4_K width4
and1.048–1.592 for Q5_K width4. The raw JSONL SHA256 is
`6635be22a932635612436ae444b9404bb9352c779946c9d5125defd1edc160b9`;
bench binary SHA256 is
`ab02d07610fcf1f334d76fa8c436831c54d65c112cc5bcd6cbe50c286fb347f3`.
The wrapper did not retain an outer affinity/NUMA/OMP receipt, so these are noisy,
noncanonical kernel-level diagnostics and no full-model gain is claimed.

A matched full-model screen then isolated expert reuse with Q8 row batching off.
Both arms used the preserved mode-1 snapshot: server SHA256
`2034495c3f386123990082ad3ede4ea0e38164b22f9996bbe2561db956ccce07`
and `libggml-cpu.so` SHA256 `9ca2c34504642ff3523b48a688c56b351e579c57b3e1c3a14730b7b69571799d`.
Actual launch receipts confirm canonical 48-thread affinity, NUMA interleave,
OMP settings, native MTP depth3, row-exact scoping, Q8 prefill threshold32, and
`GGML_Q8_ROWEXACT_BATCH=0` in both arms. The expert-on log witnesses the rows=2
branch; the off log does not.

Both arms emit the same 512-token SHA256
`b3ab59a69a821c714357a95e54df03490bee1ba73b404548f6ae88c417fdb576`,
which also matches the prior plain and MTP reference. Each reports 561 drafted
and 323 accepted tokens; parsed logs contain 187 completed verification events,
including 122 events with actual rejection and 238 rejected draft tokens. Off is
9.89853 output tokens/s and expert-on is 9.73052, a 0.98303x ratio. Both owned
servers exit rc0 and are confirmed absent. This single short-prompt screen is a
rejection signal rather than a sustained benchmark; expert reuse remains off and
does not warrant a five-repeat expert-only run. Evidence is under
`lever3-screen-20260909T085500Z`.

Checkpoint `558e8005` and the six earlier GLM documentation commits are safely
pushed on `origin/lane/glm53-three-levers-20260909`. A guarded clean promotion to
the independently advanced root `main` was aborted because the generated
`master-handoff-index.md` conflicted with remote commit `519acd08`; the lane is
the durable backup and main was not modified. Candidate base `c463f601b` remains
backed up on the private experimental fork. The uncommitted expert/Q8 kernels and
the ongoing full-model/scheduling experiments are outside both pushes.

### Q8 mode-2 compiled milestone

The two-weight-row Q8 experiment preserves each output's original accumulator
and reduction order. Modes 0/1/2 each pass five exact operator cases; CTest and
ACTIVE witnesses pass. Correctness uses three workers for chunk tails; the
AB/BA microbenchmark uses 48 workers, explicit affinity/NUMA/OMP placement,
and verifies identical outputs. MLA means are 0.074/0.069 ms (1.0730x); output
projection means are 4.403/4.305 ms (1.0230x). This is a bounded kernel screen,
not a full-model speedup. Full-model mode 0/2 comparison keeps expert reuse off.

Evidence: `q8-mode2-20260909T085524Z` under the validation artifact root.
CPU library SHA256 `e8c93f6c095fa642bef1c72fb156d1ca98a17666fea63dfac702416d3fdcf451`;
test SHA256 `32c41b5e939801cbb733e3fc8922392bdb4542cfbf5784f7cd09d2b6a990870a`.
Assembly review found no vector accumulator spills in the specialized mode-2
hot loops. Both experimental levers remain disabled by default.

The guarded expert and Q8 source/test experiments are committed and pushed as
`0da0d2728` on the private `fork/experimental/glm53-text-mtp-20260908` branch.
This backs up the implemented work; it does not enable either experiment. The
expert CTest platform guard and ordered microbenchmark sample logging still
need their final build check. Production remains untouched.

### Q8 projection-kernel full-model screen

This experiment changes exact dense Q8 projection kernels inside the same
six-shard UD-Q4_K_XL model; it does not switch to a Q8 model. Both arms load
`GLM-5.3-Flash-UD-Q4_K_XL-00001-of-00006.gguf` through the pinned manifest
SHA256 `d3c6c3ccc4cf2aa13ff4294696b345ac7e1f2f8755bc0bbcfd27749ffae2dbec`
(metadata SHA256 `cec7c7d42b151607954305f5ede2d01d74d4a3b8df92af7e7fa4cc5a931e34bd`,
1,412-tensor set SHA256
`08afa6cd3aecc131612384a7a3912bfb059fdb640a60f56c70835eeaecc9375c`).
Both use server SHA256 `2034495c3f386123990082ad3ede4ea0e38164b22f9996bbe2561db956ccce07`
and CPU library SHA256
`e8c93f6c095fa642bef1c72fb156d1ca98a17666fea63dfac702416d3fdcf451`.

Mode0 and mode2 match the prior plain/MTP 512-token SHA256
`b3ab59a69a821c714357a95e54df03490bee1ba73b404548f6ae88c417fdb576`.
Each reports 561 drafts/323 accepted tokens and 187 completed verification events,
including 122 events with rejection and 238 rejected draft tokens. Mode2 emits
the active rows=2 trace; expert reuse is disabled in both arms. Both owned
servers exit rc0 and are confirmed absent.

Observed rates are 9.0174 mode0 and 9.4659 mode2, an apparent 1.0497x ratio, but
the performance comparison is invalid. The mode0 observation overlaps median
unrelated work of 8.41 CPU-equivalents (maximum 11.16), dominated by 358.55 CPU-s
from `libuv-worker`; mode2 overlaps 1.82 median CPU-equivalents (maximum 3.48).
This pair establishes full-model correctness and reachability only. Mode2 stays
off pending a clean bracketed/interleaved comparison. Evidence is under
`q8-fullmodel-screen-20260909`.

An immediate second mode0 bracket ran after mode2 with comparable unrelated load
(1.92 median CPU-equivalents) and produced the same token/MTP/rejection evidence
at 9.30458 output tokens/s. Against mode2's 9.46585, that clean single bracket is
1.01733x in mode2's favor. It warrants inclusion in the interleaved short screen,
but remains insufficient for enablement or a sustained speed claim.

### Graph-worker profiling milestone

The filtered plain capture did not support an independent tiny-op or MLA
scheduling patch. The MTP target-topology capture exposed a separate copy
partition defect: 34 recurrent-state CPYs shaped `[1048576,1,4]` consume
11.132 ms of the 255.442 ms per-node wall sum. Existing code partitions only
`ne01`, assigning all four 4 MiB snapshots to one worker. The approved
`GGML_CPY_OUTER_ROWS` experiment distributes complete outer rows, retaining
the existing path for aliasing storage/rows; it remains default off pending
byte-exact, rollback/replay, and timing gates.

The capture mixes three prompt graphs with 99 verification graphs; metadata
comes from the first prompt graph. The 4.36% wall share is an opportunity
bound, not recoverable speedup. Full digests, denominator distinctions and
source audit are in `docs/reference/models/glm53-cpu-worker-audit-20260909.md`.
