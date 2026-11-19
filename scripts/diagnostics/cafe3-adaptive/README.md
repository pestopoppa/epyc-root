CAFE-3 adaptive chain-width policy candidate
==========================================

`controller.h` implements the model-free native policy for CAFE-3. It is a
source-only diagnostic component, not connected to any server or kernel.
Production remains frozen at `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`.
No experimental full candidate, native model run, token-identity comparison,
throughput claim or P9 verdict is established here.

The filed CAFE-2 handoff verdict requires a cost model (T(5)/T(1)=1.79).
The policy maximizes predicted committed tokens per measured round microsecond;
higher score is better. Round cost must include draft, verification and
acceptance/rollback, including the target-only baseline. It maintains an EMA
for each width and prefix-acceptance position. Undrafted positions are censored.
Current position-zero draft probability sets the first-prefix probability;
EMA ratios estimate subsequent conditional acceptance. This probability model
is an uncalibrated candidate, not an asserted native prediction quality.

Every eligible width, including zero, must be measured before cost can veto it.
The zero winner still probes positive widths with exponential delay capped by
`max_gap` (default 64 rounds). Stale-width exploration additionally refreshes
all eligible widths, oldest first. With a fixed cap, a width is retried within
`max_gap + max_width + 1` completed rounds; a cap of zero cannot legally probe
positive drafts. Re-enabling a cap allows unseen widths immediately. Request
cancellation does not count as a completed round or a timing observation.

Controller defaults off. Only exact `"1"` passes `enabled(value)`; a future
adapter must read `LLAMA_CAFE3_ADAPTIVE` at request initialization and pass the
result to the constructor. Off and `implementation::other` preserve the static
width subject to the caller's context cap. Adaptive scope is MTP, DFlash and
DFlash2 chains only; it excludes ngrams, trees and other implementations.
No process environment or production flags are changed by this component.

Native integration contract
---------------------------

- Start an experimental candidate from the then-current frozen production tip,
  preserving the full candidate. Add this component as one feature commit.
- Own one controller per request/sequence and active model-draft implementation.
  Reset between requests; do not mix timings from overlapping sequences.
- Select once with the real legal draft cap and position-zero confidence.
  Preserve token identities/sampler behavior; the controller only chooses width.
- A successful round supplies actual accepted draft count and total round time.
  Width zero bypasses drafting but still supplies a target-only timing sample.
  Failed decodes, truncated proposals and cancellations call `cancel`; never
  label shortened proposals with their originally requested width.
- Tickets reject duplicate or mismatched feedback. Do not call `observe` for
  off/excluded selections. Caller lifecycle must not leave an outstanding choice.
- Connect the native observation producer at write time, including confidence,
  chosen/actual width, acceptance, timing, sequence and selection ticket; register
  that producer when implemented. Unit tests here are not native observations.
- Build and qualify the full candidate through published rows, prove runtime
  content/linkage/residency, then run P9 against the best static width: at least
  +1.0% improvement, 100% token identity and absorbing-state test. Freeze timing
  corpus, repetitions and decision rule before measurements. Smoke proves only
  its declared qualification predicate, not P9.

Validation (2026-11-19)
-----------------------

Run `bash scripts/diagnostics/cafe3-adaptive/run_tests.sh`. C++17 strict warnings,
AddressSanitizer and UndefinedBehaviorSanitizer PASS. Assertions cover default
and explicit opt-in, excluded implementations, all three allowed model impls,
probe-before-veto, timing/acceptance EMAs and censoring, confidence-sensitive
selection, increasing bounded zero retry delays, escape from adversarial zero
lock after a regime change, context caps, cancellation and invalid/duplicate
feedback. Synthetic inputs test policy semantics only.

Source SHA-256 bindings:

- `controller.h`: `dad3f49a1950770b8e5740cc50ce649f39d33452936ee49434cfbfaac4858bdf`
- `test_controller.cpp`: `30c22b16d307d6482efc6d3ed3192e72b4c37f3a884bab24de70157a0d00beb8`
- `run_tests.sh`: `6319b81d94b8f8a12cc134923c413b6ef35986af92fcf85b6e620fd3a14a0abd`

[no-belief: source-only controller and model-free tests; no native claim]

Request/round lifecycle layer (2026-11-19)
-----------------------------------------

