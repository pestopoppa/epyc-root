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


class CitationGatePhaseTest(unittest.TestCase):
    def _run(self, results, ledger_exists=True):
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
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1].args[0][0], sys.executable)

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

    def test_missing_ledger_rebuilds_before_cite_check(self):
        def results(cmd):
            if cmd[0] == "git":
                return _Result(0, stdout="docs/citation-policy.md\n")
            return _Result(0, stdout="entries read=1068  frames=1\nclean\n")

        errs, calls = self._run(results, ledger_exists=False)
        self.assertEqual(errs, [], "a clean run after a rebuild must pass")
        kinds = ["git" if c.args[0][0] == "git" else c.args[0][2] for c in calls]
        self.assertEqual(kinds, ["git", "ingest", "cite-check"])
        ingest = calls[1].args[0]
        self.assertEqual(ingest[2:4], ["ingest", "intake"])
        as_of = ingest[ingest.index("--as-of") + 1]
        self.assertIsNotNone(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", as_of),
                             "as-of must be current UTC, ISO-8601 with Z")
        cite = calls[2].args[0]
        self.assertEqual(cite[2:6], ["cite-check", "--as-of", as_of, "docs/citation-policy.md"],
                         "cite-check must run on the changed paths only, at the same as-of")

    def test_rebuild_failure_fails_the_phase(self):
        def results(cmd):
            if cmd[0] == "git":
                return _Result(0, stdout="wiki/x.md\n")
            return _Result(2, stderr="ingest exploded\n")

        errs, calls = self._run(results, ledger_exists=False)
        self.assertEqual(len(errs), 1)
        self.assertIn("ledger rebuild failed", errs[0])
        self.assertIn("ingest exploded", errs[0])
        self.assertEqual(len(calls), 2, "cite-check must not run after a failed rebuild")


if __name__ == "__main__":
    unittest.main(verbosity=2)
