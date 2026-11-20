# BFCL native capture: local CPU process custody

`proposed/cj567/bfcl_capture_run.py` now requires a `LocalNativeTransport` for
live single- and multi-turn capture. `software_control=True` is an explicit opt-out for
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

Prospective request budgeting (2026-11-20): the original multi-turn row
`codex-bfcl-cj3d-27b-v1-20261120` aborted on a 300-second HTTP timeout during
its first case. Its final server-log sample still showed 312 decoded tokens at
about 1.08 tokens/second. This supports a budget mismatch, not a quality verdict
or a guarantee that the response would eventually complete. The aborted attempt
remains closed; existing published workers and cohorts are unchanged.

Future workers use `CaptureBudget` in `bfcl_fleet_run.py`: for 4,096 tokens,
120 seconds for prefill plus a planning floor of 0.5 tokens/second gives
8,312 seconds. The floor is an engineering assumption, not a measured throughput
bound. Smoke retains its 24-token/300-second limit. Both modes require the entire
request budget plus 30 seconds for cleanup to fit strictly before the worker's
deadline, which already precedes the grant deadline by 20 seconds. The same
budget governs admission before every exposure and the HTTP socket timeout.
`LocalNativeTransport.request_guard` rechecks the request token bound, STOP,
signal/grant state and remaining window after residency sampling and request
serialization, immediately before HTTP. A late refusal after journaling exposure
aborts that attempt; it never redraws. An already in-flight request retains its
socket timeout and the external grant's enforcement; this change does not add
mid-request STOP cancellation.

The fixed budget is recorded in the attempt and per-case capture identity.
Insufficient time before exposure leaves the remaining cases unexposed; transport
failure remains an aborted capture without a quality score or retry. Offline
controls exercise strict deadline boundaries, a simulated slow response through
the actual transport call path, STOP/grant loss, late admission refusal, timeout
propagation without retry, and worker/identity integration. No cohort generation
is needed for these controls. A fresh exposure requires a separately declared
protocol; changing this source does not authorize repeating the aborted cohort.

Single-turn capture uses the same `capture_case` entry point for the fourteen
pinned Python, Java and JavaScript cases. Their function schemas are embedded in
the pinned case, so no multi-turn catalog is loaded. The lock binds the original
corpus/gold hashes and selected content digests; the journal records the schema
and lock hashes and labels the instrument `native-single-turn`. Official request
construction supplies the language conversion and exact reverse name mapping.
One request is journaled and sent, its raw response and residency proof are saved,
then `OfficialV3.score` calls the original checker. Stop before exposure returns
UNKNOWN; disk, transport or residency failure aborts without scoring or retry.
Malformed responses remain UNKNOWN under the existing adapter. SQL is excluded.
The existing row worker still selects multi-turn cases; publishing single-turn
fleet capture is the next step. These scripted controls provide no model score.
