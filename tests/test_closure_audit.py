#!/usr/bin/env python3
"""Fixture test for scripts/handoffs/closure_audit.py — real refs resolve, phantom refs are class b.

Stdlib ``unittest`` only; runs with ``python3 tests/test_closure_audit.py`` and under pytest.

WHY THIS FILE EXISTS. The 2026-09-16 audit (progress/2026-09/2026-09-16-sub-closure-audit.md)
found ticked boxes asserting code that was on no ref (RC-9, E1a, UTM-M7/M8). The tool is the
only thing that catches that, so it needs a pinned contract. Each phantom case below has a real
twin in the same box, which proves the tool resolves refs rather than flagging everything. The
snake_case case is checked both with and without ``--strict-idents``, so the test shows the flag
is what catches it.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_TOOL = _REPO / "scripts" / "handoffs" / "closure_audit.py"


def _git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                          text=True).stdout.strip()


class ClosureAuditFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        repo = Path(cls._tmp.name) / "root"
        (repo / "src").mkdir(parents=True)
        (repo / "handoffs" / "active").mkdir(parents=True)
        _git(repo.parent, "init", "-q", "-b", "main", str(repo))
        _git(repo, "config", "user.email", "t@example.invalid")
        _git(repo, "config", "user.name", "fixture")
        (repo / "src" / "ledger.py").write_text(
            "def real_selector(rows):\n    return rows\n\nREAL_COLUMN = 'real_payload_json'\n")
        (repo / "src" / "test_stem_only.py").write_text("pass\n")
        _git(repo, "add", "src/ledger.py", "src/test_stem_only.py")
        _git(repo, "commit", "-q", "-m", "add real selector")
        cls.real_sha = _git(repo, "rev-parse", "--short=9", "HEAD")
        _git(repo, "checkout", "-q", "-b", "side")
        (repo / "src" / "side.py").write_text("def branch_only_selector():\n    return 1\n")
        _git(repo, "add", "src/side.py")
        _git(repo, "commit", "-q", "-m", "branch-only work")
        _git(repo, "checkout", "-q", "main")
        (repo / "handoffs" / "active" / "fixture.md").write_text(
            "# Fixture\n\n"
            f"- [x] **FX-1 — selector** ✅ 2026-09-16 — added `real_selector()` in `src/ledger.py` "
            f"(commit {cls.real_sha}); also added `phantom_selector()` in `src/phantom_mod.py` "
            "and `branch_only_selector()`.\n"
            "- [x] **FX-2 — columns** ✅ 2026-09-16 — now persists `real_payload_json` and "
            "`phantom_payload_json` columns; `test_stem_only` passed.\n"
            "- [ ] **FX-3 — open** — `never_checked_func()` is not verified (box is open).\n")
        _git(repo, "add", "handoffs/active/fixture.md")
        _git(repo, "commit", "-q", "-m", "fixture handoff")
        cls.repo = repo

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _run(self, *extra, triage=None):
        out = Path(self._tmp.name) / f"out{len(extra)}{'t' if triage else ''}"
        cmd = [sys.executable, str(_TOOL), "--root", str(self.repo), "--orch", str(self.repo),
               "--research", str(self.repo), "--rev", "main", "--no-external",
               "--json", str(out / "a.json"), "--md", str(out / "a.md"), "--tsv", str(out / "a.tsv"),
               *extra]
        if triage:
            tp = out.with_suffix(".triage.json")
            out.mkdir(parents=True, exist_ok=True)
            tp.write_text(json.dumps(triage))
            cmd += ["--triage", str(tp)]
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull)
        subprocess.run(cmd, check=True, capture_output=True, text=True, env=env, timeout=300)
        data = json.loads((out / "a.json").read_text())
        refs = {}
        for b in data["flagged"]:
            for r in b["refs"]:
                refs[r["value"]] = r
        return data, refs

    def test_default_run_flags_phantoms_and_resolves_real_refs(self):
        data, refs = self._run()
        self.assertEqual(data["n_boxes"], 2, "only checked boxes are audited")
        self.assertEqual(refs["phantom_selector"]["cls"], "b")
        self.assertEqual(refs["src/phantom_mod.py"]["cls"], "b")
        self.assertEqual(refs["real_selector"]["cls"], "ok")
        self.assertEqual(refs["branch_only_selector"]["cls"], "a")
        self.assertIn("off-main: root:side", refs["branch_only_selector"]["detail"])
        self.assertEqual(refs["src/ledger.py"]["cls"], "ok")
        self.assertEqual(refs[self.real_sha]["cls"], "ok")
        self.assertNotIn("never_checked_func", refs)
        # without --strict-idents the snake_case column claim is invisible
        self.assertNotIn("phantom_payload_json", refs)
        self.assertEqual(data["counts"]["ident"], {"ok": 1, "a": 1, "b": 1})

    def test_strict_idents_catches_snake_case_phantom(self):
        data, refs = self._run("--strict-idents")
        self.assertTrue(data["strict_idents"])
        self.assertEqual(refs["phantom_payload_json"]["cls"], "b")
        self.assertEqual(refs["real_payload_json"]["cls"], "ok")
        self.assertEqual(refs["test_stem_only"]["cls"], "ok", "a file stem counts as present")

    def test_triage_override_applies_and_untriaged_is_marked(self):
        _, refs = self._run(triage={"overrides": [
            {"key": "fixture.md|phantom_selector()", "class": "b TRUE", "action": "REOPEN"}]})
        self.assertEqual(refs["phantom_selector"]["triage_class"], "b TRUE")
        self.assertEqual(refs["phantom_selector"]["triage_action"], "REOPEN")
        self.assertEqual(refs["src/phantom_mod.py"]["triage_action"], "UNTRIAGED")


if __name__ == "__main__":
    unittest.main()
