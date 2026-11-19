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
such launch or manifest validation is claimed here. Reusing a journal path
fails closed. Native execution must remain blocked until that launcher exists.

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