`round_lifecycle.h` supplies the caller-facing lifecycle, with separate policies
per sequence and implementation, request reset, recycled-id epochs, strict
request-time opt-in, and explicit completion/cancellation hooks. Its synchronous
writer callback receives request/epoch, sequence, implementation, ticket,
completed round, chosen/actual width, accepted count, current position-zero
probability, probe status and elapsed microseconds **before** policy mutation.
The writer must durably persist a record or throw. Writer failure cancels the
sample and propagates; the caller must treat it as a failed round observation.
This is a typed callback contract, not an implemented native record producer.
No native observations were generated; the tests use synthetic inputs only.

Native hook locations traced against `epyc-llama` git commit
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`:

- `tools/server/server-context.cpp`: request assignment/release must call
  `begin`/`release`; generation around `get_n_draft_max()` must select before
  drafting. Width zero must still enter a timed target-only completion path.
- The ordinary `common_speculative_accept()` call precedes final target/draft
  KV removal. Call `finish` after both KV removals; do not time only the common
  acceptance hook. The full-checkpoint partial-draft replay return must cancel
  rather than relabel the original selected width. Decode failures, context
  shifts and cancellations must also cancel.
- `common/speculative.cpp`: current per-position proposal distributions are
  produced during drafting, after the server chooses its cap. A current-round
  confidence hook must be designed at the model-draft boundary before native
  selection; substituting previous-round confidence would change the policy.
  Zero-width selection must not quietly add an unaccounted draft forward pass.

The lifecycle layer is not yet called by an experimental server. No fresh
production-based candidate build, native environment hook, durable native sink,
model test or P9 result is claimed. The next implementation must resolve that
confidence/selection ordering and wire both target-only and speculative paths.
At that point register the native producer in the belief source table/program;
this source-only callback has no native measurements to project.

Both C++17 suites pass strict warnings plus ASan/UBSan. Lifecycle tests cover
interleaved sequences, independent model policies, zero-width observations,
shortening/cancellation, duplicate completion, invalid counts, failing writers,
nonfinite/nonpositive clocks, request reset, recycled ids and excluded/off paths.
SHA-256: `round_lifecycle.h`
`1e57fefa5ccb4fc6169edfcf413536f1c0e31876e36fa3c70b2d2e9bc247fbc9`;
`test_round_lifecycle.cpp`
`88d70f7292815e4c7910d140cfc35fffcdd9ac9817a829e7209104df78ed068e`.

Current-confidence native source port (2026-11-19)
------------------------------------------------

`native_port.py` now provides pure `header(source)` and
`implementation(source)` transformations against the full frozen-production
commit above. A future row builder imports these functions and applies them
to `common/speculative.h` and `.cpp` in its fresh experimental worktree, adding
this directory to the include path. Production is never edited. This is a
compiled source port, still without a server caller or executable candidate.

The optional per-round `cafe3_select(type, legal_cap, confidence)` callback runs
inside the MTP first decode or DFlash first output distribution, before first
token acceptance. Each round requires fresh draft params (`cafe3_selected`
starts false). It bounds the selected width by both implementation and request
caps, rejects invalid selections, and prevents chain fallback when a selected
model produces zero tokens. Shortened proposals still require lifecycle cancel.
Only these model implementations invoke the callback; DSpark and other
implementations retain their paths.

For MTP and generic DFlash, confidence is the first greedy candidate's mass
from the existing sampler. For DFlash2 it is the **maximum softmax mass** in
the first selector row: use sampling temperature when positive and T=1 for
greedy. This is a current-position confidence statistic, not the mass of a
possibly different stochastic draw and not a calibrated acceptance estimate.
It queries no RNG and changes no selector state at width zero. Positive widths
keep the original RNG/sampler operations and first proposed token. DFlash still
decodes its full original noise block before choosing how many outputs to
verify; this port claims no reduction of that block's drafting cost.

Call `round_lifecycle::prepare(sequence, impl)` **before** that confidence decode,
then `select` from the model callback. `prepare` retains the earlier timestamp
through selection, so even zero width includes confidence-acquisition cost.
Cancel on confidence-decode failure or context/replay interruption. Off/excluded
prepare does not read the clock. The original direct `select` timing remains
available for callers whose confidence is already available without extra work.
The future server adapter must use `prepare`, complete target-only rounds, and
finish after target AND draft KV rollback; none of those server hooks exists yet.

`run_tests.sh` runs all three sanitizer suites plus the native-port tests. The
ported full `speculative.cpp` passes a C++17 syntax check with production headers.
The actual ported MTP/DFlash/DFlash2 draft methods and common dispatcher execute
under ASan/UBSan with deterministic decoder/sampler spies: widths 0..3, independent
sequences, first-decode confidence ordering, failed decodes, zero fallback, no
zero RNG consumption, disabled behavior, and unchanged seeded stochastic output
at static width. Lifecycle assertions prove that a 50-us confidence phase plus
a 10-us target-only phase records 60 us. These are model-free code tests, not
native model runs or P9 evidence.

Current SHA-256 bindings (supersede the historical lifecycle/runner hashes):

- `model_boundary.h`: `355d0356e488a5e095ebf115c1f826cfdf99f7346675c730b8b562573b115333`
- `native_port.py`: `edcc7e7f3f0b7f77ea0b5bb2bea0cca7842fff21ef937feae841e22ffdd1ec38`
- `round_lifecycle.h`: `4567ff02cd87c0e0b621b5337570936b857edac62528b632fed04c34f7529b1e`
- `run_tests.sh`: `bb3849a5490557a8d58d498c7dee93bd6eabda122e536da7c5d1937ef3b4e02b`

Next: connect this port to request/sequence lifecycle in a fresh full experimental
server, add the durable write-time sink, and register that producer before any
native execution. No native observation producer exists in this source port.


Server completion/cancellation source port (2026-11-19)
-------------------------------------------------------

`server_port.server_context(source)` transforms the pinned v10
`tools/server/server-context.cpp`, failing closed if any expected anchor drifts.
A slot may hold an assigned `round_lifecycle` through `cafe3_rounds`. Request
setup must call `begin` before attaching it. Empty pointers preserve legacy
behavior. The port calls `finish(0,0)` after target-only sampler acceptance,
and `finish(n_draft, ids.size()-1)` after both final target/draft KV removals.
Shortened proposals cancel through the existing lifecycle guard. Checkpoint
replay and context shifts cancel explicitly. Shared-batch decode failure/retry
and speculative batch-processing failure cancel pending slot samples. Release
cancels, erases the sequence and detaches the pointer before slot reset; repeated
release remains harmless. Writer failure propagates and prevents policy training.

**2/2 targeted tests PASS**, including a strict-warning C++17 ASan/UBSan executable
using the actual transformed slot methods and actual lifecycle: target-only
confidence-plus-target timing 50+10=60 us, width-one completion, duplicate finish,
shortened proposals, cancellation, release/reused ids, off/unattached paths and
writer failure. Tests also assert completion/cancellation placement in the full
transformed native source and reject anchor drift. Full generated server
translation-unit C++17 syntax checking PASS against the v10 headers. Generated
scratch file: `/mnt/raid0/llm/tmp/df2/cafe3-server-completion-20261119/server-context.cpp`.
Production source commit: `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`.

This completes the source-level feedback seam only. Request assignment does
not yet construct or attach a lifecycle, and server draft setup does not yet
install prepare/select callbacks. No durable native sink exists; no native
observations were produced and no full executable, identity, speed or P9 verdict
is claimed. Next implement request-scoped attachment and confidence preparation/
selection, then the durable sink and its source registration before native
execution. Full experimental builds and P9 must go through published rows.

SHA-256 bindings:
- `server_port.py`: `a32a9938ad21adae476e306df3b4260294ad5fb390e7da739ec70c83fd0393de`
- `test_server_port.py`: `e38bfa403244d620a819c8fa20b92006242fdca8e92420866960d315ef442f41`
- `run_tests.sh`: `8b991d866a77367c0c43a6e635810955c4f91f801b1ec0adbdefededcf3d7d21`

[no-belief: compiled server source port and model-free tests only]


Request attachment and model preparation source port (2026-11-19)
---------------------------------------------------------------

The v10 source port now attaches a request lifecycle immediately after task
assignment, sampling `LLAMA_CAFE3_ADAPTIVE` once. Off requests stay unattached.
`server_slot::cafe3_factory` must return a lifecycle with its writer installed;
enabling without a factory, or with a null result, throws. A candidate builder
must install that factory before accepting adaptive requests. This change does
not supply a durable sink or claim an executable adaptive server.

Fresh server draft parameters receive prepare/select callbacks. The actual
MTP and DFlash methods invoke preparation before their draft work, including
confidence decoding. Inactive sequences and DSpark are excluded. Preparation
cancels an unselected prior implementation's pending timing; the matching
confidence selection retains the original start time. DFlash2 shares DFlash's
native enum but passes its selector variant explicitly, preserving separate
policy state. A selection without matching preparation throws. Existing native
completion, replay cancellation and request release hooks remain in use.

Validation: both controller/lifecycle C++17 ASan/UBSan suites pass; **2 native
boundary tests and 3 server port tests pass**, including full transformed
`speculative.cpp` and `server-context.cpp` translation-unit syntax checks.
Native method spies prove exactly one preparation before any decode for all
three model variants at widths 0..3 and none for inactive sequences. Executed
slot methods cover default-off attachment, missing-factory refusal, callback
binding, a 50+10=60 us synthetic zero round and distinct DFlash2 records.
These are model-free software controls against production git
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`; no native measurement, identity,
speed or P9 verdict. Next: implement the durable native sink, register its
write-time source and wiring task, install the factory in the full fresh
production-based experimental builder, then publish build/P9 rows.

