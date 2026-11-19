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
- `run_tests.sh`: `a1c86c89c11f1d225771452277252262fea1ff0f9da8e0bd407d0665c30fedd2`

[no-belief: source-only controller and model-free tests; no native claim]
