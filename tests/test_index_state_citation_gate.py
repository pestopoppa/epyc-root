#!/usr/bin/env python3
"""Unit tests for index_state.citation_check — the SC12 citation-gate phase of `--check`.

Stdlib ``unittest`` only (no pytest dependency) so it runs anywhere with
``python3 tests/test_index_state_citation_gate.py``; pytest also discovers it.

WHY THIS FILE EXISTS. `--check` is the mandatory pre-commit index gate; wiring the citation
gate into it turns every commit touching handoffs/wiki/docs into an SC12 enforcement point.
The behaviors that must not regress: a diff that touches nothing under the scanned paths
skips the phase entirely (no vidya subprocess at all), a blocking run (exit 3) fails the
phase with the gate's listing and the fix instructions, and a missing ledger is rebuilt via
`ingest intake` before cite-check runs. All subprocesses are mocked; nothing here reads the
real ledger or calls git.
"""

import importlib.util
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

_REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "index_state", _REPO / "scripts" / "handoffs" / "index_state.py")
index_state = importlib.util.module_from_spec(_SPEC)
sys.modules["index_state"] = index_state
_SPEC.loader.exec_module(index_state)


class _Result:
    """subprocess.CompletedProcess lookalike."""

    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _sub(cmd):
    """vidya subcommand of `python cli.py --ledger L <sub> ...`."""
    return cmd[cmd.index("--ledger") + 2] if "--ledger" in cmd else cmd[2]


class CitationGatePhaseTest(unittest.TestCase):
    def _run(self, results, ledger_exists=True, fresh=True):
        inner = results

        def results(cmd):  # noqa: F811 - freshness probe answered here; tests script the rest
            if cmd[0] != "git" and _sub(cmd) == "sync" and "--check" in cmd:
                return _Result(0 if fresh else 1)
            return inner(cmd)

        with patch.object(index_state, "VIDYA_LEDGER",
                          SimpleNamespace(exists=lambda: ledger_exists)), \
             patch.object(index_state.subprocess, "run") as m:
            m.side_effect = lambda cmd, **kw: results(cmd)
            errs = index_state.citation_check()
        return errs, m.call_args_list

    # ---- fast path -------------------------------------------------------

    def test_no_changes_under_scanned_paths_skips_the_phase(self):
        """A diff touching only scripts/ never invokes vidya; the phase passes."""
        errs, calls = self._run(lambda cmd: _Result(0, stdout="scripts/vidya/citation_gate.py\n"))
        self.assertEqual(errs, [])
        self.assertEqual(len(calls), 1, "no vidya subprocess may run on the fast path")
        self.assertEqual(calls[0].args[0], ["git", "diff", "--name-only", "HEAD"])

    def test_changed_paths_outside_the_scanned_prefixes_skip_the_phase(self):
        errs, calls = self._run(
            lambda cmd: _Result(0, stdout="scripts/handoffs/index_state.py\nprogress/x.md\n"))
        self.assertEqual(errs, [])
        self.assertEqual(len(calls), 1)

    # ---- blocking run ----------------------------------------------------

    def test_blocking_exit_3_fails_the_phase_with_instructions(self):
        def results(cmd):
            if cmd[0] == "git":
                return _Result(0, stdout="wiki/agent-architecture.md\n")
            return _Result(3, stdout="  [dangling] intake-2602  wiki/agent-architecture.md\n"
                                     "1 blocking citation(s) -- exit 3\n")

        errs, calls = self._run(results)
        self.assertEqual(len(errs), 1, "one blocking citation is one problem")
        joined = "\n".join(errs)
        self.assertIn("BLOCKING", errs[0])
        self.assertIn("intake-2602", joined, "the gate's own listing must be surfaced")
        self.assertIn("#record", joined)
        self.assertIn("#NN", joined)
        self.assertEqual(len(calls), 3)  # git diff, sync --check, cite-check
        self.assertEqual(calls[2].args[0][0], sys.executable)

    def test_unexpected_exit_fails_with_captured_output(self):
        def results(cmd):
            if cmd[0] == "git":
                return _Result(0, stdout="wiki/x.md\n")
            return _Result(2, stderr="something broke\n")

        errs, calls = self._run(results)
        self.assertEqual(len(errs), 1)
        self.assertIn("something broke", errs[0])
        self.assertIn("exit 2", errs[0])

    # ---- ledger self-heal -------------------------------------------------

    def test_missing_ledger_syncs_before_cite_check(self):
        def results(cmd):
            if cmd[0] == "git":
                return _Result(0, stdout="docs/citation-policy.md\n")
            return _Result(0, stdout="sync: ingested\nclean\n")

        errs, calls = self._run(results, ledger_exists=False)
        self.assertEqual(errs, [], "a clean run after a sync must pass")
        kinds = ["git" if c.args[0][0] == "git" else _sub(c.args[0]) for c in calls]
        self.assertEqual(kinds, ["git", "sync", "sync", "cite-check"])
        sync = calls[2].args[0]
        as_of = sync[sync.index("--as-of") + 1]
        self.assertIsNotNone(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", as_of),
                             "as-of must be current UTC, ISO-8601 with Z")
        cite = calls[3].args[0]
        self.assertEqual(cite[cite.index("cite-check"):], ["cite-check", "--as-of", as_of,
                                                          "docs/citation-policy.md"],
                         "cite-check must run on the changed paths only, at the same as-of")

    def test_stale_ledger_triggers_incremental_sync_not_unknown(self):
        def results(cmd):
            if cmd[0] == "git":
                return _Result(0, stdout="wiki/x.md\n")
            return _Result(0, stdout="ok\n")

        errs, calls = self._run(results, ledger_exists=True, fresh=False)
        self.assertEqual(errs, [])
        kinds = ["git" if c.args[0][0] == "git" else _sub(c.args[0]) for c in calls]
        self.assertEqual(kinds, ["git", "sync", "sync", "cite-check"])
        self.assertNotIn("--check", calls[2].args[0], "the second sync is the real ingest")

    def test_fresh_ledger_does_not_sync(self):
        def results(cmd):
            if cmd[0] == "git":
                return _Result(0, stdout="wiki/x.md\n")
            return _Result(0, stdout="ok\n")

        _, calls = self._run(results, fresh=True)
        kinds = ["git" if c.args[0][0] == "git" else _sub(c.args[0]) for c in calls]
        self.assertEqual(kinds, ["git", "sync", "cite-check"])

    def test_sync_failure_fails_the_phase(self):
        def results(cmd):
            if cmd[0] == "git":
                return _Result(0, stdout="wiki/x.md\n")
            return _Result(2, stderr="ingest exploded\n")

        errs, calls = self._run(results, ledger_exists=False)
        self.assertEqual(len(errs), 1)
        self.assertIn("ledger sync failed", errs[0])
        self.assertIn("ingest exploded", errs[0])
        self.assertEqual(len(calls), 3, "cite-check must not run after a failed sync")


if __name__ == "__main__":
    unittest.main(verbosity=2)
