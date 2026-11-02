#!/usr/bin/env python3
"""CAF-2 wrapup.py — temp repo with a bare origin + lane worktree; the push step is faked (git push origin HEAD:main)."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

_CHURN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "churn")
if _CHURN not in sys.path:
    sys.path.insert(0, _CHURN)
import wrapup as wu  # noqa: E402

HANDOFF = """# Demo handoff

- [ ] **D-1 — first task.** do the thing
- [ ] **D-2 — second task.** another thing
- [ ] **D-3 — twin.** same words here
- [ ] **D-4 — twin.** same words here too
- [x] **D-0 — done.** ✅ 2026-10-30
"""


def _git(cwd, *a):
    return subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, check=True).stdout


def fake_push(lane, slug):
    r = subprocess.run(["git", "-C", lane, "push", "-q", "origin", "HEAD:main"], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class WrapupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wrapup-")
        seed = os.path.join(self.tmp, "seed")
        os.makedirs(os.path.join(seed, "handoffs/active"))
        with open(os.path.join(seed, "handoffs/active/demo.md"), "w") as fh:
            fh.write(HANDOFF)
        with open(os.path.join(seed, "notes.md"), "w") as fh:
            fh.write("n\n")
        _git(seed, "init", "-q", "-b", "main")
        _git(seed, "config", "user.email", "t@t")
        _git(seed, "config", "user.name", "t")
        _git(seed, "add", "-A")
        _git(seed, "commit", "-q", "-m", "seed")
        bare = os.path.join(self.tmp, "origin.git")
        _git(seed, "init", "-q", "--bare", bare)
        _git(seed, "remote", "add", "origin", bare)
        _git(seed, "push", "-q", "origin", "main")
        _git(seed, "fetch", "-q", "origin")
        self.lane = os.path.join(self.tmp, "h-demo")
        _git(seed, "worktree", "add", "-q", "-b", "lane/h-demo", self.lane, "origin/main")
        self.seed, self.bare = seed, bare
        self.flags = os.path.join(self.tmp, "flags")
        self.rec = {"slug": "demo", "state": "progress", "task_text": "D-1 first task", "ticks": ["D-1 — first task."],
                    "progress_md": "Did D-1.\n", "paths": ["notes.md"], "belief": "no-belief: conformance only",
                    "message": "Finish D-1", "question": None, "rows_published": [],
                    "trailers": ["Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"]}
        with open(os.path.join(self.lane, "notes.md"), "a") as fh:
            fh.write("edited\n")
        with open(os.path.join(self.lane, "untracked-noise.txt"), "w") as fh:
            fh.write("must not be committed\n")

    def _run(self, rec, extra=()):
        p = os.path.join(self.tmp, "rec.json")
        json.dump(rec, open(p, "w"))
        out, err = io.StringIO(), io.StringIO()
        with patch.object(wu, "run_push", fake_push), patch.object(wu, "run_index_check", lambda lane: (0, "ok")), \
                patch.object(wu, "run_index_regen", lambda lane: (0, "")), patch.object(wu, "PUSH_SLEEP_S", 0), redirect_stdout(out), redirect_stderr(err):
            rc = wu.main(["--json", p, "--lane", self.lane, "--flags", self.flags, *extra])
        return rc, out.getvalue(), err.getvalue()

    def test_happy_path(self):
        rc, out, err = self._run(self.rec)
        self.assertEqual(rc, 0, err + out)
        sha = _git(self.lane, "rev-parse", "HEAD").strip()
        self.assertEqual(out.strip().splitlines()[-1], f"WRAPPED {sha}")
        self.assertEqual(_git(self.lane, "cherry", "origin/main").strip(), "")
        self.assertEqual(_git(self.seed, "--git-dir", self.bare, "rev-parse", "main").strip(), sha)
        files = _git(self.lane, "show", "--name-only", "--format=", "HEAD").split()
        self.assertIn("notes.md", files)
        self.assertIn("handoffs/active/demo.md", files)
        self.assertTrue(any(f.startswith("progress/") and f.endswith("-handoff-demo.md") for f in files), files)
        self.assertNotIn("untracked-noise.txt", files)
        self.assertEqual(len(files), 3)
        body = _git(self.lane, "log", "-1", "--format=%B")
        self.assertIn("Finish D-1", body)
        self.assertIn("Co-Authored-By: Claude Opus 5.5", body)
        ho = open(os.path.join(self.lane, "handoffs/active/demo.md")).read()
        self.assertEqual(ho.count("- [x]"), 2)
        line = [ln for ln in ho.splitlines() if "D-1" in ln][0]
        self.assertTrue(line.startswith("- [x]") and "✅ 20" in line and "[no-belief: conformance only]" in line, line)
        prog = [f for f in files if f.startswith("progress/")][0]
        ptxt = open(os.path.join(self.lane, prog)).read()
        self.assertTrue(ptxt.startswith("# "), ptxt)
        self.assertIn("— D-1 first task", ptxt)
        self.assertIn("Did D-1.", ptxt)
        rep = json.load(open(os.path.join(self.flags, "handoff-sessions/demo/report.json")))
        self.assertEqual(rep["wrapped_sha"], sha)
        self.assertEqual(rep["state"], "progress")
        self.assertIn("wrapped_at", rep)
        self.assertIs(rep["wrapped"], True)
        self.assertEqual(rep["ticks"], ["D-1 — first task."])

    def test_generated_index_conflict_takes_origin_and_lands(self):
        gen = "handoffs/active/.index-state.json"
        for d, v in ((self.seed, "base"),):
            open(os.path.join(d, gen), "w").write(v + "\n")
            _git(d, "add", gen); _git(d, "commit", "-q", "-m", "gen"); _git(d, "push", "-q", "origin", "main")
        _git(self.lane, "fetch", "-q", "origin"); _git(self.lane, "merge", "-q", "--ff-only", "origin/main")
        open(os.path.join(self.lane, gen), "w").write("lane\n")
        _git(self.lane, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "lane gen", "--", gen)
        open(os.path.join(self.seed, gen), "w").write("origin\n")
        _git(self.seed, "commit", "-q", "-am", "origin gen"); _git(self.seed, "push", "-q", "origin", "main")
        rc, out, err = self._run(self.rec)
        self.assertEqual(rc, 0, err + out)
        self.assertIn("generated conflicts took origin", err + out)
        self.assertEqual(open(os.path.join(self.lane, gen)).read(), "origin\n")
        self.assertEqual(_git(self.lane, "cherry", "origin/main").strip(), "")

    def test_failed_push_writes_report_with_next(self):
        rec = dict(self.rec, next="inference")
        p = os.path.join(self.tmp, "rec.json")
        json.dump(rec, open(p, "w"))
        out, err = io.StringIO(), io.StringIO()
        with patch.object(wu, "PUSH_RETRIES", 1), patch.object(wu, "run_push", lambda lane, slug: (4, "PUSH FAILED")), \
                patch.object(wu, "run_index_check", lambda lane: (0, "ok")), \
                patch.object(wu, "run_index_regen", lambda lane: (0, "")), redirect_stdout(out), redirect_stderr(err):
            rc = wu.main(["--json", p, "--lane", self.lane, "--flags", self.flags])
        self.assertEqual(rc, 1)
        rep = json.load(open(os.path.join(self.flags, "handoff-sessions/demo/report.json")))
        self.assertEqual((rep["next"], rep["wrapped"]), ("inference", False))
        self.assertIn("PUSH FAILED", rep["failure"])

    def _assert_no_commit(self, rc, err, needle):
        self.assertEqual(rc, 1)
        self.assertIn(needle, err)
        self.assertEqual(_git(self.lane, "rev-parse", "HEAD"), _git(self.lane, "rev-parse", "origin/main"))
        self.assertEqual(open(os.path.join(self.lane, "handoffs/active/demo.md")).read(), HANDOFF)
        rep = json.load(open(os.path.join(self.flags, "handoff-sessions/demo/report.json")))
        self.assertIs(rep["wrapped"], False)
        self.assertIn(rep["next"], ("non-inference", "inference", "blocked"))
        self.assertIn(needle, rep["failure"])
        self.assertNotIn("wrapped_sha", rep)

    def test_tick_zero_matches_refuses(self):
        rc, out, err = self._run(dict(self.rec, ticks=["D-9 — nowhere"]))
        self._assert_no_commit(rc, err, "matches 0 open boxes")

    def test_tick_two_matches_refuses(self):
        rc, out, err = self._run(dict(self.rec, ticks=["same words here"]))
        self._assert_no_commit(rc, err, "matches 2 open boxes")

    def test_bad_belief_and_state_refuse(self):
        rc, out, err = self._run(dict(self.rec, belief="maybe"))
        self._assert_no_commit(rc, err, "bad belief")
        rc, out, err = self._run(dict(self.rec, state="finished"))
        self._assert_no_commit(rc, err, "bad state")

    def test_dry_run_commits_nothing(self):
        rc, out, err = self._run(self.rec, extra=["--dry-run"])
        self.assertEqual(rc, 0, err + out)
        self.assertEqual(out.strip().splitlines()[-1], "DRY-RUN OK")
        self.assertNotIn("WRAPPED", out)
        self.assertEqual(_git(self.lane, "rev-parse", "HEAD"), _git(self.lane, "rev-parse", "origin/main"))
        self.assertEqual(open(os.path.join(self.lane, "handoffs/active/demo.md")).read(), HANDOFF)
        self.assertFalse(os.path.isdir(os.path.join(self.lane, "progress")))
        self.assertFalse(os.path.exists(os.path.join(self.flags, "handoff-sessions/demo/report.json")))


    def test_detached_wrapup_survives_its_caller_being_killed(self):
        """D9: codex exec tore the wrap-up down mid-push when its turn ended. Killing
        the caller's whole process group must not stop the push or orphan it."""
        import signal
        import time
        stubs = {"scripts/coordination/serialized_push.py":
                 "import subprocess, sys, time\nlane = sys.argv[sys.argv.index('--repo') + 1]\n"
                 "time.sleep(2)\nr = subprocess.run(['git', '-C', lane, 'push', '-q', 'origin', 'HEAD:main'])\n"
                 "sys.exit(r.returncode)\n",
                 "scripts/handoffs/index_state.py": "print('ok')\n"}
        for rel, body in stubs.items():
            os.makedirs(os.path.dirname(os.path.join(self.lane, rel)), exist_ok=True)
            with open(os.path.join(self.lane, rel), "w") as fh:
                fh.write(body)
        p = os.path.join(self.tmp, "rec.json")
        json.dump(self.rec, open(p, "w"))
        env = {k: v for k, v in os.environ.items() if k != "WRAPUP_INNER"}
        fg = subprocess.Popen([sys.executable, os.path.join(_CHURN, "wrapup.py"), "--json", p, "--lane", self.lane,
                               "--flags", self.flags], stdout=subprocess.PIPE, text=True, start_new_session=True,
                              env=env)
        first = fg.stdout.readline()
        self.assertIn("[wrapup] detached: pid=", first)
        time.sleep(0.5)
        os.killpg(fg.pid, signal.SIGKILL)   # what codex exec does to a yielded command at turn end
        fg.wait(timeout=10)
        report = os.path.join(self.flags, "handoff-sessions", "demo", "report.json")
        deadline = time.monotonic() + 60
        while not os.path.exists(report) and time.monotonic() < deadline:
            time.sleep(0.2)
        self.assertTrue(os.path.exists(report), "the detached wrap-up must finish after its caller died")
        sha = json.load(open(report))["wrapped_sha"]
        self.assertEqual(_git(self.seed, "--git-dir", self.bare, "rev-parse", "main").strip(), sha)
        logs = [f for f in os.listdir(os.path.dirname(report)) if f.startswith("wrapup-") and f.endswith(".log")]
        self.assertTrue(logs)
        self.assertTrue(open(os.path.join(os.path.dirname(report), logs[0])).read().strip().endswith(f"WRAPPED {sha}"))


if __name__ == "__main__":
    unittest.main()
