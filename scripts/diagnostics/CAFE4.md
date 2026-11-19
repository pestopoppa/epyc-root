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
