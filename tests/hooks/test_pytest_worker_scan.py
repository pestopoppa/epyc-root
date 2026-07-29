"""C21: the pytest-worker guard must match INVOCATIONS, not text.

The guard blocks `pytest -n auto` / `-n N > 16` on a 192-thread machine. Its
original regex ran `pytest.*-n\\s*[0-9]+` across the whole command string, where
`.*` crosses shell separators and quotes. That blocked:

  * a pytest run piped into a `sed` line-range — the line range read as workers;
  * the bus message REPORTING that bug, because its payload quoted the pattern;
  * this file's own first fixture, a heredoc listing `-n auto` as example data.

Three data-vs-command boundaries fix it, and the ALLOW cases below are the
regression: quoted runs are data, a later pipeline stage is a different program,
and a heredoc body is being written rather than run. The BLOCK cases are the
safety property, which did not move — detection of `pytest` stays deliberately
generous about position so wrappers (`timeout`, `python -m`, `xargs`) stay caught.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCANNER = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "pytest_worker_scan.py"
_spec = importlib.util.spec_from_file_location("pytest_worker_scan", SCANNER)
assert _spec and _spec.loader
scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan)


@pytest.mark.parametrize("command", [
    "pytest -n auto",
    "pytest -n=auto",
    "pytest -n 32 tests/",
    "timeout 900 python -m pytest -n 64 tests/unit",
    "xargs pytest -n 64",
    # A heredoc that ENDS before a real invocation must not shield it.
    "cat x <<'EOF'\ndata\nEOF\npytest -n 40",
])
def test_unsafe_worker_counts_are_still_blocked(command: str) -> None:
    assert scan.unsafe_worker_verdict(command), f"must block: {command!r}"


@pytest.mark.parametrize("command", [
    "pytest -n 8 tests/",                                   # at the cap
    "pytest -q tests/ | sed -n 340,360p",                   # later stage, other program
    "pytest -q tests/foo.py; sed -n 1,50p bar.txt",         # separator ends the segment
    "./session_bus.py append --json '{\"note\":\"pytest -n 340 blocked this\"}'",
    "grep -n 340 file.txt",                                 # no pytest at all
    "head -n 100 log.txt",
    "cat > cases.txt <<'EOF'\npytest -n auto is the example\nEOF",   # quoted marker
    "cat > c.txt <<EOF\npytest -n 99\nEOF",                          # bare marker
])
def test_data_that_merely_mentions_the_pattern_is_not_an_invocation(command: str) -> None:
    assert not scan.unsafe_worker_verdict(command), f"must allow: {command!r}"


def test_quote_stripping_preserves_offsets() -> None:
    """Contents are blanked, length is kept — offsets stay meaningful."""
    original = "echo 'pytest -n 99' && pytest -n 4"
    stripped = scan.strip_quoted(original)
    assert len(stripped) == len(original)
    assert "99" not in stripped and "pytest -n 4" in stripped


def test_heredoc_stripping_runs_before_quote_stripping() -> None:
    """A quoted heredoc marker must survive long enough to be recognised.

    Reversing the order blanks `'EOF'` into `''`, leaving no detectable
    terminator — the body is then scanned as commands and the guard fires on its
    own fixture again.
    """
    command = "cat <<'EOF'\npytest -n auto\nEOF"
    assert not scan.unsafe_worker_verdict(command)
    assert "pytest" not in scan.strip_heredocs(command)