[no-belief: compiled request/model source port and synthetic controls only]

Durable journal and factory-installed source candidate (2026-11-19)
------------------------------------------------------------------

`native_sink.h` now implements `epyc.cafe3.round.v1` as an exclusive per-server
JSONL journal, mode 0600. It syncs the parent directory at creation and uses
complete-write/EINTR handling plus `fdatasync` for every round before lifecycle
feedback may train the policy. Write, validation or sync failure permanently
poisons that journal; an unsynced or partial final line must not be treated as
an acknowledged observation. Successful records include a global ordinal and
wall timestamp, run/context identity, request/epoch/sequence/implementation,
round/ticket, selected/actual width, acceptance, current confidence, probe and
full elapsed microseconds. The writer executes after the timed round; its
synchronous IO overhead must remain included in future end-to-end P9 throughput.

`prepare_candidate.py <detached-worktree>` checks a clean pinned production
base and refuses paths outside `/mnt/raid0/llm/tmp/df2`. Create that worktree
from the current fetched production ref using `git worktree add --detach`;
the preparer refuses any changed production base until the port is reviewed.
It applies both native and server ports, places the required project headers
in `common/`, installs the native lifecycle factory on every server slot, and
writes `cafe3-source.json` binding every generated source/header hash to the
full production base commit. All transformation anchors are checked before
writes. This command prepares source only; a scheduled full-build row remains
required before executable qualification or native execution.

