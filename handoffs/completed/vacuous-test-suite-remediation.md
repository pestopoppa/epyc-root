# Vacuous-pass test suites — remediation backlog

> **COMPLETED 2026-08-21.** Historical ledger; the living rules are
> [`docs/guides/agent-workflows/test-suite-conventions.md`](../../docs/guides/agent-workflows/test-suite-conventions.md)
> and the gate itself (`scripts/hooks/check_test_collectability.py`).

**Status**: COMPLETED 2026-08-21, same day — all eight tasks closed by a four-agent fan-out
(VT-1+3 orchestrator, VT-2+6 gate, VT-4+7 exemptions/convention, VT-5+8 research probes), integrated
and verified by the owning session. Residual: 3 vendored kvpress zero-assertion advisories,
explicitly DECLINED (upstream NVIDIA code — do not fix).
**Categories**: verification_integrity, test_infrastructure, quality_gates
**Parent index**: was [`research-evaluation-index.md`](../active/research-evaluation-index.md) (row EVL-50, deleted on completion)
**Related**: [`progress/2026-08/2026-08-20.md`](../../progress/2026-08/2026-08-20.md) (origin);
[Benchmark Methodology](../../wiki/benchmark-methodology.md) → *a capture can lie about its own protocol*

## Objective

A **vacuous pass** is a suite that reports success while executing nothing. Two were found on
2026-08-20 and both were nearly trusted; an audit found more. The mechanical half is done. This
handoff carries the per-file repairs and the gate's own blind spots.

## What is already LIVE (do not redo)

- **`pytest.ini`: `filterwarnings = error::pytest.PytestReturnNotNoneWarning`** — a test that
  RETURNS instead of asserting is reported PASSED by pytest. Both tests in
  `scripts/hooks/tests/test_live_holder_interference.py` did exactly that, so the suite guarding
  **live inference regions** went green with a non-empty failure list. Now fails. (`1047d255`)
- **That suite is repaired** — private helpers + asserting wrappers, and `--all` (opt-IN) inverted
  to `--fast` (opt-OUT) so the default no longer runs half the suite. The guard itself was always
  correct; only its test was lying.
- **`scripts/hooks/check_test_collectability.py`** + pre-commit wiring, **changed files only**.
  Blocks shape B (self-runner pytest collects 0 from) and "no test and no `__main__`".
  Installed via `scripts/hooks/install_git_hooks.sh` — **a clone that has not run the installer is
  not protected**; the committed file alone does nothing.
- **Refusing `__main__` stanza** added to `test_v7_quality_gate_runner.py` and
  `test_pgpu1_artifact_completeness_audit.py` (research).

## The counts are 0/0/0 — and that is NOT "nothing left to do"

After four false-positive repairs the gate reports **0 blocking** in all three repos (was
17 / 104 / 26). That is honest for what the gate *measures*, and misleading as a picture of health:
the genuinely-blocking files were fixed or exempted on 2026-08-20/21, and **everything else the
audit found is either advisory here or outside this lint's reach**. The tasks below are that
remainder. Do not read 0/0/0 as "audit closed".

## Tasks

- [x] **VT-1** ✅ 2026-08-21 — moved to `tests/unit/test_audit_repository.py` (+ the docs-index
      sibling), `SCRIPT` re-anchored, refusing-`__main__` added. **6/6 pass under the default
      `testpaths` suite** — first time this security-audit suite has ever executed. Original claim: No `__main__` (so `python3 file.py` executes nothing) **and** it sits outside
      `testpaths = ["tests"]` (`pyproject.toml:134`), so the default `pytest` never collects it.
      A security-audit suite that has never run. Highest single item.
- [x] **VT-2** ✅ 2026-08-21 — both globs in discovery AND explicit-path handling (the old filter
      silently dropped a passed `*_test.py` — itself a vacuous shape). `seal_multi_role_test.py` →
      `seal_multi_role_regression_check.py` with honest exit status (`sys.exit(1)` on any regressed or
      failed-to-run role; JSON unchanged). Pre-commit pathspec widened to match and reinstalled;
      END-TO-END probe: a `*_test.py` self-runner commit is refused. Original claim: `check_test_collectability.py` globs
      only `test_*.py`, so `research/scripts/benchmark/seal_multi_role_test.py` is invisible to it —
      the audit's HIGH finding that prints `Regression YES!` and then **exits 0** (no `sys.exit`,
      no failure accumulation, no assertion in the file). Fix the glob, then fix that file.
- [x] **VT-3** ✅ 2026-08-21 — closed BY CONSTRUCTION, not by widening: nothing test-named remains
      outside `tests/` (2 genuine suites moved in; 2 probes renamed `*_check.py`/`probe_*.py` with
      their `test_`-prefixed helpers renamed too). `find scripts -name 'test_*.py' -o -name '*_test.py'`
      → empty. Original claim: Either add `scripts` to `testpaths`
      or forbid the `test_*.py` name outside `tests/`. Four files are currently invisible to the
      suite everyone runs. VT-1 is one of them; fixing the policy fixes the class.
