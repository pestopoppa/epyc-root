# GLM53 CPU optimization — 2026-09-09

> **CPY diagnosis correction (2026-09-09):** later route verification disproved the state-copy single-worker claim recorded below. Actual GLM state tensors are contiguous and already copy across 48 workers. The padded-copy experiment and microbenchmark are rejected as GLM optimizations; commit `f8e2668b6` removes them. Earlier entries remain a chronological record, not current recommendations.

## Current disposition

Core `c463f601b` is **not accepted** into the AutoKernel champion. The canonical
champion remains `ef81196d5`; frozen production is also unchanged. Fresh GLM
validation passed all 31 full-model plain/native-MTP trajectory pairs plus the
alias, rollback, restore, pooled-state, long-export and real-model phase gates.
The matched historical-harness sanity checks then measured:

- Flash-Next CPU native MTP: 32.152575 tokens/s versus historical 43.280708.
  All 24 historical output/draft trajectories match and the original contention
  screens are clean, but the one-launch cross-session comparison does not resolve
  cause and does not clear performance admission.
- Qwen3.8-27B GPU DFlash2: 79.598706 tokens/s versus historical 79.245255 under
  the same recipe, prompt and warmup, with residency proven.

No inference remains pending from this session. Future investigation of the CPU
result belongs to AutoKernel. Four `measured_null` records were inserted and
independently retrieved under campaign `ak-external-glm53-core-20260909`; inbox
`24-glm53-core-c463-external.md` is live. The evidence bundle and receipt are at
`/mnt/raid0/llm/autokernel/loop-memory/external/glm53-core-c463-20260909/ingestion-receipt.json`.
The seed preserves source and negative knowledge and cannot advance the champion.

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

### Graph-worker profiling correction

The filtered plain capture did not support an independent tiny-op or MLA
scheduling patch. The mixed MTP target topology records 34 recurrent-state CPYs
shaped `[1048576,1,4]` at 11.132 ms of the 255.442 ms per-node wall sum and
4.459 ms wall-minus-compute. Those measurements remain valid. The initial
single-worker diagnosis does not: inventory contiguity flags show both operands
are contiguous, so these nodes return through the existing contiguous path and
partition blocks across all 48 workers before the noncontiguous branch is
considered. Their `ne01=1` dimension does not serialize the four state planes.

The inventory instead contains 408 qualifying F32 `[3,8192,1,1]`
noncontiguous-source copies. These already partition over 8192 rows and account
for 0.564 ms compute and 1.512 ms wall, 11.85% of measured CPY wall. The first
full-model ACTIVE marker reported 8192 rows, verifying that route class. The capture
still mixes three prompt graphs with 99 verification graphs, and metadata still
comes from the first prompt graph. Full digests and denominator distinctions are
in `docs/reference/models/glm53-cpu-worker-audit-20260909.md`.

### Rejected recurrent-copy experiment

Private experimental commit `068db793f9be9225910ce80827129f959a5a4979`
implemented default-off `GGML_CPY_OUTER_ROWS` with conservative overlap and
self-overlap fallbacks. Its focused tests passed for separate and fallback
layouts, and the serving snapshot was structurally verified. That validates the
discarded implementation's copy semantics; it does not establish model
reachability for the costly state copies.

A corrected process-isolated AB/BA microbenchmark passed all 10 exact pairs and
preserved full backing bytes, padding, and canaries. For a synthetic padded,
noncontiguous F32 `[1048576,1,4]` layout, mean off/on time was
0.464135/0.183828 ms (2.524827x), with median ratio 2.430912x. The profiled GLM
state copies do not have that layout, so this is a rejected synthetic
copy-operation observation. Evidence remains under
`cpy-outer-rows-micro-20260909T092432Z`; benchmark-only commit `a4ec393a9`
changes no serving arithmetic.

The exact five-arm full-model selector observed 9.4175 tokens/s opening
baseline, 9.6354 Q8-only, 9.3428 CPY-only, 9.3031 combined, and 9.0335 closing
baseline. Opening-to-closing control drift was 4.08%, so the screen supports no
Q8 or CPY throughput claim. CPY reachability is independently sufficient to
reject the experiment. Private commit `f8e2668b6` removes the CPY serving change
and tests; the experiment remains off and is not retained. Q8 projection-kernel
mode 2 was then tested by the balanced repeat below and rejected.

### Final balanced selection and speculative-regression gate

The CPY route correction was applied before the final selection. The inventory
contains 408 qualifying small F32 `[3,8192,1,1]` copies and the first ACTIVE
witness verifies the 8192-row route class, but the 34 costly recurrent-state
copies are contiguous and already use the 48-worker block path. Commit
`f8e2668b6` removes the discarded CPY experiment.

