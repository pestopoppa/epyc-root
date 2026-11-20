# BFCL native capture: local CPU process custody

`proposed/cj567/bfcl_capture_run.py` now requires a `LocalNativeTransport` for
live multi-turn capture. `software_control=True` is an explicit opt-out for
model-free scripted controls and is labeled as such in the identity journal.
This change supplies process-custody checks, not a fleet score or proof of sample
representativeness. The original official checker and scoring rules are unchanged.

Before publishing a row, call `bfcl_prepare_model.prepare_model(path)` once for
its single GGUF file. Preserve the returned absolute path, SHA-256 and device,
inode, size, mtime and ctime. Preparation refuses files that change while being
hashed. The runtime transport does not import that preparer or hash model weights.
Do not place the preparer in the granted launcher's execution path.

The launcher must supply two independently verified manifests and their SHA-256s
in the capture identity:

- Build: `server_binary_sha256` and `libraries`, a list of `{path, sha256}` records
  for every mapped ggml library, including dynamically loaded backends.
- Runtime: `model`, `model_file` (the offline preparation record), and `argv`
  (the complete, exact server command line).

Launch a dedicated server with explicit `--model <prepared path>`,
`--alias <request model>`, `--host 127.0.0.1`, `--port <port>` and
`--n-gpu-layers 0`. Construct `LocalNativeTransport` using the PID captured by
that launcher, port, identity, and manifest paths, then pass it to `capture_case`.
The approved server/library digest must come from a content-bound build record;
a source path, build directory, version label or mtime does not establish it.

The transport verifies the executable through `/proc/<pid>/exe`, hashes the
small executable/libraries once at launch, and binds their inode metadata. Each
sample checks the process start ticks, exact command line, unchanged prepared
model and artifact metadata, required inode mappings, and ownership of the one
IPv4 loopback listening socket through `/proc/<pid>/net/tcp` plus its open FDs.
Mapped ggml libraries missing from the build manifest refuse capture.
HTTP requests bypass proxies and refuse redirects. Samples run before and after
each request. The durable journal writes a proof before exposure and another
after recording the raw response, before parsing or scoring. Proof failure aborts
without a verdict or retry. Existing journals remain exclusive and cannot resume.

The trust boundary is the local kernel and a trusted launcher with immutable
prepared files. Process mappings demonstrate that the bound process maps the
specified file; they do not prove GPU residency, resident RAM pages, an honest
implementation of model execution, or immunity to a privileged adversary. This
instrument currently requires one mmap model file and an explicit CPU launch;
split GGUF, no-mmap and GPU runs require additional supported proofs. The
loopback-only endpoint must belong to the launcher's own process; this code does
not inspect, restart or terminate shared production servers.

Controls use a small HTTP subprocess with a mapped fixture file, not model
weights, plus the existing original-V3 replay suite. They cover socket/PID
mismatch, content and manifest tampering, same-size mutation and inode replacement,
unmapped model/library, redirects, PID generation changes, unbound live callables,
and proof failure after the raw response preventing scoring. They establish
software behavior only. Publish actual fleet capture through rowflow next.

`proposed/cj567/bfcl_fleet_run.py` provides the dedicated row worker. Its scratch
configuration binds the approved build, prepared model, fixed selection, original
checker checkout and released catalog. The shell launcher verifies its small input
manifest before entering the row engine. The worker sets the server's own
`LD_LIBRARY_PATH`, requires the full-run grant bytes to remain unchanged, and
keeps one exclusive journal per selected multi-turn case. A partial or UNKNOWN
case stops the run; existing output refuses continuation. It terminates and reaps
only the server child it launched, escalating to SIGKILL if needed.

The CPU smoke uses a synthetic addition-tool request with 24 output tokens,
records native response and before/after residency proofs, and writes journals under
`bfcl-native/` beside rowflow's unique attempt result. It also writes its one completed-request record
to rowflow's exact `FILLER_DRYRUN_RESULT_PATH`; full runs write `run/RESULT.json`. It does not initialize the official checker or
parse the cohort. Its transport success is an engineering qualification; even a
truncated or non-tool response establishes no BFCL accuracy. Full capture covers
the ten pinned multi-turn cases. The terminal records known, unknown, passed and
completed counts; `score` stays null because this coverage selection does not
establish a representative score. SQL remains excluded by the upstream evaluator.

Run the five model-free launcher controls with
`PYTHONPATH=proposed/cj567 python3 -B -m unittest test_bfcl_fleet_run -q`.
They cover UNKNOWN/coverage semantics, malformed selections, owned-child cleanup
and escalation, and smoke isolation from the cohort, official scorer and prior smoke attempts. Actual
model inference is qualified exclusively through `publish_row.py`.