- [x] **VT-4** ✅ 2026-08-21 — `test_merge_gate` exemption CONFIRMED accurate; `test_unblock_artifact`
      verified to touch NO shared state (all writes through rebound globals into tempdirs), bridged
      (`assert main() == 0`; pytest 1 passed, self-run 27/27), its exemption DELETED;
      `test_commit_hygiene` KEPT with a firm four-hazard reason (parallel-run probe race, stray
      untracked file, live-hook subprocesses, FETCH_HEAD-mtime flakiness). Original scope: Each is exempt with a
      written reason, but two were exempted provisionally:
      `scripts/coordination/tests/test_unblock_artifact.py` ("collectable form not yet reviewed for
      shared-state writes") and `scripts/hooks/tests/test_commit_hygiene.py`. `test_merge_gate.py`
      is a firm exemption — it rewrites `coordination/session-bus/human_only_paths.sha256` to
      simulate drift, so a collectable form would mutate a shared trust-boundary file on every
      repo-wide test run and an interrupted run would leave the fleet's merge gate failed closed.
- [x] **VT-5** ✅ 2026-08-21 — all three renamed `probe_*.py` (internal `test_`-prefixed functions
      renamed too; they were collectable with unfulfillable fixtures). Zero live references confirmed
      before each rename. Originally: (research): `scripts/voice/test_latency.py`
      (+ its duplicate `scripts/voice/voice/test_latency.py`), `scripts/test_summarization.py`.
      They contain no `assert`/`raises`/`fail`. Rename to `check_*`/`probe_*` or give them assertions.
- [x] **VT-6** ✅ 2026-08-21 — ADVISORY tier added, with one-level same-file helper indirection
      counted as asserting (else every factored suite false-positives). Precision at scale: 0
      advisories across 791 orchestrator + 139 root files; catches both known probes on their
      pre-rename content. Mutation-verified (9/9 caught). Originally: — flag any `test_*.py` where no collectable test contains
      `assert` / `pytest.raises` / `pytest.fail`. Catches the VT-5 class mechanically. Cheap.
- [x] **VT-7** ✅ 2026-08-21 — `docs/guides/agent-workflows/test-suite-conventions.md` (120 lines,
      INDEX row added): both measured shapes, the naming rule, all three sanctioned stanzas, the
      exemption process, and the installer gap. Originally: — self-runners get a non-collectable name (`check_*.py`);
      anything named `test_*` MUST be pytest-collectable. Reference bridge:
      `scripts/coordination/tests/test_bus_supervisor.py:568` (`assert main() == 0`).
- [x] **VT-8** ✅ 2026-08-21 — provenance traced: BOTH nested dirs (`legacy/legacy/`, `voice/voice/`)
      born as self-copies in the initial import commit `0b6f3112`, zero live references, inner
      `whisper_server.py` actively regressive (missing offline pinning). Both dirs DELETED; survivor
      `run_pard_test.py` → `run_pard_probe.py` (shape-B self-runner under the widened glob). Originally: — `research/scripts/legacy/run_pard_test.py` and
      `scripts/legacy/legacy/run_pard_test.py` are byte-identical; neither's canonical status is
      known. Determine and delete one.

## The gate's own blind spots — read before trusting a 0

Four false-positive classes were found in `check_test_collectability.py` **after** it was written,
two of them while it was already live and refusing legitimate commits. All four made it
**under-count** what pytest collects, which is the unsafe direction:

| # | Bug | Symptom |
|---|---|---|
| 1 | module-level functions only | 237 orchestrator files reported "runs nothing" (class-based suites) |
| 2 | nested worktree inside `/workspace` | 138 files counted twice |
| 3 | arg shape decided collectability | every conftest-fixture suite misjudged; orchestrator 26 → 0 |
| 4 | only `Test*`-named classes descended into | `unittest.TestCase` subclasses missed; `test_promote_lane.py` (22 tests collected) called vacuous |

**A lint must model the collector it reasons about.** Shape A (fixture suite, no `__main__`) is
ADVISORY, not blocking, because the directory-level mixed-convention proxy is too coarse — one
self-runner in a 450-file `tests/` dir would flag every sibling.

## Why a lint and not a conftest collection floor

The audit's first-ranked fix was a `pytest_collection_modifyitems` floor raising on any file that
yields 0 items. Rejected: it runs **inside** pytest, where a mis-fire breaks every invocation for
every session, and it cannot express "self-runner ON PURPOSE" — see the `test_merge_gate.py`
reasoning in VT-4. A lint runs at authoring time, cannot break a test run, and forces every
exemption to be written down with a reason.

## Deps

None. VT-1/VT-3 are orchestrator-side; the rest are epyc-root or research.

## Completion record (2026-08-21)

Four Opus agents in parallel, disjoint file scopes, no-commit contract (owning session integrated).
Final sweep: **0 blocking everywhere** — workspace 139 files / 16 advisory, research 274 / 3 advisory
(all vendored kvpress, declined), orchestrator 791 / 0. The gate's test suite: 13 tests, 9 mutations
all caught, and the suite found a fifth latent lint bug in the process (absolute-path skip matching
made any checkout under a `tmp`-containing path invisible to the default walk). End-to-end: a
`*_test.py` self-runner commit is refused by the installed pre-commit hook.
