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