Off requests stay unattached and do not open a journal. At the first enabled
request, the factory requires `LLAMA_CAFE3_JOURNAL` (new path),
`LLAMA_CAFE3_RUN` (unique server-run identity) and
`LLAMA_CAFE3_CONTEXT_SHA256` (64 lowercase hex digits). The digest must name a
retained predeclared context manifest binding actual source/build/library/model,
protocol/corpus/repetitions/decision/stop rules and grant/placement identities.
The sink validates syntax; the future row launcher must hash and verify that
manifest and its actual launch bindings before starting native capture. No
native launch is claimed here. The validator below implements the manifest
precondition; a scheduled native launcher must still call it and use its exact
returned argv/environment. Reusing a journal path fails closed.

The source is registered prospectively in `scripts/vidya/adapters/README.md`
with task `VB-CAFE3-ROUND-WIRE`. Projection uses the existing measurement carrier
and shared `ClaimTuple.grade()`; a native planning-context canary is still
required before calling the source wired.

Validation: controller/lifecycle strict-warning C++17 ASan/UBSan suites pass;
2 native-port tests, 3 server-port tests and 2 journal/preparer tests pass.
The server syntax check now compiles the factory-installed full translation
unit, including the real sink. Journal tests parse actual persisted JSON,
check escaped run identity, ordinal, mode, confidence/elapsed fields and real
factory feedback; force EINTR and short writes, a 14-byte partial-write failure
and a sync failure; prove permanent poison and canceled/untrained feedback;
refuse missing metadata, duplicate paths, invalid digests and production-tree
preparation. These controls use synthetic rounds only. No full candidate build,
native model observation, token identity, speed or P9 verdict is established.

