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

Every run retains the off/observe/fault matched-prefix controls and the
original numerical thresholds. Default success is rc0. `--fault-injection`
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
The V4 source's original absolute numerical-floor rule is preserved; the later
single-prompt relative-floor diagnostic is separate evidence. The parent
CAFE-4 task remains open until the port's scheduled native controls land.
