# Vacuous-pass test suites — remediation backlog

**Status**: active (created 2026-08-21) — the mechanical gates are LIVE; what remains is per-file
repair plus two known coverage gaps in the gate itself.
**Categories**: verification_integrity, test_infrastructure, quality_gates
**Parent index**: [`research-evaluation-index.md`](research-evaluation-index.md)
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

- [ ] **VT-1 — `epyc-orchestrator/scripts/security/test_audit_repository.py` runs under NEITHER
      entry point.** No `__main__` (so `python3 file.py` executes nothing) **and** it sits outside
      `testpaths = ["tests"]` (`pyproject.toml:134`), so the default `pytest` never collects it.
      A security-audit suite that has never run. Highest single item.
- [ ] **VT-2 — Close the `*_test.py` glob gap in the gate.** `check_test_collectability.py` globs
      only `test_*.py`, so `research/scripts/benchmark/seal_multi_role_test.py` is invisible to it —
      the audit's HIGH finding that prints `Regression YES!` and then **exits 0** (no `sys.exit`,
      no failure accumulation, no assertion in the file). Fix the glob, then fix that file.
- [ ] **VT-3 — Decide the orchestrator `testpaths` policy.** Either add `scripts` to `testpaths`
      or forbid the `test_*.py` name outside `tests/`. Four files are currently invisible to the
      suite everyone runs. VT-1 is one of them; fixing the policy fixes the class.
- [ ] **VT-4 — Review the three `DELIBERATE_SELF_RUNNERS` exemptions.** Each is exempt with a
      written reason, but two were exempted provisionally:
      `scripts/coordination/tests/test_unblock_artifact.py` ("collectable form not yet reviewed for
      shared-state writes") and `scripts/hooks/tests/test_commit_hygiene.py`. `test_merge_gate.py`
      is a firm exemption — it rewrites `coordination/session-bus/human_only_paths.sha256` to
      simulate drift, so a collectable form would mutate a shared trust-boundary file on every
      repo-wide test run and an interrupted run would leave the fleet's merge gate failed closed.
- [ ] **VT-5 — Zero-assertion probe scripts misnamed as tests** (research): `scripts/voice/test_latency.py`
      (+ its duplicate `scripts/voice/voice/test_latency.py`), `scripts/test_summarization.py`.
      They contain no `assert`/`raises`/`fail`. Rename to `check_*`/`probe_*` or give them assertions.
- [ ] **VT-6 — Assertion-density lint** — flag any `test_*.py` where no collectable test contains
      `assert` / `pytest.raises` / `pytest.fail`. Catches the VT-5 class mechanically. Cheap.
- [ ] **VT-7 — Naming convention** — self-runners get a non-collectable name (`check_*.py`);
      anything named `test_*` MUST be pytest-collectable. Reference bridge:
      `scripts/coordination/tests/test_bus_supervisor.py:568` (`assert main() == 0`).
- [ ] **VT-8 — Duplicate legacy files** — `research/scripts/legacy/run_pard_test.py` and
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
