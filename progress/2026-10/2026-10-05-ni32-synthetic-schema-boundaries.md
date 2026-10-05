# NI32: synthetic schema boundaries and native integrity controls

MAIN accepted original run
[37326107920](https://github.com/pestopoppa/epyc-root/actions/runs/37326107920)
on 2026-10-05. Parsed `ni32-schema-boundaries.xml` contains **12 passed,
0 failed, 0 errors, 0 skipped**. Test-only source
`59e21608997009f2aa432f227ab09f46aebf9beb` changes one module,
`tests/vidya/test_session_gap_schema_boundaries.py`. Recipe
`73f68fc356f8d11a4e99e9ef9a932f02c3a9fd76` binds that source and app contract
`300cf5817edccc4f82089f0faa477828496068b6`. The app checkout is read only;
its runtime modules are not imported or executed.

Four non-native shape/mixed cases verify explicit counters, no native coverage
or gap pairs, zero emitted ledger frames and intentional SC73 missing-ledger
refusal. One unkeyed tap control preserves the distinction from keyed tap events.
Four native controls independently retain exact/proxy timestamp basis and
known/unknown client class. Three coherently resealed source-identifier mutations
cannot substitute tap request, progress task or checkpoint IDs for native
adjacency. Existing producer, adapter, ledger and shared grader remain unchanged.

Synthetic shapes are grounded in the pinned app's `TapWriter._emit_event`,
inference caller metadata, `ProgressEntry.to_json`, `Checkpoint.to_dict` and
checkpoint persistence sources. All five source files are declared original
readset inputs. These fixtures establish source-schema boundaries and native
pair integrity, not live data coverage, inferred joins/enqueues, client brands,
distributions, percentiles, TTL decisions or promotion authority.

Original retry prefix and full log remain under
`/mnt/raid0/llm/worktrees/codex-ni32-schema-boundaries-validation-20261005/`:

- `ni32-retry-artifacts/ni32-37326107920-1-schema-boundaries/`
- `ni32-retry-artifacts/ni32-37326107920-1-native-projection/`
- `ni32-retry-run-full.log`

Original native receipt file SHA-256 is
`6a0ac7c4d67f136a61ecaf7041c967fbe0f12e4638b08cc52e05f55f1292ca4f`.
MAIN independently reopened the original receipt and all 20
request/readset/log/JUnit pins through the existing CI reader, sole projection
and shared grade: **true, exit 0, Judged / Located**. Execution used pytest 9.1.1,
Python 3.13, an inner 180-second INT/KILL15 bound and an outer native-producer
240-second TERM/KILL15 bound. Original projection was written before the strict
12-case success assertion.

The first run `37324987068` remains an unchanged original **false** finding:
8 passed, 4 failed, no errors/skips, exit 1. Its four failures came from this new
test's obsolete assumption that an absent ledger verifies successfully. The
test-only correction asserts the existing fail-closed missing-ledger behavior.
Original receipt file SHA-256
`0fc321bd4c28bedb7bc131f794abc7eb6a9110c311b908927a1c795bd52ceaa4`
and all original files remain outside Git at
`/mnt/raid0/llm/artifacts/ci/ni32-false-37324987068/`; none were resealed.

No local tests, raw tap/DB reads, inference, production changes or grader changes
ran. MAIN owns shared canonical closure, source promotion and public evidence
filing. This note records the accepted synthetic boundary work only.
