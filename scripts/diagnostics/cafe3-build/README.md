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