The final Q8-only candidate is immutable source `f8e2668b6` (`llama-server`
10317, GCC 15.2.0; `libggml-cpu.so` SHA256
`e8c93f6c095fa642bef1c72fb156d1ca98a17666fea63dfac702416d3fdcf451`).
A canonical-48 A3/B3/B2/A2 run used two fresh server blocks per setting, three
fixed warmups per block, and five measured 512-token requests per setting.
Baseline rates were 9.32649, 9.28935, 9.28663, 9.03302 and 9.22355 tokens/s;
Q8 mode-2 rates were 9.15811, 9.17208, 9.02353, 9.04518 and 9.03279. Means
were 9.23181/9.08634 (0.98424x) and medians 9.28663/9.04518 (0.97400x).
Other-process load medians were 1.80/1.79/1.61/1.94 CPU-equivalents in block
order. One Q8-A sample interval spiked, but the clean Q8-B block remained below
both controls.

All stable-key response projections match. Corresponding three-request blocks
record 392 rejection events and 764 rejected tokens; two-request blocks record
270 and 525. Actual guard environments and Q8 ACTIVE/disabled witnesses match
each arm. Evidence is
`q8-retained-short-balanced-20260909T094600Z`; audit SHA256
`53ac46cbce16c7c57d8b076b44174d8829f442532489f71fae93e3bbd1a25ebe`.
The exact Q8 experiment remains default off. Since it failed the repeated short
gate, the protocol stopped before long/prefill/canonical performance runs.

All final speculative-regression executables pass against `f8e2668b6`. Both GLM
aliases pass rollback, used-MTP restore, pooled-state and long-export controls.
The real-model row-exact phase gate matches serial exactly in all six reject,
no-reject, prior-rollback and off/on/off reused-context comparisons. The first
launcher exit 1 occurred only after compute because an obsolete postprocessor
rejected additional exactness fields; corrected required-subset processing
passed without rerunning inference. Evidence is
`final-spec-regressions-candidate-f8e2668b6-20260909T094115Z`.

No additional lever from this round is retained. Expert and Q8 implementations
remain guarded/default off for future discovery, while CPY was reverted. The
existing Q8-prefill plus exact parallel-MTP recipe remains current. Future
AutoKernel work must start from source rather than an ephemeral binary; the
exact fork branch, build, canonical launch and completion gates are in the
[AutoKernel handoff](../../docs/reference/models/glm53-autokernel-handoff.md).
For future cross-build controls, the preserved baseline binary reports
`7c78663de`; it was not used in the balanced same-build short comparison. Its
only delta through `c463f601b` is a test-file change, so it is serving-code
equivalent but must be named honestly in future provenance.

### Wrap-up publication state

The final source is already backed up on the private fork: branch
`experimental/glm53-text-mtp-20260908` resolves to `f8e2668b6`. Root
documentation is prepared in the isolated `lane/glm53-three-levers-20260909`
worktree. A guarded sync against `origin/main` at `afc041c9` was aborted with
main untouched because the sole conflict is the generated block in
`handoffs/active/master-handoff-index.md`; the wrap-up lease was released. No
index regeneration or wiki-watermark update will run until that conflict has an
explicitly authorized resolution. The prepared documentation is therefore not
yet committed or pushed.

### Operator-authorized champion integration started

The operator directed actual integration, not only a recommendation. The validation
worktree `/mnt/raid0/llm/llama.cpp-experimental-glm53-champion-20260909` was created
at the clean live champion `ef81196d5` and fast-forwarded to core `c463f601b` on
`ak/champion-glm53-candidate-20260909`. The existing canonical champion, rejected
experiment reference `f8e2668b6`, and frozen production remain unchanged while
validation runs. T15 tracks admission into the single canonical champion.

Fresh matching GCC 15.2 Release CPU builds completed for both old champion and
core candidate. Main independently verified every file hash: 14 serving files
per snapshot, three baseline tools and seven candidate tools. Snapshot receipts
under `/mnt/raid0/llm/tmp/glm53-validation-20260908/`:

- `champion-baseline-ef81196d5-cpu/IDENTITY.json`: `bedcbbb8936da0ec7a8f36fb75c52eff52360d86f06ecd62992249f8d8b71a10`; version 10301 (`ef81196d5`).
- `champion-candidate-c463f601b/IDENTITY.json`: `0f4839a630649cbb2e4847456c5cf9d6123885ca72a38abc204851711cd1260a`; version 10313 (`c463f601b`).

