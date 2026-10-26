# Native CI JUnit compatibility checkpoint — 2026-10-26

The prospective producer recognizes exact module-level collection skips separately
from named test cases. The pytest 9.0.3 plugin observes passed `SubtestReport`
events and removes only their individually verified redundant passed-counter
contributions before the exporter first serializes JUnit. It records the excluded
report count in reserved suite properties. Named cases receive no invented subtest
identities; collection skips and anonymous passed-subtest counters are explicitly
excluded from the bounded proposition.

Every suite still requires exact tests/failure/error/skip count equality. Missing
cases, repeated or nested status nodes, anonymous non-skip nodes, conflicting
collection/execution identities, and malformed accounting metadata fail closed.
The existing CI adapter, ClaimTuple grading, source class and ladder are unchanged.
Plain JUnit summaries and propositions retain their previous shape.

## Validation custody

Coordinator-admitted model-free preflight ran from 16:22:58Z to 16:23:11Z on
2026-10-26, using CPUs 24,25, one numeric thread per library, external temporary
and pycache directories, and the baseline pytest 9.0.3 environment. Result:
**72 passed in 11.75s**, exit 0; P1-A checked seven tuples from one source kind
with zero byte-identity/grade-invariance violations. The two files executed were
`tests/vidya/test_ci_conformance.py` and
`tests/vidya/test_pytest_junit_compat.py`.

Local original validation custody:
`/mnt/raid0/llm/tmp/refactor-01a16fc3/compute-coordination-20261026/preflight-attempt-12-carrier/`
(`run.sh`, `preflight.log`, `exit-status`, synthetic pytest artifacts).
The four reviewed source/test bytes matched the preflight seal and were unchanged
after that run:

| File | SHA-256 |
| --- | --- |
| scripts/ci/native_conformance.py | 5855a9c9b3f12ca8b170361cbe75f8751dfaabafe4b0cf061faeb33d3e3e5d41 |
| scripts/ci/epyc_pytest_junit_compat.py | 487d6514e4607b863510785b9aaf2e34fb171afcd3756848e6f85c68c6a8fc42 |
| tests/vidya/test_ci_conformance.py | f66c3dc9ac98918cabe453a52682baea45692bf0a0996551d06dfb855b8c30bf |
| tests/vidya/test_pytest_junit_compat.py | dfd9fc72bb8fec964982304fe92ae2f578d6ff6cdc430f598dd23905e3c5af6a |

Controls include real serial and xdist passed subtests, module collection skips,
failed subtests, failed parents, setup/teardown failures, strict suite-count
mismatches, collection collisions/duplicates, malformed/duplicate reserved
properties, and original artifact tampering. This validates synthetic fixture
execution and producer behavior, not the application suite or inference.

## Fresh-run integration

Create a separate clean carrier clone at this change's published commit; retain
`public-carrier` at `dbf3cc506a55e3aff5a48246ce44d34b677622da` unchanged.
Prepend the new carrier's `scripts/ci` directory to `PYTHONPATH` and add
`-p epyc_pytest_junit_compat` to fresh pytest argv alongside `--junitxml`.
The top-level module avoids the carrier/app `scripts` namespace collision.
Declare the plugin source, installed `_pytest/junitxml.py` and
`_pytest/subtests.py`, and dependency inventory in the prospective native readset,
alongside the existing source/recipe/harness pins. The plugin requires pytest
9.0.3 and a controller-owned JUnit exporter; workers forward typed subtest reports.

The original baseline receipt, log and JUnit bytes remain immutable. That receipt
is still NULL with no adapter row; this change neither repairs nor backfills it.
Its original JUnit has six more reported tests than testcase nodes, which the new
reader also does not excuse. A new result requires a new prospective execution
with a new request/readset and original emitted artifacts. No historical assertion,
new grade, or application-suite pass is claimed here.
