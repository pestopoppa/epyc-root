"""Shared lexer contract used by shell guards.

The guard tests exercise policy. These cases pin the common data/command boundary so
the lexer cannot regress on quoted text, heredocs, comments, or command framing.
"""
from __future__ import annotations

import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

from shell_scan import lex, segments  # noqa: E402


def test_lex_blanks_quoted_mentions_and_shell_comments() -> None:
    parts = lex("echo 'pkill -f hidden' # pkill -f comment\nkill 1234")
    assert len(parts) == 2
    assert "hidden" not in parts[0]
    assert "comment" not in parts[0]
    assert "kill 1234" in parts[1]


def test_lex_removes_quoted_and_unquoted_heredoc_bodies() -> None:
    quoted = lex("cat <<'EOF'\npkill -f hidden\nEOF\nkill 1234")
    unquoted = lex("cat <<EOF\npytest -n auto\nEOF\npytest -n 8")
    assert all("pkill -f hidden" not in part for part in quoted)
    assert any("kill 1234" in part for part in quoted)
    assert all("pytest -n auto" not in part for part in unquoted)
    assert any("pytest -n 8" in part for part in unquoted)


def test_lex_splits_pipeline_and_command_separators() -> None:
    assert [part.strip() for part in lex("one | two && three; four\nfive")] == [
        "one", "two", "three", "four", "five"
    ]


def test_segments_remains_a_compatible_alias() -> None:
    command = "cat <<'EOF'\npytest -n auto\nEOF\npytest -n 8"
    assert segments(command) == lex(command)