[no-belief: source implementation and model-free compiled/IO controls only]

Source SHA-256 bindings for this milestone:

- `native_sink.h`: `6ae785888b42922d92f4e4306289ac1528471e1d303612e66db8360652157b41`
- `prepare_candidate.py`: `ca51e3fe2f6fa1ea36c2734f5dc82bdea5c90bc64f3b5123c6702abf433623ef`
- `test_native_sink.py`: `cca4ee08b251e7a58e0f7cb4309bb0f7e100bc84e4f9fb433180944f967b8a25`

### Native launch-context validator (2026-11-19)

`launch_context.validate_launch_context(manifest_path, expected_sha256, argv)`
checks the retained manifest before capture and returns an exact child argv and
isolated environment. Its CLI takes the manifest, its externally pinned SHA-256
and a file containing the actual intended argv JSON array; it prints the plan
and starts no process. `native_runner.py` executes the returned plan unchanged,
supervises STOP/deadline and grant termination, and retains up to two in-process
raw mapping samples. Verified library coverage and in-window HIP residency still
require separate checks. Preserve these modules and both sibling
build-driver directories in the runner's pinned input layout.

The `epyc.cafe3.launch-context.v1` manifest has these required fields:

| Fields | Binding |
| --- | --- |
| `run`, `row`, `journal`, `backend`, `arm` | Unique retained server-run label, official row, unused absolute journal path, `cpu` or `hip`, and declared `adaptive` or `static-N` arm |
| `argv` | Exact command array; canonical `-m`, `--model-draft`, `-t`, `-tb`, `-ngl`, `--gpu-layers-draft` each once; no competing aliases or remote model loaders |
| `build` | `{path, sha256}` of a full matching-backend receipt; producer validation checks pinned production/source, compiled markers, cache and local libraries, plus HIP exports/gfx90a; executable/cache/linkage must themselves be hash-bound |
| `prepared` | `{path, sha256}` of an `epyc.cafe3.prepared.v1` record prepared **before** the grant; `models` has exactly `target` and `draft`, plus a `corpus` record |
| `corpus` | Exact prepared corpus record, also repeated in the protocol |
| `protocol` | `{path, sha256}` of `epyc.cafe3.protocol.v1`: `corpus`, nonempty `question`, `decision_rule`, `checkpoints`, `stop_on_answer`, `stop_on_futility`, positive integer `repetitions`, unique named `arms` including `adaptive` |
| `grant` | `{path, sha256}` of the official `grants/<row>.grant`; seal this final launch manifest after assignment and before any native observations |
| `placement` | Exact `regions`, `holds`, CPU-list `cpus`, positive integer `threads`; match grant, filler environment and current process affinity |
| `device_env` | CPU: `{}`; HIP: `HIP_VISIBLE_DEVICES` and `ROCR_VISIBLE_DEVICES` both `"0"`, matching actual runner environment and `gpu-quiet` grant token |

Each prepared model/corpus record contains canonical absolute `path`, precomputed
`sha256`, and `identity` with `device`, `inode`, `size`, `mtime_ns`, `ctime_ns`.
Use `file_identity(path)` around the **outside-grant** hashing step and refuse
preparation if the identity changes. Launch validation compares this sealed
identity without reading model weights. It detects replacement and ordinary
in-place modification; it is not protection against a privileged actor restoring
filesystem metadata. Keep inputs stable between validation and child execution.
Protocol and prepared JSON bytes are checked and parsed from the same snapshot;
duplicate keys and nonfinite constants are refused. A protocol digest binds its
declared rules; this validator does not decide their statistical sufficiency.

Future execution must retain the manifest bytes and expected digest independently
of the journal. The isolated child environment sets the candidate's own
`LD_LIBRARY_PATH`, threads, `GGML_IQK=1`, adaptive/run/journal/context identities
and GPU visibility, without inherited loader overrides. Grant expiry, STOP,
ended/completed grants, dry-run capture, CPU/thread/GPU mismatches and existing
journals fail closed. CPU grants with explicit region lists may omit redundant
`cpus=` as the production allocator does.

