# Test-suite conventions — naming, bridges, and the two vacuous-pass shapes

**Status**: reference · **Created**: 2026-08-21 (VT-7) · **Origin**: measured, not theorised —
both shapes below are files that were on disk, green, and trusted on 2026-08-20.
**Owning handoff**: [`handoffs/completed/vacuous-test-suite-remediation.md`](../../../handoffs/completed/vacuous-test-suite-remediation.md)
**Related**: [Benchmark Methodology](../../../wiki/benchmark-methodology.md) → *a capture can lie about its own protocol*;
[verification-failure-catalogue.md](verification-failure-catalogue.md) (face: *a check not COUNTED by the reporter*).

## The failure this prevents

A **vacuous pass** is a suite that reports success while executing nothing. It is worse than no
suite, because it also supplies confidence. Two shapes exist, and a file has exactly one of them
depending on which entry point you use — which is why the naming rule below is about *names*, not
about intent.

### Shape A — fixture suite with no `__main__`

`test_*` functions taking fixtures, no `if __name__ == "__main__":`. Running
`python3 the_file.py` defines the functions, calls none of them, and **exits 0**.

> Measured 2026-08-20: `epyc-inference-research/scripts/benchmark/test_v7_quality_gate_runner.py`.
> A session ran it directly, read the green exit as a real pass, and moved on.

Shape A is *normal and harmless* inside a repo's pytest collection scope, where nobody invokes files
directly. It is a hazard only in a **mixed-convention directory** — one holding both pytest suites
and self-runners — where a direct invocation is a reasonable thing to do. That is why the lint
reports it as **advisory**, never blocking.

### Shape B — self-runner with no collectable test

All logic in `main()` under `__main__`, no module-level or class-level `test_*` callable.
`pytest the_file.py` **collects 0 items and reports success**, having run nothing.

> Measured 2026-08-20: `scripts/hooks/tests/test_commit_hygiene.py` and the merge-gate and
> unblock-artifact suites beside it — all under a `tests/` directory, all with a `__pycache__`
> proving pytest had walked them.

A third, adjacent shape is closed by config rather than convention: **a test that `return`s a
failure list instead of asserting is reported PASSED**. Both tests in
`scripts/hooks/tests/test_live_holder_interference.py` did exactly that, so the suite guarding live
inference regions went green with a non-empty failure list. `pytest.ini` now carries
`filterwarnings = error::pytest.PytestReturnNotNoneWarning`, which makes that shape fail at the
moment someone writes it.

## The naming rule

> **Anything matching `test_*.py` or `*_test.py` MUST be pytest-collectable.**
> A script that is not meant to be collected takes a name that does not match:
> `check_*.py`, `probe_*.py`, `run_*.py`.

The name is the contract because the name is what the collector reads. "It was obviously a
self-runner, look at the `__main__`" is not visible to pytest, to CI, or to the next session
running `pytest scripts/`. A zero-assertion latency probe named `test_latency.py` will be counted
as coverage by every human who greps for it (VT-5 tracks four such files).

## The two sanctioned bridges

**Assert-main** — the default. Reference: `scripts/coordination/tests/test_bus_supervisor.py:568`.

```python
def test_bus_supervisor() -> None:
    """Make pytest COUNT this suite."""
    assert main() == 0, "bus_supervisor.sh regressions — see stdout"


if __name__ == "__main__":
    sys.exit(main())
```

Both entry points keep working, and the same failure surfaces two ways. **If `main()` parses
argv**, the bridge must not inherit pytest's argv: give `main()` a default (`def main(argv=None)`)
and call it as `main([])`, or split the case loop into a `_run_cases()` the bridge calls directly.
A bridge that passes pytest's `-q --tb=short` into an argparse parser turns a green suite into a
`SystemExit(2)` at collection time.

**Pytest-main** — for a self-runner whose cases are already parametrisable: convert the case table
into `@pytest.mark.parametrize` and let `__main__` call `pytest.main([__file__])`. Costs more edit,
buys per-case reporting instead of one aggregate assert.

**Refusing `__main__`** — the Shape-A remedy. A fixture suite cannot run itself, so it must say so
rather than exit 0:

```python
if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: "
                     "python -m pytest path/to/test_file.py -q")
```

## Exemptions are decisions, and they are written down

Some self-runners must **not** become collectable. They live in `DELIBERATE_SELF_RUNNERS` in
`scripts/hooks/check_test_collectability.py`, keyed by repo-relative path, valued by the reason. An
entry there is a decision, not a silencer: it asserts *running this under a bare `pytest` would be
worse than not collecting it*.

The canonical example of a correct exemption is
`scripts/coordination/tests/test_merge_gate.py`. Its fail-closed case overwrites
`coordination/session-bus/human_only_paths.sha256` with a bogus digest to simulate drift, and
restores it in a `finally`. Collectable, that means every repo-wide pytest run mutates a shared
trust-boundary file — and an interrupted run leaves the fleet's merge gate **failed closed**. No
naming convention outranks that.

The test for an exemption is not "is this file awkward to bridge" but **"what does a bare
repo-wide `pytest`, run by a parallel session, do to shared state while this file executes?"**
If the answer is "nothing outside a tempdir", bridge it.

## The enforcement chain — and its one gap

1. `scripts/hooks/check_test_collectability.py` runs **pre-commit, on changed files only**. It
   blocks Shape B and "no collectable test and no `__main__`"; Shape A is advisory.
2. `pytest.ini`'s `filterwarnings = error::pytest.PytestReturnNotNoneWarning` makes a returning
   test fail rather than pass.
3. **A clone is protected only after it has run `scripts/hooks/install_git_hooks.sh`.** The
   committed hook config alone protects nobody — measured 2026-08-21. Run the installer once per
   clone; a fresh worktree is unprotected until you do.

The lint is deliberately not a `pytest_collection_modifyitems` collection floor. A floor runs
*inside* pytest, where a mis-fire breaks every invocation for every session, and it cannot express
"self-runner ON PURPOSE". A lint runs at authoring time, cannot break a test run, and forces every
exemption to carry a written reason.
