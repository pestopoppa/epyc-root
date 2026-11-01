# P6 surfaces source closure evidence

Date: 2026-11-01
ROOT publication: `9bb9ef9fcf2234dfa06643cef57581a98494c23c` (two parents: hygiene parent `f9905cfba94c4aca7167e346871d95516061d1a5` and accepted implementation `58f03662e8aee1305012c9bee84d5aae3e1a2036`).
Implementation source: `58f03662e8aee1305012c9bee84d5aae3e1a2036`.
Research producer context: `94b1dd64c163d915eb1347b118f57e44e981bf78`.

## Scope and outcome

This closes the P6 parent and its P6.8 child as one work-queue item. No P6.1–P6.7 item is newly credited. The root dashboard now presents the surviving AutoKernel loop, operator gates, and the existing Research `progression.v1` export. The dashboard is a bounded, read-only presentation reader; it adds no producer, measurement, or Vidya adapter. Missing, malformed, unknown, future, stale, and all-negative states remain visible. A failed fetch clears prior fresh content. The optional card has its own registry entry, API surface, health probe, and freshness envelope. `/api/loop/health` continues to fold independent loop and operator-gate subject verdicts; intentional gate HOLD and artifact age remain separate from subject health. `/health` remains transport-only.

The retired source/digest decoder and six obsolete decoder test files were removed. Useful terminal/evidence inspection remains unserved in `kernel_contract`; freeze and ELF checks remain unserved in `kernel_identity`. Production defaults resolve through the ratified v10 manifest and production KERNEL STORE. Speech identities and bindings remain. Missing identity cannot match itself merely because both sides are absent.

The rewritten `server.py` is 2,191 lines versus 15,238 at ROOT baseline `7011d23a76a28cb71860a29d00c442d3ed1d25db`. The final four modules contain zero fixed 64-hex digest literals. The separate historical source-gate count was 29 paths / 47 pins; the broader census of old readers found 82 occurrences / 60 distinct literals. All 100 removed function/class names are retained in `removed-functions.json`. `final-extraction-audit.json` records location-independent AST and call/reference comparisons; `vidya-caller-audit.json` records the Vidya source-reference audit. No server reference was found in `scripts/vidya/**/*.py`.

The exact six test files approved for retirement are documented by `p64-test-retirement.json`. The exact `7011d23` baseline reproduced 12 decoder failures, with IDs preserved in `legacy-decoder-baseline-failure-ids.json`. The earlier P6.4 count of 40→12 had already retired 28 deleted-page cases in 2026-08-30; this wrap does not re-credit those cases. No other test file was deleted. The two injected-child tests call `serial_run._main`, the same entry point used by the producer's own tests. They exercise the real `Popen` child identity/join, status, continuation, and DOM assertions; they do not claim CLI or watchdog-supervisor coverage.

The missing SQLite fixture was restored byte-for-byte from the unchanged `7f0509be…` source using the declared schema and sorted-status/last-three-row extraction. `fixture-db-sorted.db` is the restored fixture; its SHA-256 is `eaa63786777f71f85bdd31f9ef7882a9886c9f32c67eb5a21b046e411f16f903`. `fixture-db-native.db` preserves the producer-native ordering for comparison. No manifest re-pin or invented observation was introduced.

No live service reload/deployment, model call, inference, kernel build, production tree/store mutation, or measurement claim occurred. Evidence labels are software verification only: `[no-belief: software verification]`.

## Hosted CI runs

Each run's original ZIP, API records, logs, JUnit, source hashes, dependency pins, environment records, and exit codes are retained separately under `runs/`. Counts below are individual run results; do not add them together. Baseline failures and broad-suite results are shown to preserve the actual history, not to turn a broad suite with known failures into a green result.

| Run | Candidate result | Primary result | Disposition |
|---|---|---|---|
| `41292164204` | 79 failed, 681 passed, 85 skipped; baseline 10 failed, 173 passed, 2 skipped | — | Original early red run retained. |
| `41292673955` | 29 failed, 803 passed, 1 skipped; baseline 64 failed, 797 passed, 28 skipped, 45 errors | — | Original intermediate run retained. |
| `41293625359` | 6 failed, 826 passed, 1 skipped; baseline 64 failed, 797 passed, 28 skipped, 45 errors | 2 failed, 524 passed | Original intermediate red run retained. |
| `41294207360` | 4 failed, 831 passed, 1 skipped; baseline 64 failed, 797 passed, 28 skipped, 45 errors | 529 passed | Green primary; broad failures are the four unchanged baseline navigation failures, with one existing live-host skip. |
| `41294664497` | 4 failed, 835 passed, 1 skipped; baseline 64 failed, 797 passed, 28 skipped, 45 errors | 533 passed | Green primary; broad failures are the four unchanged baseline navigation failures, with one existing live-host skip. |
| `41295259263` | — | 535 passed | Final-source primary-only run; 181 subtests passed, zero failures/errors/skips, exit 0, Python 3.13.15. This is the final acceptance run. |

The broad runs also report their own subtest counts in their retained logs. The final source acceptance is the primary-only run `41295259263`; no final broad-suite green claim is made. The four residual broad failures are the unchanged static-site navigation cases; the one skip requires the frozen live host resolver.

The final primary run's original source archive is `runs/ci-41295259263-original/archive.original.zip`, size 85,639 bytes, SHA-256 `8ea836b80bb319bfa3c791ca53ad9bfe9e96ff744c4715d0c8df54f99d0e488e`. Its source manifest, JUnit, API records, dependency lock, Python version, and exit code are stored alongside it. The hosted recipe used Python 3.13.15 and the existing six-wheel `--require-hashes` closure.

## Reproduce evidence integrity checks

From this directory:

```bash
sha256sum -c SHA256SUMS
```

No local test suite is rerun by this wrap-up; the recorded hosted outputs are the source of the test results above.
