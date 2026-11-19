CAFE-4 rollback modes
====================

`cafe4_port.py` materializes a source port of the real-MTP V4 rollback
candidate from git blob `53035f75429327e82454f7d26f7dd67f65c80c16`.
The pinned historical source remains unchanged. Generate into scratch:

```bash
python3 scripts/diagnostics/cafe4_port.py --output /mnt/raid0/llm/tmp/df2/cafe4-modes/candidate.cpp
```

The builder needs `cafe4_modes.hpp` from this directory and
`mtp_draft_bridge.hpp` from
`docs/reports/cafe4-rollback-preparation/draft-rewind-v4-20261104/`
on its include path. Use an experimental worktree based on production v10
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`, with the existing target snapshot
instrumentation in
`docs/reports/cafe4-rollback-preparation/geometry-frozen-build-20261104/source.patch`.
Never build or patch the production tree. A full build and native runs must go
through published rows; this source result is not their qualification.

The generated executable accepts:

```text
candidate model.gguf [-ngl N] [--verify-batch d] [--fault-injection]
```

`N` is a nonnegative GPU layer count, passed to model loading. `d` is the
maximum number of MTP draft tokens (2–63); the target verify batch also includes
the boundary token. The default remains CPU, width 3. Snapshot capacity grows
to at least `d+1`. The diagnostic caps acceptance to half the actual draft,
requires a strictly positive partial acceptance, removes the rejected suffix
from both contexts, and replays the target correction. Insufficient proposals
or failed native calls remain UNKNOWN.

Every run retains the off/observe/fault matched-prefix controls. Default success is rc0. `--fault-injection`
requires the same controls and emits `RESULT FAIL injected-fault`, rc1,
only after the injected target-snapshot divergence is demonstrated. Missing
nonfault agreement or absent fault sensitivity yields UNKNOWN, rc2, in either
mode. An arbitrary nonzero exit is not a successful fault-control result.

Validation on 2026-11-19: five model-free tests pass, including malformed
arguments, width bounds, GPU-layer propagation, all eight exit-control
combinations, and fail-closed source anchors. The generated source passes
`c++ -std=c++17 -fsyntax-only` against a detached v10 worktree with the above
patch. Generated source SHA-256:
`71ce1fb3e92098dfb586b06000a0ed4dee1e836c7c889774cb754dcde8f1b597`.

```bash
python3 -m unittest discover -s scripts/diagnostics -p test_cafe4_modes.py -v
```

No native rollback, GPU residency, or fault verdict is asserted by these tests.
The later single-prompt relative-floor diagnostic is separate evidence. The parent
CAFE-4 task remains open until the port's scheduled native controls land.


Cold-reference decode-boundary correction (2026-11-19)
-----------------------------------------------------

The filed width2 UNKNOWN used a reference whose second decode contained
`boundary + accepted draft + sampled correction` together. The subject decodes
`boundary + draft` during verification, removes the rejected suffix, and then
decodes the sampled correction alone. Fusing that final correction into the
reference prefix is a concrete harness geometry mismatch. The generator now
decodes `boundary + accepted draft` and then the correction separately at
`keep`. This aligns the final replay boundary; the accepted-only reference
still differs from the subject's full verify batch. It does not isolate every
batch-shape effect or prove the cause of the observed 0.907920361 error.

The gate is frozen at **0.743863867** (lower error is better), preserving the
filed width2 threshold without recalibrating it against this changed reference.
The former dynamic reference-floor calculation is retained as a diagnostic
`CAFE4_REFERENCE floor=... tolerance=...` line. Nonfault comparisons and the
10x fault-sensitivity requirements are unchanged. Width3 has no prior executed
verdict; this prospective fixed gate applies to both widths. The published CPU
and HIP R3 artifacts are immutable and still contain the earlier source.
Do not use their build receipts for this corrected generator output.

Six model-free tests PASS. A compiled decoder spy executes the generated
reference block for acceptance counts 1, 2 and 31, checks token partitions and
positions, and checks early return at each failed decode. Pin/anchor tests
reject source drift and guard the frozen tolerance. The generated candidate
also passes C++17 syntax checking against the existing detached v10 diagnostic
worktree. Generated SHA-256:
`41fc473a908b7c385d79d1941b6576cc993b985e691682d6598d6122e968fe1c`.
Historical base blob: `53035f75429327e82454f7d26f7dd67f65c80c16`.

Next: prepare fresh hash-bound CPU/HIP build rows for this source, then qualify
native width2/3 normal and explicit-fault controls under the fixed gate.
No numerical rerun or rollback verdict was produced by this code correction.
[no-belief: source correction and model-free tests only]

Native failure attribution (2026-11-19)
---------------------------------------

The scheduled HIP R4 native diagnostic ended rc2 before numerical controls:
its combined message could mean an incomplete trial or any draft/prefix
mismatch. That record cannot identify a particular predicate retroactively.
The generator now reports `CAFE4_TRIAL_FAILURE` at every failed trial return,
with mode, requested width, stage, draft length, accepted count, sampled token
and the observation's selected/faulted counters. Thirty stages cover native
initialization, proposal, verification, strict partial acceptance, suffix
removal, correction, counters and both cold references. Compound configure /
prompt-process and target / draft suffix-removal calls are split in their
original short-circuit order.

`CAFE4_CONTROL_FAILURE` identifies each failed off/observe/fault lifecycle
check and each of the four prefix/draft comparisons. Token differences include
both lengths, first differing index and values (`-1` indicates a missing side).
All seven checks report even if an earlier check fails. The old combined UNKNOWN
message and rc2 remain; success is silent at these seams. No control is relaxed,
no token prefix is forced equal, and the **0.743863867** gate and 10x fault
requirements remain unchanged. This diagnoses a future run; it does not
identify the prior native root cause or prove rollback correctness.

**8/8 model-free tests PASS**. Compiled tests exercise each independent control
failure and simultaneous failures, preserve the old guard's truth value, check
trial telemetry, and execute the generated reference decodes with injected
failures and exact stage attribution. Generator drift fails closed. The complete
generated candidate passes C++17 syntax checking against the existing detached
v10 diagnostic worktree. No full build or native inference ran this turn.

Bindings:

- Historical source blob: `53035f75429327e82454f7d26f7dd67f65c80c16`.
- Generated scratch source: `/mnt/raid0/llm/tmp/df2/cafe4-failure-diagnostics-20261119/candidate.cpp`, SHA-256 `e6546aa7417e40efecdd2bb03de61416bf62ae21b7c1369b7161e443201f835d`.
- `scripts/diagnostics/cafe4_port.py`, SHA-256 `4b7ad1b8b4a5460916f9fd6ea0ae72bef944c186f7b85ce466aaf971494c4b7b`.
- `scripts/diagnostics/cafe4_modes.hpp`, SHA-256 `f544e718f34f2b7347d2ceeebf566eb575250c20760720676682512573507848`.
- `scripts/diagnostics/test_cafe4_modes.py`, SHA-256 `f3da152274f79c513299c78f292e61045fd79e613ebc6ca32bd276763b34376f`.

Existing CPU R2 and HIP R4 binaries retain their bound source and do not contain
these diagnostic messages. Next publish a fresh HIP build qualification with
the generated-source/header digests and compiled failure markers; only then
publish a native GPU row under the unchanged controls. The existing CPU R2 row
remains independent. Existing CAFE-4 source registration applies.
[no-belief: diagnostic source change and model-free tests only]

Pre-rollback token provenance (2026-11-19)
-----------------------------------------

HIP R5 stopped at strict partial acceptance in modes1/2. Its matched-control
messages record first draft token 248068 for off versus 32 for observe/fault;
the receipt does not record the boundary token or each target prediction.
The original UNKNOWN does not distinguish changed prefill from changed MTP
proposal or target verification. No kernel root cause is established.
Original RESULT (retained in place):
`/mnt/raid0/llm/tmp/df2/cafe4-modes-native-hip-r5-20261119/RESULT.json`,
SHA-256 `340863a393b964d58a72038cc584ed5bbcb7eb1e547e0b225a4dde75f4db6144`.

The generator now prints three native token witnesses, tagged with mode/width:

- `CAFE4_BOUNDARY`: the prompt's already-computed greedy boundary, including -1
  when invalid, before the boundary failure guard.
- `CAFE4_PROPOSAL`: every actual MTP draft token, before draft rewind and verify.
- `CAFE4_VERIFY_TOKEN`: index, proposed token and actual target prediction at
  each existing acceptance query, including the first mismatch or invalid -1.

The records add no sampling or logits calls and do not substitute a proposal,
force a prefix match, retry, or extend acceptance past its first mismatch.
There are at most 63 proposal tokens and 63 verification records per trial.
Strict positive partial acceptance, half-width cap, fixed **0.743863867** gate
(lower is better), matched controls, 10x fault tests, and UNKNOWN/rc2 remain.
These witnesses identify the first token-stage disagreement in a future run;
they do not prove which component caused R5 or fix a demonstrated kernel bug.

**9/9 model-free tests PASS**, including a compiled spy executing the actual
generated boundary/proposal/verification block in 21 mode/scenario combinations:
complete agreement, first mismatch, later mismatch, invalid logits, invalid
boundary, too-short proposal and width63. Assertions verify the exact token-query
sequence, early exits, accepted/correction tokens and complete witness output.
The entire generated candidate also passes C++17 syntax checking against the
existing detached v10 diagnostic tree. No native inference ran.

Generated scratch source:
`/mnt/raid0/llm/tmp/df2/cafe4-token-witness-20261119/candidate.cpp`, SHA-256
`f11d4e31bbdebf1533d42136d900076124acd8a3b59ec572c7ad3ed5bb28fbdc`.
Base source blob remains `53035f75429327e82454f7d26f7dd67f65c80c16`.
Generator SHA-256 `d9b4c5f349c9b5cb157046d9e9e45d3d7fc22c56d1f9550c4322bb3035dbc3f3`;
header SHA-256 `e4c7b544a72f21014d9d3999be4d8072f03c1aa779c936416b870e6978d33e70`.

Existing R5 and earlier build inputs/binaries are unchanged and contain none
of these three markers. Next publish a fresh HIP build row binding this candidate
and header, requiring all three compiled witness markers, then qualify a fresh
native diagnostic. Existing CAFE-4 source registration and VB-SERVING-DF2 wiring
task apply; do not invent historical measurement warrants from the new logs.
Parent CAFE-4 stays open.
[no-belief: diagnostic source repair and model-free tests only]

Rollback intervention boundary (2026-11-19)
------------------------------------------

R6 retained boundary token271 in all modes, but mode1 proposed `32,16106`
while modes0/2 proposed `248068,271`. The original UNKNOWN stands. Inspection
of the bound experimental source finds context-local mode atomics and counters,
independent draft/speculative instances, and synchronized NextN embedding reads.
The snapshot hook changes its selected index only for mode2 and a nonzero
rollback index. These findings do **not** establish why the pre-rollback MTP
proposals differed, nor prove that mode1 caused the difference.

The harness previously enabled the requested intervention before prefill.
The generator now explicitly configures mode0 before prefill and keeps it through
proposal and target verification. After strict partial acceptance and
`common_speculative_accept`, it configures the requested mode immediately before
the target suffix removal. A failed transition reports `rollback-configure` and
returns UNKNOWN before either suffix is removed. Trials still generate independent
proposals; no proposal is substituted or forced equal. All matched lifecycle,
prefix and draft controls, the fixed **0.743863867** tolerance (lower error is
better), explicit fault rc1 control and 10x sensitivity tests remain unchanged.
This repairs the intervention boundary; it does not certify native determinism.

**10/10 model-free tests PASS**. The new compiled spy executes the generated
prefill and rollback blocks in nine mode/failure combinations, checking the exact
order of configuration, prefill, acceptance, both suffix removals and replay.
It checks that both configuration failures stop before later operations. Existing
21 token-witness scenarios continue to pass. Full generated C++17 syntax checking
passes against the existing detached v10 diagnostic tree; no native inference or
full build ran. Generated source SHA-256:
`af8bdd0e8261e200701ae9ad8fe5ed7a00070b0a0ab46d1a18d30737173bd1d4`,
at `/mnt/raid0/llm/tmp/df2/cafe4-mode-isolation-20261119/candidate.cpp`.
Historical source blob remains `53035f75429327e82454f7d26f7dd67f65c80c16`;
code and tests are `scripts/diagnostics/cafe4_port.py` and
`scripts/diagnostics/test_cafe4_modes.py` in this commit.

Next qualify a freshly hash-bound HIP build before any native row. If independently
produced proposals still differ with every pre-rollback mode fixed to zero,
treat that as pre-intervention variation and localize hidden-state/draft-logit
inputs; do not relax matched controls or claim a snapshot-mode cause. Existing
CAFE-4 source registration and VB-SERVING-DF2 wiring task apply.
[no-belief: harness isolation correction and model-free tests only]