Validation: **10 tests PASS** via
`python3 -m unittest discover -s scripts/diagnostics/cafe3-adaptive -p test_launch_context.py -v`.
Tests exercise the real CPU build validator against model-free artifacts (mocking
source inventory and `strings` output only), stale/smoke receipts, unbound and
tampered artifacts, modified manifests/models/corpus/protocols, CLI overrides,
row/deadline/STOP/affinity/GPU placement, duplicate grant fields, ended/copied
grants, journal exclusivity and absence of weight hashing. HIP placement tests
use a mocked build validator; they establish no native HIP execution.

This is a tested launch-precondition implementation. Full builds, native
captures, token identity and P9 performance remain open.
[no-belief: source implementation and model-free launch refusal controls only]

### Grant-only native process boundary (2026-11-19)

`native_runner.py MANIFEST SHA256 ARGV_JSON LOG RESULT` validates the context
before spawning the server with exactly the returned argv and isolated env.
It refuses dry-run capture through the validator, creates exclusive outputs,
rechecks STOP/deadline and ended/completed grants after validation, and supervises
the captured child until exit or cutoff. Cleanup escalates TERM to KILL and waits
for that child, including on capture exceptions. It never signals a process by
name or prepares/hashes model weights. This CLI is for a scheduled grant only;
it has not been published as a row and must not be invoked manually for inference.

The `epyc.cafe3.process-capture.v1` receipt records exact argv/env, context digest,
PID, start/end, exit code, cutoff, reaping and available raw mapping samples.
Status is always `UNASSESSED`, including a zero exit. The CLI returns 75 on cutoff,
0 on clean exit and 1 otherwise. Missing mapping samples do not establish absent
residency. An exception leaves an incomplete result that cannot pass a grader.

**9 model-free process-boundary tests PASS**, alongside **10 launch-context
tests PASS**. The process tests mock Popen and exercise exact plan use,
pre-spawn refusal, late STOP/deadline, exclusive outputs, in-run STOP/deadline,
TERM/KILL escalation and exception cleanup. No native binary or model is run.
Run `python3 -m unittest discover -s scripts/diagnostics/cafe3-adaptive -p test_native_runner.py -v`.

The request driver below supplies declared single-arm execution. Real input
sealing, qualified full-build receipts, mapping/HIP residency verification,
multi-arm scheduling and a P9 grader remain necessary before native publication.
[no-belief: source implementation and mocked process-boundary controls only]

### Sealed multi-arm execution (2026-11-19)

`multi_arm.py SCHEDULE SHA256 RESULT` executes the bound protocol's ordered
whole-arm schedule inside one grant, using `native_runner.run` for each arm.
It is a capture driver, not a P9 grader. Schedule JSON has exactly `schema`
(`epyc.cafe3.schedule.v1`), `protocol` (`{path, sha256}`), and `launches`.
Each launch has exactly `context` (`{path, sha256}`), `log`, `process`, and
`requests` (absolute new output paths). Launch order must match protocol `arms`.
The protocol must contain adaptive plus every static width from zero through
the adaptive cap (1..64); this prevents omitting a possible best static arm.

All contexts and request settings are validated before any model process starts;
the supervisor revalidates each at launch. Only `arm`, `run` and `journal` may
differ between manifests. In particular models, build, backend, grant,
placement, CLI and protocol must match. Run identities and all output paths are
unique. Outputs must have canonical existing parents and must not exist,
including dangling symlinks. No weight hashes are computed by this driver.

The exclusive fsynced `epyc.cafe3.schedule-capture.v1` JSONL retains the schedule
digest, sequential ordering, per-arm context and hashes of completed captures.
Adaptive completion requires a nonempty journal. Static arms do not instantiate
the adaptive lifecycle and have no adaptive journal requirement. A failed arm
stops the schedule, records the error and preserves earlier/partial outputs;
reruns cannot overwrite them. Every record remains `UNASSESSED`.

**11 model-free schedule tests PASS**, including late preflight refusal before
any launch, incomplete protocols, unreaped children, output collisions, missing
adaptive journals and interrupted schedules. The native processes are mocked;
these tests do not establish round correctness, identity, residency or speed.
The fixed whole-arm order is explicit and does not establish immunity to time
drift. Native input sealing, qualified publication and the request/round P9
grader remain outstanding. No inference was run for this implementation.

### Bound protocol request execution (2026-11-19)

