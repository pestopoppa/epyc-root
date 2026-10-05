# NI37: DTAP timeout reporting and prospective native integrity

MAIN accepted bounded implementation from original off-host run
[37341395541](https://github.com/pestopoppa/epyc-root/actions/runs/37341395541)
on 2026-10-05. Actual `original-junit.xml` module counts are:

| Module | Passed | Failed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| test_dtap_harness | 90 | 0 | 0 | 0 |
| test_judge_guard | 22 | 0 | 0 | 0 |
| test_dtap_timeout_report | 24 | 0 | 0 | 0 |
| test_ingest_sources | 58 | 0 | 0 | 0 |

App source is `4238a82eee82a38d5fe5b868949649dcc5c7e5d1`, root source
`a2494f019d5d662f56971142ccfd9b1d4610bc0c`, and recipe
`43c238b3bb5520fc751eeac02a6e2d0a6aa99089`. Source bases remain the explicitly
reviewed app `099dc1af69cf465641b77575e5082bc28ace23a7` and root
`ab7f19cdd0066a6a721dbef5ae4f82e5df794260`; candidate validation does not assert
main publication. MAIN owns source promotion and canonical closure.

Actual typed terminal timeout is distinct from other errors, recovered retries,
HTTP 504 and message-string guesses. Overall denominator is all units; finished
is all units less terminal timeouts, retaining other failures. Judged-only rate
is separately descriptive. Empty denominators remain null. Existing transport
caps and judge coercion are preserved; no whole-case deadline or outcome is
invented. Benign task success is higher better; attack success is lower better.
Primary native outcome must be boolean, while a nonapplicable secondary may be
boolean or null. Unknown primary is diagnostic, never a verdict or timeout.

Opt-in capture creates an exclusive original private pre-request before endpoint
construction or any run. Immutable original traces, execution UTC/elapsed,
source readsets, selected cases/judges, configuration and terminal results are
bound before independent component recomputation. Actual module origins,
private regular-file custody, original UUID identity, source drift, malformed
outcomes and public CLI/frame privacy have refusal controls. Old runs remain
plain or their original captured outcome; no retrospective sealing occurs.
The additive source-specific public report formatter preserves existing Source
positional fields and default formatting for every other source class.

Original public prefixes remain unchanged at
`/mnt/raid0/llm/artifacts/ci/ni37-final-37341395541/`:

- `ni37-37341395541-1-app-fixtures/native-ni37-app-fixtures/`
- `ni37-37341395541-1-reader-fixtures/native-ni37-reader-fixtures/`

MAIN independently strict-read both original CI receipts and native pins through
the sole projection/shared grade: **true, Judged / Located**, 112 and 82 cases.
Receipt file SHA-256 values are app
`c128c36491fec04e8263bb08b31972105260d909ff97f50265592007264b3559`
and reader
`07f42778c35a5066b53c2766299f3fce0e2803adf2c70c0df3a94a8587c4d054`.
The reader prefix binds `ni37-safe-native-projection.json` produced during actual
fixture execution. It records original synthetic inner receipt file digest
`c6aa5065605bedbb0a43cb26aeac8f657048ee730a7147192e0abfa45bd06178`,
shared Judged / Located and three frames: five units, two successes, overall
2/5, finished 2/4, timeout 1/5, judged 2/3 and one other error preserved.
MAIN verified this bound safe proof; it did not independently reopen the private
inner capsule. Private source bodies, traces, filenames and capsules were never
exported. Scope is synthetic report integrity, excluding live applicability,
performance, promotion and dependency completeness.

First run `37338161788` retains original app false (105 passed, 2 failed) and
reader null diagnostic (66 passed, 11 failed). Retry `37340808111` retains app
true (112 passed) and reader null diagnostic (80 passed, 2 failed), because its
safe generated projection was absent. The latter XML failures are not a native
false tuple. Original artifacts are held at
`/mnt/raid0/llm/artifacts/ci/ni37-first-37338161788/` and
`/mnt/raid0/llm/artifacts/ci/ni37-retry-37340808111/`; none were resealed.
The narrow corrections preserved actual judge coercion and supplied existing
shared frame API arguments to fixture calls.

Execution used Python 3.13, pytest 9.1.1 and PyYAML 6.0.3, the latter aligned to
the declared app uv.lock readset. This is selected dependency alignment, not a
full frozen lock install. Each command retained inner 180-second INT/KILL15 and
outer 240-second TERM/KILL15 bounds with immediate original prefix upload.
No local tests, inference, live endpoint calls, production changes or grader
changes ran. Public artifact manifest is
`/mnt/raid0/llm/worktrees/codex-ni-validation-ci-20261005/ni37-final-evidence-manifest.json`
(SHA-256 `ae6984d28670ecd0f03ee011d759a708f4e5318f47d559083e27ab6e7ef6a2df`).
