# Refactoring CI checkpoint — 2026-10-27

## Status

**The multi-repository refactor is not finished. O8 remains open.** This checkpoint records the
current CI repair and scoped preflight evidence; it does not claim a complete full-suite comparison,
native grade, accepted baseline dataset, candidate full run, or O8 completion.

## Work completed

- P3 Autopilot Actions was accepted for its private candidate and published on
  `codex/refactor-autopilot-actions-01a16fc3` at `fb5db1a0a24b92172643bb670c77a4343a508c96`.
  Its final 12-file selection passed 402 with 1 skip; the three-file formatter closure and custody
  proofs passed. The earlier 34- and 90-file run failures remain part of the record. The separate
  original integration candidate `851955112b8ba8c2911a7684469551afa1541623` passed 2,897 with 8
  skips. These are package/candidate results, not whole-refactor completion.
- Root wrap-up `fcdc09c08a807491531dc0527942244a638bd957` was merged by the owning main as
  `d369b3798` on 2026-10-26 16:44 UTC.
- O8 local CI checkpoint commit `069bb34ec5414a70abf23bac5c539c4c1d7aa7ee` is the committed base;
  uncommitted workflow, fixture, and documentation changes remain on top of it. Neither the
  checkpoint commit nor the pending delta is published or accepted. The source candidate recorded
  for the scoped checks was tree `0036ae92472f2ad144c3c6222605ab1868d4083d`; later documentation
  edits may change that tree.
- The test tripwire/autouse and route fixture isolation were prepared. An actual v4 scoped run
  produced 455 passed / 112 failed, mostly shared-limiter contamination, with zero real guard
  violations; later phases were not reached. V5 resets only route-fixture limiter buckets at client
  context entry/exit and preserves real 429 behavior.

## O8 CI evidence and limits

The first full-baseline attempt produced invalid JUnit/native evidence. The second baseline halted
at 2026-10-26 19:02:52–19:02:58 UTC after two actual BGE subprocess samples at 19:01:33 and
19:01:36. Its official exit was 143. A stray terminal status 0 is rejected. There is no complete
JUnit capture, native grade, or accepted dataset from either attempt; no partial counts are accepted.

On 2026-10-27 08:08:29–08:08:48 UTC, the V5 model-free preflight completed with 582 passed, 0
failed, 0 skipped in 9.43 s. This scoped selection includes all tests across 15 route modules plus
startup, two-client 200/429 behavior, and genuine limiter tests. Separately, five guard controls
passed in 2.45 s, with three expected denial receipts, zero real violations, matching source/ignored
custody, normal completion, and an empty owned timeout process group.

On 2026-10-27 08:12:29–08:12:50 UTC, remaining scoped checks passed: workflow/YAML/Bash/Python/argv
checks; five evidence-copy tamper controls (0.44 s); and the immutable `851955112` baseline
selection with all tests across 15 route modules plus startup (566 passed in 9.24 s). It reported
zero real guard violations, matching custody, integrity count 0, and normal completion.

These are distinct scoped selections, not a full suite. Their raw evidence is retained under:

- `/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/model-free-preflight-results-20261026-attempt3/`
- `/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/remaining-validation-results-20261027-attempt1/`

## Later results on 2026-10-27

- Native admission 28 ran 08:29:09–08:29:17 UTC and passed exactly 3 safe cases. Native capture
  was true; the shared grade was conformant `Judged/Located`; completion and custody matched, with
  zero guard violations. This confirms the corrected editable `851` v4 inventory for those three
  cases only. The prior admission 27 inventory transition from v2 to v4 is documented as limited
  and preserved, not rewritten. Raw evidence: `/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/baseline-native-admission-results-20261027-attempt3/`.
- The V6 full baseline actually started at 08:42:16 UTC on q0. The guard refused four socket
  connections from `tests/integration/test_api_endpoints.py::TestHealthEndpoint::test_health_returns_ok`
  to configured backend ports, first 8070. The watcher issued immediate owned TERM at 08:43:06;
  launcher PID 4184032 and its owned process group 5774 were confirmed dead by 08:43:10. Official
  exit was 143. The attempt produced no complete JUnit, native grade, or normal-completion flag;
  no counts or dataset from it are accepted. Raw evidence:
  `/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/baseline-native-v6-results-20261027-attempt1/`.
- Tool bootstrap's initial npm `ENOENT` is preserved. Bootstrap resume (preflight attempt 31)
  completed at 08:46:20–08:46:31 UTC: pinned ShellCheck 0.11.0, shfmt 3.14.1, markdownlint 0.45.0, Node
  22.23.4, npm 10.9.9; native tool SHA was verified offline, home remained unchanged, custody
  matched, and normal completion was recorded. This is tool setup only, not execution of project
  gates. Evidence is under `/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/gates-coverage-v2/`.

The next source change is an API health test fixture that supplies a fake backend while preserving
the health semantics and the tripwire. Its source agent is working; the full baseline has not been
rearmed.

## Next work

1. Fix the API health fixture with a fake backend while preserving health semantics and the
   tripwire; run the relevant guarded API integration and scoped baseline proof.
2. Run the official full baseline and accept counts/dataset only from a valid complete capture.
3. Run full candidate native validation, required gates, and coverage; only then prepare private
   publication for review.

Codex NI owns the production `embedder.py` fix per the owner's 20:55 correction. This checkpoint's
session owns only CI test guard/tripwire work and does not edit that production file. The four
protected P5 files remain unchanged. No main promotion is authorized by these results. P3 and the
integration candidate do not close O8 or the wider refactor; O8's handoff checkbox remains
unchecked.
