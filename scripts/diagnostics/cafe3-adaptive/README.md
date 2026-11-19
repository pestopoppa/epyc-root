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