The candidate HIP build follows with the house flags. CPU inference waits for
compilation to release the physical CPU region; the planned gates cover fresh
GLM rollback/replay and 31 plain/MTP trajectories, existing Qwen CPU parity and
launch-unit performance, then GPU regression and refreshed aggregate standing.
These are planned gates, not passing results.

### Fresh integration build and GLM fixture milestone

The HIP build completed with matching house flags and gfx90a target. Its immutable
serving snapshot is `champion-candidate-c463f601b-hip`, identity SHA-256
`b4151b41bf9cb108e54101c5877330576d44602c029a5dbdbf9b0594621810ce`.
The existing HIP control was separately proved to be build 10301 at `ef81196d5`
in `/mnt/raid0/llm/tmp/build-fold-ef81196d5`; no source-path label was accepted
as binary provenance.

Fresh candidate CPU regressions passed at
`final-spec-regressions-champion-candidate-c463f601b-20260909T104706Z`: both
architecture aliases' rollback/restore/pool/long-export gates and all six
real-model phase comparisons, each with maximum absolute logit difference zero.
The separately invoked dense-Q8 cached-plan diagnostic restored its output but
produced no on/off numerical difference (exit 3, missing witness); it is not a
passing toggle witness and is retained as inconclusive diagnostic evidence.
The required phase/replay suite remains nonvacuous and passed independently.

The already-authorized full-model plain/MTP pair was inadvertently started by
a command described as a preflight; the runner has no dry-run option. It is
running under `/tmp/unused-champion-dry`, using the verified candidate, canonical
CPU lock and explicit recipe. The pathname alone does not invalidate its data.
Its inputs and launch/runtime receipts must match, and all 31 trajectory gates
must pass before acceptance; preserve the original and archive it durably after
completion. No performance result is claimed at this in-progress milestone.


### Champion integration: full-model GLM gate complete

The corrected 48-thread plain/MTP suite finished at 11:39:55Z. Its durable bundle is
`/mnt/raid0/llm/tmp/glm53-validation-20260908/champion-core-pair-c463f601b-20260909T105800Z`.
All 31 paired token trajectories are exact: short512 ×5, long2029/decode512 ×1,
prefill2029/decode1 ×1, and canonical24. The plain log has zero verification events;
MTP has 2,804 verification events containing 5,419 accepted and 2,949 rejected tokens.
Both servers exited rc0; captured PIDs 637170 and 687017 were independently checked absent.

The original bundled final analyzer rejected null absent plain draft counters before
consulting its zero-event log. A separately pinned post-hoc audit corrects only this
schema interpretation and returns PASS in `comparison-audit.json`; raw serving records
remain unchanged. The earlier partial attempt at `/tmp/unused-champion-dry` failed on
a prefill-wrapper count-validation bug before that request and is instrumentation
failure evidence, not a kernel failure or completed comparison.

The operator clarified that yesterday's Qwen champion results are the existing baseline:
run only the NEW candidate to check regressions, not the old champion again. The new
candidate-only suite acquired the CPU regions after the GLM servers exited and is using
`/mnt/raid0/llm/tmp/inf70/agents/retest1/CHAMPION-FINAL.md` and its raw six-launch-per-mode
records. GPU candidate gates follow. The operator explicitly authorizes official admission
into the same canonical champion if no regressions occur; frozen production is unchanged.


### Operator-narrowed single-stream sanity checks complete

The operator narrowed validation to basic single-stream Flash-Next MTP CPU and
Qwen3.8-27B DFlash2 GPU sanity, explicitly requesting no extended campaign.
Flash-Next (`qwen4exp`, uniform IQ4_XS trunk/shared Q8 head, 48 threads) completed
one plain and one MTP launch, each with 24 exact historical output/count/finish
trajectories; MTP draft counters also match. Launch-weighted observations are
19.7061 tok/s plain and 31.0587 MTP. The historical instrumented baseline gives
27.8934/43.2807, but its own CHAMPION-DIVERGENCE record flags an unexplained high
regime. Static audit found matching active dispatch/recipe and no attributable
GLM regression; it cannot prove unchanged throughput. Repeats were stopped.

The separate Qwen3.8-27B GPU DFlash2 smoke passed on c463: 384 tokens, 65.0559
tok/s, acceptance 0.6427, 1.963x versus same-build no-spec 33.15 tok/s. Live MI210
residency peaked at 34,713,210,880 bytes, KFD was nonzero, and all owned processes
exited. The existing smoke acceptance/speedup thresholds passed unchanged.
Candidate GPU operator/dispatch gates had already passed before scope narrowing.
No 20-pair standing refresh or additional broad tests were launched.