Add `--requests ABSOLUTE_JSONL_PATH` to the supervisor CLI to enable the trusted
local `protocol_requests.py` child. The supervisor validates request settings
before model load, supervises both captured PIDs, and reaps both on every exit.
The requester verifies the manifest digest again. Only an explicit
`protocol-complete` with requester rc 0 returns success; an early server exit
cannot conceal an incomplete protocol. Success means captured requests, with
all receipts still `UNASSESSED`; it supplies no P9 verdict.

The bound protocol adds `request_settings` with exactly these fields:

```json
{"n_predict": 128, "seed": 42, "timeout_s": 120,
 "arm_widths": {"adaptive": 3, "static-0": 0, "static-3": 3}}
```

`arm_widths` covers exactly the protocol's named arms, widths are integers 0..64,
and `static-N` must use N. Static launch contexts set `LLAMA_CAFE3_ADAPTIVE=0`;
adaptive contexts set it to 1. One server launch captures one declared arm;
each launch needs its own retained context and unused journal path. The corpus
is already prepared JSONL of unique nonempty string `id` and `prompt` records.
Execution reads it with before/after identity checks, without rehashing weights,
tokenizing, downloading or copying inputs. Hashing/sealing stays outside grants.

The exact argv must bind `--host 127.0.0.1 --port PORT` (1024..65535). Before
health and completion use, the client requires that the captured server PID owns
the loopback listening socket's inode. HTTP uses no proxies or redirects.
Readiness alone may retry; failed or ambiguous completion POSTs are never retried.
For every repetition and corpus record, the client sends `/completion` with
greedy sampling, the declared seed/width/length, token return and prompt cache
disabled. Complete untruncated token/timing responses are fsynced individually
as `epyc.cafe3.request-capture.v1`, preserving the full payload/response and
monotonic elapsed time with arm, prompt, repetition, protocol and context.
The parent remains responsive to STOP/deadline while the HTTP child blocks.

**32 tests PASS**: 11 launch-context, 12 supervisor and 9 request-driver tests.
Coverage includes declared static mode, exact protocol order, corrupted inputs,
invalid settings/endpoints, listener ownership, malformed responses without
retry, both-child cleanup and early-server-exit refusal. Transport and model
processes are mocked; the listener parser uses synthetic proc records. No native
inference or performance claim. Prospective captures extend the existing
`VB-CAFE3-ROUND-WIRE` adapter task and source registration; no new grading ladder.
[no-belief: source implementation and model-free request controls only]

Offline P9 assessment (2026-11-19)
---------------------------------

`p9_grade.py` assesses retained whole-arm captures without launching a process.
The sealed protocol must carry `p9_policy` equal to the module's `POLICY` before
capture. It fixes aggregate request-wall tokens/s (higher is better), all-token
identity against static-0, an inclusive +1% over the fastest static width, and
post-exploration zero-to-positive-probe recovery within 128 completed rounds.
The bound schedule must cover every static width from zero through the adaptive
cap. Integer-ratio comparison preserves the exact +1% boundary. Whole-arm
ordering and the descriptive timing limitation are retained in the assessment;
this is not a statistical significance claim or a new Belief Kernel ladder.

The grader checks schedule completion, hash-bound contexts/protocols/captures,
cross-arm inputs and placement, prepared model identities without weight hashing,
the full build through the trusted producer validator, archived official grant
windows, exact process argv/env, reaped children and successful requester,
overlapping local library mappings, and complete prompt/repetition request order.
`protocol_requests.py` now records Unix-nanosecond request start/end alongside
monotonic elapsed time. Those clocks must agree within max(1 ms, 1%); old captures
without boundaries refuse. Native rounds must have contiguous journal ordinals,
valid widths/acceptance/confidence/timing, and belong to exactly one disjoint
request window. Request ids, epochs, sequences and round/ticket progression
prevent cross-request recovery. Startup width exploration is not recovery;
missing recovery is inconclusive, and observed recovery beyond the bound fails.
A qualifying HIP result requires the per-request overlapping VRAM/KFD and
local-library evidence described below; older captures remain inconclusive. Known identity/speed/recovery failures remain failures.

The build consumer now binds the trusted producer's packet root to the retained
receipt directory, allowing replacement r2/r3 packets to use their own sealed
input inventory rather than the original packet directory. No packet code is
executed by this consumer. Existing published packets are unchanged.

