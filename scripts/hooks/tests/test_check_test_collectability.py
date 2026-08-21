#!/usr/bin/env python3
"""Unit suite for the vacuous-pass gate (scripts/hooks/check_test_collectability.py).

The gate is a LIVE pre-commit hook: a false positive blocks real commits fleet-wide.
Four false-positive classes were already found in it AFTER it shipped, every one from
under-modelling pytest's collector, so each is pinned here as a regression test.

Every fixture is built under tmp_path. Pointing these at real repo files would make
the suite fail whenever an unrelated session edits an unrelated file.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

LINT_PATH = Path(__file__).resolve().parents[1] / "check_test_collectability.py"


def _load_lint():
    spec = importlib.util.spec_from_file_location("check_test_collectability_undertest", LINT_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def lint():
    """A fresh module per test -- the lint memoises analyses with lru_cache."""
    return _load_lint()


def _write(root: Path, rel: str, body: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def _run(lint, root: Path, *argv: str) -> tuple[int, str]:
    """Invoke main() exactly as the pre-commit hook does; return (rc, stderr)."""
    import io
    import contextlib

    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        rc = lint.main(["check_test_collectability.py", str(root), *argv])
    return rc, err.getvalue()


# --------------------------------------------------------------- shape B / empty

def test_shape_b_self_runner_blocks(lint, tmp_path):
    p = _write(tmp_path, "test_selfrunner.py", (
        "def main():\n    return 0\n\n"
        'if __name__ == "__main__":\n    raise SystemExit(main())\n'
    ))
    problems, advisories = lint.check(tmp_path, [p])
    assert any("SELF-RUNNER" in m for m in problems), problems


def test_empty_file_blocks(lint, tmp_path):
    p = _write(tmp_path, "test_empty.py", "")
    problems, _ = lint.check(tmp_path, [p])
    assert any("runs nothing either way" in m for m in problems), problems


def test_deliberate_self_runner_is_exempt(lint, tmp_path, monkeypatch):
    p = _write(tmp_path, "pkg/test_exempt.py", (
        "def main():\n    return 0\n\n"
        'if __name__ == "__main__":\n    raise SystemExit(main())\n'
    ))
    monkeypatch.setitem(lint.DELIBERATE_SELF_RUNNERS, "pkg/test_exempt.py", "reason under test")
    problems, _ = lint.check(tmp_path, [p])
    assert problems == []


# ------------------------------------------------- collector modelling (FP 1/3/4)

UNITTEST_SUITE = (
    "import unittest\n\n"
    "class SomethingNotNamedTest(unittest.TestCase):\n"
    "    def test_one(self):\n"
    "        self.assertEqual(1, 1)\n"
)


def test_unittest_testcase_collectable_by_base_class(lint, tmp_path):
    """FP class 4: only Test*-named classes were descended into."""
    p = _write(tmp_path, "test_unittest_style.py", UNITTEST_SUITE)
    collectable, _ = lint.analyse(p)
    assert collectable == ["test_one"]
    problems, advisories = lint.check(tmp_path, [p])
    assert problems == [] and advisories == []


def test_conftest_fixture_args_do_not_decide_collectability(lint, tmp_path):
    """FP class 3: an unrecognised (conftest) fixture arg is still collected."""
    p = _write(tmp_path, "test_conftest_fixture.py",
               "def test_thing(my_project_fixture):\n    assert my_project_fixture\n")
    collectable, fixture_using = lint.analyse(p)
    assert collectable == ["test_thing"] and fixture_using == ["test_thing"]
    problems, _ = lint.check(tmp_path, [p])
    assert problems == []


# ------------------------------------------------------------- the *_test.py glob

SELF_RUNNER = (
    "def main():\n    return 0\n\n"
    'if __name__ == "__main__":\n    raise SystemExit(main())\n'
)


def test_underscore_test_suffix_is_discovered_by_default_walk(lint, tmp_path):
    _write(tmp_path, "pkg/legacy_test.py", SELF_RUNNER)
    rc, err = _run(lint, tmp_path)
    assert rc == 1
    assert "pkg/legacy_test.py" in err


def test_underscore_test_suffix_accepted_as_explicit_path(lint, tmp_path):
    """The old filter dropped an explicitly passed *_test.py -- a silent pass."""
    p = _write(tmp_path, "pkg/legacy_test.py", SELF_RUNNER)
    rc, err = _run(lint, tmp_path, str(p))
    assert rc == 1, err
    assert "pkg/legacy_test.py" in err


def test_non_test_filename_is_still_ignored(lint, tmp_path):
    """Widening must not swallow ordinary modules: check_*/probe_* stay invisible."""
    p = _write(tmp_path, "pkg/probe_thing.py", SELF_RUNNER)
    rc, err = _run(lint, tmp_path, str(p))
    assert rc == 0, err
    assert "probe_thing" not in err


# --------------------------------------------------------- assertion density (VT-6)

def test_zero_assertion_suite_is_advisory_not_blocking(lint, tmp_path):
    p = _write(tmp_path, "test_probe.py",
               "import requests\n\n"
               "def test_health(server_url):\n"
               "    resp = requests.get(server_url)\n"
               "    print(resp.status_code)\n")
    problems, advisories = lint.check(tmp_path, [p])
    assert problems == []
    assert any("ZERO assertions" in a for a in advisories), advisories


def test_same_file_helper_that_asserts_counts_as_asserting(lint, tmp_path):
    """Without one level of indirection this re-creates the false-positive problem."""
    p = _write(tmp_path, "test_helper_indirection.py",
               "def _expect(value):\n    assert value\n\n"
               "def test_thing():\n    _expect(True)\n")
    problems, advisories = lint.check(tmp_path, [p])
    assert problems == [] and advisories == []


def test_pytest_raises_counts_as_an_assertion(lint, tmp_path):
    p = _write(tmp_path, "test_raises.py",
               "import pytest\n\n"
               "def test_boom():\n"
               "    with pytest.raises(ValueError):\n"
               "        raise ValueError\n")
    _, advisories = lint.check(tmp_path, [p])
    assert advisories == []


def test_unittest_assert_counts_as_an_assertion(lint, tmp_path):
    p = _write(tmp_path, "test_unittest_assert.py", UNITTEST_SUITE)
    _, advisories = lint.check(tmp_path, [p])
    assert advisories == []


def test_unresolvable_call_target_errs_toward_asserting(lint, tmp_path):
    """Under-flagging is safe for an advisory; over-flagging gets the lint disabled."""
    p = _write(tmp_path, "test_unresolvable.py",
               "from .helpers import *  # noqa\n\n"
               "def test_thing():\n    verify_everything()\n")
    _, advisories = lint.check(tmp_path, [p])
    assert advisories == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