The canonical Flash-Next CPU recipe is native MTP, not DFlash2. Main initially
agreed prematurely with a suggested DFlash2 mismatch, then checked the recipe,
model architectures and on-disk head and corrected the statement: the available
DFlash2 head belongs to the distinct 27B target.

The candidate remains published at c463f601b on the private validation branch.
The canonical champion and frozen production are unchanged: functional sanity
passes, but the unresolved CPU performance observation does not satisfy a
claim of demonstrated no-regression throughput. The requested bounded sanity
work is complete, with no further inference left running.


### Matched historical-harness retest (operator-requested)

The operator requested last night's exact tests after questioning the GPU65.06 and
CPU31.06 observations. One candidate-only launch was run per model; no old champion
was rerun. GPU imported the exact canonical np1 recipe (hash68fe27f39db7…), used the
same odd-number induction prompt, context16384, sampling, 384-token warmup and
384-token measured request. Candidate c463 measured79.598706 tok/s against the
historical ef811 median79.245255: no slowdown signal in this sanity observation.
The earlier65.06 smoke was a different prompt, context4096 and cold first request;
it was not a valid performance comparison. Evidence:
`/mnt/raid0/llm/tmp/glm53-validation-20260908/exact-maxperf-candidate-c463-20260909T122252Z/result.json`.

CPU used the unmodified historical session2.sh, harness1/client.py and targeted
cache eviction, with the same 24 prompts, native shared-Q8 MTP nmax4/pmin0.5,
48 threads, interleaved placement and verified THP shim. The non-instrumented
candidate uses NO_KNOBS=1; the historical instrument's equivalent control knob
values are absent from this binary rather than silently assumed writable.
The full launch measured32.152575 tok/s versus historical43.280708 (-25.71%).
All24 text/count/finish/draft trajectories match exactly, including3267 proposed
and2682 accepted tokens. Both original contention screens reported CLEAN; NUMA
placement remained balanced. This confirms the CPU slowdown observation survives
restoring the original harness; its causal attribution remains unresolved.
Evidence: `/mnt/raid0/llm/tmp/inf70/agents/retest1/runs/C463_EXACT_MTP_20260909T1224Z.timeline`
and `c463_exact_mtp_20260909T1224Z.rows.jsonl`. Server4076756 exitedrc0 and all
CPU regions are free. No further tests were launched; official champion admission
remains withheld on CPU performance.

## AutoKernel reuse disposition

The operator explicitly approved seeding the actual AutoKernel experiment memory with today's GLM work, keeping champion ef81196d5 unchanged. The c463 core and f8 rejected-experiment reference are both pushed to private fork branches, verified with ls-remote. The source handoff now labels the core NOT ACCEPTED and carries the matched CPU acceptance hold, GPU sanity observation, and fresh GLM correctness gates. The memory seed preserves implementation and negative knowledge; it does not claim promotion, a resolved regression cause, or permission to mutate frozen production.

AutoKernel seed completed and independently retrieved: four `measured_null` records in `/mnt/raid0/llm/autokernel/loop-memory/experiments.db`, campaign `ak-external-glm53-core-20260909`. Inbox `24-glm53-core-c463-external.md` is read by the normal loop. Self-contained evidence bundle: `/mnt/raid0/llm/autokernel/loop-memory/external/glm53-core-c463-20260909`; receipt `ingestion-receipt.json`. Envelope SHA-256 `6ab1cd967603a6feb1ef369cc16a3756ea7eb3fd85e924ed847fff1a3cc9507f`. Idempotence verified (four initial inserts, zero duplicate inserts); records are cross-epoch/noncomparable and cannot advance champion.

## Full-session wrap-up and approved documentation reconciliation

The operator approved the audited targeted resolution on 2026-09-09. Publication uses isolated lane `lane/glm53-wrapup-publish-20260909`, combining the session history through `10db0f30a` with main `77995fe4`. The generated master-index conflict was recomputed from combined handoffs; all incoming authored operator decisions were preserved. INF-69 retains the seeded CPU-investigation next action while main's other rows remain intact. The wiki preserves every incoming content line, including the Qwen35B result and archived-link repairs, and adds the GLM findings and nonacceptance/seed disposition. No champion or production-kernel modification occurred.

Index coverage/schema/freshness passed after regeneration. Conservative pruning found zero candidates; no handoff was archived or compacted. README freshness emitted no warnings. The full wiki source scan identified 15 added/changed sources: GLM findings and evidence are synthesized in inference-serving, and the concurrent upstream documentation is reviewed before advancing the shared manifest. The AutoKernel memory's four records remain retrievable; its content-addressed 11-file bundle is separately verified. No new inference is queued by this wrap-up.
