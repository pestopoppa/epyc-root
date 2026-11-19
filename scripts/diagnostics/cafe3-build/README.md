CAFE-3 full CPU candidate build (2026-11-19)
==========================================

Row `df2-cafe3-full-cpu-build-20261119` qualifies the full v10-based adaptive
candidate, not a stand-alone controller. The detached worktree is
`/mnt/raid0/llm/tmp/df2/cafe3-full-source-20261119`, based on production commit
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`. `inputs.json` pins the full tracked
diff, every generated header/source, manifest, driver, launcher and existing
STOP/deadline supervisor. Unexpected untracked source is refused.

The preparer now resolves `refs/heads/production-consolidated-v10^{commit}`:
the bare name also identifies an annotated tag on this host and previously
compared its tag-object id with the source commit. The explicit branch passed
preparation without changing the frozen production tree.

Publisher `--smoke-now` passed on cores 116–119 at 2026-11-19T17:50:19Z,
rc 75 after validated first progress. Smoke compiled the actual transformed
server-context.cpp to an object and required adaptive environment, context,
journal schema and poison markers. This is not a full build verdict.

The scheduled row builds `llama-server` with HIP and backend dynamic loading
disabled, requires the same compiled markers in the executable, and records
SHA-256 bindings of the executable, CMake cache, logs and llama/ggml libraries.
`ldd` under the row's own LD_LIBRARY_PATH must resolve every llama/ggml library
to the hash-bound build directory, including all four required core libraries.
Every subprocess runs under the pinned descendant-draining supervisor.
Stop on a validated receipt; failure, STOP or deadline ends the attempt.

Validator regression passes: missing feature markers, artifact tampering and
stale base receipts are refused. No model execution, launch-context capture,
native identity, speed or P9 qualification is claimed. Keep this candidate
source worktree until downstream rows finish; no model weights are hashed or
prepared inside the grant.

[no-belief: build-row smoke and validator controls only]

Build exit attribution repair (2026-11-19)
----------------------------------------

The original scheduled build failed qualification after linking the server;
its supervisor rc75 did not distinguish STOP, deadline, signal or surviving
descendants. That historical cause remains unknown. The revised driver uses
`cafe3-build/supervise.py` with an additional report-path argument. It records
explicit reasons, child rc and child PIDs before draining, then persists the
drain outcome. Leftover descendants still refuse successful qualification.
The inherited pidfd identity checks and verified drain are unchanged; the
new exit-boundary tests mock process execution/draining.

Replacement inputs must pin this revised supervisor and driver in a NEW
scratch packet/row. Existing published packets and inputs.json snapshots
remain historical and are not compatible with the changed supervisor CLI.
New inputs must declare `supervisor_protocol: epyc.cafe3.supervisor.v1`;
the revised input checker refuses older packets before executing a command.
No replacement row is claimed published by this source repair.

The revised full-build marker gate reads the hash-bound
`libllama-server-impl.so`, which carries server-context code in this source
layout, and requires it in local linkage. The executable, cache and linkage
log must also be hash-bound. UI building and prebuilt UI fetching are disabled
and checked in CMakeCache. Full-build synthetic receipts exercise the linked
component gate for CPU and HIP; no new full build or native P9 verdict exists.

Replacement build publication (2026-11-19)
-----------------------------------------

`spec-r2.json` publishes `df2-cafe3-full-cpu-build-r2-20261119` from
a fresh scratch packet at `/mnt/raid0/llm/tmp/df2/cafe3-cpu-build-r2-20261119`.
`inputs-r2.json` retains the existing source base/diff/generated-file bindings
and pins the relocated revised driver, launcher and supervisor with
`supervisor_protocol: epyc.cafe3.supervisor.v1`. Original packets are unchanged.
The revised full-build marker gate targets the linked server implementation;
UI build/fetch are disabled. Supervisor attribution reports are artifact-bound.
Both rows compile on CPU capacity; the HIP row builds the gfx90a backend but
performs no GPU model execution. Full build and native P9 remain outstanding.

df2-cafe3-full-cpu-build-r2-20261119: publisher smoke PASS on cores 164–167, rc75 after validated first progress; /mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-full-cpu-build-r2-20261119/PASS.json SHA-256 7069f0ed6928b7533f10daa0af9606c7aee4ead2226d0ea84fad3266ee5f30c3.

[no-belief: compiled publisher smoke only]

## Versioned SONAME identity repair (2026-11-19)

CPU and HIP validators accept numeric SONAME suffixes such as `.so.0` and
`.so.0.0.1`. Each linkage entry must resolve inside that run's `build/bin`,
remain explicitly hash-bound in the receipt, and match both its local SONAME
and unversioned component alias. The resolved file must retain the same
component name (with only numeric version suffixes). Other suffixes and
malformed linkage are refused. Backend, marker, server implementation,
HIP exports/gfx90a and source bindings remain mandatory.

Validation: **23 focused tests PASS** (10 CPU build/supervisor/full-binding,
2 HIP, 11 launch-context). The full-binding suite includes 24 CPU/HIP subcases:
major/full numeric versions pass; missing components, external targets and
symlinks, missing hashes, tampering, wrong components, mismatched aliases or
SONAMEs, suffix lookalikes and malformed lines refuse. Subprocess metadata
is mocked; files, symlinks, linkage and SHA-256 validation are real. Updated
the launch-context receipt fixture to include existing server-library/UI
requirements. This establishes validator behavior, not a native build or P9
verdict. Existing sealed packets are unchanged; replacement publication must
bind the repaired driver hashes.

- `scripts/diagnostics/cafe3-build/driver.py` SHA-256 `4205a4af38aee964aa20ca217cf4897095144922d5c5b1bb319d1f5f33dc89b0`
- `scripts/diagnostics/cafe3-hip-build/driver.py` SHA-256 `6d209ff939a063c2a0746040e9e84d43da37987be5b83617f5f514645b6d2b7e`
- `scripts/diagnostics/cafe3-build/test_full_binding.py` SHA-256 `5db77f5146c06f4c7b3ccfb530a35ce000736d32f9681aa9504fd23d4488e004`
- `scripts/diagnostics/cafe3-adaptive/test_launch_context.py` SHA-256 `b9d8e067292bc3ec07dc05d8794da67756c17b74554551bf08f3c7528ce852fb`
