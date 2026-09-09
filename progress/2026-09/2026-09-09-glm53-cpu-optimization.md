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