Validation: **61 model-free tests PASS**: 18 grader, 11 context/build-consumer,
9 HTTP request, 12 process-supervisor and 11 multi-arm schedule tests. The grader
suite uses real sealed temporary file graphs and fake model/process/build
fixtures, with producer validation mocked there; the context suite separately
executes real producer artifact/cache/linkage validation with source inventory
and marker extraction mocked. No native inference or P9 result is established.

Run focused tests with `python3 -m unittest discover -s
scripts/diagnostics/cafe3-adaptive -p 'test_p9_grade.py'` (command on one line).
Use `python3 scripts/diagnostics/cafe3-adaptive/p9_grade.py <schedule> <sha256>
<capture.jsonl> <sha256> <new-output.json>` for an exclusive assessment output.
Malformed evidence produces no assessment. Exit 0 requires pass; valid fail or
inconclusive writes its assessment and exits 1. Prospective projection remains
under `VB-CAFE3-ROUND-WIRE`; no native planning-context canary has passed.

Source identities:

- `p9_grade.py` SHA-256 `eff6be2529472a21268dc7011e6bdd4488f92515e8ed00473632ed320a198660`.

- `test_p9_grade.py` SHA-256 `270074dcbe4aac704768a5b003889050a8700bcc8f995ed4216f83298522fe9a`.

- `protocol_requests.py` SHA-256 `ebbf8a18c9862986f0d74af4e2ef3a6d5106e3d57474bb98fc5548722834984c`.

- `launch_context.py` SHA-256 `68540c853cc9ecf73a69712f7848ad301b49d06e2b34f73eca77e39af61a7938`.


Per-request HIP residency capture (2026-11-19)
--------------------------------------------
The native supervisor now captures KFD membership, per-device VRAM bytes and
resolved mapped llama/ggml paths for its own captured server PID throughout
HIP execution, at the existing supervisor cadence (up to four samples/second).
CPU execution does not collect these observations. Every sample carries wall
time and PID; missing KFD/zero bytes stay explicit and cannot qualify residency.
Sampling uses the same loop as STOP/deadline/requester supervision and child
cleanup; it launches no new process. Sampling overhead falls inside measured
request wall time and is shared by all HIP arms. Captures remain UNASSESSED.

For every request in every arm, offline P9 assessment requires at least two
distinct sample times inside both the process and request windows, the captured
child PID, KFD membership, positive VRAM with a consistent nonnegative device
sum, and exactly the build-bound local llama/ggml library set in each sample.
A startup sample, another request's sample, exit-race absence or an observation
after exit supplies no qualifying evidence. A valid known identity, speed or
recovery failure remains FAIL even when residency is missing; an otherwise
qualifying capture without sufficient residency remains INCONCLUSIVE. Nonfinite
JSON refuses parsing. Existing numerical and P9 policy gates are unchanged.
`hip_request_residency` records the result (null for CPU) in the assessment.
Published sealed packets are unchanged and retain their old behavior; a fresh
HIP native packet must bind these revised files before collecting evidence.

Validation: **46 focused model-free tests PASS**: 21 grader, 14 supervisor and
11 multi-arm tests. New controls cover live child-specific observation, zero
VRAM, foreign PID/libraries, missing KFD/library/sample, malformed samples,
inconsistent/negative bytes, repeated timestamps, stale/other-request windows,
nonfinite JSON, valid complete HIP evidence and preservation of known failures.
Fixtures use fake processes/files and sealed temporary capture graphs; build
validation is mocked in grader fixtures. No native HIP or performance verdict.
GitNexus status/impact could not run because this lane has no repository index;
changes are confined to the diagnostic supervisor, grader and their consumers.

Source SHA-256 bindings:
- `native_runner.py`: `9232e161c79cd6766150d0f6e7b5e97b32c901822eea39b8b6fe97828641f681`
- `p9_grade.py`: `6da58c79bc11a4c1949677b675f13254f2ea98499533ce2937799e67d4e9a8d2`
- `test_native_runner.py`: `8ae77dedf103813406fc4c3d1c5baafae2f06ad8040670919a7225e7314c6ce6`
- `test_p9_grade.py`: `11978e3c6f5b7f49301b4406cda3ddd07ba058851576baed00850c876f71f340`
[no-belief: source implementation and model-free residency refusal controls only]
